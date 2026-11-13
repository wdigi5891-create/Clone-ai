from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import RateLimiter, create_access_token, get_current_user, hash_password, verify_password
from models import User
from services.storage import get_storage

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = RateLimiter(max_calls=20, per_seconds=60)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)
    accept_terms: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "created_at": u.created_at}


@router.post("/register", dependencies=[Depends(limiter)], status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not body.accept_terms:
        raise HTTPException(400, "Vous devez accepter la politique de confidentialité et les conditions d'utilisation.")
    email = body.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Un compte existe déjà avec cette adresse e-mail.")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"token": create_access_token(user.id), "user": _user_out(user)}


@router.post("/login", dependencies=[Depends(limiter)])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email.lower()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "E-mail ou mot de passe incorrect.")
    return {"token": create_access_token(user.id), "user": _user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.delete("/me", status_code=204)
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Suppression du compte et de toutes ses données."""
    for p in user.projects:
        get_storage().delete_prefix(f"projects/{p.id}")
    db.delete(user)
    db.commit()
