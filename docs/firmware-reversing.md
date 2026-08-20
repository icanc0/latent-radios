# Firmware Reversing: Turning the Blob Back Into Code

Every rung of the [SDR ladder](./taxonomy.md) above monitor mode is unlocked by the
same act: taking the opaque firmware blob a wireless NIC runs, turning it back into
something you can read, understand, and change, and then getting your modified version
back onto the silicon. This document is the practical, end-to-end methodology for doing
that. It is deliberately vendor-broad — the same six-step loop applies whether you are
patching a Broadcom D11 microengine, an ESP32 Xtensa core, or an Atheros Tensilica MAC —
but the concrete examples lean on the chips that the rest of this catalog covers in
depth: see [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md),
[../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md),
[../chips/intel.md](../chips/intel.md), [../chips/espressif.md](../chips/espressif.md),
and the flagship tooling in [../projects/nexmon.md](../projects/nexmon.md).

**The loop, in one sentence:** *obtain the blob → identify the architecture → load it into
the right disassembler → find the interesting datapath → patch and reflash → recover if
you brick it.* Everything below is a section per step. Terms in `monospace` that you do
not recognize are defined in [glossary.md](./glossary.md).

---

## 0. The mental model — where does the firmware even run?

A modern Wi-Fi NIC is not one processor. It is usually **at least two**:

1. A **general-purpose control CPU** — an ARM Cortex-M/R (Broadcom "dongle" firmware),
   Xtensa (ESP32/ESP8266, Atheros HTC), or a small RISC-V (ESP32-C/H). It runs the
   host-interface state machine, ioctl handlers, the association/auth logic, calibration,
   and power management. This is the core that `strings` and Ghidra love, because it is
   compiled C with recognizable structure.

2. A **real-time MAC/PHY microengine** — a tiny, weird, often-undocumented core that
   sits on the hot path between the DMA rings and the baseband. On Broadcom this is the
   famous **"D11" ucode**: a custom 16-bit-ish Harvard-architecture MAC microcontroller
   that the ARM copies into a dedicated code RAM at boot. On Atheros HTC parts the MAC is
   folded into the same Xtensa image. This core is where CSI, spectral scan, ACK timing,
   and TX scheduling actually live — and it is the hardest to reverse.

Climbing the ladder maps directly onto which core you touch:

| Ladder rung | Capability | Which core you patch |
|---|---|---|
| 1 | monitor + injection | Control CPU (ioctl + RX/TX frame path) |
| 2 | CSI (per-subcarrier amplitude+phase) | MAC microengine reporting path (D11 / PHY regs) |
| 3 | spectral / raw-PHY FFT scan | PHY register block + FFT report DMA |
| 4 | arbitrary waveform TX | Template RAM + transmit-vector path |
| 5 | open PHY / soft-radio | Whole image is documented or replaced |

Knowing *which* processor owns the feature you want tells you *which* blob to load and
*which* toolchain to reach for. Get this wrong and you will spend a day disassembling an
ARM image looking for a datapath that lives in a 4 KB microcode RAM you never extracted.

---

## 1. Obtaining the firmware blob

You cannot reverse what you do not have. Sources, roughly in order of convenience:

### 1a. `linux-firmware.git` — the first stop
The canonical upstream tree of redistributable vendor blobs. Clone it and browse:

```
git clone https://gitlab.com/kernel-firmware/linux-firmware.git
ls linux-firmware/brcm/        # brcmfmac*.bin, *.clm_blob, *.txt (nvram)
ls linux-firmware/cypress/     # newer Cypress-signed variants of the same parts
ls linux-firmware/iwlwifi-*    # iwlwifi-<family>-NN.ucode
ls linux-firmware/mediatek/    # mt76 / mt79 firmware
ls linux-firmware/ath9k_htc/   # htc_9271.fw, htc_7010.fw
ls linux-firmware/ath10k/ ath11k/ ath12k/
```

