#!/usr/bin/env python3
"""
Audio Transcription and Speaker Diarization Core Functionality
This script processes audio files and returns transcription with speaker labels
"""

import os
import json
import time
import warnings
from typing import Dict, List, Any, Tuple
from pathlib import Path

import torch
import whisper
import librosa
import soundfile as sf
from pyannote.audio import Pipeline
from pyannote.core import Segment
import numpy as np

# Suppress warnings
warnings.filterwarnings("ignore")

class AudioTranscriber:
    def __init__(self, model_size: str = "large-v3"):
        """
        Initialize the transcriber with Whisper and pyannote models
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large, large-v2, large-v3)
        """
        print("Loading Whisper model...")
        self.whisper_model = whisper.load_model(model_size)
        
        print("Loading diarization pipeline...")
        # You need to accept pyannote terms and get HF token for this
        # For now, we'll use a basic approach - you may need to modify this
        try:
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token="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" # You'll need this
            )
        except Exception as e:
            print(f"Warning: Could not load diarization pipeline: {e}")
            print("Using fallback speaker detection...")
            self.diarization_pipeline = None
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, float]:
        """
        Load and preprocess audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_array, duration_in_seconds)
        """
        print(f"Loading audio file: {audio_path}")
        
        # Load audio with librosa (converts to mono, 22050 Hz by default)
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(audio) / sr
        
        print(f"Audio loaded: {duration:.2f} seconds, {sr} Hz, {len(audio)} samples")
        return audio, duration

    def transcribe_with_whisper(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper with word-level timestamps
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Whisper transcription result with word-level timestamps
        """
        print("Starting Whisper transcription...")
        start_time = time.time()
        
        # Transcribe with word-level timestamps
        result = self.whisper_model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=False
        )
        
        processing_time = time.time() - start_time
        print(f"Whisper transcription completed in {processing_time:.2f} seconds")
        
        return result

    def perform_diarization(self, audio_path: str) -> Dict[str, List[Tuple[float, float]]]:
        """
        Perform speaker diarization
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary mapping speaker IDs to list of (start, end) time segments
        """
        print("Starting speaker diarization...")
        
        if self.diarization_pipeline is None:
            # Fallback: create dummy speakers based on audio length
            print("Using fallback speaker detection...")
            audio, duration = self.load_audio(audio_path)
            
            # Simple fallback: split audio into segments and alternate speakers
            # This is just for demonstration - you should use proper diarization
            segments = []
            segment_length = 30.0  # 30 second segments
            current_time = 0.0
            speaker_id = 1
            
            while current_time < duration:
                end_time = min(current_time + segment_length, duration)
                segments.append((f"speaker_{speaker_id}", current_time, end_time))
                current_time = end_time
                speaker_id = 2 if speaker_id == 1 else 1  # Alternate between speakers
            
            # Convert to expected format
            speaker_segments = {}
            for speaker, start, end in segments:
                if speaker not in speaker_segments:
                    speaker_segments[speaker] = []
                speaker_segments[speaker].append((start, end))
            
            return speaker_segments
        
        try:
            # Real diarization with pyannote
            diarization = self.diarization_pipeline(audio_path)
            
            speaker_segments = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_id = f"speaker_{speaker.split('_')[-1] if '_' in speaker else speaker}"
                if speaker_id not in speaker_segments:
                    speaker_segments[speaker_id] = []
                speaker_segments[speaker_id].append((turn.start, turn.end))
            
            print(f"Diarization completed. Found {len(speaker_segments)} speakers")
            return speaker_segments
            
        except Exception as e:
            print(f"Diarization failed: {e}")
            return {"speaker_1": [(0.0, 999999.0)]}  # Single speaker fallback

    def assign_speakers_to_words(self, whisper_result: Dict, speaker_segments: Dict) -> List[Dict]:
        """
        Assign speaker labels to each word based on timestamps
        
        Args:
            whisper_result: Result from Whisper transcription
            speaker_segments: Speaker segments from diarization
            
        Returns:
            List of word dictionaries with speaker labels
        """
        print("Assigning speakers to words...")
        
        transcript_words = []
        
        # Extract all words with timestamps from all segments
        all_words = []
        for segment in whisper_result.get("segments", []):
            if "words" in segment:
                all_words.extend(segment["words"])
        
        # If no word-level timestamps, extract from segments
        if not all_words:
            for segment in whisper_result.get("segments", []):
                words = segment["text"].split()
                segment_duration = segment["end"] - segment["start"]
                word_duration = segment_duration / len(words) if words else 0
                
                for i, word in enumerate(words):
                    word_start = segment["start"] + (i * word_duration)
                    word_end = segment["start"] + ((i + 1) * word_duration)
                    all_words.append({
                        "word": word,
                        "start": word_start,
                        "end": word_end
                    })
        
        # Assign speakers to words
        for word_info in all_words:
            word_start = word_info["start"]
            word_end = word_info["end"]
            word_mid = (word_start + word_end) / 2
            
            # Find which speaker segment this word belongs to
            assigned_speaker = "speaker_1"  # Default
            
            for speaker_id, segments in speaker_segments.items():
                for seg_start, seg_end in segments:
                    if seg_start <= word_mid <= seg_end:
                        assigned_speaker = speaker_id
                        break
                if assigned_speaker != "speaker_1":
                    break
            
            transcript_words.append({
                "word": word_info["word"].strip(),
                "start": round(word_start, 2),
                "end": round(word_end, 2),
                "speaker": assigned_speaker
            })
        
        print(f"Assigned speakers to {len(transcript_words)} words")
        return transcript_words

    def calculate_speaker_stats(self, transcript_words: List[Dict]) -> List[Dict]:
        """
        Calculate speaking time statistics for each speaker
        
        Args:
            transcript_words: List of words with speaker assignments
            
        Returns:
            List of speaker statistics
        """
        speaker_times = {}
        
        for word in transcript_words:
            speaker = word["speaker"]
            duration = word["end"] - word["start"]
            
            if speaker not in speaker_times:
                speaker_times[speaker] = 0.0
            speaker_times[speaker] += duration
        
        speakers = []
        for speaker_id, total_time in speaker_times.items():
            speakers.append({
                "id": speaker_id,
                "total_sec": round(total_time, 2)
            })
        
        # Sort by speaking time (descending)
        speakers.sort(key=lambda x: x["total_sec"], reverse=True)
        
        return speakers

    def calculate_confidence(self, whisper_result: Dict) -> float:
        """
        Calculate overall confidence score from Whisper segments
        
        Args:
            whisper_result: Whisper transcription result
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        if "segments" not in whisper_result:
            return 0.85  # Default confidence
        
        segment_confidences = []
        for segment in whisper_result["segments"]:
            if "avg_logprob" in segment:
                # Convert log probability to confidence (rough approximation)
                confidence = max(0.0, min(1.0, np.exp(segment["avg_logprob"])))
                segment_confidences.append(confidence)
        
        if segment_confidences:
            return round(np.mean(segment_confidences), 2)
        else:
            return 0.85  # Default confidence

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Complete audio processing pipeline
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Complete transcription result in required format
        """
        print(f"\n{'='*50}")
        print(f"Processing: {audio_path}")
        print(f"{'='*50}")
        
        # Load audio to get duration
        audio, duration = self.load_audio(audio_path)
        
        # Step 1: Transcribe with Whisper
        whisper_result = self.transcribe_with_whisper(audio_path)
        
        # Step 2: Perform speaker diarization
        speaker_segments = self.perform_diarization(audio_path)
        
        # Step 3: Assign speakers to words
        transcript_words = self.assign_speakers_to_words(whisper_result, speaker_segments)
        
        # Step 4: Calculate speaker statistics
        speakers = self.calculate_speaker_stats(transcript_words)
        
        # Step 5: Calculate confidence
        confidence = self.calculate_confidence(whisper_result)
        
        # Step 6: Detect language
        language = whisper_result.get("language", "en")
        
        # Build final result
        result = {
            "language": language,
            "duration_sec": round(duration, 2),
            "transcript": transcript_words,
            "speakers": speakers,
            "confidence": confidence
        }
        
        print(f"\n{'='*50}")
        print(f"Processing completed!")
        print(f"Language: {language}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Words: {len(transcript_words)}")
        print(f"Speakers: {len(speakers)}")
        print(f"Confidence: {confidence}")
        print(f"{'='*50}")
        
        return result


def main():
    """
    Main function to test the transcription system
    """
    # Configuration
    AUDIO_FILE = r"D:\me\deep_gram\new_arch\audio.wav"  # Change this to your audio file path
    OUTPUT_FILE = "transcription_result.json"
    MODEL_SIZE = "base"  # Use "base" for faster processing, "large-v3" for better accuracy
    
    # Check if audio file exists
    if not os.path.exists(AUDIO_FILE):
        print(f"Error: Audio file '{AUDIO_FILE}' not found!")
        print("Please update the AUDIO_FILE variable with your WAV file path.")
        return
    
    try:
        # Initialize transcriber
        transcriber = AudioTranscriber(model_size=MODEL_SIZE)
        
        # Process audio
        result = transcriber.process_audio(AUDIO_FILE)
        
        # Save result to JSON file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nResult saved to: {OUTPUT_FILE}")
        
        # Print sample of transcript
        print(f"\nSample transcript (first 5 words):")
        for i, word in enumerate(result["transcript"][:5]):
            print(f"  {word['word']} ({word['start']}-{word['end']}s) - {word['speaker']}")
        
        if len(result["transcript"]) > 5:
            print(f"  ... and {len(result['transcript']) - 5} more words")
            
    except Exception as e:
        print(f"Error processing audio: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()