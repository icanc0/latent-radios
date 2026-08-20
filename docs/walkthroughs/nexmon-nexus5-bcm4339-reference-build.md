# The Nexus 5 (BCM4339) nexmon reference build, end to end

> The **companion to the Raspberry Pi build** ([`bcm43455c0-raspberry-pi.md`](./bcm43455c0-raspberry-pi.md)). Where the Pi is the *convenient* nexmon platform on hardware you already own, the **LG Nexus 5 (`hammerhead`)** is the *canonical* one: it is the device on which SEEMOO's [Nexmon](https://github.com/seemoo-lab/nexmon) framework was first written, where **Shadow Wi-Fi arbitrary-IQ transmit** was demonstrated, and where a large fraction of the early Broadcom **CSI** work was done. Its Wi-Fi silicon is the Broadcom **BCM4339** (catalog id `broadcom-bcm4339`; see [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md)). If you want to reproduce the load-bearing Broadcom results *as published*, you build them here, on the exact hardware and firmware the authors used.
>
> This guide takes you end to end: source and root a Nexus 5, confirm the `6_37_34_43` firmware, build nexmon's monitor/injection patch **and** `nexmon_csi` for `bcm4339`, flash to the phone over ADB, and run monitor, injection, and CSI capture on Android. It is honest about the fact that this is a **2013, end-of-life phone** and that half the difficulty is now logistics, not radio.

**What this gets you on the SDR ladder** (see [`../taxonomy.md`](../taxonomy.md)): monitor + injection = **rung 1**; `nexmon_csi` per-subcarrier CSI = **rung 2**; and, via the separate Shadow Wi-Fi patch, arbitrary-waveform TX = **rung 4** (covered in its own guide, [`bcm4339-arbitrary-iq-transmit-shadow-wifi.md`](./bcm4339-arbitrary-iq-transmit-shadow-wifi.md), and audited in [`../verification-tier4.md`](../verification-tier4.md)). This document covers the rung-1 and rung-2 reference builds; it points at the rung-4 guide rather than duplicating it.

---

## 1. Why the Nexus 5 is still the reference

The Pi 43455c0 is the platform most people *should* start on. But three things keep the Nexus 5 / BCM4339 the reference device:

- **It is where the work was born.** Nexmon itself, the `nexmon_csi` extractor, and the *Shadow Wi-Fi* (MobiSys 2018) arbitrary-TX / covert-channel demonstrations were all developed and published against the Nexus 5's BCM4339 on stock Android 6. The [`../verification-tier4.md`](../verification-tier4.md) audit traces the entire Tier-4 (arbitrary-waveform) lineage to this device: `int16` I/Q into Template RAM via ioctls 426/427/428, first shown on a rooted Nexus 5.
- **A single, pinned, well-documented firmware.** The BCM4339 in the Nexus 5 ships **exactly one** nexmon-targeted firmware build — `6_37_34_43` on Android 6 Stock — so there is no version-matrix guessing the way there is on evolving Raspberry Pi OS images. Every nexmon and `nexmon_csi` example that names a Nexus 5 assumes this build.
- **It is the four-corner CSI reference.** `nexmon_csi`'s four officially supported chips are `bcm4339` (Nexus 5), `bcm43455c0` (Pi), `bcm4358` (Nexus 6P), and `bcm4366c0` (Asus RT-AC86U). The `bcm4339` path is the oldest and most-cited, so results reproduced on it are directly comparable to the literature.

The trade-off is bluntly stated up front: this is **aging hardware** (§9). If your goal is *new* sensing work rather than reproducing published Broadcom results, the Pi build is the pragmatic choice and this one is the archival/verification choice.

---

## 2. Confirm the target: BCM4339 on firmware 6_37_34_43

Nexmon patches are pinned to a **specific firmware build**; a mismatch either fails to build, fails to load, or is rejected by the driver. For the Nexus 5 the answer is fixed:

| Device | Codename | Wi-Fi chip | Firmware build | OS baseline | nexmon patch dir |
|---|---|---|---|---|---|
| LG Nexus 5 | `hammerhead` | Broadcom **BCM4339** | **`6_37_34_43`** | Android 6 Stock (6.0.1) | `patches/bcm4339/6_37_34_43/nexmon/` |

This table is straight from the nexmon supported-devices list — chip `bcm4339`, firmware `6_37_34_43`, OS "Android 6 Stock," with monitor mode, radiotap headers, frame injection, flash patching, and ucode compression all marked supported.

On the rooted phone, the firmware blob is the ground truth. The Broadcom driver on the Nexus 5 loads its firmware from `/vendor/firmware/fw_bcmdhd.bin` (path can vary by ROM); confirm the version string:

```bash
adb shell su -c 'strings /vendor/firmware/fw_bcmdhd.bin | grep -m1 -i "6.37.34"'
# expect a banner containing 6.37.34.43
```

If your ROM does not expose `strings`, pull the blob and check on the host:

```bash
adb shell su -c 'cat /vendor/firmware/fw_bcmdhd.bin' > fw_bcmdhd.bin
strings fw_bcmdhd.bin | grep -m1 -i '6\.37\.34'
```

The Shadow Wi-Fi arbitrary-TX work additionally pins the *Android image* to build **M4B30Z (Dec 2016, 6.0.1)**; for monitor/injection/CSI the requirement is looser (a rooted Android 6 with the `6_37_34_43` blob), but M4B30Z is the safest choice because it is the exact image the authors used.

---

## 3. Source and root the phone

### 3.1 Sourcing (the honest part)

The Nexus 5 was discontinued in 2015 and lost official updates in 2016. You are buying used hardware. Practical notes:

- **Model matters, storage does not.** Any `hammerhead` (D820 / D821) with a working Wi-Fi radio is fine; 16 GB vs 32 GB is irrelevant for this work.
- **Battery is the first failure.** Ten-year-old Li-ion packs are usually swollen or dead. Budget for a replacement battery (the Nexus 5's is user-accessible with a spudger and Phillips #00) or run the phone on USB power on a bench.
- **Buy two.** At this age, expect one of any two units to have a dead radio, a bad USB port, or a boot loop. A spare is cheaper than the time lost to a marginal unit.
- **Avoid "as-is / no power" listings** unless you specifically want a parts donor.

### 3.2 Unlock the bootloader, install a recovery, root

The standard, well-trodden path is **fastboot unlock → TWRP recovery → Magisk (or SuperSU) for root**. You need `adb`/`fastboot` on the host (`platform-tools`) and a data-capable USB cable.

```bash
# Host: install platform-tools (Debian/Ubuntu)
sudo apt-get install -y android-tools-adb android-tools-fastboot

# On the phone: Settings > About > tap Build number 7x to enable Developer options,
# then Developer options > enable "OEM unlocking" and "USB debugging".

# Reboot to the bootloader and unlock (THIS WIPES THE DEVICE):
adb reboot bootloader
fastboot oem unlock        # confirm on the phone screen

# Flash TWRP recovery for hammerhead (download the hammerhead image from twrp.me):
fastboot flash recovery twrp-hammerhead.img
fastboot boot   twrp-hammerhead.img
```

From TWRP, sideload a root manager. Magisk is the modern choice (its `.apk` can be renamed to `.zip` and flashed, or sideloaded):

```bash
adb sideload Magisk.zip     # in TWRP: Advanced > ADB Sideload
```

Reboot; verify root:

```bash
adb shell su -c 'id'        # expect uid=0(root)
```

> **Flashing a stock factory image.** If your unit is on a random ROM, reflash Google's Nexus 5 factory image for `hammerhead` (the M4B30Z build) with the bundled `flash-all.sh`, *then* re-unlock/root. Reflashing stock is also your recovery path if a firmware experiment bricks Wi-Fi (§10). Keep the factory image archived — Google's hosting for EoL Nexus images has been unreliable, so mirror the exact `hammerhead` M4B30Z zip you used.

Root is required because nexmon's install step writes the patched firmware blob into the read-only `/vendor` (or `/system`) partition and pushes `nexutil` to a system path over ADB.

---

## 4. Host build environment

Do the build **on a Linux host**, not on the phone — nexmon cross-compiles the ARM firmware and Android host utilities on the host and pushes them to the device with ADB.

Reference environment (from the repo READMEs): a Debian/Ubuntu-family host (the Shadow Wi-Fi work names **Xubuntu 16.04**; a modern Ubuntu works for monitor/injection/CSI as long as the i386 multilib and the old NDK are present) plus **Android NDK r11c — the exact version**. Newer NDKs break nexmon's toolchain assumptions.

```bash
# 1. Host dependencies
sudo apt-get update
sudo apt-get install -y git gawk qpdf adb flex bison xxd make automake autoconf

# 2. 32-bit libs — nexmon's bundled ARM toolchain is 32-bit
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install -y libc6:i386 libncurses5:i386 libstdc++6:i386

# 3. Android NDK r11c (the EXACT old version) and NDK_ROOT
#    download android-ndk-r11c-linux-x86_64.zip, unzip, then:
export NDK_ROOT=/opt/android-ndk-r11c     # adjust to your path
```

`NDK_ROOT` must point at the r11c root, and it must be exported in **every shell** you build utilities in. A wrong or newer NDK is the single most common "the utilities won't compile" cause on this platform.

---

## 5. Build the nexmon base

```bash
git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon

# setup_env.sh must be SOURCED, not executed — it exports $NEXMON_ROOT and puts the
# cross-compiler on $PATH for THIS shell. Re-source it in every new terminal.
source setup_env.sh

make                      # builds the toolchain, extracts/preps firmware components
```

`make` at the repo root builds the buildtools, extracts the ucode/flashpatches, and prepares the firmware-modification machinery. If a later step reports the wrong compiler or "command not found," you forgot to `source setup_env.sh` in the current shell.

Build the host/Android utilities (this is what needs `NDK_ROOT`):

```bash
cd utilities
make                      # builds nexutil (and, for CSI, makecsiparams)
cd ..
```

---

## 6. Path A — Monitor mode + frame injection (rung 1)

Do this first: it is the lighter patch and proves your toolchain, ADB path, and root all work before you add CSI.

### 6.1 Build, back up, and install the patched firmware

```bash
cd patches/bcm4339/6_37_34_43/nexmon/

make                      # compile the patched bcm4339 firmware (fw_bcmdhd.bin)
make backup-firmware      # pull & save the phone's ORIGINAL blob over ADB — do this once!
make install-firmware     # push the patched firmware to the rooted, adb-connected Nexus 5
```

- `make backup-firmware` copies the stock blob off the device — **this is your undo button** (§10). Do it before `install-firmware`.
- `make install-firmware` remounts the firmware partition read-write over ADB, writes the patched `fw_bcmdhd.bin`, and (depending on repo version) reloads the driver. If it cannot remount, confirm `adb shell su -c id` returns root and that the ROM allows remounting `/vendor` (some enforce dm-verity — disabling verity in TWRP or using a userdebug image resolves it).

### 6.2 Push nexutil to the phone

`nexutil` is nexmon's firmware control tool — it carries ioctls (monitor state, channel, later the CSI config) into the running firmware. The utilities `make install` step pushes it to a system path on the device:

```bash
cd "$NEXMON_ROOT/utilities"
make install              # pushes nexutil to the phone over ADB (e.g. /system/bin or /data)
adb shell su -c 'nexutil -V'   # should print the patched firmware/version string
```

### 6.3 Enter monitor mode and sniff

Everything from here runs **on the phone**, as root, over `adb shell su -c '...'` (or an on-device terminal). The Nexus 5's interface is typically `wlan0`.

```bash
adb shell su -c 'ifconfig wlan0 up'
adb shell su -c 'nexutil -m2'        # -m2 = monitor + radiotap; -m0 returns to managed
# set a channel (2.4 GHz ch 6, or 5 GHz 36 HT40+):
adb shell su -c 'iw dev wlan0 set channel 6'
# sniff 802.11 frames with radiotap headers:
adb shell su -c 'tcpdump -i wlan0 -e'     # tcpdump must be present on the ROM, or push a static build
```

If your ROM lacks `tcpdump`/`iw`, push static ARM builds to `/data/local/tmp` and call them by absolute path. You should see 802.11 frames with a radiotap header prepended — that is monitor mode working.

### 6.4 Inject a frame

With the patched firmware, standard Linux injection works against `wlan0` in monitor state. The cleanest cross-platform way is to inject **from the phone** and confirm on a **second, independent receiver** (a Pi in monitor mode, a laptop, or an RTL8812AU) on the same channel — never trust "it didn't error" as proof.

A minimal on-device injection using `packETH`/`tcpreplay`-style tools is ROM-dependent; the most portable check is to craft a beacon on the host with Scapy over a *different* NIC and instead use the phone as the **receiver** to prove monitor RX, then reverse roles. If you have Python on the host and a second radio, the beacon recipe in the Pi guide (§5.5 of [`bcm43455c0-raspberry-pi.md`](./bcm43455c0-raspberry-pi.md)) applies unchanged — the phone just plays the transmitter or the sniffer.

> **⚠ Injection is real transmission.** Frame injection keys the PA on shared ISM/U-NII spectrum. Inject only frames you are authorized to send, on channels/power your regulatory domain permits, ideally into a shielded/attenuated bench. Deauth/beacon floods against networks you do not own are illegal in most jurisdictions. The nexmon authors' own words: *use at your own risk and responsibility.* See [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md) and, for the far more dangerous arbitrary-TX patch, [`../verification-tier4.md`](../verification-tier4.md).

---

## 7. Path B — Capture CSI with nexmon_csi (rung 2)

`nexmon_csi` replaces the firmware with a build that, for every received 802.11 frame matching your filter, emits the raw per-subcarrier channel estimate as a **UDP packet looped back to the host stack** (destination port **5500**). You then just `tcpdump` those packets and decode offline. On the Nexus 5 the supported firmware is again `6_37_34_43`.

### 7.1 Build and install the CSI firmware

`nexmon_csi` is cloned **inside** the matching bcm4339 firmware directory of a built nexmon tree:

```bash
# from a built nexmon checkout with setup_env.sh sourced and NDK_ROOT set
cd "$NEXMON_ROOT/patches/bcm4339/6_37_34_43/"
git clone https://github.com/seemoo-lab/nexmon_csi.git
cd nexmon_csi

make install-firmware     # builds AND installs the CSI-enabled bcm4339 firmware over ADB
```

`nexmon_csi` builds its own `makecsiparams` alongside `nexutil`; run its `make install` for the utilities so both land on the phone:

```bash
make install              # pushes nexutil + makecsiparams to the device (per repo)
```

Reboot or reload the driver after installing. `nexmon_csi`'s officially supported chips are exactly `bcm4339`, `bcm43455c0`, `bcm4358`, `bcm4366c0` — the Nexus 5's `bcm4339` is first-class.

### 7.2 Generate the extractor config with makecsiparams

`makecsiparams` encodes *what to capture* (channel, bandwidth, RX cores, spatial streams, optional MAC filter) into a base64 blob you feed to the firmware via `nexutil`. Generate it on the host (or on the phone), then apply it on the phone:

```bash
# Channel 36 @ 80 MHz, 1 core, 1 spatial stream, filter one transmitter's frames
makecsiparams -c 36/80 -C 1 -N 1 -m 00:11:22:33:44:55 -b 0x88
# -> prints a base64 string, e.g.  m+IBEQGIAgAAESIzRFWqu6q7qrsAAA...
```

| Flag | Meaning |
|---|---|
| `-c <chan>/<bw>` | Channel and bandwidth (20/40/80). The BCM4339 tops out at **80 MHz / 802.11ac** — no 160 MHz, no HE/EHT. |
| `-C <bitmask>` | Which RX **cores** (chains) to report |
| `-N <bitmask>` | Which **spatial streams** to report |
| `-m <mac>` | Only extract CSI from frames sent by this source MAC (repeatable) |
| `-b <hex>` | Frame-type filter byte (e.g. `0x88` = QoS data) |

Run `makecsiparams -h` for the full list — regenerate it for your channel, do not paste a magic string from a blog.

### 7.3 Configure the firmware and capture

```bash
# on the phone, as root:
adb shell su -c 'stop wpa_supplicant' 2>/dev/null || \
  adb shell su -c 'pkill wpa_supplicant'      # stop the supplicant retuning the radio
adb shell su -c 'ifconfig wlan0 up'

# apply the base64 params from makecsiparams (ioctl channel = 500):
adb shell su -c 'nexutil -Iwlan0 -s500 -b -l34 -v<YOUR_BASE64>'

# park the chip on-channel via a monitor interface (or nexutil -m2 + iw set channel):
adb shell su -c 'iw dev wlan0 interface add mon0 type monitor'
adb shell su -c 'ifconfig mon0 up'

# CSI arrives as UDP :5500 packets on wlan0 (NOT mon0) — capture to a pcap on the phone,
# then pull it to the host:
adb shell su -c 'tcpdump -i wlan0 dst port 5500 -w /data/local/tmp/csi.pcap'
# ...let traffic flow, Ctrl-C, then:
adb pull /data/local/tmp/csi.pcap ./csi.pcap
```

**CSI is emitted per received frame — there must be traffic on your channel.** If the target is idle, ping it or point `-m` at a busy AP. No frames in, no CSI out.

### 7.4 Decode the pcap

The BCM4339 uses the **float-encoded** CSI format (unlike the 43455c0's plain `int16`), so pick a decoder that knows the `bcm4339` device format:

```python
from nexcsi import decoder

device  = "nexus5"                               # bcm4339 format
samples = decoder(device).read_pcap("csi.pcap")
csi     = decoder(device).unpack(samples["csi"], zero_nulls=True, zero_pilots=True)
# csi -> complex array, shape (n_frames, n_subcarriers)
print(samples["rssi"][:5], samples["mac"][:1], csi.shape)
```

[`nexcsi`](https://github.com/nexmonster/nexcsi) (NumPy) and [`CSIKit`](https://github.com/Gi-z/CSIKit) both handle the nexmon `bcm4339` format; CSIKit adds visualization and cross-vendor (Intel/Atheros/ESP32) parsing. `nexmon_csi` also ships MATLAB reader/plotter scripts under `utils/matlab/` — the bcm4339 path uses the compiled MEX for the float format. For the full "raw UDP → calibrated, phase-sanitized CSI" pipeline (subcarrier layout, null/pilot handling, phase offset removal), follow the shared guide [`nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md) — everything there applies to the Nexus 5 except the per-device format tag (`nexus5`/`bcm4339` instead of `raspberrypi`).

> The uncalibrated-phase, guard/null-bin garbage, and "cores ≠ clean MIMO" caveats from the Pi guide (§7) hold identically here — they are properties of commodity-NIC CSI, not device-specific.

---

## 8. Rung 4 — arbitrary-IQ transmit (pointer, not repeated here)

The Nexus 5's headline result is **Shadow Wi-Fi arbitrary-waveform TX**: writing `int16` I/Q into the ACPHY Template RAM (ioctl **426**), keying playback with a chanspec/gain/loop struct (ioctl **427**), and stopping it (ioctl **428**). That is a *different patch* ([`seemoo-lab/mobisys2018_nexmon_software_defined_radio`](https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio)) applied in the same `patches/bcm4339/6_37_34_43/` directory, and it is the single most dangerous demo in the catalog because its `regulations.c` **NOPs out the regulatory power clamp and unlocks illegal channels**. It has its own full walkthrough — do **not** improvise it from this page:

- Build/run: [`bcm4339-arbitrary-iq-transmit-shadow-wifi.md`](./bcm4339-arbitrary-iq-transmit-shadow-wifi.md)
- Evidence audit / why it stays `reported`, not `verified`: [`../verification-tier4.md`](../verification-tier4.md)
- Safety/legal rules that are non-negotiable before keying the PA: [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md)

The reason this reference build matters is exactly that: the same phone, same firmware, same nexmon base you set up in §5 is the substrate for all three rungs. Get §5–§7 solid and the Tier-4 patch is a directory swap away.

---

## 9. The aging-hardware reality (read before you invest a weekend)

The radio work is solved; the friction is that this is a decade-old consumer phone. Concretely:

| Pain | Why | Mitigation |
|---|---|---|
| **Dead/swollen batteries** | 10-year-old Li-ion | Replace the pack, or run on USB power on a bench (charge-only if the battery is suspect) |
| **Flaky USB / ADB drops** | Worn micro-USB port | Good cable, clean the port; a marginal port makes `make install-firmware` intermittently fail |
| **Vanishing factory images** | Google deprecated Nexus 5 hosting | Archive the exact `hammerhead` M4B30Z factory zip and TWRP image *now*; mirror them |
| **Old NDK required** | nexmon pins **r11c** | Keep `android-ndk-r11c` archived; modern NDKs will not build the utilities |
| **Old host toolchain assumptions** | Shadow Wi-Fi names Xubuntu 16.04 | For monitor/injection/CSI a current Ubuntu + i386 multilib usually works; if the utilities fight you, build in a 16.04 container/VM |
| **dm-verity / RO firmware partition** | Some ROMs block remounting `/vendor` | Disable verity in TWRP, or use a userdebug/M4B30Z image; confirm you can `mount -o rw,remount` the firmware partition |
| **`iw`/`tcpdump` missing on ROM** | Minimal Android userland | Push static ARM builds to `/data/local/tmp` and call by absolute path |
| **Thermal throttling under continuous TX/CSI** | Small phone chassis | Keep captures short; the phone is not a rack instrument |

None of this is a nexmon bug — it is the cost of using the *reference* device. If any of it is a dealbreaker, the Pi 43455c0 build is the same capabilities on current, in-production hardware; use the Nexus 5 when you specifically need to reproduce a published bcm4339 result.

---

## 10. Restore stock firmware

```bash
# If you ran `make backup-firmware`, the original blob was saved next to the patch dir.
# Reinstall it with the unpatched build's install target, or push the saved blob back:
adb shell su -c 'mount -o rw,remount /vendor'      # ROM-dependent path
adb push fw_bcmdhd.bin.orig /vendor/firmware/fw_bcmdhd.bin
adb shell su -c 'chmod 644 /vendor/firmware/fw_bcmdhd.bin'
adb reboot
```

If Wi-Fi is bricked or the partition is inconsistent, the guaranteed recovery is to **reflash the Google factory image** (`hammerhead` M4B30Z, `flash-all.sh`) and re-root. This is why §3.2 tells you to archive that zip.

---

## 11. No invented offsets — where the numbers actually live

Nothing in this guide asserts a Template-RAM size, a magic ioctl payload, or a sample-rate constant pulled from memory. Trace each to source:

- **Supported device / firmware / patch dir** (`bcm4339`, `6_37_34_43`, `patches/bcm4339/6_37_34_43/nexmon/`): the nexmon repo's supported-devices table and directory tree — [github.com/seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon).
- **CSI chip support, `makecsiparams` flags, UDP :5500, per-device decode format**: the `nexmon_csi` README and `utils/` — [github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi).
- **The three arbitrary-TX ioctls (426/427/428) and the 20-byte start struct**: read them out of the Shadow Wi-Fi patch's `src/ioctl.c`; do **not** copy them from a blog. The evidence trail is laid out in [`../verification-tier4.md`](../verification-tier4.md).
- **Template-RAM bound on *your* firmware**: disassemble `wlc_bmac_write_template_ram` in your own dump ([`ghidra-setup-wifi-firmware.md`](./ghidra-setup-wifi-firmware.md)); the `256*1024` constant in the repo's test path is a debug scratch reference, not the sample-play bound.

---

## Cross-references

- Chip family & catalog entry: [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md) (id `broadcom-bcm4339`)
- The framework internals: [`../../projects/nexmon.md`](../../projects/nexmon.md)
- The Pi companion build (same capabilities, current hardware): [`bcm43455c0-raspberry-pi.md`](./bcm43455c0-raspberry-pi.md)
- Raw UDP → usable CSI pipeline (device tag aside, identical): [`nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md)
- The rung-4 arbitrary-TX patch on this same phone: [`bcm4339-arbitrary-iq-transmit-shadow-wifi.md`](./bcm4339-arbitrary-iq-transmit-shadow-wifi.md); Tier-4 audit: [`../verification-tier4.md`](../verification-tier4.md)
- Reversing Broadcom firmware: [`ghidra-setup-wifi-firmware.md`](./ghidra-setup-wifi-firmware.md), [`broadcom-d11-ucode.md`](./broadcom-d11-ucode.md); safety/legal: [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md)

---

## References

1. seemoo-lab/nexmon — firmware-patching framework; supported-devices table (Nexus 5 = `bcm4339`, firmware `6_37_34_43`, Android 6 Stock; monitor/radiotap/injection supported), build steps (`source setup_env.sh`, `make`, `patches/bcm4339/6_37_34_43/nexmon/`, `make backup-firmware`/`install-firmware`), NDK r11c requirement. https://github.com/seemoo-lab/nexmon
2. seemoo-lab/nexmon/README. https://github.com/seemoo-lab/nexmon/blob/master/README.md
3. seemoo-lab/nexmon_csi — CSI extraction; supported chips (`bcm4339`/`bcm43455c0`/`bcm4358`/`bcm4366c0`), Nexus 5 firmware `6_37_34_43`, `makecsiparams`, UDP :5500 capture, MATLAB utils. https://github.com/seemoo-lab/nexmon_csi
4. Schulz, Link, Gringoli, Hollick — *Shadow Wi-Fi: Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi*, ACM MobiSys 2018. DOI: https://doi.org/10.1145/3210240.3210333
5. seemoo-lab/mobisys2018_nexmon_software_defined_radio — arbitrary-IQ TX patch (ioctls 426/427/428) applied under `patches/bcm4339/6_37_34_43/`. https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio
6. Gringoli, Schulz, Link, Hollick — *Free Your CSI: A Channel State Information Extraction Platform For Modern Wi-Fi Chipsets*, WiNTECH 2019. DOI: https://doi.org/10.1145/3349623.3355477
7. nexmonster/nexcsi — Python/NumPy CSI decoder (per-device formats incl. `nexus5`/bcm4339). https://github.com/nexmonster/nexcsi
8. Gi-z/CSIKit — multi-vendor CSI parsing/visualization. https://github.com/Gi-z/CSIKit
9. TWRP for `hammerhead` (Nexus 5) recovery images. https://twrp.me/lg/lgnexus5.html
10. Matthias Schulz — *Teaching Your Wireless Card New Tricks: Smartphone Performance and Security Enhancements through Wi-Fi Firmware Modifications*, PhD thesis, TU Darmstadt, 2018.
