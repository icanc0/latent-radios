## Extracting HE (802.11ax) CSI from Intel AX200/AX210 — and what "AX-CSI" actually is — Cycle 7

> **Scope note / correction.** This walkthrough was commissioned as *"AX-CSI: extracting CSI from Intel AX200/AX210, the modern successor to the 5300 tool."* On checking the **primary source**, that framing conflates two different things, and the error is propagated in several sibling files of this catalog. The real, published **AX-CSI** (Gringoli, Cominelli, Blanco & Widmer, WiNTECH'21) is **not an Intel tool at all** — it extracts HE CSI from the **Broadcom BCM43684** in an Asus RT-AX86U, and is the 802.11ax successor to **Nexmon CSI** (Broadcom 802.11ac). The tools that actually pull HE CSI out of **Intel AX200/AX201/AX210/AX211** are **PicoScenes** and **FeitCSI**. This page documents both stories honestly and reproducibly, and is the *real* modern successor to [`intel-5300-csi`](../../docs/walkthroughs/intel-5300-csi.md).

### 0. TL;DR

| If you want… | Use | Silicon | Openness |
|---|---|---|---|
| HE CSI, 160 MHz, 4×4, up to 32768 subcarriers/frame, on a **consumer AP** | **AX-CSI** | **Broadcom BCM43684** (Asus RT-AX86U) | patched FullMAC ucode; tool by email request |
| HE CSI on a **laptop/M.2 client NIC**, all formats, incl. **6 GHz** | **PicoScenes** or **FeitCSI** | **Intel AX200/AX201/AX210/AX211** | signed ucode + patched `iwlwifi`; PicoScenes binary-only, FeitCSI GPL |
| 802.11n CSI, 30 subcarrier-groups | Linux 802.11n CSI Tool | Intel IWL5300 | see [`intel-5300-csi`](../../docs/walkthroughs/intel-5300-csi.md) |

All of these top out at **SDR tier 2 (per-subcarrier complex CSI)**. None gives spectral bins, raw IQ, or arbitrary-waveform TX. See [`../../chips/intel.md`](../../chips/intel.md) for the vendor ceiling and [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) for the tool zoo.

---

### 1. Why HE CSI is a different animal

The IWL5300 tool (Halperin et al., 2011) reported **30 "subcarrier groups"** with signed 8-bit real/imaginary parts — roughly one value per two subcarriers at 20 MHz. That was fine for 802.11n sensing but is coarse by modern standards.

802.11ax (HE PHY) changes the arithmetic:

- **Subcarrier spacing drops 4×** to **78.125 kHz** (from 312.5 kHz in legacy/HT/VHT). A 20 MHz HE frame therefore carries **256 subcarriers** where a 20 MHz VHT frame carried 64 (numbers from the AX-CSI paper, Fig. 5 / Tab. 1).
- **Per-stream subcarrier counts (HE):** 20 MHz → 256, 40 MHz → 512, 80 MHz → 1024, **160 MHz → 2048**.
- With **4×4 MIMO at 160 MHz HE** that is **2048 × 4 × 4 = 32768** complex CSI values *per single received frame* — an order of magnitude past anything the 5300 could produce.
- Smaller guard bands also make the "useful" spectrum wider, which helps time-of-flight / angle-of-arrival estimation even at 20 MHz.

Any "successor to the 5300 tool" has to move this much denser data out of a chip that was never designed to export it.

---

### 2. The **real** AX-CSI — Broadcom BCM43684 (Nexmon lineage)

**Paper:** F. Gringoli, M. Cominelli, A. Blanco, J. Widmer, *"AX-CSI: Enabling CSI Extraction on Commercial 802.11ax Wi-Fi Platforms,"* WiNTECH'21 (New Orleans, Jan 31–Feb 4 2022). DOI [10.1145/3477086.3480833](https://doi.org/10.1145/3477086.3480833) · preprint PDF <https://ans.unibs.it/assets/documents/axcsi.pdf>.

**Platform:** the **Asus RT-AX86U** access point, whose radio is the **Broadcom BCM43684** (802.11ax, 4×4). This is the direct port of the team's Nexmon-CSI work on the 802.11ac **BCM4365** to the newer ax silicon — *"we ported the tool we developed for the Broadcom 4365 chipset and adapted it for the new Broadcom 43684."*

#### How it works (FullMAC, split D11 / ARM)

Broadcom's FullMAC architecture splits work between a **D11 microcontroller** (time-critical: channel access, ACKs) and an **ARM "Wi-Fi OS" CPU**. In the older 802.11ac tool the D11 core did *everything*: freeze the radio, read the PHY channel estimate, push it up. On the 43684 the D11 **ucode memory is nearly full** because HE operations are complex, so AX-CSI splits the job:

1. **Patch the D11 core** to trigger only on target frames (specific MAC address / frame-control type). On a match it puts the radio into **deaf mode** to freeze the CSI (step 1).
2. The frame is pushed through the Rx FIFO to ARM memory as usual. **Patch the Wi-Fi OS Rx handler** (on ARM) to detect the target frame and call a new routine that reads the CSI out of the PHY tables (step 2).
3. The routine embeds CSI into **crafted UDP datagrams** and DMAs them to the Linux host (step 3); a userspace app on the host stores them into a packet trace.
4. The Wi-Fi OS **re-enables the radio** (step 4).

Doing the heavy lifting on ARM instead of D11 costs latency (see performance table) but was the only way to fit HE support.

#### CSI data layout (how they found the offsets — *not* invented)

CSI lives in **four PHY tables, one per radio core**, each holding up to **8192 complex values** (reading past that crashes the chip). The layout was reverse-engineered empirically by **dumping the PHY tables under controlled conditions**: sweeping radio bandwidth, RX-frame bandwidth, encoding (VHT vs HE), and MIMO config. Result (Tab. 1):

| PHY | BW | # subcarriers | Memory indices (core, stream 0) |
|---|---|---|---|
| VHT/HT/legacy | 20 MHz | 64 | `[0,64)` |
| | 40 MHz | 128 | `[0,128)` |
| | 80 MHz | 256 | `[0,256)` |
| | 160 MHz | 512 | `[0,256)` **and** `[1024,1280)` (split!) |
| HE (11ax) | 20 MHz | 256 | `[0,256)` |
| | 40 MHz | 512 | `[0,512)` |
| | 80 MHz | 1024 | `[0,1024)` |
| | 160 MHz | 2048 | `[0,2048)` |

For spatial stream *k*, the table starts at offset **k · 2048**. A key insight: 160 MHz VHT CSI is **not contiguous** — the low and high 80 MHz halves land in separate memory ranges, revealing that the chip uses **two 80 MHz radios** rather than one 160 MHz radio (also useful for 80+80 configs).

#### Output format

CSI leaves the chip as **crafted UDP datagrams** (≤1500 B ⇒ ≤256 CSI values per datagram). One 80 MHz VHT stream fits in one datagram; a 160 MHz VHT stream needs two; **160 MHz VHT 4×4 → 32 datagrams; 160 MHz HE 4×4 → 128 datagrams**. You capture them on the host with any pcap tool and parse per the layout above.

#### Performance (the honest cost of moving work to ARM)

- **D11→ARM transfer latency ≈ 50 µs**; the "no-CSI, just send one UDP datagram" path ≈ **68 µs**; with CSI extraction the single-datagram case is **95 µs + 625 ns/subcarrier**.
- CSI throughput vs Nexmon CSI (VHT), extractions/second:

| Config | Nexmon CSI (11ac) | AX-CSI |
|---|---|---|
| VHT 80 MHz 1×1 (256 SC) | 8223 | 3348 |
| VHT 80 MHz 4×1 (1024 SC) | 3034 | 1101 |
| VHT 80 MHz 4×4 (4096 SC) | 168 | **295** |
| VHT 160 MHz 4×4 (8192 SC) | — (unsupported by default) | 148 |
| **HE 160 MHz 4×4 (32768 SC)** | — | **37** |

So AX-CSI is *slower per capture* on small frames (ARM path) but faster once the data volume is large, and it is the only one that does 160 MHz and HE at all.

#### Contrast with Nexmon CSI

AX-CSI **is** Nexmon lineage — same seemoo-lab binary-patching philosophy (`nexmon` framework, patched D11 ucode + firmware), extended from 802.11ac VHT to 802.11ax HE and from the 4365 to the 43684. Nexmon CSI cannot read HE frames or (by default) 160 MHz VHT; AX-CSI adds both. Both are for **Broadcom** parts — this is the crucial point the catalog previously got wrong. See [`../../projects/nexmon.md`](../../projects/nexmon.md).

#### How to get it / status

Distributed **by email** — send a short project description to `axcsi@unibs.it` to receive the archive (capture + conversion + instructions); project page <https://ans.unibs.it/projects/ax-csi/>. There is **no public GitHub repo**. It is pinned to the **Asus RT-AX86U / BCM43684**; the authors note plans to port to other 43684 devices. `status: verified` (paper + released-on-request tool). A separate 2023 effort (**"Collecting CSI in Wi-Fi Access Points for IoT Forensics,"** arXiv [2305.10554](https://arxiv.org/pdf/2305.10554)) also extracts HE CSI from the BCM43684 in the same Nexmon lineage.

> **Catalog corrections this establishes:** (a) `broadcom-bcm43684` is **not** a tier-0 black box — AX-CSI raises it to **tier 2 (CSI), patchable**; (b) the sibling files that describe "AX-CSI" as an **Intel** iwlwifi patch (e.g. `chips/intel.md`, `projects/csi-toolchains.md` §"AX-CSI / IAX", the "1992 subcarriers" figure) are mis-attributed and should be reconciled — the Intel HE-CSI tools are PicoScenes and FeitCSI, below.

---

### 3. The **Intel AX200/AX210** HE-CSI path — PicoScenes & FeitCSI

Intel's AX-series runs **closed, cryptographically signed `iwlwifi` microcode** — you *cannot* freely binary-patch it the way Nexmon patches Broadcom. Instead, both Intel tools ride a **channel-estimation / CSI reporting surface the firmware already has** (used internally for the equalizer/beamformer and, in later builds, exposed through an `iwlwifi` host command / debug path). The tooling is therefore: **a matched (patched or CSI-enabled) firmware blob + a modified `iwlwifi` driver + a userspace collector**, and reproducibility hinges on the *exact* firmware-driver-kernel triple.

#### Which Intel parts

| Part | Codename | Form | Bands | 11ax | Max BW | CSI tools |
|---|---|---|---|---|---|---|
| **AX200** | Cyclone Peak | discrete M.2 / mini-PCIe | 2.4/5 | ✓ | 160 MHz | PicoScenes, FeitCSI |
| **AX201** | Cyclone Peak | **CNVi** (soldered, 10th-gen+) | 2.4/5 | ✓ | 160 MHz | by extension (same ucode family) |
| **AX210** | Typhoon Peak | discrete M.2 | 2.4/5/**6** | ✓ (6E) | 160 MHz | PicoScenes, FeitCSI |
| **AX211** | Typhoon Peak | **CNVi** (12th-gen+) | 2.4/5/**6** | ✓ (6E) | 160 MHz | by extension |

All are 2×2. The headline AX210/AX211 capability is **CSI in the 6 GHz band (5945–7125 MHz)** — Intel's most capable sensing device today, still tier 2. These already exist in the catalog as `intel-ax200-ax201`, `intel-ax210-ax211`, `intel-ax210-csi`.

#### PicoScenes (Zhiping Jiang)

- **What:** a multi-NIC Wi-Fi sensing / ISAC middleware. Per its author, *"the first and currently the only publicly available platform that enables CSI extraction for 802.11ax-format frames using commodity Wi-Fi hardware."*
- **Supported NICs:** **IWL5300** (11n), **QCA9300** (Atheros AR9300 — arbitrary carrier tuning, 2.5–80 MHz), **AX200 / AX210** (11a/g/n/ac/**ax**, up to 160 MHz), plus **USRP / SoapySDR** front-ends (bridge to true SDR, [`../../docs/true-sdr-comparison.md`](../../docs/true-sdr-comparison.md)). On **AX210** it does 802.11ax CSI *and* packet injection in the **6 GHz** band.
- **Multi-NIC:** concurrent capture across many NICs (the author cites up to ~27), useful for distributed/ISAC setups.
- **Output:** a unified, **versioned-segment `.csi` container** (forward-compatible), parsed by the **PicoScenes MATLAB Toolbox (PMT)** and third-party parsers. Rich per-frame metadata.
- **Distribution:** **binary** `.deb`, `apt`-installable and auto-updated; **Ubuntu 22.04** officially supported (as of 2024). Free for academic use, **not open source**.
- **Papers:** Z. Jiang et al., *"Eliminating the Barriers: Demystifying Wi-Fi Baseband Design and Introducing the PicoScenes Wi-Fi Sensing Platform,"* **IEEE Internet of Things Journal** 9(6), 2022, DOI [10.1109/JIOT.2021.3104666](https://doi.org/10.1109/JIOT.2021.3104666) (arXiv [2010.10233](https://arxiv.org/pdf/2010.10233)); newer IEEE Communications-Magazine work *"Reshaping Wi-Fi ISAC with High-Coherence Hardware Capabilities."*
- **URL:** <https://ps.zpj.io/> · see also [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) and the project note `projects/picoscenes.md`.

#### FeitCSI (KuskoSoft, Miroslav Hutar)

- **What:** turn-key **open (GPL)** CLI+GUI tool that does **CSI extraction *and* arbitrary 802.11 frame injection** for 11a/g/n/ac/ax at **20/40/80/160 MHz**, including **6 GHz** when the NIC supports it (AX210). Ships a **live USB** and a patched `iwlwifi` + firmware.
- **Resolution:** up to **512 subcarriers at 16-bit signed** real/imag.
- **Chips:** AX200 / AX210 (AX201/AX211 by extension); architecture-portable (x86-64 + ARM).
- **URL:** <https://github.com/KuskoSoft/FeitCSI> · <https://feitcsi.kuskosoft.com/>. `status: verified`.

#### Contrast with nexmon_csi and the 5300 tool

| | 5300 tool | nexmon_csi | AX-CSI | PicoScenes / FeitCSI |
|---|---|---|---|---|
| Vendor | Intel | Broadcom | **Broadcom** | **Intel** |
| Standard | 11n | 11ac (VHT) | **11ax (HE)** | 11a/g/n/ac/**ax** |
| Max BW | 40 MHz | 80 MHz | **160 MHz** | 160 MHz |
| MIMO | up to 3×3 | up to 4×4 | **4×4** | 2×2 (NIC-limited) |
| Resolution | 30 groups, 8-bit | per-SC | **per-SC, ≤32768/frame** | per-SC, ≤512 SC / `.csi` |
| 6 GHz | ✗ | ✗ | ✗ | ✓ (AX210) |
| Firmware | patched `iwl-5000` ucode | patched D11 ucode | **patched D11 + Wi-Fi OS** | signed ucode + patched `iwlwifi` |
| Openness | open driver / patched fw | open (nexmon) | tool on request | PicoScenes binary; FeitCSI GPL |
| Tier | 2 | 2 | **2** | 2 |

**Key architectural difference:** Broadcom tools (nexmon_csi, AX-CSI) **binary-patch the chip's own firmware** because Broadcom ucode is patchable; Intel tools **cannot** patch signed ucode and instead **coax CSI out of a vendor debug/host-command path** with a matched firmware blob + driver. That is exactly why the Intel path is so sensitive to version pinning (§5).

---

### 4. Reproducible walkthrough (Intel AX200/AX210)

> These steps capture **received** CSI passively and, optionally, **inject** frames. Read §6 before transmitting.

**Hardware:** an **Intel AX200** (M.2/mini-PCIe, cheapest) or **AX210** (adds 6 GHz). CNVi AX201/AX211 are soldered to the mainboard and harder to isolate — prefer a discrete AX200/AX210 in an M.2 slot or USB-M.2 enclosure.

**Option A — FeitCSI (open, quickest):**

```bash
# Easiest: boot the FeitCSI live USB (ships the patched iwlwifi + firmware).
# Or install on a supported distro/kernel per the docs:
#   https://feitcsi.kuskosoft.com/
# Then, GUI or CLI, e.g. capture 80 MHz HE CSI on channel 36:
feitcsi -f 5180 -w 80 -o capture.csi        # frequency (MHz), width (MHz), output
# Injection is a separate, deliberate mode — see the tool's TX options and §6.
```

**Option B — PicoScenes (multi-NIC, research):**

```bash
# Ubuntu 22.04, supported kernel. Add the PicoScenes apt repo per https://ps.zpj.io/
sudo apt update && sudo apt install picoscenes
# Put the AX200/AX210 into PicoScenes' monitor/CSI mode and log:
array_status                                  # list PicoScenes-recognised NICs
PicoScenes "-d debug; -i <phyId>; --mode logger; --channel 36 --bw 160HE; --output run1"
# Parse run1.csi with the PicoScenes MATLAB Toolbox (PMT) or the Python parser.
```

Then parse with the **universal Python route** — **CSIKit** auto-detects Atheros, Intel (IWL5300/AX200/AX210), Nexmon, ESP32, **FeitCSI**, and **PicoScenes** formats: <https://github.com/Gi-z/CSIKit> (see [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md)).

---

### 5. Honest reproducibility state — version pinning is the real difficulty

This is the part every "successor to the 5300 tool" glosses over:

- **Intel ucode is signed.** You are not patching arbitrary logic; you depend on a **firmware image that contains a working CSI/channel-estimate reporting path** plus a **driver that knows how to request and demux it**. Swap either and CSI silently stops.
- **Kernel ↔ driver ↔ firmware must match.** FeitCSI ships a **specific patched `iwlwifi` + firmware** (and a live USB precisely so you don't have to fight your own kernel). PicoScenes ships **prebuilt kernel modules** targeted at specific Ubuntu kernels and is `apt`-pinned to **Ubuntu 22.04**. Running your distro's newer HWE kernel is the most common reason capture breaks. **Pin the kernel**, or use the vendor's live image / container.
- **NIC hardware revision matters.** Not every AX200/AX210 board revision behaves identically; CNVi AX201/AX211 support is "by extension" and less exercised than discrete AX200/AX210.
- **6 GHz is regulatory-gated.** AX210 6 GHz CSI/injection depends on the regdomain the firmware enforces; capability is real but availability is region-dependent.
- **Openness verdict:** AX-series firmware is `closed`/signed; the CSI surface is a vendor debug hook, so for catalog purposes Intel CSI is treated as **`patchable` (tier 2)**, never open. PicoScenes itself is **closed-source** (free academic binary); FeitCSI is **GPL**. AX-CSI (Broadcom) is nexmon-patched ucode, tool released on request.
- **Wi-Fi 7 (BE200, 320 MHz):** no verified 802.11be CSI capture yet — FeitCSI authors note "high possibility" the newest Intel NIC works; treat as `reported`/emerging (see [`../../chips/intel.md`](../../chips/intel.md)).

---

### 6. Safety & legal notes (injection / TX)

Both the Intel tools (FeitCSI/PicoScenes injection) and the AX-CSI experiments involve **transmitting** — including the paper's SDR method for synthesising 160 MHz HE frames from two synchronised **USRP N300** (or four N210, 1×1) radios split at the 80 MHz boundary via MATLAB WLAN Toolbox FFT/IFFT. Before any TX:

- **Transmit only on bands/channels you are licensed to use**, at legal EIRP, in your regdomain (2.4/5/6 GHz rules differ; **6 GHz has power/indoor restrictions**). CSI *capture* is passive and low-risk; **frame injection and SDR TX are active emissions** you are responsible for.
- **Cable + attenuator on the bench.** The paper's controlled experiments feed the AP over **coax**, not over the air, precisely to keep emissions contained and repeatable — do the same for calibration.
- Do not inject onto networks you don't own/administer. See [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md).

---

### 7. References (primary)

- **AX-CSI paper (Broadcom BCM43684):** Gringoli, Cominelli, Blanco, Widmer, WiNTECH'21. DOI <https://doi.org/10.1145/3477086.3480833> · PDF <https://ans.unibs.it/assets/documents/axcsi.pdf> · project <https://ans.unibs.it/projects/ax-csi/>
- **Nexmon CSI (802.11ac predecessor):** Gringoli, Schulz, Link, Hollick, *"Free Your CSI,"* WiNTECH'19, DOI <https://doi.org/10.1145/3349623.3355477> · <https://github.com/seemoo-lab/nexmon_csi>
- **BCM43684 AP CSI (IoT forensics, 2023):** arXiv <https://arxiv.org/pdf/2305.10554>
- **PicoScenes:** Jiang et al., IEEE IoT Journal 2022, DOI <https://doi.org/10.1109/JIOT.2021.3104666> · arXiv <https://arxiv.org/pdf/2010.10233> · <https://ps.zpj.io/>
- **FeitCSI:** <https://github.com/KuskoSoft/FeitCSI> · <https://feitcsi.kuskosoft.com/>
- **IWL5300 tool (the ancestor):** Halperin, Hu, Sheth, Wetherall, 2011, DOI <https://doi.org/10.1145/1925861.1925870> — walkthrough [`../../docs/walkthroughs/intel-5300-csi.md`](../../docs/walkthroughs/intel-5300-csi.md)
- **CSIKit universal parser:** <https://github.com/Gi-z/CSIKit>

### 8. See also (this catalog)

- [`../../chips/intel.md`](../../chips/intel.md) — Intel vendor page; the AX200/AX201/AX210/AX211 records and the tier-2 ceiling.
- [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) — the full CSI-tool comparison (reconcile the mis-attributed "AX-CSI / IAX = Intel" rows against this page).
- [`../../docs/walkthroughs/intel-5300-csi.md`](../../docs/walkthroughs/intel-5300-csi.md) — the 802.11n tool this modern HE work supersedes.
