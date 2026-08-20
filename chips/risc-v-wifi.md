# RISC-V and open(ish) Wi-Fi silicon

*Cycle 5 — the most-open end of the Wi-Fi world.*

Every other chip in this catalog is a black box with an open crack pried into it. This file looks at the opposite starting point: parts where the **application processor is an open ISA (RISC-V)**, the SDK is Apache-2.0, the toolchain is upstream GCC/LLVM, and an active community has already pointed Ghidra at the remaining closed pieces. These are not software-defined radios. But if you rank Wi-Fi silicon by *how much of the stack you can read and replace*, the RISC-V combos from **Bouffalo Lab** and **Espressif** sit closer to "open Wi-Fi" than anything short of an FPGA PHY like [openwifi](../projects/openwifi.md).

The thesis of this file: **RISC-V + community reverse-engineering is producing the closest thing to open Wi-Fi that exists on commodity silicon** — not because the PHY is open (it almost never is), but because everything *around* the PHY blob is, and the blob itself is now small, well-understood, and shared across so many vendors that reversing it once benefits the whole ecosystem.

---

## 1. The openness gradient

"Open Wi-Fi" is not a binary. It is a stack, and each layer can be open, documented, patchable, or a sealed blob. The interesting RISC-V parts are open at the top and closed at the very bottom:

| Layer | What it is | Bouffalo BL | ESP32-C/P4 | Truly open (openwifi) |
|---|---|---|---|---|
| Application firmware | Your RTOS / bare-metal code | **Open** (yours) | **Open** (yours) | Open |
| SDK / HAL / drivers | Peripheral + net glue | **Open** (Apache-2.0) | **Open** (Apache-2.0, ESP-IDF) | Open |
| CPU / ISA | Instruction set | **Open** (RISC-V) | **Open** (RISC-V) | Open (softcore) |
| 802.11 upper-MAC (UMAC) | Assoc / auth / WPA state machine | **Blob**, largely reversed | **Blob** (`libnet80211`) | **Open (HDL)** |
| 802.11 lower-MAC + PHY | Framing, timing, modulation | **Blob** (RivieraWaves-derived) | **Blob** (`libpp`) | **Open (HDL)** |
| RF front-end / calibration | Analog + cal tables | **Blob** | **Blob** (`libphy`, RF cal) | Open |

Two honest consequences:

- **The wall is always the same wall.** Both Bouffalo and Espressif license or derive their Wi-Fi MAC/PHY from third-party IP. Lup Yuen's teardown of the BL602 driver traced its lineage to **CEVA RivieraWaves** UMAC/LMAC — the exact same Wi-Fi IP family licensed into countless SoCs. Reversing it on one RISC-V part is directly transferable knowledge.
- **You still own everything else.** Unlike a Broadcom or Qualcomm part where even the host driver is a mystery, here the coprocessor mailbox, the RX/TX descriptors, the calibration hand-off, and the promiscuous-mode path are all in Apache-2.0 source you can read. That is what makes these the best *substrate* for climbing the [SDR ladder](../docs/taxonomy.md) by RE, even though they ship at Tier 1–2.

See [firmware-reversing.md](../docs/firmware-reversing.md) for the general method and [true-sdr-comparison.md](../docs/true-sdr-comparison.md) for why none of this reaches raw-IQ.

---

## 2. Bouffalo Lab BL-series (RISC-V Wi-Fi/BLE, community-reversed)

