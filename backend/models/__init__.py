"""Modèles SQLAlchemy."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base


def _id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    # uploaded | queued | processing | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="uploaded", index=True)
    source_type: Mapped[str] = mapped_column(String(10), default="upload")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    format: Mapped[str] = mapped_column(String(64), default="")
    duration: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0)
    orientation: Mapped[str] = mapped_column(String(20), default="")
    has_audio: Mapped[bool] = mapped_column(Boolean, default=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    split_mode: Mapped[str] = mapped_column(String(10), default="smart")  # smart | fixed
    split_seconds: Mapped[int] = mapped_column(Integer, default=10)
    language: Mapped[str] = mapped_column(String(32), default="")
    mood: Mapped[str] = mapped_column(Text, default="")
    visual_style: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    prompt_language: Mapped[str] = mapped_column(String(32), default="en")
    prompt_style: Mapped[str] = mapped_column(String(64), default="")
    global_prompt: Mapped[str] = mapped_column(Text, default="")
    storage_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    rights_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="projects")
    steps: Mapped[list["AnalysisStep"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="AnalysisStep.position")
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Scene.index")
    frames: Mapped[list["Frame"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Frame.timestamp")
    characters: Mapped[list["Character"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Character.index")
    dialogues: Mapped[list["DialogueLine"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="DialogueLine.start")


class AnalysisStep(Base):
    __tablename__ = "analysis_steps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    # pending | running | done | failed | skipped
    status: Mapped[str] = mapped_column(String(12), default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project: Mapped[Project] = relationship(back_populates="steps")


class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    # Durée cible choisie par l'utilisateur pour la reconstruction (None = durée d'origine)
    target_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # champs d'analyse
    character_indexes: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt_sections: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    project: Mapped[Project] = relationship(back_populates="scenes")
    frames: Mapped[list["Frame"]] = relationship(back_populates="scene", order_by="Frame.timestamp")


class Frame(Base):
    __tablename__ = "frames"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # start | middle | end | key
    timestamp: Mapped[float] = mapped_column(Float)
    key: Mapped[str] = mapped_column(String(512))
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    sharpness: Mapped[float] = mapped_column(Float, default=0)
    is_representative: Mapped[bool] = mapped_column(Boolean, default=False)
    project: Mapped[Project] = relationship(back_populates="frames")
    scene: Mapped[Scene] = relationship(back_populates="frames")


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # fiche descriptive
    # Bloc canonique réutilisé tel quel dans chaque prompt (cohérence)
    prompt_descriptor: Mapped[str] = mapped_column(Text, default="")
    descriptors: Mapped[dict] = mapped_column(JSON, default=dict)  # {langue: texte}
    scene_indexes: Mapped[list] = mapped_column(JSON, default=list)
    reference_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reference_frame_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    project: Mapped[Project] = relationship(back_populates="characters")


class DialogueLine(Base):
    __tablename__ = "dialogue_lines"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(32), default="")
    character_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tone: Mapped[str] = mapped_column(String(255), default="")
    emotion: Mapped[str] = mapped_column(String(255), default="")
    intensity: Mapped[str] = mapped_column(String(255), default="")
    pace: Mapped[str] = mapped_column(String(255), default="")
    identifiable: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    project: Mapped[Project] = relationship(back_populates="dialogues")
