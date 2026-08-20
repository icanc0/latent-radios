# Nexmon on a Raspberry Pi (BCM43455c0): monitor, injection, and CSI, step by step

This is the most accessible "Wi-Fi-as-an-instrument" project on hardware most people already own. The 3B+/4/CM4-class Raspberry Pi carries an Infineon/Cypress **CYW43455 (silicon revision `c0`)** Wi-Fi/Bluetooth combo chip. With the [Nexmon](https://github.com/seemoo-lab/nexmon) firmware-patching framework you can flash a modified firmware that adds **monitor mode**, **frame injection**, and — via [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) — **per-subcarrier Channel State Information (CSI)** export. That puts a commodity Pi on rung **2 of the SDR ladder** (CSI = complex per-subcarrier channel estimates), with monitor/injection at rung 1 as a byproduct. See [`../taxonomy.md`](../taxonomy.md) for the ladder and [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md) for the chip family overview.

> **What this is not.** This is *receiver-side PHY telemetry*, not a general-purpose SDR. You cannot synthesize arbitrary I/Q, and you only see CSI for 802.11 frames the chip actually decodes on your configured channel. It is rung 2, not rung 4/5. For the honest boundary, read [`../true-sdr-comparison.md`](../true-sdr-comparison.md).

---

## 1. Which Pis carry the BCM43455c0

| Board | Wi-Fi silicon | nexmon_csi target dir | Notes |
|---|---|---|---|
| Raspberry Pi 3B+ | CYW43455 (c0) | `patches/bcm43455c0/…` | Original CSI reference board |
| Raspberry Pi 4B (all RAM variants) | CYW43455 (c0) | `patches/bcm43455c0/…` | Most common target today |
| Raspberry Pi 400 | BCM43456 (variant) | — | *Closely related but a different part number*; the stock `bcm43455c0` patch may not match. Verify your `-sdio.bin` filename before assuming. |
| Compute Module 4 (CM4) | CYW43455 (c0) | `patches/bcm43455c0/…` | Same radio as Pi 4 |
| Raspberry Pi 5 | CYW43455 (c0) | `patches/bcm43455c0/…` | Same radio, new DDR50 SDIO bus; needs the newer `Makefile.rpi` flow (see §9) |
| Pi 3B / Zero W / Zero 2 W | BCM43430/43436 | `patches/bcm43430a1/…` | **Not** a 43455 — different patch tree, this guide does not apply verbatim |

**Confirm your chip before doing anything.** The firmware blob name is the ground truth:

```bash
ls -l /lib/firmware/brcm/brcmfmac43455-sdio.bin      # <- 43455 present = you're on target
dmesg | grep -i brcmfmac                              # driver + firmware version banner
```

If you see `brcmfmac43430` or `brcmfmac43436`, you are on a Zero/3B-class radio and need a different patch directory — stop here.

---

## 2. Firmware versions matter (read this first)

Nexmon patches are written against a **specific firmware build**. If the patch tree and your installed blob disagree, the patched firmware will either fail to build, fail to load, or the driver will reject it. Known builds shipped for the 43455c0:

| Firmware version | Where it shipped | Patch dir under `patches/bcm43455c0/` |
|---|---|---|
| `7.45.154` | Older Raspbian | `7_45_154/` |
| `7.45.189` | Cypress release; **nexmon_csi target** | `7_45_189/` |
| `7.45.206` | Newer Raspberry Pi OS | (handled by the `Makefile.rpi` flow, §9) |

Rule of thumb: **monitor + injection** patches live under `7_45_154/` and `7_45_189/`; **nexmon_csi** targets `7_45_189/`. The cleanest path on a classic (kernel ≤ 5.10) image is to let Nexmon install the matching blob rather than fighting whatever your OS shipped.

Check what you currently run:

```bash
strings /lib/firmware/brcm/brcmfmac43455-sdio.bin | grep -m1 -i '7\.45'
```

---

## 3. Prerequisites

- A Raspberry Pi 3B+/4/CM4 with the BCM43455c0 (see §1).
- Raspberry Pi OS with **matching kernel headers installed**. Nexmon builds a kernel module (the patched `brcmfmac`), so headers **must** match your running kernel (`uname -r`).
- ~1–2 GB free, and time (the toolchain build is slow on a Pi).
- Do the build **on the Pi itself** — the toolchain cross-compiles the ARM firmware but the driver module must match the running kernel.

Install dependencies (this list is from the upstream READMEs):

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y raspberrypi-kernel-headers git libgmp3-dev gawk qpdf \
                    bison flex make xxd automake autoconf libtool texinfo
sudo reboot
```

> On a 64-bit OS you will also need `armhf` cross libraries, because the Broadcom toolchain and firmware tools are 32-bit. This is the single most common "it won't even build" cause on Pi 4/5 64-bit — see §9.

---

## 4. Set up the build environment

```bash
git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon
```

On **32-bit** Raspbian, the prebuilt toolchain needs two legacy shared libs. Build them from the bundled sources only if the symlinks are missing:

```bash
# libisl.so.10
cd buildtools/isl-0.10 && ./configure && make && sudo make install
sudo ln -sf /usr/local/lib/libisl.so /usr/lib/arm-linux-gnueabihf/libisl.so.10
cd ../..

# libmpfr.so.4
cd buildtools/mpfr-3.1.4 && autoreconf -f -i && ./configure && make && sudo make install
sudo ln -sf /usr/local/lib/libmpfr.so /usr/lib/arm-linux-gnueabihf/libmpfr.so.4
cd ../..
```

Now source the environment and build the toolchain + extraction utilities. **`setup_env.sh` must be `source`d, not executed** — it exports `$NEXMON_ROOT` and puts the cross-compiler on `$PATH` for the current shell:

```bash
source setup_env.sh
make            # builds the toolchain, libnexio, nexutil, etc. (slow, first time)
```

If a later step reports "command not found: gcc-…-arm" or the wrong compiler, you forgot to `source setup_env.sh` in *this* shell. Re-source it every new terminal.

---

## 5. Path A — Monitor mode + frame injection

This is the lighter patch; do this first to prove your toolchain works before adding CSI.

### 5.1 Build and install the patched firmware

Pick the directory matching your firmware version (§2):

```bash
cd patches/bcm43455c0/7_45_189/nexmon/      # or 7_45_154/nexmon/
make                    # produce the patched brcmfmac43455-sdio.bin
make backup-firmware    # saves the current /lib/firmware/brcm blob (do this once!)
sudo make install-firmware
```

`make install-firmware` copies the patched blob to `/lib/firmware/brcm/brcmfmac43455-sdio.bin`. `backup-firmware` is your undo button — keep it.

### 5.2 Build and install the patched brcmfmac driver

Stock `brcmfmac` tears down anything that looks like monitor mode and rejects the "unofficial" firmware. Nexmon ships a patched driver that relaxes those checks. The exact sub-path depends on your kernel version — look under your patch dir and/or `patches/driver/`:

```bash
ls patches/driver/                 # e.g. brcmfmac_5.10.y-nexmon/
# build the one matching `uname -r` per that dir's Makefile, producing brcmfmac.ko
```

Then swap it in (find the live module path with `modinfo`):

```bash
DRV=$(dirname "$(modinfo -n brcmfmac)")
sudo cp "$DRV/brcmfmac.ko" "$DRV/brcmfmac.ko.orig"     # backup
sudo cp brcmfmac.ko "$DRV/brcmfmac.ko"                 # your built module
sudo depmod -a
sudo modprobe -r brcmfmac && sudo modprobe brcmfmac    # or reboot
```

### 5.3 Install nexutil (the firmware control tool)

```bash
cd "$NEXMON_ROOT/utilities/nexutil"
make && sudo make install
```

### 5.4 Enter monitor mode

Two supported ways — either put the firmware into monitor state, or create a dedicated monitor netdev:

```bash
# (a) firmware monitor state with radiotap headers
sudo ifconfig wlan0 up
sudo nexutil -m2                 # -m2 = monitor+radiotap; -m0 returns to managed
sudo tcpdump -i wlan0 -e         # you should see 802.11 frames with a radiotap header

# (b) or a separate mon0 interface
sudo iw phy "$(iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}')" \
        interface add mon0 type monitor
sudo ifconfig mon0 up
sudo tcpdump -i mon0 -e
```

Set the channel with `iw dev wlan0 set channel 6` (or `... 36 HT40+` for 5 GHz).

### 5.5 Inject a frame

With the patched firmware/driver, standard Linux injection tools work against the monitor interface. Quick sanity check with `aireplay-ng`, or a controlled single frame with Scapy:

```bash
# aircrack-ng suite
sudo aireplay-ng --test mon0

# or a single crafted beacon via Scapy (Python 3)
sudo python3 - <<'PY'
from scapy.all import RadioTap, Dot11, Dot11Beacon, Dot11Elt, sendp
f = (RadioTap()/
     Dot11(type=0, subtype=8, addr1="ff:ff:ff:ff:ff:ff",
           addr2="02:11:22:33:44:55", addr3="02:11:22:33:44:55")/
     Dot11Beacon()/Dot11Elt(ID="SSID", info="nexmon-test"))
sendp(f, iface="mon0", count=5, inter=0.1)
PY
```

Confirm injection with a **second** receiver (another Pi, a laptop in monitor mode, or an RTL8812AU — see [`../../chips/realtek.md`](../../chips/realtek.md)) sniffing the same channel; do not trust "it didn't error" as proof the frame went out.

> **⚠ TX is regulated.** Frame injection is real radio transmission on shared ISM/U-NII bands. Inject only frames you are authorized to send, on channels/power your regulatory domain (`iw reg get`) permits, ideally into a shielded/attenuated setup. Beacon/deauth floods against networks you don't own are illegal in most jurisdictions. Upstream's own words: *"our tools … you use at your own risk and responsibility."* See [`../verification-tier4.md`](../verification-tier4.md) for safe-bench practice.

---

## 6. Path B — Capture CSI with nexmon_csi

nexmon_csi replaces the firmware with a build that, for every received 802.11 frame matching your filter, emits the raw channel estimate as a **UDP packet looped back to the host**. You then just `tcpdump` those packets and decode them offline.

### 6.1 Build and install the CSI firmware

From a clean `nexmon` checkout with `setup_env.sh` sourced:

```bash
cd "$NEXMON_ROOT/patches/bcm43455c0/7_45_189"
git clone https://github.com/seemoo-lab/nexmon_csi.git
cd nexmon_csi
make install-firmware        # builds AND installs the CSI-enabled brcmfmac43455-sdio.bin
```

Install the matching patched `brcmfmac` driver and `nexutil` exactly as in §5.2–5.3 (nexmon_csi carries its own driver patches; build the one matching your kernel). Reboot after installing.

> nexmon_csi's official chip support: **bcm4339, bcm43455c0, bcm4358, bcm4366c0**. The Pi's 43455c0 is fully supported.

### 6.2 Generate the extractor configuration with `makecsiparams`

`makecsiparams` encodes *what to capture* (channel, bandwidth, which cores/streams, optional MAC filter) into a base64 blob that you feed to the firmware via `nexutil`. It is built by `make` and installed alongside nexutil.

```bash
# Channel 157 @ 80 MHz, 1 core, 1 spatial stream, filter one transmitter
makecsiparams -c 157/80 -C 1 -N 1 \
  -m 00:11:22:33:44:55 -b 0x88
# -> prints e.g.  m+IBEQGIAgAAESIzRFWqu6q7qrsAAAAAAAAAAAAAAAAAAA==
```

| Flag | Meaning |
|---|---|
| `-c <chan>/<bw>` | Channel and bandwidth (20/40/80). E.g. `36/80`, `6/20`, `157/80` |
| `-C <bitmask>` | Which **RX cores** (antennas/chains) to report |
| `-N <bitmask>` | Which **spatial streams** to report |
| `-m <mac>` | Only extract CSI from frames sent by this source MAC (repeatable) |
| `-b <hex>` | Frame-type filter byte (e.g. `0x88` = QoS data) |

Run `makecsiparams -h` for the full list — do not memorize a magic string; regenerate it for your channel.

### 6.3 Configure the firmware and start capturing

```bash
sudo pkill wpa_supplicant                  # stop the supplicant from retuning the radio
sudo ifconfig wlan0 up
sudo nexutil -Iwlan0 -s500 -b -l34 -v<YOUR_BASE64_FROM_makecsiparams>

# create a monitor interface so the chip stays parked on your channel
sudo iw phy "$(iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}')" \
        interface add mon0 type monitor
sudo ifconfig mon0 up

# CSI arrives as UDP :5500 packets on wlan0 (NOT mon0) — capture to a pcap
sudo tcpdump -i wlan0 dst port 5500 -w csi.pcap
```

**CSI is emitted per received frame — so there must be traffic on your channel.** If the target is idle, ping it, or point `-m` at a busy AP. No frames in, no CSI out.

The loopback UDP packets are sourced from `10.10.10.10 → 255.255.255.255:5500` and begin with magic bytes `0x11111111 0x1111`, then source MAC, sequence number, a core/stream id byte (low 3 bits = core, next 3 bits = spatial stream), chanspec, chip id, then the CSI payload.

### 6.4 Decode the pcap

**Python (recommended):** [`nexcsi`](https://github.com/nexmonster/nexcsi) is a fast NumPy decoder.

```bash
pip install nexcsi
```
```python
from nexcsi import decoder

device  = "raspberrypi"                       # 43455c0 format
samples = decoder(device).read_pcap("csi.pcap")
csi     = decoder(device).unpack(samples["csi"],
                                 zero_nulls=True, zero_pilots=True)
# csi -> complex64 array, shape (n_frames, n_subcarriers)
print(samples["rssi"][:5], samples["mac"][:1])
print(csi.shape)
```

[`CSIKit`](https://github.com/Gi-z/CSIKit) also parses the nexmon format and adds visualization/normalization, and interoperates with Intel/Atheros/ESP32 CSI — handy if you compare devices ([`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md)).

