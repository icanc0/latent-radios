# CSI calibration deep dive: making raw CSI usable

> The single hardest practical step in Wi-Fi sensing. Extracting CSI (via
> [Nexmon CSI](../../projects/nexmon.md), the [Atheros/ath9k path](atheros-ath9k-spectral-csi.md),
> the [Intel/Linux 802.11n tool](../../chips/intel.md), or ESP32) is the easy part.
> Turning that raw complex matrix into something a tracking or sensing algorithm
> can trust is where most projects quietly fail. This page is the missing manual.
>
> Prerequisites: read [Nexmon CSI to usable CSI](nexmon-csi-to-usable-csi.md) first
> (it gets you from firmware bytes to a `packets × subcarriers × rx × tx` array).
> Then read [The honest limitations of Wi-Fi sensing](../honest-limitations-of-wifi-sensing.md)
> so you know what calibration **cannot** fix.

---

## 1. Why raw CSI is not usable

A commodity Wi-Fi chip is a *communications* radio, not a measurement instrument.
Everything in its front end is optimized to **recover bits**, not to preserve the
absolute phase and amplitude of the channel. The receiver deliberately estimates
and removes carrier/timing offsets (that is its job — to demodulate), and the CSI
you read back is what is left *after* those loops have run, corrupted by their
residuals plus per-packet bookkeeping.

Concretely, the CSI value the chip hands you for subcarrier `k` on one packet is:

```
Ĥ(k) = H(k) · exp( -j · ( 2π·k·(τ_sfo + τ_pdd)/N  +  φ_cfo  +  φ_po ) ) · ε(k)
       └── true ──┘        └──── linear in k ────┘   └── const in k ──┘  └ noise ┘
         channel
```

The true channel `H(k)` is buried under four classes of distortion. **You cannot
sense until you remove them** — or until you use a differential quantity that is
immune to them (Section 5, the trick that actually wins).

---

## 2. The error sources, one by one

| Symbol | Name | Behaviour across subcarriers | Behaviour across packets | Root cause |
|---|---|---|---|---|
| `φ_cfo` | **Carrier Frequency Offset** residual | constant (flat) phase | drifts / random | TX & RX LOs are not phase-locked; the AFC loop leaves a residual |
| `τ_sfo` | **Sampling Frequency Offset** | linear phase ramp in `k` | slowly varying | TX & RX ADC sample clocks differ (ppm) |
| `τ_pdd` | **Packet Detection Delay** | linear phase ramp in `k` | random per packet | RX decides "packet starts here" a few samples early/late |
| `τ_sto` | Symbol Timing Offset (a.k.a. PBD, packet boundary detection) | linear phase ramp in `k` | random per packet | FFT window placement jitter; folds into `τ_pdd` |
| `φ_po` | **Random phase offset** | constant (flat) phase | uniform random each packet | initial phase of the PLL/synth when the packet is captured |
| `A_agc` | **AGC / gain scaling** | ~flat gain (frequency-flat) | jumps between gain states | automatic gain control changes the reference the CSI is scaled to |

Key observations that drive every fix below:

- **Two families of phase error.** Timing errors (`τ_sfo`, `τ_pdd`, `τ_sto`)
  produce a **phase that is linear in the subcarrier index `k`** — a *slope*.
  Frequency/synth errors (`φ_cfo`, `φ_po`) produce a **phase that is constant in
  `k`** — an *offset*. This is why "fit a line across subcarriers and subtract it"
  (Section 4) removes a huge fraction of the garbage in one step.
- **The common-across-antennas property.** On a single NIC, every RX chain shares
  the same LO and the same sample clock. Therefore `φ_cfo`, `φ_po`, and `τ_sfo`
  are (to first order) **identical on all antennas of that card**. Anything that
  is common to two chains cancels when you take a **difference of phases** or a
  **ratio of complex CSI** between two antennas (Section 5). This is the single
  most important fact in practical CSI processing.
- **Amplitude is comparatively benign but not free.** `|Ĥ(k)|` is real and mostly
  reflects the true channel magnitude, but it is scaled by AGC gain state and
  polluted by impulsive outliers; handle both (Section 6).

---

