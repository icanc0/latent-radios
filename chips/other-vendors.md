# The Long Tail: Other-Vendor Wi-Fi & Bare Radios as SDRs

Everything the six big vendor files miss. Two populations live here:

1. **Long-tail Wi-Fi silicon** — TI WiLink, Marvell Avastar, Quantenna, Celeno's
   Doppler-sensing parts, Morse Micro's sub-GHz HaLow, and Qualcomm/Wilocity's
   60 GHz WiGig. These are 802.11 chips like the big vendors', but with thinner
   public RE tooling — *except* the 60 GHz parts, where SEEMOO's `nexmon-arc`
   turns a $200 router into a steerable-beam mmWave instrument.
2. **Non-Wi-Fi transceivers routinely repurposed as bare radios.** Nordic, TI
   Sub-1GHz/CCxxxx, Silicon Labs, Microchip/Atmel 802.15.4, Semtech LoRa, and
   Qorvo/Decawave UWB. The *same reverse-and-expose-the-PHY move* applies — but
   most of these chips never had a closed firmware to fight in the first place:
   they are **register machines with fully documented PHYs**, so the "SDR" is
   handed to you at the datasheet level. A few (AT86RF215, DW1000) even export
   **raw complex baseband / channel-impulse-response** as a *documented feature*.

The through-line of this whole project is firmware reversing (see
[../projects/nexmon.md](../projects/nexmon.md),
[../docs/firmware-reversing.md](../docs/firmware-reversing.md)). This file is
where that story bifurcates: half these parts demand firmware surgery, half give
up their PHY for free. For where the ladder tops out with true SDRs, see
[../projects/rtl-sdr-lineage.md](../projects/rtl-sdr-lineage.md) and
[../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md). Terms:
[../docs/glossary.md](../docs/glossary.md).

---

## Part A — Long-tail Wi-Fi silicon

| Chip / family | Vendor | Bands | Top tier | Unlock | Firmware | RE status |
|---|---|---|---|---|---|---|
| WiLink WL18xx | TI | 2.4/5 | 1 (mon/inj) | mac80211 monitor via open `wlcore` | closed blob | closed |
| Avastar 88W8897/8997, SD8887 | Marvell/NXP | 2.4/5 | 1–2 | mwifiex monitor; CSI reported | ThreadX RTOS | RE'd (Project Zero) |
| QSR10G (Topaz/Ruby) | Quantenna | 2.4/5 | 1–2 | on-chip Linux + vendor CSI API | Linux on quad-ARC | partial |
| CL2x4x / CL6000 "Denali" | Celeno→Renesas | 2.4/5/6 | 2 (Doppler) | proprietary WFD only | closed | closed |
| MM6108 / MM8108 (HaLow) | Morse Micro | sub-GHz | 1 (mon/inj) | open mac80211 driver | closed | closed |
| **QCA9500 / QCA6320 (WiGig 60 GHz)** | Qualcomm/Wilocity | 60 GHz | **2–3** | **`nexmon-arc` + Talon Tools** | **ARC ucode** | **patchable** |

### TI WiLink WL18xx — `ti-wl18xx`
2.4/5 GHz 802.11a/b/g/n, SDIO. Ships in BeagleBone-class and industrial Linux
boards (WL1837MOD, WL1835MOD, WL1807MOD, WL1801MOD). The **driver stack is fully
open** — `wlcore` + `wl18xx` + `wlcore_sdio` in mainline Linux, mac80211-based —
so **monitor mode and mac80211 radiotap injection work out of the box** (tier 1).
The **firmware is a closed binary blob** distributed from `git.ti.com`
(`wilink8-wlan/wl18xx_fw`); no PHY telemetry / CSI path is exposed and no public
firmware-patching toolchain exists. Ladder stops at tier 1 unless someone reverses
the blob. Refs:
- https://git.ti.com/cgit/wilink8-wlan/wl18xx_fw/
- https://www.ti.com/tool/WILINK8-WIFI-NLCP

### Marvell / NXP Avastar 88W8897, 88W8997, SD8887 — `marvell-88w8897`
The Wi-Fi in PS4, Microsoft Surface, Chromebooks, Steam Link, and many SDIO IoT
modules (SD8887/SD8897). The `mwifiex` mainline driver gives monitor mode; some
sensing work reports CSI-like access, but there is no maintained public CSI
extractor (tier 1, CSI *reported*). The interesting angle is **firmware RE**: Gal
Beniamini's Project Zero "Over The Air" work reverse-engineered the 88W8897's
Wi-Fi firmware, which runs a **ThreadX RTOS** on the on-chip MAC/PHY controller —
the canonical worked example of prying open a non-Broadcom Wi-Fi firmware with
IDA/Ghidra. That RE targeted exploitation, not SDR features, so tier-2+ remains
theoretical-to-reported. Refs:
- https://googleprojectzero.blogspot.com/2017/04/over-air-exploiting-broadcoms-wi-fi_4.html
- https://github.com/torvalds/linux/tree/master/drivers/net/wireless/marvell/mwifiex

### Quantenna QSR10G — `quantenna-qsr10g`
4×4 / 8×8 802.11ac (QSR1000/QSR10G "Topaz"/"Ruby" SoCs). Unusual because the chip
**runs embedded Linux internally on a cluster of ARC cores**, and Quantenna
publicly marketed **Wi-Fi sensing / CSI** ("Quantenna Sensing") on these parts.
That makes a documented CSI path plausible (tier 2 *reported*) and the on-chip
Linux a partial-openness foothold, but there is no packaged community tool. Refs:
- https://en.wikipedia.org/wiki/Quantenna_Communications

### Celeno CL2x4x / CL6000 "Denali" — `celeno-cl6000`
Celeno (acquired by Renesas, 2022) built **Wi-Fi Doppler Imaging** into its
silicon — the earlier CL2440/CL2444 (CL2x4x) client/AP parts and the newer CL6000
"Denali" family (CL6020/CL6025) that fuses Wi-Fi 6/6E + BLE + a **Doppler radar
mode** to detect presence, falls, gestures, and even breathing through walls, in
5/6 GHz. Architecturally this is the purest "Wi-Fi-as-radar" product in the
catalog — but the Doppler engine is a **closed, proprietary feature (WFD)** with
no public API, firmware source, or RE tooling. Tier 2 by capability, but locked
(status *reported*). Refs:
- https://www.renesas.com/en/about/newsroom/celeno-announces-new-innovation-wi-fi-doppler-imaging
- https://www.prnewswire.com/news-releases/celenos-wi-fi-doppler-imaging-technology-wins-the-2019-best-wi-fi-innovation-award-at-wi-fi-now-london-conference-300958215.html

### Morse Micro MM6108 / MM8108 — `morsemicro-mm6108`
**Wi-Fi HaLow (802.11ah)** — OFDM in the **sub-1 GHz** ISM band (902–928 MHz US),
1/2/4/8 MHz channels, up to 32.5 Mbps, single-chip radio+PHY+MAC. Notable for this
catalog because it is a *sub-GHz OFDM Wi-Fi* with an **open mac80211 Linux driver**
(`morse` driver, upstreaming in progress), so **monitor + injection** are
reachable (tier 1) at frequencies where propagation and wall penetration make
sensing attractive. Firmware is a closed blob; no CSI toolchain yet, though HaLow
CSI is an active research direction. Dev HW: MM6108-EKH01/05/08 kits (many pair the
SoC with an STM32 + Raspberry Pi). Refs:
- https://www.morsemicro.com/chips/
- https://www.mouser.com/en/new/morse-micro/morse-micro-mm6108-mf08651-us-module/

### Qualcomm / Wilocity QCA9500 & QCA6320 (WiGig 60 GHz) — `qualcomm-qca9500` ⭐
The standout of the whole file. 802.11ad, **60 GHz**, single-stream over a
**32-element phased array** with analog beamforming. QCA9500 is the combined part;
QCA6320 is the 60 GHz MAC/baseband (paired with the QCA6310 RF front-end). It ships
in the **TP-Link Talon AD7200** router, **Netgear Nighthawk X10 R9000**, and
several Wilocity-based laptops/docks.

SEEMOO's **Talon Tools** turns the Talon AD7200 into a practical mmWave research
instrument: **`nexmon-arc`** ports the Nexmon firmware-patching framework to the
chip's **ARC (Argonaut RISC Core) microcode**, on top of a ported LEDE
(`lede-ad7200`). With it you can read **per-sector channel estimates (CSI)** and
**author arbitrary custom beam patterns** loaded into the array — i.e., steer and
shape a 60 GHz beam under software control. That is tier 2 (channel telemetry)
shading into tier 3/4 territory (programmable spatial front-end), and it is the
substrate for a body of 60 GHz mmWave sensing/imaging research on commodity
hardware. Firmware openness = **patchable** (ARC ucode via nexmon-arc + Ghidra).
Refs:
- https://github.com/seemoo-lab/talon-tools
- https://seemoo-lab.github.io/talon-tools/
- https://github.com/seemoo-lab/lede-ad7200
- https://dl.acm.org/doi/10.1145/3267204.3268070

---

## Part B — Non-Wi-Fi transceivers as bare radios

The recurring pattern: these are **narrowband ISM transceivers with fully
documented register-level PHYs**. You don't reverse a closed firmware — you *read
the datasheet* and drive the modulator directly. Several expose escape hatches
(async/transparent bit modes, raw CIR, or a literal I/Q port) that push them well
up the ladder.

| Chip / family | Vendor | Bands | Top tier | Key capability | Firmware / core |
|---|---|---|---|---|---|
| nRF24L01+ | Nordic | 2.4 | 1 | pseudo-promiscuous sniff (Goodspeed) | fixed-fn transceiver |
| nRF51/52/53/54 | Nordic | 2.4 | 1 | documented RADIO + radiotest | Cortex-M (documented) |
| CC1101 | TI | sub-GHz | 1 | async/transparent raw OOK/FSK | fixed-fn (documented) |
| CC1111 (YARD Stick One) | TI | sub-GHz | 1 | RfCat open firmware | 8051 (open) |
| CC2500 | TI | 2.4 | 1 | GFSK/OOK proprietary | fixed-fn (documented) |
| CC2531 / CC2540 | TI | 2.4 | 1 | 802.15.4 / BLE sniffer | 8051 |
| CC13xx / CC26xx | TI | sub-GHz+2.4 | 1–3 | RF-core "proprietary mode" | M3 app + M0 RF core (patchable) |
| EFR32 Flex/Mighty Gecko | Silicon Labs | sub-GHz+2.4 | 1 | RAIL arbitrary proprietary PHY | Cortex-M (partial) |
| AT86RF2xx / ATmega128RFA1 | Microchip/Atmel | sub-GHz+2.4 | 1 | KillerBee 802.15.4 mon/inj | fixed-fn / AVR |
| **AT86RF215** | Microchip | sub-GHz+2.4 | **4** | **documented raw I/Q LVDS port** | baseband bypassable |
| SX127x / SX126x / RFM9x | Semtech/HopeRF | sub-GHz | 1 | LoRa + raw FSK/OOK continuous | fixed-fn (documented) |
| **DW1000 / DW3000** | Qorvo/Decawave | UWB | **2–3** | **complex CIR accumulator readout** | fixed-fn (documented) |
| Ubertooth One (CC2400) | Great Scott Gadgets | 2.4 | **3** | open FW + Specan spectrum scan | Cortex-M3 (open) |

### Nordic nRF24L01+ — `nordic-nrf24l01p`
2.4 GHz GFSK, Nordic's proprietary "Enhanced ShockBurst" — a *transceiver only*,
no MCU. Travis Goodspeed's 2011 discovery: by setting a 2-byte address (invalid
per datasheet but accepted), disabling CRC, and using the preamble as a pseudo-MAC,
the chip becomes a **pseudo-promiscuous sniffer** for other 2.4 GHz ShockBurst /
compatible traffic. This underpins Bastille's **MouseJack** and the
**`nrf-research-firmware`** on the Crazyradio PA (nRF24LU1+, the USB-MCU sibling).
Tier 1 (monitor + injection within its own PHY family). Fully documented PHY, no
firmware to reverse. HW: generic nRF24L01+ modules, Crazyradio PA. Refs:
- http://travisgoodspeed.blogspot.com/2011/02/promiscuity-is-nrf24l01s-duty.html
- https://github.com/BastilleResearch/mousejack

### Nordic nRF51 / nRF52 / nRF53 / nRF54 — `nordic-nrf52`
The workhorse of DIY 2.4 GHz radio hacking, because Nordic **fully documents the
RADIO peripheral** at register level (openness = **documented**, not closed). The
SoftDevice is closed, but you bypass it with bare-metal code and Nordic's own
**`radio_test`/`radiotest`** sample: configure BLE 1M/2M/Coded, IEEE 802.15.4
(ch 11–26), or proprietary GFSK; carrier/tone TX; sweep TX power; promiscuous RX.
This is the platform under a whole ecosystem: **Sniffle** (Sultan Qasim Khan's
open BLE5 sniffer, nRF52840, long-range + extended advertising), Nordic's official
**nRF Sniffer** for BLE and for **802.15.4**, and countless BLE/ANT/Crazyflie
tools. Cores: Cortex-M0 (nRF51), M4F (nRF52), M33 (nRF53/nRF54). Tier 1, with
enough raw-RADIO control to shape arbitrary GFSK packets. HW: nRF52840 Dongle &
DK, Adafruit Feather nRF52, BBC micro:bit (nRF51822/nRF52833). Refs:
- https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples/peripheral/radio_test/README.html
- https://github.com/nccgroup/Sniffle
- https://github.com/NordicSemiconductor/nRF-Sniffer-for-802.15.4

