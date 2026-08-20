# Real 802.11 on an SDR: `gr-ieee802-11` + HackRF / USRP

> **What this page is.** The whole "Latent Radios" catalog measures how far a *repurposed Wi-Fi chip* can be pushed toward being a software-defined radio. This page describes the thing at the top of that ladder — a **genuine SDR running a full, open 802.11 physical layer in software**. It is the reference baseline. When a Broadcom or Atheros firmware hack gets you monitor+injection (Tier 1) or CSI (Tier 2), the honest question is always "how close is that to just doing the PHY on a HackRF?" This is what "just doing the PHY" looks like — and why, despite being Tier 5, it is *not* the answer for most people.

The canonical implementation is Bastian Bloessl's **`gr-ieee802-11`**, a GNU Radio out-of-tree (OOT) module that decodes and generates IEEE **802.11a / 802.11g / 802.11p** OFDM frames entirely in software. It is part of the **WIME Project** (Wireless Measurement Environment, formerly the "gr-ieee802-11 / gr-ieee802-15-4" family) out of TU Darmstadt / Trinity College Dublin / Paderborn and collaborators.

- Repo: <https://github.com/bastibl/gr-ieee802-11> (GPL-3.0)
- Companion blocks: <https://github.com/bastibl/gr-foo>
- Project home: <https://www.wime-project.net>

See also [`true-sdr-comparison.md`](../docs/true-sdr-comparison.md) for the tier-by-tier framing, [`openwifi.md`](openwifi.md) for the FPGA-based *full-MAC* open 802.11 stack (a different, harder point on the same map), and [`rtl-sdr-lineage.md`](rtl-sdr-lineage.md) for the receive-only end of the SDR world.

---

## 1. Why an SDR is the "whole PHY" (and a Wi-Fi chip is not)

A commercial Wi-Fi NIC gives you the top of the stack: you hand it a frame, it hands you a frame. The OFDM modulation, the convolutional coding, the preamble, the channel estimation, the automatic gain control — all of that happens inside sealed silicon and, at best, a signed binary firmware blob. Firmware reverse engineering (Nexmon, the CSI toolchains, the openwifi FPGA project) is the art of prying open *narrow windows* into that PHY: a monitor mode here, a per-subcarrier CSI dump there, a spectral scan register somewhere else.

A software-defined radio inverts the whole arrangement. The hardware is a near-transparent **RF front end + wideband ADC/DAC**: it converts a slice of spectrum to a stream of complex baseband samples (I/Q) and back, and does essentially nothing else. *Every* signal-processing step — synchronization, FFT, equalization, demapping, Viterbi decoding, descrambling — runs as software you can read, edit, and replace. That is the definition of **Tier 5** on this repo's ladder: an open, documented PHY where you own every sample.

`gr-ieee802-11` is the software that fills that gap for 802.11 OFDM. HackRF / USRP is the transparent radio underneath it.

---

## 2. The hardware: genuine SDRs

`gr-ieee802-11` is developed and tested primarily against **Ettus USRP N210** and **USRP B210**, and works with **HackRF One** and other GNU Radio-supported front ends with the usual caveats (clock accuracy, half- vs full-duplex, sample-rate headroom).

| SDR | Tuning | Max usable BW | Duplex | ADC | Ref clock | Rough cost | Notes for 802.11 |
|---|---|---|---|---|---|---|---|
| **HackRF One** | 1 MHz – 6 GHz | ~20 Msps (USB 2.0-limited, marginal) | Half | 8-bit | ±20 ppm (no TCXO stock) | ~$300–350 | Cheapest way in; 8-bit dynamic range and half-duplex hurt. Good for RX experiments; TX possible but jittery. |
| **USRP B210** | 70 MHz – 6 GHz | 56 MHz (AD9361) | Full (2×2) | 12-bit | ±2 ppm TCXO (GPSDO opt.) | ~$1,300+ | The comfortable choice: full-duplex, USB 3.0, plenty of BW headroom for 20 MHz Wi-Fi. |
| **USRP N210** | daughterboard (WBX/SBX/CBX ≈ 50 MHz–6 GHz) | ~25 MHz (GbE-limited) | Full | 14-bit | ±2.5 ppm (GPSDO opt.) | ~$1,700+ | The reference platform in the original papers; needs a swappable daughterboard. |

