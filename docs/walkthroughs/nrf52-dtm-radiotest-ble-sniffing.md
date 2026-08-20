# The nRF52 as a Bare Radio: DTM / radiotest + BLE Sniffing

> The nRF52 is the archetypal *non-Wi-Fi* repurpose in this catalog, and it earns
> its place by being the opposite of a Wi-Fi chip in one crucial way: **there is
> no closed PHY firmware to fight.** Nordic ships the RADIO peripheral as a
> documented register machine — you get near-raw 2.4 GHz packet TX/RX by writing
> registers on a Cortex-M core you fully control. This walkthrough shows the three
> practical faces of that: (1) driving the RADIO peripheral directly for arbitrary
> on-air GFSK / proprietary packets, (2) using Nordic's **radiotest** and Bluetooth
> **Direct Test Mode (DTM)** firmware for raw carrier and test-packet TX (the
> regulatory/production path), and (3) flashing a BLE sniffer — Nordic's official
> **nRF Sniffer for Bluetooth LE** or NCC Group's **Sniffle** — to pull BLE
> advertising and connections into Wireshark.

This is a deliberate contrast to the Wi-Fi walkthroughs. There is no `nexmon`-style
firmware patch here, because there was never a locked firmware in the first place.
The "SDR" is handed to you at the datasheet level. The catch — and it is a real one
— is that this is a **packet radio, not a general SDR**: it modulates and demodulates
a fixed menu of 2.4 GHz PHYs. It cannot hand you raw IQ, and it cannot synthesize an
arbitrary waveform. On the [SDR ladder](../taxonomy.md) that makes it an honest
**Tier 1** part: monitor + injection within its modulation families, plus enough raw
register control to shape proprietary packets and abuse cross-protocol framing. See
the `nordic-nrf52` and `nordic-nrf24l01p` records in
[../../chips/other-vendors.md](../../chips/other-vendors.md), and the
[glossary](../glossary.md) for terms.

---

## 1. What you actually get (and what you don't)

The nRF52 series (nRF52810/11/20/32/33/40, and the newer nRF53/nRF54 with the same
lineage) pairs an Arm Cortex-M4F (M33 on 53/54) with a **2.4 GHz multi-protocol
RADIO peripheral**. Nordic publishes the full RADIO register map in the product
specification. That means you can:

| You can | You cannot |
|---|---|
| TX/RX BLE 1M, BLE 2M, BLE Coded (125k S8 / 500k S2) | Get raw baseband **IQ** samples off the chip |
| TX/RX Nordic proprietary **1 Mbit / 2 Mbit GFSK** (ESB / Gazell) | Synthesize an **arbitrary waveform** (no I/Q DAC) |
| TX/RX **IEEE 802.15.4** 250 kbit O-QPSK (nRF52840/nRF52833) | Demodulate a signal the RADIO's fixed PHYs don't cover |
| Set any **on-air address, whitening, CRC**, endianness, packet length | Do wideband capture / spectrum survey beyond a stepped RSSI sweep |
| Read per-packet **RSSI**, do a stepped **RSSI energy scan** | Receive Wi-Fi/OFDM, LoRa, or any non-2.4-GHz-narrowband signal |
| Emit a bare **unmodulated carrier** or modulated test packets (DTM/radiotest) | Beat a $30 RTL-SDR at being a receiver of *unknown* signals |
| Run **fully custom bare-metal firmware** on documented registers | |

The single most important honesty check: **the RADIO is a packet engine.** It has a
GFSK/O-QPSK modem hard-wired in silicon. "Arbitrary on-air" here means *arbitrary
bytes through a fixed modulator* — you choose the address, the whitening, the CRC and
the payload, and you can therefore impersonate an nRF24 device, a BLE advertiser, or
a proprietary 2.4 GHz protocol. It does **not** mean arbitrary I/Q like a
[true SDR](../true-sdr-comparison.md). That is the whole reason this maps to Tier 1
and not Tier 4/5.

