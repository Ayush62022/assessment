"""
JWT authentication utilities
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import HTTPException

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"

def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Simple API key authentication for development
SIMPLE_API_KEY = "transcription_api_key_123"

def verify_simple_api_key(api_key: str) -> bool:
    """Verify simple API key"""
    return api_key == SIMPLE_API_KEY

# Helper endpoint to generate test tokens (remove in production)
def generate_test_token(user_id: str = "test_user") -> str:
    """Generate a test token for development"""
    return create_access_token({"sub": user_id})