# Setting up Ghidra to reverse Wi-Fi firmware

> **Scope.** This is the foundational walkthrough for the *Latent Radios* catalog. Every other walkthrough — [BCM43455c0 on the Raspberry Pi](bcm43455c0-raspberry-pi.md), [Broadcom D11 ucode](broadcom-d11-ucode.md), [ESP32 Xtensa in Ghidra](esp32-xtensa-ghidra.md), [ath9k spectral/CSI](atheros-ath9k-spectral-csi.md), [Intel 5300 CSI](intel-5300-csi.md) — assumes you have already done what is on this page: pulled a firmware blob off disk, identified its CPU, loaded it at the right base address in Ghidra, and applied symbols. If your disassembly is a wall of `??` bytes or a river of nonsense instructions, the cause is almost always one of two things covered here: **wrong processor** or **wrong base address**. Get those two right and everything downstream becomes tractable.

The goal is *reproducibility over bravado*. Where an exact number is chip- and firmware-version-specific (base addresses, symbol offsets, reset-vector locations), this guide tells you **which file or which struct to read the number out of** rather than asking you to trust a magic constant. The few concrete hex values quoted below are pinned to a named, linked source and a named firmware version — treat them as *worked examples*, and re-derive the equivalents for your own dump.

---

## 0. What you need

