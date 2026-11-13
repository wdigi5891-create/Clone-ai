"""Configuration centralisée, lue depuis l'environnement (.env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    # --- Application
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"
    # Déploiement tout-en-un : l'API relaie les pages vers le serveur Next interne
    frontend_proxy_url: str = ""

    # --- Données
    # Vide = SQLite local (storage/dev.db), pratique en développement
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    # "celery" (production) ou "inline" (thread local, sans Redis)
    task_backend: str = "celery"

    # --- Stockage
    storage_backend: str = "local"  # local | s3
    storage_local_dir: str = str(REPO_DIR / "storage" / "data")
    temp_dir: str = str(REPO_DIR / "storage" / "tmp")
    temp_ttl_hours: int = 6
    # 0 = conserver la vidéo source ; sinon suppression après N heures
    source_retention_hours: int = 0
    signed_url_ttl_seconds: int = 3600
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # --- Limites d'import
    max_upload_mb: int = 500
    max_duration_seconds: int = 600
    max_scenes: int = 60
    allowed_extensions: str = "mp4,mov,webm"
    # Hôtes autorisés pour l'import par lien direct (vide = tout hôte public)
    url_import_allowed_hosts: str = ""

    # --- IA : fournisseurs interchangeables
    vision_provider: str = "anthropic"  # anthropic | openai | gemini
    llm_provider: str = "anthropic"  # anthropic | openai | gemini
    transcription_provider: str = "openai"  # openai | gemini | faster_whisper | none
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_transcription_model: str = ""  # vide = même modèle
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: str = "medium"
    anthropic_refusal_fallbacks: bool = True
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o"
    openai_transcription_model: str = "whisper-1"
    faster_whisper_model: str = "small"
    analysis_language: str = "fr"
    ai_concurrency: int = 3
    vision_max_image_px: int = 1024

    @property
    def effective_database_url(self) -> str:
        return self.database_url or f"sqlite:///{REPO_DIR / 'storage' / 'dev.db'}"

    @property
    def allowed_ext_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    Path(s.storage_local_dir).mkdir(parents=True, exist_ok=True)
    Path(s.temp_dir).mkdir(parents=True, exist_ok=True)
    return s
