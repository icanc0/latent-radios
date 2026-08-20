# 2.4 GHz Non-Wi-Fi Radios: BLE / 802.15.4 / Thread / Zigbee

*Sniffable and repurposable short-range radios — the same "reverse the firmware, expose the PHY" spirit as the Wi-Fi entries, applied to Bluetooth Low Energy, IEEE 802.15.4 (Zigbee / Thread / Matter-over-Thread), and proprietary 2.4 GHz / sub-GHz links.*

> **Read this first — the honest tier for non-Wi-Fi radios.** A BLE or 802.15.4 SoC is *not* a general-purpose SDR. What you actually get by reverse-engineering or by using the vendor's own test hooks is **register/packet-level control of a GFSK/O-QPSK/DSSS modem**: promiscuous sniffing, arbitrary frame injection, carrier/tone transmission, PER/RSSI sweeps, and (on a few parts) an unbuffered demodulated bitstream. That is **Tier 1** in [the ladder](../docs/taxonomy.md) in almost every case — occasionally **Tier 3** where a documented spectral-scan or raw-symbol mode exists (Ubertooth's CC2400, Silicon Labs RAIL energy scan). None of these expose baseband I/Q or an arbitrary-waveform DAC, so **Tier 4/5 does not apply** unless you bolt on a true SDR. Compare against [real SDRs](../docs/true-sdr-comparison.md). Terminology: [glossary](../docs/glossary.md).

The reproducible hands-on path for the Nordic parts (Direct Test Mode + `radio_test` + promiscuous sniffing) lives in the companion walkthrough: **[nRF52 DTM / radio_test / BLE sniffing](../docs/walkthroughs/nrf52-dtm-radiotest-ble-sniffing.md)**.

---

## Why these chips are "latent radios" at all

Every BLE / 802.15.4 SoC contains a hard-macro radio (the modem) plus a thin MCU. Three standard, *documented* hooks turn that modem into a controllable transceiver without any true reverse-engineering:

| Hook | What it gives you | Standard name |
|---|---|---|
| **Direct Test Mode (DTM)** | RF PHY test: TX carrier / modulated packets on a chosen channel, RX packet count, no link layer | Bluetooth Core spec Vol 6 Part F; driven over 2-wire UART or HCI |
| **Vendor radio-test example** | Continuous wave / modulated TX, sweep, PER, per-channel RSSI | Nordic `radio_test`, Silabs `RAILtest`, TI SmartRF Studio, NXP Connectivity Test |
| **Promiscuous / raw RX** | Capture frames not addressed to you, often with CRC/whitening disabled | "sniffer" / "promiscuous" mode in the RADIO/LINK peripheral |

Reverse-engineering starts where the vendor stops: disabling address matching, defeating whitening/CRC, forcing illegal channels/data-rates, or cross-decoding a *different* protocol on the same modem (the classic nRF24 ↔ BLE and 802.15.4 ↔ BLE tricks). See [firmware reversing](../docs/firmware-reversing.md) and [techniques](../docs/techniques.md).

**Already catalogued elsewhere — referenced here, not duplicated:** the mainline Nordic BLE/802.15.4 line `nordic-nrf52` and the legacy `nordic-nrf24l01p`; TI `ti-cc2531-cc2540`, `ti-cc2500`, and the CC13xx/CC26xx multiprotocol family `ti-cc13xx-cc26xx`; Silicon Labs `silabs-efr32`; the Atmel/Microchip 802.15.4 transceivers `atmel-at86rf2xx` and `microchip-at86rf215`; and the Wi-Fi-6/Thread combo parts `espressif-esp32-h2` and `espressif-esp32-c6`. This file fills the gaps: older and newer Nordic silicon, the Ubertooth CC2400, the pre-CC26xx TI 8051 parts, the module ecosystems, and the NXP / ST / Renesas-Dialog / Telink / Realtek / Microchip BLE families.

---

## The tooling that reads/writes these radios

