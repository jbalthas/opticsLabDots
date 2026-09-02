# PIV Ground Truth — Verification Procedure

**Purpose.** Prove, with a high-speed camera and no appeal to the browser's own claims, that `piv_ground_truth.html` displays the displacement it reports. Complete this before the tool is used as a reference standard in any published validation study, and re-run it whenever the display, the machine, the browser, or the GPU driver changes.

**What this procedure establishes.**

| # | Acceptance criterion |
|---|---|
| **2** | With deterministic mode on, measured particle displacement between consecutive recorded frames equals `speed / stepFps` px to within sub-pixel measurement noise |
| **3** | The frame-code strip decodes to a strictly incrementing sequence; a deliberate browser stall produces a visible gap **and** a matching dropped-frame count in telemetry |
| **4** | The two frame-code copies agree in every untorn frame |

Record results on the log sheet at the end. File under `/Data/Research/PIV/` with the exported run manifest.

---

## 0. Equipment and prerequisites

| Item | Requirement |
|---|---|
| Display under test | The PIV TV, in its final lab position and picture mode |
| High-speed camera | Frame rate ≥ 4 × the panel refresh rate. At 60 Hz, ≥ 240 fps |
| Lens | Able to resolve one frame-code block across ≥ 4 camera pixels at the working distance |
| Machine | The machine that will drive the TV during the study — not a substitute |
| Analysis | Any frame-by-frame image tool. MATLAB, ImageJ, or `MatlabScripts/` |

**Before starting:**

1. Complete the **PIV Calibration Protocol** (6 steps) in `.claude/rules/protocols.md` — 30 min TV warm-up, luminance uniformity, gamma, white point, mura check, display identification.
2. Lab in **PIV / Display Mode**: ceiling lights off or at a logged level, TV at its named floor position, softboxes not operating simultaneously with the TV in Position A.
3. Close every other application and browser tab on the driving machine. Disable OS notifications, screen savers, automatic updates, and any background sync client. These are the dominant source of dropped frames.
4. Open `piv_ground_truth.html`, click the splash to enter fullscreen, and confirm it is running from `file://`.
5. **Confirm the display is 1:1.** Browser zoom at 100 % (`Ctrl`+`0`) and OS display scaling at 100 %. If the red *DEVICE PIXEL RATIO* banner is showing, the compositor is resampling the canvas: the particle image is interpolated a second time and every px/mm figure is wrong by that factor. Fix it and reload before doing anything else — no amount of clean timing rescues a resampled canvas.

> **Panel refresh vs. camera frame rate.** Steps 1–3 need the camera running fast enough to see individual panel refreshes. Steps 4–5 need the camera phase-locked to the panel. Do not skip §2.3.

---

## 1. Establish the panel's actual refresh rate

The tool must not be trusted to tell you the refresh rate until you have watched it settle.

1. Press `T` to open the **Metrology** panel (bottom-left).
2. Press `D` to enable **Deterministic step**. The metrology panel opens automatically if it was closed.
3. Set **Step rate** to `30`.
4. Let it run undisturbed for **60 seconds**. Do not move the mouse — cursor motion is itself work.
5. Click **Reset telemetry**, then let it run a further **60 seconds** so the whole 600-frame window is post-reset.

> **Shortcut — but read the gate first.** Pressing `A` turns on **auto-lock
> timing**, which performs steps 5–6 and §2.2 for you: it waits for a full clean
> 600-frame window, then sets the step rate to the measured refresh exactly. It
> applies the *same* gate as the table below, and while the gate fails it reports
> **BLOCKED** and diagnoses the cause rather than locking. It is a convenience
> for the arithmetic, not a substitute for the operator confirming the numbers —
> record them from the panel either way.
>
> Auto-lock does **not** set camera fps. That describes your physical camera; it
> computes the correct rate and you apply it once the camera is really there.
6. Record from the panel:

   - Measured refresh (Hz)
   - min / median / max interval (ms)
   - σ (jitter)
   - **u<sub>Δt</sub> / Δt**
   - Dropped frames and implied missed refreshes
   - Longest stall

**Gate — do not proceed unless all of these hold:**

