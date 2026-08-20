# Angle-of-arrival from multi-antenna CSI

*A focused walkthrough — Latent Radios, Cycle 10*

> [Indoor localization with Wi-Fi](../indoor-localization-wifi.md) surveys the whole
> positioning landscape (RSSI, CSI, FTM) and works one AoA number by hand. **This
> page is the deep dive on the AoA branch alone**: the array physics, the MUSIC
> super-resolution estimator, SpotFi's joint angle-and-time-of-flight trick, what
> hardware actually gives you enough *coherent* antennas, and — the step that
> silently decides whether any of it works — the inter-antenna phase calibration.
>
> Hard prerequisite: **[CSI calibration deep dive](csi-calibration-deep-dive.md)**.
> AoA is a *phase* estimator, and raw commodity CSI phase is garbage until it is
> sanitized and the per-chain offsets are removed. Read that first. This page
> assumes you can already produce a `packets × subcarriers × rx` complex CSI array
> from an [Intel 5300](intel-5300-csi.md), an [AX200/AX210](ax-csi-intel-ax200-ax210.md),
> or a coherent SDR.

This is a **Tier-2** exercise on the [SDR ladder](../taxonomy.md): everything here
runs on per-subcarrier complex CSI. You never need raw IQ — but you *do* need the
one thing a single-antenna sensing chip (ESP32, one-antenna dongles) can never give
you: **two or more receive chains that share a clock and an LO**, so their relative
phase means something.

---

## 1. The principle: a wavefront hits an array in phase-order

Point a source at an array of `M` antennas. A far-field signal is a plane wave; its
wavefront reaches the antennas at slightly different times, and "slightly different
time" at a single frequency **is** a phase difference. That phase progression across
the array encodes the incidence angle. That is the entire idea; MUSIC and SpotFi are
just ways to read it back robustly when many waves arrive at once.

### 1.1 Uniform linear array geometry

Model the receiver as a **uniform linear array (ULA)**: `M` antennas on a line,
spacing `d`. A plane wave arrives at angle `θ` measured from **broadside** (the
normal to the array). To reach antenna `m` the wavefront travels an extra
`m·d·sin(θ)` compared with antenna `0`:

```
        incoming wavefront, angle θ from broadside
              \      \      \      \
               \      \      \      \
    ───────O──────O──────O──────O───────   ULA, spacing d
          a0     a1     a2     a3
                 └──┬──┘
             extra path  d·sin(θ)  →  phase lag  2π d sin(θ)/λ
```

An extra path length `Δℓ = d·sin(θ)` is a phase lag `2π·Δℓ/λ`. So relative to
antenna 0, antenna `m` carries an *ideal* phase:

```
Φ_m(θ)  =  −2π · m · d · sin(θ) / λ
```

Stack those into the **steering vector** — the array's fingerprint for a lone source
at `θ`:

```
a(θ) = [ 1 , e^{jΦ₁} , e^{jΦ₂} , … , e^{jΦ_{M−1}} ]ᵀ ,   Φ_m = −2π m d sin(θ)/λ
```

With the usual half-wavelength spacing `d = λ/2`, `Φ_m = −π·m·sin(θ)`, and the
adjacent-antenna phase step is simply `π·sin(θ)`.

> **Why d = λ/2.** Larger than `λ/2` and the phase wraps past ±π before `θ` reaches
> ±90° → **grating lobes**, i.e. two different angles produce the same measured
> phases and you cannot tell them apart. Smaller than `λ/2` wastes aperture (worse
> resolution). Commodity Wi-Fi arrays are rarely exactly `λ/2` across the whole band
> — at 5.24 GHz `λ/2 ≈ 2.86 cm`, at 2.44 GHz `≈ 6.1 cm` — so a fixed physical spacing
> is only optimal at one frequency. You bake the *actual* `d` and the operating `λ`
> into `a(θ)`; do not assume `λ/2`.

