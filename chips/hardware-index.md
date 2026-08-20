# Buyable Hardware Index: What To Actually Buy

This is the shopping list. Everywhere else in the atlas we catalog *chips*; here we map
**real products you can put in a cart** to the chip inside them, the rung they reach on the
[SDR ladder](../docs/taxonomy.md), the project that unlocks that rung, and — most
importantly — the **buy-note**: which hardware revision, which chipset-roulette trap, and
which silent BOM swap will waste your money.

Two rules govern this whole page:

1. **The product is not the chip.** Vendors resell one model number across three different
   silicon vendors over its lifetime (the TL-WN722N is the textbook disaster). Always
   verify the chip on the *unit you receive*, not the one in the tutorial.
2. **The chip decides the ceiling; the project decides whether you reach it.** An AR9271 is
   a tier-1 part whether or not you install a driver. A BCM43455c0 is a black box until you
   flash `nexmon_csi`. Buying the silicon is necessary, not sufficient — the "unlocked by"
   column is the other half of the purchase.

Tier legend (full definitions in [taxonomy.md](../docs/taxonomy.md)): **0** black-box ·
**1** monitor+injection · **2** CSI · **3** spectral/raw-PHY · **4** arbitrary-waveform TX ·
**5** open/documented PHY.

> **How to check what you actually got.** On Linux: `lsusb` (USB) or `lspci -nn | grep -i
> net` (M.2/PCIe) prints the USB/PCI VID:PID — cross-reference it at
> [WikiDevi/DeviWiki](https://deviwiki.com) or [linux-hardware.org](https://linux-hardware.org).
> `dmesg | grep -iE 'ath|rtl|mt7|brcm|iwlwifi'` shows which driver bound. For USB Wi-Fi the
> community source of truth is [morrownr/USB-WiFi](https://github.com/morrownr/USB-WiFi).

---

## A — USB Wi-Fi dongles for monitor / injection (tier 1)

These are the cheapest way onto the ladder: plug in, load a driver, get monitor mode +
frame injection. Almost none climb past tier 1 (no CSI, no spectral) — for that jump to
sections B/C. The chip families here are detailed in [realtek.md](realtek.md),
[qualcomm-atheros.md](qualcomm-atheros.md), and [mediatek-ralink.md](mediatek-ralink.md).

| Product | Chip inside | Catalog id | Bands | Tier | Unlocked by | Buy-note |
|---|---|---|---|---|---|---|
| **Alfa AWUS036NHA** | Atheros AR9271 | `atheros-ar9271` | 2.4 | 1 | mainline `ath9k_htc` | The gold-standard reference injector. In-kernel, no DKMS. **Verify "NHA"** — counterfeits ship a Realtek and lie. |
| **Alfa AWUS036ACH / AC1200** | Realtek RTL8812AU (2×2) | `realtek-rtl8812au` | 2.4/5 | 1 | `aircrack-ng/rtl8812au` | The default 5 GHz injector. Out-of-tree DKMS. Newer units are USB-C but same chip. |
| **Alfa AWUS036ACM** | MediaTek MT7612U | `mediatek-mt7612u` | 2.4/5 | 1 | mainline `mt76x2u` | **The one that "just works"** — in-kernel since ~4.19, clean monitor/injection, no DKMS. Best default in 2026. |
| **Alfa AWUS036ACHM** | Realtek RTL8811AU (1×1) | `realtek-rtl8811au` | 2.4/5 | 1 | `aircrack-ng/rtl8812au` | Long-range 1×1; same driver as ACH, single stream. |
| **Alfa AWUS1900 / AWUS036ACHM(4×4)** | Realtek RTL8814AU (4×4) | `realtek-rtl8814au` | 2.4/5 | 1 | `aircrack-ng/rtl8812au`, `nicshaca/rtl8814au` | Four antennas, highest RX gain of the line. Some distro `rtl88xxau-dkms` packages **dropped 8814** — build dedicated. |
| **Alfa AWUS036AXM / AXML** | MediaTek MT7921AU(N) | `mediatek-mt7921` | 2.4/5 (+**6** on AXML) | 1 | mainline `mt7921u` (kernel ≥5.18) | Wi-Fi 6/6E. **AXML reaches 6 GHz** — the cheapest way to sniff 6E. Monitor works; injection support maturing, check `mt76` version. |
| **Alfa AWUS036NEH / NH** | Ralink RT3070 (older) | `ralink-rt2870-rt3070` | 2.4 | 1 | mainline `rt2800usb` | **Chipset-roulette:** classic units are RT3070; some later/rebadged stock ships RTL8188-class silicon (`realtek-rtl8188eus`). Verify before buying for a tutorial. |
| **Alfa AWUS036NEHW** | Ralink RT3070 | `ralink-rt2870-rt3070` | 2.4 | 1 | mainline `rt2800usb` | White NEH; same caveat as NEH. |
| **Panda PAU05 / PAU06** | Ralink RT5372 | `ralink-rt5370-rt5372` | 2.4 | 1 | mainline `rt2800usb` | Cheap, reliable, plug-and-play monitor/injection. PAU05 is the classic Kali starter. |
| **Panda PAU09** | Ralink **RT5572** | `ralink-rt5572` (new) | 2.4/5 | 1 | mainline `rt2800usb` | Dual-band 2×2, in-kernel. The cheapest dual-band no-DKMS injector. See net-new record below. |
| **TP-Link TL-WN722N v1** | Atheros AR9271 | `atheros-ar9271` | 2.4 | 1 | mainline `ath9k_htc` | **v1 ONLY.** The famous injection card. |
| **TP-Link TL-WN722N v2/v3** | Realtek RTL8188EUS | `realtek-rtl8188eus` | 2.4 | 1 | `aircrack-ng/rtl8188eus` (DKMS) | **THE trap.** Identical box, different chip — v2/v3 need an out-of-tree driver and inject worse. Every "my WN722N won't go monitor" thread is a v2. Check the tiny "Ver:2.0" on the label. |
| **TP-Link TL-WN821N v1–v3** | Atheros AR7010 + AR9287 | `atheros-ar9287` | 2.4 | 1 | mainline `ath9k_htc` | Early versions Atheros. |
| **TP-Link TL-WN821N v4–v6** | Realtek RTL8192EU | `realtek-rtl8192cu` | 2.4 | 1 | `rtl8192eu`/`rtl8xxxu` | Later versions silently switched to Realtek — same roulette as the WN722N. |
| **Comfast CF-912AC / CF-926AC** | Realtek RTL8812AU | `realtek-rtl8812au` | 2.4/5 | 1 | `aircrack-ng/rtl8812au` | Cheap ACH clone; same driver. QC varies. |
| **Comfast CF-WU810N** | Realtek RTL8188EUS | `realtek-rtl8188eus` | 2.4 | 1 | `aircrack-ng/rtl8188eus` | Nano dongle; monitor OK. |
| **Alfa AWUS036H (legacy)** | Realtek RTL8187L | `realtek-rtl8187l` | 2.4 | 1 | mainline `rtl8187` | The BackTrack-era legend. High TX power, 802.11b/g only. In-kernel, still works. |

**Injection-quality shortlist (2026):** for zero-hassle in-kernel monitor+injection buy
**MT7612U (AWUS036ACM)** for dual-band or **AR9271 (AWUS036NHA / WN722N v1)** for 2.4-only.
For 5 GHz with out-of-tree DKMS, **RTL8812AU (AWUS036ACH)**. Avoid RTL8812BU/8822BU for
injection — monitor works but injection is flaky ([realtek.md](realtek.md)).

**Bluetooth aside:** for Bluetooth/BLE sniffing (not Wi-Fi), the section-A analogue is the
**Ubertooth One** (`greatscottgadgets-ubertooth-one`) and TI-CC-based dongles — see
[other-vendors.md](other-vendors.md); they're a different radio, listed here only so the
"what do I buy to sniff X" question is complete.

---

## B — CSI-capable gear (tier 2): per-subcarrier channel state

CSI is the reason this atlas exists — quasi-IQ in the frequency domain, the substrate of
all Wi-Fi sensing. Every path here needs a **specific chip + specific toolchain**; there is
no generic "CSI dongle." Toolchains are detailed in
[../projects/csi-toolchains.md](../projects/csi-toolchains.md) and
[../projects/nexmon.md](../projects/nexmon.md).

| Product | Chip | Catalog id | Bands / BW | Streams | Unlocked by | Buy-note |
|---|---|---|---|---|---|---|
| **Raspberry Pi 3B+ / 4 / CM4 / 400 / Zero 2 W** | Broadcom BCM43455c0 | `broadcom-bcm43455c0` | 2.4/5, up to 80 MHz | 1×1 | [`nexmon_csi`](https://github.com/seemoo-lab/nexmon_csi) | **The people's CSI rig.** Cheap, ubiquitous, well-documented. Pi 4 & CM4 are the same chip. Walkthrough: [bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md). |
| **Raspberry Pi 3B / Zero W** | Broadcom BCM43430a1 | `broadcom-bcm43430` | 2.4, 20 MHz | 1×1 | `nexmon_csi` | 2.4-only, narrower BW than the 43455. Fine for entry sensing. |
| **Nexus 5 (phone)** | Broadcom BCM4339 | `broadcom-bcm4339` | 2.4/5, 80 MHz | 1×1 | `nexmon_csi` | Original Nexmon CSI target. Mobile form factor; used in early sensing papers. |
| **Nexus 6P / Galaxy S7 class** | Broadcom BCM4358 | `broadcom-bcm4358` | 2.4/5, 80 MHz | up to 2×2 | `nexmon_csi` | Phone-class; harder to root/flash than a Pi. |
| **ESP32 / ESP32-S3 / C-series dev boards** | Espressif ESP32(-Sx/Cx) | `espressif-esp32` (+ variants) | 2.4, 20/40 MHz | 1×1 | **built-in [`esp-csi`](https://github.com/espressif/esp-csi) API** | **No firmware RE at all** — CSI is a vendor API. ~\$5 boards (DevKitC, WROOM/WROVER). Best cost-per-node for dense sensor arrays. See [espressif.md](espressif.md). |
| **Intel 5300 laptops / M.2 cards** | Intel Ultimate-N 5300 | `intel-iwl5300` | 2.4/5, 20/40 MHz | up to 3×3 | [Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/) (Halperin) | **The academic classic** — thousands of papers. Needs an **old kernel** (the tool targets ~3.x/`iwlwifi` of that era) → run in a pinned VM/old ThinkPad (X200/T400/X1 gen1). 3-antenna CSI is its superpower. |
| **AX210 M.2 cards** | Intel Wi-Fi 6E AX210 | `intel-ax210-ax211` | 2.4/5/**6**, up to 160 MHz | 2×2 | [PicoScenes](https://ps.zpj.io/) / AX-CSI | Modern Wi-Fi 6E CSI incl. **6 GHz + 160 MHz** — the widest per-frame channel view on this page. Needs PicoScenes' patched driver/firmware; see [../projects/picoscenes.md](../projects/picoscenes.md) and [intel.md](intel.md). |
| **AX200 M.2 cards** | Intel Wi-Fi 6 AX200 | `intel-ax200-ax201` | 2.4/5, 160 MHz | 2×2 | PicoScenes / AX-CSI | Wi-Fi 6 (no 6 GHz). Cheaper AX210 alternative for 5 GHz sensing. |
| **QCA9300-class PCIe/mini-PCIe cards** | Atheros AR9300 series (QCA9300) | `atheros-ar9300-csi` | 2.4/5, 20/40 MHz | up to 3×3 | [Atheros CSI Tool](https://wands.sg/research/wifi/AtherosCSI/) (Xie et al.) | Cards branded QCA9300/AR9380/AR9382. Also runnable inside **PicoScenes**. Needs a supported card + patched `ath9k`; verify the exact AR93xx. |
| **ASUS RT-AC86U (router)** | Broadcom BCM4366c0 | `broadcom-bcm4366c0` | 2.4/5, **80 MHz** | **4×4** | `nexmon_csi` | **The only well-documented 4×4 CSI router.** 4 spatial streams × 80 MHz = the richest CSI on consumer gear. Community guide: [wifisensing.io](https://www.wifisensing.io/building-applications/devices/asus-rtac86u). See section C. |

**Choosing a CSI rig:**

- **Cheapest / most nodes:** ESP32 (\$5, vendor API, 2.4-only, 1×1).
- **Cheapest "real" 802.11n/ac CSI:** Raspberry Pi 4 + `nexmon_csi` (\$45, 1×1, up to 80 MHz).
- **Most antennas (spatial resolution):** ASUS RT-AC86U (4×4) or an Intel 5300 (3×3).
- **Widest bandwidth / 6 GHz:** Intel AX210 + PicoScenes (160 MHz, 6 GHz).
- **Most reproducible academic baseline:** Intel 5300 (pin the kernel) or QCA9300 Atheros CSI Tool.

> **Phase-calibration warning:** raw CSI phase carries hardware offsets (CFO, SFO, PBD).
> Sensing pipelines apply per-vendor correction. Datasets and calibration recipes:
> [../projects/wifi-sensing-datasets.md](../projects/wifi-sensing-datasets.md).

---

## C — Routers: CSI, spectral, and the 60 GHz outlier

Routers give you mains power, big antennas, and — crucially — **chips that dongles don't
carry** (4×4 Broadcom, ath10k QCA998x, 60 GHz QCA9500). The catch is you must flash them
(OpenWrt / vendor-U-Boot / `nexmon`) and some are one bad `nvram` write from a brick.

| Product | Radio chip(s) | Catalog id | Capability | Tier | Unlocked by | Buy-note |
|---|---|---|---|---|---|---|
| **ASUS RT-AC86U** | Broadcom BCM4366c0 (5 GHz, 4×4) | `broadcom-bcm4366c0` | **CSI** | 2 | `nexmon_csi` | Best consumer CSI router; 4×4×80 MHz. Its 2.4 GHz radio is a BCM4365e (3×3). Follow the exact firmware version the Nexmon patch targets. |
| **Netgear R8000P / R7900P** | Broadcom BCM4366 (5 GHz) | `broadcom-bcm4366c0` | CSI (port required) | 2* | `nexmon_csi` (community ports) | BCM4366-family like the AC86U but **not a first-class Nexmon target** — expect to match firmware versions / port patches. |
| **Netgear R7800 (Nighthawk X4S)** | Qualcomm QCA9984 ×2 (ath10k) | `qualcomm-qca9984` | **spectral-scan** | 3 | OpenWrt + `ath10k` `spectral_scan` | The **spectral** router: ath10k FFT bins across 4×4 160 MHz-capable radios. SoC is IPQ8065. See [qualcomm-atheros.md](qualcomm-atheros.md). |
| **Netgear R7500v2 / various QCA9880** | Qualcomm QCA9880 (ath10k) | `qualcomm-qca9880` | spectral-scan | 3 | OpenWrt + `ath10k` | Older ath10k spectral; widely available secondhand. |
| **Netgear R7000 (Nighthawk AC1900)** | Broadcom BCM4360 (5 GHz, 3×3) | `broadcom-bcm4360` (new) | black-box today | 0 | (no public nexmon port) | **Popular but a trap for SDR.** BCM4360 is **not** in Nexmon's supported firmwares and **not** a `nexmon_csi` target. Great OpenWrt router, poor SDR target. Buy an RT-AC86U instead for CSI. Net-new record below. |
| **Netgear R8000 (AC3200)** | Broadcom BCM4360 ×2 + BCM4709 SoC | `broadcom-bcm4360` | black-box today | 0 | (no public nexmon port) | Same story as R7000 — three radios, none a public Nexmon/CSI target. |
| **ASUS RT-AC68U** | Broadcom BCM4360 (5 GHz) | `broadcom-bcm4360` | black-box today | 0 | (no public nexmon port) | Listed because it's constantly recommended; not an SDR target. |
| **TP-Link Talon AD7200** | Qualcomm **QCA9500** (60 GHz, wil6210) + QCA9988/QCA9888 (ath10k) | `qualcomm-qca9500` | **60 GHz monitor + spectral** | 3 | [`talon-tools`](https://github.com/seemoo-lab/talon-tools), [`nexmon-arc`](https://github.com/seemoo-lab/nexmon-arc), [`lede-ad7200`](https://github.com/seemoo-lab/lede-ad7200) | **The only cheap 802.11ad (60 GHz) research platform.** `wil6210` gives monitor mode; SEEMOO's `nexmon-arc` patches the ARC-core 60 GHz firmware (v4.1.0.55 / v5.2.0.18) for beam/sector research. Its 2.4/5 radios are ath10k (spectral). Getting rare/expensive secondhand. See [../docs/mmwave-60ghz-radar.md](../docs/mmwave-60ghz-radar.md). |

\* "Tier 2*" = the chip supports it and it's been done, but not out-of-the-box on that exact
board — budget porting effort.

> **Correcting a persistent myth:** the Netgear **R7000/R8000 are not CSI or monitor-mode
> SDR platforms.** Their BCM4360 has no public Nexmon port. If a blog says "use an R7000 for
> Wi-Fi sensing," it is wrong — the CSI router is the **RT-AC86U (BCM4366c0)**; the spectral
> router is the **R7800 (QCA9984)**. Don't buy an R7000 expecting CSI.

**Router flashing safety:** always record the **stock firmware version** first (Nexmon/CSI
patches are version-specific), keep a serial/TFTP recovery path, and never flash over Wi-Fi.
Brick-recovery for these models usually means U-Boot TFTP + a known-good image.

---

## D — SDR-adjacent boards: openwifi (tier 5, open PHY)

If you want a Wi-Fi radio whose **PHY is actually yours**, you don't reverse-engineer a
dongle — you run [**openwifi**](https://github.com/open-sdr/openwifi), an open-source
802.11a/g/n baseband implemented in FPGA fabric on a Xilinx Zynq + an Analog Devices AD936x
RF transceiver. This is the true-SDR end of the ladder (**tier 5**): the MAC/PHY is source,
not a patched blob. It is a different kind of purchase — dev boards, not \$15 dongles — and
belongs here because it's the honest answer to "how do I get a *fully* open Wi-Fi radio."
Deep-dive: [../projects/openwifi.md](../projects/openwifi.md); yardstick SDRs in
[../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

| Platform | FPGA / SoC | RF frontend | Bands | Tier | Notes |
|---|---|---|---|---|---|
| **ADALM-PLUTO / ANTSDR E200** | Zynq-7010 | AD9363/AD9361 | 2.4/5 (hackable ~70 MHz–6 GHz) | 5 | Cheapest openwifi-capable board (ANTSDR is a Pluto-plus). Also a general SDR — `analog-adalm-pluto`. |
| **Low-cost Zynq-7020 + AD9361** (NeptuneSDR, LibreSDR) | Zynq-7020 | AD9361 | 2.4/5 | 5 | Community boards explicitly supported by openwifi-hw. Best price/capability for openwifi. |
| **ADRV9361-Z7035 + ADRV1CRR-BOB** | Zynq-7035 | AD9361 | 2.4/5 | 5 | Higher-end module; more logic + better RF. |
| **Xilinx ZC706 + FMCOMMS2/3/4** | Zynq-7045 | AD9361 (FMC) | 2.4/5 | 5 | Reference dev-board path; expensive. |
| **Xilinx ZCU102 + FMCOMMS2/3/4** | Zynq UltraScale+ | AD9361 (FMC-HPC) | 2.4/5 | 5 | Highest-end; overkill for most. |

The radio chip across all of these is the **Analog Devices AD9361** agile transceiver —
already cataloged via `analog-adalm-pluto` (the AD936x front-end), so no net-new record is
emitted here; buy by *board*, and pick the cheapest Zynq-7020 + AD9361 unit openwifi lists.
Supported-hardware source of truth:
[open-sdr/openwifi-hw](https://github.com/open-sdr/openwifi-hw).

---

## Fast decision guide

| I want to… | Buy | Then run |
|---|---|---|
| Sniff/inject 2.4 GHz, zero hassle | Alfa AWUS036NHA (AR9271) or WN722N **v1** | in-kernel `ath9k_htc` |
| Sniff/inject 2.4+5 GHz, zero hassle | Alfa AWUS036ACM (MT7612U) | in-kernel `mt76x2u` |
| Sniff/inject **6 GHz** (Wi-Fi 6E) | Alfa AWUS036AXML (MT7921AU) | in-kernel `mt7921u` (kernel ≥5.18) |
| Cheapest CSI, many nodes | ESP32 dev board | built-in `esp-csi` API |
| Cheapest "real" CSI | Raspberry Pi 4 | `nexmon_csi` |
| Richest CSI (4×4) | ASUS RT-AC86U | `nexmon_csi` |
| Widest-BW / 6 GHz CSI | Intel AX210 M.2 | PicoScenes |
| Classic 3×3 academic CSI | Intel 5300 laptop (pin old kernel) | Linux 802.11n CSI Tool |
| Spectrum analyzer view (tier 3) | Netgear R7800 (QCA9984) | OpenWrt `ath10k spectral_scan` |
| 60 GHz / 802.11ad research | TP-Link Talon AD7200 | `talon-tools` + `nexmon-arc` |
| A **fully open** Wi-Fi PHY (tier 5) | ANTSDR / Zynq-7020 + AD9361 | openwifi |

---

## Chipset-Roulette Hall of Shame

Same model number, different silicon — the traps that cost the most time:

- **TP-Link TL-WN722N** — v1 = **Atheros AR9271** (great injector, in-kernel); **v2/v3 =
  Realtek RTL8188EUS** (needs DKMS, injects worse). The single most common "why won't my
  card go monitor" cause. Read the "Ver:" on the label.
- **TP-Link TL-WN821N** — v1–v3 Atheros (AR7010+AR9287); **v4–v6 Realtek RTL8192EU**.
- **Alfa AWUS036NEH / NH** — historically **Ralink RT3070**; some later stock ships
  RTL8188-class. Verify the VID:PID.
- **Panda PAU0x line** — PAU05/PAU06 = RT5372 (2.4-only); **PAU09 = RT5572 (dual-band)** —
  don't assume the PAU09 is "just a dual-band PAU05," it's a different chip/id.
- **Counterfeit "Alfa AWUS036NHA/ACH"** — clones swap the Atheros/Realtek for a random
  cheaper part and reuse the label. Buy from Alfa/Rokland-authorized sellers; `lsusb` the
  unit on arrival.
- **Generic "RTL8812AU" AC dongles (Comfast, etc.)** — chip is usually right, but QC and
  RF power vary wildly; the *driver* (`aircrack-ng/rtl8812au`) is the constant, the antenna
  gain isn't.

**Golden rule:** trust the **chip**, not the **box**. `lsusb`/`lspci` every unit before you
build a project around it.

---

## Net-new module records

Only chips **not already in the catalog** get a record; everything else in the tables above
references an existing id. Two products introduce genuinely new silicon: the **Panda PAU09**
(Ralink RT5572) and the **Netgear R7000/R8000/ASUS RT-AC68U** (Broadcom BCM4360).

---

## References

- Nexmon (monitor/injection): <https://github.com/seemoo-lab/nexmon> · supported firmwares list: <https://github.com/seemoo-lab/nexmon/tree/master/firmwares>
- Nexmon CSI: <https://github.com/seemoo-lab/nexmon_csi>
- Talon Tools (802.11ad / QCA9500): <https://github.com/seemoo-lab/talon-tools> · <https://seemoo-lab.github.io/talon-tools/>
- nexmon-arc (wil6210 ARC firmware): <https://github.com/seemoo-lab/nexmon-arc>
- lede-ad7200 (OpenWrt for Talon AD7200): <https://github.com/seemoo-lab/lede-ad7200>
- aircrack-ng rtl8812au driver: <https://github.com/aircrack-ng/rtl8812au> · rtl8188eus: <https://github.com/aircrack-ng/rtl8188eus>
- morrownr USB-WiFi (adapter/chip index): <https://github.com/morrownr/USB-WiFi>
- Linux 802.11n CSI Tool (Intel 5300, Halperin): <https://dhalperi.github.io/linux-80211n-csitool/>
- Atheros CSI Tool (QCA9300): <https://wands.sg/research/wifi/AtherosCSI/>
- PicoScenes (AX200/AX210/QCA9300 CSI): <https://ps.zpj.io/>
- Espressif esp-csi: <https://github.com/espressif/esp-csi>
- ASUS RT-AC86U Wi-Fi sensing guide: <https://www.wifisensing.io/building-applications/devices/asus-rtac86u>
- openwifi: <https://github.com/open-sdr/openwifi> · openwifi-hw (supported boards): <https://github.com/open-sdr/openwifi-hw>
- Alfa/MediaTek support notes (Rokland): <https://store.rokland.com/pages/alfa-awus036axml-awus036axm-support-linux>
- Panda PAU09 (RT5572): <https://deviwiki.com/wiki/Panda_Wireless_PAU09>
- Cross-links: [../docs/taxonomy.md](../docs/taxonomy.md) · [../projects/nexmon.md](../projects/nexmon.md) · [../projects/csi-toolchains.md](../projects/csi-toolchains.md) · [../projects/openwifi.md](../projects/openwifi.md) · [../docs/glossary.md](../docs/glossary.md)


---

## More buyable hardware — Cycle 5 (2024–2025)

Current, purchasable gear for people who want to *do* the things in this catalog — monitor/inject, pull CSI, sweep sub-GHz, or run an open PHY — without soldering a lab together. Each row names the **chip** (cross-linked to its vendor file), the **SDR-ladder tier** the chip reaches *with the listed project*, the **unlocking project**, and a **buy-note** — because on nearly every one of these SKUs the vendor swaps silicon between revisions while keeping the model number. Treat the model number as a *hint*, not a spec: confirm the actual chip (`lsusb`, `dmesg`, an FCC ID lookup, or a review that ran `ethtool -i`/`iw dev`) **before** you pay.

> **Chipset-roulette is the rule, not the exception.** "SONOFF Dongle Plus" is two different radios; "AWUS036AX*" spans MT7921 and MT7925; the RTL-SDR "V3 vs V4" changes the tuner *and* the driver you need. A blog post from 2022 describing "this adapter" may describe a chip the box no longer contains.

### Wi-Fi 6 / 6E / 7 USB adapters (monitor + injection, some CSI)

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **Alfa AWUS036AXML** | MediaTek MT7921AU → [`chips/mediatek-ralink.md`](mediatek-ralink.md) | 2.4/5 GHz | **T1** monitor+injection | mainline `mt7921u` (`mt76`) | Best-documented AX USB adapter for monitor/inject. Needs kernel ≥ 5.16 for stable `mt7921u`; also exposes a Bluetooth interface. AX-rate injection is patchy — verify with `aireplay-ng --test`. |
| **Alfa AWUS036AXM** | MediaTek MT7921AU (*reported*) | 2.4/5 GHz | **T1** monitor+injection | `mt7921u` / `mt76` | Same silicon family as the AXML in most units, different enclosure. *Reported*, not guaranteed — check `dmesg` after plug-in. |
| **Newer Alfa "AX" SKUs (AWUS036AX…)** | MediaTek **MT7925**AU (Wi-Fi 7) — net-new, below | 2.4/5/6 GHz | **T1** monitor+injection | `mt7925u` / `mt76` (kernel ≥ 6.7) | MT7925 is a *different* driver from MT7921 — a kernel that lit up your AXML may not see this one. 6 GHz monitor is regulatory-gated. Confirm the exact string in `dmesg` before assuming CSI/6E works. |

**No turnkey CSI on the MediaTek USB parts yet.** `mt76` gives you monitor + injection (tier 1). CSI from MT7921/MT7925 exists only in research patches, not a shipping toolchain — if CSI is the goal, buy Intel or Broadcom (below), not Alfa.

### Intel M.2 cards for CSI (AX-CSI / PicoScenes)

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **Intel AX210** (M.2 2230, e.g. bare card + USB/PCIe carrier) | Intel AX210 → [`chips/intel.md`](intel.md) | 2.4/5/6 GHz | **T2** csi (+ monitor) | [PicoScenes](../projects/picoscenes.md), AX-CSI | *Verified*: PicoScenes lists AX210 for packet injection and CSI including the 6 GHz band. This is the practical 6E CSI card in 2024–25. Needs the PicoScenes-patched driver/firmware — you cannot pull CSI on the stock `iwlwifi`. |
| **Intel AX200** (M.2 2230) | Intel AX200 → [`chips/intel.md`](intel.md) | 2.4/5 GHz | **T2** csi | [PicoScenes](../projects/picoscenes.md) | *Verified* on the PicoScenes hardware list. No 6 GHz. Cheaper and more available than AX210; identical CSI workflow. |
| **Intel BE200 / BE202** (Wi-Fi 7, M.2 2230) | Intel BE200 → [`chips/intel.md`](intel.md) | 2.4/5/6 GHz | **T2** csi (*emerging*) | PicoScenes (BE-series support *in progress*) | *Reported/theoretical* for CSI — BE200 is **not** on the confirmed PicoScenes NIC list as of this cycle. Also a platform trap: **BE200 is CNVi/PCIe and is widely reported not to init on AMD platforms** (Intel-host lock). Buy for Wi-Fi 7 connectivity, not as a guaranteed CSI tool yet. |

> Intel cards do **not** do free-form injection like Atheros/MediaTek; their value here is *CSI fidelity*. The QCA9300 and IWL5300 remain the classic PicoScenes/Atheros-CSI/Linux-802.11n-CSI reference cards if you want the legacy toolchains — see [`chips/qualcomm-atheros.md`](qualcomm-atheros.md).

### Broadcom CSI via nexmon — Raspberry Pi

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **Raspberry Pi 3B+/4B** | BCM43455c0 → [`chips/broadcom-cypress.md`](broadcom-cypress.md) | 2.4/5 GHz | **T2** csi | [nexmon_csi](../projects/nexmon.md) | The reference nexmon-CSI platform; the [bcm43455c0 walkthrough](../docs/walkthroughs/bcm43455c0-raspberry-pi.md) and [CSI walkthrough](../docs/walkthroughs/nexmon-csi-to-usable-csi.md) target exactly this. Firmware `7_45_189`. |
| **Raspberry Pi 5** | BCM43455c0 (same radio as Pi 4) | 2.4/5 GHz | **T2** csi | [nexmon_csi](../projects/nexmon.md) — *see repo discussion #395* | *Verified supported*: nexmon_csi's device table lists the bcm43455c0 for "Raspberry Pi 3B+/4B/5," and the repo ships a Makefile for recent Raspberry Pi OS kernels. **Buy-note:** the Pi 5's new RP1 southbridge and current 6.x kernels break naive builds — you must follow the Pi-5/recent-kernel path in discussion #395, not the old Pi-4 recipe. |

### Sub-GHz gear (sweep, capture, replay, transmit)

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **HackRF One** | MAX2839/MAX5864 + LPC4320 (genuine SDR front-end) | 1 MHz–6 GHz | **T5** raw-iq, arbitrary-waveform (half-duplex, RX/TX, 8-bit, ~20 Msps) | GNU Radio, SDR# / `hackrf` tools; also a PicoScenes SDR frontend | The general-purpose reference SDR. Half-duplex and 8-bit — great for learning/replay, not for weak-signal work. Clones exist; a real unit has clean spurs. **TX is legal only in bands you're licensed for** — see [`docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md). |
| **RTL-SDR Blog V4** | R828D tuner + RTL2832U | ~0.5 MHz–1.766 GHz (RX only) | **T5** raw-iq (RX only) | librtlsdr / rtl_sdr, GNU Radio | *Buy the V4 specifically*: it uses the **R828D** (not the V3's R820T2) and **requires up-to-date drivers** — old `librtlsdr` will show a dead/garbled spectrum. RX only; no transmit. The canonical "$40 SDR." |
| **YARD Stick One** | TI CC1111 sub-GHz transceiver → [`chips/lora-subghz.md`](lora-subghz.md) | ~300–928 MHz (banded) | **T2** raw packet / configurable OOK-FSK-MSK TX+RX, **open-firmware** | [RfCat](https://github.com/atlas0fd00m/rfcat) (open firmware) | Not an IQ SDR — a *fully scriptable* sub-GHz transceiver. RfCat is open and hackable from Python. Ideal for reversing ISM remotes/telemetry. TX capable → licensing applies. |
| **Flipper Zero** | CC1101 sub-GHz (+ NFC/125 kHz/IR/iButton) → [`chips/lora-subghz.md`](lora-subghz.md) | 300–348 / 387–464 / 779–928 MHz | **T1** OOK/2-FSK/GFSK/MSK capture+replay (not IQ) | stock FW; **Unleashed / RogueMaster / Momentum** unofficial FW | The CC1101 is a modem, not an SDR — no raw IQ, no arbitrary waveform. Stock firmware region-locks/limits TX; unofficial firmware unlocks the full CC1101 range, which can put you **outside legal TX limits** — user's responsibility. |

### BLE / 802.15.4 / Zigbee sniffers

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **SONOFF Zigbee 3.0 USB Dongle Plus** | **Model matters** → [`chips/ble-154-thread.md`](ble-154-thread.md) | 2.4 GHz | **T1** 802.15.4 monitor | zigbee2mqtt; TI sniffer firmware | **Chipset roulette by design.** *ZBDongle-**P*** = TI **CC2652P** (flashable to router *or* packet-sniffer firmware — the one you want for RE). *ZBDongle-**E*** = Silicon Labs **EFR32MG21** (different toolchain). Buy the **P** if you want the TI SmartRF/Wireshark 802.15.4 sniffer path. |
| **Nordic nRF52840 Dongle (PCA10059)** | Nordic nRF52840 → [`chips/ble-154-thread.md`](ble-154-thread.md) | 2.4 GHz | **T1** BLE + 802.15.4 monitor | nRF Sniffer for BLE (+ Wireshark); fully reflashable | Cheap, official, well-supported. Runs the Nordic BLE sniffer firmware out of the box and takes arbitrary custom firmware (SoftDevice or bare-metal) for deeper RF work. |
| **Electronic Cats CatSniffer v3** | TI **CC1352P7** (+ RP2040) — net-new, below | sub-GHz + 2.4 GHz | **T1** multiprotocol monitor (BLE/Zigbee/802.15.4/sub-GHz) | [CatSniffer firmware](https://github.com/ElectronicCats/CatSniffer), SmartRF Sniffer Agent → Wireshark | Open-hardware multiprotocol sniffer; the CC1352P7 covers both sub-GHz and 2.4 GHz so one dongle sees ISM remotes *and* Zigbee/BLE. Newer than the CC2652-class parts. |

### ESP32 CSI dev boards (cheap, dense CSI)

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **ESP32-C6-DevKitC/M** | Espressif ESP32-C6 → [`chips/espressif.md`](espressif.md) | 2.4 GHz (Wi-Fi 6) | **T2** csi | [esp-csi](https://github.com/espressif/esp-csi) | RISC-V, Wi-Fi 6 (2.4 only) + BLE 5 + 802.15.4. *Verified*: esp-csi lists the C6 among fully supported CSI parts. See the [ESP32 Ghidra walkthrough](../docs/walkthroughs/esp32-xtensa-ghidra.md) for firmware RE (note: C-series is RISC-V, not Xtensa). |
| **ESP32-C5-DevKitC** | Espressif ESP32-C5 — net-new, below | 2.4/5 GHz (Wi-Fi 6) | **T2** csi | [esp-csi](https://github.com/espressif/esp-csi) | Espressif's first **dual-band** part — CSI on 5 GHz for a few dollars. *Verified* in the esp-csi supported list (ESP32 / S2 / C3 / S3 / **C5** / C6 / C61). Recent silicon; use current ESP-IDF. |
| **ESP32-C61-DevKit** | Espressif ESP32-C61 — net-new, below | 2.4 GHz (Wi-Fi 6) | **T2** csi | [esp-csi](https://github.com/espressif/esp-csi) | Cost-reduced 2.4-only Wi-Fi 6 RISC-V part; *verified* in the esp-csi list. Very new — toolchain/board availability still maturing. |

### Open-PHY / openwifi board

| Device | Chip | Bands | Tier + caps | Unlocking project | Buy-note / warning |
|---|---|---|---|---|---|
| **AntSDR E200** | Xilinx Zynq-7020 + Analog Devices AD9361 RFIC → [`chips/router-ap-socs.md`](router-ap-socs.md) | 70 MHz–6 GHz (AD9361), used for 2.4/5 GHz 802.11 | **T5** open/documented PHY + raw-IQ | [openwifi](../projects/openwifi.md) | A genuine SDR (AD9361) running the **openwifi** FPGA 802.11a/g/n stack — a real open-source Wi-Fi PHY/MAC you can modify. **Buy-note:** openwifi targets *specific* SoC+RFIC boards; confirm your E200 variant is on the openwifi supported-board list and flash the matching image, or you get a bring-up project, not a radio. |

### Quick decision guide

- **I want CSI, turnkey** → Intel **AX210** + PicoScenes (6E), or a **Raspberry Pi 4/5** + nexmon_csi (cheapest), or an **ESP32-C5/C6** dev board (cheapest of all, 2.4/5 GHz).
- **I want monitor + injection** → Alfa **AWUS036AXML** (MT7921AU, tier 1). Confirm chip in `dmesg`.
- **I want to touch RF / sub-GHz** → **RTL-SDR V4** (RX, $40), step up to **HackRF One** (RX/TX), **YARD Stick One** for scriptable ISM.
- **I want to sniff BLE/Zigbee** → **nRF52840 dongle** (BLE) or **SONOFF ZBDongle-P / CC2652P** (802.15.4); **CatSniffer** if you want both sub-GHz and 2.4 in one.
- **I want a real open Wi-Fi PHY** → **AntSDR E200** + openwifi.

### References

- PicoScenes supported hardware & 6 GHz CSI on AX210 — https://ps.zpj.io/
- nexmon_csi supported devices (incl. Raspberry Pi 5, discussion #395) — https://github.com/seemoo-lab/nexmon_csi
- esp-csi full-series support (ESP32 … C5 / C6 / C61) — https://github.com/espressif/esp-csi
- `mt76` driver (MT7921/MT7925 monitor+injection) — https://github.com/openwrt/mt76
- RfCat firmware for YARD Stick One — https://github.com/atlas0fd00m/rfcat
- YARD Stick One / HackRF One (Great Scott Gadgets) — https://greatscottgadgets.com/yardstickone/ , https://greatscottgadgets.com/hackrf/one/
- RTL-SDR Blog V4 (R828D tuner, driver requirement) — https://www.rtl-sdr.com/rtl-sdr-blog-v4-dongle-initial-release/
- Flipper Zero + Unleashed firmware — https://flipperzero.one/ , https://github.com/DarkFlippers/unleashed-firmware
- SONOFF Zigbee 3.0 USB Dongle Plus (P = CC2652P, E = EFR32MG21) — https://sonoff.tech/product/gateway-and-sensors/zbdongle-p/
- Nordic nRF52840 Dongle — https://www.nordicsemi.com/Products/Development-hardware/nRF52840-Dongle
- Electronic Cats CatSniffer (CC1352P7) — https://github.com/ElectronicCats/CatSniffer
- openwifi + AntSDR E200 — https://github.com/open-sdr/openwifi , https://www.crowdsupply.com/microphase-technology/antsdr-e200


---

## SDR & specialty hardware — Cycle 6

This section rounds out the buyable-hardware index with the **genuine software-defined radios** that serve as the yardstick throughout this catalog. When an entry claims "Tier 4 arbitrary-waveform TX" or "Tier 5 genuine SDR," *these* are the devices that actually clear that bar — purpose-built radios with wide continuous tuning, real ADCs/DACs, and (for most) transmit paths. They are also the reference tools for the passive-radar, cross-technology-communication (CTC), and cellular/GNSS observation work covered in this cycle: you use a real SDR to *characterize* what a repurposed Wi-Fi/baseband chip is doing, and to build the coherent front-ends (KrakenSDR) that Wi-Fi silicon cannot provide.

**Honest framing.** A $45 RTL-SDR outperforms every "repurposed Wi-Fi chip as SDR" trick in this catalog for general-purpose RX below 1.7 GHz, and a $300 HackRF beats all of them for arbitrary TX. The reason the rest of this catalog exists is *not* that Wi-Fi silicon is a better radio — it is that the Wi-Fi/cellular chip is *already inside the target device*, operates natively in the 2.4/5/6 GHz bands where cheap SDRs get expensive, and can be weaponized/measured *in situ* without adding hardware. Keep that trade in mind: SDRs win on flexibility and fidelity; repurposed chips win on ubiquity, band, and stealth.

### Where each device sits on the ladder

The SDR ladder (Tier 0–5) in this catalog measures *how much of the PHY a repurposed chip exposes*. Genuine SDRs are, almost by definition, at the top: they hand you raw IQ (Tier 3–4 RX) and, if they transmit, arbitrary-waveform TX (Tier 4), with open or fully documented signal chains (Tier 5). They are the "control group." Tiers below only become interesting when you *cannot* add one of these to the target.

### Receive-only reference radios

These are the cheap, high-fidelity "ears" — used as passive-radar surveillance/reference channels, ADS-B / GNSS / spectrum observers, and as the ground-truth receiver when validating what a Wi-Fi chip's CSI or spectral-scan is really reporting.

| Device | Tuner / ADC | Freq range | Max usable BW | ADC bits | TX? | Price band | Best use here | Catalog id |
|---|---|---|---|---|---|---|---|---|
| **RTL-SDR Blog V4** | R828D + RTL2832U | ~0.5 MHz (built-in HF upconv.) – 1766 MHz | ~2.4 MHz (3.2 theo.) | 8 | No | ~$45 | Cheapest yardstick RX; passive-radar node; ADS-B/GNSS-L1 observation | `rtlsdr-rtl2832u` |
| **Airspy Mini** | R820T2 | 24 – 1800 MHz | 6 MHz | 12 (≈10.4 ENOB) | No | ~$99 | Higher-dynamic-range RX than RTL; VHF/UHF survey | `airspy-r2-hfplus` |
| **Airspy R2** | R820T2 | 24 – 1800 MHz | 10 MHz | 12 | No | ~$169 | Wideband spectrum capture; PoCSAG/trunking/passive-radar RX | `airspy-r2-hfplus` |
| **Airspy HF+ Discovery** | Tuner-less / polyphase | 0.5 kHz–31 MHz, 60–260 MHz | 0.768 MHz | high-DR | No | ~$169 | HF/VHF weak-signal, EMC, extreme dynamic range | `airspy-r2-hfplus` |
| **SDRplay RSP1B** | Direct + MSi2500 | 1 kHz – 2 GHz | 10 MHz | 14 | No | ~$120 | HF-to-2GHz all-in-one RX; teaching/reference | `sdrplay-rsp` |
| **SDRplay RSPdx / RSPdx-R2** | as above + preselectors | 1 kHz – 2 GHz | 10 MHz | 14 | No | ~$250 | HDR mode <2 MHz; front-end filtering for hostile RF; passive-radar reference | `sdrplay-rsp` |

Notes: RTL-SDR's 8-bit ADC and ~2.4 MHz stable bandwidth are the honest ceiling — plenty for narrowband work, ADS-B (1090 MHz), NOAA/GNSS-L1, and single-channel passive-radar experiments, but you feel the dynamic-range wall next to a 12/14-bit Airspy/RSP. All of these are **RX-only**: they cannot transmit and cannot be used for the injection/jamming/CTC-TX work in this catalog.

### Transmit-capable SDRs (the TX yardstick)

These are what "Tier 4 arbitrary-waveform TX" actually looks like in buyable form — the reference for replay attacks, jamming characterization, CTC transmit experiments, and generating known waveforms to test a repurposed chip's RX.

| Device | Transceiver / FPGA | Freq range | Max BW / sample rate | Bits | Duplex | Price band | Best use here | Catalog id |
|---|---|---|---|---|---|---|---|---|
| **HackRF One** | MAX2837 + MAX5864, half-duplex | 1 MHz – 6 GHz | 20 MHz | 8 | Half | ~$300–350 | The arbitrary-waveform TX yardstick; replay, protocol fuzzing, jamming tests across 2.4/5 GHz | `greatscott-hackrf-one` |
| **ADALM-PLUTO** | AD9363 (→AD9361 hack) | 325 MHz–3.8 GHz (hack: 70 MHz–6 GHz) | 20 MHz (61.44 MSPS) | 12 | Full (1×1) | ~$230 | Cheap full-duplex TX/RX; LTE/OFDM test-vector generation; teaching | `analog-adalm-pluto` |
| **LimeSDR Mini 2.0** | LMS7002M + ECP5 FPGA | 10 MHz – 3.5 GHz | 30.72 MHz | 12 | Full (1×1) | ~$200–260 | Open-FPGA TX/RX; GNU Radio / SoapySDR; on-device DSP | `lime-limesdr` |
| **bladeRF 2.0 micro (xA4/xA9)** | AD9361 + Cyclone V FPGA | 47 MHz – 6 GHz | 56 MHz (61.44 MSPS) | 12 | Full (2×2 MIMO) | ~$540 (A4) / ~$720 (A9) | 2×2 MIMO TX/RX; coherent 2-ch experiments; larger FPGA fabric | `nuand-bladerf-2micro` |
| **USRP B200mini** | AD9364 + Spartan-6 | 70 MHz – 6 GHz | 56 MHz | 12 | Full (1×1) | ~$800 | UHD/GNU Radio reference; compact 1×1; srsRAN/OpenAirInterface cellular labs | `ettus-usrp` |
| **USRP B210** | AD9361 + Spartan-6 | 70 MHz – 6 GHz | 56 MHz (30.72 full-rate 2×2) | 12 | Full (2×2 MIMO) | ~$1,500–2,100 | 2×2 MIMO; the standard cellular-baseband/eNB test radio (srsRAN, OAI) | `ettus-usrp` |
| **USRP N320** | dual AD9371-class + 10 GbE | 3 MHz – 6 GHz | 200 MHz / channel | 14 | Full (2 ch) | ~$12,000 | High-bandwidth 5G-NR / wideband monitoring; lab-grade coherent 2-ch | `ettus-usrp` |

Notes: HackRF is half-duplex 8-bit — superb reach (1 MHz–6 GHz) and the community-standard TX tool, but it is *not* a high-dynamic-range receiver; pair it with an Airspy/RSP for RX. Pluto's "70 MHz–6 GHz" is a well-known firmware unlock of the AD9363 to AD9361 behavior — reliable but technically out-of-spec at the band edges. B210 remains the reference SDR for **cellular baseband work** (srsRAN, OpenAirInterface) discussed in `cellular-basebands.md`; N320 is the step up when you need real 100–200 MHz instantaneous bandwidth for 5G-NR capture.

### Coherent / specialty gear (net-new)

The one capability *no* consumer Wi-Fi chip and *no* single cheap SDR gives you is **phase-coherent multichannel RX** — the prerequisite for direction-finding and clean bistatic/passive radar. That is why the KrakenSDR earns a net-new record: it is the buyable device the passive-radar and DF discussions in this cycle actually run on.

- **KrakenSDR** (`krakenrf-krakensdr`, net-new): five R828D/RTL2832U tuners sharing one clock plus a built-in noise-source for phase calibration → **5 coherent channels**, ~24–1766 MHz per tuner (≈100 MHz–1 GHz practical for DF/passive-radar), ~2.4 MHz/channel, 8-bit, **RX-only**, ~$500. Open-source DAQ firmware (Heimdall) and DoA/passive-radar DSP. This is the honest "genuine coherent SDR" — it does something repurposed Wi-Fi CSI *approximates* (angle/phase info) but with real, calibrated, wideband coherence. Use it as the ground-truth reference when a catalog entry claims AoA/DF from CSI. See `../projects/rtl-sdr-lineage.md`.
- **HackRF PortaPack (H2 / H4M + Mayhem firmware)** (`greatscott-portapack-mayhem`, net-new): an LCD + navigation + battery add-on board that turns a HackRF One into a **standalone, no-PC** transceiver. The open-source **Mayhem** firmware fork provides on-device TX/RX apps (replay, ADS-B/POCSAG/AIS/RDS generation, jammer, spectrum). Same 1 MHz–6 GHz / 8-bit / half-duplex HackRF radio underneath (~$100–250 for the add-on + host). Relevant here as the *field* form of the Tier-4 TX yardstick and as a self-contained CTC/replay bench. See `greatscott-hackrf-one`.

*Not given separate records (variants of existing catalog ids):* Airspy Mini/R2/HF+ (→ `airspy-r2-hfplus`), SDRplay RSP1B/RSPdx (→ `sdrplay-rsp`), USRP B200mini/B210/N320 (→ `ettus-usrp`), LimeSDR Mini 2.0 (→ `lime-limesdr`), RTL-SDR Blog V4 (→ `rtlsdr-rtl2832u`).

### Antennas, LNAs, filters, upconverters

Accessories — no catalog records (they carry no firmware and are not radios) — but they are what make the radios above usable for the work in this cycle:

- **Antennas:** RTL-SDR Blog / Nooelec multipurpose dipole kits (telescopic, HF–UHF); band-specific for the cellular/GNSS/passive-radar tasks — 1090 MHz ADS-B collinear, active GNSS L1/L5 patch (for the raw-observable work in `cellular-basebands.md`), log-periodic (LPDA) for wideband DF/passive-radar surveillance channels, Yagi for a directional reference/illuminator channel.
- **LNAs (low-noise amplifiers):** RTL-SDR Blog wideband LNA (bias-tee powered); **Nooelec SAWbird** band-filtered LNA+SAW series — SAWbird+ GOES (1.7 GHz), ADS-B (1090 MHz), **GPS/GNSS (~1.5 GHz)**, which is the practical way to get clean L1 into an RTL/Airspy; Mini-Circuits ZX60-series for lab-grade gain.
- **Filters:** FM broadcast band-stop / notch (essential near strong FM for passive radar using FM illuminators), 1090 MHz SAW, GNSS SAW, and generic Mini-Circuits SBP/SHP/SLP bandpass/high/low-pass.
- **Upconverters:** Nooelec **Ham It Up** and SpyVerter — shift 0–30 MHz HF up into an SDR's native VHF range for radios lacking native HF (note: the RTL-SDR Blog V4 already integrates HF upconversion, so it needs no external unit).
- **Bias tees & clocks:** software-switchable bias tees (built into RTL-SDR V4, HackRF, Airspy, KrakenSDR) to power inline LNAs; external 10 MHz GPSDO reference for disciplining B2xx/N3xx and for coherent multi-radio setups beyond KrakenSDR.

### How this ties back to the catalog

- **Passive radar / bistatic sensing:** KrakenSDR (coherent) or two RTL/Airspy on a shared clock provide reference+surveillance channels; Wi-Fi-chip "passive-radar-like" CSI Doppler (see `../projects/csi-toolchains.md`) is the *repurposed* analogue — lower fidelity, but already in-band at 2.4/5 GHz.
- **Cellular basebands (`cellular-basebands.md`):** B210/N320 + srsRAN/OpenAirInterface are the real SDR-side of the LTE/5G work; the basebands themselves are Tier 0–1 (diag/measurement only), not IQ sources.
- **GNSS:** an RTL/Airspy + SAWbird-GPS LNA gives raw L1 IQ for software receivers (GNSS-SDR); GNSS chips give observables (Tier 0–1), not IQ.
- **Tier-4/5 verification (`../docs/verification-tier4.md`, `../docs/verification-tier5-openfirmware.md`):** these devices are the calibrated signal sources/sinks used to *prove* a repurposed chip's claimed TX/RX capability.

### References

- RTL-SDR Blog — V4 dongle and buyer's guide: https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/
- KrakenRF (KrakenSDR): https://www.krakenrf.com/ and docs https://github.com/krakenrf/krakensdr_docs/wiki
- Great Scott Gadgets — HackRF One: https://greatscottgadgets.com/hackrf/one/
- HackRF PortaPack Mayhem firmware: https://github.com/portapack-mayhem/mayhem-firmware
- Airspy: https://airspy.com/
- SDRplay: https://www.sdrplay.com/
- Analog Devices ADALM-PLUTO: https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/adalm-pluto.html
- Nuand bladeRF 2.0 micro: https://www.nuand.com/bladerf-2-0-micro/
- Lime Microsystems LimeSDR Mini 2.0: https://limemicro.com/products/boards/limesdr-mini-2-0/
- Ettus Research USRP B210 / N320: https://www.ettus.com/all-products/ub210-kit/ , https://www.ettus.com/all-products/usrp-n320/
- Nooelec SAWbird / Ham It Up: https://www.nooelec.com/store/sdr/sdr-addons.html
