# GNU Radio Out-of-Tree Modules for Wi-Fi & Friends

An index tying the chip-repurposing world of *Latent Radios* to the "real SDR" world. Every entry in the main catalog answers the question *"can this commodity radio be coaxed off the ground floor of the [SDR ladder](../docs/taxonomy.md)?"* This page answers the mirror-image question: *"which parts of the RF spectrum already have a fully open, host-side DSP implementation you can run on a general-purpose SDR today?"*

A GNU Radio out-of-tree (OOT) module is a third-party block collection — a `gr-*` package with C++/Python blocks, GRC flowgraphs, and usually a Wireshark bridge — that implements a complete PHY (and often a slice of MAC) in software on the host. Where a repurposed Wi-Fi chip gives you a **Tier 1–3** peek at a protocol through fixed silicon, an OOT module on a USRP/HackRF/RTL-SDR is **Tier 5 by construction**: the entire waveform is defined in source you can read and edit. See [true-SDR comparison](../docs/true-sdr-comparison.md) for the tier reasoning, and [openwifi](../projects/openwifi.md) for the one project that meets both worlds — an open FPGA+software 802.11 stack on a Zynq SDR.

---

## Why this page exists: complement, and sometimes replace

Chip repurposing and OOT modules solve overlapping problems from opposite ends:

| | Repurposed commodity chip | OOT module on a general SDR |
|---|---|---|
| **Hardware cost** | \$3–\$40 (a dongle you already own) | \$150 (RTL-SDR + upconverter) to \$1–3k (USRP B210) |
| **PHY access** | Whatever the vendor's silicon fixes; escape hatches via firmware RE | Full source; edit any DSP stage |
| **SDR tier** | 0–3 typically, occasionally 4 | 5 (open PHY) by definition |
| **RF front-end** | Purpose-built, tuned, cheap, one band | Wideband, flexible, needs external filtering/LNA |
| **Timing / MAC** | Real hardware MAC, microsecond ACKs | Host-latency bound; tight MAC (ACK, CSMA/CA) often impossible |
| **Portability** | Runs on the chip, standalone | Needs a host CPU (or FPGA) streaming IQ |

**They complement** when you use the OOT module as the *ground truth* to validate a chip hack: decode 802.11 both with a repurposed Wi-Fi NIC's monitor mode **and** with `gr-ieee802-11` on a USRP, and the SDR is your reference PHY. Nexmon CSI or a Wi-Fi radar experiment is far easier to interpret when you can generate a known, arbitrary waveform from `gr-ieee802-11` or `gr-paint` and watch how the commodity chip reports it.

**They replace** chip repurposing outright when the target protocol has *no* cheap silicon you can subvert, or when you need TX of arbitrary frames. There is no \$5 dongle that will inject a malformed 802.15.4 O-QPSK preamble or paint an image into an FM band — but `gr-ieee802-15-4` and `gr-paint` on a HackRF will. Conversely, if all you need is to *sniff* BLE advertising or capture Wi-Fi CSI at scale, a \$10 chip beats tying up a \$1200 USRP.

The honest tradeoff: OOT modules give you **PHY freedom at the cost of hardware, host latency, and (for TX) legality**. Chip repurposing gives you **cheap, timing-accurate, band-specific access at the cost of PHY ceiling**.

---

## The module index

Maintenance status verified against upstream repositories, August 2026.