### The RADIO peripheral, concretely

The near-raw control surface is a handful of registers (names from the nRF52840
product specification):

| Register | Role |
|---|---|
| `FREQUENCY` | On-air frequency. `2400 + FREQUENCY` MHz (0–100), or with `MAP=Low`, `2360 + FREQUENCY` MHz → **usable span 2360–2500 MHz** |
| `MODE` | Modulation/PHY: `Nrf_1Mbit`, `Nrf_2Mbit`, `Ble_1Mbit`, `Ble_2Mbit`, `Ble_LR125Kbit`, `Ble_LR500Kbit`, `Ieee802154_250Kbit` |
| `PCNF0` / `PCNF1` | Packet format: `LFLEN`/`S0LEN`/`S1LEN` (header field widths), `MAXLEN`/`STATLEN`, `BALEN` (base-address length), `ENDIAN`, `WHITEEN` (data whitening enable) |
| `BASE0/BASE1`, `PREFIX0/PREFIX1`, `TXADDRESS`, `RXADDRESSES` | The 8 logical addresses (the "MAC" the modem matches on) |
| `CRCCNF`, `CRCPOLY`, `CRCINIT` | CRC length, polynomial and seed |
| `DATAWHITEIV` | Whitening IV (BLE uses channel index; you can set it to anything) |
| `TASKS_TXEN/RXEN/START/STOP/DISABLE`, `EVENTS_READY/ADDRESS/PAYLOAD/END/CRCOK` | The TX/RX state machine, driven by tasks/events (and `SHORTS` for zero-CPU chaining) |
| `RSSISAMPLE` + `TASKS_RSSISTART` | Single-shot RSSI of the current channel |

Because whitening, CRC and address matching are all programmable, the RADIO is a
*superset* of the fixed-function nRF24L01+ — which is exactly why nRF52 boards are
the standard tool for sniffing and spoofing legacy ShockBurst/ESB devices
(wireless mice/keyboards, drones, toys). That cross-protocol reach is the
`covert-channel` capability in practice.

---

## 2. Hardware to buy

Any nRF52 board with a debug/DFU path works. The community-standard cheap tools:

| Board | Part | Why |
|---|---|---|
| **nRF52840 Dongle (PCA10059)** | nRF52840 | ~$10, USB-A, onboard USB bootloader (no debugger needed), the default sniffer target. Supports BLE + 802.15.4 |
| **nRF52840 DK (PCA10056)** | nRF52840 | Onboard J-Link (SEGGER), best for bare-metal RADIO dev + DTM over the DK's UART |
| **nRF52833 DK (PCA10100)** | nRF52833 | BLE + 802.15.4; same tooling |
| **nRF52 DK (PCA10040)** | nRF52832 | BLE + proprietary only (no 802.15.4 radio); classic |
| BBC **micro:bit v2** | nRF52833 | Ubiquitous, cheap, USB — great for RADIO experiments |
| Adafruit Feather nRF52840 / Seeed XIAO nRF52840 | nRF52840 | UF2 bootloader, hobby-friendly |

For a **debugger-less** path use a Dongle (PCA10059) — it enumerates as a USB DFU
target and is flashed by the nRF Connect Programmer app or `nrfutil`. For bare-metal
RADIO work and DTM you want the DK's onboard J-Link (or a standalone J-Link / a
`pyocd`-supported CMSIS-DAP probe) so you can `nrfjprog`/reset/debug freely.

Toolchain once, for everything below:

```bash
# Nordic command-line tools (nrfjprog, mergehex) + J-Link
#   https://www.nordicsemi.com/Products/Development-tools/nRF-Command-Line-Tools
# Modern replacement CLI (device programming, DFU, etc.):
#   pip install nrfutil   # then: nrfutil install device
# For building bare-metal / NCS samples:
#   nRF Connect SDK (Zephyr-based) via nRF Connect for VS Code, or west
```

