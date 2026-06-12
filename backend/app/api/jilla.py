"""Jilla AI — contextual cybersecurity teaching assistant.

Jilla sees the live simulation state and teaches students through each phase.
Uses Claude API for intelligent, contextual responses. Falls back to rule-based
guidance if no API key is configured.

Endpoints:
  POST /api/jilla/chat   — send a message, get Jilla's response
  POST /api/jilla/hint   — get a progressive hint (4 levels)
  GET  /api/jilla/phase   — get proactive phase-transition message
"""
from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/jilla", tags=["jilla"])

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
#  System prompt — Jilla's personality and teaching style
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Jilla, an AI cybersecurity instructor embedded in the GoalCert cyber range platform.

PERSONALITY:
- Friendly but professional. Like a senior analyst sitting next to a junior, teaching them the ropes.
- Use short, crisp explanations. Never walls of text. 2-3 sentences per concept.
- Bold key terms on first use: **lateral movement**, **kill switch**, **shadow copies**.
- Use code blocks for commands: `nmap -sV 10.0.0.0/24`
- Reference real incidents (WannaCry, SolarWinds, Colonial Pipeline) to make concepts tangible.

RULES:
- You can SEE the current simulation state (hosts, infections, alerts, tools used).
- When the student asks "what should I do?", give specific guidance based on their role and the current phase.
- Never give away the answer directly on first ask. Use progressive hints:
  Level 1: Nudge ("Check the SOC alerts panel — something just fired.")
  Level 2: Direction ("Suricata detected an exploit signature. What tool would you use to investigate?")
  Level 3: Specific ("Open the alert log and look for the source IP. Then isolate that host.")
  Level 4: Bottom-out ("Click 'Isolate Host', select FIN-WS-014, and hit Execute.")
- When explaining a concept, connect it to what's happening on screen.
- Keep messages under 4 sentences unless the student asks to go deeper.

