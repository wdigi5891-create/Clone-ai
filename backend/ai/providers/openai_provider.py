"""Adaptateur OpenAI : vision + langage (JSON strict) et transcription (Whisper)."""
import json

import openai

from ai.base import (AIConfigError, AIError, ImageInput, Transcript, encode_image,
                     segments_from_whisper)
from core.config import get_settings


def _client():
    s = get_settings()
    if not s.openai_api_key:
        raise AIConfigError(
            "Clé API manquante : définissez OPENAI_API_KEY dans .env "
            "(ou changez le fournisseur concerné)."
        )
    return openai.OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url or None, max_retries=3)


def _wrap(e: Exception) -> AIError:
    if isinstance(e, openai.AuthenticationError):
        return AIConfigError("Clé OPENAI_API_KEY refusée par l'API OpenAI.")
    if isinstance(e, openai.RateLimitError):
        return AIError("Limite de débit ou quota OpenAI atteint. Relancez l'étape plus tard.")
    if isinstance(e, openai.APIStatusError):
        return AIError(f"Erreur de l'API OpenAI ({e.status_code}).")
    return AIError("Connexion à l'API OpenAI impossible.")


class OpenAIModel:
    name = "openai"

    def __init__(self):
        self.client = _client()
        self.settings = get_settings()

    def generate_json(self, system: str, prompt: str, schema: dict,
                      images: list[ImageInput] | None = None) -> dict:
        parts: list[dict] = []
        for img in images or []:
            if img.label:
                parts.append({"type": "text", "text": img.label})
            data = encode_image(img.path, self.settings.vision_max_image_px)
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
        parts.append({"type": "text", "text": prompt})
        try:
            r = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": parts}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "result", "strict": True, "schema": schema}},
            )
        except openai.OpenAIError as e:
            raise _wrap(e)
        choice = r.choices[0]
        if getattr(choice.message, "refusal", None):
            raise AIError("Le modèle a refusé d'analyser ce contenu (règles de sécurité).")
        if choice.finish_reason == "length":
            raise AIError("Réponse du modèle tronquée (limite de tokens atteinte).")
        try:
            return json.loads(choice.message.content or "")
        except json.JSONDecodeError:
            raise AIError("Réponse du modèle illisible (JSON invalide).")


class OpenAITranscriber:
    name = "openai"

    def __init__(self):
        self.client = _client()
        self.model = get_settings().openai_transcription_model

    def transcribe(self, audio_path: str) -> Transcript:
        try:
            with open(audio_path, "rb") as f:
                r = self.client.audio.transcriptions.create(
                    model=self.model, file=f, response_format="verbose_json",
                    timestamp_granularities=["segment"], temperature=0,
                )
        except openai.OpenAIError as e:
            raise _wrap(e)
        return Transcript(language=getattr(r, "language", "") or "",
                          segments=segments_from_whisper(getattr(r, "segments", None) or []))
