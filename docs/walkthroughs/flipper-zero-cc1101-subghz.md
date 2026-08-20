# Flipper Zero / CC1101: Sub-GHz Capture & Replay

> **The most accessible sub-GHz repurposing tool on the planet.** A Flipper Zero puts a
> Texas Instruments CC1101 sub-1 GHz transceiver, an antenna, a screen, and a scriptable
> firmware in your pocket for the price of a mid-range keyboard. This walkthrough covers what
> the CC1101 actually is, the built-in **Sub-GHz** app (Read / Read RAW / Frequency Analyzer),
> the `.sub` file format, capturing and replaying **OOK/ASK** and **2-FSK** signals, extending
> reach with an **external CC1101 module**, and — most importantly — the honest technical and
> **legal** limits.

> ⚠️ **READ THIS FIRST.** Transmitting sub-GHz signals is regulated everywhere. Capturing and
> replaying **your own** garage door, gate, or key-fob for learning is fine in most
> jurisdictions; replaying **someone else's** remote, defeating **rolling-code** security, or
> jamming is a crime in most of the world (US: FCC Part 15 + Computer Fraud/wiretap statutes;
> EU: RED 2014/53/EU + national law; UK: Wireless Telegraphy Act 2006). See
> [../../docs/rf-safety-and-legal.md](../../docs/rf-safety-and-legal.md) before you press TX.

---

## 1. Where this sits on the SDR ladder

The CC1101 is **not** a software-defined radio in the [true-SDR](../../docs/true-sdr-comparison.md)
sense. It is a **narrowband, register-configured OOK/FSK transceiver** with a fixed analog
front-end. You do **not** get raw IQ. What you get is:

- **Demodulated bits** for known protocols (decoded on the Flipper), or
- **Raw baseband envelope timings** (`Read RAW`) via the CC1101's **asynchronous serial mode** —
  the radio's data pin carries the OOK on/off envelope (or FSK slicer output) directly, which
  the firmware timestamps in microseconds.

That async mode is genuinely powerful for **capture and replay** — you can record an arbitrary
OOK edge sequence and play it back verbatim — but it is envelope-level, not I/Q-level. On this
catalog's ladder that lands the CC1101 at **Tier 1** (packet / register-level control) with a
legitimate **arbitrary-waveform** flag for async OOK/FSK replay. It cannot do CSI, spectral
scan (beyond a coarse RSSI-per-frequency sweep), or true wideband capture.

If you want a device that gives you real IQ across these bands, that is an
[RTL-SDR / HackRF-class](../../docs/true-sdr-comparison.md) job, not a CC1101 job. For the
LoRa and other sub-GHz **chips** this catalog tracks, see
[../../chips/lora-subghz.md](../../chips/lora-subghz.md) — the CC1101 is the OOK/FSK workhorse
of that family, distinct from the Semtech LoRa parts described there.

---

## 2. The CC1101 inside the Flipper

