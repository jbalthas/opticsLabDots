"""
routers/charts.py — Chart reference library.

Serves chart metadata and images for the lab's test chart inventory.
Each chart entry maps to:
  - The scripts that require it
  - Physical setup requirements
  - Applicable ISO standards
  - Image file on disk (actual lab photo)
"""

from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/charts", tags=["charts"])

# ---------------------------------------------------------------------------
# Chart registry
# ---------------------------------------------------------------------------

_CHARTS: list[dict] = [
    {
        "id":          "te42_ll",
        "name":        "IE TE42-LL",
        "full_name":   "Image Engineering TE42-LL Low-Luminance Transmissive Chart",
        "type":        "SFR / Slanted Edge (MTF)",
        "scripts":     ["measure_sfr_slanted_edge"],
        "standards":   ["ISO 12233 (eSFR)", "EMVA 1288"],
        "description": (
            "Transmissive low-luminance chart with multiple slanted-edge patches "
            "distributed across the field of view. Used to measure spatial frequency "
            "response (MTF) and resolve spatial resolution at different field positions."
        ),
        "setup": {
            "lighting_mode": "Transmissive — LED backlight panel ONLY",
            "softboxes":     "OFF — not used with transmissive charts",
            "tv_position":   "Position D (stored, out of optical path)",
            "primary_stop":  2,
            "valid_stops":   [1, 2, 3],
            "alignment":     "Chart centered on optical axis. Self-leveling laser to chart center.",
            "notes": (
                "Ensure slanted edges are not parallel to sensor rows/columns — "
                "a slight (~5°) rotation from vertical is built into the chart. "
                "Ceiling lights OFF. Verify illuminance uniformity ±3% before capture."
            ),
        },
        "roi_presets": {
            "quad4":   "4 corner patches — standard field uniformity (default)",
            "quad4c":  "4 corners + center — 5 patches, recommended for fisheye",
            "center1": "Center patch only — quick single-point MTF",
            "cross5":  "Center + 4 cardinal mid-field — cross pattern",
        },
        "image_paths": [
            "C:/WORK/HIF/Optics lab/Charts/TE042_LL.jpg",
            "C:/WORK/HIF/Optics lab/Optics Lab Photos/Optics Lab Photos/Sampled Chart TE42.jpg",
            "C:/WORK/HIF/Optics lab/Optics Lab Photos/Optics Lab Photos/TE42_true.jpg",
        ],
    },
    {
        "id":          "te251",
        "name":        "IE TE251",
        "full_name":   "Image Engineering TE251 Distortion Chart",
        "type":        "Geometric Distortion",
        "scripts":     ["measure_distortion_tags"],
        "standards":   ["ISO 17850", "EMVA 1288"],
        "description": (
            "Regular dot-grid chart for measuring geometric distortion, "
            "including barrel, pincushion, and mustache (wave) distortion. "
            "Each dot is a precisely positioned fiducial detected by the measurement script."
        ),
        "setup": {
            "lighting_mode": "Reflective — softboxes at 45°, equal illumination",
            "softboxes":     "ON at floor registration marks, 10-min warm-up",
            "tv_position":   "Position D (stored, out of optical path)",
            "primary_stop":  2,
            "valid_stops":   [1, 2, 3],
            "alignment": (
                "Full chart must fill the frame without vignetting the dot grid. "
                "Camera yaw aligned to chart center. Level pitch/roll to ±0.05°."
            ),
            "notes": (
                "Chart must be flat — any bow will alias as distortion. "
                "Use pin registration system. Illuminance uniformity ±3% critical."
            ),
        },
        "roi_presets": None,   # not applicable for distortion
        "image_paths": [
            "C:/WORK/HIF/Optics lab/Charts/te251_updated.jpg",
            "C:/WORK/HIF/Optics lab/Charts/te251.jpg",
        ],
    },
    {
        "id":          "te264",
        "name":        "IE TE264",
        "full_name":   "Image Engineering TE264 OECF / Tonal Response Chart",
        "type":        "OECF / Tonal Response",
        "scripts":     [],
        "standards":   ["ISO 14524"],
        "description": (
            "Transmissive step-wedge chart with precisely calibrated neutral-density patches "
            "spanning the full dynamic range of the sensor. Used to characterize the "
            "opto-electronic conversion function (OECF) — gamma curve, black level, "
            "saturation point, and dynamic range in stops."
        ),
        "setup": {
            "lighting_mode": "Transmissive — LED backlight panel ONLY",
            "softboxes":     "OFF — not used with transmissive charts",
            "tv_position":   "Position D (stored, out of optical path)",
            "primary_stop":  2,
            "valid_stops":   [1, 2, 3],
            "alignment":     "Chart centered on optical axis. All ND patches fully visible in frame with no vignetting.",
            "notes": (
                "LED panel must warm up ≥10 min before capture. Verify illuminance uniformity ±3% "
                "across chart face. Camera MUST be in fully manual mode — AGC and auto-exposure OFF. "
                "Set shutter to avoid any motion blur from panel flicker."
            ),
        },
        "roi_presets": None,
        "image_paths": [
            "C:/WORK/HIF/Optics lab/Charts/TE264_intro.jpg",
        ],
    },
    {
        "id":          "flat_field",
        "name":        "Flat Field",
        "full_name":   "Flat-Field Source — Integrating Sphere or Diffuse LED Panel",
        "type":        "Noise / Uniformity",
        "scripts":     [],
        "standards":   ["EMVA 1288", "ISO 15739"],
        "description": (
            "Spatially uniform, featureless illumination source — integrating sphere output port "
            "or a large-area diffuse LED panel. Provides a uniform scene for noise "
            "characterization (SNR, FPN proxy, dynamic range) and uniformity / vignetting analysis."
        ),
        "setup": {
            "lighting_mode": "Integrating sphere output port OR diffuse LED panel facing camera",
            "softboxes":     "OFF",
            "tv_position":   "Position D (stored, out of optical path)",
            "primary_stop":  2,
            "valid_stops":   [1, 2, 3],
            "alignment":     "Uniform illumination must fill the entire sensor area. No edges or features in frame.",
            "notes": (
                "For EMVA 1288 noise: capture a sequence at multiple exposure levels. "
                "For uniformity: single capture at working illuminance. "
                "For FPN: dark frame subtraction required — capture with lens cap at same exposure."
            ),
        },
        "roi_presets": None,
        "image_paths": [],
    },
]