| Tool | Why | Install |
|---|---|---|
| **Ghidra 11.0+** | Disassembler/decompiler. 11.0+ ships a native **Xtensa** processor (no plugin needed); ARM/MIPS/ARC have shipped for years. | [ghidra-sre.org](https://ghidra-sre.org/) — needs JDK 17+ |
| **binwalk** | Container carving + entropy scan + `cpu_rec` host | `pipx install binwalk` (v3) or distro package |
| **cpu_rec** | Statistical CPU-architecture recognizer, runs as a binwalk module | [airbus-seclab/cpu_rec](https://github.com/airbus-seclab/cpu_rec) |
| **GNU binutils (multiarch)** | `arm-none-eabi-objdump`, `xtensa-esp32-elf-objdump`, `readelf`, `nm` for cross-checking | distro / [Espressif toolchains](https://docs.espressif.com/) |
| **esptool** | Parse ESP-IDF image headers, dump flash | `pipx install esptool` |
| **LIEF** | Scriptable ELF/PE parsing (extract Broadcom firmware from a `.ko`) | `pip install lief` |
| **Python 3** | glue, symbol-map conversion, Ghidra headless scripts | — |

Everything here is read-only static analysis. No radio transmits. The regulatory considerations only appear once you *flash a patched image* — see [§9](#9-safety-and-regulatory-notes).

---

## 1. Get the blob

You cannot reverse what you cannot read. Four families cover almost every Wi-Fi part in the catalog. In all four cases the artifact you load into Ghidra is a **raw code image for an embedded core**, not a host-CPU ELF — that distinction drives every later step.

### 1a. Broadcom / Cypress (brcmfmac `.bin`)

The RAM firmware ships in `linux-firmware` and is the easiest to obtain — it is already a flat blob:

```bash
# On any Linux box with the driver installed:
ls -l /lib/firmware/brcm/
#   brcmfmac43455-sdio.bin      <- RAM firmware image (this is your Ghidra input)
#   brcmfmac43455-sdio.clm_blob <- regulatory (CLM) data, NOT code
#   brcmfmac43455-sdio.txt      <- NVRAM board config, NOT code

# Canonical upstream copy:
git clone --depth 1 https://gitlab.com/kernel-firmware/linux-firmware.git
ls linux-firmware/brcm/brcmfmac*.bin
```

The `.bin` is the **RAM download image**; the on-chip **ROM** is a separate region that is *not* in `linux-firmware` (you dump it from a live chip — see [§5](#5-import-symbol-tables-nexmon-and-friends) and the [BCM43455c0 walkthrough](bcm43455c0-raspberry-pi.md)). For the proprietary `wl.ko` driver instead of brcmfmac, the firmware is embedded in the module's `.data` section under `dlarray_*` symbols; extract it with LIEF (per Quarkslab's write-up):

```python
import lief
ko = lief.parse("wl.ko")
for s in ko.symbols:
    if s.name.startswith("dlarray"):
        print(hex(s.value), s.size, s.name)
```

Chip family details and part numbers: [chips/broadcom-cypress.md](../../chips/broadcom-cypress.md).

### 1b. Intel (iwlwifi `.ucode`)

```bash
ls /lib/firmware/iwlwifi-*.ucode
# e.g. iwlwifi-cc-a0-77.ucode  (Wi-Fi 6 AX2xx)
```

An `.ucode` file is **not** a flat image — it is a **TLV container** (magic `0x0a4c5749` = `"IWL\n"` little-endian, followed by 32-bit *type* / 32-bit *length* / payload records). You must **carve the code sections out** before loading. The authoritative layout is the kernel header [`drivers/net/wireless/intel/iwlwifi/fw/img.h`](https://github.com/torvalds/linux/blob/master/drivers/net/wireless/intel/iwlwifi/fw/img.h) and the TLV enum in `fw/file.h`. The interesting payloads are the `INST` (instruction) and `DATA` sections of each ucode type (`Regular`, `Init`, `WoWLAN`, `Regular usniffer`). Parse the TLVs (a short Python struct-unpack loop, or an existing parser), write each `INST` blob to its own file, then load that. Intel's LMAC/UMAC firmware targets a Tensilica-style core and is largely undocumented — expect Tier-0/1 territory. See [chips/intel.md](../../chips/intel.md) and the [Intel 5300 CSI walkthrough](intel-5300-csi.md) for what *is* reachable without touching the ucode at all.

### 1c. ESP32 family (ESP-IDF `app.bin` / flash dump)

Two ways in. If you have the project, the build tree already has `build/<app>.bin` and, more usefully, the **ELF** `build/<app>.elf` (full symbols — load *that* and skip most of this guide). If you only have hardware, dump the SPI flash:

```bash
esptool --chip esp32 --port /dev/ttyUSB0 --baud 921600 read_flash 0x0 0x400000 flash.bin
```

Then read the image header instead of guessing offsets — the ESP image starts with magic byte `0xE9` and each segment header carries its **load address**:

```bash
# Default app partition on classic ESP32 lives at flash offset 0x10000:
esptool --chip esp32 image_info --version 2 build/app.bin
# prints: segment 0 -> load 0x3F400020 (DROM), segment N -> load 0x400D0020 (IROM), etc.
```

Those printed load addresses *are* your Ghidra memory map (see [§4](#4-set-the-load-address-and-memory-map)). Full ESP32 procedure: [esp32-xtensa-ghidra.md](esp32-xtensa-ghidra.md); silicon variants (S2/S3 Xtensa vs C2/C3/C6 RISC-V): [chips/espressif.md](../../chips/espressif.md).

### 1d. Anything else (generic `linux-firmware`)

MediaTek, Ralink, Realtek USB, Qualcomm/Atheros, Marvell — most keep their firmware under `/lib/firmware/<vendor>/`. Some are flat, many are wrapped (vendor headers, multiple concatenated cores, sometimes compressed). Do **not** assume flat — run the fingerprinting pass in [§2](#2-fingerprint-the-architecture) first. Vendor specifics live in [chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md), [chips/mediatek-ralink.md](../../chips/mediatek-ralink.md), and [chips/realtek.md](../../chips/realtek.md).

---

## 2. Fingerprint the architecture

Loading a blob with the wrong processor is the #1 cause of garbage disassembly. Spend five minutes here before touching Ghidra.

**Step 1 — carve the container.** A firmware file may bundle a header, several cores, and data. See where the boundaries are:

```bash
binwalk firmware.bin              # signatures: headers, compression, embedded FS
binwalk -E firmware.bin           # entropy plot: flat ~0.5–0.7 = code; ~0.99 = compressed/encrypted
```

High, flat entropy (>0.9) across the whole file means it is **compressed or encrypted** — no disassembler will help until you decompress. A mixed profile (a low-entropy code region followed by a high-entropy blob) is normal: code first, then a packed data/ucode section.

**Step 2 — recognize the ISA statistically.** `cpu_rec` slides a statistical model of ~70 instruction sets across the file:

```bash
# install as a binwalk module:
mkdir -p ~/.config/binwalk/modules
cp cpu_rec.py ~/.config/binwalk/modules/
cp -r cpu_rec_corpus ~/.config/binwalk/modules/
binwalk -% firmware.bin
```

Typical output — one architecture per contiguous region:

```
DECIMAL   HEXADECIMAL   DESCRIPTION
0         0x0           ARMhf   (size=0x40000, entropy=0.62)
262144    0x40000       None    (size=0x8000, entropy=0.71)   # data/tables
```

`ARMhf`/`ARMel` → ARM Thumb-2 (Broadcom). `Xtensa` → ESP32 / some Intel. `MIPSel`/`MIPS` → some MediaTek/Ralink and router SoCs. `ARCompact` → certain NIC cores. Treat cpu_rec as a *strong hint*, not gospel — IA-64 and data blobs can alias, and short regions are noisy.

**Step 3 — corroborate with `strings`.** Cheap and decisive:

```bash
strings -n 6 firmware.bin | grep -iE 'cortex|xtensa|gcc|clang|wlc_|d11|version|__ARM|reclaim' | head
```

`wlc_`, `d11`, `hndrte` → Broadcom. `xtensa`/`esp-idf`/`app_desc` → ESP32. GCC version banners often name the target triple (`arm-none-eabi`, `xtensa-esp32-elf`, `mipsel-linux`). A version string like `7.45.206` on a Broadcom blob is exactly the token you use to pick the right Nexmon symbol set in [§5](#5-import-symbol-tables-nexmon-and-friends).

**Cross-check summary:**

| Signal | Broadcom | ESP32 (classic) | MediaTek/Ralink | Intel |
|---|---|---|---|---|
| cpu_rec | ARMel/ARMhf | Xtensa | MIPSel / ARM | Xtensa-ish / undoc |
| strings | `wlc_`, `hndrte`, `d11` | `esp-idf`, `app_desc` | ` raEther`, `mt76` | sparse |
| container | flat RAM `.bin` | `0xE9` image header | vendor header | TLV `IWL\n` |

---

## 3. Choose the Ghidra processor / language

In Ghidra's import dialog, **Language** = the processor/variant/endianness triple. Pick from this table; get the variant right, not just the family.

| Target | Ghidra Language (`Processor:Endian:Size:Variant`) | Notes |
|---|---|---|
| Broadcom **app** core (BCM43xx/4356/4387…), Cortex-R4 | `ARM:LE:32:Cortex` | armv7-r, Thumb-2. Confirm per version in Nexmon `definitions.mk` (`NEXMON_ARCH := armv7-r`). |
| Broadcom **app** core, Cortex-M3 (older/BT-combo) | `ARM:LE:32:Cortex` | armv7-m; ROM commonly mapped high (see §4). |
| Broadcom **D11 PHY ucode** | *not* ARM — proprietary microcode | Do **not** load as ARM. Use the [D11 ucode walkthrough](broadcom-d11-ucode.md); it needs the SeeMoo/community ucode tooling, not a stock Ghidra processor. |
| **ESP32 / S2 / S3** (Xtensa LX6/LX7) | `Xtensa:LE:32:default` | Native in Ghidra **11.0+**. Older Ghidra: install a module (below). |
| **ESP32-C2/C3/C6/H2**, ESP8684 | `RISCV:LE:32:RV32IMC` (or `default`) | These are RISC-V, *not* Xtensa. cpu_rec/strings will disambiguate. |
| MediaTek/Ralink SoC cores | `MIPS:LE:32:default` or `ARM:LE:32:v7` | Depends on part; verify with cpu_rec. |
| ARC-based NIC cores | `ARC:LE:32:...` | Rare; native Ghidra ARC exists. |

**Xtensa on Ghidra < 11** (or if the native module chokes on windowed-register / MAC16 code): install a community module.

```bash
# yath module (targets Ghidra 9.1.x; there are forks tracking newer builds):
cd $GHIDRA_INSTALL_DIR/Ghidra/Processors
git clone https://github.com/yath/ghidra-xtensa Xtensa
cd Xtensa && make
# Alternative, more actively extended: https://github.com/Ebiroll/ghidra-xtensa
```

Even Ghidra 11's built-in Xtensa is **incomplete** — windowed-register calls (`call8`/`entry`), the MAC16 option, and zero-overhead loops are known weak spots, so the decompiler occasionally mis-models the stack on ESP32 code. If a function's decompilation looks structurally wrong around calls, suspect windowed-ABI handling before you suspect your base address. Tracking list: [BlackVS/ESP32-reversing](https://github.com/BlackVS/ESP32-reversing).

> **ARM tip:** Broadcom app firmware is almost entirely **Thumb-2**. If ARM code disassembles as garbage, you probably started analysis in ARM mode at an odd address. Set the **TMode** context register to 1 (Thumb) at your entry, or let auto-analysis follow the reset vector's LSB (see §4).

---

## 4. Set the load address and memory map

This is the other half of "why is my disassembly garbage." A flat firmware blob has **no headers telling Ghidra where it lives**. If you import it at `0x0` but the code was linked to run at `0x198000`, then every absolute pointer, every branch target, every string reference lands in unmapped space and analysis collapses.

**Why it matters concretely:** embedded firmware is full of **absolute** references — literal pools holding function pointers, jump tables, `LDR Rn, [PC, #imm]` loads of global addresses. Those only resolve to real code/data if the image base in Ghidra equals the link base the vendor used. Get the base right and Ghidra's auto-analysis will chase pointers into functions and strings automatically; get it wrong and nothing cross-references.

### How to find the base address

**Best: read it from a build definition.** For Broadcom, Nexmon literally ships the memory map per chip and firmware version in `firmwares/<chip>/<ver>/definitions.mk`. Worked example — **BCM43455c0, firmware 7.45.206** (Raspberry Pi 3B+/4/Zero2W) from the [upstream file](https://github.com/seemoo-lab/nexmon/tree/master/firmwares/bcm43455c0):

| Variable | Value | Meaning for Ghidra |
|---|---|---|
| `NEXMON_ARCH` | `armv7-r` | Language `ARM:LE:32:Cortex`, Thumb |
| `RAM_FILE` | `brcmfmac43455-sdio.bin` | the blob you load |
| `RAMSTART` | `0x198000` | **base address for the RAM `.bin`** |
| `RAMSIZE` | `0xC8000` | RAM region length |
| `ROM_FILE` | `rom.bin` | dumped separately |
| `ROMSTART` | `0x0` | base for the ROM dump (R4 → ROM at 0x0) |
| `ROMSIZE` | `0xB0000` | ROM length |
| `UCODESTART` | `0x222ED8` | D11 ucode blob location in RAM image |

So: load `brcmfmac43455-sdio.bin` as `ARM:LE:32:Cortex` at base **`0x198000`**, and add a second memory block for the ROM dump at **`0x0`**. Different chip or version → open *its* `definitions.mk` and read *its* numbers. Do not reuse these across parts. General rule of thumb from Quarkslab's survey: Cortex-**R4** chips tend to map ROM at low addresses (e.g. `0x0`), Cortex-**M3** chips often map ROM high (around `0x800000`) — but the `definitions.mk` is ground truth, not the rule of thumb.

**For ESP32: read it from the image.** `esptool ... image_info` (§1c) prints each segment's load address — create one Ghidra memory block per segment at exactly those addresses (DROM ≈ `0x3F40_0000`, IROM ≈ `0x400D_0000`, IRAM ≈ `0x4008_0000`, DRAM ≈ `0x3FFB_0000` on classic ESP32; **verify, don't assume** — they differ on S2/S3). Details: [esp32-xtensa-ghidra.md](esp32-xtensa-ghidra.md).

**When you have no build file: infer from the reset vector.** On ARM Cortex-M the image begins with a **vector table**: word[0] = initial SP, word[1] = reset handler address (Thumb, so odd). Read word[1]; its value is a link-time absolute address that must point *inside your image*. Choose the base so that `word[1]` lands on the reset handler:

```python
import struct
data = open("firmware.bin","rb").read()
sp, reset = struct.unpack_from("<II", data, 0)
print(hex(sp), hex(reset))
# base ≈ (reset & ~1) rounded down to the nearest sensible boundary such that
# (reset & ~1) - base is a valid file offset landing on code.
```

On Cortex-R/A the reset vector is a branch instruction at the vector base (`B` / `LDR PC,[PC,#..]`); decode its target and solve for the base the same way. Cross-check the base by verifying that a handful of literal-pool pointers (the `LDR Rn,[PC,#imm]` targets near the start) resolve to plausible code or ASCII strings — a correct base makes many of them line up at once; a wrong base makes essentially none line up. Relocation-style self-references (a table of absolute addresses all sharing a high prefix) also leak the base: the common prefix *is* your base region.

**In the Ghidra dialog:** *File → Import File → (pick Language) → Options…* set **Base Address** to the value above. After import, refine with the **Memory Map** window (the four-RAM-blocks icon): add ROM/IRAM/DROM blocks, mark code blocks executable, then *Analysis → Auto Analyze*.

---

## 5. Import symbol tables (Nexmon and friends)

Stripped firmware analyzes fine but reads like `FUN_00198abc`. Real symbols turn it into `wlc_recv`, `wlc_bmac_dpc`, `hnd_cons_puts` — and for Broadcom you can get them for free, because Nexmon builds against a **per-firmware symbol map**.

Each Nexmon firmware target directory (`firmwares/<chip>/<ver>/`) and the patch tree carry symbol definitions the framework uses to hook functions by name. The build produces a `wl.map`/linker map and the patch headers (`definitions.mk`, `wrapper.c`, `patch.ld`) enumerate known function and data addresses for that exact version. Convert those `name = address` pairs into a Ghidra symbol import:

```python
# nexmon_map_to_ghidra.py — turn a "0x00198abc T wlc_recv" style map into
# a Ghidra ImporterScript-friendly CSV, then apply via a headless script.
import re, sys
for line in open(sys.argv[1]):
    m = re.match(r'\s*(0x[0-9a-fA-F]+)\s+\w?\s*([A-Za-z_]\w+)', line)
    if m:
        print(f"{m.group(2)},{m.group(1)}")
```

Apply the CSV in Ghidra with a tiny headless script (`createLabel(toAddr(addr), name, true)` per row), or paste addresses into *Navigation → Label*. **Match the firmware version exactly** — a symbol map from `7_45_154` applied to a `7_45_206` image will be silently offset and mislabel everything. That version token is the one you pulled with `strings` in §2. Nexmon internals and the hook mechanism: [projects/nexmon.md](../../projects/nexmon.md).

For **ESP32**, the equivalent win is even bigger: if you have the matching **ELF** from a build, load *it* (full DWARF symbols). For ROM functions, Espressif publishes ROM ELF/`.ld` symbol files in ESP-IDF (`components/esp_rom/.../ld/*.ld`) — import those addresses the same way. For Intel/MediaTek there is generally **no** public symbol map; you build up names by hand from string cross-references (§6).

---

## 6. First-analysis checklist

With processor, base, and symbols in place, orient yourself. These three anchors unlock the rest of any Wi-Fi firmware.

**1. Find the reset / entry.** You already located it in §4. Confirm Ghidra disassembled it as a function; from here trace early init (clock/PLL setup, `.data` copy, `.bss` clear, a CRC/integrity check, then the main loop or a `WFI`/`waiti`). Per Quarkslab, Broadcom init reliably ends in a `WFI` you can cross-reference backward to reach the scheduler.

**2. Find the console / `printf`.** This is the single highest-value symbol. Broadcom keeps an in-memory **console ring buffer** (the `hnd_cons`/`hndrte_cons` machinery, ~2 KB); its writer (`hnd_cons_puts`-style) is called from all over. Find it by locating format strings (`%s`, `%d`, driver banners) and following their cross-references to a common callee — that callee is your `printf`, and its callers are your labeled event handlers. On ESP32 the analogue is `esp_rom_printf`/`ets_printf` (often already named from the ROM symbol map). Naming the logger propagates human-readable names across the whole image via its format-string arguments.

**3. Find the DMA ring / packet path.** This is where the *radio* lives. Search for the ring/descriptor setup — on Broadcom the `dma64`/`dma_attach` routines and RX/TX descriptor rings; the RX header length is even parameterized in Nexmon (`RXE_RXHDR_LEN`). Trace from the RX interrupt/FIQ handler through the DPC (`wlc_dpc` → `wlc_bmac_recv` → `wlc_recv`) to the management-frame dispatch. This chain is what monitor-mode, injection, and CSI patches hook — see [projects/csi-toolchains.md](../../projects/csi-toolchains.md) and [docs/techniques.md](../techniques.md).

Quick anchors to search for:

| Anchor | Broadcom | ESP32 |
|---|---|---|
| Entry | reset vector / `definitions.mk` | `call_start_cpu0` / image entry |
| Logger | `hnd_cons_puts`, console ring | `esp_rom_printf` / `ets_printf` |
| RX path | `wlc_recv`, `wlc_bmac_recv`, `dma_rx` | Wi-Fi MAC ISR (largely blob) |
| Ucode | `UCODESTART` region (D11) | n/a |

---

## 7. Per-target quick reference

| Target | Blob source | Language | Base address source | Symbols |
|---|---|---|---|---|
| Broadcom RAM fw | `linux-firmware/brcm/*.bin` | `ARM:LE:32:Cortex` (Thumb) | Nexmon `definitions.mk` `RAMSTART` | Nexmon map |
| Broadcom ROM | live-chip dump | `ARM:LE:32:Cortex` | `ROMSTART` (R4→0x0, M3→high) | Nexmon map |
| ESP32/S2/S3 | `build/*.elf` or flash dump | `Xtensa:LE:32:default` | `esptool image_info` per segment | ELF/ROM `.ld` |
| ESP32-C3/C6 | as above | `RISCV:LE:32:RV32IMC` | `esptool image_info` | ELF/ROM `.ld` |
| Intel | `*.ucode` (carve TLVs) | Xtensa-ish / undoc | from TLV section metadata | none public |
| MediaTek/Ralink | `linux-firmware/<vendor>/` | MIPS or ARM (cpu_rec) | infer from reset vector | none public |

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Whole file is `??`, no instructions | Wrong processor, or data/compressed region | Re-run §2; check entropy; carve container |
| Instructions look valid but branches go nowhere; no string xrefs | **Wrong base address** | Recompute base from reset vector / `definitions.mk` (§4) |
| ARM decodes as gibberish in patches | Started in ARM mode; code is Thumb-2 | Set TMode=1 at entry; follow reset LSB |
| ESP32 stack/args look wrong near calls | Windowed-ABI / MAC16 gaps in Xtensa module | Update module; reason about `entry`/`callN` manually |
| Symbols land on wrong functions | Symbol map version ≠ firmware version | Match the `strings` version token exactly (§5) |
| `.ucode` won't disassemble as anything | It's a TLV container, not flat code | Parse TLVs, extract `INST` sections first (§1b) |
| High flat entropy everywhere | Compressed/encrypted image | Decompress/decrypt before Ghidra can help |

---

## 9. Safety and regulatory notes

Everything on this page is **static, read-only** reverse engineering: you are inspecting bytes, not emitting RF, so there is nothing to authorize here. Regulatory duties attach only when you cross from *reading* firmware to *flashing a modified image* that changes radio behavior — enabling channels/power/duty-cycles outside your regional allocation, or transmitting arbitrary waveforms. At that point the [Tier-4 verification](../verification-tier4.md) rules apply: keep TX experiments in a shielded enclosure or on a wired/attenuated path, respect your local band plan, and never radiate on aviation, cellular, or emergency allocations. The **CLM/NVRAM** files beside the Broadcom `.bin` encode regulatory limits — understand that patching around them is what turns a lab exercise into a compliance question. See also [docs/roadmap.md](../roadmap.md) for where each capability sits on the SDR ladder.

---

## References

- Quarkslab — *Reverse engineering Broadcom wireless chipsets* (firmware extraction, ARM cores, base addresses, console, packet path): <https://blog.quarkslab.com/reverse-engineering-broadcom-wireless-chipsets.html>
- Nexmon firmware patching framework (per-chip `definitions.mk` memory maps, symbol maps, ROM extraction): <https://github.com/seemoo-lab/nexmon> — BCM43455c0 definitions: <https://github.com/seemoo-lab/nexmon/tree/master/firmwares/bcm43455c0>
- Schulz et al. — *NexMon: A Cookbook for Firmware Modifications on Smartphones*: <https://arxiv.org/pdf/1601.07077>
- Linux `iwlwifi` firmware image structs (`fw/img.h`, TLV format): <https://github.com/torvalds/linux/blob/master/drivers/net/wireless/intel/iwlwifi/fw/img.h>
- ESP-IDF *App Image Format* (0xE9 header, segment load addresses): <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/app_image_format.html>
- ESP-IDF *Memory Types* (IRAM/IROM/DRAM/DROM bus layout): <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/memory-types.html>
- yath — Ghidra Xtensa processor module: <https://github.com/yath/ghidra-xtensa> · Ebiroll fork: <https://github.com/Ebiroll/ghidra-xtensa>
- Ghidra Xtensa upstream PR #1407 (native support in 11.0+): <https://github.com/NationalSecurityAgency/ghidra/pull/1407>
- BlackVS — curated ESP32 reversing resources: <https://github.com/BlackVS/ESP32-reversing>
- airbus-seclab — `cpu_rec` architecture recognizer + binwalk module: <https://github.com/airbus-seclab/cpu_rec> · SSTIC 2017 paper: <https://airbus-seclab.github.io/cpurec/SSTIC2017-Article-cpu_rec-granboulan.pdf>
- linux-firmware upstream: <https://gitlab.com/kernel-firmware/linux-firmware>
- Ghidra: <https://ghidra-sre.org/>

*Sibling pages:* [firmware-reversing.md](../firmware-reversing.md) · [taxonomy.md](../taxonomy.md) · [glossary.md](../glossary.md) · walkthroughs for [BCM43455c0](bcm43455c0-raspberry-pi.md), [D11 ucode](broadcom-d11-ucode.md), [ESP32 Xtensa](esp32-xtensa-ghidra.md), [ath9k CSI](atheros-ath9k-spectral-csi.md), [Intel 5300 CSI](intel-5300-csi.md).
