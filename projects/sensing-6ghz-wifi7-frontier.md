# Sensing on 6 GHz and Wi-Fi 7: the Frontier

> **Scope.** The rest of this catalog asks *"can I get CSI out of this chip?"*
> This page asks a different, forward-looking question: **what does the newest
> Wi-Fi actually buy you as a *sensor*?** Wi-Fi 7 (802.11be) and the 6 GHz band
> change the *physics* of what a channel measurement can resolve — finer range,
> richer delay profiles, cleaner spectrum, multi-band diversity. The honest
> punchline, stated up front: **the sensing dividend of Wi-Fi 7 is real on paper
> but mostly unreachable with commodity CSI tooling today.** The silicon shipped;
> the extractors did not follow. This is a grounded map of the gap.
>
> Companion pages: reachability/driver status lives in
> [`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md); the standard that will
> formalize all of this lives in
> [`../docs/802-11bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md); the
> underlying sensing math lives in [`../docs/techniques.md`](../docs/techniques.md).
> This page is the bridge between them and does not repeat their scorecards.

---

## 1. Why bandwidth is the master variable for sensing

Wi-Fi sensing recovers the **channel impulse response (CIR)** — the set of
delayed, attenuated echoes that make up a multipath channel — from CSI, then
reads motion, range, breathing or gestures out of how that CIR changes. Every
sensing quantity that matters is gated by **occupied bandwidth `B`**, because
`B` sets how finely two echoes at different path-lengths can be separated.

The governing relations (see [`../docs/techniques.md`](../docs/techniques.md) for
the CSI→CIR derivation):

| Quantity | Formula | Meaning |
|---|---|---|
| Delay (time-of-flight) resolution | `Δτ = 1/B` | Smallest separable difference in echo arrival time |
| One-way path-length resolution | `c·Δτ = c/B` | Two reflectors closer than this merge into one CIR tap |
| Monostatic/radar range resolution | `ΔR = c/(2B)` | Round-trip range bin size |
| Unaliased CIR span | `1/Δf` | Max delay before wrap-around; set by subcarrier spacing `Δf`, **not** by `B` |

Because 802.11ax/be fixed OFDM subcarrier spacing at **78.125 kHz** (a quarter of
the legacy 312.5 kHz), the unaliased CIR window is a constant **`1/Δf ≈ 12.8 µs`
(~3.84 km of path)** across all Wi-Fi 6/7 widths. Widening the channel does not
extend that window — it **fills it with more, finer taps**. That is the whole
sensing story of Wi-Fi 7 in one sentence: *same delay span, dramatically finer
delay bins.*

### 1.1 The 320 MHz range-resolution ladder

`ΔR = c/(2B)` with `c = 3×10⁸ m/s`:

| Channel width | Standard | Radar range bin `ΔR` | One-way path bin `c/B` |
|---|---|---|---|
| 20 MHz | 11n | 7.5 m | 15 m |
| 40 MHz | 11n/ac | 3.75 m | 7.5 m |
| 80 MHz | 11ac/ax | 1.88 m | 3.75 m |
| 160 MHz | 11ac/ax/be | 0.94 m | 1.88 m |
| **320 MHz** | **11be** | **≈ 0.47 m** | **≈ 0.94 m** |

Going from the 160 MHz that AX210-class CSI already reaches to the 320 MHz of
Wi-Fi 7 **halves the range bin to ~47 cm**. That is the difference between
"someone is in the room" and "someone is at the desk, not the doorway" — sub-metre
localization and multi-person separation become geometrically feasible for the
first time on commodity Wi-Fi, *if* you can get the CSI out.

### 1.2 More subcarriers = a richer channel picture

Width also multiplies the number of complex CSI coefficients per spatial stream:

| Width | Total FFT tones | Data+pilot subcarriers (approx) |
|---|---|---|
| 20 MHz | 256 | 242 |
| 80 MHz | 1024 | 996 |
| 160 MHz | 2048 | 1992 |
| **320 MHz** | **4096** | **~3984** |

A single-stream 320 MHz CSI snapshot is nearly **4,000 complex numbers** — an
order of magnitude denser than the 52/56-tone records the classic
[nexmon_csi](nexmon.md)/Atheros toolchains were built around. Finer frequency
sampling of `H(f)` means a higher-resolution `h(τ)` after the IFFT, cleaner
super-resolution (MUSIC/ESPRIT) angle-of-arrival and time-of-arrival estimates,
and more input features for [ML pipelines](../docs/ml-csi-sensing.md). It also
means every legacy CSI *format* — fixed-width structs, radiotap plumbing, DMA
buffers — has to grow, which is a large part of why the tools lag (§4).

