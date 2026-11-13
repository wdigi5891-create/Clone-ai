from models import Character, DialogueLine, Frame, Project, Scene
from services.pipeline import STEPS
from services.storage import get_storage

STEP_LABELS = dict(STEPS)


def _url(key: str | None) -> str | None:
    return get_storage().url(key) if key else None


def frame_out(f: Frame) -> dict:
    return {"id": f.id, "kind": f.kind, "timestamp": f.timestamp, "url": _url(f.key), "width": f.width,
            "height": f.height, "is_representative": f.is_representative,
            "filename": f.key.rsplit("/", 1)[-1]}


def scene_out(s: Scene) -> dict:
    return {"id": s.id, "index": s.index, "start": s.start, "end": s.end,
            "duration": round(s.end - s.start, 2), "target_duration": s.target_duration,
            "selected": s.selected, "data": s.data or {}, "character_indexes": s.character_indexes or [],
            "description": s.description, "prompt_sections": s.prompt_sections or {},
            "prompt_text": s.prompt_text, "frames": [frame_out(f) for f in s.frames]}


def character_out(c: Character) -> dict:
    return {"id": c.id, "index": c.index, "label": c.label, "data": c.data or {},
            "prompt_descriptor": c.prompt_descriptor, "scene_indexes": c.scene_indexes or [],
            "reference_url": _url(c.reference_key)}


def dialogue_out(d: DialogueLine) -> dict:
    return {"id": d.id, "scene_index": d.scene_index, "start": d.start, "end": d.end, "text": d.text,
            "language": d.language, "character_index": d.character_index, "tone": d.tone,
            "emotion": d.emotion, "intensity": d.intensity, "pace": d.pace,
            "identifiable": d.identifiable, "edited": d.edited}


def steps_out(p: Project) -> list[dict]:
    return [{"key": s.key, "label": STEP_LABELS.get(s.key, s.key), "status": s.status,
             "progress": s.progress, "message": s.message, "error": s.error,
             "started_at": s.started_at, "finished_at": s.finished_at} for s in p.steps]


def project_summary(p: Project) -> dict:
    return {"id": p.id, "name": p.name, "status": p.status, "created_at": p.created_at,
            "completed_at": p.completed_at, "duration": p.duration, "width": p.width, "height": p.height,
            "fps": p.fps, "format": p.format, "orientation": p.orientation, "file_size": p.file_size,
            "original_filename": p.original_filename, "source_type": p.source_type,
            "scene_count": len(p.scenes), "character_count": len(p.characters),
            "thumbnail_url": _url(p.thumbnail_key), "storage_bytes": p.storage_bytes, "error": p.error}


def project_detail(p: Project) -> dict:
    return {**project_summary(p), "has_audio": p.has_audio, "split_mode": p.split_mode,
            "split_seconds": p.split_seconds, "language": p.language, "mood": p.mood,
            "visual_style": p.visual_style, "summary": p.summary, "prompt_language": p.prompt_language,
            "prompt_style": p.prompt_style, "global_prompt": p.global_prompt,
            "source_available": bool(p.source_key), "video_url": _url(p.source_key),
            "steps": steps_out(p), "scenes": [scene_out(s) for s in p.scenes],
            "characters": [character_out(c) for c in p.characters],
            "dialogues": [dialogue_out(d) for d in p.dialogues]}
