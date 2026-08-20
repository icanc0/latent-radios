# Taxonomy: how "SDR" is a Wi‑Fi chip, exactly?

A software‑defined radio, in the purest sense, hands software the raw stream of baseband IQ samples on receive and lets software author the raw IQ on transmit; everything above the ADC/DAC is code. No consumer Wi‑Fi chip does this out of the box. But "SDR‑ness" is not binary — it is a **ladder**, and Wi‑Fi silicon can be pushed up it, rung by rung, mostly by reverse‑engineering firmware. This document defines the ladder every entry in this catalog is scored against.

## The ladder

### Tier 0 — Black box
Stock firmware, stock driver. The chip associates to an AP and moves IP packets. The radio, the PHY, the per‑frame metadata: all hidden. This is where every chip starts and where the vendor wants it to stay. Not cataloged on its own — it's the baseline every higher tier is measured from.

### Tier 1 — Monitor + Injection (packet‑level control)
The chip will hand you **every** 802.11 frame it hears (monitor mode / RFMON), on a channel you choose, with radiotap metadata (RSSI, rate, channel), and it will **transmit frames you craft byte‑for‑byte** (injection), including malformed or non‑standard ones. You control the radio at the *frame* granularity: timing, channel hopping, headers, payloads.

Why it's SDR‑ish: you're no longer limited to "be a normal station." You can build any 802.11‑framed waveform, sweep channels, do time‑of‑flight tricks, run protocols the vendor never shipped. It is the floor for inclusion in this atlas.

Canonical: Atheros `ath9k`, many Realtek (`RTL8812AU`), most `mt76` MediaTek parts, ESP32 raw TX.

### Tier 2 — PHY telemetry / Channel State Information (CSI)
The chip reports, per received frame, the **complex channel estimate for each OFDM subcarrier** — amplitude *and phase* — as measured off the training fields. For a 20 MHz 802.11n link that's ~56 subcarriers × (antennas)² of complex numbers, several hundred times a second.

Why it matters: CSI is *quasi‑IQ, sampled in the frequency domain at subcarrier granularity*. It's enough to do radar‑like sensing — presence detection, breathing/heart‑rate, gesture and activity recognition, indoor localization, material sensing — the entire "Wi‑Fi sensing" field runs on it. You don't get arbitrary time‑domain IQ, but you get a genuine, calibrated look at the propagation channel.

Canonical: Intel 5300 (the original *Linux 802.11n CSI Tool*), Atheros (*Atheros CSI Tool*), Broadcom via *Nexmon CSI*, ESP32's built‑in CSI API, Intel AX200/AX210 via *AX‑CSI*/*PicoScenes*.

### Tier 3 — Spectral / raw‑PHY scan
The chip's PHY runs an FFT over the channel and hands software the **raw spectral bins** (magnitude, sometimes with phase) whether or not a valid frame is present. Effectively a narrowband spectrum analyzer bolted to the Wi‑Fi front‑end: you see interference, radar, non‑Wi‑Fi emitters, occupancy — the RF energy itself, not just decoded frames.

Why it matters: this is the first rung where you're looking at *the spectrum* rather than *packets*. It underpins channel‑selection algorithms, DFS radar detection, interference hunting, and a lot of RF forensics.

Canonical: Atheros **spectral scan** (`ath9k` debugfs `spectral_scan`), Broadcom via Nexmon, some Intel.

### Tier 4 — Arbitrary waveform transmit (the hard rung)
Software authors a **baseband IQ buffer** and the chip transmits it through the Wi‑Fi RF front‑end — not an 802.11 frame, an arbitrary signal. This is where a Wi‑Fi chip briefly becomes a real (band‑limited, low‑dynamic‑range) transmitting SDR: cross‑technology emulation (speak ZigBee/Bluetooth/LoRa‑ish out of a Wi‑Fi radio), covert channels, custom modulation, jamming research, ranging waveforms.

Why it's rare: the transmit DSP is the most locked‑down part of the chip. Reaching this rung essentially always requires deep firmware reverse‑engineering — finding the DAC feed / TX vector path in the MAC‑PHY processor and patching in a raw‑sample injector. It has been demonstrated on Broadcom D11 cores via **Nexmon**, and in various academic "cross‑technology communication" papers.

### Tier 5 — Open PHY / soft‑radio
The firmware is **documented or open**, so the PHY/MAC is genuinely yours to reprogram — no reversing required because someone already did it, or the vendor published it. Vanishingly rare for Wi‑Fi. The historical example is **OpenFWWF** (open firmware for Broadcom `b43` chips) and the `b43`/`b43-tools` D11 assembler. Genuine SDR platforms (USRP, LimeSDR, bladeRF, HackRF, PlutoSDR) live conceptually at this tier and are cataloged in [true-sdr-comparison.md](true-sdr-comparison.md) as the yardstick.

## Capability flags (orthogonal to tier)

Tier captures "how far up the ladder," but real chips expose *specific* capabilities. The database uses these flags:

| Flag | Meaning |
|------|---------|
| `monitor` | RFMON capture of all frames |
| `injection` | Byte‑exact frame transmit |
| `csi` | Per‑subcarrier complex channel state |
| `spectral-scan` | Raw PHY FFT bins |
| `raw-iq` | Time‑domain IQ **receive** |
| `arbitrary-waveform` | Author‑and‑transmit baseband IQ |
| `radar` / `fmcw` / `passive-radar` | Sensing modes built on the above |
| `covert-channel` | Emitting non‑native signals for cross‑tech comms |
| `open-firmware` | Documented/open firmware exists |

## Why the firmware‑reversing thread runs through everything

Notice the pattern: **each rung up the ladder is a rung deeper into the firmware.** Monitor/inject is often a driver‑level flag. CSI usually needs a firmware patch to *export* the channel estimates the PHY already computes. Spectral scan needs the PHY's FFT tap turned on and streamed out. Arbitrary TX needs the transmit datapath rewritten. That is the through‑line of this catalog and the subject of [firmware-reversing.md](firmware-reversing.md): *the radio is already general‑purpose; "SDR to some extent" is a measure of how much of its firmware you've managed to reverse and repurpose.*

## How entries are scored

Each database record gets:
- a single **`sdr_tier`** (0–5) = the highest rung it can currently reach with public tooling, and
- a set of **`sdr_capabilities`** flags = the specific things it can do.

A chip that can do monitor + injection + CSI but not spectral or TX is **Tier 2**, flags `[monitor, injection, csi]`. A chip with demonstrated arbitrary‑TX is **Tier 4** even if only via a fragile research patch (the record's `status` then notes `reported`/`theoretical` vs `verified`).
