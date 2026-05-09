"""
core/celery_app.py
──────────────────────────────────────────────────────────────────────────────
Celery Core Application for ILA (Production Hardened)

Upgrades Included:
  - task_acks_late: Prevents data loss if a worker crashes mid-execution.
  - worker_max_tasks_per_child: Prevents spaCy/NLP memory leaks.
  - Timeouts: Prevents rogue Regex operations from freezing the worker forever.
"""

import os
from celery import Celery

REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND_URL = os.getenv("REDIS_BACKEND_URL", "redis://localhost:6379/1")

celery_app = Celery(
    "ila_worker",
    broker=REDIS_BROKER_URL,
    backend=REDIS_BACKEND_URL
)

celery_app.conf.update(
    # ──────────────────────────────────────────────────────────
    # 1. CORE SERIALIZATION & TIMEZONE
    # ──────────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # ──────────────────────────────────────────────────────────
    # 2. FAULT TOLERANCE & DATA SAFETY (CRITICAL)
    # ──────────────────────────────────────────────────────────
    # Default Celery acknowledges tasks BEFORE execution. If the server crashes, 
    # the task is lost. 'True' forces acknowledgment AFTER successful completion.
    task_acks_late=True,
    
    # If a worker process is killed unexpectedly, the task goes back to the queue.
    task_reject_on_worker_lost=True,
    
    # ──────────────────────────────────────────────────────────
    # 3. PERFORMANCE & MEMORY MANAGEMENT
    # ──────────────────────────────────────────────────────────
    # NLP libraries (like spaCy) have notoriously bad memory leaks over time.
    # This setting kills and restarts the background worker after every 100 tasks,
    # flushing the RAM and keeping the server healthy.
    worker_max_tasks_per_child=100,
    
    # Ensures a worker only grabs one NLP task at a time (prevents resource hogging)
    worker_prefetch_multiplier=1,

    # ──────────────────────────────────────────────────────────
    # 4. TIMEOUTS (Preventing 'Zombie' Workers)
    # ──────────────────────────────────────────────────────────
    # If a custom Regex gets stuck in an infinite loop (ReDoS attack), 
    # kill the task after 60 seconds to free up the worker for other alerts.
    task_soft_time_limit=60,
    task_time_limit=65,

    # ──────────────────────────────────────────────────────────
    # 5. TASK ROUTING
    # ──────────────────────────────────────────────────────────
    broker_connection_retry_on_startup=True,
    imports=[
        "app.tasks.enrich",
        "app.tasks.neo4j_sync",
    ]
)