---

## 2. What the 6 GHz band brings to sensing — and takes away

6 GHz (5.925–7.125 GHz, ~1.2 GHz of spectrum) is not just "more channels." For a
*sensor* it changes the medium in three concrete ways.

**Cleaner channel → more stable CSI.** 6 GHz is greenfield: no microwave ovens,
no Bluetooth, no decade of legacy 2.4 GHz clutter, and far fewer incumbent Wi-Fi
networks than the DFS-fragmented 5 GHz band. A quieter noise/interference floor
means the CSI baseline drifts less from co-channel traffic, so the *change* signal
that motion/breathing detection lives on has a higher effective SNR. The band also
offers **contiguous** wide channels — up to three 320 MHz or seven 160 MHz
non-overlapping allocations — where 5 GHz forces you to stitch around DFS radar
channels and incumbents. Contiguity is what makes a full 320 MHz sensing channel
practical at all.

**Higher frequency → shorter range, sharper walls.** Free-space path loss rises
with frequency (Friis, `∝ f²`). Relative to 2.4 GHz, 6 GHz carries roughly
**+8 dB** more path loss (`20·log₁₀(6/2.4) ≈ 8 dB`) and ~1.6 dB more than 5 GHz,
plus worse material penetration. For sensing this is a **double-edged trade**: less
through-wall reach and smaller coverage cells, but also **better spatial
confinement** — 6 GHz energy stays more in-room, so a 6 GHz sensor is less likely
to pick up motion two rooms away and confound the reading. Fine-grained,
single-room sensing favors 6 GHz; whole-home presence favors 2.4 GHz.

**Regulatory gating pushes you toward passive sensing.** 6 GHz TX is governed by
power classes — **LPI** (Low-Power Indoor), **VLP** (Very-Low-Power) and
**Standard Power** (AFC-coordinated) — and many default regulatory domains keep
6 GHz **NO-IR** (no initiating radiation). The practical effect for a researcher is
that **active injection in 6 GHz is legally fraught and often silently disabled by
the driver**, while **passive monitor/CSI capture is fine**. That nudges 6 GHz
sensing toward *listening* to already-present EHT traffic rather than sounding the
channel yourself — see the TX-safety and regulatory checklist in
[`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md) §8 before any 6 GHz
transmit experiment.

---

## 3. MLO and multi-band: the new sensing degrees of freedom

Wi-Fi 7's **Multi-Link Operation (MLO)** aggregates 2–3 radios (2.4 / 5 / 6 GHz)
into one logical station. For communications this is about throughput and
latency; for *sensing* it is a genuinely new capability: **simultaneous CSI across
bands that see the environment differently.**

- **Frequency diversity.** The same motion imprints on 2.4, 5 and 6 GHz CSI with
  decorrelated fading. Fusing links smooths the deep-fade nulls that plague
  single-band sensing and hardens detection against a bad channel realization.
- **Complementary physics.** 2.4 GHz penetrates walls and gives coverage; 6 GHz at
  320 MHz gives ~47 cm range resolution but stays in-room. A multi-band sensor can
  use the low band for presence and the high band for fine localization
  *of the same target at the same instant.*
- **Spatial diversity for free.** MLO devices carry multiple antennas across links,
  widening the aperture available to AoA estimation.

**The honest caveat.** Every commodity CSI toolchain assumes **one netdev = one
PHY = one link**. MLO breaks that assumption: mac80211's monitor/CSI model is
single-link, so even where a driver exposes MLO, there is **no public tool that
delivers per-link, time-aligned CSI** from an MLO association. An "MLO-aware
capture model" is one of the open problems flagged in
[`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md) §9, and it is a
prerequisite for any of the multi-band fusion above.

---

## 4. Has the CSI tooling caught up? Mostly not.