| Check | Requirement |
|---|---|
| u<sub>Δt</sub> / Δt | **< 0.5 %** (green) |
| σ (jitter) | **< 1 ms** (green) |
| Dropped frames | **0** |
| Measured refresh | Within 0.5 Hz of the panel's nameplate rate |
| Device pixel ratio | **1.000** — green, no banner |
| Render cost / frame | **< 30 %** of the median interval (green). Run this gate with all noise at **0**; noise is the only setting that writes every pixel and it is what moves this figure |
| Pair loss / cam frame | Recorded, not gated. Note it on the log sheet — it is the fraction of particles that cross the periodic boundary between A and B and therefore contribute noise rather than signal |
| N<sub>I</sub> | Recorded. If it is below ~8, say so on the log sheet: the correlation is running below the seeding density PIV practice assumes, and that is a property of the run, not of the algorithm |

If any fails, the machine is not quiet. Find and stop the offending process, reset telemetry, and repeat.

Auto-lock's BLOCKED panel lists the failing checks and then a diagnosis in the order worth checking. The one most often missed: a measured refresh sitting **near** a standard panel rate but not on it, with a jittery interval, is a **variable-refresh display** (G-SYNC / FreeSync / VRR). A panel that changes its own refresh rate cannot be a timing reference — turn adaptive sync off for this display and set a fixed rate before doing anything else. If the machine cannot sustain a high refresh, set the panel to a fixed 60 or 120 Hz: nothing in this stimulus needs a fast panel, and every figure here rests on the interval being repeatable. A red *REFRESH UNSTABLE* warning means deterministic mode is silently dropping sim steps — the field falls behind real time while Δpx per rendered frame stays correct.

Call the settled value **R** Hz.

---

## 2. Configure the run

### 2.1 Flow

Use the simplest possible case for the geometric check:

| Control | Value |
|---|---|
| Flow type | **Uniform** |
| Vx | `0.08` m/s |
| Vy | `0` |
| Turbulence | `0` |
| Count | `400` |
| Min / Max diameter | `2` / `4` px |
| Out-of-plane % | `0` |
| All noise | `0` |
| Obstacle | none |
| Flume | off |

Set the **Particle Seed** to a recorded integer (e.g. `20260812`) so the field is reproducible.

Record the **Particle image d<sub>τ</sub>** shown in the Particles section — at 2 / 4 px diameters that is 4–8 px. This is the figure that governs sub-pixel bias, and it is what belongs on the log sheet and in the methods section, not the slider values.

Leave **Linear light** off unless you have a measured display gamma from the calibration protocol. If you turn it on, record the γ you used; the stimulus is not the same stimulus.

### 2.2 Deterministic step

- **Deterministic step**: on (`D`)
- **Step rate**: press **Match refresh (N)**. This sets the step rate to the measured refresh **R** from §1.

> **Do not leave the step rate at its default of 30 on a 60 Hz panel.** The sim-time scale would be 2.000, and a PIV package — which divides Δx by the *real* camera interval — would report **twice** the True Speed readout. That is a 100 % apparent error caused entirely by the mode. The metrology panel raises an amber *SIM TIME ≠ REAL TIME* warning whenever the scale is off 1.000 by more than 2 %.
>
> With auto-lock on this is done for you and the scale reads `×1.000` exactly —
> it locks to the measured refresh without rounding, so there is no residual.
>
> Confirm **Sim-time scale** reads `×1.000` before recording. If you deliberately need a scale other than 1 (to slow a fast channel, say), record the factor on the log sheet and divide every measured velocity by it.

Read **Δpx / rendered frame** from the metrology panel and record it. It should equal `Ref Speed (px/s) ÷ stepFps` from the bottom readout. Call this **Δ**.

At scale 1.000 with camera fps = R, Δ also equals `Ref Speed ÷ camFps` — the deterministic and nominal figures coincide. That agreement is a useful pre-flight check that everything is consistent.

### 2.3 Camera frame rate

Read **refresh / cam fps → k** from the metrology panel.

