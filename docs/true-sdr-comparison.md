# The True-SDR Yardstick

Every entry in *Latent Radios* rates a Wi-Fi/wireless chip on the [SDR ladder](./taxonomy.md) — a 0-to-5 measure of how much of a *real* software-defined radio you can coax out of silicon that was never sold as one. That phrase, **"an SDR to some extent,"** is only meaningful if you know what the *full* extent looks like. This document is the reference edge of the ruler: the purpose-built SDR platforms that a repurposed Wi-Fi chip is implicitly compared against.

A "true" SDR digitizes (and usually synthesizes) a slab of **raw IQ** — the complex baseband stream — and hands it to the host with the PHY layer left entirely to software. That is ladder **tier 5** (`raw-iq` + `arbitrary-waveform` + open control of the front-end) by construction. No unlocked Wi-Fi part reaches that today; the best climb to tier 3-4 in narrow, ISM-locked ways. Understanding *why* the gap exists — and the two dimensions where cheap Wi-Fi silicon shockingly *wins* — is the point of the catalog.

> **How to read the tiers here.** Genuine SDRs sit *above* the ladder: they are the tier-5 datum, not contestants on it. We still tag them tier 5 in the records below so the comparison table sorts cleanly, but the ladder was designed to grade *non-SDR* silicon reaching *upward*. See [../projects/rtl-sdr-lineage.md](../projects/rtl-sdr-lineage.md) for how the cheapest of these — the RTL2832U — accidentally created the hobbyist SDR era, and [taxonomy.md](./taxonomy.md) for the ladder definition.

---

## The reference platforms

### Receive-only, budget tier

**RTL-SDR (RTL2832U + R820T2 / R828D).** The archetype of "accidental SDR." A DVB-T/DAB demodulator whose debug/FM mode streams 8-bit IQ over USB 2.0. ~500 kHz–1.7 GHz (with HF up-conversion on the Blog V4), ~2.4 MHz alias-free bandwidth (3.2 MHz max, unstable), **RX only**, 8-bit. ~US$40. It is the *floor* of true-SDR performance — and yet an unlocked Wi-Fi chip in CSI mode delivers finer per-subcarrier phase resolution across a wider instantaneous band than this dongle can dream of. That contrast is the thesis of the whole project. Full lineage: [../projects/rtl-sdr-lineage.md](../projects/rtl-sdr-lineage.md).

**Airspy (R2 / Mini / HF+ Discovery).** A step up in ADC quality. The R2 and Mini use the R820T2 front-end feeding a real 12-bit ADC (10 MSPS / 6 MSPS) over 24–1800 MHz — clean, oversampled, RX only. The **HF+ Discovery** is a different beast: a polyphase-harmonic-rejection HF/VHF receiver (0.5 kHz–31 MHz, 60–260 MHz) with exceptional dynamic range (~110+ dB) but only ~768 kHz of alias-free bandwidth. Airspy exists to show that "true SDR" is not one number — dynamic range and bandwidth trade off. ~US$100–170.

**SDRplay (RSP1A / RSPdx-R2).** 14-bit ADCs, 1 kHz–2 GHz continuous, up to 10 MHz bandwidth, RX only, with front-end preselection filters the RTL-SDR lacks. The RSPdx-R2 adds an HDR mode below 2 MHz. These are the "serious listener" receivers — the closest RX-only comparison to what a Wi-Fi chip's *spectral-scan* mode (ladder tier 3) crudely imitates inside the ISM bands. ~US$120–290.

### Transmit-capable, half-duplex

**HackRF One.** The reference *wide-tuning, TX-capable* hacker SDR. 1 MHz–6 GHz, 20 MHz instantaneous bandwidth, **8-bit** ADC/DAC, **half-duplex** (cannot RX and TX at once), open hardware + open firmware (LPC43xx Cortex-M4). Its 8-bit depth and half-duplex limit are exactly the compromises you accept for 6 GHz of tuning and arbitrary TX. This is the canonical "author an IQ buffer and blast it" board — ladder tier 4+5 in one device. ~US$300 (genuine Great Scott Gadgets).

