import io
import zipfile

from ai.base import segments_from_whisper


def upload(client, auth, video_path, **data):
    with open(video_path, "rb") as f:
        return client.post("/api/projects/upload", headers=auth,
                           files={"file": ("ma video.mp4", f, "video/mp4")},
                           data={"rights_confirmed": "true", **data})


def test_auth_required_and_validation(client):
    assert client.get("/api/projects").status_code == 401
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "court", "accept_terms": True})
    assert r.status_code == 422
    r = client.post("/api/auth/register", json={"email": "b@example.com", "password": "motdepasse123"})
    assert r.status_code == 400  # conditions non acceptées
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 401


def test_upload_validation(client, auth, video_path):
    with open(video_path, "rb") as f:
        r = client.post("/api/projects/upload", headers=auth, files={"file": ("v.mp4", f, "video/mp4")})
    assert r.status_code == 400 and "droits" in r.json()["message"]
    r = client.post("/api/projects/upload", headers=auth, data={"rights_confirmed": "true"},
                    files={"file": ("doc.avi", b"xxxx", "video/avi")})
    assert r.status_code == 415
    r = client.post("/api/projects/upload", headers=auth, data={"rights_confirmed": "true"},
                    files={"file": ("faux.mp4", b"ceci n'est pas une video", "video/mp4")})
    assert r.status_code == 422


def test_missing_api_key_fails_cleanly_then_retry(client, auth, video_path, fake_ai):
    from ai import registry
    pid = upload(client, auth, video_path).json()["id"]
    registry.set_override("vision", None)  # fournisseur réel sans clé -> erreur explicite
    registry.set_override("llm", None)
    assert client.post(f"/api/projects/{pid}/analyze", headers=auth, json={}).status_code == 202
    prog = client.get(f"/api/projects/{pid}/progress", headers=auth).json()
    steps = {s["key"]: s for s in prog["steps"]}
    assert prog["status"] == "failed"
    assert steps["frames"]["status"] == "done" and steps["transcription"]["status"] == "done"
    assert steps["characters"]["status"] == "failed" and "ANTHROPIC_API_KEY" in steps["characters"]["error"]
    assert steps["prompts"]["status"] == "pending"
    assert prog["scene_count"] == 3  # les résultats vidéo restent consultables

    registry.set_override("vision", fake_ai)
    registry.set_override("llm", fake_ai)
    r = client.post(f"/api/projects/{pid}/retry", headers=auth, json={})
    assert r.status_code == 202 and r.json()["from_step"] == "characters"
    assert client.get(f"/api/projects/{pid}/progress", headers=auth).json()["status"] == "completed"


