"""Édition manuelle (scènes, personnages, dialogues) et mode « Recréer cette vidéo »."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai import tasks
from api.projects import get_project
from api.serializers import character_out, dialogue_out, project_detail, scene_out
from core.db import get_db
from models import Character, DialogueLine, Project, Scene
from services import pipeline, prompt_engine
from workers.tasks import dispatch, regenerate_prompts_task

router = APIRouter(prefix="/api/projects/{project_id}", tags=["editing"])
CHARACTER_FIELDS = {"physical_description", "skin_tone_appearance", "hair", "clothing", "accessories",
                    "apparent_age", "facial_expressions", "posture", "distinctive_features"}


def reassemble(p: Project) -> None:
    """Réinjecte personnages, dialogues et durées dans les prompts existants (sans appel IA)."""
    lang = p.prompt_language or "en"
    for s in p.scenes:
        if s.prompt_sections:
            s.prompt_sections, s.prompt_text = prompt_engine.assemble(
                s, len(p.scenes), p.characters, prompt_engine.lines_for(p, s), lang)
    if p.global_prompt:
        p.global_prompt = prompt_engine.build_global_prompt(p)


def _own(db: Session, model, obj_id: str, p: Project):
    obj = db.get(model, obj_id)
    if obj is None or obj.project_id != p.id:
        raise HTTPException(404, "Élément introuvable.")
    return obj


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    visual_style: str | None = None
    mood: str | None = None


@router.patch("")
def patch_project(body: ProjectPatch, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return project_detail(p)


class ScenePatch(BaseModel):
    data: dict[str, str] | None = None
    description: str | None = None
    target_duration: float | None = Field(default=None, gt=0, le=120)
    selected: bool | None = None
    character_indexes: list[int] | None = None
    prompt_sections: dict[str, str] | None = None


@router.patch("/scenes/{scene_id}")
def patch_scene(scene_id: str, body: ScenePatch, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    s = _own(db, Scene, scene_id, p)
    fields = body.model_dump(exclude_unset=True)
    if "data" in fields and body.data is not None:
        s.data = {**(s.data or {}), **{k: v for k, v in body.data.items() if k in tasks.SCENE_FIELDS}}
    if "description" in fields:
        s.description = body.description or ""
    if "target_duration" in fields:
        s.target_duration = body.target_duration
    if "selected" in fields:
        s.selected = bool(body.selected)
    if body.character_indexes is not None:
        valid = {c.index for c in p.characters}
        s.character_indexes = sorted(set(body.character_indexes) & valid)
    if body.prompt_sections is not None:  # retouche manuelle des sections rédigées
        editable = set(tasks.PROMPT_SCHEMA["properties"])
        s.prompt_sections = {**(s.prompt_sections or {}),
                             **{k: v for k, v in body.prompt_sections.items() if k in editable}}
    reassemble(p)
    db.commit()
    return scene_out(s)


class CharacterPatch(BaseModel):
    data: dict[str, str] | None = None
    prompt_descriptor: str | None = None


@router.patch("/characters/{character_id}")
def patch_character(character_id: str, body: CharacterPatch, p: Project = Depends(get_project),
                    db: Session = Depends(get_db)):
    c = _own(db, Character, character_id, p)
    if body.data is not None:
        c.data = {**(c.data or {}), **{k: v for k, v in body.data.items() if k in CHARACTER_FIELDS}}
    if body.prompt_descriptor is not None:
        c.prompt_descriptor = body.prompt_descriptor.strip()
        c.descriptors = {}  # les traductions seront régénérées
    reassemble(p)
    db.commit()
    return character_out(c)


class DialogueIn(BaseModel):
    text: str | None = Field(default=None, max_length=5000)
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)
    character_index: int | None = None
    tone: str | None = None
    emotion: str | None = None
    intensity: str | None = None
    pace: str | None = None


def _apply_dialogue(d: DialogueLine, body: DialogueIn, p: Project) -> None:
    fields = body.model_dump(exclude_unset=True)
    if "character_index" in fields:
        if body.character_index is not None and body.character_index not in {c.index for c in p.characters}:
            raise HTTPException(422, "Personnage inconnu.")
        d.character_index = body.character_index
    for k in ("start", "end", "tone", "emotion", "intensity", "pace"):
        if fields.get(k) is not None:
            setattr(d, k, fields[k])
    if "text" in fields and body.text is not None:
        d.text = body.text.strip()
        d.identifiable = bool(d.text)
    if d.end < d.start:
        raise HTTPException(422, "L'horodatage de fin doit suivre celui de début.")
    mid = (d.start + d.end) / 2
    d.scene_index = next((s.index for s in p.scenes if s.start <= mid < s.end),
                         p.scenes[-1].index if p.scenes else None)
    d.edited = True


@router.patch("/dialogues/{dialogue_id}")
def patch_dialogue(dialogue_id: str, body: DialogueIn, p: Project = Depends(get_project),
                   db: Session = Depends(get_db)):
    d = _own(db, DialogueLine, dialogue_id, p)
    _apply_dialogue(d, body, p)
    reassemble(p)
    db.commit()
    return dialogue_out(d)


@router.post("/dialogues", status_code=201)
def add_dialogue(body: DialogueIn, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    if body.start is None or body.end is None:
        raise HTTPException(422, "Les horodatages de début et de fin sont requis.")
    d = DialogueLine(project_id=p.id, start=body.start, end=body.end, language=p.language)
    _apply_dialogue(d, body, p)
    p.dialogues.append(d)
    reassemble(p)
    db.commit()
    return dialogue_out(d)


@router.delete("/dialogues/{dialogue_id}", status_code=204)
def delete_dialogue(dialogue_id: str, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    d = _own(db, DialogueLine, dialogue_id, p)
    p.dialogues.remove(d)
    db.flush()
    reassemble(p)
    db.commit()


class RegenerateIn(BaseModel):
    scene_ids: list[str] | None = None  # None = toutes les scènes sélectionnées
    language: str | None = Field(default=None, max_length=16)
    style: str | None = None


@router.post("/prompts/regenerate", status_code=202)
def regenerate(body: RegenerateIn, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    """RECRÉER CETTE VIDÉO : régénère les prompts avec un nouveau style / une nouvelle langue."""
    if p.status in ("queued", "processing") or any(s.key == "prompts" and s.status == "running" for s in p.steps):
        raise HTTPException(409, "Une génération est déjà en cours pour ce projet.")
    if not any(s.data for s in p.scenes):
        raise HTTPException(409, "L'analyse des scènes doit être terminée avant de générer des prompts.")
    if body.style is not None:
        if body.style not in prompt_engine.STYLES:
            raise HTTPException(422, "Style visuel inconnu.")
        p.prompt_style = body.style
    if body.language:
        p.prompt_language = body.language.lower()
    ids = body.scene_ids if body.scene_ids is not None else [s.id for s in p.scenes if s.selected]
    ids = [i for i in ids if any(s.id == i for s in p.scenes)]
    if not ids:
        raise HTTPException(422, "Sélectionnez au moins une scène.")
    pipeline.init_steps(db, p, "prompts")
    db.commit()
    dispatch(regenerate_prompts_task, p.id, ids)
    return {"status": "queued", "scenes": len(ids)}


class GlobalIn(BaseModel):
    only_selected: bool = True


@router.post("/prompts/global")
def global_prompt(body: GlobalIn, p: Project = Depends(get_project), db: Session = Depends(get_db)):
    text = prompt_engine.build_global_prompt(p, body.only_selected)
    if not text:
        raise HTTPException(409, "Aucun prompt de scène disponible pour construire le prompt global.")
    p.global_prompt = text
    db.commit()
    return {"global_prompt": text}