- **Broadcom / Cypress (`brcmfmac`)** — the SDIO/USB "FullMAC" dongle firmware is
  `brcmfmac<chip>-<bus>.bin` (e.g. `brcmfmac43455-sdio.bin` for the Raspberry Pi 3B+/4,
  `brcmfmac4339-sdio.bin` for the Nexus 5). Two companion files matter: the `.clm_blob`
  (Country Locale Matrix — regulatory power tables) and a board-specific `nvram`/`.txt`.
  The **PCIe** "SoftMAC-ish" parts (BCM4360/4366) instead pull `brcmfmac<chip>-pcie.bin`.
  The `cypress/` directory holds newer, differently-signed builds of overlapping parts —
  always diff both. See [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md).
- **Intel (`iwlwifi`)** — `iwlwifi-<family>-NN.ucode`, where `NN` is the API version. The
  last builds for 7260/7265 are `-17.ucode`; 7265D/3165/3168 go to `-29.ucode`; AX2xx go
  much higher. The `.ucode` is a **TLV container** (Tag-Length-Value) parsed by
  `iwl-drv.c` — inside are separate INIT and RUNTIME code+data sections, plus PAGING,
  debug, and calibration TLVs. See [../chips/intel.md](../chips/intel.md).
- **MediaTek (`mt76`)** — split into RA/WM/WA role images (e.g.
  `mt7921_ram_code.bin`, `WIFI_MT7961_patch_mcu_1_2_hdr.bin`). MediaTek is unusual in
  shipping ROM-patch overlays plus RAM images. See
  [../chips/mediatek-ralink.md](../chips/mediatek-ralink.md).
- **Atheros HTC (`ath9k_htc`)** — `htc_9271.fw` (AR9271) and `htc_7010.fw` (AR7010).
  These are the *only* mainstream Wi-Fi NICs whose firmware ships with **full source** —
  see §7.

### 1b. Vendor driver packages and BSPs
When `linux-firmware` lags reality (common for phones, IoT SoCs, and just-released
parts), go to the vendor: Broadcom/Cypress "WICED"/"FMAC" BSP tarballs, MediaTek and
Realtek GitHub driver mirrors (which frequently bundle `.bin` firmware next to the `.ko`
source), Qualcomm CodeAurora / `ath1?k` firmware repos, and Espressif's `esp-idf` (whose
blob "libnet80211"/"libpp" archives contain the closed PHY code). Android vendor images
(`vendor.img`, `/vendor/firmware/`, `/vendor/etc/wifi/`) are a rich source of
device-specific builds you will not find upstream.

### 1c. Pulling from Android / device images
For a phone or tablet chip:
```
# from an unpacked factory image or a rooted device
find . -iname 'bcmdhd*' -o -iname 'brcmfmac*' -o -iname '*.ucode' -o -iname 'fw_*.bin'
# common Android Broadcom paths:
#   /vendor/firmware/bcmdhd_sta.bin  (bcmdhd fullmac driver)
#   /system/vendor/firmware/fw_bcmdhd.bin
```
`bcmdhd` is Broadcom's Android driver; its firmware is the same D11+ARM structure as
`brcmfmac`, just a device-tuned build. Use `simg2img`/`payload-dumper-go` to unpack
sparse/OTA images first.

### 1d. Hardware extraction — when there is no file to download
Some parts (especially self-contained modules and dev boards) run firmware from an
on-package or on-board store rather than host-loaded blobs:

- **External SPI/QSPI NOR flash** (ESP32 boards, many routers): clip a **SOIC-8 test
  clip** onto the flash chip and read it with a `CH341A` or `flashrom`-supported
  programmer, or dump in-system over the SoC's own UART bootloader
  (`esptool.py read_flash 0 0x400000 flash.bin` for ESP32). This is the easiest hardware
  dump in the whole field.
- **NAND flash**: needs a NAND-aware reader and ECC/OOB handling; `nanddump` on-device if
  you have a root shell is far less painful than desoldering.
- **OTP / one-time-programmable fuses and boot ROM**: sometimes only reachable through a
  vendor JTAG/SWD interface or a debug mailbox. Broadcom parts keep a small boot ROM that
  the ARM runs before the host pushes the `.bin`; dumping it usually means a Nexmon patch
  that `memcpy`s the ROM out over an ioctl (see §4/§5).
- **Live RAM readout**: the most reliable "extraction" for a host-loaded NIC is to let
  the driver load the blob normally, then read it back out of the chip's code RAM through
  a debug path — this captures the *actually-running, relocated* image including any
  ROM-patch merge. Nexmon's `nex` utility and the `wintech23_nexmon_d11debug` patch do
  exactly this for the D11 ucode.

