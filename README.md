# PIV Ground Truth — Synthetic Particle Field Generator

A standalone browser-based tool for validating Particle Image Velocimetry (PIV) algorithms. Displays a synthetic particle field moving at a precisely known velocity so you can compare your PIV system's output against a ground truth.

Built for the **USGS Camera and Imaging Systems Evaluation Laboratory**.

---

## Usage

Open `piv_ground_truth.html` directly in Chrome or Edge — no server or build step required. Click the splash screen to enter fullscreen.

---

## Features

### Flow Field
Select from five analytically defined flow types:

| Type | Description |
|---|---|
| **Uniform** | Constant Vx / Vy across the field |
| **Linear Shear** | Vx varies linearly with y: `Vx(y) = Vx_c × (1 + rate × (2y/H − 1))` |
| **Solid Vortex** | Rigid-body rotation centered on screen, ω in rad/s; optional background drift Vx |
| **Poiseuille (Channel)** | Parabolic profile — zero at top/bottom walls, peak at center |
| **Rankine Vortex** | Solid-body core + irrotational (potential flow) exterior; configurable core radius and tangential speed |

All modes support independent **Turbulence (±m/s)** — a random per-particle velocity offset drawn uniformly from a disk of the specified radius.

### Particles
- **Count** — 50–2000 tracer particles
- **Min / Max Diameter (px)** — random size per particle in this range
- **Brightness** — peak pixel intensity (additive blending)
- **Seeding density** — particles-per-pixel readout (computed live)

### Particle Shape
Controls the correlated 2D Gaussian PSF profile per particle:

- **Elongation ρ** — ρ=0 circular; ρ→±1 stretched (correlated bivariate Gaussian)
- **ρ variability** — per-particle spread around the base ρ value
- **Align to flow** — orients each particle along its local velocity vector; models motion blur from finite exposure

### Particle Variability
- **Intensity var σ** — per-particle brightness drawn from N(1, σ); simulates non-uniform scattering
- **Diameter var σ** — per-particle size drawn from N(1, σ)
- **Out-of-plane %** — fraction of particles dimmed each camera frame; models light-sheet dropout in volumetric PIV

### Image Noise
- **Read noise σ (DN)** — additive Gaussian noise floor
- **Shot noise (×)** — Poisson-approximate photon noise, σ ∝ √(scale · I)
- **Background (DN)** — uniform pedestal added before noise; models stray light or sensor offset

### Timing
- **Camera fps** — sets the per-camera-frame displacement used in the readout and frame pair capture
- **Display fps** — sets the per-TV-frame displacement shown in the readout
- **Frame pair [C]** — captures Frame A (red overlay), advances exactly one camera frame, shows Frame B (green overlay); overlapping regions appear yellow. Measures actual Δpx between frames for direct comparison against your PIV output.

### Obstacle / Flow Object
- Toggle **Add obstacle** to place a circular body in the flow
- Click canvas to position it; right-click to remove; adjustable radius
- Flow deflects using the **exact irrotational doublet (potential flow) solution** around a cylinder — mathematically correct streamlines with stagnation points and shoulder acceleration

### Particle Seed
- Enter any integer to reproduce a particle layout exactly
- Hit **↻ New** to generate a random seed (value is shown — record it)
- Leave blank for non-deterministic mode
- Seed governs: particle positions, turbulence offsets, sizes, and shapes

### Scale Calibration
- Enter TV physical dimensions (mm) and screen resolution (px)
- Scale X and Y computed independently — mismatch reveals non-square pixels
- mm/px inverse displayed alongside px/mm

### PIV Validation Readout
The bottom bar shows (labels adapt to the active flow type):

| Field | Description |
|---|---|
| Ref / Center Speed (px/s) | Internal ground truth at screen center |
| Direction (°) | Flow angle |
| Δpx / TV frame | Displacement per display frame |
| Δpx / cam frame | Displacement per camera frame |
| True / Ref Speed (m/s) | Ground truth in physical units |
| PIV Measured (m/s) | Type your PIV system's output |
| Error (m/s) | Signed difference |
| % Error | PASS < 5% · WARN 5–15% · FAIL > 15% |

For non-uniform flows a third row appears showing the **analytical velocity profile**:

| Flow | V min | V center | V max |
|---|---|---|---|
| Linear Shear | `Vx·(1 − γ)` at y=0 | `Vx` at y=H/2 | `Vx·(1 + γ)` at y=H |
| Poiseuille | 0 (wall) | Peak at y=H/2 | = V center |
| Solid Vortex | 0 (center) | 0 (center) | ω·r at corner |
| Rankine Vortex | 0 (center) | Vc (core edge) | Vc (core edge) |

### Cursor Velocity Probe
Move the mouse over the canvas to see the exact analytical ground truth at that position: Vx, Vy (px/s), |V| (m/s), direction (°), and Δpx per camera frame. Updates every render frame. Useful for spot-checking your PIV output against the known solution at a specific interrogation window.

### Color-by-Speed Mode
Press `[V]` to color every particle by its local true speed using a blue→cyan→green→yellow→red colormap. A colorbar appears showing the 0→Vmax range in m/s.

- **Uniform** — all particles are the same color, confirming identical speed everywhere
- **Linear Shear / Poiseuille** — a smooth color gradient reveals the spatial velocity profile; a velocity profile diagram also appears along the left canvas edge as horizontal arrows
- **Vortex** — radial color banding shows rotation speed increasing with radius

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `H` | Toggle control panel |
| `P` | Pause / resume |
| `F` | Fullscreen |
| `R` | Re-seed particle field |
| `C` | Capture frame pair A→B / exit frame pair |
| `V` | Toggle color-by-speed particle colormap |
| `Esc` | Exit frame pair mode or remove obstacle |

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
- **Particle rendering**: correlated 2D Gaussian sprite (13×13 px unit kernel, σ=1) scaled per-particle radius; additive (`lighter`) blending; per-particle elongation via canvas rotate + anisotropic scale
- **Noise**: Gaussian table pre-computed at startup (131 072 samples); rebuilt every 4 frames for performance
- **Potential flow / obstacle**: irrotational doublet — `vx = U − R²[U(x²−y²) + 2Vxy] / r⁴`
- **Frame pair**: positions snapshot before advance; exactly 1/camFps seconds of advection applied
- **Cursor**: auto-hides after 3 s of inactivity
- Single HTML file, no dependencies, no build step
