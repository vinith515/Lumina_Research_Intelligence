"""Celery worker configuration for ResearchMind."""

import logging
from celery import Celery
from researchmind.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "researchmind",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

# Autodiscover tasks in researchmind.tasks
celery_app.autodiscover_tasks(["researchmind.tasks"])
