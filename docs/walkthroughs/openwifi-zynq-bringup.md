# Bringing up openwifi on a Zynq SDR — the real open-PHY path

> Every other walkthrough in *Latent Radios* pries a **closed** radio open from the outside: patch Broadcom firmware ([Nexmon](../../projects/nexmon.md)), poke undocumented Atheros registers ([ath9k spectral/CSI](./atheros-ath9k-spectral-csi.md)), or catch a debug IQ stream that was never meant to escape ([RTL-SDR](../../projects/rtl-sdr-lineage.md)). **openwifi is the opposite.** It is a from-scratch, license-clean 802.11a/g/n transceiver where the PHY is Verilog you can read, the low-MAC is Verilog you can read, and the driver is mainline-style `mac80211` C you can read — running on a Xilinx Zynq FPGA + an Analog Devices AD9361 RF front-end. There is no firmware to reverse because there is no secret.

This is the **Tier-5** rung of the [SDR ladder](../taxonomy.md): *the PHY is yours*. This walkthrough takes a supported Zynq board from a blank SD card to a live `sdr0` Wi-Fi interface, then out onto the two things chip-repurposing can never fully give you — a **documented** per-packet CSI/side-info tap and a **documented** raw-IQ tap — and ends by contrasting honestly with the rest of the catalog. For the conceptual overview of *why* openwifi is genuinely Tier 5, see [../../projects/openwifi.md](../../projects/openwifi.md); for where it sits next to true SDRs, see [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md).