### 1.2 The naïve inversion (and why it is a trap)

For a **single** clean wave you could measure the adjacent-antenna phase difference
`Δφ` and invert:

```
θ = arcsin( −Δφ · λ / (2π d) )       # single source, d = λ/2  →  θ = arcsin(Δφ/π)
```

Worked number: 5.24 GHz, `d = λ/2`, a source at `θ = 30°` gives
`Δφ = −π·sin(30°) = −π/2 = −90°` between adjacent antennas. Measure −90° of
progression, conclude 30°.

**Indoors this is meaningless.** You never receive one wave. The CSI at each antenna
is the coherent sum of the direct path plus a dozen reflections, each with its own
angle and delay. A single phase difference is an uninterpretable blend of all of
them. You need an estimator that resolves *multiple simultaneous* angles from the
*spatial covariance* of the array — that is MUSIC.

---

## 2. MUSIC: super-resolution from the noise subspace

**MUSIC** (MUltiple SIgnal Classification, Schmidt 1986) is the classic subspace
angle estimator. The insight: the array covariance matrix splits into a **signal
subspace** spanned by the true steering vectors and an orthogonal **noise subspace**;
sweep candidate angles and flag the ones whose steering vector is orthogonal to the
noise subspace.

### 2.1 The signal model

`D` sources (direct path + `D−1` reflections) arrive at angles `θ₁…θ_D`. Per
snapshot the length-`M` array vector is:

```
x  =  A · s  +  n
     A = [ a(θ₁) , a(θ₂) , … , a(θ_D) ]     (M × D steering matrix)
     s = complex source amplitudes (D × 1),   n = noise (M × 1)
```

A **snapshot** is one column of CSI across the antennas. On a Wi-Fi NIC you harvest
snapshots two ways: across **packets** (many frames of the same channel) and across
**subcarriers** (each OFDM tone is an independent look at the same geometry — the
trick SpotFi exploits, §3).

### 2.2 The algorithm

```
1. Covariance:      R = E[ x xᴴ ]  ≈  (1/N) Σ_n  x_n x_nᴴ         (M × M)
2. Eigendecompose:  R = Σ λ_i v_i v_iᴴ ,  λ₁ ≥ … ≥ λ_M
                    → D largest eigenvalues span the SIGNAL subspace
                    → the remaining (M−D) eigenvectors span the NOISE subspace E_n
3. Pseudo-spectrum: sweep θ, form a(θ), evaluate

                            1
        P_MUSIC(θ)  =  ───────────────────
                        a(θ)ᴴ E_n E_nᴴ a(θ)

4. Peaks of P_MUSIC(θ)  =  the arrival angles.
```

Why it spikes: a *true* steering vector lies in the signal subspace, hence is
(ideally) **orthogonal** to every noise eigenvector, so the denominator
`‖E_nᴴ a(θ)‖²` collapses toward zero and `P` shoots up. MUSIC is called
"super-resolution" because those peaks can be **sharper than the array's physical
beamwidth** — it is not beamforming, it is a null-spectrum of the noise subspace.

### 2.3 The coherent-multipath problem (the catch that bites everyone)

Plain MUSIC assumes the `D` sources are **uncorrelated**. Wi-Fi multipath violates
this badly: reflections are delayed, scaled *copies of the same transmitted signal*,
so they are **fully correlated (coherent)**. Coherent sources make the source
covariance rank-deficient, which collapses the signal subspace — `R` no longer has
`D` strong eigenvalues, the subspace split is wrong, and MUSIC misses paths or
invents them.

