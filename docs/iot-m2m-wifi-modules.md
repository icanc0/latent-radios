# IoT / M2M Wi-Fi (and Combo) Modules — Cycle 8

> **The one rule for this whole page:** a module is a *package*, not a *radio*. Quectel, Telit, Fibocom, u-blox, Sierra Wireless, TI-module and Microchip-module part numbers are shielded, pre-certified, castellated carriers wrapped around **somebody else's die** (NXP/Marvell, Broadcom/Cypress, Realtek, Espressif, Newracom, or the vendor's own SimpleLink/WINC network processor). The SDR capability of a module is **exactly the capability of the die inside it** — no more, no less. So every record here is scored at its die's tier and points you at the chip's own catalog page. We do **not** invent new capabilities for a plastic can with a shield over it.

This is the industrial/embedded/M2M corner of the catalog: parts sold to appliance, metering, medical, automotive-telematics and industrial-gateway OEMs who want an FCC/CE/TELEC-certified module and an AT-command or host-driver interface, not a bare BGA. That commercial framing has one big consequence for us: **these vendors deliberately seal the radio.** The whole value proposition is "you never touch the PHY." So the honest tiers here skew **low** — a lot of Tier 0 and Tier 1 — and the interesting entries are the handful of modules that happen to wrap a die the reverse-engineering community already cracked (ESP32 → CSI, Newracom HaLow → open mac80211 driver, NXP Avastar → `mwifiex`/`moal` monitor).

Related reading: [`../chips/other-vendors.md`](../chips/other-vendors.md) (the underlying Avastar/NXP, TI SimpleLink, Microchip WINC, Silabs/Redpine, Newracom and Morse dies live there), [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md) (which drivers actually give you `mon0`), [`../chips/realtek.md`](../chips/realtek.md), [`../chips/espressif.md`](../chips/espressif.md), [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md), [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md), and [`halow-subghz.md`](halow-subghz.md) for the sub-GHz HaLow story.

---

## How to score a module (the die-lookup method)

1. **Find the die.** The FCC ID grant, the module datasheet's "Chipset" line, the linux-firmware blob it loads, or the driver it binds to will name it. Distributor pages (Mouser/DigiKey) and the FCC OET database (internal photos + block diagram) are the two most reliable primary sources when the datasheet is coy.
2. **Look the die up in this catalog** and copy its tier + caps. A Murata/u-blox/Quectel can around an NXP 88W9098 is a Tier-1 monitor/injection part *because 88W9098 is* — see [`../chips/other-vendors.md`](../chips/other-vendors.md).
3. **Subtract for the package if the module hides the host bus.** Some AT-command "network controller" modules (WINC, SimpleLink, RNWF) never expose the 802.11 MAC to a host stack at all — the radio talks only to an on-module ROM that offers sockets/TLS. That's a genuine Tier-0 downgrade *relative to the same silicon on an open SDIO bus*, because you can't even reach `mac80211`.
4. **Never add.** A module cannot be a higher tier than its die. If the die has no CSI path, the module has no CSI path.

---

## u-blox — the cleanest "die-carrier" case study

u-blox buys silicon and wraps it; the family letter tells you whose die you're holding. This makes u-blox the easiest vendor to reason about and the one worth studying to internalize the method.

