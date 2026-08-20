# MediaTek / Ralink Wi-Fi — the open-driver end of the SDR ladder

MediaTek's Wi-Fi silicon is the friendliest mass-market family for anyone who wants
to bend a Wi-Fi radio toward software-defined-radio duty, for one structural reason:
**the Linux driver, `mt76`, is fully open, in-tree, and actively hacked in the open.**
Where Broadcom forces you to reverse-engineer and *patch* closed firmware (see
[../projects/nexmon.md](../projects/nexmon.md)) to reach monitor/injection or CSI,
the MediaTek path is different — the MCU firmware blobs stay closed, but the driver
already speaks a rich MCU-command protocol, and the interesting PHY telemetry
(**Channel State Information**) can be coaxed out *without touching the firmware at
all*, purely by patching `mt76`. That single fact is why MediaTek quietly became a
first-class Wi-Fi-sensing platform on Wi-Fi 6 hardware.

This file spans two eras that share a lineage:

- **Legacy Ralink** (Ralink Technology, acquired by MediaTek in 2011) — the
  `rt2x00`/`rt2800usb` dongles that were the *canonical* aircrack-ng injection
  adapters for a decade: RT2500, RT2570, RT2870/RT3070, RT3572, RT5370, RT5372.
- **Modern MediaTek `mt76`** — MT7601U, the MT76x0/MT76x2 USB parts (MT7610U,
  MT7612U → the Alfa AWUS036ACM), and the ConnAC AP/router/client SoCs MT7615,
  MT7663, MT7915/MT7916 (Wi-Fi 6), MT7921/MT7922 (Wi-Fi 6/6E), plus the Filogic
  MT7981/MT7986 routers where CSI extraction was actually demonstrated.

