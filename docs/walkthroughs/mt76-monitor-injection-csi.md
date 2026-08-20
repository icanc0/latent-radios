# MediaTek `mt76`: Monitor, Injection, and the Honest State of CSI

*The `mt76` driver is the single nicest place in the Wi-Fi world to do raw
802.11 work on stock, in-tree code. Monitor mode and frame injection need **no
out-of-tree build, no firmware patch, no vendor SDK** — they fall out of a fully
open, mainline `mac80211` SoftMAC driver. This is the reproducible bring-up guide
for both, followed by a candid accounting of where MediaTek CSI actually stands:
real, but far less turnkey than Broadcom (Nexmon), Intel (FeitCSI), or the ESP32.*

> Cross-links: silicon + driver background in
> [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) ·
> the full CSI toolchain survey in
> [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md) ·
> ladder definitions in [../taxonomy.md](../taxonomy.md) ·
> where Tier-4 begins in [../verification-tier4.md](../verification-tier4.md) ·
> the Atheros equivalent of this guide in
> [atheros-ath9k-spectral-csi.md](atheros-ath9k-spectral-csi.md).

---

## 0. TL;DR — what `mt76` gives you and what it costs

| Capability | Ladder rung | Out-of-tree build? | Firmware patch? | Public tooling |
|---|---|:---:|:---:|---|
| **Monitor mode** (raw 802.11 RX + radiotap) | **Tier 1** | **No** — mainline `mt76` | **No** | `iw`, `tcpdump`, `wireshark`, `airodump-ng` |
| **Injection** (arbitrary 802.11 frames) | **Tier 1** | **No** — mainline `mt76` | **No** | `aireplay-ng`, `mdk4`, `packetforge-ng`, `scapy` |
| **CSI** (per-subcarrier complex `H`) | **Tier 2** | **Yes** — patched `mt76` (research) | **No** (driver patch, not firmware) | [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump), [ekstra-csi](https://github.com/imxdemetri/ekstra-csi) |
| Spectral / raw-FFT scan | Tier 3 | — | — | **none public** (no `ath9k`-style dump) |
| Arbitrary-waveform TX | Tier 4 | — | — | **not reachable** — MCU blobs are closed |

**The headline:** for Tier 1 you do *nothing special*. Any modern distro already
ships `mt76`; you set a monitor interface with `iw` and inject with the standard
aircrack-ng tools. That is the whole appeal — no Nexmon-style firmware exploit, no
DKMS fight, no pinned kernel. CSI is where it gets honest: it exists, it is real
Wi-Fi-6 CSI, but it means building a **patched driver from a research repo** and
running on **OpenWrt on specific silicon**, not `pip install`.

---

## 1. Why `mt76` is the friendliest open Wi-Fi driver for raw work

Four structural facts, none of which hold for Broadcom or (fully) for Intel:

1. **It is a real `mac80211` SoftMAC driver, in mainline.** `mt76` lives at
   `drivers/net/wireless/mediatek/mt76/` in the Linux tree and is developed in the
   open at [openwrt/mt76](https://github.com/openwrt/mt76) (Felix Fietkau / the
   OpenWrt team). Because framing, sequencing, and the monitor/inject plumbing are
   done by `mac80211` — not hidden inside firmware — monitor and injection are
   *driver features you already have*, not capabilities you must unlock.

2. **The MCU firmware stays closed, but you never have to touch it for Tier 1.**
   The chips run closed ConnAC MCU blobs (a **WM** WiFi-MAC core + a **WA**
   WiFi-Algorithm core, plus a **WO** offload core on Filogic), loaded from
   `/lib/firmware/mediatek/`. Unlike Broadcom's D11 ucode — where monitor/CSI *are*
   inside the firmware and must be patched (see [../../projects/nexmon.md](../../projects/nexmon.md))
   — MediaTek's monitor/inject path is entirely driver-side.

3. **The driver's MCU-command protocol is open source.** Every register write and
   MCU command the closed firmware understands is visible in the `mt76` C source.
   That is *why* CSI became reachable by patching the driver rather than the
   firmware — the closed MCU already computes CSI for its own beamforming; the
   open driver just has to ask for the report and relay it (see §5).

4. **One driver, a decade of silicon.** `mt76` covers the USB dongles
   (`mt7601u`, `mt76x0u`/MT7610U, `mt76x2u`/MT7612U), the 11ac/ax AP+client SoCs
   (`mt7615`, `mt7915`/MT7916, `mt7921`/MT7922), and the Wi-Fi 7 parts
   (`mt7925`, `mt7996`). The same `iw`/radiotap workflow applies to all of them.

**Consequence for this catalog:** MediaTek reaches Tier 1 more cleanly than any
other vendor, and Tier 2 (CSI) *without a firmware exploit* — but it stops at
Tier 2. There is no public arbitrary-waveform TX and no clean spectral/FFT dump.
See [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) for the
per-chip rung table.

---

## 2. Which chips use `mt76` — pick your adapter

| Chip | `mt76` sub-driver | Form factor | Bands | Injection quality | Reference product |
|---|---|---|---|---|---|
| MT7601U | `mt7601u` | USB | 2.4 | **poor** (monitor OK, inject flaky) | cheap no-name dongles |
| MT7610U | `mt76x0u` | USB | 2.4/5 | good | small 11ac dongles |
| **MT7612U** | `mt76x2u` | USB | 2.4/5 | **excellent** | **Alfa AWUS036ACM** ← recommended |
| MT7615 / MT7663 | `mt7615` / `mt7663u` | PCIe/USB/SDIO | 2.4/5 | good | routers, some dongles |
| **MT7915 / MT7916** | `mt7915` | PCIe/SoC | 2.4/5 | good | OpenWrt APs (CSI target) |
| MT7981 / MT7986 | `mt7915` (`mt7981`/`mt7986`) | Filogic SoC | 2.4/5/(6) | good | **OpenWrt One** (CSI target) |
| MT7921 | `mt7921e`/`u`/`s` | M.2/USB/SDIO | 2.4/5 | **buggy on 11ax framing** | Alfa AWUS036AXM, laptops |
| MT7922 | `mt7921` | M.2 | 2.4/5/6 | buggy on 11ax framing | Alfa AWUS036AXML, laptops |
| MT7925 / MT7996 | `mt7925` / `mt7996` | M.2 / SoC | 2.4/5/6 | maturing | Wi-Fi 7 clients / APs |

**If you just want a rock-solid monitor+inject USB adapter, buy the
Alfa AWUS036ACM (MT7612U).** It is mainline since kernel 4.19, injects cleanly on
both bands, and is the default recommendation over Realtek RTL88x2 precisely
because it does injection *on the stock in-tree driver*. The 11ax client parts
(MT7921/22) work for monitor but have a long tail of injection bugs in HE
framing — fine for capture, frustrating for TX-heavy work.

> **Out-of-tree fork.** For very new silicon or backports, the
> [morrownr/mt76](https://github.com/morrownr/mt76) fork tracks newer chips and
> `morrownr/USB-WiFi` documents per-adapter quirks. You should not need it for
> anything in the mainline table above.

Confirm which driver bound your device before anything else:

```bash
# USB
lsusb                                   # find the MediaTek VID:PID (0e8d:…)
# any bus
iw dev                                  # list wiphy/interfaces
ethtool -i wlan0                        # 'driver: mt76x2u' (or mt7921u, mt7915e, …)
dmesg | grep -i -E 'mt76|mt79|mt7601'   # firmware load + ROM patch messages
```

You want `ethtool -i` to name an `mt76*` driver and `dmesg` to show the WM/WA
firmware loading without errors.

---

## 3. Monitor mode

`mt76` is `mac80211`, so monitor mode is the ordinary Linux path. Two ways:

**(a) Add a dedicated monitor VIF (preferred — leaves the managed vif intact):**

```bash
PHYS=wlan0
sudo ip link set $PHYS down                 # some mt76 parts refuse type-change while UP
sudo iw dev $PHYS interface add mon0 type monitor
sudo ip link set mon0 up
sudo iw dev mon0 set channel 6              # 2.4 GHz ch6; or: set freq 5180 (5 GHz ch36)
```

**(b) Flip the existing interface to monitor:**

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
sudo iw dev wlan0 set channel 36 HT40+      # width control: HT20 / HT40+/- / 80MHz / 80+80 / 160
```

**(c) The aircrack-ng shortcut** (kills interfering processes, renames to `…mon`):

```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan0                  # creates wlan0mon
sudo airodump-ng wlan0mon                   # live survey to confirm RX works
```

Capture and inspect with the usual tools — every frame carries a **radiotap**
header the driver prepends (RSSI, channel, MCS/VHT/HE rate, FCS status):

```bash
sudo tcpdump -i mon0 -w capture.pcap        # raw 802.11 + radiotap
sudo wireshark -k -i mon0                    # live; decode radiotap + 802.11
```

**mt76 monitor notes (accurate, not folklore):**

- **Channel/width must be set on the monitor interface**, and for 5/6 GHz the
  regulatory domain must permit the channel. Set your reg domain if scans look
  empty: `sudo iw reg set US` (use your actual country).
- **160 MHz / 6 GHz** capture works on the parts that support those bands
  (MT7915/16, MT7922, MT7925/7996) — width is limited by silicon, not the driver.
- On some parts the PHY will only tune once an interface is actually `up`; if
  `set channel` fails, bring the vif up first, then set the channel.
- Monitor is **verified Tier 1** across the family; the only weak spot is MT7601U
  (monitor fine, but the part is 1×1 2.4-only and injection is unreliable).

---

## 4. Injection

Because `mac80211` builds the frames, injection is the standard Linux radiotap-TX
path — no special IOCTLs, no firmware unlock. Any monitor interface that the
driver marks injection-capable will transmit a frame you hand it with a radiotap
header on the front.

### 4.1 Verify the card injects at all

```bash
sudo aireplay-ng --test mon0                # aircrack-ng's canonical injection test
```

A healthy MT7612U prints ascending `Ping` responses and an injection-success
percentage. If `--test` reports 0%, the card is not injecting on that
channel/mode (see §4.4).

### 4.2 Inject with the aircrack-ng suite

```bash
# Deauth (only against your OWN network / lab — see §7)
sudo aireplay-ng --deauth 5 -a AA:BB:CC:DD:EE:FF mon0

# Replay / forge with packetforge-ng, then send with aireplay-ng
packetforge-ng -0 -a AA:BB:CC:DD:EE:FF -h 11:22:33:44:55:66 \
               -k 255.255.255.255 -l 255.255.255.255 -y prga.xor -w forged.cap
sudo aireplay-ng -2 -r forged.cap mon0
```

### 4.3 Inject a hand-built frame with scapy (full control of the radiotap header)

```python
#!/usr/bin/env python3
# sudo python3 inject.py   — requires an interface already in monitor mode on your channel
from scapy.all import RadioTap, Dot11, Dot11Beacon, Dot11Elt, sendp

ssid = "latent-radios-test"
frame = (
    RadioTap() /
    Dot11(type=0, subtype=8,                         # management / beacon
          addr1="ff:ff:ff:ff:ff:ff",                 # DA broadcast
          addr2="02:00:00:11:22:33",                 # SA (locally-administered)
          addr3="02:00:00:11:22:33") /               # BSSID
    Dot11Beacon(cap="ESS") /
    Dot11Elt(ID="SSID", info=ssid) /
    Dot11Elt(ID="Rates", info=b"\x82\x84\x8b\x96\x0c\x12\x18\x24")
)
sendp(frame, iface="mon0", count=100, inter=0.1)     # 100 beacons, 10/s
```

Watch it land on a second card: `sudo airodump-ng mon1` should list the
`latent-radios-test` SSID. This proves the *whole* TX path end to end.

### 4.4 Radiotap TX fields `mt76`/`mac80211` honour

You control the transmit rate and flags through the radiotap header. `mac80211`
reads (and `mt76` acts on) at least:

| Radiotap field | Effect |
|---|---|
| **Rate** (legacy) | selects an 802.11a/b/g rate for the injected frame |
| **MCS** (`.11n`) | HT rate/index + bandwidth/GI flags |
| **VHT** (`.11ac`) | VHT rate/NSS/bandwidth |
| **TX flags → NO_ACK** | don't wait for/expect an ACK (fire-and-forget) |
| **TX flags → NO_SEQ** | don't let the stack overwrite the sequence number |

Practical caveats, stated honestly:

- **Legacy and HT injection are reliable** on the good parts (MT7612U, MT7915).
  **HE (11ax) rate injection on MT7921/22 is buggy** — frames may go out at a
  fallback rate or not at all; this is a known, tracked issue, not user error.
  For dependable TX at arbitrary rates, prefer MT7612U/MT7915.
- **You cannot inject an arbitrary waveform.** Injection means "a well-formed
  802.11 frame at a rate the MCU supports," not "an IQ buffer." There is no
  MediaTek path to Tier 4 with public tooling — see
  [../verification-tier4.md](../verification-tier4.md) and
  [../true-sdr-comparison.md](../true-sdr-comparison.md).
- If injection silently fails: wrong/locked channel, an unset regulatory domain
  clamping TX power to zero, or `NetworkManager`/`wpa_supplicant` still owning the
  radio (`airmon-ng check kill`).

---

## 5. CSI — the honest state on MediaTek

This is the section to read slowly. **MediaTek CSI is real and it is good Wi-Fi-6
CSI — but it is nowhere near as turnkey as Broadcom, Intel, or ESP32.** Set your
expectations accordingly.

### 5.1 What actually exists

Per-subcarrier Channel State Information (complex `H`, amplitude **and** phase) can
be exported from **ConnAC Wi-Fi-6 parts — MT7915/MT7916 and the Filogic SoCs
MT7981/MT7986 (`mt7976` radio)** — by **patching the `mt76` driver**, *not* the
firmware. The closed MCU already computes CSI for its own beamforming and
rate-control; the driver patch asks the MCU to report it and relays the report to
userspace over an **`nl80211` vendor command / vendor dump** (netlink).

Two research toolchains package this:

| Tool | What it adds | Repo |
|---|---|---|
| **MtkCSIdump** | the `mt76` driver patch + an OpenWrt server + a Python GUI client for real-time CSI visualization (per-antenna plots, amplitude/phase, raw I/Q) | [github.com/MtkWifiRev/MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump) |
| **ekstra-csi** | builds on the same patches but **preserves frame metadata** (source MAC, RSSI, SNR, sequence number) that MtkCSIdump drops; talks to `mt76` over netlink | [github.com/imxdemetri/ekstra-csi](https://github.com/imxdemetri/ekstra-csi) |

Both are tracked on the OpenWrt forum thread
[*CSI extraction for MediaTek-based Wi-Fi chipsets*](https://forum.openwrt.org/t/csi-extraction-for-mediatek-based-wi-fi-chipsets/244703).

### 5.2 The verified reference platform

The publicly demonstrated, reproducible configuration is:

- **Hardware:** **OpenWrt One** (MT7981B / `mt7976` radio) — a cheap, mainline,
  buy-it-today board.
- **OS:** **OpenWrt 24.10.1** (the MtkCSIdump README pins `24.10.1`, build
  `r28597-…`).
- **Firmware blobs in play (unmodified, closed):** `mt7981_rom_patch.bin`,
  `mt7981_wm.bin`, `mt7981_wa.bin`, `mt7981_wo.bin`.
- **Interface:** a station vif (`phy0-sta0`) associated to an AP so there is
  traffic to estimate `H` from.
- **Reach:** 802.11ax bandwidths up to 160 MHz and up to ~512 subcarriers are in
  scope on this silicon.

### 5.3 The shape of the workflow (read the repo — this is the outline)

```text
1. Build OpenWrt 24.10 for your board WITH the MtkCSIdump mt76 patch applied
   (the driver is compiled from the patched mt76 tree, not the stock package).
2. Flash the board; boot; confirm the patched mt76 loaded and the closed
   mt7981 WM/WA/WO blobs came up normally (dmesg / logread).
3. Bring up a station vif (phy0-sta0) and associate it to an AP so packets flow.
4. Enable the CSI report via the tool's control path (the vendor-command hook the
   patch adds), which starts the MCU streaming CSI reports to the driver.
5. Run the on-board server; connect the Python GUI client over the LAN; watch
   live per-antenna amplitude/phase. Wave a hand between board and AP — the
   subcarrier curves must move. That is the CSI sanity check.
```

There is deliberately **no magic offset or struct dump here**: the record layout
is defined by whichever tool/patch you build, and it changes between MtkCSIdump
and ekstra-csi (that is the whole reason ekstra-csi exists — to keep metadata
MtkCSIdump discards). Read the layout out of the repo you actually build.

### 5.4 Why this is *not* turnkey — the candid comparison

| Path | Hardware | What you install | Effort |
|---|---|---|---|
| **ESP32** (`esp-csi`) | $3 SoC | flash a firmware image; read a CSV over UART | trivial; **vendor-documented API** |
| **Broadcom** (Nexmon CSI) | Raspberry Pi 4 | apt-style install + a patched firmware image | modest; well-worn |
| **Intel** (FeitCSI) | AX200/AX210 | a **live-USB distro**, or a package | modest; GUI provided |
| **MediaTek** (MtkCSIdump) | OpenWrt One / MT7915 AP | **build patched OpenWrt + patched `mt76` from source, flash a router** | **highest** of the four |

The MediaTek reasons for the friction:

- **You build and flash a router image.** There is no `pip install`, no live USB,
  no prebuilt kernel module for your laptop. The reference target is an OpenWrt
  board, not a PC NIC.
- **It is research code, not a product.** Two overlapping repos, an OpenWrt forum
  thread, pinned to a specific OpenWrt release. Expect to match versions exactly.
- **It is not in mainline `mt76`.** Stock `mt76` has *no* CSI export. Unlike
  monitor/injection (§3–§4, which need nothing), CSI needs the out-of-tree patch.
- **The client parts (MT7921/MT7922/MT7925) have no turnkey CSI tool.** The
  demonstrated path is AP/SoC silicon (MT7915/MT7981/MT7986). Porting the
  vendor-CSI path to the 2×2 client MCUs is a plausible next step but is currently
  unproven in public — treat client-side MediaTek CSI as *theoretical*.

**So the honest scorecard:** MediaTek CSI is genuinely attractive on the *merits*
(cheap Wi-Fi-6 CSI, 160 MHz, many subcarriers, open driver, **no firmware patch**)
but it is the **least turnkey** of the modern CSI stacks. If you want CSI in an
afternoon, use an ESP32 or a Pi. If you want cheap 11ax CSI on an open driver and
you are comfortable building OpenWrt, MediaTek is excellent — see the toolchain
survey in [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md) and
the per-chip context in
[../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md).

---

## 6. Spectral / raw-PHY scan (Tier 3) — what MediaTek does *not* give you

Unlike Atheros `ath9k` — which exposes an `ath9k`-style `spectral_scan` FFT-bin
dump straight from the mainline driver (see
[atheros-ath9k-spectral-csi.md](atheros-ath9k-spectral-csi.md)) — **`mt76` has no
clean public spectral/FFT-dump interface.** The ConnAC MCUs have internal
energy-detect / DFS-radar-detect and ADC paths, but there is no `speccy`-grade
tool that hands you per-bin FFT magnitudes. If you need Tier-3 raw-PHY spectral
scan on commodity Wi-Fi silicon today, that is an Atheros job, not a MediaTek one.
This remains an open reverse-engineering target (the DFS radar-pulse detection
path is the obvious place to start looking).

---

## 7. Regulatory & safety note

- **Monitor mode is passive** — pure RX, transmits nothing, and is legal to run on
  any band your hardware and regulatory domain allow.
- **Injection transmits real 802.11 frames** on licence-exempt bands. Keep it on
  channels and TX-power levels legal in your region (`iw reg set <CC>`), and inject
  **only against networks and devices you own or are authorised to test.** Deauth
  and disassoc floods against third-party networks are illegal in most
  jurisdictions.
- **There is no arbitrary-waveform TX here.** `mt76` injection emits standard
  Wi-Fi frames at MCU-supported rates. If you need to author raw IQ, this silicon
  cannot do it — reach for a real SDR
  ([../true-sdr-comparison.md](../true-sdr-comparison.md)).
- **CSI capture is RX-side PHY telemetry** on frames you receive; the only TX
  involved is the ordinary station traffic that solicits the packets you measure.

---

## References

**Driver / primary source**

- `mt76` upstream development tree (Felix Fietkau / OpenWrt): <https://github.com/openwrt/mt76>
- Mainline location: `drivers/net/wireless/mediatek/mt76/` in the Linux kernel tree: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/mediatek/mt76>
- `morrownr/mt76` out-of-tree fork (newer chips / backports): <https://github.com/morrownr/mt76>
- `morrownr/USB-WiFi` (per-adapter monitor/injection notes): <https://github.com/morrownr/USB-WiFi>

**Monitor / injection**

- Linux Wireless — monitor mode & radiotap injection: <https://wireless.docs.kernel.org/en/latest/en/users/documentation/monitor.html>
- radiotap header definition (TX fields): <https://www.radiotap.org/>
- aircrack-ng suite (`aireplay-ng`, `airodump-ng`, `packetforge-ng`): <https://www.aircrack-ng.org/>

**CSI**

- MtkCSIdump — `mt76` CSI patch + OpenWrt server + Python GUI: <https://github.com/MtkWifiRev/MtkCSIdump>
- ekstra-csi — metadata-preserving MediaTek CSI over netlink: <https://github.com/imxdemetri/ekstra-csi>
- OpenWrt forum — "CSI extraction for MediaTek-based Wi-Fi chipsets": <https://forum.openwrt.org/t/csi-extraction-for-mediatek-based-wi-fi-chipsets/244703>
- OpenWrt One board (MT7981B / mt7976 reference target): <https://openwrt.org/toh/openwrt/one>
- CSI toolchain comparison (this catalog): [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md)

**Context**

- MediaTek / Ralink silicon in this catalog: [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md)
- SDR ladder / tier definitions: [../taxonomy.md](../taxonomy.md)
- Why injection ≠ arbitrary waveform: [../verification-tier4.md](../verification-tier4.md)