- For **§3 (frame counting)**, set the camera as fast as it will go — you want several camera frames per panel refresh so no refresh is missed.
- For **§4 (displacement)**, set **camera fps = R** exactly, or `R / k` for an integer `k`. The panel shows amber and names the nearest correct fps if the ratio is not within 0.02 of an integer. **Do not proceed in amber.**

At 60 Hz: 60 fps (k=1), 30 fps (k=2), 20 fps (k=3), 15 fps (k=4) are all valid. 24 fps is **not**.

### 2.4 Frame code

- **Frame code**: on (`G`)
- **Position**: `Top-left + bottom-right`
- **Block size**: large enough that one block spans ≥ 4 camera pixels at your working distance. Start at `24` and increase if the blocks are marginal

### 2.5 Frame the shot

Aim the camera so that **both** frame-code strips — top-left and bottom-right — are fully inside the field of view, along with the central particle region. If the lens cannot cover both corners plus usable particles, either move back or switch **Position** to `All four corners` and use whichever pair fits.

Press `H` to hide the control panel and `T` to hide the metrology panel before recording, so the overlays do not contaminate the image. Telemetry keeps accumulating while hidden.

### 2.6 Export the manifest

Press `[R]` to re-seed, **then** click **Export run manifest**. Store `YYYYMMDD_HHMMSS_pivgt_manifest.json` alongside the footage.

> **Re-seed first, or the manifest will not rebuild this run.** Any in-place control — particle count, diameter, ρ, ρ variability, turbulence, intensity or diameter variation — patches the existing field instead of rebuilding it, which leaves the layout no longer derivable from the seed. `[R]` restores the canonical layout.
>
> The export notice states either `bit-reproducible` or `NOT bit-reproducible` with the reason, and the manifest's `reproducibility` block records the same. **Confirm it reads bit-reproducible before recording.** For §3 and §4 it will, because those run with out-of-plane % and all noise at 0. If you deliberately enable dropout or noise for a later run, the realisation is not reproducible even though the configuration is — note that on the log sheet.

---

## 3. Criterion 3 & 4 — frame counting and tear detection

### 3.1 Clean baseline recording

1. Set the camera to its maximum frame rate (≥ 4 R).
2. Record **10 seconds** with the machine idle.
3. Transfer the footage.

### 3.2 Decode

For each recorded frame in which the strip is sharp:

1. Locate the strip: the quiet zone starts at the canvas corner; the strip is inset 4 px; total width is `13 × blockSize`.
2. Sample the **centre pixel** of each of the 13 blocks. Threshold at 50 % — blocks are pure 0 or 255.
3. Block 0 is the **clock**. Blocks 1–12 are data bits 0–11, **LSB leftmost**.
4. `index = Σ bit_b × 2^b` for b = 0…11.

Do this for **both** the top-left and bottom-right strips.

### 3.3 Checks

| Check | Expected | Criterion |
|---|---|---|
| Decoded index, deduplicated across repeated camera frames | Strictly incrementing by 1, wrapping 4095 → 0 | **3** |
| Clock block | Alternates on every change of index | **3** |
| Top-left index vs bottom-right index, **same camera frame** | Identical in every frame | **4** |

Any frame where the two copies disagree is a **torn** frame. Record the count and the fraction of total frames. Occasional tearing that correlates with nothing may be acceptable for your study; systematic tearing is a display or compositor configuration problem and must be resolved before proceeding.

> Because the camera is faster than the panel, each rendered frame appears in several consecutive camera frames with the same index. Deduplicate before checking monotonicity. The clock block is what distinguishes "the panel showed the same frame twice" from "the camera saw the same frame twice".

### 3.4 Deliberate-stall recording

1. Press `T`, click **Reset telemetry**, press `T` again to hide it.
2. Start recording.
3. After ~3 s, open a heavy tab in a **second browser window** on the same machine — a large video, a WebGL benchmark, or a heavy compile. Something that will genuinely contend for the GPU and main thread.
4. Record a further ~7 s, then stop and close the heavy tab.
5. Press `T` and read **Dropped frames**, **implied missed refreshes**, and **Longest stall**.

**Checks:**

