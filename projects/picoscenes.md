# PicoScenes — the unified Wi-Fi CSI / ISAC measurement platform

**PicoScenes** is the most capable general-purpose platform for Wi-Fi channel measurement in existence: a C++ runtime plus MATLAB/Python toolboxes that drives *multiple* CSI-capable NICs **and** USRP/HackRF SDR front-ends through one command-line interface and one plugin API, and writes everything into a single self-describing `.csi` file format. Where the classic single-NIC tools ([Intel 5300](../docs/walkthroughs/intel-5300-csi.md), [Atheros ath9k](../docs/walkthroughs/atheros-ath9k-spectral-csi.md), [Nexmon CSI](nexmon.md), ESP32) each give you *one chip, one standard, one parser*, PicoScenes gives you **802.11a/g/n/ac/ax(/be) CSI, up to 160 MHz on COTS silicon and 320 MHz on SDR, from up to 27 concurrent radios, in one timestamped stream**. It is the reference platform for modern Wi-Fi Integrated Sensing and Communication (ISAC) research.

- **Authors:** Zhiping Jiang (蒋志平) and Rui Li's group at **Xidian University**, with Tom Hao Luan et al.
- **Home / docs:** <https://ps.zpj.io/> · author blog <https://zpj.io/> · code org <https://github.com/wifisensing>
- **Founding paper:** Z. Jiang, T. H. Luan, X. Ren, D. Lv, H. Hao, J. Wang, K. Zhao, W. Xi, Y. Xu, R. Li, *"Eliminating the Barriers: Demystifying Wi-Fi Baseband Design and Introducing the PicoScenes Wi-Fi Sensing Platform,"* **IEEE Internet of Things Journal**, vol. 9, no. 6, pp. 4476–4496, 2022. Preprint: <https://arxiv.org/abs/2010.10233>

