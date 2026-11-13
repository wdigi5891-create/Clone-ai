"""Adaptateur Gemini : construction de la requête et traitement des réponses (API simulée)."""
import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from ai import registry
from ai.base import AIConfigError, AIError, ImageInput
from ai.providers import gemini_provider as gp
from core.config import get_settings


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.interactions = self

    def create(self, **body):
        self.calls.append(body)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(status="completed", output_text=r if isinstance(r, str) else json.dumps(r))


def api_error(code):
    return errors.APIError(code, {"error": {"message": "x", "status": "X"}})


@pytest.fixture()
def gemini(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(gp, "RETRY_DELAYS", (0, 0, 0))

    def make(replies):
        client = FakeClient(replies)
        monkeypatch.setattr(gp, "_client", lambda: client)
        return client
    return make


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    monkeypatch.setattr(get_settings(), "vision_provider", "gemini")
    with pytest.raises(AIConfigError, match="GEMINI_API_KEY"):
        registry.get_vision()


def test_generate_json_sends_images_and_schema(gemini, video_path, tmp_path):
    from video.frames import extract_frame
    img = tmp_path / "f.jpg"
    extract_frame(video_path, 1.0, str(img))
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
    client = gemini([{"a": "ok"}])
    out = gp.GeminiModel().generate_json("SYS", "PROMPT", schema, [ImageInput(str(img), "FRAME f01")])
    assert out == {"a": "ok"}
    call = client.calls[0]
    assert call["system_instruction"] == "SYS" and call["response_format"]["schema"] == schema
    assert [p["type"] for p in call["input"]] == ["text", "image", "text"]
    assert call["input"][1]["mime_type"] == "image/jpeg" and len(call["input"][1]["data"]) > 1000
    assert call["input"][2]["text"] == "PROMPT"


def test_retries_on_quota_then_succeeds(gemini):
    client = gemini([api_error(429), api_error(503), {"a": "ok"}])
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    assert gp.GeminiModel().generate_json("s", "p", schema) == {"a": "ok"}
    assert len(client.calls) == 3


def test_errors_are_user_readable(gemini):
    schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    gemini([api_error(429)] * 4)
    with pytest.raises(AIError, match="Quota"):
        gp.GeminiModel().generate_json("s", "p", schema)
    gemini([api_error(403)])
    with pytest.raises(AIConfigError):
        gp.GeminiModel().generate_json("s", "p", schema)
    gemini(["pas du json"])
    with pytest.raises(AIError, match="JSON"):
        gp.GeminiModel().generate_json("s", "p", schema)
    gemini([{"b": 1}])
    with pytest.raises(AIError, match="manquants"):
        gp.GeminiModel().generate_json("s", "p", schema)


def test_transcriber_never_invents_text(gemini, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"ID3" + b"\0" * 100)
    client = gemini([{"language": "fr", "segments": [
        {"start_seconds": 5.0, "end_seconds": 6.0, "text": "devine", "intelligible": False},
        {"start_seconds": 0.5, "end_seconds": 2.0, "text": " Bonjour. ", "intelligible": True},
    ]}])
    t = gp.GeminiTranscriber().transcribe(str(audio))
    assert t.language == "fr" and [s.start for s in t.segments] == [0.5, 5.0]
    assert t.segments[0].text == "Bonjour." and t.segments[0].identifiable
    assert t.segments[1].text == "" and not t.segments[1].identifiable
    assert client.calls[0]["input"][1]["type"] == "audio"
