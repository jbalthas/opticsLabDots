# PIV Ground Truth — Synthetic Particle Field Generator

A standalone browser-based tool for validating Particle Image Velocimetry (PIV) algorithms. Displays a synthetic particle field moving at a precisely known velocity so you can compare your PIV system's output against a ground truth.

Built for the **USGS Camera and Imaging Systems Evaluation Laboratory**.

---

## Usage

Open `piv_ground_truth.html` directly in Chrome or Edge — no server or build step required. Click the splash screen to enter fullscreen.

For metrologically verifiable work — anything destined for a published validation study — read **[VERIFICATION.md](VERIFICATION.md)**, which gives the step-by-step lab procedure for proving the tool's stated ground truth with a high-speed camera.

---

## Metrology Mode — read this before using the tool as a reference standard

By default the simulation advances by the **real elapsed wall-clock time** between browser frames, while the readout quotes the displacement that *would* occur at exactly `1/camFps`. Those are two different clocks. They agree while the browser behaves and diverge silently when it does not — a GC pause, a compositor stall, a background tab. Nothing in the image tells you it happened.

Four features exist to close that gap. Together they turn the quoted ground truth from an assertion into something you can measure off a recording:

| Feature | What it gives you | Key |
|---|---|---|
| **Deterministic step** | An exact, fixed sim timestep per rendered frame, decoupled from the wall clock | `D` |
| **Frame code** | The rendered-frame index burned into the image as a binary block strip | `G` |
| **Timing telemetry** | What the browser actually did: refresh, jitter, dropped frames, u<sub>Δt</sub>/Δt | `T` |
| **Step-pair capture** | A real, temporally separated A/B image pair a camera can actually capture | `S` |
| **Run manifest** | Export / import the complete configuration + seed + telemetry as JSON | — |
| **1:1 display gate** | Refuses to let a resampled canvas pass as a calibrated one | — |
| **Render cost** | What composing the image costs against the frame budget, measured | — |
| **Sub-pixel sweep** | Commanded displacement stepped through a pixel — measures your package's peak locking | `W` |
| **Window-averaged truth** | The comparand a correlation actually returns, not the point value | — |
| **Stimulus u<sub>c</sub>** | What the tool can say about its own uncertainty, so a pass criterion means something | — |
| **Auto-lock timing** | Locks the step rate to the measured refresh — and refuses to, when the measurement isn't good enough | `A` |

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

All modes support independent **Velocity dispersion (±m/s)** — a random per-particle velocity offset drawn once from a disk of the specified radius and carried unchanged for the particle's life.

> **This is not turbulence and must not be called turbulence in a paper.** There
> is no spatial correlation, no temporal evolution and no energy cascade — it is
> a frozen per-particle offset that models tracer-to-tracer velocity scatter.
> The control was previously labelled "Turbulence"; the manifest key stays
> `turbMs` so older manifests still import.

### Particles
- **Count** — 50–2000 tracer particles
- **Min / Max Diameter (px)** — random size per particle in this range. The control sets **2σ** of the rendered Gaussian
- **Brightness** — peak pixel intensity. Exact: a particle at brightness *B* with no per-particle intensity variation puts *B* DN in the pixel its centre falls on
- **Seeding density** — particles-per-pixel readout (computed live)
- **Particle image d<sub>τ</sub>** — the 1/e² particle image diameter, computed live

> **d<sub>τ</sub>, not the slider value, is the number that matters.** Sub-pixel
> (peak-locking) bias is governed by the particle image diameter, and the
> diameter control sets 2σ, so **d<sub>τ</sub> = 4σ = 2 × the control**. A
> "2 px" particle has d<sub>τ</sub> = 4 px. FWHM = 2√(2 ln 2)·σ ≈ 1.177 ×
> d<sub>τ</sub>/2. Quote d<sub>τ</sub> in a methods section; the panel states it
> live so there is nothing to derive by hand.

### Particle Shape
Controls the correlated 2D Gaussian PSF profile per particle:

- **Elongation ρ** — ρ=0 circular; ρ→±1 stretched (correlated bivariate Gaussian)
- **ρ variability** — per-particle spread around the base ρ value
- **Align to flow** — orients each particle along its local velocity vector; models motion blur from finite exposure
- **Bubble mode** — swaps the Gaussian profile for a translucent ring with a specular highlight, evaluated analytically like the Gaussian. Cosmetic only; motion is unchanged

### Particle Variability
- **Intensity var σ** — per-particle brightness drawn from N(1, σ); simulates non-uniform scattering
- **Diameter var σ** — per-particle size drawn from N(1, σ)
- **Out-of-plane %** — fraction of particles **dropped from the frame entirely** (not dimmed), re-drawn each camera frame; models light-sheet dropout in volumetric PIV

  The redraw cadence follows whichever clock governs motion: one redraw **per camera frame** in free-run, one **per sim step** in deterministic mode. In **step-pair** the redraw happens on each A→B advance, *after* Frame A is snapshotted — so A and B carry independent dropout sets and the pair decorrelates exactly as a real light sheet would. With dropout at 40 % roughly 52 % of particles share a state between A and B (`p² + q²`), which is the signature to look for. This is the only mode that produces a real image pair, so it is the only place dropout can actually be tested against a PIV algorithm.

### Image Noise

All three terms are applied to the **accumulated intensity**, before the single
clamp at output, and all three are **zero-mean**.

