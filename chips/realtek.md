# Realtek Wi-Fi — Monitor/Injection Workhorses & the Ameba CSI Outlier

Realtek's USB Wi-Fi silicon is the backbone of the cheap pentest-dongle market. These
parts rarely climb high up the [SDR ladder](../docs/glossary.md) — almost none expose
CSI or spectral bins the way Atheros/Broadcom/Intel do — but they earn their place
because the community RE effort here is aimed squarely at **rung 1: raw 802.11 monitor +
frame injection**, and a handful of Realtek USB chips (8187L, 8812AU, 8814AU) are the
single most widely-deployed injection adapters on Earth. Kali/Parrot ship with the
drivers, `airmon-ng`/`aircrack-ng` target them by name, and Alfa built an entire product
line around them.

The one genuine higher-rung exception is **not** a USB dongle at all: the **Ameba**
Wi-Fi MCU family (RTL8720DN and cousins) ships a Realtek-blessed **Wi-Fi CSI API** in its
RTOS SDK, exposing per-subcarrier I/Q — a real **rung 2** capability with open,
documented firmware. That makes Ameba the SDR-interesting Realtek target.

## How Realtek climbs the ladder (and where it stalls)

- **Rung 1 (monitor + injection)** — the whole story for the USB dongles. Realtek's
  vendor drivers are closed and monitor-hostile; the community reverse-engineered/patched
  them into the `aircrack-ng/*` and `morrownr/*` out-of-tree DKMS drivers that add
  `type monitor` + injection. This is a **host-driver** hack, not a firmware hack — the
  MAC/baseband already supports promiscuous RX and raw TX; the vendor driver just refused
  to expose it. That's why Realtek injection "just works" once you load the right module.
- **Rung 2 (CSI)** — only on the **Ameba RTOS MCUs** via the official CSI API. On the USB
  dongles, per-subcarrier CSI is **not** available in any maintained public tool (a few
  academic papers report scraping report-descriptor CSI off Realtek MACs, but nothing
  reproducible ships). Treat USB-Realtek CSI as *reported/theoretical*.
- **Rung 3+ (spectral / raw-IQ / arbitrary waveform)** — **no** public path on any
  Realtek Wi-Fi part. There is no Realtek analogue to Atheros `spectral_scan` or the
  Nexmon IQ-buffer TX. The firmware is closed and essentially un-reversed by the
  community.

## Firmware & on-chip cores

