# """
# Celery configuration for background tasks
# """

# import os
# from celery import Celery

# # Celery configuration
# CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
# CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# # Create Celery app
# celery_app = Celery(
#     "transcription_worker",
#     broker=CELERY_BROKER_URL,
#     backend=CELERY_RESULT_BACKEND,
#     include=["app.tasks"]
# )

# # Celery configuration
# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
#     task_track_started=True,
#     task_time_limit=30 * 60,  # 30 minutes
#     task_soft_time_limit=25 * 60,  # 25 minutes
#     worker_prefetch_multiplier=1,
#     worker_max_tasks_per_child=1000,
# )


"""
Celery configuration for background tasks
"""

import os
from celery import Celery

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "transcription_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)