# Cellular basebands as SDRs: what is (and mostly is not) possible

> **Honest verdict up front:** You cannot turn the cellular modem inside your phone or a USB LTE/5G stick into an arbitrary-IQ software-defined radio. The RF-to-bits pipeline lives in a **locked, signed DSP** you do not control. What you *can* extract is **decoded/measured data** through vendor diagnostic protocols — cellular Layer-3 / RRC / NAS signaling and a handful of PHY measurements — which lands at **Tier 0–1** (occasionally Tier 2 for richer measurement reports). If you want to actually *transmit and receive cellular waveforms in software*, you do it on a **real SDR** (USRP / LimeSDR / bladeRF / AntSDR) running a software stack (osmocom, srsRAN, OpenAirInterface) — the phone modem is not part of that path at all.

This page draws the SDR-vs-modem line as sharply as possible, then catalogs the three legitimate things you can do with a cellular baseband: **diagnostic capture**, **software-radio cellular stacks**, and **baseband firmware reverse engineering**.

Related: [true-SDR comparison](../docs/true-sdr-comparison.md) · [cellular baseband chips](../chips/cellular-basebands.md) · [GNU Radio OOT modules](../projects/gnuradio-oot-modules.md)

---

## 1. Why a cellular baseband is not an SDR

A Wi-Fi chip earns a place in this catalog because researchers have pried open its PHY: Nexmon patches Broadcom firmware for CSI, Atheros exposes spectral scan, ESP32 will do raw 802.11 TX. Cellular basebands are a categorically harder target, and for practical purposes the door is welded shut:

- **The DSP is signed and locked.** Modern basebands (Qualcomm Hexagon-based modem subsystems, Samsung/Exynos "Shannon" Cortex-R cores, MediaTek modem DSPs) boot only cryptographically signed firmware. There is no supported, and essentially no unsupported, path to load your own PHY code that streams raw IQ. Secure boot, MPU/XPU memory protection, and per-SKU signing keys all stand in the way.
- **No IQ tap is exposed.** Even fully rooted, the interfaces the modem offers the application processor are *high-level*: an AT command channel, a QMI/IPC control channel, a packet data path, and a **diagnostic (DIAG) channel**. None of them is "give me the ADC samples." The RF transceiver and the digital front-end are private to the modem.
- **Regulatory + carrier lockdown.** Basebands are type-approved as a unit. Arbitrary transmit would violate the device's certification, and the firmware is deliberately built to make it impossible. This is the opposite of an SDR, whose entire value proposition is arbitrary transmit.
- **What you get instead is telemetry.** The one genuinely useful escape hatch is the vendor diagnostic protocol, which was built for engineers to debug the stack. It emits **already-decoded** protocol messages and **measurement reports**, not signal. That is valuable — but it is monitoring, not synthesis.

So on the [SDR ladder](../docs/taxonomy.md), a phone baseband sits at **Tier 0** as a black box and climbs to **Tier 1** only in the narrow sense that DIAG gives you a passive monitor of decoded cellular control-plane traffic. It never reaches raw-IQ (Tier 4) or open-PHY (Tier 5). Don't let anyone tell you otherwise.

---

## 2. What you CAN do: diagnostic (DIAG) capture

Every major baseband vendor ships an internal diagnostic protocol. It is the single most productive thing you can do with the modem you already own. Rooted (or diag-enabled) phones expose a serial/USB endpoint speaking this protocol; tools drive it, subscribe to log message IDs, and translate the results into **GSMTAP** packets you can open in Wireshark.

### 2.1 Qualcomm DIAG (a.k.a. QCDM / DM — "Diagnostic Monitor")

The best-documented of the lot. The modem exposes a `/dev/diag` character device (or a USB diagnostic interface, PID switching required). You send command frames; it streams **log packets** identified by numeric log codes.

