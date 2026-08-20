# Consolidated Comparison Tables — the one-page reference

One page, four tables. This consolidates the numbers scattered across the catalog into a single quick-lookup sheet: **(A)** CSI-extraction toolchains, **(B)** genuine SDRs (the yardstick), **(C)** go-to monitor/injection dongles, and **(D)** the SDR ladder with a canonical example per rung.

This page **summarizes**; it does not override. Where a cell here is terse, the source page is authoritative and carries the caveats:

- CSI toolchains → [../projects/csi-toolchains.md](../projects/csi-toolchains.md)
- Genuine-SDR yardstick → [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)
- Monitor/injection driver reality → [monitor-injection-support.md](../chips/monitor-injection-support.md) *(chips/)*
- Adapter part numbers → [../chips/hardware-index.md](../chips/hardware-index.md)
- The ladder definition → [../docs/taxonomy.md](../docs/taxonomy.md)

Every "yes" in these tables hides a caveat (a kernel-version lock, a firmware branch, a rewritten header field). Read the caveats on the source page before you buy or build.

---

## A. CSI extraction toolchains (Tier 2, plus outliers)

*tool → chip/NIC → standard & bandwidth → subcarriers/streams → platform → link.* Full precision notes, packing formats, and licensing on [../projects/csi-toolchains.md](../projects/csi-toolchains.md).