- **Read noise σ (DN)** — zero-mean Gaussian, one draw per pixel (not per channel), added after the display encode
- **Shot noise (×)** — zero-mean and **signal-dependent**: σ = √(scale · I<sub>local</sub>), drawn from the intensity actually accumulated at that pixel
- **Background (DN)** — uniform DN pedestal; models stray light or sensor offset

**A fresh realisation is drawn on every rendered frame**, keyed on
`(seed, frameIndex)`. Two consequences worth stating explicitly:

- Frame A and Frame B of a step-pair can never share a noise realisation, because their frame indices differ. Noise correlated across a pair plants a spurious correlation peak at **zero displacement** and biases the measured velocity **low** — the same direction as the effect this tool exists to measure, which makes it the worst possible artefact to leave in.
- With a seed set, the realisation on a given frame index is reproducible. The manifest does not restore the frame index, so a run with noise on is still reported as **not bit-reproducible** — but the noise is no longer drawn from an unseeded source, and a decoded frame index is enough to regenerate it.

> Noise is the one setting that writes **every** pixel rather than only the
> particle footprints, so it is the one that shows up in the render-cost figure.
> Run the §1 timing gate with all noise at zero.

---

## The rendered image

The tool's ground truth is not only *where* the particle is, it is *what the
particle looks like*. PIV sub-pixel bias is set by the particle image, so the
point-spread function is part of the reference standard and is specified here
rather than left to whatever the canvas happened to do.

### Point-spread function

Every particle image is evaluated **analytically, per output pixel, at the
particle's exact sub-pixel position**. There is no sprite bitmap, no
`drawImage` interpolation and no alpha compositing anywhere in the particle
path.

```
I(u,v) = A · exp( -( u²/(2σa²) + v²/(2σb²) ) )
```

- `(u,v)` — offset from the particle centre, rotated into the particle's own frame
- `σa = σ · aspect`, `σb = σ / aspect`, `aspect = 1 + |ρ|` — so elongation is an exact correlated bivariate Gaussian, not a scaled bitmap
- `σ` — the particle's radius parameter in px; the diameter control sets 2σ
- `A` — `brightness × per-particle intensity factor`

Overlapping particles **add linearly** and the frame is **clamped once, at
output**, which is what a sensor does.

**Sampling model — state this in a methods section.** A pixel takes the value
of the continuous profile at its **centre**: `I[i,j]` is the profile evaluated
at `(i+½, j+½)`. It is *not* the integral of the profile over the pixel area.
For σ ≥ 1 px the two differ by well under 1 % of the peak. Below σ = 1 px the
profile is under-sampled and the difference stops being negligible — but
d<sub>τ</sub> < 4 px is outside sensible PIV practice anyway. Point sampling is
used because it is exactly specifiable in one line, which matters more here
than the last fraction of a percent.

Each particle is evaluated out to the radius at which its contribution falls
below 0.4 DN (bounded to 2–4.5 σ), so a faint particle costs less than a bright
one and neither is visibly truncated.

> ### What this replaced, and why it mattered
>
> The previous implementation drew a 13×13 Gaussian bitmap scaled with
> `drawImage` under `globalCompositeOperation = 'lighter'`. Canvas `ImageData`
> is unpremultiplied and `lighter` evaluates `dst + src_color × src_alpha`, so
> writing **both** the colour and the alpha as the same Gaussian **squared it**.
> The delivered profile was `exp(-r²)` — that is **σ/√2, not σ** — and the peak
> was **`brightness²/255`, not `brightness`** (at the default 220, an actual
> peak of 190). On top of that, every particle image was a bilinearly
> interpolated bitmap rather than a Gaussian.
>
> Both are exact now, and both were verified by reading pixels back off the
> canvas: peak DN equals `brightness` to the bit, and σ recovered from the
> rendered profile matches the commanded σ to 0.25 % (the residual is 8-bit
> quantisation).

### Display transfer function — `Linear light`

Default **off**, which renders intensities directly as DN exactly as before.

Everything above is composed in DN. A panel emits roughly `DN^γ`, so with this
off the *light leaving the screen* carries the Gaussian raised to the panel's
gamma — a narrower profile than the one specified, and overlapping particles
that are not additive in light. Turning **Linear light** on composes the field
in linear light and encodes it with the inverse EOTF, so the emitted profile is
the intended Gaussian.

- **Display γ** — set this from the **measured** display gamma in the calibration protocol, not from the nameplate
- Toggling it changes the stimulus, so it resets the telemetry window like any other run parameter
- It travels in the manifest's `render` block

Leave it off unless you have a measured gamma. An assumed 2.2 is not better
than a documented, uncorrected DN render.

---

## Auto-lock timing `[A]`

Three timing warnings can fire at once, and they are not the same kind of
problem. Auto-lock treats them differently on purpose.

| Warning | Who owns the quantity | What auto-lock does |
|---|---|---|
| **Sim time ≠ real time** | `stepFps` — a **tool-side** number | **Sets it**, to the measured refresh exactly. Scale becomes 1.000 |
| **Camera not an integer divisor** | `camFps` — describes your **physical camera** | **Computes and tells you.** Never applies it silently |
| **Refresh unstable** | The machine, the display mode, the render load | **Cannot fix it — so it refuses to lock**, and diagnoses it |

### Why camera fps is not set for you

`camFps` is not a setting of this tool, it is a *statement about your camera*.
Writing 29.070 into it while the camera is still running at 30 would make every
per-camera-frame figure on screen confidently wrong — which is the exact failure
class this whole tool exists to remove. So auto-lock computes the correct rate,
shows it, and waits. Change the camera, then click **set camera to 29.070 fps**
to confirm it. That click is you asserting the hardware state, not the tool
guessing at it.

