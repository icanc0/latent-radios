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
