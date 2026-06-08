"""REST endpoints for live multiplayer sessions (create / list / join / detail).

Live *play* happens over the WebSocket (ws/live.py); these endpoints exist so the lobby works
before a socket is open: a host starts a session, it appears in the open list, and others join by
clicking it and entering a name. No accounts — a player is just a name + a server-issued id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_session
from app.db.models import Scenario as ScenarioRow
from app.engine.scenario import Scenario
from app.live import missions as mp
from app.live.manager import manager

router = APIRouter(prefix="/api/live", tags=["live"])


class CreateSessionRequest(BaseModel):
    host_name: str = "host"
    mission_id: str | None = None     # launch a dedicated, self-contained mission
    scenario_id: str | None = None    # OR launch a pre-built scenario (e.g. Black Phoenix)


class JoinRequest(BaseModel):
    name: str = "operator"


def _load_scenario(db: Session, scenario_id: str) -> Scenario:
    row = db.get(ScenarioRow, scenario_id)
    if row is None:
        raise HTTPException(404, "scenario not found")
    return Scenario.model_validate(row.definition)


@router.get("/missions")
def list_missions() -> list[dict]:
    """The dedicated, standalone mission catalog (offensive/validation family)."""
    return [mp.public(m) for m in mp.MISSIONS]


@router.post("/sessions", status_code=201)
def create_session(req: CreateSessionRequest, db: Session = Depends(get_session)) -> dict:
    if req.mission_id:
        if req.mission_id not in mp.MISSION_BY_ID:
            raise HTTPException(404, "mission not found")
        scenario = mp.scenario_for(req.mission_id)
        session, host = manager.create(scenario, scenario.recommended_topology, req.host_name)
        session.mission = req.mission_id
        session.mission_locked = True
    elif req.scenario_id:
        scenario = _load_scenario(db, req.scenario_id)
        session, host = manager.create(scenario, scenario.recommended_topology, req.host_name)
    else:
        raise HTTPException(422, "provide a mission_id or a scenario_id")
    return {"session_id": session.id, "player_id": host.id,
            "scenario_name": session.scenario_name, "status": session.status}


@router.get("/sessions")
def list_sessions() -> list[dict]:
    return manager.list_open()


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict:
    session = manager.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    s = session.list_summary()
    s["players"] = [p.public() for p in session.players.values()]
    return s


@router.get("/sessions/{session_id}/report")
def get_session_report(session_id: str) -> dict:
    """The all-teams After-Action Report for a concluded live mission."""
    session = manager.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if session.report is None:
        raise HTTPException(409, "report not ready — the mission has not concluded yet")
    return session.report


@router.post("/sessions/{session_id}/join", status_code=201)
def join_session(session_id: str, req: JoinRequest) -> dict:
    session = manager.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    with manager.lock(session_id):
        player = session.add_player(req.name)
    return {"session_id": session.id, "player_id": player.id,
            "scenario_name": session.scenario_name, "status": session.status}
