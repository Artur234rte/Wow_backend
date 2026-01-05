from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "wow_meta",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-dps-meta": {
            "task": "app.workers.tasks.refresh_dps_meta",
            "schedule": settings.aggregation_schedule_hours * 60 * 60,
        }
    },
)
