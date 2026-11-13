import pytest

from services import url_import
from services.url_import import UrlImportError


def test_rejects_malformed_and_private_urls():
    for bad in ("", "ftp://example.com/a.mp4", "pas un lien"):
        with pytest.raises(UrlImportError):
            url_import.validate(bad)
    for private in ("http://127.0.0.1/a.mp4", "http://localhost:8000/a.mp4", "http://169.254.169.254/latest"):
        with pytest.raises(UrlImportError):
            url_import.validate(private)


def test_tiktok_is_never_downloaded(monkeypatch):
    class R:
        status_code = 200
        def json(self):
            return {"title": "Ma vidéo", "author_name": "auteur"}
    monkeypatch.setattr(url_import.httpx, "get", lambda *a, **k: R())
    with pytest.raises(UrlImportError) as e:
        url_import.validate("https://www.tiktok.com/@user/video/123")
    assert e.value.code == "platform_restricted" and e.value.info["title"] == "Ma vidéo"
    with pytest.raises(UrlImportError) as e:
        url_import.validate("https://youtu.be/abc")
    assert e.value.code == "platform_restricted"


def test_check_url_endpoint(client, auth):
    r = client.post("/api/projects/check-url", headers=auth, json={"url": "http://127.0.0.1/x.mp4"})
    assert r.status_code == 422 and "suggestion" in r.json()
    r = client.post("/api/projects/import-url", headers=auth, json={"url": "https://example.com/v.mp4"})
    assert r.status_code == 400  # droits non confirmés
