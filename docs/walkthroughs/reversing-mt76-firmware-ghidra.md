# Reversing MediaTek mt76 Firmware in Ghidra

MediaTek's `mt76` driver is one of the most open Wi-Fi stacks in the mainline kernel:
the host side — queue management, MCU command framing, the TXD/RXD descriptor layout,
even the firmware *loader* — is all GPL C you can read line by line. That is exactly
why mt76 is a good target and also why it is a slightly unusual one. The **driver** side
gives you almost nothing to reverse; it is already source. The **firmware** side — the
`*_wm.bin` / `*_wa.bin` / `*_rom_patch.bin` blobs that run on the on-chip MCUs — is where
the closed logic lives, and where the reverse-engineering work actually is.

This walkthrough shows how to find those blobs, how to use the *open driver* as a free,
authoritative spec for the *closed firmware*'s container format, how to carve the regions
out and load each at the right base address in Ghidra, and where inside the image the
SDR-interesting machinery (descriptor formatting, the debug/telemetry hooks the driver
already exposes, radar/DFS, CSI) tends to sit.

> **Ground rule:** every address, struct field, and firmware filename below is traced to
> a primary source — the in-kernel `mt76` driver or `linux-firmware`. Struct *sizes* are
> derived from the `__packed` C definitions and marked as such; the reader is always told
> how to re-derive a value in their own dump rather than being handed a magic number.
> See [../../docs/firmware-reversing.md](../../docs/firmware-reversing.md) for the general
> method and [../../chips/mediatek-ralink.md](../../chips/mediatek-ralink.md) for the chip
> catalog this feeds.

---

## 1. The mt76 family and where its firmware lives

`mt76` drives everything from the old Mট7603/MT7615 up through the connac2 generation
(MT7915/MT7916/MT7981/MT7986, Wi-Fi 6/6E) and connac3 (MT7996/MT7992/MT7990, Wi-Fi 7).
On a running Linux box the firmware request handler pulls the blobs from the standard
firmware search path:

```
/lib/firmware/mediatek/            # connac2 parts: MT7915/7916/7981/7986
/lib/firmware/mediatek/mt7996/     # connac3 parts: MT7996/7992/7990
```

The filenames are `#define`d in each sub-driver's header. For **MT7915** they are
(`mt7915/mt7915.h`):

| define | path |
| --- | --- |
| `MT7915_ROM_PATCH` | `mediatek/mt7915_rom_patch.bin` |
| `MT7915_FIRMWARE_WM` | `mediatek/mt7915_wm.bin` |
| `MT7915_FIRMWARE_WA` | `mediatek/mt7915_wa.bin` |

The same triplet exists for MT7916 (`mt7916_*`), MT7981 (`mt7981_*`) and MT7986
(`mt7986_*`, plus a `mt7986_wm_mt7975.bin` / `mt7986_rom_patch_mt7975.bin` variant for
the MT7975 companion RF). Wi-Fi 7 parts add two more processors and live under the
`mt7996/` subdirectory (`mt7996/mt7996.h`):

| role | MT7996 file |
| --- | --- |
| ROM patch | `mediatek/mt7996/mt7996_rom_patch.bin` |
| WiFi-MAC (WM) | `mediatek/mt7996/mt7996_wm.bin` |
| WiFi-Aux (WA) | `mediatek/mt7996/mt7996_wa.bin` |
| DSP | `mediatek/mt7996/mt7996_dsp.bin` |

(with `_233` firmware-version variants, and analogous `mt7992_*` / `mt7990_*` sets).

### What each blob is

- **ROM patch** (`*_rom_patch.bin`) — a set of *patch sections* downloaded on top of the
  masked boot ROM before the main firmware runs. The ROM itself is **not** in this file;
  the patch only carries the deltas and the branch/hook table. It is loaded first, by
  `mt76_connac2_load_patch()`.
- **WM = WiFi-MAC firmware** (`*_wm.bin`) — the main MAC/PHY control processor image.
  This is the big one: rate control, aggregation, TXD/RXD formatting, DFS, beamforming.
- **WA = WiFi-Auxiliary firmware** (`*_wa.bin`) — the offload/co-processor image
  (statistics, some data-path offload). Loaded as a second RAM image.
