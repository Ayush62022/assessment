# Use official Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    redis-tools \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory
COPY app/ ./app

# Ensure the app directory is in Python path
ENV PYTHONPATH=/app

# Expose port for FastAPI
EXPOSE 8000

# Command to run Celery worker and Uvicorn server
CMD ["sh", "-c", "celery -A app.celery_app.celery_app worker --loglevel=info & uvicorn app.main:app --host 0.0.0.0 --port 8000"]