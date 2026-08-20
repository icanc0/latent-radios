# The Honest Limitations of Wi-Fi Sensing

> *The counterweight to the hype. Read this before you promise anyone a through-wall
> fall detector that "just works."*

Wi-Fi sensing — inferring presence, motion, gestures, breathing, gait, and activity
from Channel State Information (CSI) — is real, useful, and over-sold in roughly equal
measure. Demo videos show 99% accuracy; deployments quietly ship at 60% and get
returned. The gap is not fraud, it is physics and statistics. This page catalogs the
honest limitations so you can set expectations, budget for calibration, and pick
problems that survive contact with a real room.

See also [../docs/ml-csi-sensing.md](../docs/ml-csi-sensing.md) for the modeling side and
[../docs/techniques.md](../docs/techniques.md) for the signal-processing primitives referenced
throughout.

---

## TL;DR — the expectation-setting table

| Claim you'll hear | Honest reality |
|---|---|
| "99% activity recognition accuracy" | True **in the training room, with the training people, at the training positions.** Cross-domain it commonly falls to 40–70%. |
| "Raw CSI phase gives you angle/distance" | Raw commodity-NIC phase is **corrupted by CFO, SFO, and packet-boundary offset** and is unusable without sanitization or a reference antenna. |
| "CSI amplitude is a clean channel measurement" | Amplitude is scaled by **AGC** and only meaningful after you undo the reported gain; absolute magnitude is not comparable across packets/devices. |
| "It works through walls" | Attenuated, multipath-smeared, and orientation-dependent. Sometimes yes, often a coin flip, rarely with the SNR the demo had. |
| "Just retrain and deploy" | **Domain shift** (new room / person / orientation / device) is the single biggest blocker. Retraining needs labeled data *from the deployment*, which defeats the point. |
| "Millimeter breathing detection" | Real — but only inside the right **Fresnel zones**; there are literal blind spots where the same person is invisible. |
| "High-rate sensing" | Your sample rate **is your packet rate.** No traffic, no samples. You often must inject ping floods to reach 100–1000 Hz. |

---

## 1. Phase noise: why raw CSI phase is unusable

CSI is a complex number per subcarrier, `H = |H|·e^{jθ}`. The phase θ is where most of
the geometric information (angle-of-arrival, time-of-flight, Doppler) lives — and on
commodity NICs it is dominated by hardware artifacts, not by the channel. The measured
phase on subcarrier *k* is approximately:

```
θ̂_k = θ_k  −  2π·k·(Δt_SFO + Δt_PBD)/N  −  Δφ_CFO  +  β  +  Z
```

- **CFO — Carrier Frequency Offset.** The TX and RX oscillators are never at exactly the
  same frequency. The residual after the receiver's coarse correction rotates the phase
  of *every* packet by a different, essentially random, amount. Across packets this looks
  like phase that jumps unpredictably.
- **SFO — Sampling Frequency Offset.** The ADC sampling clocks differ, producing a phase
  slope that is **linear in subcarrier index** (`∝ k`). It changes packet to packet.
- **PBD / STO — Packet Boundary (Symbol Timing) Detection error.** The FFT window start is
  estimated per packet; an error of a few samples adds another **linear-in-k** slope. This
  is the biggest single contributor to per-packet phase chaos.
- **β / PLL phase offset** and a random **measurement noise** term `Z` on top.

Because CFO adds a constant and SFO+PBD add a *k*-linear term, the workhorse mitigation is
the **linear-transform / phase-unwrap-and-detrend** method: unwrap θ̂ across subcarriers,
fit a line `a·k + b` (least squares), and subtract it. This removes the constant offset
and the linear slope — killing CFO residual and the SFO/PBD slopes — leaving a
"sanitized" phase whose *shape* is stable, at the cost of destroying any true linear phase
component (i.e. you lose absolute ToF; you keep relative structure). This is the technique
introduced for CSI fingerprinting by Sen et al. and popularized by PhaseFi
(Wang et al.) and the "precise power-delay-profiling" line of work (Xie et al.).

