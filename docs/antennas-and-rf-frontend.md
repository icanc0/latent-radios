# Antennas & the RF Front-End: the hardware around the chip

> **The practical RF companion.** Every experiment in this catalog — Nexmon CSI on a Broadcom chip, ESP32 raw-802.11 TX, an RTL-SDR pulled into GNSS observables, an nRF flooding sub-GHz — lives or dies on the few centimeters of copper, coax, and connector between the silicon and the air. The chip is only ever half the radio. This page is the other half: antennas, the front-end chain (LNA / filter / attenuator / DC block / bias-tee), why everything is 50 ohms, how to transmit safely into a load instead of the room, and how to build a shield when you need the room to *not* hear you.
>
> Read this alongside **[../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md)** (do not skip it before you key up any transmitter) and **[../chips/hardware-index.md](../chips/hardware-index.md)** (which board has which connector).

---

## 1. Why any of this matters before you touch the chip

A Wi-Fi/BLE/sub-GHz chip presents an RF port. What you bolt onto that port determines three things you cannot fix in firmware:

1. **How much signal reaches the ADC** on receive (antenna gain, pattern, feedline loss, LNA).
2. **Where your energy actually goes** on transmit (matched load vs. reflected power vs. radiated-into-the-lab).
3. **What else the front-end lets through** — out-of-band junk, adjacent transmitters, your own harmonics.

None of the tier-2..5 tricks in this catalog (CSI, spectral scan, raw-IQ, arbitrary-waveform TX) are worth much if the front-end throws away 10 dB before the signal is digitized, or if a transmit experiment dumps power back into the PA because nothing is connected.

**Golden rule:** a chip is designed to see **50 Ω** at its RF pin. Deviate from that and you lose power to reflection, detune filters, and — on TX — risk the power amplifier. Almost everything below is in service of "keep the whole chain at 50 Ω."

---

## 2. Antennas for these experiments

You are almost always working in one of four bands. Pick the antenna for the band and the *job* (survey vs. long link vs. bench).

### 2.4 GHz and 5 GHz (Wi-Fi, BLE, Zigbee, Thread)

| Antenna type | Gain (typical) | Pattern | Use it for |
|---|---|---|---|
| **Rubber-duck / dipole omni** | 2–5 dBi | doughnut (omni in azimuth) | general survey, CSI capture, promiscuous sniffing where you don't know where the target is |
| **Collinear high-gain omni** | 7–12 dBi | flatter doughnut, less vertical coverage | fixed monitoring of a floor/room; trades ceiling/floor coverage for range |
| **Panel / patch (directional)** | 8–19 dBi | forward lobe, ~30–70° beamwidth | pointing at one AP/device; improves SNR and rejects clutter behind you |
| **Yagi** | 12–18 dBi | narrow forward beam | long point-to-point, direction-finding, isolating one emitter |
| **Grid / dish** | 20–27 dBi | very narrow | long-haul; overkill on a bench, awkward indoors |

Practical notes:

- **Band matters.** A "2.4 GHz" antenna is a poor radiator at 5 GHz and vice-versa. Dual-band Wi-Fi antennas exist and are the safe default when your chip does both. For **6 GHz (Wi-Fi 6E/7)** you need an antenna actually rated to 7.1 GHz — most "dual-band" parts roll off before that.
- **Directional antennas raise SNR without raising your TX power** — this is the legal and polite way to reach farther. Antenna *gain* is not amplification; it is re-shaping the same energy into a narrower cone. That still counts toward EIRP limits (see [../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md)).
- **CSI / sensing work** generally wants a *stable, known* antenna, not a high-gain one. Swapping antennas mid-capture changes the channel and pollutes your dataset. For multi-antenna CSI (e.g. 3×3 on a Broadcom/QCA part) keep the antennas fixed, spaced, and identical.
- **Polarization**: most Wi-Fi is vertical-ish but sprayed by multipath indoors. A cross-polarized link loses ~20 dB in theory; indoors multipath rescues you, outdoors it does not. Match polarization for outdoor directional links.

### Sub-GHz (433/868/915 MHz — nRF, CC1101, TI Sub-1 GHz, LoRa-class)

