from video.frames import extract_scene_frames
from video.probe import VideoError, probe
from video.scenes import SceneSpan, fixed_scenes, normalize, smart_scenes

import pytest


def test_probe(video_path):
    info = probe(video_path)
    assert (info.width, info.height) == (640, 360)
    assert abs(info.duration - 12) < 0.2 and abs(info.fps - 25) < 0.1
    assert info.has_audio and info.orientation == "horizontal"


def test_probe_rejects_non_video(tmp_path):
    fake = tmp_path / "fake.mp4"
    fake.write_text("pas une vidéo")
    with pytest.raises(VideoError):
        probe(str(fake))


def test_fixed_split_20s_by_10s():
    spans = fixed_scenes(20.0, 10)
    assert [(s.start, s.end) for s in spans] == [(0.0, 10.0), (10.0, 20.0)]


def test_fixed_split_merges_tiny_remainder():
    spans = fixed_scenes(20.3, 10)
    assert len(spans) == 2 and spans[-1].end == 20.3
    assert [(s.start, s.end) for s in fixed_scenes(25.0, 10)][-1] == (20.0, 25.0)


def test_normalize_covers_whole_duration_and_caps():
    spans = normalize([SceneSpan(0.2, 3), SceneSpan(3, 3.2), SceneSpan(3.2, 9)], 10.0, 60)
    assert spans[0].start == 0 and spans[-1].end == 10.0
    assert all(a.end == b.start for a, b in zip(spans, spans[1:]))
    assert len(normalize([SceneSpan(i, i + 1) for i in range(10)], 10.0, 4)) == 4


def test_smart_detection_finds_real_cuts(video_path):
    spans = smart_scenes(video_path, 12.0)
    assert len(spans) == 3
    assert abs(spans[0].end - 4.0) < 0.2 and abs(spans[1].end - 8.0) < 0.2
    assert spans[0].start == 0 and spans[-1].end == 12.0


def test_keyframes_have_exact_timestamps(video_path, tmp_path):
    frames = extract_scene_frames(video_path, 4.0, 8.0, str(tmp_path), "s002", 25)
    kinds = {f.kind for f in frames}
    assert {"start", "middle", "end"} <= kinds
    assert all(4.0 <= f.timestamp < 8.0 for f in frames)
    assert sum(f.is_representative for f in frames) == 1
    assert all(f.width == 640 and f.sharpness > 0 for f in frames)
