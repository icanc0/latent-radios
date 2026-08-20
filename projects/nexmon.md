# Nexmon — The C-Based Firmware-Patching Framework for Broadcom/Cypress Wi-Fi

> _"The C-based Firmware Patching Framework for Broadcom/Cypress WiFi Chips that enables Monitor Mode, Frame Injection and much more."_ — [seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon)

**Nexmon** (SEEMOO / Secure Mobile Networking Lab, TU Darmstadt) is the single most important project in this entire catalog. It is the reason a $35 Raspberry Pi or a used Nexus 5 can be talked about in the same breath as an SDR. Every rung of the [SDR ladder](../docs/taxonomy.md) above Tier 0 that we attribute to a Broadcom or Cypress part is reachable *because Nexmon exists*: it turns the chip's closed, undocumented Wi-Fi firmware into something you can read, patch in C, and reflash — without vendor source, without an FPGA, and without leaving the commodity silicon already soldered into billions of phones and routers.

This file explains **what Nexmon is, the firmware architecture it attacks, how a patch is authored and flashed, which chips/firmwares it covers, and the sub-projects that carry the catalog from Tier 1 (monitor/injection) all the way to the Tier-4 evidence (arbitrary IQ transmission / reactive jamming).** For the chips themselves see [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md); for the general reversing methodology see [../docs/firmware-reversing.md](../docs/firmware-reversing.md).

---

## 1. Why it matters

Before Nexmon, unlocking monitor mode or CSI on a mobile Wi-Fi chip meant either an out-of-tree binary blob from a friendly researcher or nothing at all. Broadcom/Cypress ("FullMAC") chips do their 802.11 MAC and much of the PHY control *on-chip*, in firmware the host never sees, precisely so that the host driver (`brcmfmac`/`dhd`) stays a thin shim. Nexmon inverts that: it provides a reproducible toolchain to

- **extract** the on-chip ROM and the D11 microcode,
- **disassemble/annotate** both,
- let you **write new firmware features in C** that are compiled, relocated, and stitched into the stock firmware via a *flashpatch* mechanism, and
- **reflash** the patched firmware through the normal driver load path.

That single capability is what makes Broadcom the most SDR-adjacent Wi-Fi family in existence. Nexmon is a *framework*, not a single hack: dozens of per-chip/per-firmware patch directories, a plugin-style patch model, and a family of downstream research projects (CSI, spectral, jamming, AirDrop/Apple RE, WARDriving) all build on the same core.

---

## 2. The architecture Nexmon attacks

A modern Broadcom Wi-Fi chip is really **two processors plus a PHY sequencer**:

| Layer | What it is | Nexmon's handle on it |
|---|---|---|
| **ARM firmware** ("the firmware") | A Cortex-R4 / Cortex-M3-class core running the closed FullMAC 802.11 stack, IOCTL handler, power management, and rate control. Ships as `brcmfmac*.bin` / `fw_bcmdhd.bin`. | Patched in **C**; new functions are appended to RAM and hooked in via **flashpatches** that rewrite ROM branch targets. This is where monitor mode, injection, CSI export, and the IOCTL/nexutil API live. |
| **D11 microcode ("ucode")** | A tiny custom-ISA microsequencer (the "d11" core) that drives the MAC/PHY in hard real time — TX/RX state machine, ACK timing, backoff. Compressed and shipped *inside* the ARM firmware image. | Nexmon **decompresses and extracts** the ucode (`ucode.bin`), which can be disassembled/patched with **b43-tools' `b43-dasm`/`b43-asm`** (the same assembler used by the open `b43` driver). Reactive jamming and precise TX timing require ucode edits. |
| **PHY / radio front-end** | The OFDM modem + RF. Not a general DAC/ADC, but the TX path can be fed a **template/IQ sample buffer**, and the RX path exposes **FFT/spectral** bins and **per-subcarrier CSI**. | Reached indirectly: firmware writes the sample-play buffer (→ arbitrary-waveform TX, Tier 4) and reads the PHY's channel-estimate / FFT registers (→ CSI Tier 2, spectral Tier 3). |

### ROM + ucode extraction (the prerequisite)

Most chips keep the bulk of the firmware in on-chip **ROM**, with a small RAM overlay and a **flashpatch** table that redirects a handful of ROM addresses to RAM. To reverse the real code you must recover the ROM. Nexmon ships a `rom_extraction/` recipe per chip (e.g. `patches/bcm43455c0/7_45_154/rom_extraction/`, `patches/bcm43451b1/7_63_43_0/rom_extraction/`) that:

1. dumps accessible regions directly (`dhdutil membytes -r 0x0 0xA0000 > rom.bin`), or
2. loads a tiny patch that **copies ROM→RAM** and dumps it cleanly through `dhdutil`, then
3. **decompresses the embedded D11 ucode** so it can be disassembled.

The build emits the reusable artifacts the rest of the toolchain needs: `ucode.bin` (uncompressed microcode), `flashpatches.c` (extracted patch table), and `definitions.mk` (per-firmware symbol addresses / RAM layout).

### The host interface: wl / dhd / brcmfmac / nexutil

- **`brcmfmac`** — the mainline Linux FullMAC driver (Raspberry Pi, many laptops). Nexmon ships a patched `brcmfmac.ko` so the kernel accepts the modified firmware and passes Nexmon IOCTLs through.
- **`dhd`** ("Dongle Host Driver") + **`wl`/`dhdutil`** — Broadcom's own Android/vendor driver and its userspace control tools, used on Nexus/Galaxy phones.
- **`nexutil`** — Nexmon's own userspace tool that speaks the custom IOCTLs (`nexioctl.h`) to the patched firmware: set/get config, push base64 config blobs, toggle features. It is the universal front door to every Nexmon feature (`nexutil -s500 -b -l34 -v<base64>` is the canonical CSI-arming call).
- **`libnexio` / `libnexmon`** — a small library (and an `LD_PRELOAD` shim) that lets normal tools (e.g. `tcpdump`, pcap apps) reach the firmware, including a privilege-separated UDP path on locked-down phones like the Nexus 5.

---

## 3. How a patch is written and flashed

Nexmon patches are ordinary **C** compiled against the extracted firmware, using GCC hooks and a set of macros that place code and rewrite call sites.

A typical patch source uses attributes/macros like:

- `__attribute__((at(addr, "", CHIP_VER, FW_VER)))` — pin a symbol/patch to an exact address for a specific chip+firmware,
- `BPATCH` / `GPATCH` / branch-patch and hook-patch macros — overwrite a ROM instruction with a branch into your new RAM function,
- `wrapper.c` — declarations for stock firmware functions you want to *call* (so your C can reuse the vendor's own routines).

**Getting-started outline (Raspberry Pi 3B+/4, bcm43455c0):**

```bash
# 1. Deps + a compatible toolchain (ARM GCC)
sudo apt install git libgmp3-dev gawk qpdf bison flex make \
     autoconf libtool texinfo raspberrypi-kernel-headers
git clone https://github.com/seemoo-lab/nexmon.git && cd nexmon

# 2. Build the framework's own tools + extract ucode/flashpatches
source setup_env.sh
make                       # builds cc, libISL, ucode/flashpatch extractors

# 3. Enter the per-chip / per-firmware patch dir and build the patched fw
cd patches/bcm43455c0/7_45_206/nexmon    # (Pi firmware version varies)
make                       # compiles your C patch, links, emits brcmfmac*.bin

# 4. Back up stock firmware, then flash the patched image
make backup-firmware
make install-firmware      # copies patched fw + patched brcmfmac.ko into place

# 5. Use it
sudo nexutil -m2                         # enable monitor mode
sudo iw dev wlan0 interface add mon0 type monitor
```

The exact firmware version string (e.g. `7_45_154`, `7_45_189`, `7_45_206`) **must match the blob on your device** — it selects the correct address definitions. Mismatched versions are the #1 cause of build/boot failures; check `strings` on the shipped `brcmfmac43455-sdio.bin`.

---

## 4. Supported chips & firmware versions

Nexmon's `patches/` tree is organized `patches/<chip>/<firmware_version>/<feature>/`. Coverage (breadth varies by feature — many chips have monitor/injection but not every downstream project):

| Chip | Example FW string(s) | Representative device(s) | Notably unlocks |
|---|---|---|---|
| **BCM4339** | `6_37_34_43` | Nexus 5 | monitor, injection, **CSI**, **reactive jamming / arbitrary TX** |
| **BCM43455c0** | `7_45_154`, `7_45_189`, `7_45_206` | **Raspberry Pi 3B+ / 4B / (CM4 / 5)** | monitor, injection, **CSI (up to 80 MHz)**, spectral |
| **BCM43430a1** | `7_45_41_26` | Raspberry Pi 3 / Zero W | monitor, injection |
| **BCM43436b0** | — | Raspberry Pi Zero 2 W / newer Pi 3 revs | monitor, injection |
| **BCM4358** | `7_112_300_14_sta`, `7_112_200_17_sta` | Nexus 6P | monitor, injection, **CSI (4-stream, float format)** |
| **BCM4366c0** | `10_10_122_20` | Asus RT-AC86U (router) | **CSI (4×4 MIMO, 80 MHz)** |
| **BCM4335b0 / BCM4330 / BCM4358 / BCM43596** | various | Nexus/Galaxy, older | monitor, injection |
| **BCM4375 / BCM4389 / BCM4398** | e.g. `bcm4375b1`, `bcm4389c1`, `bcm4398d0` | Galaxy S10–S22, Pixel 7/8 | actively-added modern targets (monitor/injection; RE ongoing) |
| **BCM43451b1** | `7_63_43_0` | iPhone 6-class | ROM extraction / RE reference |

> The upstream list keeps growing; downstream forks ([kimocoder/nexmon](https://github.com/kimocoder/nexmon), [nexmonster](https://github.com/nexmonster)) add device/kernel fixes and newer Pi OS support faster than upstream. Treat the **feature × chip × firmware** matrix as sparse: confirm the specific `patches/<chip>/<fw>/<feature>` dir exists before promising a capability.

---

## 5. Sub-projects (the ladder, rung by rung)

### 5.1 Monitor mode + frame injection — **Tier 1**
The flagship patch: adds real 802.11 monitor mode with **radiotap** headers and arbitrary **frame injection** on chips whose stock firmware exposes neither. This is what makes a Nexus 5 / Raspberry Pi behave like a classic Atheros monitor-mode card. `nexutil -m2` + a `type monitor` interface, then `aircrack-ng`/`tcpdump`/`scapy` work as usual. **Status: verified.**

### 5.2 nexmon_csi — per-subcarrier CSI — **Tier 2**
[github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi). Extracts **Channel State Information** (complex amplitude *and* phase per OFDM subcarrier) for 802.11a/g/n/ac frames, per-frame, up to **80 MHz** bandwidth. Subcarriers: 64 (20 MHz) / 128 (40) / 256 (80). Armed with `makecsiparams` (channel/bw `-c 157/80`, core `-C`, spatial stream `-N`, MAC filter `-m`, byte filter `-b`) → base64 → `nexutil -s500 -b -l34 -v<params>`; CSI streams out as UDP packets on **port 5500** (magic `0x11111111`, MAC, seq, core/stream, chanspec, chip id, then CSI). Data format differs by chip: **int16 interleaved real/imag** (bcm4339, bcm43455c0) vs a **float-ish sign/exponent/mantissa** encoding (bcm4358, bcm4366c0). This is *the* reason the Raspberry Pi is the default Wi-Fi-sensing platform. See [../projects/csi-toolchains.md](../projects/csi-toolchains.md). **Status: verified.**
Cite: Gringoli, Schulz, Link, Hollick, *"Free Your CSI: A Channel State Information Extraction Platform for Modern Wi-Fi Chipsets,"* WiNTECH 2019, DOI [10.1145/3349623.3355477](https://dl.acm.org/doi/10.1145/3349623.3355477).

### 5.3 Spectral analysis — **Tier 3**
Nexmon exposes the PHY's **FFT / spectral-scan** engine, yielding power-per-FFT-bin across the channel whether or not a frame is present — a poor-man's spectrum analyzer on the Wi-Fi chip itself (conceptually akin to Atheros `spectral_scan`, but reached via firmware patch). Useful for interference hunting and non-Wi-Fi energy detection in-band. **Status: reported/verified depending on chip.**

### 5.4 Reactive jamming & arbitrary-waveform TX — **Tier 4 evidence**
The strongest SDR claim in the catalog. Schulz, Gringoli, Steinmetzer, Koch, Hollick, *"Massive Reactive Smartphone-Based Jamming using Arbitrary Waveforms and Adaptive Power Control,"* **WiSec 2017**, DOI [10.1145/3098243.3098253](https://dl.acm.org/doi/10.1145/3098243.3098253). On a **Nexus 5 (BCM4339)** they load firmware that runs on the chip's real-time (D11/ARM) path and **reactively jams** 2.4/5 GHz Wi-Fi by transmitting **arbitrary waveforms stored in IQ sample buffers** — including an *acknowledging jammer* that selectively jams a targeted stream while others flow, with adaptive TX-power control. This is a Wi-Fi chip driven as an SDR TX: author a baseband IQ buffer → play it out the front-end. Reproducibility + demo code are public:
- [wisec2017_nexmon_jammer_demo_app](https://github.com/seemoo-lab/wisec2017_nexmon_jammer_demo_app)
- [wisec2017_nexmon_jammer_demo_firmware](https://github.com/seemoo-lab/wisec2017_nexmon_jammer_demo_firmware)
- [wisec2017_nexmon_jammer_reproducibility](https://github.com/seemoo-lab/wisec2017_nexmon_jammer_reproducibility)

**Status: reported** — demonstrated in papers/demo firmware on specific chips, not a turnkey `nexutil` feature. It is why BCM4339 (and the arbitrary-TX-capable Broadcom line) earns Tier-4 attribution rather than being capped at Tier 3. Note: transmitting arbitrary/jamming waveforms is illegal in most jurisdictions outside a shielded lab.

> **Tier 5?** Nexmon does *not* make the PHY fully open — the radio/modem stays a black box you steer, not a documented soft-radio. So the Broadcom family tops out at a hard-won **Tier 4 (reported)**; it never reaches the "open PHY" rung. See [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

### 5.5 Other notable descendants
Nexmon's RE toolchain also underpins Apple-Wi-Fi/AirDrop research, WARDriving/monitor tooling on phones, and the many community forks that keep pace with new Pi OS kernels and new Broadcom silicon.

---

## 6. Firmware RE toolchain (what's in the box)

| Tool | Role |
|---|---|
| **Nexmon core (C hooks, `at()`/`BPATCH` macros, patch linker)** | write & place C patches into stock firmware |
| **`b43-tools` (`b43-dasm`/`b43-asm`)** | disassemble/assemble the extracted **D11 ucode** |
| **`nexutil` / `libnexio` / `libnexmon`** | userspace control + tool interop (IOCTL/UDP) |
| **Ghidra / IDA / radare2** | disassemble the extracted **ARM ROM** (Nexmon publishes symbol maps / loader helpers) |
| **`dhdutil` / `wl`** | dump memory, poke firmware on Android/vendor drivers |

See [../docs/firmware-reversing.md](../docs/firmware-reversing.md) for the general ROM-dump → symbolication → patch loop this project canonicalized.

---

## Summary table

| Sub-project | Rung | Capability | Repo / cite | Status |
|---|---|---|---|---|
| Monitor + injection | **1** | raw 802.11 RX/TX, radiotap | [seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon) | verified |
| nexmon_csi | **2** | per-subcarrier CSI (amp+phase), ≤80 MHz | [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi); WiNTECH'19 | verified |
| Spectral scan | **3** | FFT power bins across channel | nexmon spectral patches | reported/verified |
| Reactive jammer / arbitrary TX | **4** | author IQ buffer → transmit; reactive/ack jamming | WiSec'17 + jammer repos | reported |
| Open PHY (Tier 5) | — | *not reached* — PHY stays closed | — | n/a |

## Key references

- Main framework — <https://github.com/seemoo-lab/nexmon>
- CSI extractor — <https://github.com/seemoo-lab/nexmon_csi>
- "Free Your CSI" (WiNTECH 2019) — <https://dl.acm.org/doi/10.1145/3349623.3355477>
- "Massive Reactive Smartphone-Based Jamming…" (WiSec 2017) — <https://dl.acm.org/doi/10.1145/3098243.3098253>
- Nexmon (WiNTECH 2017 tool paper) — <https://dl.acm.org/doi/10.1145/3131473.3131476>
- Jammer demo/reproducibility — <https://github.com/seemoo-lab/wisec2017_nexmon_jammer_demo_firmware>
- Community fork (newer devices/kernels) — <https://github.com/kimocoder/nexmon>

## Un-cataloged / TODO
- Exact **feature × chip × firmware** support matrix (which of monitor/CSI/spectral/jamming exists per `patches/<chip>/<fw>/` dir) — needs enumeration from the live repo tree.
- Modern flagship targets **BCM4375 / BCM4389 / BCM4398** (Galaxy S10–S22, Pixel 7/8): confirm which capabilities are upstreamed vs. RE-in-progress.
- **BCM4366c0 router CSI** (Asus RT-AC86U) 4×4 detail + firmware `10_10_122_20` reproducibility.
- Raspberry Pi **CM4 / Pi 5** firmware-version drift for nexmon_csi (which `7_45_x` builds work).
- b43 ucode patch depth: how much of the D11 microsequencer is documented vs. inferred.
- nexmon-based **AirDrop / Apple Wi-Fi** RE spinoffs — cross-reference in a future cycle.
- Downstream **nexmonster / Pi-specific** forks: catalog their added device support.