### TI CC1101 — `ti-cc1101`
The iconic sub-GHz hacking transceiver (300–348 / 387–464 / 779–928 MHz),
2-FSK/GFSK/4-FSK/MSK/ASK/OOK. No MCU — driven over SPI by an external host. Its
killer feature for RE/replay is **asynchronous / synchronous serial "transparent"
mode**: feed an arbitrary bit pattern in on a GPIO and the chip keys the PA
directly, letting you replay *captured OOK/FSK waveforms* verbatim without
understanding the protocol (approaching arbitrary-waveform for these simple
modulations). Fully documented; the radio in the **Flipper Zero**, countless
Arduino/RPi projects, and 433/315 MHz remote-cloning tools. Tier 1. Refs:
- https://www.ti.com/product/CC1101

### TI CC1111 / YARD Stick One — `ti-cc1111-yardstick`
CC1111 = CC1101 radio + **8051 MCU + USB**. Great Scott Gadgets' **YARD Stick
One** runs **RfCat** (atlas0fd00m), an **open** firmware exposing the transceiver
from an interactive Python shell: 2-FSK/GFSK/MSK/ASK/OOK, raw register access,
and RSSI-sweep spectrum views. RfCat also supports CC1110/CC2510/CC2511 sibling
parts. Openness = **open**; toolchain = RfCat + sdcc. HW: YARD Stick One, IM-Me,
TI Chronos. Tier 1. Refs:
- https://greatscottgadgets.com/yardstickone/
- https://github.com/atlas0fd00m/rfcat

### TI CC2500 — `ti-cc2500`
The 2.4 GHz sibling of CC1101 (GFSK/OOK/MSK). Same transparent-mode raw-bitstream
trick; the radio in many 2.4 GHz RC transmitters and wireless peripherals. Tier 1,
documented PHY. Refs:
- https://www.ti.com/product/CC2500

### TI CC2531 / CC2540 — `ti-cc2531-cc2540`
8051-core radios: CC2531 = IEEE **802.15.4 / Zigbee** USB, CC2540 = **BLE**.
Both are stock sniffers with TI-provided firmware, plus the community **`whsniff`**
+ Wireshark path (CC2531) and **ZBOSS** `zboss_sniffer.hex`. Tier 1 (monitor within
their standards; injection with custom firmware). HW: the ubiquitous CC2531 USB
stick, CC Debugger. Refs:
- https://github.com/homewsn/whsniff
- https://www.zigbee2mqtt.io/advanced/zigbee/04_sniff_zigbee_traffic.html

### TI CC13xx / CC26xx — `ti-cc13xx-cc26xx`
CC1310/CC1312R (sub-GHz), CC2650/CC2652R (2.4 GHz), CC1352 (dual-band). Two-core:
a **Cortex-M3/M4 application core** plus a dedicated **Cortex-M0 "RF Core"** that
runs the radio from a **patchable ROM ("RF patches")** behind a documented radio
command interface. The RF Core's **"proprietary mode"** lets you configure custom
sub-GHz/2.4 GHz PHYs (arbitrary FSK/OOK params, packet formats), and RSSI/CCA
gives coarse spectrum sensing — so with effort this reaches toward tier 3.
SmartRF Studio + SmartRF Packet Sniffer 2 (Wireshark) drive capture. Openness =
**patchable / partially-documented** (driverlib open, RF ROM closed but patchable).
HW: LAUNCHXL-CC1352R, CC1310/CC26x2 LaunchPads. Tier 1–3. Refs:
- https://www.ti.com/product/CC1310
- https://www.ti.com/tool/PACKET-SNIFFER

### Silicon Labs EFR32 Flex/Mighty Gecko — `silabs-efr32`
Cortex-M4/M33 wireless SoCs (EFR32FG = proprietary sub-GHz+2.4 GHz, EFR32MG =
Zigbee/Thread/BLE). The **RAIL** (Radio Abstraction Interface Layer) library
exposes an **arbitrary proprietary PHY** builder — custom modulation, symbol rate,
framing — plus energy/RSSI scanning and a TX tone/stream mode. Radio internals are
closed but RAIL is documented (openness = **partially-documented**). Tier 1 with a
path to custom PHYs. HW: EFR32FG13/FG14/FG23/FG25 dev kits; the radio in many
Zigbee/Matter products. Refs:
- https://www.silabs.com/documents/public/data-sheets/efr32fg13-datasheet.pdf

### Microchip/Atmel AT86RF2xx & ATmega128RFA1 — `atmel-at86rf2xx`
IEEE **802.15.4** transceivers: AT86RF230/231/233 (2.4 GHz), AT86RF212(B)
(sub-GHz), and the **ATmega128RFA1 / ATmega256RFR2** SoCs (AVR + integrated
802.15.4 radio). The classic Zigbee attack platform: **KillerBee** drives the
**Atmel RZUSBstick** (AT86RF230) and RZ Raven for **monitor + injection** on
802.15.4. Documented PHYs; RIOT/Contiki drive them bare-metal. Tier 1. Refs:
- https://github.com/riverloopsec/killerbee
- https://www.microchip.com/en-us/product/at86rf233

### Microchip AT86RF215 — `microchip-at86rf215` ⭐
The one "accidental true-ish SDR" of Part B. A dual-band 802.15.4g transceiver
(sub-1 GHz **and** 2.4 GHz, independent) whose datasheet exposes a **documented
raw I/Q data interface**: three LVDS lanes (1× TX, 2× RX), **13-bit I/Q samples
at up to ~4 MHz**. You can **bypass the on-chip baseband entirely**, pull raw
complex samples out for your own DSP, and **feed arbitrary I/Q in for transmit** —
i.e., author a baseband IQ buffer and radiate it, the definition of **tier 4
(arbitrary-waveform / raw-iq)** — with *no firmware reversing at all*, because the
manufacturer documents the port. Bandwidth is narrow, but it is genuine
front-end-level access on a commodity ISM chip. HW: AT86RF215 eval boards; used in
OpenWSN and SDR-adjacent 802.15.4g research. Tier 4 (narrowband). Refs:
- https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42415-WIRELESS-AT86RF215_Datasheet.pdf
- https://wirelesspi.com/on-microchip-at86rf215-radios/

### Semtech SX127x / SX126x + HopeRF RFM9x — `semtech-sx127x`
**LoRa** (Chirp Spread Spectrum) transceivers plus a full **(G)FSK/OOK** legacy
mode. SX1272/76/77/78/79 (LoRa+FSK sub-GHz), SX126x (newer), SX1280 (2.4 GHz LoRa);
**HopeRF RFM95/96/97/98** are drop-in modules wrapping SX1276/8. Bare transceiver,
external MCU. Raw-radio access: **continuous FSK/OOK mode** streams an arbitrary
bitstream (tones, jamming, replay), and the LoRa engine gives you CSS TX/RX
directly. The *reverse-engineering* of the LoRa PHY itself was done on real SDRs
(Matt Knight / Bastille **`gr-lora`**, and rpp0 **`gr-lora`**) — a good example of
using an SDR to crack a closed PHY that these chips then let you speak natively.
Tier 1. HW: RFM95W, Adafruit LoRa Feather, Heltec/TTGO LoRa32, Dragino. Refs:
- https://github.com/BastilleResearch/gr-lora
- https://github.com/rpp0/gr-lora
- https://www.semtech.com/products/wireless-rf/lora-connect/sx1276

### Qorvo / Decawave DW1000 & DW3000 — `qorvo-dw1000` ⭐
**Ultra-wideband** (IEEE 802.15.4a / 4z), ~500 MHz channels at 3.5–6.5 GHz. The
SDR-relevant feature is documented and killer: the receiver's **CIR accumulator**
exposes the full **complex channel impulse response** — up to **1016 taps, each a
16-bit I + 16-bit Q value at ~1 ns spacing**. That is time-domain channel
telemetry with amplitude *and* phase (a UWB analog of CSI), directly readable over
SPI, and it is the basis for a large body of **device-free localization, occupancy,
and radar-style sensing** research. Tier 2 (complex channel telemetry) reaching
toward tier 3 (raw PHY snapshot). Fully documented register machine; no firmware
to reverse. HW: DWM1000 / DWM1001 modules, DW3110/DW3220, MDEK1001 kit. Refs:
- https://www.mdpi.com/1424-8220/22/16/6255
- https://www.qorvo.com/products/p/DW1000

---

## Part C — Purpose-built repurposers

### Ubertooth One — `ubertooth-one`
Great Scott Gadgets' open 2.4 GHz platform: a **CC2400** transceiver + **LPC1756
ARM Cortex-M3**, **fully open firmware** (`bluetooth_rxtx`) and host tools. Sniffs
BLE, pulls partial data from BT Classic (BR), and — relevant here — runs
**`ubertooth-specan`**, a real **spectrum-analyzer / spectral-scan** across the
2.4 GHz band via CC2400 RSSI sweeps (tier 3). The reference example of a
purpose-built firmware-reversing-adjacent SDR-lite: because the firmware is yours,
the PHY telemetry the CC2400 can produce is fully exposed. HW: Ubertooth One.
Refs:
- https://github.com/greatscottgadgets/ubertooth
- https://ubertooth.readthedocs.io/en/latest/

### Sniffle (nRF52840) — see `nordic-nrf52`
Not separate hardware — an **open firmware** (NCC Group, Sultan Qasim Khan) that
turns a stock **nRF52840 Dongle/DK** into a robust **BLE 5** sniffer with channel
selection, long-range (Coded PHY), and extended-advertising follow. Listed here as
the exemplar of the "open firmware on a documented RADIO" path; profiled under the
Nordic nRF52 record above. Ref: https://github.com/nccgroup/Sniffle

---

## Un-cataloged / TODO (feeds the next cycle)

- **TI WiLink WL12xx / WL127x / WL18xx BT-combo** — the Bluetooth side of the
  combos; any raw-radio access via TI's HCI vendor commands?
- **Marvell 88W8787 / 88W8801 / 88W9098 (Wi-Fi 6)** — newer Avastar; CSI path?
- **NXP IW416 / IW612 / 88W8987** — post-Marvell-acquisition parts; SDIO monitor?
- **Quantenna QSR1000 / "Pearl" QSR5G** — sensing API details, on-chip Linux
  toolchain.
- **Celeno CL800 / CL1500 / CL2000 series** — earlier pre-Doppler parts.
- **Morse Micro MM8108 (Wi-Fi HaLow 2)** and Newracom **NRC7292/NRC7394**,
  Palma Ceia **PCS2200** — the rest of the 802.11ah HaLow field; sub-GHz OFDM
  sensing is wide open.
- **Peraso / former Wilocity W1300, Intel WiGig 11000/18260, Sivers IMA
  60 GHz EVKs** — other 60 GHz beamforming front-ends for mmWave sensing.
- **Nordic nRF54H20 / nRF54L15** — newest RADIO peripheral generation; verify
  radiotest coverage.
- **Silicon Labs Si4432 / Si4463 (EZRadioPRO)** — sub-GHz transceivers, RadioHead
  driver; transparent raw modes.
- **Microchip AT86RF215-IQ specifics** — pin-level IQ capture rigs, FPGA
  bridges, actual measured arbitrary-waveform demos.
- **Semtech LR11xx / SX1302 gateway baseband** — multi-channel LoRa concentrator
  as a wideband capture front-end.
- **Qorvo DW3000 double-buffered CIR & STS**, NXP **SR040/SR150**, Apple **U1/U2**
  — UWB CIR access on locked-down consumer parts.
- **TI CC2400 standalone**, Nordic **nRF905** (sub-GHz), **Si24R1** (nRF24 clone),
  **Analog Devices ADF7xxx** ISM transceivers.


---

## Extended parts — Cycle 3 sweep

Exhaustive pass over the long-tail Wi-Fi/connectivity silicon flagged in the TODO
list above, plus the closed "network-processor" families that are the *anti-SDR*
of this catalog. The recurring lesson of this sweep: **the driver model decides
the tier, not the marketing.** A part with an open mac80211 driver that admits a
`monitor` interface is Tier 1 no matter who made it; a part sealed behind a ROM
"network processor" that only speaks BSD sockets is honestly **Tier 0**, however
capable its radio. Two verified surprises this cycle:

- **Marvell 88W8864 / 88W8964** reach Tier 1 through Kalle Valo/`kaloz`'s
  **open `mwlwifi` AP driver**, which explicitly documents a `mon0` monitor
  interface — a rare *open* Wi-Fi-AP driver.
- **Silicon Labs WF200** looks like it should be Tier 1 (mainline `wfx`
  mac80211 driver) but the driver's `add_interface` **rejects
  `NL80211_IFTYPE_MONITOR`** — only STA/AP/ADHOC — and the firmware is signed and
  closed. Accurate tier: **0**. Accuracy over bravado.

The whole **TI SimpleLink Wi-Fi** line (CC3000 → CC3235) and Microchip's
**WINC/PIC32MZW1/RNWF** families are the same story: the radio lives inside a
closed, ROM-based network processor exposing only a sockets/AT API — Tier 0, no
public monitor/raw path. Nothing to reverse short of glitching the NWP.

### Marvell / NXP Avastar (net-new)

