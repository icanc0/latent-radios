# Cellular Baseband / Modem Chips (and Their Diagnostic Access)

> **Reality check up front.** A cellular modem is the *least* SDR-repurposable radio in your device. Unlike a Wi-Fi chip — where Nexmon-style firmware patching can reach the PHY and, in a few cases, raw IQ — a cellular baseband is a hard black box. The modem firmware is a signed, encrypted, vendor-controlled binary running on a locked security domain (a TrustZone-adjacent island, Qualcomm's "modem subsystem" / MPSS, Samsung's Shannon core, etc.). There is **no public path to arbitrary-waveform TX or raw-IQ RX** on any shipping consumer or IoT cellular modem. What you *can* sometimes get is **diagnostic / trace data**: decoded 2G/3G/4G/5G signaling frames (GSMTAP), RF measurement reports (RSRP/RSRQ/SINR, serving+neighbor cells), and layer-3 messages. That is a **measurement capability (Tier 0–1)**, not an SDR. This page catalogs the silicon honestly and points at the real tooling.

See also: [Cellular modem as SDR — the honest limits](cellular-basebands-as-sdrs.md) · [True SDR comparison](../docs/true-sdr-comparison.md) · [Taxonomy](../docs/taxonomy.md) · [RF safety & legal](../docs/rf-safety-and-legal.md).

## What "access" actually means for a modem

| Layer | Wi-Fi chip (for contrast) | Cellular modem | Tier |
|---|---|---|---|
| Arbitrary IQ TX | some (nexmon/openwifi-adjacent research) | **none, ever, publicly** | 4–5 vs — |
| Raw PHY / spectral | a few chips (spectral scan, CSI) | **none** | 2–3 vs — |
| OTA frame capture | monitor mode | **diag/GSMTAP** (signaling only, no IQ) | 1 |
| RF measurement reports | vendor debug | **diag/trace** (RSRP/RSRQ/SINR, cell IDs, timing advance) | 1 |
| Control / status | driver | **AT commands** (documented on many IoT modems) | 0–1 |
| Nothing exposed | — | most application-processor-integrated modems | 0 |

The single most important sentence on this page: **diagnostic capture is a decoded protocol/measurement stream, not baseband IQ.** You cannot demodulate an arbitrary signal, you cannot transmit an arbitrary waveform, and you cannot see samples below the modem's own protocol stack.

## The diagnostic tooling ecosystem (this is the "SDR-ish" part)

These tools turn a locked modem into a **cellular protocol sniffer / RF measurement probe** — genuinely useful for IMSI-catcher detection, coverage analysis, and protocol research, but firmly Tier 0–1.