> Cross-reference: [../../chips/hardware-index.md](../../chips/hardware-index.md) for
> probe/adapter notes shared across the catalog.

---

## 3. Path A — Driving the RADIO peripheral directly (raw packets)

This is the "expose the PHY" move. You write a tiny bare-metal firmware that puts the
RADIO in a chosen `MODE`, sets `FREQUENCY`, configures `PCNF0/PCNF1`, addresses, CRC
and whitening, points `PACKETPTR` at a buffer, and toggles `TASKS_TXEN`/`TASKS_START`.
No SoftDevice, no stack — just the register machine.

The lowest-friction way to *reach* these registers without writing a driver from
scratch is one of:

- **NCS `radio_test` sample** (see Path B) — gives you a UART shell over the RADIO.
- **Proprietary ESB library** (`esb_prx`/`esb_ptx` samples in NCS) — Nordic's
  Enhanced ShockBurst on top of the RADIO: acknowledged, addressed 2.4 GHz packets,
  the direct descendant of the nRF24L01+ protocol. This is the sanctioned "arbitrary
  proprietary packet" API.
- A **from-scratch register poke** for full control (address, whitening off, custom
  CRC) when you want to sniff/spoof a *foreign* protocol.

Minimal illustration of the register sequence for a proprietary 2 Mbit TX (pseudocode,
CMSIS names — real code adds ramp-up/short handling and the DK's clock setup):

```c
NRF_RADIO->FREQUENCY = 2;                 // 2402 MHz (BLE adv ch37-ish region)
NRF_RADIO->MODE      = RADIO_MODE_MODE_Nrf_2Mbit;
NRF_RADIO->PCNF0     = (8 << RADIO_PCNF0_LFLEN_Pos);          // 8-bit length field
NRF_RADIO->PCNF1     = (32 << RADIO_PCNF1_MAXLEN_Pos)
                     | (4  << RADIO_PCNF1_BALEN_Pos)          // 5-byte address
                     | (RADIO_PCNF1_WHITEEN_Disabled << RADIO_PCNF1_WHITEEN_Pos);
NRF_RADIO->BASE0     = 0xDEADBEEF;         // your on-air address
NRF_RADIO->PREFIX0   = 0xC4;
NRF_RADIO->TXADDRESS = 0;
NRF_RADIO->CRCCNF    = 2;                  // 2-byte CRC
NRF_RADIO->CRCPOLY   = 0x11021;
NRF_RADIO->CRCINIT   = 0xFFFF;
NRF_RADIO->PACKETPTR = (uint32_t)&packet;  // [len][payload...]
NRF_RADIO->EVENTS_END = 0;
NRF_RADIO->TASKS_TXEN = 1;                 // ramp up + auto-START via SHORTS
```

The point of showing this is not the exact constants — it is that **every field a
receiver keys on (frequency, address, whitening, CRC) is yours to set.** That is what
makes the nRF52 a *bare radio* rather than a BLE-only widget, and it is the same
"reverse-and-expose-the-PHY" spirit as the Wi-Fi chips, minus the reversing.

**Capability mapping:** `monitor` + `injection` for the PHYs the modem supports;
`covert-channel` for cross-protocol address/whitening abuse; `open-firmware` because
the whole thing runs your documented-register code. Not `raw-iq`, not
`arbitrary-waveform`.

---

## 4. Path B — radiotest & DTM (raw carrier / test-packet TX)

> **Regulatory / safety notice — read before any TX.** Everything in this section
> keys the transmitter. The 2.4 GHz ISM band is shared and licence-exempt, but a
> **constant unmodulated carrier** is not a normal ISM emission — it is a jammer.
> Emit test carriers only into a **shielded enclosure, a dummy load, or a conducted
> setup**, at the lowest usable power, never over the air where you can interfere with
> Wi-Fi/BLE/medical/other users. DTM and radiotest exist for **certification and
> production test**, i.e. lab conditions. Respect your local limits (FCC Part 15 /
> ETSI EN 300 328). When in doubt, cable it into a spectrum analyzer, don't radiate.

### radiotest (Nordic proprietary test firmware)

`radio_test` is a Nordic sample (in the nRF Connect SDK, `samples/peripheral/radio_test`;
the classic nRF5 SDK had an equivalent). It presents a **UART shell** that drives the
RADIO peripheral for RF performance and regulatory testing across every PHY the chip
supports. Build/flash it with `west build -b nrf52840dk/nrf52840` (or your board) and
open the DK's UART at 115200. Core commands:

| Command | Effect |
|---|---|
| `start_tx_carrier` | Emit a **constant, unmodulated carrier** at the set channel (frequency-accuracy / occupied-bandwidth tests, and the classic "is my antenna radiating" check) |
| `start_tx_modulated_carrier [N]` | TX modulated test packets (optionally a fixed count `N`) |
| `start_duty_cycle_modulated_tx <pct>` | Modulated TX at a controlled 1–90% duty cycle |
| `output_power <dBm>` | Set SoC TX power |
| `transmit_pattern <...>` | Choose payload pattern (0x0F, 0x55, PRBS9, …) |
| `start_rx` | Continuous (or packet-limited) RX; pair with `print_rx` to dump payloads |
| `start_rx_sweep` / `start_tx_sweep` | Sweep RX/TX across a channel range — a crude stepped spectrum/energy scan |
| `cancel` | Stop the active carrier/sweep |
| `data_rate` / `parameters` | Select `nRF 1M/2M`, `BLE 1M/2M`, `BLE LR 125k(S8)/500k(S2)`, `802.15.4 250k` |
| `fem`, `toggle_dcdc_state` | Front-end-module and DC/DC controls |

`start_tx_carrier` is the important one for this catalog: it is the most "SDR-like"
thing the part does — a bare tone you place anywhere in 2360–2500 MHz. It is still not
arbitrary-waveform (no modulation control beyond the fixed modem), but it is a
programmable CW source, which is genuinely useful for antenna/range testing and as a
lab beacon.

### DTM (Bluetooth Direct Test Mode)

DTM is the **Bluetooth-SIG-standardized** RF PHY test mode (Core Spec Vol 6, Part F).
Where radiotest is Nordic-proprietary and driven by a friendly shell, DTM speaks the
**2-wire UART test protocol** (or HCI-over-UART) that Bluetooth test equipment
(Anritsu/R&S/LitePoint testers) expects. Nordic ships a `direct_test_mode` sample
(NCS) / `ble_app_dtm` (legacy nRF5 SDK). It implements the standard test procedures:

- **`LE Transmitter Test`** — TX a stream of reference test packets (or a carrier /
  constant tone via the vendor-specific carrier command) at a chosen channel, packet
  length and payload pattern.
- **`LE Receiver Test`** — RX test packets and count them (PER measurement).
- **`LE Test End`** — stop, return the received-packet count.
- PHYs: **LE 1M, LE 2M, LE Coded**.

Use DTM when you need **spec-conformant, tester-compatible** behavior (certification,
regulatory submissions, incoming-inspection PER tests). Use radiotest when you just
want convenient RF control from a serial terminal. Both are Tier-1-class capabilities:
they let you *drive the transmitter and count the receiver*, not sample the air.

---

## 5. Path C — BLE sniffing into Wireshark

Two mature options. Pick by hardware and by whether you need robustness on BT5
(extended advertising / Coded PHY / connection following).

### C1. Nordic nRF Sniffer for Bluetooth LE (the Nordic-native path)

Nordic's **official**, free, closed-but-supported sniffer firmware + a Wireshark
`extcap` plugin. This is the right first choice on any nRF52 board because it is
maintained and Nordic-supported.

1. **Download** the "nRF Sniffer for Bluetooth LE" package from Nordic
   (`nordicsemi.com` → nRF Sniffer for Bluetooth LE). It contains the firmware
   `.hex` images (per board) and the `extcap` Python plugin (`nrf_sniffer_ble.py`).
2. **Flash** the matching `.hex`:
   - Dongle (PCA10059): open the **nRF Connect for Desktop → Programmer** app, or use
     `nrfutil`/`nrfjprog`.
   - DK: `nrfjprog --program hci_sniffer_..._pca10056.hex --chiperase -r`
3. **Install the extcap plugin** into Wireshark's `extcap` directory (find it via
   *Help → About Wireshark → Folders → Extcap path*), install the plugin's Python
   deps (`pip install pyserial`), and restart Wireshark.
