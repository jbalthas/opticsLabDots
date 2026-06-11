"""
analysis/custom.py — Custom Python analysis scripts.

Runs independent IQ metrics as a cross-validation layer alongside IQ-Analyzer X.
Implements:
  - MTF / SFR estimation via the slanted-edge method (ISO 12233)
  - Basic noise characterization (SNR, standard deviation in flat regions)
  - Spatial uniformity / vignetting analysis

These results are stored independently and can be compared against
IQ-Analyzer X output for validation.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Optional

import numpy as np


def run_test(module: str, image_path: str) -> dict:
    """
    Run a single targeted analysis module for a specific test type.

    module choices: sfr | noise | uniformity | tonal | distortion
    Each returns a focused result dict matching the test's parameter definition.
    """
    img_array = _load_image(image_path)
    if img_array is None:
        return {"source": "custom", "module": module, "error": f"Could not load image: {image_path}"}

    size = {"width": int(img_array.shape[1]), "height": int(img_array.shape[0])}
    gray = _to_gray(img_array) if len(img_array.shape) == 3 else img_array.astype(np.float64)
    base: dict = {"source": "custom", "module": module, "image_size": size}

    if module == "sfr":
        try:
            return {**base, "metrics": {"mtf": _slanted_edge_mtf(gray)}}
        except Exception as exc:
            return {**base, "error": str(exc),
                    "hint": "No suitable slanted edge found. Ensure TE42-LL is in frame and correctly oriented."}

    elif module == "noise":
        return {**base, "metrics": {"noise": _noise_metrics(gray)}}

    elif module == "uniformity":
        return {**base, "metrics": {"uniformity": _uniformity_metrics(gray)}}

    elif module == "tonal":
        return {**base, "metrics": {"tonal": _tonal_metrics(gray)}}

    elif module == "distortion":
        return {
            **base,
            "note": "Dot-grid distortion detection is not yet implemented in the Python engine.",
            "hint": "Use MATLAB (measure_distortion_tags) or IQ-Analyzer X for distortion measurement.",
        }

    else:
        return {**base, "error": f"Unknown module: {module}"}


def run_all(image_path: str) -> dict:
    """
    Run all custom analysis scripts on a single image.
    Returns a dict with all metrics, or partial results with error keys.
    """
    results: dict = {"source": "custom", "metrics": {}, "errors": []}

    # Load image
    img_array = _load_image(image_path)
    if img_array is None:
        return {"source": "custom", "error": f"Could not load image: {image_path}"}

    results["image_size"] = {"width": img_array.shape[1], "height": img_array.shape[0]}
    results["channels"] = img_array.shape[2] if len(img_array.shape) == 3 else 1

    # Convert to grayscale for scalar metrics
    if len(img_array.shape) == 3:
        gray = _to_gray(img_array)
    else:
        gray = img_array.astype(np.float64)

    # --- Noise characterization ---
    try:
        noise = _noise_metrics(gray)
        results["metrics"]["noise"] = noise
    except Exception as exc:
        results["errors"].append(f"noise: {exc}")

    # --- Uniformity / vignetting ---
    try:
        uniformity = _uniformity_metrics(gray)
        results["metrics"]["uniformity"] = uniformity
    except Exception as exc:
        results["errors"].append(f"uniformity: {exc}")

    # --- Slanted-edge MTF (requires a suitable image) ---
    try:
        mtf = _slanted_edge_mtf(gray)
        results["metrics"]["mtf"] = mtf
    except Exception as exc:
        # MTF analysis fails gracefully if no suitable edge is found
        results["errors"].append(f"mtf: {exc}")

    # --- Tonal / dynamic range estimation ---
    try:
        tonal = _tonal_metrics(gray)
        results["metrics"]["tonal"] = tonal
    except Exception as exc:
        results["errors"].append(f"tonal: {exc}")

    return results


# ---------------------------------------------------------------------------
# Image loader
# ---------------------------------------------------------------------------

def _load_image(path: str) -> Optional[np.ndarray]:
    """Load image as float64 numpy array (0–255 range, H×W×C or H×W)."""
    try:
        from PIL import Image
        img = Image.open(path)
        return np.array(img, dtype=np.float64)
    except Exception:
        try:
            import cv2
            arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            return arr.astype(np.float64) if arr is not None else None
        except Exception:
            return None


def _to_gray(rgb: np.ndarray) -> np.ndarray:
    """BT.601 luma from RGB float array."""
    return 0.2989 * rgb[:, :, 0] + 0.5870 * rgb[:, :, 1] + 0.1140 * rgb[:, :, 2]


# ---------------------------------------------------------------------------
# Noise metrics
# ---------------------------------------------------------------------------

def _noise_metrics(gray: np.ndarray) -> dict:
    """
    Estimate temporal noise from a uniform region near the image center.
    For a single-frame image we use a flat-region proxy:
      - Find the 10% of pixels closest to the median (assumed flat field)
      - Report standard deviation as noise proxy, SNR = mean / std
    """
    flat = gray[(gray > np.percentile(gray, 45)) & (gray < np.percentile(gray, 55))]
    if flat.size < 100:
        flat = gray.ravel()

    mean_val = float(np.mean(flat))
    std_val  = float(np.std(flat))
    snr_db   = float(20 * np.log10(mean_val / std_val)) if std_val > 0 else 0.0

    return {
        "mean_dn":    round(mean_val, 2),
        "std_dn":     round(std_val, 3),
        "snr_db":     round(snr_db, 2),
        "dynamic_range_stops": round(np.log2(255.0 / std_val), 2) if std_val > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Uniformity / vignetting
# ---------------------------------------------------------------------------

def _uniformity_metrics(gray: np.ndarray) -> dict:
    """
    Divide image into a 3×3 grid and report mean luminance in each zone.
    Also reports corner-to-center ratio (vignetting proxy).
    """
    H, W = gray.shape
    ys = np.array_split(np.arange(H), 3)
    xs = np.array_split(np.arange(W), 3)

    zones: dict = {}
    names = [["TL","TC","TR"], ["ML","MC","MR"], ["BL","BC","BR"]]
    for row_i, y_idx in enumerate(ys):
        for col_i, x_idx in enumerate(xs):
            patch = gray[np.ix_(y_idx, x_idx)]
            zone_name = names[row_i][col_i]
            zones[zone_name] = round(float(np.mean(patch)), 2)

    center = zones.get("MC", 1.0)
    corners = [zones.get(c, 0) for c in ("TL", "TR", "BL", "BR")]
    corner_ratio = round(float(np.mean(corners)) / center, 4) if center > 0 else 0.0

    return {
        "zones_mean_dn": zones,
        "corner_center_ratio": corner_ratio,
        "uniformity_pct": round(corner_ratio * 100, 1),
    }


# ---------------------------------------------------------------------------
# Slanted-edge MTF (ISO 12233 simplified)
# ---------------------------------------------------------------------------

def _slanted_edge_mtf(gray: np.ndarray) -> dict:
    """
    Simplified slanted-edge MTF estimation.
    Detects the strongest near-vertical edge in the image, extracts an ESF,
    differentiates to get LSF, then computes the MTF via FFT.

    Returns MTF50 (cycles/pixel) as the primary metric.
    If no suitable edge is found, raises ValueError.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError("opencv-python required for MTF analysis")

    img_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    edges = cv2.Canny(img_u8, 50, 150)

    # Find the largest connected edge segment
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No edges found in image")

    # Pick the longest contour
    longest = max(contours, key=lambda c: len(c))
    if len(longest) < 50:
        raise ValueError("Edge too short for reliable MTF estimation")

    # Extract ROI around edge
    x, y, w, h = cv2.boundingRect(longest)
    margin = 20
    roi = gray[
        max(0, y-margin):min(gray.shape[0], y+h+margin),
        max(0, x-margin):min(gray.shape[1], x+w+margin)
    ]

    if roi.size < 100:
        raise ValueError("ROI too small")

    # Compute ESF by averaging rows of ROI (assumes near-vertical edge)
    esf = np.mean(roi, axis=0)

    # LSF = derivative of ESF
    lsf = np.diff(esf)
    lsf -= np.mean(lsf)

    # MTF = |FFT(LSF)| normalized
    mtf = np.abs(np.fft.rfft(lsf))
    mtf /= (mtf[0] if mtf[0] > 0 else 1.0)

    freqs = np.fft.rfftfreq(len(lsf))

    # Find MTF50 (frequency where MTF = 0.5)
    mtf50 = _find_mtf_at_threshold(freqs, mtf, 0.5)
    mtf30 = _find_mtf_at_threshold(freqs, mtf, 0.3)

    return {
        "mtf50_cy_px":    round(float(mtf50), 4) if mtf50 else None,
        "mtf30_cy_px":    round(float(mtf30), 4) if mtf30 else None,
        "nyquist_cy_px":  0.5,
        "note": "Simplified single-frame slanted-edge estimate. Use IQ-Analyzer X for ISO-compliant results.",
    }


