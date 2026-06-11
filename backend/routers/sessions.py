"""
routers/sessions.py — Session lifecycle endpoints.

A session tracks a complete lab measurement run (QA, PIV, or Research).
Each QA session enforces the 13-step mandatory setup sequence.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.database import get_conn
from backend.models import SessionCreate, SessionOut, StepComplete, LogEntry

router = APIRouter(prefix="/sessions", tags=["sessions"])

# ---------------------------------------------------------------------------
# The 13-step mandatory QA setup sequence (reference.md)
# ---------------------------------------------------------------------------
QA_STEPS = [
    "Switch OFF all 3 ceiling lights at Zone 5 switch",
    "Close and seal door; deploy blackout curtain",
    "Install TV in Position D (verify not in optical path)",
    "Install chart on pin registration — log chart type, substrate, batch/serial",
    "Mount camera on rail at designated stop (verify ±1 mm with laser meter)",
    "Level camera — pitch ±0.05°, roll ±0.05° (digital inclinometer)",
    "Align camera yaw — laser cross-hair within ±5 mm of chart center",
    "Position softboxes on floor registration marks (10 min warm-up)",
    "Measure and log chart illuminance (±5% of target)",
    "Log spectral data — CCT (±100 K), CRI (≥90) with UPRtek MK350S",
    "Log temperature and RH",
    "Verify and log all camera settings (ISO, aperture, shutter, WB, RAW, sharpening OFF)",
    "Test capture + review + begin programmatic capture",
]

PIV_STEPS = [
    "TV warm-up 30 min at intended brightness",
    "Full-white field — measure luminance at center + 4 quadrant centers (corner/center ≥ 80%)",
    "10-step grayscale ramp — measure each step, fit gamma (target 2.2)",
    "Measure white point CCT + spectrum with UPRtek MK350S",
    "Check for banding/mura on 100% white field",
    "Record display make/model/serial, firmware, picture mode settings",
]

RESEARCH_STEPS = [
    "Document deviation from QA setup",
    "Record operator, date, mode",
    "Confirm data destination is /Data/Research/ (NOT /Data/QA/)",
]


def _steps_for_mode(mode: str) -> list[str]:
    if mode == "QA":
        return QA_STEPS
    elif mode == "PIV":
        return PIV_STEPS
    return RESEARCH_STEPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_session(session_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


def _build_session_out(row: dict) -> SessionOut:
    conn = get_conn()
    steps = [
        dict(s) for s in conn.execute(
            "SELECT * FROM session_steps WHERE session_id=? ORDER BY step_num",
            (row["id"],)
        ).fetchall()
    ]
    log = [
        dict(l) for l in conn.execute(
            "SELECT * FROM session_log WHERE session_id=? ORDER BY timestamp",
            (row["id"],)
        ).fetchall()
    ]
    return SessionOut(
        id=row["id"],
        mode=row["mode"],
        camera_id=row.get("camera_id"),
        chart_type=row.get("chart_type"),
        rail_stop=row.get("rail_stop"),
        operator=row.get("operator"),
        notes=row.get("notes"),
        started_at=row["started_at"],
        ended_at=row.get("ended_at"),
        status=row["status"],
        steps=steps,
        log=log,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def start_session(body: SessionCreate) -> SessionOut:
    """Start a new lab session. Inserts the appropriate protocol steps."""
    conn = get_conn()
    session_id = str(uuid.uuid4())
    now = _now()

    conn.execute(
        "INSERT INTO sessions (id,mode,camera_id,chart_type,rail_stop,operator,notes,started_at,status) "
        "VALUES (?,?,?,?,?,?,?,?,'active')",
        (session_id, body.mode, body.camera_id, body.chart_type,
         body.rail_stop, body.operator, body.notes, now),
    )

    steps = _steps_for_mode(body.mode)
    for i, name in enumerate(steps, start=1):
        conn.execute(
            "INSERT INTO session_steps (session_id,step_num,step_name) VALUES (?,?,?)",
            (session_id, i, name),
        )

    conn.execute(
        "INSERT INTO session_log (session_id,timestamp,level,message) VALUES (?,?,?,?)",
        (session_id, now, "info", f"Session started — mode: {body.mode}"),
    )
    conn.commit()

    return _build_session_out(_fetch_session(session_id))


@router.get("/active")
def get_active_session() -> Optional[SessionOut]:
    """Return the currently active session, or null if none."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sessions WHERE status='active' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    return _build_session_out(dict(row))


@router.get("/{session_id}")
def get_session(session_id: str) -> SessionOut:
    return _build_session_out(_fetch_session(session_id))


@router.get("")
def list_sessions(limit: int = 50) -> list[SessionOut]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [_build_session_out(dict(r)) for r in rows]


@router.post("/{session_id}/steps/{step_num}/complete")
def complete_step(session_id: str, step_num: int, body: StepComplete) -> dict:
    """Mark a protocol step as completed."""
    _fetch_session(session_id)
    conn = get_conn()
    now = _now()
    conn.execute(
        "UPDATE session_steps SET completed=1, completed_at=?, notes=? "
        "WHERE session_id=? AND step_num=?",
        (now, body.notes, session_id, step_num),
    )
    conn.execute(
        "INSERT INTO session_log (session_id,timestamp,level,message) VALUES (?,?,?,?)",
        (session_id, now, "info", f"Step {step_num} completed"
         + (f": {body.notes}" if body.notes else "")),
    )
    conn.commit()
    return {"ok": True, "step_num": step_num, "completed_at": now}


@router.post("/{session_id}/log")
def add_log(session_id: str, body: LogEntry) -> dict:
    """Append a free-form log entry to the session."""
    _fetch_session(session_id)
    conn = get_conn()
    now = _now()
    conn.execute(
        "INSERT INTO session_log (session_id,timestamp,level,message) VALUES (?,?,?,?)",
        (session_id, now, body.level, body.message),
    )
    conn.commit()
    return {"ok": True, "timestamp": now}


@router.put("/{session_id}/end")
def end_session(session_id: str, aborted: bool = False) -> SessionOut:
    """End the session (completed or aborted)."""
    row = _fetch_session(session_id)
    if row["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    conn = get_conn()
    now = _now()
    final_status = "aborted" if aborted else "completed"
    conn.execute(
        "UPDATE sessions SET status=?, ended_at=? WHERE id=?",
        (final_status, now, session_id),
    )
    conn.execute(
        "INSERT INTO session_log (session_id,timestamp,level,message) VALUES (?,?,?,?)",
        (session_id, now, "info", f"Session ended — status: {final_status}"),
    )
    conn.commit()
    return _build_session_out(_fetch_session(session_id))
