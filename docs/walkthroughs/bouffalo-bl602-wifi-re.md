# Bouffalo BL602 Wi-Fi: the community-reversed RISC-V radio

> Cycle 5 · depth entry. A cheap RISC-V Wi-Fi+BLE SoC whose Wi-Fi stack the community pulled apart in the open — the Pine64 **Nutcracker** effort and the [`pine64/bl602-re`](https://github.com/pine64/bl602-re) working group. This page covers the silicon, what is open source vs. what stays a blob, the RE tooling (Ghidra on RISC-V, DWARF-rich blobs), and exactly how much SDR-ish access you get. For the broader RISC-V-Wi-Fi landscape see [`../../chips/risc-v-wifi.md`](../../chips/risc-v-wifi.md); for the general reversing method see [`../firmware-reversing.md`](../firmware-reversing.md) and [`ghidra-setup-wifi-firmware.md`](ghidra-setup-wifi-firmware.md).

## TL;DR — where BL602 sits on the SDR ladder

| Question | Answer |
|---|---|
| Ladder tier | **1** (monitor + injection / raw packet). Not a CSI or spectral device out of the box. |
| Monitor mode | **Verified** — public SDK API `wifi_mgmr_sniffer_register()` / `_adv()`, backed by firmware `MM_MONITOR_REQ`. |
| Injection | **Reported** — raw frames via the sniffer path and the manufacturing raw-TX PHY API. |
| CSI | **No public path.** No per-subcarrier CSI export in the SDK; only channel-survey/RSSI indications. |
| Raw RF TX | **Yes, for test:** documented `bl_mfg_tx11b/n_start_raw(mcs, len, pwr_dbm)` and continuous-RX/TX manufacturing primitives. |
| Firmware openness | **Partially documented.** Driver/glue is Apache-2.0 source; the MAC/PHY lives in `libwifi.a` (closed) — but it ships **with DWARF debug info**, and the PHY/RF register maps have been clean-room reversed. |
| Why it's interesting | Full **schematic + datasheet + reference manual + open SDK + a real community RE project**, on a $2 RISC-V part you can buy on a dev board. Rare combination. |

## 1. The silicon

The **BL602 / BL604** is a single-core 32-bit **RISC-V** SoC with an integrated 2.4 GHz radio doing both Wi-Fi and Bluetooth LE.

| Spec | BL602 / BL604 |
|---|---|
| Core | 32-bit RISC-V, **RV32IMFC** (I, M, F single-precision FPU, C), `ilp32f` ABI |
| Clock | up to **192 MHz** |
| Memory | **276 KB RAM**, 128 KB ROM, 1 Kb eFuse, external/embedded flash |
| Wi-Fi | **802.11 b/g/n** (Wi-Fi 4), 2.4 GHz, 20 MHz, 1×1 |
| Bluetooth | **BLE 5.0** (long-range) |
| Die note | BL602 and BL604 are the **same die**; BL604 simply bonds out more GPIO. |

The `-march=rv32imfc -mabi=ilp32f` compile flags recovered from the shipped objects (see §5) are the ground truth for the ISA — a hardware single-precision FPU is present. Core specs are from the [BL602/BL604 datasheet](https://github.com/pine64/bl602-docs/blob/main/mirrored/BL602_BL604_DS_1.6_en.pdf) and [reference manual](https://github.com/pine64/bl602-docs/blob/main/mirrored/BL602_BL604_RM_1.2_en.pdf) mirrored by Pine64, and the [Bouffalo product page](https://en.bouffalolab.com/product/?type=detail&id=1).

### The rest of the family (net-new records below)

| Part | Radio | Core | Notes |
|---|---|---|---|
| **BL602 / BL604** | 802.11 b/g/n + BLE 5.0 | RV32IMFC @192 MHz | The reversed part. Same die. |
| **BL702 / BL704L** | **No Wi-Fi** — BLE 5.0 + 802.15.4 (Zigbee/Thread) | RV32 | Sibling radio; `libbl702_rf.a` RF blob, `liblmac154.a` 802.15.4 MAC. |
| **BL616 (C/CL)** | **Wi-Fi 6 (802.11ax)** 2.4 GHz + BLE 5.x + 802.15.4 | T-Head-class RV32 (E907) | Newer `bouffalo_sdk`; `ax` MAC blob, RE still early. |
| **BL618 (M/DG)** | Wi-Fi 6 + BLE + 802.15.4 | Multi-core RV32 (AP + NP cores) | BL618DG dual-core; NP core built with a Zephyr RISC-V toolchain. |
| BL808 (context) | 802.11 b/g/n + BLE + 802.15.4 | Tri-core (64-bit C906 + E907 + LP) | Linux-capable; the focus of [`openbouffalo`](https://github.com/openbouffalo) (Sipeed M1s). Usually cataloged in `../../chips/risc-v-wifi.md`. |

The official SDK's own capability matrix ([`bouffalo_sdk`](https://github.com/bouffalolab/bouffalo_sdk)) marks **WIFI4** on BL602 and **WIFI6** on BL616/BL618, and no Wi-Fi on the BL702 line — a useful sanity check when you're deciding which part to buy for a given experiment.

## 2. Wi-Fi architecture — a RivieraWaves full-MAC on a RISC-V

The single most important structural fact, and the one that shaped the whole RE effort: **the BL602 Wi-Fi MAC firmware is derived from RivieraWaves (CEVA) Wi-Fi IP.** You can read it straight off the message enum in the SDK header [`components/network/wifi/include/bl60x_fw_api.h`](https://github.com/bouffalolab/bl_iot_sdk/blob/master/components/network/wifi/include/bl60x_fw_api.h):

```c
MM_SET_CHANNEL_REQ, MM_SET_BASIC_RATES_REQ,
MM_REMAIN_ON_CHANNEL_REQ, MM_CHANNEL_SURVEY_IND,
MM_MONITOR_REQ, MM_MONITOR_CFM,
MM_MONITOR_CHANNEL_REQ, MM_MONITOR_CHANNEL_CFM,
MM_RSSI_STATUS_IND, ...
```

That `MM_*` "message + confirm + indication" host↔MAC interface is the RivieraWaves LMAC/UMAC convention (the same IP lineage seen in several other embedded Wi-Fi stacks). It matters for two reasons:

1. **It is heavily documented elsewhere**, so reversers already knew the shape of the state machine, the message flow, and the descriptor rings before opening a single function.
2. It defines a **clean legal boundary.** The `pine64/bl602-re` README is explicit that this is a *clean-room* effort — reconstruct behavior from the BL602 SDK and disassembly, and **do not** paste in `Copyright (C) RivieraWaves` source found elsewhere on the internet, or you forfeit the right to contribute.

The stack layers, top to bottom:

- **`wifi_manager` (`wifi_mgmr_*`)** — high-level connection manager, scan, sniffer, AP/STA. **Open C source** in the SDK.
- **`bl60x` low-MAC driver** — descriptor rings, `MM_*` messages to firmware. Open glue, but the firmware peer is in `libwifi.a`.
- **`libwifi.a`** — the compiled LMAC/PHY-control **blob** (runs on the *same* RISC-V core; there is no separate Wi-Fi CPU).
- **PHY + RF** — baseband/RF register programming and calibration. Register maps reversed (`reg_bz_phy.h`, `reg_rf.h`); the tuning code is in the blob.

### RF calibration is data, not magic — the RFTLV table

RF trim (crystal, per-mode power tables, channel divider tables, temperature comp) is carried as a **TLV blob** you can read and edit. The types are enumerated in [`bl_phy_api.h`](https://github.com/bouffalolab/bl_iot_sdk/blob/master/components/network/wifi/include/bl_phy_api.h):

```c
#define RFTLV_TYPE_XTAL_MODE     0x0001
#define RFTLV_TYPE_PWR_TABLE_11B 0x0005
#define RFTLV_TYPE_PWR_TABLE_11G 0x0006
#define RFTLV_TYPE_PWR_TABLE_11N 0x0007
#define RFTLV_TYPE_PWR_OFFSET    0x0008
#define RFTLV_TYPE_CHAN_DIV_TAB  0x0009   // per-channel PLL divider
#define RFTLV_TYPE_TCHANNELS     0x0022   // temperature-cal channels
#define RFTLV_TYPE_PWR_TABLE_BLE 0x0030
```

The parser is **open source** (`components/network/rfparam_adapter_tmp/rftlv/phy_rftlv.c`). This is where per-board power limits and channel-to-PLL mapping actually live — the closest thing to a "front-panel" for the radio.

## 3. What is open vs. what stays a blob

| Component | Where | Status |
|---|---|---|
| Peripheral drivers (`bl602_std`: GPIO, UART, SPI, timers, GLB/AON/HBN/PDS regs, SVD file) | SDK source | **Open** (Apache-2.0) |
| Wi-Fi manager / STA / AP / **sniffer** | `components/network/wifi` | **Open** source |
| RF-param TLV parser | `phy_rftlv.c` | **Open** source |
| Manufacturing PHY/RF test API (headers) | `bl_phy_api.h` | **Documented** interface, blob implementation |
| **Wi-Fi LMAC/PHY control** | `components/network/wifi/lib/libwifi.a` | **Blob** — but built `-gdwarf`, ships DWARF symbols/structs |
| **BLE controller** | `blecontroller_602_*.a` | **Blob** (multiple link variants) |
| Baseband PHY + RF register maps | reversed in `pine64/bl602-re` (`reg_bz_phy.h`, `reg_bz_phy_agc.h`, `reg_rf.h`, `bz_phy.c`) | **Community RE** (clean-room) |
| ROM (mask ROM API on-chip) | on-die | Blob; **symbolicated** via tchebb's script |

The headline: the *policy* layers are open, the *radio* layer is a blob — but a uniquely **friendly** blob, because Bouffalo shipped it with debug info.

## 4. The blob that reverses itself: DWARF in `libwifi.a`

The proprietary libraries were compiled with `-gdwarf`, so the archives **retain DWARF debugging data** — structure layouts, function-local variable names, and inlined-function records. Tool support for reading it out of an unlinked `.a` varies, so the working group uses [DWARF Explorer (`dwex`)](https://github.com/sevaa/dwex) to dump the raw DWARF, then feeds names/structs into Ghidra. In practice this means you are not staring at anonymous `FUN_23001abc` — you often recover the real struct field names for descriptors and PHY state. Very few Wi-Fi blobs are this cooperative.

## 5. The RE toolchain (RISC-V specifics)

The exact recipe from [`pine64/bl602-re`](https://github.com/pine64/bl602-re):

**Reproduce the build flags** (so your recompiled clean-room objects diff cleanly against the blob):

```
riscv32-unknown-elf-gcc 8.3.0 \
  -march=rv32imfc -mabi=ilp32f -gdwarf -Os -std=gnu99 \
  -ffunction-sections -fdata-sections -fstrict-volatile-bitfields \
  -fshort-enums -ffreestanding -fno-strict-aliasing
```

**Split and disassemble the archive:**

```bash
ar x libwifi.a                    # explode .a into .o objects
riscv64-unknown-elf-objdump -d -r bl60x_wifi.o > bl60x_wifi.S   # -r keeps relocations
```

**Load into Ghidra:** modern Ghidra (10.1+) disassembles RISC-V natively. For *unlinked* objects that still carry relocations, the group recommends the [ElementW Ghidra fork](https://github.com/ElementW/ghidra), which handles RISC-V relocation types the stock loader trips on. [Cutter/radare2](https://cutter.re/) is the lighter-weight alternative.

**Symbolicate the on-chip ROM:** BL602 calls into a mask-ROM API. [`tchebb/bl602-ghidra-scripts`](https://github.com/tchebb/bl602-ghidra-scripts) provides `bl602-symbolicate-romapi.py`, a Ghidra script that labels the ROM entry points so cross-references into ROM stop being dead ends.

**Diff your reconstruction:** the project ships `funcdiff.py` and `headerdiff.py` (in `script/`) to compare recompiled clean-room functions against the blob's disassembly, which is how you know a reimplementation is byte-faithful without ever copying source.

General Ghidra-on-Wi-Fi setup carries over from [`ghidra-setup-wifi-firmware.md`](ghidra-setup-wifi-firmware.md); the RISC-V-specific parts (relocations, `ilp32f` calling convention, ROM API) are the only deltas.

### Getting the artifacts

- Blobs + factory images + pre-disassembled objects: the [`bl602-re`](https://github.com/pine64/bl602-re) repo (`blobs/`, `images/`, `libbl602_wifi/`, `libblecontroller/`).
- Fresh blobs / NuttX build: [`bouffalolab/bl_blob`](https://github.com/bouffalolab/bl_blob) (the "BL peripherals static library" — the same blob `bjoernQ/bl602-wifi-rs` drives from Rust).
- Flash/dump tooling: [`BLOpenFlasher`](https://github.com/bouffalolab/BLOpenFlasher) (open flasher) and the [BL602 ISP protocol doc](https://github.com/bouffalolab/bl_docs). OpenOCD support lives in the [`openbouffalo/openocd`](https://github.com/openbouffalo) fork.

## 6. SDR-ish access — what you actually get

**Monitor / sniffer (verified).** The SDK exposes promiscuous capture as a first-class, documented API:

```c
int wifi_mgmr_sniffer_register(void *env, sniffer_cb_t cb);       // per-frame callback
int wifi_mgmr_sniffer_register_adv(void *env, sniffer_cb_adv_t cb);
int wifi_mgmr_sniffer_unregister(void *env);
```

Backed by firmware `MM_MONITOR_REQ` / `MM_MONITOR_CHANNEL_REQ`, this gives raw 802.11 frames with metadata to your callback — enough to build a channel hopper and stream frames out UART/TCP as a pcap source. This is the solid, reproducible tier-1 capability.

**Injection (reported).** With the MAC in monitor/raw mode you can hand crafted frames back down the TX path. There is no vendor "inject this exact 802.11 frame" call as clean as the sniffer, so treat this as reported rather than a turnkey API — it works in community builds but needs driver poking.

**Raw RF test TX (documented, powerful, and a foot-gun).** The manufacturing PHY API drives the radio directly:

```c
int8_t bl_mfg_tx11n_start_raw(uint8_t mcs_n, uint16_t frame_len, uint8_t pwr_dbm);
int8_t bl_mfg_tx11b_start_raw(uint8_t mcs_b, uint16_t frame_len, uint8_t pwr_dbm);
void   bl_mfg_tx_stop();
void   bl_mfg_rx_start();  void bl_mfg_rx_stop();
void   bl_mfg_channel_switch(uint8_t chan_no);
void   bl_mfg_rf_cal();
void   phy_powroffset_set(int8_t power_offset[14]);   // per-channel dBm trim
```

You choose modulation (11b rate or 11n MCS), payload length, channel, and TX power in dBm — i.e. arbitrary standards-compliant test packets and continuous carriers for bench RF work. This is **not** arbitrary-IQ/waveform synthesis (no baseband sample injection), so it does **not** reach ladder tier 4 — but it is genuine raw-PHY control, and it is the hook a spectral/energy experiment would build on.

**What's missing:** no per-subcarrier **CSI** export (the API surfaces only `MM_CHANNEL_SURVEY_IND` energy/RSSI and beamformer info), and no public **spectral-scan** register dump. The reversed `reg_bz_phy_agc.h` AGC/PHY maps make a raw-PHY probe *theoretically* reachable, but no usable CSI/spectral tool exists today — so BL602 stays at **tier 1**, honestly, with tier-3 as a research target rather than a claim.

### ⚠️ TX safety & regulatory note

`bl_mfg_tx*_start_raw` and continuous-carrier modes emit **real RF in the 2.4 GHz ISM band**. A continuous test carrier is **not** a spread-spectrum Wi-Fi signal and can violate emission/duty-cycle limits and stomp on real networks. Only run raw/continuous TX **into a dummy load or shielded enclosure with proper attenuation**, keep power at the minimum that proves the point, and know your local rules (FCC Part 15 / ETSI EN 300 328 / your national regulator). Do not radiate custom carriers over the air on a shared band. See [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md).

## 7. Reproducible starting point

```bash
# 1. Get the SDK and a blob to reverse
git clone https://github.com/bouffalolab/bl_iot_sdk
git clone https://github.com/pine64/bl602-re           # blobs/, disassembly, scripts

# 2. Explode + disassemble the Wi-Fi blob
cd bl602-re/blobs
ar x libwifi.a
riscv64-unknown-elf-objdump -d -r bl60x_wifi.o | less   # -r shows relocations

# 3. Pull DWARF structs/names straight out of the archive
pip install dwex && dwex libwifi.a                       # browse structs, locals

# 4. Load bl60x_wifi.o in Ghidra (ElementW fork for reloc-carrying objects),
#    then run tchebb's ROM symbolication script so ROM calls resolve.

# 5. Build a sniffer image from the SDK's demo and stream frames as pcap:
cd bl_iot_sdk/customer_app/bl602_demo_wifi
make CONFIG_CHIP_NAME=BL602        # register wifi_mgmr_sniffer_register() in app
```

For a Rust-side path that *uses* the blob rather than reversing it, [`bjoernQ/bl602-wifi-rs`](https://github.com/bjoernQ/bl602-wifi-rs) drives the NuttX `bl_blob` (scan/connect/BLE working), and [`sipeed/bl602-hal`](https://github.com/sipeed/bl602-hal) + `bl602-pac` give an open peripheral layer.

## 8. Hardware you can buy

PineCone **BL602 EVB** (the board created specifically to seed the Nutcracker challenge), Sipeed BL602 / RV-Debugger boards, **Ai-Thinker Ai-WB2** modules (BL602), DT-BL10, and a long tail of BL602-based smart-home devices flashable with [OpenBeken/`OpenBK7231T_App`](https://github.com/openshwprojects/OpenBK7231T_App). For Wi-Fi 6 experiments the **BL616-DK** / **BL618-DK** dev kits use `bouffalo_sdk`; for Linux-on-RISC-V-with-radio, the BL808-based Sipeed M1s under [`openbouffalo`](https://github.com/openbouffalo).

## 9. Related pages

- [`../../chips/risc-v-wifi.md`](../../chips/risc-v-wifi.md) — the RISC-V Wi-Fi landscape (ESP32-C/-S RISC-V, BL808, etc.).
- [`../../chips/espressif.md`](../../chips/espressif.md) — contrast: ESP32 exposes real **CSI** and reaches higher tiers.
- [`../firmware-reversing.md`](../firmware-reversing.md) · [`../techniques.md`](../techniques.md) · [`ghidra-setup-wifi-firmware.md`](ghidra-setup-wifi-firmware.md).
- [`../taxonomy.md`](../taxonomy.md) for the tier/flag definitions used above.

## References

- BL602 IoT SDK (Apache-2.0): https://github.com/bouffalolab/bl_iot_sdk
- `bl_phy_api.h` (mfg RF/PHY API, RFTLV types): https://github.com/bouffalolab/bl_iot_sdk/blob/master/components/network/wifi/include/bl_phy_api.h
- `bl60x_fw_api.h` (RivieraWaves `MM_*` message set, monitor mode): https://github.com/bouffalolab/bl_iot_sdk/blob/master/components/network/wifi/include/bl60x_fw_api.h
- BouffaloSDK (BL602/BL702/BL616/BL618, WIFI4/WIFI6 matrix): https://github.com/bouffalolab/bouffalo_sdk
- `bl_blob` (NuttX/peripheral static libs): https://github.com/bouffalolab/bl_blob
- Pine64 BL602 reverse-engineering working group: https://github.com/pine64/bl602-re
- Pine64 BL602 docs (datasheet + reference manual mirror): https://github.com/pine64/bl602-docs
- BL602/BL604 datasheet (PDF): https://github.com/pine64/bl602-docs/blob/main/mirrored/BL602_BL604_DS_1.6_en.pdf
- BL602/BL604 reference manual (PDF): https://github.com/pine64/bl602-docs/blob/main/mirrored/BL602_BL604_RM_1.2_en.pdf
- tchebb BL602 Ghidra scripts (ROM symbolication): https://github.com/tchebb/bl602-ghidra-scripts
- bjoernQ BL602 Wi-Fi from Rust (drives the blob): https://github.com/bjoernQ/bl602-wifi-rs
- Sipeed BL602 HAL (open peripheral layer): https://github.com/sipeed/bl602-hal
- Nutcracker challenge: https://wiki.pine64.org/wiki/Nutcracker · https://pine64.org/documentation/PineCone/
- BLOpenFlasher (open flasher): https://github.com/bouffalolab/BLOpenFlasher
- openbouffalo (BL808/Linux, OpenOCD fork): https://github.com/openbouffalo
- Bouffalo BL602 product page: https://en.bouffalolab.com/product/?type=detail&id=1
- DWARF Explorer (`dwex`): https://github.com/sevaa/dwex · ElementW Ghidra RISC-V fork: https://github.com/ElementW/ghidra