This is the crux, and the answer is a grounded **no**. The sensing physics of §§1–3
is available in the *air* — every EHT PPDU carries EHT-LTFs that a receiver could
turn into 320 MHz CSI — but the extractors that would hand it to you have not
reached the newest silicon. Current state, mid-2026 (full driver/tier detail in
[`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md); tool internals in
[`csi-toolchains.md`](csi-toolchains.md)):

| Toolchain | Best it reaches | Wi-Fi 7 / 320 MHz? | Gap |
|---|---|---|---|
| [PicoScenes](picoscenes.md) / FeitCSI (Intel) | AX210 CSI incl. 6 GHz, **up to 160 MHz** | **No verified BE200/BE201 CSI** | AX210 CSI relied on RE'ing a specific firmware notification; the BE200 "Gale" blob is a new format nobody has publicly cracked |
| [nexmon_csi](nexmon.md) (Broadcom) | 11ac/11ax BCM43xx | **No — tops out below 11be** | Nexmon reaches *monitor* on BCM4398 (Pixel 8) but has no 11be CSI patch |
| MtkCSIdump (MediaTek `mt76`) | MT7915/MT7921, no firmware mod | **No — not MT7925/MT7927 @ 320 MHz** | Open driver + working older-gen extractor makes this the most tractable port |
| `ath12k` (Qualcomm WCN7850/QCN9274) | monitor landing 2025 | **No CSI, no spectral** | ath11k's spectral/FFT debugfs was never forward-ported |

So the situation is almost paradoxical: **the AX210 — a Wi-Fi 6E part — remains the
best-in-class commodity CSI radio, at 160 MHz**, precisely one width below where the
Wi-Fi 7 sensing dividend begins. The 320 MHz range resolution of §1.1 is real, and
today essentially **no public tool can deliver it from commodity silicon.** If you
need CSI now, the honest advice from the companion page stands: buy an AX210, not a
BE200, and accept 160 MHz. For genuine 320 MHz sensing research today, a
[USRP/bladeRF-class true SDR](../docs/true-sdr-comparison.md) sidesteps the
vendor-CSI bottleneck entirely — at the cost of building the PHY yourself.

### 4.1 The workaround that already works: beamforming-feedback sensing

There is one path that does *not* wait for a CSI extractor. **EHT beamforming
feedback** — the compressed steering/`V`-matrix reports STAs send back during
sounding — is transmitted **in the clear** and can be captured in ordinary monitor
mode on any 11ax/be link. **Wi-BFI**-style extraction reconstructs a
sensing-usable channel view from that feedback without any firmware patch or CSI
API. It is lossy compared to raw CSI, but it is the only method that scales to
Wi-Fi 7 traffic *today* on unmodified drivers, and it is band-agnostic (works in
6 GHz). See [`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md) §9 and
[`../docs/passive-radar-wifi.md`](../docs/passive-radar-wifi.md).

---

## 5. How 802.11bf will formalize the frontier

Everything above is *repurposing* — squeezing a sensing measurement out of silicon
the vendor never exposed for it. **IEEE 802.11bf** (published 2025) inverts that:
it makes sensing a **negotiated, spec-defined service** and, critically for this
page, it defines the measurement on top of the *same* HE/EHT sounding machinery,
which means **802.11bf sensing inherits the full Wi-Fi 7 bandwidth and 6 GHz reach
by construction.** Full treatment in
[`../docs/802-11bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md); the parts
that matter for the frontier:

- **Native, wideband CSI without a patch.** Sub-7 GHz 802.11bf sensing reuses
  NDP/NDPA sounding with EHT-LTFs, so a compliant STA can *request* per-subcarrier
  CSI at up to **320 MHz in the 6 GHz band** through a standard measurement
  exchange — the exact quantity that costs a firmware patch today. This is the
  clean, native **Tier-2** baseline the reverse-engineering craft currently has to
  fight for.
- **Airtime-aware reporting for the 6 GHz cell.** 320 MHz × ~4000 tones × multiple
  STAs is a lot of feedback. 802.11bf's **threshold-based / CSI-variation
  reporting** lets a STA report only when the channel changes past a negotiated
  bound — well matched to the presence/motion use-cases that dominate 6 GHz's
  short-range, single-room profile.
- **Multi-STA / multistatic by design.** Trigger-based sensing lets one AP harvest
  uplink and downlink CSI across a fleet of stations in a single coordinated
  exchange — the natural substrate for the multi-band, whole-room sensing MLO
  makes physically possible in §3.
- **What it still won't give you.** 802.11bf standardizes *access to a
  measurement*, not *control of the waveform*: **quantized/compressed** CSI, no
  monitor/injection guarantee, no raw IQ, no arbitrary-waveform TX. Research-grade
  320 MHz sensing that needs full-resolution CSI or channel-sounding control will
  still reach for the firmware path or a true SDR. 802.11bf raises the floor; it
  does not retire the craft — it moves the reverse-engineering *above* a clean
  Tier-2 line.

The timing gap is the honest part: a published amendment is not an exposed API.
Expect 802.11bf CSI to surface first inside vendor AP/mesh SDKs (presence,
fall-detection features), and only later — if at all — as a general Linux
`nl80211`/`cfg80211` capability. Until then, the practical Wi-Fi 7 sensing paths
are the lossy beamforming-feedback route (§4.1) or stepping back to 160 MHz AX210
CSI.

---

## 6. The frontier in one table

| Wi-Fi 7 / 6 GHz feature | Sensing dividend | Reachable today with commodity CSI? |
|---|---|---|
| 320 MHz channel | ~0.47 m range bin, multi-person separation | **No** — tools cap at 160 MHz |
| ~4000 subcarriers | High-res CIR, better super-resolution AoA/ToA | **No** — legacy CSI formats too narrow |
| 6 GHz band | Cleaner floor, stable CSI, in-room confinement | **Partial** — AX210 does 6 GHz CSI at ≤160 MHz |
| MLO multi-band | Frequency + physics diversity, fused presence/localization | **No** — no per-link CSI tool exists |
| EHT beamforming feedback | Patch-free channel view on any 11be link | **Yes** — Wi-BFI-style, lossy, works in 6 GHz |
| 802.11bf negotiated CSI | Native Tier-2 CSI at 320 MHz / 6 GHz, no patch | **Not yet** — standard published, no shipping host API |

**Bottom line.** Wi-Fi 7 and 6 GHz genuinely move the sensing frontier — halving
the range bin, quadrupling the subcarrier count, opening a clean band and a
multi-band aperture. But the frontier is currently a *silicon-ahead-of-tooling*
gap: the physics arrived, the commodity extractors did not. The most useful work
right now is closing that gap on the most open stack (porting MtkCSIdump forward on
`mt76`), harvesting beamforming feedback that is already in the clear, or waiting
for 802.11bf to make wideband 6 GHz CSI a negotiated, native measurement.

---

## References

Primary and authoritative sources (Wi-Fi 7 PHY, 6 GHz regulatory, tooling, and
802.11bf). Chip/driver citations are consolidated in the companion pages.

- IEEE 802.11 Task Group bf (TGbf) status page: <https://www.ieee802.org/11/Reports/tgbf_update.htm>
- R. Du et al., *"An Overview on IEEE 802.11bf: WLAN Sensing,"* arXiv:2207.04859: <https://arxiv.org/abs/2207.04859>
- F. Restuccia, *"IEEE 802.11bf: Toward Ubiquitous Wi-Fi Sensing,"* arXiv:2103.14918: <https://arxiv.org/abs/2103.14918>
- PicoScenes — 802.11ax CSI on Intel AX200/AX210, 6 GHz CSI/injection: <https://ps.zpj.io/> · <https://zpj.io/picoscenes-supports-csi-extraction-from-802-11ax-frames/>
- FeitCSI — Intel AX200/AX210 CSI/injection tool: <https://feitcsi.kuskosoft.com/>
- MtkCSIdump — CSI on MediaTek `mt76` without firmware modification: <https://github.com/MtkWifiRev/MtkCSIdump>
- nexmon / nexmon_csi (Broadcom, BCM4398 monitor on Pixel 8): <https://github.com/seemoo-lab/nexmon> · <https://github.com/seemoo-lab/nexmon_csi>
- Wi-BFI — beamforming-feedback extraction from 11ax/be traffic, arXiv:2309.04408: <https://arxiv.org/pdf/2309.04408>
- ath12k driver (Linux 6.3, WCN7850/QCN9274) — kernel docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath12k.html>
- FCC 6 GHz (U-NII-5–8) power classes / AFC order: <https://www.fcc.gov/document/fcc-opens-6-ghz-band-wi-fi-and-other-unlicensed-uses>

### Related pages in this catalog
- [`../docs/wifi7-and-6ghz.md`](../docs/wifi7-and-6ghz.md) — reachability scorecard and per-chip driver status (BE200, MT7925/MT7927, WCN7850/QCN9274, BCM4398)
- [`../docs/802-11bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md) — the standard that formalizes negotiated CSI sensing
- [`../docs/techniques.md`](../docs/techniques.md) — what CSI is and how the CIR/range math is derived
- [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md) · [`../docs/passive-radar-wifi.md`](../docs/passive-radar-wifi.md) · [`../docs/ftm-rtt-ranging.md`](../docs/ftm-rtt-ranging.md)
- [`../docs/honest-limitations-of-wifi-sensing.md`](../docs/honest-limitations-of-wifi-sensing.md) · [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md)
- [`csi-toolchains.md`](csi-toolchains.md) · [`picoscenes.md`](picoscenes.md) · [`nexmon.md`](nexmon.md)
