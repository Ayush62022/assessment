# Audio Transcription API

This is a FastAPI-based application for audio transcription and speaker diarization, utilizing Whisper for transcription and pyannote.audio for speaker diarization. It supports asynchronous task processing with Celery, PostgreSQL for data persistence, and Redis for rate limiting. The application can be run locally using `uvicorn` or in a containerized environment using Docker.

## Prerequisites

- Python 3.8+ (for local setup)
- PostgreSQL 13+
- Redis 6+
- FFmpeg (for audio processing)
- CUDA-enabled GPU (optional, for faster processing)
- Hugging Face account with accepted pyannote.audio terms
- Docker (for containerized deployment)

## Setup Instructions

The application can be set up and run in two ways: **locally** using `uvicorn` and Celery, or **containerized** using Docker. Follow the instructions below for your preferred method.

### Option 1: Local Setup with Uvicorn

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
   python-multipart==0.0.12
   numpy==1.26.4
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
   Run the FastAPI server using `uvicorn`:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

9. **Start Celery Worker**
   In a separate terminal, run the Celery worker for background task processing:
   ```bash
   celery -A celery_app.celery_app worker --loglevel=info
   ```

### Option 2: Containerized Setup with Docker

Run the application using Docker to manage the FastAPI application, PostgreSQL, and Redis in a containerized environment.

#### Prerequisites
- **Docker**: Ensure Docker is installed and running.
- **Project Directory**: Navigate to the project directory (e.g., `D:\me\deep_gram\new_arch` on Windows).
- **Files**: Ensure the following files are present:
  - `Dockerfile`
  - `requirements.txt` (includes `python-multipart==0.0.12`, `numpy==1.26.4`, etc.)
  - `app/celery_app.py` (configured with `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`)
  - `app/` directory with your application code.

#### Steps

1. **Create the Docker Network**
   Create a Docker network named `transcription-network` to allow communication between containers:
   ```bash
   docker network create transcription-network
   ```

2. **Start the PostgreSQL Container**
   Run the PostgreSQL container (`transcription-db`) in the `transcription-network`:
   ```bash
   docker run -d \
     --name transcription-db \
     --network transcription-network \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=Ayush@123 \
     -e POSTGRES_DB=transcription_db \
     -p 5432:5432 \
     postgres:16
   ```
   Verify it’s running:
   ```bash
   docker logs transcription-db
   ```
   Look for "database system is ready to accept connections".

3. **Start the Redis Container**
   Run the Redis container (`jolly_pike`) in the `transcription-network`. If you already have a `jolly_pike` container, ensure it’s connected to the network:
   ```bash
   docker network connect transcription-network jolly_pike
   ```
   If not, start a new Redis container:
   ```bash
   docker run -d \
     --name jolly_pike \
     --network transcription-network \
     -p 6379:6379 \
     redis:7
   ```
   Verify connectivity:
   ```bash
   docker run --rm --network transcription-network redis:7 redis-cli -h jolly_pike -p 6379 ping
   ```
   Expected output: `PONG`.

4. **Create the Storage Directory**
   Create a storage directory in your project directory (e.g., `D:\me\deep_gram\new_arch`) for file uploads:
   ```bash
   mkdir ./storage
   ```
   On Windows:
   ```powershell
   New-Item -ItemType Directory -Path .\storage -Force
   ```

5. **Build the Transcription API Docker Image**
   Build the `transcription-api` image from the project directory:
   ```bash
   docker build --no-cache -t transcription-api .
   ```
   Ensure the build output shows `python-multipart==0.0.12` being installed.

6. **Run the Transcription API Container**
   Run the `transcription-api` container in the `transcription-network`:
   ```bash
   docker run -d \
     --name transcription-api \
     --network transcription-network \
     -p 8000:8000 \
     -e DATABASE_URL="postgresql+asyncpg://postgres:Ayush%40123@transcription-db:5432/transcription_db" \
     -e REDIS_HOST="jolly_pike" \
     -e REDIS_PORT="6379" \
     -e CELERY_BROKER_URL="redis://jolly_pike:6379/0" \
     -e CELERY_RESULT_BACKEND="redis://jolly_pike:6379/0" \
     -e JWT_SECRET_KEY="your-super-secret-key-change-in-production" \
     -e WHISPER_MODEL_SIZE="base" \
     -e HF_TOKEN="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" \
     -v "$(pwd)/storage:/app/storage" \
     transcription-api
   ```

7. **Verify the Containers**
   Check that all containers are running:
   ```bash
   docker ps
   ```
   You should see `transcription-api`, `transcription-db`, and `jolly_pike`.

8. **Check Logs**
   Verify the `transcription-api` container started correctly:
   ```bash
   docker logs transcription-api
   ```
   Look for:
   - Uvicorn logs: `INFO: Started server process [...]` and `INFO: Application startup complete.`
   - Celery logs: `[INFO] celery.worker: Ready to accept tasks` and `transport: redis://jolly_pike:6379/0`.

