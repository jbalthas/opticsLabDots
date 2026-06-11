"""
routers/tests.py — IQ measurement test registry.

Each test maps a named measurement type to:
  - The parameter(s) being measured
  - Applicable ISO / EMVA standards
  - The required chart (references /charts registry by id)
  - Available engines: matlab script name, iqanalyzer profile, custom Python module

Every test is intended to be runnable with all three engines.
Where a MATLAB script does not yet exist, engines.matlab is None.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/tests", tags=["tests"])

# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

_TESTS: list[dict] = [
    {
        "id":        "sfr_mtf",
        "name":      "Spatial Resolution (MTF / SFR)",
        "parameter": (
            "Spatial frequency response — MTF50, MTF20, MTF at Nyquist "
            "in cycles/pixel and line-widths/picture-height (lw/ph)"
        ),
        "standards": ["ISO 12233 (eSFR)", "EMVA 1288"],
        "chart_id":  "te42_ll",
        "engines": {
            "matlab":     {
                "script":      "measure_sfr_slanted_edge",
                "roi_presets": ["quad4", "quad4c", "center1", "cross5"],
                "description": (
                    "Slanted-edge SFR / MTF (ISO 12233 eSFR). Supplies image path, "
                    "standardized ROI positions, and export base name automatically. "
                    "Outputs: _summary.csv, per-ROI MTF curves, ESF/LSF profiles, diagnostic PNGs."
                ),
            },
            "iqanalyzer": {"profile": "sfr"},
            "custom":     {"module": "sfr"},
        },
    },
    {
        "id":        "distortion",
        "name":      "Geometric Distortion",
        "parameter": (
            "Barrel, pincushion, and mustache (wave) distortion "
            "expressed as % of image height at each field position"
        ),
        "standards": ["ISO 17850", "EMVA 1288"],
        "chart_id":  "te251",
        "engines": {
            "matlab":     {
                "script":      "measure_distortion_tags",
                "description": (
                    "Geometric distortion via AprilTag homography residuals (ISO 17850 proxy). "
                    "Detects all dot/tag positions and computes per-point displacement vectors. "
                    "Outputs: _summary.csv, per-point residuals, diagnostic PNG."
                ),
            },
            "iqanalyzer": {"profile": "distortion"},
            "custom":     {"module": "distortion"},
        },
    },
    {
        "id":        "oecf",
        "name":      "Tonal Response (OECF)",
        "parameter": (
            "Opto-electronic conversion function — gamma curve, "
            "black point, saturation point, dynamic range in stops"
        ),
        "standards": ["ISO 14524"],
        "chart_id":  "te264",
        "engines": {
            "matlab":     None,   # MATLAB script not yet authored for this test
            "iqanalyzer": {"profile": "oecf"},
            "custom":     {"module": "tonal"},
        },
    },
    {
        "id":        "noise",
        "name":      "Noise Characterization",
        "parameter": (
            "Temporal noise (σ DN), signal-to-noise ratio (dB), "
            "dynamic range (stops), fixed-pattern noise proxy — per EMVA 1288"
        ),
        "standards": ["EMVA 1288", "ISO 15739"],
        "chart_id":  "flat_field",
        "engines": {
            "matlab":     None,
            "iqanalyzer": {"profile": "noise"},
            "custom":     {"module": "noise"},
        },
    },
    {
        "id":        "uniformity",
        "name":      "Uniformity / Vignetting",
        "parameter": (
            "Flat-field luminance uniformity — 3×3 zone luminance map, "
            "corner/center ratio (%), radial shading profile"
        ),
        "standards": ["EMVA 1288"],
        "chart_id":  "flat_field",
        "engines": {
            "matlab":     None,
            "iqanalyzer": {"profile": "uniformity"},
            "custom":     {"module": "uniformity"},
        },
    },
]

_BY_ID: dict[str, dict] = {t["id"]: t for t in _TESTS}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_tests() -> list[dict]:
    """List all available IQ measurement tests."""
    return _TESTS


@router.get("/{test_id}")
def get_test(test_id: str) -> dict:
    t = _BY_ID.get(test_id)
    if not t:
        raise HTTPException(status_code=404, detail="Test not found")
    return t
