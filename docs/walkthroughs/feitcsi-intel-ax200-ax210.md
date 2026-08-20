## FeitCSI on Intel AX200/AX210 — the kernel-agnostic modern CSI path — Cycle 10

> **Where this fits.** The [verification summary](../../docs/verification-summary.md) names three newcomer-friendly, current-hardware CSI paths: **ESP32** (no host-kernel dependency), **Nexmon CSI on a Raspberry Pi**, and **Intel AX via FeitCSI** — flagged specifically as the *"kernel-agnostic live USB"* route for Wi-Fi 6/6E CSI. This page is the deep-dive on that third path. For the broader Intel CSI story — including why "AX-CSI" is a **Broadcom** tool that the catalog once mis-attributed to Intel — see the companion walkthrough [`ax-csi-intel-ax200-ax210`](../../docs/walkthroughs/ax-csi-intel-ax200-ax210.md). For the vendor ceiling see [`../../chips/intel.md`](../../chips/intel.md); for the full tool zoo see [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md).
>
> **Primary source throughout:** <https://feitcsi.kuskosoft.com/> · code <https://github.com/KuskoSoft/FeitCSI> (GPL-3.0) · paper <https://ieeexplore.ieee.org/document/10944229/>.

### 0. TL;DR

| | |
|---|---|
| **What** | Open-source (GPL-3.0) CLI **+ GTK GUI** that extracts per-subcarrier CSI *and* injects arbitrary 802.11 frames on Intel AX-series NICs |
| **Silicon** | Intel **AX200** (2.4/5 GHz) and **AX210** (2.4/5/**6** GHz), "high possibility" newer Intel NICs work |
| **Formats** | 802.11 **a/g/n/ac/ax** (NOHT/HT/VHT/HESU), **20/40/80/160 MHz**, 6 GHz on AX210 |
| **SDR tier** | **2 — per-subcarrier complex CSI.** No spectral bins, no raw IQ, no PHY. Injection is canned-frame, not arbitrary-waveform. |
| **Openness** | Tool + `feitcsi-iwlwifi` driver are **GPL and source-available**; the Intel **microcode underneath stays closed/signed** — you read the CSI surface the firmware chooses to expose, you cannot audit the estimator. |
| **The pitch** | You do **not** have to match a specific host kernel. Either the **DKMS .deb** recompiles the patched driver against *your* running kernel, or you boot the **live ISO** with everything pre-wired. |

### 1. The problem FeitCSI solves: version-pinning hell

Every Intel CSI tool has to deal with one hard fact: **AX-series `iwlwifi` microcode is cryptographically signed**, so you cannot binary-patch it the way Nexmon patches Broadcom D11 ucode. The CSI instead rides a channel-estimation/reporting surface the firmware already has, requested through a **patched `iwlwifi` driver** plus a userspace collector. That makes the whole path acutely sensitive to the **kernel ↔ driver ↔ firmware** triple — the single most common reason Intel CSI "just stops."

PicoScenes handles this by shipping **prebuilt kernel modules pinned to specific Ubuntu 22.04 kernels**; drift onto a newer HWE kernel and capture breaks. FeitCSI takes the opposite tack — it does not pin *you* to a kernel, it adapts to whatever kernel you have. That is the "kernel-agnostic" claim, and it is delivered two ways:

- **DKMS package.** The patched driver is distributed as `feitcsi-iwlwifi` and installed through **DKMS**, which "as a kernel module, it is compiled against the current running kernel" and is "automatically recompiled on change running kernel version." Change kernels, DKMS rebuilds; you keep working.
- **Live USB/ISO.** A bootable Linux image with a **known-good kernel + patched driver + GUI already installed** — the "just boot it and capture" escape hatch when you don't want to touch your host at all. This is the route the verification summary recommends for newcomers.

Note the honest limit: kernel-*agnostic* is not firmware-*independent*. You still need Intel signed ucode that carries a working CSI reporting path in the loaded blob; FeitCSI supplies matched firmware, and swapping it out silently kills capture.

### 2. Supported hardware

| NIC | Bus | Bands | 160 MHz | 6 GHz | FeitCSI |
|---|---|---|:---:|:---:|:---:|
| **AX200** (Cyclone Peak) | discrete M.2 / mini-PCIe | 2.4 / 5 | ✓ | — | ✓ verified target |
| **AX210** (Typhoon Peak) | discrete M.2 | 2.4 / 5 / **6** | ✓ | ✓ (Wi-Fi 6E) | ✓ verified target |
| AX201 / AX211 (CNVi, soldered) | CNVi | as above | ✓ | AX211: ✓ | by extension (same ucode family) — not explicitly claimed |

The two **explicitly documented and tested** parts are the discrete **AX200** and **AX210**. 6 GHz (5945–7125 MHz) CSI and injection are real on the AX210 but **regdomain-gated** — the firmware enforces the region's rules, so 6 GHz availability is location-dependent.

### 3. Install

Two supported routes on Debian/Ubuntu-family systems (per the primary docs):

```bash
# Route A — DKMS .deb (recommended; dependencies + rebuild handled automatically)
# download the release .deb from the GitHub releases page, then:
sudo apt install ./feitcsi_*.deb
# the feitcsi-iwlwifi driver is registered with DKMS and compiled
# against your running kernel; it recompiles on every kernel change.

# Route B — from source (for people who want to modify it)
sudo apt install linux-headers-$(uname -r) build-essential
git clone https://github.com/KuskoSoft/FeitCSI
cd FeitCSI && make && sudo make install
```

Or **skip the host entirely**: write the FeitCSI **live ISO** to a USB stick and boot it — patched driver and GUI are already in place. Virtualized use (Virt-manager / VirtualBox) is also supported **only with PCI passthrough** of the NIC, since CSI needs the real device.

### 4. Capture — the CLI

The `feitcsi` binary takes long/short flags. The parameters that matter (defaults in parentheses):

| Flag | Short | Values | Meaning |
|---|---|---|---|
| `--frequency` | `-f` | 2412–7125 MHz (2412) | center frequency (2.4 / 5 / 6 GHz) |
| `--channel-width` | `-w` | `20` `40` `HT40-` `80` `160` | bandwidth |
| `--format` | `-r` | `NOHT` `HT` `VHT` `HESU` (HT) | PHY format — **`HESU` = 802.11ax (HE)** |
| `--spatial-streams` | `-s` | `1` `2` (1) | spatial streams |
| `--mode` | `-i` | `measure` `inject` `measureinject` `ftm` `ftmres` | operating mode |
| `--inject-delay` | `-d` | µs | gap between injected frames |
| `--output-file` | `-o` | path (`FeitCSI_{timestamp}.dat`) | binary CSI output |

```bash
# Passive HE (802.11ax) CSI capture: 5180 MHz, 80 MHz, 2 streams
sudo feitcsi -f 5180 -w 80 -r HESU -s 2 -o csi.dat

# HE at 160 MHz on 6 GHz (AX210, region permitting)
sudo feitcsi -f 6135 -w 160 -r HESU -s 2 -o csi_6ghz.dat

# Self-inject + measure on one NIC (see TX safety, §8)
sudo feitcsi -f 5180 -w 80 -r HESU -s 2 -i measureinject -d 50000 -o loop.dat
```

The **GUI** (GTK/Glade, `MainWindow.glade` in-tree) exposes the same parameters as controls plus a live CSI plot; a **UDP socket** control interface lets a remote process drive capture over the network. All three front-ends write the same file format.

### 5. The CSI output format

FeitCSI writes a flat binary file: repeated `[header][CSI block]` records concatenated. The **header is a fixed 272 bytes**; field offsets, taken from the primary [`csi_format`](https://feitcsi.kuskosoft.com/csi_format/) docs (so these are *documented offsets, not reverse-engineered guesses*):

| Bytes | Type | Field |
|---|---|---|
| 0–3 | u32 | CSI data size (bytes that follow this header) |
| 8–11 | u32 | FTM clock |
| 12–19 | u64 | timestamp (µs) |
| 46 | u8 | RX antenna count |
| 47 | u8 | TX antenna count |
| 52–55 | u32 | subcarrier count |
| 60–63 | u32 | TX1 RSSI |
| 64–67 | u32 | TX2 RSSI |
| 68–73 | — | source MAC |
| 92–95 | u32 | rate flags (format, MCS, bandwidth, antenna, LDPC, streams, beamforming) |

The **CSI block** follows immediately and is `4 × RX × TX × subcarrier_count` bytes. Each complex value is **4 bytes = int16 real (bytes 0–1) + int16 imaginary (bytes 2–3)**, signed. Iteration order is RX → TX → subcarrier.

The actual subcarrier count is **recorded per-record in the header**, so you never have to hardcode it — but for reference, HE per-stream counts are 20 MHz → 256, 40 MHz → 512, 80 MHz → 1024, 160 MHz → 2048 (78.125 kHz spacing). Catalog notes elsewhere quote FeitCSI resolution as "up to ~512 subcarriers at 16-bit"; trust the header field over any fixed number, since it reflects what the firmware actually emitted for that frame and bandwidth.

**Parsing.** The project ships both a **MATLAB** and a **Python** parser. The Python entry point is `parseFeitCSI(fileName)`, returning a list of per-frame dicts with a `header` and a `csi_matrix` shaped `[num_subcarriers, num_rx, num_tx]` of complex values:

```python
from feitcsi_parser import parseFeitCSI   # per feitcsi.kuskosoft.com/python/
frames = parseFeitCSI("csi.dat")
h   = frames[0]["header"]        # timestamp, RSSI, MCS, bandwidth, antenna cfg, format
csi = frames[0]["csi_matrix"]    # ndarray [subcarriers, rx, tx], complex
sc10 = csi[10, 0, 0]             # subcarrier 10, rx0, tx0
```

The universal parser **CSIKit** also auto-detects the FeitCSI format (alongside IWL5300 / AX200 / AX210 / Nexmon / ESP32 / PicoScenes) if you'd rather stay in one toolchain — see [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md). FeitCSI additionally emits an **FTM** (Fine Timing Measurement) format from its `ftm`/`ftmres` modes, useful for ranging — cross-reference [`../../docs/ftm-rtt-ranging.md`](../../docs/ftm-rtt-ranging.md).

### 6. How it compares — FeitCSI vs AX-CSI vs PicoScenes

| | **FeitCSI** | **AX-CSI** | **PicoScenes** |
|---|---|---|---|
| Silicon | **Intel AX200 / AX210** | **Broadcom BCM43684** (consumer AP) | IWL5300, QCA9300, AC9260, **AX200 / AX210**, USRP |
| Mechanism | patched `iwlwifi` (`feitcsi-iwlwifi`) + signed ucode + collector | Nexmon-patched **D11 + Wi-Fi OS** ucode | patched Intel/Atheros drivers + collector |
| Formats / BW | 11a…**ax**, **≤160 MHz**, 6 GHz (AX210) | 11ax HE, **≤160 MHz**, 4×4 | 11a…**ax**, ≤160 MHz, 6 GHz (AX210) |
| Injection | ✓ canned-frame inject | — (extraction only) | ✓ + **≤27 NICs concurrent** |
| Host coupling | **kernel-agnostic** (DKMS rebuild **or** live USB); x86-64 **and ARM** | AP firmware, host-independent | **pinned to Ubuntu 22.04** prebuilt kernel modules |
| Interface | **CLI + GUI + UDP socket** | pcap of UDP CSI datagrams | CLI + MATLAB/Python SDK |
| Source | **GPL-3.0, auditable** | tool released on request; nexmon-lineage patches | **closed-source**, free-for-academic binary |
| Best when | Modern Wi-Fi 6/6E, **single NIC, easiest**, open license | You have the RT-AX86U / BCM43684 AP | Many NICs, most formats, largest research platform |

**Reading the table honestly:**

- **FeitCSI's differentiators** are the ones the verification summary rewards: *open license* (GPL vs PicoScenes' academic binary), *no OS pinning* (DKMS + live USB vs Ubuntu-22.04 lock), *GUI*, and *ARM support*. For a newcomer who owns an AX200/AX210 and wants CSI today, it is the lowest-friction path.
- **AX-CSI is not a competitor on the same silicon** — it is a **Broadcom** AP tool, the 802.11ax successor to Nexmon CSI. The recurring catalog error was calling it an Intel tool; the Intel HE-CSI tools are FeitCSI and PicoScenes. Full untangling in [`ax-csi-intel-ax200-ax210`](../../docs/walkthroughs/ax-csi-intel-ax200-ax210.md).
- **PicoScenes wins on breadth** — it carries legacy NICs (IWL5300, QCA9300) and USRP front-ends onto a modern host and runs large MIMO arrays. If you need multiple NIC generations or >2 NICs synchronized, that's the platform. FeitCSI wins on being open and drop-in on *any* Debian/Ubuntu kernel.

### 7. Honest ceiling — why this is still Tier 2

FeitCSI is a genuinely nice tool, but it does not move Intel silicon off the CSI rung:

- **You consume, you don't author, the PHY.** The channel estimate comes out of Intel's **closed, signed microcode**; FeitCSI's GPL code is the *driver + collector*, not the estimator. You cannot see or change how the equalizer produces those numbers.
- **No spectral, no IQ, no waveform.** There are no FFT power bins (unlike Atheros `ath9k` spectral, Tier 3), no raw baseband IQ, and injection is **pre-formed 802.11 frames**, not arbitrary-waveform TX (unlike the nexmon SDR patch on Broadcom, Tier 4). See [`../../docs/true-sdr-comparison.md`](../../docs/true-sdr-comparison.md).
- **Catalog verdict:** Intel AX CSI = **tier 2**, openness **`patchable`** (open *tooling* over a closed *ucode debug surface*), never `open`. The GPL license and kernel-agnostic packaging improve *reproducibility and auditability of the tooling*, not the openness of the radio.

### 8. TX safety (injection / FTM modes)

`inject`, `measureinject`, and the FTM modes **transmit**. Before running them:

- **Do it in a shielded enclosure or on cabled/attenuated links.** Over-the-air injection on Wi-Fi bands is regulated; you are responsible for your regdomain's power/channel rules.
- **6 GHz is doubly gated.** AX210 6 GHz TX depends on the firmware-enforced regdomain; capability being present does not make it legal to radiate where you are.
- **Don't jam a live network.** Tight `--inject-delay` values flood the medium; keep injection on a quiet channel or in isolation.
- Passive `measure` mode does **not** transmit and is the safe default for pure sensing.

### 9. Reproduce it — minimal checklist

1. AX200 or AX210 in an M.2/mini-PCIe slot (discrete, not CNVi, for the simplest path).
2. Boot the **FeitCSI live USB**, *or* `apt install` the DKMS `.deb` on Debian/Ubuntu.
3. `sudo feitcsi -f 5180 -w 80 -r HESU -s 2 -o csi.dat` — capture a few seconds while a nearby AP/client transmits on that channel.
4. `parseFeitCSI("csi.dat")` in Python (or CSIKit) → array `[subcarriers, rx, tx]`.
5. Sanity check: subcarrier count in the header should match the bandwidth (80 MHz HE → ~1024/stream), and amplitude across subcarriers should look like a smooth channel response, not noise.

### References

- FeitCSI — home / documentation: <https://feitcsi.kuskosoft.com/>
- FeitCSI — CSI format: <https://feitcsi.kuskosoft.com/csi_format/> · FTM format: <https://feitcsi.kuskosoft.com/ftm_format/> · Python parser: <https://feitcsi.kuskosoft.com/python/> · CLI: <https://feitcsi.kuskosoft.com/command_line_interface/> · install: <https://feitcsi.kuskosoft.com/installation_and_upgrade/> · license (GPL-3.0): <https://feitcsi.kuskosoft.com/license/>
- FeitCSI source (GPL-3.0, Miroslav Hutar / KuskoSoft): <https://github.com/KuskoSoft/FeitCSI>
- Paper: *Enhancing CSI-based Wireless Sensing with an Open Source Linux 802.11ax CSI Tool*, IEEE 2025 — <https://ieeexplore.ieee.org/document/10944229/>
- CSIKit universal parser (reads FeitCSI): <https://github.com/Gi-z/CSIKit>
- PicoScenes (comparison): <https://ps.zpj.io/>
- Companion pages: [`ax-csi-intel-ax200-ax210`](../../docs/walkthroughs/ax-csi-intel-ax200-ax210.md) · [`../../chips/intel.md`](../../chips/intel.md) · [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) · [`../../docs/verification-summary.md`](../../docs/verification-summary.md) · [`../../docs/ftm-rtt-ranging.md`](../../docs/ftm-rtt-ranging.md)
