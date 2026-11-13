import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="avc_tests_"))
os.environ.update({
    "DATABASE_URL": f"sqlite:///{ROOT / 'test.db'}",
    "STORAGE_BACKEND": "local",
    "STORAGE_LOCAL_DIR": str(ROOT / "data"),
    "TEMP_DIR": str(ROOT / "tmp"),
    "TASK_BACKEND": "sync",
    "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "",
    "VISION_PROVIDER": "anthropic", "LLM_PROVIDER": "anthropic", "TRANSCRIPTION_PROVIDER": "openai",
    "SECRET_KEY": "test-secret-key-of-sufficient-length-0123456789", "MAX_DURATION_SECONDS": "60",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ai import registry  # noqa: E402
from ai.base import Transcript, TranscriptSegment  # noqa: E402


@pytest.fixture(scope="session")
def video_path() -> str:
    """Vidéo de 12 s : trois plans nettement différents (coupes à 4 s et 8 s) + piste audio."""
    out = ROOT / "sample.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=4",
        "-f", "lavfi", "-t", "4", "-i", "mandelbrot=size=640x360:rate=25",
        "-f", "lavfi", "-i", "smptebars=size=640x360:rate=25:duration=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p[v]",
        "-map", "[v]", "-map", "3:a", "-t", "12", "-c:v", "libx264", "-c:a", "aac", str(out),
    ], check=True)
    return str(out)


@pytest.fixture(scope="session")
def client():
    import main
    with TestClient(main.app) as c:
        yield c


@pytest.fixture()
def auth(client):
    import uuid
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "motdepasse123",
                                                "name": "Test", "accept_terms": True})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


class FakeModel:
    """Double de test conforme aux schémas (aucun appel réseau)."""
    name = "fake"

    def __init__(self):
        self.calls = []

    def generate_json(self, system, prompt, schema, images=None):
        props = schema["properties"]
        self.calls.append((list(props), len(images or [])))
        if "characters" in props:
            ids = [i.label.split()[1] for i in images]
            box = {"x": 0.25, "y": 0.1, "width": 0.4, "height": 0.8}
            common = {k: f"{k} test" for k in props["characters"]["items"]["properties"]
                      if props["characters"]["items"]["properties"][k] == {"type": "string"}}
            return {"overall": {"summary": "Résumé test", "mood": "Calme", "visual_style": "Mire de test"},
                    "characters": [
                        {**common, "index": 1, "prompt_descriptor": "A tall figure in a red coat.",
                         "frame_ids": ids, "reference_frame_id": ids[0], "reference_box": box},
                        {**common, "index": 2, "prompt_descriptor": "A short figure in a blue hat.",
                         "frame_ids": ids[-1:], "reference_frame_id": ids[-1], "reference_box": {"x": 2, "y": 0, "width": 0, "height": 0}},
                    ]}
        if "dialogue_notes" in props:
            import re
            out = {k: f"{k} test" for k, v in props.items() if v == {"type": "string"}}
            out["characters_present"] = [1, 99]
            out["dialogue_notes"] = [{"line_id": i, "speaker_index": 1, "tone": "posé", "emotion": "neutre",
                                      "intensity": "moyenne", "pace": "lent"}
                                     for i in re.findall(r"line_id=(\w+)", prompt)]
            return out
        if "descriptors" in props:
            import re
            return {"descriptors": [{"index": int(i), "text": f"TRADUIT {i}"}
                                    for i in re.findall(r"Character (\d+):", prompt)]}
        return {k: f"{k} generated" for k in props}


class FakeTranscriber:
    name = "fake"

    def transcribe(self, audio_path):
        assert Path(audio_path).stat().st_size > 0
        return Transcript(language="fr", segments=[
            TranscriptSegment(0.5, 2.0, "Bonjour tout le monde."),
            TranscriptSegment(5.0, 6.5, "", identifiable=False),
            TranscriptSegment(9.0, 11.0, "À bientôt."),
        ])


@pytest.fixture()
def fake_ai():
    model = FakeModel()
    registry.set_override("vision", model)
    registry.set_override("llm", model)
    registry.set_override("transcriber", FakeTranscriber())
    yield model
    for role in ("vision", "llm", "transcriber"):
        registry.set_override(role, None)
