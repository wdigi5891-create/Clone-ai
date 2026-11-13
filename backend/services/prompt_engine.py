"""PROMPT ENGINE : assemble les prompts en 13 sections.

Les sections rédactionnelles viennent du modèle de langage ; les blocs
CHARACTER DESCRIPTION, DIALOGUE et DURATION sont injectés par le code à partir
des fiches et de la transcription, pour garantir cohérence et fidélité.
"""
from ai import tasks
from ai.base import JSONModel
from models import Character, DialogueLine, Project, Scene

STYLES = {
    "": ("Fidèle à la vidéo source", ""),
    "cinematic_realism": ("Réalisme cinématographique", "Photorealistic cinematic live-action look, natural skin texture, shallow depth of field, anamorphic lens character, filmic colour grade, 4K detail."),
    "semi_realistic_3d": ("3D semi-réaliste", "Semi-realistic 3D render, slightly stylised proportions with realistic materials, subsurface skin scattering, physically based lighting, high-end game cinematic quality."),
    "3d_animation": ("Animation 3D", "Stylised 3D animated feature film look, expressive characters, appealing shapes, soft global illumination, rich saturated palette."),
    "nollywood": ("Style Nollywood", "Contemporary Nollywood drama aesthetic: vivid warm colour palette, expressive performances, naturalistic West African settings and wardrobe, clean digital cinematography."),
    "documentary": ("Documentaire", "Observational documentary style, natural available light, handheld or shoulder-mounted camera, authentic unpolished realism."),
    "commercial": ("Publicité professionnelle", "High-end commercial look, polished studio-grade lighting, crisp detail, premium colour grade, smooth controlled camera moves."),
    "cinematic_drama": ("Drame cinématographique", "Cinematic drama, moody contrasty lighting, restrained desaturated palette, slow deliberate camera, emotional intimacy."),
    "horror": ("Horreur", "Horror film atmosphere, low-key lighting, deep shadows, cold desaturated tones, unsettling framing and slow creeping camera."),
    "comedy": ("Comédie", "Bright comedy look, high-key even lighting, warm lively colours, clear wide framings that favour physical performance and timing."),
}

SECTIONS = [
    ("scene_description", "SCENE DESCRIPTION"), ("character_description", "CHARACTER DESCRIPTION"),
    ("environment", "ENVIRONMENT"), ("action_and_movement", "ACTION AND MOVEMENT"),
    ("camera_direction", "CAMERA DIRECTION"), ("lighting", "LIGHTING"),
    ("facial_expressions", "FACIAL EXPRESSIONS"), ("dialogue", "DIALOGUE"),
    ("voice_direction", "VOICE DIRECTION"), ("sound_design", "SOUND DESIGN"),
    ("visual_style", "VISUAL STYLE"), ("duration", "DURATION"), ("continuity", "CONTINUITY"),
]

NOTICE = ("Reconstruction prompt derived from an AI analysis of the finished video's picture and "
          "sound. It is not the original prompt of the video.")


def ts(t: float) -> str:
    m, s = divmod(max(t, 0), 60)
    return f"{int(m):02d}:{s:04.1f}" if s % 1 else f"{int(m):02d}:{int(s):02d}"


def scene_duration(scene: Scene) -> float:
    return scene.target_duration or round(scene.end - scene.start, 2)


def descriptor_for(c: Character, language: str) -> str:
    if language != "en" and (c.descriptors or {}).get(language):
        return c.descriptors[language]
    return c.prompt_descriptor


def speaker_name(line: DialogueLine) -> str:
    return f"Character {line.character_index}" if line.character_index else "Unattributed speaker"


def character_block(scene: Scene, characters: list[Character], language: str) -> str:
    present = [c for c in characters if c.index in (scene.character_indexes or [])]
    if not present:
        return "No identified character in this scene."
    return "\n".join(f"Character {c.index}: {descriptor_for(c, language)}" for c in present)


def dialogue_block(lines: list[DialogueLine]) -> str:
    if not lines:
        return "No identifiable dialogue in this scene."
    out = []
    for l in lines:
        if l.identifiable and l.text.strip():
            out.append(f"[{ts(l.start)}–{ts(l.end)}] {speaker_name(l)}: \"{l.text.strip()}\"")
        else:
            out.append(f"[{ts(l.start)}–{ts(l.end)}] Unintelligible speech in the source — do not invent words.")
    return "\n".join(out)


def duration_block(scene: Scene) -> str:
    d = scene_duration(scene)
    return f"{d:g} seconds (source segment {ts(scene.start)}–{ts(scene.end)})."