| Part(s) | Standards | Tier | Capability | Firmware | Note |
|---|---|---|---|---|---|
| 88W8686 / 88W8688 (SD8686/8688) | 802.11b/g | 1 | monitor, injection | closed | `libertas`/`libertas_tf` mainline; `rtap` radiotap monitor iface (OLPC XO, Chumby) |
| 88W8782 / 88W8787 / 88W8797 / 88W8801 | 802.11n (+BT combo) | 1 | monitor, injection | closed (ThreadX) | `mwifiex` SDIO/USB/PCIe; siblings of the P0-reversed 88W8897; limited net-mon |
| 88W8864 / 88W8964 | 802.11ac 4×4 | 1 | monitor, injection | closed | **open `mwlwifi` AP driver** w/ documented `mon0`; WRT1900/3200ACM, high-end APs |
| 88W9098 | 802.11ax 2×2 | 1 | monitor, injection | closed | NXP `moal/mlan` driver; i.MX8 boards; no public CSI path |
| IW416 | 802.11n 1×1 + BT5.2 | 1 | monitor, injection | closed | NXP post-acquisition combo; `moal` net-mon; firmware in `linux-firmware/nxp` |
| IW611 / IW612 | 802.11ax 1×1 + BT5 + 802.15.4 | 1 | monitor, injection | closed | **IW612 is a single-chip tri-radio** (Wi-Fi6/BLE/Thread-Zigbee) — 3 PHYs, one part |

### TI (net-new)

| Part(s) | Standards | Tier | Capability | Firmware | Note |
|---|---|---|---|---|---|
| CC3000 / CC3100 / CC3200 / CC3220 / CC3230 / CC3235 | 802.11b/g/n (a/b/g/n dual-band on CC3235) | 0 | — | closed | SimpleLink Wi-Fi = ROM "network processor," sockets/TLS API only; the anti-SDR |
| WL1271 / WL1273 / WL128x (WiLink 6/7) | 802.11b/g/n | 1 | monitor, injection | closed blob | open `wl12xx` mac80211 driver; older sibling of the catalogued `ti-wl18xx` |

### Nordic, Silabs, Microchip (net-new)

| Part(s) | Standards | Tier | Capability | Firmware | Note |
|---|---|---|---|---|---|
| nRF54L15 / nRF54H20 (+L05/L10) | BLE, 802.15.4, proprietary 2.4 | 1 | monitor, injection | documented | new "global RADIO" generation; `radio_test` + register-documented PHY (nRF52 record covers 52805/810/811/820/833/840 + nRF5340) |
| Silabs WF200 / WFM200 | 802.11b/g/n | **0** | — | closed (signed) | mainline `wfx` mac80211 driver but **monitor iftype rejected**; no raw path |
| Silabs RS9116 (RS9113) | 802.11n + BT5 + 802.15.4 | 1 | monitor, injection | closed | Redpine→Silabs; open `rsi` mac80211 driver with sniffer/monitor mode |
| Silabs SiWx917 (SiWG917) | 802.11ax + BLE | 0–1 | — | closed (NWP) | Wi-Fi 6 SoC = M4 + closed network processor; WiSeConnect socket API |
| Silabs EFR32 Series 2 (xG21/22/23/24/25/27/28) | BLE/Zigbee/Thread/Matter, prop. sub-GHz+2.4 | 1 | monitor, injection, arbitrary-waveform | partially-documented | RAIL arbitrary-PHY builder; extends catalogued Series-1 `silabs-efr32` |
| Microchip ATWILC1000 / ATWILC3000 | 802.11b/g/n (+BT4 on 3000) | 1 | monitor, injection | closed | open `wilc1000` mainline mac80211 driver; monitor + injection |
| Microchip WINC1500 / WINC3400 | 802.11b/g/n (+BLE on 3400) | 0 | — | closed | "network controller," WiFi101 sockets API; no monitor/raw |
| Microchip PIC32MZW1 / WFI32E | 802.11n + BLE | 0 | — | closed | MCU + closed Wi-Fi system service (Harmony); no public sniff path |
| Microchip RNWF02 / RNWF11 | 802.11b/g/n (RNWF11 Wi-Fi 6) | 0 | — | closed | AT-command network controller; sealed like WINC |

### Espressif, Quantenna, Celeno, Peraso, Semtech, UWB (net-new)

| Part(s) | Standards | Tier | Capability | Firmware | Note |
|---|---|---|---|---|---|
| ESP32-C61 | 802.11ax (Wi-Fi 6, 20 MHz) + BLE5 | 2 | monitor, injection, csi | closed (RISC-V) | ESP-IDF `esp_wifi` promiscuous + raw 802.11 TX + CSI API, like other ESP32 |
| ESP32-P4 | none (host MCU) | 0 | — | closed (RISC-V) | **no integrated RF**; Wi-Fi/BT only via ESP-Hosted companion (ESP32-C series) |
| Quantenna QSR3610 / QSR3620 | 802.11ac 2×2 | 1 | monitor | closed | on-chip processor; sensing/CSI marketed on QSR10G but no public client tooling |
| Celeno CL1800 | 802.11ac wave 2 | 0–1 | — | closed | pre-Doppler Celeno AP silicon; Doppler engine is on the catalogued CL2x4x/CL6000 |
| Peraso W110x / W120x | 802.11ad (WiGig) 60 GHz | 0 | — | closed | 60 GHz baseband/MAC + RF; **no open RE tooling** (unlike QCA9500 Talon Tools) |
| Semtech SX1280 / SX1281 | 2.4 GHz LoRa / FLRC / (G)FSK | 1 | — | documented | ranging engine (ToF distance telemetry); continuous FSK/OOK for replay/tones |
| NXP Trimension SR040 / SR150 / SR160 | UWB 802.15.4z | 1–2 | — | closed (+M33 on SR150) | UWB anchor/tag; CIR access is vendor-gated (reported); deep UWB → UWB doc |

**Bands/UWB note.** Deep UWB channel-impulse-response work stays in the UWB doc;
the catalogued **Qorvo DW1000/DW3000** remains the one UWB part with a *documented*
complex-CIR readout. NXP Trimension exposes CIR only through gated debug paths
(status *reported*). **u-blox** short-range UWB is sold as *modules* wrapping
third-party (Qorvo-class) silicon rather than u-blox radio IP, so it is not minted
as a separate chip record here.

See [../projects/nexmon.md](../projects/nexmon.md) for the firmware-surgery half of
the ladder and [../docs/mmwave-60ghz-radar.md](../docs/mmwave-60ghz-radar.md) for
why Peraso 60 GHz stays Tier 0 without a `nexmon-arc` equivalent.


---

## Long-tail sweep — Cycle 4

This round pushes past the Wi-Fi/BLE core into the **genuine-radar** and **UWB** adjacencies, plus a
handful of Wi-Fi/BT parts that earlier cycles missed. The honest framing matters here:

