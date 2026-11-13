"""Pipeline d'analyse. Chaque étape est persistée (statut, progression réelle,
erreur) et peut être relancée individuellement à partir de l'étape en échec."""
import logging
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

import cv2
from sqlalchemy import delete

from ai import registry, tasks
from ai.base import AIError, ImageInput
from audio.extract import extract_audio
from core.config import get_settings
from core.db import session_scope
from models import AnalysisStep, Character, DialogueLine, Frame, Project, Scene, now
from services import prompt_engine
from services.storage import get_storage
from video import frames as vframes
from video import scenes as vscenes
from video.probe import VideoError, probe

log = logging.getLogger("pipeline")

STEPS = [
    ("import", "Importation"),
    ("metadata", "Analyse générale"),
    ("scenes", "Détection des scènes"),
    ("frames", "Extraction des images"),
    ("transcription", "Transcription audio"),
    ("characters", "Identification des personnages"),
    ("scene_analysis", "Analyse des scènes"),
    ("prompts", "Génération des prompts"),
]
STEP_KEYS = [k for k, _ in STEPS]
MAX_CHARACTER_FRAMES = 24


class StepSkipped(Exception):
    """L'étape ne s'applique pas (ex. pas de piste audio)."""


def init_steps(db, project: Project, from_step: str = "metadata") -> None:
    """Crée les étapes manquantes et remet à zéro celles à (re)lancer."""
    existing = {s.key: s for s in project.steps}
    start = STEP_KEYS.index(from_step)
    for pos, key in enumerate(STEP_KEYS):
        step = existing.get(key)
        if step is None:
            step = AnalysisStep(project_id=project.id, key=key, position=pos)
            project.steps.append(step)
            if key == "import":
                step.status, step.progress, step.finished_at = "done", 1.0, now()
        if pos >= start and key != "import":
            step.status, step.progress, step.message, step.error = "pending", 0, "", ""
            step.started_at = step.finished_at = None


def _set_step(project_id: str, key: str, **fields) -> None:
    with session_scope() as db:
        step = db.query(AnalysisStep).filter_by(project_id=project_id, key=key).one()
        for k, v in fields.items():
            setattr(step, k, v)


def _progress(project_id: str, key: str, done: int, total: int, message: str = "") -> None:
    _set_step(project_id, key, progress=round(done / max(total, 1), 3), message=message)