The standard fix is **spatial smoothing** (Shan, Wax & Kailath, 1985): partition the
`M`-element array into overlapping sub-arrays of size `L < M`, average their
covariance matrices, and run MUSIC on the `L×L` average. Averaging over spatial
shifts **de-correlates** the coherent sources (each sub-array sees the sources with a
different common phase), restoring rank. The price is aperture: an `M`-element array
smoothed into sub-arrays of size `L` behaves like an `L`-element array for
resolution, and can resolve at most `L−1` sources. This is exactly why AoA is *hungry
for antennas*: to resolve, say, 4 coherent paths you want `L ≥ 5`, i.e. `M` well
above 5 physical elements — uncomfortable on a 3-antenna Intel 5300. ArrayTrack's
answer was a 16-antenna research array; SpotFi's answer was to **synthesize** extra
array elements from the subcarriers (next section).

---

## 3. SpotFi: joint AoA + ToF super-resolution on 3-antenna cards

SpotFi (Kotaru, Joshi, Bharadia, Katti — SIGCOMM 2015) is the reference for getting
decimeter-ish localization out of **commodity 3-antenna Intel 5300 cards** instead of
an antenna farm. Two ideas do the work.

### 3.1 Subcarriers as a second dimension → virtual antennas

A propagation delay `τ` (time of flight) shows up in CSI as a **phase slope across
subcarriers**: a delay is a linear phase ramp in frequency,
`e^{−j 2π f_k τ}` for subcarrier frequency offset `f_k`. So the CSI matrix has *two*
structured phase progressions at once:

```
   across ANTENNAS  (index m):    phase step  ∝ sin(θ)     → Angle of Arrival
   across SUBCARRIERS (index k):  phase step  ∝ τ          → Time of Flight
```

SpotFi builds a **2-D smoothed covariance** whose steering vector is a function of
**both** `θ` and `τ`, and runs MUSIC over the joint `(θ, τ)` plane. Concretely it
arranges the `M`×`K` (antenna × subcarrier) CSI into a **spatially-smoothed
Hankel/block matrix** where sliding a window across subcarriers manufactures extra
"virtual antennas." A 3-antenna, 30-subcarrier 5300 capture becomes an effective
array large enough to spatially-smooth and resolve several coherent paths — the
subcarriers buy back the aperture the physical array lacks.

The joint steering vector combines both progressions:

```
a(θ, τ)  ⟵  outer structure of  { e^{−j 2π m d sin(θ)/λ} }  and  { e^{−j 2π k Δf τ} }
P(θ,τ)  = 1 / ( a(θ,τ)ᴴ E_n E_nᴴ a(θ,τ) )      # 2-D MUSIC pseudo-spectrum
```

### 3.2 Picking the direct path

The payoff of the joint plane: each resolved path is now a **`(θ, τ)` point**. The
**direct path is the one with the smallest time-of-flight** — even when a reflection
is *stronger* in amplitude. SpotFi clusters the `(θ, τ)` peaks over many packets and
scores clusters by a likelihood that rewards low ToF, small ToF/AoA variance, and
strong power, then reports that cluster's angle. This direct-path identification is
what lets a single AP produce a usable bearing in a rich multipath room; it is the
core of "decimeter localization on cheap hardware."

### 3.3 SpotFi also self-calibrates the timing offset

Because SpotFi already models the phase slope across subcarriers, it folds the
unknown **sampling-time/packet-detection offset** (which *also* looks like a slope,
see the [calibration deep dive](csi-calibration-deep-dive.md) §4) into the estimation
and sanitizes it out per packet before the 2-D MUSIC. That is why a faithful SpotFi
reimplementation "just works" on raw 5300 phase where a hand-rolled arcsin does not —
it never trusts absolute phase, only the *structure* across the two axes.

> **ArrayTrack (Xiong & Jamieson, NSDI 2013)** is the other pillar to cite: it did
> spatial-smoothed MUSIC AoA directly, but on a **custom WARP software-radio AP with
> up to 16 antennas**, hitting ~23 cm median. SpotFi's contribution was matching the
> spirit of that on 3-antenna commodity silicon by trading physical antennas for
> subcarrier-derived virtual ones.

---

## 4. What hardware gives you enough *coherent* antennas