| Check | Expected | Criterion |
|---|---|---|
| Decoded index sequence | Shows one or more **gaps** — indices skipped entirely | **3** |
| Total skipped indices across all gaps | **Matches the implied missed-refresh count** in telemetry, ± a small margin for gaps at the recording boundaries | **3** |
| Longest gap in the decoded sequence | Consistent with **Longest stall (ms)** ÷ median interval | **3** |

This is the point of the whole exercise: the image itself reports the drop, and the tool's own telemetry independently agrees. If the decoded gaps and the telemetry disagree substantially, stop — one of the two is not measuring what it claims.

---

## 4. Criterion 2 — displacement equals `speed / stepFps`

### 4.1 Record

1. Restore a quiet machine. Reset telemetry and re-confirm the §1 gate (u<sub>Δt</sub>/Δt < 0.5 %, 0 dropped).
2. Set camera fps to **R** exactly (k = 1), verified green in the metrology panel.
3. Record **10 seconds**.

### 4.2 Measure

1. Extract consecutive frame pairs whose decoded frame-code indices differ by exactly **1**. Discard every pair that does not — this is why the frame code exists.
2. For each pair, measure the particle-field displacement. Either:
   - **Preferred** — run your PIV package on the pair with a window large enough to bracket Δ comfortably (Δ ≤ ¼ window), and take the modal displacement across the field; or
   - **Independent** — compute the 2D cross-correlation of the two full frames (masking out the frame-code corners) and locate the peak to sub-pixel precision by Gaussian three-point fit.
3. Convert to pixels **on the display**, correcting for the camera's magnification. Use a known on-screen dimension for this — the frame-code strip is exactly `13 × blockSize` px wide and is the most convenient ruler in the image.

### 4.3 Check

| Quantity | Expected |
|---|---|
| Mean measured displacement per rendered frame | **Δ = Ref Speed ÷ stepFps**, from §2.2 |
| Deviation | Within your sub-pixel measurement noise — typically ≤ 0.1 px for a well-resolved field |
| Standard deviation across pairs | Small and **not** growing with time |

**Criterion 2 passes** when the mean measured displacement equals Δ within measurement noise.

### 4.4 Repeat at k = 2

Set camera fps to `R / 2` (30 fps at a 60 Hz panel) and repeat §4.1–4.3. Consecutive camera frames now differ by **2** in the decoded index, and the expected displacement is `2 × Δ`. Confirm the metrology panel's **Δpx / camera frame** figure matches what you measure.

This is the check that the `k` arithmetic in the panel is not just arithmetic.

---

## 5. Criterion 5 — step-pair produces a real image pair

A sanity check that the A/B sequencer yields temporally distinct, separately capturable frames.

1. Set **Hold frames** to `10` and enable **Loop**, then press `S` to start **step-pair**.

   > Set the field up *before* starting the mode. Re-seeding, changing the particle count, or resizing the window drops out of step-pair automatically — Frame A was captured from the old field, so the tool refuses to present a stale pair. If the `[S]` button reads *Start A/B* when you expected *Stop A/B*, something rebuilt the field; restart it.

2. Record at ≥ R fps for 5 seconds. Do not press `P` — pause freezes the sequencer.
3. In the footage, confirm:
   - Frames containing **only** Frame A alternate with frames containing **only** Frame B — never both composited
   - Each phase persists for ~10 rendered frames
   - The frame-code **bit 11** is `0` while A is shown and `1` while B is shown
   - The displacement between the last A frame and the first B frame equals **Δ**

Any adjacent A-frame and B-frame from the recording is a valid PIV image pair with a known, exact displacement.

---

## 6. Log sheet

