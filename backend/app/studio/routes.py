"""Scenario Studio API — /api/studio/*

Contract (the Scenario-Engine block): catalogue (domains/faults/presets), scenario library +
authoring, run (simulate → KPI-scored result) + run history, training (procedure + authoritative
grade + coach + director), and settings (Anthropic API key).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_session

from . import catalog, service, settings_store
from .models import Procedure, ScenarioSpec, TrainAction

router = APIRouter(prefix="/api/studio", tags=["studio"])


# ── Catalogue ─────────────────────────────────────────────────────────
@router.get("/domains")
def domains() -> dict:
    return {"domains": catalog.domains()}


@router.get("/faults")
def faults(domain: str = "generic") -> dict:
    return {"domain": domain, "faults": catalog.faults(domain)}


@router.get("/presets")
def presets(domain: str = "generic") -> dict:
    return {"domain": domain, "presets": catalog.presets(domain)}


# ── Scenario library + authoring ──────────────────────────────────────
@router.get("/scenarios")
def scenarios(domain: str | None = None, db: Session = Depends(get_session)) -> dict:
    return {"scenarios": service.list_scenarios(db, domain)}


class AuthorReq(BaseModel):
    description: str
    domain: str = "generic"
    kind: str = "scenario"           # scenario | fault
    horizon_min: float = 60.0
    save: bool = True


@router.post("/scenarios/author")
def author(req: AuthorReq, db: Session = Depends(get_session)) -> dict:
    return service.author_and_save(db, req.description, req.domain, req.kind, req.horizon_min, req.save)


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(scenario_id: str, db: Session = Depends(get_session)) -> dict:
    if scenario_id.startswith("seed-"):
        raise HTTPException(403, "seed scenarios cannot be deleted")
    if not service.delete_scenario(db, scenario_id):
        raise HTTPException(404, "scenario not found")
    return {"id": scenario_id, "deleted": True}


# ── Run (simulate + score) ────────────────────────────────────────────
class RunReq(BaseModel):
    scenario_id: str | None = None
    spec: ScenarioSpec | None = None     # ad-hoc run of an authored (unsaved) spec
    analyze: bool = True


@router.post("/runs")
def create_run(req: RunReq, db: Session = Depends(get_session)) -> dict:
    try:
        result = service.run_scenario(db, scenario_id=req.scenario_id, spec=req.spec, analyze=req.analyze)
    except KeyError:
        raise HTTPException(404, "scenario not found")
    return result.model_dump()


@router.get("/runs")
def list_runs(limit: int = 25, domain: str | None = None, db: Session = Depends(get_session)) -> dict:
    return {"runs": service.list_runs(db, limit, domain)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_session)) -> dict:
    result = service.get_run(db, run_id)
    if result is None:
        raise HTTPException(404, "run not found")
    return result.model_dump()


@router.get("/runs/{run_id}/events")
def get_run_events(run_id: str, db: Session = Depends(get_session)) -> list[dict]:
    result = service.get_run(db, run_id)
    if result is None:
        raise HTTPException(404, "run not found")
    return [e.model_dump() for e in result.events]


# ── Training ──────────────────────────────────────────────────────────
class ProcedureReq(BaseModel):
    domain: str = "generic"
    system: str = "System"
    fault: str = "none"
    title: str = ""
    context: str = ""


@router.post("/training/procedure")
def training_procedure(req: ProcedureReq, db: Session = Depends(get_session)) -> dict:
    proc = service.build_procedure(db, req.domain, req.system, req.fault, req.title, req.context)
    return {"procedure": proc.model_dump()}


class GradeReq(BaseModel):
    procedure: Procedure
    actions: list[TrainAction] = []


@router.post("/training/grade")
def training_grade(req: GradeReq) -> dict:
    return service.grade_training(req.procedure, req.actions).model_dump()


class DirectorReq(BaseModel):
    procedure: Procedure


@router.post("/training/director")
def training_director(req: DirectorReq, db: Session = Depends(get_session)) -> dict:
    return {"beats": service.director(db, req.procedure)}


class CoachReq(BaseModel):
    messages: list[dict] = []
    context: dict = {}


@router.post("/training/coach")
def training_coach(req: CoachReq, db: Session = Depends(get_session)) -> dict:
    return {"reply": service.coach(db, req.messages, req.context)}


# ── Settings (Anthropic API key) ──────────────────────────────────────
@router.get("/settings")
def get_settings(db: Session = Depends(get_session)) -> dict:
    return settings_store.status(db)


class SettingsReq(BaseModel):
    api_key: str | None = None
    model: str | None = None


@router.post("/settings")
def update_settings(req: SettingsReq, db: Session = Depends(get_session)) -> dict:
    if req.api_key is not None:
        settings_store.set_api_key(db, req.api_key)
    if req.model:
        settings_store.set_model(db, req.model)
    return settings_store.status(db)


@router.delete("/settings/key")
def delete_key(db: Session = Depends(get_session)) -> dict:
    settings_store.clear_api_key(db)
    return settings_store.status(db)