The non-negotiable requirement: the receive chains must be **phase-coherent** —
driven by **one shared LO and one shared sample clock** — so the inter-antenna phase
is a stable function of geometry, not of two oscillators drifting against each other.
This is why you cannot bolt two USB dongles together and call it an array (their LOs
free-run independently; the [passive-radar walkthrough](passive-radar-coherent-sdr.md)
§1 makes the same point). Coherence is a property of the *radio*, not the antennas.

| Platform | Coherent RX chains | Bands usable for Wi-Fi AoA | CSI/phase source | Notes for AoA |
|---|---|---|---|---|
| **Intel IWL5300** | **3** (shared clock) | 2.4 / 5 GHz | Linux 802.11n CSI Tool, 30 subcarrier-groups | The SpotFi platform. 3 elements is the practical floor; lean on subcarrier virtual-antennas + spatial smoothing. See [intel-5300-csi](intel-5300-csi.md). |
| **Intel AX200/AX210** | **2** (2×2) | 2.4 / 5 GHz; **6 GHz on AX210** | PicoScenes / FeitCSI, per-subcarrier HE CSI | Only 2 antennas → AoA gives a single phase difference; you *need* the subcarrier dimension (SpotFi-style) to do anything super-resolved. Wider BW (160 MHz) sharpens ToF. See [ax-csi](ax-csi-intel-ax200-ax210.md). |
| **Atheros QCA9300 (AR9300)** | up to **3** | 2.4 / 5 GHz | PicoScenes / Atheros CSI Tool, up to 56 subcarriers | More subcarriers than the 5300; a common modern SpotFi-style platform. |
| **Coherent SDR array** (USRP N310/X310 + Octoclock, phased daughterboards) | 4–many | tune anywhere incl. 2.4/5/6 GHz | raw IQ → your own OFDM channel estimator | The "do it properly" path: real aperture, real spatial smoothing, arbitrary array geometry. Cost and DSP effort are high; Tier-5 hardware feeding a Tier-2 estimator. |
| **KrakenSDR** (5× RTL-SDR, shared clock + noise-source auto-cal) | **5** | **24 MHz – ~1.766 GHz only** | raw IQ | Purpose-built *coherent DF array* and the best cheap illustration of the AoA principle — **but it does not reach the Wi-Fi bands.** Learn/verify MUSIC AoA on it against VHF/UHF; to point it at 2.4/5 GHz Wi-Fi you would need external coherent downconverters on every channel (rare, fiddly). Treat KrakenSDR as the pedagogical/DF array, not a Wi-Fi CSI device. See [passive-radar-coherent-sdr](passive-radar-coherent-sdr.md). |

Two honest takeaways from the table:

1. **Commodity Wi-Fi AoA lives or dies on the subcarrier dimension.** With only 2–3
   physical antennas, the raw angular aperture is tiny; SpotFi's virtual-antenna
   construction is not an optimization, it is the thing that makes 2–3 antennas
   workable at all.
2. **KrakenSDR is the array everyone reaches for and the one that cannot see Wi-Fi.**
   Its coherence and price make it the ideal bench for *understanding* MUSIC AoA, but
   its RTL front end tops out around 1.7 GHz. Do not plan a Wi-Fi AoA build around it
   without solving the downconversion problem first.

---

## 5. The calibration prerequisite (do not skip)

Every RF chain on the same NIC has an **unknown, fixed phase offset** relative to the
others — from unequal PCB trace lengths, connector/pigtail lengths, and per-chain
analog front-end delay. This offset sits **directly on top of the geometric phase you
are trying to measure**, and it is typically *larger* than the signal. Feed
un-calibrated phase into MUSIC and the pseudo-spectrum peaks land at the wrong angle,
confidently. This is the number-one reason a reimplementation "runs" and produces
garbage bearings.

The [CSI calibration deep dive](csi-calibration-deep-dive.md) is the full manual;
here is the AoA-specific short version.

**What must be removed before MUSIC:**

