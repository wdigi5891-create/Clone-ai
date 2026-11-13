"""Mots de passe, jetons JWT, URLs signées et limitation de débit."""
import hashlib
import hmac
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.config import get_settings
from core.db import get_db

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, s.secret_key, algorithm="HS256")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    from models import User

    if creds is None:
        raise HTTPException(401, "Authentification requise.")
    try:
        payload = jwt.decode(creds.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session invalide ou expirée.")
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(401, "Utilisateur introuvable.")
    return user


def sign_path(key: str, expires: int) -> str:
    msg = f"{key}:{expires}".encode()
    return hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_signature(key: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(sign_path(key, expires), signature)


class RateLimiter:
    """Fenêtre glissante en mémoire (par IP). Suffisant pour un nœud API ;
    placer un reverse-proxy / Redis devant pour un déploiement multi-nœuds."""

    def __init__(self, max_calls: int, per_seconds: int):
        self.max_calls, self.per = max_calls, per_seconds
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = Lock()

    def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        with self.lock:
            q = self.hits[ip]
            while q and q[0] < now - self.per:
                q.popleft()
            if len(q) >= self.max_calls:
                raise HTTPException(429, "Trop de requêtes. Réessayez dans un instant.")
            q.append(now)