def _find_mtf_at_threshold(freqs: np.ndarray, mtf: np.ndarray, threshold: float) -> Optional[float]:
    """Interpolate the spatial frequency where MTF crosses a threshold."""
    for i in range(len(mtf) - 1):
        if mtf[i] >= threshold >= mtf[i+1]:
            # Linear interpolation
            slope = (mtf[i+1] - mtf[i]) / (freqs[i+1] - freqs[i])
            return freqs[i] + (threshold - mtf[i]) / slope if slope != 0 else freqs[i]
    return None


# ---------------------------------------------------------------------------
# Tonal / dynamic range
# ---------------------------------------------------------------------------

def _tonal_metrics(gray: np.ndarray) -> dict:
    """
    Compute basic tonal statistics: histogram spread, clipped pixel fraction,
    and a rough gamma estimate from the histogram centroid vs. linear midpoint.
    """
    hist, bins = np.histogram(gray.ravel(), bins=256, range=(0, 256))
    total = gray.size

    clipped_low  = int(np.sum(gray < 5))
    clipped_high = int(np.sum(gray > 250))

    # Midpoint of histogram by CDF
    cdf = np.cumsum(hist) / total
    median_bin = int(np.searchsorted(cdf, 0.5))

    return {
        "min_dn":         round(float(np.min(gray)), 1),
        "max_dn":         round(float(np.max(gray)), 1),
        "mean_dn":        round(float(np.mean(gray)), 2),
        "median_dn":      float(median_bin),
        "clipped_low_pct":  round(100.0 * clipped_low / total, 3),
        "clipped_high_pct": round(100.0 * clipped_high / total, 3),
    }