For the CSI toolchain details and how MediaTek compares to Atheros/Intel/Broadcom CSI
paths, cross-link [../projects/csi-toolchains.md](../projects/csi-toolchains.md). For
the firmware-reversing methodology, see
[../docs/firmware-reversing.md](../docs/firmware-reversing.md); for where these sit
against a true SDR, [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

---

## The SDR ladder, MediaTek-flavored

| Rung | What it buys | Best MediaTek/Ralink representative |
|-----:|--------------|-------------------------------------|
| 1 Monitor + Injection | raw 802.11 RX/TX, channel hop, arbitrary frames | **RT3070/RT5372, MT7612U (AWUS036ACM)** — the reference injection dongles |
| 2 PHY telemetry / CSI | per-subcarrier amplitude **and** phase | **MT7915/MT7916**, **MT7981/mt7976** (Filogic) via `mt76` CSI + [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump) |
| 3 Spectral / raw-PHY scan | FFT bins with/without a frame | *partial* — `mt76` has ADC/energy-detect paths but no clean public FFT-dump tool (TODO) |
| 4 Arbitrary waveform TX | author an IQ buffer, transmit it | **not reached** on any MediaTek part with public tooling |
| 5 Open PHY / soft-radio | documented/open firmware | **not reached** — MCU blobs remain closed |

The MediaTek story tops out honestly at **Tier 2**. What makes it special is *how
cheaply and cleanly* Tier 2 is reached: no firmware patch, just an open driver and a
netlink/debugfs plumbing job. The ceiling above Tier 2 is the closed MCU firmware.

---

## Legacy Ralink — the aircrack-ng dongles (`rt2x00` / `rt2800usb`)

For most of the 2005–2015 era, "which adapter does injection?" had a Ralink answer.
The **`rt2x00`** driver family (mac80211, in-tree, open) plus the closed MAC
microcode blobs (`rt2860.bin`, `rt2870.bin`, `rt3070.bin`, `rt73.bin`) delivered
rock-solid **monitor + injection** — **Tier 1** — long before it was common. These
are SoftMAC parts, so mac80211 does the framing and injection "just works."

- **RT2500 / RT2570** — the earliest generation. RT2500 (PCI, `rt2500pci`) and
  RT2570 (USB, historically the out-of-tree `rt2570`/`rt73usb` lineage) were classic
  802.11b/g monitor+injection cards. Tier 1, verified, but obsolete (2.4 GHz b/g only).
- **RT2870 / RT3070** — *the* classic USB injection chipset. 802.11n 1T1R/2T2R,
  2.4 GHz, driven by `rt2800usb`. Enormous device-ID list (D-Link, Sitecom, Alfa
  AWUS036NH, TP-Link TL-WN727N, countless clones). Still the "known-good" cheap
  injection dongle. Tier 1, verified.
- **RT3572** — dual-band 2.4/5 GHz 802.11n (Alfa AWUS051NH etc.), `rt2800usb`.
  Tier 1, verified; valued because it added 5 GHz monitor/injection in the Ralink era.
- **RT5370 / RT5372** — later low-power 1T1R (RT5370) / 2T2R (RT5372) 2.4 GHz n
  parts, `rt2800usb`. Ubiquitous in cheap dongles and Raspberry Pi kits. Tier 1,
  verified; injection quality is good and widely used with aircrack-ng.

**Firmware/RE angle:** `rt2x00`/`rt2800usb` are open GPL drivers, but the on-chip MAC
microcode is a small closed blob loaded from `linux-firmware`. There was never a
"nexmon for Ralink" because there was never a *need* — monitor/injection were already
exposed by the open driver, and nobody unlocked CSI or spectral scan on these legacy
MACs. The firmware is a small proprietary MCU image; **openness: closed**, minimal
public RE tooling. These parts do **not** climb past Tier 1.

---

## MediaTek `mt76` USB parts — MT7601U, MT7610U, MT7612U

The `mt76` driver ([openwrt/mt76](https://github.com/openwrt/mt76), mainline; the
[morrownr/mt76](https://github.com/morrownr/mt76) out-of-tree fork tracks newer chips)
covers the modern USB adapters. All are SoftMAC → monitor/injection via mac80211.

- **MT7601U** (`mt7601u`) — 802.11b/g/n **1T1R** 2.4 GHz, in kernel since 4.2. The
  cheapest "monitor mode" dongle. Monitor works; **injection is flaky/limited** in
  practice (widely reported), so treat it as Tier 1 with an asterisk. Verified monitor,
  reported/partial injection.
- **MT7610U** (`mt76x0u`) — 802.11ac **1T1R** dual-band. Adds 5 GHz monitor/injection
  in a tiny package. Tier 1, verified.
- **MT7612U** (`mt76x2u`) — 802.11ac **2T2R** dual-band, ~866 Mbit/s PHY. This is the
  chip inside the **Alfa AWUS036ACM**, the modern reference monitor/injection adapter,
  mainline since kernel 4.19. Strong, reliable injection on both bands; the default
  recommendation over Realtek RTL88x2 for a "does injection cleanly on stock in-tree
  driver" card. Tier 1, verified. (PCIe sibling **MT7612E**/`mt76x2e` is the same PHY.)

**Firmware/RE angle:** MT76x0/MT76x2 run closed MCU firmware (ROM patch + RAM code)
loaded by the open `mt76` driver. Openness **closed**, but the driver's MCU-command
API is fully in the open — the reason CSI became reachable on the *bigger* siblings.
No public CSI/spectral tool targets the USB parts specifically; they stay Tier 1.

---

## ConnAC AP/router silicon — MT7615, MT7663 (Wi-Fi 5)

- **MT7615** — 802.11ac 4x4 DBDC (dual-band dual-concurrent) AP/router chip; the
  `mt7615` sub-driver also covers **MT7622** (SoC) and **MT7663** (a 2x2 11ac
  client/AP part, also in `mt7663u`/`mt7663s` USB/SDIO forms). Introduces the modern
  ConnAC **dual-MCU** design: **WM** (WiFi-MAC firmware) + **WA** (WiFi-Algorithm /
  offload) loaded sequentially. Tier 1 monitor/injection, verified. CSI hooks are far
  less mature here than on the Wi-Fi 6 family — treat CSI as reported/experimental.

**Firmware/RE angle:** dual MCU, closed WM/WA blobs, rich in-driver MCU command set.
Openness **partially-documented** (the *interface* is open in `mt76`; the *firmware*
is not). RE tooling: ghidra/IDA on the blobs; the practical unlock path is *driver*
patching, not firmware patching.

---

## The Wi-Fi 6 CSI platform — MT7915 / MT7916 (and Filogic MT7981/MT7986)

This is where MediaTek earns its place in an SDR catalog. The **MT7915/MT7916**
(802.11ax AP/router, up to 4x4, 160 MHz) family — and the newer **Filogic**
SoCs **MT7981** (Filogic 820, with the `mt7976` radio) and **MT7986** (Filogic 830) —
support **per-subcarrier Channel State Information export straight out of the box of an
open driver**, reaching **Tier 2**.

- **How the unlock works.** The `mt76` driver added a CSI path that asks the firmware
  MCU to report CSI and relays it to userspace over an **nl80211 vendor command /
  vendor dump** (netlink). **No firmware modification is needed** — the closed MCU
  already computes CSI for its own beamforming/rate-control, and the open driver just
  taps the report channel. [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump)
  packages the driver patch + userland; it was demonstrated on the **OpenWrt One
  (MT7981B / mt7976 radio)** under OpenWrt 24.10. Bandwidths to 160 MHz and up to
  ~512 subcarriers are in reach on 11ax.
- **Metadata & better tooling.** MtkCSIdump emits I/Q but drops source MAC/RSSI/SNR/
  sequence numbers; [ekstra-csi](https://github.com/imxdemetri/ekstra-csi) builds on
  the same patches to preserve that metadata, talking to `mt76` over netlink. Both are
  tracked on the OpenWrt forum thread
  ([CSI extraction for MediaTek](https://forum.openwrt.org/t/csi-extraction-for-mediatek-based-wi-fi-chipsets/244703)).
  Works, in principle, on any `mt76` device exposing the CSI vendor extension —
  GL.iNet, Xiaomi, TP-Link Archer, and other OpenWrt targets on this silicon.
- **Why it matters.** This is the *cheapest, cleanest* route to real Wi-Fi-6 CSI —
  160 MHz, more subcarriers than the old Atheros `ath9k`/`csitool` or Intel 5300
  paths (see [../projects/csi-toolchains.md](../projects/csi-toolchains.md)), on
  commodity routers, with an open driver and no firmware patch. It sits alongside the
  Intel AX210 route ([../chips/intel.md](../chips/intel.md)) and the ESP32
  micro-CSI route ([../chips/espressif.md](../chips/espressif.md)) as one of the three
  practical 2024–2026 CSI stacks.

**Firmware/RE angle:** MT7915/MT7916/MT798x use a **dual-MCU** (WM + WA) design, plus a
**WO** (WiFi-offload) core on Filogic; ConnAC MCUs are ARM-class cores running closed
RAM firmware over a ROM patch. Openness **partially-documented**: the MCU command
protocol, register maps, and CSI report format are effectively open through the `mt76`
source, even though the firmware binary is not redistributably reverse-engineered.
RE tooling: **ghidra/IDA** on the blobs, but — crucially — the *unlock is a driver
patch*, which is why MediaTek CSI arrived without a nexmon-style firmware exploit.

---

## Wi-Fi 6/6E client silicon — MT7921 / MT7922 (and MT7925 Wi-Fi 7)

- **MT7921** (`mt7921e`/`mt7921u`/`mt7921s`) — 802.11ax **2x2** client (M.2, USB, SDIO).
  Inside the **Alfa AWUS036AXM** and many laptop modules. Monitor works; **injection
  is present but historically buggy** in 11ax framing (tracked in `morrownr/USB-WiFi`
  issues). Tier 1, verified monitor / reported-with-caveats injection.
- **MT7922** (`mt7922`, shares `mt7921` driver) — 802.11ax **Wi-Fi 6E** 2x2 client,
  adds the 6 GHz band; inside the **Alfa AWUS036AXML** and many Ryzen/laptop modules.
  Tier 1, verified.
- **MT7925 / MT7927** — **Wi-Fi 7** clients (also covered by `morrownr/mt76`). Newest
  generation; monitor/injection maturing, CSI unexplored publicly. Tracked in TODO.

CSI on the *client* parts (MT7921/22/25) is not yet a turnkey public tool the way it is
on MT7915/MT7981 — **theoretical/reported**, a natural next target since they share the
ConnAC MCU-command lineage.

**Firmware/RE angle:** ConnAC2/3 dual-MCU, closed blobs, open driver. Same
partially-documented posture as the AP family.

---

## Summary table

| Chip / family | Driver | Bands | Best rung | CSI? | Firmware openness | Status |
|---------------|--------|-------|:---------:|:----:|-------------------|--------|
| RT2500 / RT2570 | rt2500pci / rt73usb | 2.4 | 1 | no | closed | verified |
| RT2870 / RT3070 | rt2800usb | 2.4 | 1 | no | closed | verified |
| RT3572 | rt2800usb | 2.4/5 | 1 | no | closed | verified |
| RT5370 / RT5372 | rt2800usb | 2.4 | 1 | no | closed | verified |
| MT7601U | mt7601u | 2.4 | 1* | no | closed | verified (inj. partial) |
| MT7610U | mt76x0u | 2.4/5 | 1 | no | closed | verified |
| MT7612U (AWUS036ACM) | mt76x2u | 2.4/5 | 1 | no | closed | verified |
| MT7615 / MT7663 | mt7615 / mt7663u | 2.4/5 | 1 | exp. | partially-documented | verified (mon/inj) |
| **MT7915 / MT7916** | mt7915 | 2.4/5 | **2** | **yes** | partially-documented | **verified (CSI)** |
| **MT7981 / MT7986 (Filogic)** | mt7915/mt7981 | 2.4/5/6 | **2** | **yes** | partially-documented | **verified (CSI)** |
| MT7921 | mt7921 | 2.4/5 | 1 | reported | partially-documented | verified (mon), inj. caveats |
| MT7922 | mt7921 | 2.4/5/6 | 1 | reported | partially-documented | verified |
| MT7925 / MT7927 (Wi-Fi 7) | mt7925 | 2.4/5/6 | 1 | — | partially-documented | reported |

\* MT7601U monitor verified; injection limited/unreliable.

---

## Un-cataloged / TODO (feeds the next cycle)

- **RT73 / RT2501USB, RT2870-era RT2770/RT2860/RT2890 PCIe** — full device-ID and
  injection-quality matrix across the `rt61pci`/`rt73usb`/`rt2800pci` split.
- **MT7628 / MT7688 (`mt7628`)** — the tiny MIPS SoC Wi-Fi (Onion Omega2, Vocore2);
  monitor/injection profile and whether any CSI/spectral hooks exist.
- **MT7603 / MT7602** — 11n-era `mt76` cores; injection quality vs. the 11ac parts.
- **MT7902 / MT7920** — newer `mt76` client cores (in `morrownr/mt76`); band support
  and CSI potential unprofiled.
- **MT7925 / MT7927 / MT7928 (Wi-Fi 7)** — monitor/injection maturity and any CSI path.
- **Spectral / FFT-bin dump (Tier 3)** — does any `mt76` ConnAC part expose an
  ath9k-style raw spectral/FFT scan? The MCU has energy-detect/ADC paths but no clean
  public FFT-dump tool exists yet. Open question.
- **MT7921/MT7922 client-side CSI** — porting the MT7915 vendor-CSI path to the 2x2
  client MCUs; currently theoretical.
- **Firmware RE depth** — a public ghidra loader / annotated map for the ConnAC WM/WA
  (and Filogic WO) MCU blobs; nothing nexmon-grade exists for MediaTek yet.
