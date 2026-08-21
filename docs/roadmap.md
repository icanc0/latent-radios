# Roadmap — this catalog is never finished

There is no last Wi‑Fi chip, and there is no last firmware reverse‑engineering write‑up. This file tracks what's cataloged, what's next, and how the project grows in **cycles**.

## How growth works: research cycles

The catalog is expanded in discrete research cycles. Each cycle:

1. Picks a batch of vendors / chip families / techniques (see the queue below).
2. Fans out parallel research — one investigator per family — cross‑checking primary sources (repos, papers, datasheets, driver code).
3. Produces (a) a prose chip/project file and (b) structured `data/modules.json` records, each with citations.
4. Validates the database, regenerates the CSV, commits, and pushes.

Cycles keep running as long as there are un‑cataloged parts — which is forever. Every vendor file's `## Un‑cataloged / TODO` section feeds the next cycle.

## Cycle log

| Cycle | Focus | Status |
|-------|-------|--------|
| 0 | Scaffold: taxonomy, schema, firmware‑RE methodology, tooling | seeded |
| 1 | Core families: Broadcom/Cypress, Atheros, Intel, Realtek, MediaTek, Espressif, long‑tail vendors | ✅ done — 116 modules, 14 files |
| 1 | Docs + projects: Nexmon, CSI toolchains, firmware‑RE, techniques, true‑SDR yardstick, glossary, RTL‑SDR lineage | ✅ done |
| 2 | RE walkthroughs (Ghidra · D11 ucode · ESP32 · ath9k · Intel 5300) · PicoScenes/openwifi · Wi‑Fi 7 · 60 GHz · HaLow · hardware index · Tier‑4 audit | ✅ done — +28 modules, 14 files |
| 3 | Exhaustive per‑vendor part sweeps (Intel · Realtek · Atheros · Broadcom · MediaTek · long‑tail) · RTL8812AU/mt76/nRF52/openwifi walkthroughs · UWB · CTC · FTM · Tier‑2 CSI audit | ✅ done — +217 modules, 14 files |
| 4 | Adjacent PHYs (BLE/802.15.4 · LoRa/sub‑GHz · router SoCs · radar/UWB) · gr‑ieee802‑11 · open‑AR9271 · nexmon‑CSI · Flipper walkthroughs · Tier‑3 audit · passive radar · 802.11az · RF‑safety · GNU Radio OOT · canon | ✅ done — +72 modules, 14 files |
| 5 | Firmware‑RE deep dives (BCM4339 Shadow‑Wi‑Fi · ESP32 raw TX · mt76 · BL602) · RISC‑V/open Wi‑Fi · 802.11bf · CSI‑ML + HAR pipeline · driver/lib indexes · decision guide · Tier‑1 audit | ✅ done — +33 modules, 14 files |
| 6 | Cellular baseband/diag & GNSS repurposing · productized + defensive sensing · Tier‑5 open‑fw audit · regulatory/front‑end refs · methodology · capability index | ✅ done — +39 modules, 16 files |
| 7 | Open‑firmware classics (OpenFWWF · carl9170 · AX‑CSI) · Linux/Android stack integration · 802.11 standards ref · history · comparison tables · FAQ · datasheet audit | ✅ done — +14 modules, 13 files |
| 8 | Module integrators (Murata/AMPAK/AzureWave/Laird) · SoC‑integrated & IoT/M2M Wi‑Fi · retro lineage (Prism2/HostAP · rt2x00) · gesture/occupancy CSI · sensing limits · audit 2 · awesome‑tools · troubleshooting | ✅ done — +73 modules, 14 files |
| 9 | Consolidation: unified verification summary · kernel‑source cross‑check · Nexus 5 reference build · CSI calibration · testbed & repro checklist · sensing‑app catalog · ethics · sweep 7 | ✅ done — +7 modules, 13 files |
| 10 | Modern‑HW walkthroughs (MT7921/25 · AX210+FeitCSI · PlutoSDR) · multi‑antenna AoA · real‑time CSI viz · Wi‑Fi 7 sensing frontier · changelog · final sweep (long‑tail exhausted: +2) | ✅ done — 8 agents, +2 modules |
| 11 | **Primary-source** entry: AICSemi **AIC8800** (RivieraWaves RW‑nX, ARM Cortex‑M) reversed first‑hand off the host machine's own USB module (`a69c:8d81`, fw v6.4.3.1) — new `chips/aicsemi.md`, Ghidra walkthrough, Tier‑1 verified | ✅ done — +1 module, +1 vendor (602 / 108) |
| 12+ | Polish / site‑ification / re‑verification — the long‑tail is effectively exhausted at ~600 modules; net-new entries now come from **first-hand hardware** rather than web sweeps | queued |