# Build lookup by id and by script name
_BY_ID:     dict[str, dict] = {c["id"]: c for c in _CHARTS}
_BY_SCRIPT: dict[str, list[dict]] = {}
for _c in _CHARTS:
    for _s in _c["scripts"]:
        _BY_SCRIPT.setdefault(_s, []).append(_c)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_charts() -> list[dict]:
    """List all chart entries (without image data)."""
    return [_strip_image_paths(c) for c in _CHARTS]


@router.get("/for-script/{script_name}")
def charts_for_script(script_name: str) -> list[dict]:
    """Return chart(s) required by a specific MATLAB script."""
    charts = _BY_SCRIPT.get(script_name, [])
    return [_strip_image_paths(c) for c in charts]


@router.get("/{chart_id}")
def get_chart(chart_id: str) -> dict:
    c = _BY_ID.get(chart_id)
    if not c:
        raise HTTPException(status_code=404, detail="Chart not found")
    return _strip_image_paths(c)


@router.get("/{chart_id}/image")
def get_chart_image(chart_id: str, index: int = 0) -> FileResponse:
    """Serve the chart's reference photo."""
    c = _BY_ID.get(chart_id)
    if not c:
        raise HTTPException(status_code=404, detail="Chart not found")

    paths = c.get("image_paths", [])
    # Try the requested index, fall back to any available image
    candidates = paths[index:] + paths[:index]
    for p in candidates:
        path = Path(p)
        if path.exists():
            return FileResponse(str(path), media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Chart image not found on disk")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _strip_image_paths(c: dict) -> dict:
    """Return chart dict without internal file paths (replaced with API URLs)."""
    out = {k: v for k, v in c.items() if k != "image_paths"}
    out["image_url"]   = f"/charts/{c['id']}/image"
    out["has_image"]   = any(Path(p).exists() for p in c.get("image_paths", []))
    return out