- **Quarter-wave whip** is the workhorse: ~17 cm at 433 MHz, ~8.2 cm at 868/915 MHz. Length is `λ/4`, and it needs a **ground plane** (the board's ground, or a counterpoise) to work as designed — a whip floating with no ground plane is badly detuned.
- **Helical / coil-loaded stubby** antennas trade efficiency for size; fine for short-range bench work, poor for range.
- Sub-GHz penetrates walls better than 2.4/5 GHz — a modest whip often outperforms expectations indoors.

### 60 GHz (802.11ad/ay) and UWB

- 60 GHz is essentially all **on-package phased-array / beamforming**; you rarely attach an external antenna, and connectorized 60 GHz hardware is exotic and lossy. Treat the module's built-in array as fixed.
- **UWB** (e.g. DW1000/DW3000-class) uses wideband antennas; keep leads short, respect the reference-design antenna, and do not substitute a narrowband Wi-Fi antenna.

---

## 3. Connectors — and the RP-SMA gotcha that eats an afternoon

### The connectors you will actually meet

| Connector | Where it shows up | Notes |
|---|---|---|
| **SMA** | SDRs (HackRF, RTL-SDR v3/v4 blog), lab gear, LNAs/filters | Threaded, 50 Ω, good to 18 GHz. The lab standard. |
| **RP-SMA** | Consumer Wi-Fi routers, cards, many Wi-Fi antennas | *Reverse-polarity* SMA — mechanically identical thread, swapped center pin/socket (see below). |
| **U.FL / IPEX (MHF)** | Tiny modules: ESP32, nRF, m.2/mini-PCIe Wi-Fi cards, many dev boards | Snap-on micro-coax. Fragile, ~30 mate cycles. Use a **U.FL-to-SMA pigtail** to reach the outside world. |
| **MHF4** | Newer m.2 Wi-Fi (Intel AX2xx) | Even smaller than U.FL; needs the matching MHF4 pigtail. |
| **N-type** | Higher-power / outdoor gear, some antennas | Bigger, weatherable, low loss. |
| **BNC** | Test gear, some HF SDR ports | Bayonet; common on scopes and low-freq SDR. |

### The RP-SMA gotcha (read this twice)

**RP-SMA (Reverse Polarity SMA) was created for a regulatory reason, not an electrical one.** US FCC rules pushed consumer Wi-Fi vendors to use a *non-standard* antenna connector so end-users couldn't trivially bolt on a high-gain standard-SMA antenna. The fix vendors chose: keep the SMA thread and shell but **swap the genders of the center contact**.

- **Standard SMA male** (plug) = male thread (outer nut) **+ center pin**.
- **Standard SMA female** (jack) = female thread **+ center socket**.
- **RP-SMA male** = male thread **but a center *socket*** (the pin was removed).
- **RP-SMA female** = female thread **but a center *pin***.

Consequences that bite:

1. **The threads mate. The center contacts do not.** An RP-SMA "male" will thread cleanly onto a standard SMA "female" and then make **no center-conductor contact** — the connection looks perfect and passes zero signal. This is the classic "why is my link dead / why is VSWR infinite" afternoon.
2. **Almost all consumer Wi-Fi routers, USB Wi-Fi adapters, and their antennas are RP-SMA.** Almost all SDRs, LNAs, filters, and lab accessories are standard SMA. **They do not interoperate without an adapter.**
3. **Buy `RP-SMA ↔ SMA` adapters** (and label them) if you mix worlds — which in this catalog you constantly will (e.g. an RP-SMA Wi-Fi antenna onto an SMA LNA onto an SMA-port SDR).
4. **Gender ≠ what you'd guess by looking at the hole.** Check the *center contact*, not the thread, when identifying RP-SMA. This is the single most common connector mistake.

**Handling discipline for all of the above:** hand-tighten SMA/RP-SMA, then a light snug (a proper torque wrench is 8 in-lb / ~0.9 N·m if you have one — over-tightening ruins the interface). Never rotate the *body* of a device to tighten — turn the nut only, or you twist the internal launch. Keep U.FL/MHF4 mate cycles to a minimum; they are consumables.

---

## 4. The front-end chain: LNA, filter, attenuator, DC block, bias-tee

Think of the front-end as a signal path you assemble from 50 Ω lego bricks. Order matters.

```
RX:  antenna → [BPF] → [LNA] → [BPF] → [attenuator?] → SDR/chip
TX:  chip → [attenuator/DC block] → [BPF] → dummy load OR antenna
```

### Low-Noise Amplifier (LNA)

- **Job:** boost a weak received signal *before* the coax and receiver add their own noise. In a receive chain the **first amplifier's noise figure dominates the whole system** (Friis' formula), so the LNA belongs **as close to the antenna as possible** — ideally right at it.
- **Do not** slap an LNA on a strong signal to "get more" — you will overdrive/desense the receiver and manufacture intermodulation. LNAs are for weak-signal, low-noise front-ends, not volume knobs.
- Popular hobby LNAs: **Mini-Circuits ZX60 / PSA-series**, the **RTL-SDR Blog wideband LNA**, SPF5189Z-based boards. Many are **bias-tee powered** (see below) — the RTL-SDR Blog v3/v4 and airspy can feed 4.5–5 V up the coax to power them.
- An LNA in front of the **wrong** filter amplifies out-of-band trash too; pair a strong nearby FM/cellular environment with **filter-first-then-LNA** or a filtered LNA.

