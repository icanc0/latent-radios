# Espressif — the hobbyist's CSI radio

Espressif silicon is the single most *accessible* rung of this whole catalog. Where Broadcom, Qualcomm, and Intel force you to reverse-engineer and hot-patch a closed firmware blob just to reach **monitor**, **injection**, or **CSI**, Espressif ships all three as **first-class, documented ESP-IDF APIs** on a $2 chip. You do not need `nexmon`, a jailbroken phone, or a kernel patch — you `#include "esp_wifi.h"`, register a callback, and per-frame complex channel state falls out.

That generosity is also the ceiling. Espressif exposes the PHY's *outputs* (CSI, RSSI, noise floor) and the MAC's *inputs* (raw 802.11 TX), but never the PHY's *internals*. There is **no FFT-bin / spectral-scan API** (unlike Atheros/QCA `spectral_scan` or the Broadcom register hack), **no raw-IQ tap**, and **no arbitrary-baseband transmit** — you author 802.11 *frames*, not IQ samples. So every Wi-Fi-capable Espressif part lands at **SDR tier 2 (PHY telemetry / CSI)** and no higher with public tooling. What makes them exceptional is that tier 2 is reachable *out of the box, on every SKU, in both 2.4 GHz and — with the ESP32-C5 — 5 GHz*.

See also [../projects/csi-toolchains.md](../projects/csi-toolchains.md) for the ESP32 CSI Toolkit / Wi-ESP tooling deep-dive, [../docs/techniques.md](../docs/techniques.md) for what CSI actually buys you (sensing, ranging, motion/respiration), and [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md) for why "tier 2" is not the same as a HackRF.

---

## The three built-in super-powers

Every ESP32-family part (and, contested, the ESP8266) gives you these through open ESP-IDF headers — no firmware patching required:

1. **Promiscuous / monitor RX** — `esp_wifi_set_promiscuous(true)` + `esp_wifi_set_promiscuous_rx_cb()`. You receive full 802.11 headers, management/control/data frames, with an `rx_ctrl` struct carrying RSSI, rate, channel, noise floor, and timestamp. Combined with `esp_wifi_set_channel()` for hopping → a working **sniffer**. (**tier 1**)
2. **Raw 802.11 injection** — `esp_wifi_80211_tx(ifx, buffer, len, en_sys_seq)` transmits an arbitrary frame buffer straight to the MAC. Beacons, probe requests, deauths, custom management frames — anything you can byte-assemble. The community `esp32-80211-tx` / `esp32free80211` (Jeija) predate and validate the official API. Note the MAC still owns the low PHY: you pick the 802.11 rate via `esp_wifi_config_80211_tx_rate()`, not an arbitrary waveform. (**tier 1**)
3. **Channel State Information** — `esp_wifi_set_csi_config()` + `esp_wifi_set_csi_rx_cb()` deliver a `wifi_csi_info_t` per received frame: **complex (I/Q, i.e. amplitude *and* phase) channel estimates per OFDM subcarrier** across L-LTF / HT-LTF / STBC-HT-LTF fields. For HT20 that's up to 64 subcarriers (≈128 signed bytes), HT40 up to 128. This is the headline feature and the reason Espressif appears in nearly every low-cost Wi-Fi-sensing paper. (**tier 2**)

### What Espressif does *not* give you (the tier-2 ceiling)

| Rung | Available? | Why not |
|---|---|---|
| 3 — spectral / raw-PHY FFT scan | ❌ | No public FFT-bin API. CSI is emitted only when a frame is decoded; there is no "scan the channel with no frame present" primitive. |
| 4 — arbitrary waveform TX | ❌ | TX path is frame-oriented (`esp_wifi_80211_tx`); the baseband/DAC is not exposed. No IQ buffer transmit. |
| 5 — open PHY / soft-radio | ❌ | ESP-IDF is open (Apache-2.0), but the Wi-Fi MAC/PHY lives in the **closed pre-compiled `esp32-wifi-lib` blob** + a binary PHY init table. The application layer is yours; the radio is not. |

**Firmware reality:** the RISC-V or Xtensa CPU core and ESP-IDF are fully open and toolchained (GCC/LLVM, GDB, OpenOCD). But the parts that would let you climb past tier 2 — the Wi-Fi MAC state machine and PHY control — are shipped as `libpp.a` / `libnet80211.a` / `libphy.a` **closed binaries** with a binary `phy_init` blob. Reverse-engineering them (Ghidra/IDA on the Xtensa or RV32 blobs) is the *only* research path to spectral/IQ access, and no public project has done it. Hence `firmware.openness = "partially-documented"` across the family: open host SDK, closed radio core.