---

## 2. Identifying the core architecture

You have a blob. Before any disassembler, **fingerprint it.**

### 2a. `binwalk`, `strings`, entropy
```
binwalk firmware.bin              # signatures: LZMA, gzip, ELF, headers, ARM code
binwalk -E firmware.bin           # entropy plot: flat ~1.0 = compressed/encrypted,
                                  #   stepped = code+data mix, spikes = tables/keys
strings -n 8 firmware.bin | less  # version banners, chip revs, symbol/format strings
```
`strings` is the highest-value first move. Broadcom images leak strings like
`wl%d: ` printf formats, `PHYVERSION`, `d11ucode`, and file-and-line assertion strings
that name the *original source files* (`wlc_phy_n.c`, `phy_ac_...`) — free ground truth
about the code layout. iwlwifi TLV images leak `TLV_FW_*` tags and a build tag. ESP32
images leak `esp-idf` versions and function names in the `.debug`-ish sections.

An entropy plot that is **flat and high across the whole file** means the payload is
compressed or encrypted — you must find and run the unpacker (or dump post-decompression
from RAM, §1d) before disassembly is meaningful. A **stepped** profile is the friendly
case: low-entropy header, medium-entropy code, high-entropy tables.

### 2b. The architecture cheat-sheet

| Vendor / part | Control CPU | Real-time MAC/PHY core | Tell-tale signs |
|---|---|---|---|
| Broadcom/Cypress dongle (BCM43xx, BCM4339/43455/4358/4366) | ARM Cortex-M3/R4 (Thumb-2) | **D11 ucode** (custom 16-bit MAC microengine) | Thumb vector table at 0; separate ucode blob copied to code RAM; `wlc_` strings |
| Intel (7260…AX210) | ARC / Intel LMAC+UMAC on Tensilica-like cores | on-die MAC | TLV container, `iwl-*` strings, INIT/RUNTIME split |
| Atheros AR9271/AR7010 (HTC USB) | **Xtensa** (Tensilica) | same core | `htc_*.fw`, eCos, FUSB200 USB strings |
| Atheros AR9170 (carl9170) | Xtensa (Tensilica) | same core | small RAM image, USB |
| MediaTek mt76 | ARM (Andes/xtensa varies) + MCU roles | on-die | RA/WM/WA role split, ROM-patch overlays |
| Espressif ESP32 / ESP32-S | **Xtensa LX6/LX7** (dual-core) | closed PHY lib | `Xtensa:LE:32`, `esp-idf`, ELF-ish app image |
| Espressif ESP32-C/H/P | **RISC-V** (RV32IMC) | closed PHY lib | RISC-V opcodes, `esp-idf` |
| Realtek RTL8188/8812 | 8051-class "FW" MCU + hardware MAC | hardware MAC | tiny 8051 fw, most logic in hardware/driver |

The single most important identification fact for this catalog: **Broadcom's D11 is not
ARM.** If you throw the whole `brcmfmac*.bin` at Ghidra as ARM you will correctly
decompile the dongle firmware and completely miss the microengine — the D11 ucode is a
*separate region* the ARM relocates at runtime, and it needs the **b43 disassembler**,
not Ghidra (§3d).

### 2c. Locating the ucode inside a Broadcom image
The D11 ucode is embedded in the ARM `.bin`. The community approach (see the
`b43-tools` PR that added a `bcm43438` prep script) is: find the ucode region by its
characteristic structure/relocation, carve it out, byte-swap if needed, and hand the raw
region to `b43-dasm`. Nexmon automates this — after a build the *actually-assembled*
microcode lands at `gen/ucode.bin`, and the `d11-emu` project can even execute a carved
ucode in an emulator for analysis.

---

## 3. Tooling

### 3a. Ghidra — the free workhorse
Best for the **control CPU** (ARM/Thumb, Xtensa, RISC-V). Workflow:
1. **Import** with the correct language spec. ARM Broadcom dongle: `ARM:LE:32:Cortex`
   (Thumb). ESP32: `Xtensa:LE:32:default` — **native since Ghidra 11.0**; on older Ghidra
   install a SLEIGH module (`Ebiroll/ghidra-xtensa` or `yath/ghidra-xtensa`). ESP32-C/H:
   `RISCV:LE:32:RV32IC`.