| Tool | Chip(s) / NIC | Std / BW | Subcarriers / streams | Platform | Link |
|---|---|---|---|---|---|
| **Linux 802.11n CSI Tool** (Halperin) | Intel IWL5300 | 11n, 20/40 MHz | 30 groups, ≤3×3, int8 | Linux (patched `iwlwifi`) | [dhalperi.github.io](https://dhalperi.github.io/linux-80211n-csitool/) |
| **Atheros CSI Tool** (Xie) | AR9580/9590/9344, QCA9558 | 11n, 20/40 MHz | 56 @20 / 114 @40, ≤3×3, full-precision | Linux + OpenWRT | [github](https://github.com/xieyaxiongfly/Atheros-CSI-Tool) |
| **Nexmon CSI** (SEEMOO) | BCM4339 / 43455c0 / 4358 / 4366c0 | 11a/g/n/ac, ≤80 MHz | per-SC, ≤4×4 (RT-AC86U), int16 | Raspberry Pi OS / Android / router | [github](https://github.com/seemoo-lab/nexmon_csi) |
| **ESP32 CSI Toolkit** (Hernandez) | ESP32 / S2/S3 / C3/C6 | 11n (C6: 11ax), 20/40 MHz | ≤52/64, 1×1, int8 pairs | standalone MCU (UART/UDP) | [github](https://github.com/StevenMHernandez/ESP32-CSI-Tool) |
| **esp-csi** (Espressif, official) | ESP32 family | 11n/ax | native `wifi_csi_info_t` | ESP-IDF | [github](https://github.com/espressif/esp-csi) |
| **AX-CSI / IAX** (Gringoli) | Intel AX200/201/210/211 | 11a…**ax**, ≤160 MHz | up to **1992** / packet, multi-antenna | Linux (patched `iwlwifi`) | [paper (PDF)](https://ans.unibs.it/assets/documents/axcsi.pdf) |
| **FeitCSI** (KuskoSoft) | Intel AX200 / AX210 | 11a…ax, 20/40/80/160 MHz, **6 GHz** | full + TX injection | Linux (CLI+GUI, live USB) | [github](https://github.com/KuskoSoft/FeitCSI) |
| **PicoScenes** (Jiang) | IWL5300, QCA9300, AC9260, AX200/AX210, USRP/SoapySDR | 11a…ax, ≤160 MHz, **6 GHz** (AX210) | full, ≤27 NICs concurrent | Linux (Ubuntu/Debian) | [ps.zpj.io](https://ps.zpj.io/) |
| **UbiLocate / UbiquitiCSI** (IMDEA) | Atheros/QCA 11ac | 11ac, ≤80 MHz | per-SC, AoA/AoD-tuned | Linux / OpenWRT | [github](https://github.com/IMDEANetworksWNG/UbiLocate) |
| **BCM43684 AP CSI** | Broadcom BCM43684 | 11ax, ≤160 MHz | per-SC, 4×4 | consumer AP (Nexmon lineage) | [arXiv](https://arxiv.org/pdf/2305.10554) |
| **ZTECSITool** | ZTE Wi-Fi 6 AP (Broadcom-class) | 11ax, ≤160 MHz | 512 SC | AP + Python GUI | [arXiv](https://arxiv.org/abs/2506.16957) |
| **Wi-BFI / BFI extractor** | any injection-capable NIC | 11ac/ax | compressed **V** (φ/ψ angles) | Linux monitor mode (no patch) | [arXiv](https://arxiv.org/pdf/2309.04408) |
| **openwifi** *(Tier 5 outlier)* | Zynq FPGA + AD9361/AD9364 | 11a/g/n, 20 MHz | per-SC (soft PHY) | Linux / Zynq SoC | [github](https://github.com/open-sdr/openwifi) |
| **CSIKit** *(universal parser)* | reads all of the above | — | format-agnostic | Python (cross-platform) | [github](https://github.com/Gi-z/CSIKit) |

**Quick pick:** cheapest/standalone → ESP32 Toolkit; best on ubiquitous hardware → Nexmon CSI on a Pi 4 (43455c0) or RT-AC86U (4366c0, 4×4); highest-fidelity 11n → Atheros CSI Tool; easy Wi-Fi 6/6E → FeitCSI; research platform / many NICs / 6 GHz → PicoScenes; no-firmware-patch/compliance-safe → Wi-BFI beamforming-feedback sniffing; you own the PHY → openwifi.

---

## B. Genuine SDRs — the tier-5 yardstick

*device → freq range → instantaneous BW → TX? → approx price → link.* These sit **above** the ladder as the reference datum, not as contestants on it. Full front-end detail, resolution, and duplex notes on [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

| Device | Freq range | Instant. BW | TX? | Full-duplex | Res. | Approx price | Link |
|---|---|---|---|---|---|---|---|
| RTL-SDR Blog V4 | ~0.5 kHz–1.7 GHz | ~2.4 MHz | No | — | 8-bit | ~$40 | [rtl-sdr.com](https://www.rtl-sdr.com/) |
| Airspy Mini | 24–1800 MHz | ~6 MHz | No | — | 12-bit | ~$100 | [airspy.com](https://airspy.com/) |
| Airspy R2 | 24–1800 MHz | ~9 MHz | No | — | 12-bit | ~$170 | [airspy.com](https://airspy.com/) |
| Airspy HF+ Discovery | 0.5 kHz–31 MHz, 60–260 MHz | ~0.77 MHz | No | — | high-DR | ~$170 | [airspy.com](https://airspy.com/airspy-hf-discovery/) |
| SDRplay RSP1A | 1 kHz–2 GHz | up to 10 MHz | No | — | 14-bit | ~$120 | [sdrplay.com](https://www.sdrplay.com/rsp1a/) |
| SDRplay RSPdx-R2 | 1 kHz–2 GHz | up to 10 MHz | No | — | 14-bit | ~$290 | [sdrplay.com](https://www.sdrplay.com/rspdx/) |
| **HackRF One** | 1 MHz–6 GHz | 20 MHz | **Yes** | No (half) | 8-bit | ~$300 | [greatscottgadgets.com](https://greatscottgadgets.com/hackrf/) |
| **ADALM-PLUTO** | 325 MHz–3.8 GHz (hack: 70–6000) | up to 20 MHz | **Yes** | Yes (1×1) | 12-bit | ~$150–230 | [wiki.analog.com](https://wiki.analog.com/university/tools/pluto) |
| LimeSDR Mini | 10 MHz–3.5 GHz | up to 30.72 MHz | Yes | Yes (1×1) | 12-bit | ~$180 | [limemicro.com](https://limemicro.com/) |
| LimeSDR (full) | 100 kHz–3.8 GHz | up to 61.44 MHz | Yes | Yes (2×2) | 12-bit | ~$300+ | [limemicro.com](https://limemicro.com/) |
| bladeRF 2.0 xA4 | 47 MHz–6 GHz | up to 56 MHz | Yes | Yes (2×2) | 12-bit | ~$540 | [nuand.com](https://www.nuand.com/bladerf-2-0-micro/) |
| bladeRF 2.0 xA9 | 47 MHz–6 GHz | up to 56 MHz | Yes | Yes (2×2) | 12-bit | ~$780 | [nuand.com](https://www.nuand.com/product/bladerf-xa9/) |
| USRP B200 | 70 MHz–6 GHz | 56 MHz | Yes | Yes (1×1) | 12-bit | ~$1,200 | [ettus.com](https://www.ettus.com/all-products/ub200-kit/) |
| USRP B210 | 70 MHz–6 GHz | 56 MHz | Yes | Yes (2×2) | 12-bit | ~$1,700 | [ettus.com](https://www.ettus.com/all-products/ub210-kit/) |
| USRP N310 | 10 MHz–6 GHz | 100 MHz/ch | Yes | Yes (4×4) | 14-bit | ~$10,000+ | [ettus.com](https://kb.ettus.com/) |

*Prices are ballpark 2026 street prices for genuine units; treat as order-of-magnitude.*

**The framing that matters:** for *generic* "receive/transmit an arbitrary signal at an arbitrary frequency," a $40 RTL-SDR or $150 Pluto beats every Wi-Fi chip in this catalog. But on the *sensing* axis — dense native CSI across 160 MHz at 60 GHz, on hardware already installed in the target's device at $0 marginal cost — unlocked Wi-Fi silicon does things no affordable true SDR does. See [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

---

## C. Go-to monitor / injection dongles (Tier 1)

*dongle → chip → driver → 5 GHz? → notes.* Prefer **in-tree mac80211** so a kernel update does not brick you. Monitor is near-solved on any mac80211 driver; **injection is the differentiator** — always confirm with `aireplay-ng --test`. Full driver matrix and Realtek out-of-tree maze on [monitor-injection-support.md](../chips/monitor-injection-support.md); part numbers on [../chips/hardware-index.md](../chips/hardware-index.md).

| Dongle / board | Chip | Driver | 5 GHz? | Notes |
|---|---|---|---|---|
| **Alfa AWUS036NHA** | Atheros AR9271 | `ath9k_htc` (in-tree) | ✘ | **The 2.4 GHz reference.** Best injection ever shipped in USB; honours rate/retry. Needs `htc_9271.fw`. |
| TP-Link **TL-WN722N v1** | Atheros AR9271 | `ath9k_htc` (in-tree) | ✘ | Same chip as above — **but only v1.** v2/v3 are RTL8188EUS (check FCC ID / box). |
| **Alfa AWUS036ACM** | MediaTek MT7612U | `mt76x2u` (in-tree) | ✔ | **Default 2.4+5 GHz recommendation.** In-tree, monitor + injection + 5 GHz, no DKMS. |
| MT7921AU adapter | MediaTek MT7921AU | `mt7921u` (in-tree) | ✔ | **Modern do-everything Wi-Fi 6 USB.** In-tree, monitor + injection, morrownr-approved. |
| PCIe/M.2 card | MediaTek MT7915 | `mt7915e` (in-tree) | ✔ | Wi-Fi 6 AP silicon; strong monitor/injection for lab work. |
| **Alfa AWUS036ACH** | Realtek RTL8812AU | aircrack-ng `rtl8812au` (OOT) | ✔ | Injects well, dual-band — but **repo deprecated**, DKMS breakage on new kernels. Keep if owned; don't buy new for this. |
| various | Realtek RTL8814AU | aircrack-ng `rtl8812au` (OOT) | ✔ | 4×4; same OOT/deprecation caveats. |
| **Alfa AWUS036H** | Realtek RTL8187L | `rtl8187` (in-tree) | ✘ | The *original* aircrack dongle. 2.4-only, legacy. |
| Intel AX210 M.2 | Intel AX210 | `iwlwifi` (in-tree) | ✔ | **Capture only.** Excellent monitor incl. 6 GHz; injection unreliable (firmware rewrites fields). |
| RT5572 dongle | Ralink RT5572 | `rt2800usb` (in-tree) | ▲ | Old, slow, but honest mac80211 injection. Dependable teaching reference. |
| Raspberry Pi (onboard) | Broadcom BCM43455c0 | `brcmfmac` + **nexmon** patch | ▲ | Not a dongle — firmware-patch path. Stock = no monitor/injection; nexmon adds both (and CSI). See [../projects/nexmon.md](../projects/nexmon.md). |

**Traps:** TL-WN722N — only **v1** is AR9271; Realtek **RTL8852** (Wi-Fi 6) USB — `rtw89` gives a working client but injection is essentially absent in 2025, don't buy for pen-testing; "Kali-compatible" listings are marketing — match the *chip*, not the label. **Any injection is a transmit — you are legally responsible for it.** See [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md).

---

## D. The SDR ladder — one canonical example per rung

Each database record carries a single **`sdr_tier`** (0–5, the highest rung reachable with public tooling) plus orthogonal **capability flags**. Full definitions on [../docs/taxonomy.md](../docs/taxonomy.md).

| Tier | Name | What you get | Canonical example |
|---|---|---|---|
| **0** | Black box | Stock firmware/driver; the chip just moves IP packets. The baseline every higher tier is measured from. | any locked commodity NIC (stock `brcmfmac` / `iwlwifi`) |
| **1** | Monitor + injection | Every 802.11 frame it hears (RFMON) + byte-exact frame transmit. Control at *frame* granularity. | Atheros **AR9271** / `ath9k` (also the open-firmware classics: OpenFWWF on BCM4318, carl9170fw on AR9170) |
| **2** | PHY telemetry / CSI | Per-frame complex channel estimate per OFDM subcarrier — amplitude **and** phase. Quasi-IQ in the frequency domain. | Intel **5300** (*Linux 802.11n CSI Tool*) |
| **3** | Spectral / raw-PHY scan | Raw PHY FFT bins whether or not a valid frame is present — a narrowband spectrum analyzer on the front-end. | Atheros **`ath9k` `spectral_scan`** (debugfs) |
| **4** | Arbitrary-waveform TX | Software authors a baseband IQ buffer and the chip transmits it — an arbitrary signal, not an 802.11 frame. The hard rung. | Broadcom **D11** core via **Nexmon** (raw-sample TX; cross-technology comms) |
| **5** | Open / soft PHY | The PHY/MAC is documented or open — genuinely yours to reprogram — or a genuine SDR *implementing* Wi-Fi. | **openwifi** (open Verilog PHY on Zynq + AD9361); genuine SDRs (USRP/HackRF/bladeRF/Lime/Pluto) as the yardstick |

**Ladder caveats:** a chip is scored at its *highest* reachable rung with public tooling, and higher rungs generally mean deeper firmware reversing — monitor/inject is often a driver flag, CSI needs a firmware patch to *export* channel estimates the PHY already computes, arbitrary TX needs the transmit datapath rewritten. Note two easy inflations this catalog rejects: (1) **open MAC firmware ≠ open PHY** — OpenFWWF/carl9170fw/open-ath9k-htc give Tier 1 + `open-firmware`, not Tier 5, because the PHY stays fixed silicon; (2) an **open *driver* over a closed blob** (ath10k, brcmfmac, iwlwifi, mt76) is never Tier 5 on openness alone. Only an open *PHY* (openwifi) or a genuine SDR earns Tier 5. See [../docs/verification-tier5-openfirmware.md](../docs/verification-tier5-openfirmware.md).

---

## See also

- CSI toolchains, in full: [../projects/csi-toolchains.md](../projects/csi-toolchains.md)
- Genuine-SDR yardstick, in full: [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)
- Monitor/injection driver matrix + buy-list: [monitor-injection-support.md](../chips/monitor-injection-support.md)
- Adapter part numbers & FCC IDs: [../chips/hardware-index.md](../chips/hardware-index.md)
- The ladder definition and capability flags: [../docs/taxonomy.md](../docs/taxonomy.md)
- Tier-5 openness audit: [../docs/verification-tier5-openfirmware.md](../docs/verification-tier5-openfirmware.md)
- RF safety & legal (read before any TX): [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md)
