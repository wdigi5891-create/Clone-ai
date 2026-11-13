"""Sélection des fournisseurs IA d'après la configuration."""
from ai.base import AIConfigError, JSONModel, Transcriber
from core.config import get_settings

# Permet d'injecter des implémentations (tests, fournisseurs maison).
_overrides: dict[str, object] = {}


def set_override(role: str, impl) -> None:
    if impl is None:
        _overrides.pop(role, None)
    else:
        _overrides[role] = impl


def _json_model(provider: str) -> JSONModel:
    if provider == "anthropic":
        from ai.providers.anthropic_provider import AnthropicModel
        return AnthropicModel()
    if provider == "openai":
        from ai.providers.openai_provider import OpenAIModel
        return OpenAIModel()
    if provider == "gemini":
        from ai.providers.gemini_provider import GeminiModel
        return GeminiModel()
    raise AIConfigError(f"Fournisseur IA inconnu : « {provider} ».")


def get_vision() -> JSONModel:
    return _overrides.get("vision") or _json_model(get_settings().vision_provider)


def get_llm() -> JSONModel:
    return _overrides.get("llm") or _json_model(get_settings().llm_provider)


def get_transcriber() -> Transcriber | None:
    """None si la transcription est désactivée (TRANSCRIPTION_PROVIDER=none)."""
    if "transcriber" in _overrides:
        return _overrides["transcriber"]
    provider = get_settings().transcription_provider
    if provider in ("", "none"):
        return None
    if provider == "openai":
        from ai.providers.openai_provider import OpenAITranscriber
        return OpenAITranscriber()
    if provider == "gemini":
        from ai.providers.gemini_provider import GeminiTranscriber
        return GeminiTranscriber()
    if provider == "faster_whisper":
        from ai.providers.faster_whisper_provider import FasterWhisperTranscriber
        return FasterWhisperTranscriber()
    raise AIConfigError(f"Fournisseur de transcription inconnu : « {provider} ».")
