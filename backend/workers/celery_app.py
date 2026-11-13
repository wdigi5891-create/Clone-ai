import sys
from pathlib import Path

# Les processus du pool doivent retrouver les paquets du backend quel que soit le répertoire courant.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from celery import Celery  # noqa: E402

from core.config import get_settings  # noqa: E402

s = get_settings()
celery_app = Celery("ai_video_cloner", broker=s.redis_url, backend=s.redis_url, include=["workers.tasks"])
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={"cleanup-expired": {"task": "workers.tasks.cleanup", "schedule": 1800.0}},
)