### Why it refuses to lock on an unstable machine

**This is the important part.** Locking the step rate to a refresh measured
through heavy interval jitter bakes a wrong number into the stimulus and then
prints a reassuring `×1.000` next to it. The warning disappears and the error
does not. A tool that cannot fix a problem must not be able to hide it either.

So auto-lock will not lock until a **full 600-frame window** clears the same gate
VERIFICATION.md §1 makes you check by eye:

| Check | Gate |
|---|---|
| u<sub>Δt</sub>/Δt | < 0.5 % |
| Interval σ | < 1.0 ms |
| Dropped intervals | 0 |
| Median agreement between consecutive windows | within 0.2 % |

Until then the state reads **measuring**; if the gate fails it reads **BLOCKED**
and the metrology panel lists every failing check, then a diagnosis in the order
worth checking.

### What it diagnoses

- **Adaptive sync.** A measured refresh sitting *near* a standard panel rate but not on it, with a jittery interval, is the signature of a variable-refresh display — G-SYNC, FreeSync, VRR. A panel that changes its own refresh rate cannot be a timing reference. This is the most common cause on an otherwise idle machine and it is invisible unless you look for it
- **Render headroom.** If composing the image is taking a large fraction of the interval, it names the figure and the remedies (noise off, fewer particles, smaller window)
- **A panel that is too fast for the machine.** Above ~130 Hz with drops, it says so plainly: nothing about this stimulus needs a high refresh, and a rock-steady 60 or 120 Hz is worth far more than an unstable 240 Hz, because every timing figure here rests on the interval being repeatable
- **Background load.** The standard checklist, listed last because it is the one people already know

### Behaviour

- Default **off**. Turning it on enables deterministic mode, since a timing lock is meaningless without it
- **Locks exactly, not rounded.** Rounding 232.56 Hz to 233 leaves a 0.2 % scale error standing for no reason. `Match refresh` no longer rounds either, and the step-rate control now accepts decimals up to 480
- **Re-locks on sustained drift** (> 0.5 %, three consecutive checks, never faster than every 5 s) — so moving the window to a different monitor is picked up without thrashing
- **If stability is lost after a lock**, the state goes to **LOCK LOST**. The applied step rate is *kept* — reverting it mid-run would change the stimulus — but the panel stops claiming the conditions still hold and tells you not to trust a capture taken now
- The manifest records whether it was on, the locked refresh, the camera recommendation, whether you applied it, and **the evidence the lock rested on**: u<sub>Δt</sub>/Δt, σ, median, frame count, drops and render cost at the moment of locking. Importing a manifest does **not** replay a lock — it is a property of the machine it was measured on, so it re-measures

> **Worked example.** A 240 Hz panel measuring 232.56 Hz with σ = 2.33 ms,
> u<sub>Δt</sub>/Δt = 37.9 % and 1284 dropped frames: auto-lock reports BLOCKED,
> lists all three failing checks, and leads with adaptive sync — 232.56 Hz is
> near 240 but not on it, which is what a VRR panel looks like. Fix that, and the
> same machine locks at 232.560 Hz with a sim-time scale of exactly 1.000 and a
> camera recommendation of 29.070 fps at k = 8.

---

## Sub-pixel displacement sweep `[W]`

**This is the one measurement here that is about the algorithm rather than the
display, and it is the most diagnostic thing the tool can do.**

Peak locking — the tendency of a correlation peak-fit to pull measured
displacements toward integer pixel values — is the dominant systematic in
sub-pixel PIV. It is a property of the *algorithm*, and it shows up as a bias
that oscillates with the fractional part of the true displacement, with a period
of exactly one pixel. You cannot see it by running a flow at one speed. You have
to sweep the commanded displacement through a pixel and watch the bias trace out
its curve.

### What the mode does

**It does not use the flow field at all.** Each sweep point is a pure, uniform
translation of one identical particle layout by an exactly commanded Δ px:

1. Frame **A** — the canonical layout, untouched
2. Frame **B** — the same layout, every particle displaced by exactly `(Δ·cos θ, Δ·sin θ)`
3. Hold each for `holdFrames`, then move to the next Δ

Same particles, same intensities, same seed, same everything. The **only**
variable between points is the sub-pixel displacement, so whatever structure
appears in `measured − commanded` belongs to the algorithm, with nothing else to
blame it on.

Every point restarts from the same snapshot rather than accumulating, so errors
cannot compound down the sweep and point 20 is as clean as point 1. Verified:
the realised displacement matches the commanded value to **9 × 10⁻¹⁴ px**, and
every particle moves by an identical vector.

### Controls

| Control | Meaning |
|---|---|
| **Start / End / Step (px)** | The commanded displacements. Default 0 → 1 in 0.1 px steps (11 points); up to 201 points |
| **Angle (deg)** | Direction of translation. **0°** sweeps along x only, so y stays integer. **26.57°** (atan ½) drives both axes off-lattice at once and is the more searching test |
| **Hold frames / step rate** | Taken from the Step-Pair section |
| **Re-stage points** | Rebuilds the schedule from the current settings and clears entered measurements |

### Reading it back

Each point records the **rendered-frame index** at which A and B were displayed.
Those indices are exactly what the frame-code strip in the captured image
decodes to, so matching a recorded frame to its commanded Δ needs no timing
assumption — read the strip, look it up in the table. The frame code carries the
A/B phase in its top data bit during a sweep, exactly as in step-pair.

