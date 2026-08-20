# Wi-Fi Modules by Integrator (Package → Die)

A **module** (Murata Type, AMPAK AP6xxx, AzureWave AW-xx, Laird/Ezurio Sterling, Silex SX-, SparkLAN WPEQ, USI WM-, Espressif ESP-WROOM…) is almost never its own radio. It is a shielded package — an antenna path, a crystal/TCXO, matching, a power-management shim, and regulatory certifications — wrapped around **someone else's die**. Nine times out of ten that die is a Broadcom/Cypress/Infineon FullMAC part, a Qualcomm Atheros/QCA MAC, a NXP/Marvell (mwifiex) part, a MediaTek MT76 part, a Realtek RTL87xx, or — for the Espressif modules — Espressif's own SoC.

**The one rule that matters for this catalog: a module's SDR tier IS its die's SDR tier.** The package cannot add monitor mode, CSI, spectral scan, or raw-IQ that the silicon does not already expose. So every record below is scored by the die it carries, and its `notes` name that die and cross-reference the die's entry in the chip catalog:

- Broadcom / Cypress / Infineon dies → [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md)
- Realtek dies → [`../chips/realtek.md`](../chips/realtek.md)
- Qualcomm / Atheros dies → [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md)
- MediaTek / Ralink dies → [`../chips/mediatek-ralink.md`](../chips/mediatek-ralink.md)
- Espressif SoCs → [`../chips/espressif.md`](../chips/espressif.md) and [`../chips/risc-v-wifi.md`](../chips/risc-v-wifi.md)

> **How to read a module you actually hold.** The FCC ID on the can is the fastest ground truth: look it up at fcc.io/<ID> or fccid.io, and the internal photos + test report almost always reveal the die underneath. On Linux, `dmesg | grep -iE 'brcmfmac|ath1?0k|mwifiex|rtl|mt76'`, `lspci`/`lsusb`, and the loaded firmware filename (e.g. `brcmfmac43455-sdio.bin`) tell you the same thing. Once you know the die, its tier is fixed — go read that chip's page.

---

## The SDR ladder, applied to modules

| Tier | Meaning | Typical module dies |
|-----:|---------|----------------------|
| 0 | Black box, vendor blob only | NXP/Marvell 88W89xx, some AIROC combo parts |
| 1 | Monitor + injection | CYW4343W, BCM4330, RTL8723BS, RTL8822CS, QCA6174, MT7921, ESP8266 |
| 2 | + CSI | BCM4339, CYW43455/43456, BCM43430/43438 (via Nexmon); ESP32 family |
| 3 | + Spectral scan | Atheros AR9382/AR9271, QCA9880/9882 (ath9k/ath10k) |
| 4 | + Arbitrary waveform / raw-IQ TX | (no commodity Wi-Fi module reaches this) |
| 5 | Open/documented PHY, genuine SDR | (none in this file — see the SDR-grade chips) |

