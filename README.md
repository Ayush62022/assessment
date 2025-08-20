# AI Services API Suite

This repository contains two FastAPI-based microservices for AI-powered content processing: Audio Transcription with Speaker Diarization and AI-assisted Blog Title & Metadata Generation. Both services are built with production-ready features including authentication, rate limiting, background processing, and comprehensive monitoring.

## 🎯 Services Overview

### 1. Audio Transcription API
A comprehensive audio processing service that converts speech to text with speaker identification and timestamps.

**Key Features:**
- **Audio Processing**: Supports WAV, MP3, FLAC files up to 120 minutes
- **Speaker Diarization**: Identifies and labels different speakers (speaker_00, speaker_01, etc.)
- **Multi-language Support**: Auto-detects primary language with ISO-639-1 codes
- **Real-time Progress**: Server-Sent Events (SSE) for live transcription updates
- **Word-level Timestamps**: Precise timing and confidence scores for each word

**Tech Stack:**
- Whisper large-v3 for transcription
- pyannote.audio for speaker diarization
- PostgreSQL for data persistence
- MinIO for S3-compatible audio storage
- Celery for background processing

### 2. Blog Suggestion API
An intelligent content optimization service that generates SEO-friendly titles, descriptions, and metadata for blog posts.

**Key Features:**
- **Smart Title Generation**: Multiple title suggestions based on content analysis
- **SEO Optimization**: Meta descriptions, slugs, and keyword extraction
- **Content Analysis**: SERP scores and confidence ratings
- **Flexible Input**: Supports both markdown text and .md file uploads
- **Tone Control**: Formal, casual, or clickbait style options

**Tech Stack:**
- Custom BlogSuggestionEngine with NLP analysis
- CSV dataset for title corpus training
- Content similarity matching algorithms

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone <repository-url>
cd <repository-name>
```

2. **Set up environment variables:**
```bash
# Create .env file with the following:
JWT_SECRET_KEY=your-super-secret-key-change-in-production
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/transcription_db
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_SERVER_URL=http://minio:9000
MINIO_BUCKET_NAME=transcriptions
```

3. **Start all services:**
```bash
docker-compose up -d
```

### Local Development Setup

**For Audio Transcription Service:**

1. **Install dependencies:**
```bash
pip install -r requirements-transcription.txt
```

2. **Start external services:**
```bash
# PostgreSQL
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15

# Redis
docker run -d --name redis -p 6379:6379 redis:7

# MinIO
docker run -d --name minio -p 9000:9000 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio/minio server /data
```

3. **Run the services:**
```bash
# FastAPI app
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker (separate terminal)
celery -A app.celery_app.celery_app worker --loglevel=info
```

**For Blog Suggestion Service:**

1. **Install dependencies:**
```bash
pip install -r requirements-blog.txt
```

2. **Ensure dataset is available:**
```bash
# Place your medium_post_titles.csv in the project root
ls medium_post_titles.csv
```

3. **Run the service:**
```bash
uvicorn new_project.main:app --host 0.0.0.0 --port 8001 --reload
```

## 📋 API Documentation

### Authentication

Both services use JWT token authentication with a simple fallback API key for testing.

**Get JWT Token:**
```bash
# Audio Transcription
curl -X GET http://localhost:8000/auth/token

# Blog Suggestions  
curl -X POST http://localhost:8001/api/v1/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

**Alternative API Key:** Use `transcription_api_key_123` for quick testing.

### Audio Transcription Endpoints

#### Create Transcription Task
```bash
curl -X POST http://localhost:8000/api/v1/transcribe \
  -H "Authorization: Bearer <jwt_token>" \
  -F "file=@assets/sample.wav"

# Response
{
  "task_id": "abc-123-def",
  "status": "pending", 
  "message": "Transcription task created successfully"
}
```

#### Stream Progress (SSE)
```bash
curl -X GET http://localhost:8000/api/v1/transcribe/<task_id>/stream \
  -H "Authorization: Bearer <jwt_token>"

# Output: Real-time progress updates ending with full JSON result
```

#### Get Task Status
```bash
curl -X GET http://localhost:8000/api/v1/transcribe/<task_id> \
  -H "Authorization: Bearer <jwt_token>"
```

### Blog Suggestion Endpoints

#### Generate Suggestions (Markdown Text)
```bash
curl -X POST http://localhost:8001/api/v1/blog/suggest \
  -H "Authorization: Bearer <jwt_token>" \
  -F "body_markdown=# My Blog Post\n\nThis is about AI and machine learning..." \
  -F "tone=casual"
```

#### Generate Suggestions (File Upload)
```bash
curl -X POST http://localhost:8001/api/v1/blog/suggest \
  -H "Authorization: Bearer <jwt_token>" \
  -F "file=@my-blog-post.md" \
  -F "tone=formal"
```

#### Sample Response
```json
{
  "titles": [
    "AI Revolution: How Machine Learning is Transforming Industries",
    "The Future of AI: 5 Trends You Need to Know",
    "Machine Learning Explained: A Beginner's Guide"
  ],
  "meta_description": "Discover how artificial intelligence and machine learning are reshaping industries, with practical insights and future predictions.",
  "slug": "ai-machine-learning-industry-transformation",
  "keywords": ["artificial intelligence", "machine learning", "AI trends", "technology"],
  "confidence": 0.89,
  "serp_score": 0.76
}
```

## 🔒 Security & Rate Limiting

- **JWT Authentication**: Tokens expire after 1 hour
- **Rate Limiting**: 30 requests per minute per user (Redis-based)
- **API Key Fallback**: Simple key for development/testing
- **Input Validation**: Comprehensive request validation and sanitization

## 📊 Monitoring & Health Checks

### Health Check Endpoints

