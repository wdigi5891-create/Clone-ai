"""Tâches asynchrones. Worker : celery -A workers.celery_app worker -B --loglevel=info"""
import threading

from core.config import get_settings
from workers.celery_app import celery_app


@celery_app.task(name="workers.tasks.run_analysis")
def run_analysis_task(project_id: str, from_step: str = "metadata"):
    try:
        from services.pipeline import run_analysis
        run_analysis(project_id, from_step)
    except Exception:
        _mark_failed(project_id)
        raise


@celery_app.task(name="workers.tasks.regenerate_prompts")
def regenerate_prompts_task(project_id: str, scene_ids: list[str] | None):
    from services.pipeline import run_regeneration
    run_regeneration(project_id, scene_ids)


@celery_app.task(name="workers.tasks.cleanup")
def cleanup():
    from services.cleanup import cleanup_expired
    return cleanup_expired()


def _mark_failed(project_id: str) -> None:
    """Filet de sécurité : un projet ne doit jamais rester bloqué « en cours »."""
    from core.db import session_scope
    from models import Project
    with session_scope() as db:
        p = db.get(Project, project_id)
        if p is not None and p.status in ("queued", "processing"):
            p.status = "failed"
            p.error = "Le traitement s'est interrompu de façon inattendue. Relancez l'analyse."


def dispatch(task, *args) -> None:
    """Celery en production ; thread local (inline) ou appel direct (sync, tests) sinon."""
    backend = get_settings().task_backend
    if backend == "celery":
        task.delay(*args)
    elif backend == "sync":
        task.run(*args)
    else:
        threading.Thread(target=task.run, args=args, daemon=True).start()