**Reality check:** essentially every combo module in the wild lands at Tier 1–3. The high tiers come from the *toolchain* wrapped around a small set of dies — [Nexmon](../projects/nexmon.md)/[`nexmon_csi`](https://github.com/seemoo-lab/nexmon_csi) for Broadcom, ath9k/ath10k `spectral_scan` for Atheros, the [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool) for Espressif — not from anything the module vendor did.

---

## Murata (Type 1DX / 1LD / 1MW / 1YN / 2BC …)

Murata is the archetype: a "Type" number is a form-factor + die combination. Historically the dies are Cypress (now Infineon AIROC, ex-Broadcom IoT line); newer NXP-partner Types (1XK/2EL/1ZM) carry NXP/Marvell silicon. Murata ships the matching `brcmfmac` NVRAM (`.txt`) file, which is why these dominate NXP i.MX, ST, Renesas and TI reference designs.

| Type | Die (chip catalog id) | Class | Tier | Note |
|------|------------------------|-------|-----:|------|
| Type 1DX | Cypress **CYW4343W** (BCM4343W) | 11n 2.4G + BT4.2 | 1 | Same die as Laird Sterling-LWB |
| Type 1LD | Cypress **CYW43455** | 11ac dual + BT4.2 | 2 | **Same die family as RPi 3B+/4 → full Nexmon/`nexmon_csi`** |
| Type 1MW / 1PJ | Cypress **CYW43012** | 11ac dual + BT5, low-power | 1 | AIROC, largely closed |
| Type 1YN | Infineon **CYW54591** | Wi-Fi 5 1x1 + BT5.2 | 1 | AIROC, closed FW |
| Type 2BC | Cypress **CYW4373** | 11ac 1x1 + BT5 | 1 | Shared die with Sterling-LWB5 |
| Type 2EL | NXP/Marvell **88W8997** | 11ac 2x2 + BT5 (mwifiex) | 1 | *reported* |
| Type 1ZM | NXP/Marvell **88W9098** | Wi-Fi 6 2x2 + BT5 | 1 | *reported* |

---

## AMPAK (AP6xxx) — the SBC/TV-box workhorses

If a cheap ARM SBC or Android TV box has Wi-Fi, odds are it is an AMPAK AP6xxx module. Almost all are Broadcom/Cypress FullMAC dies (a handful of low-end parts are Realtek). Because several of these dies are *exactly* the Nexmon reference chips, an AP62xx/AP6335 board can often be turned into a CSI/monitor node with stock Nexmon.

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| AP6210 / AP6181 | BCM43362 | 11n 2.4G (+BT on 6210) | 1 | Older, no Nexmon |
| AP6212 / AP6212A | Cypress **BCM43438/CYW43438** | 11n 2.4G + BT4.1 | 2 | RPi-Zero-W-class die → Nexmon monitor/CSI |
| AP6255 | Cypress **CYW43455** | 11ac dual + BT | 2 | Full Nexmon/`nexmon_csi` |
| AP6256 | Cypress **CYW43456** | 11ac dual + BT5 | 2 | 43455 sibling; Nexmon works |
| AP6330 | BCM4330 | 11n dual + BT | 1 | Monitor/injection only |
| AP6335 | BCM4339 | 11ac 1x1 + BT | 2 | **One of the original Nexmon chips** |
| AP6354 / AP6356S | BCM4354 / BCM4356 | 11ac 2x2 + BT | 1 | Nexmon monitor partial, no stock CSI |
| AP6398S | BCM4359 | 11ac 2x2 + BT5 | 1 | RK3399 boards (RockPro64, NanoPC-T4) |

---

## AzureWave (AW-CB / AW-CE / AW-CM / AW-NB / AW-CU / AW-XB)

AzureWave spans hobbyist and industrial. The **AW-CB/AW-CE** desktop m.2/mini-PCIe parts carry big Broadcom BCM43xx dies (the AW-CB160 is the classic "hackintosh"/macOS-native BCM4360 3x3). **AW-CM** are Cypress SDIO combos; **AW-CU** are Cypress/PSoC or NXP SoC-in-module parts; **AW-NB** are older BT/Wi-Fi combos; **AW-XB** lean NXP/Marvell.

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| AW-CB160H / AW-CB375NF | BCM4360 | 11ac 3x3 | 1 | macOS-native; `brcmfmac` monitor partial |
| AW-CE123H | BCM4352 | 11ac 2x2 | 1 | Monitor/injection only |
| AW-CM256SM | Cypress **CYW43456** | 11ac dual + BT5 | 2 | 43455 sibling → Nexmon |
| AW-NB197 / AW-NB159 | BCM4330 / BCM43239 | 11n + BT | 1 | Legacy |
| AW-CU / AW-XB series | Cypress AIROC or NXP 88W8xxx | varies | 0–1 | *reported* — verify die by FCC ID |

---

## Fn-Link — mostly Realtek, some Broadcom clones

Fn-Link is a high-volume Chinese module house feeding TV boxes and low-cost SBCs. The bulk are **Realtek RTL87xx** SDIO parts (RTL8723BS, RTL8723DS, RTL8822CS/BS); some are pin-compatible AMPAK-style Broadcom parts. Realtek monitor/injection is real but driver-dependent (out-of-tree `rtl8xxxu`/vendor forks).

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| Fn-Link 6222B-SRC / 6222B-UUB | Realtek **RTL8723BS** | 11n 2.4G + BT4.0 | 1 | *reported* |
| Fn-Link 8822-family | Realtek **RTL8822CS** | 11ac dual + BT5 | 1 | *reported* |
| Fn-Link 6223x (AP6212-style) | Cypress BCM43438 | 11n 2.4G + BT | 2 | Broadcom die — see AMPAK row |

---

## Laird / Ezurio (Sterling-LWB / LWB5 / EWB)

Laird Connectivity (rebranded **Ezurio**, 2024) sells industrial, pre-certified Cypress/Infineon modules with long lifecycles.

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| Sterling-LWB | Cypress **CYW4343W** | 11n 2.4G + BT | 1 | Same die as Murata Type 1DX |
| Sterling-LWB5 / LWB5+ | Cypress **CYW4373** | 11ac 1x1 + BT5 | 1 | Same die as Murata Type 2BC |
| Sterling-EWB | Cypress **CYW43439** | Wi-Fi 4 1x1 + BT5 | 1 | Pico-W-class die; *reported* |

---

## Silex Technology (SX-PCEAC / SX-SDMAC / SX-ULPGN)

Silex mixes Qualcomm/Atheros and Cypress/Infineon dies. The Atheros-based PCIe parts inherit the **best commodity RF-sensing story in this file** (ath9k/ath10k spectral scan + Atheros CSI Tool).

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| SX-PCEGN | Atheros **AR9382** (ath9k) | 11n 2x2 | 3 | Spectral scan + Atheros CSI Tool; *reported* die |
| SX-PCEAC2 | QCA **QCA9377** (ath10k) | 11ac 1x1 + BT | 1 | Monitor/injection |
| SX-SDMAC-2830S | Infineon **CYW54591** | Wi-Fi 5 1x1 + BT | 1 | AIROC, closed |

---

## SparkLAN (WPEQ / WPEA / WNFQ / WNFB)

SparkLAN targets embedded/AP designs, so its catalog is rich in **Atheros multi-stream** parts — the ath9k/ath10k dies with `spectral_scan`. This is where a module genuinely reaches Tier 3.

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| WPEA-121N / WPEA-128N | Atheros **AR9382** (ath9k) | 11n 2x2 | 3 | monitor + injection + CSI + spectral |
| WPEQ-353ACN(BT) | QCA **QCA9880** (ath10k) | 11ac 3x3 | 3 | spectral scan (ath10k) |
| WNFQ-261ACN(BT) / WPEQ-261ACN | QCA **QCA6174A** (ath10k) | 11ac 2x2 + BT | 1 | monitor/injection |
| WNFB-266AXI(BT) | MediaTek **MT7921** (mt76) | Wi-Fi 6 2x2 + BT | 1 | monitor/injection |

---

## USI (Universal Scientific Industrial)

USI (WM-BN / WM-BAC / WM-B…) supplies laptops, Chromebooks and consumer devices with Broadcom, Cypress, Qualcomm or NXP/Marvell dies depending on the customer. Identify by FCC ID before assuming a tier.

| Module | Die (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| WM-BN-BM-04 | BCM4330 | 11n dual + BT | 1 | Legacy laptops/tablets |
| WM-BAC-… (Chromebook) | BCM4356 or Marvell 88W8897 | 11ac 2x2 + BT | 1 | *reported* — die varies by SKU |

---

## Espressif (ESP-WROOM / ESP32-WROOM / WROVER / C-series)

Unlike every other integrator here, an Espressif module is a package around **Espressif's own SoC** — so it is not a "die from another vendor," and its capability is exactly the SoC's. These are the friendliest sensing modules in the catalog: documented SDKs, first-party CSI, and (C-series) RISC-V cores. Cross-reference [`../chips/espressif.md`](../chips/espressif.md) and, for the RISC-V parts, [`../chips/risc-v-wifi.md`](../chips/risc-v-wifi.md).

| Module | SoC (chip catalog id) | Class | Tier | Note |
|--------|------------------------|-------|-----:|------|
| ESP-WROOM-02 | **ESP8266** | 11n 2.4G | 1 | monitor + `esp_wifi_80211_tx` injection |
| ESP32-WROOM-32 / -32E | **ESP32** (Xtensa LX6) | 11n 2.4G + BT | 2 | first-party CSI via ESP32-CSI-Tool |
| ESP32-WROVER-E | **ESP32** + PSRAM | 11n 2.4G + BT | 2 | same die as WROOM-32, extra RAM for CSI logging |
| ESP32-S3-WROOM-1 | **ESP32-S3** (Xtensa LX7) | 11n 2.4G + BLE5 | 2 | CSI + more compute for on-device ML |
| ESP32-C3-WROOM-02 | **ESP32-C3** (RISC-V) | 11n 2.4G + BLE5 | 2 | RISC-V CSI node |
| ESP32-C6-WROOM-1 | **ESP32-C6** (RISC-V) | Wi-Fi 6 2.4G + BLE5 + 802.15.4 | 2 | Wi-Fi 6 CSI; also Thread/Zigbee radio |

---

## Practical: from module to sensing node

1. **Broadcom/Cypress path (Tier 2 CSI).** Best targets are the CYW43455/43456 (Type 1LD, AP6255/6256, AW-CM256SM) and BCM4339 (AP6335) — the Nexmon reference dies. Flash the matching `nexmon_csi` firmware for the die, then extract CSI as UDP frames. See [`../chips/nexmon.md`](../projects/nexmon.md) and the walkthrough [`../docs/walkthroughs/nexmon-csi-to-usable-csi.md`](../docs/walkthroughs/nexmon-csi-to-usable-csi.md).
2. **Atheros path (Tier 3 spectral).** SparkLAN WPEA-121N (AR9382) or WPEQ-353ACN (QCA9880) give real `spectral_scan` via ath9k/ath10k — the only commodity modules here that see the raw sub-carrier magnitude sweep. Atheros CSI Tool adds per-packet CSI.
3. **Espressif path (Tier 2, easiest).** Any ESP32/-S3/-C3/-C6 WROOM board + [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool) is a $5 CSI node with a fully documented SDK. See [`../docs/walkthroughs/wifi-csi-human-activity-recognition.md`](../docs/walkthroughs/wifi-csi-human-activity-recognition.md).
4. **Everything else is Tier 0–1.** NXP/Marvell (mwifiex), MediaTek MT7921, Realtek RTL87xx and the AIROC combo parts give monitor/injection at best; treat the shiny module marketing as irrelevant and go read the die's chip page.

> **TX safety.** Injection and any raw-frame TX put energy on regulated bands. Stay within your licence, keep TX inside a shielded enclosure or on a wired-attenuator path for experiments, and read [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md) before transmitting.

---

## References

- Nexmon firmware patching framework — <https://github.com/seemoo-lab/nexmon>
- `nexmon_csi` (Broadcom/Cypress CSI extraction, supported chip list) — <https://github.com/seemoo-lab/nexmon_csi>
- linux-sunxi Wi-Fi module ↔ Broadcom/Realtek die table (AP6xxx) — <https://linux-sunxi.org/Wifi>
- ESP32-CSI-Tool — <https://github.com/StevenMHernandez/ESP32-CSI-Tool>
- ath9k `spectral_scan` documentation — <https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan>
- Atheros CSI Tool (WANDS, NUS) — <https://wands.sg/research/wifi/AtherosCSI/>
- Linux 802.11n CSI Tool (Halperin, Intel) — <https://dhalperi.github.io/linux-80211n-csitool/>
- Ezurio (ex-Laird) Wi-Fi/BT modules — <https://www.ezurio.com/wireless-modules/wifi-bluetooth-modules>
- Silex Technology embedded wireless modules — <https://www.silextechnology.com/connectivity-solutions/embedded-wireless>
- SparkLAN embedded modules — <https://www.sparklan.com/>
- FCC ID lookup (die identification from internal photos) — <https://fccid.io/>
