# USGS Optics Lab Bench (OLB)

Tools for the **USGS Camera and Imaging Systems Evaluation Laboratory** — session-managed QA data collection, camera control, image analysis, and PIV algorithm validation.

---

## Repository Contents

| Path | Description |
|---|---|
| `backend/` | FastAPI server — sessions, cameras, captures, analysis |
| `frontend/index.html` | OLB web UI (Alpine.js + Chart.js) |
| `piv_ground_truth.html` | Standalone PIV ground truth generator |
| `config.yaml` | Server, lab paths, and camera registry |
| `data/` | SQLite database and captured images |
| `requirements.txt` | Python dependencies |
| `run.bat` | One-click launch on Windows |

---

## OLB Server

A local FastAPI application that enforces the lab's mandatory QA protocols, manages measurement sessions, drives cameras, and routes image data to IQ-Analyzer X and MATLAB.

### Quick Start

```bat
run.bat
```

Or manually:

```bash
pip install -r requirements.txt
python backend/main.py
```

The UI is served at `http://localhost:8000`.  
API docs at `http://localhost:8000/docs`.

### API Modules

| Router | Prefix | Purpose |
|---|---|---|
| Sessions | `/sessions` | Create/close QA, PIV, and Research sessions; enforces the 13-step setup sequence |
| Cameras | `/cameras` | Registry of configured cameras; live status |
| Captures | `/captures` | Trigger and store image captures; filename follows lab naming convention |
| Analysis | `/analysis` | Chart detection, IQ-Analyzer X hand-off, custom MTF/profile extraction |
| Charts | `/charts` | Test chart tracking |
| Tests | `/tests` | Structured test runs against cameras |

### Configuration (`config.yaml`)

```yaml
server:
  host: localhost
  port: 8000

lab:
  data_dir: data
  iqanalyzer_input_dir: ...   # IQ-Analyzer X hot folder
  matlab_scripts_dir: ...

cameras:
  - id: vivotek_it9388
    driver: vivotek
    ip: 192.168.13.101
    ...
```

> **Security note:** `config.yaml` contains camera credentials. Do not commit this file to a public repository. Add it to `.gitignore` if this repo becomes public.

### Data Layout

```
data/
  olb.db              — SQLite: sessions, captures, test runs
  captures/           — JPEG captures + CSV analysis results
```

Capture filenames follow the lab naming convention:
`YYYYMMDD_HHMMSS_[driver]_[model]_[session_id_prefix].jpg`

---

## PIV Ground Truth Tool

`piv_ground_truth.html` — open directly in Chrome or Edge, no server required.

Displays a synthetic particle field moving at a precisely known velocity so you can compare your PIV system's measured output against a mathematically correct ground truth.

### Features

- **Flow control** — Vx / Vy in m/s; turbulence intensity (±m/s, disk-uniform)
- **Particle parameters** — count, min/max diameter (px), brightness; Gaussian PSF rendering
- **Obstacle** — click to place a circular body; flow deflects using the exact irrotational doublet (potential flow) solution
- **Seed control** — reproducible particle fields; record seed for inter-run comparison
- **Scale calibration** — enter TV physical size and resolution; computes px/mm (X and Y separately)
- **Validation readout** — ground truth speed vs. your PIV measurement; signed error and % error (color-coded)

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `H` | Toggle control panel |
| `P` | Pause / resume |
| `F` | Fullscreen |
| `R` | Re-seed |
| `Esc` | Exit obstacle placement |

### USGS Lab TV Defaults

| Setting | Value |
|---|---|
| TV width | 1543.05 mm |
| TV height | 863.6 mm |
| Resolution | 1920 × 1080 px |
| Scale | ~1.25 px/mm |

### Technical Notes

- **PRNG**: mulberry32 — seeded, deterministic
- **Potential flow**: `vx = U − R²[U(x²−y²) + 2Vxy] / r⁴`
- **Rendering**: additive (`lighter`) blending; Gaussian unit sprite scaled per-particle
- Single HTML file, no dependencies, no build step

---

## Standards in Scope

| Standard | Domain |
|---|---|
| ISO 12233 | Sharpness / MTF (eSFR) |
| ISO 17850 | Geometric distortion |
| ISO 14524 | OECF / tonal response |
| ISO 15739 | Low-light noise |
| EMVA 1288 | Noise characterization (FPN, PRNU, SNR, dynamic range) |

---

## Requirements

Python 3.10+

```
fastapi, uvicorn, httpx, pydantic, pyyaml,
pillow, numpy, scipy, opencv-python-headless
```
