"""Adaptateur Google Gemini : vision, langage et transcription avec une seule clé.

Le niveau gratuit de l'API Gemini suffit pour essayer l'application (quotas limités ;
Google peut utiliser les contenus du niveau gratuit pour améliorer ses produits).
"""
import base64
import json
import time
from pathlib import Path

from google import genai
from google.genai import errors

from ai.base import (AIConfigError, AIError, ImageInput, Transcript, TranscriptSegment,
                     encode_image)
from core.config import get_settings

MAX_INLINE_BYTES = 18 * 1024 * 1024  # la requête entière est limitée à 20 Mo
RETRY_DELAYS = (15, 30, 60)  # quotas du niveau gratuit : on patiente puis on réessaie


def _client() -> genai.Client:
    s = get_settings()
    if not s.gemini_api_key:
        raise AIConfigError(
            "Clé API manquante : définissez GEMINI_API_KEY "
            "(clé gratuite sur https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=s.gemini_api_key)


def _run(client: genai.Client, sleep=time.sleep, **body) -> str:
    """Appel avec reprise sur dépassement de quota (429) et erreurs serveur passagères."""
    last: Exception | None = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            interaction = client.interactions.create(**body)
            if interaction.status not in (None, "completed"):
                raise AIError(f"Réponse incomplète du modèle Gemini (statut : {interaction.status}).")
            return interaction.output_text or ""
        except errors.APIError as e:
            last = e
            code = getattr(e, "code", None)
            if code in (401, 403):
                raise AIConfigError("Clé GEMINI_API_KEY refusée par l'API Gemini.")
            if code in (429, 500, 503) and attempt < len(RETRY_DELAYS):
                sleep(RETRY_DELAYS[attempt])
                continue
            if code == 429:
                raise AIError("Quota gratuit Gemini atteint. Patientez quelques minutes puis relancez l'étape.")
            raise AIError(f"Erreur de l'API Gemini ({code}) : {getattr(e, 'message', '') or e}")
    raise AIError(f"Erreur de l'API Gemini : {last}")


def _parse(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise AIError("Réponse du modèle illisible (JSON invalide).")
    if not isinstance(data, dict):
        raise AIError("Réponse du modèle inattendue.")
    return data


class GeminiModel:
    name = "gemini"

    def __init__(self):
        self.client = _client()
        self.settings = get_settings()

    def generate_json(self, system: str, prompt: str, schema: dict,
                      images: list[ImageInput] | None = None) -> dict:
        parts: list[dict] = []
        for img in images or []:
            if img.label:
                parts.append({"type": "text", "text": img.label})
            parts.append({"type": "image", "mime_type": "image/jpeg",
                          "data": encode_image(img.path, self.settings.vision_max_image_px)})
        parts.append({"type": "text", "text": prompt})
        text = _run(self.client, model=self.settings.gemini_model, system_instruction=system, input=parts,
                    response_format={"type": "text", "mime_type": "application/json", "schema": schema})
        data = _parse(text)
        missing = [k for k in schema.get("required", []) if k not in data]
        if missing:
            raise AIError(f"Réponse du modèle incomplète (champs manquants : {', '.join(missing)}).")
        return data


TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "segments": {"type": "array", "items": {
            "type": "object",
            "properties": {"start_seconds": {"type": "number"}, "end_seconds": {"type": "number"},
                           "text": {"type": "string"}, "intelligible": {"type": "boolean"}},
            "required": ["start_seconds", "end_seconds", "text", "intelligible"],
            "additionalProperties": False}},
    },
    "required": ["language", "segments"],
    "additionalProperties": False,
}

TRANSCRIBE_PROMPT = (
    "Transcribe every spoken utterance in this audio, verbatim, in the language actually spoken "
    "(do not translate, do not correct, do not summarise). Split it into short segments (one "
    "sentence or phrase each) with start_seconds and end_seconds measured from the beginning of "
    "the audio. If a passage contains speech you cannot make out with confidence, still return a "
    "segment for it with text \"\" and intelligible=false; never guess or invent words. Ignore "
    "music, noise and silence: if there is no speech at all, return an empty segments list. "
    "language: ISO 639-1 code of the main spoken language, or \"\" if there is no speech."
)


class GeminiTranscriber:
    name = "gemini"

    def __init__(self):
        self.client = _client()
        self.model = get_settings().gemini_transcription_model or get_settings().gemini_model

    def transcribe(self, audio_path: str) -> Transcript:
        raw = Path(audio_path).read_bytes()
        if len(raw) > MAX_INLINE_BYTES:
            raise AIError("Piste audio trop longue pour la transcription Gemini (limite de 20 Mo par requête).")
        text = _run(self.client, model=self.model, input=[
            {"type": "text", "text": TRANSCRIBE_PROMPT},
            {"type": "audio", "mime_type": "audio/mp3", "data": base64.b64encode(raw).decode()},
        ], response_format={"type": "text", "mime_type": "application/json", "schema": TRANSCRIPT_SCHEMA})
        data = _parse(text)
        segments = []
        for s in data.get("segments") or []:
            try:
                start, end = float(s.get("start_seconds", 0)), float(s.get("end_seconds", 0))
            except (TypeError, ValueError):
                continue
            body = (s.get("text") or "").strip()
            ok = bool(s.get("intelligible", True)) and bool(body)
            segments.append(TranscriptSegment(start=max(start, 0), end=max(end, start),
                                              text=body if ok else "", identifiable=ok))
        segments.sort(key=lambda x: x.start)
        return Transcript(language=(data.get("language") or "").strip(), segments=segments)
