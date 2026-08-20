# Building and Flashing Open AR9271 Firmware

> **Why this walkthrough is special.** Almost every entry in *Latent Radios* describes a chip whose firmware is a signed, closed binary you have to *reverse* to bend toward SDR-like behavior (see [../firmware-reversing.md](../firmware-reversing.md)). The Atheros **AR9271** is the rare exception: Qualcomm Atheros released the **complete, buildable source** of the firmware that runs inside the chip, as [`qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware). This is, to date, the **only open-source Wi-Fi firmware for a shipping, mass-market USB Wi-Fi chip**. You do not patch a blob here — you `git clone`, compile a `.fw` from C source, drop it into `/lib/firmware`, and reload the driver. If you have ever wanted to *own the whole radio stack* of a real 802.11n NIC, this is the on-ramp.
>
> This complements the reverse-engineering path documented for closed chips. Compare with the parent chip page: [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md).

---

## 1. What the AR9271 actually is

The **AR9271** is a single-chip **USB 2.0 → 802.11n (2.4 GHz, 1×1, 20/40 MHz)** SoC. On-chip it integrates RAM, ROM, the 802.11 MAC/baseband/radio, a USB controller, and — the part that matters here — an embedded **Tensilica Xtensa** microprocessor that runs the "HTC" (Host-Target Communication) firmware. The Linux host driver `ath9k_htc` streams commands and 802.11 frames over USB to that firmware; the firmware drives the MAC and PHY.

Its sibling, the **AR7010**, is a USB↔PCIe bridge SoC that runs the *same* firmware source and pairs with an external PCIe radio (typically AR9280/AR9287, i.e. 2.4/5 GHz dual-band). Both are built from the one repository.

Because the firmware source is open, you can modify **MAC-layer timing, retransmission policy, rate control hand-off, aggregation, LED behavior, and monitor/injection handling** and observe the result on real hardware — the kind of low-level control that, on closed chips, requires the Nexmon-style patching described in [../../projects/nexmon.md](../../projects/nexmon.md).

> **Honest scope / SDR tier.** Open firmware does **not** turn the AR9271 into a general-purpose SDR. You still work above the hardware MAC/PHY: you control framing, timing, and packet-level behavior, not raw I/Q at the ADC/DAC. In the [taxonomy ladder](../taxonomy.md), a stock AR9271 sits around **Tier 1** (monitor + injection are first-class and well supported by `ath9k_htc`). The open firmware's value is not a higher tier "for free" — it is that *every rung above Tier 1 is now reachable by editing C you can read*, rather than by defeating a signature. Treat any PHY-level ambition as a research project you now have the source to attempt, not a shipped capability.

---

## 2. Target hardware (buy the *right* revision)

| Device | Chip | Notes |
|---|---|---|
| **TP-Link TL-WN722N v1** | AR9271 | The classic. **Only hardware revision 1 uses the AR9271.** v2/v3 switched to a Realtek RTL8188EUS — *not* this firmware, no open source. Check the label: `Ver 1.x`. |
| **Alfa AWUS036NHA** | AR9271 | Long-range 2.4 GHz, excellent RP-SMA antenna, widely used for monitor/injection. Consistently AR9271. |
| Alfa AWUS036NHR / various "AR9271" dongles | AR9271 | Many generic AR9271 sticks exist; verify with `lsusb`. |
| Devices around AR7010 (e.g. some dual-band n adapters) | AR7010 + AR928x | Build `htc_7010.fw` from the same tree. |

Verify the chip after plugging in:

```bash
lsusb | grep -i atheros
# Typical AR9271: 0cf3:9271 Atheros Communications, Inc. AR9271 802.11n
dmesg | grep -i ath9k_htc
# ... usb 1-1: ath9k_htc: Firmware ath9k_htc/htc_9271-1.4.0.fw requested
# ... ath9k_htc: FW Version: 1.4
```

The `0cf3:9271` USB VID:PID is the tell for a genuine AR9271. If you instead see a Realtek ID (e.g. `0bda:...`), you have a later TL-WN722N revision — see [../../chips/realtek.md](../../chips/realtek.md) and the [RTL8812AU walkthrough](rtl8812au-monitor-injection.md) instead.

---

## 3. Where the driver loads the firmware

The in-kernel `ath9k_htc` driver requests a **versioned** firmware filename via the standard Linux firmware loader. On current kernels that is:

```
/lib/firmware/ath9k_htc/htc_9271-1.4.0.fw     # AR9271
/lib/firmware/ath9k_htc/htc_7010-1.4.0.fw     # AR7010
```

The version string (`1.4.0`) is compiled into the driver (`FIRMWARE_AR9271` / `MAJOR_VERSION_REQ` / `MINOR_VERSION_REQ` in `drivers/net/wireless/ath/ath9k/hif_usb.c`) so the driver and firmware ABI stay in lockstep. The stock file ships from [`linux-firmware`](https://gitlab.com/kernel-firmware/linux-firmware) (directory `ath9k_htc/`). Historically the names were unversioned (`htc_9271.fw`) and then `htc_9271-1.3.0.fw`; **1.4.0** is the current requested version on modern kernels — always confirm what *your* kernel asks for:

```bash
dmesg | grep -oE 'ath9k_htc/htc_9271-[0-9.]+\.fw'
# -> ath9k_htc/htc_9271-1.4.0.fw   (use exactly this filename)
```

Whatever filename `dmesg` prints is the filename your build must masquerade as. The open-firmware build emits an *unversioned* `htc_9271.fw`; you rename it to match.

---

## 4. Build the firmware

The build has two stages: (1) build a cross-toolchain that targets the chip's **Tensilica Xtensa** core, then (2) compile the firmware against it.

> A note on the toolchain target: the on-chip processor is a **Tensilica Xtensa** core (the repo bundles Tensilica `xtos`/xtensa runtime under MIT license), so `make toolchain` builds an **`xtensa-elf`** GCC/binutils/newlib cross-compiler — *not* a host-native or MIPS/ARM one. You are cross-compiling C for the little processor inside the Wi-Fi chip.

### 4.1 Prerequisites

Debian/Ubuntu host:

```bash
sudo apt update
sudo apt install -y build-essential cmake wget git bison flex \
                    texinfo gawk libncurses-dev
```

- `cmake` is required (the project's own note lists it explicitly).
- On FreeBSD, use `gmake` in place of `make` and install `wget`.

### 4.2 Clone

```bash
git clone https://github.com/qca/open-ath9k-htc-firmware.git
cd open-ath9k-htc-firmware
```

### 4.3 Build the Xtensa cross-toolchain

`make toolchain` downloads and verifies the GNU sources (binutils, GMP, MPFR, MPC, GCC, newlib), then builds them under `./toolchain/` — dependency-ordered GMP → MPFR → MPC → GCC, with binutils built alongside. It installs into `./toolchain/inst`.

```bash
make toolchain        # FreeBSD: gmake toolchain
```

Directory layout it creates:

```
toolchain/dl      # downloaded + checksum-verified source tarballs
toolchain/build   # intermediate build trees
toolchain/inst    # installed xtensa-elf-gcc, -as, -ld, newlib, ...
```

This step is the slow one (compiling a GCC). It only has to be done once; the firmware itself rebuilds in seconds afterward.

### 4.4 Build the firmware images

```bash
make -C target_firmware      # FreeBSD: gmake -C target_firmware
```

This produces the two RAM firmware images **in `target_firmware/`**:

```
target_firmware/htc_9271.fw     # AR9271
target_firmware/htc_7010.fw     # AR7010
```

(`make all` from the repo root does toolchain + firmware in one shot; `make clean` rebuilds only the firmware; `make toolchain-clean` wipes the toolchain.)

### 4.5 Optional: Docker / reproducible builds

The repository itself has **no official `Dockerfile`** — the canonical path is the native `make toolchain` above, and its CI (`.travis.yml`) exercises exactly that. If you want isolation, wrap the two commands in a throwaway container so the heavyweight toolchain build cannot pollute your host:

```dockerfile
# ad-hoc, unofficial — pins the whole build inside one container
FROM debian:bookworm
RUN apt-get update && apt-get install -y \
    build-essential cmake wget git bison flex texinfo gawk libncurses-dev
WORKDIR /src
RUN git clone https://github.com/qca/open-ath9k-htc-firmware.git .
RUN make toolchain && make -C target_firmware
# copy the .fw out with:  docker cp <container>:/src/target_firmware/htc_9271.fw .
```

```bash
docker build -t oath9k .
docker create --name oath9k-out oath9k
docker cp oath9k-out:/src/target_firmware/htc_9271.fw ./htc_9271.fw
docker rm oath9k-out
```

Because `make toolchain` verifies source checksums before building, the container build is deterministic enough to hand the exact same `.fw` to teammates.

---

## 5. Flash / swap in your build

"Flashing" here is a misnomer in the nice way: the AR9271 firmware lives in **RAM**, downloaded fresh over USB on every driver bind. There is nothing to brick — a bad firmware just fails to load, and restoring the stock file + replug recovers you completely. This is the safest place in the entire catalog to experiment with radio firmware.

### 5.1 Back up the stock firmware

```bash
sudo cp /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw \
        /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw.orig
```

### 5.2 Install your build under the versioned name the driver expects

```bash
# Rename the unversioned build output to the exact name dmesg requested
sudo install -m0644 target_firmware/htc_9271.fw \
        /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw
```

### 5.3 Reload

```bash
sudo modprobe -r ath9k_htc      # unbind + unload
sudo modprobe ath9k_htc         # reload -> re-downloads firmware to the chip
dmesg | tail -n 20              # confirm "FW Version: 1.4" and no errors
```

Or simply **unplug and replug** the dongle — the firmware is re-fetched from `/lib/firmware` on every enumeration.

### 5.4 Recover

```bash
sudo cp /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw.orig \
        /lib/firmware/ath9k_htc/htc_9271-1.4.0.fw
sudo modprobe -r ath9k_htc && sudo modprobe ath9k_htc
```

---

## 6. What you can actually experiment with

Because the whole target runs source you can read and rebuild, the interesting knobs are in `target_firmware/` (MAC/HTC layer) and `sboot/` (secondary boot). Grounded, real things people modify:

- **Monitor-mode behavior.** `ath9k_htc` already exposes clean monitor + injection at the driver level (`iw dev wlan0 interface add mon0 type monitor`), which is why AR9271 is a default recommendation for Kismet/aircrack workflows. In the firmware you can change *which* frames the target forwards up and how promiscuous/error-tolerant capture is (e.g. passing up frames with bad FCS).
- **Retransmission and timing.** The MAC retry limits, ACK/SIFS handling, and backoff are in target source. Tightening or loosening retransmission and inspecting the airtime/throughput effect is a classic experiment — and one you can *only* do at this layer on an open chip.
- **Rate control hand-off & aggregation.** The host `ath9k` rate-control (Minstrel-HT) negotiates with target behavior; you can observe and alter how the target reacts to the host's rate/aggregation decisions.
- **TX power / regulatory (read the warning below).** Register writes exist in source; changing them has legal consequences.
- **Instrumentation.** Add debug counters / register dumps in the firmware and surface them over the HTC channel to correlate PHY register state with what you see in `radiotap` captures — a stepping stone toward the [CSI-style](../../projects/csi-toolchains.md) and [PHY-verification](../verification-tier2-csi.md) work catalogued elsewhere.

This is the "open-firmware" capability flag made concrete: not a magic SDR, but a genuine, unlocked MAC firmware you can rebuild at will.

---

## 7. Safety & regulatory notes (read before any TX change)

- **Transmission is regulated.** The moment you touch TX power, channel/frequency tables, duty cycle, or regulatory-domain handling, you can emit signals that are **illegal** in your jurisdiction (FCC / ETSI / local equivalents) and that interfere with others. Monitor/receive-side and timing experiments are far lower risk than anything that changes what the radio *transmits*.
- **Keep TX experiments on a wired/shielded bench or RF enclosure**, use minimum power, and never operate outside license-free 2.4 GHz allocations you are actually entitled to use.
- **The chip is RAM-loaded — nearly unbrickable.** A malformed `.fw` fails to load and the driver logs an error; restore the `.orig` and replug. There is no fuse to blow and no flash to corrupt from normal firmware iteration, which is exactly what makes this a good teaching platform.
- **ABI lockstep.** If you bump the firmware's version fields, the driver's `MAJOR/MINOR_VERSION_REQ` must match or it refuses the image. Keep the versioned filename **and** the embedded version consistent with your kernel's `ath9k_htc`.

---

## 8. References (primary sources)

- Firmware source repository — [`github.com/qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware) (README: cmake + `make toolchain` + `make -C target_firmware`; ClearBSD / MIT / GPLv2 mixed licensing; outputs `htc_9271.fw` / `htc_7010.fw`).
- Issue tracker & mailing list — `github.com/qca/open-ath9k-htc-firmware/issues`, `ath9k_htc_fw@lists.infradead.org`.
- Linux wireless driver page — `ath9k_htc` (firmware filenames, `/lib/firmware`, "This firmware is now open"): [wireless.wiki.kernel.org/en/users/drivers/ath9k_htc](https://wireless.wiki.kernel.org/en/users/drivers/ath9k_htc) (now served via `archive.kernel.org` / `wireless.docs.kernel.org`).
- Stock firmware binaries — [`linux-firmware`](https://gitlab.com/kernel-firmware/linux-firmware), directory `ath9k_htc/` (`htc_9271-1.4.0.fw`).
- Driver source (firmware version request / filename constants) — `drivers/net/wireless/ath/ath9k/hif_usb.c` in the mainline Linux kernel.

## 9. See also (within this catalog)

- Parent chip family and AR9271/AR7010 entries — [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md)
- How the *closed* chips get opened by contrast — [../firmware-reversing.md](../firmware-reversing.md)
- The Nexmon patching model for closed Broadcom firmware — [../../projects/nexmon.md](../../projects/nexmon.md)
- Where AR9271 sits on the SDR ladder — [../taxonomy.md](../taxonomy.md)
- The other end of the spectrum (real SDRs) — [../true-sdr-comparison.md](../true-sdr-comparison.md)
- Sibling injection-focused walkthrough — [rtl8812au-monitor-injection.md](rtl8812au-monitor-injection.md)
