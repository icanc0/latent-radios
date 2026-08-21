# Reversing the AICSemi AIC8800 firmware (RivieraWaves, ARM Cortex-M)

> **This is a primary-source walkthrough.** Every command and address below was run first-hand on an **RK3588 SBC with an AIC8800D81 USB module** (`a69c:8d81`), firmware **`v6.4.3.1`** (build `Jan 04 2024 - g32003198`), driver **`aic8800-usb 3.0+git20240327.3561b08f`**. If you have any RK3588/RK3566 board, an Android TV box, or a cheap "AIC8800" USB dongle, you very likely have this exact silicon — check with `lsusb | grep a69c`. Chip background: [../../chips/aicsemi.md](../../chips/aicsemi.md). Ghidra fundamentals: [ghidra-setup-wifi-firmware.md](ghidra-setup-wifi-firmware.md).

The AIC8800 is the friendliest firmware-RE target in the catalog that *isn't* already done to death by researchers. You get: a clean ARM Cortex-M image, a licensed **RivieraWaves RW-nX** MAC whose function names leak through assert strings, the **full driver source on disk**, and a **vendor patch-table** you can hook without reflashing. This walkthrough takes you from "what's my chip" to "Ghidra is showing me named MAC/PHY functions."

---

## 0. Confirm you have the part

```bash
lsusb | grep -i a69c                 # a69c:8d81 = AIC8800D81 (USB Wi-Fi 6)
readlink -f /sys/class/net/wlan0/device/driver   # -> .../aic8800_fdrv
lsmod | grep -iE 'aic8800|aic_load_fw'
```

USB PIDs in the family (from `aicwf_usb.h`): `0x8800` AIC8800, `0x8801` AIC8801, `0x88dc` AIC8800DC, `0x88dd` AIC8800DW, `0x8d81` AIC8800D80/D81. Vendor `0xA69C`.

## 1. Get the blob (no hardware dump needed)

The firmware ships as flat files — nothing to extract off the chip:

```bash
ls -l /lib/firmware/aic8800_fw/USB/aic8800/
#   fmacfw.bin              <- full-MAC application firmware  (your Ghidra input)
#   lmacfw_rf.bin           <- lower-MAC / RF core (separate target)
#   fw_patch.bin            <- ROM patch payload
#   fw_patch_table.bin      <- {ROM address -> replacement} table  (the hook mechanism)
#   fw_ble_scan.bin         <- BLE
cp /lib/firmware/aic8800_fw/USB/aic8800/fmacfw.bin ~/aic_fmacfw.bin
```

For the **D80/D81** the app image is `USB/aic8800D80/fmacfw_8800d80_u02.bin`; the SDIO/PCIe trees hold the same set. Start with the plain `fmacfw.bin` — it's the smallest complete MAC image.

## 2. Fingerprint the architecture (5 minutes, saves hours)

**Read the header as words.** A Cortex-M image *is* its vector table:

```python
import struct
d = open("aic_fmacfw.bin","rb").read()
sp, reset = struct.unpack_from("<II", d, 0)
print(hex(sp), hex(reset))        # 0x184000 0x110191
for i in range(1,8):
    print(i, hex(struct.unpack_from("<I", d, i*4)[0]))
```

Observed:

```
SP    = 0x00184000        # word[0] = initial stack pointer
reset = 0x00110191        # word[1] = reset handler, ODD -> Thumb
[2..] = 0x0011f111 0x0011f505 0x0011f50d 0x0011f515 0x0011f51d ...  # all odd, all 0x0011_xxxx
```

Two things fall out immediately:

- **Processor = ARM Cortex-M, Thumb-2.** Every vector is odd (Thumb) and clusters in one region.
- **Load base = `0x0011_0000`.** `reset & ~1 = 0x110190`; if the file loads at `0x110000`, the reset handler sits at **file offset `0x190`** — exactly where code should start, right after a ~100-entry vector table. The SP at `0x184000` marks the top of RAM.

**Corroborate with strings** (this is the payoff — RivieraWaves leaves its names in asserts):

```bash
strings -n 5 aic_fmacfw.bin | grep -iE 'nxmac|rwnx|ke_state|TASK_|phy_|calib|build'
```

```
%s - build: %s
rwnx_env.prev_hw_state == nxmac_current_state_getf()
ke_state_get(KE_BUILD_ID(TASK_BAM, bam_idx)) == BAM_DELETE
nxmac_tx_ac_0_state_getf() != 2
phy_hw_set_channel
phy_set_channel
wf dccalib begin!
li Jan 04 2024 21:58:09 - g32003198          # build stamp
v6.4.3.1                                       # firmware version
```

`nxmac_*_getf()`, `ke_state_get(TASK_*)`, `rwnx_env` → **RivieraWaves RW-nX**. This tells you where to get free symbols (§5).

> If you have `binwalk`+`cpu_rec`, `binwalk -% aic_fmacfw.bin` should report ARM across the code region. But the vector-table read above is faster and decisive.

## 3. Load into Ghidra

- **File → Import File →** `aic_fmacfw.bin`
- **Language:** `ARM:LE:32:Cortex`  (Thumb-2)
- **Options… → Base Address:** `0x00110000`
- Import, but **don't auto-analyze yet** — fix the memory map first.

