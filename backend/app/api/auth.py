"""Minimal but real auth: a seeded demo account + HMAC-signed bearer tokens (stdlib only).

This gates the SPA — sign in with the demo credentials to receive a token, which the frontend stores
and sends as `Authorization: Bearer <token>`. One demo operator for the POC; no DB users table needed.
Demo credentials default to admin@goalcert.io / GoalCert@2026 (override via GOALCERT_DEMO_* env vars).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

TOKEN_TTL = 7 * 24 * 3600  # 7 days


def _hash_pw(pw: str) -> str:
    return hashlib.sha256((settings.auth_secret + ":" + pw).encode()).hexdigest()


# Seeded demo operator. password is stored only as a salted hash.
DEMO_USER = {
    "email": settings.demo_email,
    "name": "Austin Robertson",
    "role": "Admin",
    "password_hash": _hash_pw(settings.demo_password),
}
USERS: dict[str, dict] = {DEMO_USER["email"].lower(): DEMO_USER}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload: str) -> str:
    sig = hmac.new(settings.auth_secret.encode(), payload.encode(), hashlib.sha256).digest()
    return _b64(sig)


def create_token(email: str) -> str:
    payload = _b64(json.dumps({"sub": email, "exp": int(time.time()) + TOKEN_TTL}).encode())
    return f"{payload}.{_sign(payload)}"


def verify_token(token: str) -> dict | None:
    try:
        payload, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return USERS.get(str(data.get("sub", "")).lower())
    except Exception:
        return None


def public_user(u: dict) -> dict:
    return {"email": u["email"], "name": u["name"], "role": u["role"]}


def current_user(authorization: str = Header(default="")) -> dict:
    user = verify_token(authorization.removeprefix("Bearer ").strip())
    if user is None:
        raise HTTPException(401, "not authenticated")
    return user


class LoginReq(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginReq) -> dict:
    user = USERS.get(req.email.strip().lower())
    if user is None or not hmac.compare_digest(user["password_hash"], _hash_pw(req.password)):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(user["email"]), "user": public_user(user)}


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return public_user(user)