```
PIV GROUND TRUTH — VERIFICATION RECORD

Date / operator ......................................................
Display make / model / serial ........................................
Firmware / picture mode ..............................................
Driving machine / OS / browser + version .............................
GPU / driver version .................................................
Camera make / model / lens / frame rate ..............................
Working distance / camera px per frame-code block ....................
Manifest file ........................................................
Re-seeded [R] before export .............................. [ ] YES
Export notice read "bit-reproducible" .................... [ ] YES
  if NOT, reason recorded ............................................

§1  PANEL TIMING (60 s post-reset window)
    Measured refresh R ..................... Hz    nameplate ....... Hz
    Interval min / median / max ............ / ......... / ......... ms
    Jitter sigma ........................... ms      [ ] < 1 ms
    u_dt / dt .............................. %       [ ] < 0.5 %
    Dropped frames ......................... (missed ..........)  [ ] 0
    Longest stall .......................... ms @ frame ..............
    GATE PASSED                                              [ ] YES

§2  RUN CONFIGURATION
    Seed ................  Step rate .......  Ref speed .......... px/s
    Sim-time scale = refresh / stepFps ......... [ ] 1.000 confirmed
      if not 1.000, divisor applied to all measured velocities ........
    Delta = speed / stepFps .................................... px
    Frame-code block size ......... px    Position ..................
    Camera fps ............  k = ........   ratio error ............

§3  FRAME COUNTING  (criterion 3)
    Clean recording: frames decoded ............ gaps ..............
    Index strictly incrementing                              [ ] PASS
    Clock alternates on every index change                   [ ] PASS
    Stall recording: decoded gaps ........ skipped indices .........
    Telemetry implied missed refreshes .............................
    Decoded skips match telemetry                            [ ] PASS

§3  TEAR DETECTION  (criterion 4)
    Frames compared ............ disagreements ...............
    Tear fraction ............. %
    Two copies agree in every untorn frame                   [ ] PASS

§4  DISPLACEMENT  (criterion 2)
    k = 1:  expected .......... px   measured .......... +/- ....... px
            deviation .......... px                          [ ] PASS
    k = 2:  expected .......... px   measured .......... +/- ....... px
            deviation .......... px                          [ ] PASS
    Measurement method ...........................................

§5  STEP-PAIR  (criterion 5)
    A and B temporally distinct                              [ ] PASS
    Phase bit tracks displayed phase                         [ ] PASS
    A-to-B displacement .......... px  vs Delta .......... px

OVERALL                                                      [ ] PASS
Notes / deviations ...................................................
......................................................................
Signature ....................................  Date .................
```

---

## 7. Failure triage

| Symptom | Likely cause | Action |
|---|---|---|
| u<sub>Δt</sub>/Δt won't go below 0.5 % | Background process, browser extension, power-saving GPU state | Quiet the machine; set the OS power plan to high performance; disable extensions |
| Dropped frames with an idle machine | Compositor or vsync misconfiguration; display doing frame interpolation | Turn off all TV motion-smoothing / interpolation picture settings; confirm the browser is not throttled |
| Copies disagree frequently | Panel tearing; vsync off | Enable vsync; avoid windowed mode; re-run fullscreen |
| PIV reports ~2× (or R/stepFps ×) the True Speed readout | Sim-time scale is not 1.000 — the mode is running sim time faster than real time | Press **Match refresh**; confirm *Sim-time scale* reads `×1.000` |
| Measured displacement is a consistent multiple of Δ | Camera fps is not R — you are sampling every k-th refresh | Re-check `k` in the metrology panel |
| Measured displacement drifts over the recording | Camera and panel are not phase-locked; ratio error > 0.02 | Set camera fps to the value the amber warning names |
| Decoded indices repeat rather than increment | Camera faster than panel — expected | Deduplicate on the clock block before checking monotonicity |
| Blocks read as grey | Blocks under-resolved, or camera exposure clipping | Increase block size; refocus; check exposure |
| Only two strips appear with **Position = all four** | Window too narrow for two strips on one row; the tool fell back to the diagonal pair | Widen the window or reduce block size. The two strips shown are correct — use them |
| Step-pair stopped on its own | Something rebuilt the field (re-seed, particle count, resize) and the mode dropped out to avoid a stale pair | Settle the configuration first, then press `S` |
| A and B both visible in one recorded frame | Not step-pair — this is the overlay frame-pair mode `[C]` | Press `Esc`, then `S` for step-pair |

---

## 7A. Sub-pixel displacement sweep (algorithm characterisation)

This is not part of verifying the *standard* — it uses the verified standard to
characterise the *instrument under test*. Run it after §1–§4 pass, with the
algorithm parameters frozen (per R4 in the research plan, freeze them before
Tier 1).

