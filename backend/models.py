"""
models.py — Pydantic request/response models for the OLB API.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class CameraStatus(BaseModel):
    id: str
    name: str
    model: str
    ip: str
    port: int
    online: bool
    firmware: Optional[str] = None
    resolution: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    mode: str = Field(..., pattern="^(QA|PIV|Research)$")
    camera_id: Optional[str] = None
    chart_type: Optional[str] = None
    rail_stop: Optional[int] = Field(None, ge=1, le=3)
    operator: Optional[str] = "Jack"
    notes: Optional[str] = None


class StepComplete(BaseModel):
    notes: Optional[str] = None


class LogEntry(BaseModel):
    message: str
    level: str = Field("info", pattern="^(info|warn|error)$")


class SessionOut(BaseModel):
    id: str
    mode: str
    camera_id: Optional[str]
    chart_type: Optional[str]
    rail_stop: Optional[int]
    operator: Optional[str]
    notes: Optional[str]
    started_at: str
    ended_at: Optional[str]
    status: str
    steps: list[dict]
    log: list[dict]


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

class CaptureRequest(BaseModel):
    session_id: Optional[str] = None
    label: Optional[str] = None
    rail_stop: Optional[int] = Field(None, ge=1, le=3)


class CaptureOut(BaseModel):
    id: str
    session_id: Optional[str]
    camera_id: str
    captured_at: str
    file_path: str
    format: str
    width: Optional[int]
    height: Optional[int]
    file_size: Optional[int]
    label: Optional[str]
    rail_stop: Optional[int]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    engine: str = Field(..., pattern="^(iqanalyzer|custom|matlab)$")
    test_id: Optional[str] = Field(None, description="Test id from /tests registry — determines script/module/profile")
    profile: Optional[str] = Field(None, description="IQ-Analyzer X profile override (iqanalyzer engine only)")
    roi_preset: str = Field("quad4", description="SFR ROI preset: quad4 | quad4c | center1 | cross5")
    layout_file: Optional[str] = Field(None, description="Tag layout CSV for measure_distortion_tags. Overrides config.yaml value.")


class AnalysisOut(BaseModel):
    id: int
    capture_id: str
    engine: str
    test_id: Optional[str] = None
    profile: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    results_json: Optional[Any]
    error_msg: Optional[str]