## Vendor / family queue (feeds future cycles)

**Wi‑Fi silicon still to profile or deepen**
- Broadcom/Cypress: BCM4329, BCM4330, BCM4334, BCM4356, BCM4359, BCM4375, BCM4387, BCM43012, BCM43436, BCM43596, CYW43012, CYW4373, CYW89459
- Qualcomm Atheros: AR9271, AR9280, AR9285, AR9287, AR9380, AR9382, AR9462, AR9485, AR9580, QCA9880, QCA9882, QCA9984, QCA6174, QCA6390, QCA6490, WCN3990, WCN6855
- Intel: 4965, 5100/5150, 6200/6300, 7260/7265, 8260/8265, 9260/9560, AX200/AX201, AX210/AX211, BE200
- Realtek: RTL8187, RTL8188EU/EUS, RTL8192CU, RTL8811AU, RTL8812AU/BU, RTL8814AU, RTL8821AU/CU, RTL8720 (RTL8720DN), RTL8730
- MediaTek/Ralink: RT2570, RT2870/RT3070, RT5370, MT7601U, MT7610U, MT7612U, MT7615, MT7663, MT7915, MT7921, MT7922
- Espressif: ESP8266, ESP32, ESP32‑S2, ESP32‑S3, ESP32‑C2, ESP32‑C3, ESP32‑C5, ESP32‑C6, ESP32‑H2 (802.15.4)

**Other‑wireless modules that repurpose to bare radios**
- Nordic: nRF24L01+, nRF51, nRF52 (RADIO test mode / `radiotest`), nRF53, nRF54
- TI: CC1101, CC1310/CC1312, CC2500, CC2531/CC2540 (BLE sniffer), CC13xx/CC26xx, WL18xx (WiLink)
- Silicon Labs: EFR32 (Flex Gecko), CP210x‑adjacent radios
- Microchip/Atmel: ATmega128RFA1, AT86RF2xx (802.15.4)
- Bluetooth sniffing/attack: Ubertooth One, Sonoff/nRF Sniffle, TI packet sniffer
- Sub‑GHz/LoRa: Semtech SX127x/SX126x, HopeRF RFM9x
- Wi‑Fi HaLow (802.11ah): Morse Micro MM6108
- 60 GHz (802.11ad): Qualcomm/Wilocity QCA6320/QCA9500 (WiGig, used in passive/active radar research)
- UWB: Qorvo/Decawave DW1000/DW3000, NXP Trimension
- Quantenna (QSR10G), Celeno (CL2x4x, doppler/sensing), Cypress/Infineon AIROC

**Techniques still to write up**
- Wi‑Fi passive radar / bistatic radar with commodity cards
- FMCW‑style ranging and Wi‑Fi round‑trip‑time (802.11mc FTM) as a sensing primitive
- Cross‑technology communication (Wi‑Fi → ZigBee/BLE emulation)
- Full‑duplex / covert channels via CSI manipulation
- Beamforming feedback (802.11ac/ax) as an alternative channel probe
- De‑blobbing methodology per architecture (D11 ucode, Xtensa, ARC, Cortex‑R)

## How to push a cycle forward
Grab any item above, profile it against [the schema](../data/schema.json), cite sources, and open a PR. See [CONTRIBUTING.md](../CONTRIBUTING.md). The queue should never empty — when it gets short, add the parts you find that aren't on it.
