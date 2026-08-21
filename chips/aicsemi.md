# AICSemi (爱旌 / Aightec) — AIC8800 family

> **Primary-source entry.** Everything on this page was verified **first-hand** on an RK3588 SBC carrying an AIC8800D81 USB module (`a69c:8d81`), firmware `v6.4.3.1` (build `Jan 04 2024 - g32003198`), DKMS driver `aic8800-usb 3.0+git20240327.3561b08f`. Where a claim comes from the shipped driver source or the firmware blob itself, it is called out. See the reproducible walkthrough: [../docs/walkthroughs/aic8800-rivierawaves-firmware-re.md](../docs/walkthroughs/aic8800-rivierawaves-firmware-re.md).

**AICSemi** (Shanghai) is a low-cost Chinese Wi-Fi/BT combo vendor whose **AIC8800** line shows up all over the RK3588/RK3566 SBC and Android-TV-box world (often as the cheaper alternative to an AMPAK/Broadcom AP6xxx or a Realtek RTL8852BE). It is **not** a Broadcom/Atheros-class part with a research following — there is no Nexmon-equivalent — but it is one of the most *approachable* firmware-RE targets in the catalog, for three reasons this page documents: a clean ARM Cortex-M image, a **licensed RivieraWaves RW-nX MAC** whose symbol names leak through assert strings, and a **vendor-provided firmware patch-table mechanism** you can hook without reflashing.

## Parts

| Part | USB PID | Bands | Wi-Fi | Notes |
|---|---|---|---|---|
| AIC8800 | `0x8800` | 2.4 GHz | 11n | Base SDIO/USB combo |
| AIC8801 | `0x8801` | 2.4 GHz | 11n | Variant |
| AIC8800DC / DW | `0x88dc` / `0x88dd` | 2.4 GHz | 11n | "DC"/"DW" low-cost combo, separate calib firmware |
| AIC8800D80 / **D81** | `0x8d81` | 2.4 + **5 GHz** | **11ax (Wi-Fi 6)** | Dual-band; **this is the analyzed part** |

Vendor USB ID `0xA69C`. Bus options: USB, SDIO, PCIe (D80). BT is a separate USB function driven by `aic_btusb`.

## Firmware architecture (from the blob)

- **CPU:** ARM **Cortex-M, Thumb-2**. The `fmacfw*.bin` images open with a textbook Cortex-M vector table — word[0] = initial SP (`0x0018_4000`), word[1] = reset handler (`0x0011_0191`, Thumb/odd), followed by exception vectors all in `0x0011_xxxx`.
- **Load base:** `0x0011_0000` for the RAM image (reset lands at file offset `0x190`, right after the vector table). RAM/stack region up around `0x0018_4000`.
- **MAC stack:** **RivieraWaves RW-nX** ("`rwnx`"). Assert strings expose the internals verbatim — `nxmac_current_state_getf()`, `nxmac_tx_ac_0_state_getf()`, `ke_state_get(TASK_SCAN)`, `KE_BUILD_ID(TASK_BAM, ...)`, `rwnxl_reset_evt`, `scan_start_req_handler`. This is the same IP lineage flagged for RE in [risc-v-wifi.md](risc-v-wifi.md) (search tokens `rwnx`/`me_`/`sm_`/`mm_`/`scanu_`).
- **PHY/RF entry points** appear as named strings: `phy_set_channel`, `phy_hw_set_channel`, `phy_get_channel`, `phy_stop`, plus RF calibration (`wfrf calib`, `wf dccalib begin!/end!`).
- **Blob set:** `fmacfw*.bin` (full-MAC application), `lmacfw_rf*.bin` (lower-MAC/RF), `fw_patch*.bin` + `fw_patch_table*.bin` (**ROM patch table**), `fw_ble_scan*.bin` (BLE), `fw_adid*.bin`, `m2d_ota.bin`. Entropy of `fmacfw.bin` is ~6.9 (dense but uncompressed code + tables; not packed).

## Why it's an unusually good RE target