Type each measured Δ into the panel and it computes **bias = measured −
commanded**, plots bias against commanded displacement, and reports:

- **bias RMS** — the number to quote. Under ~0.05 px is well behaved; 0.1 px is roughly where peak locking becomes visible by eye in a displacement histogram
- **peak-to-peak** — the amplitude of the locking oscillation
- **mean bias** — a constant offset, which is a different fault from locking and points at the calibration rather than the peak-fit

Integer-pixel displacements are marked on the plot, because those are the values
a locking algorithm is pulled toward. **Export sweep CSV** writes the schedule,
the frame indices, the measurements, the bias column and a full configuration
header. The schedule and any entered measurements also travel in the run
manifest.

> These RMS bands are **reporting** bands, not pass criteria. See *Stimulus
> uncertainty* below for why the tool declines to invent a pass/fail line here.

---

## Interrogation window

A PIV cross-correlation returns the displacement that best matches a whole
interrogation window, which to first order is the **spatial average of the
displacement field over that window** — not the velocity at its centre. For any
flow with curvature those differ, and the difference is a property of the
measurement, not an error in the algorithm.

Booking it as algorithm error is the standard way to make a good package look
biased on a parabolic profile. The bottom bar now reports **V window-avg**
alongside V center, with the percentage difference between them, so the right
comparand is on screen.

For Poiseuille the leading term is analytic,

```
<v> ≈ v_c + (L²/24) · v''
```

but rather than special-case each flow the tool samples the analytic field over
the window on a 16×16 quadrature and averages — uniform across every flow type.
Verified against the closed form above, and confirmed to give **exactly zero**
bias for uniform and linear-shear fields, which is the correct answer for a
linear field.

### Camera pixels vs display pixels — do not get this wrong

`IW size` is entered in **camera** pixels, because that is what a PIV package is
configured with. The maths needs display pixels:

```
IW_display = IW_camera / (camera px per display px)
```

A 32 px window on a camera resolving the screen at 0.5 cam-px per display-px
covers **64 display pixels** — twice the field, four times the particles, and a
different gradient bias. The panel shows the converted figure.

### N<sub>I</sub> and the ¼-rule

- **N<sub>I</sub>** — particles per interrogation window, the seeding figure PIV practice actually uses. Green at ≳ 8, amber 4–8, red below. Particles-per-pixel is still shown, but N<sub>I</sub> is the one to report
- **Δ / IW** — displacement as a fraction of the window. Green at ≤ 25 % (the quarter rule), red past a third

> **Worth checking on your own configuration.** At 600 particles on a 1080p
> panel with a 32 px window at 1:1 magnification, N<sub>I</sub> ≈ 0.3 — far
> below the usual floor of 8. Either the particle count needs to go up, or the
> camera needs to be imaging a smaller part of the screen than 1:1. The readout
> is there so this is visible before a run rather than after.

---

## Particle recycling and pair loss

A particle that crosses the periodic boundary between Frame A and Frame B is
**unpaired**: it contributes noise to the correlation instead of signal. Every
periodic synthetic field has this, it is unavoidable at the boundaries, and it
is normally small — but it is part of the stimulus, so it is counted and
reported rather than left for a reviewer to ask about.

**Pair loss / cam frame** shows the measured rate, scaled from the sim step to
the camera frame. Green under 0.5 %, red past 2 %.

**Return to origin** is the old recycling behaviour — after a full field-span of
travel a particle teleported back to where it was first placed. It is now **off
by default**. All five flow fields here are incompressible, so the field cannot
clump and the periodic wrap alone recycles it correctly: the teleport was
redundant, and it was injecting unpaired particles at a rate nothing reported.
The toggle restores it if you want the old behaviour.

---

## Stimulus uncertainty

A pass criterion only means something if it sits outside the uncertainty of the
stimulus it is being judged against. The metrology panel reports **stimulus
u<sub>c</sub> (k=1)** — what the tool can honestly say about its own uncertainty.

Two random terms combine in quadrature:

| Term | Source |
|---|---|
| u<sub>Δt</sub>/Δt | Timing. Measured, straight off the telemetry window |
| u<sub>L</sub>/L | Spatial scale, from **u(TV dim)** — your standard uncertainty on the panel's measured active-area dimension. This is the only part of the px→mm chain the tool cannot measure for itself |

Systematic departures — sim-time scale ≠ 1, camera not an integer divisor — are
listed **separately and not folded in**, because they are corrections to apply,
not uncertainties to carry. A sim-time scale of 1.996 does not mean "±100 %", it
means "divide by 1.996".

> **This is a floor, not a budget.** It does not include display response,
> spatial non-uniformity, or anything else MVE-1 is meant to measure. Quote it
> as what it is.

### QA pass thresholds are now operator-set and recorded

The shipped 5 / 10 / 20 % criteria were asserted, not derived. They are now
**editable per test**, and each shows how it compares with the stimulus
uncertainty:

- `operator-set · 12.4× stimulus u_c (0.40 %)` — a meaningful criterion
- `operator-set · inside 2 u_c (1.80 %) — not a criterion` — flagged in red, because a threshold tighter than twice the stimulus's own uncertainty cannot decide anything

The exported CSV carries the threshold used, the stimulus u<sub>c</sub> at the
moment each result was logged, the u<sub>c</sub> term breakdown, any uncorrected
systematics, and an explicit line stating that thresholds are operator-set
rather than derived from an uncertainty budget.

---

## Integration

The trajectory *is* the ground truth, so each flow type gets the cheapest
scheme that is actually correct for it.