CONTEXT AWARENESS:
- You receive the current simulation state with each message.
- Use host names, tool names, and MITRE technique IDs from the actual state.
- If the student's role is Red, teach from the attacker perspective.
- If SOC, teach detection and investigation.
- If Blue, teach containment and recovery."""


# ---------------------------------------------------------------------------
#  Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    role: str = "red"               # student's role: red | soc | blue
    scenario_id: str = ""
    sim_state: dict[str, Any] = {}  # current simulation snapshot (topology, worm, alerts, etc.)
    history: list[dict] = []        # previous messages [{role: "user"|"assistant", content: "..."}]


class HintRequest(BaseModel):
    role: str = "red"
    scenario_id: str = ""
    sim_state: dict[str, Any] = {}
    hint_level: int = 1             # 1-4, progressive


class ChatResponse(BaseModel):
    message: str
    suggestions: list[str] = []     # quick-action buttons
    highlight_host: str | None = None  # host to spotlight on topology
    highlight_tool: str | None = None  # tool to pulse in the palette


# ---------------------------------------------------------------------------
#  Claude API integration
# ---------------------------------------------------------------------------
async def _call_claude(system: str, messages: list[dict], max_tokens: int = 300) -> str:
    """Call Claude API. Returns empty string if no API key or on error."""
    if not ANTHROPIC_KEY:
        return ""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
#  Build context string from simulation state
# ---------------------------------------------------------------------------
def _build_context(sim_state: dict, role: str, scenario_id: str) -> str:
    """Build a concise context string from the sim state for the AI."""
    if not sim_state:
        return "No simulation state available."

    parts = []
    parts.append(f"Scenario: {scenario_id}")
    parts.append(f"Student role: {role}")

    worm = sim_state.get("worm", {})
    if worm:
        parts.append(f"Infected hosts: {worm.get('infected', 0)}")
        parts.append(f"Impacted (encrypted): {worm.get('impacted', 0)}")
        parts.append(f"R-value: {worm.get('r_value', 0)}")
        parts.append(f"Propagating: {worm.get('propagating', False)}")
        parts.append(f"Kill switch: {worm.get('kill_switch', 'None')}")
        parts.append(f"Segmented: {worm.get('segmented', False)}")
        parts.append(f"Backups safe: {worm.get('backups_safe', True)}")

    guide = sim_state.get("guide", {})
    if guide:
        parts.append(f"Current phase: {guide.get('phase', 'unknown')}")
        parts.append(f"Progress: {guide.get('progress', {}).get('done', 0)}/{guide.get('progress', {}).get('total', 0)} tools used")
        next_tools = guide.get("next_tools", {})
        if next_tools.get(role):
            nt = next_tools[role]
            parts.append(f"Suggested next tool: {nt.get('name', '')} — {nt.get('guide_text', nt.get('summary', ''))}")

    teams = sim_state.get("teams", {})
    if teams.get(role):
        team = teams[role]
        parts.append(f"{role.upper()} score: {team.get('score', 0)}")
        done = [t["id"] for t in team.get("tools", []) if not t.get("available") and t.get("id")]
        if done:
            parts.append(f"Tools already used: {', '.join(done[:10])}")

    alerts = sim_state.get("alerts", [])
    if alerts:
        new_alerts = [a for a in alerts if a.get("status") == "new"]
        if new_alerts:
            parts.append(f"Untriaged alerts: {len(new_alerts)}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
#  Rule-based fallback (when no API key)
# ---------------------------------------------------------------------------
def _fallback_response(message: str, role: str, sim_state: dict) -> ChatResponse:
    """Generate a rule-based response when Claude API is not available."""
    msg_lower = message.lower()
    guide = sim_state.get("guide", {})
    phase = guide.get("phase", "")
    next_tool = (guide.get("next_tools", {}).get(role) or {})

    # "What should I do?" / "I'm stuck" / "Help"
    if any(k in msg_lower for k in ["what should", "stuck", "help", "next", "do now"]):
        if next_tool:
            return ChatResponse(
                message=f"Your next move should be **{next_tool.get('name', '')}**.\n\n{next_tool.get('guide_text', next_tool.get('summary', ''))}",
                suggestions=["Tell me more about this tool", "What happens after?", "Why this step?"],
                highlight_tool=next_tool.get("id"),
            )
        return ChatResponse(
            message="You've used all available tools for now. Watch the simulation play out and see how the other teams respond.",
            suggestions=["Explain current phase", "What's the score?"],
        )

    # Phase / concept questions
    if any(k in msg_lower for k in ["what is", "explain", "how does", "why"]):
        if "lateral" in msg_lower:
            return ChatResponse(
                message="**Lateral movement** is when an attacker spreads from one compromised host to others inside the network. In WannaCry, the worm automatically scanned for SMBv1 hosts and exploited them — no human needed.\n\nLook at the topology map — see how the red zone is expanding? That's lateral movement in action.",
                suggestions=["How to stop it?", "What is segmentation?"],
            )
        if "kill switch" in msg_lower or "killswitch" in msg_lower:
            return ChatResponse(
                message="WannaCry had a hardcoded domain check. If the domain resolved, the worm stopped. Marcus Hutchins registered it for **$10.69** and accidentally stopped the global outbreak.\n\nIn this simulation, Blue can sinkhole the domain to trigger the same effect.",
                suggestions=["How to sinkhole?", "Who is Marcus Hutchins?"],
            )
        if "segment" in msg_lower:
            return ChatResponse(
                message="**Network segmentation** divides your network into isolated zones. If the worm infects Finance, it can't reach Servers if the VLAN boundary on port 445 is severed.\n\nThis is THE most effective containment for a worm. The NHS hospitals that were segmented survived WannaCry; the flat ones were devastated.",
                suggestions=["How to segment?", "Show me on the map"],
            )
        if "ransomware" in msg_lower:
            return ChatResponse(
                message="**Ransomware** encrypts your files and demands payment (usually Bitcoin) for the decryption key. WannaCry demanded $300-600 per machine.\n\nThe key insight: encryption is the LAST step. By the time you see the ransom note, you've already lost. Defense must happen earlier in the kill chain.",
                suggestions=["What are the earlier steps?", "How to recover?"],
            )

    # Current state
    if any(k in msg_lower for k in ["status", "score", "state", "happening"]):
        worm = sim_state.get("worm", {})
        return ChatResponse(
            message=f"**Current state:** {worm.get('infected', 0)} hosts infected, {worm.get('impacted', 0)} encrypted.\nContainment trending: **{worm.get('outcome_band', 'Unknown')}**.\nPhase: **{phase}**.",
            suggestions=["What should I do?", "Explain this phase"],
        )

    # Default
    return ChatResponse(
        message=f"I'm Jilla, your cyber range instructor. I can see what's happening in the simulation and help you learn.\n\nYou're currently in the **{phase}** phase as **{role.upper()}**. Want me to explain what's happening or guide you to the next step?",
        suggestions=["Walk me through it", "What should I do next?", "Explain current phase"],
    )


# ---------------------------------------------------------------------------
#  Hint system (progressive, 4 levels)
# ---------------------------------------------------------------------------
HINT_TEMPLATES: dict[str, list[str]] = {
    "Host Discovery": [
        "The first step in any attack is knowing what's out there. What tool maps a network?",
        "Try using **nmap** to scan the subnet. Look at the tool palette on the left.",
        "Click the **Nmap** tool, select the target range, and run a host discovery scan.",
        "Click Nmap → select 'Local subnet' → click RUN. This reveals live hosts on the topology map.",
    ],
    "SMB Enumeration": [
        "You know the hosts. Now find which ones are vulnerable. What protocol does WannaCry exploit?",
        "**SMBv1** is the target. Use **NetExec** to enumerate which hosts still have it enabled.",
        "Click **NetExec (SMB Enum)** in the tool palette. It will flag vulnerable hosts in amber.",
        "Click NetExec → RUN. Hosts with SMBv1 enabled will turn amber on the map — those are your targets.",
    ],
    "Exploit": [
        "You have vulnerable targets. What famous exploit targets SMBv1?",
        "**EternalBlue** exploits a buffer overflow in SMBv1. Select a vulnerable host and fire it.",
        "Click **EternalBlue**, select a host marked amber, and attempt the exploit.",
        "Click EternalBlue → pick a host from the dropdown (only amber/vulnerable ones) → RUN.",
    ],
}


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Send a message to Jilla, get a contextual teaching response."""
    context = _build_context(req.sim_state, req.role, req.scenario_id)

    # Try Claude API first
    if ANTHROPIC_KEY:
        system = SYSTEM_PROMPT + f"\n\nCURRENT SIMULATION STATE:\n{context}"
        messages = []
        for h in req.history[-6:]:  # last 6 messages for context
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": req.message})

        response = await _call_claude(system, messages)
        if response:
            return ChatResponse(
                message=response,
                suggestions=["What should I do next?", "Explain this concept", "I'm stuck"],
            )

    # Fallback to rule-based
    return _fallback_response(req.message, req.role, req.sim_state)


