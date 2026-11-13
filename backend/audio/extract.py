"""Extraction de la piste audio (mono 16 kHz, MP3 compact) pour la transcription."""
import subprocess
from pathlib import Path

from video.probe import VideoError


def extract_audio(video: str, out: str) -> str:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         "-b:a", "48k", str(out)],
        capture_output=True, text=True, timeout=900,
    )
    if r.returncode != 0 or not Path(out).exists() or Path(out).stat().st_size == 0:
        raise VideoError("Extraction de la piste audio impossible.")
    return str(out)
