import os

from celery import Celery

broker_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
result_backend = broker_url

celery_app = Celery(
    "wow_meta",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
