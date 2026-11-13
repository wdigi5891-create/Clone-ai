"""Adaptateur Anthropic (Claude) : vision + langage, sortie JSON contrainte par schéma."""
import json

import anthropic

from ai.base import AIConfigError, AIError, ImageInput, encode_image
from core.config import get_settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicModel:
    name = "anthropic"

    def __init__(self):
        s = get_settings()
        if not s.anthropic_api_key:
            raise AIConfigError(
                "Clé API manquante : définissez ANTHROPIC_API_KEY dans .env "
                "(ou changez VISION_PROVIDER / LLM_PROVIDER)."
            )
        self.settings = s
        self.client = anthropic.Anthropic(api_key=s.anthropic_api_key, max_retries=3)

    def generate_json(self, system: str, prompt: str, schema: dict,
                      images: list[ImageInput] | None = None) -> dict:
        s = self.settings
        content: list[dict] = []
        for img in images or []:
            if img.label:
                content.append({"type": "text", "text": img.label})
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg",
                "data": encode_image(img.path, s.vision_max_image_px)}})
        content.append({"type": "text", "text": prompt})
        kwargs = dict(
            model=s.anthropic_model,
            max_tokens=32000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": s.anthropic_effort,
                           "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            # Streaming : évite les timeouts HTTP sur les réponses longues.
            if s.anthropic_refusal_fallbacks:
                # En cas de refus du modèle principal, l'API relance la requête
                # sur un modèle de repli dans le même appel.
                ctx = self.client.beta.messages.stream(
                    betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
            else:
                ctx = self.client.messages.stream(**kwargs)
            with ctx as stream:
                message = stream.get_final_message()
        except anthropic.AuthenticationError:
            raise AIConfigError("Clé ANTHROPIC_API_KEY refusée par l'API Anthropic.")
        except anthropic.RateLimitError:
            raise AIError("Limite de débit Anthropic atteinte. Relancez l'étape dans quelques instants.")
        except anthropic.APIStatusError as e:
            raise AIError(f"Erreur de l'API Anthropic ({e.status_code}) : {e.message}")
        except anthropic.APIConnectionError:
            raise AIError("Connexion à l'API Anthropic impossible.")

        if message.stop_reason == "refusal":
            raise AIError("Le modèle a refusé d'analyser ce contenu (règles de sécurité).")
        if message.stop_reason == "max_tokens":
            raise AIError("Réponse du modèle tronquée (limite de tokens atteinte).")
        text = next((b.text for b in message.content if b.type == "text"), "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise AIError("Réponse du modèle illisible (JSON invalide).")
