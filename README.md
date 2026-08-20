# Latent Radios

**An exhaustive, structured catalog of Wi‑Fi and wireless modules that can be repurposed as software‑defined radios — to some extent — by reverse‑engineering and patching their firmware, or by tapping the PHY telemetry the silicon already exposes.**

![modules](https://img.shields.io/badge/modules-361-brightgreen) ![vendors](https://img.shields.io/badge/vendors-52-blue) ![ladder](https://img.shields.io/badge/SDR%20ladder-tier%200--5-orange) ![license](https://img.shields.io/badge/license-CC0--1.0-lightgrey)

> Almost every Wi‑Fi chip is a fully programmable radio wearing a locked‑down costume. The RF front‑end, ADC/DAC, and a small MAC/PHY processor are all right there on the die — the vendor just hides them behind a signed firmware blob and a thin driver API. There is a **latent radio** in the silicon. This project maps, chip by chip, **how far each module can be pushed back toward a general radio**, and **what it takes to get there** (usually: dump the firmware, disassemble it, and patch it back into something you control).

This is not "turn a $5 dongle into a HackRF." Real Wi‑Fi silicon is band‑limited, its converters are tuned for OFDM, and most of the interesting DSP is frozen in ROM. But there is a surprisingly deep spectrum between *"stock driver"* and *"true SDR"* — monitor mode, frame injection, channel‑state information (CSI), spectral scan, raw‑PHY FFTs, and — on a few heroically reversed chips — arbitrary waveform transmit. This repo catalogs that whole spectrum.

**Catalog at a glance** — **361 modules across 52 vendors**, each scored on the SDR ladder: **207** reach monitor + injection (Tier 1), **35** expose CSI (Tier 2), **48** do spectral / raw‑PHY scan (Tier 3), **5** have demonstrated arbitrary‑waveform TX (Tier 4), and **19** are open‑firmware or true‑SDR references (Tier 5); a further **47** are catalogued as stock‑only (Tier 0 — the chip exists, but no public path off the ground floor yet). Full machine‑readable database: [data/modules.json](data/modules.json) · [modules.csv](data/modules.csv). *(These numbers grow every research cycle.)*

---

## The "SDR to some extent" ladder

Every entry is placed on a capability ladder. The higher the tier, the closer the chip is to a general‑purpose radio, and (almost always) the more firmware reverse‑engineering it took to get there. Full details in **[docs/taxonomy.md](docs/taxonomy.md)**.

| Tier | Name | What you get | Canonical example |
|------|------|--------------|-------------------|
| **0** | Black box | Stock association only; radio is opaque | Any locked mobile Wi‑Fi chip |
| **1** | Monitor + Inject | Raw 802.11 frame RX/TX, channel hopping, arbitrary frame crafting | `ath9k`, RTL8812AU |
| **2** | PHY telemetry (CSI) | Per‑subcarrier amplitude **and phase** — quasi‑IQ at OFDM‑subcarrier granularity | Intel 5300, ESP32, Nexmon CSI |
| **3** | Spectral / raw‑PHY scan | FFT bins / raw spectral samples across the channel | Atheros spectral scan, Nexmon |
| **4** | Arbitrary waveform | Baseband IQ you author, transmitted through the Wi‑Fi front‑end | Nexmon arbitrary‑TX demos (Broadcom D11) |
| **5** | Open PHY / soft‑radio | Documented or open firmware; PHY is yours | OpenFWWF/`b43`, and true SDRs for comparison |

The firmware‑reverse‑engineering thesis of this repo lives in **[docs/firmware-reversing.md](docs/firmware-reversing.md)**: the workflow of blob extraction → identifying the MAC/PHY core (Broadcom "D11" ucode, an ARM Cortex‑M/R, an Xtensa, an ARC…) → disassembly in Ghidra/IDA/radare2 → finding the RX/TX DMA rings and the PHY registers → patching new capabilities in.

---

## How the catalog is organized

```
chips/       One file per silicon vendor — every part number we can find,
             its SDR tier, firmware architecture, and RE status.
projects/    One file per tool/framework that unlocks these capabilities
             (Nexmon, the CSI toolchains, PicoScenes, spectral tools, …).
docs/        Cross‑cutting theory: the taxonomy, firmware‑RE methodology,
             techniques (CSI, passive radar, covert channels), glossary.
data/        Machine‑readable database (modules.json + modules.csv) with a
             JSON‑Schema (data/schema.json). This is the "exhaustive list."
scripts/     Validation + CSV generation for the database.
```

### Start here
- **New to the idea?** → [docs/taxonomy.md](docs/taxonomy.md), then [docs/firmware-reversing.md](docs/firmware-reversing.md)
- **Looking for a specific chip?** → the [`chips/`](chips/) directory or [`data/modules.json`](data/modules.json)
- **Want to buy the right hardware?** → [chips/hardware-index.md](chips/hardware-index.md) — product → chip → tier → what you can do
- **Want to *do* something today?** → [projects/](projects/) — most people start with **Nexmon** (Broadcom, incl. Raspberry Pi) or an **ESP32** for CSI.

### Hands‑on reverse‑engineering walkthroughs
Reproducible, end‑to‑end, with real repos and no fabricated offsets — start with Ghidra setup, then pick your silicon:
- [Setting up Ghidra for Wi‑Fi firmware](docs/walkthroughs/ghidra-setup-wifi-firmware.md) — the foundation the rest build on
- [Nexmon on a Raspberry Pi (BCM43455c0)](docs/walkthroughs/bcm43455c0-raspberry-pi.md) — monitor, injection, CSI
- [Reversing Broadcom D11 microcode](docs/walkthroughs/broadcom-d11-ucode.md) — b43‑tools + d11‑emu
- [ESP32 Xtensa firmware in Ghidra + CSI](docs/walkthroughs/esp32-xtensa-ghidra.md)
- [ath9k spectral scan + Atheros CSI Tool](docs/walkthroughs/atheros-ath9k-spectral-csi.md)
- [The Intel 5300 802.11n CSI Tool](docs/walkthroughs/intel-5300-csi.md)
- [RTL8812AU monitor + injection](docs/walkthroughs/rtl8812au-monitor-injection.md) — the reliable Alfa AWUS036ACH setup
- [MediaTek mt76: monitor, injection, CSI](docs/walkthroughs/mt76-monitor-injection-csi.md)
- [nRF52 as a bare radio + BLE sniffing](docs/walkthroughs/nrf52-dtm-radiotest-ble-sniffing.md) — the non‑Wi‑Fi repurpose
- [openwifi on a Zynq SDR](docs/walkthroughs/openwifi-zynq-bringup.md) — the genuinely open‑PHY path

**More deep‑dives:** [Nexmon](projects/nexmon.md) · [PicoScenes](projects/picoscenes.md) · [openwifi — open‑source 802.11 SDR](projects/openwifi.md) · [CSI toolchains](projects/csi-toolchains.md) · [sensing datasets](projects/wifi-sensing-datasets.md) · [techniques](docs/techniques.md) · [Wi‑Fi 7 / 6 GHz](docs/wifi7-and-6ghz.md) · [60 GHz mmWave radar](docs/mmwave-60ghz-radar.md) · [Wi‑Fi HaLow](docs/halow-subghz.md) · [UWB / FiRa ranging](docs/uwb-fira-ranging.md) · [cross‑technology comms](docs/cross-technology-communication.md) · [FTM / Wi‑Fi RTT](docs/ftm-rtt-ranging.md) · [Tier‑4 audit](docs/verification-tier4.md) · [Tier‑2 CSI audit](docs/verification-tier2-csi.md)

---

## Vendor coverage

| Vendor | File | Flagship SDR‑ish parts | Headline capability |
|--------|------|------------------------|---------------------|
| Broadcom / Cypress / Infineon | [chips/broadcom-cypress.md](chips/broadcom-cypress.md) | BCM4339, BCM43455c0, CYW43455 | Nexmon → CSI, spectral, arbitrary TX |
| Qualcomm Atheros | [chips/qualcomm-atheros.md](chips/qualcomm-atheros.md) | AR9280/9380, QCA9300 | Spectral scan, Atheros‑CSI |
| Intel | [chips/intel.md](chips/intel.md) | 5300, AX200/AX210 | 802.11n CSI Tool, AX‑CSI, PicoScenes |
| Realtek | [chips/realtek.md](chips/realtek.md) | RTL8812AU/8814AU, RTL8720 | Monitor/inject, some CSI |
| MediaTek / Ralink | [chips/mediatek-ralink.md](chips/mediatek-ralink.md) | MT7612U, MT7921 | Monitor/inject, mt76 CSI research |
| Espressif | [chips/espressif.md](chips/espressif.md) | ESP32, ESP32‑S3/C6 | Built‑in CSI, raw 802.11 TX |
| Everything else | [chips/other-vendors.md](chips/other-vendors.md) | TI, Marvell, Nordic, Silabs, Morse Micro, Quantenna… | varies |

> **This table (and every file it links) is designed to keep growing.** See [Roadmap & "never finished"](#roadmap--never-finished).

---

## What counts for inclusion

A module earns a place here if it can reach **Tier 1 or above** — i.e. it can do *something* a stock Wi‑Fi driver won't, that moves it toward a general radio. That deliberately includes:

- Wi‑Fi chips with monitor/injection, CSI, or spectral access (the core of the catalog).
- Combo Wi‑Fi/Bluetooth chips where either radio can be pushed.
- Non‑Wi‑Fi wireless modules that are routinely repurposed as bare radios (Nordic nRF with `RADIO` test mode, TI CC1101/CC13xx, Bluetooth sniffers like Ubertooth) — because the *technique* (reflash/reverse the firmware, expose the PHY) is identical, and they belong in the same toolbox.
- The RTL2832U / RTL‑SDR lineage is documented in [projects/rtl-sdr-lineage.md](projects/rtl-sdr-lineage.md) as the canonical "repurpose a consumer radio chip as an SDR" precedent — it is *not* Wi‑Fi, but it is the intellectual ancestor of everything here.

For comparison and calibration, genuine SDR platforms (RTL‑SDR, HackRF, bladeRF, LimeSDR, PlutoSDR, USRP) are summarized in [docs/true-sdr-comparison.md](docs/true-sdr-comparison.md) so you always know what "to some extent" is being measured against.

---

## The machine‑readable database

Everything in `chips/` is also encoded as structured data:

- **[data/modules.json](data/modules.json)** — the canonical database, validated against **[data/schema.json](data/schema.json)**.
- **[data/modules.csv](data/modules.csv)** — flattened for spreadsheets, generated by [scripts/build_csv.py](scripts/build_csv.py).

Each record carries: vendor, family, part numbers, 802.11/other standards, bands, **SDR tier**, capability flags, **firmware architecture + openness + RE tooling**, the projects that unlock it, common hardware you can buy, notes, and references.

---

## Roadmap & "never finished"

There is no last Wi‑Fi chip. This catalog is built to be extended forever:

- Each vendor file has an **`## Un‑cataloged / TODO`** section listing part numbers we know exist but haven't profiled yet.
- [docs/roadmap.md](docs/roadmap.md) tracks whole vendors and techniques still to be added.
- New silicon (Wi‑Fi 7 / 802.11be, Wi‑Fi HaLow / 802.11ah, UWB, the next reverse‑engineering write‑up) gets folded in as it appears.

Contributions and corrections are welcome — see **[CONTRIBUTING.md](CONTRIBUTING.md)** for the data schema and the one rule that matters: *cite your source.*

---

## Legal & ethical scope

The capabilities cataloged here are **dual‑use**. Monitor mode, frame injection, CSI‑based sensing, and firmware patching are the everyday tools of Wi‑Fi research, network defense, RF engineering, academic sensing, amateur radio, and repair — and, in the wrong hands, of abuse.

- **Transmitting** is regulated. Arbitrary‑waveform TX, out‑of‑band emissions, and even some injection can violate radio regulations (FCC/CE/etc.) and interfere with licensed services. Know your local rules; use a shielded enclosure / RF cage for TX experiments.
- **Sensing and capturing** other people's traffic or presence can be unlawful and unethical. Only operate on networks and in spaces you are authorized to.
- This repository is a **reference and research index**. It documents published work and public tooling; it is not an invitation to interfere with radios you don't own or aren't cleared to test.

Use it to understand your own hardware, defend your own networks, and do honest research.

---

*Cataloged with an eye toward completeness. If a chip can be a radio, it belongs here.*
