# Modern MediaTek (MT7921 / MT7922 / MT7925): monitor, injection, and the CSI question

*If you are buying a Wi-Fi adapter in 2026 to do raw 802.11 work — monitor mode
and frame injection — and you want it to **just work on a stock, in-tree Linux
driver**, the modern MediaTek Wi-Fi 6/6E/7 client parts are the correct default
answer. This is the buyer-and-bring-up guide for that specific slice of the `mt76`
family: the **MT7921** (Wi-Fi 6/6E), **MT7922** (Wi-Fi 6E), and **MT7925**
(Wi-Fi 7) client silicon you find in cheap USB dongles and M.2 cards — what carries
each chip, why the mainline `mt76` driver makes them a genuinely good choice
(contrast the Realtek out-of-tree DKMS grind), how to set monitor and inject, and
the honest state of CSI on these client parts.*

> This file is deliberately narrow — the **client** parts. For the family-wide
> treatment (the MT7612U reference dongle, the MT7915/MT7981 CSI *AP* platform,
> radiotap TX fields, the full toolchain), read the companion guide
> [mt76-monitor-injection-csi.md](mt76-monitor-injection-csi.md). Silicon and
> per-chip rungs: [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md).
> Cross-vendor injection support matrix:
> [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md).
> Ladder definitions: [../taxonomy.md](../taxonomy.md).

---

## 0. TL;DR

| | MT7921 (Filogic 380) | MT7922 (Filogic 380) | MT7925 (Filogic 360/680) |
|---|---|---|---|
| **Standard** | Wi-Fi 6 / 6E, 2×2 | Wi-Fi 6E, 2×2 | **Wi-Fi 7 (802.11be)**, 2×2 |
| **Bands** | 2.4 / 5 (/6) GHz | 2.4 / 5 / 6 GHz | 2.4 / 5 / 6 GHz |
| **Typical form factor** | **USB** dongle (MT7921AU) + M.2 | **M.2** card | M.2 + newest **USB** dongles |
| **mt76 sub-driver** | `mt7921e` / `mt7921u` / `mt7921s` | `mt7921e` (shared) | `mt7925e` / `mt7925u` |
| **In mainline since** | PCIe 5.12, **USB 5.18** | 5.16 | **6.7** (USB later) |
| **Monitor** | **Tier 1 — verified** | Tier 1 — verified | Tier 1 — verified |
| **Injection** | works; **HE-rate caveats** (see §4) | works; HE-rate caveats | maturing (EHT newest) |
| **CSI** | no turnkey tool — **theoretical** | theoretical | theoretical |

**The one-line pitch:** monitor + injection cost you *nothing special* — no
out-of-tree build, no firmware patch, no pinned kernel. Plug in, `iw ... type
monitor`, inject with aircrack-ng. That is the whole reason to prefer these over a
Realtek RTL88x2/8832 dongle, whose monitor/injection lives in an out-of-tree DKMS
module you must rebuild against every kernel bump. **CSI is the honest weak spot:**
unlike the MT7915/MT7981 *AP* silicon, there is no public turnkey CSI tool for the
2×2 *client* parts — treat client-side MediaTek CSI as unproven/theoretical today.

---

## 1. Why the modern MediaTek client parts are the good default

Three structural facts, none of which hold for Realtek's popular monitor dongles:

1. **`mt76` is a real mainline `mac80211` SoftMAC driver.** It lives at
   `drivers/net/wireless/mediatek/mt76/` in the Linux tree and is developed in the
   open at [openwrt/mt76](https://github.com/openwrt/mt76). Because `mac80211`
   builds and sequences frames, **monitor mode and injection are driver features
   you already have** — not capabilities you unlock. Any current distro
   (kernel ≥ 5.18 for MT7921 USB) already ships the driver; nothing to compile.

2. **The MCU firmware stays closed, but you never touch it for Tier 1.** The chips
   run closed ConnAC2/ConnAC3 MCU blobs (a **WM** WiFi-MAC core + a **WA**
   WiFi-Algorithm core) from `/lib/firmware/mediatek/`. Unlike Broadcom's D11 ucode
   — where monitor/CSI *are inside* the firmware and must be patched with Nexmon —
   the MediaTek monitor/inject path is entirely driver-side. No exploit, no reflash.

3. **Contrast: the Realtek out-of-tree tax.** The go-to Realtek monitor dongles
   (RTL8812AU/8814AU/8832AU — `88XXau`, `8852au`) reach monitor/injection only
   through **out-of-tree DKMS drivers** (`aircrack-ng/rtl8812au`,
   `morrownr/8852au`, etc.). Those must be rebuilt on every kernel update, break on
   HWE/rolling kernels, need Secure Boot MOK signing, and vary in injection quality
   per fork. The MediaTek parts sidestep *all* of that: the injection-capable driver
   is the one already in your kernel. See
   [rtl8812au-monitor-injection.md](rtl8812au-monitor-injection.md) for the pain
   this avoids, and [../../chips/realtek.md](../../chips/realtek.md).

**The catch, stated up front:** these are 2×2 802.11ax/be *client* MCUs. HE/EHT
rate injection is less battle-tested than legacy/HT (§4), and — unlike the MediaTek
*AP* silicon — they have no public CSI tool (§5). For rock-solid arbitrary-rate
injection specifically, the older **MT7612U (Alfa AWUS036ACM)** is still the safest
`mt76` pick; the modern client parts win on band coverage (6 GHz), availability,
and being current silicon.

---

## 2. Which hardware carries these chips

### USB adapters (plug-and-play, no internal install)

| Adapter | Chip | Driver | Bands | Notes |
|---|---|---|---|---|
| **Alfa AWUS036AXM** | MT7921AU(N) | `mt7921u` | 2.4/5/6 | USB-A; tri-band Wi-Fi 6E; BT 5.2 on-die |
| **Alfa AWUS036AXML** | MT7921AU(N) | `mt7921u` | 2.4/5/6 | USB-C; longer-range antenna variant of the AXM |
| **Netgear A9000** | MT7925 | `mt7925u` | 2.4/5/6 | first **Wi-Fi 7** USB adapter (mid-2025); needs a recent `mt7925u` kernel |
| Various no-name MT7921AU dongles | MT7921AU | `mt7921u` | 2.4/5/(6) | cheap; same driver, verify VID:PID `0e8d:7961`/`7922` |

> **Chip-vs-adapter reality check.** Current Alfa spec sheets list **MT7921AUN**
> for *both* the AXM and AXML — the "L" is the longer-antenna/USB-C variant, not a
> different chip. **MT7922 is the M.2 die**, not what ships in these USB Alfas.
> Always confirm with `lsusb` / `ethtool -i`, not the marketing name, because Alfa
> has reused model names across silicon revisions.

### M.2 / laptop cards (internal, PCIe)

| Card | Chip | Driver | Bands |
|---|---|---|---|
| **AMD RZ608** (MediaTek MT7921K) | MT7921 | `mt7921e` | 2.4/5/6 |
| **AMD RZ616** (MediaTek MT7922) | MT7922 | `mt7921e` | 2.4/5/6 |
| **AMD RZ717 / MediaTek MT7925** modules | MT7925 | `mt7925e` | 2.4/5/6 |
| Countless OEM Wi-Fi 6E/7 M.2 2230 modules | MT7921/22/25 | `mt7921e`/`mt7925e` | 2.4/5/6 |

The M.2 MT7922 (AMD RZ616) is extremely common in 2022+ Ryzen laptops — meaning a
huge number of machines already have an injection-capable `mt76` radio soldered in.
That is a quiet advantage: no dongle purchase to do lab monitor/inject work.

### Confirm what you actually have before anything else

```bash
lsusb                                    # MediaTek USB VID is 0e8d: (e.g. 0e8d:7961 MT7921U)
lspci -nn | grep -i -E '14c3|mediatek'   # M.2: MediaTek PCI vendor 14c3
iw dev                                    # list wiphy / interfaces
ethtool -i wlan0                          # 'driver: mt7921u' / mt7921e / mt7925e ...
dmesg | grep -i -E 'mt7921|mt7922|mt7925|mt76'   # WM/WA firmware load, ROM patch
```

You want `ethtool -i` to name an `mt7921*`/`mt7925*` driver and `dmesg` to show the
WM/WA blobs loading without error. If `dmesg` complains about a missing
`mediatek/….bin`, update `linux-firmware`.

---

## 3. Monitor mode

`mt76` is `mac80211`, so this is the ordinary Linux path — identical to the family
guide, repeated here so this file stands alone.

**(a) Add a dedicated monitor VIF (preferred — leaves the managed vif intact):**

```bash
PHY=wlan0
sudo ip link set $PHY down                       # some mt76 parts refuse type-change while UP
sudo iw dev $PHY interface add mon0 type monitor
sudo ip link set mon0 up
sudo iw dev mon0 set channel 6                    # 2.4 GHz ch6
# 6 GHz example (needs reg domain that allows it):
# sudo iw dev mon0 set freq 5955                  # 6 GHz ch1 (6E)
```

**(b) The aircrack-ng shortcut:**

```bash
sudo airmon-ng check kill                         # stop NetworkManager/wpa_supplicant
sudo airmon-ng start wlan0                         # creates wlan0mon
sudo airodump-ng wlan0mon                          # live survey confirms RX works
```

Capture with the usual tools; every frame carries a **radiotap** header the driver
prepends (RSSI, channel, HE/EHT rate, FCS status):

```bash
sudo tcpdump -i mon0 -w capture.pcap
sudo wireshark -k -i mon0
```

**Client-part monitor notes (accurate, not folklore):**

- **6 GHz capture needs a permissive regulatory domain.** Set your country first
  (`sudo iw reg set US`, or your real CC); 6 GHz channels are gated by reg rules and
  will silently not tune otherwise.
- **160 MHz** capture works on the parts that support it (all three here), limited
  by silicon, not the driver. Wi-Fi 7 320 MHz on MT7925 is newest and least tested.
- On some parts the PHY only tunes once the vif is `up`; if `set channel` fails,
  bring the interface up first, then set the channel.
- Monitor is **verified Tier 1** across MT7921/7922/7925 — the mature, boring case.

---

## 4. Injection

Because `mac80211` builds the frames, injection is the standard radiotap-TX path —
no special IOCTLs, no firmware unlock. Any monitor interface the driver marks
injection-capable transmits a frame you hand it with a radiotap header on the front.

### 4.1 Verify the card injects at all

```bash
sudo aireplay-ng --test mon0        # aircrack-ng's canonical injection test
```

A healthy card prints ascending `Ping` responses and an injection-success
percentage. `0%` usually means a wrong/locked channel, an unset reg domain clamping
TX power to zero, or `NetworkManager`/`wpa_supplicant` still owning the radio
(`airmon-ng check kill`).

### 4.2 Inject with aircrack-ng (test only against your own lab — see §6)

```bash
# Deauth (your OWN network / lab devices only)
sudo aireplay-ng --deauth 5 -a AA:BB:CC:DD:EE:FF mon0
```

### 4.3 Hand-built frame with scapy (full radiotap control)

```python
#!/usr/bin/env python3
# sudo python3 inject.py   — interface already in monitor mode on your channel
from scapy.all import RadioTap, Dot11, Dot11Beacon, Dot11Elt, sendp

frame = (
    RadioTap() /
    Dot11(type=0, subtype=8,                        # management / beacon
          addr1="ff:ff:ff:ff:ff:ff",
          addr2="02:00:00:11:22:33",                # SA (locally-administered)
          addr3="02:00:00:11:22:33") /
    Dot11Beacon(cap="ESS") /
    Dot11Elt(ID="SSID", info="latent-radios-test") /
    Dot11Elt(ID="Rates", info=b"\x82\x84\x8b\x96\x0c\x12\x18\x24")
)
sendp(frame, iface="mon0", count=100, inter=0.1)     # 100 beacons, 10/s
```

Watch it land on a second card (`airodump-ng` on another radio should list the
SSID). That proves the whole TX path end-to-end.

### 4.4 The honest injection caveats for these client parts

- **Legacy / HT / VHT injection is reliable.** For 802.11a/b/g/n/ac-rate frames
  the MT7921/22 inject cleanly and are fine for deauth testing, fuzzing, replay,
  and beacon flooding in a lab.
- **HE (802.11ax) rate injection has a history of bugs** on MT7921/22 — frames may
  go out at a fallback rate or be dropped when you force a specific HE MCS via the
  radiotap HE field. This is a tracked driver/MCU-framing issue (see the
  `morrownr/USB-WiFi` issue tracker), not user error; it has improved across kernel
  releases but is still less bulletproof than the older MT7612U. If you must inject
  at a *precise* rate, validate on your exact kernel, or use MT7612U/MT7915.
- **EHT (Wi-Fi 7) injection on MT7925 is newest and least proven.** Monitor is
  solid; forced-EHT-rate injection is bleeding-edge — verify empirically.
- **Injection ≠ arbitrary waveform.** These parts emit *well-formed 802.11 frames
  at MCU-supported rates*, never an author-your-own IQ buffer. There is no MediaTek
  path to Tier 4 with public tooling — reach for a real SDR
  ([../true-sdr-comparison.md](../true-sdr-comparison.md)).

For the full radiotap TX-field table (Rate / MCS / VHT / HE, NO_ACK, NO_SEQ), see
§4.4 of [mt76-monitor-injection-csi.md](mt76-monitor-injection-csi.md).

---

## 5. The CSI question — the honest state on the *client* parts

This is where the modern client story diverges sharply from the MediaTek *AP*
story, and it is the section to read slowly.

**What exists on MediaTek CSI is real, but it is on the AP/router silicon, not
these chips.** Per-subcarrier Channel State Information (complex `H`, amplitude
*and* phase) is extracted from **MT7915/MT7916 and the Filogic SoCs MT7981/MT7986**
by *patching the `mt76` driver* (not the firmware) and building an OpenWrt image —
the [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump) and
[ekstra-csi](https://github.com/imxdemetri/ekstra-csi) research toolchains. The
reference platform is the **OpenWrt One (MT7981B)**. That whole path is documented
in §5 of [mt76-monitor-injection-csi.md](mt76-monitor-injection-csi.md).

**For MT7921 / MT7922 / MT7925 specifically, there is no turnkey public CSI tool:**

- **Stock `mt76` exports no CSI** on any part — CSI is always an out-of-tree patch.
- The demonstrated CSI vendor-command path targets the **4×4 AP MCUs**
  (MT7915/MT798x), not the 2×2 client MCUs. The client parts share the ConnAC
  MCU-command lineage, so porting the CSI report path to them is *plausible* — the
  closed MCU already computes CSI for its own beamforming — but it is **currently
  unproven in public**. Treat client-side MediaTek CSI as **theoretical**.
- If you need Wi-Fi CSI *this afternoon*, do not start here. Use an **ESP32**
  (vendor-documented `esp-csi`, a $3 turnkey CSV-over-UART path —
  [esp32-csi-motion-detection.md](esp32-csi-motion-detection.md)), a **Broadcom Pi**
  (Nexmon CSI — [nexmon-csi-to-usable-csi.md](nexmon-csi-to-usable-csi.md)), or an
  **Intel AX200/AX210** (FeitCSI — [ax-csi-intel-ax200-ax210.md](ax-csi-intel-ax200-ax210.md)).
  If you want cheap Wi-Fi-6 CSI on MediaTek, buy an **OpenWrt One** (AP silicon),
  not an MT7921 dongle.

So the client-part scorecard is honest and short: **Tier 1 (monitor + injection),
verified, on a stock in-tree driver — and that is the whole value proposition.**
CSI and spectral scan do not come with these chips today.

---

## 6. Regulatory & safety notes

- **Monitor mode is passive** — pure RX, transmits nothing, legal to run on any
  band your hardware and regulatory domain allow. Set `iw reg set <CC>` so 5/6 GHz
  channels are permitted and TX power is sane.
- **Injection transmits real 802.11 frames** on licence-exempt bands. Keep it on
  channels and TX-power levels legal in your region, and inject **only against
  networks and devices you own or are explicitly authorised to test.** Deauth /
  disassoc floods against third-party networks are illegal in most jurisdictions.
- **6 GHz (6E/Wi-Fi 7) has stricter rules** than 2.4/5 GHz in many regions
  (indoor-only / low-power, AFC where required). Confirm your reg domain before any
  6 GHz TX.
- **No arbitrary-waveform TX exists here.** Injection emits standard Wi-Fi frames at
  MCU-supported rates; there is no IQ-authoring path on this silicon.

---

## References

**Driver / primary source**

- `mt76` upstream tree (Felix Fietkau / OpenWrt): <https://github.com/openwrt/mt76>
- Mainline location `drivers/net/wireless/mediatek/mt76/` (contains `mt7921`,
  `mt7925`, `mt7996` sub-drivers): <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/mediatek/mt76>
- `morrownr/USB-WiFi` — per-adapter monitor/injection notes, chip↔driver map:
  <https://github.com/morrownr/USB-WiFi>

**Monitor / injection**

- Linux Wireless — monitor mode & radiotap injection: <https://wireless.docs.kernel.org/en/latest/en/users/documentation/monitor.html>
- radiotap header (TX fields): <https://www.radiotap.org/>
- aircrack-ng suite (`aireplay-ng`, `airodump-ng`, `airmon-ng`): <https://www.aircrack-ng.org/>

**Hardware**

- Alfa AWUS036AXM (MT7921AUN, tri-band Wi-Fi 6E USB): <https://www.alfa.com.tw/products/awus036axm>
- Alfa AWUS036AXML (MT7921AUN, USB-C long-range): <https://www.alfa.com.tw/products/awus036axml>

**CSI context (why client parts are not the CSI path)**

- MtkCSIdump — `mt76` CSI patch + OpenWrt server (AP silicon): <https://github.com/MtkWifiRev/MtkCSIdump>
- ekstra-csi — metadata-preserving MediaTek CSI over netlink: <https://github.com/imxdemetri/ekstra-csi>
- OpenWrt forum — "CSI extraction for MediaTek-based Wi-Fi chipsets": <https://forum.openwrt.org/t/csi-extraction-for-mediatek-based-wi-fi-chipsets/244703>

**This catalog**

- Family-wide `mt76` guide: [mt76-monitor-injection-csi.md](mt76-monitor-injection-csi.md)
- MediaTek / Ralink silicon & per-chip rungs: [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md)
- Monitor/injection support matrix: [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md)
- The Realtek out-of-tree contrast: [rtl8812au-monitor-injection.md](rtl8812au-monitor-injection.md) · [../../chips/realtek.md](../../chips/realtek.md)
- Ladder / tier definitions: [../taxonomy.md](../taxonomy.md)
- Why injection ≠ arbitrary waveform: [../true-sdr-comparison.md](../true-sdr-comparison.md)