1. **Open driver source ships with it.** The DKMS tree (`/usr/src/aic8800-usb-*/`) is full C — `rwnx_main.c`, `rwnx_tx.c`, `lmac_msg.h`, `rwnx_radar.c`, `rwnx_bfmer.c`. The host side of every firmware message (the `MM_*`/`SCANU_*`/`ME_*` command IDs in `lmac_msg.h`) is right there, so you never reverse the host↔firmware protocol blind.
2. **RivieraWaves symbols are public.** Other RW-nX-derived trees (`ecrnx`, `fullmac` drivers) name the same structs/functions — free labels for Ghidra.
3. **A built-in patch mechanism.** `fw_patch_table.bin` is a `{ROM address → replacement}` table the host uploads at load. That is *exactly* the redirect primitive Nexmon has to inject on Broadcom — here it is vendor-sanctioned, so you can reroute a ROM function to your own code **without reflashing**.

## SDR-ladder placement — **Tier 1 (verified), with an honest RE path upward**

| Capability | Status | Evidence |
|---|---|---|
| **Monitor** | ✅ verified | Driver registers `NL80211_IFTYPE_MONITOR` (`rwnx_main.c`); radiotap RX path in `rwnx_rx.c`. |
| **Injection** | ✅ verified (in-driver) | `mgmt_tx` + `<net/ieee80211_radiotap.h>` in `rwnx_tx.c`; monitor-vif TX path present. |
| CSI | ❌ not exposed | No CSI/channel-state readout anywhere in the driver. Would require a firmware patch tapping the PHY channel estimator. |
| Spectral scan | ⚠️ partial/coarse | Only standard cfg80211 **survey** (per-channel `NOISE(dBm)`/busy-time) via debugfs — not a readable FFT. |
| DFS radar | ⚠️ detection-only | `rwnx_radar.c` is a real pulse-width/PRI/PPB DFS **pattern matcher** — regulatory detection, **not** a radar you can steer or read raw pulses from. Not tagged `radar` to avoid conflating it with FMCW silicon. |
| Beamforming feedback | ⚠️ present | `rwnx_bfmer.c` handles compressed BF reports (MU-MIMO sounding) — a channel-feedback primitive, sensing-adjacent but not CSI. |

**Verdict:** a solid, cheap **Tier 1** monitor/injection radio today. The combination of a documented RW-nX PHY (named `phy_*` functions, a beamformer, a DFS pulse engine) **and** a built-in patch table makes a **Tier 2/3 firmware mod (CSI or spectral readout) genuinely plausible** — but nobody has published one, so that remains **theoretical**, not a claim of this catalog. If you want to be the first, this page + the walkthrough are your starting map.

## Un-cataloged / TODO
- Confirm 5 GHz behaviour and DFS on the D81 vs the 2.4-only DC/DW.
- Map the `fw_patch_table` binary format and demonstrate a no-op ROM redirect (the "hello world" of patching this part).
- Trace `phy_hw_set_channel` → the RF/PLL programming and the `wfrf calib` DC-calibration path; identify the channel-estimator output buffer (the CSI candidate).
- SDIO/PCIe (D80) firmware differences; the `lmacfw_rf` lower-MAC image as a separate Ghidra target.

## References
- **Primary:** first-hand analysis on-device (RK3588, AIC8800D81 `a69c:8d81`, fw `v6.4.3.1`), firmware under `/lib/firmware/aic8800_fw/`, driver `/usr/src/aic8800-usb-3.0+git20240327.3561b08f`.
- Debian/Radxa packaging: `aic8800-usb-dkms` / `aic8800-firmware` (`3.0+git20240327.3561b08f`).
- RivieraWaves RW-nX MAC lineage — cross-driver symbol source (`ecrnx`/`fullmac` public trees).
- Ghidra load recipe and symbol-harvest procedure: [../docs/walkthroughs/aic8800-rivierawaves-firmware-re.md](../docs/walkthroughs/aic8800-rivierawaves-firmware-re.md) · foundations in [../docs/walkthroughs/ghidra-setup-wifi-firmware.md](../docs/walkthroughs/ghidra-setup-wifi-firmware.md).
