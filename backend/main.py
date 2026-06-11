"""
main.py — OLB (Optics Lab Bench) FastAPI application entry point.

Startup sequence:
  1. Load config.yaml
  2. Initialize SQLite database
  3. Build camera registry
  4. Mount all routers
  5. Serve frontend/index.html at root
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure the lab-bench root is on the path (for running as: python backend/main.py)
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.database import init_db
from backend.cameras import build_registry
from backend.routers import sessions, cameras, captures, analysis, charts, tests

# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = _ROOT / "config.yaml"

def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        print(f"[OLB] config.yaml not found at {_CONFIG_PATH} — using defaults")
        return {"server": {}, "lab": {}, "cameras": []}
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

cfg = _load_config()
_server_cfg = cfg.get("server", {})
_lab_cfg    = cfg.get("lab", {})
_cam_cfg    = cfg.get("cameras", [])

# Resolve data directory relative to project root
_DATA_DIR = _ROOT / _lab_cfg.get("data_dir", "data")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Optics Lab Bench",
    description="USGS Camera and Imaging Systems Evaluation Laboratory — Data Collection & Analysis Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # localhost-only deployment; restrict if remote access is added
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup() -> None:
    print("[OLB] Starting up...")

    # 1. Database
    db_path = _DATA_DIR / "olb.db"
    init_db(db_path)
    print(f"[OLB] Database: {db_path}")

    # 2. Camera registry
    build_registry(_cam_cfg)
    print(f"[OLB] Cameras loaded: {len(_cam_cfg)}")

    # 3. Inject config into routers that need it
    captures.set_data_dir(str(_DATA_DIR))
    analysis.set_config(cfg)

    print("[OLB] Ready.")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(sessions.router)
app.include_router(cameras.router)
app.include_router(captures.router)
app.include_router(analysis.router)
app.include_router(charts.router)
app.include_router(tests.router)


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

_FRONTEND_DIR = _ROOT / "frontend"

@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(str(_FRONTEND_DIR / "index.html"))

# Serve any other static files in frontend/
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = _server_cfg.get("host", "localhost")
    port = _server_cfg.get("port", 8000)
    print(f"[OLB] Listening on http://{host}:{port}")
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
