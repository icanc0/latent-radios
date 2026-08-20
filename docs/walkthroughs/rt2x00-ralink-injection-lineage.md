# The rt2x00 / Ralink injection lineage

> **Scope.** How Ralink's cheap USB radios and the `rt2x00` (plus the older
> out-of-tree `rt2570`/`rt73`) drivers made **monitor + injection** — SDR-ladder
> **Tier 1** — a commodity in the aircrack-ng era, which specific dongles became the
> canonical wardriving sticks, and how that whole lineage folded into today's
> `mt76`. This is the *retro / driver-history* companion to the chip catalog in
> [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) — read that file
> for the modern MediaTek CSI story and the already-cataloged RT2500/RT2570/
> RT2870/RT3070/RT3572/RT5370 records. This page does **not** duplicate those; it
> adds the net-new *retro* parts (RT73, RT61, RT2860-PCI, RT5572) and the practical
> setup on a surviving RT3070 stick.

None of these parts climb past **Tier 1**. There was never a "nexmon for Ralink"
because there never needed to be one: the open GPL SoftMAC driver already exposed
raw 802.11 RX and TX, and nobody unlocked CSI or spectral scan on these legacy MACs.
The value here is historical and practical — this is the hardware that taught a
generation what monitor mode and packet injection *were*.

---

## Why Ralink owned the injection era

For roughly **2005–2015**, the answer to "which cheap adapter actually does
injection?" was almost always a Ralink one. Three structural facts made it so:

1. **SoftMAC parts.** Ralink USB/PCI radios are SoftMAC — the 802.11 MLME and
   framing live in the host `mac80211` stack, not in on-chip firmware. That means
   `mac80211` builds the frames, so **monitor mode and injection "just work"** once
   the driver hands the PHY raw TX. No closed full-MAC to fight (contrast Broadcom
   FullMAC, which needed [nexmon](nexmon-csi-to-usable-csi.md)).
2. **A tiny, redistributable firmware blob.** The only closed piece is a small
   on-chip MAC microcode image (`rt2561.bin`, `rt2661.bin`, `rt73.bin`, `rt2860.bin`,
   `rt2870.bin`, `rt3070.bin`) shipped in `linux-firmware`. Openness is **closed**,
   but it is small, loads cleanly, and never blocked injection.
3. **Cheap silicon, everywhere.** Ralink chips were the low-cost default in D-Link,
   Linksys, Sitecom, TP-Link, Belkin and a sea of no-name dongles — so a working
   injection adapter cost a few dollars and was easy to find.

Ralink Technology (founded 2001, Cupertino → Hsinchu) was **acquired by MediaTek on
5 May 2011**. The driver lineage outlived the brand: `rt2x00`/`rt2800usb` for the
legacy parts, and `mt76` for everything from the MT7601U onward.

---

## The driver family tree