class Workspace:
    """Répertoire temporaire d'une exécution ; rapatrie les fichiers depuis le stockage."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.dir = Path(tempfile.mkdtemp(prefix=f"{project_id}_", dir=get_settings().temp_dir))
        self._video: str | None = None

    def video(self) -> str:
        if self._video is None:
            with session_scope() as db:
                p = db.get(Project, self.project_id)
                if not p.source_key or not get_storage().exists(p.source_key):
                    raise VideoError("La vidéo source n'est plus disponible (expirée ou supprimée). Réimportez-la.")
                dest = self.dir / f"source{Path(p.source_key).suffix}"
                get_storage().download(p.source_key, dest)
            self._video = str(dest)
        return self._video

    def local(self, key: str) -> str:
        dest = self.dir / key.replace("/", "_")
        if not dest.exists():
            get_storage().download(key, dest)
        return str(dest)

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


# ------------------------------------------------------------------ étapes
def step_metadata(pid: str, ws: Workspace) -> str:
    info = probe(ws.video())
    with session_scope() as db:
        p = db.get(Project, pid)
        p.duration, p.width, p.height, p.fps = info.duration, info.width, info.height, info.fps
        p.format, p.orientation, p.has_audio = info.format, info.orientation, info.has_audio
    return f"{info.width}x{info.height} · {info.fps:g} i/s · {info.duration:.1f}s"


def step_scenes(pid: str, ws: Workspace) -> str:
    s = get_settings()
    with session_scope() as db:
        p = db.get(Project, pid)
        mode, seconds, duration = p.split_mode, p.split_seconds, p.duration
    if mode == "fixed":
        spans = vscenes.normalize(vscenes.fixed_scenes(duration, seconds), duration, s.max_scenes)
    else:
        spans = vscenes.smart_scenes(ws.video(), duration, s.max_scenes)
    with session_scope() as db:
        p = db.get(Project, pid)
        for prefix in ("frames", "characters"):
            get_storage().delete_prefix(f"projects/{pid}/{prefix}")
        db.execute(delete(Frame).where(Frame.project_id == pid))
        db.execute(delete(Scene).where(Scene.project_id == pid))
        db.execute(delete(Character).where(Character.project_id == pid))
        for i, sp in enumerate(spans, 1):
            db.add(Scene(project_id=pid, index=i, start=sp.start, end=sp.end))
    return f"{len(spans)} scène(s) détectée(s)"


def step_frames(pid: str, ws: Workspace) -> str:
    storage = get_storage()
    video = ws.video()
    with session_scope() as db:
        p = db.get(Project, pid)
        fps = p.fps
        db.execute(delete(Frame).where(Frame.project_id == pid))
        scene_rows = [(s.id, s.index, s.start, s.end) for s in p.scenes]
    storage.delete_prefix(f"projects/{pid}/frames")
    count, size = 0, 0
    for n, (sid, idx, start, end) in enumerate(scene_rows, 1):
        extracted = vframes.extract_scene_frames(video, start, end, str(ws.dir / "frames"), f"s{idx:03d}", fps)
        with session_scope() as db:
            for f in extracted:
                key = f"projects/{pid}/frames/{Path(f.path).name}"
                size += storage.put_file(f.path, key, "image/jpeg")
                db.add(Frame(project_id=pid, scene_id=sid, kind=f.kind, timestamp=f.timestamp, key=key,
                             width=f.width, height=f.height, sharpness=f.sharpness,
                             is_representative=f.is_representative))
                count += 1
                if idx == 1 and f.is_representative:
                    db.get(Project, pid).thumbnail_key = key
        _progress(pid, "frames", n, len(scene_rows), f"Scène {n}/{len(scene_rows)}")
    with session_scope() as db:
        p = db.get(Project, pid)
        p.storage_bytes = p.file_size + size
    return f"{count} image(s) extraite(s)"


def step_transcription(pid: str, ws: Workspace) -> str:
    with session_scope() as db:
        p = db.get(Project, pid)
        has_audio = p.has_audio
        scene_rows = [(s.index, s.start, s.end) for s in p.scenes]
        db.execute(delete(DialogueLine).where(DialogueLine.project_id == pid))
    if not has_audio:
        raise StepSkipped("La vidéo ne contient pas de piste audio.")
    transcriber = registry.get_transcriber()
    if transcriber is None:
        raise StepSkipped("Transcription désactivée (TRANSCRIPTION_PROVIDER=none).")
    audio = extract_audio(ws.video(), str(ws.dir / "audio.mp3"))
    _progress(pid, "transcription", 1, 3, "Piste audio extraite, transcription en cours")
    transcript = transcriber.transcribe(audio)
    with session_scope() as db:
        p = db.get(Project, pid)
        p.language = transcript.language
        for seg in transcript.segments:
            mid = (seg.start + seg.end) / 2
            scene_index = next((i for i, a, b in scene_rows if a <= mid < b), scene_rows[-1][0] if scene_rows else None)
            db.add(DialogueLine(project_id=pid, scene_index=scene_index, start=round(seg.start, 2),
                                end=round(seg.end, 2), text=seg.text, language=transcript.language,
                                identifiable=seg.identifiable, confidence=seg.confidence))
    n = len(transcript.segments)
    return f"{n} réplique(s) transcrite(s)" if n else "Aucune parole détectée"


def _crop_reference(src: str, box: dict, dest: str) -> bool:
    img = cv2.imread(src)
    if img is None:
        return False
    h, w = img.shape[:2]
    try:
        x, y, bw, bh = (float(box[k]) for k in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError):
        return False
    if not (0 <= x < 1 and 0 <= y < 1 and bw > 0.02 and bh > 0.02):
        return False
    pad = 0.08  # marge autour du personnage
    x0, y0 = max(0, int((x - bw * pad) * w)), max(0, int((y - bh * pad) * h))
    x1, y1 = min(w, int((x + bw * (1 + pad)) * w)), min(h, int((y + bh * (1 + pad)) * h))
    if x1 - x0 < 24 or y1 - y0 < 24:
        return False
    return bool(cv2.imwrite(dest, img[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 92]))


def step_characters(pid: str, ws: Workspace) -> str:
    vision = registry.get_vision()
    s = get_settings()
    with session_scope() as db:
        p = db.get(Project, pid)
        all_frames = [(f.id, f.scene.index, f.timestamp, f.key, f.is_representative, f.kind) for f in p.frames]
        db.execute(delete(Character).where(Character.project_id == pid))
    get_storage().delete_prefix(f"projects/{pid}/characters")
    if not all_frames:
        raise VideoError("Aucune image extraite : relancez l'étape « Extraction des images ».")
    # Sélection : image représentative de chaque scène, puis début/fin tant que le budget le permet
    chosen = [f for f in all_frames if f[4]]
    for kind in ("start", "end", "middle", "key"):
        extra = [f for f in all_frames if f[5] == kind and f not in chosen]
        if len(chosen) + len(extra) <= MAX_CHARACTER_FRAMES:
            chosen += extra
    if len(chosen) > MAX_CHARACTER_FRAMES:
        step = len(chosen) / MAX_CHARACTER_FRAMES
        chosen = [chosen[int(i * step)] for i in range(MAX_CHARACTER_FRAMES)]
    chosen.sort(key=lambda f: f[2])
    short = {f[0]: f"f{i:02d}" for i, f in enumerate(chosen, 1)}
    by_short = {v: k for k, v in short.items()}
    info = {f[0]: f for f in chosen}
    images = [ImageInput(ws.local(f[3]), f"FRAME {short[f[0]]} — scene {f[1]} — t={f[2]:.2f}s") for f in chosen]
    _progress(pid, "characters", 1, 3, f"{len(images)} images envoyées au modèle de vision")
    result = tasks.identify_characters(vision, images, s.analysis_language)

    storage = get_storage()
    size = 0
    with session_scope() as db:
        p = db.get(Project, pid)
        overall = result.get("overall", {})
        p.summary, p.mood, p.visual_style = (overall.get(k, "") for k in ("summary", "mood", "visual_style"))
        chars = sorted(result.get("characters", []), key=lambda c: c.get("index", 0))
        for n, c in enumerate(chars, 1):
            frame_ids = [by_short[x] for x in c.get("frame_ids", []) if x in by_short]
            ref_id = by_short.get(c.get("reference_frame_id")) or (frame_ids[0] if frame_ids else None)
            ref_key = None
            if ref_id:
                src = ws.local(info[ref_id][3])
                dest = str(ws.dir / f"character_{n}.jpg")
                if not _crop_reference(src, c.get("reference_box") or {}, dest):
                    shutil.copyfile(src, dest)  # boîte invalide : image entière
                ref_key = f"projects/{pid}/characters/character_{n}.jpg"
                size += storage.put_file(dest, ref_key, "image/jpeg")
            data = {k: c.get(k, "") for k in (
                "physical_description", "skin_tone_appearance", "hair", "clothing", "accessories",
                "apparent_age", "facial_expressions", "posture", "distinctive_features")}
            db.add(Character(
                project_id=pid, index=n, label=f"Personnage {n}", data=data,
                prompt_descriptor=c.get("prompt_descriptor", ""),
                scene_indexes=sorted({info[i][1] for i in frame_ids}),
                reference_key=ref_key, reference_frame_id=ref_id))
        p.storage_bytes += size
    return f"{len(chars)} personnage(s) identifié(s)"


def step_scene_analysis(pid: str, ws: Workspace) -> str:
    vision = registry.get_vision()
    s = get_settings()
    with session_scope() as db:
        p = db.get(Project, pid)
        context = " ".join(x for x in (p.summary, p.visual_style) if x)
        chars = [{"index": c.index, "descriptor": c.prompt_descriptor, "ref": c.reference_key,
                  "scenes": c.scene_indexes or []} for c in p.characters]
        jobs = []
        for sc in p.scenes:
            jobs.append({
                "id": sc.id, "index": sc.index, "start": sc.start, "end": sc.end,
                "frames": [(f.key, f.timestamp, f.kind) for f in sc.frames],
                "dialogue": [{"id": d.id, "start": d.start, "end": d.end, "text": d.text,
                              "identifiable": d.identifiable} for d in p.dialogues if d.scene_index == sc.index],
            })
    total = len(jobs)
    char_refs = {c["index"]: ws.local(c["ref"]) for c in chars if c["ref"]}

    def run(job):
        images = [ImageInput(ws.local(k), f"KEYFRAME ({kind}) t={t:.2f}s") for k, t, kind in job["frames"]]
        # Références des personnages susceptibles d'apparaître (ou de tous si peu nombreux)
        for c in chars:
            if c["index"] in char_refs and (len(chars) <= 4 or job["index"] in c["scenes"]):
                images.append(ImageInput(char_refs[c["index"]], f"REFERENCE — Character {c['index']}"))
        return tasks.analyze_scene(
            vision, images, scene_no=job["index"], total=total, start=job["start"], end=job["end"],
            characters=chars, dialogue=job["dialogue"], context=context, language=s.analysis_language)

    valid = {c["index"] for c in chars}
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, s.ai_concurrency)) as pool:
        futures = {pool.submit(run, j): j for j in jobs}
        for fut in as_completed(futures):
            job, result = futures[fut], fut.result()
            with session_scope() as db:
                sc = db.get(Scene, job["id"])
                sc.data = {k: result.get(k, "") for k in tasks.SCENE_FIELDS if k != "cinematic_description"}
                sc.description = result.get("cinematic_description", "")
                sc.character_indexes = sorted({i for i in result.get("characters_present", []) if i in valid})
                ids = {d["id"] for d in job["dialogue"]}
                for note in result.get("dialogue_notes", []):
                    if note.get("line_id") not in ids:
                        continue
                    line = db.get(DialogueLine, note["line_id"])
                    if line.edited:
                        continue
                    sp = note.get("speaker_index")
                    line.character_index = sp if sp in valid else None
                    line.tone, line.emotion = note.get("tone", ""), note.get("emotion", "")
                    line.intensity, line.pace = note.get("intensity", ""), note.get("pace", "")
            done += 1
            _progress(pid, "scene_analysis", done, total, f"Scène {done}/{total} analysée")
    # Les apparitions par scène priment sur la première estimation globale
    with session_scope() as db:
        p = db.get(Project, pid)
        for c in p.characters:
            seen = {sc.index for sc in p.scenes if c.index in (sc.character_indexes or [])}
            if seen:
                c.scene_indexes = sorted(seen)
    return f"{total} scène(s) analysée(s)"


def generate_prompts(pid: str, scene_ids: list[str] | None = None, on_progress=None) -> int:
    """Génère (ou régénère) les prompts des scènes choisies. Utilisé par le pipeline
    et par le mode « Recréer cette vidéo »."""
    llm = registry.get_llm()
    s = get_settings()
    with session_scope() as db:
        p = db.get(Project, pid)
        language, style = p.prompt_language or "en", p.prompt_style or ""
        prompt_engine.ensure_descriptors(llm, p.characters, language)
        targets = [sc.id for sc in p.scenes if scene_ids is None or sc.id in scene_ids]
    done = 0

    def run(scene_id):
        with session_scope() as db:
            sc = db.get(Scene, scene_id)
            p = sc.project
            prev = next((x for x in p.scenes if x.index == sc.index - 1), None)
            return scene_id, prompt_engine.generate_scene_sections(llm, p, sc, prev, language, style)

    with ThreadPoolExecutor(max_workers=max(1, s.ai_concurrency)) as pool:
        for fut in as_completed([pool.submit(run, sid) for sid in targets]):
            scene_id, sections = fut.result()
            with session_scope() as db:
                sc = db.get(Scene, scene_id)
                sc.prompt_sections = sections
                p = sc.project
                sc.prompt_sections, sc.prompt_text = prompt_engine.assemble(
                    sc, len(p.scenes), p.characters, prompt_engine.lines_for(p, sc), language)
            done += 1
            if on_progress:
                on_progress(done, len(targets))
    with session_scope() as db:
        p = db.get(Project, pid)
        p.global_prompt = prompt_engine.build_global_prompt(p)
    return done


def step_prompts(pid: str, ws: Workspace) -> str:
    n = generate_prompts(pid, None, lambda d, t: _progress(pid, "prompts", d, t, f"Prompt {d}/{t}"))
    return f"{n} prompt(s) généré(s)"


RUNNERS = {
    "metadata": step_metadata, "scenes": step_scenes, "frames": step_frames,
    "transcription": step_transcription, "characters": step_characters,
    "scene_analysis": step_scene_analysis, "prompts": step_prompts,
}


def run_analysis(project_id: str, from_step: str = "metadata") -> None:
    with session_scope() as db:
        p = db.get(Project, project_id)
        if p is None:
            return
        p.status, p.error = "processing", ""
    ws = Workspace(project_id)
    failed = False
    try:
        for key in STEP_KEYS[STEP_KEYS.index(from_step):]:
            if key == "import":
                continue
            _set_step(project_id, key, status="running", started_at=now(), error="", progress=0, message="")
            try:
                message = RUNNERS[key](project_id, ws)
                _set_step(project_id, key, status="done", progress=1.0, message=message, finished_at=now())
            except StepSkipped as e:
                _set_step(project_id, key, status="skipped", progress=1.0, message=str(e), finished_at=now())
            except Exception as e:
                if isinstance(e, (AIError, VideoError)):
                    error = str(e)
                else:
                    log.exception("Étape %s en échec pour le projet %s", key, project_id)
                    error = f"Erreur inattendue pendant l'étape ({type(e).__name__}). Relancez l'étape."
                _set_step(project_id, key, status="failed", error=error, finished_at=now())
                with session_scope() as db:
                    p = db.get(Project, project_id)
                    p.status, p.error = "failed", error
                failed = True
                break
        if not failed:
            with session_scope() as db:
                p = db.get(Project, project_id)
                p.status, p.completed_at = "completed", now()
                hours = get_settings().source_retention_hours
                if hours > 0:
                    p.source_expires_at = now() + timedelta(hours=hours)
    finally:
        ws.cleanup()


def run_regeneration(project_id: str, scene_ids: list[str] | None) -> None:
    """Régénération des prompts (mode reconstruction), suivie via l'étape « prompts »."""
    _set_step(project_id, "prompts", status="running", started_at=now(), error="", progress=0,
              message="Régénération des prompts")
    try:
        n = generate_prompts(project_id, scene_ids,
                             lambda d, t: _progress(project_id, "prompts", d, t, f"Prompt {d}/{t}"))
        _set_step(project_id, "prompts", status="done", progress=1.0,
                  message=f"{n} prompt(s) généré(s)", finished_at=now())
    except Exception as e:
        if not isinstance(e, AIError):
            log.exception("Régénération en échec pour le projet %s", project_id)
        error = str(e) if isinstance(e, AIError) else "Erreur inattendue pendant la génération des prompts."
        _set_step(project_id, "prompts", status="failed", error=error, finished_at=now())
