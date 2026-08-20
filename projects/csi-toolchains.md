# CSI Extraction Toolchains — Wi-Fi as a Sensing Radio (Tier 2)

Channel State Information (CSI) is the per-OFDM-subcarrier complex channel response **H** — amplitude **and** phase — that every 802.11 receiver already estimates from the training fields (L-LTF / HT-LTF / VHT-LTF / HE-LTF) in order to equalize a packet. Stock firmware computes it, uses it, and throws it away. A **CSI extraction toolchain** is the firmware patch + driver hack + host parser that intercepts that matrix on its way to the equalizer and ships it to userspace. This is the practical heart of **Tier 2** on the SDR ladder: you are not synthesizing a waveform, but you *are* reading the radio's own PHY telemetry at subcarrier granularity, which is enough for ranging, imaging, gesture/vital-sign sensing, localization, and material characterization.

This file surveys **every** CSI toolchain worth knowing, old and new. For the underlying silicon and how the firmware is cracked open, see [../chips/intel.md](../chips/intel.md), [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md), [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md), and [../chips/espressif.md](../chips/espressif.md). For the signal-processing side (phase sanitization, CFO/SFO/STO removal, spectrum→imaging), see [../docs/techniques.md](../docs/techniques.md).

> **What CSI is not:** CSI is *processed* PHY telemetry (post-FFT, post-channel-estimation), not raw IQ. A tool that gives you CSI is Tier 2, not Tier 3/4. The exceptions noted below — openwifi (Tier 5, soft-PHY) and the ath9k spectral-scan path (Tier 3, raw FFT bins) — reach higher rungs and are included for contrast.

---

## The canonical four (802.11n era)

