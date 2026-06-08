"""Live multiplayer play over WebSocket.

A player connects with its server-issued id; the hub broadcasts a fresh full snapshot to everyone
on every state change (simple and race-free for a POC). Client → server messages:
  claim_role · set_profile · start · red_action · conclude · chat
"""
from __future__ import annotations

import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.live.manager import manager

router = APIRouter(tags=["live-stream"])


@router.websocket("/ws/live/{session_id}")
async def live_ws(websocket: WebSocket, session_id: str, player_id: str = "") -> None:
    await websocket.accept()
    session = manager.get(session_id)
    if session is None:
        await websocket.send_json({"type": "error", "message": "session not found"})
        await websocket.close()
        return

    player = session.players.get(player_id)
    if player is None:
        await websocket.send_json({"type": "error", "message": "unknown player — re-join the session"})
        await websocket.close()
        return

    manager.register(session_id, websocket)
    with manager.lock(session_id):
        player.connected = True
    await websocket.send_json({"type": "welcome", "player_id": player_id, "session_id": session_id})
    await manager.broadcast_snapshot(session_id)
    manager.ensure_ticker(session_id)  # drive any unoccupied seats while someone is watching

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")
            changed = True
            err: str | None = None

            with manager.lock(session_id):
                if action == "claim_role":
                    session.claim_role(player_id, msg.get("role", ""))
                elif action == "set_profile":
                    if player_id == session.host_id or player.role == "red":
                        session.set_profile(msg.get("profile", ""))
                elif action == "set_mission":
                    if player_id == session.host_id:
                        session.set_mission(msg.get("mission", ""))
                    else:
                        changed, err = False, "only the host can choose the mission"
                elif action == "start":
                    if player_id == session.host_id:
                        session.start(msg.get("profile"), msg.get("mission"))
                    else:
                        changed, err = False, "only the host can start the operation"
                elif action == "set_auto":
                    if player_id == session.host_id:
                        session.set_auto(msg.get("role", ""), msg.get("value"))
                    else:
                        changed, err = False, "only the host can change automation"
                elif action == "red_action":
                    ok, reason = session.execute_red_action(
                        player_id, msg.get("action_id", ""), msg.get("target_id"))
                    if not ok:
                        changed, err = False, reason
                elif action == "blue_action":
                    ok, reason = session.execute_blue_action(
                        player_id, msg.get("action_id", ""), msg.get("target_id"))
                    if not ok:
                        changed, err = False, reason
                elif action == "soc_action":
                    ok, reason = session.execute_soc_action(
                        player_id, msg.get("action_id", ""), msg.get("target_id"))
                    if not ok:
                        changed, err = False, reason
                elif action == "conclude":
                    if not session.conclude_manual(player_id):
                        changed, err = False, "cannot conclude right now"
                elif action == "chat":
                    text = str(msg.get("text", ""))[:300]
                    if text:
                        session._emit("chat", player.name, text, role=player.role or "observer")
                    else:
                        changed = False
                else:
                    changed, err = False, "unknown action"

            if err:
                await websocket.send_json({"type": "error", "message": err})
            if changed:
                await manager.broadcast_snapshot(session_id)
                # Persist report to DB when match completes
                if session.status == "completed" and session.report is not None:
                    manager.persist_report(session)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        manager.unregister(session_id, websocket)
        with manager.lock(session_id):
            player.connected = False
        with contextlib.suppress(Exception):
            await manager.broadcast_snapshot(session_id)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
