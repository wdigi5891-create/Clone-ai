import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.serializers import project_detail, project_summary, steps_out
from core.config import get_settings
from core.db import get_db
from core.security import RateLimiter, get_current_user
from models import Project, User, now
from services import pipeline, url_import
from services.storage import get_storage
from video.frames import extract_frame
from video.probe import VideoError, probe
from workers.tasks import dispatch, run_analysis_task

router = APIRouter(prefix="/api", tags=["projects"])
upload_limiter = RateLimiter(max_calls=30, per_seconds=3600)
RIGHTS_MSG = "Vous devez confirmer détenir les droits ou l'autorisation d'utiliser cette vidéo."
MIME = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm"}


def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Project:
    p = db.get(Project, project_id)
    if p is None or p.user_id != user.id:
        raise HTTPException(404, "Projet introuvable.")
    return p


def _create_project(db: Session, user: User, local: Path, filename: str, name: str,
                    source_type: str, source_url: str | None = None) -> Project:
    """Validation réelle du fichier (ffprobe), stockage, miniature."""
    s = get_settings()
    try:
        info = probe(str(local))
    except VideoError as e:
        raise HTTPException(422, str(e))
    if info.duration > s.max_duration_seconds:
        raise HTTPException(422, f"Vidéo trop longue ({info.duration:.0f}s). Durée maximale : {s.max_duration_seconds}s.")
    ext = local.suffix.lstrip(".").lower()
    clean = re.sub(r"[^\w\-. ]+", "_", Path(filename).name)[:200] or f"video.{ext}"
    project = Project(user_id=user.id, name=(name.strip() or Path(clean).stem)[:255], source_type=source_type,
                      source_url=source_url, original_filename=clean, file_size=local.stat().st_size,
                      duration=info.duration, width=info.width, height=info.height, fps=info.fps,
                      format=info.format, orientation=info.orientation, has_audio=info.has_audio,
                      rights_confirmed_at=now())
    db.add(project)
    db.flush()
    storage = get_storage()
    project.source_key = f"projects/{project.id}/source.{ext}"
    storage.put_file(local, project.source_key, MIME.get(ext))
    thumb = local.parent / "thumb.jpg"
    try:
        extract_frame(str(local), min(1.0, info.duration / 2), str(thumb), max_width=640)
        project.thumbnail_key = f"projects/{project.id}/thumbnail.jpg"
        storage.put_file(thumb, project.thumbnail_key, "image/jpeg")
    except VideoError:
        pass
    project.storage_bytes = project.file_size
    pipeline.init_steps(db, project)
    db.commit()
    return project


