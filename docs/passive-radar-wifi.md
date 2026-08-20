# Wi-Fi Passive & Bistatic Radar

*Using ambient Wi-Fi as an illuminator of opportunity — the principle, the hardware, the landmark literature, and where an unlocked Wi-Fi chip actually fits versus a real SDR.*

Passive radar (a.k.a. **passive bistatic radar, PBR**, or **passive coherent location, PCL**) turns a transmitter you do **not** control into your radar illuminator. You never transmit. You listen. If a Wi-Fi access point is already flooding a room with 2.4/5/6 GHz OFDM energy, that energy scatters off people, walls, and moving objects; a receiver that captures both the *direct* signal and the *scattered* signal can cross-correlate them and recover range and Doppler on the movers. This is the "see people through a wall using only the neighbour's Wi-Fi" idea — and it is real, but the honest version is narrower and more hardware-dependent than the headlines.

This page covers the physics, the two dominant hardware architectures (a pair of coherent SDR channels vs. a single Wi-Fi NIC's CSI), the landmark academic lineages, the open tooling, and the tier/capability mapping that tells you when the `passive-radar` flag is earned. For the underlying DSP building blocks see [`../docs/techniques.md`](../docs/techniques.md); for how any of this stacks up against a purpose-built radio see [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md).

---

## 1. The principle

### 1.1 Bistatic geometry

In a monostatic radar the transmitter and receiver are co-located and you measure round-trip delay. In a **bistatic** radar they are separated by a **baseline** of length *L*. The illuminator (Tx) and the receiver (Rx) sit at two fixed points; a target scatters energy from Tx to Rx.

The quantity you measure from time delay is the **bistatic range**:

```
R_bistatic = c · τ = (R_t + R_r) − L
```

where `R_t` is Tx→target distance, `R_r` is target→Rx distance, `τ` is the extra delay of the scattered path relative to the direct path, and `L` is the baseline. A single delay measurement does **not** give you a point — it gives you an **iso-range ellipse** with the transmitter and receiver at its two foci. Every target on that ellipse produces the same bistatic delay. You need a second observable (angle-of-arrival at the Rx, or a second receiver / second illuminator) to collapse the ellipse to a location. This is why multi-receiver or AoA-capable front ends matter for *localisation* as opposed to mere *detection*.

### 1.2 Bistatic Doppler

Motion shows up as a Doppler shift set by the rate of change of the *total* bistatic path `(R_t + R_r)`:

```
f_d = (1/λ) · d/dt (R_t + R_r)
```

For a target moving with radial speed contributions toward Tx and Rx, the classic monostatic special case reduces to `f_d = 2·v_radial/λ`. The carrier does the heavy lifting here:

| Band | λ | Doppler at 1 m/s (monostatic) |
|------|-----|-------------------------------|
| 2.4 GHz | ~12.5 cm | ~16 Hz |
| 5 GHz | ~6 cm | ~33 Hz |
| 6 GHz | ~5 cm | ~40 Hz |

A walking human (~1 m/s) is tens of Hz; limb micro-Doppler spreads that into a signature; breathing/heartbeat are sub-Hz and demand long coherent integration. The short Wi-Fi wavelength is the reason Wi-Fi is a *good* Doppler illuminator even though it is a poor ranging illuminator (next section).

### 1.3 Reference channel vs. surveillance channel

A passive radar receiver has (at least) **two channels**:

- **Reference channel** — a directional antenna (or a beam) pointed **at the illuminator** to capture the cleanest possible copy of the transmitted waveform. Because the transmitted Wi-Fi symbols are non-cooperative and unknown ahead of time, you must *acquire* them; the reference channel is your best estimate of `s_ref(t)`.
- **Surveillance channel** — an antenna pointed **at the scene** to capture the weak scattered returns `s_surv(t)`, ideally with the strong direct path suppressed.

For the cross-correlation to work, the two channels must be **phase-coherent** — sampled from a common clock/LO so their relative phase is stable over the coherent processing interval. This coherence requirement is the single most important hardware constraint, and it is exactly what an ordinary Wi-Fi NIC does **not** give you across two independent antennas.

### 1.4 The cross-ambiguity function (CAF)

The core estimator is the **cross-ambiguity function**, correlating the surveillance signal against delayed, Doppler-shifted copies of the reference:

```
χ(τ, f_d) = ∫  s_surv(t) · s_ref*(t − τ) · e^(−j2π f_d t)  dt
```

Evaluating `|χ(τ, f_d)|²` over a grid of delays `τ` and Doppler shifts `f_d` produces the **range–Doppler map** (a.k.a. delay-Doppler surface). Peaks are moving scatterers; their `τ` gives bistatic range, their `f_d` gives bistatic velocity. Efficient implementations compute this as batched FFTs (the "fast CAF" / cross-correlation-by-FFT), because a naïve double loop over the grid is prohibitive.

### 1.5 Direct-Signal Interference (DSI) cancellation

The dominant problem in PBR is that the **direct path** from illuminator to surveillance antenna is 60–90 dB stronger than any target echo. Its delay-Doppler sidelobes bury the targets. Before (or during) the CAF you must remove it. The standard tools:

- **Physical isolation / antenna nulling** — directionality, screening, or a spatial null steered at the illuminator.
- **CLEAN** — iteratively estimate and subtract the strongest (direct + static clutter) returns.
- **ECA — Extensive Cancellation Algorithm** (and its block/batch variants ECA-B/ECA-C, from the Sapienza/Colone line) — project the surveillance signal onto the subspace spanned by delayed/Doppler-shifted copies of the reference and subtract, removing the zero-Doppler direct signal *and* stationary clutter in one adaptive step.

Static clutter (walls, furniture) sits at zero Doppler; cancelling zero-Doppler returns is what lets movers pop out. This is why passive Wi-Fi radar is fundamentally a **moving-target** sensor.

### 1.6 Wi-Fi as an illuminator: strengths and pains

| Property | Consequence for radar |
|----------|----------------------|
| Bandwidth 20 / 40 / 80 / 160 MHz | Range resolution `ΔR ≈ c/(2B)` ≈ **7.5 m** (20 MHz), **3.75 m** (40), **1.9 m** (80), **0.94 m** (160). Coarse — Wi-Fi is a *detector/Doppler* sensor, not a fine ranger. |
| Carrier 2.4/5/6 GHz | Excellent Doppler sensitivity (short λ), compact antennas. |
| OFDM waveform | Near-ideal "thumbtack" ambiguity function *while transmitting* — good for correlation. |
| **Packetised / bursty traffic** | The illuminator is **intermittent**. Idle gaps, and the periodic training fields / preambles, put structure into the effective waveform → **ambiguity sidelobes** in Doppler and range. Managing these dominated the early UCL/Sapienza work (e.g. Doppler-sidelobe control). |
| Non-cooperative, unknown symbols | You must recover the reference from the air; demodulate-and-reconstruct ("clean reference") schemes improve on a raw antenna copy. |
| Ubiquitous, free, licence-exempt | The whole appeal: illuminators everywhere, and you never transmit → generally no spectrum licence needed to *receive*. |

---

## 2. Two hardware architectures

Everything in the wild is a variation on one of these two.

### 2.1 Architecture A — coherent multi-channel SDR (the "real" passive radar)

Two (or more) **phase-coherent receive channels** sharing one clock and LO:

- One channel = reference (aimed at the AP), one channel = surveillance (aimed at the scene).
- Capture **raw IQ** on both, cancel DSI, compute the CAF, plot range-Doppler.
- Add channels (3–5) to get AoA on the surveillance side → **localisation**, not just detection.

Typical platforms:

| Platform | Coherent channels | Notes |
|----------|-------------------|-------|
| **USRP** (N2x0/X310, MIMO/OctoClock) | 2–8+ | The academic workhorse — Chetty/UCL and Colone/Sapienza prototypes are USRP/dedicated-front-end class. Shared 10 MHz + PPS enforce coherence. |
| **bladeRF 2.0 micro** | 2×2 MIMO on one chip | Two phase-coherent RX on a single AD9361 — a cheap genuine 2-channel PBR front end. |
| **KerberosSDR / KrakenSDR** | 4 / 5 coherent RTL-SDR tuners | Purpose-built coherent RTL-SDR arrays; a noise-source sample injects a calibration reference so the tuners can be phase-aligned. Firmware: `heimdall_daq_fw`. Primarily marketed for direction-finding (`krakensdr_doa`), and the KerberosSDR generation shipped a community passive-radar demo. Cheap, but RTL bandwidth (~2.4–2.56 MHz usable) is far below a Wi-Fi channel, so these shine on **FM/DAB/DVB-T** illuminators, not on wideband Wi-Fi. |

For Wi-Fi specifically you want a front end that can actually digitise ≥20 MHz of instantaneous bandwidth coherently on two channels — i.e. bladeRF/USRP class, not RTL class. See the SDR lineage notes in [`../projects/rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md) and the platform comparison in [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md).

### 2.2 Architecture B — a single Wi-Fi NIC's CSI (the accessible cousin)

Here the illuminator (an AP) and the receiver (a Wi-Fi NIC) are already a bistatic pair — but instead of raw IQ you read the NIC's **Channel State Information**: per-subcarrier complex channel estimates the demodulator computes anyway. Motion perturbs the multipath channel; the time-series of CSI amplitude/phase carries Doppler and micro-Doppler you can process much like a radar return (spectrograms, Doppler bins, activity classification).

- The Tx symbols are known/cooperative (it's decoded traffic), so there is **no reference-channel acquisition problem** — the NIC has already equalised against the pilots.
- But you get **decoded, per-subcarrier CSI**, not coherent wideband IQ, and there is **no independent, steerable reference or surveillance antenna pair** — so you cannot form a classic clean CAF / range-Doppler surface. What you get is closer to a **monostatic-flavoured channel-perturbation sensor**: excellent for presence, breathing, gesture, and gait Doppler at short range; weak for standoff bistatic ranging.
- Tooling and chip support live in the CSI ecosystem: see [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md), [`../projects/nexmon.md`](../projects/nexmon.md), and [`../projects/openwifi.md`](../projects/openwifi.md). `openwifi` is notable because, being a full FPGA PHY, it *can* expose pre-equalisation raw samples — the closest a "Wi-Fi chip" comes to true SDR IQ.

The UCL group made this dichotomy explicit and measured it head-to-head in **"A Taxonomy of Wi-Fi Sensing: CSI vs Passive Wi-Fi Radar"** (see references) — the canonical read on when each approach wins.

---

## 3. Landmark work

Two academic lineages built the field, plus the MIT "see through walls" line that popularised it.

### 3.1 UCL — Chetty, Smith, Woodbridge, Tan, Li, Shi (passive Wi-Fi radar for people)

The University College London group is the reference lineage for **through-the-wall human sensing with passive Wi-Fi**:

- **Chetty, Smith, Guo, Woodbridge (2009)** — *Target detection in high clutter using passive bistatic Wi-Fi radar* — the early demonstration.
- **Chetty, Smith, Woodbridge (2012)** — *Through-the-Wall Sensing of Personnel Using Passive Bistatic Wi-Fi Radar at Standoff Distances*, *IEEE Trans. Geoscience & Remote Sensing* 50(4):1218–1226 — the landmark paper: detecting and Doppler-tracking people **through a brick wall** using only ambient Wi-Fi, at standoff, RX-only.
- **Tan, Woodbridge, Chetty (2014)** — *A real-time high resolution passive Wi-Fi Doppler-radar and its applications* — real-time Doppler processing for indoor monitoring.
- **Li, Piechocki, Woodbridge, Tang, Chetty (2021)** — *Passive Wi-Fi Radar for Human Sensing Using a Stand-Alone Access Point*, *IEEE TGRS* 59(3):1986–1998 — a self-contained AP acting as its own passive-radar node.
- **Shi, Chetty, Julier (2019)** — *Passive Activity Classification Using Just Wi-Fi Probe Response Signals* — exploiting management frames as the illuminating waveform.

### 3.2 Sapienza (Rome) — Colone, Falcone, Bongioanni, Lombardo (signal processing & localisation)

The Sapienza University group built out the **DSP and localisation** theory:

- **Falcone, Colone, Bongioanni, Lombardo (2010)** — *Experimental results for OFDM Wi-Fi-based passive bistatic radar*.
- **Falcone, Colone, Lombardo (2011)** — *Doppler frequency sidelobes level control for Wi-Fi-based Passive Bistatic Radar* — directly attacking the intermittent-waveform ambiguity problem.
- **Colone, Falcone, Bongioanni, Lombardo (2012)** — *Wi-Fi-Based Passive Bistatic Radar: Data Processing Schemes and Experimental Results*, *IEEE Trans. Aerospace & Electronic Systems* 48(2):1061–1079 — the comprehensive processing-chain reference (reference reconstruction, ECA-family DSI cancellation, CAF).
- **Falcone, Colone, Macera, Lombardo (2012)** — *Localization and tracking of moving targets with Wi-Fi-based passive radar* — moving from detection to tracking.
- **Martelli, Murgia, Colone, Bongioanni, Lombardo (2017)** — *Detection and 3D localization of ultralight aircrafts and drones with a Wi-Fi-based Passive Radar* — extending the technique outdoors to small aerial targets.
- **Milani, Colone, Bongioanni, Lombardo (2018)** — *Wi-Fi emission-based vs passive radar localization of human targets*.

### 3.3 The MIT "See Through Walls with Wi-Fi" line (Adib, Katabi et al.)

The line that put "Wi-Fi vision" in the press — and where accuracy matters, because not all of it is *passive*:

- **Adib & Katabi (2013), *"See Through Walls with Wi-Fi!"*, ACM SIGCOMM** — **Wi-Vi**. It detects and tracks moving people behind a wall, but its mechanism is **active MIMO nulling**: two transmit antennas null the static direct/wall reflection so the receiver sees only movers, then it tracks the mover's angle over time (an inverse-SAR-style trajectory). It *uses* Wi-Fi-band signals but it **transmits its own** — this is an active technique, not an ambient-illuminator passive radar. Worth reading precisely to see the contrast with true PBR.
- **WiTrack (Adib et al., NSDI 2014)** and **RF-Capture (SIGGRAPH Asia 2015)** — the same group's follow-ons; both are **active FMCW** systems (they sweep their own wideband chirp), *not* passive and *not* standard Wi-Fi waveforms. Cite them for the sensing results, but do **not** call them passive Wi-Fi radar.
- **Adib (2019), *"Seeing with radio"*, IEEE Spectrum** — an accessible overview of the line.

> **On "PADAR":** a specific landmark system published under the exact name *PADAR* could not be verified in the passive-Wi-Fi-radar literature (a Crossref bibliographic search returned no matching title). If you encountered the name, it most plausibly refers generically to a *passive detection-and-ranging* demonstrator; the *verified* canonical prototypes are the UCL (Chetty/Woodbridge) and Sapienza (Colone/Lombardo) systems above, with **KrakenSDR/KerberosSDR** as the accessible modern hobbyist equivalent. Treat any unsourced "PADAR" claim as **unverified**.

---

## 4. Tooling

| Tool | What it does | Illuminators | Link |
|------|--------------|--------------|------|
| **`Max-Manning/passiveRadar`** | Clean Python reference implementation: reference/surveillance IQ → LMS/ECA-style clutter cancellation → range-Doppler via cross-ambiguity. The best-documented open CAF pipeline. | FM / DVB-T (RTL-SDR); adaptable | github.com/Max-Manning/passiveRadar |
| **`krakenrf/heimdall_daq_fw`** | Coherent multi-channel DAQ + calibration for the KerberosSDR/KrakenSDR arrays — provides the phase-aligned IQ streams any PBR/DoA app needs. | any | github.com/krakenrf/heimdall_daq_fw |
| **`krakenrf/krakensdr_doa`** | Direction-finding app on the 5-channel coherent array; the AoA side of localisation. (Passive-radar mode shipped with the earlier KerberosSDR software.) | any | github.com/krakenrf/krakensdr_doa |
| **`kit-cel/gr-radar`** | GNU Radio OOT for CW/FMCW/OFDM radar estimators (CAF, range-Doppler, CFAR) — bridges SDR IQ into radar processing. | SDR-general | github.com/kit-cel/gr-radar |
| **GNU Radio + `gr-radar`/custom flowgraphs** | Live capture and processing glue for USRP/bladeRF two-channel front ends. | any | see [`../projects/gnuradio-oot-modules.md`](../projects/gnuradio-oot-modules.md) |
| **MATLAB Phased Array / custom scripts** | The academic prototypes (UCL, Sapienza) run bespoke MATLAB/CAF code on recorded USRP IQ. | any | — |

Practical note: most turnkey open passive-radar software (Manning's, the Kraken lineage) is tuned for **narrowband broadcast illuminators** (FM ~200 kHz, DAB ~1.5 MHz, DVB-T ~7–8 MHz) because RTL-class front ends can't span a 20 MHz Wi-Fi channel. Doing Wi-Fi-band PBR properly means a wideband coherent front end (bladeRF/USRP) and, usually, your own CAF + ECA code following the Colone 2012 processing chain.

---

## 5. Where an unlocked Wi-Fi chip fits vs. a real SDR

This is the crux for this catalog. A repurposed Wi-Fi chip is **not** a drop-in passive-radar receiver, and it is important to say why.

**What true passive bistatic radar needs:** two (or more) **phase-coherent channels** delivering **raw wideband IQ**, so you can hold a clean reference, cancel the direct signal, and integrate a cross-ambiguity surface over a long CPI.

**What an unlocked Wi-Fi chip actually exposes:**

- **CSI** (Nexmon/Atheros/Intel/openwifi toolchains) — *decoded per-subcarrier channel estimates*, one antenna path, cooperative traffic. Great motion/Doppler sensor; **not** coherent dual-channel raw IQ. → radar-*like* sensing, **not** PBR.
- **Spectral scan** (Atheros `spectral_scan`, Nexmon spectral on some Broadcom) — *FFT magnitude bins*, no cross-channel phase. → occupancy/energy, not a CAF. See [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md).
- **Raw pre-equalisation samples** (`openwifi` FPGA PHY, some Nexmon research builds) — the rare case that approaches genuine IQ, on the platforms where firmware/FPGA is truly open.

So the Wi-Fi chip's real role in the passive-radar story is **Architecture B**: a cheap, ubiquitous **CSI-based motion/Doppler sensor** that happens to be bistatic (AP → NIC). It buys you presence, breathing, gesture, and gait at short indoor range. It does **not** give you standoff through-wall range-Doppler maps — for that you need Architecture A's two coherent SDR channels. The UCL taxonomy paper quantifies exactly this trade.

### 5.1 Tier & capability mapping

Mapping onto the project's SDR ladder ([`../docs/taxonomy.md`](../docs/taxonomy.md)):

| Setup | Radio | Delivers | Capability flags | Tier |
|-------|-------|----------|------------------|------|
| Two coherent SDR channels (bladeRF/USRP) doing CAF on ambient Wi-Fi | real SDR | coherent raw IQ ×2, CAF, range-Doppler | `raw-iq`, `passive-radar` (+`radar`) | **5** |
| KrakenSDR/KerberosSDR coherent RTL array (narrowband illuminators) | quasi-SDR | coherent raw IQ ×4–5 (narrowband) | `raw-iq`, `passive-radar` | **5** (narrowband) |
| `openwifi` FPGA PHY exposing pre-eq samples | open Wi-Fi PHY | near-IQ, one path | `raw-iq`, `open-firmware`, (bistatic sensing) | **5** (as an SDR) / functionally B |
| Unlocked Wi-Fi NIC — **CSI** Doppler sensing | Wi-Fi chip | per-subcarrier CSI time series | `csi` | **2** |
| Unlocked Wi-Fi NIC — **spectral scan** only | Wi-Fi chip | FFT magnitude bins | `spectral-scan` | **3** (but not usable for CAF) |

**Rule for the `passive-radar` flag in this database:** award it only when the setup delivers **coherent raw IQ suitable for cross-ambiguity processing** — i.e. a real/quasi SDR (Tier 5), or the rare open-PHY Wi-Fi platform that dumps coherent samples. A plain Wi-Fi NIC doing CSI motion sensing earns **`csi` at Tier 2**, described honestly as "radar-like bistatic channel sensing," **not** `passive-radar`. Reserving the flag this way keeps the catalog's central promise — *accuracy over bravado*.

---

## 6. Regulatory & safety notes

Passive radar's headline legal advantage: **you never transmit.** A pure passive/bistatic Wi-Fi radar (Architectures A and B, receive-only) uses licence-exempt spectrum you are merely *listening* to, so it sidesteps the transmit-licensing and duty-cycle rules that constrain any active technique. That is a genuine reason the field exists.

Caveats to keep it honest:

- **The moment you transmit, the rules change.** Wi-Vi-style MIMO nulling, FMCW (WiTrack/RF-Capture), or injecting your own reference beacon are **active** and fall under the transmit regulations for the band (EIRP limits, channel/duty rules, and in the US Part 15 / equivalent national regimes). Do not conflate these with passive radar.
- **Privacy/legal use.** Through-wall human sensing is powerful and surveillance-adjacent; deployment against people without consent may be unlawful regardless of the RF being licence-exempt. Treat it as a sensing capability with real ethical/legal weight.
- **Coherence hardware, not power, is the barrier.** Nothing here requires a power amplifier or antenna you must certify — the engineering cost is clock/LO discipline and DSP, not emissions.

---

## 7. Key references

**Passive Wi-Fi radar — UCL lineage**
- K. Chetty, G. E. Smith, K. Woodbridge, "Through-the-Wall Sensing of Personnel Using Passive Bistatic Wi-Fi Radar at Standoff Distances," *IEEE Trans. Geosci. Remote Sens.*, 50(4):1218–1226, 2012. DOI: [10.1109/TGRS.2011.2164411](https://doi.org/10.1109/TGRS.2011.2164411)
- K. Chetty, G. Smith, H. Guo, K. Woodbridge, "Target detection in high clutter using passive bistatic Wi-Fi radar," *2009 IEEE Radar Conf.* DOI: [10.1109/RADAR.2009.4976964](https://doi.org/10.1109/RADAR.2009.4976964)
- B. Tan, K. Woodbridge, K. Chetty, "A real-time high resolution passive Wi-Fi Doppler-radar and its applications," *2014 Int. Radar Conf.* DOI: [10.1109/RADAR.2014.7060359](https://doi.org/10.1109/RADAR.2014.7060359)
- W. Li, R. J. Piechocki, K. Woodbridge, C. Tang, K. Chetty, "Passive Wi-Fi Radar for Human Sensing Using a Stand-Alone Access Point," *IEEE Trans. Geosci. Remote Sens.*, 59(3):1986–1998, 2021. DOI: [10.1109/TGRS.2020.3006387](https://doi.org/10.1109/TGRS.2020.3006387)
- W. Li et al., "A Taxonomy of Wi-Fi Sensing: CSI vs Passive Wi-Fi Radar," *2020 IEEE Globecom Workshops.* DOI: [10.1109/GCWkshps50303.2020.9367546](https://doi.org/10.1109/GCWkshps50303.2020.9367546)
- F. Shi, K. Chetty, S. Julier, "Passive Activity Classification Using Just Wi-Fi Probe Response Signals," *2019 IEEE Radar Conf.* DOI: [10.1109/RADAR.2019.8835660](https://doi.org/10.1109/RADAR.2019.8835660)

**Passive Wi-Fi radar — Sapienza lineage (processing & localisation)**
- F. Colone, P. Falcone, C. Bongioanni, P. Lombardo, "Wi-Fi-Based Passive Bistatic Radar: Data Processing Schemes and Experimental Results," *IEEE Trans. Aerosp. Electron. Syst.*, 48(2):1061–1079, 2012. DOI: [10.1109/TAES.2012.6178049](https://doi.org/10.1109/TAES.2012.6178049)
- P. Falcone, F. Colone, C. Bongioanni, P. Lombardo, "Experimental results for OFDM Wi-Fi-based passive bistatic radar," *2010 IEEE Radar Conf.* DOI: [10.1109/RADAR.2010.5494565](https://doi.org/10.1109/RADAR.2010.5494565)
- P. Falcone, F. Colone, P. Lombardo, "Doppler frequency sidelobes level control for Wi-Fi-based Passive Bistatic Radar," *2011 IEEE RadarCon.* DOI: [10.1109/RADAR.2011.5960576](https://doi.org/10.1109/RADAR.2011.5960576)
- P. Falcone, F. Colone, A. Macera, P. Lombardo, "Localization and tracking of moving targets with Wi-Fi-based passive radar," *2012 IEEE Radar Conf.* DOI: [10.1109/RADAR.2012.6212229](https://doi.org/10.1109/RADAR.2012.6212229)
- T. Martelli, F. Murgia, F. Colone, C. Bongioanni, P. Lombardo, "Detection and 3D localization of ultralight aircrafts and drones with a Wi-Fi-based Passive Radar," *Int. Conf. Radar Systems (Radar 2017).* DOI: [10.1049/cp.2017.0423](https://doi.org/10.1049/cp.2017.0423)
- I. Milani, F. Colone, C. Bongioanni, P. Lombardo, "Wi-Fi emission-based vs passive radar localization of human targets," *2018 IEEE Radar Conf.* DOI: [10.1109/RADAR.2018.8378753](https://doi.org/10.1109/RADAR.2018.8378753)

**"See through walls" — MIT (active techniques; cite carefully)**
- F. Adib, D. Katabi, "See Through Walls with Wi-Fi!," *ACM SIGCOMM 2013* (CCR 43(4):75–86). DOI: [10.1145/2486001.2486039](https://doi.org/10.1145/2486001.2486039) — Wi-Vi, active MIMO nulling.
- F. Adib, "Seeing with radio," *IEEE Spectrum* 56(6):34–39, 2019. DOI: [10.1109/MSPEC.2019.8727144](https://doi.org/10.1109/MSPEC.2019.8727144)

**Tooling**
- Max Manning, *passiveRadar* — open CAF / clutter-cancellation pipeline: [github.com/Max-Manning/passiveRadar](https://github.com/Max-Manning/passiveRadar)
- KrakenRF org (`heimdall_daq_fw`, `krakensdr_doa`, `gr-krakensdr`): [github.com/krakenrf](https://github.com/krakenrf)
- KIT CEL, *gr-radar* GNU Radio OOT: [github.com/kit-cel/gr-radar](https://github.com/kit-cel/gr-radar)

**Adjacent (illuminator-of-opportunity, non-Wi-Fi, for context)**
- P. Karpovich, S. Kareneuski, T. P. Zieliński, "Practical Results of Drone Detection by Passive Coherent DVB-T2 Radar," *2020 IRS.* DOI: [10.23919/IRS48640.2020.9253800](https://doi.org/10.23919/IRS48640.2020.9253800)

---

*See also: [`../docs/techniques.md`](../docs/techniques.md) (CAF, clutter cancellation, spectral/CSI primitives) · [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md) (Wi-Fi chip vs. genuine SDR) · [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) · [`../projects/openwifi.md`](../projects/openwifi.md) · [`../projects/rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md).*