**Setup.** Deterministic mode on, step rate = measured refresh **R**, camera fps
= R or an integer divisor, frame code on, DPR 1.000, all noise at 0 for the
first pass. Record the particle image d<sub>τ</sub> and N<sub>I</sub>.

1. Press `W`. Set **Start 0**, **End 1**, **Step 0.1**, **Angle 0**.
2. Set **Hold frames** so each phase lasts comfortably longer than one camera exposure — 10 is a reasonable start at R = 60.
3. Press `H` to hide the control panel, leave the sweep panel open only if it is outside the camera's field of view, and record the whole sweep.
4. Decode the frame-code strip on each captured frame and use the panel's **frame A / B** column to match every captured pair to its commanded Δ. No timing assumption is needed for this step — the index is in the image.
5. Process each pair through your PIV package with the settings you intend to freeze. Take the median displacement over the central region, away from the boundaries where the periodic wrap unpairs particles.
6. Type each measured Δ into the sweep panel. Read **bias RMS**, **peak-to-peak** and **mean bias**, and export the CSV.

**Repeat at 26.57°** (atan ½). At 0° the y displacement is identically zero, so
a package can look clean on x alone while locking badly in two dimensions.

**Then repeat the whole sweep with realistic noise** (the QA T03 settings are a
reasonable start) and with d<sub>τ</sub> at 2 px and at 4 px. Peak locking is
strongly dependent on particle image diameter — a sweep at one d<sub>τ</sub> is
one point, not a characterisation.

**What to record on the log sheet:** bias RMS and peak-to-peak for each
(angle, d<sub>τ</sub>, noise) combination, with the exported CSV filed alongside
the run manifest and the footage.

> **Interpretation.** A flat bias curve near zero means the peak-fit is doing its
> job. A curve oscillating with period one pixel is peak locking, and its
> amplitude is the systematic you would otherwise carry, unlabelled, into every
> Tier 1 and Tier 2 result. A constant offset with no oscillation is not locking
> — look at the spatial calibration instead.
>
> The tool deliberately does **not** put a pass/fail line on this. The bands in
> the panel are reporting bands; the acceptable level depends on the
> displacement range and the uncertainty target of the study, and that is a
> decision to make and record, not one to inherit from a default.

---

## 8. Scope limits

This procedure verifies the **temporal** ground truth: that the displayed field advances by the stated displacement per rendered frame, and that frame delivery is observable. It does **not** verify:

- **Spatial scale.** The px → mm calibration rests on the entered TV dimensions and resolution. Verify those independently against a physical measurement of the panel's active area.
- **Radiometry.** Gamma, linearity and absolute luminance are out of scope here — see the PIV Calibration Protocol. Gamma/linearity compensation and a gray-step wedge are not yet implemented in the tool.
- **Sub-pixel rendering fidelity.** The particle image is now evaluated analytically at the exact sub-pixel position — there is no bitmap and no interpolation stage — so the *commanded* profile is identical at every sub-pixel phase. What remains uncharacterised is what the **panel** does with it: pixel response, subpixel geometry and the display transfer function. That is MVE-1's photometric half and it is still open.
- **Stochastic realisations.** A manifest reproduces the *configuration and particle layout*. Image noise is now keyed on `(seed, frameIndex)`, so a given frame is regenerable if you can recover its frame index from the frame code — but the manifest does not restore the frame index, so a noisy run is still not bit-reproducible from the manifest alone. Out-of-plane dropout still draws from unseeded randomness by design. A run using either is repeatable in its statistics, not in its pixels. The manifest's `reproducibility` block states this per run.
- **The PIV algorithm.** That is what the QA Suite and the sub-pixel sweep (§7A) inside the tool are for. This procedure verifies the *standard*; those characterise the *instrument under test*.
- **Pass criteria.** The QA thresholds are operator-set and recorded as such. The tool reports its own stimulus u<sub>c</sub> — timing plus spatial scale, in quadrature — so a threshold can be judged against something, and flags any threshold tighter than 2 u<sub>c</sub> as unable to decide anything. That u<sub>c</sub> is a floor, not a budget: it excludes display response and spatial non-uniformity, which is exactly what MVE-1's photometric half is for.
