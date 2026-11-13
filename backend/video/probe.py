"""Métadonnées vidéo via ffprobe."""
import json
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction


class VideoError(Exception):
    """Erreur de traitement vidéo présentable à l'utilisateur."""


@dataclass
class VideoInfo:
    duration: float
    width: int
    height: int
    fps: float
    format: str
    video_codec: str
    has_audio: bool
    orientation: str

    def dict(self):
        return asdict(self)


def probe(path: str) -> VideoInfo:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise VideoError("La lecture du fichier vidéo a expiré.")
    if out.returncode != 0:
        raise VideoError("Fichier illisible : ce n'est pas une vidéo valide ou elle est corrompue.")
    data = json.loads(out.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and s.get("disposition", {}).get("attached_pic") != 1), None)
    if video is None:
        raise VideoError("Aucune piste vidéo détectée dans ce fichier.")
    fmt = data.get("format", {})
    duration = float(video.get("duration") or fmt.get("duration") or 0)
    if duration <= 0:
        raise VideoError("Durée de la vidéo indéterminable.")
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    if abs(rotation) in (90, 270):
        width, height = height, width
    try:
        fps = float(Fraction(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0"))
    except (ZeroDivisionError, ValueError):
        fps = 0.0
    orientation = "vertical" if height > width else "horizontal" if width > height else "carré"
    return VideoInfo(
        duration=round(duration, 3), width=width, height=height, fps=round(fps, 3),
        format=fmt.get("format_name", ""), video_codec=video.get("codec_name", ""),
        has_audio=any(s.get("codec_type") == "audio" for s in streams), orientation=orientation,
    )
