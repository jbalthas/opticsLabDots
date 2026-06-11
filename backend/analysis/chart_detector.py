"""
analysis/chart_detector.py — Computer vision chart detection and identification.

Detects whether a test chart is present in a capture image and identifies
which chart from the lab inventory it is, using rule-based feature extraction.

Pipeline
--------
1. Find the largest bright rectangular region (chart presence)
2. Extract discriminating features from that region
3. Apply rule-based classifier to name the chart
4. Return chart_id, confidence, and recommended test IDs

No training data required — purely visual fingerprints of each known chart.
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Chart <-> test mapping (chart IDs match charts.py and tests.py registries)
# ---------------------------------------------------------------------------

_CHART_TESTS: dict[str, list[str]] = {
    "te251":      ["distortion"],
    "te42_ll":    ["sfr_mtf"],
    "te264":      ["oecf"],
    "flat_field": ["noise", "uniformity"],
}

_CHART_NAMES: dict[str, str] = {
    "te251":      "IE TE251 — Distortion (ISO 17850)",
    "te42_ll":    "IE TE42-LL — Slanted Edge MTF (ISO 12233)",
    "te264":      "IE TE264 — OECF Step Wedge (ISO 14524)",
    "flat_field": "Flat Field Source",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_chart(image_path: str) -> dict:
    """
    Detect and identify the test chart in an image.

    Returns
    -------
    dict with keys:
        present            bool
        chart_id           str | None   — matches charts.py id
        chart_name         str | None
        confidence         float        — 0.0–1.0
        recommended_tests  list[str]    — test ids from tests.py registry
        features           dict         — diagnostic breakdown (all numeric)
    """
    img = cv2.imread(image_path)
    if img is None:
        return _no_chart("Could not read image file")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1 — locate the bright chart region
    chart_mask, bbox = _detect_chart_region(gray, w, h)
    if chart_mask is None:
        return _no_chart("No bright rectangular region found — chart may not be present")

    x, y, bw, bh = bbox
    roi_gray = gray[y : y + bh, x : x + bw]

    # 2 — extract features
    features = _extract_features(roi_gray)
    features["chart_bbox"] = [int(x), int(y), int(bw), int(bh)]
    features["chart_area_pct"] = round(100.0 * (bw * bh) / (w * h), 1)

    # 3 — classify
    chart_id, confidence = _classify(features)

    return {
        "present":           True,
        "chart_id":          chart_id,
        "chart_name":        _CHART_NAMES.get(chart_id) if chart_id else "Unrecognized chart",
        "confidence":        round(confidence, 2),
        "recommended_tests": _CHART_TESTS.get(chart_id, []) if chart_id else [],
        "features":          features,
    }


# ---------------------------------------------------------------------------
# Step 1 — chart region detection
# ---------------------------------------------------------------------------

def _detect_chart_region(
    gray: np.ndarray, w: int, h: int
) -> tuple[Optional[np.ndarray], Optional[tuple[int, int, int, int]]]:
    """Find the largest bright rectangular region in the image."""

    # Otsu threshold finds the natural split between chart (bright) and background (dark)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morphological closing fills internal structure (crosses, patches) so we get one solid blob
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    # Reject if too small (< 15% of total image area)
    if area < 0.15 * w * h:
        return None, None

    bx, by, bw, bh = cv2.boundingRect(largest)

    # Reject extreme aspect ratios
    ar = bw / max(bh, 1)
    if ar < 0.35 or ar > 3.5:
        return None, None

    mask = np.zeros_like(gray)
    cv2.drawContours(mask, [largest], -1, 255, cv2.FILLED)
    return mask, (bx, by, bw, bh)


# ---------------------------------------------------------------------------
# Step 2 — feature extraction
# ---------------------------------------------------------------------------

def _extract_features(roi: np.ndarray) -> dict:
    """Compute discriminating features from the chart ROI (grayscale)."""
    h, w = roi.shape
    area = h * w

    # ── Brightness features ──────────────────────────────────────────────
    white_ratio = float(np.mean(roi > 200))          # fraction very bright
    mean_brightness = float(np.mean(roi)) / 255.0
    uniformity_std = float(np.std(roi.astype(np.float32))) / 255.0

    # ── Edge / line features ─────────────────────────────────────────────
    edges = cv2.Canny(roi, 40, 120)

    min_line_len = max(15, w // 12)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=50,
        minLineLength=min_line_len,
        maxLineGap=8,
    )

    h_lines = v_lines = diag_lines = 0
    if lines is not None:
        for seg in lines:
            x1, y1, x2, y2 = seg[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 18 or angle > 162:
                h_lines += 1
            elif 72 < angle < 108:
                v_lines += 1
            else:
                diag_lines += 1

    total_lines = h_lines + v_lines + diag_lines
    grid_ratio = (h_lines + v_lines) / max(total_lines, 1)
    diag_ratio = diag_lines / max(total_lines, 1)

    # ── Solid dark blob count (fiducial squares) ─────────────────────────
    # Ignore a 5% margin (avoids picking up the chart border itself)
    my = max(1, int(0.05 * h))
    mx = max(1, int(0.05 * w))
    interior = roi[my : h - my, mx : w - mx]

    _, dark = cv2.threshold(interior, 40, 255, cv2.THRESH_BINARY_INV)
    num_lbl, _, stats, _ = cv2.connectedComponentsWithStats(dark)

    interior_area = interior.shape[0] * interior.shape[1]
    black_squares = 0
    for i in range(1, num_lbl):
        blob_area = int(stats[i, cv2.CC_STAT_AREA])
        blob_w = int(stats[i, cv2.CC_STAT_WIDTH])
        blob_h = int(stats[i, cv2.CC_STAT_HEIGHT])
        # Fiducial: 0.05%–4% of chart area, roughly square, well-filled
        if 0.0005 * interior_area < blob_area < 0.04 * interior_area:
            ar = blob_w / max(blob_h, 1)
            fill = blob_area / max(blob_w * blob_h, 1)
            if 0.35 < ar < 2.8 and fill > 0.45:
                black_squares += 1

    # ── Gradient monotonicity (step wedge / OECF) ───────────────────────
    # Average each column, smooth, measure how monotone the result is
    col_means = np.mean(roi.astype(np.float32), axis=0)
    k = max(3, len(col_means) // 20)
    if k % 2 == 0:
        k += 1
    smoothed = np.convolve(col_means, np.ones(k) / k, mode="valid")
    diffs = np.diff(smoothed)
    pos_frac = float(np.mean(diffs > 2))    # ignores tiny noise
    neg_frac = float(np.mean(diffs < -2))
    gradient_monotonicity = max(pos_frac, neg_frac)

    return {
        "white_ratio":            round(white_ratio, 3),
        "mean_brightness":        round(mean_brightness, 3),
        "uniformity_std":         round(uniformity_std, 3),
        "h_lines":                int(h_lines),
        "v_lines":                int(v_lines),
        "diag_lines":             int(diag_lines),
        "grid_ratio":             round(grid_ratio, 3),
        "diag_ratio":             round(diag_ratio, 3),
        "black_square_count":     int(black_squares),
        "gradient_monotonicity":  round(gradient_monotonicity, 3),
    }


# ---------------------------------------------------------------------------
# Step 3 — rule-based classifier
# ---------------------------------------------------------------------------

def _classify(f: dict) -> tuple[Optional[str], float]:
    """
    Map feature vector to (chart_id, confidence) using explicit rules.

    Rules are ordered by specificity: most distinctive charts first.
    Confidence is an additive score capped at 1.0.
    """
    scores: dict[str, float] = {}

    # ── Flat field ───────────────────────────────────────────────────────
    # Very uniform, very bright, no structure
    ff = 0.0
    if f["uniformity_std"] < 0.06:
        ff += 0.5
    elif f["uniformity_std"] < 0.10:
        ff += 0.3
    if f["white_ratio"] > 0.70:
        ff += 0.3
    if f["black_square_count"] == 0 and f["diag_lines"] < 10:
        ff += 0.2
    scores["flat_field"] = min(ff, 1.0)

    # ── TE251 (cross-grid distortion) ────────────────────────────────────
    # High white ratio, regular H+V grid, ~4 solid black fiducials
    te251 = 0.0
    if f["white_ratio"] > 0.70:
        te251 += 0.30
    elif f["white_ratio"] > 0.55:
        te251 += 0.15
    if f["grid_ratio"] > 0.75:
        te251 += 0.25
    elif f["grid_ratio"] > 0.60:
        te251 += 0.12
    if 2 <= f["black_square_count"] <= 7:
        te251 += 0.30
    if f["h_lines"] > 15 and f["v_lines"] > 15:
        te251 += 0.15
    scores["te251"] = min(te251, 1.0)

    # ── TE264 (OECF step wedge) ──────────────────────────────────────────
    # Column/row means vary monotonically; medium white ratio; few fiducials
    te264 = 0.0
    if f["gradient_monotonicity"] > 0.80:
        te264 += 0.50
    elif f["gradient_monotonicity"] > 0.65:
        te264 += 0.30
    if 0.15 < f["white_ratio"] < 0.80:
        te264 += 0.20
    if f["grid_ratio"] < 0.55:
        te264 += 0.15
    if f["black_square_count"] < 3:
        te264 += 0.15
    scores["te264"] = min(te264, 1.0)

    # ── TE42-LL (slanted edge MTF) ───────────────────────────────────────
    # Multiple edges at angles, lower white ratio, few fiducials
    te42 = 0.0
    if f["diag_ratio"] > 0.25:
        te42 += 0.30
    elif f["diag_ratio"] > 0.15:
        te42 += 0.15
    if 0.25 < f["white_ratio"] < 0.80:
        te42 += 0.20
    if f["black_square_count"] < 3:
        te42 += 0.15
    if f["grid_ratio"] < 0.70:
        te42 += 0.15
    if f["diag_lines"] > 10:
        te42 += 0.20
    scores["te42_ll"] = min(te42, 1.0)

    if not scores:
        return None, 0.0

    best = max(scores, key=lambda k: scores[k])
    conf = scores[best]

    # Require minimum confidence threshold to name a chart
    if conf < 0.38:
        return None, conf

    return best, conf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_chart(reason: str = "") -> dict:
    return {
        "present":           False,
        "chart_id":          None,
        "chart_name":        None,
        "confidence":        0.0,
        "recommended_tests": [],
        "features":          {"reason": reason},
    }