Compare that to the line-item cost of the radio you are *actually* trying to repurpose: the Wi-Fi chip already soldered into the laptop, phone, or ESP32 in front of you, which cost the OEM **single-digit dollars**. That price gap is half the thesis of this repository.

---

## 3. What `gr-ieee802-11` implements

The module is a full **802.11 OFDM transceiver** (not just a receiver):

- **Standards / bandwidths:** 802.11a & 802.11g at **20 MHz**, 802.11p at **10 MHz**, plus **5 MHz** narrowband — selected purely by changing the sample rate (20 / 10 / 5 Msps). Same DSP, scaled clock. This band-agility is itself something a stock NIC will never give you.
- **OFDM parameters:** 64-point FFT, 48 data + 4 pilot subcarriers, 16-sample cyclic prefix, the standard L-STF / L-LTF preamble.
- **Modulation & coding (the full MCS set):** BPSK, QPSK, 16-QAM, 64-QAM with convolutional coding rates 1/2, 2/3, 3/4 — i.e. the eight legacy data rates **6, 9, 12, 18, 24, 36, 48, 54 Mbit/s** at 20 MHz (halved at 10 MHz, quartered at 5 MHz).
- **FEC:** rate-1/2 K=7 convolutional encoder (generators 133/171 octal) with puncturing on TX; soft/hard Viterbi decoding on RX.
- **Interoperability:** the papers below demonstrate decoding frames from, and being decoded by, **commercial Wi-Fi cards** and other 802.11p prototypes — proof it is a standards-faithful PHY, not a toy.

### 3.1 Companion module: `gr-foo`

`gr-ieee802-11` depends on **`gr-foo`** for the plumbing that a real over-the-air, burst-mode SDR link needs:

- **Wireshark Connector** — emits PDUs as PCAP/radiotap so decoded frames open directly in Wireshark / tshark / tcpdump.
- **Packet Pad** / **Pad Tagged Stream** — zero-pads bursts and adds `tx_time` tags to avoid transmit underruns.
- **Burst Tagger** — adds `tx_sob` / `tx_eob` (start/end-of-burst) tags so a half-duplex radio (e.g. HackRF) keys up only for the packet.
- **Periodic Msg Source** / **Packet Dropper** — traffic generation and loss injection for throughput/BER testing.

---

## 4. Install (GNU Radio + gr-foo + gr-ieee802-11)

Match the module's `maint-*` branch to your GNU Radio version (`maint-3.7`, `maint-3.8`, `maint-3.10`, …). Example for GNU Radio 3.10 on a Debian/Ubuntu host:

```bash
# 0. GNU Radio + UHD (USRP) and/or HackRF host tools
sudo apt install gnuradio gnuradio-dev uhd-host hackrf libhackrf-dev \
                 cmake build-essential swig python3-numpy python3-opengl

# One-time SIMD kernel selection (big real-time throughput win)
volk_profile

# USRP only: download the FPGA images
sudo uhd_images_downloader

# 1. gr-foo (build first — gr-ieee802-11 links against it)
git clone -b maint-3.10 https://github.com/bastibl/gr-foo
cd gr-foo && mkdir build && cd build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
cd ../..

# 2. gr-ieee802-11
git clone -b maint-3.10 https://github.com/bastibl/gr-ieee802-11
cd gr-ieee802-11 && mkdir build && cd build
cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig
```

Two host-tuning steps the README calls out:

```bash
# Larger shared memory so GRC's circular buffers don't choke at 20 Msps
sudo sysctl -w kernel.shmmax=2147483648
```

For USRP daughterboards, run the Ettus **calibration utilities** (`uhd_cal_tx_dc_offset`, `uhd_cal_tx_iq_balance`, `uhd_cal_rx_iq_balance`) once per board (WBX/SBX/CBX) to null DC offset and I/Q imbalance — otherwise you get a spur at DC and a mirror image that wreck the constellation.

The OFDM PHY is a **hierarchical block**: open `examples/wifi_phy_hier.grc` in **GNU Radio Companion** once and generate it so `wifi_rx.grc` / `wifi_tx.grc` can import it.

---

## 5. The RX flowgraph — decoding 802.11a/g/p

`examples/wifi_rx.grc` is the over-the-air receiver. Conceptually the chain is:

```
USRP/HackRF Source (I/Q @ 20 Msps, 2.412–2.472 GHz or 5.9 GHz)
   │
   ├─► Sync Short   : autocorrelation on the L-STF → coarse frame detection + AGC + coarse CFO
   ├─► Sync Long    : cross-correlation on the L-LTF → symbol timing + fine CFO
   ├─► FFT (64-pt)  : per-symbol OFDM demodulation
   ├─► Frame Equalizer : channel estimate from LTF; pilot tracking; residual phase;
   │                     selectable equalizer (LS / STA / comb / LMS / SPD)
   ├─► Decode MAC   : demap → deinterleave → Viterbi decode → descramble → SIGNAL
   │                  field parse (rate/length) → payload decode → FCS/CRC-32 check
   └─► gr-foo Wireshark Connector ─► PCAP ─► Wireshark / tap0
```

Practical notes:

- Feed the **constellation sink** (needs `python3-opengl`) to *watch* BPSK/QPSK/16-/64-QAM clouds tighten as your equalizer and SNR improve — a live view of the PHY no NIC exposes.
- Point it at a nearby access point or a phone hotspot on channel 1/6/11; decoded beacons and data frames appear in Wireshark with radiotap headers.
- The **frame equalizer** choice matters a lot for 802.11p (high-mobility, fast-fading channels) — this is exactly the kind of PHY-level knob the whole SDR premise buys you.

Loopback without any radio at all: `examples/wifi_loopback.grc` wires the TX chain straight into the RX chain through a simulated channel — the fastest way to confirm the install decodes what it encodes.

---

## 6. The TX flowgraph — and why it is dangerous

`examples/wifi_tx.grc` runs the encoder in reverse: a message source (or `tap0`) → MAC framing → scrambler → convolutional encoder + puncturing → interleaver → constellation mapping → OFDM carrier allocator → 64-pt IFFT → cyclic-prefix + preamble insertion → `gr-foo` Packet Pad / Burst Tagger → USRP/HackRF Sink.

It works. It will put real, decodable 802.11 frames into the air. **That is precisely the problem.**

> ### ⚠️ Regulatory warning — read before you key up
>
> An SDR + this flowgraph is an **uncertified intentional radiator**. Transmitting 802.11 on it is trivially easy to do **illegally**, and "it was easy" is not a defense.
>
> - **No equipment authorization.** A commercial Wi-Fi NIC has passed **FCC Part 15** (US) / **ETSI EN 300 328** (2.4 GHz) / **EN 301 893** (5 GHz U-NII) and carries an ID. A HackRF/USRP running a GNU Radio flowgraph has passed *nothing*. Operating an uncertified transmitter in these bands is unlawful in most jurisdictions regardless of power.
> - **Power & spectral limits.** ISM/U-NII bands cap **EIRP** and impose spectral masks and, on U-NII, **DFS/TPC** (radar detection). An SDR ignores all of it by default; add any PA and you will exceed limits and splatter energy into adjacent channels and harmonics. HackRF and USRP front ends have **weak output filtering** — expect harmonics and wideband noise unless you add a proper bandpass filter.
> - **802.11p is a licensed band.** 802.11p lives at **5.850–5.925 GHz (ITS / C-V2X)**, reserved for vehicular/road-safety use in the US and EU. It is **not** a free-for-all ISM band. Do not transmit there over the air without the appropriate ITS/experimental authorization.
> - **Never** use TX for jamming, deauthentication, beacon spoofing, or evil-twin work. Those are separate criminal offenses on top of the spectrum violation.
>
> **Do this instead:** conduct all TX experiments **conducted, not radiated** — SDR TX port → coax → **attenuator(s)** → SDR RX port (or a shielded/anechoic enclosure). Use the lowest possible gain. If you must radiate, do it under an **amateur radio license** (in an amateur allocation, e.g. parts of the 2.4 GHz band, following those rules) or a formal **experimental license**, inside an RF-shielded chamber. The `wifi_loopback.grc` cabled/simulated path covers most learning goals with **zero** emissions.

---

## 7. Performance limits vs a real NIC

This is the crux of why Tier 5 is not automatically "best." A genuine SDR gives you the *whole* PHY but pays for it in latency, throughput, and real-time behavior:

| Dimension | `gr-ieee802-11` on HackRF/USRP | Commercial Wi-Fi NIC |
|---|---|---|
| **PHY access** | Total — every sample, every block, arbitrary waveforms | Sealed; narrow windows via firmware RE |
| **MAC** | **No real-time MAC.** No SIFS-timed ACKs (16 µs is unreachable through host+bus latency), no hardware CSMA/CA. Cannot properly participate in a contending BSS. | Full hardware MAC: ACK, RTS/CTS, backoff, aggregation, block-ACK |
| **Latency (air→app)** | **milliseconds** (USB/GbE transport + host DSP scheduling) | **microseconds** (on-chip) |
| **Throughput** | Real-time decode of a 20 MHz stream is **CPU-bound** and marginal on a laptop; 10 MHz 802.11p is comfortable. Sustained goodput far below line rate. | Hundreds of Mbit/s to Gbit/s, effortlessly |
| **Bus/BW ceiling** | HackRF ~20 Msps half-duplex over USB 2.0; N210 ~25 MHz over GbE; B210 up to 56 MHz over USB 3.0 | Dedicated PHY; 20/40/80/160 MHz channels native |
| **Duplex** | HackRF half-duplex; B210/N210 full-duplex | Full hardware TX/RX |
| **Cost** | $300 (HackRF) → $1,700+ (N210) **plus a capable host CPU** | ~$2–20, already in your device |
| **Power** | Watts of SDR + a laptop CPU pinned near 100% | Milliwatts |

The headline limitation is the **missing real-time MAC**: because ACK/CSMA timing cannot be met in software over a general-purpose bus, `gr-ieee802-11` is a superb *analysis and single-link/experimental* transceiver but a poor *network participant*. (This is exactly the wall that [`openwifi.md`](openwifi.md) climbs by pushing the time-critical MAC into **FPGA** — a much larger engineering effort than a GNU Radio flowgraph, and a different point on the map.)

---

## 8. Why this proves the point of the whole repo

Put the two worlds side by side:

- **The SDR (this page).** Full PHY, Tier 5, infinitely hackable — and slow, expensive, power-hungry, non-real-time, and legally fraught to transmit with. It is the *reference*: it shows you the entire signal chain that the silicon hides.
- **The Wi-Fi chip in your laptop (the rest of this repo).** Already present, ~$2, real-time hardware MAC, certified to transmit, sips power — but a black box you must *reverse-engineer* to extract even a sliver of PHY access.

Everything the "Latent Radios" catalog documents — Nexmon monitor/injection (Tier 1), the CSI toolchains (Tier 2), spectral-scan registers (Tier 3), the rare arbitrary-waveform test modes (Tier 4) — is the story of **clawing back pieces of the SDR from a chip that already lives in your device, for free, with certification and a real MAC intact**. `gr-ieee802-11` on a HackRF is the yardstick those pieces are measured against: it is the *whole* PHY made of software, proving both what is possible (everything) and why you would still reach for the cheap sealed chip first (cost, speed, legality, power).

That trade — **total access at high cost and low speed** vs. **narrow access at near-zero cost and full speed** — is the entire subject of this repository. See [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md) for the side-by-side tier framing across all the hardware here.

---

## 9. References (primary)

- **`gr-ieee802-11` source** — B. Bloessl et al. <https://github.com/bastibl/gr-ieee802-11>
- **`gr-foo` source** — <https://github.com/bastibl/gr-foo>
- **WIME Project home** — <https://www.wime-project.net>
- B. Bloessl, M. Segata, C. Sommer, F. Dressler, **"An IEEE 802.11a/g/p OFDM Receiver for GNU Radio,"** *2nd ACM SIGCOMM Workshop on Software Radio Implementation Forum (SRIF '13)*, Hong Kong, Aug. 2013, pp. 9–16. DOI: 10.1145/2491246.2491248.
- B. Bloessl, M. Segata, C. Sommer, F. Dressler, **"Decoding IEEE 802.11a/g/p OFDM in Software using GNU Radio,"** demo, *ACM MobiCom 2013*.
- B. Bloessl, M. Segata, C. Sommer, F. Dressler, **"Performance Assessment of IEEE 802.11p with an Open Source SDR-based Prototype,"** *IEEE Transactions on Mobile Computing*, 17(5):1162–1175, May 2018. DOI: 10.1109/TMC.2017.2751474.
- Ettus Research **UHD** / USRP B210 & N210 product pages and daughterboard specs — <https://www.ettus.com>
- Great Scott Gadgets **HackRF One** — <https://greatscottgadgets.com/hackrf/>

*Regulatory references to consult before any transmission:* FCC 47 CFR Part 15 (US, unlicensed); ETSI EN 300 328 (2.4 GHz); ETSI EN 301 893 (5 GHz U-NII / DFS); and your national administration's ITS/5.9 GHz allocation rules for 802.11p.
