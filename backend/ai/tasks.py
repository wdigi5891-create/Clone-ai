"""Tâches IA de haut niveau (indépendantes du fournisseur) : consignes + schémas JSON.

Suivi des personnages : le modèle de vision reçoit des images clés horodatées de
toutes les scènes et doit regrouper les apparitions d'un même individu sous un
identifiant neutre ; les scènes d'apparition sont déduites des images citées.
"""
from ai.base import ImageInput, JSONModel

LANG_NAMES = {"fr": "French", "en": "English", "es": "Spanish", "pt": "Portuguese", "de": "German",
              "it": "Italian", "ar": "Arabic", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
              "hi": "Hindi", "sw": "Swahili", "yo": "Yoruba"}


def lang_name(code: str) -> str:
    return LANG_NAMES.get((code or "en").lower(), code or "English")


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


S = {"type": "string"}
INT = {"type": "integer"}
NUM = {"type": "number"}

SAFETY = (
    "Strict rules: never name, guess or hint at the real-world identity of any person, even if "
    "they look famous; use only neutral identifiers and visual descriptions. Describe only what "
    "is actually visible; when something cannot be determined, say so instead of inventing it. "
    "Apparent age is a rough visual estimate (a range), never a fact."
)

# ---------------------------------------------------------------- personnages
CHARACTERS_SCHEMA = _obj({
    "overall": _obj({"summary": S, "mood": S, "visual_style": S}),
    "characters": {"type": "array", "items": _obj({
        "index": INT,
        "physical_description": S,
        "skin_tone_appearance": S,
        "hair": S,
        "clothing": S,
        "accessories": S,
        "apparent_age": S,
        "facial_expressions": S,
        "posture": S,
        "distinctive_features": S,
        "prompt_descriptor": S,
        "frame_ids": {"type": "array", "items": S},
        "reference_frame_id": S,
        "reference_box": _obj({"x": NUM, "y": NUM, "width": NUM, "height": NUM}),
    })},
})


def identify_characters(model: JSONModel, images: list[ImageInput], language: str) -> dict:
    system = (
        "You are a film continuity supervisor analysing keyframes of one video in order to build "
        "character reference sheets for AI video generation. " + SAFETY
    )
    prompt = f"""The images above are keyframes from a single video, in chronological order. Each is preceded by a label giving its frame id, scene number and timestamp.

Identify every distinct character (person, or animal/creature/animated figure that acts as a character) visible in these frames. Track each one across frames: the same individual seen in several frames or scenes must be ONE character, even if the angle, lighting or framing changes. If the same individual clearly changes outfit between scenes, keep one character and describe each outfit with the scenes it belongs to. Ignore indistinct background extras unless they matter to the action. If there is no character at all, return an empty list.

Number characters from 1 in order of first appearance. For each character:
- Sheet fields (physical_description, skin_tone_appearance, hair, clothing, accessories, apparent_age, facial_expressions, posture, distinctive_features): write in {lang_name(language)}, precise and concrete (build, face shape, colours, fabrics, patterns, lengths). Write "none visible" (translated) when a field does not apply.
- prompt_descriptor: one dense English paragraph (60-110 words) that a video generation model can reuse verbatim in every scene to render this same character consistently: apparent age range, build, skin tone, face, hair, full outfit with colours, accessories, distinctive marks. No name, no action, no scene context.
- frame_ids: the ids of ALL frames in which this character is visible.
- reference_frame_id: the single frame where the character is clearest (sharp, face visible, largest in frame).
- reference_box: tight bounding box of the character (head to as much of the body as is visible) in that reference frame, as fractions of image width/height (x, y = top-left corner; values between 0 and 1).

Also fill "overall" in {lang_name(language)}: summary (2-3 sentences on what the video shows), mood (general atmosphere), visual_style (live action / animation / 3D, colour grading, production quality, genre feel)."""
    return model.generate_json(system, prompt, CHARACTERS_SCHEMA, images)


