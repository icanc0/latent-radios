# Indoor localization with Wi-Fi: CSI, RSSI, and FTM

*A practical tutorial — Latent Radios, Cycle 7*

GPS dies indoors. The dream of "GPS-grade location, but inside" has driven twenty
years of Wi-Fi research, and the recurring lesson is that the pretty numbers in
the papers (23 cm! 40 cm!) are produced under lab conditions that do not survive
contact with a real building. This page walks the three practical families of
Wi-Fi positioning — RSSI fingerprinting, CSI-based AoA/ToF, and 802.11mc FTM/RTT
— explains the physics of each, works a minimal CSI angle-of-arrival example by
hand, and is deliberately blunt about the gap between what a paper reports and
what you will measure on your own hardware.

See also: [`../docs/techniques.md`](./techniques.md) for the underlying
capture/measurement primitives, [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md)
for the firmware/driver tools that actually give you CSI, and
[`../docs/ftm-rtt-ranging.md`](./ftm-rtt-ranging.md) for the timing side of ranging
in depth.

---

## 0. The three approaches at a glance

| Approach | What it measures | Infrastructure | Typical *real-world* median error | Effort |
|---|---|---|---|---|
| **RSSI fingerprinting** | Received signal *strength* (1 scalar/AP) | ≥3 APs + a survey map | **2–4 m** (often worse across days) | Low to capture, high to maintain |
| **RSSI trilateration** (path-loss model) | RSSI → distance via log-distance model | ≥3 APs, known positions | **4–10 m** | Low, but fragile |
| **CSI AoA/ToF** (SpotFi/ArrayTrack style) | Per-subcarrier amplitude + **phase** | APs with **antenna arrays**, CSI-capable NICs | **0.4–1 m** in papers; **1–3 m** in the wild | Very high |
| **802.11mc FTM/RTT** | Round-trip **time of flight** | FTM-capable AP + client (Android 9+) | **1–2 m** (sub-meter best case) | Medium; needs compatible HW both ends |

The single most important honest statement on this page: **there is no cheap,
robust, sub-meter, off-the-shelf Wi-Fi positioning system today.** FTM is the
closest to "productizable" because it is standardized and shipping in phones, but
its accuracy is limited by multipath and clock resolution. CSI methods are the
most accurate on paper and the least reproducible in practice.

---

## 1. RSSI fingerprinting — simple, coarse, and everywhere

### 1.1 Why it works at all

Every Wi-Fi frame you overhear carries an RSSI (received signal strength
indicator) — a single scalar per packet per AP, reported by essentially every
Wi-Fi chip on Earth with no special firmware. Signal strength falls off with
distance and is shaped by walls, furniture, and bodies. A given point in a
building therefore has a semi-stable *vector* of RSSI values, one per audible AP:
its **fingerprint**.

### 1.2 The two modes

**Trilateration (model-based).** Convert each AP's RSSI to a distance using the
log-distance path-loss model:

```
RSSI(d) = RSSI(d0) - 10 * n * log10(d / d0)
```

where `n` is the path-loss exponent (~2 in free space, 3–5 indoors), `d0` a
reference distance. Solve for `(x,y)` given ≥3 AP positions. **This works poorly
indoors** — `n` is not constant, multipath makes RSSI non-monotonic with
distance, and human bodies swing RSSI by 5–10 dB. Treat it as a fallback, not a
method.

**Fingerprinting (survey-based).** The dominant approach. Two phases:

1. *Offline / training:* walk a grid of known reference points, record the RSSI
   vector at each. Store as a radio map.
2. *Online / positioning:* record the live RSSI vector, find the closest
   fingerprint(s).

Classic matchers:

- **k-Nearest-Neighbours (kNN)** in RSSI space (the RADAR system, Bahl &
  Padmanabhan, INFOCOM 2000). Euclidean distance over the RSSI vector; report the
  centroid of the *k* nearest fingerprints.
- **Probabilistic / Bayesian** (the Horus system, Youssef & Agrawala, MobiSys
  2005): model each cell's RSSI as a distribution, pick the maximum-likelihood
  cell. More robust to the inherent RSSI noise.
- **Modern ML:** random forests, and increasingly CNNs that treat the AP-RSSI
  vector (or a heatmap image of it) as input. These improve the *average* but
  inherit fingerprinting's structural weakness (below).