| Flow | Scheme | Why |
|---|---|---|
| Uniform, Linear shear, Poiseuille | Explicit step | `vy = 0` and `vx = vx(y)`, so `y` is constant along a trajectory and the velocity a particle sees never changes. The explicit update is the **exact** solution |
| Solid vortex | **Closed form** | `dx/dt = A·x + b` with `A = [[0,−ω],[ω,0]]`. The trajectory is a circle about the fixed point `x* = −A⁻¹b`, and the particle rotates about it by exactly `ω·dt`. Background drift and the particle's turbulence offset are carried in `b`, so they stay exact too |
| Rankine vortex, anything with an obstacle | **RK4** | The field varies along the trajectory with no convenient closed form. Fourth order puts the truncation error below any displacement the camera can resolve |

> ### Why this was worth fixing
>
> Explicit Euler on a rotation is **unconditionally unstable in radius** — it
> scales `r` by `√(1 + (ω·dt)²)` every step:
>
> | ω | step rate | radius growth / s | over 60 s |
> |---|---|---|---|
> | 0.5 rad/s | 60 Hz | 0.21 % | **+13.3 %** |
> | 0.5 rad/s | 30 Hz | 0.42 % | **+28.4 %** |
> | 1.0 rad/s | 60 Hz | 0.84 % | **+64.9 %** |
>
> Since `v = ωr` in the core, the actual speed climbed away from the analytical
> ground truth the readout was quoting, silently, over the length of a
> recording. QA test **T05** (Rankine) carries a 20 % criterion, which the
> integrator alone could consume on a one-minute run at 30 Hz.
>
> Measured after the fix: radius drift over 60 s at 60 Hz is **2 × 10⁻¹¹ %**,
> and the accumulated rotation angle is correct to 4 × 10⁻¹⁵ rad.

---

## Display 1:1 gate

The canvas backing store is sized in **CSS pixels**. When
`devicePixelRatio != 1` the compositor resamples the whole canvas on its way to
the panel, which

1. puts a second, unmodelled interpolation stage on top of the rendered PSF, and
2. makes every px/mm figure wrong by exactly that factor.

Neither is visible in the image, and both invalidate the ground truth however
clean the timing is.

`devicePixelRatio` also tracks **browser zoom**, so this catches an accidental
`Ctrl`+scroll as well as an OS display-scaling setting — the more likely of the
two failures in a lab.

When the ratio is not 1.000 the tool raises a **red banner across the top of
the screen** that is deliberately not dismissible (the operator may be running
with both panels hidden), and a matching red warning in the metrology panel.
The verdict is recorded in the manifest as
`environment.devicePixelRatio1to1`.

**Fix:** browser zoom to 100 % (`Ctrl`+`0`), OS display scaling to 100 %,
reload, re-run the §1 gate.

---

## Timing

### Camera fps / Display fps
- **Camera fps** — sets the per-camera-frame displacement used in the readout and frame-pair capture
- **Display fps** — sets the per-TV-frame displacement shown in the readout

> **`Display fps` is a typed number that never touches the motion.** It is used *only* to compute the "Δpx / TV frame" figure. If you type 120 and the panel is running at 60 Hz, that figure is simply wrong. Once the telemetry has measured the real refresh rate, an amber banner appears under the control if the two disagree by more than 1 Hz. The fix is to type the measured refresh, or to stop relying on that field and use deterministic mode instead.

### Deterministic step `[D]`

Default **off**, so existing behaviour is preserved. With it on, **every `requestAnimationFrame` callback advances the simulation by exactly `1 / stepFps` seconds**, whatever the measured interval was. The `Math.min(dt, 0.05)` clamp does not apply. Out-of-plane dropout keys off the same fixed step, so it stays one refresh per step.

- **Step rate (`stepFps`)** — default 30, range 1–240
- **Match refresh (N)** — sets the step rate to the measured panel refresh in one click, making the sim-time scale exactly 1.000. Turns amber when pressing it would change anything. Read the warning below before running with any other value

#### The critical subtlety: sim time is not real time

In deterministic mode the displacement between two consecutive **display refreshes** is exactly:

```
Δpx per rendered frame  =  speed / stepFps
```

The panel refreshes at its own rate, so the apparent real-time speed is scaled:

```
sim-time scale  =  refresh / stepFps
```

At 60 Hz with `stepFps = 30`, the field moves through sim-seconds at **twice** real time.

> ### ⚠ This scales the m/s your PIV system reports
>
> A PIV package computes `v = Δx / Δt` using the **real** camera frame interval. Working through it:
>
> | | |
> |---|---|
> | Δx per camera frame | `k × speed / stepFps` px |
> | Δt | `k / refresh` real seconds |
> | **v measured** | `speed × (refresh / stepFps)` px per **real** second |
>
> **Your PIV package will report the True Speed readout multiplied by the sim-time scale.** With the defaults on a 60 Hz panel that is a factor of **2** — an apparent 100 % error that is entirely an artefact of the mode, not your algorithm.
>
> **The fix: set `stepFps` equal to the measured refresh rate.** The scale becomes exactly 1.000, sim time and real time coincide, and the m/s readout is directly comparable with no correction. Press **Match refresh (N)** in the Timing section — it reads the measured rate and sets the step rate to it in one click. The button turns amber whenever the scale is off 1.000 by more than 2 %, and the metrology panel raises a matching warning that names both the corrected figure and the divisor.
>
> Run at `stepFps ≠ refresh` only when you deliberately want the field slowed or sped up relative to real time — and then divide your measurement by the stated scale.

Separately, **you must set your camera frame rate deliberately**:

- Set camera fps **equal to the panel refresh rate**, or
- Set it to an **integer divisor** `k` of the refresh rate — then

```
Δpx per camera frame  =  k × (speed / stepFps)     where  k = round(refresh / cameraFps)
```

If `|refresh / cameraFps − k| > 0.02` the camera is not phase-locked to the panel and the per-frame displacement will beat between `k` and `k±1` steps. The metrology panel flags this in **amber** and tells you the nearest correct camera fps.

The metrology panel states all of this live: commanded Δpx per rendered frame, measured refresh, the ratio and `k`, the resulting Δpx per camera frame, and the sim-time scale factor. It raises three independent warnings:

| Warning | Colour | Trigger |
|---|---|---|
| **Sim time ≠ real time** | amber | `\|refresh/stepFps − 1\| > 0.02` — your reported m/s will be scaled |
| **Camera not an integer divisor** | amber | `\|refresh/camFps − k\| > 0.02` — Δpx per camera frame will beat |
| **Refresh unstable** | red | σ > 3 ms, u<sub>Δt</sub>/Δt > 1.5 %, or any dropped frame |

The three are orthogonal and can fire together. The red one matters most in deterministic mode: a dropped refresh is a dropped *sim step*, so the field falls behind real time without changing Δpx per rendered frame — the displacement stays correct while the elapsed time does not.

### Frame pair `[C]`
Captures Frame A (red overlay), advances exactly one camera frame, shows Frame B (green overlay); overlapping regions appear yellow. Good for reading Δpx **by eye**.

> A camera photographing this captures a *single* frame containing both A and B. It **cannot** produce a real PIV image pair. Use step-pair for that.

### Step-pair capture `[S]`

Sequences the two frames in time instead of compositing them:

1. Displays **only Frame A**, normally rendered, for `holdFrames` rendered frames
2. Advances the sim by exactly `1 / stepFps`
3. Displays **only Frame B** for `holdFrames` rendered frames
4. Stops (freezing on B), or loops A→B→A→B… if **Loop** is enabled, advancing one step per transition

Controls:
- **Hold frames** — 1–120, default 10
- **Loop A→B→A** — default off
- **Phase badge** — large `A` / `B` badge at top-center, default on, toggleable

The frame-code strip additionally encodes the displayed phase in its top bit while step-pair is active (see below). The two pair modes are mutually exclusive; starting one exits the other.

**Interactions to be aware of:**

- **Pause `[P]` freezes the sequencer.** The displayed phase, its position, and the hold counter all stop; nothing advances behind the PAUSED overlay. Unpausing resumes mid-hold.
- **Anything that rebuilds the particle field exits step-pair automatically** — re-seed `[R]`, a change to particle count, a window resize, a manifest import, or a QA test. Frame A was snapshotted from the old field, so keeping the mode active would present a pair with a meaningless displacement. The mode drops out rather than showing a silently invalid pair; restart it with `[S]` once the field is settled.
- Every drawing pass — including the colour-by-speed overlay — renders only the displayed phase. A step-pair frame never contains both A and B.

---

## Frame Code `[G]`

Default **on**. Burns the rendered-frame index into the image so a high-speed camera can count actual rendered frames and detect drops and tearing **without trusting the browser**.

### Layout

Each strip is **13 square blocks** in a row, drawn left to right:

```
[ clock ][ b0 ][ b1 ][ b2 ][ b3 ][ b4 ][ b5 ][ b6 ][ b7 ][ b8 ][ b9 ][ b10 ][ b11 ]
   ^        ^                                                              ^
 flips    LSB                                                            MSB
every
frame
```

- **12 data blocks**, **LSB leftmost**, white (`#fff`) = 1, black (`#000`) = 0
- One extra **clock block** immediately left of the data, toggling black/white **every single rendered frame**. This catches a repeated frame even if the count itself is misread
- Blocks are pure black and pure white with hard edges — drawn after everything else with additive blending, global alpha, smoothing and filters explicitly reset
- A 4 px black quiet zone surrounds each strip, anchoring it to the canvas corner and keeping particles and noise off the blocks

### What it encodes

| Mode | Data blocks encode |
|---|---|
| Normal | `frameIndex mod 4096` |
| Step-pair | bit 11 = phase (**0 = A, 1 = B**); bits 0–10 = `frameIndex mod 2048` |

`frameIndex` counts **display refreshes**, not sim steps — it increments on every `requestAnimationFrame` callback, including while paused.

### Tear detection

The **entire strip is rendered twice** (or four times), at opposite corners, both encoding the same index. If the panel tears mid-refresh, the two copies will **disagree inside a single captured image**. That is the only direct evidence of tearing available to the operator — in an untorn frame the copies always match.

Controls:
- **Position** — top-left + bottom-right (default) · top-right + bottom-left · all four corners
- **Block size** — 8–48 px, default 24. Size this to your camera's spatial resolution at the screen; you want each block several camera pixels across

> **Four-corner fallback.** Only the four-corner layout places two strips on the same row. If the window is too narrow to fit both (`2 × 13 × blockSize + margins > width` — e.g. 48 px blocks on a window under ~1260 px), they would overlap and corrupt each other's blocks. In that case the tool silently falls back to the diagonal top-left + bottom-right pair, which can never collide. Two correct copies beat four corrupt ones. Widen the window or reduce the block size if you need all four.

### How to decode a strip

