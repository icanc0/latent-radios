# openwifi — The Fully Open-Source 802.11 SDR (the real Tier-5 endpoint)

> _"openwifi: a free and open-source IEEE 802.11 WiFi baseband FPGA (chip) design — driver, software, PHY and MAC source you can read, change, and rebuild."_ — [open-sdr/openwifi](https://github.com/open-sdr/openwifi)

Every other chip in *Latent Radios* is a black box you pry open from the outside: you patch closed firmware ([Nexmon](./nexmon.md)), poke undocumented registers ([ath9k spectral/CSI](../chips/qualcomm-atheros.md)), or catch a debug-mode IQ stream that was never meant to escape ([RTL-SDR](./rtl-sdr-lineage.md)). You climb the [SDR ladder](../docs/taxonomy.md) *upward* toward a radio you do not own.

**openwifi is the opposite.** It is a from-scratch, license-clean 802.11a/g/n transceiver where **the PHY is Verilog you can read, the low-MAC is Verilog you can read, and the driver is mac80211 C you can read** — running on an FPGA + AD9361 RF front-end. There is no firmware to reverse because there is no secret. That is what **Tier 5** means on this ladder: *the PHY is yours*. openwifi is the datum the rest of the catalog is measured against — the answer to "what would it take to actually own a Wi-Fi radio?" — and this file explains what that buys you, what it costs, and why it is a fundamentally different animal from chip-repurposing.

Led by **Xianjun Jiao** (imec / Ghent University) with Wei Liu, Michael Mehari, Muhammad Aslam, and Ingrid Moerman. Licensed **AGPL-3.0+** (with GPLv2/BSD components), commercial licensing via [openwifi.tech](https://openwifi.tech).

---

## 1. Why openwifi is genuinely Tier 5 (and Broadcom/Atheros are not)

The ladder tops out at **Tier 5 = open/documented PHY**: you possess and can modify the baseband signal-processing chain itself, not merely steer a sealed one. The distinction is concrete:

| | Repurposed Wi-Fi chip (Tiers 1–4) | openwifi (Tier 5) |
|---|---|---|
| PHY (OFDM modem) | Closed silicon/ucode; you feed it or read its outputs | **Verilog source** — FFT, channel est., Viterbi, scrambler, interleaver all editable |
| Low-MAC (ACK/backoff/SIFS timing) | Hard real-time in D11 ucode / ASIC, undocumented | **Verilog state machine** — you set SIFS, slot time, CCA, CW, TX power per-packet |
| Raw IQ | Rarely; a side-effect of a debug mode, ISM-locked | **First-class**: capture/inject baseband IQ at the AD9361 (70 MHz–6 GHz) |
| Modify the waveform | Only by replaying a stored buffer (Nexmon jammer) | **Author any PHY** — change constellation, preamble, timing, or bolt on a non-802.11 modem |
| Source of truth | RE'd from dumps; correct until the next firmware rev | The build *is* the truth; rebuild from HDL |

A Nexmon-patched BCM4339 can reach [Tier 4 (author an IQ buffer and transmit it)](./nexmon.md) — impressive, but the modem around that buffer is still a sealed box whose timing and constellation you cannot touch. openwifi hands you the box open. See [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md) for how this sits next to true SDRs (USRP, bladeRF, Pluto) — openwifi essentially *is* one of those boards, plus a complete open Wi-Fi stack running on its FPGA.

---

## 2. Architecture — three blocks, all open

openwifi is a **SoC design**: everything but the RF transceiver lives inside a single Xilinx Zynq (ARM Cortex-A9 + 7-series FPGA fabric).

```
   ┌─────────────────────────── Zynq SoC ───────────────────────────┐
   │  ARM Cortex-A9 (PS)                 FPGA fabric (PL)            │      AD9361 / AD9363
   │  ┌─────────────────────┐   AXI    ┌──────────────────────────┐ │  ┌──────────────────┐
   │  │ Linux + mac80211    │◄────────►│ openwifi baseband:       │ │  │ RF agile         │
   │  │  sdr.ko driver      │  DMA/IRQ │  • openofdm RX (Rx)      │◄├──┤ transceiver      │
   │  │  high-MAC (kernel)  │          │  • openofdm/TX PHY       │─├──►│ 70 MHz–6 GHz     │
   │  │  hostapd / wpa_sup  │          │  • low-MAC DCF (CSMA/CA) │ │  │ 2–20 MHz BW      │
   │  │  nl80211 userspace  │          │  • side-channel/CSI taps │ │  │ real-time SPI    │
   │  └─────────────────────┘          └──────────────────────────┘ │  │ ctrl from FPGA   │
   └────────────────────────────────────────────────────────────────┘  └──────────────────┘
```

- **RF front-end — Analog Devices AD9361/AD9363** ("RF-agile transceiver"): the same chip inside USRP B210, bladeRF 2.0, and PlutoSDR. 70 MHz–6 GHz, 12-bit, up to 56 MHz sample rate (openwifi runs the Wi-Fi PHY at 2–20 MHz channel BW). Crucially, openwifi drives the AD9361 **SPI control from the FPGA**, achieving the sub-microsecond RF turnaround 802.11 timing demands (a host-driven SDR cannot meet SIFS).
- **FPGA baseband (PL)** — the [openwifi-hw](https://github.com/open-sdr/openwifi-hw) repo. The receiver builds on Jiao's **openofdm** decoder; TX PHY, the DCF **low-MAC** (carrier sense, backoff, ACK generation, per-packet TX power), and the AXI/DMA plumbing to the ARM are all in Verilog with a MATLAB/Octave reference model for the DSP.
- **ARM Linux + mac80211 driver** — the [openwifi](https://github.com/open-sdr/openwifi) repo. `sdr.ko` is a **standard Linux `mac80211` SoftMAC driver**, so the chip appears as an ordinary `wlanX` interface: `iw`, `hostapd`, `wpa_supplicant`, `scapy`, and `tcpdump` all work unmodified. High-MAC (association, aggregation control) is the normal kernel stack.

Three repos: **openwifi** (driver + boot files), **openwifi-hw** (FPGA source), **openwifi-hw-img** (prebuilt bitstreams so you can run without Vivado on supported boards).

---

## 3. Supported boards (net-new Tier-5 records)

openwifi targets any **Zynq-7000 (or Zynq UltraScale+) + AD9361/AD9363** combination. The `boards/` directory in openwifi-hw selects the FPGA build; prebuilt SD-card images exist for the common ones.

| Board (openwifi id) | Zynq part | RF | MIMO | Vivado licence for rebuild? | Notes |
|---|---|---|---|---|---|
| **ADRV9361-Z7035** (`adrv9361z7035`) | Z7035 (larger PL) | AD9361 | 2×2 | Yes (7035 needs paid Vivado) | Flagship 2×2 SOM on ADRV1CRR carrier; most capable |
| **ADRV9364-Z7020** (`adrv9364z7020`) | Z7020 | AD9364 | 1×1 | **No** (WebPACK covers 7020) | Cheapest ADI SOM path; single-stream |
| **ANTSDR / E310v2 / E200** (`antsdr`, `e310v2`, `antsdr_e200`) | Z7020 | AD9361/AD9363 | 1×1 (some 2×2) | No | MicroPhase Pluto-adjacent boards, low cost |
| **Xilinx ZC706 + FMCOMMS2/3/4** (`zc706_fmcs2`) | Z7045 | AD9361 | 2×2 | Yes | Classic dev reference platform |
| **Xilinx ZedBoard + FMCOMMS2/3/4** (`zed_fmcs2`) | Z7020 | AD9361 | 1×1 | No | Common academic combo |
| **Xilinx ZCU102 + FMCOMMS** (`zcu102_fmcs2`) | UltraScale+ | AD9361 | 2×2 | Yes | UltraScale+ path |
| **NeptuneSDR / LibreSDR** (unofficial) | Z7020 | AD9361 | 2×2 | No | Low-cost community Zynq-7020+AD9361 clones |

The **ADALM-PLUTO** (Z7010 + AD9363) is *adjacent* but its Z7010 is too small for the full openwifi PL; the ANTSDR/E310-class boards are the "Pluto-form-factor" way to run openwifi. See [../chips/hardware-index.md](../chips/hardware-index.md) and [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md) for how these compare to Pluto/USRP/bladeRF as raw SDRs.

---

## 4. Build & run (end-to-end)

Prereqs: a supported board, an SD card, a host Linux PC, and (only if you rebuild the FPGA) Xilinx Vivado + the version openwifi pins. To *run* on a supported board you need **no Vivado** — flash a prebuilt image.

```bash
# 1. Get the driver/software repo
git clone https://github.com/open-sdr/openwifi.git
cd openwifi

# 2. Fetch a prebuilt SD image for your board (see doc/ + Releases),
#    write it to the SD card, insert, boot the board, then SSH in (root@192.168.10.122 typical)

# 3. On the board: load the FPGA bitstream + driver for your board name
cd openwifi
./wgd.sh          # "wifi go der" — loads .bit, inserts sdr.ko, brings up sdr0

# 4. It is now a normal Linux Wi-Fi interface:
iw dev
iwconfig sdr0
# scan / associate / run hostapd exactly like any mac80211 card
```

To modify the PHY/MAC you rebuild the FPGA from [openwifi-hw](https://github.com/open-sdr/openwifi-hw) (`git clone`, source `setup.sh`, `./boards/<board>/openwifi.tcl` in Vivado), regenerate the bitstream, and re-run `wgd.sh`. The MATLAB/Octave models under `openwifi-hw` let you validate DSP changes in simulation before synthesis.

**Verification of a live install:** `dmesg | grep sdr` shows the driver binding; `iw dev sdr0 info` reports the interface; a second Wi-Fi device (phone/laptop) can associate to an openwifi `hostapd` AP, or openwifi can associate to a commercial AP — real interoperation with off-the-shelf 802.11a/g/n is the acceptance test.

---

## 5. What openwifi does that no repurposed chip can

This is the payoff of owning the PHY/MAC. All of these are documented app-notes in the repo (`doc/app_notes/`), not speculation.

1. **Arbitrary / custom PHY.** Because the modem is Verilog, you can change the constellation, insert a custom preamble, alter the scrambler/interleaver, or graft a non-802.11 waveform onto the same RF. This is `arbitrary-waveform` at the *design* level, not the replay-a-buffer level.
2. **Precise, programmable MAC timing.** SIFS, slot time, CCA threshold, contention window, and per-packet TX power are **registers into the low-MAC**, tunable at runtime. Standards-violating timing (for reactive experiments, TSN, or attack/defense research) is a config change, not a fight with sealed ucode.
3. **Real, per-packet CSI + raw IQ to the host.** openwifi exports per-subcarrier channel estimate, frequency offset, and equalizer state, plus real-time IQ capture with AGC/RSSI — from a *documented* tap point. Compare to the RE'd, format-varies-by-chip CSI in [../projects/csi-toolchains.md](../projects/csi-toolchains.md).
4. **Full-duplex self-reception → Wi-Fi radar.** The baseband can receive its own transmitted signal (`doc/app_notes/radar-self-csi.md`). A **SIMO openwifi radar** (1 TX, 2 RX) senses passive targets and does joint radar+communication — vital-sign and presence sensing demonstrated by the authors.
5. **CSI fuzzer / covert channel.** A 3-tap FIR between PHY-TX and DAC imposes an *artificial* channel impulse response on the outgoing signal; thanks to full-duplex + CSI extraction, an authorized receiver reads a side channel over-the-air without disturbing normal traffic (WiSec 2021, `doc/app_notes/csi_fuzzer.md`).
6. **Security / protocol fuzzing.** openwifi is the injection engine behind **Owfuzz** (WiSec 2023): monitor + inject *any* 802.11 frame — including malformed/edge-case frames a commercial NIC's firmware refuses to emit — to fuzz commercial Wi-Fi devices over the air.

No amount of firmware patching on a Broadcom/Atheros/Realtek part reaches 1–2 or the *documented* forms of 3–5, because the modem and hard-real-time MAC are not yours to change.

---

## 6. The limits (why you still keep a Broadcom card)

Tier 5 is not "strictly better" — it trades ubiquity and speed for openness.

- **Throughput.** openwifi tops out around **40–50 Mbps** TCP / ~50 Mbps UDP (with AMPDU) on 802.11n 20 MHz — an order of magnitude below a modern commercial NIC. It is a research radio, not a fast one.
- **Standard coverage.** **802.11a/g/n only** (up to 20 MHz, single/limited spatial streams on most boards). No mainline 802.11ac/ax/be, no 40/80/160 MHz, no 6 GHz, no 60 GHz. 802.11ax is an experimental/commercial add-on. For Wi-Fi 6E/7 and mmWave you are back to chip-repurposing ([../docs/wifi7-and-6ghz.md](../docs/wifi7-and-6ghz.md), [../docs/mmwave-60ghz-radar.md](../docs/mmwave-60ghz-radar.md)).
- **Cost & bulk.** A capable board (ADRV9361-Z7035 SOM + carrier) is hundreds of dollars and the size of a small SBC — versus a $10 Realtek dongle or the Wi-Fi chip already in your phone. You cannot deploy openwifi in a billion handsets; that is exactly why the rest of the catalog exists.
- **Toolchain weight.** Editing the PHY means Vivado, HDL, and synthesis timing closure — a heavier lift than a C patch in Nexmon or a `debugfs` write in ath9k.

**Rule of thumb:** use openwifi when you need to *own the PHY/MAC* (new waveforms, exact timing, radar, side channels, standards-compliant-but-hostile frames); use a repurposed chip when you need ubiquity, cost, higher-order standards, or a form factor that fits in a pocket.

---

## 7. Other open-PHY 802.11 efforts (brief survey)

openwifi is the most complete *real-time, standard-interoperable, mac80211-integrated* open stack, but it stands on a lineage:

| Project | What it is | PHY location | Real-time MAC? | Status |
|---|---|---|---|---|
| **openwifi** | Full a/g/n SDR on Zynq+AD9361, mac80211 driver | FPGA (Verilog) | **Yes** (FPGA DCF) | Active, interoperates with real APs |
| **gr-ieee802-11** (Bloessl / bastibl) | 802.11a/g/p **OFDM transceiver in GNU Radio** flowgraph, runs on any SDR (USRP/Pluto) | Host CPU (GNU Radio) | No (host latency ≫ SIFS) | Active; RX/TX but cannot ACK in time to be a real STA |
| **gr-ieee80211** (cloud9477) | Newer GNU Radio 802.11a/g/n/ac TX+RX incl. MIMO | Host CPU | No | Research, VHT/MIMO focus |
| **WARP + Mango 802.11 Ref Design** | Rice University WARP v3 FPGA; real-time OFDM PHY + DCF MAC, can be AP/STA/IBSS | FPGA (Virtex-6) | **Yes** | Legacy — hardware discontinued (Mango wound down); designs archived |
| **SoftMAC (mac80211) generally** | The Linux framework openwifi plugs into: MAC management in kernel, PHY in device | device (FPGA/chip) | depends on device | The integration layer, not a PHY itself |

- **gr-ieee802-11** is the reference "PHY entirely in software on the host" approach: brilliant for RX analysis and offline TX, but host↔SDR latency makes it unable to meet 802.11's SIFS/ACK deadlines, so it cannot behave as a live station the way openwifi (FPGA MAC) can. Repo: [github.com/bastibl/gr-ieee802-11](https://github.com/bastibl/gr-ieee802-11); paper: Bloessl et al., "An IEEE 802.11a/g/p OFDM Receiver for GNU Radio," SRIF 2013.
- **WARP** (Wireless open-Access Research Platform, Rice, 2006; commercialized by **Mango Communications**) was the FPGA-testbed ancestor of this whole idea — a real-time open 802.11 PHY+MAC — but on expensive, now-discontinued Virtex hardware. openwifi is effectively its spiritual successor on cheap Zynq+AD9361 silicon with a mainline-Linux driver.

---

## Summary table

| Aspect | openwifi |
|---|---|
| Ladder rung | **Tier 5** — open/documented PHY *and* MAC |
| Capabilities | monitor, injection, per-subcarrier CSI, raw IQ, arbitrary/custom PHY, full-duplex radar, covert channel, protocol fuzzing |
| Standards | 802.11a/g/n (≤20 MHz); ax experimental/commercial |
| RF | AD9361/AD9363, 70 MHz–6 GHz, 2–20 MHz BW |
| Compute | Xilinx Zynq (ARM A9 + 7-series FPGA) |
| Driver | mainline-style Linux `mac80211` SoftMAC (`sdr.ko`) |
| Throughput | ~40–50 Mbps (research-grade) |
| Licence | AGPL-3.0+ (GPLv2/BSD parts); commercial via openwifi.tech |
| Status | **verified** — works with public tooling, interoperates with commercial 802.11 |

## Key references

- Main repo (driver/software) — <https://github.com/open-sdr/openwifi>
- FPGA baseband — <https://github.com/open-sdr/openwifi-hw>
- Prebuilt bitstreams — <https://github.com/open-sdr/openwifi-hw-img>
- App-notes (CSI, radar-self-csi, csi_fuzzer, etc.) — <https://github.com/open-sdr/openwifi/tree/master/doc/app_notes>
- Jiao, Liu, Mehari, Aslam, Moerman, "openwifi: a free and open-source IEEE802.11 SDR implementation on SoC," IEEE VTC2020-Spring — <https://ieeexplore.ieee.org/document/9128614/>
- Jiao et al., "openwifi CSI fuzzer for authorized sensing and covert channels," ACM WiSec 2021 — <https://dl.acm.org/doi/10.1145/3448300.3468255>
- Owfuzz (openwifi-based Wi-Fi fuzzing), ACM WiSec 2023 — <https://dl.acm.org/doi/10.1145/3558482.3590174>; tool: <https://github.com/alipay/Owfuzz>
- openofdm decoder (predecessor) — <https://github.com/jhshi/openofdm>
- gr-ieee802-11 (Bloessl) — <https://github.com/bastibl/gr-ieee802-11>
- WARP / Mango 802.11 Reference Design — <https://warpproject.org/trac/wiki/802.11>
- Analog Devices AD9361 — <https://www.analog.com/en/products/ad9361.html>
- Comparison to true SDRs — [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)

## Un-cataloged / TODO
- Exact per-board PL utilization and which boards support 2×2 vs 1×1 in the current `openwifi-hw` tree.
- 802.11ax experimental branch scope (which OFDMA/HE features are open vs. commercial-only).
- openwifi-on-ZCU111/RFSoC direct-RF experiments (dropping the AD9361).
- Latency/timing-closure numbers for custom low-MAC edits (SIFS margin per board clock).
- Cross-link a hands-on walkthrough (`docs/walkthroughs/`) building a custom preamble/PHY tap once written.