### Band-pass / low-pass filters (BPF/LPF)

- **RX:** reject out-of-band energy (strong FM broadcast, cellular, pagers) that would desense a broadband SDR front-end. A 2.4 GHz BPF in front of an RTL-SDR/HackRF makes a night-and-day difference in a noisy urban lab.
- **TX:** a **low-pass or band-pass filter after the transmitter suppresses harmonics.** Cheap TX chains (and any square-wave-ish source like the HackRF at band edges) throw harmonics; filtering them is often a *legal requirement*, not a nicety (see [../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md)).
- Vendors: **Mini-Circuits** (SBP/VBFZ/VLF series), **RTL-SDR Blog** broadcast-band and 2.4 GHz filters, Nooelec.

### Attenuators

- A **fixed attenuator** (3/6/10/20/30 dB, SMA, 50 Ω) is the most useful and most under-bought bench part. Uses:
  - **Protect a receiver** from a too-strong signal or a nearby transmitter.
  - **Safely sample a transmitter's output** — put a big attenuator (e.g. 30–40 dB) between a TX port and a receiver so you can look at your own signal without cooking the RX.
  - **Set a known link budget** on the bench so two radios "hear" each other at a realistic level instead of screaming into each other's front ends inches apart.
- **Power rating matters:** a 2 W attenuator will burn on a 10 W input. Match to your TX power (most chips here are ≤100 mW / +20 dBm, so a common 2 W part is ample — but the HackRF/PlutoSDR are milliwatts, and a Wi-Fi PA can be higher).
- **Step attenuators** (rotary, e.g. 0–30/0–90 dB) are convenient for sweeping levels.

### DC block

- A **DC block** is a series capacitor in a coax barrel: it passes RF, blocks DC. Use it to protect a device from **another device's bias voltage** — e.g. when you connect an SDR whose bias-tee is (accidentally) on, or when interfacing two boards that each expect to source DC. Cheap insurance; keep one in the kit.

### Bias-tee

- A **bias-tee** injects DC onto the coax to power a remote device (an LNA or an active antenna) **up the same cable that carries RF back down.** It is an inductor (DC in) + capacitor (RF out) network.
  - **Built into many SDRs:** RTL-SDR Blog v3/v4 (4.5 V), Airspy, some HackRF setups (external), SDRplay. Enable it in software (`rtl_biast -b 1` for RTL-SDR Blog dongles).
  - **The GNSS case (directly relevant to this cycle):** **active GNSS antennas** contain an LNA and need **3.0–5 V of bias up the coax.** A GPS/GNSS receiver front-end (or an SDR receiving GNSS) must supply that bias via a bias-tee, or the active antenna is deaf. This is exactly why "just plug an antenna into the SDR" fails for GNSS — the antenna is *active* and unpowered.