1. Locate the strip by geometry: its quiet zone starts 0 px from the canvas corner, and the strip itself is inset 4 px. Total strip width is `13 × blockSize`
2. Sample the **centre pixel** of each block. Threshold at 50 % — the blocks are pure 0 or 255, so any threshold in between works
3. Block 0 is the clock. Blocks 1–12 are data bits 0–11
4. `index = Σ bit_b × 2^b` for b = 0…11
5. In step-pair mode, mask off bit 11 for the phase and take bits 0–10 as the count

A correct recording gives a strictly incrementing sequence. A gap means dropped rendered frames — cross-check it against the dropped-frame count in the telemetry panel.

---

## Timing Telemetry `[T]`

Maintains a rolling window of the **last 600 rendered frames**' real inter-frame intervals, taken from the `requestAnimationFrame` timestamp. The metrology panel (bottom-left) is toggleable and opens automatically when deterministic mode is switched on.

| Figure | Meaning |
|---|---|
| **u<sub>Δt</sub> / Δt** | σ<sub>interval</sub> / mean<sub>interval</sub>, as a percentage — **the relative velocity uncertainty implied by timing alone**. The single most decision-relevant number on the screen. Green < 0.5 % · amber 0.5–1.5 % · red > 1.5 % |
| Measured refresh (Hz) | 1 / median interval |
| min / median / max | Frame interval extremes, ms |
| mean | Mean frame interval, ms |
| **σ (jitter)** | Standard deviation of the interval. Green < 1 ms · amber 1–3 ms · red > 3 ms |
| Dropped (missed) | Intervals exceeding 1.5 × median, and the implied number of missed refreshes |
| Longest stall | Largest single interval and the frame index it occurred at |
| Frames since reset | Cumulative rendered-frame count |
| Suspends | Gaps over 5 s — a hidden tab, not jitter. Counted separately and excluded from the statistics so one tab switch does not poison the window |
| Device pixel ratio | The 1:1 gate. Green at 1.000, red otherwise |
| **Render cost / frame** | What composing the image costs, as an exponential moving mean, and as a percentage of the median refresh interval. Green < 30 % · amber 30–50 % · red > 50 %, with a matching warning. Image noise is the setting that moves this — it is the only one that writes every pixel rather than only the particle footprints |

**Reset telemetry** is available in the metrology panel and in the control panel. Telemetry also resets automatically whenever any flow or timing parameter changes, on window resize, and on manifest import — the statistics describe one run, and changing a parameter starts a new one.

On an idle machine u<sub>Δt</sub>/Δt reads well under 0.5 %; it rises visibly as soon as the machine is loaded.

---

## Run Manifest

**Export run manifest** writes a JSON file capturing the entire run:

- Every flow, particle, shape, variability, noise, timing, flume and obstacle parameter
- The particle **seed**
- The scale calibration (including derived px/mm)
- The full **telemetry summary**
- `stepFps`, `holdFrames`, frame-code settings
- User agent, screen resolution, `devicePixelRatio`, canvas size
- ISO 8601 timestamp
- `schemaVersion: 1`
- An **`autoLock`** block — whether it was on, the state, the locked refresh, the camera recommendation and whether it was applied, and the timing evidence the lock rested on
- An **`interrogation`** block — IW in camera px, the camera/display scale, the derived display-px window, and N<sub>I</sub>
- A **`recycling`** block — `returnToDeployment` and the measured pair-loss rate
- An **`uncertainty`** block — `tvDimUncertMm`, the combined u<sub>c</sub>, its term breakdown, and any uncorrected systematics
- A **`sweep`** block — the sweep configuration plus the full schedule with commanded Δ, the frame indices each phase was shown on, and any measured values entered
- A **`render`** block — the PSF model and its floor/extent constants, the resulting d<sub>τ</sub> range, `linearLight`, `displayGamma`, and the measured mean render cost per frame
- `environment.devicePixelRatio1to1` — the 1:1 display gate's verdict for the run
- A **`reproducibility`** block — `bitReproducible`, `fieldReproducible`, `seeded`, `fieldCanonical`, which stochastic components were active, and human-readable notes naming each obstacle to exact reproduction

Filename: `YYYYMMDD_HHMMSS_pivgt_manifest.json`

**Import run manifest** restores every setting exactly, including the seed, and rebuilds the particle field deterministically from it.

### What "reproducible" actually means here

The manifest carries a `reproducibility` block stating exactly what it can and cannot rebuild, and the tool reports the same thing in plain language at both export and import. Do not assume bit-identity — read what it tells you.

A run is **bit-reproducible** only when all four hold:

| Condition | Why |
|---|---|
| A **seed is set** | Without one the layout comes from `Math.random()` |
| The field is **canonical** | See below |
| **Out-of-plane % = 0** | Dropout is redrawn every step from unseeded randomness |
| **All noise = 0** | The Gaussian table is unseeded and read from a random offset |

**Canonical field.** Import always rebuilds the field with `seedParticles()`, so the *imported* state is the canonical layout for that seed. But the in-place controls — particle count, min/max diameter, elongation ρ, ρ variability, turbulence, intensity var, diameter var — patch the existing particles rather than rebuilding them, drawing from the PRNG in a different order than the initial layout does. After touching any of them the live field is self-consistent but **no longer derivable from the seed**, so an import will not match the session that exported it.

> **Rule: press `[R]` to re-seed immediately before exporting.** That makes the live field canonical, and the export/import pair is then exact. The export notice tells you when you have not.

The tool will not let this pass silently. Export reports either `bit-reproducible` or `NOT bit-reproducible` with the specific reason; import repeats the exporting session's caveats plus a canvas-size check, since particle positions are laid out across the canvas and need matching window dimensions.

