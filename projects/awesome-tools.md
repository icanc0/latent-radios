# Awesome Tools & Repos — The Consolidated Toolbox

*Cycle 8 · one flat, categorized index of **every** tool, firmware framework, driver, library, and dataset the Latent Radios catalog references.* One line of purpose per entry, a real primary URL, and the catalog page where it is used in depth. If a repo appears in several chip pages, it lives here once.

**How to read the tiers referenced below:** entries are tools, not chips, so they carry no `sdr_tier` of their own — they *unlock* tiers on hardware. A CSI extractor pushes a chip to Tier 2; a spectral-scan patch to Tier 3; an arbitrary-waveform TX patch or a genuine SDR PHY to Tier 4–5. See [`../docs/taxonomy.md`](../docs/taxonomy.md) for the ladder.

See also: [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) (deep dives on the CSI stacks) · [`../docs/further-reading.md`](../docs/further-reading.md) (papers, talks, background) · [`../projects/nexmon.md`](../projects/nexmon.md) · [`../projects/ml-csi-sensing.md`](../docs/ml-csi-sensing.md).

---

## 1. Firmware reverse-engineering & patching frameworks

The core of "latent radios": tooling that disassembles, patches, rebuilds, or replaces the closed firmware on a commodity Wi-Fi chip to expose monitor/injection, CSI, spectral scan, or raw TX.

| Tool | Purpose | URL |
|---|---|---|
| **Nexmon** | C-based patching framework for Broadcom/Cypress FullMAC Wi-Fi firmware (BCM43xx / CYW43xx); the reference platform for monitor mode, injection, and custom firmware on phones and the Raspberry Pi. | https://github.com/seemoo-lab/nexmon |
| **nexmon_csi** | Nexmon extension that extracts per-subcarrier CSI from BCM43455c0 / BCM4358 / BCM4366c0 and similar — Tier 2 on otherwise black-box FullMAC parts. | https://github.com/seemoo-lab/nexmon_csi |
| **b43-tools** | Assembler/disassembler for the Broadcom SoftMAC (b43) microcode — the classic entry point to reading and modifying legacy Broadcom PHY firmware. | https://github.com/mbuesch/b43-tools |
| **d11-emu** | SEEMOO's D11 microcode emulator/disassembler for Broadcom's 802.11 on-chip microcontroller — lets you trace and understand firmware behavior offline. | https://github.com/seemoo-lab/d11-emu |
| **OpenFWWF** | Open Firmware for WiFi networks: fully open microcode for Broadcom b43 SoftMAC cards — a from-scratch, hackable MAC used heavily in research. | http://netweb.ing.unibs.it/~openfwwf/ |
| **carl9170fw** | Open, buildable firmware for Atheros AR9170 USB (carl9170) dongles — modifiable SoftMAC firmware for a USB-attached Wi-Fi PHY. | https://github.com/chunkeey/carl9170fw |
| **open-ath9k-htc-firmware** | Qualcomm/Atheros' officially open firmware for AR7010/AR9271 USB (ath9k_htc) — buildable source enabling custom MAC behavior and SDR-ish experiments. | https://github.com/qca/open-ath9k-htc-firmware |
| **openwifi** | Full open-source 802.11 design (Linux mac80211 driver + FPGA baseband) for Xilinx Zynq SoC + AD9361 — a genuine soft-MAC/soft-PHY Wi-Fi SDR (Tier 5). | https://github.com/open-sdr/openwifi |

Catalog cross-refs: [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md), [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md), [`../chips/risc-v-wifi.md`](../chips/risc-v-wifi.md), [`../projects/nexmon.md`](../projects/nexmon.md).

---

## 2. CSI extraction tools (the sensor front-ends)

Firmware/driver stacks that turn a NIC into a channel-state sensor. See [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) for build recipes and [`../docs/walkthroughs/nexmon-csi-to-usable-csi.md`](../docs/walkthroughs/nexmon-csi-to-usable-csi.md).