- **Danger:** enabling a bias-tee into a device that isn't expecting DC (or shorting the center pin) can damage it. Know which end sources DC, use a **DC block** on anything downstream that shouldn't see it, and never enable a bias-tee into a **short** (a shorted load or a passive antenna that grounds the center conductor will trip/damage the supply on some units).

---

## 5. 50 ohms and impedance matching — why the whole chain is one number

Nearly all RF gear in this catalog is **50 Ω characteristic impedance** (the outlier you'll meet is 75 Ω cable/CATV and some TV-tuner-derived RTL-SDR front-ends). Here's why it's non-negotiable:

- When a transmission line's impedance **matches** the source and load, **all the power transfers and none reflects.** Mismatch creates a **reflected wave**; forward and reflected waves interfere to form standing waves.
- The mismatch metric is **VSWR** (Voltage Standing Wave Ratio) or, equivalently, **return loss** / reflection coefficient (Γ):
  - VSWR **1.0:1** = perfect match, 0 reflected power.
  - VSWR **2.0:1** ≈ **~11%** of power reflected (return loss ~9.5 dB) — a common "acceptable" ceiling for antennas.
  - VSWR **3.0:1** ≈ 25% reflected; getting bad.
  - VSWR **∞:1** = open or short = **100% reflected** (nothing connected, or a dead RP-SMA mate).
- **On receive**, mismatch just costs you signal (lower SNR). Annoying, not dangerous.
- **On transmit**, reflected power goes **back into the power amplifier.** Into a bad mismatch (open/short/no antenna), a PA can overheat and **fail.** This is *the* reason you never key up a transmitter with nothing connected.

**Practical takeaways:**
- Keep every element 50 Ω: cable, connectors, adapters, attenuators, filters, loads.
- Minimize adapter stacking — each junction adds a small mismatch and loss.
- Use good coax for the band. **RG-174/RG-316** (thin, flexible U.FL/SMA pigtails) are *lossy at 5+ GHz* — keep them short. **RG-58** is mediocre at microwave. **LMR-240/LMR-400** or low-loss microwave cable for any run of length at 2.4/5 GHz. At 5 GHz a cheap 2 m RG-174 pigtail can eat several dB before your LNA ever runs.
- If you own one instrument for this, a **NanoVNA** (cheap vector network analyzer, ~50 kHz–3/6 GHz depending on model) lets you *measure* VSWR/return loss of antennas, cables, and filters instead of guessing. It is the highest-leverage sub-$100 tool in RF hobby work.

---

## 6. Transmitting safely: dummy loads + attenuators on the bench

**Do not radiate while you develop.** Almost all TX experiments in this catalog (ESP32 raw 802.11, HackRF replay, nRF/CC1101 sub-GHz) should first run **into a load, not an antenna**, both to protect the PA and to stay legal/quiet. See [../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md) for the legal side; this is the hardware side.

### Dummy load

- A **50 Ω dummy load** (a matched resistive termination in an SMA/N barrel) gives the transmitter a perfect match with **~no radiation.** It converts your TX power to heat.
- **Power rating is the whole point.** A 2 W SMA dummy load is fine for the ≤+20 dBm chips here; a Wi-Fi PA or a higher-power amp needs a rated load (and possibly a heatsink). Never terminate more power than the load's rating.
- Use it to: bring up a transmitter, tune modulation, measure spectral output (via a big attenuator + SDR sniffing the *load side* through a coupler), and confirm the chip is actually keying without spraying the building.

### Attenuator-coupled "over-the-wire" testing

The safe bench pattern for TX ↔ RX between two of your own radios:

```
TX chip  ──►  [30–40 dB attenuator]  ──►  RX (SDR/chip)
                (or via a directional coupler + dummy load)
```

- The big attenuator drops your TX to a level the RX front-end can survive and see cleanly, and — crucially — keeps the signal **in the coax**, not in the air.
- For watching your *own* transmit spectrum while it's terminated, use a **directional coupler**: main port → dummy load, coupled port (−20/−30 dB) → SDR.

### The rules of the road (hardware version)

1. **Never key a transmitter into an open, a short, or "nothing."** Antenna, dummy load, or attenuator+load — always something 50 Ω.
2. **Filter TX harmonics** before anything radiates (§4).
3. **Rate every part for the power** it will see (loads, attenuators, couplers).
4. **Develop into a load; radiate only when you've confirmed the signal is clean and you're legally clear.**

---

## 7. Shielding: RF-tight boxes, copper tape, and the DIY Faraday enclosure

Two reasons you'll want a shield:

- **Keep your test signal in** (repeatable RX/TX measurements, harmonic hunting, or just not stepping on the neighbors' Wi-Fi while you fuzz).
- **Keep the world out** (measure a device's *own* emissions or a weak signal without ambient 2.4/5 GHz drowning it).

### How a Faraday enclosure works (and why the lid is the hard part)

- A conductive, **fully enclosed** box excludes/contains fields. The physics is easy; the **seams and openings** are where it leaks. An enclosure is only as good as its **worst gap.**
- **Aperture rule of thumb:** a slot leaks meaningfully once its longest dimension approaches ~**λ/20 to λ/10**. At 2.4 GHz, λ ≈ 12.5 cm, so slots of even ~1 cm start leaking — and cables, hinges, and lid gaps are exactly that size. **A metal box with a loose lid is not a shield at Wi-Fi frequencies.**
- **Every cable that enters is an antenna** that drags the outside signal in. Feedthroughs need bulkhead connectors and/or ferrites; a bare coax through a hole defeats the box.

### DIY options, roughly in order of effort

| Build | Isolation (2.4 GHz, ballpark) | Notes |
|---|---|---|
| **Anti-static/metallized bag, doubled** | ~10–30 dB, unreliable | quick sanity test only; seams leak |
| **Cookie/paint tin, taped lid** | ~20–40 dB if the lid seam is taped with copper | classic cheap Faraday can; conductivity of the seam is everything |
| **Copper-tape-lined project box** | ~30–50 dB with *conductive-adhesive* copper tape and overlapping seams | use **conductive-adhesive** copper tape so overlaps actually bond; non-conductive adhesive leaves capacitive gaps |
| **Commercial RF-shielded box / "Faraday bag" test enclosure** | 40–90+ dB, characterized | Ramsey STE-series-class boxes, shielded test enclosures; expensive but honest numbers |
| **Screen-room / shielded tent** | 60–100+ dB | overkill for this catalog |

DIY tips that actually move the needle:

- **Use conductive-adhesive copper tape** and **overlap seams by a few cm** — the adhesive must conduct across the joint, or you've built a capacitor, not a bond.
- **Line the lid and the box, and make lid-to-box contact continuous** — copper-tape "fingers" or conductive gasket/foam around the rim. The lid seam is the #1 leak.
- **Feed cables through bulkhead SMA connectors mounted in the wall**, with the connector body bonded to the shield — don't drill a hole and pass bare coax.
- **Verify, don't assume.** Put a known transmitter (a phone, a beacon) inside, sniff from outside with an SDR, and see how far the level actually drops. Shielding claims are only real if you measure them.
- **Thermal:** a sealed box holds heat; long TX sessions inside a small can will cook parts. Ventilate with **waveguide-below-cutoff** honeycomb or many small holes (each ≪ λ/20), not one big vent.

Legitimate, honest uses: repeatable measurements, harmonic/EMI hunting, keeping fuzzing off the air, protecting a weak-signal test from ambient noise. (Deliberately jamming or containing signals to defeat someone else's system is a different conversation — see [../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md).)

---

## 8. A practical starter kit (buying notes)

You do not need all of this to start, but this is the "wish I'd bought it on day one" list for working through this catalog. Prices are order-of-magnitude, not quotes.

**Connectors / cables (buy first — they unblock everything):**
- Assorted **SMA ↔ RP-SMA adapters** (M/F both ways) — the single most-needed thing when mixing Wi-Fi and SDR gear.
- **U.FL-to-SMA** and **MHF4-to-SMA** pigtails (short, RG-178/RG-316) for ESP32/nRF/m.2 modules.
- SMA **M-M, F-F, and M-F barrels/couplers**; a couple of **right-angle** SMA adapters.
- One or two lengths of **decent 50 Ω coax** (LMR-240-class) for anything longer than a jumper at 2.4/5 GHz.

**Loads / attenuators (buy before you transmit):**
- **50 Ω dummy load**, SMA, rated ≥2 W (more if you'll drive a Wi-Fi PA).
- **Fixed attenuators**: a set of 3/6/10/20 dB, plus a **30 dB** for sampling transmitters. 2 W parts are fine for ≤+20 dBm work.
- A **DC block** or two.

**Front-end (buy as needed):**
- A **bias-tee** (or an SDR with one built in) — mandatory for active GNSS antennas and remote LNAs.
- A **2.4 GHz band-pass filter** and, if you'll transmit, a **low-pass filter** for harmonics.
- A **wideband LNA** (RTL-SDR Blog LNA / SPF5189Z / Mini-Circuits) — only if you're chasing weak signals.

**Antennas:**
- A **dual-band 2.4/5 GHz omni** (the default), plus a **2.4/5 GHz directional panel** for pointing at one device.
- **Sub-GHz whips** cut for your band (433 and/or 868/915 MHz) with the right ground plane.
- For CSI/sensing: **matched, fixed omnis** you won't swap mid-capture.

**Measurement (the force-multiplier):**
- A **NanoVNA** — measure VSWR/return loss of every antenna, cable, and filter instead of guessing. Highest leverage cheap tool here.
- Optional: a small **directional coupler** for watching your own TX into a load.

**Where people buy:** RTL-SDR Blog store and Nooelec (SDR-oriented LNAs, filters, bias-tees, dongles), **Mini-Circuits** (lab-grade attenuators/filters/couplers, sold individually), plus the usual electronics distributors and marketplaces for adapters and pigtails. Buy attenuators and loads from reputable sources — the rating printed on a $2 no-name part is optimistic.

---

## 9. Cross-references

- **[../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md)** — before you key up: EIRP/power limits, harmonics, dummy-load discipline, and what "legal to transmit" means in your region.
- **[../chips/hardware-index.md](../chips/hardware-index.md)** — which board/chip carries which RF connector (U.FL vs SMA vs RP-SMA vs on-package), so you can plan the adapter chain before ordering.

---

## References

- Wikipedia — SMA connector: <https://en.wikipedia.org/wiki/SMA_connector>
- Wikipedia — RP-SMA (reverse-polarity SMA): <https://en.wikipedia.org/wiki/RP-SMA>
- Wikipedia — Hirose U.FL: <https://en.wikipedia.org/wiki/Hirose_U.FL>
- Wikipedia — Standing wave ratio (VSWR): <https://en.wikipedia.org/wiki/Standing_wave_ratio>
- Wikipedia — Bias tee: <https://en.wikipedia.org/wiki/Bias_tee>
- Wikipedia — Low-noise amplifier / noise figure (Friis): <https://en.wikipedia.org/wiki/Low-noise_amplifier>
- Wikipedia — Faraday cage: <https://en.wikipedia.org/wiki/Faraday_cage>
- microwaves101 — VSWR / return loss reference: <https://www.microwaves101.com/encyclopedias/voltage-standing-wave-ratio-vswr>
- microwaves101 — 50 ohms / characteristic impedance: <https://www.microwaves101.com/encyclopedias/why-fifty-ohms>
- RTL-SDR.com — bias tee usage (`rtl_biast`) and active-antenna power: <https://www.rtl-sdr.com/rtl-sdr-blog-v-3-dongles-user-guide/>
- RTL-SDR.com — LNAs, filters, and front-end accessories store/blog: <https://www.rtl-sdr.com/store/>
- Great Scott Gadgets — HackRF One documentation (TX cautions, filtering): <https://hackrf.readthedocs.io/en/latest/>
- Mini-Circuits — attenuators, filters, and directional couplers (component catalog): <https://www.minicircuits.com/>
- NanoVNA project (measuring VSWR/return loss): <https://nanovna.com/>