- **Per-chain constant phase offset** `β_m` (the unknown array calibration) — the one
  that maps directly onto `sin(θ)`.
- **Per-packet common terms** — CFO residual and the random PLL phase offset. These
  are *shared by all chains on the card* (same LO), so they cancel when you work with
  **phase differences relative to a reference antenna**, or take the CSI ratio /
  conjugate product (calibration deep dive §5). Take antenna 0 as reference and every
  other antenna's phase becomes referenced and CFO-free.
- **Sampling-time / packet-detection slope** across subcarriers — folds into the ToF
  axis; SpotFi models it, or you linear-detrend it (deep dive §4) if you only want
  AoA.

**How to actually measure the per-chain offsets `β_m`** (choose one):

| Method | How | Pros / cons |
|---|---|---|
| **Wired reference (gold standard)** | Feed all RX chains from **one source through a matched power splitter and equal-length cables**. With a common input, any measured inter-chain phase is pure hardware offset `β_m` (plus a known cable delta). Record it, subtract it forever. | Most accurate; needs a splitter + matched cables and takes the card off the air. Re-do if you change pigtails. |
| **Known-angle source** | Put a transmitter at a **known broadside/known θ**, in as clean a line-of-sight as you can manage; the *residual* phase after subtracting the expected geometric term is `β_m`. | No splitter; but multipath contaminates the estimate — do it in an open space / anechoic setting. |
| **Blind / self-calibration** | Estimate `β_m` as extra unknowns jointly with the angles (SpotFi treats the timing offset this way; array-processing literature has joint DOA + array-calibration variants). | No extra hardware; more parameters → needs more snapshots and can be ill-conditioned with only 2–3 antennas. |

> **Sanity check that calibration worked** (mirrors the deep dive §9): capture a
> static line-of-sight source at a *known* angle after applying `β_m`. The MUSIC peak
> should sit at that angle within a few degrees and stay put across packets. If the
> peak wanders packet-to-packet, your CFO/PLL cancellation is broken (you are not
> referencing to antenna 0). If it is *stable but offset* by a fixed amount, your
> `β_m` estimate is wrong. Stable-and-correct is the only pass.

Amplitude calibration matters far less for AoA than phase, but grossly mismatched
per-chain gains will bias the covariance; normalize per chain if the chains differ by
more than a couple of dB.

---

## 6. A conceptual MUSIC pseudo-spectrum sketch

Teaching skeleton, **not** a product. It shows the 1-D spatial MUSIC with optional
spatial smoothing; the 2-D joint `(θ, τ)` SpotFi version is the same machinery with a
larger, subcarrier-smoothed matrix and a two-parameter steering vector. Assumes phase
is already sanitized and per-chain offsets `β_m` already subtracted (§5).