**MATLAB:** upstream ships reader/plotter scripts and an example pcap under `utils/matlab/` in the nexmon_csi repo (one format path uses a compiled MEX for the float-encoded chips; the 43455c0 uses the plain int16 path).

---

## 7. What the CSI output actually is

For each captured frame you get one **complex value per OFDM subcarrier, per reported RX core**. On the 43455c0 the encoding is **interleaved `int16` real + `int16` imaginary** (4 bytes/subcarrier). CSI is the estimated channel `H` per subcarrier: amplitude = `abs(H)`, phase = `angle(H)`.

Subcarrier count is fixed by bandwidth (this is `bandwidth_MHz × 3.2`, i.e. the full FFT including guard/DC/null bins):

| Bandwidth | Subcarriers returned | Usable data bins (rest are guard/null/pilot) |
|---|---|---|
| 20 MHz | 64 | ~52 |
| 40 MHz | 128 | ~108 |
| 80 MHz | 256 | ~234 |

Important caveats:
- **Guard/DC/null bins contain arbitrary garbage** — zero or drop them (`zero_nulls=True` in nexcsi) before analysis or your amplitude/phase plots will have spikes.
- **Cores vs spatial streams.** `-C`/`-N` are bitmasks selecting which RX chains and streams the firmware reports; the per-packet id byte tells you which core/stream each record belongs to (low 3 bits core, next 3 bits stream). The 43455c0 on a Pi is effectively a modest MIMO front end — don't expect a full 4×4 of clean, calibrated chains.
- **Phase is uncalibrated.** There is per-packet CFO/STO and random phase offset. Sensing pipelines apply phase sanitization (linear-fit removal, conjugate-multiplication across antennas). This is a property of *all* commodity-NIC CSI, not a Nexmon bug — see [`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md) and [`../techniques.md`](../techniques.md).
- **Bandwidth ceiling.** The 43455c0 tops out at **80 MHz / 802.11ac**; there is no 160 MHz and no HE/EHT CSI here. For wider/newer captures you need different silicon — see [`../wifi7-and-6ghz.md`](../wifi7-and-6ghz.md) and the Intel AX210 path in [`../../walkthroughs`](.) / [`../../chips/intel.md`](../../chips/intel.md).

---

## 8. Known pitfalls & troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make` fails immediately with compiler/lib errors | `setup_env.sh` not sourced, or missing `libisl.so.10`/`libmpfr.so.4` (32-bit), or missing `armhf` libs (64-bit) | Re-`source setup_env.sh`; build the two legacy libs (§4); add armhf multiarch (§9) |
| Firmware won't load / `dmesg` shows a firmware CRC or version error | Patch tree version ≠ installed blob version | Match `patches/bcm43455c0/<ver>` to your `-sdio.bin` (§2); use `backup-firmware`/`install-firmware`, not manual copies |
| Monitor mode silently **drops** or the interface flaps back to managed | Stock (unpatched) `brcmfmac`, or `wpa_supplicant`/NetworkManager retuning the radio | Install the patched `brcmfmac.ko` (§5.2); `sudo pkill wpa_supplicant`; `sudo rfkill unblock wifi` |
| `makecsiparams: command not found` | nexutil/utilities not built, or not on PATH | `cd utilities/nexutil && make && sudo make install`; re-source env (nexmon_csi issue #241) |
| `tcpdump` on port 5500 shows nothing | Watching `mon0` instead of `wlan0`, no traffic on channel, or `nexutil -v…` not applied | Capture on **wlan0**; generate traffic (ping the target); re-run the `nexutil -I… -v…` config |
| Driver won't build on a new kernel / signature complaints | Kernel too new for the shipped driver patch; some distros enforce **module signing / firmware integrity checks** the patched blob doesn't satisfy | Use the newer **`Makefile.rpi`** flow (§9) which avoids modifying `brcmfmac`, or the Kali packaged route (§9) |
| Everything worked, then an `apt full-upgrade` broke it | Kernel/firmware bumped underneath you; stock blob restored; DKMS not rebuilt | Pin kernel, or reinstall the patched firmware/driver for the new version; on DKMS setups let it rebuild |

**The two structural gotchas worth internalizing:**

1. **Kernel ↔ firmware ↔ driver-patch must all agree.** Nexmon is version-pinned by design. An OS update that bumps any of the three can silently revert you to stock. This is the single biggest source of "it stopped working."
2. **Integrity/signing on newer stacks.** Modern Raspberry Pi OS / kernel builds are stricter about the driver–firmware pair (module signing, and the driver validating the firmware image it loads). Rather than defeat those checks by hand, the community moved to flows that **don't patch `brcmfmac` at all** (§9).

---

## 9. Newer kernels, Pi 5, and the packaged shortcuts

Two modern routes avoid most of §8's pain:

- **`Makefile.rpi` (nexmon_csi, Raspberry Pi 5 & recent Raspberry Pi OS / kernel 6.x).** Discussed in [nexmon_csi discussion #395](https://github.com/seemoo-lab/nexmon_csi/discussions/395). Key points: it **no longer requires a modified `brcmfmac`**, so it's kernel-version-flexible; it installs the patched firmware via `update-alternatives` so you can flip between Nexmon-CSI and stock firmware without recompiling a driver; on Pi 5 you may need the non-16K-page kernel (`kernel=kernel8.img` in `config.txt`); the 32-bit bcm43 toolchain needs Python 2.7 and `armhf` libraries even on 64-bit images; and `nexutil` must be built with `USE_VENDOR_CMD=1` or its IOCTLs are rejected on new kernels.

- **Kali Linux packaged Nexmon (2025.1+, kernel 6.12).** Two apt packages do it all: `brcmfmac-nexmon-dkms` (DKMS driver that auto-rebuilds on kernel updates) and `firmware-nexmon` (patched blobs). Install and reboot:

  ```bash
  sudo apt update && sudo apt full-upgrade -y
  sudo apt install -y brcmfmac-nexmon-dkms firmware-nexmon
  sudo reboot
  ```

  This enables on-board monitor mode + injection on supported Pis (Zero W, 3B, 3B+, 4, 5) with no from-source build. See the [Kali Wi-Fi glow-up post](https://www.kali.org/blog/raspberry-pi-wi-fi-glow-up/). Note it packages the **monitor/injection** side; for CSI you still use nexmon_csi's firmware.

If your goal is CSI research on a Pi 5 or a fresh Bookworm/Trixie image, start at discussion #395's `Makefile.rpi` rather than the classic §4–§6 flow.

---

## 10. Restoring stock firmware

```bash
# if you ran `make backup-firmware`, the original blob is saved alongside the patch dir;
# reinstall it or reinstall the distro firmware package:
sudo apt install --reinstall firmware-brcm80211
sudo cp "$DRV/brcmfmac.ko.orig" "$DRV/brcmfmac.ko"   # restore stock driver
sudo depmod -a && sudo reboot
```

---

## Cross-references

- Chip family & catalog entry: [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md) (id `broadcom-bcm43455c0`)
- The framework internals: [`../../projects/nexmon.md`](../../projects/nexmon.md)
- Reversing Broadcom firmware in Ghidra: [`ghidra-setup-wifi-firmware.md`](ghidra-setup-wifi-firmware.md) and the D11 microcode deep-dive [`broadcom-d11-ucode.md`](broadcom-d11-ucode.md)
- CSI toolchains & cross-vendor decoding: [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md), [`../../projects/picoscenes.md`](../../projects/picoscenes.md)
- Where a real SDR beats this: [`../true-sdr-comparison.md`](../true-sdr-comparison.md); tier-4 safety bench: [`../verification-tier4.md`](../verification-tier4.md)

---

## References

1. seemoo-lab/nexmon — firmware patching framework. https://github.com/seemoo-lab/nexmon
2. seemoo-lab/nexmon/README (build steps, `nexutil -m2`, driver install, legal warning). https://github.com/seemoo-lab/nexmon/blob/master/README.md
3. seemoo-lab/nexmon_csi — CSI extraction (supported chips, `makecsiparams`, capture on wlan0:5500, subcarrier counts, int16 format). https://github.com/seemoo-lab/nexmon_csi
4. seemoo-lab/nexmon_csi/README. https://github.com/seemoo-lab/nexmon_csi/blob/master/README.md
5. nexmon_csi Discussion #395 — Pi 5 & recent kernels, `Makefile.rpi`, no modified brcmfmac, `USE_VENDOR_CMD=1`, `update-alternatives`. https://github.com/seemoo-lab/nexmon_csi/discussions/395
6. nexmon_csi Issue #241 — `makecsiparams: command not found`. https://github.com/seemoo-lab/nexmon_csi/issues/241
7. nexmonster/nexcsi — Python/NumPy decoder (`device="raspberrypi"`, `unpack`, `zero_nulls`). https://github.com/nexmonster/nexcsi
8. Gi-z/CSIKit — multi-vendor CSI parsing/visualization. https://github.com/Gi-z/CSIKit
9. Kali Linux — "The Raspberry Pi's Wi-Fi Glow-Up" (`brcmfmac-nexmon-dkms`, `firmware-nexmon`, kernel 6.12). https://www.kali.org/blog/raspberry-pi-wi-fi-glow-up/
10. Raspberry Pi forums — CYW43455 across 3B+/4/CM4/5. https://forums.raspberrypi.com/viewtopic.php?t=291824