---

## Obstacle / Flow Object
- Toggle **Add obstacle** to place a circular body in the flow
- Click canvas to position it; right-click to remove; adjustable radius
- Flow deflects using the **exact irrotational doublet (potential flow) solution** around a cylinder — mathematically correct streamlines with stagnation points and shoulder acceleration

## Particle Seed
- Enter any integer to reproduce a particle layout exactly
- Hit **↻ New** to generate a random seed (value is shown — record it, or just export a manifest)
- Leave blank for non-deterministic mode
- Seed governs: particle positions, turbulence offsets, sizes, and shapes

## Scale Calibration
- Enter TV physical dimensions (mm) and screen resolution (px)
- Scale X and Y computed independently — mismatch reveals non-square pixels
- mm/px inverse displayed alongside px/mm

## Flume Geometry `[L]`
Simulates a physical open channel on screen. While on, every velocity control and the headline ground truth are expressed in **world (flume) m/s** — what a bank-calibrated PIV package reports — with the display-plane speed still available in row 4. Presets, unit selection, fit mode, surface coefficient α, playback time scale, bank/station/scale-bar overlays and particle confinement are all configurable. Derived hydraulics (Q, Froude, Reynolds, A, R<sub>h</sub>) appear in the readout.

---

## PIV Validation Readout
The bottom bar shows (labels adapt to the active flow type):

| Field | Description |
|---|---|
| Ref / Center Speed (px/s) | Internal ground truth at screen center |
| Direction (°) | Flow angle |
| Δpx / TV frame | Displacement per display frame — **see the `Display fps` caveat above** |
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

## Cursor Velocity Probe
Move the mouse over the canvas to see the exact analytical ground truth at that position: Vx, Vy (px/s), |V| (m/s), direction (°), and Δpx per camera frame. Updates every render frame. Useful for spot-checking your PIV output against the known solution at a specific interrogation window.

## Color-by-Speed Mode
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
| `B` | Toggle bubble mode (cosmetic) |
| `L` | Toggle flume geometry simulation |
| `D` | **Toggle deterministic step mode** |
| `S` | **Start / stop step-pair (true A→B) capture** |
| `G` | **Toggle optical frame-code strips** |
| `T` | **Toggle metrology / timing telemetry panel** |
| `A` | **Toggle auto-lock timing** (enables deterministic mode) |
| `W` | **Start / stop the sub-pixel displacement sweep** (opens its panel) |
| `Esc` | Exit sweep / frame pair / step pair / remove obstacle |
| `?` | Show / hide the shortcut reference |

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
- **Particle rendering**: analytic correlated 2D Gaussian, evaluated per output pixel at the exact sub-pixel position and accumulated into a `Float32Array` intensity buffer; no bitmap, no `drawImage`, no alpha compositing. Linear addition, one clamp at output. The quadratic form is separable whenever ρ = 0, so the inner loop is one multiply per pixel; only per-particle footprints are touched, not the full canvas. See *The rendered image*
- **Noise**: Gaussian table pre-computed at startup (131 072 samples); a fresh realisation drawn **every rendered frame**, keyed on `(seed, frameIndex)`. Shot noise is signal-dependent (σ = √(scale·I_local)) and zero-mean; read noise is zero-mean and drawn once per pixel. Output rounds to nearest rather than truncating, which would be a uniform −0.5 DN systematic
- **Potential flow / obstacle**: irrotational doublet — `vx = U − R²[U(x²−y²) + 2Vxy] / r⁴`
- **Frame pair**: positions snapshot before advance; exactly 1/camFps seconds of advection applied
- **Deterministic step**: `dt = 1 / stepFps` per rendered frame, unclamped. Verified exact to < 2 × 10⁻¹⁴ px against synthetic 5–250 ms interval jitter
- **Step-pair**: the sequencer runs *after* the draw, so each phase is held for the full `holdFrames` worth of rendered frames. In loop mode the frame shown as B becomes the next A, giving exactly one sim step per A→B→A cycle. The displayed set is resolved once per frame and reused by every drawing pass, so no pass can composite the other phase in
- **Frame code**: integer-aligned `fillRect` only, inside a `save`/`restore` that resets composite op, alpha, filter and image smoothing
- **Sweep**: pure translation of a fixed snapshot; realised displacement matches commanded to 9 × 10⁻¹⁴ px, and every particle moves by an identical vector. Frame indices for both phases recorded per point
- **Window average**: 16×16 quadrature of the analytic field over the interrogation window. Verified against `<v> = v_c + (L²/24)·v''` for Poiseuille, and exactly zero for uniform and linear-shear fields
- **Pair loss**: counted by testing the pre-wrap position against the domain bounds — comparing the post-modulo coordinate against its input counts floating-point rounding as a wrap and reports ~100 %
- **Integration**: exact where the flow permits (uniform / shear / Poiseuille explicit; solid vortex in closed form as a rotation about the fixed point of `dx/dt = Ax + b`), RK4 for Rankine and obstacle flows. Verified: solid-vortex radius drift over 60 s at 60 Hz is 2 × 10⁻¹¹ %
- **Display gate**: `devicePixelRatio` must read 1.000; anything else means the compositor is resampling the canvas and both the PSF and the px/mm scale are invalid
- **Telemetry**: 600-sample ring buffer of rAF intervals; statistics recomputed at 5 Hz, drop detection per-frame against the running median
- **Cursor**: auto-hides after 3 s of inactivity
- Single HTML file, no dependencies, no build step, runs from `file://`