| Module series | Die inside | Bands / standard | Tier | Cross-ref |
|---|---|---|---|---|
| **JODY-W1** (W164/W167) | Cypress/Broadcom **CYW89359** | 2.4/5 GHz, Wi-Fi 5 (11ac 2×2) + BT 5 | 1 | [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md) |
| **JODY-W2** (W263/W264/W267) | NXP **88W8987** (Marvell Avastar) | 2.4/5 GHz, Wi-Fi 5 + BT 5.1 | 1 | [`../chips/other-vendors.md`](../chips/other-vendors.md) |
| **JODY-W3** (W377/W378) | NXP **88W9098** | 2.4/5 GHz, Wi-Fi 6 (11ax 2×2) + BT 5.2 | 1 | [`../chips/other-vendors.md`](../chips/other-vendors.md) (`88W9098` row) |
| **JODY-W5** | NXP **IW612** tri-radio | 2.4/5 GHz, Wi-Fi 6 + BT 5 + 802.15.4 | 1 | [`../chips/other-vendors.md`](../chips/other-vendors.md) (`IW611/IW612` row) |
| **NORA-W10** (W101/W106) | Espressif **ESP32** | 2.4 GHz, Wi-Fi 4 + BT 4.2/BLE | **2** | [`../chips/espressif.md`](../chips/espressif.md) |
| **NORA-W2** (W256/W266) | Espressif **ESP32-S3** | 2.4 GHz, Wi-Fi 4 + BT 5 LE | **2** | [`../chips/espressif.md`](../chips/espressif.md) |
| **LILY-W1** (W131/W132) | 802.11n+BT combo, **die unconfirmed** (Marvell/NXP SD8801-class believed) | 2.4 GHz, Wi-Fi 4 | 1 (reported) | [`../chips/other-vendors.md`](../chips/other-vendors.md) |
| **ODIN-W2** (W260/W262) | Qualcomm **QCA4004**-class Wi-Fi + CSR BT (reported) | 2.4/5 GHz, Wi-Fi 4 + BT | 0–1 (reported) | [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md) |

**The standout is NORA-W10 / NORA-W2.** Because the die is a plain ESP32 / ESP32-S3, the module inherits the ESP-IDF **CSI API** — `esp_wifi_set_csi(true)` plus a callback delivering per-subcarrier `(I,Q)` — the same path the [ESP32-CSI-Tool](../projects/csi-toolchains.md) uses. That lifts these two modules to **Tier 2** while every other u-blox Wi-Fi module sits at Tier 1 (monitor/injection through the die's Linux driver) or lower. It is the single clearest illustration of the die-lookup rule: identical package philosophy, wildly different tier, entirely because of what silicon is under the shield.

The JODY automotive line wraps NXP/Cypress combo dies whose Linux drivers (`mwifiex`/`moal` for NXP, `brcmfmac` for Cypress) support netlink monitor and injection but expose **no public CSI**. JODY-W1's Cypress die is in the Nexmon-adjacent family, but there is no confirmed Nexmon port for CYW89359 specifically, so we do not credit it with spectral/CSI — honest Tier 1.

---

## Quectel — mostly cellular, but two Wi-Fi parts that matter

Quectel's core business is LTE/5G cellular (those basebands live in [`../chips/cellular-basebands.md`](../chips/cellular-basebands.md)). Their Wi-Fi/BT and companion modules are die-carriers like everyone else here, and two are genuinely interesting:

- **FGH100M — Wi-Fi HaLow (802.11ah), sub-GHz.** This is the reason Quectel appears on the SDR ladder at all. It wraps a **Newracom HaLow SoC (NRC7292-class)**, which means it inherits Newracom's unusually open **`nrc7292_sw_pkg`** GPL-2.0 `mac80211` driver → **monitor + injection over CSPI/SDIO, radiotap capture, sniffer mode**, in the 902–928 MHz (US) / 863–868 MHz (EU) band with 1/2/4 MHz S1G channels. Honest Tier 1: the host driver is open but the PHY firmware (`uni_s1g.bin`) is a closed blob, and **there is no public CSI path on any HaLow chip** (see [`halow-subghz.md`](halow-subghz.md) for the full sub-GHz picture and why this is the catalog's most inviting open problem). Cross-ref die: `newracom-nrc7292` in [`../chips/other-vendors.md`](../chips/other-vendors.md).
- **FC41D — Wi-Fi 4 + BT combo.** A tiny 802.11 b/g/n + BT 4.2 module for appliance/metering hosts. Die is a small Realtek-Ameba-class combo (**reported, unconfirmed** from public docs); scored at Tier 1 monitor/injection *if* the die is a Realtek `rtw`/`rtl8xxx` part — verify against the FCC internal photos before relying on it. Cross-ref [`../chips/realtek.md`](../chips/realtek.md).

Quectel also ships **cellular+Wi-Fi companion combos** (e.g. FC20/FC21-class Wi-Fi/BT add-ons paired with their LTE modules). These are Tier 0–1 die-carriers with no exposed radio; treat them the same way — identify the die from the FCC grant, then look it up.

---

## Telit (Telit Cinterion) — WE866 / WL865

Telit is another cellular-first house whose short-range line is pure die-carrier:

- **WE866C3 / WE866C6** — 802.11 b/g/n (+ dual-band on C6) + BT/BLE combo modules. Die is a **Realtek RTL8723-class** combo on the C3 (reported); scored Tier 1 (monitor/injection via the Realtek driver) with the usual caveat to confirm the die from the FCC filing. Cross-ref [`../chips/realtek.md`](../chips/realtek.md).
- **WL865E4-P** — 802.11 b/g/n Wi-Fi module. Public documentation does not cleanly name the die; it is a sealed "network-processor" style Wi-Fi module (**die unconfirmed**, candidates include a Redpine/Silabs RS9116-class or Qualcomm QCA401x network processor). Scored conservatively **Tier 0–1, reported** — if it is an RS9116 it inherits the open `rsi` monitor path ([`../chips/other-vendors.md`](../chips/other-vendors.md), `Silabs RS9116` row); if it is a QCA40xx "IoT network processor" it is sealed Tier 0. Verify before trusting.

---

## Fibocom — AW-series Wi-Fi/BT (Realtek dies)

Fibocom (like Quectel/Telit) is cellular-led; its short-range **AW-series** Wi-Fi/BT modules wrap **Realtek** combo dies:

- **AW600** — 802.11 b/g/n + BT 5, single-band 2.4 GHz. Die: Realtek RTL8733BS-class (reported). Tier 1 via the Realtek monitor path.
- **AW808** — 802.11ac dual-band + BT 5. Die: Realtek RTL8822CS-class (reported). Tier 1 (`rtw88`/`rtw89`-family monitor/injection). Cross-ref [`../chips/realtek.md`](../chips/realtek.md) and [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md).

As always: Realtek-die modules inherit whatever the corresponding `rtl8xxx`/`rtw` driver supports; none of these carries a Nexmon-class CSI path, so Tier 1 is the ceiling.

---

## Sierra Wireless / Semtech — not really a Wi-Fi-die vendor

Sierra Wireless (acquired by **Semtech** in 2023) is a **cellular and LoRa** house. It does not fab an independent merchant Wi-Fi die:
- Its AirLink gateways and combo modules **rebrand Qualcomm/Atheros** Wi-Fi silicon — look those up in [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md); the cellular basebands are in [`../chips/cellular-basebands.md`](../chips/cellular-basebands.md).
- Semtech's own RF IP is **LoRa sub-GHz** (SX127x/SX126x), already catalogued as `semtech-sx127x` in [`../chips/other-vendors.md`](../chips/other-vendors.md) / [`../chips/lora-subghz.md`](../chips/lora-subghz.md). That is a chirp-spread transceiver, **not** a Wi-Fi part, and not repurposable as a Wi-Fi SDR.

So the honest entry for "Sierra/Semtech Wi-Fi" is: **there isn't one** — it's a Qualcomm die under the hood, tracked elsewhere. Recorded below only as a pointer so the trail doesn't dead-end.

---

## TI SimpleLink CC32xx modules — the anti-SDR, in module form

TI's **CC3220MODA** (2.4 GHz 11 b/g/n) and **CC3235MODAS / CC3235MODASF** (dual-band 11 a/b/g/n) are TI's own silicon in a certified can — a Cortex-M4 application core plus a **closed "network processor"** that runs the entire 802.11 MAC/PHY and hands the user only a sockets/TLS API. There is **no host `mac80211`, no monitor iftype, no raw path** by design. This is the [`../chips/other-vendors.md`](../chips/other-vendors.md) "SimpleLink = the anti-SDR" family (`CC3000 → CC3235` row) in packaged form. Honest **Tier 0**. Verified from TI product pages.

---

## Microchip WINC / RNWF modules — sealed network controllers

Microchip's **ATWINC1500 / ATWINC3400** (WINC3400 adds BLE) and the newer **RNWF02** (Wi-Fi 4) / **RNWF11** (Wi-Fi 6) are "network controller" modules: the radio speaks only to an on-module ROM offering a sockets or AT-command API (WiFi101/AT), never to a host 802.11 stack. Same sealed story as SimpleLink — **Tier 0**, closed, no monitor/CSI/raw. Cross-ref [`../chips/other-vendors.md`](../chips/other-vendors.md) (`WINC1500/WINC3400`, `RNWF02/RNWF11` rows).

