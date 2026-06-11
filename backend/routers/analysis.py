"""
routers/analysis.py — Analysis pipeline endpoints.

Supports three engines:
  iqanalyzer — Image Engineering IQ-Analyzer X (hot folder or CLI)
  custom     — Built-in Python metrics (MTF, noise, uniformity, tonal)
  matlab     — MATLAB script runner (MatlabScripts/)
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.database import get_conn
from backend.models import AnalysisRequest, AnalysisOut

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Injected at app startup by main.py
_cfg: dict = {}

def set_config(cfg: dict) -> None:
    global _cfg
    _cfg = cfg


# ---------------------------------------------------------------------------
# MATLAB script discovery
# ---------------------------------------------------------------------------

@router.get("/matlab/scripts")
def list_matlab_scripts() -> list[dict]:
    """
    List all .m files in the configured MatlabScripts directory.
    Returns name (without .m), full path, and a description extracted
    from the first comment line of each script.
    """
    scripts_dir = Path(_cfg.get("lab", {}).get("matlab_scripts_dir",
                        "C:/WORK/HIF/Optics lab/MatlabScripts"))
    if not scripts_dir.exists():
        return []

    # Only expose entry-point scripts (measure_*). Helper functions like
    # sfrStandardROIs are called internally by _run_matlab and must not
    # appear in the UI dropdown — they require different arguments.
    results = []
    for f in sorted(scripts_dir.glob("measure_*.m")):
        description = _read_matlab_description(f)
        results.append({
            "name":        f.stem,
            "filename":    f.name,
            "path":        str(f),
            "description": description,
        })
    return results


def _read_matlab_description(path: Path) -> str:
    """Extract first non-empty comment line from a MATLAB script."""
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("%"):
                desc = line.lstrip("% ").strip()
                if desc:
                    return desc
    except Exception:
        pass
    return ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/detect-chart/{capture_id}")
def detect_chart(capture_id: str) -> dict:
    """
    Detect and identify the test chart in a capture using computer vision.

    Runs synchronously (fast — typically < 1 s).
    Returns chart presence, identification, confidence, and recommended test IDs.
    """
    conn = get_conn()
    row = conn.execute("SELECT * FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Capture not found")

    from backend.analysis.chart_detector import detect_chart as _detect
    return _detect(row["file_path"])


@router.post("/{capture_id}", status_code=202)
def submit_analysis(
    capture_id: str,
    body: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisOut:
    """
    Submit a capture for analysis. Runs in the background; poll status via GET.
    """
    conn = get_conn()
    row = conn.execute("SELECT * FROM captures WHERE id=?", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Capture not found")

    # Create pending analysis run record
    now = _now()
    cur = conn.execute(
        "INSERT INTO analysis_runs (capture_id,engine,profile,test_id,status,started_at) VALUES (?,?,?,?,'pending',?)",
        (capture_id, body.engine, body.profile, body.test_id, now),
    )
    run_id = cur.lastrowid
    conn.commit()

    # Dispatch to background task
    image_path = row["file_path"]
    background_tasks.add_task(
        _run_analysis, run_id, body.engine, image_path,
        body.test_id, body.profile, body.roi_preset, body.layout_file,
    )

    return _fetch_run(run_id)


@router.get("/{capture_id}")
def list_analysis_runs(capture_id: str) -> list[AnalysisOut]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM analysis_runs WHERE capture_id=? ORDER BY id DESC",
        (capture_id,)
    ).fetchall()
    return [_row_to_out(dict(r)) for r in rows]


@router.get("/runs/{run_id}")
def get_run(run_id: int) -> AnalysisOut:
    return _fetch_run(run_id)


# ---------------------------------------------------------------------------
# Background analysis tasks
# ---------------------------------------------------------------------------

def _run_analysis(run_id: int, engine: str, image_path: str, test_id: Optional[str],
                  profile: Optional[str], roi_preset: str = "quad4",
                  layout_file: Optional[str] = None) -> None:
    """Execute the requested analysis engine and update the DB with results."""
    from backend.routers.tests import _BY_ID as _TESTS_BY_ID

    conn = get_conn()
    conn.execute(
        "UPDATE analysis_runs SET status='running', started_at=? WHERE id=?",
        (_now(), run_id),
    )
    conn.commit()

    # Look up the test to get engine-specific parameters
    test = _TESTS_BY_ID.get(test_id or "", {})

    try:
        if engine == "custom":
            module = (test.get("engines", {}).get("custom") or {}).get("module")
            if module:
                from backend.analysis.custom import run_test
                results = run_test(module, image_path)
            else:
                from backend.analysis.custom import run_all
                results = run_all(image_path)

        elif engine == "iqanalyzer":
            # Use test's default IQ-Analyzer profile unless the request overrides it
            default_profile = (test.get("engines", {}).get("iqanalyzer") or {}).get("profile")
            effective_profile = profile or default_profile
            results = _run_iqanalyzer(image_path, effective_profile)

        elif engine == "matlab":
            engine_info = (test.get("engines") or {}).get("matlab")
            if not engine_info:
                results = {
                    "error": f"No MATLAB script defined for test '{test_id}'. "
                             "Check the test registry or choose a different engine.",
                }
            else:
                results = _run_matlab(image_path, engine_info["script"], roi_preset, layout_file)

        else:
            results = {"error": f"Unknown engine: {engine}"}

        conn.execute(
            "UPDATE analysis_runs SET status='completed', completed_at=?, results_json=? WHERE id=?",
            (_now(), json.dumps(results), run_id),
        )
    except Exception as exc:
        conn.execute(
            "UPDATE analysis_runs SET status='failed', completed_at=?, error_msg=? WHERE id=?",
            (_now(), str(exc), run_id),
        )
    finally:
        conn.commit()


def _run_iqanalyzer(image_path: str, profile: Optional[str]) -> dict:
    from backend.analysis.iqanalyzer import submit_to_hot_folder, run_cli
    lab = _cfg.get("lab", {})

    exe = lab.get("iqanalyzer_exe", "")
    if Path(exe).exists():
        # CLI mode if executable exists
        out_dir = lab.get("iqanalyzer_output_dir", "data/analysis")
        return run_cli(exe, image_path, profile=profile, output_dir=out_dir)

    # Hot folder mode
    in_dir  = lab.get("iqanalyzer_input_dir",  "data/iq_input")
    out_dir = lab.get("iqanalyzer_output_dir", "data/iq_output")
    return submit_to_hot_folder(image_path, in_dir, out_dir, profile=profile)


def _run_matlab(image_path: str, script: Optional[str], roi_preset: str = "quad4",
                layout_file: Optional[str] = None) -> dict:
    """Run a MATLAB analysis script via subprocess (fully non-interactive)."""
    lab = _cfg.get("lab", {})
    scripts_dir = lab.get("matlab_scripts_dir", "C:/WORK/HIF/Optics lab/MatlabScripts")

    if script is None:
        script = "measure_sfr_slanted_edge"

    # Hard guard: only measure_* scripts are valid entry points.
    # Helper functions (sfrStandardROIs, testWebCam, etc.) require different
    # arguments and must never be called directly via this endpoint.
    if not script.startswith("measure_"):
        return {
            "error": f"'{script}' is not a valid OLB analysis script. "
                     f"Only scripts prefixed 'measure_' can be run via the GUI. "
                     f"Helper functions like sfrStandardROIs are called internally.",
            "script": script,
        }

    script_path = Path(scripts_dir) / f"{script}.m"
    if not script_path.exists():
        return {"error": f"MATLAB script not found: {script_path}",
                "scripts_dir": scripts_dir}

    matlab_exe = _find_matlab_exe(lab.get("matlab_exe", ""))
    if not matlab_exe:
        return {"error": "MATLAB executable not found. Check matlab_exe in config.yaml.",
                "searched": lab.get("matlab_exe", "")}

    # Build exportBaseName alongside the image file
    img_path = Path(image_path)
    export_base = str(img_path.parent / img_path.stem).replace("\\", "/")
    img_path_fwd = str(img_path).replace("\\", "/")
    scripts_dir_fwd = str(scripts_dir).replace("\\", "/")

    # Build the MATLAB -batch command with all required args so no GUI prompts fire
    if script == "measure_sfr_slanted_edge":
        w, h = _get_image_dims(image_path)
        if w and h:
            batch_cmd = (
                f"addpath('{scripts_dir_fwd}'); "
                f"rois = sfrStandardROIs({w}, {h}, '{roi_preset}'); "
                f"measure_sfr_slanted_edge('{img_path_fwd}', rois, '{export_base}')"
            )
        else:
            batch_cmd = (
                f"addpath('{scripts_dir_fwd}'); "
                f"measure_sfr_slanted_edge('{img_path_fwd}', "
                f"sfrStandardROIs(1920,1080,'{roi_preset}'), '{export_base}')"
            )
    elif script == "measure_distortion_tags":
        # Resolve layout file: request param > config.yaml > error
        resolved_layout = (
            layout_file
            or _cfg.get("lab", {}).get("distortion_layout_file", "")
        )
        if not resolved_layout:
            return {
                "error": "measure_distortion_tags requires a tag layout CSV. "
                         "Set distortion_layout_file in config.yaml or supply it via the GUI.",
                "script": script,
            }
        layout_fwd = str(resolved_layout).replace("\\", "/")
        batch_cmd = (
            f"addpath('{scripts_dir_fwd}'); "
            f"cfg.layoutFile = '{layout_fwd}'; "
            f"cfg.exportBaseName = '{export_base}'; "
            f"measure_distortion_tags('{img_path_fwd}', cfg)"
        )
    else:
        # Generic scripts: pass image path only (they must handle headless themselves)
        batch_cmd = f"addpath('{scripts_dir_fwd}'); {script}('{img_path_fwd}')"

    cmd = [matlab_exe, "-batch", batch_cmd]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300.0)
        return {
            "source":       "matlab",
            "script":       script,
            "matlab_exe":   matlab_exe,
            "export_base":  export_base,
            "roi_preset":   roi_preset if script == "measure_sfr_slanted_edge" else None,
            "stdout":       result.stdout,
            "stderr":       result.stderr,
            "returncode":   result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "MATLAB script timed out after 300s"}
    except FileNotFoundError:
        return {"error": f"MATLAB executable not found: {matlab_exe}"}


def _get_image_dims(image_path: str) -> tuple[Optional[int], Optional[int]]:
    """Return (width, height) of an image file, or (None, None) on failure."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        pass
    try:
        import cv2
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            return img.shape[1], img.shape[0]
    except Exception:
        pass
    return None, None


def _find_matlab_exe(configured_path: str) -> Optional[str]:
    """
    Return the MATLAB executable path.
    Tries the configured path first, then searches standard install locations.
    """
    # Try configured path
    if configured_path and Path(configured_path).exists():
        return configured_path

    # Auto-discover: walk C:/Program Files/MATLAB/ for any R20xx installation
    search_root = Path("C:/Program Files/MATLAB")
    if search_root.exists():
        candidates = sorted(search_root.glob("R*/bin/matlab.exe"), reverse=True)
        if candidates:
            return str(candidates[0])   # newest version first

    return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_run(run_id: int) -> AnalysisOut:
    conn = get_conn()
    row = conn.execute("SELECT * FROM analysis_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return _row_to_out(dict(row))


def _row_to_out(row: dict) -> AnalysisOut:
    results = None
    if row.get("results_json"):
        try:
            results = json.loads(row["results_json"])
        except Exception:
            results = row["results_json"]
    return AnalysisOut(
        id=row["id"],
        capture_id=row["capture_id"],
        engine=row["engine"],
        test_id=row.get("test_id"),
        profile=row.get("profile"),
        status=row["status"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        results_json=results,
        error_msg=row.get("error_msg"),
    )
