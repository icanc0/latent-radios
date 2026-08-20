# 60 GHz / 802.11ad mmWave: Radar, Imaging & Sensing

Almost every other chip in this catalog is a sub-6 GHz radio you pry open to read **per-subcarrier
CSI** (see [../projects/csi-toolchains.md](../projects/csi-toolchains.md)). The 60 GHz WiGig
(IEEE 802.11ad / 802.11ay) family is a different animal. At 60 GHz the wavelength is ~5 mm, so a
commodity router carries a **phased-array antenna** (dozens of elements) and does **analog
beamforming** in hardware. The "channel measurement" these chips hand you is not a subcarrier
transfer function — it is a **per-beam SNR vector**: how strong the link was for each of dozens of
steerable pencil beams. That vector is inherently *angular*, which is exactly the primitive a radar
wants. Point 36 narrow beams at a room, read the reflected power per beam, and you have a crude
angle-resolved reflectivity map — a poor man's imaging radar built from a $150 Wi-Fi router.

This file covers:

1. **The silicon** — Qualcomm/Wilocity WiGig chips (Sparrow QCA6320/QCA6310, VIVE
   [QCA9500](../chips/qualcomm-atheros.md)) and the two routers that made this research possible:
   the **TP-Link Talon AD7200** and **Netgear Nighthawk X10 (R9000)**.
2. **The tooling** — SEEMOO's [`talon-tools`](https://github.com/seemoo-lab/talon-tools) /
   `nexmon-arc` firmware-patching stack, the `sweep_dump` debugfs hook, and the FPGA testbeds
   (mm-FLEX, WiMi) used when the router isn't flexible enough.
3. **What beam-SNR actually buys you** — angle, coarse range, Doppler, and where it stops.
4. **The yardstick** — purpose-built mmWave radar (TI IWR/AWR FMCW, Infineon BGT60 as in Google
   Soli), so you can calibrate how far below a *real* radar the repurposed-Wi-Fi approach sits.

> **Regulatory note up front.** The 57–71 GHz band is unlicensed in most regions (FCC Part 15.255,
> ETSI EN 302 567) with generous EIRP allowances *for communications*. Firmware-patched routers that
> transmit custom sector sweeps still emit inside an associated 802.11ad link and stay within the
> stock RF envelope, which is the safe regime. Building a *transmitter* that sweeps arbitrary
> waveforms (mm-FLEX, or a TI radar reconfigured off-label) can leave the Part-15 communications
> allowance and enter radar/telemetry rules — check EIRP and duty-cycle limits for your locale before
> keying up. See [verification-tier4.md](../docs/verification-tier4.md).

---

## 1. Why 60 GHz is structurally radar-shaped

| Property | Sub-6 GHz Wi-Fi (e.g. [ath9k](../chips/qualcomm-atheros.md)) | 60 GHz WiGig (802.11ad) |
|---|---|---|
| Wavelength | ~12 cm (2.4 GHz) / ~6 cm (5 GHz) | **~5 mm** |
| Channel bandwidth | 20–160 MHz | **2.16 GHz** (×4 bonded in 11ay) |
| Range resolution (`c / 2B`) | ~1–5 m | **~7 cm** |
| Antenna | 1–8 discrete elements, digital MIMO | **32-element phased array**, analog beamforming |
| Native measurement | per-subcarrier CSI `H(f)` | **per-sector SNR** (beam-space power) |
| Sensing analogue | bistatic passive radar / CSI Doppler | **angle-resolved reflectivity / SAR** |

Two consequences fall out of the physics:

- **Huge bandwidth → real range resolution.** 2.16 GHz gives ~7 cm range bins if you can get at a
  time-of-flight or delay measurement. Stock firmware does *not* expose per-tap channel impulse
  response, so on a COTS router you usually can't cash this in directly — but the wideband PHY is why
  the FPGA testbeds (§4) and the TI radars (§6) get centimetric imaging.
- **Phased array → free angular sampling.** The chip *must* sweep beams to establish a link
  (beamforming training, below). Every sweep is, for free, an angular scan of the environment. Read
  the per-beam quality and you are reading an angle-power profile. This is the crux of every
  "60 GHz Wi-Fi radar/imaging" paper.

### 802.11ad beamforming training in one paragraph

