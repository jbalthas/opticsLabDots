# Task: make `piv_ground_truth.html` metrologically verifiable

## Context

`piv_ground_truth.html` is a standalone browser tool used by the USGS Camera and
Imaging Systems Evaluation Laboratory. It renders a synthetic particle field
moving at an analytically known velocity on a dimensionally calibrated TV, so a
PIV system can be pointed at the screen and its measured velocity compared
against the tool's stated ground truth.

The tool is about to be used as a *reference standard* in a published validation
study. Before that can happen, the ground truth it reports must be something we
can independently measure, not something we assert. Right now it is asserted.

## Hard constraints — do not violate

- **Single HTML file.** No build step, no bundler, no npm, no external
  dependencies, no CDN imports. It must keep opening directly in Chrome/Edge by
  double-clicking.
- Keep all existing functionality working. This is additive.
- Match the existing code style: plain ES2020, no framework, `const`/`let`, the
  existing `ctx` 2D canvas drawing, the existing control-panel markup patterns
  (`.section-label`, `.obs-btn`, `.info-row`, and the `wireSliderNum()` helper).
- Existing keyboard shortcuts are taken: `H P F R C V Esc`. Pick unused keys.
- Update `README.md` to document everything you add.

## Existing code you need to know about

Render loop, around line 1969:

```js
let lastTime = null;

function frame(ts) {
  requestAnimationFrame(frame);
  if (lastTime === null) lastTime = ts;
  const dt = Math.min((ts - lastTime) / 1000, 0.05);
  lastTime = ts;

  if (!paused && !framePairMode) {
    for (const p of particles) advanceParticle(p, dt);

    if (outOfPlanePct > 0) {
      _camFrameAcc += dt;
      if (_camFrameAcc >= 1/camFps) {
        _camFrameAcc -= 1/camFps;
        refreshOutOfPlane();
      }
    }
  }
  // ... drawing ...
}
```

Frame-pair capture, around line 1947:

```js
function captureFramePair() {
  frameAParticles = particles.map(p => ({ ...p }));
  const dt = 1 / camFps;
  for (const p of particles) advanceParticle(p, dt);
  framePairMode = true;
  paused = true;
  // ...
}
```

Readout displacement, lines ~1435 and ~2053:

```js
const dispPx  = speedPs / camFps;
const tvDisp  = speed / dispFps;
const camDisp = speed / camFps;
```

Relevant globals: `camFps`, `dispFps`, `particles`, `advanceParticle(p, dt)`,
`paused`, `framePairMode`, `frameAParticles`, `W`, `H`, `ctx`, `bgColor`,
`drawParticles(arr, sprite)`, `getSprite()`, `_camFrameAcc`,
`refreshOutOfPlane()`, `outOfPlanePct`, and a seeded `mulberry32` PRNG.

## The defect

Motion and ground truth come from two different clocks.

Particles advance by `dt`, the **real elapsed wall-clock time** between
`requestAnimationFrame` callbacks. But the readout reports the displacement that
*would* occur if the frame interval were exactly `1/camFps`. These diverge
whenever the browser hiccups — GC pause, compositor stall, background tab — and
nothing surfaces that it happened.

`Math.min(dt, 0.05)` makes it worse: on a 200 ms stall the particles advance by
only 50 ms of motion while the readout keeps quoting the ideal number. The error
is silent and unbounded.

Separately, `dispFps` is a user-typed number used **only** in the readout, never
in the motion. If the user types 120 and the panel runs at 60 Hz, the
"Δpx / TV frame" figure is simply wrong.

`captureFramePair()` is the one path that does it correctly — deterministic
`dt = 1/camFps`. That is the model to follow.

---

## Requirement 1 — Deterministic step mode

Add a mode where the simulation advances by an **exact fixed timestep per
rendered frame**, decoupled from the wall clock.

- New control in the Timing section: **Deterministic step** toggle (default off,
  so current behavior is preserved).
- New numeric input **Step rate** `stepFps` (default 30, range 1–240). When
  deterministic mode is on, every `requestAnimationFrame` callback advances the
  sim by exactly `1 / stepFps` seconds, regardless of measured `dt`.
- The clamp `Math.min(..., 0.05)` must not apply in this mode.
- `_camFrameAcc` / `refreshOutOfPlane()` must also key off the deterministic
  step, so out-of-plane dropout stays one refresh per step.

**Critical subtlety — get this right and surface it in the UI.** In
deterministic mode the displacement between two consecutive *display refreshes*
is exactly `speed / stepFps` pixels. The apparent real-time speed is therefore
scaled by `refreshRate / stepFps`. The operator must set their camera frame rate
to the panel refresh rate, or to an integer divisor `k` of it — in which case
the displacement per *camera* frame is `k × (speed / stepFps)`.

Add a readout block that states, live:

- Commanded Δpx per **rendered** frame
- Measured panel refresh rate (Hz) — from Requirement 3
- Integer ratio `k = round(refresh / cameraFps)` and whether it is close to
  integer (warn in amber if `|refresh/cameraFps − k| > 0.02`)
- Resulting Δpx per **camera** frame
- Effective sim-time scale factor `refresh / stepFps`

Warn clearly if deterministic mode is on and the refresh rate is unstable.

## Requirement 2 — Optical frame counter and tear detector

The screen must self-report, in the captured image, which rendered frame it is.
This is what lets a high-speed camera count actual rendered frames and detect
drops and tearing without trusting the browser.

