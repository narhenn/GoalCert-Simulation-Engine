"""In-memory live-session registry + a WebSocket broadcast hub.

Sessions live in process memory (single-server POC). The Hub tracks the WebSockets connected to
each session so any state change can be broadcast to every participant. All session mutation is
serialised through a per-session lock so REST joins and WS actions don't race.
"""
from __future__ import annotations

import asyncio
import threading
import uuid

from fastapi import WebSocket

from app.engine.environment import EnvironmentSpec
from app.engine.scenario import Scenario

from . import auto
from .session import LiveSession, Player

AUTO_TICK = 3.0  # seconds between auto-driver actions (paced so humans can react)


class LiveManager:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSession] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._conns: dict[str, set[WebSocket]] = {}
        self._tickers: dict[str, asyncio.Task] = {}

    # ---- registry ------------------------------------------------------------
    def create(self, scenario: Scenario, env: EnvironmentSpec, host_name: str) -> tuple[LiveSession, Player]:
        host = Player(id=uuid.uuid4().hex[:12],
                      name=(host_name or "host").strip()[:40] or "host", is_host=True)
        session = LiveSession(scenario, env, host)
        self._sessions[session.id] = session
        self._locks[session.id] = threading.Lock()
        self._conns[session.id] = set()
        return session, host

    def get(self, session_id: str) -> LiveSession | None:
        return self._sessions.get(session_id)

    def lock(self, session_id: str) -> threading.Lock:
        return self._locks.setdefault(session_id, threading.Lock())

    def list_open(self) -> list[dict]:
        """Joinable / running sessions, newest first (completed ones drop off)."""
        rows = [s.list_summary() for s in self._sessions.values() if s.status in ("lobby", "active")]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)
        self._conns.pop(session_id, None)

    # ---- connections ---------------------------------------------------------
    def register(self, session_id: str, ws: WebSocket) -> None:
        self._conns.setdefault(session_id, set()).add(ws)

    def unregister(self, session_id: str, ws: WebSocket) -> None:
        self._conns.get(session_id, set()).discard(ws)

    async def broadcast(self, session_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._conns.get(session_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(session_id, ws)

    async def broadcast_snapshot(self, session_id: str) -> None:
        session = self.get(session_id)
        if session is not None:
            await self.broadcast(session_id, session.snapshot())

    # ---- auto-driver ticker --------------------------------------------------
    def ensure_ticker(self, session_id: str) -> None:
        """Start the auto-driver loop for a session if one isn't already running."""
        t = self._tickers.get(session_id)
        if t is not None and not t.done():
            return
        self._tickers[session_id] = asyncio.create_task(self._ticker_loop(session_id))

    async def _ticker_loop(self, session_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(AUTO_TICK)
                session = self.get(session_id)
                if session is None or not self._conns.get(session_id):
                    break  # gone, or nobody watching
                if session.status == "completed":
                    break
                if session.status != "active":
                    continue  # lobby — wait for start
                with self.lock(session_id):
                    changed = auto.tick(session)
                if changed:
                    await self.broadcast_snapshot(session_id)
                    if session.status == "completed":
                        break
        finally:
            self._tickers.pop(session_id, None)


manager = LiveManager()
