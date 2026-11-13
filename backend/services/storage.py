"""Stockage objet : backend local (dev) ou compatible S3 (production)."""
import shutil
import time
from pathlib import Path
from urllib.parse import quote

from core.config import get_settings
from core.security import sign_path


class Storage:
    def put_file(self, local_path: str | Path, key: str, content_type: str | None = None) -> int: ...
    def download(self, key: str, local_path: str | Path) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def delete_prefix(self, prefix: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def url(self, key: str) -> str: ...


class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError("Clé de stockage invalide.")
        return p

    def put_file(self, local_path, key, content_type=None) -> int:
        dest = self.path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dest)
        return dest.stat().st_size

    def download(self, key, local_path) -> None:
        shutil.copyfile(self.path(key), local_path)

    def read(self, key) -> bytes:
        return self.path(key).read_bytes()

    def delete(self, key) -> None:
        self.path(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix) -> None:
        shutil.rmtree(self.path(prefix), ignore_errors=True)

    def exists(self, key) -> bool:
        return self.path(key).is_file()

    def url(self, key) -> str:
        s = get_settings()
        exp = int(time.time()) + s.signed_url_ttl_seconds
        return f"{s.public_api_url}/api/files/{quote(key)}?exp={exp}&sig={sign_path(key, exp)}"


class S3Storage(Storage):
    def __init__(self):
        import boto3

        s = get_settings()
        self.bucket = s.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=s.s3_region,
            endpoint_url=s.s3_endpoint_url or None,
            aws_access_key_id=s.s3_access_key_id or None,
            aws_secret_access_key=s.s3_secret_access_key or None,
        )

    def put_file(self, local_path, key, content_type=None) -> int:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.upload_file(str(local_path), self.bucket, key, ExtraArgs=extra)
        return Path(local_path).stat().st_size

    def download(self, key, local_path) -> None:
        self.client.download_file(self.bucket, key, str(local_path))

    def read(self, key) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def delete_prefix(self, prefix) -> None:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix.rstrip("/") + "/"):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})

    def exists(self, key) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def url(self, key) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=get_settings().signed_url_ttl_seconds,
        )


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        _storage = S3Storage() if s.storage_backend == "s3" else LocalStorage(s.storage_local_dir)
    return _storage
