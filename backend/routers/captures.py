"""
routers/captures.py — Image capture pipeline and file serving.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.cameras import get_camera
from backend.database import get_conn
from backend.models import CaptureRequest, CaptureOut

router = APIRouter(prefix="/captures", tags=["captures"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_captures_dir(data_dir: str) -> Path:
    return Path(data_dir) / "captures"


# Set by main.py at startup
_data_dir: str = "data"

def set_data_dir(path: str) -> None:
    global _data_dir
    _data_dir = path


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{camera_id}", status_code=201)
def trigger_capture(camera_id: str, body: CaptureRequest) -> CaptureOut:
    """
    Trigger a single-frame capture from the specified camera.

    The image is saved locally as JPEG. File name encodes session, timestamp,
    and camera ID for traceability.  Metadata (dimensions, file size) is
    extracted with Pillow and logged to the database.
    """
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Capture the frame
    try:
        image_bytes = cam.snapshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Capture failed: {exc}")

    # Derive image dimensions
    width = height = None
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
    except Exception:
        pass

    # Build file path using the USGS naming convention
    capture_id = str(uuid.uuid4())
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_tag = (body.session_id or "nosession")[:8]
    filename = f"{now_str}_{camera_id}_{session_tag}.jpg"

    captures_dir = Path(_data_dir) / "captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    file_path = captures_dir / filename
    file_path.write_bytes(image_bytes)

    # Persist to database
    conn = get_conn()
    conn.execute(
        "INSERT INTO captures "
        "(id,session_id,camera_id,captured_at,file_path,format,width,height,file_size,label,rail_stop) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            capture_id,
            body.session_id,
            camera_id,
            _now(),
            str(file_path),
            "jpeg",
            width,
            height,
            len(image_bytes),
            body.label,
            body.rail_stop,
        ),
    )

    # Log the capture into the session if one is active
    if body.session_id:
        conn.execute(
            "INSERT INTO session_log (session_id,timestamp,level,message) VALUES (?,?,?,?)",
            (body.session_id, _now(), "info",
             f"Capture: {filename} — {width}×{height} px, {len(image_bytes)//1024} KB"),
        )

    conn.commit()

    return CaptureOut(
        id=capture_id,
        session_id=body.session_id,
        camera_id=camera_id,
        captured_at=_now(),
        file_path=str(file_path),
        format="jpeg",
        width=width,
        height=height,
        file_size=len(image_bytes),
        label=body.label,
        rail_stop=body.rail_stop,
    )


@router.get("")
def list_captures(session_id: str | None = None, limit: int = 100) -> list[CaptureOut]:
    """List captures, optionally filtered by session."""
    conn = get_conn()
    if session_id:
        rows = conn.execute(
            "SELECT * FROM captures WHERE session_id=? ORDER BY captured_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM captures ORDER BY captured_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_capture(dict(r)) for r in rows]


@router.get("/{capture_id}")
def get_capture(capture_id: str) -> CaptureOut:
    conn = get_conn()
    row = conn.execute("SELECT * FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Capture not found")
    return _row_to_capture(dict(row))


@router.get("/{capture_id}/image")
def serve_capture_image(capture_id: str) -> FileResponse:
    """Serve the raw JPEG file for a capture."""
    conn = get_conn()
    row = conn.execute("SELECT file_path FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Capture not found")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")
    return FileResponse(str(path), media_type="image/jpeg")


@router.delete("/{capture_id}", status_code=204)
def delete_capture(capture_id: str) -> None:
    conn = get_conn()
    row = conn.execute("SELECT file_path FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Capture not found")
    path = Path(row["file_path"])
    if path.exists():
        path.unlink()
    conn.execute("DELETE FROM captures WHERE id=?", (capture_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _row_to_capture(row: dict) -> CaptureOut:
    return CaptureOut(
        id=row["id"],
        session_id=row.get("session_id"),
        camera_id=row["camera_id"],
        captured_at=row["captured_at"],
        file_path=row["file_path"],
        format=row.get("format", "jpeg"),
        width=row.get("width"),
        height=row.get("height"),
        file_size=row.get("file_size"),
        label=row.get("label"),
        rail_stop=row.get("rail_stop"),
    )