2. **Set the load/base address** correctly — wireless firmware is not PIC and absolute
   pointers only resolve if the image is based where the chip maps it. Wrong base = a sea
   of undefined references. Recover the base from the reset/vector table, from absolute
   branch targets, or from the driver source's `RAMBASE`/`TCM` constants.
3. **Bootstrap symbols from strings.** The assertion strings (§2a) carry `file:line`;
   the printf format strings anchor logging functions. Rename outward from there.
4. **FIDBs / FLIRT.** For ESP32, build a Ghidra FID database from a matching `esp-idf`
   toolchain build to auto-name library functions (Tarlogic published a walk-through of
   exactly this). Enormous time-saver against statically-linked SDK code.

### 3b. IDA Pro
The commercial counterpart; Nexmon's own reverse-engineering workflow is documented
around **IDA** plus custom loaders and scripts. IDA's Thumb handling and its ability to
script the D11/PHY register annotations are why the SEEMOO group historically used it.
Either IDA or Ghidra is fine for the ARM side; pick what you own.

### 3c. radare2 / rizin
Scriptable, headless, great for batch triage, entropy, and quick `strings`/xref work in
CI. Rizin's Cutter GUI is a reasonable free IDA-alike. Weaker than Ghidra's decompiler on
the exotic cores, but excellent glue.

### 3d. The b43 / b43-tools D11 assembler+disassembler — the *only* way into the ucode
`b43-tools` (Michael Büsch; mirror at `pfalcon/b43-tools`, upstream
`git://git.bues.ch/b43-tools.git`) is the toolchain that made open Broadcom firmware
possible in the first place. It contains:
- **`b43-dasm`** — disassembler for the D11 microengine ISA.
- **`b43-asm`** — assembler, so you can round-trip: disassemble → edit → reassemble.
- **`b43-fwcutter`** — historically carves the ucode out of the proprietary driver blob.
- **`ssb_sprom`** — SPROM/EEPROM helper.

This is the tool that decodes the custom MAC microengine that Ghidra cannot. OpenFWWF and
every CSI/spectral trick that touches the D11 stands on it.

### 3e. Nexmon — the integration layer
[Nexmon](../projects/nexmon.md) (`seemoo-lab/nexmon`) is a **C-based firmware patching
framework** for Broadcom/Cypress that ties the whole loop together: it wraps IDA-derived
symbol maps, lets you write patches in C that link against the reverse-engineered
firmware symbols, drives `b43-asm` for the ucode side, and produces a flashable image
plus a `nex` host utility for the new ioctls. Companion repos:
`nexmon_csi` (CSI on BCM4339/43455c0/4358/4366c0), `nexmon_tx_task` (scheduled TX),
`wintech23_nexmon_d11debug` (D11 state extraction), and `d11-emu` (D11 emulator). Community
forks `Re4son/re4son-nexmon` and `kimocoder/nexmon` track newer kernels and chips. Nexmon
is the reference implementation of *everything in this document* for Broadcom — read
[../projects/nexmon.md](../projects/nexmon.md) alongside this file.

---

## 4. Finding the interesting bits — the datapath map

Once you can read the code, the climb is about locating specific datapaths. What to hunt
for, and which rung it unlocks:

- **RX/TX DMA rings (rung 1).** Descriptor-ring setup and the RX completion handler are
  where frames enter software. Find them and you can strip the hardware filter, forward
  every frame with a radiotap header (monitor), and craft outbound frames (injection).
  On Broadcom, search for the ring-init that writes the DMA base registers and the RX
  handler that the ucode signals; Nexmon's monitor-mode patch lives here.
- **PHY register writes (rungs 2–4).** The PHY is a memory-mapped register block the MAC
  pokes. Sequences of `phy_reg_write(addr, val)` are your map of the baseband. The
  register *names* often survive in assertion strings (`wlc_phy_*`). Controlling these is
  how you force spectral-scan mode, change gain, or hold the radio in a raw state.