---

## Per-chip breakdown

### ESP8266 (Tensilica L106 / Xtensa) — the ancestor
The original $2 Wi-Fi SoC. Single-core Xtensa L106 @ 80/160 MHz, 2.4 GHz 802.11 b/g/n. **Monitor + injection are rock-solid and verified** (it's the classic deauth/sniffer platform). **CSI is contested:** Espressif's ESP-FAQ documents `esp_wifi_set_csi_rx_cb()` for the ESP8266 RTOS SDK, but the community-blessed CSI toolchains (ESP32-CSI-Tool, Wi-ESP) are all ESP32; ESP8266 CSI is best treated as *reported*, not a daily-driver path. Hardware: ESP-01, ESP-12E/F, NodeMCU, Wemos/LOLIN D1 mini.

### ESP32 (Xtensa LX6, dual-core) — the reference CSI platform
The part every CSI paper means when it says "ESP32." Dual-core LX6 @ 240 MHz, 2.4 GHz Wi-Fi 4 + BT Classic + BLE. **CSI, monitor, and raw TX all verified** and heavily used. This is the target of **StevenMHernandez's ESP32-CSI-Tool** (active + passive modes, 52-subcarrier output, CSV logging) and **Wi-ESP**. Hardware: ESP32-WROOM-32, WROVER, DevKitC, TTGO, M5Stack.

### ESP32-S2 (Xtensa LX7, single-core) — Wi-Fi only
Single-core LX7 @ 240 MHz, 2.4 GHz Wi-Fi, **no Bluetooth**. Full CSI + monitor + raw-TX API parity. Native USB-OTG makes it a tidy USB-tethered CSI capture dongle. Hardware: ESP32-S2-WROOM, -S2-Saola, -S2-Kaluga, Wemos S2 mini.

### ESP32-S3 (Xtensa LX7, dual-core + vector DSP) — CSI + on-chip ML
Dual-core LX7 with AI/vector extensions, 2.4 GHz Wi-Fi 4 + BLE 5. Same CSI/monitor/TX APIs, but the vector unit makes on-device CSI feature extraction / TinyML sensing viable. Hardware: ESP32-S3-WROOM-1/2, -S3-DevKitC-1, -S3-BOX, XIAO ESP32-S3.

### ESP32-C3 (RISC-V single-core) — the cheap RISC-V CSI node
Single-core 32-bit RISC-V @ 160 MHz, 2.4 GHz Wi-Fi 4 + BLE 5. First RISC-V Espressif Wi-Fi part; full CSI/monitor/TX support, verified. Cheapest reliable CSI node. Hardware: ESP32-C3-WROOM-02, -C3-DevKitM-1, XIAO ESP32-C3, Lolin C3 mini.

### ESP32-C2 / ESP8684 (RISC-V single-core) — cost-optimized, thin
RISC-V @ 120 MHz, 2.4 GHz Wi-Fi 4 + BLE 5, minimal RAM/flash. Monitor + raw TX verified. **CSI support is limited/reported** — the C2 is notably absent from Espressif's canonical "all series support CSI" list (which enumerates ESP32/S2/C3/S3/C5/C6/C61). Treat CSI as unverified on this SKU. Hardware: ESP8684 modules, ESP32-C2-DevKitM.

### ESP32-C5 (RISC-V single-core) — the dual-band breakthrough (5 GHz CSI!)
Espressif's **first dual-band 2.4 GHz + 5 GHz Wi-Fi 6 (802.11ax)** part; RISC-V @ 240 MHz, + BLE 5 + 802.15.4. Crucially, **CSI is supported on both bands** — this is the accessible route to **5 GHz CSI** without a Broadcom/Intel jailbreak, a genuinely new capability for the hobbyist tier. Wi-Fi 6 HE-LTF CSI is newer and rougher around the edges (see C6 caveats). Hardware: ESP32-C5-DevKitC-1, ESP32-C5-WROOM-1, Waveshare ESP32-C5 Wi-Fi6 kit, XIAO ESP32-C5.

### ESP32-C6 (RISC-V, HP+LP dual-core) — Wi-Fi 6 (2.4 GHz) + 802.15.4
RISC-V high-perf core @ 160 MHz + a low-power core, **2.4 GHz Wi-Fi 6 (802.11ax)** + BLE 5 + 802.15.4 (Thread/Zigbee). CSI/monitor/TX supported, but **HE (Wi-Fi 6) CSI has documented quirks** — e.g. IDF issue #14271 reports missing L-LTF data and wrong HT-LTF subcarrier ordering in the callback. Solid for HT (11n) CSI, treat HE CSI as evolving. Hardware: ESP32-C6-WROOM-1, -C6-DevKitC-1, XIAO ESP32-C6.

### ESP32-H2 (RISC-V single-core) — **no Wi-Fi** (802.15.4 / Thread / BLE)
RISC-V @ 96 MHz, **802.15.4 (Thread/Zigbee/Matter) + BLE 5 only — no Wi-Fi radio, therefore no Wi-Fi CSI**. Included for completeness and because it *does* offer raw 802.15.4 frame access (a different-standard analog of monitor/injection at 2.4 GHz). Outside the Wi-Fi-SDR thesis; catalogued at the floor. Hardware: ESP32-H2-DevKitM-1, ESP32-H2-WROOM.

---

## Beyond frames: FTM ranging & CSI-radar
Two adjacent capabilities worth flagging because they lean on the same PHY telemetry:

- **FTM (Fine Timing Measurement / Wi-Fi RTT)** — `esp_wifi_ftm_initiate_session()` gives round-trip-time ranging (802.11mc). Supported on ESP32/C2/C3/C6/S2/S3 (C5 evolving). Not IQ, but a distinct radio-metrology primitive; indoor accuracy ~sub-5 m for most measurements.
- **esp-csi / esp-radar** — Espressif's own CSI application stack does **motion detection, human presence, and respiration** sensing purely from CSI amplitude/phase variance. This is the closest Espressif gets to "passive radar" behavior, though it is statistical motion inference over frame-triggered CSI, not true continuous-wave radar.

---

## Summary table

| Chip | Core | Bands / std | CSI | Monitor | Raw TX | Max tier | Firmware openness | Status |
|---|---|---|---|---|---|---|---|---|
| ESP8266 | Xtensa L106 | 2.4 / 11n | reported | ✅ | ✅ | 2 | partially-documented | reported |
| ESP32 | Xtensa LX6 ×2 | 2.4 / 11n | ✅ | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-S2 | Xtensa LX7 | 2.4 / 11n | ✅ | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-S3 | Xtensa LX7 ×2 | 2.4 / 11n | ✅ | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-C2 | RISC-V | 2.4 / 11n | limited | ✅ | ✅ | 1 | partially-documented | reported |
| ESP32-C3 | RISC-V | 2.4 / 11n | ✅ | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-C5 | RISC-V | **2.4 + 5** / 11ax | ✅ (both bands) | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-C6 | RISC-V | 2.4 / 11ax | ✅ (HE quirks) | ✅ | ✅ | 2 | partially-documented | verified |
| ESP32-H2 | RISC-V | 2.4 / **802.15.4 only** | ✗ (no Wi-Fi) | 15.4 only | 15.4 only | 1 | partially-documented | verified |

---

## Un-cataloged / TODO
- **ESP32-C61** — 2.4 GHz Wi-Fi 6 cost-optimized part; appears in Espressif's CSI-support list but not yet profiled here (module availability, CSI verification).
- **ESP32-C5 5 GHz HE-LTF CSI** — confirm subcarrier count/ordering and whether the C6-class L-LTF/HT-LTF callback bugs recur on 5 GHz.
- **ESP32-P4** — high-performance dual-core RISC-V with **no native Wi-Fi** (uses ESP-Hosted over an ESP32-C6); does hosted-radio CSI pass through? Unknown.
- **ESP8266 CSI** — resolve the FAQ-vs-community contradiction: is `esp_wifi_set_csi_rx_cb()` genuinely functional on L106 silicon, and at what subcarrier fidelity?
- **esp32-wifi-lib blob RE** — no public Ghidra/IDA teardown of `libpp/libphy` that would expose an FFT-bin or IQ path; the standing research gap that could push any of these parts to tier 3+.
- **Antenna-diversity / 2-RX parts** — Espressif is single-antenna; document why MIMO-CSI (Intel 5300-style) is out of reach here.
- **ESP-NOW / LR (long-range) proprietary PHY mode** — Espressif's sub-1-Mbps custom mode; does it expose different CSI characteristics? Uncatalogued.
