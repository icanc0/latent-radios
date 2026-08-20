# Analyzing Captured 802.11 with Wireshark & Radiotap

*Latent Radios — Cycle 6 walkthrough. A beginner-friendly bridge from a monitor-mode capture to actually understanding what you captured.*

You have a Wi-Fi card that can go into monitor mode. Now what? This walkthrough takes you from "put the card in monitor mode" to "read the RF and protocol story in every frame," using nothing but standard, free tools: `iw`, `airmon-ng`, `tcpdump`/`tshark`, and Wireshark. It also explains what the **radiotap** header does and does not tell you about the physical layer — and why radiotap's RSSI-and-rate readout is the *poor man's* version of the far richer per-subcarrier telemetry you get from [CSI](../../docs/glossary.md).

> **Scope honesty.** Everything here is passive receive. Monitor mode + radiotap is squarely **Tier 1** on the [SDR ladder](../../docs/taxonomy.md): you get raw 802.11 frames with per-frame PHY metadata, but no I/Q, no subcarrier phase, no arbitrary waveform. That is a huge amount of insight for zero cost — just do not mistake it for an SDR.

---

## 0. Prerequisites: a card that can monitor

You need an adapter whose driver supports `monitor` mode (and, if you want to transmit, injection). Which chips can do this — and which drivers to use — is catalogued in [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md). If you are setting up a common USB adapter (RTL8812AU / 88XXAU class) for the first time, follow the driver and mode-switch steps in [rtl8812au-monitor-injection.md](./rtl8812au-monitor-injection.md) first, then come back here — that walkthrough gets the interface into monitor mode; this one is about *reading* what it captures.

Quick capability check:

```bash
# List phys and the modes each supports
iw phy | grep -A8 "Supported interface modes"
# You want to see "* monitor" in the list
```

---

## 1. Put the card in monitor mode

Two roads lead to the same place. Use **one**.

### Road A — `iw` (manual, minimal, no extra packages)

```bash
# Identify the interface (e.g. wlan0) and its phy
iw dev

# Bring it down, switch type, bring it up
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up

# Park it on a specific channel (see §2 for how to choose)
sudo iw dev wlan0 set channel 6          # 2.4 GHz ch 6
# 5 GHz example with 80 MHz width, centered correctly:
sudo iw dev wlan0 set channel 36 80MHz

# Confirm
iw dev wlan0 info
```

You should see `type monitor` and the channel/width you set. A common failure is a background process (NetworkManager, `wpa_supplicant`) snatching the interface back. Silence it first:

```bash
sudo systemctl stop NetworkManager     # or: sudo airmon-ng check kill
```

### Road B — `airmon-ng` (aircrack-ng suite, does the housekeeping for you)

```bash
sudo airmon-ng check kill                # kill NM / wpa_supplicant interference
sudo airmon-ng start wlan0               # creates a monitor iface, often wlan0mon
iw dev                                    # confirm the new monitor interface name
sudo airmon-ng start wlan0 6             # optionally start locked to channel 6
```

`airmon-ng` may create a *new* interface named `wlan0mon`; use that name everywhere below. To undo everything: `sudo airmon-ng stop wlan0mon`.

> **Regulatory note.** Your regulatory domain (`iw reg get`) gates which channels — and which channel *widths* and 5/6 GHz sub-bands — you may even tune to for receive. See [../../docs/regulatory-by-region.md](../../docs/regulatory-by-region.md). Passive monitoring is legal in most places; be aware DFS channels and 6 GHz may be restricted.

---

## 2. Capture: tcpdump, tshark, or airodump

Monitor mode hears only the **one channel** the radio is tuned to at any instant. You either **park** on a channel of interest or **hop** across channels (which means you miss frames on every channel you are not currently on).

### Park + capture with `tcpdump` (simplest, writes a pcap)

```bash
# -i monitor iface, -w write pcap, -s0 full frames, keep it running:
sudo tcpdump -i wlan0mon -w capture.pcap -s0
# Ctrl-C to stop. Open capture.pcap in Wireshark later.
```

### Capture with `tshark` (Wireshark's CLI — live dissection + filtering)

```bash
# Live one-line summary of every 802.11 frame:
sudo tshark -i wlan0mon

# Write a pcapng and simultaneously print beacons only:
sudo tshark -i wlan0mon -w capture.pcapng -Y "wlan.fc.type_subtype == 0x08"

# Pull just the fields you care about (RF + who's talking):
sudo tshark -i wlan0mon -T fields \
  -e frame.time_relative -e wlan.sa -e wlan.da \
  -e wlan.fc.type_subtype -e radiotap.dbm_antsignal -e radiotap.datarate \
  -E header=y
```

