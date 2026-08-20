# Building carl9170 Open Firmware for AR9170 USB

> **The other open Wi-Fi firmware.** The sibling walkthrough [building-flashing-open-ar9271-firmware.md](building-flashing-open-ar9271-firmware.md) covers the AR9271 (`ath9k_htc`, Tensilica **Xtensa** core, [`qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware)). This page covers the **AR9170** — a *different* USB chip, a *different* driver (`carl9170`), a *different* CPU core (**SuperH SH-2**, not Xtensa), and a *different* open-source firmware tree ([`carl9170fw`](https://github.com/chunkeey/carl9170fw)). Both are genuinely open — you `git clone` C source and compile a `.fw` — but they share no code and no toolchain. Do not confuse them.
>
> Parent chip page: [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md). Reverse-engineering context for *closed* chips: [../firmware-reversing.md](../firmware-reversing.md).

---

## 1. What the AR9170 actually is

The **AR9170** is an Atheros **USB 2.0 → 802.11n (draft-n)** MAC/baseband controller from the ~2008 era. It is a *two-chip* design: the AR9170 provides the USB interface, 802.11 MAC, and baseband, and pairs with an external Atheros radio (e.g. **AR9104** dual-band 2×2, or a 2.4 GHz-only radio) to make a finished dongle. Depending on the radio fitted, a device is 2.4 GHz-only or dual-band 2.4/5 GHz, typically up to **2 spatial streams (2T2R)**.

Inside the AR9170 is an embedded **Renesas SuperH SH-2** microcontroller that runs the firmware. The Linux host driver `carl9170` streams commands and 802.11 frames over USB; the on-chip firmware drives the hardware MAC and the baseband/radio. Because Atheros **released the firmware source under GPLv2**, you can read and rebuild that firmware end-to-end.

> **Terminology note / correction.** The AR9170's embedded core is **SuperH SH-2**, *not* SPARC. The clue is in the toolchain: `carl9170fw` builds a cross-compiler configured `--target=sh-elf`. Any reversing you do (Ghidra, objdump) must use the **SH-2/SuperH** processor module, not SPARC or Xtensa.

### Honest SDR tier

Open firmware does **not** make the AR9170 a general-purpose SDR. You operate **above** the hardware MAC/PHY: you control framing, timing, retransmission, aggregation, LED and monitor/injection behavior — not raw I/Q at the ADC/DAC. On the [taxonomy ladder](../taxonomy.md) a stock `carl9170` device sits at **Tier 1**: monitor mode and frame injection are first-class and well supported. Unlike `ath9k`/`ath9k_htc`, mainline `carl9170` exposes **no spectral-scan or CSI interface**, so there is no "free" Tier 3 here. The real value is that **every rung above Tier 1 is now reachable by editing C you can read and recompile**, rather than by defeating a signature — treat higher tiers as a research project you now own the source to attempt (`status: theoretical` until demonstrated), not a shipped capability.

---

## 2. Driver lineage — otus → ar9170usb → carl9170

| Era | Name | Notes |
|---|---|---|
| ~2.6.29 | **otus** | Original Atheros vendor/staging driver. Needed a custom wpa_supplicant; poor code quality; used a *closed* firmware blob. |
| ~2.6.30 | **ar9170usb** | Johannes Berg rewrote it against mac80211 for upstream; Christian Lamparter (`chunkeey`) refined it. Crucially, Atheros **released the firmware source under GPLv2** in this period. |
| 2010+ | **carl9170** | Christian Lamparter's clean successor that fully replaced both otus and ar9170usb. It runs **only** the open `carl9170fw` firmware (`carl9170-1.fw`). This is the current in-kernel driver. |

`carl9170` and `ar9170usb`/`otus` are mutually exclusive — modern kernels ship only `carl9170`.

---

## 3. Target hardware (older USB dongles)

The AR9170 shipped in a wide range of 2008–2011 USB sticks. The generic Atheros VID:PID is **`0cf3:9170`**; many vendors rebadged it. Confirmed IDs from the mainline `carl9170_usb_ids` table (`drivers/net/wireless/ath/carl9170/usb.c`):

| Device | USB VID:PID |
|---|---|
| Atheros AR9170 reference / Airlive X.USB a/b/g/n | `0cf3:9170` / `1b75:9170` |
| Atheros TG121N | `0cf3:1001` |
| TP-Link TL-WN821N v2 | `0cf3:1002` |
| 3Com / H3C Dual Band 802.11n USB | `0cf3:1010` / `0cf3:1011` |
| **CACE AirPcap NX** (Wireshark sniffer) | `cace:0300` |
| D-Link DWA-160 A1 / A2, DWA-130 D | `07d1:3c10` / `07d1:3a09` / `07d1:3a0f` |
| Netgear WNA1000 / WNDA3100 v1 / WN111 v2 | `0846:9040` / `0846:9010` / `0846:9001` |
| ZyXEL NWD271N | `0586:3417` |
| Z-Com UB81 BG / UB82 ABG / Sphairon Homelink 1202 | `0cde:0023` / `0cde:0026` / `0cde:0027` |
| AVM FRITZ!WLAN USB Stick N / N 2.4 | `057c:8401` / `057c:8402` |
| Planex GWUS300 | `2019:5304` |
| NEC WL300NU-G / WL300NU-AG | `0409:0249` / `0409:02b4` |
| IO-Data WNGDNUS2, Proxim ORiNOCO 11n, Arcadyan WN7512, Qwest/Actiontec 802AIN | `04bb:093f`, `1435:0804`, `083a:f522`, `1668:1200` |

> The **CACE AirPcap NX** (`cace:0300`) is a notable entry: it was the top-tier AirPcap Wi-Fi capture adapter for Wireshark on Windows, and under Linux it is just an AR9170 that `carl9170` drives for monitor capture.

Identify what you have before building:

```bash
lsusb | grep -iE 'atheros|9170'
# e.g. 0cf3:9170 Atheros Communications, Inc. AR9170 802.11n
dmesg | grep -i carl9170
# ... usb 1-1: driver api version 1.9.9, firmware api version ...
# ... carl9170 1-1:1.0: Atheros AR9170 is registered as 'wlan0'
```

If `lsusb` shows a Realtek/MediaTek ID instead, this is not an AR9170 device — see [../../chips/realtek.md](../../chips/realtek.md) / [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md).

---

## 4. Where the driver loads the firmware

`carl9170` requests a single **API-revisioned** firmware file through the standard Linux firmware loader:

```
/lib/firmware/carl9170-1.fw
```

The stock, signed-by-nobody (GPLv2) binary ships in [`linux-firmware`](https://gitlab.com/kernel-firmware/linux-firmware) as `carl9170-1.fw`. Historically distributed release binaries were **1.9.2** (works on Linux 2.6.x / 3.0) and **1.9.9** (Linux 3.1+); the firmware and driver negotiate a compatible **API version** at load time, which is why the filename carries the API rev (`-1`) rather than the release number. Confirm what your kernel wants:

```bash
dmesg | grep -oE 'carl9170[-0-9.]*\.fw'
# -> carl9170-1.fw   (this is the filename your build must install as)
```

---

## 5. Clone and build the firmware

Repo (pick either mirror — same tree):

```bash
# GitHub (Christian Lamparter / chunkeey)
git clone https://github.com/chunkeey/carl9170fw.git
# or kernel.org
git clone https://git.kernel.org/pub/scm/linux/kernel/git/chr/carl9170fw.git
cd carl9170fw
```

### 5a. Build the SH-2 cross toolchain

The firmware is SuperH SH-2 code, so you need an `sh-elf` cross-compiler. The repo bundles a Makefile that fetches and builds **binutils + gcc + newlib** configured `--target=sh-elf`:

```bash
make -C toolchain          # downloads sources, builds sh-elf binutils/gcc/newlib into toolchain/inst
```

> This is slow and needs roughly **3–5 GiB** of disk. On current master it builds a modern toolchain (binutils ≈ 2.47, gcc ≈ 16.x, newlib ≈ 4.6). If you already have an `sh-elf-gcc` (e.g. from your distro or crosstool-NG), you can point the firmware build at it instead of running this step. Put `toolchain/inst/bin` on your `PATH`.

### 5b. Configure and compile the firmware image

Host-side build dependencies (from the README):

- **gcc 6.0+** (plus dev headers/libs)
- **bison / flex**
- **cmake 3.8+**

Configure (a Linux KConfig-style CLI — press `<Enter>` to accept each default), then build:

```bash
./autogen.sh               # runs KConfig prompts, then cmake + make
```

This produces the firmware image (e.g. `carlfw/carl9170.fw`) under the build directory. The `carlfw/` sources are the actual on-chip firmware; `tools/`, `include/`, and `minifw/` provide host utilities, the shared driver/firmware API headers (`genapi.sh` regenerates them), and a minimal bring-up firmware respectively.

### 5c. Install

```bash
./autogen.sh install
# copies the image to /lib/firmware/carl9170-1.fw (API rev appended automatically)
```

Then reload the driver and re-plug the dongle:

```bash
sudo modprobe -r carl9170 && sudo modprobe carl9170
dmesg | grep -i carl9170     # confirm your freshly built firmware API version loaded
```

---

## 6. Verify monitor + injection (Tier 1, verified)

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
sudo iw dev wlan0 set channel 6
# capture:
sudo tcpdump -i wlan0 -e -s0 type mgt subtype beacon
# inject (aircrack-ng suite):
sudo aireplay-ng --test wlan0        # injection self-test
```

See [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md) and [wireshark-radiotap-80211-analysis.md](wireshark-radiotap-80211-analysis.md) for capture-side tooling. For anything that **transmits** custom frames, read [../rf-safety-and-legal.md](../rf-safety-and-legal.md) first: stay on channels/power your regulatory domain permits, and prefer a shielded/attenuated setup for injection experiments.

---

## 7. What to do with open firmware (and honest limits)

Because `carlfw/` is readable C compiled for the SH-2, you can modify **MAC timing, retransmission policy, aggregation, rate-control hand-off, LED behavior, and monitor/injection paths** and observe them on real hardware — the low-level control that on closed chips requires Nexmon-style patching ([../../projects/nexmon.md](../../projects/nexmon.md)).

What you **cannot** get for free:

- **No mainline spectral scan / CSI.** Unlike `ath9k`/`ath9k_htc` (see [atheros-ath9k-spectral-csi.md](atheros-ath9k-spectral-csi.md)), the `carl9170` driver exposes no FFT-bin or CSI debugfs. Extracting PHY-domain data would mean adding firmware code to read baseband registers and a host transport for it — a research effort, `status: theoretical`.
- **No raw I/Q.** The SH-2 firmware is a MAC controller, not a sample pipe; there is no ADC/DAC I/Q path exposed to it.

For reversing the firmware image itself (or the ROM), load it in **Ghidra with the SuperH/SH-2 processor module** and cross-reference symbols against the open `carlfw/` source — the open tree is effectively ground truth, so this is validation rather than blind RE. General method: [../firmware-reversing.md](../firmware-reversing.md), [ghidra-setup-wifi-firmware.md](ghidra-setup-wifi-firmware.md).

---

## 8. carl9170 vs ath9k_htc — don't mix them up

| | **AR9170 / carl9170** (this page) | **AR9271 / ath9k_htc** ([sibling](building-flashing-open-ar9271-firmware.md)) |
|---|---|---|
| Chip | AR9170 (2-chip: MAC/BB + ext. radio) | AR9271 (single-chip) / AR7010 bridge |
| Embedded CPU | **SuperH SH-2** (`sh-elf`) | **Tensilica Xtensa** |
| Open firmware repo | [`chunkeey/carl9170fw`](https://github.com/chunkeey/carl9170fw) | [`qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware) |
| Firmware file | `/lib/firmware/carl9170-1.fw` | `/lib/firmware/ath9k_htc/htc_9271-1.4.0.fw` |
| Toolchain | binutils/gcc/newlib `--target=sh-elf` | Xtensa GNU toolchain |
| Mainline PHY data | none (Tier 1) | spectral scan (Tier 3) |

Both are GPLv2 and buildable from source; they are otherwise unrelated.

---

## References

- carl9170fw source (GitHub, Christian Lamparter): <https://github.com/chunkeey/carl9170fw>
- carl9170fw source (kernel.org): <https://git.kernel.org/pub/scm/linux/kernel/git/chr/carl9170fw.git>
- carl9170fw README (SH-2 toolchain, `autogen.sh`, install): <https://github.com/chunkeey/carl9170fw/blob/master/README.md>
- SH-2 toolchain Makefile (`--target=sh-elf`, binutils/gcc/newlib): <https://github.com/chunkeey/carl9170fw/blob/master/toolchain/Makefile>
- linux-wireless carl9170 driver page (history: otus → ar9170usb → carl9170, firmware versions 1.9.2 / 1.9.9): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/carl9170.html>
- Mainline driver + USB ID table: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/ath/carl9170>
- Stock firmware binary (`carl9170-1.fw`) in linux-firmware: <https://gitlab.com/kernel-firmware/linux-firmware>
- Parent chip page: [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md)