- **The FFT / CSI datapath (rungs 2–3).** The baseband already computes an FFT for every
  received OFDM symbol — CSI *is* the equalizer's per-subcarrier channel estimate.
  Extraction means finding where the MAC microengine stashes those complex values and
  redirecting/copying them into a buffer you can DMA to the host. On Broadcom this is a
  D11-side change (hence `b43-asm` + Nexmon); the report format differs by chip (int16
  real/imag on BCM4339/43455c0, float on BCM4358/4366c0). Spectral scan is the same FFT
  hardware told to report bins **whether or not a frame is present** — on Atheros this is
  a documented `spectral_scan` sysfs knob; on Broadcom it is a firmware patch.
- **Template RAM + the transmit-vector path (rung 4 — arbitrary TX).** This is the top of
  the practically-reachable ladder. **Template RAM** is an on-chip buffer the transmitter
  normally uses for ACK/CTS templates; Nexmon SDR repurposes it to hold **raw IQ samples**.
  The two ioctls that define the technique: `NEX_WRITE_TEMPLATE_RAM` (426) writes an
  arbitrary IQ buffer into Template RAM, and `NEX_SDR_START_TRANSMISSION` (427) fires it —
  taking sample count, Template-RAM offset, channel, power index, and a loop flag. Finding
  the transmit-vector setup (the code that arms the PHY to emit whatever is in Template
  RAM instead of a normal frame) is what converts a Wi-Fi chip into a TX-capable SDR and
  enables reactive jammers and covert channels (Schulz et al., *Shadow Wi-Fi*; the
  `mobisys2018_nexmon_software_defined_radio` release).
- **ioctl / host-command dispatch (glue for all rungs).** The dispatch table that maps a
  host command number to a handler is where you *add* your own commands. Find it once and
  every new capability gets an entry point.

A pragmatic ordering: get monitor/injection working first (proves your obtain→patch→flash
loop end-to-end on the cheap ARM side), then move up into the PHY/D11 for CSI, spectral,
and finally arbitrary TX.

---

## 5. Patching and reflashing safely (and un-bricking)

### 5a. RAM-loaded parts are your safety net
Most Wi-Fi NICs — all host-loaded Broadcom `brcmfmac`/`bcmdhd`, all iwlwifi, ath9k_htc,
mt76 — run firmware from **RAM that the driver reloads on every probe.** This is the
single most reassuring fact in the field: a bad patch that hangs the chip is fixed by
`rmmod`/`modprobe` (or a USB replug), because the *stored* blob on disk is untouched.
Keep a pristine copy of the original `.bin`/`.ucode` next to your patched one and you can
always revert by copying it back into `/lib/firmware`. **Nexmon patches are RAM patches —
you are not burning anything.**

### 5b. The patch workflow (Broadcom / Nexmon shape)
1. Work against a specific `chip + firmware version` (e.g. `bcm43455c0/7_45_189`) — the
   symbol offsets are version-exact and a patch for one build will land in the wrong place
   on another.
2. Write the C patch against the reversed symbols; write any ucode change in D11 asm.
3. `make` — Nexmon assembles the ucode (`gen/ucode.bin`), compiles and links your C,
   applies the relocations/hooks, and emits a flashable `.bin`.
4. Deploy: replace the file in `/lib/firmware/brcm/`, reload the driver, load the new
   ioctls with the `nex` utility.
5. Verify on a **known-good, cheap target first** — a Raspberry Pi (BCM43430/43455) or a
   spare USB NIC — never your daily-driver laptop's soldered card.

### 5c. When the store *is* writable — real bricking, real recovery
Parts that boot from **on-board SPI flash or OTP** (ESP32 boards, some routers, PCIe
cards with a flash EEPROM) *can* be bricked, and here you plan recovery **before** you
flash:
- **Keep the golden image.** Full-chip read (`esptool.py read_flash`, `flashrom -r`)
  before your first write, stored off-device.
- **Know the ROM bootloader escape.** ESP32 always boots its mask-ROM serial loader when
  `GPIO0` is held low at reset — an unbrickable recovery path: `esptool.py write_flash`
  reflashes the golden image over UART no matter how dead the app firmware is.
- **Have a hardware programmer for the flash chip.** A SOIC-8 clip + CH341A reflashes a
  NOR chip in-circuit (or desoldered) when there is no serial escape.