@router.post("/hint", response_model=ChatResponse)
async def hint(req: HintRequest) -> ChatResponse:
    """Get a progressive hint (level 1-4). Each level reveals more."""
    guide = req.sim_state.get("guide", {})
    phase = guide.get("phase", "")
    level = max(1, min(4, req.hint_level))
    idx = level - 1

    hints = HINT_TEMPLATES.get(phase, [
        "Look at the current phase and think about what the next logical step would be.",
        "Check the tool palette — there's one tool available that matches this phase.",
        "The highlighted tool in the palette is your next move. Click it to see the briefing.",
        "Click the highlighted tool, fill in the parameters, and hit RUN.",
    ])
    hint_text = hints[min(idx, len(hints) - 1)]

    return ChatResponse(
        message=f"**Hint (level {level}/4):**\n{hint_text}",
        suggestions=["I need another hint" if level < 4 else "Got it, thanks!", "Explain this concept"],
    )


@router.get("/intro")
async def intro(role: str = "red", scenario_id: str = "") -> ChatResponse:
    """Get Jilla's introduction message for a new session."""
    role_intros = {
        "red": "You're the **attacker**. Your job is to progress the kill chain — from reconnaissance to encryption. I'll teach you what each tool does and why it matters in the real world.",
        "soc": "You're the **SOC analyst**. Your job is to detect the attack through telemetry — Zeek, Suricata, Splunk, Sysmon. I'll help you recognize the signals and triage the alerts.",
        "blue": "You're the **incident responder**. Your job is to contain the threat, stop the spread, and recover the organization. I'll guide you through the response playbook.",
    }

    return ChatResponse(
        message=f"Hey! I'm **Jilla**, your cyber range instructor.\n\n{role_intros.get(role, role_intros['red'])}\n\nI can see exactly what's happening in the simulation. Ask me anything — or pick an option below to get started.",
        suggestions=["Walk me through the scenario", "What should I do first?", "Just nudge me when I'm stuck"],
    )