def assemble(scene: Scene, total: int, characters: list[Character], lines: list[DialogueLine],
             language: str) -> tuple[dict, str]:
    """Reconstruit les sections injectées et le texte final du prompt."""
    sections = dict(scene.prompt_sections or {})
    sections["character_description"] = character_block(scene, characters, language)
    sections["dialogue"] = dialogue_block(lines)
    sections["duration"] = duration_block(scene)
    parts = [f"SCENE {scene.index:02d} / {total:02d}"]
    for i, (key, title) in enumerate(SECTIONS, 1):
        parts.append(f"{i}. {title}\n{(sections.get(key) or '').strip() or '—'}")
    return sections, "\n\n".join(parts)


def lines_for(project: Project, scene: Scene) -> list[DialogueLine]:
    return [l for l in project.dialogues if l.scene_index == scene.index]


def generate_scene_sections(llm: JSONModel, project: Project, scene: Scene, prev: Scene | None,
                            language: str, style: str) -> dict:
    chars = [{"index": c.index, "descriptor": c.prompt_descriptor}
             for c in project.characters if c.index in (scene.character_indexes or [])]
    dialogue = [{"start": l.start, "end": l.end, "text": l.text, "identifiable": l.identifiable,
                 "speaker": speaker_name(l), "tone": l.tone, "emotion": l.emotion,
                 "intensity": l.intensity, "pace": l.pace} for l in lines_for(project, scene)]
    previous = ""
    if prev is not None:
        d = prev.data or {}
        previous = (f"Scene {prev.index}: location: {d.get('location', '?')}; lighting: {d.get('lighting', '?')}; "
                    f"characters: {prev.character_indexes or 'none'}; ends with: {d.get('actions', '?')}")
    analysis = dict(scene.data or {})
    if scene.description:
        analysis["cinematic_description"] = scene.description
    return tasks.write_scene_prompt(
        llm, scene_no=scene.index, total=len(project.scenes), duration=scene_duration(scene),
        analysis=analysis, characters=chars, dialogue=dialogue, previous=previous,
        video_style=project.visual_style, style_directive=STYLES.get(style, ("", ""))[1],
        spoken_language=project.language, language=language)


def ensure_descriptors(llm: JSONModel, characters: list[Character], language: str) -> None:
    """Traduit (une seule fois par langue) les blocs personnages réutilisés dans chaque prompt."""
    if language == "en":
        return
    missing = [c for c in characters if not (c.descriptors or {}).get(language) and c.prompt_descriptor]
    if not missing:
        return
    translated = tasks.translate_descriptors(
        llm, [{"index": c.index, "descriptor": c.prompt_descriptor} for c in missing], language)
    for c in missing:
        if translated.get(c.index):
            c.descriptors = {**(c.descriptors or {}), language: translated[c.index]}


def build_global_prompt(project: Project, only_selected: bool = True) -> str:
    scenes = [s for s in project.scenes if s.prompt_text and (s.selected or not only_selected)]
    if not scenes:
        return ""
    lang = project.prompt_language or "en"
    used = {i for s in scenes for i in (s.character_indexes or [])}
    total = sum(scene_duration(s) for s in scenes)
    style = STYLES.get(project.prompt_style, ("", ""))[1] or project.visual_style
    out = [f"GLOBAL VIDEO PROMPT — {project.name}", NOTICE, "",
           f"Total duration: {total:g} seconds · {len(scenes)} scene(s) · "
           f"Format: {project.width}x{project.height} ({project.orientation})",
           f"Overall visual style: {style or 'n/a'}", f"Overall mood: {project.mood or 'n/a'}",
           f"Spoken language: {project.language or 'none detected'}", "",
           "CHARACTER BIBLE (keep every character strictly identical in all scenes)"]
    chars = [c for c in project.characters if c.index in used]
    out += [f"Character {c.index}: {descriptor_for(c, lang)}" for c in chars] or ["No identified character."]
    for s in scenes:
        out += ["", "=" * 60, s.prompt_text]
    return "\n".join(out)


def build_script(project: Project) -> str:
    """Script global lisible : scènes, descriptions et dialogues attribués."""
    out = [f"# Script — {project.name}", "",
           "_Reconstruction issue de l'analyse de la vidéo ; les répliques sont celles réellement transcrites._", ""]
    for s in project.scenes:
        d = s.data or {}
        out += [f"## Scène {s.index:02d} — {ts(s.start)} à {ts(s.end)}",
                f"**Lieu :** {d.get('location') or '—'} · **Moment :** {d.get('time_of_day') or '—'}", ""]
        if s.description:
            out += [s.description, ""]
        for l in lines_for(project, s):
            who = f"PERSONNAGE {l.character_index}" if l.character_index else "VOIX NON ATTRIBUÉE"
            extra = ", ".join(x for x in (l.tone, l.emotion) if x)
            text = l.text.strip() if l.identifiable and l.text.strip() else "[Dialogue non identifiable]"
            out += [f"**{who}**" + (f" _({extra})_" if extra else "") + f" [{ts(l.start)}]", f"> {text}", ""]
    return "\n".join(out)