### Practical mitigations for phase

| Technique | What it kills | What it costs | Reference |
|---|---|---|---|
| **Linear detrend** across subcarriers | CFO const + SFO/PBD slope | Absolute ToF / true linear phase | Sen 2012; PhaseFi |
| **Conjugate multiplication / CSI ratio** between two antennas on the same NIC | CFO, SFO, PBD (shared RF chain → common phase cancels) | Needs ≥2 RX antennas; mixes two channels | FarSense; FullBreathe |
| **Phase difference across antennas** | Common per-packet offsets | Loses per-antenna absolute phase | SpotFi, Widar |
| **AoA/ToF joint sanitization (MUSIC + offset estimation)** | STO/SFO via super-resolution | Compute; needs ≥3 antennas | SpotFi |

**The CSI-ratio trick is the single most important practical result here.** Because two
antennas on one card share the same oscillator and timing, dividing (or conjugate-
multiplying) their CSI cancels CFO/SFO/PBD exactly, yielding a stable complex quantity.
This is what makes commodity-Wi-Fi respiration sensing at meters of range actually work
(FarSense, Zeng et al.).

**Bottom line:** never feed raw phase to a model. Either sanitize, or use a phase-difference
/ ratio representation, or use amplitude-only. Papers that report "phase features" almost
always mean *sanitized* phase.

---

## 2. Amplitude instability and AGC

Amplitude looks friendlier than phase but has its own trap: **Automatic Gain Control.**
The RX front-end scales the incoming signal to fit the ADC's dynamic range, and that gain
changes packet-to-packet with received power. The reported `|H|` therefore mixes *channel*
magnitude with *hardware gain*. Two consequences:

- **Absolute amplitude is not comparable** across packets, antennas, or devices unless you
  read and undo the AGC/RSSI scaling the tool exposes. The Intel 5300 tool (Halperin et al.)
  reports an AGC value and per-antenna RSSI precisely so you can renormalize; Nexmon-CSI on
  Broadcom chips has its own gain/RSSI bookkeeping. If you skip this, an "activity" your
  model learned may just be an AGC step.
- **Amplitude is bursty and heavy-tailed.** Impulsive noise, rate adaptation, and
  neighboring-AP interference create spikes. Standard hygiene: Hampel/median outlier
  removal, then low-pass or wavelet denoising, then per-stream normalization (z-score or
  min-max). Keep the normalization statistics *per deployment* — global normalization
  leaks domain information.

Even after normalization, amplitude alone is a weak discriminator for fine motion; the
practical systems combine sanitized-phase-difference and amplitude, or use Doppler/BVP
representations (below) that are more invariant.

---

## 3. Domain shift — the single biggest real-world blocker

Everything above is a nuisance. **Domain shift is the thing that kills products.** A model
trained on CSI in room A, with people P1–P5, facing north, on NIC N1, systematically fails
when *any* of those changes:

- **Environment / room:** different multipath, different static reflectors → the CSI-to-label
  mapping is different. Reported cross-environment drops of 20–40 accuracy points are typical.
- **Person:** body size, gait, RCS, and habit change the signal. Cross-subject is often
  worse than cross-room.
- **Orientation / position:** the same gesture performed facing a different direction, or a
  meter to the left, produces a different Doppler signature (see Fresnel zones, §5).
- **Device / chipset:** different antenna spacing, filters, AGC behavior, subcarrier
  reporting → not transferable without adaptation.
- **Time:** furniture moves, humidity changes, an AP reboots and picks new antennas. Even the
  *same* room drifts.

Why it is fundamental: supervised sensing learns `P(label | CSI)`, but CSI is a function of
the *whole* propagation environment, not just the target. Change the environment and you
change `P(CSI)` and the conditional. This is textbook covariate/domain shift, and Wi-Fi is a
severe case because the "nuisance" variables (multipath geometry) carry more energy than the
signal of interest.

### The families of mitigation (and what they really buy you)