The Flipper Zero's sub-GHz radio is a **Texas Instruments CC1101** connected to the main MCU
(STM32WB55) over SPI, driving a fixed helical PCB antenna. Per the
[CC1101 datasheet (TI SWRS061)](https://www.ti.com/lit/ds/symlink/cc1101.pdf) the chip is a
sub-1 GHz ISM/SRD transceiver with:

| Parameter | CC1101 capability | What the Flipper exposes |
|---|---|---|
| **Frequency bands** | 300–348 MHz, 387–464 MHz, 779–928 MHz | Same three ranges (front-end/antenna tuned to these) |
| **Modulation** | 2-FSK, 4-FSK, GFSK, MSK, **OOK/ASK** | OOK (AM) + 2-FSK (FM) presets exposed in UI |
| **Data rate** | ~0.6 to 600 kBaud (register-set) | Set by preset / custom register block |
| **Output power** | up to ~+10/+12 dBm (band-dependent, PATABLE) | Firmware limits TX to region-legal levels |
| **Channel BW (RX)** | ~58–812 kHz (register-set) | Encoded in the modulation preset |
| **Control** | SPI registers + async/sync serial data modes | Full register access from firmware |

The important consequence: the **front-end is fixed**. You are limited to those three bands and
to what the CC1101's PLL/filters can be programmed to. There is no path to 2.4 GHz Wi-Fi/BLE,
no cellular, no aviation/marine, no arbitrary tuning outside the ISM/SRD windows the antenna
and matching network were built for.

---

## 3. The Sub-GHz app

Open **Menu → Sub-GHz**. The core functions (per the
[official Flipper docs](https://docs.flipper.net/)) are:

- **Read** — listens on a chosen frequency + preset and **decodes known protocols**
  (Princeton, KeeLoq, Nice FLO, CAME, Hormann, Holtek, etc.). Static-code protocols are
  saved as decoded keys; the screen shows protocol, key, bit length.
- **Read RAW** — records the **raw envelope timings** on a frequency + preset, for remotes
  whose protocol is unknown or unsupported. This is the general capture/replay primitive.
- **Frequency Analyzer** — hold a remote near the Flipper and it sweeps and reports the
  **strongest frequency** (RSSI peak), so you know where to point Read/Read RAW.
- **Read (Saved)** / **Saved** — manage, transmit, rename, delete captured signals.
- **Add Manually** — build a signal from a known protocol + key without capturing.
- **Region info** — the firmware carries a region/frequency allow-list.

### 3.1 Frequency and modulation selection

Every Read/Read RAW session needs a **frequency** and a **modulation preset**. The Flipper's
default is **433.92 MHz** with an **AM650** preset — the single most common EU/US SRD remote
setting. Built-in presets map to CC1101 register blocks:

| UI preset | Meaning | Typical use |
|---|---|---|
| **AM270** | OOK, ~270 kHz RX bandwidth | Narrow OOK remotes |
| **AM650** | OOK, ~650 kHz RX bandwidth (`FuriHalSubGhzPresetOok650Async`) | Most OOK garage/gate remotes (default) |
| **FM238** | 2-FSK, ~2.38 kHz deviation (`FuriHalSubGhzPreset2FSKDev238Async`) | Narrow FSK remotes/sensors |
| **FM476** | 2-FSK, ~47.6 kHz deviation | Wider FSK |
| **Custom** | `FuriHalSubGhzPresetCustom` + raw CC1101 register dump | Anything the datasheet supports |

Common frequencies to try: **433.92 MHz** (EU/global SRD), **315 MHz** (US/JP remotes),
**868.35 MHz** (EU), **915 MHz** (US ISM), **390/310 MHz** (US gate openers). The frequency
you pick **must be in one of the CC1101's three bands** or the app refuses it.

---

## 4. The `.sub` file format

Captured signals are stored as human-readable **`.sub`** text files on the SD card under
`/ext/subghz/`. Two flavors exist — decoded **key** files and **RAW** files. Fields
(per the [Flipper developer docs](https://developer.flipper.net/)):

**Common header**

```
Filetype: Flipper SubGhz Key File      # or: Flipper SubGhz RAW File
Version: 1
Frequency: 433920000                    # Hz
Preset: FuriHalSubGhzPresetOok650Async  # or ...2FSKDev238Async / ...Custom
```

**Decoded key file** (static protocol)

```
Protocol: Princeton
Bit: 24
Key: 00 00 00 00 00 A9 EC E0
TE: 400                                 # quantization interval, microseconds
```

**RAW capture file**

```
Protocol: RAW
RAW_Data: 289 -160 148 -457 442 -160 148 ...   # signed durations in µs,
                                                # + = carrier on, - = carrier off
```

- `RAW_Data` is a list of **signed microsecond durations**: positive = transmitter keyed on,
  negative = off. It is exactly the OOK envelope, so replay is edge-for-edge faithful.
- **Custom preset** files add `Custom_preset_module: CC1101` plus
  `Custom_preset_data:` — a hex blob of CC1101 register address/value pairs and the PATABLE
  (power-amp table). This is how the community ports exotic modulations: dump the datasheet's
  register recipe into the file.

Because `.sub` is plain text, you can diff two captures, hand-edit timings, or generate one
programmatically. This is the "reverse-engineering" surface: study `RAW_Data`, recover the
symbol timing (`TE`), identify the encoding, and promote a RAW capture into a decoded protocol.

---

## 5. Walkthrough: capture and replay your own OOK remote

> Use a remote **you own** — a spare garage/gate fob, a cheap 433 MHz relay kit, or an
> RF-controlled socket you bought for testing. Nothing borrowed, nothing shared.

**A. Find the frequency**

1. `Sub-GHz → Frequency Analyzer`.
2. Hold your remote ~2–10 cm from the top-left of the Flipper and press its button.
3. Note the reported frequency (e.g. `433.92`). If it jumps around, average a few presses.

**B. Read (try decoded first)**

1. `Sub-GHz → Read`.
2. Set the frequency (long-press / config) to the analyzer's result; leave preset at **AM650**.
3. Press the remote button. If the protocol is known and **static**, you'll see
   `Princeton / 24 bit / Key ...`. Save it (name it, e.g. `my_gate`).

**C. Read RAW (fallback for unknown protocols)**

1. `Sub-GHz → Read RAW`, set frequency + preset (AM650 for OOK, try AM270 if noisy).
2. Press **record**, then press your remote button 2–3 times, then stop.
3. Save. The `.sub` will be `Protocol: RAW` with a long `RAW_Data` list.

**D. Replay**

1. `Sub-GHz → Saved → my_gate → Send`.
2. The Flipper retransmits on the stored frequency/preset. Your **own** device should respond.

**E. Inspect the file (optional, on a computer)**

Mount the SD card or use `qFlipper`, open `/ext/subghz/my_gate.sub`, and read the fields
above. Editing `RAW_Data` and re-sending is the entry point to real protocol RE.

### Why this fails on modern remotes (and should)

If replay does **nothing**, the remote almost certainly uses a **rolling code** (KeeLoq,
Nice Smilo, Somfy Keeloq, HCS301, etc.): every press emits a different, cryptographically
sequenced code, so a captured code is stale on the next press. **This is the security
working as designed.** Flipper firmware deliberately will not run rolling-code *attacks*, and
attempting to bypass a security system you don't own is illegal. Treat a failed replay as
confirmation that the target is protected, not as a problem to solve.

---

## 6. External CC1101 module (extended range / bands)

The Flipper exposes SPI + GPIO on its header, and the community supports **external CC1101
modules** (e.g. the common "CC1101 SubGHz" add-on boards) for:

- A **larger / tuned antenna** (SMA connector) → meaningfully better range and sensitivity.
- A module tuned for a **different band segment** (e.g. an 868/915 MHz-optimized matching
  network vs. the internal 433-centric one).
- A **low-noise-amplifier** variant on some boards.

Wiring is the standard CC1101 SPI set to the Flipper GPIO (`CS/CSN`, `SCK`, `MOSI`, `MISO`,
`GDO0`, plus `3V3`/`GND`); firmware/apps let you select the external radio. **Important
honesty:** an external module is still a **CC1101**. It does **not** unlock new modulations,
new bands beyond 300–928 MHz, or IQ. It improves the RF path (antenna/gain), not the
fundamental capability class. You are still Tier 1.

---

## 7. Honest limits

- **Fixed front-end, ISM/SRD only.** Three bands (300–348 / 387–464 / 779–928 MHz). No 2.4 GHz,
  no cellular, no arbitrary tuning. External modules don't change this.
- **No raw IQ.** You get OOK envelope / FSK slicer output, not complex samples. No spectral
  display beyond a coarse RSSI sweep, no CSI, no wideband capture.
- **Narrowband.** One channel at a time, ~hundreds of kHz wide. It cannot survey a band the way
  an [RTL-SDR](../../projects/rtl-sdr-lineage.md)-class receiver can.
- **Rolling codes defeat replay by design** — and the firmware won't (and you shouldn't) attack
  them.
- **Legal, not just polite:** unauthorized TX, interception of others' signals, and
  jamming are offenses in essentially every jurisdiction.

For what a real SDR adds over the CC1101 across these same frequencies, compare
[../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md). For the broader
sub-GHz chip landscape (LoRa, Si4x6x, TI CCxxxx family), see
[../../chips/lora-subghz.md](../../chips/lora-subghz.md).

---

## 8. Legal & safety summary

- ✅ Capture/replay **your own** remotes, on **your own** devices, for learning.
- ✅ Bench-testing kit you bought (relays, sockets) at legal power on ISM frequencies.
- ❌ Capturing or replaying **anyone else's** remote, fob, gate, car, or alarm.
- ❌ Attacking rolling-code or any security you don't own — a crime even if technically trivial.
- ❌ Jamming, continuous TX, or transmitting outside region-legal frequency/power/duty-cycle.
- ⚠️ Keep TX brief, on legal ISM frequencies, at legal power. When in doubt, **receive only**.

Full regulatory breakdown: [../../docs/rf-safety-and-legal.md](../../docs/rf-safety-and-legal.md).

---

## References

- Texas Instruments, *CC1101 Low-Power Sub-1 GHz RF Transceiver* datasheet (SWRS061) — https://www.ti.com/lit/ds/symlink/cc1101.pdf
- Flipper Zero official documentation (Sub-GHz app: Read, Read RAW, Frequency Analyzer) — https://docs.flipper.net/
- Flipper developer documentation (`.sub` file format, presets, register blocks) — https://developer.flipper.net/
- Flipper Zero firmware (open source, Sub-GHz subsystem) — https://github.com/flipperdevices/flipperzero-firmware