Upstream: **[open-sdr/openwifi](https://github.com/open-sdr/openwifi)** (driver + software) and **[open-sdr/openwifi-hw](https://github.com/open-sdr/openwifi-hw)** (FPGA source), led by Xianjun Jiao et al. (imec / Ghent University), AGPL-3.0+.

---

## 1. What you get vs. chip-repurposing (read this first)

openwifi is not "strictly better" than a patched Broadcom or Atheros card — it trades ubiquity, cost, and standard-coverage for **total, documented control of the baseband and MAC timing**. Be honest about the trade before you spend the money.

| | Repurposed Wi-Fi chip (Tiers 1–4) | openwifi (Tier 5) |
|---|---|---|
| PHY (OFDM modem) | Closed silicon/ucode; you feed or read it | **Verilog source** — FFT, chan-est, Viterbi, scrambler, interleaver all editable |
| Low-MAC timing (SIFS/backoff/CCA) | Hard real-time in ASIC/ucode, undocumented | **Verilog DCF state machine** — 10 µs SIFS in FPGA; SIFS/slot/CCA/CW/TX-power are registers |
| Raw IQ | Rare, a side-effect of a debug mode, ISM-locked | **First-class, documented tap** at the AD9361 (70 MHz–6 GHz front-end) |
| CSI / side info | Reverse-engineered, format varies by chip | **Documented** per-packet: TSF, CFO, channel response, equalizer constellation |
| Modify the waveform | Replay a stored IQ buffer (Nexmon jammer) | **Author any PHY** in HDL — constellation, preamble, timing, or a non-802.11 modem |
| Standards | Whatever the silicon does — up to Wi-Fi 6E/7, 60 GHz | **802.11a/g/n only, ≤20 MHz** (ax is experimental/commercial) |
| Throughput | Line-rate commercial | **~40–50 Mbps** — a research radio, not a fast one |
| Cost / form factor | $10 dongle, or the chip already in your phone | Hundreds of $, SBC-sized board + RF front-end |

**Rule of thumb:** reach for openwifi when you must *own* the PHY/MAC (new waveforms, exact timing, radar, covert channels, standards-compliant-but-hostile frames); reach for a repurposed chip when you need ubiquity, cost, higher standards (ac/ax/be, 6 GHz, 60 GHz), or a pocketable form factor. Most serious labs keep both.

---

## 2. Supported boards & choosing one

openwifi targets any **Zynq-7000 / Zynq UltraScale+ + AD9361/AD9363** combination. The board name selects the FPGA build and the boot files; prebuilt SD images exist for the common targets, so **you need no Vivado to run** — only to rebuild the HDL.

| openwifi board name | SoC / RF | MIMO | Vivado to rebuild? | Catalog record |
|---|---|---|---|---|
| `adrv9361z7035` | Zynq-7035 + AD9361 | 2×2 | **Yes** (7035 needs paid Vivado) | `adi-adrv9361-z7035` (existing) |
| `adrv9364z7020` | Zynq-7020 + AD9364 | 1×1 | No (WebPACK covers 7020) | `adi-adrv9364-z7020` (existing) |
| `antsdr`, `antsdr_e200`, `e310v2`, `sdrpi` | Zynq-7020 + AD9361/AD9363 | 1×1 (some 2×2) | No | `microphase-antsdr-openwifi` (existing) |
| `zc706_fmcs2` | Zynq-7045 + AD-FMCOMMS2/3/4 | 2×2 | **Yes** | `xilinx-zc706-fmcomms-openwifi` (existing) |
| `zed_fmcs2` | Zynq-7020 (ZedBoard) + FMCOMMS2/3/4 | 1×1 | No | **`xilinx-zedboard-fmcomms2-openwifi` (new)** |
| `zcu102_fmcs2` | Zynq UltraScale+ ZU9EG + FMCOMMS | 2×2 | **Yes** | **`xilinx-zcu102-fmcomms-openwifi` (new)** |
| `LibreSDR` | Zynq-7020 + AD9361 (clone) | 2×2 | No | **`libresdr-openwifi` (new)** |
| `neptunesdr` | Zynq-7020 + AD9361 (clone) | 2×2 | No | **`neptunesdr-openwifi` (new)** |

**Which to buy:**
- **Cheapest license-free path:** `adrv9364z7020` SOM, or a MicroPhase **AntSDR E200** (`antsdr_e200`). The Zynq-7020 is covered by free Vivado **WebPACK**, so you can rebuild the PHY without a paid license.
- **Most capable official board:** `adrv9361z7035` (2×2, largest 7-series PL) — but the 7035 needs a paid Vivado edition to synthesize.
- **Classic dev reference:** Xilinx **ZC706** + an Analog Devices **FMCOMMS2/3/4** FMC card (`zc706_fmcs2`), or the cheaper **ZedBoard** + FMCOMMS2 (`zed_fmcs2`) — the common academic combo.
- **UltraScale+ path:** ZCU102 + FMCOMMS (`zcu102_fmcs2`).
- **Low-cost community clones:** LibreSDR / NeptuneSDR — Zynq-7020 + AD9361 boards in a Pluto-ish form factor. They are in the board list but get less official test coverage; treat them as "works, with caveats."

> **On the ADALM-Pluto:** the Pluto is Zynq-7010 + AD9363, and its **7010 PL is too small** for the full openwifi baseband. The AntSDR/E310-class boards are the "Pluto-form-factor" way to run openwifi; the Pluto itself is a Tier-3/4 *true SDR* (see [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md)), not an openwifi target.

You also need: a **micro-SD card** (≥8 GB), an Ethernet cable (control plane / SSH), **antennas or 50 Ω cables + attenuators** for the RF ports (cable + attenuator is strongly preferred for TX experiments), and a host Linux PC.

---

## 3. Flash the prebuilt SD-card image

To *run* openwifi you flash a prebuilt image — no Vivado, no HDL build. Grab the image matching your board from the [openwifi releases / img links](https://github.com/open-sdr/openwifi) (the project ships one compressed `.img` plus per-board `BOOT/` overlays).

```bash
# 1. Extract the downloaded image, then find your SD device (NOT a disk on your PC!)
lsblk
sudo fdisk -l            # confirm the exact /dev/sdX or /dev/mmcblkN of the card

# 2. Write it. Use the count printed for your image; verify size with fdisk -l first.
sudo dd bs=512 count=31116288 if=openwifi-xyz.img of=/dev/your_sdcard_dev status=progress
sync
```

> ⚠️ **`dd` is unforgiving** — the wrong `of=` overwrites your PC's disk. Double-check with `lsblk` before and after inserting the card so you are certain which device is the SD card.

After flashing, apply the **board-specific overlay** onto the mounted card:

```bash
# Re-plug the card so the BOOT and rootfs partitions mount, then:
# copy the per-board boot files (bitstream, devicetree, FSBL/u-boot) into the BOOT root
cp -r BOOT/openwifi/<board_name>/*  /media/$USER/BOOT/

# housekeeping the image ships (safe to remove if present):
rm -rf /media/$USER/rootfs/root/kernel_modules
rm -f  /media/$USER/rootfs/etc/network/interfaces.new
sync
```

Replace `<board_name>` with your target from §2 (`adrv9364z7020`, `zed_fmcs2`, `antsdr_e200`, …). The `BOOT/openwifi/<board_name>/` directory contains that board's FPGA bitstream (`system_top.bit.bin`), device tree, and first-stage boot loader — this is the step that makes one image boot on many boards.

---

## 4. Boot the board & first login

1. Set the board's boot-mode jumpers/switches to **SD boot**.
2. Connect the **RF ports to antennas or (better) a cabled+attenuated setup**, connect **Ethernet**, insert the SD card, power on.
3. The board's default control-plane address is **`192.168.10.122`**. Put your PC on that subnet (e.g. `192.168.10.1/24`) and SSH in:

```bash
ssh root@192.168.10.122     # password: openwifi
```

First boot on a fresh card, expand the rootfs and run the one-time setup:

```bash
raspi-config --expand-rootfs   # (on the SD-based boards that ship this helper)
./openwifi/setup_once.sh       # one-time environment setup
```

---

## 5. Load the bitstream & bring up `sdr0`

`wgd.sh` ("wifi go der") is the whole bring-up: it programs the FPGA with `system_top.bit.bin` if present, inserts the `sdr.ko` mac80211 driver (plus the AD9361 and DMA modules), and creates the `sdr0` interface.

```bash
cd openwifi
./wgd.sh          # program FPGA + insert sdr.ko -> sdr0 appears
# ./wgd.sh 1      # same, but enable experimental AMPDU aggregation (test_mode bit0)
```

Verify the interface came up:

```bash
dmesg | grep sdr           # driver binding, AD9361 detected, no firmware/DMA errors
iw dev                     # sdr0 listed as a phy/interface
iwconfig sdr0              # openwifi wireless interface
ifconfig sdr0 up
```

From here **`sdr0` is an ordinary Linux `mac80211` interface.** `iw`, `hostapd`, `wpa_supplicant`, `tcpdump`, and `scapy` all work unmodified. openwifi ships convenience scripts:

```bash
./fosdem.sh          # bring sdr0 up in a default 802.11 config
./fosdem-11ag.sh     # force legacy 802.11a/g mode
./monitor_ch.sh sdr0 11   # put sdr0 into monitor mode on channel 11 (used by CSI/IQ capture)
```

**Acceptance test — real interoperation:** run `hostapd` on openwifi and associate a phone/laptop to it, *or* have openwifi associate to a commercial AP. Passing traffic with off-the-shelf 802.11a/g/n gear is the honest proof the open PHY works — not a loopback.

### `sdrctl` — the runtime knob for the open MAC/PHY

openwifi exposes MAC/PHY parameters and FPGA registers at runtime through `sdrctl`:

```bash
# parameters
sdrctl dev sdr0 get para_name
sdrctl dev sdr0 set para_name value

# raw FPGA module registers (module_name e.g. drv_tx, drv_rx, xpu, tx_intf, rx_intf)
sdrctl dev sdr0 get reg <module> <reg_idx>
sdrctl dev sdr0 set reg <module> <reg_idx> <value>

# verbose driver logging while you experiment
sdrctl dev sdr0 set reg drv_tx 7 3
sdrctl dev sdr0 set reg drv_rx 7 3
dmesg
```

Because SIFS/slot-time/CCA/contention-window/TX-power live in the FPGA DCF and are register-mapped, changing 802.11 timing here is a `sdrctl` write — not a fight with sealed ucode. That is the whole point of Tier 5.

---

## 6. Capture per-packet CSI / side-info (the open side channel)

openwifi's **side channel** is a documented FPGA tap that streams, per received packet, the values the PHY computed internally. This is the "side info" — the honest, *documented* analogue of the reverse-engineered CSI in [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md).

**On the board:**

```bash
cd openwifi
./wgd.sh
./monitor_ch.sh sdr0 11        # monitor on the channel you want to observe

# insert the side-channel driver (default = CSI mode, up to 8 equalizer taps)
insmod side_ch.ko              # optional: num_eq_init=X  (X 0..8, equalizer outputs)

# arm capture and start streaming side info (default 100 ms interval)
./side_ch_ctl g               # ./side_ch_ctl gN  -> N ms interval
```

**On your host PC** (the display script pulls the side-info stream from the board over the network):

```bash
cd openwifi/user_space/side_ch_ctl_src
python3 side_info_display.py        # live: CFO, channel response, equalizer constellation
```

**Side-info format.** Each element is 64-bit; per captured packet the tap delivers:

| Field | Meaning |
|---|---|
| Timestamp | 64-bit TSF timer (packet arrival) |
| Frequency offset | estimated CFO (low 16 bits used) |
| Channel response | per-subcarrier channel estimate, I/Q (low 16 bits each) — the CSI |
| Equalizer output | equalized constellation points, I/Q (low 16 bits each), up to `num_eq_init` taps |

**Conditional capture / filtering.** You can trigger only on frames matching header fields, so you record just the link you care about instead of everything on-air:

```bash
./side_ch_ctl wh1hY     # match on Frame Control (FC)
./side_ch_ctl wh5hY     # match on addr1
./side_ch_ctl wh6hY     # match on addr2
./side_ch_ctl wh7hY     # match on addr3
```

Data logs to `side_info.txt` for offline work; the repo ships `test_side_info_file_display.m` (MATLAB/Octave) to render a saved capture. Full details and the FIR/covert-channel extensions are in the app notes `doc/app_notes/csi.md` and `doc/app_notes/csi_fuzzer.md`, and radar self-reception in `doc/app_notes/radar-self-csi.md`.

---

## 7. Capture raw IQ (Tier-3 tap, documented)

The same `side_ch.ko` re-purposed into **IQ mode** streams baseband IQ samples with real-time AGC/RSSI to the host — a documented raw-IQ tap, not a reverse-engineered debug mode.

```bash
# insert in IQ mode (this parameter turns OFF the default CSI mode).
insmod side_ch.ko iq_len_init=8187     # use 4095 on smaller-PL boards (e.g. 7020)

# select IQ source and pre-trigger length, then arm
./side_ch_ctl wh3h01                   # choose IQ capture source
./side_ch_ctl wh11d4094                # pre-trigger length (0..8190)
./side_ch_ctl g                        # arm (default 100 ms interval)

# free-running (always-triggered) capture instead of packet-triggered:
./side_ch_ctl wh8d0
./side_ch_ctl wh5d1
```

**On the host:**

```bash
cd openwifi/user_space/side_ch_ctl_src
python3 iq_capture.py        # captures every 100 ms until Ctrl-C; logs to iq.txt
```

Capture is **trigger-based** by default (on packet detection), with the trigger condition set via `./side_ch_ctl wh8dY`. Samples are the openwifi baseband IQ (20 MHz-channel-class sampling; the AD9361 runs faster and is decimated to the PHY rate — the app note does not pin an exact figure, so measure it against a known tone rather than assuming). The two-antenna variant is documented in `doc/app_notes/iq_2ant.md`.

---

## 8. Rebuilding the PHY/MAC (when a prebuilt image is not enough)

Everything above runs on a prebuilt bitstream. To actually **change** the modem or MAC timing you rebuild the FPGA from [openwifi-hw](https://github.com/open-sdr/openwifi-hw):

```bash
git clone https://github.com/open-sdr/openwifi-hw.git
cd openwifi-hw
source ./setup.sh                      # sets Vivado paths / board vars
# generate the project + bitstream for your board (Vivado, pinned version):
#   vivado -source boards/<board>/openwifi.tcl
# then copy the resulting system_top.bit.bin back to the board and re-run ./wgd.sh
```

Validate DSP changes in the MATLAB/Octave reference model under `openwifi-hw` **before** synthesis — timing closure on the FPGA is the slow step. Zynq-7020 boards build under free Vivado **WebPACK**; 7035/7045/UltraScale+ need a paid Vivado edition. This HDL-rebuild loop is the heavier lift that a Nexmon C patch or an ath9k `debugfs` write avoids — the price of owning the PHY.

---

## 9. ⚠️ Safety & regulatory notes — you are running a full transmitter

openwifi is a **real transmitter with the regulatory logic removed**. Unlike a commercial NIC, it does not enforce a regulatory domain, and it does **not implement DFS/radar detection**. You are legally responsible for everything it emits.

- **Prefer cabled RF.** For any TX, injection, radar, or covert-channel experiment, connect the RF ports through **coax + attenuators** into the DUT (or a shielded enclosure) rather than antennas. The openwifi README states plainly that it is *your* duty to follow local spectrum regulation or **use cable** to avoid over-the-air interference.
- **Avoid DFS/radar channels** on air. openwifi has no radar detection; transmitting on radar-required 5 GHz channels can be illegal and disruptive. Prefer non-DFS channels where you are licensed (e.g. 2.4 GHz ch 1/6/11, or U-NII-1 where permitted).
- **The AD9361 tunes 70 MHz–6 GHz.** openwifi can be retuned far outside the ISM bands — doing so over the air without a licence is illegal in most jurisdictions. Keep out-of-ISM experiments on cable/into a load.
- **Injection & fuzzing** (`inject_80211.md`, Owfuzz) emit malformed frames real NICs refuse to send. Only aim them at devices/networks you own, on an isolated link.
- Keep TX power low and never jam or disrupt production Wi-Fi.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| No `sdr0` after `./wgd.sh` | Bitstream not loaded — confirm `system_top.bit.bin` for **your** board is in the BOOT partition (§3). Check `dmesg | grep -i -E "sdr|ad9361|fpga"`. |
| Board unreachable over SSH | You are not on `192.168.10.0/24`. Set your PC to `192.168.10.1/24`; the board is `192.168.10.122`. |
| `dmesg` shows AD9361 SPI/init errors | Wrong board overlay copied, or RF front-end (FMCOMMS/SOM) not seated. Re-copy `BOOT/openwifi/<board_name>/`. |
| CSI display shows nothing | No packets on the monitored channel, or channel mismatch — set `./monitor_ch.sh sdr0 <ch>` to a channel with live a/g/n traffic; confirm `side_ch.ko` is inserted in CSI (not IQ) mode. |
| IQ capture empty | You inserted `side_ch.ko` in CSI mode. Re-insert with `iq_len_init=...`; set trigger with `wh8d...` (use `wh8d0`+`wh5d1` for free-running). |
| Very low throughput | Expected — openwifi tops out ~40–50 Mbps. It is a research radio. |
| Can't act as AP on a 5 GHz DFS channel | Expected — no radar/DFS logic. Use a non-DFS channel. |
| Vivado rejects the build | 7035/7045/UltraScale+ need a **paid** Vivado edition; only 7020-class boards build under free WebPACK. |

---

## 11. Where to go next

- **Concept & capability map:** [../../projects/openwifi.md](../../projects/openwifi.md) — why openwifi is genuinely Tier 5, and the full app-note catalog (radar-self-csi, csi_fuzzer, Owfuzz).
- **How this compares to true SDRs** (USRP, bladeRF, Pluto): [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md) — openwifi essentially *is* an AD9361 SDR plus a complete open Wi-Fi stack on its FPGA.
- **Reverse-engineered CSI, for contrast:** [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md), the [Intel 5300 CSI walkthrough](./intel-5300-csi.md), and the [ath9k spectral/CSI walkthrough](./atheros-ath9k-spectral-csi.md) — the closed-chip roads to a *subset* of what openwifi hands you openly.
- **Tier-4 authorship on a closed chip:** [Nexmon](../../projects/nexmon.md) — how far you can push a sealed Broadcom modem, and exactly where it stops short of Tier 5.

---

## References

1. openwifi — driver/software repo (README, quick start, board list, `wgd.sh`, `setup_once.sh`). https://github.com/open-sdr/openwifi
2. openwifi-hw — FPGA baseband source (per-board `openwifi.tcl`, `setup.sh`, reference models). https://github.com/open-sdr/openwifi-hw
3. Application notes index — https://github.com/open-sdr/openwifi/tree/master/doc/app_notes
4. CSI / side-info app note (`csi.md`) — `side_ch.ko`, `side_ch_ctl`, `side_info_display.py`, side-info format, header filtering. https://github.com/open-sdr/openwifi/blob/master/doc/app_notes/csi.md
5. Raw-IQ app note (`iq.md`) — `iq_len_init`, IQ trigger config, `iq_capture.py`. https://github.com/open-sdr/openwifi/blob/master/doc/app_notes/iq.md
6. Project documentation & `sdrctl` usage (`doc/README.md`). https://github.com/open-sdr/openwifi/blob/master/doc/README.md
7. Jiao, Liu, Mehari, Aslam, Moerman, "openwifi: a free and open-source IEEE 802.11 SDR implementation on SoC," IEEE VTC2020-Spring. https://ieeexplore.ieee.org/document/9128614/
8. openwifi CSI fuzzer / covert channel, ACM WiSec 2021. https://dl.acm.org/doi/10.1145/3448300.3468255
9. Owfuzz (openwifi-based Wi-Fi fuzzing), ACM WiSec 2023 / tool. https://github.com/alipay/Owfuzz
10. Analog Devices AD9361 RF-agile transceiver. https://www.analog.com/en/products/ad9361.html
11. Analog Devices AD-FMCOMMS2/3/4 FMC RF cards (for ZC706/ZedBoard/ZCU102). https://wiki.analog.com/resources/eval/user-guides/ad-fmcomms2-ebz
12. Commercial licensing / subscription. https://openwifi.tech
