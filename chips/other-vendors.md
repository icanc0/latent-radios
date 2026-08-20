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