- **nRF Sniffer for Bluetooth LE** — Nordic's free firmware + Wireshark extcap plugin; runs on nRF52840/52833/52832 dongles and DKs. Follows one connection, all advertising channels, all BT5 PHYs. *Vendor-blessed, closed firmware.*
- **[Sniffle](https://github.com/nccgroup/Sniffle)** (NCC Group) — open-source BLE 5 sniffer. **Runs on TI hardware only** (CC26x2R, CC2652RB/P/R7, CC1352R/P/P7, CC2651P3, CC1354P10 LaunchPads, SONOFF CC2652P dongle, Electronic Cats CatSniffer). Captures all three primary advertising channels with one radio, all BT5 PHY modes (1M/2M/coded), extended advertising, CSA #1/#2; PCAP + Wireshark. The best free BLE sniffer today.
- **[BTLEJack](https://github.com/virtualabs/btlejack)** (Damien Cauquil) — BLE connection sniff / jam / hijack. Runs on **nRF51822** boards (BBC micro:bit, Adafruit Bluefruit LE, PCA10028). Uses register-level RADIO abuse the stack never intends.
- **[Ubertooth](https://github.com/greatscottgadgets/ubertooth)** (Great Scott Gadgets) — open hardware + firmware BT/BLE sniffer and 2.4 GHz spectrum analyzer built on the **TI CC2400** (below).
- **TI SmartRF Packet Sniffer 2** / legacy **Packet Sniffer** — captures BLE and IEEE 802.15.4 with CC13xx/CC26xx and CC2531 dongles; Wireshark export.
- **nrf-research-firmware / MouseJack** ([Bastille](https://github.com/BastilleResearch/nrf-research-firmware)) — turns nRF24LU1+/nRF51 into an nRF24 ShockBurst promiscuous sniffer/injector; the CVE-2016-* wireless-mouse/keyboard work.
- **[KillerBee](https://github.com/riverloopsec/killerbee)** — 802.15.4/Zigbee attack framework; drives Atmel RZUSBstick, ApiMote, TI CC2531, and CC13xx sniffers.
- **[OpenThread](https://github.com/openthread/openthread) `ot-cli` + RCP / spinel** — a Radio Co-Processor build exposes a raw 802.15.4 PHY (transmit/receive/energy-scan) over a serial API, which doubles as a promiscuous-capable radio driver on nRF52840, EFR32, KW41Z, CC1352, and DA-series parts.

Datasets, CSI-adjacent sensing, and the true-SDR baseline are cross-referenced in [wifi-sensing-datasets](../projects/wifi-sensing-datasets.md), [csi-toolchains](../projects/csi-toolchains.md), and [rtl-sdr-lineage](../projects/rtl-sdr-lineage.md).

---

## Quick tier map (net-new entries)

| Chip / family | Vendor | Radios | Best raw hook | Tooling | Tier |
|---|---|---|---|---|---|
| nRF51822/824 | Nordic | BLE, prop 2.4, nRF24 | RADIO regs, DTM | BTLEJack, MouseJack, nRF Sniffer | 1 |
| nRF5340 | Nordic | BLE, 802.15.4 | net-core RADIO, DTM, `radio_test` | nRF Sniffer, OpenThread RCP | 1 |
| nRF54L15 | Nordic | BLE, 802.15.4, prop 4 Mbps | RADIO, `radio_test`, DTM | nRF Sniffer | 1 |
| nRF54H20 | Nordic | BLE, 802.15.4, prop | RADIO, DTM | (emerging) | 1 |
| CC2400 | TI | 2.4 GHz FSK transceiver | **unbuffered demod + RSSI sweep** | **Ubertooth** | **3** |
| CC2430/2431 | TI | 802.15.4 (CC2420 core)+8051 | RF regs, test modes | SmartRF, KillerBee (CC2531 proxy) | 1 |
| CC2510/2511 | TI | 2.4 GHz FSK (CC2500 core)+8051 | RF regs, PN9/CW test | SmartRF Studio | 1 |
| CC2541 | TI | BLE + 8051 | radio regs, DTM, obs. mode | SmartRF, promiscuous FW | 1 |
| BGM/MGM modules | Silabs | BLE / 802.15.4 (EFR32 die) | **RAIL / RAILtest** | RAILtest, Simplicity | 1 |
| KW41Z/KW45/K32W/KW21 | NXP | BLE + 802.15.4/Thread | Connectivity Test, DTM, prom. | OpenThread, KillerBee | 1 |
| BlueNRG-1/2/LP/MS | ST | BLE (+ prop 2.4 on -LP) | **radio HAL** raw TX/RX, DTM | ST radio driver samples | 1 |
| STM32WB / WBA | ST | BLE, 802.15.4, Thread | DTM via HCI (CPU2 blob) | ST DTM, OpenThread | 1 |
| DA14531/535 | Renesas/Dialog | BLE | `prod_test`/DTM, radio regs | SmartSnippets, DTM | 1 |
| DA1469x/1470x | Renesas/Dialog | BLE (+ prop 2.4) | `ble_test`, radio API | SmartBond SDK | 1 |
| TLSR825x/827x/921x | Telink | BLE, 802.15.4, Zigbee, prop | **open register-level RADIO** | pvvx FW, Telink SDK | 1 |
| RTL8762C/D | Realtek | BLE | DTM, closed SDK radio API | vendor DTM | 1 |
| RN487x / BM70/71 | Microchip | BLE (module) | DTM / test AT cmds | vendor test tool | 1 |
| PIC32CX-BZ (WBZ451) | Microchip | BLE + 802.15.4/Zigbee | Harmony radio test, DTM | MPLAB Harmony | 1 |

---

## Nordic Semiconductor

Nordic's `RADIO` peripheral is the reference design for "documented modem you can drive by hand": its product specifications publish every register (MODE, PCNF0/1, CRCCNF, DATAWHITEIV, FREQUENCY, TXPOWER, tasks/events). That is what makes Nordic parts the workhorses of BLE research. The mainline `nordic-nrf52` entry covers **nRF52805 / 52810 / 52811 / 52820 / 52832 / 52833 / 52840** — all the same RADIO block, differing in flash/RAM, 802.15.4 support (811/820/833/840), and long-range coded PHY. The three net-new Nordic entries are the *older* nRF51 and the *newer* nRF53/nRF54 generations.

### nRF51822 — the BTLEJack / MouseJack chip
Cortex-M0, 2.4 GHz GFSK RADIO supporting BLE 1M/2M and Nordic proprietary rates including the **nRF24L01+ ShockBurst** framing. Because the RADIO's whitening, address length, and CRC are register-controlled, the nRF51 can be pointed at *foreign* protocols: BTLEJack sniffs/hijacks BLE connections on it, and Bastille's MouseJack firmware turns it into an nRF24 promiscuous sniffer/injector. Fully register-documented; the SoftDevice (BLE stack) is a closed binary but you bypass it entirely for radio work. **Tier 1** (monitor + injection + covert cross-protocol).

### nRF5340 — dual-core, network-core radio
Application Cortex-M33 + a dedicated **network core** (M33) that owns the RADIO. Same documented RADIO peripheral as nRF52, adds BLE long range, 802.15.4 (Thread/Zigbee/Matter), and runs `radio_test` / DTM on the net core. Supported by nRF Sniffer and as an OpenThread RCP. Net-core firmware image is user-buildable (Zephyr/nRF Connect SDK), radio registers documented — openness **documented/patchable**. **Tier 1.**

### nRF54L15 — 2024 successor
Cortex-M33 + RISC-V "FLPR" coprocessor, new-generation multiprotocol RADIO: BLE 1M/2M/coded, 802.15.4, and a **4 Mbps proprietary** GFSK mode. `radio_test` and DTM ship in nRF Connect SDK; RADIO registers documented in the product spec. **Tier 1**, with the highest proprietary data-rate of the family (useful for custom high-throughput 2.4 GHz links).

### nRF54H20 — high-end multicore
Multiple Cortex-M33 cores + coprocessors, 2.4 GHz radio for BLE / 802.15.4 / proprietary. Newest and least community-tooled, but the same documented-RADIO philosophy; expect DTM/`radio_test` parity as nRF Connect SDK support matures. **Tier 1 (reported).**

---

## Texas Instruments (pre-CC26xx parts)

The modern TI multiprotocol line (**CC2640/2650/2652/1352**, plus the Zigbee/BLE dongles CC2531/CC2540) is catalogued under `ti-cc13xx-cc26xx` and `ti-cc2531-cc2540`, and `ti-cc2500` covers the bare 2.4 GHz FSK transceiver. The net-new TI entries are the parts those omit.

### CC2400 — the Ubertooth radio (the interesting one)
A 2.4 GHz FSK/GFSK **transceiver** (not an SoC) from ~2006. Its importance: the CC2400 can be put into a mode that streams the **demodulated, unbuffered bitstream** out a serial pin *and* perform a fast **RSSI/energy sweep across the band**. Great Scott Gadgets' **Ubertooth One** (CC2400 + LPC175x ARM) uses exactly this to do Bluetooth BR/EDR and BLE sniffing and to run `ubertooth-specan` / a Kismet spectrum-analyzer plugin. That raw-symbol + spectral-scan access is why this single part earns **Tier 3** where the rest of the family is Tier 1 — it is the closest a commodity 2.4 GHz chip gets to "SDR-lite" without a real ADC. Open firmware, open hardware. Capabilities: monitor, injection, spectral-scan, open-firmware.

### CC2430 / CC2431 — 8051 + 802.15.4
First-generation Zigbee SoC: a CC2420-class IEEE 802.15.4 O-QPSK/DSSS radio bonded to an 8051. The CC2431 adds a hardware "location engine" (RSSI-based positioning). Register-level RF control and TI test modes (unmodulated carrier, PN9). Sniffing is normally done with the newer CC2531 dongle + SmartRF Packet Sniffer / KillerBee, but the CC2430 radio core is the same 802.15.4 PHY. **Tier 1.**

### CC2510 / CC2511 — 8051 + CC2500 radio
2.4 GHz FSK/GFSK/MSK SoC: the `ti-cc2500` modem plus an 8051 (CC2511 adds USB). SmartRF Studio exposes continuous-wave and PN9 modulated test transmissions and full register editing; the packet engine can be disabled for near-raw framing. Sub-GHz siblings CC1110/CC1111 share the architecture (see [lora-subghz](lora-subghz.md) for the sub-GHz world). **Tier 1.**

### CC2541 — BLE + 8051
Sibling of the catalogued CC2540: same 8051 + BLE radio, lower power, adds I²C, drops USB. Runs TI's BLE stack; community "promiscuous"/observer firmwares and DTM give raw advertising capture. Grouped in spirit with `ti-cc2531-cc2540` but a distinct part number. **Tier 1.**

---

## Silicon Labs — BGM / MGM / FG modules

The **EFR32** Blue/Mighty/Flex Gecko die is catalogued as `silabs-efr32`. Net-new here is the **module** ecosystem and the radio-abstraction tooling that makes them latent radios:

- **BGM** (BLE), **MGM** (Zigbee/Thread 802.15.4), **FGM/Flex** (proprietary sub-GHz **and** 2.4 GHz) — pre-certified modules wrapping an EFR32BG/MG/FG die with crystal, matching, and antenna (e.g. BGM220, MGM210/240, FGM230).
- The lever is **RAIL** (Radio Abstraction Interface Layer) and its `RAILtest` app: tone/CW TX, arbitrary-channel packet TX/RX, **energy/RSSI scan**, PER, and a fairly free PHY definition (data rate, deviation, sync word) via the Radio Configurator. This is a documented path to a custom 2.4 GHz proprietary link and to promiscuous 802.15.4.
- Firmware: application source is open (Gecko SDK / Simplicity Studio); the link/stack and lowest PHY tables are vendor-provided. Openness **partially-documented**. **Tier 1** (RAIL energy scan brushes spectral-scan but is coarse).

Bands: 2.4 GHz for BGM/MGM; add sub-GHz for FG/Flex parts.

---

## NXP — Kinetis W (KW) and K32W

**KW41Z / KW31Z / KW21Z** (Cortex-M0+), **K32W061/041** (M0+/M4, successor), and the newer **KW45 / K32W1** (M33): multimode radios doing **BLE + IEEE 802.15.4** simultaneously (dynamic/GenFSK), targeting Thread, Zigbee, and Matter. Raw access comes from NXP's **Connectivity Test / RF test** application (CW, PRBS, per-channel PER), DTM, and an 802.15.4 **promiscuous** mode; OpenThread and KillerBee-style capture run on them. The "GenFSK" personality is explicitly a *generic* configurable 2.4 GHz FSK link — the documented route to a custom proprietary protocol. Connectivity stack is a closed library; radio test is documented. **Tier 1.** (KW21 here denotes the KW2xZ 802.15.4-only members.)

---

## STMicroelectronics

### BlueNRG-1 / BlueNRG-2 / BlueNRG-LP
Cortex-M0/M0+ BLE SoCs whose **radio driver is a documented low-level HAL**: you can transmit and receive *raw* 2.4 GHz packets (set frequency, whitening, CRC, sync word, schedule TX/RX action) without the BLE link layer — ST ships "radio" example projects that build proprietary point-to-point links. BlueNRG-LP adds a proprietary 2.4 GHz mode and better multi-link. DTM is supported for PHY test. Stack is a closed binary; the radio HAL is open/documented. **Tier 1** — one of the more injection-friendly closed-stack parts.

### BlueNRG-MS
A BLE **network coprocessor** (host talks ACI/HCI over SPI). No application core, no user radio access beyond HCI/DTM — effectively **Tier 0/1**; listed for completeness because it appears on countless modules but is *not* a repurposable radio the way BlueNRG-1/2 are.

### STM32WB55 / STM32WBA
Dual-core STM32 (M4 application + M0+ "CPU2" running the wireless stack) for BLE / 802.15.4 / Thread / Zigbee / Matter; WBA is a single-core M33 successor. **CPU2 is a signed, closed binary blob** — you cannot reprogram the radio directly. Your raw hooks are the stack's **DTM (HCI)** and OpenThread's RCP/energy-scan. Powerful product silicon, but the least "reverse-and-expose" of the group. Openness **closed** (CPU2). **Tier 1.**

---

## Renesas (ex-Dialog Semiconductor) — SmartBond

### DA14531 / DA14535 ("SmartBond TINY")
Tiny, cheap Cortex-M0+ BLE SoCs. Raw access via **`prod_test`** firmware and DTM (CW/modulated TX, RX counting) and register-level radio control in the SmartSnippets SDK (source-available). Popular in dongles and beacons; register-documented enough for proprietary 2.4 GHz experiments. **Tier 1.**

### DA1469x (DA14691/95/97/99) and DA1470x
Cortex-M33 SmartBond with a coprocessor-driven radio, higher TX power, and a **`ble_test` / radio test** path plus an SDK radio API. DA1470x extends flash/graphics. SDK is source-available (register-level), stack partially documented — openness **partially-documented**. **Tier 1**, with proprietary 2.4 GHz modes documented on the newer parts.

---

## Telink — the most open of the bunch

**TLSR825x** (TLSR8251/8253/8258, ARC/proprietary core), **TLSR827x** (TLSR8278), and **TLSR921x / TLSR9518 "B91"** (RISC-V) are multiprotocol 2.4 GHz SoCs: **BLE + IEEE 802.15.4 + Zigbee + proprietary**. They power a huge slice of cheap BLE sensors, LED controllers, and Zigbee devices — and are the darling of the flashing community. The **RADIO is register-programmable at a low level**, and Telink publishes SDK source; combined with community reverse-engineering this makes them the *most* repurposable non-Nordic BLE parts:

- **[pvvx firmware](https://github.com/pvvx)** — custom open firmware for TLSR825x thermometers/sensors (**[ATC_MiThermometer](https://github.com/pvvx/ATC_MiThermometer)** supports TLSR8250/8251/8253/8258/8359/8656), with OTA and open build via the Telink toolchain or a GNU makefile.
- Telink BLE/Zigbee SDKs (source) + community Zigbee stacks feed **[zigbee2mqtt](https://www.zigbee2mqtt.io/)** and Home Assistant.
- Register-level GFSK control enables custom 2.4 GHz links and raw sniffing experiments.

Openness **documented/open** (community + vendor source). **Tier 1** — but the *ease* of getting there is unmatched outside Nordic. Bands: 2.4 GHz (BLE, 802.15.4).

---

## Realtek — RTL8762

**RTL8762C / RTL8762D** are Cortex-M4/M0 BLE SoCs found in cheap smart bands and beacons. DTM and a vendor radio/DTM API exist, but the SDK is largely closed and community RE is thinner than Telink's. Repurposable as a bare BLE radio via DTM (CW/packet test); raw promiscuous sniffing is not a first-class documented mode. Openness **closed/partially-documented**. **Tier 1 (reported).**

---

## Microchip

### RN4870 / RN4871 and BM70 / BM71 (modules)
AT-command BLE **modules** (built on Microchip/ISSC IS187x BLE silicon). You script them over UART; radio access is limited to the module's **DTM / RF test** commands (CW, modulated packet TX, RX). Great for a controlled BLE PHY test source, weak for arbitrary sniffing. Openness **closed**. **Tier 1.**

### PIC32CX-BZ2 / WBZ451 (and BZ3/WBZ351)
Microchip's modern combo: PIC32 (MIPS/Arm) + **BLE 5 + IEEE 802.15.4** (Zigbee/Thread/Matter) in one SoC/module. MPLAB Harmony 3 provides a **radio/PHY test** (CW, PER, energy detect) and 802.15.4 promiscuous capture; OpenThread runs on it. Openness **partially-documented** (Harmony source + closed stack libs). **Tier 1** — the Microchip analogue of KW45 / EFR32MG.

---

## Cross-protocol tricks worth knowing

- **802.15.4 ↔ BLE cross-decoding** on the same modem underpins [cross-technology communication](../docs/cross-technology-communication.md): a chip demodulating O-QPSK/DSSS can be coaxed into emitting energy a BLE receiver parses, and vice-versa.
- **nRF24 ShockBurst ↔ BLE** on Nordic (and Telink) modems is the MouseJack / BTLEJack lever: same GFSK, different address/whitening/CRC — flip the registers and you sniff the "other" protocol.
- **DTM constant carrier** on any of these is a legal-only lab tone source for antenna/range work — see the regulatory note below.

For UWB and FiRa ranging (a different PHY entirely) see [uwb-fira-ranging](../docs/uwb-fira-ranging.md); for Wi-Fi FTM/RTT distance work see [ftm-rtt-ranging](../docs/ftm-rtt-ranging.md).

---

## Safety & regulatory notes (any transmit)

- **DTM and `radio_test`/`RAILtest`/Connectivity-Test emit real RF.** Continuous-carrier and modulated-packet TX outside a normal protocol can violate 2.4 GHz emission rules (FCC Part 15 / ETSI EN 300 328). Test **into a shielded enclosure or a 50 Ω dummy load**, or under an experimental licence. Keep TX power minimal and dwell short.
- **Injection / jamming / connection hijacking** (BTLEJack, deauth-style 802.15.4 attacks) can be illegal on live networks and disrupt medical/industrial devices sharing the band. Only against hardware you own, in a controlled space.
- **Foreign-protocol reception** (promiscuous sniffing of others' BLE/Zigbee) may be restricted by wiretap/computer-misuse law in your jurisdiction even though it is passive. Know your local rules.
- 802.15.4 channel 26 and some proprietary rates can spill outside band edges when whitening/CRC are disabled — verify with a spectrum analyzer before radiating.

---

## References

- Nordic RADIO peripheral, Direct Test Mode, and `radio_test` — nRF Connect SDK / product specifications: https://docs.nordicsemi.com/
- nRF Sniffer for Bluetooth LE: https://www.nordicsemi.com/Products/Development-tools/nRF-Sniffer-for-Bluetooth-LE
- Sniffle (NCC Group), TI-only BLE 5 sniffer: https://github.com/nccgroup/Sniffle
- BTLEJack (nRF51822): https://github.com/virtualabs/btlejack
- Bastille nrf-research-firmware / MouseJack: https://github.com/BastilleResearch/nrf-research-firmware
- Ubertooth (CC2400): https://github.com/greatscottgadgets/ubertooth
- TI CC2400 datasheet: https://www.ti.com/product/CC2400
- TI CC2430 / CC2510 / CC2541 product pages: https://www.ti.com/product/CC2430 , https://www.ti.com/product/CC2510 , https://www.ti.com/product/CC2541
- Silicon Labs RAIL / RAILtest and Gecko SDK: https://docs.silabs.com/rail/latest/
- NXP Kinetis KW41Z and Connectivity Test: https://www.nxp.com/products/KW41Z ; OpenThread: https://github.com/openthread/openthread
- ST BlueNRG-1/2 radio driver & DTM: https://www.st.com/en/wireless-connectivity/bluenrg-2.html
- STM32WB series: https://www.st.com/en/microcontrollers-microprocessors/stm32wb-series.html
- Renesas/Dialog DA14531 & DA1469x SmartBond SDK: https://www.renesas.com/en/products/wireless-connectivity/bluetooth-low-energy
- Telink TLSR825x / B91 SDKs: https://wiki.telink-semi.cn/ ; pvvx firmware: https://github.com/pvvx ; ATC_MiThermometer: https://github.com/pvvx/ATC_MiThermometer
- Realtek RTL8762: https://www.realtek.com/en/products/communications-network-ics/category/bluetooth
- Microchip RN4870: https://www.microchip.com/en-us/product/RN4870 ; PIC32CX-BZ2 / WBZ451: https://www.microchip.com/en-us/product/PIC32CX1051BZ23048
- KillerBee 802.15.4 framework: https://github.com/riverloopsec/killerbee
- TI SmartRF Packet Sniffer 2: https://www.ti.com/tool/PACKET-SNIFFER-2