def test_full_analysis_flow(client, auth, video_path, fake_ai):
    r = upload(client, auth, video_path, name="Mon projet")
    assert r.status_code == 201, r.text
    p = r.json()
    pid = p["id"]
    assert p["status"] == "uploaded" and p["width"] == 640 and p["thumbnail_url"]
    assert p["steps"][0]["key"] == "import" and p["steps"][0]["status"] == "done"

    assert client.post(f"/api/projects/{pid}/analyze", headers=auth,
                       json={"split_mode": "fixed", "split_seconds": 7}).status_code == 422
    assert client.post(f"/api/projects/{pid}/analyze", headers=auth,
                       json={"split_mode": "smart"}).status_code == 202
    p = client.get(f"/api/projects/{pid}", headers=auth).json()
    assert p["status"] == "completed", p["steps"]
    assert all(s["status"] == "done" and s["progress"] == 1 for s in p["steps"])
    assert p["language"] == "fr" and p["mood"] == "Calme"

    # Scènes et images clés
    assert [round(s["start"]) for s in p["scenes"]] == [0, 4, 8]
    for s in p["scenes"]:
        assert {f["kind"] for f in s["frames"]} >= {"start", "middle", "end"}
        assert sum(f["is_representative"] for f in s["frames"]) == 1
        assert s["data"]["location"] and s["description"]
        assert s["character_indexes"] == [1]  # l'index inconnu 99 est écarté
    img = client.get(p["scenes"][0]["frames"][0]["url"].replace("http://localhost:8000", ""))
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/files/projects/{pid}/source.mp4?exp=9999999999&sig=bad").status_code == 403

    # Personnages : identifiants neutres, image de référence, scènes d'apparition
    c1, c2 = p["characters"]
    assert c1["label"] == "Personnage 1" and c1["reference_url"] and c2["reference_url"]
    assert c1["scene_indexes"] == [1, 2, 3]

    # Dialogues : passage inaudible non inventé, attribution, rattachement aux scènes
    d = p["dialogues"]
    assert [x["scene_index"] for x in d] == [1, 2, 3]
    assert d[1]["identifiable"] is False and d[1]["text"] == ""
    assert d[0]["character_index"] == 1 and d[0]["tone"] == "posé"

    # Prompts : 13 sections, personnage et dialogue injectés à l'identique
    prompt = p["scenes"][0]["prompt_text"]
    for n, title in enumerate(["SCENE DESCRIPTION", "CHARACTER DESCRIPTION", "ENVIRONMENT", "ACTION AND MOVEMENT",
                               "CAMERA DIRECTION", "LIGHTING", "FACIAL EXPRESSIONS", "DIALOGUE", "VOICE DIRECTION",
                               "SOUND DESIGN", "VISUAL STYLE", "DURATION", "CONTINUITY"], 1):
        assert f"{n}. {title}" in prompt
    assert "Character 1: A tall figure in a red coat." in prompt
    assert '"Bonjour tout le monde."' in prompt and "4 seconds" in prompt
    assert "do not invent words" in p["scenes"][1]["prompt_text"]
    assert "not the original prompt" in p["global_prompt"] and "CHARACTER BIBLE" in p["global_prompt"]

    # Édition : un dialogue modifié est répercuté dans le prompt sans appel IA
    calls = len(fake_ai.calls)
    r = client.patch(f"/api/projects/{pid}/dialogues/{d[0]['id']}", headers=auth, json={"text": "Salut à tous !"})
    assert r.status_code == 200 and r.json()["edited"]
    cid = c1["id"]
    client.patch(f"/api/projects/{pid}/characters/{cid}", headers=auth,
                 json={"prompt_descriptor": "A tall figure in a GREEN coat."})
    sid = p["scenes"][0]["id"]
    client.patch(f"/api/projects/{pid}/scenes/{sid}", headers=auth, json={"target_duration": 8})
    p = client.get(f"/api/projects/{pid}", headers=auth).json()
    prompt = p["scenes"][0]["prompt_text"]
    assert '"Salut à tous !"' in prompt and "GREEN coat" in prompt and "8 seconds" in prompt
    assert "GREEN coat" in p["scenes"][2]["prompt_text"]  # cohérence entre scènes
    assert len(fake_ai.calls) == calls

    # Recréer : scènes choisies, nouvelle langue et nouveau style
    r = client.post(f"/api/projects/{pid}/prompts/regenerate", headers=auth,
                    json={"scene_ids": [sid], "language": "fr", "style": "horror"})
    assert r.status_code == 202
    assert client.post(f"/api/projects/{pid}/prompts/regenerate", headers=auth,
                       json={"style": "inconnu"}).status_code == 422
    p = client.get(f"/api/projects/{pid}", headers=auth).json()
    assert p["prompt_language"] == "fr" and p["prompt_style"] == "horror"
    assert "Character 1: TRADUIT 1" in p["scenes"][0]["prompt_text"]
    assert '"Salut à tous !"' in p["scenes"][0]["prompt_text"]  # dialogue conservé en langue d'origine
    client.patch(f"/api/projects/{pid}/scenes/{p['scenes'][2]['id']}", headers=auth, json={"selected": False})
    g = client.post(f"/api/projects/{pid}/prompts/global", headers=auth, json={"only_selected": True}).json()
    assert "SCENE 01" in g["global_prompt"] and "SCENE 03" not in g["global_prompt"]

    # Exports
    for kind in ("characters.json", "storyboard.md", "dialogues.srt", "prompts.txt", "script.md", "images.zip"):
        assert client.get(f"/api/projects/{pid}/export/{kind}", headers=auth).status_code == 200, kind
    srt = client.get(f"/api/projects/{pid}/export/dialogues.srt", headers=auth).text
    assert "[Dialogue non identifiable]" in srt and "00:00:00,500 --> 00:00:02,000" in srt
    pdf = client.get(f"/api/projects/{pid}/export/report.pdf", headers=auth)
    assert pdf.content[:5] == b"%PDF-" and len(pdf.content) > 20_000
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/projects/{pid}/export/all.zip", headers=auth).content))
    names = set(z.namelist())
    assert {"report.pdf", "script.md", "storyboard.md", "prompts/scene_01.txt", "prompts/global_prompt.txt",
            "dialogues/dialogues.srt", "characters/characters.json", "characters/character_1.jpg"} <= names
    assert sum(n.startswith("frames/") for n in names) >= 9

    # Tableau de bord, isolation entre comptes, suppression
    dash = client.get("/api/dashboard", headers=auth).json()
    assert dash["videos_analyzed"] == 1 and dash["total_duration_analyzed"] > 11 and dash["storage_bytes"] > 0
    other = client.post("/api/auth/register", json={"email": "autre@example.com", "password": "motdepasse123",
                                                    "accept_terms": True}).json()["token"]
    assert client.get(f"/api/projects/{pid}", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.delete(f"/api/projects/{pid}", headers=auth).status_code == 204
    assert client.get(f"/api/projects/{pid}", headers=auth).status_code == 404
    from services.storage import get_storage
    assert not get_storage().exists(f"projects/{pid}/source.mp4")


def test_fixed_split_and_no_audio_skip(client, auth, video_path, fake_ai, tmp_path):
    import subprocess
    silent = tmp_path / "muet.webm"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video_path, "-an", "-t", "10", "-c:v", "libvpx",
                    "-b:v", "300k", str(silent)], check=True)
    pid = upload(client, auth, str(silent)).json()["id"]
    client.post(f"/api/projects/{pid}/analyze", headers=auth, json={"split_mode": "fixed", "split_seconds": 5})
    p = client.get(f"/api/projects/{pid}", headers=auth).json()
    assert p["status"] == "completed"
    assert [(s["start"], s["end"]) for s in p["scenes"]] == [(0.0, 5.0), (5.0, 10.0)]
    step = next(s for s in p["steps"] if s["key"] == "transcription")
    assert step["status"] == "skipped" and "audio" in step["message"]
    assert "No identifiable dialogue" in p["scenes"][0]["prompt_text"]


def test_whisper_segments_never_invent_text():
    segs = segments_from_whisper([
        {"start": 0, "end": 1, "text": " Bonjour ", "avg_logprob": -0.2, "no_speech_prob": 0.01},
        {"start": 1, "end": 2, "text": "blabla", "avg_logprob": -1.6, "no_speech_prob": 0.2},
        {"start": 2, "end": 3, "text": "Merci", "avg_logprob": -1.4, "no_speech_prob": 0.9},
    ])
    assert len(segs) == 2
    assert segs[0].text == "Bonjour" and segs[0].identifiable
    assert segs[1].text == "" and not segs[1].identifiable
