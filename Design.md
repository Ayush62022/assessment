# AI Microservices Suite

This repository contains two FastAPI-based microservices designed for AI-powered content processing:

1. **Audio Transcription API** - Advanced speech-to-text with speaker diarization
2. **Blog Suggestion API** - AI-assisted title and metadata generation for blog posts

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Audio Transcription API](#audio-transcription-api)
- [Blog Suggestion API](#blog-suggestion-api)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🚀 Project Overview

### Audio Transcription API

A robust microservice for converting audio content to text with advanced features:
- **High-accuracy transcription** using Whisper large-v3
- **Speaker diarization** with pyannote.audio (>90% F1 score)
- **Multilingual support** with automatic language detection
- **Real-time progress streaming** via Server-Sent Events (SSE)
- **Scalable architecture** designed for 100x workload handling

### Blog Suggestion API

An intelligent content optimization service for bloggers and content creators:
- **AI-powered title generation** with multiple suggestions
- **SEO metadata creation** (descriptions, keywords, slugs)
- **Content analysis** with confidence scoring
- **Flexible input methods** (markdown text or file upload)
- **Customizable tone** (formal, casual, clickbait)

## 🎙️ Audio Transcription API

### Features

- **Advanced Models**:
  - Whisper large-v3 for speech-to-text
  - pyannote.audio for speaker diarization
  - Word-level timestamps and confidence scores

- **Scalability**:
  - Celery-based task processing
  - Redis for caching and rate limiting
  - PostgreSQL for data persistence
  - MinIO for audio storage

- **Performance**:
  - Optimized for 1 vCPU / 4 GB machines
  - Transcribes 20-minute podcasts in <10 minutes
  - Handles 100x concurrent workloads

### Tech Stack

```
FastAPI + Celery + Redis + PostgreSQL + MinIO
Whisper large-v3 + pyannote.audio
Docker + Kubernetes (production)
```

### Key Endpoints

```
POST /api/v1/transcribe          # Submit audio for transcription
GET  /api/v1/transcribe/{id}     # Get transcription results
GET  /api/v1/transcribe/{id}/stream # Real-time progress (SSE)
GET  /healthz                    # Health check
```

### Audio Processing Pipeline

1. **Upload**: Audio files via multipart/form-data or URL
2. **Validation**: File format (.wav, .mp3, .flac) and size (<500MB)
3. **Storage**: Secure storage in MinIO with presigned URLs
4. **Processing**: 
   - Whisper large-v3 for transcription
   - pyannote.audio for speaker identification
   - Word-level alignment and confidence scoring
5. **Results**: JSON output with timestamps, speakers, and metadata

### Rate Limiting & Security

- **Rate Limits**: 30 requests/minute per user
- **Authentication**: JWT tokens or API keys
- **Error Handling**: Comprehensive error responses with retry mechanisms
- **Monitoring**: Structured logging with Loguru

## 📝 Blog Suggestion API

### Features

- **Title Generation**: Multiple AI-generated title suggestions
- **SEO Optimization**: Meta descriptions, keywords, and URL slugs
- **Content Analysis**: Confidence scores and SERP optimization ratings
- **Flexible Input**: Accept markdown text or .md file uploads
- **Tone Customization**: Formal, casual, or clickbait styles

### Tech Stack

```
FastAPI + Redis + Custom ML Engine
JWT Authentication + Rate Limiting
Pydantic for data validation
```

### Key Endpoints

```
POST /api/v1/token               # Generate JWT token
POST /api/v1/blog/suggest        # Get blog suggestions
GET  /healthz                    # Health check
```

### Input Methods

**Option 1: JSON Body**
```json
{
  "body_markdown": "# Your Blog Content\n\nYour blog post content here..."
}
```

**Option 2: Form Data**
```
body_markdown: "# Your Blog Content..."
tone: "casual"
```

**Option 3: File Upload**
```
file: blog-post.md
tone: "formal"
```

### Response Format

```json
{
  "titles": [
    "5 Ways to Improve Your Productivity",
    "The Ultimate Guide to Getting Things Done",
    "Boost Your Efficiency: Expert Tips"
  ],
  "meta_description": "Discover proven strategies to enhance your productivity and achieve better work-life balance with these actionable tips.",
  "slug": "improve-productivity-guide",
  "keywords": ["productivity", "efficiency", "time management", "work-life balance"],
  "confidence": 0.87,
  "serp_score": 0.73
}
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Redis server
- PostgreSQL (for Audio API)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-microservices-suite
```

2. **Environment Setup**
```bash
# Create environment file
cp .env.example .env

# Edit with your configurations
JWT_SECRET_KEY=your-secret-key
REDIS_HOST=localhost
REDIS_PORT=6379
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Start Services**

**For Audio Transcription API:**
```bash
# Start infrastructure
docker-compose up -d redis postgresql minio

# Start Celery worker
celery -A audio_transcription_core worker --loglevel=info

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

**For Blog Suggestion API:**
```bash
# Start Redis
docker-compose up -d redis

# Start FastAPI server
uvicorn blog_suggestion_main:app --reload --port 8001
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Scale workers for high load
docker-compose up --scale audio-worker=3 --scale blog-api=2
```

## 📚 API Documentation

### Authentication

Both APIs use JWT token authentication:

```bash
# Generate token
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "your-user-id"}'

# Use token in subsequent requests
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "Authorization: Bearer your-jwt-token" \
  -F "audio=@podcast.mp3"
```

### Audio Transcription Examples

**Submit Audio File:**
```bash
curl -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@meeting.wav" \
  -F "language=en"
```

**Check Progress:**
```bash
curl "http://localhost:8000/api/v1/transcribe/task-123" \
  -H "Authorization: Bearer $TOKEN"
```

**Stream Progress (SSE):**
```bash
curl -N "http://localhost:8000/api/v1/transcribe/task-123/stream" \
  -H "Authorization: Bearer $TOKEN"
```

### Blog Suggestions Examples

**Text Input:**
```bash
curl -X POST "http://localhost:8001/api/v1/blog/suggest" \
  -H "Authorization: Bearer $TOKEN" \
  -F "body_markdown=# How to Code Better\n\nHere are some tips..." \
  -F "tone=casual"
```

**File Upload:**
```bash
curl -X POST "http://localhost:8001/api/v1/blog/suggest" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@blog-post.md" \
  -F "tone=formal"
```

## 🏗️ Architecture

### Audio Transcription Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI   │───▶│    Redis    │───▶│   Celery    │
│   Server    │    │   Broker    │    │  Workers    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                      │
       ▼                                      ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PostgreSQL  │    │    MinIO    │    │  Whisper +  │
│  Database   │    │   Storage   │    │  pyannote   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Blog Suggestion Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FastAPI   │───▶│    Redis    │    │ BlogEngine  │
│   Server    │    │Rate Limiter │◄───│   + ML      │
└─────────────┘    └─────────────┘    └─────────────┘
       │
       ▼
┌─────────────┐
│  Dataset    │
│   CSV/DB    │
└─────────────┘
```

### Scaling Strategy

**100x Workload Scaling:**

1. **Horizontal Scaling**:
   - Multiple Celery workers across Kubernetes cluster
   - Load balancer (Nginx) for API requests
   - Auto-scaling based on queue length

2. **Database Optimization**:
   - PostgreSQL read replicas
   - Connection pooling with asyncpg
   - Optimized indexes on frequently queried fields

3. **Storage & Caching**:
   - MinIO distributed setup for high throughput
   - Redis cluster for rate limiting and caching
   - CDN for static content delivery

4. **Model Optimization**:
   - GPU-accelerated Whisper inference
   - Batch processing for multiple requests
   - Model quantization (int8) for CPU fallback

## 🐳 Deployment

### Production Docker Compose

```yaml
version: '3.8'

services:
  audio-api:
    build: ./audio-transcription
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/audio_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - minio

  blog-api:
    build: ./blog-suggestions
    ports:
      - "8001:8001"
    environment:
      - REDIS_HOST=redis
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - redis

  celery-worker:
    build: ./audio-transcription
    command: celery -A audio_transcription_core worker --loglevel=info
    depends_on:
      - redis
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=audio_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
 

### Monitoring & Logging

**Health Check Endpoints:**
- Audio API: `GET /healthz` - Checks PostgreSQL, Redis, MinIO
- Blog API: `GET /healthz` - Checks Redis, dataset, ML engine

**Logging:**
- Structured JSON logs with Loguru
- Request/response logging with correlation IDs
- Error tracking with stack traces
- Performance metrics for transcription times

**Metrics to Monitor:**
- Request rate and response times
- Queue length and processing time
- Error rates and retry attempts
- Resource utilization (CPU, Memory, Disk)
- Model inference times

## 🔧 Configuration

### Environment Variables

**Audio Transcription API:**
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/audio_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=audio_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0

# Storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
AUDIO_BUCKET_NAME=audio-files

# Authentication
JWT_SECRET_KEY=your-super-secret-key
API_KEY_HEADER=X-API-Key

# Processing
MAX_AUDIO_SIZE_MB=500
MAX_TRANSCRIPTION_LENGTH_MINUTES=120
WHISPER_MODEL=large-v3
```

**Blog Suggestion API:**
```env
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Authentication
JWT_SECRET_KEY=your-super-secret-key
TOKEN_EXPIRE_SECONDS=3600

# ML Engine
DATASET_PATH=medium_post_titles.csv
MODEL_CONFIDENCE_THRESHOLD=0.5
MAX_TITLE_SUGGESTIONS=5
```

### Rate Limiting

Both APIs implement Redis-based rate limiting:
- **Default**: 30 requests per minute per user
- **Sliding window** implementation
- **Graceful degradation** when Redis is unavailable
- **Custom limits** configurable per endpoint

## 🧪 Testing

### Unit Tests

```bash
# Audio Transcription API tests
pytest tests/audio/ -v

# Blog Suggestion API tests
pytest tests/blog/ -v

# Integration tests
pytest tests/integration/ -v
```

### API Testing with cURL

**Audio Transcription Flow:**
```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}' | jq -r .access_token)

# 2. Submit audio
TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/transcribe" \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@test.wav" | jq -r .task_id)

