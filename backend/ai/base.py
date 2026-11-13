"""Couche d'adaptation IA : interfaces communes à tous les fournisseurs.

Trois rôles interchangeables par configuration (.env) :
  - VisionModel   : comprend des images (personnages, scènes) -> JSON structuré
  - LanguageModel : produit descriptions et prompts            -> JSON structuré
  - Transcriber   : transcrit la piste audio                    -> segments horodatés
Ajouter un fournisseur = implémenter ces interfaces dans ai/providers/ et
l'enregistrer dans ai/registry.py. Le reste de l'application n'en dépend pas.
"""
import base64
from dataclasses import dataclass, field
from typing import Protocol

import cv2


class AIError(Exception):
    """Erreur IA présentable à l'utilisateur."""


class AIConfigError(AIError):
    """Fournisseur non configuré (clé API manquante, etc.)."""


@dataclass
class ImageInput:
    path: str
    label: str = ""


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    identifiable: bool = True
    confidence: float | None = None


@dataclass
class Transcript:
    language: str = ""
    segments: list[TranscriptSegment] = field(default_factory=list)


class JSONModel(Protocol):
    name: str

    def generate_json(self, system: str, prompt: str, schema: dict,
                      images: list[ImageInput] | None = None) -> dict: ...


class Transcriber(Protocol):
    name: str

    def transcribe(self, audio_path: str) -> Transcript: ...


def encode_image(path: str, max_px: int) -> str:
    """JPEG base64 redimensionné (limite le coût et respecte les limites des API)."""
    img = cv2.imread(str(path))
    if img is None:
        raise AIError(f"Image illisible : {path}")
    h, w = img.shape[:2]
    scale = max_px / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise AIError("Encodage d'image impossible.")
    return base64.standard_b64encode(buf.tobytes()).decode()


def segments_from_whisper(raw_segments, min_logprob: float = -1.0) -> list[TranscriptSegment]:
    """Convertit des segments de type Whisper. Les passages détectés comme parole mais
    trop incertains sont marqués non identifiables au lieu d'être inventés."""
    out = []
    for s in raw_segments:
        get = (lambda k, d=None: s.get(k, d)) if isinstance(s, dict) else (lambda k, d=None: getattr(s, k, d))
        text = (get("text") or "").strip()
        logprob = get("avg_logprob")
        no_speech = get("no_speech_prob") or 0.0
        if no_speech > 0.6 and (logprob is None or logprob < min_logprob):
            continue  # silence / musique : pas de parole
        uncertain = not text or (logprob is not None and logprob < min_logprob)
        out.append(TranscriptSegment(
            start=float(get("start") or 0), end=float(get("end") or 0),
            text="" if uncertain else text, identifiable=not uncertain,
            confidence=None if logprob is None else round(float(logprob), 3),
        ))
    return out
