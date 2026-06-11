# PIV Ground Truth — Synthetic Particle Field Generator

A standalone browser-based tool for validating Particle Image Velocimetry (PIV) algorithms. Displays a synthetic particle field moving at a precisely known velocity so you can compare your PIV system's output against a ground truth.

Built for the **USGS Camera and Imaging Systems Evaluation Laboratory**.

---

## Usage

Open `piv_ground_truth.html` directly in Chrome or Edge — no server or build step required. Click the splash screen to enter fullscreen.

---

## Features

### Flow Control
- **Vx / Vy** — set mean flow velocity in **m/s** (converted to px/s internally via your screen scale)
- **Turbulence (±m/s)** — adds a random per-particle velocity offset, drawn uniformly from a disk of the specified radius, to simulate non-uniform flow
- Readout always shows the commanded mean — your ground truth for PIV comparison

### Particles
- **Count** — number of tracer particles (50–2000)
- **Min / Max Diameter (px)** — each particle is assigned a random size in this range; Gaussian intensity profile (realistic PSF)
- **Brightness** — peak intensity (additive blending mimics real particle images)

### Obstacle / Flow Object
- Toggle **Add obstacle** to place a circular body in the flow
- Click canvas to position it; right-click to remove
- Flow deflection uses the **exact potential flow (irrotational doublet) solution** around a cylinder — mathematically correct streamlines with proper stagnation points and shoulder acceleration

### Particle Seed
- Enter any integer seed to get a fully reproducible particle layout
- Hit **↻ New** to generate a random seed (the value is shown so you can record it)
- Leave blank for non-deterministic mode
- Seed covers: particle positions, turbulence offsets, and sizes

### Scale Calibration
- Enter your **TV physical dimensions** (width and height in mm) and **screen resolution** (px)
- Scale X and Y are computed separately — any mismatch indicates non-square pixels
- Mean scale used for scalar speed conversion

### PIV Validation
The bottom readout bar shows:

| Field | Description |
|---|---|
| Mean Speed (px/s) | Internal ground truth |
| Direction (°) | Flow angle |
| Δpx / TV frame | Displacement per display frame |
| Δpx / cam frame | Displacement per camera frame |
| True Speed (m/s) | Ground truth in physical units |
| PIV Measured (m/s) | Type your PIV system's output |
| Error (m/s) | Signed difference |
| % Error | Color-coded: green < 5%, yellow 5–15%, red > 15% |

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `H` | Toggle control panel |
| `P` | Pause / resume |
| `F` | Fullscreen |
| `R` | Re-seed particle field |
| `Esc` | Exit obstacle placement mode |

---

## Screen Defaults (USGS Lab TV)

| Setting | Value |
|---|---|
| TV width | 1543.05 mm |
| TV height | 863.6 mm |
| Resolution | 1920 × 1080 px |
| Scale X | ~1.2443 px/mm |
| Scale Y | ~1.2503 px/mm |

---

## Technical Notes

- **PRNG**: mulberry32 — fast, high-quality 32-bit seeded generator
- **Particle rendering**: Gaussian PSF via a normalized unit sprite scaled per-particle; additive (`lighter`) blending
- **Potential flow**: irrotational doublet solution — `vx = U − R²[U(x²−y²) + 2Vxy] / r⁴`
- **Cursor**: auto-hides after 3 seconds of inactivity
- Single HTML file, no dependencies, no build step
