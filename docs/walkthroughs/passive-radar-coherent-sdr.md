# Building a Passive Radar with a Coherent SDR

> Practical companion to [../../docs/passive-radar-wifi.md](../../docs/passive-radar-wifi.md).
> Where that page asks *"can a Wi-Fi chip be the illuminator/receiver?"*, this page is the
> hands-on build guide for the **receiver** side using a genuinely coherent SDR — the path that
> actually produces range–Doppler detections today. For how these radios compare to Wi-Fi-chip
> "SDRs," see [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md).

## STRONG NOTE — this is a receive-only project, and that is the point

**Passive (bistatic) radar transmits nothing.** It listens to a powerful transmitter that is
*already on the air* — an FM broadcast station, DAB, DVB-T, or a Wi-Fi/cellular tower — and
detects the faint echoes those signals bounce off aircraft, cars, and rain. Because you never key
a transmitter, the build is **RX-only and legal to operate** in essentially every jurisdiction:
receiving is unlicensed almost everywhere, there is no emission to coordinate, and you are not an
"illuminator of opportunity" for anyone. The *only* legal caveats are downstream of RF:
some countries restrict decoding certain content (don't demodulate what you're not allowed to),
and export/ITAR rules can touch "radar" software in the abstract. Contrast this sharply with the
active-injection walkthroughs elsewhere in this catalog — **nothing here needs a shielded
enclosure, a dummy load, or a band plan.** You point antennas and correlate.

That legal simplicity is the whole appeal. The difficulty is entirely in the **signal processing
and the antenna geometry**, not in staying legal.

---

## 1. Why you need coherent channels

A passive radar measures the *time delay* and *Doppler shift* of an echo **relative to the direct
signal from the transmitter**. To do that you need two receive chains sampling **the same clock at
the same instant** so their relative phase is stable:

- **Reference channel** — an antenna pointed at (or otherwise dominated by) the illuminator. It
  captures a clean copy of what the transmitter sent. You do not know the broadcast content in
  advance, so you *measure* it here and use it as your matched-filter template.
- **Surveillance channel** — an antenna pointed at the airspace/target zone. It captures the same
  broadcast plus weak, delayed, Doppler-shifted echoes.

If the two channels drift in phase or sample offset, the cross-correlation smears and the (already
~60–90 dB weaker) echoes vanish under the direct signal. Two independent RTL-SDR dongles will
**not** work: each has its own free-running 28.8 MHz oscillator. You need one of:

| Option | Channels | How coherence is achieved | Cost tier | Notes |
|---|---|---|---|---|
| **KrakenSDR** | 5× RTL-SDR (R820T2 + RTL2832U) | Single shared clock; built-in noise source auto-correlates every channel to CH0 in software | ~$500 | Purpose-built coherent array; 24 MHz–1766 MHz, 8-bit, **2.56 MHz max BW/channel** |
| **KerberosSDR** | 4× RTL-SDR | Same shared-clock + noise-source scheme (KrakenSDR's predecessor) | (EOL) | Runs the same DAQ/software stack |
| **Clock-modded RTL-SDR pair** | 2× | Cut the oscillator trace on one dongle, feed both from one 28.8 MHz source (Piotr Krysik / "coherent RTL" mod) | ~$40 | DIY; no auto-calibration — you must correct sample offset yourself |
| **USRP B210 / X310** | 2 (B210) / many (phase-synced X310 + Octoclock) | Single FPGA/LO drives both RX chains; MIMO cable or Octoclock for multi-device | $$$ | Wider BW (up to tens of MHz) → far better range resolution than RTL |
| **BladeRF 2.0 micro / LimeSDR** | 2 | Shared LO across the two RX ports | $$ | Common in Max Manning's `passiveRadar` configs |

**Why the extra RTL-SDR channels help:** with FM you only strictly need 2 channels (reference +
surveillance). The KrakenSDR's 5 coherent channels let you (a) run several surveillance beams or
several illuminators at once, and (b) do **direction-of-arrival** on the echo so a detection
becomes a *bearing*, not just a range–Doppler blob. That is the same coherence the KrakenSDR was
designed for in its DF role — passive radar reuses it.

> **Bandwidth is destiny for range resolution.** Range resolution ≈ c / (2·B). An RTL/Kraken
> channel caps at ~2.4 MHz usable → ~60 m best-case range bin. A USRP at 20 MHz → ~7.5 m. FM
> stations are only ~150–200 kHz wide anyway, so the *illuminator's* bandwidth, not the SDR's,
> usually limits you with FM. Switch to DVB-T (6–8 MHz) or DAB (~1.5 MHz) and the SDR bandwidth
> starts to matter — which is why DVB-T passive radar wants a USRP-class front end.

---

## 2. Antenna placement — the part people underestimate

The dominant problem in passive radar is that the **direct path from the transmitter is 10^6–10^9
times stronger than the echo**. Antenna geometry is your first (and cheapest) 30–50 dB of that
fight, *before* any DSP clutter cancellation.

- **Reference antenna:** a **directional** antenna (Yagi, or a small dish for UHF DVB-T) aimed
  straight at the illuminator. You *want* the direct signal here — clean and strong. High SNR on
  the reference directly sets your correlation gain.
- **Surveillance antenna:** a directional antenna aimed at the target volume (e.g. the approach
  path of an airport), **steered away from the transmitter**. Every dB of front-to-back ratio
  toward the illuminator is direct-path suppression you don't have to do in software.
- **Isolation between them:** mount them back-to-back or with terrain/buildings blocking the line
  between reference and surveillance. Physical separation and cross-polarization help.
- **Cardioid / null-steering trick:** with a coherent 2-channel setup you can synthesize a
  cardioid pattern that places a **null on the transmitter** in the surveillance beam. This is the
  cheapest large suppression available and is standard practice in the KrakenSDR community.
- **FM illuminator selection:** pick a strong, *high-bit-rate/complex-content* station (talk and
  music with wide spectral occupancy correlate better than a pure tone/pilot). Note the exact
  carrier — you tune the reference channel to it. A local ~50–100 kW station a few tens of km away
  is ideal: strong direct path, and aircraft in between.

---

## 3. The processing chain

Given reference signal `s_ref[n]` and surveillance signal `s_surv[n]` at the same sample clock:

### 3a. Clutter / direct-path cancellation (do this FIRST)

The zero-delay, zero-Doppler direct signal and static clutter (buildings, ground) must be removed
or they mask everything. Standard methods, cheapest→best:

- **Adaptive/Wiener least-squares filter:** model the surveillance channel as a filtered copy of
  the reference over the first few range bins, solve for the filter, subtract. Kills direct path +
  near-in static clutter. This is the workhorse.
- **ECA / ECA-B (Extensive Cancellation Algorithm, Batched):** projects the surveillance signal
  onto the subspace spanned by delayed (and optionally Doppler-shifted) copies of the reference and
  removes that subspace. ECA-B processes in time batches so it also nulls slowly-moving clutter.
- **CLEAN:** iteratively finds the strongest peak (usually the direct path), subtracts a scaled
  reference at that delay/Doppler, repeats. Good for removing a few dominant returns.

### 3b. Cross-Ambiguity Function (CAF) → range–Doppler map

The detector is the **2-D cross-ambiguity function** of the cleaned surveillance signal against the
reference:

```
                N-1
  χ(τ, f_d) =   Σ   s_surv[n] · s_ref*[n − τ] · e^(−j 2π f_d n / f_s)
                n=0
```

- `τ` (delay) → **bistatic range** (range sum from Tx→target→Rx, minus the baseline).
- `f_d` (Doppler) → **bistatic radial velocity** of the target.
- A peak at `(τ, f_d)` = a moving target. The map updates every coherent processing interval
  (CPI), typically 0.2–1 s of data; longer CPI = finer Doppler + more processing gain but blurs
  fast targets.

Naïvely this is O(N²·Nτ·Nf). Practical implementations do it as **decimated cross-correlation +
FFT along the Doppler axis** (batches method), or on GPU. Daniel Kaminski's
[Ambiguity-function-CUDA](https://github.com/DanielKami/Ambiguity-function-CUDA) exists precisely
because the CAF is the compute bottleneck.

### 3c. Detection + tracking

Threshold the range–Doppler map (CFAR), then feed detections to a tracker. Max Manning's project
ships `simple_kalman_tracker.py` and `multitarget_kalman_tracker.py` to turn frame-by-frame blobs
into aircraft tracks; with a coherent array you also get **azimuth** per detection and can plot
true positions.

---

## 4. Open tools you can actually run

### KrakenSDR stack (turnkey coherent hardware)
- [github.com/krakenrf/heimdall_daq_fw](https://github.com/krakenrf/heimdall_daq_fw) — "Coherent
  data acquisition signal processing chain for multichannel SDRs." This is the layer that gives you
  time-aligned, phase-calibrated IQ from all channels (noise-source calibration described in the
  [KrakenSDR wiki](https://github.com/krakenrf/krakensdr_docs/wiki)).
- [github.com/krakenrf/krakensdr_doa](https://github.com/krakenrf/krakensdr_doa) — the DoA app;
  shares the DAQ front end. Passive-radar experiments in the community are built on top of the same
  Heimdall DAQ output (the KrakenSDR passive-radar app has circulated in beta; the DAQ + a CAF
  script is the reliable route). Pre-built Raspberry Pi 4 SD-card images lower the entry barrier.
- [github.com/krakenrf/gr-krakensdr](https://github.com/krakenrf/gr-krakensdr) — GNU Radio source
  block, so you can pipe coherent IQ straight into a GNU Radio flowgraph (e.g. gr-radar).

### Python passive-radar pipelines (bring your own coherent SDR)
- **Max Manning — [github.com/Max-Manning/passiveRadar](https://github.com/Max-Manning/passiveRadar)**
  (MIT). Pure-Python FM passive radar. Supports **≥2 coherent channels** on clock-modded RTL /
  KerberosSDR / LimeSDR / BladeRF 2.0 micro / **USRP B210**. Pipeline: `main.py --config
  prconfig.yaml` (clutter removal + range–Doppler, ~20 min on the sample set), then
  `range_doppler_plot.py` (video via ffmpeg), then the Kalman trackers. Ships a >6 GB example
  capture so you can validate the whole chain **before** touching hardware — do this first.
- **Daniel Kaminski — [github.com/DanielKami/PassiveRadar](https://github.com/DanielKami/PassiveRadar)**
  and the GPU CAF [Ambiguity-function-CUDA](https://github.com/DanielKami/Ambiguity-function-CUDA).
- **Jean-Michel Friedt — [github.com/jmfriedt](https://github.com/jmfriedt)** (`passive_radar`,
  plus spaceborne PBR work `NISAR_pbr`, `sentinel1_pbr`) — rigorous, well-documented academic
  treatments if you want the math to line up with the code.

### GNU Radio
- **gr-radar — [github.com/kit-cel/gr-radar](https://github.com/kit-cel/gr-radar)** (KIT, GPL-3.0,
  maint-3.10 / UHD 3.15). A general radar OOT module (see also
  [../../projects/gnuradio-oot-modules.md](../../projects/gnuradio-oot-modules.md)). It centers on
  *active* FMCW/CW estimation blocks, but the estimator/plot infrastructure and example flowgraphs
  are a useful scaffold, and it pairs naturally with `gr-krakensdr` as the coherent source.

---

## 5. Honest assessment of difficulty

This is **not** a plug-and-play weekend project, even though the hardware is cheap and legal.

- **Getting *any* detection** on strong FM with a KrakenSDR/Kerberos and Max Manning's code on the
  provided sample data: easy — an afternoon. This is the recommended first milestone.
- **Getting your *own* live capture to show aircraft:** moderate–hard. You will fight direct-path
  leakage, pick the wrong (too-quiet) FM station, and mis-place antennas. Expect several iterations
  on antenna aiming and cardioid nulling before the range–Doppler map is legible.
- **Reliable multi-target tracking / true position plots:** hard. Needs good geometry (baseline
  vs. target zone), a strong reference, tuned clutter cancellation (ECA-B), and often DoA from the
  full array. This is where the coherent 5-channel advantage pays off.
- **DVB-T/DAB illuminators for finer range:** hardest — you now need USRP-class bandwidth, more
  compute (GPU CAF), and more careful synchronization.

The two things that most separate "it works" from "it doesn't" are **(1) direct-path suppression**
(antenna geometry + clutter filter) and **(2) reference-channel SNR**. Spend your effort there
before optimizing anything else.

### Recommended path
1. Run Max Manning's pipeline on the **sample capture** → confirm your toolchain and read a real
   range–Doppler video.
2. Buy/borrow a **KrakenSDR** (or clock-mod a pair of RTL-SDRs) and stand up **heimdall_daq_fw** →
   confirm coherent, phase-calibrated IQ.
3. Reference Yagi on a strong local FM; surveillance Yagi on an airport approach; synthesize a
   **cardioid null on the transmitter**.
4. Clutter-cancel (Wiener/ECA) → CAF → CFAR → Kalman track. Iterate on geometry.

---

## References

- KrakenSDR org: <https://github.com/krakenrf>
- Heimdall coherent DAQ firmware: <https://github.com/krakenrf/heimdall_daq_fw>
- KrakenSDR DoA app: <https://github.com/krakenrf/krakensdr_doa>
- KrakenSDR docs/wiki (coherence via shared clock + noise-source calibration): <https://github.com/krakenrf/krakensdr_docs/wiki>
- gr-krakensdr (GNU Radio source): <https://github.com/krakenrf/gr-krakensdr>
- Max Manning `passiveRadar` (FM, multi-SDR, Kalman tracking): <https://github.com/Max-Manning/passiveRadar>
- Daniel Kaminski `PassiveRadar`: <https://github.com/DanielKami/PassiveRadar>
- Daniel Kaminski CUDA ambiguity function: <https://github.com/DanielKami/Ambiguity-function-CUDA>
- Jean-Michel Friedt passive/bistatic radar repos: <https://github.com/jmfriedt>
- gr-radar (KIT, Stefan Wunsch): <https://github.com/kit-cel/gr-radar>
- RTL-SDR.com passive-radar coverage: <https://www.rtl-sdr.com/tag/passive-radar/>

## See also
- [../../docs/passive-radar-wifi.md](../../docs/passive-radar-wifi.md) — passive radar using Wi-Fi as the illuminator/receiver.
- [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md) — where KrakenSDR/USRP sit versus repurposed Wi-Fi chips.
- [../../projects/gnuradio-oot-modules.md](../../projects/gnuradio-oot-modules.md) — gr-radar and related OOT modules.
