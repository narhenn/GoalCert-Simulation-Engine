"""Studio settings persistence — the Anthropic API key + model, set from the platform UI.

The key is stored in the DB so it survives restart and is set once from the UI (never returned in
full to the client — only a masked preview + a has_key flag). Falls back to the ANTHROPIC_API_KEY
environment variable when nothing is stored.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from .db import StudioSetting

DEFAULT_MODEL = "claude-opus-4-8"
KEY_API = "anthropic_api_key"
KEY_MODEL = "anthropic_model"


@dataclass
class AiConfig:
    api_key: str = ""
    model: str = DEFAULT_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


def _get(db: Session, key: str) -> str:
    row = db.get(StudioSetting, key)
    return row.value if row else ""


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(StudioSetting, key)
    if row is None:
        db.add(StudioSetting(key=key, value=value, updated_at=datetime.utcnow()))
    else:
        row.value = value
        row.updated_at = datetime.utcnow()


def get_config(db: Session) -> AiConfig:
    key = _get(db, KEY_API) or os.getenv("ANTHROPIC_API_KEY", "")
    model = _get(db, KEY_MODEL) or DEFAULT_MODEL
    return AiConfig(api_key=key, model=model)


def set_api_key(db: Session, api_key: str) -> None:
    _set(db, KEY_API, (api_key or "").strip())
    db.commit()


def set_model(db: Session, model: str) -> None:
    _set(db, KEY_MODEL, (model or DEFAULT_MODEL).strip())
    db.commit()


def clear_api_key(db: Session) -> None:
    _set(db, KEY_API, "")
    db.commit()


def status(db: Session) -> dict:
    cfg = get_config(db)
    stored = bool(_get(db, KEY_API))
    src = "stored" if stored else ("env" if os.getenv("ANTHROPIC_API_KEY") else "none")
    masked = ""
    if cfg.api_key:
        masked = f"{cfg.api_key[:7]}…{cfg.api_key[-4:]}" if len(cfg.api_key) > 14 else "set"
    return {"has_key": cfg.enabled, "source": src, "model": cfg.model,
            "masked_key": masked, "ai_mode": "agent" if cfg.enabled else "stub"}