> **Where it sits on the SDR ladder.** PicoScenes is not a firmware-reversing project — it is the *consumer* of firmware/driver hooks that other projects (and its own patched drivers) provide, wrapped in a serious measurement platform. On a **COTS NIC** (5300 / QCA9300 / AX200 / AX210) it reaches **Tier 2 (CSI)** — per-subcarrier complex **H** across HT/VHT/HE, plus monitor + injection (Tier 1). Driving a **USRP** through its software 802.11 PHY it reaches **Tier 4–5**: arbitrary-waveform TX, full soft-PHY RX, and — because the whole 802.11a/g/n/ac/ax/be baseband is in host code — an *openly documented* transmit/receive chain. See [../docs/taxonomy.md](../docs/taxonomy.md) and [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

---

## 1. What problem it solves

Every 802.11 OFDM receiver estimates the per-subcarrier channel **H** from the training fields (L-LTF / HT-LTF / VHT-LTF / HE-LTF) to equalize a packet, then discards it. CSI-extraction tools intercept **H** on its way to the equalizer (the general story is in [csi-toolchains.md](csi-toolchains.md)). The classic four tools each solved this for *one* chip family and stopped:

| Pain point with single-NIC tools | PicoScenes' answer |
|---|---|
| One tool = one standard (mostly 802.11n) | One platform spanning **a/g/n/ac/ax** on COTS, **+be** on SDR |
| Kernel-version-locked patched blobs, hard to reproduce | Signed `.deb` packages + `MaintainPicoScenes` updater pinned to Ubuntu LTS |
| Every tool has its own incompatible dump format & parser | One **versioned-segment `.csi`** format; one MATLAB + one Python parser |
| Can't cross-correlate two radios | **Up to 27 NICs concurrently**, common host clock |
| CSI only — no controlled TX, no ranging | **Injector / responder** modes + **EchoProbe** round-trip plugin |
| COTS bandwidth capped at what the chip does | **USRP soft-PHY** front-end: arbitrary 1–400 MHz (scalable to 1600), 4×4 |

The founding paper's technical contribution is deeper than plumbing: it reverse-engineers the **QCA9300 baseband** and shows that COTS CSI carries a previously-unmodeled hardware **CSI distortion** (residual filtering / non-idealities), then provides on-platform calibration — which is why PicoScenes CSI is treated as metrologically usable rather than just "a pile of complex numbers."

---

## 2. Architecture — three layers

The platform is deliberately stratified (paper §V; [manual/plugin.html](https://ps.zpj.io/manual/plugin.html)):

1. **PicoScenes drivers** — patched kernel modules (`picoscenes-driver-modules-*`) that unlock CSI reporting, monitor mode, injection, and manual gain on each supported NIC, plus UHD/libhackrf glue for SDR. This is the layer that is kernel-version-sensitive.
2. **PicoScenes platform (C++ runtime)** — abstracts every radio behind a uniform **NIC API** (`getNic()`, `startRxService()`, `startTxService()`, `transmitPicoScenesFrameSync()`), owns frame (de)modulation for the SDR PHY, timestamps, multi-NIC scheduling, and the `.csi` writer.
3. **Plugin subsystem** — the actual measurement logic. The runtime auto-discovers plugins at startup, parses their command-line options, and fans every received frame out to all active plugins' `rxHandle()`.

```
        ┌───────────────── plugins (measurement tasks) ─────────────────┐
        │  logger   injector   responder   EchoProbe   your-plugin ...  │
        └───────────────▲───────────────────────┬──────────────────────┘
                         │ rxHandle(RxFrame)     │ tx / nic->transmit...
        ┌────────────────┴───────────────────────▼──────────────────────┐
        │      PicoScenes C++ platform — unified NIC API + .csi writer   │
        └────────────────▲───────────────────────┬──────────────────────┘
                          │                       │
        ┌─────────────────┴──────┐   ┌────────────┴─────────────────────┐
        │ patched NIC drivers    │   │ SDR back-ends (UHD / libhackrf)  │
        │ 5300 · QCA9300 · AXxxx │   │ USRP soft-802.11 PHY · HackRF    │
        └────────────────────────┘   └──────────────────────────────────┘
```

---

## 3. Supported hardware — the capability table

Values below are from the official **[hardware manual](https://ps.zpj.io/manual/hardware.html)**. Bandwidth is channel bandwidth (CBW) in MHz; "arbitrary tunable" is a genuine PicoScenes feature on QCA9300 and SDR that stock drivers do not expose.

| Radio | Catalog entry | Standards (CSI) | CBW (MHz) | Max spatial streams | Frequency range | Gain | Injection | Notes |
|---|---|---|---|---|---|---|---|---|
| **Intel IWL5300** | [intel-iwl5300](../chips/intel.md) | a/g/n | 20 / 40 | 3 (3×3) | 2.4 / 5 GHz | auto only | a/g/n | The "legendary" original; 30 grouped subcarriers; monitor limited to special-address (`12:34:56…`) sounding frames |
| **Atheros QCA9300 (AR9300)** | [atheros-ar9300-csi](../chips/qualcomm-atheros.md) | a/g/n | **arbitrary 2.5 – 80** | 3 (3×3) | **arbitrary 2.2–2.9 & 4.4–6.1 GHz** | **manual 0–66 dB** | a/g/n | Most-controllable COTS NIC; full per-subcarrier CSI; arbitrary carrier + sample-rate tuning is its signature capability |
| **Intel AX200 (Wi-Fi 6)** | [intel-ax200-ax201](../chips/intel.md) | a/g/n/ac/**ax** | 20 / 40 / 80 / 160 | 2 (2×2) | 2.4 / 5 GHz | auto only | ≤160 MHz, all formats | First public 802.11ax CSI on COTS silicon (paired with AX210) |
| **Intel AX210 (Wi-Fi 6E)** | [intel-ax210-ax211](../chips/intel.md) | a/g/n/ac/**ax** | 20 / 40 / 80 / 160 | 2 (2×2) | 2.4 / 5 / **6 GHz** ([5955, 7115] MHz) | auto only | ≤160 MHz, all formats | **Only public platform doing CSI + injection in the 6 GHz band**; unlocks ~1.18 GHz of new spectrum |
| **USRP (all models: B2xx, N3xx, X3xx, X4xx…)** | [ettus-usrp](../chips/other-vendors.md) | a/g/n/ac/ax/**be** | **1 – 400 (→1600)** | 4 (4×4) | **1 – 7200 MHz** | auto/manual | all-format | Software 802.11 PHY in host: full soft-PHY RX + arbitrary-waveform TX, precoding/beamforming, up to 39 CSI per packet — **Tier 4/5** |
| **HackRF One** | [greatscott-hackrf-one](../chips/other-vendors.md) | a/g/n/ac/ax/be | arbitrary 1 – 20 | 1 (1×1) | 10 – 7250 MHz | none | all-format | Cheapest SDR path; RX monitor limited to 20 MHz CBW; half-duplex |

**Cross-format / MIMO limits (SDR PHY):** MCS 0–13, LDPC and BCC coding, up to 4×4. **CSI rate:** up to ~1 kHz at 20 MHz. **Injection throughput:** ~4 kHz real-time, ~40 kHz in replay mode. **Concurrency:** up to **27** radios in one process sharing the host clock.

> **Buying/flashing notes.** The QCA9300 is a mini-PCIe/M.2 AR9300-series card (the same silicon behind the [Atheros CSI Tool](../docs/walkthroughs/atheros-ath9k-spectral-csi.md)); AX200 is M.2 2230 / CNVio-free, AX210 is M.2 2230 (needs a mainboard that will POST with it). PicoScenes replaces the stock driver, so a dedicated card is strongly recommended — do not repurpose your only Wi-Fi NIC. USRP support routes through **UHD** (`uhd_find_devices` to enumerate).

---

## 4. What it captures — frames, CSI, and the `.csi` format

### The frame object

Received packets arrive as a **`ModularPicoScenesRxFrame`** (TX side: `ModularPicoScenesTxFrame`) — a container of *typed, versioned segments*. The segments you care about for sensing:

- **`RxSBasic`** — reception basics: carrier frequency, sampling rate / CBW, format, MCS, RSSI (per-chain), noise floor, antenna count.
- **`StandardHeader`** — the 802.11 MAC header (addresses, seq).
- **`CSISegment`** — the star: complex CSI as an **`N_tone × N_sts × N_rx`** array, with the raw OFDM **subcarrier indices** (they are not contiguous — DC/guard/pilot gaps matter), plus per-packet metadata (CBW, format, number of tones).
- Extra segments (`ExtraInfo`, `MVMExtra` for Intel, `PicoScenesFrameHeader`, `SignalMatrix`, etc.) carry chip-specific and payload data.

### The `.csi` file

`.csi` is a flat concatenation of these versioned segments — **self-describing and forward-compatible**: a newer parser reads old files, and an old parser skips segment versions it doesn't understand instead of choking. This is the single most practical advantage over the legacy `.dat` formats, each of which was a bespoke, undocumented byte layout. One file can hold frames from *different NICs and different standards* interleaved, which is exactly what multi-radio experiments produce.

---

## 5. Parsers — MATLAB, Python, and third-party

### PicoScenes MATLAB Toolbox (PMT) — the reference parser

Requires MATLAB R2020b+ and a C/C++ compiler (GCC 9.3+ on Linux). Install and use:

```matlab
% one-time, from the PicoScenes-MATLAB-Toolbox-Core folder
install_PicoScenes_MATLAB_Toolbox
compileRXSParser

% parse a capture (also: double-click the .csi in Current Folder, or drag into the console)
data = opencsi('my_capture.csi');
```

PMT parses in two stages — **raw** (each frame → a cell) then **bundled** (cells merged into arrays; this can refuse if frames have heterogeneous shapes, which is intentional). Per-frame fields after parsing:

| Field | Meaning |
|---|---|
| `RxSBasic` | freq, CBW, MCS, RSSI, noise floor, #antennas |
| `StandardHeader` | 802.11 MAC header |
| `CSI` | complex CSI, `N_tone × N_sts × N_rx` |
| `Mag` / `Phase` | magnitude and **unwrapped, CSD-removed** phase |
| `SubcarrierIndex` | OFDM subcarrier indices (int16) |
| `Timestamp` | µs-level PPDU start time (device clock) |
| `SystemTime` | ns-level host timestamp |

PMT does real pre-processing for you: pilot-subcarrier interpolation, phase unwrap, and **cyclic-shift-delay (CSD) removal** — the per-STS cyclic shift that 802.11 mandates for MIMO and that will otherwise wreck naïve phase analysis (see phase sanitization in [../docs/techniques.md](../docs/techniques.md)).

### PyPicoScenes — the official Python binding

Uses **cppyy** to bind the same C++ classes at runtime (no separate reimplementation), so the Python API mirrors the native one exactly. Setup on Ubuntu:

```bash
git clone https://github.com/wifisensing/PyPicoScenes
# install PicoScenes itself first, then:
conda install -c conda-forge libstdcxx-ng=13 -y
pip install -r requirements.txt
python parse_frame.py         # smoke test → prints a cppyy object
```

Live-capture scripting uses the same verbs as C++ (`picoscenes_start()`, `NICPortal.getInstance().getNic(...)`, `nic.startRxService()`, register an `rxHandle`-style callback).

### Third-party parsers (no PicoScenes install needed)

For just reading `.csi` files on any OS, these community parsers are widely used:

| Parser | Language | Install / repo |
|---|---|---|
| **csiread** — `Picoscenes` class (`read/seek/pmsg/display`) | Cython | `pip install csiread` · <https://github.com/citysu/csiread> |
| **PicoscenesToolbox** (Herrtian) | Python | `git clone --recursive https://github.com/Herrtian/PicoscenesToolbox` |
| **PicoScenes-Python-Toolbox** (official, GitLab) | Python | <https://gitlab.com/wifisensing/PicoScenes-Python-Toolbox> |
| **CSIKit** (Gi-z) — unified reader incl. PicoScenes/USRP | Python | `pip install CSIKit` · <https://github.com/Gi-z/CSIKit> |

See [csi-toolchains.md](csi-toolchains.md) and [wifi-sensing-datasets.md](wifi-sensing-datasets.md) for how these formats interoperate.

---

## 6. The plugin / measurement model

A measurement in PicoScenes *is* a plugin. Built-in ones cover the common cases; you subclass for anything custom.

**Operating modes (built-in plugins / CLI `--mode`):**
- **`logger`** — RX + CSI capture to `.csi` (the workhorse).
- **`injector`** — craft and transmit frames of a chosen format/CBW/MCS/STS.
- **`responder`** — listen and auto-reply, optionally echoing CSI (`--ack-type`), the basis of two-way sounding.
- **`EchoProbe`** — the flagship plugin: a probe/response round-trip that measures both ends' CSI, enabling ranging, reciprocity studies, and channel-sounding sweeps across frequency.
- **`UDP-Forwarder`** — stream received frames off-box over UDP for real-time pipelines.

**Writing a plugin (PS-PDK).** Plugins subclass **`AbstractPicoScenesPlugin`** and implement:

| Method | Role |
|---|---|
| `getPluginName()` / `getPluginDescription()` | identity |
| `getSupportedDeviceTypes()` | which radios it accepts |
| `initialization()` | declare CLI options via Boost.ProgramOptions |
| `parseAndExecuteCommands()` | parse args, run logic |
| `rxHandle(ModularPicoScenesRxFrame)` | per-frame RX callback |
| `pluginStatus()` | status reporting |

The shared object must export its factory with `BOOST_DLL_ALIAS(MyPlugin::create, initPicoScenesPlugin)` so the runtime can load it. TX is done by building a `ModularPicoScenesTxFrame` and calling `nic->startTxService()` / `nic->transmitPicoScenesFrameSync()`. Headers ship under `/usr/local/PicoScenes/include/PicoScenes`; the **PS-PDK** repo has Demo / EchoProbe / UDP-Forwarder as worked examples. Load a plugin at runtime with `--plugin-dir`.

---

## 7. OS / kernel requirements and installation

PicoScenes is **proprietary freeware** distributed as Debian packages with a EULA (the toolboxes and PDK are open, the core runtime and drivers are not — an honest contrast with the fully-open single-NIC tools). It runs **only on real x86-64 hardware** — *no virtualization* (the drivers need direct PCIe/USB access).

**Requirements** ([installation manual](https://ps.zpj.io/manual/installation.html)):

- **OS:** Ubuntu **22.04 LTS** or a direct variant (Kubuntu/Xubuntu/Mint); the project tracks LTS releases (24.04 migration in progress).
- **CPU:** x86-64 with **SSE4.2** minimum, **AVX2** recommended; **≥4 GB RAM**.
- **Firmware/BIOS:** **Secure Boot disabled** (the driver modules are self-signed). The installer pulls the latest HWE kernel and builds matching `picoscenes-driver-modules-<kver>` — a kernel upgrade without a matching module rebuild is the #1 support issue (see the [Issue Tracker](https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues)).
- **Network:** required at install and periodically (the build performs an online expiration/licence check).

**Install:**

```bash
# 1. Download the "PicoScenes Source Updater" .deb for 22.04, install it (GDebi/dpkg).
# 2. Run the maintainer TUI and choose "1 Update/Install PicoScenes":
MaintainPicoScenes
# 3. Accept the EULA (arrows to scroll, TAB to <Ok>), then reboot.
# 4. Verify:
PicoScenes            # first launch throws a "scheduled exception" by design — run it again, Ctrl-C to exit
```

---

## 8. Concrete usage

```bash
# List USRP radios (COTS NICs are addressed by phy index or name)
uhd_find_devices

# Capture CSI (logger) on interface id 3, 2412 MHz, 20 MHz sample rate → writes a .csi
PicoScenes "-i 3 --freq 2412e6 --rate 20e6 --mode logger"

# Inject 802.11 frames: id 4, 20 MHz CBW, MCS 0, single stream
PicoScenes "-i 4 --freq 2412e6 --rate 20e6 --mode injector --cbw 20 --mcs 0 --sts 1 --format HTSU"

# Two-way sounding: responder that replies with CSI, 40 MHz, 2 streams
PicoScenes "-i 3 --freq 2412e6 --rate 20e6 --mode responder --cbw 40 --sts 2 --ack-type csi"
```

Key parameters: `-i/--interface` (phy index, `phyN`, or `usrp<addr>`), `--freq` carrier, `--rate` baseband sample rate, `--cbw` channel bandwidth, `--mcs`, `--sts`, `--format` (`nonHT` / `HT` / `VHT` / `HESU`), `--mode`. The full grammar is in the [parameters manual](https://ps.zpj.io/manual/parameters.html).

**Regulatory / safety.** `injector`, `responder`, and any SDR TX **emit RF**. Restrict experiments to bands and power you are licensed for, prefer a **shielded box / conducted setup with attenuators** for repeatable work, and remember that arbitrary carrier tuning on QCA9300/USRP will happily transmit *outside* the ISM bands — that is on you, not the tool. The 6 GHz AX210 path is subject to region-specific 6E rules (indoor-only / LPI in many jurisdictions). See TX-safety notes in [../docs/verification-tier4.md](../docs/verification-tier4.md).

---

## 9. How it compares to the single-NIC tools

| | Intel 5300 tool | Atheros CSI Tool | Nexmon CSI | ESP32 | **PicoScenes** |
|---|---|---|---|---|---|
| Chips | IWL5300 | ath9k (AR9300 family) | BCM43455c0 / 4339 / 4366c0 … | ESP32(-S/C) | **5300 · QCA9300 · AX200 · AX210 · USRP · HackRF** |
| Standards | 11n | 11n | a/g/n/ac | a/g/n(/ax C6) | **a/g/n/ac/ax(+be on SDR)** |
| Max CBW | 40 | 40 | 80 | 40 | **160 COTS / 320 SDR** |
| Multi-NIC | no | no | no | no | **up to 27** |
| Controlled TX / ranging | no | no | no | limited | **injector/responder/EchoProbe** |
| File format | `.dat` (bespoke) | `.dat` (bespoke) | pcap/UDP | CSV | **versioned `.csi`** |
| Parser | MATLAB `read_bf_file` | MATLAB | pcap parsers | serial CSV | **PMT + PyPicoScenes** |
| SDR back-end | — | — | — | — | **USRP soft-PHY (Tier 4/5)** |
| Openness | open tool / closed µcode | GPL driver | GPL + Nexmon | open + vendor API | **proprietary freeware core** |
| Runs on | old kernels | Linux/OpenWRT | Pi/Android/router | MCU | **Ubuntu LTS, x86-64 only** |

**When to reach for PicoScenes:** anything needing 802.11ac/**ax** CSI, 6 GHz, wide bandwidth, multi-radio synchrony, controlled two-way sounding, or an SDR-based fully-known PHY. **When not to:** cheap/embedded/edge deployment (Pi → Nexmon, MCU → ESP32), fully-open-source pipelines, non-x86 or VM-only hosts, or when a legacy 5300/ath9k `.dat` corpus already covers you. The tools are complementary, and [csi-toolchains.md](csi-toolchains.md) maps the whole landscape.

---

## 10. Limitations and honest caveats

- **Not open source.** The core runtime and drivers are closed freeware under a EULA with an online expiration check; reproducibility depends on the project staying alive and reachable. Budget for that in long-lived experiments.
- **Hardware/OS-narrow.** x86-64 + Ubuntu LTS + Secure-Boot-off + bare metal. No ARM, no VM, no macOS/Windows for capture (toolboxes parse cross-platform, but not capture).
- **COTS CSI is still COTS CSI.** AX200/AX210 CSI is 2×2 with automatic gain — usable and calibrated, but not the clean, gain-controlled 3×3 you get from QCA9300, and not IQ. For true raw-PHY/IQ you need the USRP path (or a real SDR — [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)).
- **Kernel churn.** Driver modules are per-kernel; unattended-upgrades can break capture until `MaintainPicoScenes` rebuilds them.
- **Injection is regulated RF.** See §8.

---

## References

- PicoScenes home & manual — <https://ps.zpj.io/> (installation <https://ps.zpj.io/manual/installation.html>, hardware <https://ps.zpj.io/manual/hardware.html>, parameters <https://ps.zpj.io/manual/parameters.html>, MATLAB toolbox <https://ps.zpj.io/manual/matlab.html>, plugin dev <https://ps.zpj.io/manual/plugin.html>, PyPicoScenes <https://ps.zpj.io/manual/pypicoscenes.html>)
- Z. Jiang et al., *Eliminating the Barriers: Demystifying Wi-Fi Baseband Design and Introducing the PicoScenes Wi-Fi Sensing Platform,* IEEE IoT-J 9(6):4476–4496, 2022 — <https://arxiv.org/abs/2010.10233>
- Zhiping Jiang's research blog (6 GHz CSI, AX200 11ax CSI, USRP spectrum stitching demos) — <https://zpj.io/>
- Code org — <https://github.com/wifisensing> · Issue tracker — <https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues>
- PyPicoScenes — <https://github.com/wifisensing/PyPicoScenes> · PicoScenes-Python-Toolbox — <https://gitlab.com/wifisensing/PicoScenes-Python-Toolbox>
- Third-party parsers: csiread <https://github.com/citysu/csiread> · PicoscenesToolbox <https://github.com/Herrtian/PicoscenesToolbox> · CSIKit <https://github.com/Gi-z/CSIKit>
- *Hands-on Wireless Sensing with Wi-Fi: A Tutorial* (tool comparison incl. PicoScenes) — <https://arxiv.org/pdf/2206.09532>
- wifisensing.io platform page — <https://www.wifisensing.io/building-applications/platforms/picoscenes>

**Related in this catalog:** [csi-toolchains.md](csi-toolchains.md) · [nexmon.md](nexmon.md) · [openwifi.md](openwifi.md) · [wifi-sensing-datasets.md](wifi-sensing-datasets.md) · [../chips/intel.md](../chips/intel.md) · [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../docs/walkthroughs/intel-5300-csi.md](../docs/walkthroughs/intel-5300-csi.md) · [../docs/walkthroughs/atheros-ath9k-spectral-csi.md](../docs/walkthroughs/atheros-ath9k-spectral-csi.md) · [../docs/techniques.md](../docs/techniques.md) · [../docs/taxonomy.md](../docs/taxonomy.md)