- **DSP** (`mt7996_dsp.bin`, connac3 only) — a separate DSP core image.
- **WO = WED offload** (`mediatek/mt7986_wo.bin`, `mediatek/mt7981_wo.bin`) — firmware
  for the **W**ireless-**E**thernet-**D**ispatch **O**ffload micro-processor. This one is
  *not* loaded by the Wi-Fi driver; it is requested by the Ethernet WED block in
  `drivers/net/ethernet/mediatek/` (`mtk_wed_wo`), because WED bridges the Wi-Fi and
  Ethernet MACs for hardware NAT/flow offload. Treat it as a fourth, independent target.

So on a modern part you can have **four** distinct code images — ROM-patch, WM, WA, and
either DSP (connac3) or WO (WED) — each on its own core with its own base address. Reverse
them separately.

---

## 2. Core architecture: identify it, don't assume it

MediaTek's connac WiFi MCUs (WM/WA) are widely **reported** to run on **Andes** cores
(AndeStar / AndesCore — the same IP family, NDS32-derived on older parts and RISC-V–based
`AndesCore` on newer ones), while some peripheral processors and older Ralink-era parts
are ARM or MIPS. The WED **WO** processor on MT7986/MT7981 is likewise an Andes-class RISC
core. **This is exactly the kind of fact you must confirm from the binary, not assert.**
Ghidra does not ship an AndeStar/NDS32 processor module by default, so getting the arch
right is the first real RE step, not a footnote.

Practical identification workflow (all in your own dump):

1. `file *.bin` and `binwalk -A *.bin` — look for recognizable instruction signatures and
   for LZMA/compressed sub-regions (connac RAM regions can be compressed; see the
   `decomp_*` fields below).
2. Inspect the **reset/entry** behavior: the RAM trailer/region descriptors (Section 4)
   give you the load address of each region, so you know where the image *thinks* it lives.
   Load it flat at that address in Ghidra with the **RAW binary** loader, then try
   candidate languages and see which one produces a sane prologue/epilogue at the region
   start.
3. Candidate languages to try, in order: any **NDS32 / AndeStar** SLEIGH module you have
   installed (community Andes/NDS32 Ghidra processor modules exist — search current
   sources), then **RISC-V** (`RISCV:LE:32`) for newer AndesCore-based images, then
   **ARM** (`ARM:LE:32` Cortex-M/`v7`) for peripheral/older cores, then **MIPS** for
   Ralink-era MT76xx. The correct one is obvious once function boundaries and the string
   xrefs line up.
4. Confirm with strings: connac firmware carries build-date and version strings (the
   headers below have `build_date[16]`/`build_date[15]` and `fw_ver[10]`) plus subsystem
   tags — those give you natural anchors and confirm you've based the image correctly.

Record whatever you actually observe (`status: reported` until you have confirmed the ISA
against a datasheet or a known-good disassembly).

---

## 3. Pulling the blobs

No hardware dump is needed for WM/WA/patch — they ship in `linux-firmware`:

```bash
# From a running system
cp /lib/firmware/mediatek/mt7915_wm.bin      ~/re/
cp /lib/firmware/mediatek/mt7915_wa.bin      ~/re/
cp /lib/firmware/mediatek/mt7915_rom_patch.bin ~/re/

# Or straight from upstream (authoritative, versioned)
#   https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/mediatek
git clone --depth=1 \
  https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git
ls linux-firmware/mediatek/          # connac2
ls linux-firmware/mediatek/mt7996/   # connac3
```

The **boot ROM** proper is the one piece you cannot get from `linux-firmware` — it is
masked into the silicon. If you need it, dump it over the MCU debug/JTAG path or by
abusing a memory-read MCU command; that is out of scope here and the patch file plus a
live `fw_util` PC read (Section 6) usually tell you enough about ROM entry points to work
without it.

---

## 4. The container format — read it out of the open driver

This is the payoff of mt76 being open: you never have to *guess* the header format. The
loader parses it in `drivers/net/wireless/mediatek/mt76/mt76_connac_mcu.c`
(`mt76_connac2_load_patch()` for the ROM patch, `mt76_connac2_load_ram()` for WM/WA), and
the structs are declared in `mt76_connac_mcu.h`. Open those two files alongside Ghidra;
they are your ground truth. The four structs, verbatim from `mt76_connac_mcu.h`:

```c
struct mt76_connac2_patch_hdr {                 /* ROM patch, at file START, BIG-endian */
        char build_date[16];
        char platform[4];
        __be32 hw_sw_ver;
        __be32 patch_ver;
        __be16 checksum;
        u16 rsv;
        struct {
                __be32 patch_ver;
                __be32 subsys;
                __be32 feature;
                __be32 n_region;
                __be32 crc;
                u32 rsv[11];
        } desc;
} __packed;

struct mt76_connac2_patch_sec {                 /* one per patch region, BIG-endian */
        __be32 type;
        __be32 offs;                            /* file offset of this section's payload */
        __be32 size;
        union {
                __be32 spec[13];
                struct {
                        __be32 addr;            /* LOAD address -> Ghidra base for this section */
                        __be32 len;
                        __be32 sec_key_idx;
                        __be32 align_len;
                        u32 rsv[9];
                } info;
        };
} __packed;

struct mt76_connac2_fw_trailer {                /* WM/WA, at file END, LITTLE-endian */
        u8 chip_id;
        u8 eco_code;
        u8 n_region;
        u8 format_ver;
        u8 format_flag;
        u8 rsv[2];
        char fw_ver[10];
        char build_date[15];
        __le32 crc;
} __packed;

struct mt76_connac2_fw_region {                 /* one per RAM region, LITTLE-endian */
        __le32 decomp_crc;
        __le32 decomp_len;
        __le32 decomp_blk_sz;
        u8 rsv[4];
        __le32 addr;                            /* LOAD address -> Ghidra base for this region */
        __le32 len;
        u8 feature_set;
        u8 type;
        u8 rsv1[14];
} __packed;
```

Two things worth committing to memory because they trip people up:

- **Endianness differs by file.** The ROM-patch header/section use `__be32` (big-endian).
  The WM/WA trailer/region use `__le32` (little-endian). Parse accordingly.
- **The addresses come from the firmware, not the driver.** `mt76_connac2_load_ram()`
  does `addr = le32_to_cpu(region->addr)` and `mt76_connac2_load_patch()` does
  `addr = be32_to_cpu(sec->info.addr)`. There is no single hardcoded base you can reuse
  across regions — each region names its own load VA. (`mt7915/mcu.c` does define
  `MCU_PATCH_ADDRESS 0x200000`, but that is the DMA download target used when *shipping*
  the patch to the MCU, not necessarily the per-section execution VA — the per-section
  `info.addr` is what you base on in Ghidra.)

### Layouts (derived from the `__packed` structs — verify against the file)

Because the structs are `__packed`, their byte sizes follow directly from the field
widths. Re-derive them yourself, but as a cross-check:

| struct | derived size |
| --- | --- |
| `mt76_connac2_patch_hdr` | 16+4+4+4+2+2 + (5·4 + 11·4) = **0x60 (96)** bytes |
| `mt76_connac2_patch_sec` | 4+4+4 + 13·4 = **0x40 (64)** bytes |
| `mt76_connac2_fw_trailer` | 7 + 10 + 15 + 4 = **0x24 (36)** bytes |
| `mt76_connac2_fw_region` | 4·5 + 1 + 1 + 14 = **0x28 (40)** bytes |

**ROM patch file (`*_rom_patch.bin`)** — header first, then a section table, then payloads:

```
[ patch_hdr (0x60) ][ patch_sec[0] ][ patch_sec[1] ] ... [ payloads ... ]
                       |                                    ^
                       +-- sec[i].offs -> file offset of payload i (be32)
                           sec[i].info.addr -> load VA of payload i (be32)
                           sec[i].info.len  -> payload length (be32)
```

The driver walks `i = 0 .. hdr->desc.n_region-1`, reads `sec[i]` at
`fw->data + sizeof(*hdr) + i*sizeof(*sec)`, and downloads `fw->data + sec[i].offs` for
`sec[i].info.len` bytes to `sec[i].info.addr`. Mirror that exactly.

**WM/WA RAM file (`*_wm.bin` / `*_wa.bin`)** — payloads first, region table + trailer at
the **end**:

```
[ region0 payload ][ region1 payload ] ... [ region_desc[0..n-1] ][ trailer (0x24) ]
        |                                          ^
        offset starts at 0, += region[i].len       region descriptors, one per payload
```

The driver reads the trailer from `fw->data + fw->size - sizeof(trailer)`, gets
`n_region`, then for each region reads a `fw_region` descriptor located just before the
trailer and copies the next `region->len` bytes (running from file offset 0) to
`region->addr`. If `decomp_len`/`decomp_blk_sz` are non-zero the region is compressed
(LZMA-style block) and `region->addr`/`decomp_len` describe the *decompressed* image —
decompress before basing in Ghidra.

### A carving script you can trust (widths straight from the structs)