Render, on every frame:

- A **binary-coded block strip**: 12 square blocks, each 24×24 px, LSB leftmost,
  white (`#fff`) = 1, black (`#000`) = 0, encoding `frameIndex mod 4096`.
- Immediately left of the strip, one extra **clock block** that toggles
  black/white every single rendered frame. This detects a repeated frame even if
  the count is misread.
- Render the **entire strip twice**: once top-left, once bottom-right, both
  encoding the same index. If the panel tears mid-refresh, the two copies will
  disagree in the captured image, which makes tearing directly observable.
- Blocks must be pure black and pure white with hard edges — no antialiasing, no
  blending. Draw them **after** everything else, and make sure the additive
  (`lighter`) particle blending does not touch them (save/restore composite op).
- Toggle: **Frame code** button, default **on**. Position selectable
  (corners / all four). Block size adjustable 8–48 px, since it depends on the
  camera's spatial resolution at the screen.

## Requirement 3 — Timing telemetry

Measure and expose what the browser is actually doing.

Maintain a rolling window (last 600 rendered frames) of real inter-frame
intervals from the `requestAnimationFrame` timestamp, and compute:

- Measured refresh rate (Hz) = 1 / median interval
- min / mean / median / max interval (ms)
- Standard deviation of interval (ms)
- **Dropped-frame count**: intervals exceeding 1.5 × median, counted, with the
  implied number of missed refreshes
- Longest single stall (ms) and when it occurred (frame index)
- Cumulative frame count since last reset

Display a compact live panel (toggleable, default on during deterministic mode).
Colour the jitter figure: green if σ < 1 ms, amber 1–3 ms, red > 3 ms.

Also compute and display **`u_Δt / Δt`, the implied relative velocity
uncertainty from timing alone** — this is σ_interval / mean_interval expressed as
a percentage. It is the single most decision-relevant number on the screen.

Add a **Reset telemetry** button, and reset automatically when any flow or
timing parameter changes.

## Requirement 4 — True A/B step capture

The existing frame-pair mode composites Frame A (red) and Frame B (green) into
one displayed image. That is useful for reading Δpx by eye, but a camera
photographing it captures a *single* frame containing both — not two images
separated in time. It cannot generate a real PIV image pair.

Add a **Step-pair mode** alongside (do not remove the existing overlay mode):

- Displays **only Frame A**, normally rendered, for `holdFrames` rendered frames
  (default 10, adjustable 1–120).
- Then advances the sim by exactly `1 / stepFps` and displays **only Frame B**
  for `holdFrames` rendered frames.
- Then either stops, or loops (A→B→A→B…) if **Loop** is enabled, advancing one
  step each transition.
- During step-pair mode the frame-code strip must additionally encode which
  phase is displayed — reserve the top bit: 0 = A, 1 = B.
- A large on-screen phase badge (`A` / `B`) outside the region the camera will
  use for PIV, toggleable.

Bind to an unused key and add a button.

## Requirement 5 — Run manifest export

There is currently `exportQACSV()` for results, but no way to save or reload a
*configuration*, and no way to record what the timing actually did.

Add:

- **Export run manifest** → downloads a JSON file containing: every flow,
  particle, shape, variability, noise, timing, flume, and obstacle parameter;
  the particle seed; the scale calibration; the full telemetry summary from
  Requirement 3; `stepFps`; `holdFrames`; user agent; screen resolution;
  `devicePixelRatio`; and an ISO 8601 timestamp.
- **Import run manifest** → file picker that restores every setting exactly,
  including the seed, so a run is bit-reproducible.
- Filename: `YYYYMMDD_HHMMSS_pivgt_manifest.json`.
- Add a **schema version** field. Set it to `1`.

## Out of scope for this task

Do not implement these now, but do not architect in a way that blocks them:
gamma/linearity compensation and gray-step wedge, burned-in run header text on
canvas, dot-grid calibration pattern mode, scripted condition sweeps, QR/
datamatrix config encoding.

---

## Acceptance criteria

1. Existing behaviour is unchanged with all new toggles off.
2. With deterministic mode on and a screen recording at the panel refresh rate,
   the measured particle displacement between consecutive recorded frames equals
   `speed / stepFps` pixels to within the sub-pixel measurement noise.
3. The frame-code strip decodes to a strictly incrementing sequence in a
   high-speed camera recording; deliberately stalling the browser (open a heavy
   tab) produces a visible gap in the decoded sequence **and** a matching
   dropped-frame count in the telemetry panel.
4. The two frame-code copies agree in every untorn frame.
5. Step-pair mode produces recordings in which Frame A and Frame B appear in
   temporally distinct, separately capturable frames.
6. Exporting a manifest, changing every setting, then importing it restores an
   identical particle field and identical readouts.
7. Telemetry `u_Δt/Δt` reads < 0.5% on an idle machine and rises visibly when
   the machine is loaded.
8. Everything still runs from a `file://` URL with no server.

## Deliverables

- Modified `piv_ground_truth.html`
- Updated `README.md` covering all new controls, the new keyboard shortcuts, the
  deterministic-mode camera-sync guidance from Requirement 1, and how to decode
  the frame-code strip
- A short `VERIFICATION.md` giving the step-by-step lab procedure an operator
  follows to check acceptance criteria 2, 3, and 4 with a high-speed camera