4. In Wireshark you now see an **"nRF Sniffer for Bluetooth LE"** capture interface.
   Start it, then use the **sniffer toolbar** (View → Interface Toolbars) to pick a
   device to follow from the live advertiser list.

What it does: captures advertising on the three primary advertising channels, then
**follows one selected device into its connection**, decoding link-layer packets. It
can decrypt a connection if you supply the pairing key / passkey / OOB / an LTK.

Limitations (be honest with yourself): **passive only** (no injection), **follows one
device / one connection at a time**, can *miss* packets (a single radio can't be on
all channels at once), and its extended-advertising / Coded-PHY robustness is weaker
than Sniffle's. Perfect for "what is this beacon advertising" and for debugging your
own peripheral's connection; not a comprehensive multi-link capture rig.

### C2. Sniffle (NCC Group) — the robust BT5 sniffer

**Sniffle** (Sultan Qasim Khan / NCC Group) is the strongest open BLE sniffer for
**BT5** features: it does BT5 Channel Selection Algorithms #1 & #2, all PHYs
(1M/2M/Coded long-range), **extended advertising with `AuxPtr` following**,
single-sniffer multi-advertising-channel capture (~3× reliability), MAC/RSSI
filtering, IRK-based RPA resolution, PCAP export and a Wireshark extcap plugin.