```python
import struct

def carve_ram(path):
    data = open(path, 'rb').read()
    TRAILER = 0x24
    REGION  = 0x28
    (chip_id, eco, n_region, fmt_ver, fmt_flag) = struct.unpack_from('<5B', data, len(data)-TRAILER)
    fw_ver = data[len(data)-TRAILER+7 : len(data)-TRAILER+17].split(b'\0')[0]
    print(f'chip_id={chip_id:#x} eco={eco} n_region={n_region} fw_ver={fw_ver!r}')
    off = 0
    desc_base = len(data) - TRAILER - n_region*REGION
    for i in range(n_region):
        b = desc_base + i*REGION
        decomp_crc, decomp_len, decomp_blk = struct.unpack_from('<3I', data, b)
        addr, ln = struct.unpack_from('<2I', data, b+16)          # after 3*4 + rsv[4]
        feat, typ = struct.unpack_from('<2B', data, b+24)
        print(f'  region[{i}] addr={addr:#010x} len={ln:#x} '
              f'feat={feat:#x} decomp_len={decomp_len:#x}')
        open(f'{path}.region{i}_{addr:08x}.bin','wb').write(data[off:off+ln])
        off += ln

carve_ram('mt7915_wm.bin')
```

Sanity-check the printed `chip_id`, `fw_ver` and per-region `addr` against the driver's
own parse before you trust the split — if `n_region` or the addresses look absurd you have
the endianness or a struct size wrong. (Confirm `mt76_connac2_load_ram()` still matches
these offsets for the kernel version you're targeting; the format is stable but read it,
don't assume.)

---

## 5. Loading a region in Ghidra

For each carved region / patch section:

1. **File → Import File**, choose **Raw Binary**.
2. **Language:** the ISA you confirmed in Section 2 (try Andes/NDS32 module → RISC-V →
   ARM → MIPS). Get this right *before* auto-analysis; a wrong ISA wastes the whole pass.
3. **Options → Base Address:** the region's `addr` (`fw_region.addr` for WM/WA,
   `patch_sec.info.addr` for the patch). This is the single most important field — with
   the wrong base every absolute pointer and jump-table entry lands nowhere and xrefs die.
4. If regions cross-reference each other (WM calling into a patched ROM hook, or WA and WM
   sharing a mailbox), import them into the **same** Ghidra program at their respective
   bases (File → Add To Program) so inter-region xrefs resolve.
5. Run auto-analysis, then fix the entry point at the region base and let function
   discovery propagate.

If the ISA has no upstream Ghidra module, disassemble with a matching `objdump`/LLVM
backend and import as comments, or use the community NDS32/AndeStar processor spec — but
verify a handful of instructions by hand against a known call sequence first.

---

## 6. Where the interesting bits are

Use the **open driver** as a map into the **closed firmware**. Anything the host and MCU
must agree on is documented on the host side, which tells you what to grep for in the blob.

### TXD / RXD descriptors — the data-path contract

The transmit/receive descriptor layout the firmware builds and the hardware consumes is
fully spelled out in `mt76_connac2_mac.h` as `MT_TXD*` / `MT_RXD*` bitfield macros:

- **TXD0–TXD8** cover queue index, packet format, byte count (TXD0); WLAN index, TID,
  A-MSDU, header format (TXD1); fixed-vs-dynamic **rate**, power offset, max TX time,
  RTS/NDPA/NDP/**sounding** (TXD2); sequence/PN, retry & transmit counts (TXD3); the
  64-bit **PN** (TXD4/5); and crucially **TXD6 = beamforming indicators, transmit rate,
  SGI, HE-LTF, LDPC, antenna ID, bandwidth**, plus the separate TX-rate field macros
  (STBC/NSS/mode/DCM/index).
- **RXD DW0–DW4 + group-4 extended** carry length, WLAN index, security, error flags,
  BSSID, TID and PHY status.

TXD6 and the TX-rate macros are your lever toward the higher SDR rungs: they are how the
firmware is *told* to transmit a specific rate/MCS/bandwidth/antenna/LTF combination.
Finding the firmware routine that *consumes* TXD6 and programs the PHY/RF is the path to
raw-rate injection and, further in, to influencing the transmitted waveform. Grep the
disassembly for the TXD6 bit positions and the code that shifts/masks them.

### The debug hooks mt76 already hands you

`mt7915/debugfs.c` creates a set of debugfs knobs that are gifts for RE — you get live
telemetry from the running firmware without touching the silicon:

| debugfs file | why it matters for RE |
| --- | --- |
| `fw_util_wm`, `fw_util_wa` | **prints the MCU program counter + CPU utilization** — read the live PC and correlate it directly with Ghidra addresses to find hot paths and confirm your base address |
| `fw_debug_wm`, `fw_debug_wa` | enable in-firmware debug logging to the host |
| `fw_debug_bin` | binary firmware log via the kernel **relay** interface — a firehose of structured events straight from the blob |
| `rf_regval` | read/write RF registers live — cross-reference with the firmware's RF programming routines |
| `radar_trigger`, `rdd_monitor`, `dfs_hw_pattern` | DFS/radar-detection path (see below) |
| `txpower_sku`, `txpower_path` | per-rate / per-spatial-stream TX power tables — the data structures the firmware enforces |

Mounting: `mount -t debugfs none /sys/kernel/debug` then look under
`/sys/kernel/debug/ieee80211/phyN/mt76/`. The `fw_util_*` PC read is the single most
useful RE aid here — treat it as a poor-man's live debugger.

### Radar / DFS

The `radar_trigger`, `rdd_monitor` and `dfs_hw_pattern` knobs expose the **R**adar
**D**etection **D**river block. The pattern-matching and event path in the firmware is a
concrete, self-contained subsystem — a good first target for understanding how the MCU
processes PHY-level events, and adjacent to any passive-radar ambitions.

### CSI / spectral — the honest status

- **Spectral scan:** there is **no** `spectral`/`fft` debugfs hook in mainline `mt7915` or
  `mt7921` (verified — the driver does not expose one the way ath9k/ath10k do). Any raw-PHY
  spectral capability would have to be found and driven inside the firmware itself.
- **CSI:** mainline mt76 has **no** CSI debugfs/vendor path either (checked
  `mt7921/debugfs.c` and the openwrt/mt76 `mt7915` tree). CSI *does* exist for connac2
  parts, but only **out-of-tree**, via nl80211 **vendor commands** shipped in MediaTek's
  OpenWrt feed (`mtk-openwrt-feeds`, the `mt76` package's `vendor.c` with
  `MTK_VENDOR_ATTR_CSI_CTRL`-style attributes) and a companion userspace collector. Treat
  MediaTek-mt76 CSI as **`reported`**: real and used in the field, but not mainline, and
  the firmware-side CSI extraction it relies on is one of the more interesting things to
  confirm in a WM disassembly.

---

## 7. Suggested first session

1. Grab `mt7915_wm.bin`, `mt7915_wa.bin`, `mt7915_rom_patch.bin` from `linux-firmware`.
2. Carve WM with the script in Section 4; verify `chip_id`/`fw_ver`/region addresses
   against `mt76_connac2_load_ram()`.
3. Identify the ISA (Section 2); import the largest WM region at its `addr` (Section 5).
4. On live hardware, read `fw_util_wm` repeatedly to sample the PC, and confirm those PCs
   land inside your based image — that proves the base is right and highlights hot code.
5. Anchor on the build/version strings, then walk out to the TXD6-consuming routine and
   the DFS/RDD handler as your first two mapped subsystems.

Everything above is reproducible from public sources; nothing here transmits. Any step
that ends in **injecting** frames or driving the RF/PHY from modified firmware is a TX
activity — do it only into a shielded enclosure / on a licensed band, and see
[../../docs/rf-safety-and-legal.md](../../docs/rf-safety-and-legal.md) before you key up.

---

## References

- mt76 driver (openwrt/mt76 mirror), firmware loader & structs:
  `mt76_connac_mcu.c`, `mt76_connac_mcu.h`, `mt76_connac2_mac.h` —
  <https://github.com/openwrt/mt76>
- In-tree kernel source: `drivers/net/wireless/mediatek/mt76/` —
  <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/mediatek/mt76>
- MT7915 firmware filename defines: `mt7915/mt7915.h`; MT7996: `mt7996/mt7996.h`;
  debugfs hooks: `mt7915/debugfs.c` — same repo
- WED WO firmware/processor: `drivers/net/ethernet/mediatek/mtk_wed_wo.{c,h}` —
  <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/ethernet/mediatek>
- Firmware blobs: `linux-firmware/mediatek/` and `linux-firmware/mediatek/mt7996/` —
  <https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/mediatek>
- MediaTek OpenWrt feed (out-of-tree CSI vendor commands): `mtk-openwrt-feeds` —
  <https://git01.mediatek.com/plugins/gitiles/openwrt/feeds/mtk-openwrt-feeds>
- Ghidra: <https://github.com/NationalSecurityAgency/ghidra>

*Cross-links: [MediaTek / Ralink chips](../../chips/mediatek-ralink.md) ·
[Firmware Reversing](../../docs/firmware-reversing.md).*