| Module | Protocol / band | Decode | Encode (TX) | Typical SDRs | GNU Radio | Status |
|---|---|---|---|---|---|---|
| [gr-ieee802-11](https://github.com/bastibl/gr-ieee802-11) | Wi-Fi 802.11a/g/p, 2.4/5 GHz | Yes | Yes (full Tx) | USRP N2x0, B2x0 | 3.7 / 3.8 / 3.10 (maint branches) | **Active** (wime-project) |
| [gr-foo](https://github.com/bastibl/gr-foo) | helper blocks (not a PHY) | — | — | any | 3.7 / 3.8 / 3.10 | **Active** |
| [gr-bluetooth](https://github.com/greatscottgadgets/gr-bluetooth) | Bluetooth BR baseband, 2.4 GHz | Yes (Rx only) | No | USRP, RTL-SDR | 3.7 | **Archived** (Aug 2024) |
| [gr-nordic](https://github.com/bkerler/gr-nordic) | Nordic nRF24L Enhanced ShockBurst, 2.4 GHz | Yes | Yes | HackRF, USRP, bladeRF | 3.10 (fork) | **Maintained fork** |
| [gr-ieee802-15-4](https://github.com/bastibl/gr-ieee802-15-4) | 802.15.4 O-QPSK + CSS (ZigBee/6LoWPAN), 2.4 GHz + 868/915 MHz | Yes | Yes | USRP B2x0/N2x0 | 3.7 / 3.8 / 3.10 | **Active** |
| [gr-lora](https://github.com/rpp0/gr-lora) | LoRa CSS (blind RE), sub-GHz | Yes | partial | USRP B201, HackRF, RTL-SDR, LimeSDR | 3.7 (Python 2) | **Stale** (last 0.6, 2017) |
| [gr-lora_sdr](https://github.com/tapparelj/gr-lora_sdr) | LoRa CSS (full stack), sub-GHz | Yes | Yes | USRP, tested vs SX127x/SX126x | 3.10 | **Active** (EPFL) |
| [gr-adsb](https://github.com/mhostetter/gr-adsb) | ADS-B / Mode-S, 1090 MHz | Yes | No | RTL-SDR, HackRF, USRP, bladeRF | 3.10 (maint) | **Maintained** |
| [gr-gsm](https://github.com/ptrkrysik/gr-gsm) | GSM downlink/uplink, 850–1900 MHz | Yes | No | RTL-SDR, HackRF, USRP | 3.7 / 3.8 | **Legacy / low activity** |
| [gr-dect2](https://github.com/pavelyazev/gr-dect2) | DECT voice channel, 1880–1900 MHz | Yes (unencrypted) | No | USRP B200, HackRF | 3.7–3.8 era | **Semi-active** |
| [gr-paint](https://github.com/drmpeg/gr-paint) | "spectrum painter" — image into waterfall | — | Yes (TX only) | USRP B2x0, bladeRF | 3.7+ | **Maintained** |
| [gr-rds](https://github.com/bastibl/gr-rds) | FM RDS/RBDS + TMC, 88–108 MHz | Yes | Yes | RTL-SDR (Rx), USRP (Tx) | 3.7 / 3.8 / 3.10 | **Active** |
| [gr-satellites](https://github.com/daniestevez/gr-satellites) | amateur-sat telemetry (AX.25, CCSDS, dozens of modems), VHF/UHF/S-band | Yes | No | RTL-SDR, Airspy, USRP, LimeSDR, etc. | 3.10 (v5) | **Very active** |

---

## Per-module notes

### gr-ieee802-11 — the reference open Wi-Fi PHY
Bastian Bloessl's transceiver implements 802.11a/g/p (OFDM) end to end: encoding, framing, OFDM modulation, and on the Rx side synchronization, channel estimation, equalization, and Viterbi decoding — emitting frames as PDUs you can pipe straight to Wireshark (via [gr-foo](#gr-foo--the-glue)). It is the canonical way to *transmit* and *receive* real, standards-compliant Wi-Fi frames from an SDR, and the natural ground-truth companion to any Wi-Fi chip hack in this catalog. Fitted for Ettus N210 and B210. Its documented limitation is instructive for the whole page: host+Ethernet latency makes real-time ACKs and CSMA/CA impractical — the classic "PHY freedom, MAC-timing poverty" tradeoff. Actively maintained under the [WiME project](https://www.wime-project.net); maintenance branches track GNU Radio releases (`maint-3.7`, `maint-3.8`, `maint-3.10`).

### gr-foo — the glue
Not a PHY. A grab-bag of blocks that the Wi-Fi and 802.15.4 flowgraphs depend on: a **Wireshark Connector** that wraps PDUs in PCAP (Radiotap for Wi-Fi, ZigBee for 15.4), a **Packet Pad** and **Burst Tagger** that insert `tx_sob`/`tx_eob` and `tx_time` tags for half-duplex burst TX, a **Packet Dropper** for protocol-robustness testing, and periodic/tagged-stream sources. If you build any burst-mode TX flowgraph on a USRP, you will reach for gr-foo. Same maintainer and branch scheme as gr-ieee802-11.

### gr-bluetooth — Ubertooth lineage, now archived
Originally Michael Ossmann's work and the DSP ancestor of the **Ubertooth** project; it implements a Bluetooth **Basic Rate baseband receiver** for experimentation and teaching, explicitly *not* a usable comms stack. Now under the Great Scott Gadgets org and **archived (read-only since 16 Aug 2024)**, stuck on GNU Radio 3.7. For live BR/EDR or BLE sniffing the practical successor is dedicated hardware — an **Ubertooth One** or a repurposed BLE chip (see [ble-154-thread](../chips/ble-154-thread.md)) — rather than an SDR flowgraph. Included here because it is the historical bridge between SDR DSP and the cheap-hardware sniffer world.

### gr-nordic — nRF24 Enhanced ShockBurst on an SDR
Decodes and *encodes* the Nordic Semiconductor **nRF24L Enhanced ShockBurst** protocol used by wireless keyboards, mice, and countless 2.4 GHz peripherals, and ships a Wireshark dissector. Origin is Bastille Research's `gr-nordic` (the SDR half of the "MouseJack" research); the actively updated fork is **bkerler/gr-nordic** on `maint-3.10`. This is the SDR counterpart to repurposing an nRF24 chip itself for [cross-technology communication](../docs/cross-technology-communication.md) — the SDR sees ESB blindly across the whole band, where the chip is fast and cheap but locked to Nordic's framing.

### gr-ieee802-15-4 — ZigBee / 6LoWPAN PHY, both flavors
Bastian Bloessl's 802.15.4 transceiver implements the **2.4 GHz O-QPSK** PHY and the sub-GHz **CSS** PHY, plus the Rime stack, and interoperates with real **TelosB motes / Contiki OS** — a genuine software radio for the ZigBee/Thread/6LoWPAN world. Packets go to Wireshark via gr-foo. Runs on USRP B2x0/N2x0; maintenance branches for GR 3.7/3.8/3.10. Compare to repurposing an 802.15.4 radio in [ble-154-thread](../chips/ble-154-thread.md): the SDR lets you malform the PHY (preamble, chip sequence) in ways no commodity 15.4 transceiver will.

### gr-lora & gr-lora_sdr — two generations of open LoRa
Two distinct projects, and the difference matters:
- **gr-lora (rpp0)** was the *blind reverse-engineering* effort — Pieter Robyns et al. reconstructed LoRa's CSS modulation from captured IQ; by v0.6 (Aug 2017) the author declared "LoRa fully reverse engineered." It runs on GR 3.7 with Python 2 and is effectively **frozen**, but it is the historically important proof that a proprietary sub-GHz PHY could be cracked purely from the air. Rx-focused; broad SDR support (HackRF, USRP B201, RTL-SDR, LimeSDR).
- **gr-lora_sdr (tapparelj, EPFL)** is the modern, **actively maintained** successor: a *complete* LoRa transceiver (whitening, Hamming FEC, interleaving, gray coding, modulation, sync, demod, decode) on GNU Radio 3.10, validated for interoperability against real **SX1276 / SX1262 / RFM95** hardware. This is what you use today to TX/RX standards-compatible LoRa from a USRP and to experiment at the [sub-GHz](../chips/lora-subghz.md) PHY level.

### gr-adsb — 1090 MHz aircraft surveillance
Matt Hostetter's decoder handles Mode-S downlink formats including **DF17 ADS-B Extended Squitter** (position, velocity, identification) and DF 0/4/5/11/16/18/19/20/21. Receive-only (transmitting on 1090 MHz is illegal essentially everywhere). Works across the OsmoSDR family — RTL-SDR, HackRF, USRP, bladeRF — via GNU Radio; `maint-3.10` branch. The canonical "point a \$25 dongle at the sky and decode a real protocol" demo, and a good first OOT module for anyone coming from RTL-SDR (see [rtl-sdr-lineage](../projects/rtl-sdr-lineage.md)).

### gr-gsm — GSM receiver, Airprobe's descendant
Piotr Krysik's `gr-gsm` is the successor to the old **Airprobe** `gsm-receiver`: it demultiplexes GSM bursts, decodes control and voice (TCH) channels, and interfaces to `gsmtap`/Wireshark. Receive/analysis only. It targets GR 3.7/3.8 and sees only sporadic maintenance today — most users run it from a pinned container. There is no single blessed successor; forks and Osmocom's own tooling carry the torch. Historically pivotal as the first widely reproducible open GSM Rx, but heed the strict legality of intercepting cellular traffic.

### gr-dect2 — cordless phone / baby-monitor audio
Pavel Yazev's module locks onto a **DECT** voice channel (1880–1900 MHz) and decodes audio **when no encryption is applied** — classic against old baby monitors and unencrypted handsets. Developed/tested on USRP2+WBX and USRP B200, with a HackRF flowgraph variant. Semi-maintained. Same legal caveats as any voice interception.

### gr-paint — a transmit-only curiosity that is pedagogically perfect
Ron Economos' ("drmpeg") "spectrum painter": it takes a monochrome image and synthesizes a **4K-IFFT OFDM** waveform so the picture appears in a receiver's waterfall/spectrogram. TX-only, on B2x0/bladeRF via UHD. It is the cleanest possible demonstration of *arbitrary-waveform TX* — the very [Tier-4/5](../docs/verification-tier4.md) capability that chip repurposing almost never reaches — because there is no protocol at all, just raw control over what energy lands where in time and frequency. Great for calibrating what a repurposed chip's spectral-scan (Tier 3) actually "sees."

### gr-rds — FM Radio Data System, both directions
Bastian Bloessl's FM **RDS/RBDS** transceiver decodes the 57 kHz subcarrier (station name/PS, RadioText, TMC traffic) from an FM broadcast — trivially with an RTL-SDR — and can *encode* it for TX on a USRP. Maintained, branches for GR 3.7/3.8/3.10. A friendly on-ramp to demodulation chains and a reminder that "SDR" includes the broadcast bands, not just the digital radios in this catalog.

### gr-satellites — the deep, living decoder library
Daniel Estévez's project is the outlier in scale: **dozens** of amateur-satellite telemetry decoders (AX.25, GOMspace NanoCom U482C/AX100 modems, a large part of the CCSDS stack, plus many bespoke cubesat formats) in one maintained package. Current **v5.x on GNU Radio 3.10** (the 3.8/3.9 branches were frozen 31 Jul 2025). Runs on essentially any SDR — RTL-SDR, Airspy, USRP, LimeSDR, PlutoSDR. Receive/analysis oriented. It shows what a *mature, community-sustained* OOT module looks like, and it is the reference for anyone extending the catalog's [true-SDR comparison](../docs/true-sdr-comparison.md) toward space.

---

## Installing and running OOT modules (the shape of it)

Modern (GNU Radio 3.10) modules follow a uniform pattern:

```bash
# Match the branch to your GNU Radio version first
gnuradio-config-info --version        # e.g. 3.10.x

git clone https://github.com/bastibl/gr-ieee802-11.git
cd gr-ieee802-11
git checkout maint-3.10               # or maint-3.8 / maint-3.7 to match your GR
mkdir build && cd build
cmake ..
make -j"$(nproc)"
sudo make install
sudo ldconfig                         # register the new blocks
```

Then open the example flowgraphs in **GNU Radio Companion** (`gnuradio-companion`), which appear under the module's category in the block tree, or run the shipped `.py`/`.grc` examples. Most Wi-Fi/15.4/nordic modules pair with **gr-foo** for the Wireshark bridge — install gr-foo first. For RTL-SDR/HackRF/USRP source and sink blocks, install **gr-osmosdr** (or **gr-uhd** for Ettus) so the modules can reach real hardware.

Two recurring gotchas: (1) the `maint-*` branch **must** match your installed GNU Radio minor version, and (2) after `make install` you must `ldconfig` (and sometimes fix `PYTHONPATH`/`LD_LIBRARY_PATH`) or GRC will not find the blocks.

---

## Transmit safety and regulatory notes

Several modules on this page **transmit**: gr-ieee802-11, gr-foo-assisted bursts, gr-nordic, gr-ieee802-15-4, gr-lora_sdr, gr-paint, and gr-rds. Software radios emit whatever you tell them to, with no built-in respect for band plans, power limits, or spectral masks.

- **Do not transmit on licensed/allocated bands.** GSM, DECT, ADS-B (1090 MHz), and cellular are off-limits — gr-gsm, gr-dect2, and gr-adsb are Rx-only here for exactly this reason, and intercepting voice/cellular traffic is itself illegal in many jurisdictions.
- **Wi-Fi, ZigBee, LoRa, nRF24 live in ISM/U-NII bands** but are still bound by regional power and duty-cycle rules; SDR TX will not enforce them.
- **Use a shielded RF enclosure, a dummy load, or heavy attenuation and a wired coax path** for any TX experiment. Radiating with a USRP/HackRF into an antenna can trivially exceed legal limits and jam real services.
- **gr-paint** deserves a specific warning: painting an image into a band means dumping wideband energy across it — only ever do this into a cable/attenuator on a band you are licensed for (amateur radio operators: on your own allocations).

When in doubt, keep it in a Faraday bag and off the air. The point of these modules is to *understand* PHYs — receiving and analyzing carries none of this risk.

---

## References

- gr-ieee802-11 — <https://github.com/bastibl/gr-ieee802-11> · WiME project <https://www.wime-project.net>
- gr-foo — <https://github.com/bastibl/gr-foo>
- gr-bluetooth (Great Scott Gadgets, archived) — <https://github.com/greatscottgadgets/gr-bluetooth>
- gr-nordic (maintained fork) — <https://github.com/bkerler/gr-nordic> · origin <https://github.com/BastilleResearch/gr-nordic>
- gr-ieee802-15-4 — <https://github.com/bastibl/gr-ieee802-15-4>
- gr-lora (rpp0, blind RE) — <https://github.com/rpp0/gr-lora>
- gr-lora_sdr (tapparelj, EPFL) — <https://github.com/tapparelj/gr-lora_sdr>
- gr-adsb (mhostetter) — <https://github.com/mhostetter/gr-adsb>
- gr-gsm (ptrkrysik) — <https://github.com/ptrkrysik/gr-gsm>
- gr-dect2 (pavelyazev) — <https://github.com/pavelyazev/gr-dect2>
- gr-paint (drmpeg / Ron Economos) — <https://github.com/drmpeg/gr-paint>
- gr-rds (bastibl) — <https://github.com/bastibl/gr-rds>
- gr-satellites (daniestevez / Daniel Estévez) — <https://github.com/daniestevez/gr-satellites> · docs <https://gr-satellites.readthedocs.io>
- GNU Radio — <https://www.gnuradio.org> · gr-osmosdr <https://osmocom.org/projects/gr-osmosdr>

---

*Related in this catalog:* [true-SDR comparison](../docs/true-sdr-comparison.md) · [openwifi](../projects/openwifi.md) · [RTL-SDR lineage](../projects/rtl-sdr-lineage.md) · [sub-GHz & LoRa chips](../chips/lora-subghz.md) · [BLE / 802.15.4 / Thread](../chips/ble-154-thread.md) · [taxonomy & the SDR ladder](../docs/taxonomy.md)