| Strategy | Idea | Honest cost / limit | Representative work |
|---|---|---|---|
| **Domain-invariant features** | Transform CSI into a physical representation that is (mostly) independent of environment before learning | Requires ≥2 links / multiple receivers; still not fully person-invariant | **Widar3.0 — Body-coordinate Velocity Profile (BVP)** (Zheng et al.) |
| **Adversarial domain adaptation** | Train a feature extractor whose features a domain-discriminator can't classify | Needs *unlabeled* target-domain data at train time; degrades with many domains | **EI** (Jiang et al.) |
| **Transfer / fine-tuning** | Pretrain, then adapt with a little target data | Needs *labeled* target data — the thing you were trying to avoid | CrossSense (Zhang et al.) |
| **Meta-learning / few-shot** | Learn to adapt from 1–few examples per new domain | Still needs *some* labeled target samples; brittle beyond trained shift types | **RF-Net** (Ding et al.) |
| **Data augmentation / synthesis** | Simulate new environments, rotate/scale Doppler, mix reflectors | Sim-to-real gap; can't cover unseen multipath | Various |
| **Signal-level domain factors removal** | Extract Doppler Frequency Shift (DFS) / velocity, discard static component | Loses information; DFS still orientation-dependent | Widar2.0/Widar3.0 |

**BVP (Widar3.0) is the canonical "do it in the physics, not the network" answer:** by
combining DFS from multiple receivers and projecting motion into a body-centric coordinate
frame, it produces a feature that generalizes across rooms and orientations far better than
raw CSI — the paper's premise is literally *zero-effort cross-domain* recognition. But note
the cost: it needs a **multi-receiver deployment** and careful synchronization, and it is
still not immune to cross-*person* variation.

**Honest framing for stakeholders:** cross-domain generalization in Wi-Fi sensing is an open
research problem, not a solved engineering step. If a vendor claims turnkey
room-to-room transfer with no site data, ask for the cross-domain (leave-one-environment-out)
numbers, not the in-domain ones.

---

## 4. Multipath and environment dependence