- **Watch for signature enforcement.** Newer parts (recent iwlwifi, signed Cypress
  builds, secure-boot ESP32) refuse or fault on an unsigned/mismatched image. If the boot
  ROM verifies a signature you cannot forge, RAM-patching the *post-verification* running
  image (§1d) is the only route, and reflashing the store is off the table.
- **`.clm_blob` / regulatory:** editing power/regulatory tables can push the radio out of
  legal limits and, on some parts, trip a firmware safety check that halts TX. Keep tests
  in a shielded enclosure; do not radiate patched power tables over the air.

---

## 6. The open-firmware efforts — where the whole PHY is yours (rung 5)

For a handful of chips you can skip reverse engineering entirely because someone
published (or the vendor released) real source. These are the gold standard the ladder's
top rung points at:

- **OpenFWWF** (Open FirmWare for WiFi, University of Brescia) — open **D11 ucode** for
  older Broadcom b43 parts (tested on BCM4306 and BCM4318 chipset revisions). Built with
  the b43 assembler; the project explicitly credits the b43 community's `b43-asm`/`b43-dasm`
  as the enabling tools. It is the proof-of-concept that the MAC microengine can be a
  fully open, hackable MAC — the ancestor of every "custom MAC mechanism" experiment.
- **open-ath9k-htc-firmware** (`qca/open-ath9k-htc-firmware`) — Qualcomm Atheros
  **released the full source** for the AR9271/AR7010 (ath9k_htc USB) firmware. It builds
  with an Xtensa toolchain; QCA code is ClearBSD, the Tensilica xtos bits MIT, a few eCos
  files GPLv2. This is the *only* mainstream Wi-Fi NIC where the shipping firmware is
  literally open source — which is exactly why the AR9271 is the canonical hackable Wi-Fi
  dongle. Forks like `vanhoefm/modwifi-ath9k-htc` add injection/reactive-jamming
  primitives on top.
- **carl9170 firmware** (`pkgadd/firmware-carl9170`, source lineage from the carl9170
  project) — open firmware for the Atheros **AR9170** USB parts, again Xtensa. Same story
  as ath9k_htc: an open image means you edit C and rebuild rather than patch a blob.

If your goal tolerates older silicon, **start here** — an AR9271 with modwifi or an
AR9170 with carl9170 gives you a documented MAC and a rebuild loop in an afternoon, versus
weeks of reversing a modern Broadcom part. See
[../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md).

---

## 7. Putting it together — a worked decision tree

```
Do you want a capability that already exists as open firmware?
  └─ yes → AR9271/AR7010 (open-ath9k-htc-firmware) or AR9170 (carl9170): edit C, rebuild. DONE.
  └─ no  → is your target a Broadcom/Cypress part?
             └─ yes → is there a Nexmon patch for your exact chip+fwver?
                        └─ yes → build on Nexmon (monitor/inject/CSI/spectral/TX). ../projects/nexmon.md
                        └─ no  → obtain brcmfmac*.bin → carve D11 with b43-tools,
                                 reverse ARM with Ghidra/IDA → port a Nexmon patch.
             └─ no  → ESP32 family? → esptool dump → Ghidra (Xtensa/RISC-V) → esp-idf FIDB.
                      Intel? → linux-firmware .ucode → parse TLV → ARC/Tensilica reverse (hard, signed).
                      MediaTek? → mt76 role images → ARM reverse; watch ROM-patch overlays.
```

## 8. Summary of the toolchain

| Job | Tool | Notes |
|---|---|---|
| Get the blob | `linux-firmware.git`, vendor BSPs, `esptool read_flash`, `flashrom`+CH341A, Android `/vendor/firmware` | RAM-loaded parts = grab the `.bin`; module parts = dump the flash |
| Fingerprint | `binwalk`, `binwalk -E`, `strings` | entropy tells you if it is packed; strings leak arch + source filenames |
| Reverse control CPU | **Ghidra** (ARM/Xtensa/RISC-V), **IDA Pro**, rizin/Cutter | Ghidra 11+ has native Xtensa; ESP32 FIDB from esp-idf |
| Reverse the D11 MAC ucode | **b43-tools** (`b43-dasm`/`b43-asm`), `d11-emu` | the *only* disassembler for the microengine |
| Integrate patch + reflash | **Nexmon** (+ `nex`, `nexmon_csi`, `nexmon_tx_task`) | C patches against reversed symbols; RAM-flash = un-brickable |
| Open reference firmware | OpenFWWF, open-ath9k-htc-firmware, carl9170 | source you can just read and rebuild |