- **Automotive/industrial mmWave radar** (TI AWR/IWR, NXP TEF810x + S32R, NXP SAF85xx, Infineon BGT,
  Uhnder, Arbe) are *actual raw-IQ radars*. You get the ADC cube off the chip through a documented
  capture path — no firmware jailbreak required. These sit high on the ladder **for radar/FMCW work
  specifically** (Tier 4), but they are *not* general-purpose SDRs: the TX is a chirp/code generator,
  not an arbitrary baseband DAC, and the RF is a fixed 24/60/77/79/120 GHz front-end. See
  [`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md) for where "raw-IQ radar" lands
  versus a HackRF/USRP.
- **UWB** (NXP Trimension SR040/SR150/SR160, 3db Access) behaves like the already-catalogued Qorvo
  `dw1000`: the useful export is the **channel-impulse-response (CIR)**, a per-tap channel snapshot
  analogous to Wi-Fi CSI (Tier 2 where the CIR is reachable, Tier 1 for ranging-only, closed silicon).
  Qorvo remains the more open path; NXP's UWB firmware is signed/closed. **Zebra** (DART/UWB RTLS) and
  **Sewio** are *system integrators*, not silicon vendors — Sewio's anchors are built on Qorvo DW1000/
  DW3000, so they carry no net-new chip record here.
- **Missed Wi-Fi/BT** parts are mostly closed vendor blobs (Airoha, SigmaStar, Amlogic, On-Semi/
  Quantenna, Methods2Business) — Tier 0–1 — with two bright spots: **Espressif ESP32-C5/-C61**, which
  inherit the open ESP-IDF CSI path (Tier 2), the C5 notably offering **5 GHz CSI**. Note **ESP32-P4
  has no radio at all** (verified against Espressif's SoC page) and is therefore excluded as a module.

Cross-references: FMCW/radar theory in [`../docs/techniques.md`](../docs/techniques.md); UWB ranging in
[`../docs/uwb-fira-ranging.md`](../docs/uwb-fira-ranging.md) and
[`../docs/ftm-rtt-ranging.md`](../docs/ftm-rtt-ranging.md); the already-catalogued anchors
`ti-iwr6843`, `infineon-bgt60tr13c`, `qorvo-dw1000`, `quantenna-qsr10g`, `celeno-cl6000`,
`morsemicro-mm6108/mm8108`, `newracom-nrc7292/nrc7394` are not repeated below.

### Compact summary

| Module | Band | Class | Tier | Key capability | FW openness | Status |
|---|---|---|---|---|---|---|
| ti-awr1243 | 60/76–81 GHz | FMCW transceiver (cascade) | 4 | raw ADC via DCA1000/LVDS | closed | verified |
| ti-awr1443 | 76–81 GHz | Single-chip FMCW radar | 4 | raw ADC (mmWave Studio) | closed | verified |
| ti-awr1642 | 76–81 GHz | FMCW radar + C674x DSP | 4 | raw-IQ + on-chip DSP | closed | verified |
| ti-awr1843 | 76–81 GHz | FMCW radar + DSP + HWA | 4 | raw-IQ radar cube | closed | verified |
| ti-awr2243 | 76–81 GHz | 2G cascade transceiver | 4 | imaging-radar raw ADC | closed | verified |
| ti-awr2944 | 76–81 GHz | 2G single-chip radar | 4 | raw-IQ, 4TX/4RX MIMO | closed | verified |
| nxp-tef810x | 76–81 GHz | RFCMOS radar transceiver | 4 | raw ADC to S32R MCU | closed | reported |
| nxp-s32r274 | n/a (RF-less) | Radar signal processor | 0 | SPT/FFT, no RF of its own | partially-documented | reported |
| nxp-saf85xx | 76–81 GHz | Single-chip radar SoC | 4 | on-chip radar cube + raw ADC | closed | reported |
| infineon-bgt24ltr11 | 24 GHz | CW/Doppler front-end | 3 | analog I/Q IF (ext. ADC) | documented | verified |
| infineon-bgt60atr24c | 60 GHz | Automotive FMCW radar | 4 | raw ADC (Radar SDK) | documented | reported |
| infineon-bgt120 | 120 GHz | FMCW transceiver | 4 | raw-IQ radar | closed | reported |
| uhnder-s80 | 76–81 GHz | Digital-code (PMCW) radar | 4 | digital-modulation radar cube | closed | reported |
| arbe-phoenix | 76–81 GHz | Imaging FMCW radar chipset | 4 | 2304-ch raw radar | closed | reported |
| nxp-sr150 | 6–9 GHz UWB | FiRa UWB + Cortex-M33 | 2 | CIR / AoA readout | closed | reported |
| nxp-sr040 | 6–9 GHz UWB | FiRa UWB controlee tag | 1 | ranging, signed FW | closed | reported |
| nxp-sr160 | 6–9 GHz UWB | Mid-range UWB IC | 1 | ranging (+CIR debug) | closed | reported |
| 3dbaccess-3db6830 | 6–9 GHz UWB | Low-power 15.4z UWB | 1 | ranging (CIR reported) | closed | reported |
| airoha-ab1565 | 2.4 GHz | BT 5.x TWS audio SoC | 0 | black-box BT | closed | reported |
| sigmastar-ssw101b | 2.4 GHz | 802.11n IoT combo | 1 | monitor (limited) | closed | reported |
| allwinner-xr829 | 2.4 GHz | 11n + BT combo (xradio) | 1 | monitor (poor) | partially-documented | reported |
| amlogic-w2 | 2.4/5 GHz | Wi-Fi 6 combo | 1 | vendor-driver monitor | closed | reported |
| quantenna-qsr1000 | 2.4/5 GHz | 802.11ac 4×4 | 1 | monitor/injection | closed | reported |
| m2b-halow | sub-GHz | 802.11ah HaLow IP/SoC | 1 | 11ah PHY (licensed IP) | closed | theoretical |
| espressif-esp32-c5 | 2.4/5 GHz | Wi-Fi 6 + BLE + 15.4 | 2 | **5 GHz CSI**, monitor | partially-documented | verified |
| espressif-esp32-c61 | 2.4 GHz | Wi-Fi 6 + BLE | 2 | CSI, monitor | partially-documented | verified |

### Automotive & industrial mmWave radar (raw-IQ, not general SDR)

The **TI AWR** line is the most accessible: `MMWAVE-STUDIO`/`mmWave Studio` drives the device over SPI,
streams **raw ADC samples over LVDS to the `DCA1000EVM`** capture card (UDP-to-PC), and the community
tooling ([OpenRadar](https://github.com/PreSenseRadar/OpenRadar), [pymmw](https://github.com/m6c7l/pymmw))
parses the resulting radar cube in Python. AWR1443 folds a Cortex-R4F + hardware accelerator on-die;
AWR1642/1843 add a **C674x DSP** for on-chip range/Doppler FFTs; AWR1243/AWR2243 are TX/RX-only
**transceivers** meant for cascade imaging (`MMWCAS-RF-EVM`, 4-chip 12TX×16RX). The **2G** family
(AWR2944, AWR2544) is the current automotive generation with `MMWAVE-STUDIO-2G`. All expose the ADC
cube through a documented path — you never touch a firmware jailbreak — but the TX is a programmable
**FMCW chirp** generator, not an arbitrary IQ DAC, so this is Tier 4 *for radar/FMCW only*. `IWR`
variants are the industrial-temp siblings (the already-catalogued `ti-iwr6843` is the 60 GHz one).

**NXP** splits the chain: **TEF810x** is the 77 GHz RFCMOS transceiver (3TX/4RX) that hands raw ADC to
an **S32R274/S32R294** radar MCU (PowerPC e200 + the **SPT** "Signal Processing Toolbox" for FFT/CFAR).
The S32R part is *RF-less* — a processor, not a radio — so it is recorded only for completeness at
Tier 0. **SAF85xx** (SAF8544/SAF8510) is the newer **single-chip** RFCMOS radar SoC that integrates
transceiver + processing and can emit either a processed point cloud or raw ADC. Access is gated behind
NDA'd tooling, hence `reported`.

**Infineon** spans the widest frequency range. **BGT24LTR11** is a low-cost 24 GHz Doppler/CW
front-end that outputs **analog I/Q IF** you digitize with any external ADC (Tier 3, well-documented in
app notes — a hobbyist favorite). The 60 GHz **BGT60ATR24C** (automotive) and the already-catalogued
**BGT60TR13C** (consumer, XENSIV) stream raw ADC through the **Radar Development Kit** / `ifxradarsdk`
Python/C SDK. **BGT120** pushes to 120 GHz for short-range industrial sensing. The 60/120 GHz FMCW
parts are Tier 4; the 24 GHz CW part is Tier 3 (simpler modulation, external ADC).

**Uhnder S80** is the outlier modulation: a 79 GHz **digital-code-modulation (PMCW/DCM)** "radar-on-chip"
in 28 nm RFCMOS with up to ~192 virtual channels and on-chip correlation — closer to a spread-spectrum
digital transmitter than an FMCW ramp, which is why it earns an `arbitrary-waveform`-adjacent flag.
Uhnder wound down operations in 2024, so its tooling is effectively orphaned (`reported`). **Arbe
Phoenix** is a two-chip imaging set (RFIC + radar processor) fielding **48TX × 48RX ≈ 2304 virtual
channels** of 79 GHz FMCW for high-resolution 4D point clouds; raw access is OEM-only.

### Ultra-wideband (CIR ≈ CSI, mostly closed)

NXP's **Trimension** UWB family implements IEEE 802.15.4z HRP / FiRa. **SR150** integrates an Arm
**Cortex-M33** and 3-antenna AoA, and can surface the **channel impulse response** for research-grade
sensing (Tier 2 where reachable). **SR040** is a controlee/tag optimized for low power (ranging-only,
Tier 1); **SR160** is a mid-range single-chip device. All run **signed/closed** firmware — unlike Qorvo,
there is no Nexmon-style patch path — so the more open UWB route remains `qorvo-dw1000`/DW3000 (see
[`../docs/uwb-fira-ranging.md`](../docs/uwb-fira-ranging.md)). **3db Access 3DB6830** is a low-power
15.4z ranging IC in the same closed camp. **Zebra** (DART UWB RTLS) and **Sewio** are location-system
vendors rather than chip makers — Sewio's hardware is built on Qorvo DecaWave silicon — so neither adds
a net-new chip record.

### Missed Wi-Fi / BT (closed long-tail, plus two open ESP32s)

- **Airoha AB1562/AB1565** are Bluetooth 5.x dual-mode **TWS earbud audio** SoCs (not Wi-Fi), closed
  firmware, no public off-the-ground path → Tier 0.
- **SigmaStar SSW101B** — 2.4 GHz 802.11n IoT combo paired with SigmaStar camera SoCs; closed vendor
  driver, limited monitor → Tier 1.
- **Allwinner XR829** — 2.4 GHz 11n + BT combo (the `xradio`/`xr819` lineage, common on Allwinner SBCs).
  A partially-documented staging-style driver exists but monitor/injection support is poor → Tier 1.
- **Amlogic W1/W2** — Amlogic's own Wi-Fi silicon (W1 = 11n 1×1, **W2** = Wi-Fi 6 dual-band) for
  set-top/AIoT SoCs; closed firmware, vendor-driver monitor only → Tier 1.
- **On-Semi / Quantenna QSR1000** — 802.11ac 4×4 (the pre-`qsr10g` "Topaz/Rurik" generation). Closed,
  with some GPL driver fragments in OpenWrt trees; CSI work exists on the newer `qsr10g` but not here →
  Tier 1.
- **Methods2Business HaLow** — a Dutch design house's 802.11ah **HaLow IP/SoC** (acquired by Renesas,
  2021). Sub-GHz 11ah PHY, licensed IP with no public reversing path → Tier 1, `theoretical`.
- **Espressif ESP32-C5 / -C61** — the open ESP-IDF CSI/monitor path applies (Tier 2). The **C5 is
  dual-band Wi-Fi 6**, giving a rare cheap route to **5 GHz CSI**; C61 is single-band 2.4 GHz Wi-Fi 6.
  PHY is a blob but the driver/API is documented. **ESP32-P4 has no radio and is excluded.**

**Regulatory/TX note:** every radar part above transmits in licensed/ISM mmWave bands (24/60/77/79/120
GHz) under regional EIRP and duty-cycle limits (e.g., FCC Part 15.253/15.256, ETSI EN 305 550 / EN 302
264 for automotive 76–81 GHz). Automotive 76–81 GHz emission is generally restricted to vehicular use;
bench operation should use shielded enclosures or absorptive fixtures. UWB TX is governed by FCC Part 15
Subpart F / ETSI EN 302 065. Never radiate a modified FMCW/UWB waveform on-air outside a chamber without
confirming your license class.


---

## Emerging & regional vendors — Cycle 5

This sweep catalogs the second- and third-tier silicon that has flooded the low-cost IoT, smart-home, and mobile-combo market in the last five years: Chinese fabless WiFi/BLE houses (Beken, ASR, Unisoc/RDA, Bestechnic, Bluetrum, PHY+, Onmicro, Chipsea), a captive giant (HiSilicon), the module integrators that repackage everyone's dies (AMPAK, USI, Fn-Link), and the newest closed mobile flagships (Qualcomm FastConnect 7900). The honest headline: **almost all of it is Tier 0–1.** None of these vendors ship a documented PHY, and none has an out-of-tree SDR toolchain in the class of nexmon or openwifi. What *does* exist — and what makes a handful of these genuinely interesting — is the **open-firmware-framework layer** that the smart-home hacking community built on top of them.

### The one thing that matters here: LibreTiny + OpenBeken

The reason the Beken/Realtek-Ameba/LN882H cluster punches above its weight is [**LibreTiny**](https://github.com/libretiny-eu/libretiny) and [**OpenBeken (OpenBK7231T_App)**](https://github.com/openshwprojects/OpenBK7231T_App). LibreTiny is a PlatformIO development platform that replaces the vendor SDKs with an open build system + Arduino core across **Beken BK7231N/BK7231T/BK7238/BK7252, Realtek RTL8710B (AmebaZ), RTL8720C (AmebaZ2), and LN882H** — the exact dies Tuya solders onto its `CB`-series and `WB`-series modules. That means for these chips you get **buildable, patchable application + RTOS firmware** even though the WiFi MAC/PHY remains a vendor blob. The community also documented the flash layout and RE workflow ([`bk7231tools`](https://github.com/openshwprojects/bk7231tools)), which is what lifts Beken from "black box" to a real **Tier 1** monitor/injection target.

### Compact table

| Chip | Vendor | Radio | Core | Tier | Firmware | Note |
|---|---|---|---|---|---|---|
| BK7231N / BK7231T | Beken | 2.4G 11n + BLE | ARM968E-S (ARM9) | 1 | partially-documented | The Tuya smart-plug chip; monitor+raw-TX via SDK, open via LibreTiny/OpenBeken |
| BK7251 | Beken | 2.4G 11n + BLE + audio | ARM968E-S | 1 | partially-documented | BK7231 + audio codec |
| BK7238 | Beken | 2.4G 11n | ARM (new gen) | 1 | partially-documented | Newer Tuya `CBU`/`CB3S` die, LibreTiny-supported |
| Hi1103 / Hi1105 | HiSilicon | 2.4/5G 11ax + BT5 | closed | 0 | closed | Huawei/Honor Wi-Fi 6 mobile & router combo |
| Hi1151 | HiSilicon | 2.4/5/6G 11ax(+be?) | closed | 0 | closed | Reported Wi-Fi 6E/7 combo; sparse public data |
| UWE5621/5622 | Unisoc (Spreadtrum) | 2.4(/5)G 11n/ac + BT | closed | 1 | closed | Cheap Android tablet/IoT combo; GPL kernel driver, blob FW |
| BES2600 | Bestechnic | 2.4/5G 11ac + BT + audio | dual Cortex-M | 1 | closed | Smart-speaker/TWS SoC; RT-Thread BSP, blob FW |
| ASR5822 / ASR5505 | ASR Micro | 2.4G 11n + BLE | Cortex-M4F | 1 | partially-documented | Tuya `WB`-series alt-die; vendor SDK |
| ATS362x / ATS28xx | Actions | 2.4G BT audio | ARM / RISC-V | 0 | partially-documented | BT-audio SoC; Zephyr supports the MCU, radio closed |
| RTL8710B (AmebaZ) | Realtek | 2.4G 11n | Cortex-M4 (KM0/KM4) | 1 | documented | Open SDK + LibreTiny; promisc monitor |
| RTL8720C (AmebaZ2) | Realtek | 2.4G 11n | Cortex-M4F | 1 | documented | AmebaZ2; LibreTiny; sibling of already-listed RTL8720DN |
| AB53xx | Bluetrum | 2.4G BT audio | proprietary RISC-V | 0 | closed | BT-audio; closed RISC-V ISA |
| PHY6222 | PHY+ (PhyPlus) | 2.4G BLE 5 | Cortex-M0 96MHz | 1 | documented | Cheap BLE beacon SoC; semi-open SDK |
| OM6621 | Onmicro | 2.4G BLE 5 | Cortex-M0 | 0 | closed | Ultra-low-cost BLE |
| CST92F4x | Chipsea | 2.4G BLE 5 | Cortex-M0 | 0 | closed | BLE from an ADC/MCU house |
| RDA5981 | RDA (→Unisoc) | 2.4G 11n | Cortex-M4 | 1 | documented | Arm Mbed OS port; audio/IoT WiFi |
| AP6xxx / USI / Fn-Link | AMPAK/USI/Fn-Link | (host die) | — | — | (host die) | **Integrators** — carry Broadcom/Cypress/Qualcomm/Realtek dies |
| RK-Realtek combo | Rockchip pairing | 2.4/5G | — | — | (host die) | Rockchip SoCs pair external RTL/AP6xxx modules, not own WiFi silicon |
| FastConnect 7900 | Qualcomm | 2.4/5/6G 11be + BT5.4 + UWB | closed | 0 | closed | First combo to fuse Wi-Fi 7 + BT + UWB; Snapdragon flagships |

---

### Beken BK72xx — the Tuya smart-home workhorse

The single most-deployed chip in this whole sweep. Beken's `BK7231T`/`BK7231N` (an **ARM968E-S / ARMv5TE ARM9** core with 2.4 GHz 802.11 b/g/n and, on the `N`/`U`, BLE) is what sits inside the overwhelming majority of ~$3 Tuya WiFi smart plugs, bulbs, and switches sold as the `CB2S`, `CB3S`, `CBU`, `WB2S`, `WB3S` modules. `BK7251` adds an audio codec; `BK7252` is the WiFi+audio part; `BK7238` is the newer-generation 11n die (`CB3SE`/`CBU` refreshes).

**Why it's Tier 1, not Tier 0:** the vendor SDK lineage — Tuya's [`tuya-iotos-embeded-sdk-wifi-ble-bk7231t`](https://github.com/tuya/tuya-iotos-embeded-sdk-wifi-ble-bk7231t) and Beken's newer open [`Armino`](https://github.com/bekencorp/armino) SDK — expose **promiscuous/monitor** APIs (`bk_wlan_start_monitor()` + a registered RX callback delivering raw 802.11 frames, `bk_wlan_set_channel()`), plus a **raw-frame transmit** primitive used to ACK SmartConfig/AirKiss provisioning. Monitor RX of arbitrary 802.11 frames is verified through the open re-implementations; raw injection is reported (SDK-exposed, less independently exercised). No CSI, spectral, or IQ path is documented — the PHY is a blob. Firmware is therefore **partially-documented**: application + RTOS are fully open/buildable via LibreTiny and OpenBeken, RF firmware is a closed library.

**RE workflow:** load a dump into Ghidra as **ARMv5TE (ARM968E-S)** little-endian; use [`bk7231tools`](https://github.com/openshwprojects/bk7231tools) to unpack the `RBL`/`OTA` container and locate the app partition; recover symbol boundaries from the SDK's public headers (the WiFi API surface is documented even where the implementation is a blob). Do **not** invent addresses — resolve `bk_wlan_*` entry points by cross-referencing the SDK header names against string/xref matches in your own image. See the sibling walkthrough conventions in [`docs/walkthroughs/ghidra-setup-wifi-firmware.md`](../docs/walkthroughs/ghidra-setup-wifi-firmware.md).

**TX caution:** the raw-frame API transmits real 2.4 GHz energy. Only exercise injection into a shielded enclosure or on a licensed/ISM-legal basis; see [`docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md).

