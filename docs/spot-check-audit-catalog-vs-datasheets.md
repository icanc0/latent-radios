# Spot-check audit: catalog vs datasheets

*Cycle 7 meta-verification pass.* This page does to the catalog what the catalog does to silicon: it picks a representative sample of entries and cross-checks each machine-readable claim (`bands`, `standards`, MIMO/streams, the headline SDR capability, firmware arch) against a **primary source** — a vendor datasheet, a kernel driver, or the reverse-engineering project that actually unlocks the chip. The point is to measure the catalog's own accuracy honestly and to fix what the sample turns up.

This is a companion to the process described in [methodology.md](./methodology.md); the record shape being audited is defined in [../data/schema.json](../data/schema.json).

## Method

- **Sample (20 records)** chosen to span vendors (Broadcom, Qualcomm Atheros, Intel, Realtek, MediaTek, Espressif, Bouffalo, Analog Devices, Airspy, Realtek/RTL-SDR, Celeno) and the full SDR ladder (tier 1 → tier 5), weighted toward records that make *strong* claims (CSI, raw-IQ, arbitrary-waveform, radar, open-firmware), because those are where over-claiming hurts most.
- **For each record**, one concrete claim is pulled and compared against a primary source. A claim is **OK** only if the source affirms it; **OK (caveat)** if it is true but the field elides an important condition; **FIX** if the source contradicts it.
- **Every FIX** below is emitted as a corrected module record (same `id`, merge semantics) in this cycle's output.

A useful recurring pattern surfaced: in all four FIX cases, the record's *prose* `notes` field was already honest ("raw-iq is … not a stock ath9k feature"; "24-1800MHz"; "~0.5kHz-1.7GHz"), while the *structured* field (`sdr_capabilities` / `bands`) over-reached. The machine-readable claim, not the human-readable one, is what needed correcting — which is exactly the class of defect a structured spot-check is designed to catch.

## Audit table