### 1.3 Minimal kNN fingerprinting sketch

```python
import numpy as np

# radio_map: dict  point (x,y) -> np.array of RSSI over APs (missing AP = -100 dBm)
def locate_knn(live_rssi, radio_map, k=3):
    pts   = np.array(list(radio_map.keys()))
    fps   = np.array(list(radio_map.values()))
    dists = np.linalg.norm(fps - live_rssi, axis=1)   # Euclidean in dBm-space
    idx   = np.argsort(dists)[:k]
    return pts[idx].mean(axis=0)                        # centroid of k nearest
```

That is genuinely the whole idea. The complexity is all in the survey and its
maintenance.

### 1.4 The honest limits of RSSI

- **Median error 2–4 m** is typical and generous; RADAR reported ~2.9 m median,
  Horus ~1.4 m under favourable conditions with dense APs.
- **Fingerprints rot.** Move furniture, change AP transmit power, add people, or
  swap the *receiving device* (every chip reports RSSI on its own scale) and the
  map drifts. Re-surveying is the real cost.
- **Device heterogeneity.** A phone and a laptop at the same spot report
  different RSSI. Calibration or differential/ratio features are needed for
  cross-device use.
- RSSI has **no phase, no timing, no direction** — it is one number. There is a
  hard floor on how well one scalar per AP can localize you. That floor is why
  people reach for CSI and FTM.

---

## 2. CSI-based localization — AoA and ToF from the subcarriers

### 2.1 What CSI gives you that RSSI does not

RSSI collapses the whole channel into one number. **Channel State Information
(CSI)** is the complex channel response `H(f)` per **OFDM subcarrier** per TX×RX
antenna pair — i.e. amplitude *and phase* across frequency and across space.
That richness is what enables two physical estimators:

- **Angle of Arrival (AoA)** — the *phase difference of the same subcarrier
  across the receiver's antennas* tells you the direction the signal came from.
- **Time of Flight / Time of Arrival (ToF/ToA)** — the *phase slope across
  subcarriers* (a delay is a linear phase ramp in frequency) tells you propagation
  delay, hence distance.

Combine AoA from multiple APs → triangulate. Or combine AoA + ToF at a single AP
to separate the direct path from reflections. This is the ArrayTrack / SpotFi
lineage.

Getting CSI at all requires a CSI-capable NIC + firmware/driver — see
[`../projects/csi-toolchains.md`](../projects/csi-toolchains.md). The canonical
extractors: **Intel 5300** (Halperin CSI Tool, 30 subcarriers, 3 antennas),
**Atheros ath9k** (Atheros CSI Tool, up to 56 subcarriers), **Broadcom via
Nexmon CSI** (up to 80 MHz, phone-class chips), and **ESP32 CSI** (single
antenna — fine for sensing, *not* for AoA).

### 2.2 The AoA physics — a uniform linear array

Model an AP receiver as a **uniform linear array (ULA)** of `M` antennas spaced
`d` apart. A far-field plane wave arriving at angle `θ` (measured from
broadside/normal) reaches antenna `m` a little later than antenna `m-1`, because
it must travel an extra `d·sin(θ)`:

```
        incoming wavefront at angle θ
             \   \   \   \
              \   \   \   \
   ------O------O------O------O------   ULA, spacing d
        a0     a1     a2     a3
                <-- extra path d·sin(θ) between adjacent antennas
```

That extra path is a phase shift. For wavelength `λ` and half-wavelength spacing
`d = λ/2`:

```
Δφ  =  2π · d · sin(θ) / λ   =   π · sin(θ)      (when d = λ/2)
```

So the phase of subcarrier *k* at antenna *m* is (ideally):

```
∠H_k(m)  =  ∠H_k(0)  +  m · Δφ   =   ∠H_k(0)  +  m · π · sin(θ)
```

**Invert it.** If you measure a clean phase difference `Δφ` between adjacent
antennas at one subcarrier:

```
θ  =  arcsin( Δφ / π )          # for d = λ/2
```

A worked number: at 5.24 GHz, `λ ≈ 5.72 cm`, so `d = λ/2 ≈ 2.86 cm`. A source at
`θ = 30°` gives `Δφ = π·sin(30°) = π/2 = 90°` between adjacent antennas.
Measure 90° of phase progression across the array → conclude 30°. That is the
entire kernel of AoA. Everything else is (a) cleaning the phase and (b) coping
with the fact that indoors you never receive *one* wave — you receive dozens of
multipath copies at once.