### Transmit-capable, full-duplex, mid tier

**ADALM-PLUTO (PlutoSDR).** Analog Devices AD9363 "RF agile transceiver" + Zynq-7010 SoC. 325 MHz–3.8 GHz (widely hacked to ~70 MHz–6 GHz by re-flagging the chip as an AD9364), 12-bit, up to 20 MHz bandwidth, **full-duplex** 1×1 TX/RX. ~US$150-230. The best price/performance entry into full-duplex transceiver SDR, and the platform most Wi-Fi-sensing researchers reach for when they outgrow CSI extraction.

**LimeSDR / LimeSDR Mini.** Lime Microsystems LMS7002M field-programmable RF. Full LimeSDR: 100 kHz–3.8 GHz, 61.44 MSPS, 12-bit, **2×2 MIMO full-duplex**, USB 3.0. Mini: 10 MHz–3.5 GHz, 30.72 MSPS, 12-bit, 1×1, USB 3.0. The LMS7002M is itself a *programmable* transceiver, making Lime a favorite for open-source cellular (srsRAN/Osmocom). ~US$180 (Mini) / ~US$300+ (full).

**bladeRF 2.0 micro (xA4 / xA9).** Nuand's AD9361-based board. 47 MHz–6 GHz, up to **56 MHz** bandwidth, 12-bit, **2×2 MIMO full-duplex**, USB 3.0. The xA4 (Cyclone V 49k LE) and xA9 (301k LE) differ only in on-board FPGA size — meaning user DSP/PHY can run *on the board*. ~US$540 (xA4) / ~US$780 (xA9).

### Professional / lab tier

**Ettus USRP (B200/B210, N210, N310).** The research standard. **B200/B210** (AD9364/AD9361): 70 MHz–6 GHz, 56 MHz bandwidth, 12-bit, USB 3.0, B210 is 2×2 full-duplex. **N210**: modular daughterboard front-ends, 100 MS/s 14-bit ADC, ~50 MHz BW, Gigabit Ethernet. **N310**: 4×4, 10 MHz–6 GHz, up to 100 MHz/channel, 14-bit, 10 GbE, embedded ARM + large FPGA for standalone PHY. First-class UHD/GNU Radio support. ~US$1,200 (B200) to US$10,000+ (N310). This is the far end of the yardstick — what "the PHY is entirely yours, at instrument grade" costs.

---

## Comparison table

