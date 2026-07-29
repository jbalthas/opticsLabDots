# Smart-Rocks PIV Validation — Master Roadmap

**Project:** Physical ground-truth validation of the lab's PIV/LSPIV velocity algorithm using instrumented ("smart") rocks in the flume.
**Lab:** USGS Camera and Imaging Systems Evaluation Laboratory.
**Status:** Foundation / planning. Hardware not yet locked.
**Last updated:** 2026-06-30.

---

## 1. The core idea in one paragraph

The lab already has a **synthetic** ground truth: `piv_ground_truth.html` renders a particle field moving at an analytically known velocity, and you compare your PIV system's measured velocity against that known value (the readout grades error PASS < 5% / WARN 5–15% / FAIL > 15%). That proves the algorithm is correct *against an idealized image*. It does **not** prove the algorithm is correct against **real water carrying real objects**, where lighting, free-surface distortion, seeding irregularity, and genuine 3D motion all intrude. The smart rocks close that gap: each rock reports its own position and velocity from onboard sensors, giving an *independent physical truth* to compare the PIV output against — in the same flume, at the same instant, under real imaging conditions. The simulator validates the math; the smart rocks validate the math *in the field*. The paper is about the algorithm, and these two validation tiers are its evidence base.

---

## 2. Validation architecture: three sources of truth

```
                 ┌─────────────────────────┐
   SYNTHETIC ───▶│  piv_ground_truth.html  │── known V(x,y), Δpx/frame
   (idealized)   └─────────────────────────┘        │
                                                     ▼
                 ┌─────────────────────────┐   ┌───────────────┐
   IMAGED     ──▶│  Flume + camera + rocks │──▶│  PIV / LSPIV  │── measured V
   (real)        └─────────────────────────┘   │   algorithm   │
                            │                   └───────────────┘
                            │ RFID id + IMU + pressure                │
                            ▼                                         ▼
                 ┌─────────────────────────┐            ┌────────────────────┐
   PHYSICAL   ──▶│  Smart-rock ground truth│───────────▶│  Error / agreement │
   (in-situ)     │  position + velocity    │            │  metrics + report  │
                 └─────────────────────────┘            └────────────────────┘
```

The decisive design principle (carried over from the lab's standing QA position): **the algorithm's measurement must remain independent of the image-acquisition chain.** The smart-rock truth is derived from sensors that do *not* touch the imaging path, which is exactly what makes it a valid independent reference. Guard this independence everywhere — do not, for example, use the camera to help calibrate the rock's position and then call the rock an independent truth.

---

## 3. Phases and milestones

### Phase 0 — Foundation (now)
- [x] Working synthetic simulator (`piv_ground_truth.html`) with frame-pair Δpx capture and graded error readout.
- [x] FastAPI backend for camera/image-quality analysis (`backend/`).
- [ ] This roadmap agreed and circulated.
- [ ] **Decision gate D1:** flume environment (dry / wet / submerged) + channel width. *Blocks all antenna and reader design.*
- [ ] **Decision gate D2:** collaboration model (USGS-only vs. + university/postdoc co-authors). *Shapes authorship, data sharing, and timeline.*

### Phase 1 — Smart-rock sensing proven on the bench (dry)
- [ ] Lock tag chemistry/frequency (working assumption: **LF 134.2 kHz PIT**; confirm against D1).
- [ ] Read a single moving tag reliably across the antenna field; characterize read range, read rate, and orientation tolerance.
- [ ] Log IMU (6/9-axis) + optional pressure, timestamped and clock-synced to the camera.
- [ ] **Deliverable:** smart-rock data spec (see §5) frozen.
- [ ] **Milestone M1:** one rock, tracked on a bench, position+velocity recovered to a stated uncertainty.

### Phase 2 — Single rock in the flume
- [ ] Waterproof/encapsulate; verify read performance under the real water condition from D1.
- [ ] Time-synchronize rock log ↔ camera frames (this is the make-or-break detail; see §6).
- [ ] First side-by-side: PIV-measured velocity vs. rock-reported velocity for a single pass.
- [ ] **Milestone M2:** first real PIV-vs-physical error number, with an honest uncertainty budget.

### Phase 3 — Multi-rock / distribution
- [ ] Several rocks, distinct RFID IDs, simultaneous tracking.
- [ ] Sweep flow regimes; build a velocity-distribution comparison (ties naturally to the existing SynPIX / DOT-simulator distribution work).
- [ ] **Milestone M3:** statistically meaningful agreement (or disagreement) across the operating envelope.

### Phase 4 — Publication
- [ ] Lock the claims the paper will make (see §7) and confirm each is supported by M1–M3 evidence.
- [ ] Draft, internal USGS review, co-author review, submit.
- [ ] **Milestone M4:** manuscript submitted.

---

## 4. Open hardware decisions (DO NOT treat as settled)

These are live questions, not conclusions. The working assumptions are recorded so the team argues against something concrete.

| Decision | Working assumption | Why it's still open | What unblocks it |
|---|---|---|---|
| Frequency | LF **134.2 kHz** PIT (not UHF) | UHF is killed by water/rock attenuation; LF penetrates and tolerates tumbling tag orientation — strong default, but confirm range is adequate at your channel width | Bench read-range test at D1 condition |
| Tag | Biomark ISO HDX / Destron Fearing 12×2.1 mm; 23 mm glass for more range | Bigger tag = more range but a bigger hole drilled in the rock | Rock size + required range |
| Reader | RDM6300 (cheap) or ID-20LA | DIY LC resonance tuning is the hard part; module choice affects it | Antenna geometry from D1 |
| Antenna | Flat overhead loop ~30×40 cm | Size and tuning depend entirely on channel width + submersion (D1) | **D1** |
| IMU | 6- or 9-axis, dead-reckoning for velocity | IMU drift may dominate error over a pass; may need RFID gate crossings to bound it | Phase-1 drift characterization |
| Pressure | Optional, for depth/free-surface | Only worth it if depth is part of the truth you need | Define what "position" must include |

**Critical dependency:** almost everything in this column waits on **D1 (flume environment + channel width)**. Resolve D1 first.

---

## 5. Smart-rock data spec (to be frozen in Phase 1)

Minimum fields each rock should emit per sample, so the truth aligns cleanly with PIV output:

- `rock_id` — RFID UID (which rock).
- `t` — timestamp on a clock synchronized to the camera (see §6). The single most important field.
- IMU: `ax,ay,az`, `gx,gy,gz` (and `mx,my,mz` if 9-axis).
- `pressure` (optional) → depth.
- Derived (post-processed, not on-device): `x,y(,z)` position and `vx,vy(,vz)` velocity, each with an uncertainty estimate.

Mapping to PIV: the PIV algorithm reports velocity over interrogation windows in image space; the rock reports velocity in physical space. Reconcile through the simulator's existing **scale calibration** (mm↔px, computed per-axis so non-square pixels show up). Keep that calibration in one place and reuse it for both the synthetic and physical paths.

---

## 6. The two risks most likely to sink this

1. **Time synchronization (rock clock ↔ camera frame).** A velocity comparison is only as good as the alignment of the two time bases. A few milliseconds of skew at flume speeds is a real position error. Plan an explicit sync mechanism (shared trigger, LED/RFID gate event visible to both, or PTP-style clock discipline) and *measure* the residual skew rather than assuming it.
2. **IMU drift masquerading as truth.** Dead-reckoned velocity from an IMU drifts; if uncharacterized, you could "validate" PIV against a degrading reference. Bound IMU drift with RFID gate crossings (known positions at known times) and carry an explicit uncertainty budget so the "ground truth" is never quoted as exact.

A third, quieter risk: **letting the truth depend on the camera.** If rock position is ever inferred with help from the imaging chain, the independence that justifies the whole experiment is lost (see §2).

---

## 7. Paper scaffold (algorithm-focused)

- **Claim 1 — Correctness:** the algorithm recovers known velocity fields. *Evidence:* simulator across all five flow types (uniform, linear shear, solid vortex, Poiseuille, Rankine), graded error.
- **Claim 2 — Real-world validity:** correctness holds against independent physical truth in real imaging conditions. *Evidence:* M2/M3 PIV-vs-rock agreement with uncertainty budget.
- **Claim 3 — Envelope:** the regimes where it holds and where it degrades. *Evidence:* Phase-3 sweep.
- **Methods anchor:** the dual ground-truth design (synthetic + physical) is itself a contribution — a reusable validation methodology, not just a result.
- **Authorship / collaboration (decision D2):** decide early whether university/postdoc partners are co-authors, because it affects who runs which experiments and how data is shared. Settle author order and data-sharing terms before Phase 2 generates the headline numbers.

---

## 8. Immediate next actions

1. Resolve **D1** (flume environment + channel width) — unblocks all hardware.
2. Resolve **D2** (collaboration model) — unblocks authorship/timeline.
3. On D1, return to the **antenna tuning math and reader wiring** (the DIY LC-resonance step we left off on).
4. Freeze the **§5 data spec**, then build the **§2 comparison/metrics** module against the existing FastAPI backend.

*Open items D1 and D2 are the gates. Everything downstream is cheap to plan and expensive to redo, so decide these two first.*