### Survey with `airodump-ng` (best for "what APs and clients are around")

```bash
# Live AP/client dashboard; also writes a pcap with --write
sudo airodump-ng wlan0mon
sudo airodump-ng --write survey --output-format pcap wlan0mon

# Lock to a channel (stops hopping) to catch every frame there:
sudo airodump-ng -c 6 wlan0mon
```

`airodump-ng` channel-hops by default, which is great for discovery but bad for complete capture. When you have picked a target BSSID/channel, **lock the channel** (`-c`) so you stop missing frames.

---

## 3. What is a radiotap header, really?

A raw 802.11 frame off the air contains no RF metadata — the PHY strips all of that before handing the MAC frame up. **Radiotap** is a de-facto standard "pseudo-header" that Linux (`mac80211`) prepends to each received frame in monitor mode, carrying the receiver's view of the physical layer: how strong it was, what data rate/MCS decoded it, which channel, a hardware timestamp, and so on. Wireshark dissects it as the `radiotap` protocol sitting *underneath* `wlan`.

Radiotap is extensible and **presence-flagged**: a bitmap says which fields are present, and each driver/chip populates a different subset. So do not be surprised when one capture has MCS and channel-flags and another only has signal + rate. The authoritative field catalogue is the radiotap spec at [radiotap.org](https://www.radiotap.org/).

### The fields you will actually use

| Radiotap field | Wireshark filter name | What it tells you about the PHY |
|---|---|---|
| Antenna signal | `radiotap.dbm_antsignal` | **RSSI in dBm** — how strong this frame arrived (e.g. −45 = close/strong, −85 = far/weak). One scalar per antenna. |
| Antenna noise | `radiotap.dbm_antnoise` | Noise floor in dBm; combine with signal for SNR. Often absent. |
| Channel freq | `radiotap.channel.freq` | Center frequency in MHz (2412 = ch 1, 5180 = ch 36…). Confirms what the radio was tuned to. |
| Channel flags | `radiotap.channel.flags.*` | Band + modulation hints (CCK vs OFDM, 2 GHz vs 5 GHz). |
| Rate | `radiotap.datarate` | Legacy data rate in Mb/s (802.11a/b/g). **Absent for 11n/ac/ax** — those use MCS instead. |
| MCS index | `radiotap.mcs.index` | 802.11n modulation-and-coding-scheme index → modulation + coding + spatial streams. |
| MCS flags | `radiotap.mcs.bw`, `radiotap.mcs.gi`, `radiotap.mcs.fmt` | Channel width (20/40 MHz), short/long guard interval, mixed/greenfield. |
| VHT / HE | `radiotap.vht.*`, `radiotap.he.*` | 802.11ac/ax equivalents: bandwidth (up to 160 MHz), NSS, MCS. |
| TSFT / timestamp | `radiotap.mactime`, `radiotap.timestamp.ts` | Microsecond hardware receive timestamp — useful for ordering and timing. |
| Flags | `radiotap.flags.badfcs` | e.g. **FCS check failed** — this frame was corrupted; monitor mode still hands it to you. |
| Antenna | `radiotap.antenna` | Which physical antenna index reported the signal (on multi-antenna cards you may see one row per antenna). |

> **Read the presence flags, not your assumptions.** If `radiotap.datarate` is missing on an 802.11n network, that is expected — look at `radiotap.mcs.index`. If signal looks implausibly flat, your driver may be reporting a fixed value; radiotap quality is a driver/chip trait, not a Wi-Fi guarantee.

A tiny worked example — an 802.11n beacon might carry: `channel.freq = 2437` (ch 6), `mcs.index = 0`, `mcs.bw = 20 MHz`, `mcs.gi = long`, `dbm_antsignal = −52 dBm`, `flags.badfcs = 0`. That single header tells you the AP is on channel 6, the frame decoded at the most robust 11n rate, arrived moderately strong, and passed CRC — all before you have looked at a single MAC field.

---

## 4. Dissecting the frame: management, control, data

Above radiotap sits the 802.11 MAC. Every frame has a **Frame Control** field whose *type* (2 bits) and *subtype* (4 bits) Wireshark exposes as `wlan.fc.type` and the combined `wlan.fc.type_subtype`. The three types:

### Management frames (`wlan.fc.type == 0`) — the "who and how" of the network

These are unencrypted and are where reconnaissance lives:

| Subtype | `type_subtype` | What it is / why you care |
|---|---|---|
| Beacon | `0x08` | AP's periodic advertisement: SSID, supported rates, channel, capabilities, security (RSN/WPA IEs), HT/VHT/HE capabilities. The single richest management frame. |
| Probe Request | `0x04` | A client asking "is network X here?" — reveals client presence and sometimes SSIDs it has joined before. |
| Probe Response | `0x05` | AP's targeted reply to a probe. |
| Authentication | `0x0b` | Start of the association handshake. |
| Association Request/Response | `0x00` / `0x01` | Client joining; response carries the assigned AID and negotiated capabilities. |
| Deauthentication | `0x0c` | "You are disconnected." Classic ingredient of deauth attacks — a flood of these is a red flag. |

Open a beacon in Wireshark and expand **IEEE 802.11 wireless LAN → Tagged parameters**: you will see the SSID, supported/extended rates, DS Parameter Set (channel), RSN Information (encryption + cipher suites), and HT/VHT/HE Capabilities. This is how tools like `airodump-ng` know everything they display.

### Control frames (`wlan.fc.type == 1`) — the traffic cops

Short, header-only frames that regulate medium access. You mostly *count* these rather than read them:

| Subtype | `type_subtype` | Meaning |
|---|---|---|
| RTS | `0x1b` | Request to Send — reserve the medium. |
| CTS | `0x1c` | Clear to Send — grant. |
| ACK | `0x1d` | Acknowledged receipt (heavy volume). |
| Block Ack / BAR | `0x19` / `0x18` | Aggregated acknowledgements (11n+). |

A high RTS/CTS ratio hints at hidden-node contention or a busy medium.

### Data frames (`wlan.fc.type == 2`) — the payload

The actual carried traffic. On an **encrypted** network (WPA2/WPA3), the payload is ciphertext — you can see addresses, QoS, sequence numbers, and frame sizes, but not the contents unless you captured the 4-way handshake *and* hold the passphrase (Wireshark → *IEEE 802.11* preferences → enable decryption → add `wpa-pwd:passphrase:SSID`). Subtype `0x28` is QoS Data, the workhorse on modern networks.

### The three/four addresses

802.11 frames carry up to four MAC addresses (`wlan.sa` source, `wlan.da` destination, `wlan.bssid`, plus a transmitter/receiver split on WDS). Which address is "the sender" depends on `ToDS`/`FromDS` (`wlan.fc.tods` / `wlan.fc.fromds`). For infrastructure Wi-Fi, `wlan.bssid` is the AP and `wlan.sa`/`wlan.da` are the endpoints. Wireshark's *Statistics → WLAN Traffic* rolls this up per-BSSID automatically.

---

## 5. A display-filter cheat sheet

Type these into Wireshark's filter bar (or pass to `tshark -Y "..."`):

```text
# By frame category
wlan.fc.type == 0                         # all management
wlan.fc.type == 1                         # all control
wlan.fc.type == 2                         # all data

# Specific subtypes
wlan.fc.type_subtype == 0x08              # beacons
wlan.fc.type_subtype == 0x04              # probe requests
wlan.fc.type_subtype == 0x0c              # deauthentications  (attack hunting)

# By station / network
wlan.sa == aa:bb:cc:dd:ee:ff              # frames FROM this MAC
wlan.addr == aa:bb:cc:dd:ee:ff            # any address field matches (to or from)
wlan.bssid == aa:bb:cc:dd:ee:ff           # one AP's cell only
wlan.ssid == "CoffeeShopWiFi"             # by advertised SSID (mgmt frames)

# By RF quality (radiotap)
radiotap.dbm_antsignal > -60              # only strong frames (near the radio)
radiotap.channel.freq == 2437             # only frames heard on channel 6
radiotap.mcs.index >= 7                   # high-throughput 11n frames
radiotap.flags.badfcs == 1               # corrupted frames (weak signal / interference)

# Retransmissions and QoS
wlan.fc.retry == 1                        # retried frames — a link-quality smell test

# Combine them
wlan.fc.type_subtype == 0x08 && radiotap.dbm_antsignal > -70
```

Two colouring/analysis tips: right-click any field in the packet detail pane → **Apply as Filter** to build filters without memorising names; and **Statistics → I/O Graph** with `radiotap.dbm_antsignal` (Y = AVG) plotted over time turns your capture into a crude RSSI-vs-time signal trace.

---

## 6. Radiotap RSSI/rate is the poor man's CSI

Here is the honest ceiling of what monitor mode gives you, and where the [CSI toolchains](../../projects/csi-toolchains.md) begin.

Radiotap hands you, per frame, a **single scalar** RSSI (`dbm_antsignal`) and a **single** rate/MCS. That is the receiver's already-collapsed summary of a rich physical event. The Wi-Fi PHY actually estimated the channel across **every OFDM subcarrier** (52 for 20 MHz 11n, 234 for 80 MHz 11ac, etc.), producing a complex number — **amplitude and phase** — for each. That per-subcarrier complex vector is **Channel State Information (CSI)**. The hardware computed it to equalise the signal, then *threw it away*, keeping only the averaged magnitude it reports as RSSI.

| | Radiotap (monitor mode) | CSI (Nexmon / Atheros CSI Tool / ESP32 / Intel) |
|---|---|---|
| Per frame you get | 1 RSSI scalar, 1 rate/MCS | tens–hundreds of complex values (per subcarrier, per antenna) |
| Amplitude | Yes, one number | Yes, per subcarrier |
| **Phase** | **No** | **Yes** (per subcarrier) |
| Frequency selectivity | Invisible (collapsed) | Fully resolved (multipath fingerprint) |
| Typical uses | link quality, presence, survey, protocol analysis | motion/breathing sensing, gesture/pose, indoor localisation, material sensing |
| SDR tier | Tier 1 | Tier 2 |
| Cost | any monitor-capable card | specific chips + patched firmware |

Consequences you feel in practice:

- **Presence/motion sensing on RSSI alone** works but is coarse and noisy — RSSI wobbles a few dB when someone moves, and you cannot separate multipath from fading. CSI resolves the multipath directly and is what modern Wi-Fi sensing papers actually use.
- **No phase means no true ranging/angle** from radiotap. RSSI-distance models are notoriously unreliable indoors; CSI phase (and FTM timestamps) is what enables real localisation.
- Radiotap's rate/MCS tells you *which* modulation decoded — a proxy for link margin — but nothing about *why* the channel favoured that rate. CSI shows you the frequency-selective fade that forced it.

So: monitor-mode + radiotap is the right first tool for **protocol** understanding and **coarse RF** situational awareness, and it costs nothing. When your question becomes "what is the channel doing across frequency and phase" — sensing, imaging, fine localisation — you have outgrown radiotap and need CSI. The upgrade path (patched firmware, which chips, and how to turn raw CSI into something usable) is in [../nexmon-csi-to-usable-csi.md](./nexmon-csi-to-usable-csi.md) and [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md).

---

## 7. Cleanup

```bash
# iw road:
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up
sudo systemctl start NetworkManager

# airmon-ng road:
sudo airmon-ng stop wlan0mon
sudo systemctl start NetworkManager
```

---

## References

- Radiotap specification and field definitions — [radiotap.org](https://www.radiotap.org/)
- Wireshark `wlan` (IEEE 802.11) display-filter reference — [wireshark.org/docs/dfref/w/wlan.html](https://www.wireshark.org/docs/dfref/w/wlan.html)
- Wireshark `radiotap` display-filter reference — [wireshark.org/docs/dfref/r/radiotap.html](https://www.wireshark.org/docs/dfref/r/radiotap.html)
- Wireshark WLAN capture setup — [wiki.wireshark.org/CaptureSetup/WLAN](https://wiki.wireshark.org/CaptureSetup/WLAN)
- Linux `iw` documentation — [wireless.wiki.kernel.org/en/users/documentation/iw](https://wireless.wiki.kernel.org/en/users/documentation/iw)
- aircrack-ng suite (`airmon-ng`, `airodump-ng`) — [aircrack-ng.org](https://www.aircrack-ng.org/)
- `tcpdump` manual — [tcpdump.org/manpages/tcpdump.1.html](https://www.tcpdump.org/manpages/tcpdump.1.html)
- `tshark` manual — [wireshark.org/docs/man-pages/tshark.html](https://www.wireshark.org/docs/man-pages/tshark.html)
- IEEE 802.11 frame types/subtypes overview — [en.wikipedia.org/wiki/802.11_Frame_Types](https://en.wikipedia.org/wiki/802.11_Frame_Types)

### Related in this catalog

- [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md) — which chips/drivers do monitor + injection
- [./rtl8812au-monitor-injection.md](./rtl8812au-monitor-injection.md) — getting a common USB adapter into monitor/injection mode
- [../nexmon-csi-to-usable-csi.md](./nexmon-csi-to-usable-csi.md) — the CSI upgrade path
- [../../docs/glossary.md](../../docs/glossary.md) — RSSI, CSI, radiotap, MCS, and other terms
- [../../docs/taxonomy.md](../../docs/taxonomy.md) — the SDR tier ladder this walkthrough is calibrated against