| Platform | Front-end | Freq range | Instant. BW | TX? | Full-duplex? | Resolution | Approx price | Link |
|---|---|---|---|---|---|---|---|---|
| RTL-SDR Blog V4 | R828D + RTL2832U | ~0.5 kHz–1.7 GHz | ~2.4 MHz | No | — | 8-bit | ~$40 | [rtl-sdr.com](https://www.rtl-sdr.com/) |
| Airspy R2 | R820T2 | 24–1800 MHz | ~9 MHz | No | — | 12-bit | ~$170 | [airspy.com](https://airspy.com/) |
| Airspy Mini | R820T2 | 24–1800 MHz | ~6 MHz | No | — | 12-bit | ~$100 | [airspy.com](https://airspy.com/) |
| Airspy HF+ Discovery | polyphase HR | 0.5 kHz–31 MHz, 60–260 MHz | ~0.77 MHz | No | — | high-DR (~18-bit eff.) | ~$170 | [airspy.com](https://airspy.com/airspy-hf-discovery/) |
| SDRplay RSP1A | Mirics tuner | 1 kHz–2 GHz | up to 10 MHz | No | — | 14-bit | ~$120 | [sdrplay.com](https://www.sdrplay.com/rsp1a/) |
| SDRplay RSPdx-R2 | Mirics tuner | 1 kHz–2 GHz | up to 10 MHz | No | — | 14-bit | ~$290 | [sdrplay.com](https://www.sdrplay.com/rspdx/) |
| HackRF One | MAX2837 + MAX5864 | 1 MHz–6 GHz | 20 MHz | Yes | No (half) | 8-bit | ~$300 | [greatscottgadgets.com](https://greatscottgadgets.com/hackrf/) |
| ADALM-PLUTO | AD9363 (→AD9364) | 325 MHz–3.8 GHz (hack: 70–6000) | up to 20 MHz | Yes | Yes (1×1) | 12-bit | ~$150–230 | [wiki.analog.com](https://wiki.analog.com/university/tools/pluto) |
| LimeSDR Mini | LMS7002M | 10 MHz–3.5 GHz | up to 30.72 MHz | Yes | Yes (1×1) | 12-bit | ~$180 | [limemicro.com](https://limemicro.com/) |
| LimeSDR (full) | LMS7002M | 100 kHz–3.8 GHz | up to 61.44 MHz | Yes | Yes (2×2) | 12-bit | ~$300+ | [limemicro.com](https://limemicro.com/) |
| bladeRF 2.0 xA4 | AD9361 | 47 MHz–6 GHz | up to 56 MHz | Yes | Yes (2×2) | 12-bit | ~$540 | [nuand.com](https://www.nuand.com/bladerf-2-0-micro/) |
| bladeRF 2.0 xA9 | AD9361 | 47 MHz–6 GHz | up to 56 MHz | Yes | Yes (2×2) | 12-bit | ~$780 | [nuand.com](https://www.nuand.com/product/bladerf-xa9/) |
| USRP B200 | AD9364 | 70 MHz–6 GHz | 56 MHz | Yes | Yes (1×1) | 12-bit | ~$1,200 | [ettus.com](https://www.ettus.com/all-products/ub200-kit/) |
| USRP B210 | AD9361 | 70 MHz–6 GHz | 56 MHz | Yes | Yes (2×2) | 12-bit | ~$1,700 | [ettus.com](https://www.ettus.com/all-products/ub210-kit/) |
| USRP N210 | daughterboards | DC–6 GHz (board-dep.) | ~50 MHz | Yes | Yes | 14-bit | ~$1,700+ | [ettus.com](https://kb.ettus.com/) |
| USRP N310 | AD9371 | 10 MHz–6 GHz | 100 MHz/ch | Yes | Yes (4×4) | 14-bit | ~$10,000+ | [ettus.com](https://kb.ettus.com/) |

*Prices are ballpark 2026 street prices for genuine units and move with supply; treat them as order-of-magnitude.*

---

## Where unlocked Wi-Fi chips FALL SHORT

An unlocked Wi-Fi chip is not a general-purpose SDR, and the gaps are structural, not incidental:

- **Tuning is nailed to the ISM/UNII bands.** The RF front-end, PLL, and filters are laid out for 2.4/5/6 GHz Wi-Fi (or 60 GHz for 802.11ad). You cannot tune to 100 MHz FM, 400 MHz LMR, or 1090 MHz ADS-B the way any $40 RTL-SDR can. A true SDR's continuous multi-GHz coverage is simply absent.
- **You rarely get true raw IQ.** The chip hands you *processed* PHY products — decoded frames (tier 1), CSI matrices (tier 2), or FFT/spectral bins (tier 3) — not an unshaped baseband stream. The DSP pipeline is baked into closed D11 ucode / Xtensa / ARC firmware; you tap it, you don't own it. Reaching even *near*-raw output means reverse-engineering that firmware — see [../docs/firmware-reversing.md](./firmware-reversing.md).
- **Modest, quantized instantaneous bandwidth.** You get 20/40/80/160 MHz *Wi-Fi channel* widths, not a freely chosen capture width, and CSI is sampled only on the ~52–2000 populated OFDM subcarriers, not as a flat wideband spectrum.
- **Low TX dynamic range and no arbitrary waveform (mostly).** Where TX injection exists (tier 1) it emits *802.11 frames*, not an author-your-own IQ buffer. Genuine arbitrary-waveform TX (tier 4) is rare, ISM-locked, and power/linearity-limited — nothing like a HackRF or Pluto driving a clean 20 MHz signal anywhere from 1 MHz to 6 GHz.
- **Coarse amplitude calibration.** AGC, per-subcarrier gain, and phase offsets are uncalibrated and drift; sensing work spends real effort sanitizing CSI before it is usable — a problem instrument-grade USRPs largely don't have.

The blunt summary: for *generic* "receive/transmit an arbitrary signal at an arbitrary frequency," a $40 RTL-SDR or $150 Pluto beats every Wi-Fi chip in this catalog. See [true-sdr-comparison](./true-sdr-comparison.md) framing throughout the [taxonomy](./taxonomy.md).

## Where they SURPRISINGLY COMPETE

And yet — measured on the axes that *matter for RF sensing and pervasive radio*, unlocked Wi-Fi silicon does things no affordable true SDR does:

- **CSI subcarrier density, for free, at real Wi-Fi bandwidth.** A modern chip natively estimates the complex channel on **up to ~2000 subcarriers across a 160 MHz band** (802.11ac/ax), every packet, in hardware. Reproducing that with a USRP means building an OFDM channel estimator in GNU Radio and paying for the instrument. For Doppler/respiration/gesture/localization sensing, dense native CSI is often *better* raw material than a bare IQ stream. See [../projects/csi-toolchains.md](../projects/csi-toolchains.md).
- **Near-zero marginal cost and total ubiquity.** The radio is *already there* — in every laptop, phone, router, and IoT node on Earth. A CSI or monitor-mode capability turns billions of deployed devices into sensors/receivers at **$0 hardware cost**. No SDR platform can match "already installed in a device the target already owns."
- **Native operation at multi-hundred-MHz Wi-Fi bandwidths and 60 GHz.** 802.11ax runs 160 MHz channels; 802.11ad/ay run **~2 GHz-wide channels at 60 GHz** with steerable phased arrays — territory where even a bladeRF or B210 (56 MHz) falls short and only a >$10k N310-class rig or specialized mmWave gear competes. An unlocked 60 GHz Wi-Fi chip is, in bandwidth terms, playing in the professional league.
- **Integrated antenna arrays and beamforming.** MIMO Wi-Fi parts carry 2–8 calibrated-ish chains and hardware beamforming — MIMO capability that costs thousands in USRP form.
- **Tight timing and packet synchronization built in.** The MAC gives you hardware timestamps and per-packet triggers that a bare SDR must reconstruct in software.

**The verdict the catalog is built on:** a repurposed Wi-Fi chip is a *terrible* general-purpose SDR and a *superb, absurdly cheap, ubiquitous* channel-sounder / passive-radar / sensing front-end within its home bands. "An SDR to some extent" means exactly this — climb the [ladder](./taxonomy.md) far enough on the right chip and you get tier-2/3 sensing capability that, on the sensing axis alone, embarrasses hardware costing 100× more.

---

## Un-cataloged / TODO

*(true-SDR platforms noted for completeness but out of primary scope — a fuller yardstick could profile these)*

- **XTRX** (Fairwaves) — LMS7002M in mini-PCIe form, embeddable full-duplex SDR.
- **PicoSDR / Epiq Sidekiq** — module-format AD936x SDRs for embedded/SWaP-constrained use.
- **USRP X310 / X410 / E320** — higher-end Ettus (X410: 1–7.2 GHz, 400 MHz/ch, RFSoC).
- **RFSoC dev boards** (Xilinx ZCU111/216, RFSoC 4×2) — direct-RF-sampling ADCs/DACs, the emerging "no analog front-end" tier.
- **LimeSDR XTRX / LimeNET Micro** and **Lime's newer LMS8001** millimeter extensions.
- **KrakenSDR** — 5-channel coherent RTL-SDR for direction finding (relevant to passive-radar comparisons).
- **PortaPack + HackRF** standalone use; **HackRF "Pro"/clones** — verify 2026 variants.
- **RX888 / RX-666** — 16-bit direct-sampling wideband RX (0–64 MHz), a distinct HF-DDC lineage worth its own row.
- **Fobos SDR, SDRplay RSPduo/RSP1B, Airspy Ranger (R3)** — newer receive-tier parts to slot into the table.
- **60 GHz reference mmWave SDRs** (e.g., NI mmWave, Sivers EVKs) — the genuine yardstick for 802.11ad/ay chips.