```python
import numpy as np

def steering(theta, M, d_over_lambda):
    """ULA steering vector for angle theta (radians), M antennas, spacing d/lambda."""
    m = np.arange(M)
    return np.exp(-1j * 2*np.pi * d_over_lambda * m * np.sin(theta))

def spatial_smooth(R, L):
    """Average overlapping L×L subarray covariances to de-correlate coherent paths.
       R is M×M; returns L×L. Needed because Wi-Fi multipath is coherent (§2.3)."""
    M = R.shape[0]
    Rs = np.zeros((L, L), dtype=complex)
    n_sub = M - L + 1                       # number of overlapping subarrays
    for i in range(n_sub):
        Rs += R[i:i+L, i:i+L]
    return Rs / n_sub

def music_aoa(X, d_over_lambda, n_src, L=None,
              grid=np.deg2rad(np.arange(-90, 90.1, 0.5))):
    """
    X : M×N complex snapshots — M antennas (phase-sanitized, β_m removed),
        N looks (packets and/or subcarriers). Each COLUMN is one snapshot.
    n_src : assumed number of arriving paths D (direct + reflections).
    L : subarray size for spatial smoothing (None → no smoothing, only valid
        if paths are uncorrelated, which indoors they are NOT).
    Returns (grid_radians, pseudo-spectrum). Peaks = arrival angles.
    """
    M = X.shape[0]
    R = (X @ X.conj().T) / X.shape[1]        # sample covariance, M×M

    if L is not None:
        R = spatial_smooth(R, L)             # → L×L
        M = L

    # eigendecomposition; eigenvalues ascending
    w, V = np.linalg.eigh(R)
    En = V[:, :M - n_src]                     # noise subspace = smallest (M−D) eigvecs
    EnEnH = En @ En.conj().T

    P = np.empty(grid.size)
    for i, th in enumerate(grid):
        a = steering(th, M, d_over_lambda)
        P[i] = 1.0 / np.real(a.conj() @ EnEnH @ a)   # ‖noise-proj‖⁻²  → spikes at true θ
    return grid, P

# ---- usage sketch ----
# X = sanitized_csi_snapshots        # shape (M_antennas, N_snapshots)
# grid, P = music_aoa(X, d_over_lambda=0.5, n_src=3, L=2)   # 3-ant card → tiny L
# peaks = grid[scipy.signal.find_peaks(10*np.log10(P))[0]]  # candidate AoAs (rad)
# For a single AP bearing: take the SMALLEST-ToF cluster (SpotFi), not the strongest.
```

Everything hard is in the assumptions this hides: `n_src` is unknown (estimate it
with AIC/MDL on the eigenvalues), `L` is painfully small on a 3-antenna card, the
snapshots must be genuinely independent looks, and the direct-path pick needs the ToF
axis. That gap between "the code runs" and "the angle is right" is the whole subject.

---

## 7. Honest accuracy limits

Read these before quoting any decimeter figure.

- **Antenna count is a hard ceiling.** An `M`-element array can resolve at most
  `M−1` sources (fewer after spatial smoothing, which needs `L−1 ≥ D`). A 3-antenna
  5300 has almost no raw angular aperture; a 2-antenna AX210 has *one* phase
  difference. Super-resolution and the subcarrier virtual-antenna trick stretch this,
  but they cannot manufacture information that `M` physical elements never captured.
  If you want genuine multi-path AoA, more antennas (or a real SDR array) is the only
  true fix.
- **Calibration error maps straight to angle error.** A few degrees of un-removed
  per-chain phase offset `β_m` is a few degrees of bearing bias — and at 10 m that is
  ~1 m of position error per AP before any other effect. Calibration quality, not
  algorithm cleverness, usually sets your accuracy floor.
- **Paper numbers are best-case ceilings.** ArrayTrack ~23 cm median used a **16-antenna
  WARP array**; SpotFi ~40 cm median used commodity 5300s **under controlled multipath
  with careful per-card calibration and multiple APs at surveyed positions.** Very few
  groups outside the original labs reproduce those numbers. **In a real building expect
  1–3 m**, not decimeters, once multipath is richer/dynamic (people, doors), geometry
  is imperfect, and calibration is merely "good."
- **You usually need multiple APs.** One AP gives a *bearing*, not a *position*.
  Triangulating requires ≥2–3 APs with **known positions and orientations**; surveying
  those precisely is its own error source. SpotFi's single-AP localization leans hard
  on the joint AoA+ToF direct-path pick to squeeze a position from one vantage — and
  that is exactly the fragile part.
- **Bandwidth bounds the ToF axis.** ToF resolution ≈ `1/B`; 20 MHz → 50 ns → ~15 m of
  range-sum resolution, far too coarse to separate close paths on ToF alone. 80/160 MHz
  (VHT/HE) helps, which is one concrete reason to prefer an AX210/QCA9300 wide-BW
  capture over a 20 MHz 5300 one when the ToF dimension carries the direct-path pick.
- **The hardware is aging.** The 5300/ath9k CSI toolchains are pinned to old kernels
  and increasingly hard to source; AX210 via PicoScenes/FeitCSI is the live path but
  is only 2 antennas. Factor sourcing and version-pinning pain into any AoA plan.