These are the tools every Wi-Fi-sensing paper from ~2011–2019 was built on. All three commodity-NIC tools report **grouped/quantized** CSI (the firmware hands over what the hardware's rate-adaptation logic wanted, not a clean per-subcarrier dump), which is why phase sanitization is mandatory downstream.

### 1. Linux 802.11n CSI Tool (Halperin) — Intel 5300

The original. Halperin, Hu, Sheth & Wetherall released it in 2010/2011 (SIGCOMM CCR). A patched **closed** Intel `iwlwifi` microcode plus a modified open driver expose CSI on the **Intel Wi-Fi Link 5300** (IWL5300), a 3-antenna 802.11n MIMO card.

- **Output:** channel matrices for **30 subcarrier groups** (≈1 group per 2 subcarriers at 20 MHz, 1 per 4 at 40 MHz), each entry a complex number with **signed 8-bit** real/imag, up to 3×3 streams. Delivered over a netlink `connector` to a `log_to_file` utility; MATLAB `read_bf_file.m` parses it.
- **Bandwidth:** 20/40 MHz (802.11n only).
- **Platform:** Linux, kernel ~3.x-era `iwlwifi`; needs the specific patched firmware blob. Notoriously kernel-version-locked.
- **Firmware:** closed Intel microcode, *binary-patched* (not source). See [../chips/intel.md](../chips/intel.md).
- **License:** the tool's driver/userspace are open; firmware is Intel's.
- **Why it still matters:** the de-facto reference dataset format for a decade; the `.dat` format is understood by every downstream parser.
- **URL:** <https://dhalperi.github.io/linux-80211n-csitool/> · <https://github.com/dhalperi/linux-80211n-csitool>

### 2. Atheros CSI Tool (Yaxiong Xie) — ath9k

Xie & Li's answer to the Intel tool, built on the **open-source `ath9k`** driver — which means far more transparency and *uncompressed* CSI.

- **Chips:** tested on **AR9580, AR9590, AR9344, QCA9558** (and the AR9462/AR9485 family); community reports of QCA9880 via ath9k backward-compat.
- **Output:** **full per-subcarrier** CSI — **56 subcarriers @ 20 MHz, 114 @ 40 MHz** — retaining full amplitude+phase precision, up to 3×3. Richer than the Intel tool's 30 groups.
- **Platform:** Linux (Ubuntu build) **and OpenWRT** (router/embedded build in a separate repo) — you can run it on APs and embedded boards, not just PCs.
- **Firmware:** ath9k is a SoftMAC driver; the PHY is largely driver-side, so the CSI hook lives in `ar9003_csi.c` in the driver, no separate firmware blob to patch. See [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md).
- **License:** GPL (kernel driver).
- **URL:** <https://github.com/xieyaxiongfly/Atheros-CSI-Tool> · OpenWRT: <https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src> · guide: <https://wands.sg/research/wifi/AtherosCSI/>

### 3. Nexmon CSI (SEEMOO) — Broadcom / Cypress

The most widely deployed *modern* commodity-CSI path, because it runs on the **Raspberry Pi** and cheap phones/routers. Built on the **Nexmon** C-based firmware patching framework (see [../projects/nexmon.md](../projects/nexmon.md), [../docs/firmware-reversing.md](../docs/firmware-reversing.md)).

- **Chips:** **BCM4339** (Nexus 5), **BCM43455c0** (Raspberry Pi 3B+/4), **BCM4358** (Nexus 6P), **BCM4366c0 / BCM4365** (Asus RT-AC86U 4×4). CSI for OFDM 802.11a/g/n/ac frames.
- **Output:** per-subcarrier CSI up to **80 MHz** bandwidth; interleaved int16 real/imag (varies by chip — bcm4339/43455c0 give int16 pairs, the 4366c0 uses a different float-ish packing). Up to **4×4 MIMO** on the RT-AC86U. Delivered as UDP frames on the local interface, captured with `tcpdump`/pcap.
- **Platform:** Raspberry Pi OS / Raspbian, Android (rooted Nexus), OpenWRT-ish router builds. Firmware version-specific (7.45.154 / .189 / .206 for the Pi's 43455c0).
- **Firmware:** Broadcom **D11 ucode + ARM Cortex-R/M** — closed, *patched* via Nexmon (Ghidra/IDA + the nexmon toolchain). This is the canonical firmware-RE story of the whole catalog.
- **License:** GPL + Nexmon's own license terms.
- **URL:** <https://github.com/seemoo-lab/nexmon_csi> · original MobiSys'18 extractor: <https://github.com/seemoo-lab/mobisys2018_nexmon_channel_state_information_extractor> · friendlier fork (Pi one-liner installer): nexmonster/zeroby0 forks.

### 4. ESP32 CSI Toolkit (Steven M. Hernandez) + native ESP-IDF API

The cheapest CSI radio on earth (~$3 SoC). Espressif *documented and blessed* CSI in the SDK, so — uniquely — **no firmware reversing is required**. This is the one Tier-2 path with an official vendor API.

- **Chips:** **ESP32**, ESP32-S2/S3, **ESP32-C3/C5/C6** (C6 adds Wi-Fi 6; note ordering/L-LTF quirks per esp-idf issues). See [../chips/espressif.md](../chips/espressif.md).
- **Output:** CSI for **up to 52/64 subcarriers** (L-LTF + HT-LTF, 20/40 MHz depending on part) via the native `wifi_csi_info_t` struct — each subcarrier two signed bytes (imag then real). Single antenna (1×1). Active mode (SoC associates) and passive/sniffer mode.
- **Platform:** standalone MCU; streams CSV over UART/serial (or Wi-Fi/UDP). Runs from any host, phone, or fully standalone.
- **Firmware:** Xtensa LX6/LX7 (or RISC-V on C-series); Wi-Fi MAC is a closed blob but the **CSI callback is a public ESP-IDF API** — `openness: documented`.
- **License:** the toolkit is open (Hernandez, MIT-ish); ESP-IDF is Apache-2.0.
- **URL:** toolkit <https://github.com/StevenMHernandez/ESP32-CSI-Tool> (<https://stevenmhernandez.github.io/ESP32-CSI-Tool/>) · official <https://github.com/espressif/esp-csi> · API guide: ESP-IDF Wi-Fi Driver docs.
- **Related — Wi-ESP:** Atif et al., *Journal of Computational Design and Engineering* 2020 — an ESP8266/ESP32 DFWS tool that also exposes all **52** subcarriers and packages the whole sense-and-classify pipeline on the MCU as a standalone device. Paper: <https://academic.oup.com/jcde/article/7/5/644/5837600>.

---

## The 802.11ax generation (Wi-Fi 6 / 6E)

These unlock **160 MHz, up to ~2000 subcarriers, and the 6 GHz band** — a huge jump in spatial/frequency resolution over the 802.11n tools.

### AX-CSI / IAX (Gringoli, Cominelli, Blanco & Widmer) — Intel AX200/AX210

Presented at WiNTECH'21. The first tool to pull CSI from commercial 802.11ax silicon by patching the **Intel AX200/AX201/AX210/AX211** firmware.

- **Output:** CSI from **all** OFDM formats (802.11a/g/n/ac/**ax**), up to **160 MHz HE** with **up to 1992 subcarriers in a single packet**, multi-antenna.
- **Platform:** Linux; patched Intel firmware + modified `iwlwifi`.
- **Firmware:** Intel closed microcode (ARC-based op-code), binary-patched. See [../chips/intel.md](../chips/intel.md).
- **License:** open source (tool); Intel firmware proprietary.
- **URL:** paper <https://ans.unibs.it/assets/documents/axcsi.pdf> · <https://dl.acm.org/doi/10.1145/3477086.3480833>. Code distributed via the UNIBS/ANS group.

### FeitCSI (KuskoSoft) — Intel AX200/AX210

The most *usable* modern Intel-CSI tool: a packaged CLI **+ GUI**, live-USB distro, x86_64 and ARM builds. Backed by the 2025 IEEE paper *"Enhancing CSI-based Wireless Sensing with Open Source Linux 802.11ax CSI Tool."*

- **Output:** CSI **and frame injection** for all formats 802.11a/g/n/ac/ax at **20/40/80/160 MHz** with "no limits"; **6 GHz** (5945–7125 MHz) when the NIC supports it (AX210).
- **Chips:** Intel **AX200, AX210** (AX201/211 by extension).
- **Platform:** Linux; ships source, binary, and a live distro so you don't fight kernel/firmware versions.
- **Firmware:** patched Intel microcode; the tool wraps the driver plumbing. `openness: patchable`.
- **License:** open source (GPL).
- **URL:** <https://github.com/KuskoSoft/FeitCSI> · <https://feitcsi.kuskosoft.com/> · paper: <https://ieeexplore.ieee.org/document/10944229/>.

### PicoScenes (Zhiping Jiang) — the multi-NIC platform

The most capable and general research platform. One C++ framework + patched drivers spanning **many** NIC generations, with a MATLAB/Python parsing SDK, and support for **up to 27 NICs concurrently** (MIMO arrays, distributed sensing).

- **Supported NICs:** **IWL5300** (802.11n), **QCA9300** (Atheros AR9300 family — arbitrary carrier tuning across ~2.4 GHz of spectrum, 2.5–80 MHz bandwidth), **AC9260** (802.11ac), **AX200 / AX210** (802.11ax, incl. **6 GHz** on AX210), plus **USRP / SoapySDR** front-ends (bridging to true SDR, [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)).
- **Output:** CSI for **all** formats 802.11a/g/n/ac/ax up to **160 MHz**; on AX210 it is (per the author) the **first & only public platform** to do packet injection + CSI measurement in the **6 GHz** band. Rich frame metadata; unified `.csi` container parsed by the PicoScenes MATLAB Toolbox.
- **Platform:** Linux (Ubuntu); Debian packages.
- **Firmware:** patched Intel & Atheros firmware/drivers under the hood.
- **License:** free for academic use (binary distribution; not fully open).
- **URL:** <https://ps.zpj.io/> · <https://www.wifisensing.io/building-applications/platforms/picoscenes> · arXiv "Eliminating the Barriers…" <https://arxiv.org/pdf/2010.10233>.

### CSI from commercial APs (802.11ax) — Broadcom 43684 & ZTECSITool

Beyond client NICs, 2023–2025 work pulls CSI straight out of consumer **access points**:

- **Broadcom BCM43684 AP CSI:** first system to extract CSI from 802.11ax consumer devices on the **BCM43684** chip — up to **160 MHz, 4×4 MIMO**, full HE PHY. Ties into the Nexmon lineage. (arXiv 2305.10554, "Collecting CSI in Wi-Fi Access Points for IoT Forensics".)
- **ZTECSITool (2025):** customized firmware + open tools capturing CSI from a commercial Wi-Fi 6 AP up to **160 MHz / 512 subcarriers**, with a Python GUI for real-time visualization. Paper: <https://arxiv.org/abs/2506.16957>.

---

## 802.11ac / AoA specialists

### UbiLocate / "UbiquitiCSI" (IMDEA Networks) — Atheros 802.11ac

The 802.11ac CSI extractor most people mean by "UbiquitiCSI": extracts CSI from **IEEE 802.11ac** frames on Atheros/QCA hardware (as found in Ubiquiti-class APs) and is built for **AoA/AoD + relative time-of-flight** estimation across paths — i.e. localization rather than generic sensing.

- **Output:** 802.11ac per-subcarrier CSI (up to 80 MHz), multi-antenna, tuned for angle estimation.
- **Platform:** Linux/OpenWRT on QCA98xx-class radios.
- **License:** open (academic).
- **URL:** <https://github.com/IMDEANetworksWNG/UbiLocate>.

### Beamforming-feedback "pseudo-CSI" (Wi-BFI, BFI extraction)

A different route to channel info that needs **no firmware patch at all**: 802.11ac/ax beamforming feedback (compressed **V**-matrix angles φ/ψ) is sent *in the clear* in management frames. Sniff it in monitor mode ([../chips/intel.md](../chips/intel.md) / any injection-capable NIC) and reconstruct a quantized channel.

- **Wi-BFI:** <https://arxiv.org/pdf/2309.04408> · MU-MIMO BFI extractor: <https://github.com/kfoysalhaque/MU-MIMO-Beamforming-Feedback-Extraction-IEEE802.11ac>. This is Tier ~1.5 — it uses only monitor mode, not a PHY tap — but yields CSI-like features, so it belongs in any CSI survey.

---

## Higher-rung outliers (for contrast)

- **openwifi (open-sdr)** — a full **open-source 802.11a/g/n PHY+MAC on Xilinx Zynq FPGA+ARM SoC**. Its `side_ch` module streams CSI in monitor **and** AP/client/ad-hoc modes. Because the PHY is *yours*, this is **Tier 5**, not Tier 2 — the CSI just falls out. 20 MHz, 802.11n. See [../projects/rtl-sdr-lineage.md](../projects/rtl-sdr-lineage.md) for the SDR family and [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md). URL: <https://github.com/open-sdr/openwifi> (CSI doc: `doc/app_notes/csi.md`).
- **ath9k spectral scan** — the same Atheros silicon that gives CSI can dump **raw FFT bins** (Tier 3) via `spectral_scan`, visualized with `speccy`/`FFT_eval`. Not CSI per se, but the same chips, one rung up. See [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) and [../docs/techniques.md](../docs/techniques.md).

---

## Parsers & glue (format-agnostic)

- **CSIKit (Gi-z)** — the universal Python parser. Auto-detects and reads **Atheros, Intel (IWL5300 / AX200 / AX210), Nexmon, ESP32, FeitCSI, and PicoScenes (incl. USRP)** formats; processing/visualization on numpy+matplotlib, CSV/JSON export. This is the "Gi-CSI" of the scope. URL: <https://github.com/Gi-z/CSIKit> · docs <https://gi-z.github.io/CSIKit/>.
- **csiparser** (PyPI) — lightweight ESP32-CSI CSV parser.
- **PicoScenes MATLAB Toolbox** — parses the `.csi` container.
- Downstream feature/DL libraries: **SenseFi** benchmark (arXiv 2207.07859) consumes these formats.

---

## Comparison table

| Tool | Chip(s) / NIC | Std / BW | Subcarriers / streams | Platform / OS | Firmware RE | License | Link |
|---|---|---|---|---|---|---|---|
| **Linux 802.11n CSI Tool** (Halperin) | Intel IWL5300 | 11n, 20/40 MHz | 30 groups, ≤3×3, int8 | Linux (patched iwlwifi) | closed µcode, binary-patched | open tool | [dhalperi.github.io](https://dhalperi.github.io/linux-80211n-csitool/) |
| **Atheros CSI Tool** (Xie) | AR9580/9590/9344, QCA9558 | 11n, 20/40 MHz | 56 @20 / 114 @40, ≤3×3, full-precision | Linux + OpenWRT | ath9k SoftMAC (driver hook) | GPL | [github](https://github.com/xieyaxiongfly/Atheros-CSI-Tool) |
| **Nexmon CSI** (SEEMOO) | BCM4339/43455c0/4358/4366c0 | 11a/g/n/ac, ≤80 MHz | per-SC, ≤4×4 (RT-AC86U), int16 | Pi OS / Android / router | D11 ucode+ARM, Nexmon patch | GPL | [github](https://github.com/seemoo-lab/nexmon_csi) |
| **ESP32 CSI Toolkit** (Hernandez) | ESP32 / S2/S3 / C3/C6 | 11n (C6: 11ax), 20/40 MHz | ≤52/64, 1×1, int8 pairs | standalone MCU, UART/UDP | Xtensa/RISC-V, **documented API** | open / Apache-2.0 | [github](https://github.com/StevenMHernandez/ESP32-CSI-Tool) |
| **esp-csi** (Espressif official) | ESP32 family | 11n/ax | native `wifi_csi_info_t` | ESP-IDF | vendor-documented | Apache-2.0 | [github](https://github.com/espressif/esp-csi) |
| **Wi-ESP** (Atif et al.) | ESP8266/ESP32 | 11n | 52, 1×1 | standalone MCU | documented API | academic | [paper](https://academic.oup.com/jcde/article/7/5/644/5837600) |
| **AX-CSI / IAX** (Gringoli) | Intel AX200/201/210/211 | 11a…**ax**, ≤160 MHz | up to **1992** / packet | Linux (patched iwlwifi) | closed µcode, binary-patched | open tool | [paper](https://ans.unibs.it/assets/documents/axcsi.pdf) |
| **FeitCSI** (KuskoSoft) | Intel AX200 / AX210 | 11a…ax, 20/40/80/160 MHz, **6 GHz** | full, + TX injection | Linux (CLI+GUI, live USB) | patched µcode | GPL | [github](https://github.com/KuskoSoft/FeitCSI) |
| **PicoScenes** (Jiang) | IWL5300, QCA9300, AC9260, AX200, AX210, USRP | 11a…ax, ≤160 MHz, **6 GHz** (AX210) | full, ≤27 NICs concurrent | Linux (Ubuntu/Debian) | patched Intel+Atheros | free academic (binary) | [ps.zpj.io](https://ps.zpj.io/) |
| **UbiLocate / UbiquitiCSI** (IMDEA) | Atheros/QCA 11ac | 11ac, ≤80 MHz | per-SC, AoA/AoD-tuned | Linux/OpenWRT | driver/firmware patch | academic | [github](https://github.com/IMDEANetworksWNG/UbiLocate) |
| **BCM43684 AP CSI** | Broadcom BCM43684 | 11ax, ≤160 MHz | per-SC, 4×4 | consumer AP | Nexmon-lineage patch | academic | [arXiv](https://arxiv.org/pdf/2305.10554) |
| **ZTECSITool** | ZTE Wi-Fi 6 AP (Broadcom-class) | 11ax, ≤160 MHz | 512 SC | AP + Python GUI | custom firmware | open | [arXiv](https://arxiv.org/abs/2506.16957) |
| **Wi-BFI / BFI extractor** | any injection-capable NIC | 11ac/ax | compressed V (φ/ψ) | Linux monitor mode | **none** (sniff) | open | [arXiv](https://arxiv.org/pdf/2309.04408) |
| **openwifi** (Tier 5) | Zynq FPGA+ADRV9361 SDR | 11a/g/n, 20 MHz | per-SC (soft PHY) | Linux/Zynq SoC | **open PHY** | open (AGPL/BSD) | [github](https://github.com/open-sdr/openwifi) |
| **CSIKit** (parser) | reads all above | — | universal | Python (cross-platform) | n/a | MIT-ish | [github](https://github.com/Gi-z/CSIKit) |

---

## Choosing a toolchain (quick guidance)

- **Cheapest / classroom / standalone sensor:** ESP32 CSI Toolkit — $3, no RE, but 1×1 and few subcarriers.
- **Best price/quality on ubiquitous hardware:** Nexmon CSI on a Raspberry Pi 4 (43455c0) or RT-AC86U (4366c0, 4×4).
- **Highest fidelity, 802.11n, uncompressed:** Atheros CSI Tool.
- **Modern Wi-Fi 6 / 6E, single NIC, easy:** FeitCSI (GUI, live USB).
- **Research platform, many NICs, most formats, 6 GHz:** PicoScenes.
- **You own the PHY (Tier 5):** openwifi.
- **No firmware patching allowed (compliance-safe):** Wi-BFI beamforming-feedback sniffing.

## Un-cataloged / TODO

- **Gi-CSI vs CSIKit** — the scope lists "Gi-CSI"; confirm whether this is a distinct repo or simply CSIKit (Gi-z). Treated here as CSIKit pending confirmation.
- **nexmon_csi on BCM4375b1 / BCM4389** (flagship phones, Wi-Fi 6/6E) — reported community work; needs verification of a public patch.
- **mt76 CSI** — any CSI path on MediaTek (MT7615/MT7915/MT7921) via the open `mt76` driver? See [../chips/mediatek-ralink.md]; not yet located.
- **QCA9880/9882 (ath10k) CSI** — firmware is closed (no SoftMAC); CSI extraction status unclear beyond spectral scan. Cross-check [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md).
- **Intel AX411 / BE200 (Wi-Fi 7, 320 MHz)** — has anyone extended AX-CSI/FeitCSI to Wi-Fi 7? Likely near-term.
- **ZTECSITool repo URL** — locate the code release accompanying arXiv 2506.16957.
- **Nexmon CSI exact packing per chip** (4366c0 float format, phase-per-core offsets) — document precisely.
- **RISC-V ESP32-C5/C6 subcarrier ordering bugs** (esp-idf #14271) — track fix status for reliable 11ax CSI.
- **Broadcom BCM43684 AP CSI** — pin down public tooling vs paper-only status.
