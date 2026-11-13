import time

import pytest

from core.security import sign_path, verify_signature
from services.storage import LocalStorage, S3Storage


def test_local_storage_blocks_path_traversal(tmp_path):
    st = LocalStorage(str(tmp_path / "root"))
    with pytest.raises(ValueError):
        st.path("../../etc/passwd")


def test_signed_urls_expire():
    future, past = int(time.time()) + 60, int(time.time()) - 1
    assert verify_signature("a/b.jpg", future, sign_path("a/b.jpg", future))
    assert not verify_signature("a/other.jpg", future, sign_path("a/b.jpg", future))
    assert not verify_signature("a/b.jpg", past, sign_path("a/b.jpg", past))


def test_s3_storage_roundtrip(tmp_path, monkeypatch):
    moto = pytest.importorskip("moto")
    import boto3
    from core.config import get_settings

    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(k, "test")
    monkeypatch.setattr(get_settings(), "s3_bucket", "avc-test")
    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="avc-test")
        st = S3Storage()
        src = tmp_path / "a.txt"
        src.write_text("bonjour")
        assert st.put_file(src, "projects/p1/frames/a.txt", "text/plain") == 7
        st.put_file(src, "projects/p1/source.txt")
        assert st.exists("projects/p1/frames/a.txt") and st.read("projects/p1/source.txt") == b"bonjour"
        st.download("projects/p1/frames/a.txt", tmp_path / "b.txt")
        assert (tmp_path / "b.txt").read_text() == "bonjour"
        assert "projects/p1/source.txt" in st.url("projects/p1/source.txt")
        st.delete_prefix("projects/p1")
        assert not st.exists("projects/p1/frames/a.txt") and not st.exists("projects/p1/source.txt")