9. **Test the Application**
   Test the health endpoint to confirm the application is running:
   ```bash
   curl http://localhost:8000/healthz
   ```
   On Windows (PowerShell):
   ```powershell
   Invoke-RestMethod -Uri http://localhost:8000/healthz
   ```
   Expected output:
   ```json
   {
       "status": "healthy",
       "timestamp": "2025-08-19T18:20:00Z",
       "services": {
           "database": "ok",
           "redis": "ok",
           "storage": "ok"
       }
   }
   ```

#### Troubleshooting (Docker)

- **Database Connection Error**:
  - Verify `transcription-db` is running:
    ```bash
    docker logs transcription-db
    ```
    Look for "database system is ready to accept connections".
  - Test connectivity:
    ```bash
    docker run --rm --network transcription-network postgres:16 psql -h transcription-db -U postgres -d transcription_db
    ```
    Enter password `Ayush@123`. You should see a `psql` prompt. Type `\q` to exit.

- **Redis Connection Error**:
  - Verify Celery uses `jolly_pike`:
    ```bash
    docker logs transcription-api
    ```
    Confirm `transport: redis://jolly_pike:6379/0`.
  - Test Redis connectivity:
    ```bash
    docker run --rm --network transcription-network redis:7 redis-cli -h jolly_pike -p 6379 ping
    ```
    Expected output: `PONG`.

- **Port Conflict**:
  - If port 8000 is in use, use a different port:
    ```bash
    docker run -d --name transcription-api --network transcription-network -p 8080:8000 ...
    ```
    Test at `http://localhost:8080/healthz`.

- **Hugging Face Token**:
  - If logs indicate an invalid `HF_TOKEN`, replace it with a valid token for `pyannote/speaker-diarization-3.1` from your Hugging Face account.

#### Stopping the Containers
To stop and remove all containers:
```bash
docker stop transcription-api transcription-db jolly_pike
docker rm transcription-api transcription-db jolly_pike
docker network rm transcription-network
```

#### Alternative: Using Docker Compose
For a simpler setup, use the `docker-compose.yml` file in the project directory:
1. Save the `docker-compose.yml` file (ensure it exists or create it as needed).
2. Stop any existing containers:
   ```bash
   docker stop transcription-api transcription-db jolly_pike
   docker rm transcription-api transcription-db jolly_pike
   ```
3. Run:
   ```bash
   docker-compose up -d
   ```
4. Verify:
   ```bash
   docker logs new_arch-app-1
   docker logs new_arch-db-1
   docker logs new_arch-redis-1
   ```
5. Test:
   ```bash
   curl http://localhost:8000/healthz
   ```
   Or on Windows (PowerShell):
   ```powershell
   Invoke-RestMethod -Uri http://localhost:8000/healthz
   ```

## Sample Usage

The following commands work for both local and Docker setups, assuming the application is running on `http://localhost:8000` (or `http://localhost:8080` if you changed the port).

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
  "created_at": "2025-08-19T18:20:00Z",
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
data: {"task_id": "<task_id>", "status": "processing", "progress": 20, "timestamp": "2025-08-19T18:20:01Z"}
data: {"task_id": "<task_id>", "status": "completed", "progress": 100, "timestamp": "2025-08-19T18:20:05Z", ...}
```

## Trade-offs

- **Framework Choice (FastAPI vs. Django)**: The project was built using FastAPI instead of Django, despite the initial assessment requiring Django, due to greater familiarity with FastAPI. FastAPI offers better support for asynchronous operations, which aligns well with the application's need for non-blocking I/O during audio processing and database interactions. It also provides a simpler setup for REST APIs with automatic OpenAPI documentation. However, Django's robust ecosystem, built-in admin interface, and ORM might have simplified database management and authentication but would have added complexity for async support and potentially slower performance for this specific use case.
- **Whisper Model Size**: Using `base` model by default balances speed and accuracy. Larger models (e.g., `large-v3`) offer better accuracy but increase processing time and memory usage.
- **Diarization Fallback**: If pyannote.audio fails (e.g., due to missing Hugging Face token), a basic alternating-speaker fallback is used, which is less accurate but ensures functionality.
- **Rate Limiting**: Redis-based rate limiting ensures fair usage but adds dependency on Redis. If Redis is unavailable, rate limiting is disabled to maintain service availability.
- **Asynchronous Processing**: Celery handles long-running transcription tasks, improving API responsiveness but introducing complexity in task monitoring and error handling.
- **Database Choice**: PostgreSQL provides robust data persistence and indexing for efficient querying, but requires proper configuration and maintenance compared to lighter alternatives like SQLite.
- **Local vs. Docker Deployment**: Local setup with `uvicorn` is simpler for development and debugging but lacks the consistency and scalability of Docker. Docker ensures reproducible environments and easier deployment but requires familiarity with containerization and increases resource overhead.