## 3. Order of operations (the pipeline)

Do these in order. Later steps assume earlier ones ran.

```
raw CSI (complex, packets × subcarriers × rx × tx)
  1. Parse & index         → attach real subcarrier indices k; drop null SCs
  2. Guard/DC handling     → remove DC + guard bands; optionally interpolate pilots
  3. AGC / amplitude scale → undo gain state; convert to a consistent reference
  4. Amplitude sanitize    → Hampel outlier filter, then smoothing
  5. Phase unwrap          → np.unwrap along subcarrier axis
  6. Linear phase detrend  → remove slope (SFO/PDD) + offset (per-packet)   ← toy→usable
  7. Cross-antenna combine → conjugate-mult OR CSI-ratio to kill CFO/PO     ← the winner
  8. Feature extraction    → Doppler/DFS, AoA, amplitude variance, etc.
```

Steps 1–6 give you *sanitized* CSI — good enough for classifiers that tolerate an
unknown constant/linear phase term. Step 7 gives you *calibrated-by-construction*
CSI, where the nuisance terms are algebraically gone. Serious tracking systems
(Widar2.0, IndoTrack, FarSense, Widar3.0) all live in step 7.

---

## 4. Fixing phase: linear detrending across subcarriers

This is the classic **phase sanitization** used since the Linux 802.11n CSI Tool
and formalized by SpotFi. It removes the linear (timing) term and the constant
(per-packet) term simultaneously, at the cost of also removing any *genuine*
linear/constant channel phase.

### The model and the fix

Measured phase on subcarrier index `kᵢ` (for 802.11n/20 MHz, `kᵢ ∈ {-28…-1, 1…28}`,
FFT size `N = 64`):

```
φ̂ᵢ = φᵢ  -  2π·kᵢ·τ / N  -  β  +  Zᵢ
```

- `τ` — lumped timing offset (SFO + PDD + STO) → the **slope** we must kill.
- `β` — lumped CFO + random phase offset → the **intercept** we must kill.

Estimate slope `a` and intercept `b` by least squares over subcarriers, then
subtract the fitted line:

```
a = Σ(kᵢ·φ̂ᵢ) ... /  ...      (LS slope over the packet's subcarriers)
b = mean(φ̂ᵢ)
φ̃ᵢ = φ̂ᵢ - a·kᵢ - b
```

A cheaper, widely-used two-point estimator (SpotFi/Linux-tool style) uses the
first and last usable subcarrier for the slope and the mean for the intercept:

```
a = (φ̂_last - φ̂_first) / (k_last - k_first)
b = (1/M)·Σ φ̂ᵢ
```

Both work; least squares is more robust to a single bad subcarrier once you have
already run the Hampel filter.

### What it does and does not give you

- **Removes**: SFO/PDD/STO slope and the per-packet constant offset. The sanitized
  phase is now comparable *across packets* up to the fact that you also subtracted
  the mean.
