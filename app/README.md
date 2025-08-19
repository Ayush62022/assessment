# Audio Transcription API

This is a FastAPI-based application for audio transcription and speaker diarization, utilizing Whisper for transcription and pyannote.audio for speaker diarization. It supports asynchronous task processing with Celery, PostgreSQL for data persistence, and Redis for rate limiting.

## Prerequisites

- Python 3.8+
- PostgreSQL 13+
- Redis 6+
- FFmpeg (for audio processing)
- CUDA-enabled GPU (optional, for faster processing)
- Hugging Face account with accepted pyannote.audio terms

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd audio-transcription-api
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Ensure you have a `requirements.txt` file with:
   ```
   fastapi==0.95.1
   uvicorn==0.21.1
   sqlalchemy==2.0.9
   asyncpg==0.27.0
   celery==5.2.7
   redis==4.5.4
   whisper==1.1.10
   pyannote.audio==3.1.0
   torch==2.0.0
   librosa==0.9.2
   soundfile==0.12.1
   aiofiles==23.1.0
   python-jwt==4.0.0
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the project root:
   ```bash
   touch .env
   ```
   Add the following variables:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/transcription_db
   REDIS_HOST=localhost
   REDIS_PORT=6379
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   JWT_SECRET_KEY=your-super-secret-key-change-in-production
   WHISPER_MODEL_SIZE=base
   HUGGINGFACE_TOKEN=hf_YourHuggingFaceToken
   ```
   Replace `your_password` and `hf_YourHuggingFaceToken` with your actual PostgreSQL password and Hugging Face token.

5. **Set Up PostgreSQL**
   Create a database named `transcription_db`:
   ```bash
   psql -U postgres -c "CREATE DATABASE transcription_db;"
   ```

6. **Start Redis**
   Ensure Redis is running:
   ```bash
   redis-server
   ```

7. **Run Database Migrations**
   The application automatically creates tables on startup via `init_db()` in `database.py`.

8. **Start the FastAPI Application**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

9. **Start Celery Worker**
   In a separate terminal:
   ```bash
   celery -A celery_app.celery_app worker --loglevel=info
   ```

## Sample Usage

### Get a Test JWT Token
```bash
curl -X GET "http://localhost:8000/auth/token"
```
Response:
```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer",
  "instructions": "Use this token in Authorization header: 'Bearer <token>'"
}
```

### Submit a Transcription Task (File Upload)
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
     -H "Authorization: Bearer <jwt_token>" \
     -F "file=@/path/to/audio.wav"
```
Response:
```json
{
  "task_id": "<task_id>",
  "status": "pending",
  "message": "Transcription task created"
}
```

### Submit a Transcription Task (URL)
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe?url=<audio_url>" \
     -H "Authorization: Bearer <jwt_token>"
```

### Check Task Status
```bash
curl -X GET "http://localhost:8000/api/v1/transcribe/<task_id>" \
     -H "Authorization: Bearer <jwt_token>"
```
Response:
```json
{
  "task_id": "<task_id>",
  "status": "completed",
  "progress": 100,
  "created_at": "2025-08-19T12:00:00.000Z",
  "result": {
    "language": "en",
    "duration_sec": 120.45,
    "transcript": [...],
    "speakers": [...],
    "confidence": 0.85
  }
}
```

### Stream Task Progress
```bash
curl -X GET "http://localhost:8000/api/v1/transcribe/<task_id>/stream" \
     -H "Authorization: Bearer <jwt_token>"
```
Response (Server-Sent Events):
```
data: {"task_id": "<task_id>", "status": "processing", "progress": 20, "timestamp": "2025-08-19T12:00:01Z"}
data: {"task_id": "<task_id>", "status": "completed", "progress": 100, "timestamp": "2025-08-19T12:00:05Z", ...}
```

## Trade-offs

- **Whisper Model Size**: Using `base` model by default balances speed and accuracy. Larger models (e.g., `large-v3`) offer better accuracy but increase processing time and memory usage.
- **Diarization Fallback**: If pyannote.audio fails (e.g., due to missing Hugging Face token), a basic alternating-speaker fallback is used, which is less accurate but ensures functionality.
- **Rate Limiting**: Redis-based rate limiting ensures fair usage but adds dependency on Redis. If Redis is unavailable, rate limiting is disabled to maintain service availability.
- **Asynchronous Processing**: Celery handles long-running transcription tasks, improving API responsiveness but introducing complexity in task monitoring and error handling.
- **Database Choice**: PostgreSQL provides robust data persistence and indexing for efficient querying, but requires proper configuration and maintenance compared to lighter alternatives like SQLite.