An 11ad link is established by a **Sector Level Sweep (SLS)**: the initiator transmits a burst of
**Sector Sweep (SSW) frames**, one per antenna sector (direction) in its codebook, while the
responder listens omni; then they swap roles; then a feedback step picks the best TX/RX sector pair.
An optional **Beam Refinement Protocol (BRP)** fine-tunes with AGC and training (TRN) fields. The
device records a **received signal strength / SNR per sector** during this sweep — that table is the
sensing goldmine. The Talon's array supports a codebook of steerable sectors (research typically
drives ~36 usable TX beams plus a quasi-omni RX beam); each SSW carries a sector ID, so a sniffer or
a patched responder can attribute an SNR to a known beam direction.

---

## 2. The silicon: Wilocity → Qualcomm WiGig

Wilocity built the first practical 802.11ad chipset; Qualcomm acquired them in 2014 and folded the
line into the Qualcomm Atheros WiGig portfolio. All of it is driven in Linux by the mainline
**`wil6210`** driver (`drivers/net/wireless/ath/wil6210`), and all of it runs FullMAC firmware on
**Synopsys ARC** processor cores — which is the hook the reverse-engineering tooling grabs.

| Generation | MAC/Baseband | RF front-end | Bands | Seen in |
|---|---|---|---|---|
| **Sparrow** (2015) | QCA6320 | QCA6310 | 60 GHz | TP-Link Talon AD7200, Acer/Dell laptops (QCA6320) |
| **Sparrow+** | QCA6335 | QCA6310 | 60 GHz | Silex SX-PCEAD module, docks |
| **VIVE / "Sparrow" SiP** | **QCA9500** | integrated SiP | 60 GHz | Netgear Nighthawk X10 (R9000), APs |
| **Talyn** (11ay) | QCA64x0 | — | 60 GHz | later 11ay APs (limited FOSS support) |

> **Naming caveat worth internalizing.** Hardware teardowns of the **Talon AD7200** show discrete
> **QCA6320 (MAC/BB) + QCA6310 (RF)** Sparrow silicon. Much of the *sensing literature* nonetheless
> writes "the Talon implements a **QCA9500** transceiver." Both statements circulate because the chips
> are close cousins under one `wil6210`/ARC firmware family and the QCA9500 VIVE part is the
> better-known SKU. When you read a paper, treat "QCA9500-class 802.11ad" as the operative unit and
> confirm the exact PN against the board if it matters. The catalog already carries
> [`qualcomm-qca9500`](../chips/qualcomm-atheros.md); this file adds the Sparrow QCA6320 and the two
> router products as distinct records.

### The two research routers

