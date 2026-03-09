from celery import Celery

from app.config import settings

celery_app = Celery(
    "transcription",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Process one task at a time (Whisper is heavyweight)
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app"])
