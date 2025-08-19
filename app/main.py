# app/main.py
"""
FastAPI application for audio transcription and speaker diarization
"""

import os
import uuid
import json
import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from celery import Celery
import redis
import aiofiles

from .database import get_db, init_db
from .models import TranscriptionSession, TranscriptWord, Speaker
from .celery_app import celery_app
from .audio_transcription_core import AudioTranscriber
from .auth import verify_jwt_token, generate_test_token, verify_simple_api_key, SIMPLE_API_KEY
from .rate_limiter import RateLimiter

# Initialize FastAPI app
app = FastAPI(
    title="Audio Transcription API",
    description="AI-powered audio transcription with speaker diarization",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Configuration
UPLOAD_DIR = Path("storage/audio/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac"}
MAX_DURATION_MINUTES = 120

# Redis connection for rate limiting
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()  # Test connection
    rate_limiter = RateLimiter(redis_client, max_requests=30, window_minutes=1)
except Exception as e:
    print(f"Redis not available: {e}. Rate limiting disabled.")
    redis_client = None
    rate_limiter = None

@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks"""
    await init_db()
    print("Application started successfully")

@app.get("/auth/token")
async def get_test_token():
    """Generate a test JWT token for development"""
    token = generate_test_token("test_user")
    return {
        "access_token": token,
        "token_type": "bearer",
        "instructions": "Use this token in Authorization header: 'Bearer <token>'"
    }

@app.get("/auth/info")
async def auth_info():
    """Get authentication information"""
    return {
        "methods": [
            {
                "type": "JWT Token",
                "description": "Get token from /auth/token endpoint",
                "header": "Authorization: Bearer <jwt_token>"
            },
            {
                "type": "Simple API Key",
                "description": "Use the simple API key for quick testing",
                "header": f"Authorization: Bearer {SIMPLE_API_KEY}",
                "api_key": SIMPLE_API_KEY
            }
        ]
    }

@app.get("/healthz")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        await db.execute("SELECT 1")
        
        # Check Redis
        if redis_client:
            redis_client.ping()
        
        # Check storage
        if not UPLOAD_DIR.exists():
            raise Exception("Upload directory not accessible")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "ok",
                "redis": "ok",
                "storage": "ok"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and verify JWT token or API key"""
    try:
        # Try JWT token first
        payload = verify_jwt_token(credentials.credentials)
        return payload.get("sub", "anonymous")
    except Exception:
        # Try simple API key
        if verify_simple_api_key(credentials.credentials):
            return "api_user"
        raise HTTPException(status_code=401, detail="Invalid authentication token or API key")

def validate_audio_file(file: UploadFile) -> None:
    """Validate uploaded audio file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (this is approximate, actual size checked during upload)
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

@app.post("/api/v1/transcribe")
async def create_transcription_task(
    file: UploadFile = File(None),
    url: Optional[str] = Query(None, description="Pre-signed URL to audio file"),
    request: Request = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new transcription task
    
    Accept either file upload or URL parameter
    Returns task ID immediately
    """
    
    # Rate limiting (skip if Redis not available)
    if rate_limiter:
        client_ip = request.client.host
        await rate_limiter.check_rate_limit(f"user:{user_id}:{client_ip}")
    
    # Validate input
    if not file and not url:
        raise HTTPException(
            status_code=400,
            detail="Either 'file' upload or 'url' parameter is required"
        )
    
    if file and url:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'file' or 'url', not both"
        )
    
    task_id = str(uuid.uuid4())
    
    try:
        # Handle file upload
        if file:
            validate_audio_file(file)
            
            # Save uploaded file
            file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                await f.write(content)
            
            audio_source = str(file_path)
            source_type = "upload"
        
        # Handle URL
        else:
            # TODO: Add URL validation and download
            audio_source = url
            source_type = "url"
        
        # Create database session
        session = TranscriptionSession(
            id=task_id,
            user_id=user_id,
            audio_source=audio_source,
            source_type=source_type,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(session)
        await db.commit()
        
        # Start background task or process directly
        use_celery = os.getenv("USE_CELERY", "false").lower() == "true"
        
        if use_celery and redis_client:
            # Use Celery for background processing
            celery_app.send_task(
                'app.tasks.process_transcription',
                args=[task_id, audio_source],
                task_id=task_id
            )
        else:
            # Process in background thread (for development without Celery)
            print(f"Starting background processing for task {task_id}...")
            thread = threading.Thread(
                target=process_audio_background,
                args=(task_id, audio_source),
                daemon=True
            )
            thread.start()
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Transcription task created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup file if error occurs
        if file and 'file_path' in locals():
            try:
                file_path.unlink(missing_ok=True)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.get("/api/v1/transcribe/{task_id}/stream")
# async def stream_transcription_progress(
#     task_id: str,
#     user_id: str = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Stream transcription progress using Server-Sent Events
#     """
    
#     # Verify task exists and belongs to user
#     session = await db.get(TranscriptionSession, task_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Task not found")
    
#     if session.user_id != user_id:
#         raise HTTPException(status_code=403, detail="Access denied")
    
#     async def event_generator():
#         """Generate Server-Sent Events"""
#         last_status = None
        
#         while True:
#             try:
#                 # Refresh session from database
#                 await db.refresh(session)
                
#                 # Check if status changed
#                 if session.status != last_status:
#                     last_status = session.status
                    
#                     # Prepare progress data
#                     progress_data = {
#                         "task_id": task_id,
#                         "status": session.status,
#                         "progress": session.progress or 0,
#                         "timestamp": datetime.utcnow().isoformat()
#                     }
                    
#                     # Add error message if failed
#                     if session.status == "failed" and session.error_message:
#                         progress_data["error"] = session.error_message
                    
#                     # Send progress update
#                     yield f"data: {json.dumps(progress_data)}\n\n"
                    
#                     # If completed, send final result
#                     if session.status == "completed":
#                         # Fetch complete result
#                         result = await get_transcription_result(task_id, db)
#                         yield f"data: {json.dumps(result)}\n\n"
#                         break
                    
#                     # If failed, stop streaming
#                     elif session.status == "failed":
#                         break
                
#                 # Wait before next check
#                 await asyncio.sleep(2)
                
#             except Exception as e:
#                 error_data = {
#                     "task_id": task_id,
#                     "status": "error",
#                     "error": str(e),
#                     "timestamp": datetime.utcnow().isoformat()
#                 }
#                 yield f"data: {json.dumps(error_data)}\n\n"
#                 break
    
#     return StreamingResponse(
#         event_generator(),
#         media_type="text/plain",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Content-Type": "text/event-stream"
#         }
#     )

@app.get("/api/v1/transcribe/{task_id}/stream")
async def stream_transcription_progress(
    task_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream transcription progress using Server-Sent Events
    """
    
    # Verify task exists and belongs to user
    session = await db.get(TranscriptionSession, task_id)
    if not session:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    async def event_generator():
        """Generate Server-Sent Events"""
        last_status = None
        
        while True:
            try:
                # Fetch a fresh session object from the database in each iteration
                session = await db.get(TranscriptionSession, task_id)
                if not session:
                    error_data = {
                        "task_id": task_id,
                        "status": "error",
                        "error": "Task not found",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break
                
                # Check if status changed
                if session.status != last_status:
                    last_status = session.status
                    
                    # Prepare progress data
                    progress_data = {
                        "task_id": task_id,
                        "status": session.status,
                        "progress": session.progress or 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Add error message if failed
                    if session.status == "failed" and session.error_message:
                        progress_data["error"] = session.error_message
                    
                    # Send progress update
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    
                    # If completed, send final result
                    if session.status == "completed":
                        # Fetch complete result
                        result = await get_transcription_result(task_id, db)
                        yield f"data: {json.dumps(result)}\n\n"
                        break
                    
                    # If failed, stop streaming
                    elif session.status == "failed":
                        break
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                error_data = {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/api/v1/transcribe/{task_id}")
async def get_transcription_status(
    task_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get transcription task status and result"""
    
    session = await db.get(TranscriptionSession, task_id)
    if not session:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = {
        "task_id": task_id,
        "status": session.status,
        "progress": session.progress or 0,
        "created_at": session.created_at.isoformat(),
    }
    
    if session.status == "completed":
        result = await get_transcription_result(task_id, db)
        response["result"] = result
    elif session.status == "failed":
        response["error"] = session.error_message
    
    return response

async def get_transcription_result(task_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Build complete transcription result from database"""
    
    session = await db.get(TranscriptionSession, task_id)
    if not session:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get transcript words
    from sqlalchemy import select
    word_result = await db.execute(
        select(TranscriptWord)
        .where(TranscriptWord.session_id == task_id)
        .order_by(TranscriptWord.start_time)
    )
    words = word_result.scalars().all()
    
    # Get speakers
    speaker_result = await db.execute(
        select(Speaker)
        .where(Speaker.session_id == task_id)
        .order_by(Speaker.total_seconds.desc())
    )
    speakers = speaker_result.scalars().all()
    
    # Build transcript array
    transcript = []
    for word in words:
        transcript.append({
            "word": word.word,
            "start": word.start_time,
            "end": word.end_time,
            "speaker": word.speaker_label
        })
    
    # Build speakers array
    speakers_data = []
    for speaker in speakers:
        speakers_data.append({
            "id": speaker.speaker_id,
            "total_sec": speaker.total_seconds
        })
    
    return {
        "language": session.language or "en",
        "duration_sec": session.duration_seconds or 0,
        "transcript": transcript,
        "speakers": speakers_data,
        "confidence": session.confidence_score or 0.85
    }

async def save_transcription_results_direct(db: AsyncSession, task_id: str, result: Dict[str, Any]):
    """Save transcription results to database (direct processing)"""
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )