# Materials List — Smart Rocks + Antenna Setup (Large Flume)

**Context:** Large flume (D1 = large channel), **6 ft wide × 4 ft deep**. Rocks **float on the surface** — they are validation targets for surface-velocity PIV/LSPIV, not bedload. This drives the antenna and reader choice away from a single DIY loop toward a multi-antenna HDX system. Prices are indicative (2026, USD unless noted) — confirm with a quote before ordering.
**Possible vendor/collaborator:** Oregon RFID.

**Confirmed decisions (2026-06-30):**
- **Flume:** 6 ft wide, 4 ft deep. Rocks ride the **surface** (PIV/LSPIV algorithm validation).
- **Tags:** rocks float → no flow-disturbance penalty → use **32 mm HDX+** for max read range/reliability.
- **Rocks are recoverable/reusable** → sealed housings with O-rings, **not** fully potted/disposable.
- **Depth is NOT part of ground truth** → **no pressure sensor**. Position ground truth is 2D surface (x, y).
- Surface float also means **no tumbling/impacts** → **high-g accelerometer not required** (see Part B).
- **Still open:** US pricing + lead times from Oregon RFID; whether they'll partner on antenna tuning.

---

## Why the large flume changes the design

At LF (134.2 kHz), a single loop antenna's read range is roughly its own largest dimension. One ~30×40 cm loop blankets a narrow channel but leaves dead zones across a wide flume. The fix is **multiple tuned antennas along/across the channel, multiplexed into one reader** — which is exactly what Oregon RFID's ORMR is built for (up to 4 antennas, each from inches to >50 m across, with antenna-number logged per detection). For a large flume, multiplex is the path; DIY single-loop is not.

This also means the RFID gives you **position by gate crossing** (which antenna saw the tag, when) rather than continuous position. Continuous position/velocity between gates comes from the **IMU inside the rock**. The two are complementary: RFID bounds IMU drift; IMU fills the gaps between antennas. Keep that division of labor in mind when sizing the array.

**Width-specific note (6 ft flume, surface float):** The read zone must span the full **6 ft (≈1.83 m) width at the water surface**, where the tags ride. A single loop won't blanket that width cleanly, so the array should be **multiple antennas across the width** (multiplexed into the ORMR), giving a cross-channel "gate" the rocks pass through. Because rocks float, the antenna-to-tag distance is just the freeboard above the loop plane — small and consistent — which is the easy case for HDX range. The 4 ft depth is irrelevant to the read; antennas can be surface-mounted or bank-mounted at the water line rather than on the bed.

---

## Part A — RFID detection system (buy, Oregon RFID)

| Item | Spec / why | Indicative price |
|---|---|---|
| **ORMR multi-antenna HDX reader** | Drives up to 4 antennas, multiplexed; internal datalogger (16 GB), GNSS, Bluetooth; logs tag ID + antenna # + time + duration | ~€4,650 (EU list); get US quote |
| *(alt)* **ORSR single-antenna reader** | Cheaper, one antenna only — viable only if one antenna covers the read zone | Lower; quote |
| **Antenna wire** (per antenna) | Multi-strand copper; you build loops sized to the channel. Tuning to resonance is the hard part — Oregon RFID provides tuning guidance/boxes | Wire is cheap; tuning hardware via vendor |
| **Antenna tuning boxes / capacitors** | Bring each loop to 134.2 kHz LC resonance; mismatch kills range | Vendor-supplied; quote |
| **32 mm HDX+ PIT tags** ✅ **CHOSEN** | Max range. Rocks float → no flow-disturbance penalty from the larger bore, so take the range. | ~$1.70/ea, packs of 100 |
| *(not chosen)* 23 mm HDX+ PIT tags | Smaller bore, less range. Only relevant if tag size disturbed flow — it doesn't here. | quote |
| **Tag sleeves** | Protect/seat the tag | ~$0.20/ea |

**Recommendation:** ORMR + antennas spanning the **6 ft width** + **32 mm tags**. For a 6 ft cross-channel gate, plan on **2–4 antennas across the width** (final count is the open question for Oregon RFID — it trades against per-antenna read width and the cross-channel resolution you want). This is the part to talk to **Oregon RFID** about directly — they spec these for river/flume installs routinely, and a collaboration could cover antenna tuning (the trickiest step).

---

## Part B — Smart-rock internals (the IMU logger)

The RFID tag only gives identity + gate crossings. Velocity/attitude *between* gates comes from an onboard inertial logger. Two routes:

### Route 1 — Off-the-shelf logger (fastest to first data)
| Option | What it gives | Notes |
|---|---|---|
| **SparkFun OpenLog Artemis** | 9-axis IMU, logs CSV to microSD, low power | Cheap (~$50–60), well-documented, easy to pot into a housing |
| **SparkFun DataLogger IoT 9DoF** | ISM330DHCX + MMC5983MA, zero-code logging | Similar class |
| **Yost Labs 3-Space Data Logger** | Miniature IMU + microSD + LiPo, calibrated | Higher quality/cost; better attitude solution |
| **LP-Research LPMS-AL2** | IP67 waterproof 9-axis IMU | Rugged, but a sensor not a full logger — pair with logging |

### Route 2 — Purpose-built "kinematic logger" design (best for publication)
Published designs embed a **9-axis IMU + a separate 3-axis high-g accelerometer** (impacts during *bedload* transport exceed normal IMU ranges) + flash + **motion-triggered wakeup** for months of standby. If the paper is the goal, matching/citing this class of design strengthens it. More build effort; better science.

**High-g accelerometer — NOT required here.** That spec exists for tumbling bedload that slams into the bed. **Our rocks float on the surface and don't impact**, so a standard ±2–16 g 9-axis IMU is sufficient — no clipping concern. Drop the high-g channel; it removes build complexity with no loss of dynamics for surface drift. (Keep this in mind only if the design is ever reused for a bedload study.)

### Rock-build consumables (either route)
- Artificial cobble or drilled natural rock (controlled mass/shape → better than natural for first runs). **Must float** — pick/ballast for positive buoyancy so the rock + electronics ride at the surface.
- **Sealed, reusable housing with O-rings** (decision: rocks are recoverable). Machined or molded watertight enclosure that opens to swap battery / pull data, not fully potted-in epoxy. Use epoxy only to shock-mount internals, not to seal them in permanently.
- Small LiPo (sized to deployment duration; motion-wakeup extends it). Rechargeable, since housings reopen.
- ~~Pressure sensor~~ — **not needed**. Depth is not part of ground truth; position is 2D surface.

---

## Part C — Timing & sync (do not skip)

A velocity comparison is only as good as the rock-clock ↔ camera-frame alignment.
- Shared trigger or a visible event (LED flash / RFID gate crossing) that lands in both the camera stream and the rock log.
- The ORMR's GNSS time can anchor the RFID side; the camera side needs to be disciplined to the same reference, and the **residual skew measured**, not assumed.

---

## Suggested first-buy (minimum to get to Milestone M2 = first real PIV-vs-rock number)

1. **1× ORMR reader** + **2 antennas** for the 6 ft cross-channel gate (talk to Oregon RFID re: tuning + final antenna count).
2. **100× 32 mm HDX+ tags** + sleeves (one per rock; spares for loss).
3. **2–3× OpenLog Artemis** loggers (Route 1) to get data fast; evaluate Route 2 (minus the high-g channel) for the publication build.
4. Sealed reusable housings + O-rings, LiPos, a few buoyant artificial cobbles. **No pressure sensor.**
5. Sync hardware (trigger/LED).

Start with **one fully built rock + one antenna pair** end-to-end before scaling to a multi-rock array.

---

## Open items to confirm before ordering
- ✅ ~~Flume width/depth → antennas + tag size~~ — **6 ft × 4 ft, surface float → 32 mm tags, 2–4 antennas across the 6 ft width.**
- ✅ ~~Recoverable vs potted~~ — **recoverable: sealed reusable housings with O-rings.**
- ✅ ~~Depth in ground truth → pressure sensor?~~ — **no; 2D surface position, no pressure sensor.**
- ⬜ **US pricing + lead times from Oregon RFID**, and whether they'll partner on antenna tuning. ← only remaining blocker.
  - When contacting them, give: 6 ft channel width, surface-floating 32 mm HDX+ tags, need a cross-channel gate; ask how many antennas they'd spec for full-width coverage and whether they'll help tune.

---

### Sources
- Oregon RFID ORMR multi-antenna reader — https://www.oregonrfid.com/products/hdx-long-range-readers/hdx-multiple-antenna-pit-tag-reader/
- Oregon RFID 23 mm HDX+ tag — https://www.oregonrfid.com/products/hdx-pit-tags/23mm-hdx-pit-tag/
- Oregon RFID 32 mm HDX+ tag — https://www.oregonrfid.com/products/hdx-pit-tags/32mm-hdx-pit-tag/
- SparkFun OpenLog Artemis — https://www.sparkfun.com/products/16832
- SparkFun DataLogger IoT 9DoF — https://www.sparkfun.com/products/20594
- Yost Labs 3-Space Data Logger — https://yostlabs.com/product/3-space-data-logger/
- LP-Research LPMS-AL2 waterproof IMU — https://www.lp-research.com/products/inertial-measurement-units-imu/9-axis-waterproof-imu-lpms-al2-series/
- Kinematic Loggers (stones, flood bedload, high-g + 9-axis) — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8839180/