### HiSilicon Hi110x — Huawei's captive Wi-Fi 6/7 combos

`Hi1103` (announced 2019) was Huawei's first Wi-Fi 6 + BT 5.1 combo, shipping in Kirin-era P40/Mate 30/Honor phones and Huawei AX3-class routers; `Hi1105` is the router-oriented sibling; `Hi1151` is a reported later Wi-Fi 6E/7 part with little public documentation. These are **fully captive** — no public SDK, no datasheet, no RE tooling, no monitor path. Firmware is closed and signed. **Tier 0**, `status: reported` (Hi1103/Hi1105) / `theoretical` (Hi1151). Listed for completeness; there is no known SDR handle. Cross-ref [`chips/qualcomm-atheros.md`](qualcomm-atheros.md) only for lineage contrast — HiSilicon shares none of the ath9k/ath10k openness.

### Unisoc / Spreadtrum UWE56xx & RDA5981

`UWE5621` (2.4 GHz 11n + BT) and `UWE5622` (adds 5 GHz 11ac) are Unisoc's low-cost combos for budget Android tablets, TV dongles, and IoT. A GPL Linux/Android kernel driver (`sprdwl_ng`, in AOSP vendor kernels — not mainline) provides `cfg80211` monitor mode, but the on-chip firmware is a closed downloadable blob, so the SDR ceiling is standard `nl80211` monitor. **Tier 1**, `closed` firmware. `RDA5981` (RDA Micro, absorbed into Unisoc) is a Cortex-M4 2.4 GHz 11n WiFi SoC notable for an **Arm Mbed OS port** — genuinely documented at the RTOS/driver layer, still a blob PHY. **Tier 1**, `documented`.

### Bestechnic BES2600