**Audio Transcription:**
```bash
curl http://localhost:8000/healthz
```
Checks: PostgreSQL, Redis, MinIO storage

**Blog Suggestions:**
```bash  
curl http://localhost:8001/healthz
```
Checks: Redis, Dataset availability, Engine functionality

### Logging

- **Structured JSON Logging**: Using loguru for consistent log formatting
- **Request/Response Tracking**: Full API interaction logging
- **Error Monitoring**: Detailed error tracking with stack traces

## 📁 Project Structure

```
├── audio-transcription/
│   ├── app/
│   │   ├── celery_app.py          # Celery background tasks
│   │   ├── auth.py               # JWT authentication
│   │   ├── main.py               # FastAPI transcription app
│   │   ├── database.py           # PostgreSQL setup
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── audio_transcription_core.py  # Whisper + pyannote logic
│   │   ├── tasks.py              # Celery transcription tasks
│   │   └── rate_limiter.py       # Redis rate limiting
│   ├── assets/
│   │   └── sample.wav            # Sample audio (Jay Shetty Podcast)
│   └── Dockerfile
├── blog-suggestions/
│   ├── blog_app/
│   │   ├── main.py               # FastAPI blog suggestion app
│   │   └── test2.py              # BlogSuggestionEngine implementation
│   ├── medium_post_titles.csv    # Training dataset
│   └── Dockerfile
├── docker-compose.yml            # Multi-service orchestration
├── requirements-transcription.txt
├── requirements-blog.txt
└── README.md                     # This file
```

## ⚡ Performance & Optimization

### Audio Transcription
- **Processing Speed**: <50% of audio duration (10 min processing for 20 min audio)
- **GPU Acceleration**: Automatic CUDA detection for Whisper
- **Memory Management**: Efficient audio chunk processing
- **Storage**: MinIO presigned URLs for scalable file handling

### Blog Suggestions
- **Response Time**: <2 seconds for typical blog post analysis
- **Content Analysis**: Advanced NLP with similarity matching
- **SEO Scoring**: Real-time SERP potential calculation
- **Memory Efficient**: CSV-based corpus with optimized lookup

## 🐳 Docker Configuration

### Multi-stage Builds
- **Base Image**: python:3.11-slim for minimal footprint
- **Image Size**: <200MB per service
- **Layer Optimization**: Efficient caching and dependency management

### Environment Variables
```bash
# Shared Configuration
JWT_SECRET_KEY=your-secret-key
REDIS_HOST=redis
REDIS_PORT=6379

# Audio Transcription Specific  
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/transcription_db
MINIO_SERVER_URL=http://minio:9000
CELERY_BROKER_URL=redis://redis:6379/0

# Blog Suggestions Specific
DATASET_PATH=medium_post_titles.csv
```

## 🧪 Testing & CI/CD

### Local Testing
```bash
# Audio Transcription Tests
pytest audio-transcription/tests/ --cov=app --cov-report=html

# Blog Suggestions Tests  
pytest blog-suggestions/tests/ --cov=blog_app --cov-report=html
```

### GitHub Actions Pipeline
- **Linting**: ruff for code quality
- **Type Checking**: mypy for static analysis
- **Testing**: pytest with ≥80% coverage requirement
- **Docker**: Automated builds pushed to GitHub Container Registry

## 🔧 Development Notes

### Technology Choices

**Audio Transcription:**
- **FastAPI over Django**: Better async support for I/O-bound operations
- **Celery over Threading**: Production-grade background processing
- **MinIO over Local Storage**: S3-compatible scalability
- **PostgreSQL**: Robust relational data with async support

**Blog Suggestions:**
- **Custom Engine over OpenAI API**: Cost control and offline capability
- **CSV Dataset**: Simple, fast, and easily updateable training data
- **Form Data Support**: Flexible input methods for web integration

### Trade-offs & Considerations

1. **Performance vs Accuracy**: Whisper large-v3 for best quality, accepts longer processing
2. **Complexity vs Features**: Rich feature set requires more dependencies
3. **Storage vs Speed**: MinIO for scalability, local fallback for development
4. **Memory vs Disk**: In-memory caching balanced with persistent storage

## 📖 Sample Assets

### Audio Transcription
- **Sample File**: `assets/sample.wav` (20-minute Jay Shetty Podcast clip)
- **Source**: [YouTube Link](https://www.youtube.com/watch?v=4qykb6jKXdo&t=321s)
- **Expected Output**: See `transcription_result.json` for format example

### Blog Suggestions  
- **Dataset**: `medium_post_titles.csv` with 10K+ Medium article titles
- **Sample Input**: Any markdown blog post content
- **Expected Output**: 3-5 title suggestions with SEO metadata

## 🚀 Deployment

### Production Checklist
- [ ] Update JWT_SECRET_KEY with secure random value
- [ ] Configure Redis clustering for high availability  
- [ ] Set up PostgreSQL with proper backup strategy
- [ ] Configure MinIO with persistent volumes
- [ ] Enable HTTPS with proper TLS certificates
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation (ELK stack recommended)

### Scaling Considerations
- **Horizontal**: Multiple FastAPI instances behind load balancer
- **Celery Workers**: Scale based on transcription queue length
- **Database**: Read replicas for query optimization
- **Storage**: MinIO clustering for high availability

---

## 📧 Support & Contributing

For issues, feature requests, or contributions, please refer to the project's GitHub repository. Both services are actively maintained and welcome community contributions.

**Quick Links:**
- 🐛 [Report Issues](./issues)
- 📝 [Feature Requests](./discussions)  
- 🔧 [Contributing Guide](./CONTRIBUTING.md)
- 📚 [API Documentation](http://localhost:8000/docs) (when running)
