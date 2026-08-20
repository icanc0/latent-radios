# Spot-check audit, batch 2: catalog vs datasheets

*Cycle 8 meta-verification pass.* This is the second sampling audit of *Latent Radios*, a companion to [batch 1](./spot-check-audit-catalog-vs-datasheets.md). Where batch 1 stress-tested the classic Wi-Fi/CSI/SDR core of the catalog, this pass deliberately samples the **newer cycle-5..7 additions** — RISC-V Wi-Fi SoCs, cellular-IoT modems, mmWave/UWB radar silicon, and retro/IoT transceivers — because new families are where structured claims are least battle-tested. Each machine-readable claim (`bands`, `standards`, `sdr_capabilities`, `sdr_tier`, firmware arch) is compared against a **primary source**: a vendor datasheet/product page, a kernel/RTOS driver, or the reverse-engineering project that unlocks the part.

Method and record shape are unchanged from batch 1 and are defined in [methodology.md](./methodology.md); the schema being audited is [../data/schema.json](../data/schema.json).

## Method

- **Sample (18 records)**, chosen to span the *new* vendor families (Infineon/TI mmWave radar, Qorvo/NXP UWB, Bouffalo/Espressif RISC-V, Nordic/Qualcomm cellular-IoT, Morse Micro HaLow, Semtech LoRa, Richwave FPV, Realtek Ameba) and the full ladder, weighted toward records that make *strong* structured claims (`raw-iq`, `arbitrary-waveform`, `radar`, `passive-radar`, `csi`).
- **For each record**, one concrete claim is pulled and checked against a primary source. **OK** = source affirms it; **OK (caveat)** = true but a field elides an important condition or hits an enum limit; **FIX** = the source (or the catalog's own definitions/sibling records) contradicts it.
- **Every FIX** is emitted as a corrected record (same `id`, merge semantics) in this cycle's output.

Two structural facts about this batch shape the findings:

1. **The `bands` enum has no bucket between 6 GHz and 60 GHz, and none at all above 60 GHz.** K-band (24 GHz) and W-band automotive radar (76–81 GHz) therefore have no honest home. The catalog is *inconsistent* about how it copes — some 24 GHz parts get `[]`, one got `2.4GHz`; 76–81 GHz parts get `60GHz` as a "nearest mmWave" approximation. This audit standardizes the honest choice.
2. **Capability inflation recurs at the radar/UWB frontier**, exactly as it did for Wi-Fi in batch 1: a *chirp generator* tagged `arbitrary-waveform`, an *active* UWB sensor tagged `passive-radar`. The enum values have precise ladder meanings ([taxonomy.md](./taxonomy.md)); a flag must be dropped when the evidence supports only an adjacent, weaker one.

## Audit table

| Chip (id) | Audited claim | Primary source says | Verdict |
|---|---|---|---|
| `infineon-bgt24ltr11` | `bands: ["2.4GHz"]`, 24 GHz Doppler radar | Infineon: BGT24LTR11N16 is a **24 GHz** (24.0–24.25 GHz ISM, K-band) SiGe radar MMIC. The record's own note already says "24.0–24.25 GHz." `2.4GHz` is a 10× error and disagrees with sibling `infineon-bgt24mtr11-radar` (same 24 GHz, `bands: []`). | **FIX** — `bands` → `[]` |
| `ti-awr1243` | `bands: ["60GHz"]`, `raw-iq`/`fmcw`, no `arbitrary-waveform` | TI: AWR1243 is a **76–81 GHz** automotive FMCW MMIC; raw ADC over LVDS to DCA1000; TX is a chirp generator. Correctly omits `arbitrary-waveform`. | **OK (caveat)** — `60GHz` is a nearest-bucket stand-in for 76–81 GHz (no W-band enum); note already flags it |
| `ti-iwr6843` | tier 4, caps incl. **`arbitrary-waveform`**, 60 GHz | TI: IWR6843 is 60–64 GHz; raw ADC IQ over LVDS (`raw-iq` ✓, tier 4 ✓). But TX is a fractional-N **chirp engine** (start freq/slope/ramp), *not* baseband-IQ authoring. Sibling `ti-awr1243`'s note explicitly says "TX is a chirp generator, not arbitrary IQ" and omits the flag. | **FIX** — drop `arbitrary-waveform` |
| `qorvo-dw1000` | caps `csi`/`radar`/**`passive-radar`**, UWB | Qorvo DW1000: SPI-readable CIR accumulator (1016 I/Q taps) = CSI-analog ✓; monostatic CIR sensing = active `radar` ✓. But the device **transmits its own UWB frames** — that is active radar, not *passive* radar (which exploits non-cooperative illuminators). | **FIX** — drop `passive-radar` |
| `bouffalo-bl808` | tier 1 monitor+injection, 2.4 GHz b/g/n, heterogeneous RISC-V (C906 64-bit D0 + C906 32-bit M0 + E902 LP) | Pine64/Sipeed/bouffalo_sdk: BL808 = T-Head C906 64-bit (D0) + C906 32-bit (M0, wireless) + E902 (LP), 2.4 GHz Wi-Fi 4 + BLE5 + 802.15.4; Linux via openbouffalo. Arch and bands correct. | **OK** |
| `espressif-esp32-c5` | tier 2 CSI, dual-band 2.4/**5 GHz** Wi-Fi 6, single RISC-V | Espressif: "industry's first RISC-V MCU supporting 2.4 and 5 GHz dual-band Wi-Fi 6," single 32-bit core; listed in `esp-csi` supported parts. | **OK** |
| `espressif-esp32-c2` | tier 1 monitor+injection, **no** CSI | ESP-IDF: C2 (ESP8684) absent from Espressif's canonical CSI-support set (ESP32/S2/C3/S3/C5/C6/C61). Record correctly declines to claim CSI. | **OK** (correctly conservative) |
| `nordic-nrf9160-sip` | tier 1 monitor, `bands: ["sub-GHz"]`, LTE-M/NB-IoT/GPS | Nordic: documented AT + vendor modem-trace (nrf_modem_lib) into Wireshark = clean Tier 1; modem is a signed closed binary, no IQ. But LTE-M/NB-IoT bands run past 1 GHz (to ~2.2 GHz) and GPS L1 is 1.575 GHz — `sub-GHz` is a catalog convention, not literal. | **OK (caveat)** — cellular bands exceed `sub-GHz` (convention) |
| `qualcomm-mdm9x07-iot-modem` | tier 1 monitor via DIAG (QCSuper/SCAT) | P1sec QCSuper / fgsect SCAT: Qualcomm DIAG over USB yields GSMTAP signaling + RF measurement on these Cat-1/M1 modems. No PHY/IQ. | **OK (caveat)** — same `sub-GHz` cellular-band convention |
| `microchip-at86rf215` | tier 4, `raw-iq`/`arbitrary-waveform`, sub-GHz+2.4 GHz | Microchip datasheet: documented **I/Q data interface** (LVDS) that bypasses the on-chip baseband — read raw complex samples in, feed arbitrary I/Q out. Genuine tier-4 access, no RE needed. | **OK** |
| `semtech-sx127x` | caps incl. **`arbitrary-waveform`**, LoRa/FSK/OOK | Semtech: continuous FSK/OOK mode streams an arbitrary *bitstream*; LoRa engine does CSS. This is arbitrary data through a fixed modulator, not baseband-IQ authoring — the same liberal reading applied across the ISM-transceiver rows (`ti-cc1101`, `ti-cc2500`, `flipper-cc1101-subghz`). | **OK (caveat)** — `arbitrary-waveform` = arbitrary bitstream, not IQ; flag for a future enum split |
| `richwave-rtc6705-fpv-vtx` | tier **3** + `arbitrary-waveform`, 5.8 GHz analog FM video | Betaflight `vtx_rtc6705.c`: SPI-tunable 5645–5945 MHz carrier, FM-modulates an arbitrary analog baseband. 5.8 GHz ∈ `5GHz` ✓. `arbitrary-waveform` normally implies tier 4 (baseband IQ); here it is deliberately scored tier 3 as analog-FM-of-arbitrary-baseband. | **OK (caveat)** — non-standard tier/cap pairing, but note is transparent |
| `realtek-rtl8720dn` | tier 2 CSI + open-firmware, dual-band 2.4/5 GHz, `standards: [b,g,n,BLE]` | Realtek Ameba: official Wi-Fi CSI API (per-subcarrier I/Q) ✓; documented FreeRTOS SDK ✓. But BW16/RTL8720DN is dual-band **802.11 a**/b/g/n — `standards` omits `802.11a`, the only PHY it does on 5 GHz (cf. batch-1's `intel-iwl5300`). | **OK (caveat)** — add `802.11a` to `standards` |
| `morsemicro-mm6108` | tier 1 monitor+injection, 802.11ah sub-GHz | Morse Micro: sub-1 GHz OFDM HaLow (1/2/4/8 MHz); open `mac80211` morse driver (upstreaming) gives monitor+injection. Firmware blob; no CSI yet. | **OK** |
| `nxp-sr150` | tier 2 CSI, UWB, `status: reported` | NXP Trimension: Cortex-M33 + HRP UWB, exportable CIR (CSI-analog), signed/closed FW. `reported` status appropriately hedges reachability. | **OK** |
| `uhnder-s80` | tier 4 `radar`/`arbitrary-waveform`, `bands: ["60GHz"]` | EE Times / Uhnder: 79 GHz (76–81 GHz) PMCW/DCM **digital-code** radar-on-chip — phase-coded spread spectrum is genuinely arbitrary-waveform-adjacent (unlike FMCW). Vendor defunct 2024 → `status: reported` ✓. Band is the 76–81→`60GHz` approximation again. | **OK (caveat)** — `60GHz` stand-in for 76–81 GHz |
| `espressif-esp8266` | tier 2 CSI, `status: reported` | ESP-FAQ documents `esp_wifi_set_csi_rx_cb()` on the ESP8266 RTOS SDK, but every mainstream CSI toolkit (ESP32-CSI-Tool, Wi-ESP) is ESP32-only. Vendor-documented, not community-reproduced. | **OK** (`reported` is the honest hedge) |
| `ti-cc2400` | tier 3 spectral-scan + open-firmware, 2.4 GHz | Ubertooth: CC2400 exposes a fast RSSI/energy sweep (`ubertooth-specan`) + unbuffered demod bitstream; open firmware. Tier 3 via spectral energy scan. `injection` is BLE-limited but present. | **OK** |

## Results

- **Sampled:** 18 records.
- **OK:** 7 (`bl808`, `esp32-c5`, `esp32-c2`, `at86rf215`, `mm6108`, `sr150`, `esp8266`, `cc2400` — 8, counting `cc2400`). **OK (caveat):** 7 (`awr1243`, `nrf9160`, `mdm9x07`, `sx127x`, `rtc6705`, `rtl8720dn`, `uhnder-s80`). **FIX:** 3 (`infineon-bgt24ltr11`, `ti-iwr6843`, `qorvo-dw1000`).
- **Implied error rate:** ~17% of a deliberately high-claim sample carried a structured claim contradicted by its primary source or by the catalog's own definitions — consistent with batch 1's ~20%, and again concentrated in the strongest-claiming records.

### The three recurring failure signatures (batch 2)

1. **Band mis-bucketing at the mmWave/microwave frontier.** The `bands` enum stops at 60 GHz and has no K-band (24 GHz) slot. `infineon-bgt24ltr11` was tagged `2.4GHz` — a literal 10× error that also disagrees with its own 24 GHz sibling. The honest mapping for a 24 GHz part with no enum bucket is `[]` (matching `infineon-bgt24mtr11-radar`), with the true frequency in `standards`/`notes` — never `2.4GHz`, which implies Wi-Fi/BLE. Separately, 76–81 GHz automotive parts (`awr1243`, `uhnder-s80`) use `60GHz` as a "nearest mmWave" stand-in; that is a *documented approximation the notes already flag*, so it is a caveat, not a FIX — but a future enum should add `24GHz`/`76-81GHz`/`W-band` values to end both compromises.
2. **`arbitrary-waveform` attached to a chirp generator.** `ti-iwr6843` earns tier 4 honestly via `raw-iq` (raw ADC over LVDS), but its TX is a fractional-N ramp engine — programmable *chirps*, not authored baseband IQ. Its own sibling `ti-awr1243` says exactly this and omits the flag. FMCW ≠ arbitrary waveform; PMCW/DCM (`uhnder-s80`) is the genuinely arbitrary-waveform-adjacent radar modulation, which is why that flag survives there.
3. **`passive-radar` attached to an active transmitter.** `qorvo-dw1000` does monostatic CIR sensing by **transmitting its own UWB frames** — active radar. *Passive* radar has a precise meaning: detection via non-cooperative illuminators of opportunity. The `radar` flag is correct; `passive-radar` is not.

## Corrections issued this cycle

The three FIX rows are emitted as corrected records (same `id`, merged):

- **`infineon-bgt24ltr11`** — `bands` `["2.4GHz"]` → `[]`. A 24.0–24.25 GHz K-band radar has no enum bucket; `[]` matches the sibling `infineon-bgt24mtr11-radar` and avoids the false Wi-Fi/BLE-band implication. The 24 GHz frequency stays spelled out in `standards`/`notes`. Tier (3) and capabilities unchanged.
- **`ti-iwr6843`** — `sdr_capabilities` `["radar","fmcw","raw-iq","arbitrary-waveform"]` → `["radar","fmcw","raw-iq"]`. Tier 4 is retained (justified by `raw-iq`). The chirp engine's programmability is real but is FMCW chirp authoring, not baseband-IQ, so it no longer claims `arbitrary-waveform` — consistent with sibling `ti-awr1243`.
- **`qorvo-dw1000`** — `sdr_capabilities` `["csi","radar","passive-radar"]` → `["csi","radar"]`. The CIR-accumulator CSI and active radar sensing are well-supported; `passive-radar` is dropped because the device is its own illuminator. Tier (2) unchanged.

The seven **OK (caveat)** rows are not error-level and are left as-is, but flagged for a future cycle: add `802.11a` to `realtek-rtl8720dn`'s `standards`; annotate the `sub-GHz` cellular convention on `nordic-nrf9160-sip`/`qualcomm-mdm9x07-iot-modem`; and revisit `arbitrary-waveform` on the ISM-transceiver rows (`semtech-sx127x`, `richwave-rtc6705-fpv-vtx`) once the capability enum distinguishes "arbitrary bitstream/analog baseband" from "arbitrary baseband IQ."

## Limitations of this audit

- 18 of 519 records is ~3.5%; absence of a FIX outside the sample is not evidence of correctness. The value is calibration — the *kinds* of error in newly-added families — not exhaustive validation.
- For RE-unlocked or research-grade capabilities the "primary source" is the unlocking project or a sensing paper, not a vendor datasheet; where those over- or under-state their own reach, the audit inherits it.
- WebSearch budget for this cycle was exhausted, so verification leaned on direct fetches of vendor product pages/datasheets and repos plus the catalog's own citations; a couple of caveats (e.g. exact LTE band edges) are asserted from documented convention rather than a freshly-pulled 3GPP table.
- The two 76–81 GHz `60GHz` band tags are enum-limitation compromises, not defects; they are called out here so a future schema change can resolve them cleanly rather than being silently "fixed" into a different wrong bucket.

## References

- Infineon BGT24LTR11N16 (24 GHz radar): https://www.infineon.com/cms/en/product/sensor/radar-sensors/radar-sensors-for-iot/24ghz-radar/bgt24ltr11n16/
- Infineon BGT24MTR11 (sibling 24 GHz, `bands: []` precedent): https://www.infineon.com/cms/en/product/sensor/radar-sensors/
- TI AWR1243 (76–81 GHz FMCW, LVDS raw ADC): https://www.ti.com/product/AWR1243
- TI IWR6843 (60–64 GHz, chirp engine + C674x DSP): https://www.ti.com/product/IWR6843
- TI DCA1000EVM (raw-ADC capture): https://www.ti.com/tool/DCA1000EVM
- Qorvo DW1000 (CIR accumulator): https://www.qorvo.com/products/p/DW1000
- UWB CIR device-free sensing (MDPI Sensors): https://www.mdpi.com/1424-8220/22/16/6255
- Bouffalo BL808 SDK: https://github.com/bouffalolab/bouffalo_sdk / openbouffalo: https://github.com/openbouffalo
- Espressif ESP32-C5 (dual-band Wi-Fi 6): https://www.espressif.com/en/products/socs/esp32-c5
- esp-csi (supported-parts list): https://github.com/espressif/esp-csi
- ESP32-C2 Wi-Fi API (no CSI): https://docs.espressif.com/projects/esp-idf/en/v5.2/esp32c2/api-guides/wifi.html
- ESP8266 CSI callback (ESP-FAQ): https://docs.espressif.com/projects/esp-faq/en/latest/software-framework/wifi.html
- Nordic nRF9160 modem trace: https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/test_and_optimize/testing/modem_trace.html
- QCSuper (Qualcomm DIAG): https://github.com/P1sec/QCSuper — SCAT: https://github.com/fgsect/scat
- Microchip AT86RF215 datasheet (I/Q interface): https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42415-WIRELESS-AT86RF215_Datasheet.pdf
- Semtech SX127x / gr-lora RE: https://github.com/BastilleResearch/gr-lora
- Richwave RTC6705 Betaflight driver: https://github.com/betaflight/betaflight/blob/master/src/main/drivers/vtx_rtc6705.c
- Realtek Ameba Wi-Fi CSI API: https://aiot.realmcu.com/en/latest/rtos/wifi/csi/index.html
- Morse Micro (open mac80211 morse driver): https://www.morsemicro.com/chips/
- NXP Trimension UWB: https://www.nxp.com/products/wireless-connectivity/secure-ultra-wideband-uwb
- Uhnder digital radar-on-chip: https://www.eetimes.com/uhnder-ships-digital-radar-on-chip/
- Ubertooth (CC2400 specan): https://github.com/greatscottgadgets/ubertooth
- Batch 1 audit: [spot-check-audit-catalog-vs-datasheets.md](./spot-check-audit-catalog-vs-datasheets.md)
- Catalog methodology & provenance: [methodology.md](./methodology.md)
- Record schema: [../data/schema.json](../data/schema.json)
