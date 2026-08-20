# Sub-GHz LoRa / FSK / OOK Modules as Generic Radios

> **Scope.** Semtech LoRa/FSK transceivers (SX127x, SX126x, SX128x, LLCC68), the
> STM32WL LoRa SoC, TI's CC112x/CC1200 FSK line, Silicon Labs EZRadioPro
> (Si443x / Si446x), HopeRF RFM9x/RFM69, Microchip's RN2483/RN2903 LoRaWAN
> modules, and the Ebyte/NiceRF module ecosystem built on all of the above.
>
> **The honest headline.** None of these parts is a software-defined radio.
> They are *narrowband programmable transceivers*: a fixed hardware modem
> (fractional-N PLL + limited set of keyed modulators) wrapped in an SPI/UART
> register interface. You do **not** get baseband IQ, an ADC tap, or a
> reprogrammable PHY. What you *do* get, and what makes them worth cataloguing
> here, is **full register-level control of a real RF front end**: arbitrary
> carrier frequency across a whole ISM band, selectable (G)FSK/(G)MSK/OOK/LoRa,
> user-defined bitrate / deviation / preamble / sync word, a *continuous /
> direct / transparent* bitstream mode that bypasses the packet engine, and a
> continuous-wave (CW) test mode. That is enough to receive and forge almost any
> hobby sub-GHz protocol, build cross-technology bridges, and emit
> arbitrary on/off- or frequency-keyed waveforms — squarely **Tier 1** on our
> [SDR ladder](../docs/taxonomy.md), reaching toward "arbitrary keyed waveform"
> without ever becoming a general Tier 4/5 SDR.

Already catalogued elsewhere in this database and only referenced here:
[`semtech-sx127x`](../chips/lora-subghz.md) (the bare SX1272/76/78 die),
[`ti-cc1101`](../chips/lora-subghz.md), the
[`ti-cc1111-yardstick`](../projects/rtl-sdr-lineage.md) YARD Stick One dongle,
and the [`ti-cc13xx-cc26xx`](../chips/ble-154-thread.md) SimpleLink SoCs (which
absorb the CC1310/CC1312 sub-GHz cores). This page adds the *net-new* parts and
the module-level repackagings.

---

## 1. Why a LoRa/FSK modem is not an SDR — and what it is instead

A true SDR digitizes an IF/baseband and hands you IQ. These chips do the
opposite: they hide the ADC/DAC entirely and expose only the *products* of a
hardwired modem. Concretely, the signal path you can touch is:

```
                  ┌─────────────── you control via SPI/UART registers ───────────────┐
   antenna ──▶ LNA ──▶ mixer ──▶ [ fixed demod: FSK slicer / LoRa correlator ] ──▶ FIFO/bits
                          ▲                                                             │
                  fractional-N PLL  ◀── you set: freq, deviation, bitrate, mod, sync ───┘
   antenna ◀── PA ◀── modulator ◀── [ FIFO bytes  OR  direct DIO bitstream ] ◀─────────┘
```

The **three levers** that turn this from "a LoRa chip" into "a generic
sub-GHz radio":

1. **Arbitrary frequency + modulation registers.** Set any carrier the PLL can
   reach (e.g. SX1276 137–1020 MHz, CC1200 137–950 MHz, Si4468 142–1050 MHz),
   pick (G)FSK/OOK/(G)MSK, dial bitrate and deviation continuously. That alone
   lets you speak the vast majority of 315/433/868/915 MHz consumer protocols.
2. **Direct / continuous / transparent mode.** Every FSK part here can drop the
   packet engine and stream *raw bits* to/from a GPIO (SX127x/RFM9x
   `transmitDirect`/`receiveDirect` on DIO1-clock/DIO2-data; CC1101/CC120x
   async & sync serial modes; Si44xx direct TX/RX with GPIO data+clock). Feed it
   an arbitrary on/off or FSK pattern and it becomes an OOK/FSK
   *waveform player* — this is exactly how Flipper Zero and RfCat replay garage
   remotes, and how cross-technology-communication tricks are built.
3. **CW / continuous-preamble test modes.** A pure carrier (`radio cw on`,
   SX126x `SetTxContinuousWave`, CC1200 `MODCFG`) is an unmodulated tone
   generator — useful for jammer/interference studies, PLL characterization, and
   as the "on" symbol for hand-rolled AM.

