"""Nettoyage : fichiers temporaires expirés et vidéos sources arrivées à expiration."""
import shutil
import time
from pathlib import Path

from core.config import get_settings
from core.db import session_scope
from models import Project, now
from services.storage import get_storage


def cleanup_expired() -> dict:
    s = get_settings()
    limit = time.time() - s.temp_ttl_hours * 3600
    removed_tmp = 0
    for entry in Path(s.temp_dir).iterdir():
        try:
            if entry.stat().st_mtime < limit:
                shutil.rmtree(entry, ignore_errors=True) if entry.is_dir() else entry.unlink(missing_ok=True)
                removed_tmp += 1
        except OSError:
            continue
    removed_sources = 0
    with session_scope() as db:
        expired = db.query(Project).filter(
            Project.source_expires_at.isnot(None), Project.source_expires_at < now(),
            Project.source_key.isnot(None)).all()
        for p in expired:
            get_storage().delete(p.source_key)
            p.storage_bytes = max(0, p.storage_bytes - p.file_size)
            p.source_key = None
            removed_sources += 1
    return {"temp": removed_tmp, "sources": removed_sources}