| Chip (id) | Audited claim | Primary source says | Verdict |
|---|---|---|---|
| `broadcom-bcm4339` | tier 2, CSI via Nexmon-CSI, 802.11ac 1×1, 2.4/5 GHz, ARM FullMAC (patchable) | Nexmon lists `BCM4339` (fw `6_37_34_43`); nexmon_csi supports it. 802.11ac 1×1 combo. | **OK** |
| `broadcom-bcm43455c0` | tier 2, CSI, 802.11ac 1×1 (Raspberry Pi 3B+/4/Zero2W), patchable | Nexmon lists `BCM43455` across many fw builds incl. `7_45_189/206/234`; nexmon_csi's flagship target. | **OK** |
| `broadcom-bcm4366c0` | tier 2, CSI, 802.11ac **4×4**, ARM Cortex-R FullMAC | Nexmon/nexmon_csi supports BCM4366c0 (Asus RT-AC86U); 4×4 11ac. | **OK** |
| `broadcom-bcm4398` | tier 1, `open-firmware`, 802.11be, Nexmon-patchable | Nexmon repo lists **`BCM4398d05` (fw `24_671_6_9`, Pixel 8)** — patchability is real for this newest part. | **OK** (hard case, catalog correct) |
| `atheros-ar9271` | open ath9k_htc firmware, 802.11n 2.4 GHz 1×1, Xtensa MAC | `open-ath9k-htc-firmware` (QCA-published, ClearBSD/MIT/GPLv2) builds a replacement MAC image. | **OK** |
| `atheros-ar9380` | tier 3, caps include **`raw-iq`**; ath9k SoftMAC | ath9k / Atheros-CSI-Tool expose per-subcarrier **CSI** and spectral-scan **FFT magnitude bins only** — *no raw baseband I/Q*. Record's own note concedes "not a stock ath9k feature." | **FIX** — remove `raw-iq` |
| `qualcomm-qca9500` | tier 3, caps include **`arbitrary-waveform`, `radar`, `spectral-scan`**; 60 GHz 802.11ad | talon-tools (nexmon-arc) demonstrates sector-sweep/**beam** control, per-sector channel estimation, and firmware patching — **not** arbitrary baseband-waveform TX, **not** FMCW/radar, **not** spectral scan. | **FIX** — drop overclaimed caps, tier 3→2, status→reported |
| `qualcomm-ipq4019` | tier 3, spectral-scan, 802.11n/ac, ath10k | ath10k/ath10k-ct + OpenWrt expose the Atheros spectral scan on IPQ40xx integrated radio. | **OK** |
| `intel-iwl5300` | tier 2, CSI (Halperin tool), 802.11n, 2.4/5 GHz 3×3 | Linux 802.11n CSI Tool (dhalperi) delivers 30-subcarrier CSI on the 5300. | **OK (caveat)** — `standards:["802.11n"]` omits the a/g PHYs the 5300 also does (its `-csi` sibling record lists a/g/n) |
| `intel-ax210-csi` | tier 2, CSI, 6 GHz, patchable ucode | PicoScenes extracts CSI from AX200/AX210; 6E band confirmed. | **OK** |
| `realtek-rtl8812au` | tier 1, monitor+injection, 802.11ac dual-band, 8051-class MCU | aircrack-ng `rtl8812au` driver provides monitor+injection; RTL8812AU is 2×2 11ac dual-band. | **OK** |
| `mediatek-mt7612u` | tier 1, monitor+injection, 802.11a/b/g/n/ac, MT76x2 | mt76 (`mt76x2u`) supports monitor+injection; MT7612U is 2×2 11ac dual-band. | **OK** |
| `espressif-esp32` | tier 2, CSI + injection, 2.4 GHz only, Xtensa LX6 | ESP-IDF exposes `esp_wifi_set_csi` and raw `esp_wifi_80211_tx`; ESP32 is 2.4 GHz b/g/n. | **OK** |
| `espressif-esp32-c6` | tier 2, CSI + injection, **802.11ax** 2.4 GHz, RISC-V | ESP32-C6 is Wi-Fi 6 (2.4 GHz only), BLE5, 802.15.4; ESP-IDF CSI + raw TX apply. | **OK** |
| `bouffalo-bl602` | tier 1, monitor+injection, 802.11b/g/n 2.4 GHz, RV32IMFC | Open BL602 Wi-Fi work (pine64/openbouffalo, bl_iot_sdk) + RE tooling; single-core RISC-V. | **OK** |
| `analog-adalm-pluto` | tier 5, raw-IQ/arb-waveform, bands sub-GHz/2.4/**5 GHz**, AD9363 | AD9363 is spec'd **325 MHz–3.8 GHz**; 5 GHz is reachable only via the well-known AD9364 firmware "frequency extension" (70 MHz–6 GHz). | **OK (caveat)** — 5 GHz depends on the documented hack; note it |
| `openwifi-ad9361` | tier 5, open Verilog PHY, 802.11a/g/n, CSI/raw-IQ/arb-waveform | open-sdr/openwifi is a genuine open-PHY 11a/g/n baseband on Zynq+AD9361. | **OK** |
| `airspy-r2-hfplus` | tier 5, bands sub-GHz **+ 2.4 GHz** | Airspy R2/Mini native range is **24–1700 MHz**; HF+ Discovery is HF/VHF. None reach 2.4 GHz. Record's own note says "24-1800MHz". | **FIX** — `bands` → `["sub-GHz"]` |
| `rtlsdr-rtl2832u` | tier 5, bands sub-GHz **+ 2.4 GHz** | RTL2832U + R820T/2 tops out at **1766 MHz** (R828D lower still); cannot tune 2.4 GHz. Record's own note says "~0.5kHz-1.7GHz". | **FIX** — `bands` → `["sub-GHz"]` |
| `celeno-cl6000` | tier 2, caps `csi`/`radar`/`fmcw`, closed firmware | CL6000 "Doppler"/WLAN-sensing is a **vendor-exposed** engine, not reverse-engineered or independently reproduced; no public tooling. | **OK (caveat)** — capabilities are vendor-claimed; `status` should read *reported*, not verified |

## Results

- **Sampled:** 20 records.
- **OK:** 13. **OK (caveat):** 3 (`intel-iwl5300`, `analog-adalm-pluto`, `celeno-cl6000`). **FIX:** 4 (`atheros-ar9380`, `qualcomm-qca9500`, `airspy-r2-hfplus`, `rtlsdr-rtl2832u`).
- **Implied error rate:** ~20% of the sample carried a structured claim contradicted by its primary source. That is *higher* than the catalog average would be, because the sample was deliberately weighted toward the strongest-claiming records — spot-check auditing samples where the risk is, not uniformly.

### The two recurring failure signatures

1. **Band over-reach on receive-only SDRs.** Both `airspy-r2-hfplus` and `rtlsdr-rtl2832u` were tagged `2.4GHz` despite topping out near 1.7–1.8 GHz. The enum lacks an "L-band / 1–2 GHz" value, so the honest mapping for a 24–1766/1700 MHz tuner is `["sub-GHz"]` with the upper extent spelled out in `notes` — never `2.4GHz`, which implies Wi-Fi/BLE reception these dongles cannot do.
2. **Capability inflation past the enum's meaning.** `raw-iq` (a tier-4 *baseband I/Q* capability) was attached to an ath9k part that only yields CSI + FFT magnitude; `arbitrary-waveform`/`radar` were attached to a 60 GHz part whose tooling only re-programs *beam patterns*. The enum values have precise ladder meanings ([taxonomy.md](./taxonomy.md)); a capability must be dropped when the evidence supports only an adjacent, weaker one.

## Corrections issued this cycle

The four FIX rows are emitted as corrected records (same `id`, merged):

- **`atheros-ar9380`** — removed `raw-iq` from `sdr_capabilities`; tier unchanged (3, still justified by `spectral-scan`). The reported PicoScenes "flexibility" stays described in `notes` but is no longer asserted as a verified capability.
- **`qualcomm-qca9500`** — `sdr_capabilities` reduced to `["monitor","csi","open-firmware"]` (dropped `arbitrary-waveform`, `radar`, `spectral-scan`), `sdr_tier` 3 → 2, `status` verified → **reported**. talon-tools' real, verified reach is per-sector channel estimation + ARC-microcode patching; beam-pattern authoring is *spatial* programmability, not baseband arbitrary-waveform, and no FMCW/radar is demonstrated.
- **`airspy-r2-hfplus`** — `bands` `["sub-GHz","2.4GHz"]` → `["sub-GHz"]`; L-band upper extent (≈1.7 GHz) documented in `notes`.
- **`rtlsdr-rtl2832u`** — `bands` `["sub-GHz","2.4GHz"]` → `["sub-GHz"]`; ≈1.766 GHz ceiling documented in `notes`.

The three **OK (caveat)** rows are not error-level and are left as-is, but flagged here for a future cycle: `intel-iwl5300` should list its a/g PHYs; `analog-adalm-pluto`'s 5 GHz entry should carry the frequency-extension caveat inline; `celeno-cl6000` should have `status: reported`.

## Limitations of this audit

- A 20-record sample of 505 is ~4%; absence of a FIX outside the sample is not evidence of correctness. The value here is calibration (the *kinds* of error, and their rough rate in high-claim records), not exhaustive validation.
- "Primary source" for RE-unlocked capabilities is the unlocking **project**, not a vendor datasheet — vendors rarely document repurposing. Where a project's README under- or over-states what its code does, this audit inherits that error.
- Datasheet frequency ranges are *typical/guaranteed* figures; real parts often tune slightly beyond them. That widens grey zones (e.g. an RTL dongle reaching ~1.9 GHz on a good unit) but does not rescue a 2.4 GHz claim that is ~600 MHz out of range.

## References

- Airspy R2 specifications (24–1700 MHz): https://airspy.com/airspy-r2/
- Airspy HF+ Discovery (HF/VHF): https://airspy.com/airspy-hf-discovery/
- RTL-SDR tuner range (R820T/2 → 1766 MHz): https://www.rtl-sdr.com/about-rtl-sdr/
- osmocom rtl-sdr driver/wiki: https://osmocom.org/projects/rtl-sdr/wiki
- Nexmon (supported-chip list incl. BCM4398d05): https://github.com/seemoo-lab/nexmon
- nexmon_csi: https://github.com/seemoo-lab/nexmon_csi
- Atheros-CSI-Tool (CSI, not raw I/Q): https://github.com/xieyaxiongfly/Atheros-CSI-Tool
- ath9k spectral scan (FFT magnitude bins): https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html
- SEEMOO talon-tools / nexmon-arc (60 GHz beam control): https://github.com/seemoo-lab/talon-tools
- PicoScenes (Intel AX210 / QCA9300 CSI): https://picoscenes.readthedocs.io/
- open-ath9k-htc-firmware: https://github.com/qca/open-ath9k-htc-firmware
- openwifi (open 11a/g/n PHY): https://github.com/open-sdr/openwifi
- ADALM-PLUTO frequency extension (AD9363→AD9364): https://wiki.analog.com/university/tools/pluto/users/customizing
- aircrack-ng rtl8812au driver: https://github.com/aircrack-ng/rtl8812au
- mt76 driver (MediaTek): https://github.com/openwrt/mt76
- ESP-IDF Wi-Fi (CSI + raw 802.11 TX): https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guide/wifi.html
- Catalog methodology & provenance: [methodology.md](./methodology.md)
- Record schema: [../data/schema.json](../data/schema.json)