## 4. Memory map

Add blocks so absolute pointers resolve (Cortex-M code is full of `LDR Rn,[PC,#imm]` literal loads):

| Block | Start | Notes |
|---|---|---|
| `CODE` (the .bin) | `0x00110000` | mark **executable**; length = file size |
| `RAM` | `~0x00180000` | data/stack region; SP = `0x00184000` sits here |

If some literal-pool targets still land unmapped after analysis, widen `RAM` downward — the vendor links code low and RAM high in the same `0x001x_xxxx` space. Then **Analysis → Auto Analyze** (keep ARM Aggressive Instruction Finder on).

**Sanity check:** after analysis, `reset` at `0x110190` should be a function; its early body does the usual `.data` copy / `.bss` clear then branches into init. If instead you see a wall of `??`, your base is wrong — re-read §2.

## 5. Get symbols for free (this is why AIC8800 is easy)

Three independent symbol sources, in order of value:

1. **Assert strings → function names.** RW-nX asserts embed the *expression that failed*, e.g. `nxmac_current_state_getf() != HW_IDLE`. Find the string, follow its xref to the `assert`/`printf` call, and the enclosing function is almost always the one named in the string. `strings -n 6 aic_fmacfw.bin | grep -cE '_getf\(\)|_handler|TASK_|phy_'` returns ~50 such anchors here.

2. **The console `printf`.** Locate `%s - build: %s` (or any `%d`/`%s`), xref to its common callee — that callee is the logger. Every caller is an event handler you can name from its format string. (RW-nX logger ≈ `dbg_print`/`ke_msg`-adjacent.)

3. **The driver source names the protocol.** The DKMS tree is on disk:
   ```bash
   ls /usr/src/aic8800-usb-*/USB/driver_fw/drivers/aic8800/aic8800_fdrv/
   #   lmac_msg.h   <- ALL host<->fw message IDs: MM_*, SCANU_*, ME_*, MM_ROC_OP_START ...
   #   rwnx_radar.c <- DFS pulse detector (radar pattern specs)
   #   rwnx_bfmer.c <- beamforming-report handling
   ```
   `lmac_msg.h` gives you the exact command enum the firmware dispatches on. Cross-referencing a message ID constant in Ghidra lands you on the firmware-side handler for that command — the fastest way to find `scanu_*`, `mm_*`, and the TX path.

Other public **RivieraWaves-derived** trees (`ecrnx`, various `fullmac` drivers) name the same structs — use them as a labeling dictionary.

## 6. Where to go for the SDR-ladder payoff

The point of this catalog is climbing the [ladder](../taxonomy.md). AIC8800 is verified **Tier 1** (monitor + injection — the driver registers `NL80211_IFTYPE_MONITOR` and has a radiotap TX path). The *interesting* work is whether the PHY can be coaxed to Tier 2/3. Anchors to chase:

- **`phy_hw_set_channel` / `phy_set_channel`** → the RF/PLL programming. Understand channel selection first; it gates everything.
- **`wf dccalib` / `wfrf calib`** → the RF calibration path. The DC/IQ calibration routines touch the same ADC/mixer registers a spectral or CSI tap would.
- **The RX descriptor / PHY-status path** (`hal_desc.h` in the driver names the RX descriptor fields) → find where per-packet PHY metadata (RSSI/EVM/rate) is written. The **channel-estimator output**, if it is ever DMA'd to a buffer, is your **CSI candidate**.
- **The patch table.** `fw_patch_table.bin` is a `{address → replacement}` list the host uploads at load (see `rwnx_platform.c` / the load path in `aic_load_fw`). Map its binary format, then redirect one ROM function to a no-op as a "hello world" — that proves you can inject code **without reflashing**, which is the whole game for adding a CSI/spectral dump.

**Honest status:** no public CSI/spectral mod for this part exists yet. The ingredients (named PHY functions + beamformer + DFS pulse engine + a built-in patch mechanism) make it *plausible*, not done. If you build it, you'd be first — and it'd be a genuine Tier-2 promotion for this record.

## 7. Safety

Everything through §5 is **static, read-only** — no RF. You only enter regulatory territory when you *upload a modified patch/firmware* that changes channels, power, or waveform. At that point keep TX on a wired/attenuated path in a shielded setup and respect your band plan — see [../verification-tier4.md](../verification-tier4.md) and [../rf-safety-and-legal.md](../rf-safety-and-legal.md).

## References
- Primary: on-device analysis (RK3588 / AIC8800D81 `a69c:8d81`, fw `v6.4.3.1`); `/lib/firmware/aic8800_fw/`, `/usr/src/aic8800-usb-3.0+git20240327.3561b08f`.
- RivieraWaves RW-nX MAC lineage (shared symbol names across `ecrnx`/`fullmac` driver trees).
- Ghidra + firmware fundamentals: [ghidra-setup-wifi-firmware.md](ghidra-setup-wifi-firmware.md) · taxonomy: [../taxonomy.md](../taxonomy.md) · chip page: [../../chips/aicsemi.md](../../chips/aicsemi.md).
