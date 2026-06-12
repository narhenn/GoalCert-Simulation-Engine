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
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
#  System prompt — Jilla's personality and teaching style
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Jilla, an AI cybersecurity instructor inside the GoalCert cyber range.

You are NOT a chatbot. You are a Socratic tutor who guides students to DISCOVER answers themselves.

CORE RULE: NEVER give the answer directly. Ask a question that leads the student there.
- Bad: "You should use nmap to scan the network."
- Good: "What tool would an attacker use first to map out what's on a network?"
- Bad: "The worm exploits SMBv1 on port 445."
- Good: "Look at the amber hosts on the map. What protocol do they all have in common? Why would an attacker care about that?"

PERSONALITY:
- Warm, encouraging senior analyst sitting next to a junior.
- Short and crisp. MAX 3 sentences per message. One concept at a time.
- Bold **key terms** on first use. Code blocks for commands: `nmap -sV 10.0.0.0/24`
- Reference real incidents: WannaCry ($4B damage), Colonial Pipeline ($4.4M ransom), NHS (£92M loss).
- When the student gets something right, celebrate briefly: "Exactly right."
- When wrong, redirect gently: "Close! But think about what protocol the worm actually uses..."

SOCRATIC METHOD (based on Khanmigo research):
1. First response: Ask a guiding question. Never state the answer.
2. If student answers correctly: Confirm + ask a deeper follow-up.
3. If student answers wrong: Give a nudge toward the right direction, ask again.
4. If student says "just tell me": Give a hint, not the answer. "Think about port 445..."
5. Only give direct instructions after 3+ failed attempts (the "bottom-out" hint).

ROLE-AWARE TEACHING:
- Red team student: Teach offensive tradecraft. "What would a real attacker do after getting this foothold?"
- SOC student: Teach detection. "Where in your telemetry would evidence of this technique show up?"
- Blue student: Teach response. "You've isolated one host. But the attacker had credentials — what else do you need to revoke?"

CONTEXT AWARENESS:
- You see the full simulation state: hosts, infections, R-value, phase, alerts, tools used.
- Use ACTUAL host names and tool names from the state. Don't be generic.
- Connect every explanation to what's happening on the student's screen RIGHT NOW.
- If the student's topology shows 5 infected hosts, say "see those 5 red nodes?" not "imagine some hosts are infected."

FORMAT:
- Max 3 sentences per message unless student asks to go deeper.
- One concept per message. Don't info-dump.
- End with a question that prompts the student to think or act.
- Use emoji sparingly: ✅ for correct, 🤔 for think about it, ⚡ for action needed."""


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
#  LLM API integration (OpenAI preferred, Claude fallback)
# ---------------------------------------------------------------------------
async def _call_openai(system: str, messages: list[dict], max_tokens: int = 400) -> str:
    """Call OpenAI GPT-4o-mini. Fast, cheap, good for teaching."""
    if not OPENAI_KEY:
        return ""
    try:
        import httpx
        oai_messages = [{"role": "system", "content": system}] + messages
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": oai_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception:
        pass
    return ""


async def _call_claude(system: str, messages: list[dict], max_tokens: int = 400) -> str:
    """Call Claude API. Fallback if OpenAI is not available."""
    if not ANTHROPIC_KEY:
        return ""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
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


async def _call_llm(system: str, messages: list[dict], max_tokens: int = 400) -> str:
    """Try OpenAI first (faster), then Claude, then return empty for rule-based fallback."""
    result = await _call_openai(system, messages, max_tokens)
    if result:
        return result
    result = await _call_claude(system, messages, max_tokens)
    if result:
        return result
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
                message=f"🤔 Look at the **{phase}** phase you're in. What kind of tool would an attacker/defender typically use at this stage?\n\nHint: check the tool palette — there's one that's available and matches this phase.",
                suggestions=[f"Is it {next_tool.get('name', '')}?", "I have no idea", "Just tell me"],
                highlight_tool=next_tool.get("id"),
            )
        return ChatResponse(
            message="You've used the available tools. Watch the simulation — what do you notice happening on the topology map? 🤔",
            suggestions=["What's changing?", "Explain current phase"],
        )

    # Phase / concept questions — Socratic style
    if any(k in msg_lower for k in ["what is", "explain", "how does", "why"]):
        if "lateral" in msg_lower:
            return ChatResponse(
                message="Look at the topology map — see how the red zone is expanding from one node to others? 🤔 What do you think is happening? How is the worm getting from one host to another without anyone clicking anything?",
                suggestions=["It uses SMB?", "It's scanning the network?", "I don't know"],
            )
        if "kill switch" in msg_lower or "killswitch" in msg_lower:
            return ChatResponse(
                message="🤔 WannaCry checked a specific domain before encrypting. If it resolved, the worm stopped. Why do you think the malware author included this check? And what could a defender do with that knowledge?",
                suggestions=["Sinkhole the domain?", "Block it at the firewall?", "Tell me the story"],
            )
        if "segment" in msg_lower:
            return ChatResponse(
                message="Think about it like hospital wards. If a disease breaks out in one ward, you close the doors between wards to stop it spreading. 🤔 What's the network equivalent of 'closing the doors'? And which specific port would you block for this worm?",
                suggestions=["Block port 445?", "Use a firewall?", "What is a VLAN?"],
            )
        if "ransomware" in msg_lower:
            return ChatResponse(
                message="Here's a question: if ransomware encrypts files at the END of the attack chain, what are all the steps that happen BEFORE encryption? 🤔 Look at the kill chain — where could a defender have stopped this?",
                suggestions=["During recon?", "Block the exploit?", "Stop lateral movement?"],
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

    # Try LLM (OpenAI first, then Claude)
    system = SYSTEM_PROMPT + f"\n\nCURRENT SIMULATION STATE:\n{context}"
    messages = []
    for h in req.history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    response = await _call_llm(system, messages)
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
