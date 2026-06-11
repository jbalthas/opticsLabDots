"""
routers/cameras.py — Camera management, live stream proxy, and diagnostics.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.cameras import get_camera, list_cameras
from backend.models import CameraStatus

router = APIRouter(prefix="/cameras", tags=["cameras"])

_MJPEG_CHUNK = 8192


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def get_cameras() -> list[CameraStatus]:
    """List all configured cameras with online/offline status."""
    results = []
    for cam in list_cameras():
        online = cam.ping()
        info = cam.get_info() if online else {}
        results.append(CameraStatus(
            id=cam.config.id,
            name=cam.config.name,
            model=cam.config.model,
            ip=cam.config.ip,
            port=cam.config.port,
            online=online,
            firmware=info.get("firmware") or None,
            resolution=info.get("resolution") or None,
            notes=cam.config.notes,
        ))
    return results


@router.get("/{camera_id}/status")
def get_camera_status(camera_id: str) -> CameraStatus:
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    online = cam.ping()
    info = cam.get_info() if online else {}
    return CameraStatus(
        id=cam.config.id,
        name=cam.config.name,
        model=cam.config.model,
        ip=cam.config.ip,
        port=cam.config.port,
        online=online,
        firmware=info.get("firmware") or None,
        resolution=info.get("resolution") or None,
        notes=cam.config.notes,
    )


@router.get("/{camera_id}/probe")
def probe_camera(camera_id: str) -> dict:
    """
    Diagnostic endpoint — tries every known path with both Basic and Digest auth.
    Open in browser to identify the correct snapshot URL for a camera.
    """
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    from backend.cameras.vivotek import _SNAPSHOT_PATHS, _MJPEG_PATHS

    username = cam.config.username
    password  = cam.config.password
    base      = f"http://{cam.config.ip}:{cam.config.port}"

    auths = {
        "basic":  (username, password),
        "digest": httpx.DigestAuth(username, password),
    }

    results: dict = {"base_url": base, "paths": {}}

    with _httpx.Client(verify=False, follow_redirects=True, timeout=5.0) as client:
        for path in _SNAPSHOT_PATHS + _MJPEG_PATHS + ["/home.html", "/", "/index.html"]:
            path_results: dict = {}
            for auth_name, auth in auths.items():
                try:
                    r = client.get(f"{base}{path}", auth=auth, timeout=5.0)
                    path_results[auth_name] = {
                        "status": r.status_code,
                        "content_type": r.headers.get("content-type", ""),
                        "content_length": len(r.content),
                        "is_image": "image" in r.headers.get("content-type", ""),
                    }
                except Exception as exc:
                    path_results[auth_name] = {"error": str(exc)}
            results["paths"][path] = path_results

    return results


@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: str) -> Response:
    """Single-frame JPEG capture — no inter-frame codec compression."""
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    try:
        data = cam.snapshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return Response(content=data, media_type="image/jpeg")


@router.get("/{camera_id}/preview")
def preview_frame(camera_id: str) -> Response:
    """
    Return a single JPEG frame for live preview polling.

    The IT9388/IT9380 cameras have no HTTP MJPEG endpoint (all CGI viewer
    paths return 404). The frontend polls this endpoint every 1.5 s to
    produce a near-live view — adequate for lab framing and alignment.
    """
    cam = get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    try:
        data = cam.snapshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store"},
    )