### 2.3 Why you can't just do `arcsin` — multipath and MUSIC

Indoors, `H_k(m)` is the sum of the direct path plus many reflections, each with
its own `θ` and delay. A single phase difference is a meaningless blend. You need
a **super-resolution spectral estimator** that resolves *multiple* simultaneous
angles. The standard tool is **MUSIC** (MUltiple SIgnal Classification):

1. Form the array covariance matrix `R = E[ x xᴴ ]` from the per-antenna signal
   vector `x` (one entry per antenna, using CSI as the snapshot).
2. Eigendecompose `R`. The `D` largest eigenvalues span the **signal subspace**;
   the remaining `M-D` eigenvectors span the **noise subspace** `E_n`.
3. Define the **steering vector** `a(θ) = [1, e^{jΔφ}, e^{j2Δφ}, …]`,
   `Δφ = 2π d sin(θ)/λ` — what the array *would* see for a lone source at `θ`.
4. Sweep `θ` and compute the **MUSIC pseudospectrum**:

```
P(θ)  =  1 / ( a(θ)ᴴ · E_n · E_nᴴ · a(θ) )
```

Peaks of `P(θ)` are the arrival angles: a true steering vector is orthogonal to
the noise subspace, so the denominator dives toward zero and `P` spikes.

**The two hard practical wrinkles:**

- **Coherent multipath breaks plain MUSIC.** Reflections are correlated copies of
  the direct signal, which makes `R` rank-deficient. The fix is **spatial
  smoothing** — average sub-array covariances to de-correlate — which costs you
  effective aperture (you need more antennas). ArrayTrack uses this directly.
