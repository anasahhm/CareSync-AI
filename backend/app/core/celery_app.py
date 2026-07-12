"""
GestureMed AI — Celery Application
Background task queue for AI report generation and notifications.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "gesturemed",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.report_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.report_tasks.*": {"queue": "ai_reports"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    task_soft_time_limit=120,
    task_time_limit=180,
)
