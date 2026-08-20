# RF Test Equipment for the Workbench — Cycle 8

Turning a Wi-Fi chip into an SDR is only half the job. The other half is *proving* it — confirming that your patched firmware is actually radiating the waveform you think it is, at the frequency and power you intend, and that your antenna and cabling are not silently eating (or leaking) your signal. That is what measurement gear is for. Software says "I set channel 6, 15 dBm"; the spectrum analyzer says "you are actually putting a spur into the aviation band at +22 dBm." Believe the instrument.

This page catalogs the affordable bench that pairs with the chips in [`../chips/`](../chips/) and the projects in this directory. Every transmit experiment here must be read alongside [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md) (never radiate into a live antenna without knowing your licensing and power limits) and [`../docs/antennas-and-rf-frontend.md`](../docs/antennas-and-rf-frontend.md) (the front-end these instruments characterize). `modules[]` is empty for this file — it is reference material, not a chip entry.

---

## Why measure at all?

A firmware-defined radio built on a Wi-Fi chip is a black box that *claims* things about itself. Firmware RE gets it transmitting; measurement is how you close the loop:

- **Frequency** — Did the PLL land where you asked? Harmonic/image regions on cheap analyzers, and the harmonic-mixing bands of a chip's own synthesizer, mean "the number on the screen" is not always the band you occupy.
- **Level / power** — A Wi-Fi PA can push +18 to +23 dBm (60–200 mW). Feeding that straight into a −10 dBm-rated analyzer input destroys it. You must *know* your output level before you connect anything sensitive.
- **Spectral occupancy & spurs** — Arbitrary-waveform TX (tier 4) and out-of-spec channels produce splatter, harmonics, and images. You cannot see these from the host; only in the frequency domain.
- **Antenna / feedline health** — A poorly matched antenna reflects power back into the PA (high VSWR), wastes your link budget, and can cook a front-end. This is the VNA's job.

Two instrument families cover almost everything on a hobby budget: a **spectrum analyzer** (what am I transmitting, and where?) and a **vector network analyzer** (is my antenna/filter/cable behaving?). Around them sit **attenuators, dummy loads, and couplers** (so you can measure TX *safely, by cable*) and a **shielded enclosure** (so you can measure over-the-air *without breaking the law or drowning in ambient Wi-Fi*).

---

## 1. TinySA / TinySA Ultra — the pocket spectrum analyzer