---

### References
- Nexmon framework — https://github.com/seemoo-lab/nexmon
- nexmon_csi — https://github.com/seemoo-lab/nexmon_csi
- Nexmon SDR (arbitrary TX, MobiSys 2018) — https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio
- nexmon_tx_task — https://github.com/seemoo-lab/nexmon_tx_task
- wintech23 D11 debug — https://github.com/seemoo-lab/wintech23_nexmon_d11debug
- d11-emu (D11 emulator) — https://github.com/seemoo-lab/d11-emu
- Nexmon SDR write-up — https://www.rtl-sdr.com/nexmon-sdr-turning-a-broadcom-802-11ac-wifi-chip-into-a-tx-capable-software-defined-radio/
- b43-tools (D11 asm/dasm) — https://github.com/pfalcon/b43-tools · upstream `git://git.bues.ch/b43-tools.git`
- b43-tools bcm43438 ucode prep PR — https://github.com/mbuesch/b43-tools/pull/4
- OpenFWWF background — https://www.linux-magazine.com/Online/News/Free-Firmware-for-Broadcom-WiFi-Chips · https://lwn.net/Articles/314313/
- open-ath9k-htc-firmware — https://github.com/qca/open-ath9k-htc-firmware
- modwifi (ath9k_htc injection) — https://github.com/vanhoefm/modwifi-ath9k-htc
- carl9170 firmware (AR9170) — https://github.com/pkgadd/firmware-carl9170
- linux-firmware — https://gitlab.com/kernel-firmware/linux-firmware
- brcm80211 driver / firmware — https://wireless.wiki.kernel.org/en/users/drivers/brcm80211
- iwlwifi driver docs — https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html
- Ghidra Xtensa module — https://github.com/Ebiroll/ghidra-xtensa · https://deepwiki.com/yath/ghidra-xtensa
- ESP32 flash dumps in Ghidra/IDA — https://olof-astrand.medium.com/reverse-engineering-of-esp32-flash-dumps-with-ghidra-or-ida-pro-8c7c58871e68
- ESP32 firmware FIDB in Ghidra (Tarlogic) — https://www.tarlogic.com/blog/esp32-firmware-using-ghidra-fidb/
- Matthias Schulz (Shadow Wi-Fi, covert channels) — https://scholar.google.com/citations?user=w9ahvT8AAAAJ

*Related in this catalog:* [../projects/nexmon.md](../projects/nexmon.md) ·
[../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) ·
[../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) ·
[../chips/espressif.md](../chips/espressif.md) · [./glossary.md](./glossary.md) ·
[./techniques.md](./techniques.md) · [./taxonomy.md](./taxonomy.md)

## Un-cataloged / TODO
- **Signed-firmware bypass matrix** — which families (recent iwlwifi, signed Cypress,
  secure-boot ESP32-S3) enforce signatures at boot ROM vs. loader, and which allow
  post-verification RAM patching. Needs per-part confirmation.
- **MediaTek mt76 ROM-patch overlay format** — document the patch/RAM split and whether
  the on-die MCU is Andes vs. Xtensa per generation; no clean disassembler workflow yet.
- **Realtek 8051 firmware** — RTL8188/8812 MCU images are tiny but the interesting logic
  is in hardware + driver; map what is actually reversible on the firmware side.
- **Qualcomm ath10k/ath11k/ath12k WCN firmware** — closed, signed, Hexagon/Q6 DSP-adjacent;
  entry points for CSI (802.11-mc FTM) exist but firmware RE status is thin.
- **Broadcom PCIe FullMAC (BCM4360/4366) ucode carving** — confirm the exact carve offsets
  and whether `d11-emu` runs these newer ucode revisions.
- **OTP/boot-ROM dumping recipes** per Broadcom chip — the `memcpy`-over-ioctl trick needs
  a per-chip ROM base/size table.
- **Nexmon chip/version support matrix** — a maintained table of which `chip/fwver` pairs
  have working monitor/CSI/TX patches across seemoo, Re4son, and kimocoder forks.