Wi-Fi sensing *works because of* multipath (the target modulates reflected paths) and *fails
because of* multipath (every room's paths are unique and drift). Key facts:

- The channel is the superposition of a **static component** (walls, furniture — huge, slowly
  varying) and a **dynamic component** (the moving person — small). Sensing is essentially the
  problem of extracting a small dynamic term riding on a large static one. Static-component
  removal (mean subtraction, CSI ratio, or DFS extraction) is mandatory and imperfect.
- **Furniture rearrangement, doors, other people, and even the sensor's own antenna selection**
  change the static component and can invalidate a trained model overnight.
- Rich multipath *helps* diversity-based localization (SpotFi-style AoA/ToF) but *hurts*
  clean Doppler; poor multipath (open field) does the opposite. You cannot optimize for both.

There is no mitigation that removes environment dependence entirely; you *manage* it with
static-component removal, invariant features (§3), and by constraining the deployment
geometry.

---

## 5. Fresnel zones, blind spots, and orientation

Commodity Wi-Fi respiration/motion sensing is governed by **Fresnel-zone diffraction**
(Wang, Zhou et al.). As a chest moves through successive Fresnel zones between TX and RX, the
received signal oscillates. Two brutal consequences for honesty:

- **Blind spots are real and predictable.** At certain positions/orientations the motion is
  tangent to the Fresnel boundaries and produces almost no signal — the *same person breathing*
  is undetectable there while being crisp a half-wavelength away. "Does user location and body
  orientation matter?" — yes, decisively.
- **Orientation is a domain variable, not a detail.** Chest displacement projected onto the
  TX-RX line changes with facing direction; a model trained facing the link fails facing across
  it. This is a big part of why "orientation" appears in every cross-domain study.

Mitigation: multiple spatially-diverse links so that a blind spot on one link is covered by
another; deployment guidance that places links to bracket the expected activity area; and
representations (BVP) that fuse across links.

---

## 6. Subcarrier nulls, pilots, and reporting quirks

OFDM does not give you a clean, uniform spectrum:

- **Null and guard subcarriers.** In 802.11n 20 MHz, only 56 of 64 subcarriers carry
  data/pilots; the DC subcarrier and band edges are null. You get **no CSI** there — permanent
  gaps in the frequency response.
- **Pilot subcarriers** are modulated differently and their CSI is not directly comparable to
  data subcarriers.
- **Tool-specific decimation.** The Intel 5300 tool reports only **30 subcarrier groups**
  (subsampled), not the full 56/114 — you are already working with a lossy view. Atheros and
  Nexmon-CSI report more subcarriers but with their own quirks (Nexmon exposes the full set on
  supported Broadcom chips; see [../docs/techniques.md](../docs/techniques.md)).
- **Deep fades / spectral nulls** from multipath can null out individual subcarriers per
  packet, injecting NaNs/near-zero magnitudes and wild phase. Interpolate or mask; never treat a
  faded subcarrier's phase as signal.

---

## 7. Sample rate, bandwidth, and latency limits

- **Your sampling rate is your packet rate.** CSI is produced only when a packet is received.
  Idle Wi-Fi ≈ a handful of packets/second → uselessly low temporal resolution. Practical
  systems **inject traffic** (ICMP ping floods, or a dedicated transmitter) to force 100–1000
  packets/s. That consumes airtime, drains battery, and is fragile to rate adaptation and
  contention (CSMA backoff makes the sampling **non-uniform** — you often must resample).
- **Bandwidth caps range resolution.** Time-of-flight resolution is `c / (2·B)`: 20 MHz → ~7.5 m,
  80 MHz → ~1.9 m. Commodity Wi-Fi cannot range at the resolution marketing implies; sub-meter
  localization comes from *angle* (antenna arrays) and *super-resolution*, not raw ToF.
- **Latency.** Real-time sensing must survive driver/CSI-extraction latency, jitter, and the
  windowing needed for Doppler (a 1–2 s window for breathing means ≥1–2 s inherent latency).
- **Non-stationary rate/MCS.** If the link changes MCS or antenna set mid-capture, the CSI's
  scaling and even dimensionality can shift under you.

---

## 8. The lab-to-deployment gap and the calibration burden

Putting it together, the reasons a 99%-in-paper system disappoints in the field:

1. **Reported accuracy is in-domain.** Ask for leave-one-room-out / leave-one-subject-out
   numbers. The honest benchmark literature (e.g. **SenseFi**, Yang et al.) exists precisely to
   standardize this — use it.
2. **Class balance and staging.** Lab activities are segmented, cued, and repeated; real life is
   continuous, ambiguous, and full of the "null/other" class that lab datasets omit.
3. **Ground truth is expensive.** Every new site needs labeled data to calibrate — cameras,
   wearables, or manual annotation — which undercuts the "privacy-preserving, no-wearable"
   selling point.
4. **Drift.** Even a calibrated site degrades as furniture and RF environment change;
   plan for periodic recalibration or online adaptation.

### A realistic calibration checklist for any deployment

- [ ] Fix and document antenna geometry, TX power, MCS/rate (pin the rate if the driver allows).
- [ ] Read and undo **AGC**; store normalization stats **per site**.
- [ ] Sanitize phase (linear detrend) or use **CSI-ratio / phase-difference** representations.
- [ ] Remove the static component (mean/CSI-ratio/DFS); mask nulls and faded subcarriers.
- [ ] Force and *resample* to a uniform packet rate; log actual timestamps.
- [ ] Collect **site-and-person-specific** labeled data for the classes that matter, including a
      rich "other/none" class.
- [ ] Validate with **leave-one-domain-out**, not random split, before quoting accuracy.
- [ ] Plan recalibration cadence; monitor for drift in feature statistics.

---

## What Wi-Fi sensing is genuinely good at (so this isn't all doom)

Set against the limits, these are the problems that *do* survive deployment:

- **Coarse presence / motion / occupancy** in a fixed space — robust, low calibration.
- **Respiration and heart-rate at rest**, given good Fresnel-zone placement and CSI-ratio
  processing.
- **A small, fixed gesture vocabulary** in a fixed geometry with per-site calibration.
- **Anything where you can co-locate a multi-receiver deployment and use invariant features**
  (BVP-style) and accept per-site tuning.

Everything more ambitious — turnkey cross-home fall detection, universal gesture control,
through-wall identity — is at the research frontier, not on the shelf. Promise accordingly.

---

## References

Signal / phase sanitization and CSI tooling:

- D. Halperin, W. Hu, A. Sheth, D. Wetherall. *Tool Release: Gathering 802.11n Traces with
  Channel State Information.* ACM SIGCOMM CCR, 2011. Linux 802.11n CSI Tool —
  <https://dhalperi.github.io/linux-80211n-csitool/>
- F. Gringoli, M. Schulz, J. Link, M. Hollick. *Free Your CSI: A Channel State Information
  Extraction Platform for Modern Wi-Fi Chipsets.* ACM WiNTECH, 2019. Nexmon-CSI —
  <https://github.com/seemoo-lab/nexmon_csi>
- Y. Xie, Z. Li, M. Li. *Precise Power Delay Profiling with Commodity Wi-Fi.* ACM MobiCom, 2015.
  Atheros CSI Tool — <https://wands.sg/research/wifi/AtherosCSI/>
- S. Sen, B. Radunovic, R. R. Choudhury, T. Minka. *You Are Facing the Mona Lisa: Spot
  Localization Using PHY Layer Information.* ACM MobiSys, 2012.
- X. Wang, L. Gao, S. Mao. *PhaseFi: Phase Fingerprinting for Indoor Localization with a Deep
  Learning Approach.* IEEE GLOBECOM, 2015.
- M. Kotaru, K. Joshi, D. Bharadia, S. Katti. *SpotFi: Decimeter Level Localization Using
  WiFi.* ACM SIGCOMM, 2015.
- J. Zeng, D. Wu, J. Xiong, et al. *FarSense: Pushing the Range Limit of WiFi-based Respiration
  Sensing with CSI Ratio of Two Antennas.* ACM IMWUT, 2019.

Fresnel zones, orientation, and blind spots:

- H. Wang, D. Zhang, J. Ma, et al. *Human Respiration Detection with Commodity WiFi Devices: Do
  User Location and Body Orientation Matter?* ACM UbiComp, 2016.

Domain shift and cross-domain generalization:

- Y. Zheng, Y. Zhang, K. Qian, et al. *Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi
  (Widar3.0).* ACM MobiSys, 2019. Project & dataset — <http://tns.thss.tsinghua.edu.cn/widar3.0/>
- W. Jiang, C. Miao, F. Ma, et al. *Towards Environment Independent Device Free Human Activity
  Recognition (EI).* ACM MobiCom, 2018.
- J. Zhang, Z. Tang, M. Li, et al. *CrossSense: Towards Cross-Site and Large-Scale WiFi
  Sensing.* ACM MobiCom, 2018.
- S. Ding, Z. Chen, T. Zheng, J. Luo. *RF-Net: A Unified Meta-Learning Framework for RF-Enabled
  One-Shot Human Activity Recognition.* ACM SenSys, 2020.
- Y. Ma, G. Zhou, S. Wang. *WiFi Sensing with Channel State Information: A Survey.* ACM Computing
  Surveys, 2019. DOI <https://doi.org/10.1145/3310194>

Sign language / environment dependence and benchmarking:

- Y. Ma, G. Zhou, S. Wang, H. Zhao, W. Jung. *SignFi: Sign Language Recognition Using WiFi.* ACM
  IMWUT, 2018. Dataset — <https://github.com/yongsen/SignFi>
- J. Yang, X. Chen, H. Zou, et al. *SenseFi: A Library and Benchmark on Deep-Learning-Empowered
  WiFi Human Sensing.* Patterns (Cell Press), 2023. arXiv <https://arxiv.org/abs/2207.07859> ·
  code <https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark>

Internal cross-references: [../docs/ml-csi-sensing.md](../docs/ml-csi-sensing.md) ·
[../docs/techniques.md](../docs/techniques.md)
