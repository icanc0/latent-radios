# GNSS Receivers as SDRs, and SDRs as GNSS Receivers

*Latent Radios — Cycle 6. Two directions of the same coin: a general-purpose SDR can be turned into a GPS receiver in software, and a purpose-built GNSS chip is a narrowband RX-only correlator whose RF front-end and raw observables make it **SDR-adjacent** — never a general SDR.*

The honest thesis up front: **consumer GNSS chips are receive-only spread-spectrum correlators, not arbitrary-waveform radios.** You cannot make a u-blox module transmit an IQ waveform, and you cannot make it look at Wi-Fi. What you *can* extract — raw pseudorange, carrier phase, and Doppler observables (u-blox `RXM-RAWX`), or the raw 1–2-bit IF sample stream out of a bare GNSS front-end (MAX2769, SiGe SE4110) — is genuinely useful measurement data that sits *below* the decoded-position layer. That earns Tier 1–3, never Tier 4/5. The interesting SDR is the *general* SDR (RTL-SDR, HackRF, USRP) pointed at 1575.42 MHz.

---

## 1. The L1 story: why 1575.42 MHz is hard and easy at once

| Signal | Center freq | Chipping rate / code | Data rate | Notes |
|---|---|---|---|---|
| GPS L1 C/A | **1575.42 MHz** | 1.023 Mcps, 1023-chip Gold code | 50 bps | Open Service, CDMA, the classic SDR target |
| GPS L2C | 1227.60 MHz | 1.023 Mcps (CM/CL) | 25 bps | Dual-freq / ionosphere correction |
| GPS L5 | 1176.45 MHz | 10.23 Mcps | 50/100 sps | Wider, needs ≥10–20 Msps SDR |
| Galileo E1 | 1575.42 MHz | 1.023 Mcps BOC(1,1) | 125 sps | Shares L1 band |
| Galileo E5a/b | 1176.45 / 1207.14 MHz | 10.23 Mcps AltBOC | — | Wideband |
| GLONASS L1 | ~1598–1606 MHz | 0.511 Mcps | 50 bps | **FDMA** (per-satellite frequency) |
| BeiDou B1I | 1561.098 MHz | 2.046 Mcps | 50 bps | — |

Two facts define the whole problem:

1. **The signal is below the noise floor.** GPS L1 C/A arrives at roughly **−128 to −130 dBm**, ~20 dB *under* the thermal noise floor in the receiver bandwidth. You never "see" it on a spectrum display; you recover it only by correlating against the known Gold code (despreading gives ~43 dB of processing gain). This is why a bare SDR needs an **active antenna + LNA + a clean front-end**, and why acquisition is compute-heavy (a 2-D search over code phase × Doppler).

2. **Timing is everything.** A position fix is really a *timing* measurement (pseudoranges = code phase × c). Frequency stability of the SDR's reference clock directly limits sensitivity and time-to-first-fix — which is why the humble RTL-SDR needs help (below).

---

## 2. SDR → GNSS receiver: the RTL-SDR / HackRF / USRP path

### GNSS-SDR (CTTC) — the reference open receiver

