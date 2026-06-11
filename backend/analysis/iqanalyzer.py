"""
analysis/iqanalyzer.py — IQ-Analyzer X integration.

Two integration modes (configured in config.yaml):
  1. Hot Folder  — copy image to iqanalyzer_input_dir; watch iqanalyzer_output_dir
                   for result XML/CSV. Reliable, no CLI dependency.
  2. CLI         — invoke IQ-Analyzer X executable with --batch flag.
                   Faster, but requires knowing the installed CLI syntax.

Mode 1 (Hot Folder) is the default and preferred method.
Set iqanalyzer_exe in config.yaml to enable CLI mode.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Hot Folder integration
# ---------------------------------------------------------------------------

def submit_to_hot_folder(
    image_path: str,
    input_dir: str,
    output_dir: str,
    profile: Optional[str] = None,
    timeout: float = 120.0,
    poll_interval: float = 2.0,
) -> dict:
    """
    Copy image into IQ-Analyzer X hot folder and wait for results.

    IQ-Analyzer X monitors the hot folder and processes any new image.
    Results may appear in output_dir, a 'Results' subfolder of input_dir,
    or alongside the input image — we scan all candidate locations.

    Returns a dict with parsed results on success, or an error key on failure.
    """
    src = Path(image_path)
    if not src.exists():
        return {"error": f"Image not found: {image_path}"}

    in_dir  = Path(input_dir)
    out_dir = Path(output_dir)
    in_dir.mkdir(parents=True, exist_ok=True)

    # Candidate result locations IQ-Analyzer X may write to
    result_search_dirs = [
        out_dir,
        in_dir / "Results",
        in_dir / "results",
        in_dir / "Output",
        in_dir,
    ]

    # Copy image into hot folder
    dest = in_dir / src.name
    shutil.copy2(src, dest)

    stem = src.stem
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for search_dir in result_search_dirs:
            if not search_dir.exists():
                continue
            for result_file in search_dir.iterdir():
                if result_file.stem == stem and result_file.suffix.lower() in (".xml", ".csv", ".txt"):
                    results = _parse_result_file(result_file)
                    results["result_file"] = str(result_file)
                    results["result_dir"]  = str(search_dir)
                    return results
        time.sleep(poll_interval)

    # Helpful diagnostic: list what IS in the hot folder after timeout
    found_files = []
    for d in result_search_dirs:
        if d.exists():
            found_files += [str(f) for f in d.iterdir() if f.is_file()]

    return {
        "error": f"IQ-Analyzer X did not produce results within {timeout:.0f}s",
        "hot_folder": str(in_dir),
        "scanned_dirs": [str(d) for d in result_search_dirs if d.exists()],
        "files_found": found_files[:20],
        "tip": "Confirm IQ-Analyzer X is running and the hot folder is active (Jobs tab should show activity).",
    }


def _parse_result_file(path: Path) -> dict:
    """Parse IQ-Analyzer X XML or CSV output into a Python dict."""
    if path.suffix.lower() == ".xml":
        return _parse_iqanalyzer_xml(path)
    elif path.suffix.lower() == ".csv":
        return _parse_iqanalyzer_csv(path)
    return {"error": f"Unknown result format: {path.suffix}"}


def _parse_iqanalyzer_xml(path: Path) -> dict:
    """Parse IQ-Analyzer X XML result file."""
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
        results: dict = {"source": "iqanalyzer", "format": "xml", "metrics": {}}

        # Walk all elements and collect measurement values
        for elem in root.iter():
            if elem.text and elem.text.strip():
                key = elem.tag
                val = elem.text.strip()
                # Try numeric conversion
                try:
                    results["metrics"][key] = float(val)
                except ValueError:
                    results["metrics"][key] = val

        return results
    except ET.ParseError as exc:
        return {"error": f"XML parse error: {exc}", "raw": path.read_text(errors="replace")}


def _parse_iqanalyzer_csv(path: Path) -> dict:
    """Parse IQ-Analyzer X CSV result file (key,value pairs)."""
    try:
        metrics: dict = {}
        for line in path.read_text(errors="replace").splitlines():
            parts = line.strip().split(",", 1)
            if len(parts) == 2:
                key, val = parts[0].strip(), parts[1].strip()
                try:
                    metrics[key] = float(val)
                except ValueError:
                    metrics[key] = val
        return {"source": "iqanalyzer", "format": "csv", "metrics": metrics}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# CLI integration (optional)
# ---------------------------------------------------------------------------

def run_cli(
    iqanalyzer_exe: str,
    image_path: str,
    profile: Optional[str] = None,
    output_dir: Optional[str] = None,
    timeout: float = 120.0,
) -> dict:
    """
    Run IQ-Analyzer X in batch/CLI mode.

    CLI syntax (from IE documentation):
        IQ-Analyzer-X.exe --batch --input <image> [--profile <profile>] [--output <dir>]

    Returns parsed results dict or error.
    """
    exe = Path(iqanalyzer_exe)
    if not exe.exists():
        return {"error": f"IQ-Analyzer X executable not found: {iqanalyzer_exe}"}

    cmd = [str(exe), "--batch", "--input", image_path]
    if profile:
        cmd += ["--profile", profile]
    if output_dir:
        cmd += ["--output", output_dir]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return {
                "error": f"IQ-Analyzer X exited with code {result.returncode}",
                "stderr": result.stderr,
                "stdout": result.stdout,
            }
        return {
            "source": "iqanalyzer_cli",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"IQ-Analyzer X CLI timed out after {timeout:.0f}s"}
    except Exception as exc:
        return {"error": str(exc)}
