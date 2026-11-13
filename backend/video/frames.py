"""Extraction des images clés : début, milieu, fin + image la plus représentative
(netteté mesurée par OpenCV), avec horodatages exacts."""
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2

from video.probe import VideoError


@dataclass
class ExtractedFrame:
    kind: str  # start | middle | end | key
    timestamp: float
    path: str
    width: int
    height: int
    sharpness: float
    is_representative: bool = False


def extract_frame(video: str, t: float, out: str, max_width: int | None = None) -> None:
    """Capture exacte à l'instant t (ffmpeg applique la rotation des vidéos mobiles)."""
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1"]
    if max_width:
        cmd += ["-vf", f"scale='min({max_width},iw)':-2"]
    cmd += ["-q:v", "2", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not Path(out).exists():
        raise VideoError(f"Extraction d'image impossible à {t:.2f}s.")


def sharpness_of(path: str) -> tuple[float, int, int]:
    img = cv2.imread(str(path))
    if img is None:
        return 0.0, 0, 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()), w, h


def _candidate_scores(video: str, times: list[float]) -> list[tuple[float, float]]:
    """Score de netteté (variance du Laplacien) sur des instants candidats."""
    cap = cv2.VideoCapture(str(video))
    scores = []
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            small = cv2.resize(frame, (320, max(1, int(frame.shape[0] * 320 / frame.shape[1]))))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            scores.append((t, float(cv2.Laplacian(gray, cv2.CV_64F).var())))
    finally:
        cap.release()
    return scores


def extract_scene_frames(video: str, start: float, end: float, out_dir: str, prefix: str,
                         fps: float = 25.0) -> list[ExtractedFrame]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    length = max(end - start, 0.0)
    eps = min(max(2.0 / (fps or 25.0), 0.04), length / 4 if length else 0.04)
    anchors = {"start": start + eps, "middle": start + length / 2, "end": max(end - eps, start)}
    # L'image de fin ne doit jamais appartenir à la scène suivante
    anchors["end"] = min(anchors["end"], end - 1.0 / (fps or 25.0))
    frames: list[ExtractedFrame] = []
    for kind, t in anchors.items():
        p = out / f"{prefix}_{kind}.jpg"
        try:
            extract_frame(video, t, str(p))
        except VideoError:
            if kind == "end":  # dernière image parfois indécodable : on recule
                t = max(start, t - 0.25)
                extract_frame(video, t, str(p))
            else:
                raise
        s, w, h = sharpness_of(str(p))
        frames.append(ExtractedFrame(kind, round(t, 3), str(p), w, h, s))

    # Image représentative : la plus nette parmi des candidats répartis dans la scène
    n = 9 if length >= 2 else 5
    cands = [start + length * (i + 1) / (n + 1) for i in range(n)]
    scores = _candidate_scores(video, cands)
    best = max(frames, key=lambda f: f.sharpness)
    if scores:
        t_best, _ = max(scores, key=lambda x: x[1])
        if all(abs(t_best - f.timestamp) > max(0.4, length * 0.12) for f in frames):
            p = out / f"{prefix}_key.jpg"
            try:
                extract_frame(video, t_best, str(p))
                s, w, h = sharpness_of(str(p))
                key = ExtractedFrame("key", round(t_best, 3), str(p), w, h, s)
                frames.append(key)
                if s >= best.sharpness * 0.9:
                    best = key
            except VideoError:
                pass
    best.is_representative = True
    return sorted(frames, key=lambda f: f.timestamp)