| Tool | Targets | Transport | Output | Notes |
|---|---|---|---|---|
| **QCSuper** (P1sec) | Qualcomm basebands (2G/3G/4G, some 5G) | Qualcomm **DIAG/QCDM** over USB diag port, ADB, serial, TCP | GSMTAP **pcap** (RR/RRC/NAS, layer-3+) | Signaling frames, **not** IQ. [github.com/P1sec/QCSuper](https://github.com/P1sec/QCSuper) |
| **SCAT** (fgsect) | Qualcomm (`-t qc`), **Samsung Shannon** (`-t sec`), HiSilicon (`-t hisi`, experimental) | Vendor diag over USB | GSMTAP v2/v3 UDP → pcap | Control-plane messages only. [github.com/fgsect/scat](https://github.com/fgsect/scat) |
| **MobileInsight** | Qualcomm + some MediaTek | On-device diag log (rooted Android) | Decoded messages + Python API | Adds LTE/5G RRC/PHY *measurement* decode. [mobileinsight.net](http://www.mobileinsight.net) |
| **SnoopSnitch** (SRLabs) | Qualcomm (rooted Android) | Diag interface | IMSI-catcher / SS7 heuristics | Consumer-facing detector. [opensource.srlabs.de/projects/snoopsnitch](https://opensource.srlabs.de/projects/snoopsnitch) |
| **Nordic Cellular Monitor + Trace Collector** | nRF91 series | **Modem trace** (proprietary format over UART/RTT) | Decoded LTE-M/NB-IoT protocol + AT in Wireshark | Vendor-blessed trace; still no IQ. [docs.nordicsemi.com](https://docs.nordicsemi.com) |

**Access almost always requires:** a rooted/engineering device, a hidden USB "diag" composite interface (often behind a magic dialer code or `setprop`/`efs` tweak), and sometimes a signed diag-enable. On many modern phones the diag port is fused off in production. IoT modules (Quectel/Telit/Sierra/u-blox/Nordic) are far friendlier because they expose a documented AT/USB interface by design.

---

## Qualcomm — Snapdragon X-series modems & standalone MDM IoT modems

Qualcomm is the *reason the diag ecosystem exists*: the DIAG protocol is the most-reverse-engineered baseband debug interface on earth.

**Snapdragon X-series modem-RF (X12 → X75).** These are the cellular engines inside (or paired with) Snapdragon SoCs and in standalone M.2 cards: X12/X16/X20/X24 (LTE), **X50** (first 5G mmWave), X55/X60/X65/X70/**X75** (5G sub-6 + mmWave, X75 adds a dedicated AI tensor block for the modem). All run a closed MPSS firmware image. Diag exposure depends entirely on the host device: an engineering phone or a bare M.2 modem on a dev board typically exposes `/dev/ttyUSB*` diag → **QCSuper/SCAT** work; a locked retail phone usually does not. **Access = decoded signaling + RF measurement reports. No IQ.**

**Standalone MDM IoT modems** — the ones you actually solder onto a board (Quectel EC25, Telit, Sierra, Simcom modules are built around these):
- **MDM9207 / MDM9x07 / MDM9607** — LTE Cat-1 / Cat-M1 IoT workhorses; the classic "LTE-in-a-module" silicon.
- **MDM9x40** — LTE Cat-6 (carrier aggregation); **MDM9650 / MDM9x50** — Cat-9/gigabit-class, used in early 4G/5G hotspots and automotive.
- (Adjacent: **Qualcomm 9205 / MDM9206** LTE-M/NB-IoT modem — the low-power IoT part.)

These commonly expose a USB diag interface out of the box, so QCSuper/SCAT capture works reliably on dev hardware. Still Tier 1: you get GSMTAP + measurement, never IQ.

---

## MediaTek — integrated Dimensity/Helio modems & T-series IoT

MediaTek integrates its modem (the **"M-series" modem IP**, e.g. **M70/M80** 5G modem) directly into Dimensity/Helio SoCs; there is no separate part number you buy. Standalone IoT: **T750** and **T830** (5G RedCap / mmWave IoT platforms), plus the older **MT2625** (NB-IoT) and **MT2735** (RedCap). MediaTek diag ("**MTK ELT**"/catcher, `mtklog`) exists but the tooling is proprietary and closed; public reverse-engineering lags far behind Qualcomm. MobileInsight has *partial* MediaTek support. Treat MediaTek as **Tier 0 with reported diag** — the firmware is closed and the debug path is not openly documented. No IQ.

---

## Samsung — Exynos Modem (Shannon baseband)

Samsung's in-house baseband is codenamed **Shannon**. Modern parts: **Shannon 5123** (5G companion modem for Exynos 990 / used with some Snapdragon-less variants), **Shannon 5300** (integrated in Exynos 2200/2400). Historically Exynos Modem 5100 was Samsung's first 5G modem. The good news for researchers: **SCAT supports Shannon diag via `-t sec`**, and Shannon has been a heavy target of baseband security research (Comsecuris/TASZK "Shannon" work, over-the-air baseband exploitation). That makes Shannon **Tier 1** for signaling capture — but again, decoded messages, not IQ. Firmware is a closed signed image.

---

## Apple — C1 modem

The **Apple C1** is Apple's first in-house cellular modem, debuting in the **iPhone 16e (Feb 2025)**. It is sub-6 GHz 5G only (no mmWave at launch), built after Apple acquired Intel's smartphone-modem business (2019). It is **completely closed** — no diag interface, no public tooling, no documented AT surface for third parties. **Tier 0, black box.** Expect this to stay closed indefinitely given Apple's security posture.

---

## Intel — XMM (Infineon lineage)

Intel's XMM basebands (Infineon Wireless heritage) shipped mostly in Apple iPhones: **XMM7360** (iPhone 7-era LTE), **XMM7560** (iPhone XS/XR-era, also the M.2 modem in some laptops). **XMM7660** was Intel's planned 5G part, largely abandoned when Apple bought the unit. Notable open-ish angle: the PCIe variant of **XMM7360** used in laptops has a **community-reverse-engineered Linux driver** ([github.com/xmm7360/xmm7360-pci](https://github.com/xmm7360/xmm7360-pci)) that brings up control + data planes — but that is *networking control*, **not** baseband IQ or PHY. **Tier 0** for SDR purposes.

---

## Sequans — Monarch / Calliope (LTE-M / NB-IoT)

Sequans makes purpose-built cellular-IoT modems: **Monarch** (LTE-M/NB-IoT, e.g. GM01Q/Monarch-N chip), **Monarch 2** (GM02SP, adds GNSS), and **Calliope** (Cat-1). Interface is a well-documented **AT command** set plus a proprietary logging/trace tool for licensees. Firmware is closed. You get control + measurement AT responses (signal quality, cell info) — useful, but **Tier 0** (documented AT, no diag-grade OTA capture, no IQ). [sequans.com/products/monarch-2](https://www.sequans.com/products/monarch-2/)

---

## Nordic — nRF9160 / nRF9151 / nRF9161 (the most open of the bunch)

Nordic's **nRF91 SiP** family is the friendliest cellular silicon for hobbyists, and the closest thing to a "hackable" modem — but stay honest about *why*:
- **nRF9160** — LTE-M / NB-IoT + GPS SiP; Arm Cortex-M33 application core *plus* a separate, **signed closed-binary modem firmware**.
- **nRF9151 / nRF9161** — newer, smaller, add **DECT NR+** (a standalone 3GPP-adjacent PHY) alongside LTE-M/NB-IoT.

What's genuinely open: a **fully documented AT command set** (the "nRF91 AT Commands" reference), and a **vendor-supported modem trace** pipeline — `nrf_modem_lib` trace over UART/RTT, decoded by Nordic's **Cellular Monitor** app (nRF Connect for Desktop) and **Trace Collector** into Wireshark, exposing LTE protocol layers, AT, and IP. That's a real, legitimate **Tier 1 measurement** capability — arguably the cleanest diag/trace UX of any cellular part. But the modem itself is still a locked binary: **no PHY access, no IQ, no arbitrary TX.** GPS output is NMEA/PVT, not raw GNSS IQ. DECT NR+ on nRF9151 runs inside the same closed modem firmware. [nordicsemi.com/Products/nRF9160](https://www.nordicsemi.com/Products/nRF9160) · [nordicsemi.com/Products/nRF9151](https://www.nordicsemi.com/Products/nRF9151)

---

## u-blox — SARA cellular modules

u-blox **SARA** modules wrap third-party baseband (varies by series) behind u-blox firmware and a documented AT interface: **SARA-R5** (LTE-M/NB-IoT + GNSS), **SARA-R4** (LTE-M/NB-IoT), **SARA-N2** (NB-IoT), **SARA-G3** (2G). Access is documented AT + u-blox `m-center` diagnostics; firmware is closed. You get measurement and control, **Tier 0** for SDR purposes — no OTA frame capture, no IQ. [u-blox.com/en/product/sara-r5-series](https://www.u-blox.com/en/product/sara-r5-series)

---

## Bottom line

- **Nobody** ships a consumer/IoT cellular modem you can turn into an IQ-capable SDR. If you want cellular IQ, use a real SDR (USRP/LimeSDR/bladeRF) with srsRAN/OpenAirInterface — see [True SDR comparison](../docs/true-sdr-comparison.md).
- **Qualcomm and Samsung Shannon** give the best *measurement* access (diag → GSMTAP + RF reports) via QCSuper/SCAT/MobileInsight — **Tier 1**.
- **Nordic nRF91** gives the cleanest *vendor-supported* trace + open AT — **Tier 1**, and the best learning platform.
- **MediaTek, Intel XMM, Apple C1, Sequans, u-blox** are effectively **Tier 0** black boxes (documented AT ≠ SDR).
- Legal note: capturing another subscriber's traffic, or transmitting on licensed cellular bands, is illegal in most jurisdictions even where the hardware allows it. Diag capture of *your own* device on *your own* SIM is the safe research posture. See [RF safety & legal](../docs/rf-safety-and-legal.md).

## References

- QCSuper (Qualcomm DIAG → GSMTAP pcap): https://github.com/P1sec/QCSuper
- SCAT (Qualcomm/Samsung Shannon/HiSilicon diag → GSMTAP): https://github.com/fgsect/scat
- MobileInsight: http://www.mobileinsight.net
- SnoopSnitch (SRLabs): https://opensource.srlabs.de/projects/snoopsnitch
- Nordic nRF Connect / Cellular Monitor & modem trace docs: https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/test_and_optimize/testing/modem_trace.html
- Nordic nRF9160 product page: https://www.nordicsemi.com/Products/nRF9160
- Nordic nRF9151 product page: https://www.nordicsemi.com/Products/nRF9151
- Qualcomm Snapdragon X75 modem-RF: https://www.qualcomm.com/products/technology/modems/snapdragon-x75-5g-modem-rf-system
- xmm7360-pci (reverse-engineered Intel XMM7360 PCIe driver): https://github.com/xmm7360/xmm7360-pci
- Sequans Monarch 2: https://www.sequans.com/products/monarch-2/
- u-blox SARA-R5: https://www.u-blox.com/en/product/sara-r5-series
- Apple C1 (iPhone 16e newsroom, Feb 2025): https://www.apple.com/newsroom/2025/02/apple-introduces-iphone-16e-a-powerful-new-member-of-the-iphone-16-family/