@router.post("/projects/upload", status_code=201, dependencies=[Depends(upload_limiter)])
def upload_video(file: UploadFile = File(...), name: str = Form(""), rights_confirmed: bool = Form(False),
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_settings()
    if not rights_confirmed:
        raise HTTPException(400, RIGHTS_MSG)
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in s.allowed_ext_set:
        raise HTTPException(415, "Format non pris en charge. Formats acceptés : MP4, MOV, WEBM.")
    tmp = Path(tempfile.mkdtemp(prefix="upload_", dir=s.temp_dir))
    try:
        local, size, limit = tmp / f"upload.{ext}", 0, s.max_upload_mb * 1024 * 1024
        with open(local, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"Fichier trop volumineux (limite {s.max_upload_mb} Mo).")
                out.write(chunk)
        if size == 0:
            raise HTTPException(422, "Fichier vide.")
        return project_detail(_create_project(db, user, local, file.filename or local.name, name, "upload"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class UrlIn(BaseModel):
    url: str = Field(max_length=2000)
    name: str = ""
    rights_confirmed: bool = False


def _url_error(e: url_import.UrlImportError) -> HTTPException:
    return HTTPException(422, {"message": str(e), "code": e.code, "info": e.info,
                               "suggestion": "Importez le fichier vidéo original (MP4, MOV ou WEBM)."})


@router.post("/projects/check-url")
def check_url(body: UrlIn, user: User = Depends(get_current_user)):
    try:
        return url_import.validate(body.url)
    except url_import.UrlImportError as e:
        raise _url_error(e)


@router.post("/projects/import-url", status_code=201, dependencies=[Depends(upload_limiter)])
def import_url(body: UrlIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.rights_confirmed:
        raise HTTPException(400, RIGHTS_MSG)
    tmp = Path(tempfile.mkdtemp(prefix="url_", dir=get_settings().temp_dir))
    try:
        try:
            local, filename = url_import.download(body.url, str(tmp))
        except url_import.UrlImportError as e:
            raise _url_error(e)
        return project_detail(_create_project(db, user, Path(local), filename, body.name, "url", body.url))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@router.get("/projects")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Project).filter_by(user_id=user.id).order_by(Project.created_at.desc()).all()
    return [project_summary(p) for p in rows]


@router.get("/projects/{project_id}")
def read_project(p: Project = Depends(get_project)):
    return project_detail(p)


@router.get("/projects/{project_id}/progress")
def progress(p: Project = Depends(get_project)):
    return {"status": p.status, "error": p.error, "steps": steps_out(p),
            "scene_count": len(p.scenes), "character_count": len(p.characters)}


class AnalyzeIn(BaseModel):
    split_mode: str = Field(default="smart", pattern="^(smart|fixed)$")
    split_seconds: int = 10


@router.post("/projects/{project_id}/analyze", status_code=202)
def analyze(body: AnalyzeIn, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    if p.status in ("queued", "processing"):
        raise HTTPException(409, "Une analyse est déjà en cours pour ce projet.")
    if body.split_mode == "fixed" and body.split_seconds not in (5, 10, 15, 20, 30):
        raise HTTPException(422, "Durée de séquence invalide : choisissez 5, 10, 15, 20 ou 30 secondes.")
    if not p.source_key:
        raise HTTPException(410, "La vidéo source n'est plus disponible. Réimportez-la.")
    p.split_mode, p.split_seconds, p.status, p.error = body.split_mode, body.split_seconds, "queued", ""
    pipeline.init_steps(db, p, "metadata")
    db.commit()
    dispatch(run_analysis_task, p.id, "metadata")
    return {"status": "queued"}


class RetryIn(BaseModel):
    step: str | None = None


@router.post("/projects/{project_id}/retry", status_code=202)
def retry(body: RetryIn, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    """Relance l'analyse à partir d'une étape (par défaut : la première en échec)."""
    if p.status in ("queued", "processing"):
        raise HTTPException(409, "Une analyse est déjà en cours pour ce projet.")
    step = body.step or next((s.key for s in p.steps if s.status in ("failed", "pending")), None)
    if step not in pipeline.RUNNERS:
        raise HTTPException(422, "Aucune étape à relancer.")
    p.status, p.error = "queued", ""
    pipeline.init_steps(db, p, step)
    db.commit()
    dispatch(run_analysis_task, p.id, step)
    return {"status": "queued", "from_step": step}


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(p: Project = Depends(get_project), db: Session = Depends(get_db)):
    get_storage().delete_prefix(f"projects/{p.id}")
    db.delete(p)
    db.commit()


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Project).filter_by(user_id=user.id)
    count = lambda *st: q.filter(Project.status.in_(st)).count()
    agg = db.query(func.coalesce(func.sum(Project.duration), 0), func.coalesce(func.sum(Project.storage_bytes), 0)) \
        .filter(Project.user_id == user.id)
    analyzed_duration = db.query(func.coalesce(func.sum(Project.duration), 0)) \
        .filter(Project.user_id == user.id, Project.status == "completed").scalar()
    _, storage_bytes = agg.one()
    return {"videos_analyzed": count("completed"), "in_progress": count("queued", "processing"),
            "completed": count("completed"), "failed": count("failed"), "total_projects": q.count(),
            "total_duration_analyzed": float(analyzed_duration), "storage_bytes": int(storage_bytes),
            "recent": [project_summary(p) for p in q.order_by(Project.created_at.desc()).limit(5)]}