---

## Silicon Labs / Redpine (RS9116, SiWx917) and Espressif industrial — reference existing

These are dies, not modules, and are already catalogued — listed here only so the M2M reader lands on them:
- **Silabs RS9116 (ex-Redpine)** — 802.11n + BT5 + 802.15.4, **Tier 1** thanks to the open `rsi` `mac80211` driver with sniffer/monitor mode. See [`../chips/other-vendors.md`](../chips/other-vendors.md).
- **Silabs SiWx917 (SiWG917)** — Wi-Fi 6 SoC = Cortex-M4 + closed network processor (WiSeConnect socket API), **Tier 0–1**. See [`../chips/other-vendors.md`](../chips/other-vendors.md).
- **Espressif industrial modules** — ESP32/-S3/-C3/-C6-WROOM etc. carry the **CSI** path and are the M2M world's most SDR-friendly Wi-Fi (Tier 2). Fully covered in [`../chips/espressif.md`](../chips/espressif.md); the u-blox NORA-W10/W2 rows above are third-party ESP32 modules.

---

## Practical: getting `mon0` (or CSI) out of an M2M module

Two worked flows, one per interesting die-class. TX/injection is legally constrained — only inject on bands/power you are licensed for; see [`rf-safety-and-legal.md`](rf-safety-and-legal.md).

**A) ESP32-based module (u-blox NORA-W10, or any ESP32-WROOM) → Tier 2 CSI**
```c
// esp-idf: enable CSI and receive per-subcarrier I/Q in a callback
wifi_csi_config_t csi_cfg = { .lltf_en = true, .htltf_en = true,
                              .stbc_htltf2_en = true, .channel_filter_en = false };
esp_wifi_set_csi_config(&csi_cfg);
esp_wifi_set_csi_rx_cb(&csi_rx_cb, NULL);   // csi_rx_cb receives wifi_csi_info_t (buf = int8 I/Q pairs)
esp_wifi_set_csi(true);
```
Then parse the `int8` I/Q buffer exactly as in the [ESP32-CSI-Tool walkthrough](../projects/csi-toolchains.md). No firmware RE required — the API is documented.

**B) Newracom-HaLow module (Quectel FGH100M) → Tier 1 monitor over sub-GHz**
```bash
# out-of-tree open GPL driver; brings up an S1G radio you can sniff
git clone https://github.com/newracom/nrc7292_sw_pkg
cd nrc7292_sw_pkg/package/evk/sw_pkg/nrc_pkg
sudo ./start.py 0 0 US        # STA/sniffer role, US 902–928 MHz regdomain
sudo iw dev nrc0 set type monitor
sudo tcpdump -i nrc0 -w halow.pcap   # radiotap-tagged 802.11ah capture
```
This gives monitor + injection in the sub-GHz band; **no CSI** (no HaLow chip exposes one publicly). Details, S1G channel maps and caveats: [`halow-subghz.md`](halow-subghz.md).

For NXP-Avastar-die modules (JODY-W2/W3/W5), use the vendor `moal`/`mlan` (or upstream `mwifiex`) driver and its netlink monitor interface as described in [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md); expect Tier 1, no CSI.

---

## Compact module summary