# 3. Check status
curl "http://localhost:8000/api/v1/transcribe/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Blog Suggestion Flow:**
```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://localhost:8001/api/v1/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "blogger1"}' | jq -r .access_token)

# 2. Get suggestions
curl -X POST "http://localhost:8001/api/v1/blog/suggest" \
  -H "Authorization: Bearer $TOKEN" \
  -F "body_markdown=# My Blog Post\n\nThis is about productivity..." \
  -F "tone=casual"
```

### Load Testing

```bash
# Install artillery
npm install -g artillery

# Load test audio API
artillery run tests/load/audio-api.yml

# Load test blog API
artillery run tests/load/blog-api.yml
```

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```
4. **Run pre-commit hooks**
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```
5. **Write tests** for new features
6. **Update documentation** as needed
7. **Submit a pull request**

### Code Style

- **Black** for code formatting
- **isort** for import sorting  
- **flake8** for linting
- **mypy** for type checking
- **pytest** for testing

### Project Structure

```
├── audio-transcription/
│   ├── main.py                 # FastAPI app
│   ├── audio_transcription_core.py # Core processing
│   ├── database.py            # Database models
│   ├── auth.py                # Authentication
│   └── tests/
├── blog-suggestions/
│   ├── blog_suggestion_main.py # FastAPI app
│   ├── test2.py               # ML engine
│   ├── medium_post_titles.csv # Training data
│   └── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](../../issues)
- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Contact**: [Your Contact Information]

## 🎯 Roadmap

### Audio Transcription API
- [ ] Multi-language parallel processing
- [ ] Real-time streaming transcription
- [ ] Advanced speaker identification
- [ ] Custom vocabulary support
- [ ] Noise reduction preprocessing

### Blog Suggestion API  
- [ ] A/B testing for title effectiveness
- [ ] Social media optimization
- [ ] Competitor analysis integration
- [ ] Image suggestion for blog posts
- [ ] Content readability scoring

### Infrastructure
- [ ] Horizontal pod autoscaling (HPA)
- [ ] Advanced monitoring with Prometheus/Grafana
- [ ] Multi-region deployment
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Security scanning and vulnerability management

---


**Built with ❤️ for content creators and developers**