Bouffalo Lab is the poster child. The chips are cheap, the [`bouffalo_sdk`](https://github.com/bouffalolab/bouffalo_sdk) is Apache-2.0, and Pine64/Sipeed shipped open dev boards that pulled a hobbyist RE community in. The Wi-Fi firmware is still a closed coprocessor blob, but it is the **most-reversed Wi-Fi blob on any current RISC-V part**.

### 2.1 The lineup

| Chip | Wireless | RISC-V core(s) | Notable boards |
|---|---|---|---|
| **BL602 / BL604** | Wi-Fi 4 (b/g/n) + BLE 5.0, 2.4 GHz | 1× SiFive E24-class RV32 @192 MHz | Pine64 PineCone BL602 EVB, Ai-Thinker modules |
| **BL616 / BL618** | Wi-Fi 6 (ax) + BLE 5.3 + 802.15.4, 2.4 GHz | 1× T-head E907-class RV32 @320 MHz | Sipeed M0S Dock, M0P Dock |
| **BL808** | Wi-Fi 4 + BLE 5.0 + 802.15.4, 2.4 GHz | 3× (C906 64-bit @480 MHz + C906 32-bit @320 MHz + E902 LP), NPU | Sipeed M1s Dock, Pine64 Ox64 |

> **BL606P** is a Bouffalo RISC-V part too, but it is an audio/AIoT SoC (dual C906) **without a confirmed integrated Wi-Fi radio**, so it is intentionally omitted from the radio records below rather than listed with fabricated capabilities. Treat any "BL606 Wi-Fi" claim as unverified.

### 2.2 What the community actually reversed (BL602)

This is the concrete, reproducible part — see the companion walkthrough [bl602-wifi-re.md](../docs/walkthroughs/bouffalo-bl602-wifi-re.md).

- **The blob's origin was identified.** Decompilation (Ghidra, RISC-V processor module) showed the BL602 Wi-Fi driver matches **RivieraWaves UMAC** code plus a `wpa_supplicant` port — meaning symbol names and struct layouts from public RivieraWaves-derived sources can be matched against the dump instead of guessed. This is the single highest-leverage RE finding: *don't reverse blind, diff against the known IP*.
- **Undocumented registers were mapped** by correlating the open SDK's register accesses with the blob's MMIO reads/writes.
- **The gap is the crypto/auth path.** As documented, "a big chunk of the BL602 Wi-Fi driver doesn't come with source" — the WPA authentication functions in particular. Those are what a fully open driver still needs.

How to reproduce the *starting point* in your own dump (no invented offsets — find them yourself):
1. Flash the open `bouffalo_sdk` Wi-Fi demo; dump the running image + the bundled Wi-Fi firmware blob.
2. Load into Ghidra as **`RISCV:LE:32:default`** (the mature built-in RISC-V module; see [ghidra-setup-wifi-firmware.md](../docs/walkthroughs/ghidra-setup-wifi-firmware.md)).
3. Import the SDK's public symbols/headers so the *open* half is named. The named functions bracket the blob.
4. String-search for RivieraWaves/UMAC tokens (`rwnx`, `me_`, `sm_`, `mm_`, `scanu_`) — matches confirm the IP lineage and let you pull field names from public RivieraWaves-derived driver trees rather than inventing them.

### 2.3 Linux on BL808 — openbouffalo

The [openbouffalo](https://github.com/openbouffalo) project runs Linux on the BL808's 64-bit C906 core; [`buildroot_bouffalo`](https://github.com/openbouffalo/buildroot_bouffalo) is a Buildroot overlay producing Linux images for BL808 boards (Pine64 Ox64 confirmed). This matters for RE because it moves the Wi-Fi driver into a *Linux* address space where standard tooling (`ftrace`, `devmem`, kernel mailbox drivers) can instrument the coprocessor hand-off far more easily than on bare-metal RTOS. The Wi-Fi driver itself remains a work-in-progress wrapper around the same blob.

### 2.4 SDR reality check

BL parts ship at **Tier 1**: monitor mode is exposed by the SDK, and injection is reachable through the reversed MAC path. There is no documented CSI, spectral-scan, or raw-IQ interface. What makes them special is not their native capability — it is that the road from Tier 1 to a fully open Tier 5 driver is shorter here than anywhere else in the catalog, because you can already read 90% of the stack.

---

## 3. Espressif RISC-V (ESP32-C series + ESP32-P4)

Espressif switched its low-cost line from Xtensa to RISC-V. The [ESP-IDF](https://github.com/espressif/esp-idf) SDK is Apache-2.0 and superbly documented, but the Wi-Fi MAC/PHY ships as **precompiled binaries** (`libnet80211.a`, `libpp.a`, `libphy`) — open glue, closed radio. See [espressif.md](espressif.md) for the full family and the [esp32-c3 Ghidra walkthrough](../docs/walkthroughs/esp32-xtensa-ghidra.md) (Xtensa; the C-series is RISC-V, load as `RISCV:LE:32:default`).

### 3.1 Existing records (referenced, not re-described)

These already live in the catalog — reference by id:

| id | Chip | Wireless | Core |
|---|---|---|---|
| `espressif-esp32-c2` | ESP32-C2 (ESP8684) | Wi-Fi 4 + BLE 5, 2.4 GHz | 1× RV32 @120 MHz |
| `espressif-esp32-c3` | ESP32-C3 | Wi-Fi 4 + BLE 5, 2.4 GHz | 1× RV32 @160 MHz |
| `espressif-esp32-c5` | ESP32-C5 | **Wi-Fi 6, dual-band 2.4 + 5 GHz** + BLE 5.3 | 1× RV32 @240 MHz |
| `espressif-esp32-c6` | ESP32-C6 | Wi-Fi 6 (2.4 GHz) + BLE 5.3 + 802.15.4 | HP RV32 @160 MHz + LP core |

**ESP32-C5 is the standout for this catalog**: Espressif's first dual-band part puts a *5 GHz-capable* RISC-V radio in a hobbyist-priced package — the natural target if 5 GHz CSI/monitor work moves off Xtensa.

### 3.2 CSI — the one native rung above Tier 1

ESP-IDF exposes **Channel State Information** (`esp_wifi_set_csi`, `wifi_csi_info_t`) on the ESP32 line including the RISC-V C-series, with Espressif's own [esp-csi](https://github.com/espressif/esp-csi) reference apps. That puts C3/C5/C6/C61 at **Tier 2** out of the box — subcarrier amplitude/phase per received frame, usable for presence/motion sensing. See [csi-toolchains.md](../projects/csi-toolchains.md) and [verification-tier2-csi.md](../docs/verification-tier2-csi.md).

### 3.3 New records added here

- **ESP32-C61** — cost-optimized Wi-Fi 6 (2.4 GHz) + BLE 5, single RISC-V core. Essentially a C6 with the 802.15.4 radio removed to hit a lower price; same ESP-IDF, same CSI API, same closed `libpp`/`libnet80211` blob.
- **ESP32-P4** — the honest edge case. A high-performance **dual-core RV32IMAFC @400 MHz application processor with *no integrated radio at all***. It gets Wi-Fi/BLE only through a companion ESP32-C5/C6 over SDIO/SPI using [esp-hosted](https://github.com/espressif/esp-hosted). It earns a record as a family member and as a caution: RISC-V + Espressif does **not** imply "a radio," and the P4 is Tier 0 for SDR purposes. Its value here is the *fully open, documented* HAL — the P4 is the most-open Espressif chip precisely because it has no radio blob to hide.

---

## 4. Sipeed / Allwinner combos — the closed foil

Sipeed also ships boards around **Allwinner RISC-V** application processors (D1/D1s = T-head C906). These make the openness contrast sharp: the *CPU* is open RISC-V, but **Allwinner parts have no integrated Wi-Fi** and are paired with an external module whose firmware is a sealed blob:

- **XRadio XR829** (Xradio is an Allwinner subsidiary) — 2.4 GHz Wi-Fi 4 + BT combo, firmware distributed as an opaque binary with a vendor kernel driver. No community RE traction comparable to Bouffalo.
- **Realtek RTL8723DS** — common alternative; see [other-vendors.md](other-vendors.md) / [realtek.md](realtek.md).

So a Lichee RV / Nezha board is "open RISC-V Linux" bolted to a **closed** Wi-Fi part — the opposite of the Bouffalo model, where the radio and the CPU are the *same* reversible RISC-V SoC. This is why the BL808 (radio + Linux-capable RISC-V on one die, one community, one blob) is the more interesting open-Wi-Fi vehicle than any Allwinner+external-module combo.

---

## 5. Where this leaves "open Wi-Fi"

| Approach | CPU | Driver/SDK | 802.11 PHY/MAC | Verdict |
|---|---|---|---|---|
| Bouffalo BL602/808 | Open RISC-V | Open (Apache-2.0) | Closed blob, ~largely reversed | **Closest practical open Wi-Fi** |
| Espressif C5/C6/C61 | Open RISC-V | Open (ESP-IDF) | Closed blob (`libpp`) | Open host, sealed radio; native CSI (Tier 2) |
| Allwinner D1 + XR829 | Open RISC-V | Vendor | Closed blob, un-reversed | Open CPU, closed radio |
| [openwifi](../projects/openwifi.md) | Softcore/ARM | Open | **Open HDL PHY** | Only genuinely open PHY (needs FPGA/SDR) |

The takeaway for this catalog: **the RISC-V combos don't beat an FPGA PHY on openness of the radio itself, but they beat everything else on openness of the whole system** — and that is what makes them the practical frontier for community RE. The remaining blob is small, shared (RivieraWaves/CEVA), and already partly cracked. If a fully open commodity Wi-Fi driver ever ships, the evidence in this file says it lands on a Bouffalo BL-series part first.

### References

- Bouffalo `bouffalo_sdk` (Apache-2.0): https://github.com/bouffalolab/bouffalo_sdk
- Bouffalo `bl_iot_sdk` (BL602/BL70x): https://github.com/bouffalolab/bl_iot_sdk
- openbouffalo Buildroot (Linux on BL808): https://github.com/openbouffalo/buildroot_bouffalo
- openbouffalo org: https://github.com/openbouffalo
- Lup Yuen Lee — "BL602 Wi-Fi Driver reverse engineering" (RivieraWaves lineage, Ghidra): https://lupyuen.github.io/articles/wifi
- Espressif SoC lineup: https://www.espressif.com/en/products/socs
- Espressif ESP-IDF: https://github.com/espressif/esp-idf
- Espressif esp-csi (CSI reference apps): https://github.com/espressif/esp-csi
- Espressif esp-hosted (ESP32-P4 companion radio): https://github.com/espressif/esp-hosted
- ESP32 family (Wikipedia): https://en.wikipedia.org/wiki/ESP32