**[GNSS-SDR](https://gnss-sdr.org/)** is the canonical open-source software-defined GNSS receiver, written in C++ on GNU Radio building blocks, developed at **CTTC** (Centre Tecnològic de Telecomunicacions de Catalunya) with Carles Fernández-Prades as lead. License **GPLv3**. It takes raw IQ — live from an SDR or from a file — and runs the full chain: acquisition → tracking → telemetry decode → PVT (position/velocity/time), emitting standard **RINEX** observation/navigation files, RTCM, and NMEA.

Supported front-ends and signals (verified from the project docs):

- **Front-ends:** USRP family via **UHD** (B200/B210, X300/X310, USRP1/2); **gr-osmosdr** devices — **RTL-SDR dongles, HackRF, bladeRF, LimeSDR**; **ADALM-PLUTO**; and arbitrary **raw sample files** (the most reproducible path for research).
- **Signals:** GPS **L1 C/A, L2C, L5**; Galileo **E1, E5a, E5b, E6**; GLONASS **L1/L2**; BeiDou **B1I/B3I**; QZSS L1/L5.

The `gr-osmosdr` layer ([Osmocom](https://osmocom.org/projects/gr-osmosdr/wiki), [source](https://github.com/osmocom/gr-osmosdr)) is what lets one config file target an RTL dongle, a HackRF, or a bladeRF interchangeably — the same abstraction the wider SDR ecosystem leans on (see [`../projects/rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md)).

### Making an RTL-SDR actually work at L1

The [RTL-SDR](../projects/rtl-sdr-lineage.md) is the cheapest entry point but has two catches for GNSS:

- **Frequency stability.** A stock RTL2832U + R820T dongle drifts with temperature (tens of ppm); at 1575 MHz even 1 ppm ≈ 1.5 kHz, which smears the Doppler search and hurts sensitivity. **Use an RTL-SDR "v3"-class dongle with a 0.5–1 ppm TCXO**, or discipline it. GNSS-SDR can estimate and correct residual clock offset, but a good reference makes acquisition far more reliable.
- **Powering the active antenna.** GPS patch antennas are active (built-in LNA needing 3–5 V). Use a dongle with a **software-switchable bias-tee** (RTL-SDR v3 has one) or an external bias-tee/LNA.

A typical live-L1 configuration: tune **1575.42 MHz**, sample **~2.0–2.6 Msps** (enough for the 2.046 MHz-wide C/A main lobe), `gr-osmosdr` source, GPS L1 C/A acquisition + tracking blocks. HackRF, bladeRF, and USRP work the same way with more bandwidth headroom (useful for L5/E5 wideband or multi-band). This is a **real, verified capability** — GNSS-SDR obtains genuine position fixes from an RTL dongle and a patch antenna.

> Note: RTL-SDR's *direct-sampling* mode (the HF trick) is irrelevant here — 1575 MHz is well within the R820T tuner's normal range; you use the ordinary quadrature-tuned path.

---

## 3. SDR → GNSS *simulator*: gps-sdr-sim (and the hard legal line)

**[gps-sdr-sim](https://github.com/osqzss/gps-sdr-sim)** (osqzss / Takuji Ebinuma) does the inverse: it *generates* a GPS L1 C/A baseband IQ stream from a broadcast ephemeris (a RINEX/`brdc` navigation file) and a chosen static location or a dynamic trajectory (NMEA / user-motion file). The IQ file is then replayed through a transmit-capable SDR — **HackRF, bladeRF, ADALM-Pluto, USRP** — up-converted to **1575.42 MHz**. Output formats are 1-bit, 8-bit (`int8`), or 16-bit I/Q at a default ~2.6 MHz sample rate.

This is the standard way to **test** a GNSS receiver's cold-start, leap-second handling, position/time response, or a project's spoof-resistance — on the bench, deterministically.

> ### ⚠️ Legal — read before you generate a single sample
>
> **Transmitting a GPS-like signal over the air is illegal in virtually every jurisdiction and is genuinely dangerous.** 1575.42 MHz is protected Aeronautical Radionavigation / RNSS spectrum. A benign-looking replay can capture nearby phones, car navigation, aircraft, cell-tower timing references, and financial-timing receivers — this is **spoofing**, and real incidents have disrupted airports and vehicles.
>
> **The only acceptable path** for gps-sdr-sim output is a **conducted, contained** one: SDR TX port → coax → attenuator → the receiver under test, or inside a **shielded/Faraday enclosure or anechoic chamber**. **Never connect an antenna.** Use the minimum power. This is a hard rule, not a caution. See [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md) for the regulatory framing (FCC Part 15 / equivalent, and the specific protection of GNSS bands). The upstream README ships without a disclaimer — treat the above as the missing one.

---

## 4. GNSS chip → SDR-adjacent: RF front-ends and raw observables

Here is where a *purpose-built* GNSS device is repurposable — with honest limits.

### 4a. Bare GNSS RF front-ends = a narrowband, RX-only SDR front-end

A GNSS **front-end IC** is, functionally, exactly what an RTL-SDR's tuner+ADC is: LNA → mixer/PLL → filter → quantizing ADC, spitting out **raw quantized IF/IQ samples**. The difference is it is *fixed to the GNSS band* and quantizes hard (1–3 bits). Feed those samples to an FPGA, microcontroller, or a PC running GNSS-SDR and you have a software receiver. This is the "GNSS front-end + FPGA" design pattern.

- **MAX2769 / MAX2769B / MAX2769C** (Maxim, now **Analog Devices**) — the textbook *universal* GNSS front-end. Single chip: dual-input LNA, mixer, image-reject, PGA, integer-N PLL/VCO, and a programmable **1-to-3-bit ADC**, covering **GPS L1 (1575.42), GLONASS, Galileo** with a configurable IF and 2.5–20+ MHz bandwidth. Register-programmable over SPI; outputs a clocked **1–2-bit sign/magnitude IF stream** straight into an FPGA or logic. It is the front-end behind countless academic and hobby software receivers. Fully **documented** register map — no firmware to reverse. ([product page](https://www.analog.com/en/products/max2769.html), [datasheet PDF](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX2769.pdf))
- **SiGe SE4110L / SE4120 "Stereo"** (SiGe Semiconductor → Skyworks/NSL) — L1 (and dual-band, in the SE4120) front-ends. The **SE4110** is the front-end inside the well-known **SparkFun GN3S Sampler v2/v3**, a USB dongle that streams raw GPS L1 IF samples to a PC for offline software correlation — one of the original "GNSS as an SDR capture device" tools.

These deliver **raw-IQ (heavily quantized) RX only, single band, no TX**. That is a real raw-PHY tap — hence **Tier 3** — but do not confuse a narrowband 1-bit GNSS front-end with a HackRF. It is a superb, cheap dedicated GNSS capture front-end and nothing more.

### 4b. u-blox raw measurements: `RXM-RAWX` — the pragmatic win

Most people don't want raw IF; they want **raw observables**, and modern u-blox modules hand them over. The **`UBX-RXM-RAWX`** message emits, per tracked satellite, the **pseudorange, carrier phase (in cycles), Doppler, C/N₀, and lock/validity flags** — the very quantities an RTK/PPP engine needs. Paired with **`UBX-RXM-SFRBX`** (raw navigation subframe bits), you have everything to run your own positioning engine off the shelf.

- **ZED-F9P** — dual-band (L1+L2/L5-class: GPS L1C/A+L2C, GLONASS, Galileo E1+E5b, BeiDou), full **`RXM-RAWX`** carrier-phase output, and an onboard **RTK** engine reaching **centimetre-level** accuracy (~0.01 m + 1 ppm) with corrections. This is the "$30 dream" of the scope — with an honest price note: **bare modules run ~$150–220** on breakout boards (ArduSimple, SparkFun); the *bare chip* is cheaper in volume but not a $30 retail item. What *is* remarkable is that **cm-grade RTK carrier-phase sensing** is now a commodity module, not a survey instrument. ([ZED-F9P product page](https://www.u-blox.com/en/product/zed-f9p-module))
- **NEO-M8T / LEA-M8T** (timing series) and **NEO-M8P** — single-band but **raw-capable** (`RXM-RAWX`/`RXM-SFRBX`), in the **~$40–75** range — the affordable entry to raw carrier phase.
- **[RTKLIB](https://github.com/tomojitakasu/RTKLIB)** (Tomoji Takasu, BSD-2) is the standard open toolchain that ingests u-blox `RXM-RAWX` → RTK / PPP / post-processed cm positioning. This is the real, verified workflow that turns a raw-capable u-blox into an RTK **sensor**.

The u-blox path yields **measurement/phase data, not IQ**. Carrier phase is a genuine per-satellite complex-phase observable — the GNSS analogue of Wi-Fi CSI — so raw-capable u-blox modules earn **Tier 2**. A position-only NMEA module (most phones/cars) exposes nothing below the fix and is **Tier 1** at best. Neither is programmable to arbitrary waveforms; there is no offset to patch, no open firmware.

---

## 5. Honest tiering

| Thing | What you can actually get | Tier | Why not higher |
|---|---|---|---|
| General SDR (RTL/HackRF/USRP) @ 1575 MHz + GNSS-SDR | Full software GNSS RX; **TX = simulation only, contained** | (n/a — it's a real SDR) | The SDR is the radio; GNSS is just the app |
| MAX2769 / SE4110 front-end + FPGA | Raw 1–3-bit IF/IQ, RX only, GNSS band only | **3** | No TX, single narrow band, hard-quantized |
| u-blox ZED-F9P / M8T (`RXM-RAWX`) | Pseudorange + **carrier phase** + Doppler → RTK/PPP | **2** | Correlator, not IQ; no TX; firmware closed |
| Consumer GNSS (NMEA position only) | Lat/lon/time; maybe C/N₀ | **1** | Black-box fix, nothing below it |
| "Make a GPS chip transmit / do Wi-Fi" | — | — | Physically not a general SDR; don't pretend |

**Bottom line:** the GNSS chip's value to this catalog is its *RF front-end* (a cheap dedicated L-band SDR capture head) and its *raw observables* (carrier phase = a real phase-measurement layer). Both are SDR-*adjacent*. The general-purpose SDR remains the only thing here that both transmits and receives arbitrary waveforms.

---

## References

- GNSS-SDR (CTTC) — software-defined GNSS receiver: <https://gnss-sdr.org/> · source: <https://github.com/gnss-sdr/gnss-sdr> (GPLv3)
- gps-sdr-sim (osqzss / Ebinuma) — GPS L1 baseband generator: <https://github.com/osqzss/gps-sdr-sim>
- Osmocom gr-osmosdr (RTL/HackRF/bladeRF/LimeSDR source abstraction): <https://osmocom.org/projects/gr-osmosdr/wiki> · <https://github.com/osmocom/gr-osmosdr>
- Analog Devices/Maxim MAX2769 universal GNSS front-end: <https://www.analog.com/en/products/max2769.html> · datasheet: <https://www.analog.com/media/en/technical-documentation/data-sheets/MAX2769.pdf>
- u-blox ZED-F9P high-precision RTK module (`RXM-RAWX`, RTK): <https://www.u-blox.com/en/product/zed-f9p-module>
- u-blox NEO-M8T timing / raw series: <https://www.u-blox.com/en/product/neo-m8t-series>
- RTKLIB (Takasu) — RTK/PPP toolchain consuming u-blox raw obs: <https://github.com/tomojitakasu/RTKLIB>
- Related in this catalog: [`../projects/rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md) · legal framing: [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md)