**What you can pull:**
- **Control-plane signaling**, decoded per RAT: 2G (GSM L3), 2.5G (GPRS/EDGE L2 MAC-RLC), 3G (UMTS RRC, optional SIB reassembly), 4G (LTE RRC + optional decrypted NAS), and *limited* 5G NR signaling on some models.
- **PHY / measurement telemetry**: serving-cell and neighbor-cell measurements (RSRP/RSRQ/RSSI/SINR), cell IDs, EARFCN/UARFCN, timing advance, and similar — the numbers the modem reports, not the samples behind them.
- **Device internals** (with QCSuper): firmware/version info, **EFS** (embedded filesystem) browsing, and memory dumps on permissive builds.

**Tools:**

| Tool | Source | Notes |
|---|---|---|
| **QCSuper** | P1Sec, [github.com/P1sec/QCSuper](https://github.com/P1sec/QCSuper) | Open source (Python). Captures 2G/3G/4G (+partial 5G) frames to **PCAP with GSMTAP headers**, live-streams to Wireshark, browses EFS, dumps memory. Works over ADB on rooted phones or against USB modems/dongles exposing a diag port. |
| **SCAT** (Signaling Collection and Analysis Tool) | fgsect, [github.com/fgsect/scat](https://github.com/fgsect/scat) | Open source. Parses **Qualcomm (`-t qc`) and Samsung (`-t sec`)** diag, emits **GSMTAP v2/v3** (control plane → UDP 4729, user plane → 47290). Experimental HiSilicon (`-t hisi`, dump only). Backed by Hong et al., IEEE 2018. |
| **MobileInsight** | UCLA WiNG, [github.com/mobile-insight/mobileinsight-core](https://github.com/mobile-insight/mobileinsight-core) | Open source, on-device Android app + desktop. Parses **Qualcomm and MediaTek** diag; exposes cross-layer analyzers (RRC, NAS, PHY measurements) with a Python API. |
| **QXDM / QCAT** | Qualcomm (proprietary, NDA/licensed) | The vendor tools the above reimplement. QXDM captures live; QCAT post-processes `.isf`/`.dlf` logs. Gold standard for coverage but closed and gated. |

**Representative commands:**
```bash
# QCSuper: live-decode a rooted phone's cellular signaling into Wireshark
python3 qcsuper.py --adb --wireshark-live

# QCSuper: dump to a GSMTAP pcap you can open later
python3 qcsuper.py --adb --pcap-dump /tmp/lte.pcap

# SCAT: Qualcomm diag over a USB serial diag port -> pcap
scat -t qc -s /dev/ttyUSB0 -F /tmp/qc.pcap

# SCAT: Samsung Shannon diag over an ACM diag interface
scat -t sec -s /dev/ttyACM0 -F /tmp/sec.pcap
```

**Honest tier:** decoded control-plane monitoring + measurement reports = **Tier 1** (passive monitor of decoded frames). It is *not* CSI-grade raw PHY, and it is emphatically not IQ. Where a model streams rich raw measurement structures it can feel Tier-2-ish, but you are still consuming the modem's decisions, not the signal.

### 2.2 Samsung / Exynos "Shannon" diag

Samsung's in-house Shannon modems speak their own diagnostic dialect. **SCAT `-t sec`** decodes it to GSMTAP. This is the practical capture path on Exynos-based Galaxy devices (the ones that don't ship a Qualcomm modem).

### 2.3 MediaTek diag

MediaTek modems expose diagnostic logging through vendor engineering channels (the "catcher" / ELT / DebugLogger tooling internally; `MTKLogger`/`mtklog` on retail builds). Open tooling coverage is thinner than Qualcomm's, but **MobileInsight** parses MediaTek diag alongside Qualcomm, making it the most accessible open route for MTK signaling capture. Expect less completeness and more per-chipset variation than the Qualcomm path.

### 2.4 What DIAG does *not* give you

- No IQ samples, no ability to transmit arbitrary waveforms.
- No open PHY: you cannot change modulation, insert a custom preamble, or run a passive-radar experiment off the modem.
- Coverage is model- and firmware-dependent, and 5G NR support in open tools lags the hardware.

---

## 3. What "cellular as an SDR" actually means: software stacks on real SDRs

When people say "I'm running a cellular network in software," they are **not** using a phone modem. They are running a full L1/L2/L3 stack on a general-purpose CPU and pushing/pulling IQ through a **genuine SDR**. This is the real intersection of "cellular" and "SDR," and it belongs in this catalog as a pointer, not as a baseband trick.

| Stack | Standards | Real SDR front-ends | Source |
|---|---|---|---|
| **Osmocom** (OsmoTRX + OsmoBTS + OsmoBSC/OsmoMSC) | GSM/GPRS (2G) | USRP (via **OsmoTRX-UHD**), LimeSDR (**OsmoTRX-LMS**), bladeRF | [osmocom.org/projects/osmotrx](https://osmocom.org/projects/osmotrx), [osmobts](https://osmocom.org/projects/osmobts) |
| **srsRAN** (srsRAN 4G; srsRAN Project 5g) | LTE + 5G NR (gNB/CU/DU, plus srsUE) | USRP B2x0/N3xx, LimeSDR, AntSDR, other UHD/SoapySDR radios | [github.com/srsran/srsRAN_4G](https://github.com/srsran/srsRAN_4G), [github.com/srsran/srsRAN_Project](https://github.com/srsran/srsRAN_Project) *(archived Jun 2026; continues as **OCUDU**, [gitlab.com/ocudu/ocudu](https://gitlab.com/ocudu/ocudu))* |
| **OpenAirInterface (OAI)** | LTE + 5G NR (gNB/eNB, nrUE, and core CN) | USRP B210/N300/N310, AW2S, some SDR boards via UHD | [openairinterface.org](https://openairinterface.org), [gitlab.eurecom.fr/oai/openairinterface5g](https://gitlab.eurecom.fr/oai/openairinterface5g) |

**Key distinction:** in all three the **PHY runs in your code** on the host CPU (or an accelerator), and the SDR is a dumb-ish RF+ADC/DAC pipe. That is the exact inverse of a phone modem, where the PHY is a sealed DSP and the host only sees decoded results. If your goal is "software-defined cellular," buy an SDR and run one of these — do not try to jailbreak a modem into it.

```bash
# Osmocom 2G: transceiver bridges the stack to a USRP; osmo-bts-trx runs the BTS L1
osmo-trx-uhd -c osmo-trx-uhd.cfg
osmo-bts-trx -c osmo-bts.cfg

# srsRAN 5G gNB against a USRP B210
sudo gnb -c gnb_uhd.yaml
```

For pairing these stacks with GNU Radio-based tooling and OOT blocks, see [../projects/gnuradio-oot-modules.md](../projects/gnuradio-oot-modules.md).

---

## 4. The baseband reverse-engineering research line

There is a rich, legitimate research field around basebands — but note its **goal is security analysis (finding memory-corruption bugs, understanding the stack), not converting the modem into an SDR.** These efforts prove how locked the DSP is precisely by how hard they have to work to peer inside it.

- **Comsecuris "Breaking Band" / shannonRE** (RECON 2016) — the seminal public teardown of Samsung's Shannon baseband (Galaxy S6): unpacking modem images, live memory dumps, IDA Pro helpers for function/task discovery and MPU-table parsing. Slides: [comsecuris.com/slides/recon2016-breaking_band.pdf](https://comsecuris.com/slides/recon2016-breaking_band.pdf); tooling: [github.com/Comsecuris/shannonRE](https://github.com/Comsecuris/shannonRE).
- **BaseSpec** (NDSS 2021, KAIST) — comparative analysis of baseband binaries against the 3GPP L3 specification to surface mismatches and bugs. [ndss-symposium.org/ndss-paper/basespec-...](https://www.ndss-symposium.org/ndss-paper/basespec-comparative-analysis-of-baseband-software-and-cellular-specifications-for-l3-protocols/).
- **FirmWire** (NDSS 2022) — a full-system **emulation** platform for **Samsung (Shannon) and MediaTek** baseband firmware, enabling fuzzing, debugging, and root-cause analysis without the phone. Authors incl. Grant Hernandez, Marius Muench, Dominik Maier. [github.com/FirmWire/FirmWire](https://github.com/FirmWire/FirmWire) · [paper](https://www.ndss-symposium.org/ndss-paper/firmwire-transparent-dynamic-analysis-for-cellular-baseband-firmware/).
- **Google Project Zero — Exynos baseband RCEs** (2023) — internet-to-baseband remote code execution in Samsung Exynos modems, a high-profile demonstration of attack surface (VoLTE/IMS path). [googleprojectzero.blogspot.com/2023/03/...](https://googleprojectzero.blogspot.com/2023/03/multiple-internet-to-baseband-remote-rce.html).
- **"Attacking phone basebands"** talk/tooling lineage — the broader conference body (Hardwear.io, OffensiveCon, Black Hat) that FirmWire and the Shannon/MediaTek RE work feed into.

**Why it matters here:** an exploited baseband can be made to run attacker code on the *modem CPU* — but that still does not hand you the DSP or an IQ tap. Even a fully compromised baseband is not an SDR; it is a compromised modem. The RE line is your best window into *how* the PHY is walled off, and confirms the Section 1 verdict rather than overturning it.

---

## 5. SDR vs. modem — the crisp table

| | Phone/USB cellular **modem** | Real **SDR** (USRP/LimeSDR/…) |
|---|---|---|
| Where the PHY lives | Signed, locked DSP inside the modem | Your software on the host CPU |
| IQ sample access | **None** | Full raw IQ TX + RX |
| Arbitrary transmit | **Impossible** (signed FW, type approval) | Yes (within legal limits) |
| What the host sees | Decoded frames + measurements (DIAG) | ADC/DAC samples |
| Best you can do | Passive signaling/measurement capture | Run a whole cellular network |
| Catalog tier | **0–1** (Tier 2 at the very most, for rich measurement reports) | **5** (genuine SDR) |
| Example tooling | QCSuper, SCAT, MobileInsight, QXDM | osmocom, srsRAN/OCUDU, OpenAirInterface |

---

## 6. Tier summary

| Capability | Path | Tier | Status |
|---|---|---|---|
| Black-box modem, no access | — | 0 | verified |
| Qualcomm DIAG signaling + measurement capture | QCSuper / SCAT / MobileInsight | 1 | verified |
| Samsung Shannon diag capture | SCAT `-t sec` | 1 | verified |
| MediaTek diag capture | MobileInsight | 1 | reported |
| Rich raw measurement structures (model-specific) | QXDM/QCAT, some DIAG logs | ~2 | reported |
| Arbitrary-IQ TX/RX from a phone baseband | — | **not achievable** | theoretical / no |
| Software cellular PHY (the real "cellular SDR") | srsRAN / OAI / osmocom **on a real SDR** | 5 (of the SDR, not the modem) | verified |

---

## References

- QCSuper (P1Sec) — https://github.com/P1sec/QCSuper
- SCAT (fgsect) — https://github.com/fgsect/scat
- MobileInsight (UCLA WiNG) — https://github.com/mobile-insight/mobileinsight-core · http://www.mobileinsight.net
- srsRAN 4G — https://github.com/srsran/srsRAN_4G
- srsRAN Project (5G, archived Jun 2026) — https://github.com/srsran/srsRAN_Project → OCUDU https://gitlab.com/ocudu/ocudu
- OpenAirInterface — https://openairinterface.org · https://gitlab.eurecom.fr/oai/openairinterface5g
- Osmocom OsmoTRX — https://osmocom.org/projects/osmotrx · OsmoBTS https://osmocom.org/projects/osmobts
- Comsecuris "Breaking Band" (RECON 2016) — https://comsecuris.com/slides/recon2016-breaking_band.pdf · shannonRE https://github.com/Comsecuris/shannonRE
- BaseSpec (NDSS 2021) — https://www.ndss-symposium.org/ndss-paper/basespec-comparative-analysis-of-baseband-software-and-cellular-specifications-for-l3-protocols/
- FirmWire (NDSS 2022) — https://github.com/FirmWire/FirmWire · https://www.ndss-symposium.org/ndss-paper/firmwire-transparent-dynamic-analysis-for-cellular-baseband-firmware/
- Google Project Zero, Exynos internet-to-baseband RCE (2023) — https://googleprojectzero.blogspot.com/2023/03/multiple-internet-to-baseband-remote-rce.html