# -------------------------------------------------------------------- scènes
SCENE_SCHEMA = _obj({
    "location": S, "set_design": S, "time_of_day": S,
    "characters_present": {"type": "array", "items": INT},
    "character_positions": S, "actions": S, "gestures": S, "expressions": S, "movements": S,
    "lighting": S, "mood": S,
    "camera_type": S, "camera_angle": S, "camera_movement": S,
    "ambient_sounds": S, "music": S,
    "cinematic_description": S,
    "dialogue_notes": {"type": "array", "items": _obj({
        "line_id": S,
        "speaker_index": {"type": ["integer", "null"]},
        "tone": S, "emotion": S, "intensity": S, "pace": S,
    })},
})

SCENE_FIELDS = [k for k in SCENE_SCHEMA["properties"] if k not in ("characters_present", "dialogue_notes")]


def analyze_scene(model: JSONModel, images: list[ImageInput], *, scene_no: int, total: int,
                  start: float, end: float, characters: list[dict], dialogue: list[dict],
                  context: str, language: str) -> dict:
    system = (
        "You are a cinematographer and script supervisor producing a precise shot breakdown of "
        "one scene from its keyframes, for faithful re-creation with AI video tools. " + SAFETY
    )
    chars = "\n".join(f"- Character {c['index']}: {c['descriptor']}" for c in characters) or "- (no character identified in this video)"
    lines = "\n".join(
        f"- line_id={d['id']} [{d['start']:.2f}s-{d['end']:.2f}s]: "
        + (f"\"{d['text']}\"" if d["identifiable"] else "(speech present but unintelligible)")
        for d in dialogue) or "- (no speech detected in this scene)"
    prompt = f"""Scene {scene_no} of {total}, from {start:.2f}s to {end:.2f}s ({end - start:.2f}s long). The first images are this scene's keyframes in chronological order (labelled with their timestamps). Any images labelled "REFERENCE" are character reference crops, provided only so you can recognise who is who.

Video context: {context or 'n/a'}

Known characters (use these numbers; do not invent new ones):
{chars}

Speech transcribed in this scene (from the audio track, already transcribed by another system):
{lines}

Write every text field in {lang_name(language)}. Be specific and visual; infer motion from the differences between the successive keyframes.
- location, set_design (set dressing, props, background), time_of_day
- characters_present: numbers of the known characters visible in this scene's keyframes
- character_positions (placement in frame and relative to each other), actions, gestures, expressions, movements (how bodies and objects move through the scene)
- lighting (sources, direction, contrast, colour temperature), mood
- camera_type (shot size and lens feel), camera_angle, camera_movement (static, pan, tilt, dolly, handheld, zoom..., deduced from framing changes)
- ambient_sounds, music: you cannot hear the audio. Only state sounds that the visible action or setting makes near-certain, prefixed with the equivalent of "Inferred from the image:". Otherwise write the equivalent of "Not identifiable from the analysis".
- cinematic_description: 4-7 sentences describing the scene as a director would brief a crew, in chronological order.
- dialogue_notes: one entry per transcribed line above (same line_id). speaker_index: the character number ONLY if the keyframes make the speaker reasonably certain (e.g. only one character present, visibly speaking); otherwise null. tone, emotion, intensity, pace: short estimates based on the wording and the visible expressions; write the equivalent of "undetermined" when you cannot tell. Return an empty list if there are no lines."""
    return model.generate_json(system, prompt, SCENE_SCHEMA, images)


# ------------------------------------------------------------------- prompts
PROMPT_SCHEMA = _obj({
    "scene_description": S, "environment": S, "action_and_movement": S, "camera_direction": S,
    "lighting": S, "facial_expressions": S, "voice_direction": S, "sound_design": S,
    "visual_style": S, "continuity": S,
})


