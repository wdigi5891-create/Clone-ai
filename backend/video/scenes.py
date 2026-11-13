"""Découpage en scènes : détection réelle des changements de plan (PySceneDetect)
ou découpage à durée fixe."""
from dataclasses import dataclass

MIN_SCENE_SECONDS = 0.6


@dataclass
class SceneSpan:
    start: float
    end: float


def fixed_scenes(duration: float, seconds: float) -> list[SceneSpan]:
    """Ex. 20 s avec un pas de 10 s -> [0-10], [10-20]. Un reliquat très court
    est fusionné avec la séquence précédente."""
    spans, t = [], 0.0
    while t < duration - 1e-6:
        spans.append(SceneSpan(round(t, 3), round(min(t + seconds, duration), 3)))
        t += seconds
    if len(spans) > 1 and spans[-1].end - spans[-1].start < MIN_SCENE_SECONDS:
        last = spans.pop()
        spans[-1].end = last.end
    return spans


def smart_scenes(path: str, duration: float, max_scenes: int = 60) -> list[SceneSpan]:
    from scenedetect import AdaptiveDetector, ContentDetector, SceneManager, open_video

    video = open_video(str(path))
    manager = SceneManager()
    manager.add_detector(AdaptiveDetector(min_scene_len=max(int((video.frame_rate or 25) * MIN_SCENE_SECONDS), 8)))
    manager.detect_scenes(video, show_progress=False)
    found = manager.get_scene_list()
    if not found:
        # Second passage avec un détecteur de contenu plus sensible (fondus, coupes douces)
        video = open_video(str(path))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=22.0))
        manager.detect_scenes(video, show_progress=False)
        found = manager.get_scene_list()
    spans = [SceneSpan(round(a.seconds, 3), round(b.seconds, 3)) for a, b in found]
    return normalize(spans, duration, max_scenes)


def normalize(spans: list[SceneSpan], duration: float, max_scenes: int) -> list[SceneSpan]:
    """Couvre toute la durée, fusionne les plans trop courts et plafonne le nombre de scènes."""
    if not spans:
        return [SceneSpan(0.0, round(duration, 3))]
    spans = sorted(spans, key=lambda s: s.start)
    spans[0].start = 0.0
    spans[-1].end = round(max(duration, spans[-1].start + 0.1), 3)
    merged: list[SceneSpan] = []
    for s in spans:
        if merged and (s.end - s.start) < MIN_SCENE_SECONDS:
            merged[-1].end = s.end
        else:
            if merged:
                s.start = merged[-1].end
            merged.append(s)
    while len(merged) > max_scenes:
        i = min(range(len(merged)), key=lambda k: merged[k].end - merged[k].start)
        j = i - 1 if i > 0 else i + 1
        a, b = sorted((i, j))
        merged[a].end = merged[b].end
        merged.pop(b)
    return merged