Bottom line: multi-antenna CSI AoA is real and genuinely reaches decimeters *in the
lab*, but it is the **least reproducible** Wi-Fi positioning method in the field.
Budget for the calibration fight, expect metre-level in the wild, and consider fusing
with FTM/RTT ([ftm-rtt-ranging](../ftm-rtt-ranging.md)) rather than betting everything
on angles.

---

## 8. Safety & legal note

**Capturing** CSI to estimate AoA is **passive** and low-risk — you are listening.
But the canonical measurement setup *injects* known HT/HE frames to guarantee a steady
stream of decodable packets to estimate the channel from (the 5300 and PicoScenes/
FeitCSI workflows both do this), and the wired-splitter calibration in §5 involves a
source. Injection and any bench source are **active RF emission you are responsible
for**:

- Transmit only on bands/channels and at power levels you are licensed to use in your
  regdomain. Prefer non-DFS channels (2.4 GHz ch 1/6/11, or U-NII-1 36–48 where
  permitted); commodity injection paths do **not** implement radar detection.
- For calibration, feed the splitter over **coax with attenuators**, not over the air,
  to keep emissions contained and the measurement repeatable.
- Do not inject onto networks you do not own. See
  [rf-safety-and-legal](../rf-safety-and-legal.md).

---

## References

- R. O. Schmidt. **"Multiple Emitter Location and Signal Parameter Estimation"**
  (MUSIC). *IEEE Trans. Antennas and Propagation* 34(3), 1986.
  <https://ieeexplore.ieee.org/document/1143830>
- J. Xiong, K. Jamieson. **"ArrayTrack: A Fine-Grained Indoor Location System."**
  USENIX NSDI 2013.
  <https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/xiong>
- M. Kotaru, K. Joshi, D. Bharadia, S. Katti. **"SpotFi: Decimeter Level Localization
  Using WiFi."** ACM SIGCOMM 2015.
  <https://web.stanford.edu/~skatti/pubs/sigcomm15-spotfi.pdf> ·
  DOI <https://doi.org/10.1145/2785956.2787487>
- T.-J. Shan, M. Wax, T. Kailath. **"On Spatial Smoothing for Direction-of-Arrival
  Estimation of Coherent Signals."** *IEEE Trans. ASSP* 33(4), 1985.
  <https://ieeexplore.ieee.org/document/1164649>
- D. Halperin, W. Hu, A. Sheth, D. Wetherall. **"Tool Release: Gathering 802.11n
  Traces with Channel State Information."** ACM SIGCOMM CCR, 2011.
  <https://dhalperi.github.io/linux-80211n-csitool/>
- Z. Jiang et al. **"Eliminating the Barriers: … the PicoScenes Wi-Fi Sensing
  Platform."** IEEE IoT Journal 9(6), 2022. DOI
  <https://doi.org/10.1109/JIOT.2021.3104666>
- KrakenSDR — coherent 5-channel RTL array (DF/passive-radar), 24 MHz–~1.766 GHz:
  <https://github.com/krakenrf> · docs/wiki
  <https://github.com/krakenrf/krakensdr_docs/wiki>

*Internal cross-links:* [Indoor localization with Wi-Fi](../indoor-localization-wifi.md) ·
[CSI calibration deep dive](csi-calibration-deep-dive.md) ·
[Intel 5300 CSI](intel-5300-csi.md) ·
[AX-CSI (AX200/AX210)](ax-csi-intel-ax200-ax210.md) ·
[Passive radar with a coherent SDR](passive-radar-coherent-sdr.md) ·
[FTM/RTT ranging](../ftm-rtt-ranging.md) ·
[Techniques](../techniques.md) ·
[Honest limitations of Wi-Fi sensing](../honest-limitations-of-wifi-sensing.md) ·
[True-SDR comparison](../true-sdr-comparison.md)