def write_scene_prompt(model: JSONModel, *, scene_no: int, total: int, duration: float, analysis: dict,
                       characters: list[dict], dialogue: list[dict], previous: str, video_style: str,
                       style_directive: str, spoken_language: str, language: str) -> dict:
    system = (
        "You are an expert prompt writer for AI video generators (Veo / Google Flow, Kling, Runway). "
        "You turn a shot breakdown into production-ready prompt sections. You are RECONSTRUCTING a "
        "scene from an analysis of the finished video: never claim or imply that this is the "
        "original prompt of the video. Never name real people. Voice direction must describe "
        "generic vocal qualities only, never instruct to imitate or clone a specific real person's voice."
    )
    chars = "\n".join(f"- Character {c['index']}: {c['descriptor']}" for c in characters) or "- (none)"
    lines = "\n".join(
        f"- [{d['start']:.2f}s-{d['end']:.2f}s] {d['speaker']}: "
        + (f"\"{d['text']}\"" if d["identifiable"] else "(unintelligible)")
        + f" | tone: {d['tone'] or '?'}, emotion: {d['emotion'] or '?'}, intensity: {d['intensity'] or '?'}, pace: {d['pace'] or '?'}"
        for d in dialogue) or "- (no dialogue)"
    breakdown = "\n".join(f"{k}: {v}" for k, v in analysis.items() if v)
    prompt = f"""Write the prompt sections for scene {scene_no} of {total} (target duration {duration:.1f}s), in {lang_name(language)}.

SHOT BREAKDOWN (from analysis of the source video):
{breakdown}

CHARACTERS IN THIS SCENE (their appearance block is inserted verbatim elsewhere; refer to them only as "Character N" and do not re-describe or alter their appearance):
{chars}

DIALOGUE (inserted verbatim elsewhere in its original language; do not translate, rewrite or add lines):
{lines}
Spoken language detected: {spoken_language or 'unknown'}

PREVIOUS SCENE (for continuity): {previous or 'this is the first scene'}
OVERALL LOOK OF THE SOURCE VIDEO: {video_style or 'n/a'}
REQUESTED VISUAL STYLE: {style_directive or 'stay faithful to the look of the source video'}

Sections to write (each rich, concrete and directly usable; 2-5 sentences unless noted):
- scene_description: the full situation and what happens, start to end.
- environment: location, set, props, background, time of day.
- action_and_movement: beat-by-beat physical actions, gestures and interactions, paced to fit the duration.
- camera_direction: shot size, angle, lens feel, camera movement and distance.
- lighting: sources, direction, shadows, colour palette, atmosphere.
- facial_expressions: expressions and visible emotions per character.
- voice_direction: language, apparent accent only if the breakdown identifies it, tone, pace and emotion per speaking character; state "No spoken dialogue." (translated) if none.
- sound_design: ambient sound, foley and music. Keep the breakdown's caveats: clearly mark suggestions as suggestions when the source audio was not identifiable.
- visual_style: cinematic style, realism level, quality and overall aesthetic, applying the requested visual style.
- continuity: explicit instructions to stay consistent with previous scenes (same characters with identical appearance and outfits, same location/lighting when unchanged, matching positions and screen direction)."""
    return model.generate_json(system, prompt, PROMPT_SCHEMA)


TRANSLATE_SCHEMA = _obj({"descriptors": {"type": "array", "items": _obj({"index": INT, "text": S})}})


def translate_descriptors(model: JSONModel, characters: list[dict], language: str) -> dict[int, str]:
    system = "You are a precise translator of character appearance descriptions for video generation prompts."
    body = "\n".join(f"Character {c['index']}: {c['descriptor']}" for c in characters)
    prompt = (f"Translate each character description into {lang_name(language)}. Keep every visual "
              f"detail, add nothing, name no one.\n\n{body}")
    r = model.generate_json(system, prompt, TRANSLATE_SCHEMA)
    return {int(d["index"]): d["text"] for d in r.get("descriptors", [])}