Dual-Cortex-M SoC combining 2.4/5 GHz 802.11ac WiFi, Bluetooth, and an audio DSP — the brains of many Xiaomi/AI smart speakers and some TWS docks. RT-Thread ships a board-support package for it ([`bsp/bestechnic/BES2600`](https://github.com/RT-Thread/rt-thread)), and a `bes2600` cfg80211 driver was floated on linux-wireless, but it is **not in current mainline staging** (verified against `drivers/staging` on `torvalds/linux`). WiFi firmware is a closed blob. **Tier 1** (monitor via the vendor/driver stack), `closed`.

### ASR Microelectronics ASR582x / ASR550x

ASR's `ASR5822`/`ASR5822S` (Cortex-M4F, 2.4 GHz 11n + BLE) and `ASR5505` are a second-source die for Tuya `WB`-series modules and other white-label IoT. A vendor SDK (`ASR-SDK`/`lega` RTOS) exists with the usual SmartConfig promiscuous path, so treat it like Beken minus the mature open-framework support: **Tier 1**, `partially-documented`. LibreTiny does not (yet) target ASR, so RE is more DIY.

### Realtek Ameba — AmebaZ (RTL8710B) & AmebaZ2 (RTL8720C)

Realtek's Ameba IoT line is the Realtek counterpart to Beken in Tuya modules. `RTL8710B` (**AmebaZ**, Cortex-M4) and `RTL8720C` (**AmebaZ2**, Cortex-M4F) are already carried by **LibreTiny** (`generic-rtl8710bn-*`, `generic-rtl8720cf-*`, `generic-rtl8720cm-*` board targets) and by Realtek's own reasonably-open Ameba SDK. Both expose documented **promiscuous/monitor** mode (used for SmartConfig). Their bigger sibling **RTL8720DN (AmebaD)** — already catalogued — additionally exposes a documented **CSI API** (`wifi_csi_config`/report) in the AmebaD SDK; the same family lineage makes AmebaZ2 a plausible CSI target, but treat CSI on the `B`/`C` parts as reported, not verified. **Tier 1**, `documented`. See [`chips/realtek.md`](realtek.md) for the broader Realtek picture and [`projects/csi-toolchains.md`](../projects/csi-toolchains.md) for the CSI landscape.

### BLE & BT-audio budget silicon: Bluetrum, PHY+, Onmicro, Chipsea, Actions

A cluster of ultra-low-cost 2.4 GHz single-mode parts. None is a WiFi SDR, but they matter for the 2.4 GHz-covert-channel / BLE-sniffing side of the catalog:

- **PHY+ (PhyPlus) `PHY6222`** — 96 MHz Cortex-M0 BLE 5 SoC with a **semi-open SDK** (community mirrors, e.g. [`SoCXin/PHY6222`](https://github.com/SoCXin/PHY6222)); the openness makes it the most hackable BLE part here. **Tier 1**, `documented`.
- **Onmicro `OM6621`** and **Chipsea `CST92F4x`** — commodity Cortex-M0 BLE from an RF house and an ADC/MCU house respectively; closed SDKs. **Tier 0**.
- **Bluetrum `AB53xx`** — BT-audio SoC built on a **proprietary RISC-V core** (closed ISA extensions), which blocks conventional RE tooling. **Tier 0**, `closed`.
- **Actions `ATS362x`/`ATS28xx`/`ATS30xx`** — BT-audio SoCs; **Zephyr mainline supports the Actions Semi MCU/SoC family**, so the application core is open-ish, but the Bluetooth radio firmware is closed. **Tier 0**, `partially-documented` (MCU only).

Cross-ref [`chips/ble-154-thread.md`](ble-154-thread.md) for the BLE/802.15.4 SDR angle.

### Module integrators — AMPAK, USI, Fn-Link (and Rockchip pairings)

**These are not silicon vendors** — they are packaging houses whose part numbers hide someone else's die, a frequent source of catalog confusion:

- **AMPAK** `AP6xxx` (`AP6212`, `AP6255`, `AP6398S`, `AP6275S`) → almost always **Broadcom/Cypress** dies (CYW/BCM43xxx). These are the Tier-3/Tier-4 nexmon targets in disguise — cross-ref [`chips/broadcom-cypress.md`](broadcom-cypress.md) and [`projects/nexmon.md`](../projects/nexmon.md).
- **USI (Universal Scientific Industrial)** → Broadcom, Qualcomm/Atheros, or Realtek dies depending on the SKU.
- **Fn-Link** → predominantly Realtek and Broadcom dies.
- **Rockchip** SoCs (RK33xx/RK35xx) ship **no first-party WiFi silicon**; their "RTL-combo" boards pair an external **Realtek** (`RTL8723DS`, `RTL8821CS`, `RTL8188FU`) or AMPAK/Broadcom module. The SDR capability is entirely that of the mounted die.

**Rule:** always resolve an integrator part number to its underlying die before assigning a tier — the module label carries no independent SDR capability. See [`chips/hardware-index.md`](hardware-index.md).

### Qualcomm FastConnect 7900

The newest closed flagship: FastConnect 7900 (2024) is notable as the **first mobile connectivity system to integrate Wi-Fi 7 (802.11be), Bluetooth 5.4, and Ultra-Wideband (UWB) on a single die**, across 2.4/5/6 GHz plus UWB, paired with Snapdragon 8-Elite-class SoCs. Like all FastConnect combos it is entirely closed — signed firmware, no public SDK, no monitor path. **Tier 0**, `reported`. Cross-ref [`chips/qualcomm-atheros.md`](qualcomm-atheros.md); note the FastConnect line shares none of the historical ath10k/ath11k openness.

### Bottom line for this cohort

Reach for **Beken BK72xx or Realtek Ameba (Z/Z2/D)** if you want a hackable, buildable-firmware 2.4 GHz target on a $3 budget — LibreTiny + OpenBeken make them the only genuinely open-framework parts in the sweep, and AmebaD even gives you CSI. Everything mobile-flagship (HiSilicon Hi110x, FastConnect 7900) is a closed Tier-0 dead end for SDR purposes. And never let an **AMPAK/USI/Fn-Link/Rockchip** label fool you — chase the die underneath.

#### References

- LibreTiny (open PlatformIO platform; BK72xx / RTL8710B / RTL8720C / LN882H): https://github.com/libretiny-eu/libretiny
- OpenBeken (OpenBK7231T_App): https://github.com/openshwprojects/OpenBK7231T_App
- bk7231tools (flash/RE tooling): https://github.com/openshwprojects/bk7231tools
- Beken Armino open SDK: https://github.com/bekencorp/armino
- Tuya IoTOS BK7231 SDK: https://github.com/tuya/tuya-iotos-embeded-sdk-wifi-ble-bk7231t
- PHY6222 community SDK: https://github.com/SoCXin/PHY6222
- RT-Thread (BES2600 BSP): https://github.com/RT-Thread/rt-thread
- Qualcomm FastConnect 7900: https://www.qualcomm.com/products/technology/wi-fi/fastconnect-7900
- Zephyr Actions Semi support: https://docs.zephyrproject.org/


---

## Long-tail sweep — Cycle 6 (satellite/IoT & stragglers, round 4)

This round sweeps up the *other* radios that ship inside modern devices — satellite‑IoT modems, standalone GNSS RF front‑ends, 24/77 GHz automotive radar front‑ends, 5.8 GHz analog‑FPV video transmitters — plus a few Wi‑Fi parts missed earlier. The discipline of this catalog applies with extra force here: **most of these are fixed‑function modems or type‑approved network endpoints, not repurposable IQ radios.** Where the honest answer is Tier 0, it is stated as Tier 0. The genuinely interesting exceptions are the GNSS and radar *front‑ends*, which were SDR components to begin with, and the analog‑FM FPV transmitters, which will happily modulate arbitrary baseband onto a programmable ~5.8 GHz carrier.

> Already catalogued elsewhere — not repeated here: `semtech-sx127x`, `qorvo-dw1000`, `morsemicro-mm6108`.

### Legal preface (read before keying any of these)
Satellite uplink bands — VHF 148–150 MHz (Swarm/Myriota), L‑band 1616–1626.5 MHz (Iridium), L/S‑band NTN — are licensed to the operators, not to you. These modems are *type‑approved endpoints* for a specific constellation; transmitting on those bands with anything else is unlawful in essentially every jurisdiction, and the constellations actively geolocate rogue emitters. GNSS L1/L2/L5 and the 24 GHz / 76–81 GHz radar bands are equally protected. Treat everything in this section as **receive‑only / captive‑network** unless you are inside a shielded enclosure. See [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md) and [../docs/regulatory-by-region.md](../docs/regulatory-by-region.md).

### Summary table

| Chip / module | Vendor | Class | Band(s) | Honest tier | What you actually get |
|---|---|---|---|---|---|
| LR1120 | Semtech | LoRa/(G)FSK + S‑band sat modem | sub‑GHz, 2.4 GHz, S‑band ~2 GHz | 1 | Programmable LoRa/LR‑FHSS/(G)FSK + CW; register‑documented, but a fixed modem, not IQ |
| M138 | Swarm (SpaceX) | VHF satellite‑IoT modem | VHF 137/148 MHz | 0 | AT commands over UART; closed modem, no RF access |
| Astronode S | Astrocast | L‑band satellite‑IoT modem | L‑band | 0 | AT/SPI command API; closed |
| 9602 / 9603 | Iridium | L‑band SBD transceiver | L‑band 1616–1626.5 MHz | 0 | AT (SBD) commands; closed. Downlink is RX‑able only with an *external* SDR (`gr-iridium`) |
| 9770 | Iridium | Certus core transceiver | L‑band | 0 | Vendor API; closed |
| (module) | Myriota | VHF store‑&‑forward sat‑IoT | VHF ~160 MHz | 0 | SDK/AT; closed |
| MAX2771 | Analog Devices | Multi‑band GNSS RF front‑end | GNSS L1/L2/L5 (~1.15–1.61 GHz) | 5 (RX only) | Genuine raw‑IQ/IF SDR front‑end, fully register‑documented; drives GNSS‑SDR |
| SE4150L | Skyworks (ex‑SiGe) | GPS L1 RF front‑end | L1 1575 MHz | 4 (RX only) | 2‑bit sign/mag raw IF samples — the classic textbook GNSS‑SDR front‑end |
| BGT24MTR11 | Infineon | 24 GHz radar transceiver | 24 GHz ISM | 5 (radar) | Real analog radar front‑end: raw IQ IF out, arbitrary chirp via external VCO |
| TEF810X | NXP | 76–81 GHz automotive radar Tx/Rx | mmWave 76–81 GHz | 3 | Raw ADC/IF, but NDA docs and needs S32R radar MCU |
| RTC6705 | Richwave | 5.8 GHz analog‑FM video Tx | 5.8 GHz (5645–5945 MHz) | 3 | SPI‑programmable carrier + **arbitrary analog baseband** FM‑modulated — abusable covert channel |
| DA16200 | Renesas (Dialog) | Ultra‑low‑power Wi‑Fi 4 SoC | 2.4 GHz | 1 | 802.11b/g/n, closed PHY; SDK exposes promiscuous RX at best |

---

### Satellite‑IoT modems — the honest floor is Tier 0

Swarm **M138**, Astrocast **Astronode S**, Iridium **9602/9603/9770**, and **Myriota** are all the same story from an SDR standpoint: a closed MCU running proprietary firmware behind a UART/SPI AT‑style command interface, RF‑type‑approved for exactly one constellation. There is no register path to raw IQ, no documented PHY, and the network side is authenticated. You cannot turn one into a general transmitter, and you should not try (see legal preface). They are Tier 0 and belong next to the [cellular basebands](./cellular-basebands.md) in spirit — closed radios you talk to, not radios you drive.

The one repurposing that *is* real happens on the receive side and needs a **separate** SDR: the Iridium L‑band downlink (1616–1626.5 MHz, DE‑QPSK bursts) is decodable with **[`gr-iridium`](https://github.com/muccc/gr-iridium)** + `iridium-toolkit` feeding from an RTL‑SDR/HackRF/USRP. That demonstrates the *waveform* is open to analysis, but the **9603 chip itself contributes nothing** — you are not repurposing the modem, you are listening to the constellation with real hardware. Catalogued honestly as Tier 0 for the chip, with a pointer to the RX toolchain in [../projects/gnuradio-oot-modules.md](../projects/gnuradio-oot-modules.md).

**Skylo** is *not a chip* — it is an NB‑IoT NTN (3GPP Rel‑17 non‑terrestrial) service that rides on standard cellular basebands with NTN firmware (e.g. NTN‑capable Qualcomm/Sony/MediaTek modems). Its repurposability is exactly that of the underlying baseband: see [./cellular-basebands.md](./cellular-basebands.md). No net‑new module.

**Semtech LR1120** is the interesting straggler in this group. It is a multi‑band LoRa transceiver covering sub‑GHz (150–960 MHz), the 2.4 GHz ISM band, **and an S‑band (~1.9–2.1 GHz) segment used for direct‑to‑satellite** links with LEO IoT operators. Modulations: LoRa, LR‑FHSS, (G)FSK, plus raw CW. That makes it more flexible than the pure sat modems — you have register‑level control of frequency, deviation, and packet framing across three widely separated bands — but it is still a **fixed modem, not an IQ transceiver**. No CSI, no raw‑IQ tap, no spectral scan. Tier 1: you can emit arbitrary FSK/OOK/CW patterns (a covert‑channel primitive) within its bands, and sniff LoRa/FSK traffic, and nothing more. It is a close cousin of the already‑catalogued `semtech-sx127x` lineage with S‑band bolted on.

### GNSS RF front‑ends — these were SDR components all along

**MAX2771** (Analog Devices/Maxim) is a broadband, multi‑constellation GNSS front‑end: two RF paths covering the lower L‑band (~1155–1305 MHz: L2/L5/E5/E6/B2) and upper L‑band (~1550–1610 MHz: L1/E1/B1/G1), programmable IF and bandwidth, and an on‑chip 2‑bit (up to ~3‑bit) ADC delivering **raw digitized IF/IQ samples** over CMOS/LVDS. That is the textbook definition of an SDR receive front‑end, and it is exactly how the open **[GNSS‑SDR](https://gnss-sdr.org/)** project and many open‑hardware GNSS boards use it. It is fully register‑documented. Tier **5, receive‑only** — a genuine, documented SDR front‑end. The only caveat versus the catalog's usual subjects is that it is *purpose‑built* rather than *repurposed*; it earns Tier 5 on capability, not on cleverness.

**SE4150L** (Skyworks, ex‑SiGe Semiconductor) is the GPS/GNSS **L1** single‑band front‑end that anchored a generation of academic SDR receivers — the SiGe GN3S sampler and the front‑ends bundled with the Borre/Akos *A Software‑Defined GPS and Galileo Receiver* textbook descend from this SE41xx line. It outputs 2‑bit sign/magnitude IF samples. Tier **4, RX‑only**: genuine raw IF, but single‑band and coarse quantization make it less capable than the MAX2771. Both are the honest high‑water mark of this section — and both underline that "GNSS chip → SDR" means *reception of raw observables*, never transmission. (GPS *spoofing* projects like GPS‑SDR‑SIM transmit with a real SDR + these front‑ends only for RX; the front‑end never transmits.)

### Automotive radar stragglers

**Infineon BGT24MTR11** (and the MTR12 2‑RX / LTR11 Doppler variants) is a **24 GHz ISM radar transceiver**: 1 TX + 1 RX (MTR12: 2 RX), on‑chip VCO, quadrature down‑conversion to a **raw IQ IF baseband** you digitize yourself. Drive the VCO with an external ramp/DAC and you have arbitrary FMCW chirps; leave it CW and you have Doppler. Infineon ships eval kits (Distance2Go, Position2Go) and there is a healthy hobbyist‑radar community around it. This is a *real* analog radar front‑end with full documentation — Tier **5** for radar work: `radar`, `fmcw`, `raw-iq`, and (via VCO control) `arbitrary-waveform`, all inside the 24 GHz ISM band. The 24 GHz band has no entry in this catalog's band enum, so `bands` is left empty and the frequency is recorded in notes.

**NXP TEF810X** is a fully‑integrated **76–81 GHz** RF‑CMOS automotive radar transceiver (3 TX / 4 RX), typically paired with an NXP S32R radar MCU (MR3003/S32R274 lineage). It exposes raw ADC/IF data, so it is *technically* an mmWave radar front‑end — but the documentation is NDA‑gated, it requires the matching radar processor and chirp sequencer, and there is no open toolchain. Tier **3**: raw PHY exists but is closed/partially‑documented. Contrast with TI's more hacker‑accessible AWR/IWR mmWave line covered elsewhere.

### 5.8 GHz analog‑FPV video transmitters as "arbitrary‑ish" transmitters

The analog‑FPV ecosystem is full of cheap, SPI‑controllable **5.8 GHz FM transmitter ICs** — the canonical one is Richwave **RTC6705**. It takes a **composite/analog baseband input** and FM‑modulates it onto an SPI‑programmable carrier across **5645–5945 MHz** (the 40 standard FPV channels and everything between). The register interface was reverse‑engineered by the drone community and is a first‑class driver in **[Betaflight](https://github.com/betaflight/betaflight)** (`vtx_rtc6705.c`), exposed to users via the SmartAudio/Tramp protocols. From an SDR angle this is more interesting than it looks: you can set an arbitrary carrier in the 5.8 GHz band and feed **arbitrary analog baseband** into an FM modulator — a genuine (if single‑modulation, non‑IQ) transmitter and a ready‑made covert‑channel/analog‑telemetry primitive. Tier **3**: `arbitrary-waveform` (analog FM of arbitrary baseband) and `covert-channel`, programmable carrier, but no IQ and no complex modulation. Its companion **RX5808** receiver module (same ecosystem) is a tunable 5.8 GHz FM down‑converter with an analog RSSI output — occasionally abused as a crude 5.8 GHz power/spectrum sniffer.

### Missed Wi‑Fi

**Renesas DA16200** (formerly Dialog) is an ultra‑low‑power **Wi‑Fi 4 (802.11b/g/n, 2.4 GHz)** SoC with an integrated Cortex‑M4 and a FreeRTOS SDK. It is a closed‑PHY IoT part; the SDK exposes a promiscuous/monitor receive path at best, with no documented CSI, injection, or raw‑PHY access. Tier **1** (monitor plausible via SDK, unverified for injection/CSI), openness partially‑documented. Net‑new to the catalog.

**Module vendors are not silicon.** Telit (WE866‑series), Quectel (FC41D and similar), SparkLAN, and Silex Technology sell Wi‑Fi *modules*, but the RF/PHY is third‑party silicon already in this catalog — most commonly Realtek, Qualcomm Atheros, NXP/Marvell, or Infineon/Cypress dies. Their SDR ceiling is exactly that of the underlying chip: a Silex/SparkLAN module built on an `ath9k`‑class Atheros die inherits monitor/injection/CSI (see [./qualcomm-atheros.md](./qualcomm-atheros.md)); one built on a Cypress/BCM43xx die inherits Nexmon CSI (see [./broadcom-cypress.md](./broadcom-cypress.md)). No net‑new module records are warranted for the rebrands — identify the die (FCC ID → internal photos is the fastest route, cross‑referenced in [./hardware-index.md](./hardware-index.md)) and look it up under its real vendor. This is the single most useful takeaway for anyone holding an M.2/SDIO module of unknown provenance.

### Cross‑references
- Fixed closed radios you command but cannot drive: [./cellular-basebands.md](./cellular-basebands.md)
- FCC‑ID → die identification for rebranded modules: [./hardware-index.md](./hardware-index.md)
- Iridium/GNSS receive toolchains: [../projects/gnuradio-oot-modules.md](../projects/gnuradio-oot-modules.md)
- Why "GNSS/cellular chip → IQ radio" is almost always false: [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)
- Transmit legality on satellite/GNSS/radar bands: [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md)

### References
- Semtech LR1120 (LoRa Connect, multi‑band incl. S‑band): https://www.semtech.com/products/wireless-rf/lora-connect/lr1120
- Swarm M138 modem: https://swarm.space/product/swarm-m138-modem/
- Astrocast Astronode S / dev docs: https://docs.astrocast.com/
- Iridium 9603 SBD transceiver: https://www.iridium.com/products/iridium-9603/
- `gr-iridium` (external‑SDR Iridium downlink RX): https://github.com/muccc/gr-iridium
- Myriota: https://myriota.com/
- Analog Devices MAX2771 GNSS front‑end: https://www.analog.com/en/products/max2771.html
- GNSS‑SDR (uses MAX2771/front‑ends): https://gnss-sdr.org/
- Skyworks SE4150L GPS front‑end: https://www.skyworksinc.com/en/Products/Timing/GPS-Receivers
- Infineon BGT24MTR11 24 GHz radar: https://www.infineon.com/cms/en/product/sensor/radar-sensors/radar-sensors-for-automation/24ghz-radar-sensors/
- NXP TEF810X 77 GHz radar transceiver: https://www.nxp.com/products/radio-frequency/radar-transceivers:MC_71571
- RTC6705 driver in Betaflight: https://github.com/betaflight/betaflight/blob/master/src/main/drivers/vtx_rtc6705.c
- Renesas DA16200 ultra‑low‑power Wi‑Fi SoC: https://www.renesas.com/en/products/wireless-connectivity/wi-fi/low-power-wi-fi/da16200-ultra-low-power-wi-fi-soc-battery-powered-iot-devices


---

## Long-tail sweep — Cycle 7

*Round 5: stragglers & retro.* This sweep closes out the pre-mac80211 "retro" era (the chips that first made monitor mode and injection real) plus a handful of modern module-vendor parts that slipped past earlier cycles. Historical parts are catalogued for provenance: several are the *reason* SDR-style Wi-Fi hacking exists, even though by the tier ladder they only reach **tier 1** (monitor + injection). Net-new ids only; `marvell-88w8897` and `realtek-rtl8187l` are already catalogued and are **not** repeated here.

### Why the retro chips matter

The tier ladder rewards raw-IQ and PHY access, so almost everything below sits at **tier 1**. But tier 1 undersells their place in history. Before mac80211/cfg80211 existed, the MAC layer lived either in host software (softMAC) or in firmware (fullMAC). The softMAC and host-driven parts — Prism2, ADM8211, ACX1xx, ZD1211, the Libertas thin-firmware — are precisely the ones that let researchers craft, inject, and capture 802.11 frames arbitrarily, which is the direct ancestor of today's Nexmon/`ath9k` injection work. The fullMAC/closed-firmware parts (Hermes/Orinoco, Aironet, DA16600) needed patched firmware or vendor cooperation to expose even monitor mode, which foreshadows the whole premise of this catalog.

### Net-new parts

| id | vendor | part(s) | era / std | tier | why it's here |
|---|---|---|---|---|---|
| `intersil-prism2` | Intersil (Harris → Conexant → GlobespanVirata) | HFA3841 / ISL3874 (Prism2), ISL3872 (2.5), ISL3880/3890 (3) | 1999, 802.11b | 1 | **The original monitor-mode + injection chipset.** `hostap` driver. |
| `agere-hermes-orinoco` | Lucent / Agere (ex-NCR/AT&T WaveLAN) | Hermes (WaveLAN/IEEE, Orinoco Gold/Silver) | 1999, 802.11b | 1 | WaveLAN = the original 802.11; monitor via `orinoco` patches. |
| `cisco-aironet-350` | Cisco (ex-Aironet Wireless Comms.) | Aironet 340/350 (AIR-PCM/LMC350) | 2000, 802.11b | 1 | Enterprise LEAP/MIC radio; `airo` driver monitor mode. |
| `symbol-spectrum24` | Symbol Technologies | Spectrum24 LA-4121/LA-4137 | 2000, 802.11b | 1 | Prism2-derived; `orinoco`/`hostap` "Symbol" firmware path. |
| `admtek-adm8211` | ADMtek (→ Infineon) | ADM8211 | 2001, 802.11b | 1 | Extreme softMAC — host builds beacons/frames; `adm8211`. |
| `ti-acx1xx` | Texas Instruments | ACX100 (11b) / ACX111 = TNETW1130 (11g) | 2002–03, 802.11b/g | 1 | Reverse-engineered open `acx` driver, uploaded firmware blob. |
| `zydas-zd1211` | ZyDAS (→ Atheros/Qualcomm) | ZD1211 / ZD1211B (USB); ZD1201 (older 11b) | 2004, 802.11b/g USB | 1 | Open softMAC `zd1211rw`; long an aircrack-ng favorite. |
| `marvell-libertas-8388` | Marvell | 88W8388 (Libertas; SDIO/USB/CF) | 2006, 802.11b/g | 1 | **OLPC XO-1 radio**; 802.11s mesh; `libertas_tf` thin-firmware. |
| `renesas-da16600` | Renesas (ex-Dialog) | DA16600 module (DA16200 SoC + DA14531 BLE) | 2020, 802.11b/g/n + BLE 5 | 0 | Ultra-low-power Wi-Fi IoT; closed FreeRTOS SDK. |
| `telit-we310f5` | Telit Cinterion | WE310F5 (rebrand of Redpine/Silicon Labs RS9113) | 2018, 802.11abgn + BT | 0 | Module rebrand — tier inherits from the RS9113 die. |
| `quectel-fgh100m` | Quectel | FGH100M-H (Wi-Fi HaLow; Newracom NRC7292/NRC7394) | 2022, 802.11ah **sub-GHz** | 1 | Sub-GHz HaLow; Newracom host driver is open-ish on GitHub. |
| `quectel-fcu630` | Quectel | FCU630 / FC41D combo modules | 2021, 802.11a/b/g/n/ac + BT | 0 | Combo module; underlying die varies (ASR/Realtek class). |
| `sparklan-wpeq-series` | SparkLAN | WPEQ-/WNFQ-series (MediaTek MT7915, Qualcomm QCAxxxx) | 2019+, 802.11ac/ax | 0 | Pure carrier board — tier inherits from the MediaTek/QCA die. |

### Detail & provenance

**`intersil-prism2` — Prism 2 / 2.5 / 3 (802.11b, 2.4 GHz).** The historically decisive part. Because the MAC ran host-side under Jouni Malinen's `hostap` driver, a card could be forced into AP mode, monitor mode, and arbitrary frame injection from userspace — this is what made AirSnort, early WEP cracking, and the first practical rogue-AP work possible. Datasheets and register maps were widely circulated (partially-documented), though the on-chip firmware itself stayed closed. Kernel `hostap` lists it as "Intersil/Conexant." No PHY/IQ access — **tier 1**, caps monitor + injection. Verified. See [Prism (chipset)](https://en.wikipedia.org/wiki/Prism_(chipset)) and [hostap](https://w1.fi/hostap.html).

**`agere-hermes-orinoco` — Lucent/Agere Hermes (WaveLAN/Orinoco, 802.11b).** Direct descendant of NCR/AT&T WaveLAN, the very first 802.11 product line. FullMAC: the MAC lived in closed firmware, so the mainline `orinoco` driver (vendors listed as "Agere/Intersil/Symbol") originally had *no* monitor mode; the community shim/patch and later the `orinoco_cs` monitor support unlocked capture, with injection only partial. Agere was notoriously reluctant to document, which is exactly the closed-firmware wall this catalog exists to climb. **Tier 1**, openness closed. Verified via kernel driver docs and [WaveLAN](https://en.wikipedia.org/wiki/WaveLAN).

**`cisco-aironet-350` — Cisco Aironet 340/350 (802.11b).** Cisco absorbed Aironet in 1999; the 350-series PCMCIA/PCI radios were the enterprise workhorse (LEAP, Cisco MIC). The open `airo` driver (kernel: "Aironet/Cisco") supports monitor mode; injection support was limited and firmware closed. **Tier 1**, caps monitor. Verified via kernel `airo` driver.

**`symbol-spectrum24` — Symbol Spectrum24 (802.11b).** Symbol's barcode-scanner and warehouse radios were largely Prism2-derived; several are driven by `orinoco`/`hostap` with Symbol-specific firmware download. Same softMAC lineage → monitor + injection reachable. **Tier 1**, status reported (firmware-variant dependent).

**`admtek-adm8211` — ADMtek ADM8211 (802.11b PCI).** Unusually thin hardware: the `adm8211` driver builds beacon frames and does much of the MAC in host software, which made the part a favorite for frame-injection experimentation despite mediocre RX. Register interface was reverse-engineered (partially-documented). Kernel lists "ADMtek/Infineon." **Tier 1**, caps monitor + injection.

**`ti-acx1xx` — TI ACX100 / ACX111 (TNETW1130) (802.11b/g).** The `acx` project reverse-engineered a fully open Linux driver around a closed firmware blob uploaded at init — an early template for exactly the "open driver, opaque firmware" split this catalog tracks. ACX111 added 802.11g. Monitor works; injection partial. **Tier 1**, openness partially-documented. See [acx100 project](https://acx100.sourceforge.net/).

**`zydas-zd1211` — ZyDAS ZD1211 / ZD1211B (USB, 802.11b/g).** Open softMAC `zd1211rw` (kernel: "ZyDAS/Atheros" — Atheros acquired ZyDAS in 2006). Clean monitor + injection support made ZD1211 USB dongles a long-running aircrack-ng recommendation. Older sibling ZD1201 was 802.11b-only. **Tier 1**, openness partially-documented/patchable. Verified via kernel `zd1211rw`.

**`marvell-libertas-8388` — Marvell 88W8388 "Libertas" (802.11b/g; SDIO/USB/CF).** The **OLPC XO-1** radio, and the most open-firmware-relevant retro part here. Two firmware personalities: the standard fullMAC `libertas` firmware (with hardware 802.11s mesh, the XO-1's headline feature), and `libertas_tf` — a **thin-firmware** variant that pushes the MAC up into `mac80211`, giving softMAC-style monitor/injection. Genuinely open firmware never shipped: Red Hat/OLPC operated under a Marvell NDA that drew sustained criticism from open-source advocates (documented in the OLPC coverage), so the firmware stayed closed even as the drivers went upstream. **Tier 1**, openness partially-documented (thin-firmware offload, closed blob). Distinct from the already-catalogued modern `marvell-88w8897`. Verified via kernel `libertas`/`libertas_tf` and the OLPC/Marvell NDA history.

**`renesas-da16600` — Renesas (ex-Dialog) DA16600 (802.11b/g/n 2.4 GHz + BLE 5).** Ultra-low-power Wi-Fi IoT module pairing the DA16200 Wi-Fi SoC with a DA14531 BLE die. Vendor FreeRTOS SDK only; no host driver source for the PHY, no IQ path. Modern, closed, **tier 0** — catalogued so the modern IoT long-tail is complete. See [Renesas DA16600](https://www.renesas.com/en/products/wireless-connectivity/wi-fi/low-power-wi-fi).

**`telit-we310f5` — Telit WE310F5.** A module-vendor rebrand of the Redpine Signals (later Silicon Labs) RS9113 single-die abgn+BT/BLE part. No independent silicon; SDR potential is whatever the RS9113 die offers, which in the shipping firmware is nil. **Tier 0**, closed. Status reported (rebrand).

**`quectel-fgh100m` — Quectel FGH100M-H (Wi-Fi HaLow, 802.11ah, sub-GHz).** The one genuinely interesting modern straggler: **sub-GHz** (sub-1 GHz ISM) 802.11ah HaLow built on a **Newracom** NRC7292/NRC7394 SoC. Newracom publishes an open host driver package (`nrc7292_sw_pkg`) with monitor-mode support and a CSPI/host interface, though the firmware image is a supplied binary — a HaLow analogue of the ath9k story worth a deeper look in a future cycle. **Tier 1** (monitor reported), openness partially-documented, band **sub-GHz**. See [Newracom nrc7292_sw_pkg](https://github.com/newracom/nrc7292_sw_pkg).

**`quectel-fcu630` — Quectel FCU630 / FC41D.** Wi-Fi 5 (11ac) + Bluetooth combo modules; the underlying die is an ASR/Realtek-class combo part depending on SKU. Closed. **Tier 0**, status reported. Catalogued as the "combo module" placeholder — chase the die, not the module.

**`sparklan-wpeq-series` — SparkLAN WPEQ/WNFQ modules.** SparkLAN is a carrier-board/module house, not a silicon vendor: WPEQ-series wraps MediaTek MT7915 (Wi-Fi 6), WNFQ-series wraps Qualcomm QCA parts. SDR capability inherits entirely from the underlying die (see the MediaTek and Qualcomm-Atheros chip files). **Tier 0** as a module record; the real tier lives with the silicon. Status reported.

### Cross-references & consolidated retro references

- Linux mainline drivers for every retro part above (chip↔vendor mapping): [kernel wireless drivers list](https://wireless.docs.kernel.org/en/latest/en/users/drivers.html) — `hostap`, `orinoco`, `airo`, `adm8211`, `acx`, `zd1211rw`, `libertas`/`libertas_tf`.
- Prism2/hostap lineage: [Prism (chipset)](https://en.wikipedia.org/wiki/Prism_(chipset)), [hostap](https://w1.fi/hostap.html) — historical bridge to modern injection (`../chips/qualcomm-atheros.md`, `../projects/nexmon.md`).
- WaveLAN/Orinoco origin: [WaveLAN](https://en.wikipedia.org/wiki/WaveLAN).
- TI ACX open-driver-over-closed-firmware pattern: [acx100.sourceforge.net](https://acx100.sourceforge.net/) — compare methodology in `../docs/firmware-reversing.md`.
- ZyDAS: [ZyDAS](https://en.wikipedia.org/wiki/ZyDAS).
- Newracom HaLow (sub-GHz, forward-looking): [github.com/newracom/nrc7292_sw_pkg](https://github.com/newracom/nrc7292_sw_pkg).

**Honest-tier reminder:** none of these retro parts reach tier 2+. Their value is provenance and softMAC frame-level control (tier 1), not IQ/PHY access. Modern rebrand modules (Telit, Quectel combo, SparkLAN) are tier 0 pointers whose true capability is the die they carry — always resolve the module to its silicon before assigning a tier.


---

## Long-tail sweep — Cycle 8

Round 6 of the straggler sweep: retro client cards, Chinese IoT Wi-Fi SoCs/modules, and ruggedized MANET mesh radios that had not yet been catalogued. As always for **modules/integrators**, the SDR ceiling is the ceiling of the underlying **die** — a Murata/AzureWave/Doodle Labs/Rajant assembly inherits its radio's tier and nothing more. Tiers here are deliberately low; almost everything in this batch is Tier 0–1. Where a part is a repackaged die already in the catalog, score by the die and cross-reference it rather than inventing new offsets.

Already catalogued elsewhere — not repeated here: `marvell-88w8897`, `realtek-rtl8187l`, and the Intersil **Prism2/2.5** family (referenced below only as the *die* inside retro modules).

### Retro client cards

| id | Part(s) | Die / radio | Linux driver | Tier | Notes |
|----|---------|-------------|--------------|------|-------|
| `cisco-aironet-cb21ag` | AIR-CB21AG, AIR-PI21AG | **Atheros AR5212** (a/b/g) | `ath5k` / MadWifi | 1 | Genuine Atheros die → monitor + injection. Best retro pick. |
| `cisco-aironet-350` | AIR-PCM350, AIR-LMC352, AIR-PCI350 | Cisco proprietary 802.11b MAC | `airo` | 1 | `airo` supports monitor mode; no injection; closed firmware blob. |
| `symbol-spectrum24` | Symbol/Motorola/Zebra Spectrum24 HR (LA-4121, etc.) | **Intersil Prism2** | `hostap` / `orinoco` | 1 | Prism2 die → classic monitor + injection. Score by Prism2. |
| `proxim-orinoco-gold` | Orinoco Gold/Silver, WaveLAN Gold | **Lucent/Agere Hermes** (WaveLAN) | `orinoco_cs` | 1 | Gold vs Silver = 128- vs 64-bit WEP only; same Hermes die. Monitor via patched `orinoco`; no injection. |
| `dlink-legacy-wlan` | DWL-650, DWL-520, DWL-G650, DWL-G122 | mixed: **Prism2/2.5**, **AR5212**, **Ralink RT2570**, **Marvell** | `hostap`/`ath5k`/`rt2500usb` | 1 | Integrator — tier = whichever die the revision carries. |
| `3com-usr-legacy-wlan` | 3Com OfficeConnect 11g, USRobotics USR2210/5410/5416 | mixed: **Prism2**, **Atmel AT76C503**, **Atheros**, **Broadcom** | `hostap`/`atmel`/`ath5k`/`b43` | 1 | Rebadge integrator — score by the specific die per revision. |

**Notes on the retro batch**

- **CB21AG is the standout.** Cisco's a/b/g client is a bog-standard **Atheros AR5212** behind a Cisco sticker, so it does full RFMON monitor + frame injection under `ath5k`/MadWifi exactly like any AR5212 (cross-reference `chips/qualcomm-atheros.md`). The older **Aironet 340/350** 802.11b cards are a *different, proprietary* Cisco radio driven by the in-tree `airo` module — monitor mode works, injection does not, and the on-card firmware is an opaque flashable blob.
- **Prism2 lives on inside other people's plastic.** Symbol/Motorola/Zebra **Spectrum24 High-Rate**, many **D-Link DWL-650**, and a good fraction of **3Com/USR** cards are Intersil **Prism2/2.5** dies — the canonical monitor/injection retro chipset. These modules add no capability of their own; their tier is the Prism2 die's tier.
- **Hermes (Orinoco Gold/Silver)** is the Lucent/Agere WaveLAN die. It predates cheap monitor mode: the `orinoco` driver needs the monitor-mode patch and cannot inject, so it tops out at Tier 1 monitor-only. Historically important (it was the "classic" WarDriving card with NetStumbler/Kismet) but weak as an SDR.

### Chinese IoT Wi-Fi SoCs & modules

| id | Part(s) | Core | Radio | Tier | Notes |
|----|---------|------|-------|------|-------|
| `winnermicro-w600` | WinnerMicro W600/W601, TW-01/02/03 modules | ARM Cortex-M3 | 2.4 GHz 802.11 b/g/n | 0 | Open **WM SDK**, but PHY/MAC closed — no monitor/CSI path. Flashable (open-firmware) only. |
| `winnermicro-w800` | WinnerMicro W800/W801/W806, HLK-W806 | ARM Cortex-M3 | 2.4 GHz 802.11 b/g/n + BLE | 0 | Wi-Fi+BLE combo; open SDK, closed PHY. Popular ESP-alternative. |
| `tuya-wifi-modules` | TYWE1S/2S/3S, WB2/WB3, WBR series | — | 2.4 GHz | 1 | Integrator: TYWE=**ESP8266**, WB=**Beken BK7231N/T** or **Realtek RTL8720**. Tier = die (ESP8266 → monitor/CSI via `chips/espressif.md`). |
| `aithinker-modules` | ESP-01/12 (ESP8266), ESP-32S, RTL-02/03 (RTL8710), BW12/BW15 (BK7231) | — | 2.4 GHz (+5 GHz on RTL8720/BW15) | 1 | Integrator: score by die — ESP → `chips/espressif.md`; RTL87xx/BK72xx → `chips/realtek.md` / Beken. |
| `lierda-modules` | Lierda NB/Wi-Fi combo modules | — | 2.4 GHz | 1 | Integrator carrying **ESP32/ESP8266** or **Realtek RTL87xx** dies; tier per die. |

**Notes on the Chinese IoT batch**

- **Winner Micro W60x/W80x** are the "domestic ESP" — cheap Cortex-M3 Wi-Fi SoCs (the W800 adds BLE) from Beijing Winner Microelectronics, widely reflashed with the open **WM SDK**, Arduino cores, MicroPython and community forks. Crucially the SDK is open but the **PHY/baseband is a closed blob**: there is no published monitor/CSI/injection interface, so despite `open-firmware` they sit at **Tier 0**. Treat any Tuya/Lierda/Ai-Thinker module built on a W60x/W80x the same way.
- **Tuya, Ai-Thinker and Lierda are packagers, not silicon vendors.** A Tuya `TYWE3S` is an **ESP8266**; a `WB3S` is a **Beken BK7231**; a `WBR3` is a **Realtek RTL8720**. An Ai-Thinker `ESP-12F` is an ESP8266, an `RT-02` is an RTL8710. So the SDR ceiling is entirely the die's: an ESP8266-based module reaches the ESP8266's monitor/injection/CSI tier (see `chips/espressif.md`), a BK7231/RTL8710 module is a closed Tier 0–1. Do not double-count these as new capabilities.

### Ruggedized / MANET mesh radios

| id | Part(s) | Underlying radio | Stack | Tier | Notes |
|----|---------|-----------------|-------|------|-------|
| `doodle-labs-mesh-rider` | Mesh Rider / Smart Radio (RM-2450, RM-915, embedded H/W-series) | **QCA IPQ40xx + QCA9880/9882/9888**, some **AR9xxx** | OpenWrt + ath9k/ath10k | 3 | Standard QCA dies on OpenWrt → monitor, injection, ath9k CSI, ath10k spectral. Tier = die (`chips/qualcomm-atheros.md`). |
| `rajant-breadcrumb` | Rajant BreadCrumb (ME4, LX5, ES1, Cardinal) + InstaMesh | **Atheros/QCA 802.11 a/b/g/n/ac** | proprietary InstaMesh over 802.11 | 1 | Integrator: standard Atheros radios behind a closed mesh protocol; die gives monitor/injection at best. |
| `silvus-streamcaster` | Silvus StreamCaster SC4200/SC4400 (MN-MIMO) | proprietary FPGA MIMO-OFDM baseband | closed "Mobile Networked MIMO" waveform | 0 | A genuine *soft* radio but fully proprietary/black-box — not a repurposable Wi-Fi die. No user PHY access. |

**Notes on the mesh batch**

- **Doodle Labs Mesh Rider** is the useful one: it is **OpenWrt on Qualcomm Atheros silicon** (IPQ40xx SoCs with QCA9880/9882/9888 or older AR9xxx radios), including sub-GHz (900 MHz), 2.4, and 5 GHz variants. Because the die is mainline `ath9k`/`ath10k`, you inherit the full Atheros SDR ladder — monitor + injection, **Atheros CSI Tool** on `ath9k` (Tier 2), and **`ath10k` spectral scan** (Tier 3) on the QCA988x radios. The tier belongs to the die; cross-reference `chips/qualcomm-atheros.md` and `projects/csi-toolchains.md`.
- **Rajant BreadCrumb** wraps ordinary Atheros 802.11 a/b/g/n/ac radios in the closed **InstaMesh** protocol. The radios themselves are Atheros dies (monitor/injection possible if you can get to the driver), but the shipped firmware exposes only the mesh stack → practically Tier 1.
- **Silvus StreamCaster** is the odd one out: it is *already* a software radio (FPGA-based MIMO-OFDM "MN-MIMO" waveform, not 802.11), but it is a sealed defense/industrial product with no open PHY, SDK, or driver — a black box, **Tier 0**, listed only for completeness.

### Cross-references

- Prism2/2.5 dies inside Symbol/D-Link/3Com cards → the Intersil Prism family entries and `chips/monitor-injection-support.md`.
- Atheros AR5212 (CB21AG, DWL-G650) and QCA988x (Doodle Labs) → `chips/qualcomm-atheros.md`.
- ESP8266/ESP32 inside Tuya/Ai-Thinker/Lierda modules → `chips/espressif.md`; RTL87xx modules → `chips/realtek.md`.
- Monitor-mode retro landscape → `chips/monitor-injection-support.md`; timeline of WaveLAN/Prism/Aironet → `docs/history-timeline.md`.

### References

- Linux `airo` driver (Cisco Aironet 340/350): https://www.kernel.org/doc/html/latest/networking/device_drivers/wifi/airo.html
- Linux `ath5k` (Atheros AR5212, incl. Cisco CB21AG, D-Link DWL-G650): https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath5k.html
- Linux `orinoco` / Hermes (Orinoco Gold/Silver, WaveLAN): https://wireless.docs.kernel.org/en/latest/en/users/drivers/orinoco.html
- Linux `hostap` (Intersil Prism2/2.5 — Symbol Spectrum24, D-Link DWL-650, 3Com/USR): https://wireless.docs.kernel.org/en/latest/en/users/drivers/hostap.html
- WaveLAN / Hermes background: https://en.wikipedia.org/wiki/WaveLAN
- Cisco Aironet series: https://en.wikipedia.org/wiki/Cisco_Aironet_series
- WinnerMicro (W600/W800 vendor): https://www.winnermicro.com/
- Tuya module cross-reference (die-per-module): https://tasmota.github.io/docs/devices/
- Ai-Thinker modules: https://docs.ai-thinker.com/en/wifi
- Doodle Labs Mesh Rider (OpenWrt / QCA): https://doodlelabs.com/products/mesh-rider-radio/
- Rajant Kinetic Mesh / InstaMesh: https://rajant.com/technology/
- Silvus StreamCaster MN-MIMO: https://silvustechnologies.com/products/streamcaster-radios/
- Atheros CSI Tool (ath9k CSI on QCA radios): https://wands.sg/research/wifi/AtherosCSI/


---

## Long-tail sweep — Cycle 9

*Round 7 — final stragglers.* After six prior long-tail rounds the breadth is genuinely near-exhausted: the popular cheap-BLE RE targets (Telink TLSR825x/TLSR9, Beken BK3435/BK3633/BK7231, PHYPLUS/PhyPlusInc PHY62xx, Bouffalo BL602/BL616) were already catalogued in earlier cycles and are **not** repeated here. What remained were three genuinely un-catalogued classes:

1. **RISC-V Chinese BLE + proprietary-2.4G SoCs** (WCH CH57x/CH58x/CH585) — cheap, well-documented, open toolchain, closed RF blob. Real tier-1 injection targets.
2. **Bluetooth-audio SoCs** (Jieli AC63xx/AC69xx) — ubiquitous in TWS earbuds/dongles; fully closed RF, listed for completeness.
3. **Professional MANET / kinetic-mesh radios** (Doodle Labs Mesh Rider, Persistent Systems MPU5, Rajant BreadCrumb, Silvus StreamCaster). Important honesty note: **these last three are already genuine software-defined radios internally, but their firmware is locked.** They are catalogued as *reference points* — what a fielded SDR-based waveform looks like — not as repurposing targets. Their tiers reflect the RE path available to an owner (near zero), not the hardware's intrinsic capability. The Doodle Labs radios are the exception: they ship an OpenWrt-derived "Mesh Rider OS" with shell access, so an owner reaches `mac80211` monitor/injection legitimately.

Beyond these, the residual long tail (avionics VDL/ACARS datalink modules, marine AIS baseband ICs such as CML Microcircuits CMX7042/CMX994, Iridium 9603 SBD) is **off-theme**: those are dedicated single-purpose RF/baseband parts, not general wireless SoCs repurposable via firmware RE, so they are noted here but not given catalog entries. The long tail is effectively closed after this round.

### Net-new entries

| id | part(s) | bands | tier | RE path |
|---|---|---|---|---|
| `wch-ch58x` | CH581 / CH582 / CH583 | 2.4 GHz | 1 | Open RISC-V toolchain; RF blob; proprietary-2.4G raw TX/RX |
| `wch-ch585` | CH584 / CH585 | 2.4 GHz | 1 | RV32IMBC; BLE 5.4 + 8 kHz-poll 2.4G + NFC |
| `wch-ch57x` | CH571 / CH573 | 2.4 GHz | 1 | Older BLE 4.2 RISC-V sibling of CH58x |
| `jieli-ac63xx` | AC632N / AC6329 / AC696N | 2.4 GHz | 0 | Closed BT-audio SoC; RF blob only |
| `doodle-labs-mesh-rider-nano2` | Nano² / Mini | sub-GHz, 2.4 GHz | 1 | OpenWrt shell → mac80211 monitor/injection |
| `doodle-labs-mesh-rider-boost` | Boost (4 W C-band) | 5 GHz, 6 GHz | 1 | Same OS, C-band front-end + PA |
| `persistent-mpu5` | MPU5 Wave Relay | sub-GHz, 2.4 GHz, 5 GHz | 0 | Locked SDR MANET; reference point |
| `rajant-breadcrumb` | ES1 / ME4 / LX5 / DX2 | sub-GHz, 2.4 GHz, 5 GHz | 0 | Multi-radio ath appliance; InstaMesh locked |
| `silvus-streamcaster` | SC4200 / SC4400 | sub-GHz, 2.4 GHz, 5 GHz | 0 | Locked MN-MIMO SDR; reference point |

### Notes on the WCH RISC-V family

The CH57x/CH58x/CH585 parts are attractive because everything *except the radio* is open: the QingKe RISC-V core is documented, the WCH-Link debugger + `wlink`/`openocd`/`riscv-gdb` and Ghidra's RV32 loader give full firmware visibility, and WCH ships the SDK openly ([openwch/ch583](https://github.com/openwch/ch583), [openwch/ch585](https://github.com/openwch/ch585), [openwch/ch573](https://github.com/openwch/ch573)). The RF itself is a linked binary library (`LIBCH58xBLE.a` / RF lib) — the modulator/PHY is not source-available. However, the SDK exposes a **proprietary 2.4 GHz mode** (nRF24-class): arbitrary payload, selectable channel and data rate (125 kbps / 500 kbps / 1 / 2 Mbps), promiscuous RX, and CRC/whitening control. That is enough for real **packet injection and promiscuous monitoring** within the chip's framing — hence tier 1 — but it is *not* raw-IQ or arbitrary-waveform, so it does not climb higher. CH585/CH584 add BLE 5.4, an 8 kHz-polling 2.4G HID mode, and an NFC interface (~13.56 MHz, outside the SDR band enum here).

### Notes on the professional MANET radios

- **Doodle Labs Mesh Rider** (Nano², Mini, OEM, Boost, Wearable) are frequency-agile MIMO 802.11-derived radios tuning roughly 255 MHz–2510 MHz (L/S band models) up to 4400–6400 MHz (Boost, C-band, 36 dBm / 4 W). They run "Mesh Rider OS," an OpenWrt derivative on a Qualcomm/Atheros-class front-end, so an owner has a root shell and legitimate `mac80211` monitor + injection (tier 1); ath-style spectral scan *may* be reachable but is unverified on the shifted-frequency firmware, so it is not claimed.
- **Persistent Systems MPU5 / Wave Relay** — a 3×3 MIMO MANET "smart radio," quad-core 1 GHz applications processor, software-defined OFDM waveform, band-specific (L/S/C) variants. Internally an SDR; firmware is locked, no owner RE path → tier 0, reference point only.
- **Rajant BreadCrumb** (ES1, ME4, LX5, DX2, Peregrine) — multi-transceiver kinetic-mesh nodes built on Qualcomm/Atheros 802.11 radios (2.4/5 GHz, some 900 MHz) with proprietary *InstaMesh* routing. The underlying Atheros silicon is covered by the `qualcomm-atheros.md` entries; the appliance firmware is locked → tier 0.
- **Silvus StreamCaster** (SC4200, SC4400, SC4240) — MN-MIMO MANET SDRs, 2×2/4×4, wide tuning across sub-GHz to ~6 GHz depending on model; locked firmware → tier 0, reference point.

### References

- WCH CH583 product page — https://www.wch-ic.com/products/CH583.html
- openwch SDKs — https://github.com/openwch/ch583 · https://github.com/openwch/ch585 · https://github.com/openwch/ch573
- Jieli (Zhuhai JieLi) — https://www.zh-jieli.com/ (AC63xx/AC69xx BT-audio SDKs distributed via the vendor's Gitee; RF is blob-only)
- Doodle Labs Mesh Rider products — https://doodlelabs.com/products/
- Persistent Systems MPU5 — https://www.persistentsystems.com/mpu5/
- Rajant Kinetic Mesh — https://rajant.com/
- Silvus Technologies StreamCaster — https://www.silvustechnologies.com/products/
