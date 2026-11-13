"""AI VIDEO CLONER — API FastAPI. Lancement : uvicorn main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import auth, editing, misc, projects
from core.config import get_settings
from core.db import Base, engine

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env != "production" and settings.secret_key == "change-me-in-production":
        logging.warning("SECRET_KEY par défaut : à changer avant tout déploiement.")
    if settings.app_env == "production" and settings.secret_key == "change-me-in-production":
        raise RuntimeError("SECRET_KEY doit être défini en production.")
    if settings.effective_database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)  # dev sans migrations ; PostgreSQL : alembic upgrade head
    from services.cleanup import cleanup_expired
    try:
        cleanup_expired()
    except Exception:
        logging.exception("Nettoyage initial impossible")
    yield


app = FastAPI(title="AI Video Cloner API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    """Format d'erreur uniforme : {"message": "...", ...}."""
    body = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)


for r in (auth.router, projects.router, editing.router, misc.router):
    app.include_router(r)