| Tool | Purpose | URL |
|---|---|---|
| **Linux 802.11n CSI Tool** | Halperin et al.'s original CSI extractor for the Intel 5300 (iwlwifi) — the tool that launched Wi-Fi sensing; 30-subcarrier CSI over a custom driver. | https://dhalperi.github.io/linux-80211n-csitool/ |
| **Atheros CSI Tool** | Yaxiong Xie et al.'s CSI extractor for Atheros ath9k NICs (AR9380 etc.) — full-bandwidth per-subcarrier CSI, an open alternative to the Intel tool. | https://wands.sg/research/wifi/AtherosCSI/ |
| **ESP32-CSI-Tool** | Turns a US\$5 ESP32 into a standalone CSI sensor — firmware + CSV logging, the cheapest on-ramp to Wi-Fi sensing. | https://github.com/StevenMHernandez/ESP32-CSI-Tool |
| **AX-CSI** | Gringoli et al.'s method for extracting CSI from commercial 802.11ax (Wi-Fi 6) Intel AX200/AX210 platforms — extends sensing to OFDMA/1024-QAM PHYs. | https://dl.acm.org/doi/10.1145/3477086.3480833 |
| **PicoScenes** | Unified CSI measurement platform spanning Intel AX200/AX210, QCA9300, and nexmon targets, with a MATLAB/Python toolbox — the most capable cross-vendor sensing stack. | https://ps.zpj.io/ |
| **FeitCSI** | Open-source (GPL) GUI/CLI CSI extractor and generator for Intel AX2xx/BE2xx using the iwlwifi debug path — modern Wi-Fi 6/6E CSI without proprietary blobs. | https://feitcsi.kuskosoft.com/ |
| **nexmon_csi** | (see §1) The extractor that makes Broadcom FullMAC parts — Pi 3B+/4, many phones — into CSI sensors. | https://github.com/seemoo-lab/nexmon_csi |

---

## 3. CSI parsing, analysis & ML libraries

Read, decode, and learn from the byte streams the extractors above produce.

| Tool | Purpose | URL |
|---|---|---|
| **CSIKit** | Python toolkit that parses CSI from Intel, Atheros, nexmon, ESP32, and PicoScenes formats into a common API, with visualization and feature helpers. | https://github.com/Gi-z/CSIKit |
| **csiread** | Fast C-accelerated Python reader for Intel 5300, Atheros, nexmon, and ESP32 CSI files — the throughput-oriented parsing choice. | https://github.com/citysu/csiread |
| **nexcsi** | Lightweight Python decoder specifically for nexmon_csi `.pcap` output (BCM43455c0 etc.). | https://github.com/nexmonster/nexcsi |
| **SenseFi** | Benchmark + PyTorch library for deep-learning Wi-Fi CSI sensing (HAR, gesture, identity) with reference models and standardized datasets. | https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark |

Catalog cross-refs: [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md), [`../docs/walkthroughs/wifi-csi-human-activity-recognition.md`](../docs/walkthroughs/wifi-csi-human-activity-recognition.md).

---

## 4. Drivers (monitor mode, injection, general enablement)

Mainline and out-of-tree kernel drivers that deliver Tier 1 (monitor + injection) — and keep awkward USB adapters working. See [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md).

| Tool | Purpose | URL |
|---|---|---|
| **aircrack-ng** | The canonical Wi-Fi auditing suite (airodump/aireplay/airmon) plus patched drivers; the practical yardstick for whether a chip does monitor + injection. | https://github.com/aircrack-ng/aircrack-ng |
| **morrownr 8812au / 8821cu** | Maintained out-of-tree drivers for Realtek RTL8812AU/8814AU/8821CU USB adapters with monitor + injection; the go-to for popular pentest dongles. | https://github.com/morrownr/8812au-20210629 |
| **morrownr USB-WiFi (index)** | Curated guide + driver hub mapping which USB adapters support monitor/injection and which driver to use. | https://github.com/morrownr/USB-WiFi |
| **mt76** | Mainline Linux driver for MediaTek MT76xx USB/PCIe Wi-Fi (MT7612U, MT7921, MT7996…) with solid monitor-mode and, on some parts, spectral/CSI hooks. | https://github.com/openwrt/mt76 |
| **rtw88** | Linux driver for Realtek 802.11ac parts (RTL8822BU/CU, RTL8821C…) — monitor-mode enablement for a huge installed base. | https://github.com/lwfinger/rtw88 |
| **rtw89** | Linux driver for Realtek 802.11ax parts (RTL8852AE/BE, RTL8922AE) — the Wi-Fi 6/6E front. | https://github.com/lwfinger/rtw89 |