What you still **cannot** do, and why these stay Tier 1: no I/Q sample access,
no simultaneous wideband capture, no reprogramming of the demodulator, no phase
control finer than the modulator's, and (except LoRa parts) no processing gain.
For genuine IQ and an editable PHY you cross over to real SDRs — see
[`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md) and the
[RTL-SDR lineage](../projects/rtl-sdr-lineage.md).

---

## 2. Part-by-part catalog

| Family | Bands (MHz) | Modulations | Direct/CW mode | Repurposing tier |
|---|---|---|---|---|
| Semtech SX127x *(catalogued)* | 137–1020 | LoRa, (G)FSK, OOK | ✅ DIO clk/data | 1 |
| Semtech SX126x | 150–960 | LoRa, (G)FSK | CW + limited direct | 1 |
| Semtech LLCC68 | 150–960 | LoRa (SF5–11), GFSK | CW | 1 |
| Semtech SX128x | **2400–2500** | LoRa, FLRC, GFSK, **ranging** | CW | 1 |
| ST STM32WL (SX126x + M4) | 150–960 | LoRa, (G)FSK, (G)MSK, BPSK | CW + open MCU | 1 (most hackable) |
| TI CC1200 / CC112x | 137–950 | 2/4-(G)FSK, MSK, OOK/ASK | ✅ async/sync serial | 1 |
| SiLabs Si446x (EZRadioPRO) | 119–1050 | (G)FSK, 4(G)FSK, (G)MSK, OOK | ✅ direct GPIO | 1 |
| SiLabs Si4432 / Si4438 | 240–930 / 425–525 | (G)FSK, OOK, FSK | ✅ direct GPIO | 1 |
| HopeRF RFM95/96/97/98 | 433/868/915 | = SX127x | ✅ DIO clk/data | 1 |
| HopeRF RFM69(H)(C)W | 315/433/868/915 | (G)FSK, OOK | ✅ direct | 1 |
| Microchip RN2483 / RN2903 | 433/868 / 915 | LoRa, FSK (via `radio`) | `radio cw`, `radio tx` | 1 (UART-boxed) |
| Ebyte / NiceRF modules | 170–930 + 2.4G | (host chip) | (host chip) | 1 |

### 2.1 Semtech SX126x (SX1261 / SX1262 / SX1268)
The second-generation LoRa transceiver: command-oriented SPI (opcodes, not a
flat register map), integrated DC-DC, +15 dBm (SX1261) / +22 dBm (SX1262) PA,
150–960 MHz. From a repurposing standpoint it is *more* capable than SX127x on
packets (better sensitivity, LoRa SF5) but *less* friendly for raw hacking: the
old DIO-clock/data continuous FSK path is gone, replaced by opcode-driven GFSK
packets, a **continuous-preamble** mode, and **`SetTxContinuousWave`** for a
bare tone. RadioLib still exposes `transmitDirect()`/`receiveDirect()` for
SX126x but with documented limits. Full command/register behaviour is published
in the SX126x datasheet and the *SX1261/2 Transceiver* reference — treat
openness as **documented**. SX1268 is the China-market (470 MHz) sibling.
Common carriers: Ebyte E22, Waveshare Core1262, NiceRF LoRa1262.

### 2.2 Semtech LLCC68
A cost-reduced SX1262: same command set and CW mode, but **LoRa SF5–SF11 only**
(no SF12) and reduced max bandwidth. Everything you'd do with SX1262 register
tricks applies; just note the missing SF12 when spoofing long-range links.

### 2.3 Semtech SX128x (SX1280 / SX1281) — 2.4 GHz LoRa
The outlier: LoRa in the **2.4 GHz ISM band** (2400–2500 MHz), plus **FLRC**
(fast long-range coherent), **(G)FSK**, and — uniquely — a hardware
**ranging engine** doing round-trip time-of-flight distance measurement between
two SX128x. It is also **PHY-compatible with BLE** (1 Mbps GFSK), so an SX1281
can be coerced into transmitting/sniffing raw BLE-shaped frames. For sensing
work the ranging engine is the interesting hook — see
[`../docs/ftm-rtt-ranging.md`](../docs/ftm-rtt-ranging.md) for how cooperative
ToF differs from true radar. SX1281 is the reduced-package SX1280. Carriers:
Ebyte E28, Semtech SX1280MB2xAS eval board.

### 2.4 ST STM32WLE5 / STM32WL55 — the LoRa SoC (most hackable)
STM32WL fuses an **SX126x-class radio** onto the same die as a Cortex-M4
(WLE5, single-core) or M4+M0+ (WL55, dual-core). Radio spec: 150 MHz–960 MHz,
LoRa / (G)FSK / (G)MSK / BPSK, up to +22 dBm. Crucially the radio is a
**memory-mapped peripheral fully documented in RM0453/RM0461**, driven through
the `SUBGHZSPI` internal bus — so you write *all* the firmware, on an open GCC
toolchain, with the radio state machine documented at register level. That
makes STM32WL the one part in this list where the **firmware flag is
`open-firmware`**: there is no vendor blob between you and the modem. Ideal for
custom PHY experiments, timing-precise TX, and CTC where you need the CPU and
radio tightly coupled. Boards: NUCLEO-WL55JC, Seeed LoRa-E5 (which *is* an
STM32WLE5 module), RAK3172.

### 2.5 TI CC1200 / CC112x (CC1120 / CC1121 / CC1125)
TI's high-performance narrowband line: 137–158 / 164–190 / 205–238 / 274–317 /
410–475 / 820–950 MHz, **2-FSK, 2-GFSK, 4-FSK, 4-GFSK, MSK, OOK/ASK**, up to
1.25 Mbps (CC1200) with –123 dBm sensitivity, and a flexible register modem.
Like the CC1101 it exposes **asynchronous and synchronous serial (transparent)
modes** on GPIO, i.e. a genuine direct bitstream path for arbitrary OOK/FSK
waveform play and capture. CC112x targets **IEEE 802.15.4g** SUN-FSK, wM-Bus
and narrowband ISM. CC1125 is the ultra-narrowband (12.5 kHz channel) variant;
CC1120/CC1121 are lower-cost cuts. Register map fully documented (**documented**
openness) in the CC120x user's guide (SWRU346). These pair naturally with the
already-catalogued CC1101 workflow.

### 2.6 Silicon Labs EZRadioPRO — Si446x and Si443x
- **Si446x** (Si4460/61/63/64/67/68): 119–1050 MHz, **(G)FSK, 4(G)FSK,
  (G)MSK, OOK**, up to 1 Mbps, –126 dBm (Si4468) narrowband sensitivity. They
  support a **direct mode** (TX/RX bitstream over GPIO with data+clock),
  which — as with the TI/Semtech parts — is the lever for arbitrary keyed
  waveforms and protocol forging. Quirk: the register map is delivered as
  **firmware "patch" + WDS-generated config blobs** rather than a fully open
  flat map, so real openness is **partially-documented**; community projects
  reverse the WDS output to regain manual control.
- **Si4432 / Si4438**: earlier EZRadioPRO. Si4432 (240–930 MHz, (G)FSK/OOK) is
  the chip inside the ubiquitous cheap "RF4432" modules and is well documented;
  Si4438 is the 425–525 MHz China ISM variant. Both offer a classic direct
  mode. These are the parts most hobby 433 MHz links and many alarm sensors use,
  making them prime targets for RX forensics and replay.

### 2.7 HopeRF RFM9x and RFM69
HopeRF modules are **repackaged Semtech die**, so their "repurposing" story is
inherited wholesale:
- **RFM95W/RFM96W/RFM97W/RFM98W** = **SX1276/77/78** on a castellated module
  (RFM95 868/915, RFM96 433, RFM98 for lower bands). Everything on the
  [`semtech-sx127x`](../chips/lora-subghz.md) page — LoRa, FSK, and the
  `transmitDirect`/`receiveDirect` DIO clk/data raw mode — applies verbatim.
- **RFM69(H)(C)W** = Semtech **SX1231/SX1231H** GFSK/OOK engine (no LoRa).
  315/433/868/915 MHz, direct mode supported, widely used in sensor networks
  (RadioHead, LowPowerLab). Excellent, cheap OOK/FSK transmit-and-capture front
  end for CTC and replay experiments.

### 2.8 Microchip RN2483 / RN2903 — the UART-boxed radio
These are **SX1276/SX1272 + PIC** modules running Microchip's **closed**
LoRaWAN stack, spoken over an ASCII UART. Two command trees:
`mac ...` (full LoRaWAN Class A) and, more usefully for us, **`radio ...`** —
`radio set mod {lora|fsk}`, `radio set freq`, `radio set bt/bitrate`,
`radio set fdev`, `radio set prlen`, `radio set sync`, `radio set pwr`,
`radio tx <hex>`, `radio rx <window>`, and **`radio cw on/off`** for continuous
wave. So even through a closed firmware you retain enough raw control for
arbitrary-payload FSK/LoRa TX/RX and a CW tone — Tier 1, just boxed behind a
serial API you cannot bypass (**closed** firmware). RN2483 = 433/868 EU,
RN2903 = 915 NA.

### 2.9 Ebyte / NiceRF / generic modules
Ebyte (Chengdu Ebyte, "E-series": E22=SX1262, E28=SX128x, E07=CC1101,
E49/E30/E32 variants, E80=LR11xx) and NiceRF/G-NiceRF sell **carrier boards for
every chip above** plus PA/LNA front ends and, often, an on-board MCU running a
transparent-UART firmware. Two modes of use: (a) **transparent-UART firmware** —
convenient but opaque, effectively an RN2483-style closed box; (b) **strip the
firmware and talk SPI to the bare Semtech/TI/SiLabs die**, which restores the
full register-level Tier-1 capability of the host chip. Always identify the
*inner* chip — the module part number tells you which of the sections above
governs its real capability.

---

## 3. Toolchains for repurposing

### 3.1 RadioLib (embedded, Arduino/RP2040/ESP32)
[RadioLib](https://github.com/jgromes/RadioLib) is the single most useful lever:
one API across **SX127x, SX126x, SX128x, LLCC68, RFM9x, RFM69/RF69, CC1101,
Si443x, LR11x0 and STM32WL**. Beyond `transmit()/receive()` it exposes the raw
knobs we care about:

```cpp
// SX1276 / RFM95 as a raw FSK bit-banger (direct mode on DIO1=clk, DIO2=data)
radio.beginFSK();
radio.setFrequency(433.92);        // any carrier the PLL reaches
radio.setBitRate(4.8);
radio.setFrequencyDeviation(5.0);
radio.setPreambleLength(16);
uint8_t sync[] = {0x2D, 0xD4};
radio.setSyncWord(sync, 2);
radio.transmitDirect();            // stream arbitrary bits on the DIO pins
// radio.receiveDirect();          // promiscuous raw-bit capture
```

`transmitDirect()`/`receiveDirect()` (FSK-mode only) are exactly the "monitor +
injection" primitives that make a packet chip behave like a bitstream radio;
`transmitDirect(uint32_t frf)` can also emit a fixed carrier for CW work.

### 3.2 GNU Radio — where the *real* SDR does the LoRa PHY
The chips can't be SDRs, but their **PHY can be reproduced on one**:
- **[gr-lora_sdr](https://github.com/tapparelj/gr-lora_sdr)** (EPFL, Tapparel) —
  a *fully functional* LoRa transceiver in GNU Radio 3.10: TX (header,
  whitening, Hamming, interleaving, Gray-map, chirp modulation) and RX
  (sync, CFO/STO estimation, demod, decode, CRC), SF5–12, validated against
  real RFM95 / SX1276 / SX1262 hardware. Run it on a USRP/HackRF/PlutoSDR to
  *transmit and receive genuine LoRa* — the reference for understanding what the
  Semtech correlator does internally.
- **[gr-lora](https://github.com/rpp0/gr-lora)** (Robyns/Bastille) — the earlier
  receive-oriented decoder, useful for RTL-SDR-class capture and teardown.

This is the bridge to the [`gnuradio-oot-modules`](../projects/gnuradio-oot-modules.md)
and [`rtl-sdr-lineage`](../projects/rtl-sdr-lineage.md) side of the catalog: a
$30 RTL-SDR + gr-lora_sdr will *demodulate* what these chips emit, closing the
loop between the Tier-1 transceiver and a Tier-5 SDR.

### 3.3 Flipper Zero & RfCat — direct-mode replay in your hand
The [Flipper Zero sub-GHz](../docs/walkthroughs/flipper-zero-cc1101-subghz.md) stack
is a CC1101 (300–348 / 387–464 / 779–928 MHz, 2-FSK & OOK/AM) driven in exactly
this transparent style: **Read**, **Read RAW** (captures the raw sub-carrier
timings for arbitrary/unknown OOK protocols), decode of common encoders
(Princeton, KeeLoq, etc.), and replay. RfCat/YARD Stick One (the catalogued
[`ti-cc1111-yardstick`](../projects/rtl-sdr-lineage.md)) does the same from a
Python REPL on a CC1111. Both are the canonical demonstration that a
"packet radio" in direct/async mode is a general OOK/FSK waveform player.

### 3.4 Bare-metal register control
For maximum control, skip libraries and drive SPI directly (or `SUBGHZSPI` on
STM32WL). Semtech, TI (SWRU346), and SiLabs all publish register/command maps;
the STM32WL reference manuals (RM0453/RM0461) document the embedded radio as a
memory-mapped peripheral. This is the route to non-standard preamble/sync
lengths, illegal-but-interesting deviation settings, and precise timing for
[cross-technology communication](../docs/cross-technology-communication.md).

---

## 4. Capability & tier summary

- **Tier 1 for the whole family.** Raw promiscuous receive (`monitor`) and
  arbitrary-frame transmit (`injection`) are universal; a direct/transparent
  bitstream mode (`covert-channel`, arbitrary keyed OOK/FSK) is available on
  every FSK part except where a closed module firmware hides it (RN2483,
  transparent-UART Ebyte builds).
- **No `raw-iq`, no `csi`, no `spectral-scan`, no true `arbitrary-waveform`.**
  There is no ADC/DAC tap and no editable PHY. "Continuous mode" gives a raw
  *bitstream*, not raw *IQ* — an important honesty line versus a real SDR. The
  closest thing to spectral awareness is per-channel RSSI polling.
- **`open-firmware` only for STM32WL**, because you own the MCU and the radio is
  register-documented; every other part interposes closed transceiver silicon
  (openness ranges `documented` → `partially-documented` → `closed`).
- **SX128x** adds cooperative **ToF ranging** (not radar) and BLE-PHY mimicry in
  2.4 GHz — its own small superpower.
- **Reproducing the PHY** on an actual SDR (gr-lora_sdr) is how you reach Tier 5
  behaviour with these waveforms; the chips themselves stay Tier 1.

---

## 5. Safety & regulatory notes (any TX)

Everything on this page can key a real transmitter. Before transmitting:

- **Licensing.** 433.05–434.79, 863–870 (EU SRD), 902–928 (US ISM), 315 MHz,
  and 2.4 GHz are license-exempt *only within* duty-cycle, bandwidth, channel,
  and EIRP limits set by your regulator (ETSI EN 300 220 / EN 300 440,
  FCC Part 15.231/15.247/15.249). CW tones and continuous direct-mode TX easily
  violate duty-cycle rules and can constitute illegal jamming.
- **Do not replay/forge live security devices.** Direct-mode capture+replay of
  garage doors, gates, car remotes, alarms, and utility meters is trivial with
  these parts and is illegal in most jurisdictions against equipment you do not
  own. Keep experiments to your own devices, on a bench, ideally into a dummy
  load or shielded enclosure.
- **PA front ends.** Ebyte/NiceRF "H"/PA modules can emit +20…+30 dBm — well
  above bare-chip limits; a mismatched or absent antenna at that power can
  damage the PA and radiate far beyond legal levels. Always terminate.
- **2.4 GHz coexistence.** SX128x/BLE-PHY experiments share the band with Wi-Fi
  and Bluetooth; sweep and CW modes can disrupt nearby links.

See [`../docs/verification-tier4.md`](../docs/verification-tier4.md) and
[`../docs/techniques.md`](../docs/techniques.md) for bench methodology and
attenuator/dummy-load setups.

---

## References

- Semtech SX1261/2 datasheet & *SX1261/2 Transceiver* reference — <https://www.semtech.com/products/wireless-rf/lora-connect/sx1262>
- Semtech SX1280/SX1281 (2.4 GHz LoRa + ranging) — <https://www.semtech.com/products/wireless-rf/lora-connect/sx1280>
- Semtech SX1276/77/78/79 datasheet — <https://www.semtech.com/products/wireless-rf/lora-connect/sx1276>
- Semtech LLCC68 datasheet — <https://www.semtech.com/products/wireless-rf/lora-connect/llcc68>
- ST STM32WLE5JC product page & RM0461 — <https://www.st.com/en/microcontrollers-microprocessors/stm32wle5jc.html>
- TI CC1200 datasheet & CC120x user's guide (SWRU346) — <https://www.ti.com/product/CC1200>
- Silicon Labs EZRadioPRO Sub-GHz ICs (Si446x / Si4438) — <https://www.silabs.com/wireless/proprietary/ezradiopro-sub-ghz-ics>
- HopeRF RFM95/96/97/98W & RFM69 modules — <https://www.hoperf.com/modules/lora/index.html>
- Microchip RN2483 command reference (DS40001784) — <https://www.microchip.com/en-us/product/RN2483>
- RadioLib (universal driver) — <https://github.com/jgromes/RadioLib>
- gr-lora_sdr (full LoRa PHY in GNU Radio, EPFL) — <https://github.com/tapparelj/gr-lora_sdr>
- gr-lora (RX decoder, Bastille) — <https://github.com/rpp0/gr-lora>
- Ebyte E-series module catalog — <https://www.ebyte.com/en/>

*Cross-links:* [`../docs/walkthroughs/flipper-zero-cc1101-subghz.md`](../docs/walkthroughs/flipper-zero-cc1101-subghz.md) ·
[`../projects/rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md) ·
[`../projects/gnuradio-oot-modules.md`](../projects/gnuradio-oot-modules.md) ·
[`../docs/cross-technology-communication.md`](../docs/cross-technology-communication.md) ·
[`../docs/true-sdr-comparison.md`](../docs/true-sdr-comparison.md)