The [TinySA](https://tinysa.org/wiki/) is a ~US$60 handheld spectrum analyzer + tracking-style signal generator. It is the single most useful "am I transmitting what I think?" tool for this hobby, because it also *generates* a signal you can trace through filters and couplers.

| | TinySA (basic) | TinySA Ultra |
|---|---|---|
| Analyzer input, low band | 100 kHz – 350 MHz (real RBW filters) | 100 kHz – ~800 MHz (fundamental) |
| Analyzer input, high band | 240 MHz – 960 MHz (harmonic mixer) | ~800 MHz – 5.3 GHz (harmonic bands) |
| RBW | ~3 kHz – 600 kHz | ~200 Hz – 850 kHz |
| Built-in generator | 100 kHz–350 MHz sine; 240–960 MHz square/harmonic | to ~800 MHz fundamental + harmonics |
| Display | 2.8" | 4" |
| Internal attenuator | 0–31 dB step | 0–31 dB step |

**What it measures:** signal presence, center frequency, power level (dBm), occupied bandwidth, harmonics and spurs. Put your chip on the low-power conducted path (below) and you can *see* your channel, its shoulders, and any harmonic products.

**Why it helps the SDR work:** after a Nexmon/firmware TX patch you can confirm the carrier is where the register math predicted, watch the shape of an injected frame, and catch a synthesizer that is off-frequency or producing an image. The built-in generator lets you sweep a home-made bandpass/notch filter (feed generator → filter → analyzer input) and read the response directly.

**The Wi-Fi caveat (important):** 2.4 GHz and 5 GHz sit in the TinySA Ultra's **harmonic** bands, not its fundamental range. Measurements there are usable for *relative* work (is the carrier present, is a spur appearing, is one build louder than another) but are **not lab-grade absolute-power measurements**. For calibrated 2.4/5 GHz power, step up to a real analyzer (Section 3).

**Input protection — read this before connecting a transmitter.** The TinySA input is a low-level receiver: its rated maximum is on the order of **+6 to +10 dBm**, and it has only a 0–31 dB internal attenuator. A bare Wi-Fi PA at ~+20 dBm is roughly **10× to 40× over the damage threshold**. *Never connect a transmitter to a TinySA without external attenuation* (Section 4). Even ambient bench pickup on a whip antenna is usually fine; a cabled PA output is not.

**Firmware/tooling:** the TinySA runs open firmware; [`tinySA-saver`](https://github.com/nanovna-saver/tinysa-saver) (a fork of the NanoVNA-Saver project) drives it from a PC for logging and larger sweeps.

---

## 2. NanoVNA — antenna, filter, and cable characterization

A **vector network analyzer** measures how RF energy reflects off and passes through a two-port network. The [NanoVNA](https://nanovna.com/) brought this to ~US$50. It answers the question the spectrum analyzer cannot: *is my antenna/feedline any good at the frequency I care about?*

| Variant | Frequency range | Notes |
|---|---|---|
| Original NanoVNA | 50 kHz – 300 MHz | fundamental |
| NanoVNA-H | to 900 MHz | harmonic synthesis |
| NanoVNA-H4 (rev 3.4+) | to 1.5 GHz (fw to 2.7 GHz, noisy >1.5 GHz) | 4" screen |
| [NanoVNA V2 / SAA-2N](https://nanovna-v2.com/) | 50 kHz – 3 GHz | true 3 GHz hardware, higher dynamic range |
| NanoVNA V2 Plus4 | to 4.4 GHz | reaches the low 5 GHz edge poorly; see caveat |

**What it measures:**
- **S11 (reflection):** return loss, **VSWR/SWR**, and complex impedance on a Smith chart — i.e. how well your antenna is matched to 50 Ω at each frequency.
- **S21 (transmission):** insertion loss and passband of a filter, cable, attenuator, or amplifier gain (small-signal).
- **TDR** (from S11): cable length and fault/discontinuity location.

**Calibration is mandatory.** A VNA measures relative to a **SOLT** cal — **S**hort, **O**pen, **L**oad (50 Ω), **T**hru — performed at the exact reference plane (end of your test cable) over the exact span you will use. Skip calibration and every number is fiction. Re-cal whenever you change the span or the cable.

**Why it helps the SDR work:** before you trust a CSI or sensing capture (see [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md)), confirm the antenna actually resonates in-band — a whip cut for 900 MHz will read a terrible SWR at 2.4 GHz and quietly halve your SNR. When you build the front-end filters and LNAs from [`../docs/antennas-and-rf-frontend.md`](../docs/antennas-and-rf-frontend.md), the NanoVNA is how you verify the passband and match. And a high measured VSWR at the PA is a direct warning that reflected power is stressing your chip's output stage.

**Caveat:** at 2.4/5 GHz, harmonic-mode NanoVNAs run out of dynamic range and accuracy. A V2 (3 GHz) is realistic for 2.4 GHz antenna work; genuine 5 GHz/6 GHz characterization wants a V2 Plus4 at minimum, and ideally a real VNA. Tooling: [`NanoVNA-Saver`](https://github.com/NanoVNA-Saver/nanovna-saver) for PC-side sweeps, export, and multi-segment scans; [NanoVNA-D firmware](https://github.com/DiSlord/NanoVNA-D) for the H/H4 hardware.

---

## 3. A real spectrum analyzer — when the numbers must be trusted

When you need calibrated absolute power, low noise floor, and clean 2.4/5/6 GHz coverage (regulatory-style emission checks, honest spur hunting, PA output verification), a benchtop analyzer earns its cost.

**[Siglent SSA / SVA family](https://siglentna.com/product-category/spectrum-analyzers/)** is the common hobby-to-prosumer choice:

| Model | Range | DANL | Tracking generator |
|---|---|---|---|
| SSA3000X Plus | 9 kHz – 1.5 / 2.1 / 3.2 GHz | −165 dBm/Hz | yes (hardware installed on SSA3000-series) |
| SVA1000X | 9 kHz – 1.5 / 3.2 / 7.5 GHz | −165 dBm/Hz | yes (also does VNA-style measurements) |
| SSA3000X-R | 9 kHz – 3.2 / 5.0 / 7.5 GHz | −165 dBm/Hz | real-time |
| SSA5000A | 9 kHz – 13.6 / 26.5 GHz | −165 dBm/Hz | real-time |

The **7.5 GHz** variants (SVA1015X, SSA3032X-R, etc.) reach across 2.4 GHz, 5 GHz, and the new **6 GHz** Wi-Fi 6E/7 bands with a real, calibrated noise floor and a **tracking generator** for scalar filter/antenna sweeps. The **SVA1000X** additionally does reflection/VSWR and distance-to-fault, blurring into VNA territory.

**A real analyzer still needs the same input protection as a TinySA** — its front end is typically rated around **+30 dBm absolute max / ~0 dBm for undistorted measurement**. Always pad transmitter outputs down (Section 4).

### The poor-man's analyzer: an RTL-SDR (or better)

An **RTL-SDR** (R820T2/R860 tuner, ~24 MHz – 1.766 GHz) can act as a swept spectrum analyzer with [`rtl_power`](https://github.com/keenerd/rtl-sdr-misc) / [`QSpectrumAnalyzer`](https://github.com/xmikos/qspectrumanalyzer) / `gqrx`. It is excellent for **sub-GHz** work (ISM 433/868/915 MHz, the sub-GHz radios in [`../chips/`](../chips/)) and for cheap monitoring.

Hard limits to respect:
- **It cannot see Wi-Fi bands.** The R820T2 tops out near 1.7 GHz — no 2.4/5/6 GHz without a **downconverter** or a higher-range SDR.
- **Narrow instantaneous bandwidth** (~2.4 MHz usable), so wide spans are *stitched sweeps*, not a live snapshot — you can miss bursty spurs.
- **Uncalibrated** power; treat readings as relative dB, not dBm, unless you calibrate against a known source (your TinySA generator is handy here).

Stepping up: an **Airspy** (to ~1.8 GHz, cleaner), a **HackRF One** (1 MHz – 6 GHz, so it *does* reach Wi-Fi bands and can even transmit — see legal warnings), or a **PlutoSDR** give real IQ across the bands these chips use. These overlap with the SDR targets themselves, not just measurement — but as an analyzer, a HackRF + `soapy_power`/`hackrf_sweep` is the cheapest way to *see* a 2.4 GHz channel.

---

## 4. Attenuators, dummy loads, and directional couplers — measuring TX *safely*

This is the section that keeps your instruments (and your chip) alive. **Every conducted transmit test** — hooking a transmitter to an analyzer by cable instead of by antenna — must go through a padding/absorbing path. This directly implements the conducted-testing guidance in [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md): measuring by cable inside attenuators/loads keeps your signal off the air and out of trouble.

### Fixed attenuators

A fixed coaxial attenuator drops signal level by a known amount (in dB) while presenting 50 Ω both ways. [Mini-Circuits fixed attenuators](https://www.minicircuits.com/WebStore/Attenuators.html) span **0–30+ dB, DC–67 GHz**, in two power classes:

- **Small SMT / SMA pads** (e.g. BAT-6+, BAT-20+): ~**1–2 W** — fine on the *low-power side*, after the big attenuator, protecting the analyzer input.
- **Connectorized power attenuators** (e.g. BW-N series): up to **100 W** — these go *first*, right at the transmitter, to absorb most of the energy.

**Sizing example:** a Wi-Fi PA at **+20 dBm (100 mW)** into a TinySA rated ~+6 dBm needs to arrive near **−20 dBm** for a comfortable reading — a **40 dB** pad. Put a **30 dB / ≥1 W power attenuator** at the source, then a small **10 dB** pad at the instrument. Never rely on a 0.5 W SMD pad as the *first* element in front of a real PA — check the power rating dissipates your full TX power with margin.

### Dummy loads (terminations)

A **50 Ω dummy load** absorbs the transmitter's *entire* output and turns it to heat, presenting a perfect (low-VSWR) match so the PA sees an ideal antenna. Use it whenever you want the radio keyed up but **radiating nothing** — bring-up, thermal tests, or the load side of a coupler. The power rating must exceed your TX power continuously (a 5 W load for a ~0.1 W Wi-Fi chip is ample; err large — they get hot).

### Directional couplers

A **directional coupler** taps off a small, calibrated fraction of the power travelling in one direction on a through-line, letting you *sample* a live transmit path without interrupting it. Key numbers:

- **Coupling factor** (e.g. 10, 20, 30 dB): how much weaker the tapped sample is than the main line — a 20 dB coupler on a +20 dBm main line gives a **0 dBm** sample (still pad it before an instrument!).
- **Directivity:** how well it distinguishes *forward* from *reflected* power — the property that lets a **dual/bi-directional coupler** report transmitted power *and* return loss/VSWR at the same time.
- **Main-line power handling & insertion loss:** the through path must survive full TX power with little loss.

**The safe conducted-TX bench** for one of these chips looks like:

```
[chip / PA out] --> [30 dB power attenuator, >=1 W]
                        |
                        v
            [dual directional coupler] --fwd sample--> [10 dB pad] --> [analyzer]
                        |                 --rfl sample--> [10 dB pad] --> (VSWR/return loss)
                        v
                 [50 ohm dummy load, >= TX power]
```

Nothing radiates; the analyzer sees a padded, calibrated sample; the coupler simultaneously reports how much power is bouncing back. This is the canonical way to verify TX frequency, level, and match *before* you ever connect a real antenna.

---

## 5. Shielded test enclosure — over-the-air testing without breaking the law

Sometimes you must test **over-the-air** — antenna in the loop, real radiated pattern (CSI captures, injection range, antenna comparisons). Doing that on an open bench means (a) your emissions leak into licensed spectrum, and (b) the room's ambient 2.4/5 GHz Wi-Fi swamps your measurement.

A **shielded test enclosure** (RF/Faraday box, e.g. the Ramsey STE-series and equivalents from JRE Test, or a DIY copper-mesh/steel box) solves both:

- **Contains your emissions** so an unlicensed or out-of-band experiment stays legal and interference-free — the enclosure attenuates 60–100 dB, keeping your radiated signal *inside the box*. Tie this back to [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md): a good enclosure is often the difference between a legal experiment and an illegal transmission.
- **Excludes ambient RF** so your measured signal is *only* your device — essential when the whole point is a clean CSI or spectral capture (see [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md)). A crowded 2.4 GHz band otherwise buries a low-power injected frame.
- **Repeatable geometry** with internal absorber (foam) approximating a mini-anechoic chamber, and feedthrough bulkhead connectors so the DUT sits inside while your analyzer/VNA stays outside.

Budget options: metallized fabric **Faraday bags** for quick isolation checks, a **galvanized-steel + copper-tape** DIY box, or a laptop-sized commercial STE enclosure with SMA/N feedthroughs. Verify the enclosure itself with the TinySA: transmit a known signal inside, sniff outside, and confirm the leakage is down where the datasheet claims.

---

## Minimum viable bench (priority order)

1. **NanoVNA (V2 if you touch 2.4 GHz)** — nothing else tells you your antenna works. ~US$50–120.
2. **TinySA / TinySA Ultra** — see your signal, catch spurs, sweep filters, and it generates too. ~US$60–130.
3. **Attenuator + dummy-load kit** — a 30 dB power pad, a couple of 10 dB SMA pads, and a 5 W 50 Ω load. The cheapest insurance you will ever buy for your instruments. ~US$30–60.
4. **RTL-SDR** — poor-man's analyzer for sub-GHz, plus a genuinely useful receiver. ~US$30.
5. **Dual directional coupler** — the moment you do serious conducted TX/VSWR work.
6. **Real analyzer (Siglent 7.5 GHz w/ tracking gen)** — when 2.4/5/6 GHz numbers must be trusted. ~US$1.5k+.
7. **Shielded enclosure** — when you must radiate to test but must not radiate to the neighborhood.

**Golden rule:** pad first, connect second. Read [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md) before any transmit test, and characterize your front-end per [`../docs/antennas-and-rf-frontend.md`](../docs/antennas-and-rf-frontend.md) before you trust a single capture.

---

## References

- TinySA — official wiki and specifications: <https://tinysa.org/wiki/>
- tinySA-saver (PC software, NanoVNA-Saver fork): <https://github.com/nanovna-saver/tinysa-saver>
- NanoVNA — overview and frequency coverage: <https://nanovna.com/>
- NanoVNA V2 / SAA-2N: <https://nanovna-v2.com/>
- NanoVNA-Saver (PC control, SOLT cal, sweeps): <https://github.com/NanoVNA-Saver/nanovna-saver>
- NanoVNA-D firmware (H/H4): <https://github.com/DiSlord/NanoVNA-D>
- Siglent spectrum analyzers (SSA3000X Plus, SVA1000X, SSA3000X-R, SSA5000A): <https://siglentna.com/product-category/spectrum-analyzers/>
- Mini-Circuits fixed coaxial attenuators (values, power, DC–67 GHz): <https://www.minicircuits.com/WebStore/Attenuators.html>
- Mini-Circuits directional couplers: <https://www.minicircuits.com/WebStore/Directional_Couplers.html>
- QSpectrumAnalyzer (rtl_power / soapy_power GUI): <https://github.com/xmikos/qspectrumanalyzer>
- rtl-sdr utilities incl. rtl_power: <https://github.com/keenerd/rtl-sdr-misc>
- RTL-SDR blog (as spectrum analyzer): <https://www.rtl-sdr.com/>