**Important accuracy note on hardware:** Sniffle *began* life on the **nRF52840**
(that was its original and only platform), but NCC Group later migrated the firmware
to **TI's CC1352/CC2652** family, and the **current releases (the 2024–2025 v1.5–v1.11
line) are TI-only** — the README's supported-hardware list is entirely TI Launchpads,
the SONOFF CC2652P dongle, and the Electronic Cats CatSniffer. To run Sniffle on an
**nRF52840 dongle today you must check out one of the older, pre-migration tagged
releases** from the repo's history (the last nRF-capable versions); the modern
firmware will not build for nRF. If you specifically want a *current, supported* sniffer
**on nRF52 hardware**, use **nRF Sniffer (C1)**; if you want Sniffle's superior BT5
capture, the path of least resistance in 2026 is a **~$10 SONOFF CC2652P dongle**.

Sniffle usage (host side is identical regardless of the flashed board):

```bash
git clone https://github.com/nccgroup/Sniffle
cd Sniffle/python_cli

# Install the Wireshark extcap plugin (POSIX):
mkdir -p ~/.local/lib/wireshark/extcap
ln -s "$(pwd)/sniffle_extcap.py" ~/.local/lib/wireshark/extcap/

# CLI capture: advertising channel 38, RSSI floor -50, all adv channels, to PCAP
./sniff_receiver.py -c 38 -r -50 -a -o capture.pcap

# Follow a specific device by MAC, extended adv + long-range PHY
./sniff_receiver.py -m 12:34:56:78:9A:BC -le -a -o dev.pcap
```

Flashing the firmware (current TI path, SONOFF dongle example):

```bash
# from the fw/ dir, using the prebuilt or freshly built hex + the TI serial bootloader
python3 cc2538-bsl.py -p /dev/ttyUSB0 --bootloader-sonoff-usb -ewv \
        sniffle_cc1352p1_cc2652p1.hex
```

