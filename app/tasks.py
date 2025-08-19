"""
Celery background tasks for audio processing
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from .celery_app import celery_app
    from .database import AsyncSessionLocal
    from .models import TranscriptionSession, TranscriptWord, Speaker
    from .audio_transcription_core import AudioTranscriber
except ImportError:
    from celery_app import celery_app
    from database import AsyncSessionLocal
    from models import TranscriptionSession, TranscriptWord, Speaker
    from audio_transcription_core import AudioTranscriber

# Initialize transcriber (will be loaded once per worker)
transcriber = None

def get_transcriber():
    """Lazy load transcriber to avoid loading models during import"""
    global transcriber
    if transcriber is None:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        transcriber = AudioTranscriber(model_size=model_size)
    return transcriber

@celery_app.task(bind=True)
def process_transcription(self, task_id: str, audio_source: str):
    """
    Background task to process audio transcription
    
    Args:
        task_id: Unique task identifier
        audio_source: Path to audio file or URL
    """
    async def run_transcription():
        async with AsyncSessionLocal() as db:
            try:
                # Update status to processing
                session = await db.get(TranscriptionSession, task_id)
                if not session:
                    raise Exception(f"Session {task_id} not found")
                
                session.status = "processing"
                session.started_at = datetime.utcnow()
                session.progress = 10
                await db.commit()
                
                # Update progress
                current_task.update_state(
                    state="PROGRESS",
                    meta={"progress": 10, "status": "Loading models..."}
                )
                
                # Get transcriber
                audio_transcriber = get_transcriber()
                
                # Update progress
                session.progress = 20
                await db.commit()
                current_task.update_state(
                    state="PROGRESS", 
                    meta={"progress": 20, "status": "Processing audio..."}
                )
                
                # Process audio
                result = audio_transcriber.process_audio(audio_source)
                
                # Update progress
                session.progress = 80
                await db.commit()
                current_task.update_state(
                    state="PROGRESS",
                    meta={"progress": 80, "status": "Saving results..."}
                )
                
                # Save results to database
                await save_transcription_results(db, task_id, result)
                
                # Update session as completed
                session.status = "completed"
                session.completed_at = datetime.utcnow()
                session.progress = 100
                session.language = result["language"]
                session.duration_seconds = result["duration_sec"]
                session.confidence_score = result["confidence"]
                await db.commit()
                
                current_task.update_state(
                    state="SUCCESS",
                    meta={"progress": 100, "status": "Completed", "result": result}
                )
                
                return result
                
            except Exception as e:
                # Update session as failed
                try:
                    session = await db.get(TranscriptionSession, task_id)
                    if session:
                        session.status = "failed"
                        session.error_message = str(e)
                        session.completed_at = datetime.utcnow()
                        await db.commit()
                except:
                    pass  # If we can't update DB, at least the task will show as failed
                
                current_task.update_state(
                    state="FAILURE",
                    meta={"progress": 0, "status": "Failed", "error": str(e)}
                )
                raise
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(run_transcription())
    finally:
        loop.close()

async def save_transcription_results(db: AsyncSession, task_id: str, result: Dict[str, Any]):
    """Save transcription results to database"""
    # Save transcript words
    for word_data in result["transcript"]:
        word = TranscriptWord(
            session_id=task_id,
            word=word_data["word"],
            start_time=word_data["start"],
            end_time=word_data["end"],
            speaker_label=word_data["speaker"]
        )
        db.add(word)
    
    # Save speakers
    for speaker_data in result["speakers"]:
        speaker = Speaker(
            session_id=task_id,
            speaker_id=speaker_data["id"],
            total_seconds=speaker_data["total_sec"]
        )
        db.add(speaker)
    
    await db.commit()