---

## 5. SDR frameworks & Wi-Fi/LoRa/GNSS flowgraphs

General SDR software that pairs with the above (or with a real SDR) for signal-level work.

| Tool | Purpose | URL |
|---|---|---|
| **GNU Radio** | The foundational SDR DSP framework — flowgraph runtime + block library underpinning almost every custom PHY experiment. | https://github.com/gnuradio/gnuradio |
| **gr-ieee802-11** | Bastian Bloessl's GNU Radio 802.11a/g/p transceiver — a fully open Wi-Fi PHY in software, ideal for understanding OFDM and for TX/RX on an SDR. | https://github.com/bastibl/gr-ieee802-11 |
| **gr-lora** | GNU Radio implementation of a LoRa PHY receiver (blind decode of CSS chirps) — reference for sub-GHz LPWAN work. | https://github.com/rpp0/gr-lora |
| **GNSS-SDR** | Open GNSS software receiver (GPS/Galileo/GLONASS/BeiDou) — the reference for turning raw IQ into position fixes. | https://github.com/gnss-sdr/gnss-sdr |
| **SoapySDR** | Vendor-neutral SDR hardware abstraction layer — one API across RTL-SDR, HackRF, USRP, LimeSDR, bladeRF, etc. | https://github.com/pothosware/SoapySDR |

Catalog cross-refs: [`../docs/techniques.md`](../docs/techniques.md), [`../chips/hardware-index.md`](../chips/hardware-index.md).

---

## 6. Sniffing & protocol analysis (Wi-Fi, BLE, Zigbee, cellular)

Capture, dissect, and analyze traffic across the wireless stacks the catalog touches.

| Tool | Purpose | URL |
|---|---|---|
| **Kismet** | Wireless sniffer/IDS aggregating Wi-Fi, Bluetooth, RF, and SDR sources into one capture/analysis engine. | https://github.com/kismetwireless/kismet |
| **Sniffle** | BLE 4.x/5.x sniffer firmware for TI CC1352/CC26x2 dongles — reliable connection-following BLE capture on cheap hardware. | https://github.com/nccgroup/Sniffle |
| **Ubertooth** | Great Scott Gadgets' open Bluetooth/BLE monitoring platform — hardware + firmware + host tools for 2.4 GHz classic BT experimentation. | https://github.com/greatscottgadgets/ubertooth |
| **KillerBee** | Python framework for 802.15.4 / ZigBee sniffing and injection (with supported radios). | https://github.com/riverloopsec/killerbee |
| **QCSuper** | Turns rooted Qualcomm phones/modems into cellular sniffers by capturing DIAG-layer messages into pcap (2G–5G). | https://github.com/P1sec/QCSuper |
| **SCAT** | Signaling Collection And Analysis Tool — parses Qualcomm/Samsung baseband diag logs into GSMTAP/pcap for cellular analysis. | https://github.com/fgsect/scat |
| **MobileInsight** | On-device cellular protocol analyzer exposing fine-grained LTE/5G control-plane messages from the baseband. | https://github.com/mobile-insight/mobileinsight-core |
| **Wireshark** | The universal packet dissector — the shared lens for radiotap Wi-Fi captures, GSMTAP cellular, BLE, and more. | https://gitlab.com/wireshark/wireshark |

Catalog cross-refs: [`../chips/other-vendors.md`](../chips/other-vendors.md), [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md).

---

## 7. Sensing datasets & benchmarks

Public CSI datasets for reproducing and comparing Wi-Fi sensing results (mostly bundled/linked via SenseFi and the source labs).

| Dataset | Purpose | URL |
|---|---|---|
| **SignFi** | 276-class sign-language gesture CSI dataset (Intel 5300) — a standard gesture-recognition benchmark. | https://github.com/yongsen/SignFi |
| **Widar3.0** | Large cross-domain gesture dataset with BVP (body-coordinate velocity profile) features for domain-independent sensing. | http://tns.thss.tsinghua.edu.cn/widar3.0/ |
| **UT-HAR** | Human-activity-recognition CSI dataset (Intel 5300, 7 activities) redistributed and standardized in the SenseFi benchmark. | https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark |
| **NTU-Fi (HAR / HumanID)** | Wi-Fi CSI datasets for activity and person identification packaged with SenseFi loaders. | https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark |

Catalog cross-refs: [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md), [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md).

---

## Quick chooser

- **"Make my Broadcom phone/Pi a sensor"** → Nexmon → nexmon_csi → nexcsi/CSIKit.
- **"Cheapest possible CSI"** → ESP32-CSI-Tool → CSIKit.
- **"Wi-Fi 6 CSI on a laptop"** → FeitCSI or PicoScenes (Intel AX2xx).
- **"Legacy but full-bandwidth CSI"** → Atheros CSI Tool or Linux 802.11n CSI Tool.
- **"Just monitor + inject"** → aircrack-ng + morrownr driver (Realtek) or mt76 (MediaTek).
- **"Real open Wi-Fi PHY on an SDR"** → openwifi (FPGA) or gr-ieee802-11 (software).
- **"Read someone else's air"** → Kismet / Wireshark (Wi-Fi), Sniffle / Ubertooth (BLE), KillerBee (Zigbee), QCSuper / SCAT / MobileInsight (cellular).

> **Safety & legality:** several entries enable transmit (gr-ieee802-11, openwifi, injection drivers, CSI tools that emit probe frames). Transmit only into a shielded enclosure or on bands/power you are licensed for. See [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md).

---

## References (primary sources)

- Nexmon framework — https://github.com/seemoo-lab/nexmon
- nexmon_csi — https://github.com/seemoo-lab/nexmon_csi
- b43-tools — https://github.com/mbuesch/b43-tools
- d11-emu — https://github.com/seemoo-lab/d11-emu
- OpenFWWF — http://netweb.ing.unibs.it/~openfwwf/
- carl9170fw — https://github.com/chunkeey/carl9170fw
- open-ath9k-htc-firmware — https://github.com/qca/open-ath9k-htc-firmware
- openwifi — https://github.com/open-sdr/openwifi
- Linux 802.11n CSI Tool — https://dhalperi.github.io/linux-80211n-csitool/
- Atheros CSI Tool — https://wands.sg/research/wifi/AtherosCSI/
- ESP32-CSI-Tool — https://github.com/StevenMHernandez/ESP32-CSI-Tool
- AX-CSI (WiNTECH '21) — https://dl.acm.org/doi/10.1145/3477086.3480833
- PicoScenes — https://ps.zpj.io/
- FeitCSI — https://feitcsi.kuskosoft.com/
- CSIKit — https://github.com/Gi-z/CSIKit
- csiread — https://github.com/citysu/csiread
- nexcsi — https://github.com/nexmonster/nexcsi
- SenseFi — https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark
- aircrack-ng — https://github.com/aircrack-ng/aircrack-ng
- morrownr 8812au — https://github.com/morrownr/8812au-20210629
- morrownr 8821cu — https://github.com/morrownr/8821cu-20210916
- morrownr USB-WiFi — https://github.com/morrownr/USB-WiFi
- mt76 — https://github.com/openwrt/mt76
- rtw88 — https://github.com/lwfinger/rtw88
- rtw89 — https://github.com/lwfinger/rtw89
- GNU Radio — https://github.com/gnuradio/gnuradio
- gr-ieee802-11 — https://github.com/bastibl/gr-ieee802-11
- gr-lora — https://github.com/rpp0/gr-lora
- GNSS-SDR — https://github.com/gnss-sdr/gnss-sdr
- SoapySDR — https://github.com/pothosware/SoapySDR
- Kismet — https://github.com/kismetwireless/kismet
- Sniffle — https://github.com/nccgroup/Sniffle
- Ubertooth — https://github.com/greatscottgadgets/ubertooth
- KillerBee — https://github.com/riverloopsec/killerbee
- QCSuper — https://github.com/P1sec/QCSuper
- SCAT — https://github.com/fgsect/scat
- MobileInsight — https://github.com/mobile-insight/mobileinsight-core
- Wireshark — https://gitlab.com/wireshark/wireshark
- SignFi — https://github.com/yongsen/SignFi
- Widar3.0 — http://tns.thss.tsinghua.edu.cn/widar3.0/
