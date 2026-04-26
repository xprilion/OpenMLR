"""Celery application configuration for background agent jobs."""

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "openmlr",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["openmlr.tasks.agent_tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after completion for reliability
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Don't prefetch, process one at a time

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_concurrency=4,  # Number of concurrent workers

    # Task routing (optional - can route different tasks to different queues)
    task_routes={
        "openmlr.tasks.agent_tasks.process_agent_message": {"queue": "agent"},
    },

    # Default queue
    task_default_queue="default",
)


def get_celery_app() -> Celery:
    """Get the configured Celery app."""
    return celery_app