| Module | Die (cross-ref) | Bands | Std | Tier | Caps | Status |
|---|---|---|---|---|---|---|
| u-blox JODY-W1 | Cypress CYW89359 | 2.4/5 | Wi-Fi5+BT5 | 1 | mon, inj | verified |
| u-blox JODY-W2 | NXP 88W8987 | 2.4/5 | Wi-Fi5+BT5.1 | 1 | mon, inj | verified |
| u-blox JODY-W3 | NXP 88W9098 | 2.4/5 | Wi-Fi6+BT5.2 | 1 | mon, inj | verified |
| u-blox JODY-W5 | NXP IW612 | 2.4/5 | Wi-Fi6+BT+154 | 1 | mon, inj | reported |
| u-blox NORA-W10 | Espressif ESP32 | 2.4 | Wi-Fi4+BT4.2 | **2** | mon, inj, **csi** | verified |
| u-blox NORA-W2 | Espressif ESP32-S3 | 2.4 | Wi-Fi4+BT5LE | **2** | mon, inj, **csi** | verified |
| u-blox LILY-W1 | 11n+BT, unconfirmed | 2.4 | Wi-Fi4 | 1 | mon, inj | reported |
| u-blox ODIN-W2 | Qualcomm QCA4004-class | 2.4/5 | Wi-Fi4+BT | 0–1 | — | reported |
| Quectel FGH100M | Newracom NRC7292 | sub-GHz | 11ah HaLow | 1 | mon, inj | reported |
| Quectel FC41D | Realtek-Ameba-class | 2.4 | Wi-Fi4+BT4.2 | 1 | mon, inj | reported |
| Telit WE866C3 | Realtek RTL8723-class | 2.4 | Wi-Fi4+BT | 1 | mon, inj | reported |
| Telit WL865E4-P | unconfirmed (RS9116/QCA401x) | 2.4 | Wi-Fi4 | 0–1 | — | reported |
| Fibocom AW600 | Realtek RTL8733BS | 2.4 | Wi-Fi4+BT5 | 1 | mon, inj | reported |
| Fibocom AW808 | Realtek RTL8822CS | 2.4/5 | Wi-Fi5+BT5 | 1 | mon, inj | reported |
| Sierra/Semtech | Qualcomm (Wi-Fi) / LoRa (Semtech) | 2.4/5 · sub-GHz | — | 0 | — | reported |
| TI CC3220MODA | TI CC3220S | 2.4 | Wi-Fi4 | 0 | — | verified |
| TI CC3235MODAS(F) | TI CC3235S | 2.4/5 | Wi-Fi4 | 0 | — | verified |
| Microchip ATWINC1500/3400 | Microchip WINC | 2.4 | Wi-Fi4(+BLE) | 0 | — | verified |
| Microchip RNWF02/RNWF11 | Microchip RNWF | 2.4 | Wi-Fi4/6 | 0 | — | reported |

**Bottom line for the M2M reader:** almost every industrial Wi-Fi module is Tier 0 or Tier 1. If you need CSI, reach for an **ESP32-based module** (NORA-W10, or any ESP32-WROOM). If you need sub-GHz reach, the **Newracom-HaLow modules** (Quectel FGH100M and the ALFA/Silex boards in [`halow-subghz.md`](halow-subghz.md)) give you monitor/injection but no CSI. Everything else is a sealed can, and the vendor intends it that way.

## References

- u-blox JODY-W3 (NXP 88W9098): https://www.u-blox.com/en/product/jody-w3-series
- u-blox JODY-W2 (NXP 88W8987): https://www.u-blox.com/en/product/jody-w2-series
- u-blox NORA-W10 (ESP32): https://www.u-blox.com/en/product/nora-w10-series
- u-blox LILY-W1: https://www.u-blox.com/en/product/lily-w1-series
- u-blox ODIN-W2: https://www.u-blox.com/en/product/odin-w2-series
- Quectel Wi-Fi/BT & HaLow modules: https://www.quectel.com/product-category/wi-fi-bt-modules/
- Newracom open GPL HaLow driver (die inside FGH100M): https://github.com/newracom/nrc7292_sw_pkg
- Telit Wi-Fi/BT modules (WE866/WL865): https://www.telit.com/m2m-iot-products/wi-fi-bt-modules/
- Fibocom Wi-Fi modules (AW series): https://www.fibocom.com/en/products/WiFi-Modules.html
- TI CC3220MODA (SimpleLink Wi-Fi module): https://www.ti.com/product/CC3220MODA
- TI CC3235MODASF (dual-band SimpleLink module): https://www.ti.com/product/CC3235MODASF
- Microchip ATWINC1500: https://www.microchip.com/en-us/product/ATWINC1500
- Microchip RNWF02: https://www.microchip.com/en-us/product/RNWF02
- Semtech (LoRa) / Sierra Wireless: https://www.semtech.com/products/wireless-rf
- ESP-IDF Wi-Fi CSI API (used by NORA-W10 modules): https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi.html
- Underlying dies: [`../chips/other-vendors.md`](../chips/other-vendors.md) · monitor paths: [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md) · HaLow: [`halow-subghz.md`](halow-subghz.md)