- **Destroys**: the true absolute ToF (that lived in the slope) and any true flat
  phase (that lived in the intercept). So do **not** try to read absolute range or
  absolute AoA from linearly-detrended single-antenna phase — the information you
  wanted is exactly what you deleted. For AoA/ToF, sanitize *relative* to a
  reference antenna instead, or use MUSIC on the raw (per-antenna) phases with the
  offsets modeled (SpotFi's approach). For Doppler/breathing/gesture, detrended
  phase (or better, Section 5) is fine.

> Rule of thumb: linear detrending makes phase **look** clean and stable on a plot.
> That is necessary but not sufficient. If your downstream feature needs the
> absolute phase, detrending has silently thrown it away.

---

## 5. Fixing phase properly: cross-antenna cancellation

Because `φ_cfo`, `φ_po`, and (to first order) `τ_sfo` are **shared by all RX chains
on the card**, combine two antennas so the shared term cancels *exactly*, with no
line-fitting and no information destroyed.

### 5a. Conjugate multiplication (Widar2.0 / IndoTrack)

Let antennas 1 and 2 see the same nuisance phase `e^{jψ_common}`:

```
H₁(k) = A₁(k)·e^{jφ₁(k)}·e^{jψ_common}
H₂(k) = A₂(k)·e^{jφ₂(k)}·e^{jψ_common}

CM(k) = H₁(k) · conj(H₂(k))
      = A₁A₂ · e^{ j( φ₁(k) - φ₂(k) ) }        ← ψ_common CANCELLED
```

The result carries the **phase difference** between the two antennas. Its
time-evolution is the **Doppler Frequency Shift (DFS)** of the reflected paths —
exactly the quantity IndoTrack and Widar2.0 feed to MUSIC to get velocity and
angle. A practical wrinkle (Widar2.0): if a static/strong path dominates one
antenna it injects a DC/mirror term; pick the antenna pair (or add a constant
offset to one) so the conjugate product's static component sits away from the
Doppler band, then band-pass.

### 5b. CSI ratio (FarSense) — often the better default

Instead of multiplying by the conjugate, **divide**:

```
Hq(k) = H₁(k) / H₂(k)
      = (A₁/A₂) · e^{ j( φ₁(k) - φ₂(k) ) }
```

Division cancels the common phase **and** the common amplitude noise / AGC scaling
(both LOs and both AGCs are shared enough that the burst noise correlates). FarSense
showed the CSI ratio (a) removes the random phase offset, (b) sharply reduces
amplitude noise, and (c) roughly *doubles* the sensing range for respiration versus
raw amplitude — because the ratio's real/imaginary parts each carry the channel
variation and the "blind spots" of one antenna are filled by the other. It is a
complex quantity, so you get a cleaner signal *and* keep phase.

Practical notes for the ratio:
- Choose the denominator antenna to be the one with the more stable, higher-SNR
  response (avoid deep fades → division blow-up). Some pipelines add a tiny
  regularizer, `H₂ ← H₂ + ε`, or skip subcarriers where `|H₂|` is in a fade.
- Track the **real and imaginary parts separately** (or the complex value) rather
  than magnitude/phase, to avoid `atan2` wrapping artifacts near the origin.

### 5c. Which to use

- **Doppler / velocity / gesture / tracking** → conjugate multiplication (you want
  the phase *difference dynamics*; Widar2.0, IndoTrack, Widar3.0's BVP pipeline).
- **Respiration / small vital-sign motion / max range** → CSI ratio (FarSense).
- **Classifier that just needs a stable feature** → either; the ratio is a good
  low-effort default because it also denoises amplitude for free.

---

## 6. Fixing amplitude: AGC, normalization, outliers

### 6a. Undo AGC / put amplitude on a consistent reference

Different chips expose gain differently:

- **Intel/Linux 802.11n tool** — CSI is reported in an internal fixed-point form;
  the tool's `get_scaled_csi()` converts to an absolute SNR-referenced value using
  the reported RSSI (per RX chain) and the AGC/`noise` fields. Use it. If you skip
  scaling, amplitude jumps whenever the AGC changes gain state and your features
  see phantom "motion."
- **Atheros (ath9k / Atheros CSI Tool)** — CSI is paired with per-packet RSSI and
  AGC gain; apply the same RSSI-referenced scaling before comparing packets.
- **Broadcom (Nexmon CSI)** — the extractor returns unnormalized complex CSI and
  (chip-dependent) an RSSI. Nexmon CSI amplitudes are **not** absolute; treat them
  as relative and normalize per-stream (below). See
  [nexmon-csi-to-usable-csi.md](nexmon-csi-to-usable-csi.md) for the scaling caveats
  specific to the 43455c0 / 4366c0.
- **ESP32** — `wifi_csi_info` gives raw I/Q bytes plus `rssi` and `agc_gain` in the
  RX control block; subtract/normalize by `agc_gain` before using amplitude across
  packets.

### 6b. Per-stream amplitude normalization

If you only need *relative* dynamics (most sensing), normalize each
antenna/subcarrier stream to zero mean / unit variance, or divide by a running
median. This removes slow gain drift and makes streams comparable. Do this **after**
outlier removal, not before (one spike poisons the mean/variance).

### 6c. Hampel filter for impulsive outliers

Commodity CSI is peppered with single-sample spikes (bad packets, retries, gain
glitches). A **Hampel filter** — a sliding-window median with a MAD-based decision —
is the standard tool (CARM, E-eyes, and most sensing pipelines use it):

```
For each sample i in a window of half-width W:
  m   = median(x[i-W : i+W])
  MAD = median(|x[i-W : i+W] - m|)
  σ   ≈ 1.4826 · MAD            (Gaussian-consistent scale)
  if |x[i] - m| > n_sigma · σ:  replace x[i] with m      (n_sigma ≈ 3)
```

Apply it **per subcarrier along the packet (time) axis** on amplitude. Follow with
a light low-pass (moving average or a low-order Butterworth at your motion band,
e.g. 0.1–2 Hz for breathing, up to tens of Hz for gestures). Do not median-filter
across subcarriers — that smears real frequency-selective structure.

---

## 7. DC subcarrier, guard bands, pilots, nulls

Never feed these to your model — they are structurally meaningless or reserved:

| Region (802.11n, 20 MHz, `N=64`) | Indices | Action |
|---|---|---|
| DC subcarrier | `k = 0` | **Drop** (it carries LO leakage, not channel). If a routine needs contiguous SCs, interpolate from neighbours `±1`. |
| Guard / null subcarriers | edges `k = -32…-29` and `29…31` (and `±28` region varies) | **Drop** — no energy transmitted; values are noise. |
| Pilot subcarriers | `k = ±7, ±21` | Handle with care — the RX uses them for residual CFO/phase tracking, so they can behave differently from data SCs. Many pipelines drop or interpolate them. |
| Data subcarriers | remaining of the 52 (n) / 56 SCs | **Keep** — these are your signal. |

Chip/bandwidth-specific maps differ (802.11ac 80 MHz → 256-point FFT, more nulls;
Nexmon reports a fixed FFT-bin layout you must re-index to real SC numbers). The
mistake to avoid: extractors emit CSI for **all FFT bins including nulls/DC**; if
you forget to drop them, your "subcarrier 0" and edge bins inject constant garbage
that dominates variance-based features. Build the correct index mask **once** for
your `(standard, bandwidth, chip)` and reuse it. See the per-chip layouts in
[nexmon-csi-to-usable-csi.md](nexmon-csi-to-usable-csi.md).

---

## 8. A minimal, honest Python routine

Dependencies: `numpy`, `scipy`. Input `csi` is complex, shape
`(n_packets, n_subcarriers, n_rx)` for one TX stream, with a matching integer
`sc_idx` array of **real** subcarrier indices (already excluding nulls/DC, or with a
mask). This does the full pipeline through Section 5.

```python
import numpy as np
from scipy.signal import medfilt

def hampel(x, half_win=5, n_sigma=3.0):
    """Impulsive-outlier removal along axis 0 (time/packets), per column."""
    x = np.asarray(x, dtype=float)
    out = x.copy()
    k = 1.4826
    n = x.shape[0]
    for i in range(n):
        lo, hi = max(0, i - half_win), min(n, i + half_win + 1)
        win = x[lo:hi]
        med = np.median(win, axis=0)
        mad = np.median(np.abs(win - med), axis=0)
        sigma = k * mad
        bad = np.abs(x[i] - med) > (n_sigma * sigma)
        out[i][bad] = med[bad]
    return out

def linear_phase_detrend(phase, sc_idx):
    """
    Remove the linear (SFO/PDD) slope + constant (per-packet) offset.
    phase: (n_pkt, n_sc) already unwrapped along subcarrier axis.
    sc_idx: (n_sc,) real subcarrier indices.
    Returns sanitized phase. NOTE: absolute ToF/flat-phase are DESTROYED.
    """
    k = sc_idx.astype(float)
    # least-squares slope a and intercept b per packet
    kbar = k.mean()
    kc = k - kbar
    denom = np.sum(kc * kc)
    a = (phase * kc).sum(axis=1) / denom          # (n_pkt,)
    b = phase.mean(axis=1) - a * kbar             # (n_pkt,)
    return phase - (a[:, None] * k[None, :] + b[:, None])

def sanitize_csi(csi, sc_idx, ref_ant=0, mode="ratio"):
    """
    csi: complex (n_pkt, n_sc, n_rx), nulls/DC already removed.
    mode: 'ratio' (FarSense) or 'conj' (Widar2.0/IndoTrack) or 'detrend'.
    """
    # --- amplitude path: Hampel per (sc, rx) over time, then normalize ---
    amp = np.abs(csi)
    for r in range(amp.shape[2]):
        amp[:, :, r] = hampel(amp[:, :, r])
    amp = amp / (np.median(amp, axis=0, keepdims=True) + 1e-9)

    # --- phase path ---
    if mode == "detrend":
        ph = np.unwrap(np.angle(csi), axis=1)
        for r in range(ph.shape[2]):
            ph[:, :, r] = linear_phase_detrend(ph[:, :, r], sc_idx)
        return amp * np.exp(1j * ph)              # sanitized, single-antenna

    # cross-antenna cancellation: nuisance phase common to all RX chains cancels
    H = csi
    Href = H[:, :, ref_ant:ref_ant + 1]           # (n_pkt, n_sc, 1)
    if mode == "conj":
        # H_i * conj(H_ref): keeps phase DIFFERENCE -> Doppler/AoA dynamics
        return H * np.conj(Href)
    elif mode == "ratio":
        # H_i / H_ref: cancels common phase AND common amplitude noise
        return H / (Href + 1e-9)
    raise ValueError(mode)

# ---- usage ----
# clean = sanitize_csi(csi, sc_idx, ref_ant=0, mode="ratio")
# For Doppler: take clean[:, :, other_ant], band-pass along axis 0, then MUSIC/FFT.
```

Caveats baked into the code (read them):
- `hampel` here is the readable O(n·win) version; for long captures use a
  vectorized rolling median (`scipy.ndimage.median_filter`) or `pandas`.
- `mode="detrend"` returns single-antenna sanitized CSI — good for a classifier,
  **not** for absolute AoA/ToF.
- `mode="ratio"`/`"conj"` return a 2-antenna quantity — the `ref_ant` column
  becomes trivially 1 (ratio) or `|H|²` real (conj); drop it downstream.
- Both cross-antenna modes assume the antennas are on **the same NIC** so the
  nuisance terms are truly shared. Across two separate radios, none of this holds.

---

## 9. Sanity checks — did calibration actually work?

Cheap tests that catch the common failure modes:

1. **Static-scene phase should be flat over time.** Capture with nothing moving.
   After Section 5, the per-subcarrier phase (of the ratio/conj product) should be
   nearly constant across packets. If it still walks randomly ±π each packet, your
   antennas are **not** sharing a clock (wrong chip, or you combined two radios) —
   cancellation is a no-op.
2. **Detrended phase should be smooth across subcarriers.** A sawtooth means you
   forgot to `np.unwrap`, or a null/DC subcarrier is still in the array.
3. **Amplitude variance should drop but not vanish.** If Hampel + normalization
   flattens *everything* including your target motion, `n_sigma`/window is too
   aggressive, or you normalized before removing outliers.
4. **Known-Doppler test.** Wave a metal plate / walk toward the link at a steady
   pace; the conjugate-product spectrogram (DFS) should show a clean shifting band
   at the expected frequency. No band → the nuisance terms are not cancelled, or
   the static path dominates (add the Widar2.0 offset / pick another antenna pair).

---

## 10. What calibration does NOT fix

Calibration cleans up *systematic front-end* distortion. It does not manufacture
information the hardware never captured. Do not expect it to overcome:

- **Coarse subcarrier resolution / bandwidth** — 20/40/80 MHz limits range/Doppler
  resolution regardless of how clean the phase is.
- **Sparse, uncontrolled packet timing** — irregular CSI sample intervals alias
  your Doppler; calibration can't resample information that wasn't there. Prefer a
  steady injected ping stream.
- **Multipath ambiguity in one link** — one TX/RX pair sees a projection of the
  scene; more geometry (antennas/links) is the only real fix.
- **Cross-environment / cross-person generalization** — a sanitized feature is
  still environment-coupled; domain-invariant features (Widar3.0's BVP) or
  learned domain adaptation are separate problems.

For the full accounting, read
[The honest limitations of Wi-Fi sensing](../honest-limitations-of-wifi-sensing.md).
Calibration is necessary. It is not sufficient. The point of this page is to make
sure the *necessary* part is done right, so that when a result is disappointing you
know it is a physics/geometry limit and not a bug in your phase handling.

---

## References

Primary CSI-extraction and sanitization sources:

- D. Halperin, W. Hu, A. Sheth, D. Wetherall. **"Tool Release: Gathering 802.11n
  Traces with Channel State Information."** ACM SIGCOMM CCR, 2011.
  <https://dl.acm.org/doi/10.1145/1925861.1925870> ·
  Linux 802.11n CSI Tool (incl. `get_scaled_csi`):
  <https://dhalperi.github.io/linux-80211n-csitool/>
- F. Gringoli, M. Schulz, J. Link, M. Hollick. **"Free Your CSI: A Channel State
  Information Extraction Platform for Modern Wi-Fi Chipsets."** ACM WiNTECH, 2019.
  <https://dl.acm.org/doi/10.1145/3349623.3355477> · Nexmon CSI:
  <https://github.com/seemoo-lab/nexmon_csi>

Phase sanitization / localization:

- M. Kotaru, K. Joshi, D. Bharadia, S. Katti. **"SpotFi: Decimeter Level
  Localization Using WiFi."** ACM SIGCOMM, 2015.
  <https://dl.acm.org/doi/10.1145/2785956.2787487>
- S. Sen, B. Radunovic, R. R. Choudhury, T. Minka. **"Precise Indoor Localization
  Using PHY Information"** (PinLoc). ACM MobiSys, 2011.
  <https://dl.acm.org/doi/10.1145/1999995.2000011>

Cross-antenna cancellation (conjugate multiplication & CSI ratio):

- K. Qian, C. Wu, Y. Zhang, G. Zhang, Z. Yang, Y. Liu. **"Widar2.0: Passive Human
  Tracking with a Single Wi-Fi Link."** ACM MobiSys, 2018.
  <https://dl.acm.org/doi/10.1145/3210240.3210314>
- X. Li, D. Zhang, Q. Lv, J. Xiong, S. Li, Y. Zhang, H. Mei. **"IndoTrack:
  Device-Free Indoor Human Tracking with Commodity Wi-Fi."** ACM IMWUT, 2017.
  <https://dl.acm.org/doi/10.1145/3130940>
- Y. Zeng, D. Wu, J. Xiong, E. Yi, R. Gao, D. Zhang. **"FarSense: Pushing the Range
  Limit of WiFi-based Respiration Sensing with CSI Ratio of Two Antennas."**
  ACM IMWUT, 2019. <https://dl.acm.org/doi/10.1145/3351279> ·
  arXiv: <https://arxiv.org/abs/1907.03994>
- Y. Zheng, Y. Zhang, K. Qian, G. Zhang, Y. Liu, C. Wu, Z. Yang. **"Zero-Effort
  Cross-Domain Gesture Recognition with Wi-Fi"** (Widar3.0). ACM MobiSys, 2019.
  <https://dl.acm.org/doi/10.1145/3307334.3326081>

Activity-recognition modeling & amplitude denoising:

- W. Wang, A. X. Liu, M. Shahzad, K. Ling, S. Lu. **"Understanding and Modeling of
  WiFi Signal Based Human Activity Recognition"** (CARM). ACM MobiCom, 2015.
  <https://dl.acm.org/doi/10.1145/2789168.2790093>
- Y. Ma, G. Zhou, S. Wang. **"WiFi Sensing with Channel State Information: A
  Survey."** ACM Computing Surveys, 2019.
  <https://dl.acm.org/doi/10.1145/3310194>

Related pages in this catalog: [nexmon-csi-to-usable-csi](nexmon-csi-to-usable-csi.md) ·
[atheros-ath9k-spectral-csi](atheros-ath9k-spectral-csi.md) ·
[CSI toolchains](../../projects/csi-toolchains.md) ·
[ML CSI sensing](../ml-csi-sensing.md) ·
[Honest limitations of Wi-Fi sensing](../honest-limitations-of-wifi-sensing.md) ·
[Verification: tier-2 CSI](../verification-tier2-csi.md)