Realtek USB Wi-Fi MACs carry a small **8051-class microcontroller** ("RTL8051"-style
core) running a closed firmware blob (`rtlwifi`/`rtl8xxxu` fetch these from
`/lib/firmware`), alongside a hardware MAC and a fixed-function OFDM/DSSS baseband. The
firmware handles power-save, rate control, and TX/RX descriptor housekeeping — it is
**not** a soft-PHY. Community RE of these blobs is almost nonexistent (unlike Broadcom's
Nexmon or Atheros' `ath9k`): people patch the *Linux driver*, not the *chip firmware*.
See [../docs/firmware-reversing.md](../docs/firmware-reversing.md) for the general
methodology and why Realtek is a hard/low-payoff RE target.

The **Ameba** MCUs are the opposite: RTL8720DN (AmebaD) is a dual-core **Arm Cortex-M4F
(KM4, 200 MHz) + Cortex-M0 (KM0, 20 MHz)** SoC with an **open, documented FreeRTOS SDK**,
Arduino core, and the CSI API in the vendor docs. Newer Ameba parts (RTL8721/8730/8735)
add more CSI-capable cores.

## Summary table

| Chip | Bands | Std | Go-to driver | Tier | Caps | Firmware openness | Iconic hardware |
|---|---|---|---|---|---|---|---|
| RTL8187 / 8187L | 2.4 | b/g | in-kernel `rtl8187` (mac80211) | 1 | monitor, injection | closed (thin ucode) | Alfa AWUS036H |
| RTL8188EU/EUS/CUS | 2.4 | n | `aircrack-ng/rtl8188eus`, `r8188eu`/`rtl8xxxu` | 1 | monitor, injection | closed (8051) | Alfa AWUS036NEH, TL-WN722N v2/v3 |
| RTL8192CU / EU | 2.4 | n | `rtl8192cu`/`rtl8xxxu` | 1 | monitor(partial), injection | closed (8051) | many OEM dongles |
| RTL8188FU / FTV | 2.4 | n | `rtl8188fu` (out-of-tree) | 1 | monitor(partial), injection | closed (8051) | cheap nano dongles |
| RTL8811AU | 2.4/5 | ac (1×1) | `aircrack-ng/rtl8812au` | 1 | monitor, injection | closed (8051) | Alfa AWUS036AC |
| RTL8812AU | 2.4/5 | ac (2×2) | `aircrack-ng/rtl8812au` (morrownr) | 1 | monitor, injection | closed (8051) | **Alfa AWUS036ACH / AC1200** |
| RTL8814AU | 2.4/5 | ac (4×4) | `aircrack-ng/rtl8812au`, `nicshaca/rtl8814au` | 1 | monitor, injection | closed (8051) | **Alfa AWUS1900** |
| RTL8812BU / 8822BU | 2.4/5 | ac (2×2) | `morrownr/88x2bu-20210702` | 1 | monitor(partial), injection | closed (8051) | Alfa AWUS036ACU, many |
| RTL8811CU/8821CU(H)/8731AU | 2.4/5 | ac (1×1) | `morrownr/8821cu-20210916` | 1 | monitor, injection | closed (8051) | Alfa AWUS036ACS, USB nano |
| RTL8821AU | 2.4/5 | ac (1×1) | `aircrack-ng/rtl8812au` | 1 | monitor, injection | closed (8051) | combo dongles |
| RTL8723AU/BU/DU | 2.4 | n +BT | `rtl8723au`/`rtl8xxxu`, `8723bu` | 1 | monitor(partial), injection | closed (8051) | combo Wi-Fi+BT |
| **RTL8720DN (AmebaD)** | 2.4/5 | b/g/n +BLE | Ameba RTOS SDK / Arduino | **2** | **csi**, monitor, open-firmware | **documented** (Cortex-M4+M0) | BW16, Rtlduino |

## Chip-by-chip

### RTL8187 / RTL8187L — the original injection legend

The USB part that made "Wi-Fi hacking" mainstream in the BackTrack era. `rtl8187` is a
**mainline mac80211 driver**, so monitor + injection work out of the box on any modern
kernel — no out-of-tree build. 2.4 GHz 802.11b/g only, but high TX power (~27 dBm on the
8187L) made the **Alfa AWUS036H** the definitive long-range injection card for a decade.
The chip is nearly a "soft MAC" from the host's view (thin on-chip ucode), which is why
injection was trivial to support. Still perfectly usable today for WEP/WPA-handshake work,
just band-limited. **Tier 1, verified.**
Refs: [aircrack-ng r8187 wiki](https://www.aircrack-ng.org/doku.php?id=r8187).

### RTL8188EU / EUS / CUS — the cheap monitor default

Ubiquitous nano/USB dongle silicon. Mainline offers `r8188eu` (older, monitor-flaky) and
`rtl8xxxu`; the community answer is **`aircrack-ng/rtl8188eus`**, the reference DKMS driver
adding solid monitor + injection (and it's what NetHunter/Kali docs point to). Found in the
**Alfa AWUS036NEH/NEHW** and — importantly — the **TP-Link TL-WN722N v2/v3** (v1 was
Atheros AR9271; v2/v3 silently switched to RTL8188EUS, which is why so many tutorials
break). 2.4 GHz 802.11n 1×1. **Tier 1, verified.**
Refs: [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus).

### RTL8192CU / RTL8192EU — 802.11n workhorse

Very common OEM 2.4 GHz n dongle. Mainline `rtl8192cu` and the reverse-engineered
`rtl8xxxu` cover it; monitor works (sometimes partial/injection-limited depending on
driver). Not a first-choice pentest card today but everywhere in the wild. **Tier 1,
verified** (monitor), injection quality driver-dependent.
Refs: [rtl8xxxu kernel driver](https://github.com/torvalds/linux/tree/master/drivers/net/wireless/realtek/rtl8xxxu).

### RTL8188FU / RTL8188FTV — nano n dongle

Later cheap 2.4 GHz n part. No mainline support for years; monitor/injection via
out-of-tree `rtl8188fu` forks (kelebek333 / others). Monitor is usable but flakier than
8188EUS; treat injection as partial. **Tier 1, reported→verified** depending on fork.
Refs: [rtl8188fu driver](https://github.com/kelebek333/rtl8188fu).

### RTL8811AU / RTL8812AU / RTL8821AU — the AC pentest standard

The **`aircrack-ng/rtl8812au`** driver (astsam → morrownr lineage) is *the* out-of-tree
Realtek driver: monitor + injection on dual-band 802.11ac. 8811AU = 1×1, **8812AU = 2×2**
(the default), 8821AU = 1×1 AC+combo. The **Alfa AWUS036ACH / AWUS036AC / "AC1200"** built
this chip into the standard modern injection dongle — 2.4 **and** 5 GHz, external
antennas, wide channel support. If a tutorial says "buy an Alfa for 5 GHz," it means an
8812AU. **Tier 1, verified.**
Refs: [aircrack-ng/rtl8812au](https://github.com/aircrack-ng/rtl8812au).

### RTL8814AU — 4×4 flagship (Alfa AWUS1900)

Realtek's top 802.11ac USB part: **4×4 MIMO**, dual-band, in the **Alfa AWUS1900** (the
four-antenna brick) and **AWUS036ACHM**-class adapters. Supported by the same
`aircrack-ng/rtl8812au` unified driver (build with 8814 support) and dedicated
**`nicshaca/rtl8814au`** fork (adds AP + jammer modes). Note: some distro `rtl88xxau-dkms`
packages *dropped* 8814AU, so a dedicated build is often needed. Highest RX gain / most
antennas of the Realtek line — but still just **Tier 1** (no CSI/spectral). **Verified.**
Refs: [nicshaca/rtl8814au](https://github.com/nicshaca/rtl8814au),
[aircrack-ng/rtl8812au](https://github.com/aircrack-ng/rtl8812au).

### RTL8812BU / RTL8822BU — the "B" generation

Newer 2×2 AC USB silicon (8822BU is the combo Wi-Fi+BT sibling). Driver is
**`morrownr/88x2bu-20210702`** (fork of RinCat's RTL88x2BU). Monitor works; **injection is
partial/less reliable** than 8812AU — morrownr's own docs steer pentesters back to
8812AU/8821CU for serious injection. Found in later Alfa/Comfast/generic dongles. **Tier
1, reported→verified** (monitor solid, injection caveated).
Refs: [morrownr/88x2bu-20210702](https://github.com/morrownr/88x2bu-20210702),
[RinCat/RTL88x2BU-Linux-Driver](https://github.com/RinCat/RTL88x2BU-Linux-Driver).

### RTL8811CU / RTL8821CU / RTL8821CUH / RTL8731AU — the "C" injection pick

Single-stream dual-band AC. Driver **`morrownr/8821cu-20210916`** gives clean monitor +
injection and is morrownr's *recommended* small/cheap injection adapter. Very common in
USB-nano AC dongles. **Tier 1, verified.**
Refs: [morrownr/8821cu-20210916](https://github.com/morrownr/8821cu-20210916).

### RTL8723AU / BU / DU — Wi-Fi + Bluetooth combo

2.4 GHz n + BT combo parts (common on SBCs/laptops). Mainline `rtl8xxxu` / `rtl8723bs`
handle station mode; monitor is possible but injection support is weak and driver-
dependent. Catalogued for completeness, not a pentest choice. **Tier 1, reported.**
Refs: [rtl8xxxu kernel driver](https://github.com/torvalds/linux/tree/master/drivers/net/wireless/realtek/rtl8xxxu).

### RTL8720DN (Ameba D) — the SDR-interesting Realtek

Not a dongle — a **Wi-Fi MCU**: dual-band b/g/n + BLE 5.0, **Cortex-M4F (KM4) + Cortex-M0
(KM0)**, open FreeRTOS/Arduino SDK, sold as the **BW16 module** and **$6 Rtlduino / A1
Pico** boards. Crucially, Realtek's Ameba RTOS docs expose an **official Wi-Fi CSI API**
delivering per-subcarrier **I/Q (amplitude + phase)** raw data, in active or passive
modes — a genuine **rung 2 / CSI** capability with **documented, patchable firmware**. The
CSI framework spans the Ameba line (RTL8721Dx/8720E/8730E/8735C, etc.); RTL8720DN is the
cheap, hobbyist-accessible entry point. This is the Realtek part worth reversing further.
**Tier 2, verified (CSI API), open-firmware.**
Refs: [Realtek Ameba Wi-Fi CSI docs](https://aiot.realmcu.com/en/latest/rtos/wifi/csi/index.html),
[AmebaD product page](https://www.amebaiot.com/en/amebad/),
[Rtlduino RTL8720DN board](https://www.cnx-software.com/2021/01/10/rtlduino-rtl8720dn-dual-band-wifi-iot-board-features-2-4-5ghz-wireless-mcu/).

## CSI on USB Realtek — the honest status

Despite frequent forum claims, there is **no maintained, reproducible CSI tool** for
Realtek USB dongles (8812AU/8814AU/etc.). CSI extraction requires either firmware hooks
Realtek doesn't document or a report-descriptor path the open drivers don't expose. A few
academic "free your CSI"-style efforts touch Realtek MACs, but nothing ships as usable
tooling. If you need cheap CSI, use the **Ameba MCUs** (official API) or cross to
[Broadcom/Nexmon](../projects/nexmon.md), [Atheros](../projects/csi-toolchains.md), or
[Intel](intel.md)-class tools. See [../projects/csi-toolchains.md](../projects/csi-toolchains.md).

## Un-cataloged / TODO

- **RTL8852AU / RTL8852BU / RTL8832AU (Wi-Fi 6/6E USB)** — newest gen; `rtw89`-family and
  early out-of-tree drivers; monitor/injection status unconfirmed. Profile next cycle.
- **RTL8822CU / RTL8811FU** — additional AC/n USB parts with partial community drivers.
- **RTL8723DU / RTL8733BU** — later combo parts; injection status unknown.
- **RTL8730E / RTL8735C / RTL8721F (Ameba Pro/Smart)** — CSI-capable per Realtek docs;
  need per-board profiling (antennas, MIMO, CSI resolution S(8,x)/S(16,x)).
- **RTL8188GU / RTL8710BU / RTL8720CM** — verify whether Ameba-Z parts expose the CSI API.
- **PicoScenes / report-descriptor CSI on Realtek USB MACs** — chase whether any 8812AU
  CSI path is reproducible; currently theoretical.
- **Firmware RE** — no public Ghidra/IDA teardown of the 8051-class USB Wi-Fi ucode; a
  first real disassembly would be a genuinely new contribution.


---

## Extended parts — Cycle 3 sweep

An exhaustive pass over the Realtek Wi-Fi line that the chip-by-chip section above skips:
the legacy b/g softMACs, the whole `rtlwifi` PCIe/SDIO n/ac fleet, the `rtw88` and `rtw89`
generations (Wi-Fi 5/6/6E/7), and the wider **Ameba** SoC family that carries the official
Wi-Fi CSI API. The honest headline: **almost none of these climb past rung 1**, and many
PCIe/SDIO parts stall *below* the USB dongles because their in-kernel drivers expose
`monitor` but have famously unreliable **injection** (`rtlwifi`, `rtw88`, `rtw89`). The
only genuine rung-2 story remains the **Ameba MCUs** — and Cycle 2 only catalogued the
RTL8720DN, so the CSI-capable AmebaLite / AmebaDplus / AmebaSmart / AmebaPro2 SoCs are the
real net-new depth here.

### How to read the tiers below

- **Tier 1 (monitor+injection)** — USB dongles with a community/out-of-tree driver
  (`rtl8xxxu`, `rtl8812au`, `8821cu`, `88x2bu`, `r8712u`) that genuinely injects.
- **Tier 1 (monitor only)** — PCIe/SDIO parts where mainline `rtlwifi`/`rtw88`/`rtw89`
  register `NL80211_IFTYPE_MONITOR` and give you RX capture, but **injection is broken or
  unreliable** — do not treat these as pentest TX cards. Honest, common, and not inflatable.
- **Tier 2 (CSI)** — **only** the Ameba SoCs whose RTOS SDK ships the documented CSI API
  (per-subcarrier I/Q, `S(8,x)`/`S(16,x)` fixed-point). Open/documented firmware.

### Legacy 802.11 b/g (mac80211 softMAC — real injection)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8180 | b · 2.4 | `rtl818x_pci` (mainline) | 1 | monitor, injection | closed (thin) | original PCI softMAC; injection works |
| RTL8185 / 8185L | g · 2.4 | `rtl818x_pci` (mainline) | 1 | monitor, injection | closed (thin) | g-era PCI card |
| RTL8187B | g · 2.4 | `rtl8187` (mainline) | 1 | monitor, injection | closed (thin ucode) | USB sibling of the 8187L legend; slightly weaker TX |

### 802.11n USB (softMAC / rtl8xxxu era)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8188CUS / 8188RU | n 1×1 · 2.4 | `rtl8192cu` / `rtl8xxxu` | 1 | monitor, injection | closed (8051) | Edimax EW-7811Un, RPi-era dongle; 8188RU = high-power |
| RTL8192SU / 8191SU | n · 2.4 | `r8712u` (staging) | 1 | monitor(partial) | closed (8051) | early fullmac-ish USB n; injection flaky |
| RTL8188GU | n 1×1 · 2.4 | `rtl8xxxu` (recent) | 1 | monitor(partial), injection | closed (8051) | late nano n part |

### 802.11n PCIe / SDIO (rtlwifi — monitor OK, injection weak)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8188CE / 8192CE | n 1×1/2×2 · 2.4 | `rtl8192ce` (rtlwifi) | 1 | monitor | closed (8051) | mini-PCIe laptop cards; injection unreliable |
| RTL8191SE / 8192SE | n · 2.4 | `rtl8192se` (rtlwifi) | 1 | monitor | closed (8051) | early n laptop PCIe |
| RTL8188EE | n 1×1 · 2.4 | `rtl8188ee` (rtlwifi) | 1 | monitor | closed (8051) | budget laptop mini-PCIe |
| RTL8192DE / 8192DU | n · 2.4/5 | `rtl8192de` / `rtl8192du` | 1 | monitor | closed (8051) | Realtek's dual-band n |

### 802.11n + BT combos (rtlwifi / rtw88, PCIe·SDIO)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8723AE | n 1×1 +BT · 2.4 | `rtl8723ae` (rtlwifi) | 1 | monitor | closed (8051) | early combo mini-PCIe |
| RTL8723BE / 8723BS | n 1×1 +BT · 2.4 | `rtl8723be` / `rtl8723bs` | 1 | monitor | closed (8051) | very common laptop/tablet combo |
| RTL8723DE / 8723DS / 8723DU | n 1×1 +BT · 2.4 | `rtw88` | 1 | monitor | closed | rtw88-era combo (PCIe/SDIO/USB) |
| RTL8723CS | n 1×1 +BT · 2.4 | `rtw88` (SDIO) | 1 | monitor | closed | SBC / TV-box SDIO combo |

### 802.11ac PCIe (rtlwifi / rtw88 — monitor only)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8812AE | ac 2×2 · 2.4/5 | `rtl8821ae` (rtlwifi) | 1 | monitor | closed (8051) | PCIe sibling of the 8812AU dongle |
| RTL8821AE | ac 1×1 +BT · 2.4/5 | `rtl8821ae` (rtlwifi) | 1 | monitor | closed (8051) | ubiquitous laptop ac+BT card |
| RTL8814AE | ac 4×4 · 2.4/5 | out-of-tree `rtl8814ae` | 1 | monitor | closed (8051) | 4×4 PCIe; router/desktop |
| RTL8822BE / 8822BS | ac 2×2 +BT · 2.4/5 | `rtw88` | 1 | monitor | closed | rtw88 flagship-ac laptop card |
| RTL8822CE / 8822CS | ac 2×2 +BT · 2.4/5 | `rtw88` | 1 | monitor | closed | later 8822 revision, wide OEM use |
| RTL8821CE / 8821CS | ac 1×1 +BT · 2.4/5 | `rtw88` | 1 | monitor | closed | budget ac+BT combo |

### 802.11ac USB (net-new vs Cycle 2)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8812CU | ac 2×2 · 2.4/5 | `rtw88` (USB) | 1 | monitor, injection(partial) | closed (8051) | rtw88 USB ac; injection less proven than 8812AU |
| RTL8822CU | ac 2×2 · 2.4/5 | `rtw88` / `morrownr` | 1 | monitor, injection(partial) | closed (8051) | 8822C USB combo |
| RTL8811FU | ac 1×1 · 2.4/5 | out-of-tree `rtl8811fu` | 1 | monitor, injection(partial) | closed (8051) | cheap nano ac dongle |

### Wi-Fi 6 / 6E (rtw89 — monitor only, injection unproven)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8851BE | ax 1×1 +BT · 2.4/5 | `rtw89` | 1 | monitor | closed | budget Wi-Fi 6 1×1 |
| RTL8852AE | ax 2×2 +BT · 2.4/5 | `rtw89` | 1 | monitor | closed | first mass rtw89 Wi-Fi 6 card |
| RTL8852BE | ax 2×2 +BT · 2.4/5 | `rtw89` | 1 | monitor | closed | most common OEM Wi-Fi 6 Realtek |
| RTL8852CE | ax 2×2 +BT · 2.4/5/6 | `rtw89` | 1 | monitor | closed | Wi-Fi **6E** (6 GHz) |
| RTL8852BU | ax 2×2 · 2.4/5 | out-of-tree rtw89-USB | 1 | monitor(partial) | closed | Wi-Fi 6 USB; early driver |
| RTL8832AU / 8832CU | ax 2×2 · 2.4/5/6 | out-of-tree | 1 | monitor(partial) | closed | Wi-Fi 6E USB; sparse support |

### Wi-Fi 7 (rtw89)

| Part | Std / bands | Driver | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8922AE | be · 2.4/5/6 | `rtw89` | 1 | monitor | closed | Realtek's first Wi-Fi 7 PCIe (rtw89 explicit) |

### Ameba SoCs — the rung-2 CSI family (net-new depth)

| Part | Std / bands | SDK / core | Tier | Caps | FW | Note |
|---|---|---|---|---|---|---|
| RTL8195A / 8711AM | n · 2.4 | Ameba1 · Cortex-M3 | 1 | monitor, open-firmware | documented | original Ameba; open SDK, **no** CSI API |
| RTL8710 (AF/BN/BX) | n · 2.4 | AmebaZ · Cortex-M0/M3 | 1 | monitor, open-firmware | documented | low-cost Wi-Fi MCU; RTL8710E variant adds CSI |
| RTL8720E / 8710E / 8713E / 8726E | n · 2.4/5 | AmebaLite · Cortex-M55 | **2** | **csi**, monitor, open-firmware | documented | **official CSI API** — S(8,x)/S(16,x) I/Q |
| RTL8721Dx / 8720DN(cat.) / 8721F | b/g/n +BLE · 2.4/5 | AmebaD/Dplus · M4F+M0 | **2** | **csi**, monitor, open-firmware | documented | 8720DN already catalogued; **8721F (Dplus)** is net-new CSI |
| RTL8730E | ac · 2.4/5 | AmebaSmart · Cortex-A55 | **2** | **csi**, monitor, open-firmware | documented | Linux-class SoC, CSI API |
| RTL8735C / 8735B | ac · 2.4/5 | AmebaPro2 · M33 +NPU | **2** | **csi**, monitor, open-firmware | documented | AI-camera SoC; CSI + on-chip NPU |

**Cross-refs:** [rtw88 kernel driver](https://wireless.docs.kernel.org/en/latest/en/users/drivers/rtw88.html) ·
[lwfinger/rtw89](https://github.com/lwfinger/rtw89) ·
[Ameba Wi-Fi CSI API](https://aiot.realmcu.com/en/latest/rtos/wifi/csi/index.html) ·
[morrownr/USB-WiFi](https://github.com/morrownr/USB-WiFi) ·
[../projects/csi-toolchains.md](../projects/csi-toolchains.md) ·
[hardware-index.md](hardware-index.md).

> **Honest injection note.** For `rtlwifi` (PCIe/SDIO n & ac), `rtw88`, and `rtw89`, monitor
> capture is real but **frame injection is unreliable-to-broken** — these are RX/observation
> cards, not TX weapons. If you need injection, stay on the USB dongles in the chip-by-chip
> section (8812AU / 8814AU / 8821CU). None of these parts expose spectral scan, raw-IQ, or
> arbitrary-waveform TX — that door stays shut on Realtek Wi-Fi silicon (rungs 3–5 unbuilt).