- **Joint AoA–ToF (SpotFi's trick).** SpotFi builds a *2-D* smoothed MUSIC over
  **both** angle and time-of-flight simultaneously, using the phase-across-antenna
  *and* phase-across-subcarrier structure at once. This lets it identify which
  `(θ, ToF)` peak is the **direct path** even when reflections are stronger — the
  key to working with commodity 3-antenna Intel 5300 cards instead of a 16-antenna
  research array.

### 2.4 Phase sanitization — the step that quietly decides success

Raw commodity CSI phase is **not** the clean `∠H_k(m)` above. It is corrupted by:

- **CFO** (carrier frequency offset) — TX and RX oscillators differ → a per-packet
  phase rotation.
- **SFO** (sampling frequency offset) and **PDD** (packet detection delay) — timing
  errors → a *linear phase ramp across subcarriers* that masquerades as ToF.
- **Random per-packet phase offset** from the phase-locked loop.

These are large and, worse, partly random per packet. Absolute phase is
essentially unusable; you must work with **phase differences across antennas that
share a clock** (they cancel CFO), and you must **linearly detrend the phase
across subcarriers** to remove SFO/PDD before reading ToF. SpotFi's "phase
sanitization" fits and subtracts the linear slope across subcarriers. Skipping or
botching this step is the number-one reason a reimplementation "runs" but
produces garbage angles.

> Antenna **amplitude/phase calibration** matters too: different RF chains on the
> same NIC have unknown fixed phase offsets. You calibrate them with a known
> reference (e.g. a wired splitter feeding all chains, or a source at a known
> angle) once per card. The offsets are not documented — you *measure* them.

### 2.5 A minimal CSI-AoA pipeline (conceptual)

```
   CSI capture              per-packet cleanup            estimator
 ┌──────────────┐         ┌────────────────────┐      ┌──────────────┐
 │ H[k, rx, tx] │  ─────▶  │ - unwrap phase     │ ───▶ │ spatial-     │
 │ Intel5300 /  │         │ - remove CFO (use  │      │ smoothed     │
 │ Atheros /    │         │   antenna diffs)   │      │ MUSIC over   │
 │ Nexmon CSI   │         │ - detrend subcarr. │      │ (θ) or (θ,τ) │
 └──────────────┘         │   slope (SFO/PDD)  │      └──────┬───────┘
                          │ - antenna cal.     │             │
                          └────────────────────┘        peaks = AoA
                                                              │
                                        ┌─────────────────────▼──────────┐
                                        │ pick direct path (min ToF /     │
                                        │ SpotFi likelihood), triangulate │
                                        │ across multiple APs             │
                                        └─────────────────────────────────┘
```

```python
import numpy as np

def music_aoa(H, d_over_lambda=0.5, n_src=1, grid=np.deg2rad(np.arange(-90,90,0.5))):
    """
    H : complex CSI snapshot matrix, shape (M_antennas, N_snapshots)
        (one column per subcarrier or per packet, phase already sanitized)
    Returns the MUSIC pseudospectrum over `grid` (radians).
    NOTE: no spatial smoothing here — add it for coherent multipath.
    """
    M = H.shape[0]
    R = (H @ H.conj().T) / H.shape[1]          # M x M covariance
    w, V = np.linalg.eigh(R)                    # ascending eigenvalues
    En = V[:, :M - n_src]                       # noise subspace
    m = np.arange(M)[:, None]
    P = []
    for th in grid:
        a = np.exp(1j * 2*np.pi * d_over_lambda * m * np.sin(th))  # steering vec
        P.append(1.0 / np.abs(a.conj().T @ En @ En.conj().T @ a).item())
    return grid, np.array(P)                     # peaks of P => AoA(s)
```

This is a teaching skeleton, not a product. A working system adds spatial
smoothing, the joint AoA–ToF dimension, multi-packet aggregation, direct-path
selection, and per-card calibration — which is exactly where the reproducibility
cliff is.

### 2.6 Accuracy and the paper-vs-practice gap (be blunt)

- **ArrayTrack** (Xiong & Jamieson, NSDI 2013): ~23 cm median. But that used
  **WARP software radios with up to 16 antennas** and a custom AP — not commodity
  gear. The accuracy is real; the hardware is not something you own.
- **SpotFi** (Kotaru, Joshi, Bharadia, Katti, SIGCOMM 2015): ~40 cm median using
  commodity **Intel 5300** 3-antenna cards — its whole contribution was getting
  decimeter-ish accuracy without an antenna farm, via the 2-D super-resolution +
  phase sanitization. This is the reference to cite for "CSI localization on
  cheap hardware."
- **In the wild you should expect 1–3 m**, not decimeters, unless you replicate
  the geometry, calibration, and clean multipath of the papers. Common reasons the
  gap opens up:
  - Only 3 antennas on commodity NICs → weak angular resolution and limited
    spatial smoothing.
  - Phase sanitization and antenna calibration done imperfectly.
  - Multipath much richer / more dynamic than the evaluated environment (people
    moving, doors).
  - You need **multiple** APs with **known** positions and orientations; surveying
    those precisely is itself hard.
  - CSI extraction tools are pinned to old kernels/NICs (Intel 5300, ath9k) that
    are increasingly hard to source.
- **Reproducibility reality:** very few groups outside the original labs have
  reproduced SpotFi's exact numbers. Treat published medians as *best-case ceilings*
  achieved by the authors, not as spec sheets.

---

## 3. 802.11mc FTM / RTT — standardized time-of-flight ranging

Where CSI-AoA infers *direction*, **FTM measures distance directly** by timing a
round trip. This is the one branch that is standardized, shipping, and has a real
OS API. Full treatment in [`../docs/ftm-rtt-ranging.md`](./ftm-rtt-ranging.md);
the summary here places it against RSSI and CSI.

### 3.1 The mechanism

FTM (Fine Timing Measurement), added in **IEEE 802.11-2016 (originally 802.11mc)**,
runs a handshake: the initiator (phone) sends an FTM request; the responder (AP)
sends FTM frames and reports precise **t2/t3** timestamps; the initiator records
**t1/t4**. The round-trip time is

```
RTT  =  (t4 - t1)  -  (t3 - t2)
distance  ≈  RTT / 2  ×  c        (c = speed of light)
```

Light travels ~30 cm per **nanosecond**, so the entire game is timestamp
resolution. FTM responders timestamp in the PHY with picosecond-nominal clocks,
and the initiator averages over a burst of frames to beat down noise. Crucially,
FTM does **not** need known AP positions to get a *range*; for a *position* you
still trilaterate from ≥3 ranged APs.

### 3.2 The Android API (cite this)

Android exposes FTM as **Wi-Fi RTT** via `android.net.wifi.rtt`, added in
**API level 28 (Android 9 "Pie")**:

- `WifiRttManager` — the service.
- `RangingRequest` (builder: `addAccessPoint(ScanResult)` / `addResponder(...)`).
- `WifiRttManager.startRanging(request, executor, callback)`.
- `RangingResult` → `getDistanceMm()`, `getDistanceStdDevMm()`, `getRssi()`,
  `getStatus()`.
- Requires the AP to support 802.11mc FTM responder mode, and the phone's chipset
  + firmware to support RTT (`WifiRttManager.isAvailable()`), plus location
  permission.

```java
// sketch — Android Wi-Fi RTT
WifiRttManager mgr = (WifiRttManager) ctx.getSystemService(Context.WIFI_RTT_RANGING_SERVICE);
RangingRequest req = new RangingRequest.Builder()
        .addAccessPoint(scanResultFor11mcAp)     // an 802.11mc-capable AP
        .build();
mgr.startRanging(req, ctx.getMainExecutor(), new RangingResultCallback() {
    public void onRangingResults(List<RangingResult> results) {
        for (RangingResult r : results)
            if (r.getStatus() == RangingResult.STATUS_SUCCESS)
                Log.i("FTM", r.getDistanceMm() + " mm ± " + r.getDistanceStdDevMm());
    }
    public void onRangingFailure(int code) { /* ... */ }
});
```

### 3.3 Accuracy and limits

- **1–2 m typical**, sub-meter in clean line-of-sight with a good AP/phone pair;
  Google has cited ~1–2 m and improving. The `getDistanceStdDevMm()` field is your
  honest per-measurement confidence — use it.
- **Multipath biases it long/short** — a strong reflection can be mistaken for the
  direct path, adding metres. NLOS (a wall in the way) is the classic failure.
- **Hardware gating is the real barrier.** You need FTM-*responder* APs (a minority
  of deployed APs) and an FTM-*initiator* phone (Pixel and many recent flagships,
  but far from universal). No matching hardware → no FTM.
- **Better than RSSI, more deployable than CSI-AoA.** FTM is the pragmatic middle:
  standardized, in-OS, no antenna array, no fingerprint survey — but capped by
  clock resolution and multipath rather than pushing to decimeters.

---

## 4. Choosing an approach (decision guide)

- **You need "which room / which floor," cheap, works on any device today** →
  **RSSI fingerprinting.** Accept 2–4 m and budget for re-surveys. This is what
  virtually all shipping indoor-navigation apps actually use.
- **You control both AP and client hardware and want metre-level range without a
  survey** → **FTM/RTT.** Standardized, no radio-map maintenance, honest std-dev
  per reading.
- **You are doing research, control the APs, can add antenna arrays / SDRs, and
  want decimeter angles** → **CSI AoA/ToF (SpotFi/ArrayTrack style).** Expect a
  long fight with phase sanitization, calibration, and CSI-tool sourcing, and
  expect real-world 1–3 m unless you replicate lab conditions.
- **Passive / device-free sensing** (localizing a person who carries nothing) is a
  *different* problem living on the CSI side — see
  [`../docs/passive-radar-wifi.md`](./passive-radar-wifi.md).

A common production pattern is **fusion**: FTM ranges + RSSI fingerprints +
phone IMU/dead-reckoning, tied together with a particle filter or Kalman filter.
Fusion beats any single modality precisely because each one's failure modes
(RSSI drift, FTM multipath bias, IMU drift) are uncorrelated.

---

## 5. Public tools and datasets

**CSI extraction (prerequisite for any CSI method)** — details in
[`../projects/csi-toolchains.md`](../projects/csi-toolchains.md):

- **Linux 802.11n CSI Tool** (Halperin et al.) — Intel 5300, the classic. 30
  subcarrier groups × 3×3 antennas. <https://dhalperi.github.io/linux-80211n-csitool/>
- **Atheros CSI Tool** (Xie, Li, Li) — ath9k, up to 56 subcarriers.
  <https://wands.sg/research/wifi/AtherosCSI/>
- **Nexmon CSI** — Broadcom/Cypress incl. phone-class chips, up to 80 MHz.
  <https://github.com/seemoo-lab/nexmon_csi>
- **ESP32 CSI Toolkit** — cheap, single antenna → sensing yes, AoA no.
  <https://stevenmhernandez.github.io/ESP32-CSI-Tool/>

**Reference implementations / algorithms:**

- **SpotFi** — no official code release; multiple community reimplementations exist
  (search "SpotFi MATLAB" on GitHub). Reproducing its numbers is nontrivial; treat
  third-party ports as starting points, not ground truth.
- **Android Wi-Fi RTT sample** — Google's `WifiRttScan` demo app.
  <https://developer.android.com/develop/connectivity/wifi/wifi-rtt>

**Datasets (RSSI / fingerprinting):**

- **UJIIndoorLoc** (UCI ML Repository) — the standard large multi-building,
  multi-floor Wi-Fi RSSI fingerprint dataset.
  <https://archive.ics.uci.edu/dataset/310/ujiindoorloc>
- **IPIN competition** datasets — from the annual Indoor Positioning and Indoor
  Navigation conference; multiple modalities.

**Datasets (CSI):** far scarcer and hardware-specific — most CSI localization
papers release environment-specific captures (or none), which is itself a major
reason results don't transfer. Check each paper's repo; do not expect a clean
"ImageNet of CSI."

---

## 6. Honest closing summary

- **RSSI fingerprinting** is coarse (2–4 m), maintenance-heavy, and universally
  deployable — and it is what almost everything in production actually runs.
- **CSI AoA/ToF** is the most *accurate on paper* (ArrayTrack ~23 cm, SpotFi
  ~40 cm) and the *least reproducible* in practice; budget for 1–3 m, aging
  hardware, and a long calibration/phase-sanitization fight.
- **FTM/RTT** is the standardized, in-OS, metre-level middle ground — limited by
  clock resolution and multipath, and gated by whether your AP *and* client both
  support 802.11mc.
- Every decimetre claim you read was earned under controlled multipath, precise
  geometry, and careful per-card calibration. Reproduce those conditions or halve
  your expectations. When in doubt, **fuse** modalities and trust the reported
  confidence intervals over the headline median.

---

## References

- K. Joshi, D. Bharadia, M. Kotaru, S. Katti. *SpotFi: Decimeter Level
  Localization Using WiFi.* ACM SIGCOMM 2015.
  <https://web.stanford.edu/~skatti/pubs/sigcomm15-spotfi.pdf>
- J. Xiong, K. Jamieson. *ArrayTrack: A Fine-Grained Indoor Location System.*
  USENIX NSDI 2013. <https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/xiong>
- P. Bahl, V. N. Padmanabhan. *RADAR: An In-Building RF-based User Location and
  Tracking System.* IEEE INFOCOM 2000.
  <https://www.microsoft.com/en-us/research/publication/radar-an-in-building-rf-based-user-location-and-tracking-system/>
- M. Youssef, A. Agrawala. *The Horus WLAN Location Determination System.* ACM
  MobiSys 2005. <https://www.cs.umd.edu/~moustafa/papers/horus_usenix.pdf>
- D. Halperin, W. Hu, A. Sheth, D. Wetherall. *Tool Release: Gathering 802.11n
  Traces with Channel State Information.* ACM SIGCOMM CCR 2011.
  <https://dhalperi.github.io/linux-80211n-csitool/>
- Android developers. *Wi-Fi location: ranging with RTT (802.11mc / FTM).*
  <https://developer.android.com/develop/connectivity/wifi/wifi-rtt>
- Android reference. `android.net.wifi.rtt.WifiRttManager`.
  <https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager>
- IEEE Std 802.11-2016 (incorporating 802.11mc), Fine Timing Measurement.
  <https://standards.ieee.org/ieee/802.11/5536/>
- UCI ML Repository. *UJIIndoorLoc* Wi-Fi fingerprint dataset.
  <https://archive.ics.uci.edu/dataset/310/ujiindoorloc>
- R. O. Schmidt. *Multiple Emitter Location and Signal Parameter Estimation
  (MUSIC).* IEEE Trans. Antennas and Propagation, 1986.
  <https://ieeexplore.ieee.org/document/1143830>

*Internal cross-links:* [`../docs/techniques.md`](./techniques.md) ·
[`../docs/ftm-rtt-ranging.md`](./ftm-rtt-ranging.md) ·
[`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) ·
[`../docs/passive-radar-wifi.md`](./passive-radar-wifi.md)
