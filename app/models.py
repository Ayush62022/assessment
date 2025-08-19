"""
Database models for transcription service
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
try:
    from .database import Base
except ImportError:
    from database import Base

class TranscriptionSession(Base):
    """Main transcription session table"""
    __tablename__ = "transcription_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    audio_source = Column(String, nullable=False)  # File path or URL
    source_type = Column(String, nullable=False)   # 'upload' or 'url'
    
    # Status tracking
    status = Column(String, nullable=False, default="pending", index=True)
    progress = Column(Integer, default=0)  # 0-100
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    language = Column(String)
    duration_seconds = Column(Float)
    confidence_score = Column(Float)
    
    # Error handling
    error_message = Column(Text)
    
    # Relationships
    words = relationship("TranscriptWord", back_populates="session", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )

class TranscriptWord(Base):
    """Individual words with timestamps and speaker labels"""
    __tablename__ = "transcript_words"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("transcription_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Word data
    word = Column(String, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    speaker_label = Column(String, nullable=False)
    
    # Optional confidence for individual words
    confidence = Column(Float)
    
    # Relationships
    session = relationship("TranscriptionSession", back_populates="words")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_words_session_time', 'session_id', 'start_time'),
        Index('idx_words_session_speaker', 'session_id', 'speaker_label'),
    )

class Speaker(Base):
    """Speaker statistics for each session"""
    __tablename__ = "speakers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("transcription_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Speaker data
    speaker_id = Column(String, nullable=False)  # speaker_1, speaker_2, etc.
    total_seconds = Column(Float, nullable=False, default=0.0)
    
    # Optional metadata
    word_count = Column(Integer, default=0)
    
    # Relationships
    session = relationship("TranscriptionSession", back_populates="speakers")
    
    # Indexes
    __table_args__ = (
        Index('idx_speakers_session_speaker', 'session_id', 'speaker_id'),
    )