import mimetypes
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse

from ai.tasks import LANG_NAMES
from api.projects import get_project
from core.config import get_settings
from core.security import verify_signature
from models import Project
from services import export, prompt_engine
from services.pipeline import STEPS
from services.storage import LocalStorage, get_storage

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/meta")
def meta():
    """Options de l'interface et état de configuration des fournisseurs IA (sans secret)."""
    s = get_settings()
    configured = {"anthropic": bool(s.anthropic_api_key), "openai": bool(s.openai_api_key),
                  "faster_whisper": True, "none": False, "": False}
    return {
        "styles": [{"key": k, "label": v[0]} for k, v in prompt_engine.STYLES.items()],
        "languages": [{"code": k, "label": v} for k, v in LANG_NAMES.items()],
        "split_seconds": [5, 10, 15, 20, 30],
        "steps": [{"key": k, "label": v} for k, v in STEPS],
        "limits": {"max_upload_mb": s.max_upload_mb, "max_duration_seconds": s.max_duration_seconds,
                   "extensions": sorted(s.allowed_ext_set)},
        "providers": {
            "vision": {"name": s.vision_provider, "configured": configured.get(s.vision_provider, False)},
            "llm": {"name": s.llm_provider, "configured": configured.get(s.llm_provider, False)},
            "transcription": {"name": s.transcription_provider,
                              "configured": configured.get(s.transcription_provider, False)},
        },
    }


@router.get("/files/{key:path}")
def serve_file(key: str, exp: int = Query(...), sig: str = Query(...)):
    """Fichiers du stockage local, accessibles uniquement par URL signée à durée limitée."""
    storage = get_storage()
    if not isinstance(storage, LocalStorage) or not verify_signature(key, exp, sig):
        raise HTTPException(403, "Lien expiré ou invalide.")
    try:
        path = storage.path(key)
    except ValueError:
        raise HTTPException(404, "Fichier introuvable.")
    if not path.is_file():
        raise HTTPException(404, "Fichier introuvable.")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                        headers={"Cache-Control": "private, max-age=3600"})


@router.get("/projects/{project_id}/export/{kind}")
def export_project(kind: str, p: Project = Depends(get_project)):
    if kind not in export.EXPORTS:
        raise HTTPException(404, "Type d'export inconnu.")
    if not p.scenes:
        raise HTTPException(409, "Aucune donnée à exporter : lancez d'abord l'analyse.")
    builder, media = export.EXPORTS[kind]
    content = builder(p)
    if isinstance(content, str):
        content = content.encode("utf-8")
        media += "; charset=utf-8"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", p.name).strip("-")[:60] or "projet"
    return Response(content, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{slug}_{kind}"'})