- **TP-Link Talon AD7200** (2016) — the *first* consumer 802.11ad router, and the workhorse of the
  entire field. 32-element planar phased array, single 60 GHz stream (up to 4.6 Gb/s) alongside
  legacy 2.4/5 GHz radios. SEEMOO's LEDE port gives you a root shell and the ability to load patched
  firmware, which is what made `sweep_dump` possible. If you want to reproduce a 60 GHz Wi-Fi sensing
  paper, this is almost certainly the box you buy (used, since it's discontinued).
- **Netgear Nighthawk X10 (R9000)** — QCA9500-based, single-stream 60 GHz radio on a beefier ARM SoC
  host. Used in several sensing/localization papers (e.g. gesture recognition and "beyond-RF"
  studies). Less turnkey for firmware patching than the Talon because there is no equally mature
  open LEDE/OpenWrt image exposing the WiGig debugfs, but the same `wil6210`/ARC internals apply.

---

## 3. The tooling: `talon-tools`, `nexmon-arc`, and `sweep_dump`

Everything hangs off the fact that the WiGig firmware runs on an **ARC** core, and SEEMOO ported the
[nexmon](../projects/nexmon.md) C-based firmware-patching methodology to that architecture.

| Component | Repo | What it gives you |
|---|---|---|
| **talon-tools** | `github.com/seemoo-lab/talon-tools` | Umbrella project + getting-started tutorial + BibTeX of the papers |
| **lede-ad7200** | `github.com/seemoo-lab/lede-ad7200` | LEDE/OpenWrt image for the Talon AD7200 → root, custom firmware loading, the `sweep_dump` debugfs |
| **nexmon-arc** | `github.com/seemoo-lab/nexmon-arc` | nexmon patching framework retargeted to **ARC**; builds patches against `wil6210` fw **v4.1.0.55** and **v5.2.0.18** |
| **talon-sector-patterns** | `github.com/seemoo-lab/talon-sector-patterns` | Measured antenna patterns per sector (CoNEXT'17) → maps a beam/sector index to a real-world direction |
| **wil6210 (experimentation fork)** | `github.com/swetanksaha/wil6210` | Driver fork with hooks for experimentation on top of the mainline `ath/wil6210` |

### 3.1 Build the firmware-patch toolchain (nexmon-arc)

```bash
# host: Debian/Ubuntu. Install the ARC/nexmon build deps.
sudo apt install -y texinfo byacc flex libncurses5-dev zlib1g-dev libexpat1-dev \
                    texlive build-essential git wget bison gawk libgmp3-dev

git clone https://github.com/seemoo-lab/nexmon-arc.git
cd nexmon-arc

# Downloads the target firmware blob and BUILDS THE ARC GCC TOOLCHAIN from source.
make                      # first run is long — it compiles a cross-compiler
source setup_env.sh       # puts the ARC toolchain + nexmon vars on PATH

# Build the canonical smoke-test patch for fw v4.1.0.55:
cd patches/wil6210/4-1-0_55/hello_world
make                      # emits a patched firmware image
```

The patch model is identical to Broadcom nexmon (see
[../docs/walkthroughs/broadcom-d11-ucode.md](../docs/walkthroughs/broadcom-d11-ucode.md) and
[../projects/nexmon.md](../projects/nexmon.md)): you write C, the framework wraps it, resolves
symbols against a per-firmware symbol table, and splices your code into free ROM/RAM regions with
branch trampolines. The debug plumbing exposes three debugfs files once the patched firmware is
loaded:

- `console_dump_fw` — firmware (main MAC) console
- `console_dump_uc` — the **microcode (UC)** console (the beam-management engine)
- `sweep_dump` — **the per-sector-sweep signal-strength table** (the sensing output)

### 3.2 Read beam-SNR out of a live Talon

On a Talon flashed with the `lede-ad7200` image (phy index varies — it is usually `phy2` for the
WiGig radio; check `ls /sys/kernel/debug/ieee80211/`):

```bash
# One-shot dump of the last sector sweep's per-sector received signal strength:
cat /sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump

# Watch it update as an emitter sweeps beams past the environment:
watch -n 0.2 cat /sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump
```

Each row corresponds to a received SSW frame and carries the **source sector ID + measured signal
strength**. To turn a sector ID into a *direction*, cross-reference
[`talon-sector-patterns`](https://github.com/seemoo-lab/talon-sector-patterns), which contains the
measured gain-vs-angle pattern for each codebook sector. The typical experimental setup: one Talon
transmits SSW frames across N sectors; a second Talon (or the same node in a monostatic/reflection
setup) records the per-sector SNR; you assemble a length-N vector per time step; that vector *is*
your radar frame.

> **Do NOT hard-code sector counts, ROM addresses, or symbol offsets from this page.** They are
> firmware-version specific (`4.1.0.55` vs `5.2.0.18` differ) and board specific. Get them from *your*
> build: `nexmon-arc` ships the per-version symbol tables under `patches/wil6210/<ver>/`, and the
> `hello_world` patch shows how symbols are referenced. If you need to reverse a symbol yourself, load
> the firmware blob into **Ghidra with the ARC (ARCompact) processor module** — the same workflow as
> [../docs/walkthroughs/ghidra-setup-wifi-firmware.md](../docs/walkthroughs/ghidra-setup-wifi-firmware.md),
> just with the ARC language selected instead of the Broadcom/Xtensa targets — and label the sweep
> buffer where the UC writes per-sector RSSI before it hits `sweep_dump`.

---

## 4. What beam-SNR gives you — the honest capability ledger

A per-sector SNR vector is **not** per-subcarrier CSI. It is a real-valued (magnitude-only,
no phase) vector indexed by beam direction. Here is what you can and cannot recover on a stock-PHY
COTS Talon/X10:

| Radar observable | Recoverable from beam-SNR? | How / caveat |
|---|---|---|
| **Angle (azimuth/elev.)** | **Yes** | Argmax / centroid over sectors → direction; resolution ~ beamwidth (coarse, a few degrees to tens of degrees). Refine with the measured sector patterns. |
| **Reflectivity map / crude imaging** | **Yes (reported)** | Reflected power per beam over a scanned scene → angle-power image. SAR papers add aperture motion for cross-range resolution. |
| **Motion / Doppler** | **Partial** | Temporal changes in per-sector SNR track motion (walking, gestures); true Doppler needs phase/IQ the firmware doesn't export. It's power-Doppler, not frequency-Doppler. |
| **Range (time-of-flight)** | **No (stock)** | Firmware exposes no per-tap CIR or ToF; range comes only from geometry/triangulation, RSSI-vs-distance models, or the SAR aperture — not a direct delay measurement. |
| **Complex CSI (I/Q, phase)** | **No (stock)** | Needs the FPGA testbeds (§5) or a full PHY tap. |

**Ladder placement.** On the [taxonomy](../docs/taxonomy.md) ladder we score the COTS 802.11ad
router at **tier 2**. It clears tier 1 comfortably (patched firmware gives monitor of SSW frames and
injection of custom sectors), and it exports a *spatial channel-state measurement* (per-beam SNR)
that functions as the mmWave sensing primitive — richer than bare monitor/injection. We deliberately
**do not** flag `csi`, because beam-SNR is magnitude-only beam-space power, not per-subcarrier complex
CSI; over-claiming that flag would mislead. The router earns `monitor`, `injection`, `radar` (used as
a pseudo-radar in the literature) and `open-firmware` (nexmon-arc patchable). To climb higher — real
IQ, arbitrary 60 GHz waveforms, tier 4+ — you leave the router and pick up an FPGA front-end or a
purpose-built radar.

---

## 5. When the router isn't enough: FPGA front-ends (WiMi, mm-FLEX)

The COTS approach is cheap but shackled to the stock PHY. Two academic platforms give full baseband
access at 60 GHz and are the reference points when a paper needs raw IQ or arbitrary waveforms:

- **WiMi** (Sur/Zhang et al., SIGMETRICS'15, *"60 GHz Indoor Networking through Flexible Beams"*) —
  a 60 GHz software-radio testbed on a **WARP FPGA** baseband + high-speed ADC/DAC + a 60 GHz RF
  development board. It profiles flexible-beam links (SNR, obstacle detour via reflection paths) with
  full baseband control the Talon never gives you.
- **mm-FLEX** (Lacruz & Widmer, IMDEA, MobiSys'20) — an open, modular 60 GHz platform: **Xilinx
  Kintex UltraScale (AMC599)** baseband + an **Intel Core-i7 (AMC726)** host + the **Sivers IMA
  EVK06002** 60 GHz up/down-converter front-end, with **up to 2 GHz** instantaneous bandwidth and
  real-time processing. This is the tool for full-bandwidth 60 GHz channel sounding, arbitrary TX,
  and IQ-level radar experiments — effectively a mmWave [USRP-class](../chips/hardware-index.md)
  instrument (**tier 4–5**, but not a repurposed Wi-Fi chip, so it lives outside the core catalog).

These are the bridge between "repurposed WiGig router" (tier 2, cheap) and "purpose-built radar"
(tier 4–5, below).

---

## 6. The yardstick: purpose-built mmWave radar (TI, Infineon)

To calibrate how far below a real radar the Wi-Fi approach sits, put three things side by side. The
purpose-built parts are **not** repurposed Wi-Fi — they are here as the measuring stick, and because
they are the correct tool if you actually need range-Doppler-angle imaging.

| Device | Waveform | Bandwidth | Antennas | Raw access | Ladder analogue |
|---|---|---|---|---|---|
| **Talon AD7200 / X10** (802.11ad) | comms packets (SSW) | 2.16 GHz PHY, but only beam-SNR exported | 32-elem array | per-sector SNR only | **tier 2** |
| **TI IWR6843 / AWR1642** | **FMCW chirp** | up to ~4 GHz (60–64 GHz) / (76–81 GHz) | 3Tx×4Rx MIMO | **raw ADC IQ** via DCA1000 | **tier 4** |
| **Infineon BGT60TR13C** (Soli) | **FMCW chirp** | >5 GHz (57–64 GHz) | 1Tx×3Rx AiP | **raw IQ** via Radar SDK | **tier 4** |

### TI IWR/AWR (mmWave SDK + DCA1000)

TI's single-chip radars (IWR6843 at 60–64 GHz for industrial/IoT, AWR1642/AWR6843 at 76–81 GHz for
automotive) integrate an FMCW synthesizer, MIMO TX/RX, ADCs, and a Cortex-R4F/DSP running the
documented **mmWave SDK**. You fully control the **chirp waveform** (start freq, slope, ramp time)
and can stream **raw ADC samples** off-chip with the **DCA1000EVM** capture card into **mmWave
Studio**, then do range-FFT → Doppler-FFT → angle-FFT yourself. That is genuine range-Doppler-angle
imaging with ~cm range bins — the thing beam-SNR only gestures at. Because the PHY and chirp are
documented and IQ is exposed, this is a **tier-4** device natively (arbitrary FMCW waveform + raw IQ),
approaching tier 5 on openness.

### Infineon BGT60TR13C (Google Soli)

The BGT60TR13C is the **60 GHz FMCW radar behind Google Soli** — shipped in the **Pixel 4** for
gesture control and in Nest devices for presence/sleep sensing. 57–64 GHz, >5 GHz sweep bandwidth,
**1 Tx / 3 Rx antenna-in-package** (L-shaped, for azimuth+elevation), configured through Infineon's
documented **Radar SDK / Avian driver** and Fusion GUI, which expose **raw IQ frames**. Like the TI
part it is a purpose-built **tier-4** radar and the canonical reference for "what a real 60 GHz
gesture/vital-sign radar looks like" when you benchmark a Wi-Fi-based imitation.

---

## 7. Reproduce it: minimal 60 GHz Wi-Fi radar pipeline

End-to-end, the cheapest reproducible "Wi-Fi radar" using COTS gear:

1. **Hardware.** Two TP-Link Talon AD7200 (one TX beacon/sweeper, one RX sensor). Buy used.
2. **Root + firmware.** Flash both with `lede-ad7200`; build a `sweep_dump`-enabled patch with
   `nexmon-arc` (fw `4.1.0.55`) and load it. Verify `console_dump_uc` prints and `sweep_dump` exists.
3. **Geometry.** Fix TX and RX; place the target (person/object) in the beam field of view. For an
   imaging/SAR variant, translate the array along a rail to synthesize an aperture (this is where the
   SAR papers get cross-range resolution — see the 60 GHz SAR references).
4. **Capture.** Drive the TX through its sector codebook; log `sweep_dump` on the RX at your frame
   rate. Each frame = a per-sector SNR vector.
5. **Map beams → angles.** Join sector IDs to directions via `talon-sector-patterns`.
6. **Process.** Background-subtract a static scene; the residual per-sector power over time is your
   motion/reflectivity signal. Threshold/argmax for angle; stack frames for a Doppler-power
   spectrogram; back-project along the aperture for a SAR image.
7. **Verify.** Cross-check against ground truth (tape-measured angle, a metal corner reflector at a
   known bearing). Sanity-check that occluding the line of sight collapses the expected sectors.

**Expected output:** a time series of length-N SNR vectors that visibly track a moving target's
bearing, and (with aperture motion) a low-resolution angle-range reflectivity image. **Do not
expect** clean Doppler velocity or absolute range without an FPGA/TI radar — see the ledger in §4.

> **TX safety/regulatory.** You are transmitting inside a normal 802.11ad association at stock RF
> levels, which is the low-risk regime. Do not modify PA gain or emit outside an associated link.
> Sensing people raises privacy/consent obligations — run against yourself or consenting subjects.
> See [../docs/techniques.md](../docs/techniques.md) and
> [../docs/verification-tier4.md](../docs/verification-tier4.md).

---

## 8. See also

- [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) — the existing `qualcomm-qca9500`
  record and the ath9k CSI/spectral lineage.
- [../projects/nexmon.md](../projects/nexmon.md) — the C firmware-patching methodology `nexmon-arc`
  descends from.
- [../docs/walkthroughs/ghidra-setup-wifi-firmware.md](../docs/walkthroughs/ghidra-setup-wifi-firmware.md)
  — Ghidra setup; select the ARC (ARCompact) processor for wil6210 firmware.
- [../docs/techniques.md](../docs/techniques.md) — the sensing "verbs" (passive radar, FMCW ranging,
  imaging) this file supplies the 60 GHz silicon for.
- [../docs/taxonomy.md](../docs/taxonomy.md) — the SDR ladder and capability-flag definitions used
  for the tier scores above.

---

## References

**Tooling / firmware (primary):**

- Talon Tools (SEEMOO): <https://seemoo-lab.github.io/talon-tools/> and
  <https://github.com/seemoo-lab/talon-tools>
- nexmon-arc (ARC firmware patching): <https://github.com/seemoo-lab/nexmon-arc>
- lede-ad7200 (Talon OpenWrt/LEDE port): <https://github.com/seemoo-lab/lede-ad7200>
- talon-sector-patterns (measured antenna patterns): <https://github.com/seemoo-lab/talon-sector-patterns>
- wil6210 experimentation fork: <https://github.com/swetanksaha/wil6210>
- Mainline `wil6210` driver: <https://wireless.wiki.kernel.org/en/users/drivers/wil6210>

**60 GHz Wi-Fi sensing / beamforming (papers):**

- S. Sur, V. Venkateswaran, X. Zhang, P. Ramanathan, *"60 GHz Indoor Networking through Flexible
  Beams: A Link-Level Profiling"* (WiMi), SIGMETRICS 2015:
  <https://xyzhang.ucsd.edu/papers/SSur_SIGMETRICS_60GHzLink.pdf>
- D. Steinmetzer et al., *"Compressive Millimeter-Wave Sector Selection in Off-the-Shelf IEEE
  802.11ad Devices"*, CoNEXT 2017:
  <https://dspace.networks.imdea.org/bitstream/handle/20.500.12761/475/Compressive%20Millimeter-Wave_%20conext17-.pdf?sequence=1&isAllowed=y>
- *"LEAP: Location Estimation and Predictive Handover with Consumer-Grade mmWave Devices"*,
  INFOCOM 2019 (IMDEA):
  <https://dspace.networks.imdea.org/bitstream/handle/20.500.12761/652/LEAP_Location_Estimation_Predictive_Handover_Consumer-Grade_mmWave_Devices_2019_EN.pdf?sequence=1&isAllowed=y>
- MERL, *"Fingerprinting-Based Indoor Localization with Commercial mmWave Wi-Fi"*, TR2020-054:
  <https://www.merl.com/publications/docs/TR2020-054.pdf>
- *"Gesture Recognition with mmWave Wi-Fi Access Points: Lessons Learned"*, arXiv 2306.17062:
  <https://arxiv.org/pdf/2306.17062>
- *"Going beyond RF: How AI-enabled multimodal beamforming will change the 6G world"* (X10-based),
  Computer Networks 228 (2023): <https://genesys-lab.org/papers/Going_beyond_RF.pdf>
- B. Mamandipoor et al., *"60 GHz Synthetic Aperture Radar for Short-Range Imaging: Theory and
  Experiments"*, Asilomar 2014:
  <https://wcsl.ece.ucsb.edu/sites/default/files/publications/babak_asilomar_2014.pdf>
- *"MMWiLoc: A Multi-Sensor Dataset and Robust Device-Free Localization"*, arXiv 2506.11540:
  <https://arxiv.org/pdf/2506.11540>

**FPGA testbeds:**

- J. O. Lacruz, J. Widmer et al., *"mm-FLEX: An Open Platform for Millimeter-Wave Mobile
  Full-Bandwidth Experimentation"*, MobiSys 2020:
  <https://dspace.networks.imdea.org/bitstream/handle/20.500.12761/808/MOBISYS_2020_FINAL.pdf?sequence=1&isAllowed=y>
  (ACM: <https://dl.acm.org/doi/10.1145/3386901.3389034>)

**Silicon / products:**

- Qualcomm QCA6335 (Sparrow 802.11ad MAC/BB): <https://www.qualcomm.com/products/technology/wi-fi/qca6335>
- Wilocity 60 GHz WiGig chipset (history): <https://www.anandtech.com/show/5456/wilocity-demonstrates-60-ghz-wigig-draft-80211ad-chipset-at-ces>
- WikiDevi — Wilocity / QCA 802.11ad hardware: <https://wikidevi.wi-cat.ru/Wilocity>

**Purpose-built radar (yardstick):**

- TI IWR6843 (60–64 GHz FMCW): <https://www.ti.com/product/IWR6843>
- TI AWR1642 (76–81 GHz FMCW): <https://www.ti.com/product/AWR1642>
- TI DCA1000EVM (raw-ADC capture): <https://www.ti.com/tool/DCA1000EVM>
- Infineon BGT60TR13C (60 GHz FMCW, Google Soli): <https://www.infineon.com/part/BGT60TR13C>
- Soli in Google Pixel 4: <https://www.everythingrf.com/news/details/9085-Infineon-s-60-GHz-Radar-Chip-Brings-Motion-Detection-to-Google-Pixel-4>