(For the legacy nRF52840 build, check out an older Sniffle tag and flash its
`sniffle.hex` with `nrfjprog --program sniffle.hex --chiperase -r`.)

---

## 6. Where this sits on the ladder

| Question | Answer |
|---|---|
| **Tier?** | **Tier 1.** Raw *packet* TX/RX with monitor + injection across a fixed menu of 2.4 GHz PHYs, plus a programmable CW carrier via DTM/radiotest. |
| **Capabilities** | `monitor`, `injection`, `covert-channel` (cross-protocol address/whitening spoofing), `open-firmware` (documented registers, fully custom bare-metal). |
| **Explicitly NOT** | `raw-iq` (no baseband samples off-chip), `arbitrary-waveform` (fixed GFSK/O-QPSK modem — the carrier is CW, not an I/Q DAC), `csi`, `spectral-scan` (only a crude stepped-RSSI sweep), `radar`/`fmcw`. |
| **Firmware openness** | **documented** — SoftDevice is closed, but the RADIO peripheral is fully documented and you run your own bare-metal code. |

### Limits vs a real SDR

A [true SDR](../true-sdr-comparison.md) (RTL-SDR, HackRF, USRP, PlutoSDR) digitizes a
**band** of spectrum into I/Q and lets software be the modem — so it can receive
*unknown* signals, demodulate anything within its bandwidth, and (on TX-capable SDRs)
synthesize *any* waveform. The nRF52 does none of that. It has a hard-wired modem: it
can only speak the specific 2.4 GHz PHYs Nordic built into it, and it can only *emit*
those modulations plus a bare tone. You will never do a spectrum survey, capture LoRa,
or transmit an arbitrary constellation with it.

What it gives you *instead* — and why it's in this catalog — is **near-raw, low-latency
control of a real 2.4 GHz packet radio for under $15**, with a documented register map
and no firmware to reverse. For BLE/ESB/802.15.4 work — sniffing, fuzzing, spoofing,
range/PER testing, protocol emulation — that is often more useful than a general SDR,
because you get the modem *for free* and only have to think about packets. It is the
purest example of this project's second population: **a bare radio whose PHY was never
hidden.**

---

## 7. References (primary sources)

- Nordic **nRF52840 Product Specification — RADIO peripheral** (register map, MODE/
  FREQUENCY/PCNF/CRC/whitening/RSSI):
  https://docs.nordicsemi.com/bundle/ps_nrf52840/page/radio.html
- Nordic **radio_test** sample (nRF Connect SDK):
  https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples/peripheral/radio_test/README.html
- Nordic **Direct Test Mode (DTM)** sample:
  https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples/bluetooth/direct_test_mode/README.html
- Nordic **Enhanced ShockBurst (ESB)** protocol / samples:
  https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/esb/index.html
- Nordic **nRF Sniffer for Bluetooth LE** (firmware + Wireshark extcap):
  https://www.nordicsemi.com/Products/Development-tools/nRF-Sniffer-for-Bluetooth-LE
- Nordic **nRF Sniffer for 802.15.4** (Thread/Zigbee capture):
  https://github.com/NordicSemiconductor/nRF-Sniffer-for-802.15.4
- **Sniffle** (NCC Group / Sultan Qasim Khan) — repo, README, releases:
  https://github.com/nccgroup/Sniffle
- Nordic **nRF Command Line Tools** (`nrfjprog`) / **nrfutil**:
  https://www.nordicsemi.com/Products/Development-tools/nRF-Command-Line-Tools
- Bluetooth Core Specification, **Vol 6, Part F — Direct Test Mode**:
  https://www.bluetooth.com/specifications/specs/core-specification/

---

*See also:* [../../chips/other-vendors.md](../../chips/other-vendors.md) (the
`nordic-nrf52` and `nordic-nrf24l01p` records) ·
[../true-sdr-comparison.md](../true-sdr-comparison.md) ·
[../taxonomy.md](../taxonomy.md) · [../glossary.md](../glossary.md)