The upstream, in-tree, `mac80211`-based **`rt2x00`** framework began life in the
community **serialmonkey** project ("Enhanced rt2x00 / legacy rt2500/rt2570/rt73/rt61
drivers") and was built from *partial* Ralink documentation plus GPL vendor code. It
was progressively mainlined (RT2x00 PCI/USB parts landed around Linux 2.6.24–2.6.31).
Sub-drivers, by die:

| Sub-driver | Chipsets (dies) | Bus | Std | Firmware blob | Notes |
|------------|-----------------|-----|-----|---------------|-------|
| `rt2400pci` | RT2460 | PCI | 11b | — | earliest generation |
| `rt2500pci` | RT2560 | PCI | 11b/g | — | *(cataloged as RT2500)* |
| `rt2500usb` | RT2571, RT2572 | USB | 11b/g | — | *(cataloged as RT2570)* |
| **`rt61pci`** | RT2561, RT2561S, RT2661 | PCI/MiniPCI | 11g | `rt2561*.bin`, `rt2661.bin` | **net-new here → `ralink-rt61`** |
| **`rt73usb`** | RT2571W, RT2573, RT2671 | USB | 11b/g | `rt73.bin` | **net-new here → `ralink-rt73`** |
| **`rt2800pci`** | RT2760, RT2790, RT2860, RT2880, RT2890, RT3090/91/92, RT3390, RT3060/62, RT3290, RT3562/92, RT5390/92 | PCI/MiniPCIe | 11n | `rt2860.bin` | **PCI 11n → net-new `ralink-rt2860`** |
| `rt2800usb` | RT2770, RT2870, RT3070/71/72, RT3370, RT3572, RT5370, **RT5572** | USB | 11n | `rt2870.bin`, `rt3070.bin` | *(RT2870/RT3070/RT3572/RT5370 cataloged; **RT5572 net-new → `ralink-rt5572`**)* |

`rt2800lib` is the shared core behind both `rt2800pci` and `rt2800usb`. Monitor mode
is **"Yes" across PCI/USB/MiniPCI** in the upstream capability matrix; injection is
supported everywhere the PHY exposes raw TX (all of the above).

### The legacy out-of-tree drivers (pre-`mac80211`)

Before `rt2x00` matured, aircrack users ran the **serialmonkey legacy drivers** — the
standalone **`rt2570`** (for RT2570) and **`rt73`** (for RT2573), plus the famous
**"ASPj mods"** that patched in injection. Their fingerprints are all over old
tutorials:

- Interfaces were named **`rausb0`** (USB) / `raX` — not `wlanX`/`wmaster0` — so a
  tutorial that says `rausb0` is a legacy-driver tutorial.
- Monitor: `iwconfig rausb0 mode monitor` (or `airmon-ng start rausb0`).
- **Injection had to be armed explicitly:** `iwpriv rausb0 rfmontx 1` before
  `aireplay-ng` would transmit.
- A notorious quirk: the radio would **freeze after ~700–1000 injected packets**, so
  people throttled with `aireplay-ng -x 100..250` to cap the injection rate.

These were superseded by in-tree `rt73usb`/`rt2500usb` once `mac80211` injection was
solid, but the legacy drivers are why RT2570/RT73 sticks became early aircrack folklore.

---

## The go-to dongles

The hardware that made this lineage famous:

| Dongle | Chipset (die) | Driver | Bands | Why it mattered |
|--------|---------------|--------|-------|-----------------|
| **Alfa AWUS036NH** | **RT3070** | `rt2800usb` | 2.4 | *The* long-range aircrack stick — high-power PA, RP-SMA, rock-solid injection |
| **Alfa AWUS036NHR / NHR v2** | RT3070 / RT3070L | `rt2800usb` | 2.4 | consumer-cased NH; same silicon, same injection |
| **Alfa AWUS051NH** | **RT3572** | `rt2800usb` | 2.4/5 | first easy **dual-band** monitor/injection stick in this family |
| D-Link DWL-G122 (C1/rev C) | **RT2573 (RT73)** | `rt73usb` / legacy `rt73` | 2.4 | ubiquitous early-2000s injection dongle |
| Linksys WUSB54GC | **RT2573 (RT73)** | `rt73usb` | 2.4 | the "just works" USB g adapter of the era |
| TP-Link TL-WN727N, Sitecom, countless clones | RT3070 / RT5370 | `rt2800usb` | 2.4 | cheap, everywhere, known-good injection |
| ASUS USB-N53 and dual-band clones | **RT5572** | `rt2800usb` | 2.4/5 | later 2T2R dual-band n, good injection |

The RT3070-based **AWUS036NH** in particular was for years the single most-recommended
adapter in Kali/BackTrack guides, WEP-cracking tutorials, and Wi-Fi security courses.

---

## How this fed into `mt76`

When MediaTek absorbed Ralink, new silicon moved to a fresh driver, **`mt76`**
([openwrt/mt76](https://github.com/openwrt/mt76)), starting with the **MT7601U**. The
continuity is real: still SoftMAC, still `mac80211` framing, still monitor/injection
"for free," still a small closed MCU blob loaded by an open driver. The modern
reference injection stick, the **Alfa AWUS036ACM (MT7612U, `mt76x2u`)**, is the direct
spiritual heir of the AWUS036NH — same vendor lineage, same "clean injection on the
in-tree driver" promise, now dual-band 11ac. And it is precisely `mt76`'s *open
driver + MCU-command protocol* posture — inherited from this Ralink open-driver
culture — that later made **CSI on MT7915/MT7981 reachable without a firmware patch**.
See [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) and the
[mt76 monitor/injection/CSI walkthrough](mt76-monitor-injection-csi.md).

**Bottom line:** the Ralink era set the expectation that a cheap Wi-Fi dongle *should*
do monitor + injection on an open in-tree driver. `mt76` kept that promise; the Tier-1
ceiling (closed MAC/MCU microcode, no CSI/spectral on the legacy parts) also carried
over until the Wi-Fi-6 `mt76` CSI unlock.

---

## Net-new retro parts added this cycle

These are **not** in [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md)
and are added here to complete the retro lineage. All are **Tier 1**, SoftMAC,
monitor + injection via `mac80211`, closed on-chip MAC microcode, **no CSI/spectral**.

- **`ralink-rt73`** — RT2573 / RT2571W / RT2671, `rt73usb` (+ legacy serialmonkey
  `rt73`). The classic early USB injection chipset (DWL-G122, WUSB54GC). 2.4 GHz b/g.
- **`ralink-rt61`** — RT2561 / RT2561S / RT2661, `rt61pci`. The 802.11g PCI/MiniPCI
  sibling of RT73; injection-capable, common in mid-2000s laptops and desktop cards.
- **`ralink-rt2860`** — RT2760 / RT2860 / RT2790 / RT2890, `rt2800pci`. The first-gen
  802.11n PCI/MiniPCIe Ralink MAC — the internal-card counterpart to the RT2870 USB
  parts; monitor/injection via `rt2800pci`.
- **`ralink-rt5572`** — later low-power **dual-band 2T2R** 802.11n USB die,
  `rt2800usb`. The 5 GHz-capable 2T2R cousin of RT5370/RT5372; good injection.

---

## Practical: monitor + injection on a surviving RT3070 stick

> **Legal / RF-safety note.** Monitor mode is passive and generally fine. **Packet
> injection is active transmission** — `aireplay-ng`, deauth, fake-auth, replay all
> put energy on the air and may be **illegal** against networks you do not own or
> lack written authorization to test, and can violate radio regulations. Test only on
> **your own** hardware, on channels you are licensed to use, ideally in a
> shielded/conducted setup or against a lab AP. See
> [../rf-safety-and-legal.md](../../docs/rf-safety-and-legal.md).

Assume an Alfa AWUS036NH (or any RT3070/RT5370 clone). All commands as root on a
modern Linux (`aircrack-ng` ≥ 1.6, `iw`, in-tree `rt2800usb`).

**1. Identify the stick and confirm the driver binds.**
```bash
lsusb | grep -i ralink                  # e.g. 148f:3070 Ralink RT2870/RT3070
dmesg | grep -iE 'rt2800usb|rt3070'     # driver + rt3070.bin firmware load
ethtool -i wlan0 | grep driver          # -> driver: rt2800usb
iw list | sed -n '/Supported interface modes/,/Band/p'   # must list "monitor"
```
If the firmware blob is missing, install `linux-firmware` (provides `rt2870.bin` /
`rt3070.bin`); `rt2800usb` refuses to bring the PHY up without it.

**2. Stop interfering processes.**
```bash
airmon-ng check kill      # kills NetworkManager/wpa_supplicant that would hop channels
```

**3. Enter monitor mode.** Either the airmon-ng way or the plain `iw` way:
```bash
# airmon-ng (creates wlan0mon)
airmon-ng start wlan0

# --- or, explicit iw ---
ip link set wlan0 down
iw dev wlan0 set type monitor        # some builds prefer: iw dev wlan0 interface add mon0 type monitor
ip link set wlan0 up
iw dev wlan0 set channel 6           # park on a channel (or let airodump hop)
iw dev                                # confirm type "monitor"
```

**4. Confirm injection actually works** (this is the whole point of a Ralink stick):
```bash
aireplay-ng --test wlan0mon
# Expect: "Injection is working!" and a list of APs that ACK the test frames.
```

**5. Passive capture / channel hop:**
```bash
airodump-ng wlan0mon                       # hop all 2.4 GHz channels, list APs+clients
airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w cap wlan0mon   # lock one BSSID, write pcap
```

**6. (Authorized lab only) an active example** — e.g. a client-deauth to force a
handshake capture on **your own** AP:
```bash
aireplay-ng -0 3 -a AA:BB:CC:DD:EE:FF -c 11:22:33:44:55:66 wlan0mon
```

**7. Tear down cleanly:**
```bash
airmon-ng stop wlan0mon
systemctl restart NetworkManager     # restore normal networking
```

**Legacy-driver equivalents** (if you are on a museum-piece RT2570/RT73 out-of-tree
stack with a `rausb0` interface):
```bash
iwconfig rausb0 mode monitor
iwpriv  rausb0 rfmontx 1              # ARM injection (ASPj-mod path)
aireplay-ng -x 150 --test rausb0     # -x throttles to dodge the ~700-1000-pkt freeze
```

---

## Firmware / RE angle (why it stops at Tier 1)

`rt2x00`, `rt61pci`, `rt73usb`, `rt2800pci`, `rt2800usb` are **open GPL** drivers, but
the on-chip MAC microcode (`rt2561.bin`, `rt2661.bin`, `rt73.bin`, `rt2860.bin`,
`rt2870.bin`, `rt3070.bin`) is a small **closed** proprietary MCU image loaded from
[`linux-firmware`](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git).
No public project reverse-engineered or patched it to expose CSI, spectral scan, or
arbitrary-waveform TX — there was no demand, because monitor + injection were already
handed over by the open driver. So these parts are honest **Tier 1**: raw RX, raw TX,
channel control, arbitrary 802.11 frame injection — and nothing above that. For the
tiers above (CSI on Wi-Fi 6 `mt76`), cross over to
[../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) and
[mt76-monitor-injection-csi.md](mt76-monitor-injection-csi.md).

---

## References

- Linux-wireless `rt2x00` driver page (supported chipsets, sub-drivers, monitor
  support): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/rt2x00.html>
- serialmonkey — the community rt2x00 / legacy rt2570 / rt73 / rt61 project:
  <http://rt2x00.serialmonkey.com/>
- aircrack-ng driver compatibility (kernel/`mac80211` monitor+injection notes):
  <https://www.aircrack-ng.org/doku.php?id=compatibility_drivers>
- aircrack-ng RT73 driver notes (`rausb0`, `iwpriv rfmontx 1`, `-x` throttle):
  <https://www.aircrack-ng.org/doku.php?id=rt73>
- aircrack-ng — general monitor/injection tutorial: <https://www.aircrack-ng.org/doku.php?id=tutorial>
- Ralink Technology (history, MediaTek acquisition 2011): <https://en.wikipedia.org/wiki/Ralink>
- `linux-firmware` (Ralink MAC microcode blobs):
  <https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git>
- Chip catalog / modern MediaTek CSI: [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md)
