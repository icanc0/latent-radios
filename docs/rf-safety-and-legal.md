# RF Safety, Shielding, and the Law Before You Transmit

> **Read this before you key up anything.** Most of the *Latent Radios* catalog is dual-use: the same firmware patch that lets a Wi‑Fi chip *listen* to raw I/Q or channel state can also make it *emit* arbitrary waveforms. Listening is almost always legal. Emitting is a regulated act with legal, safety-of-life, and health dimensions. This page is the "measure twice, cut once" for the transmit side.
>
> **This is not legal advice.** Rules differ by country, by band, and by year. You are responsible for knowing the regulations of the jurisdiction you physically transmit in. When in doubt: don't radiate — do it on coax into a dummy load, or don't do it at all.

Back to the catalog: [../README.md](../README.md) · Technique index: [../docs/techniques.md](../docs/techniques.md)

---

## 1. Why receiving is (usually) fine and transmitting is not

Radio regulation almost universally treats **reception/sensing** and **emission** as fundamentally different acts:

| Act | What the chip does | Typical legal status | Physical risk |
|---|---|---|---|
| **RX / passive sensing** — monitor mode, CSI capture, spectral scan, passive radar, raw-I/Q sniffing | Absorbs energy that is *already in the air*; emits nothing | Generally legal to *receive* (with narrow exceptions, below) | None — you add no energy to the environment |
| **TX** — packet injection, arbitrary-waveform TX, replay, active radar/FMCW, covert-channel emission, jamming | *Adds* RF energy to shared spectrum | Heavily regulated; often illegal without authorization | You can interfere with others, including safety-of-life systems, and expose people to RF energy |

**Receiving is not a blank cheque, though.** Even passive listening has limits in some jurisdictions:

- **US** — The Electronic Communications Privacy Act and the Communications Act (47 U.S.C. § 605) restrict *divulging or using* the contents of certain intercepted communications, and it is illegal to intercept/decode most **cellular** and other protected transmissions. Merely tuning a receiver is broadly permitted; *decrypting protected content or acting on intercepted private communications* is not.
- **UK** — Under the Wireless Telegraphy Act 2006 it is an offence to *receive* messages you are not authorized to receive and to disclose them. "Listening" is more constrained than in the US.
- **Everywhere** — Passive **radar** and RX-only sensing emit nothing and are the safe default for experimentation. If your project can answer its question by listening, do that.

The rest of this page is about the moment you decide to **emit**.

---

## 2. The unlicensed / ISM framework at a high level

The bands most *Latent Radios* chips live in — 2.4 GHz, 5 GHz, 6 GHz, sub‑GHz (433/868/915 MHz), 60 GHz, UWB — are mostly **unlicensed** (a.k.a. licence-exempt) bands. "Unlicensed" does **not** mean "unregulated." It means you may operate a *certified device* within *strict technical limits* **without an individual station licence**, on two conditions baked into the rules everywhere:

1. **Non-interference:** you must not cause harmful interference to licensed (primary) services.
2. **Non-protection:** you must accept any interference you receive, including from other unlicensed users.

That bargain is the entire basis of Wi‑Fi, Bluetooth, Zigbee, and LoRa coexisting in the same spectrum.

### United States — FCC Part 15 (47 CFR Part 15)

- **Intentional radiators** (anything designed to emit RF) are governed by [47 CFR Part 15](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15). Every consumer Wi‑Fi/BT device is certified under Part 15 and carries an **FCC ID**.
- Key sub-parts: **§ 15.247** (digitally-modulated / frequency-hopping systems in 902–928 MHz, 2400–2483.5 MHz, 5725–5850 MHz), **§ 15.407** (U‑NII 5 GHz), plus power-spectral-density, out-of-band-emission, and — for 5 GHz — **DFS** (radar avoidance) and **TPC** requirements.
- The limits regulate **EIRP / conducted power, power spectral density, and spurious/out-of-band emissions**. A firmware patch that raises TX power, widens occupied bandwidth, transmits out of band, defeats DFS, or emits arbitrary waveforms will almost certainly push a *certified* device **out of compliance** — at which point it is no longer operating lawfully under Part 15, even inside the ISM band.
- **Certification travels with the as-tested firmware/hardware.** Re-flashing the PHY behaviour can legally void the device's authorization to radiate.

### European Union / EFTA — RED + ETSI harmonised standards

- The **Radio Equipment Directive 2014/53/EU (RED)** is the legal umbrella; the **CE** mark asserts conformity.
- Technical limits live in **ETSI harmonised standards**: **EN 300 328** (2.4 GHz wideband data), **EN 301 893** (5 GHz RLAN, with DFS/LBT), **EN 300 220** (sub‑GHz SRD 25–1000 MHz), **EN 305 550 / EN 302 567** (60 GHz), **EN 302 065** (UWB). These cap EIRP, PSD, duty cycle, and mandate polite-spectrum behaviours like **Listen-Before-Talk (LBT)** and **Adaptive Frequency Agility**.
- Sub‑GHz differs from the US: EU short-range devices commonly use **868 MHz** with **duty-cycle limits** (e.g. 1%), whereas the US uses **902–928 MHz** with different rules — a firmware "world mode" that ignores this is non-compliant in one region or the other.

### Everywhere else — check your national regulator

Spectrum is **national**. There is no global licence. Representative regulators:

- **UK** — Ofcom (IR 2030 interface requirements)
- **Canada** — ISED (RSS‑210 / RSS‑247)
- **Australia** — ACMA (LIPD Class Licence)
- **Japan** — MIC / certification via the "technical conformity" (技適, *giteki*) mark; transmitting on an uncertified device is an offence
- **India** — WPC; **Brazil** — ANATEL; **China** — SRRC

Band plans, power limits, and even *which* sub‑GHz frequencies are legal (433 vs 868 vs 915 MHz) vary between all of these. **A device legal in one country is frequently illegal to transmit with in another.**

### Bands that are never a free-for-all

Even hobby experimentation must stay clear of:

- **Aeronautical & radionavigation** (GPS/GNSS L1/L2/L5, ILS, radar altimeters, ADS‑B) — safety-of-life.
- **Emergency / public-safety, GMDSS maritime distress (156.8 MHz / Ch16), 406 MHz EPIRB/PLB.**
- **Cellular uplink/downlink** — licensed to carriers; even a "test" emitter is a serious offence and is exactly what illegal cell-site simulators do.
- **Weather / air-traffic / military radar** in and near 5 GHz — this is *why* DFS exists; defeating DFS to transmit into radar spectrum is a classic way to cause real harm.

---

## 3. Jamming: the bright red line

**Never build, sell, market, or operate a jammer.** A jammer is any device whose purpose is to *deliberately degrade, block, or override* authorized radio communication — including "Wi‑Fi deauth floods," "GPS blockers," "cell blockers," and broadband noise emitters.

- **US:** Jamming is prohibited under the Communications Act — **47 U.S.C. § 333** (no wilful/malicious interference to licensed/authorized stations) — and the manufacture, importation, marketing, sale, and *operation* of jammers is illegal under FCC rules. The FCC has issued substantial monetary penalties to individuals and businesses for operating even small personal jammers. See the FCC's jammer enforcement guidance: <https://www.fcc.gov/general/jammer-enforcement>.
- **EU/UK/most nations:** equivalent prohibitions exist; jammers are illegal to possess/use for the public.
- **"Deauth" / management-frame attacks** made trivial by injection-capable firmware are a form of denial-of-service against a radio service. Doing this to networks you do not own/administer is both an FCC interference violation *and*, in most countries, a **computer-misuse / unauthorized-interference criminal offence**.

There is no hobby exemption, no "it was only a few watts," and no amateur-licence exemption for jamming. Malicious interference is illegal on **every** band, licensed or not.

**Also treat as jamming-adjacent and out of bounds:** replaying captured transmissions of systems you don't own (garage doors, car key fobs, industrial telemetry), and spoofing (GNSS spoofing, rogue-AP/evil-twin emission) against anyone but your own isolated equipment.

---

## 4. Conducted lab testing vs. radiating into the air

This is the single most useful distinction for a firmware experimenter, because **it turns a regulated act into an unregulated bench measurement.**

- **Radiating** = an antenna is attached and RF leaves into free space, into shared spectrum, past people. This is the regulated act.
- **Conducted testing** = the antenna is replaced by a **coaxial cable** that carries the RF into instruments and terminations, so (ideally) *nothing escapes into the air*. You are measuring the signal on a wire.

If you want to characterize an arbitrary-waveform TX, verify an occupied bandwidth, or debug an injection patch, do it **conducted**:

```
[ chip u.FL/RF port ] --coax--> [ attenuator(s) ] --coax--> [ 50 Ω dummy load ]
                                       |
                                    (tap) --coax--> [ spectrum analyzer / SDR RX ]
```

- Replace the antenna with a **50 Ω dummy load** so the transmitter sees a proper match and the energy is dissipated as heat, not radiated.
- Put **attenuators** (e.g. 20–60 dB, correctly power-rated) between the DUT and any analyzer/SDR so you don't destroy the front end, and so leakage is tiny.
- Use a **directional coupler or power splitter** to tap a measurement copy while the bulk of the power lands in the dummy load.
- Realistically, cheap chips have **u.FL / IPEX** connectors or must have the chip antenna physically removed and a pigtail soldered on; MMCX/SMA pigtails are common. Board-level leakage still exists — see shielding below.

Conducted work is how professional RF labs develop transmitters legally. It is also just *better engineering*: repeatable, quantitative, and safe.

---

## 5. Practical containment — keeping your RF to yourself

When you must energize a real antenna, or your DUT leaks despite conducted setup, contain the energy. Options, roughly in order of cost/effectiveness:

| Method | What it is | Good for | Caveats |
|---|---|---|---|
| **Dummy load + attenuators** (§4) | Antenna replaced by 50 Ω termination | The default for TX development | Board/trace leakage still radiates a little; pair with shielding |
| **RF-tight / shielded enclosure** | A gasketed metal box (finger-stock/mesh EMI gasket) around the DUT | Blocking board-level leakage; small DUTs | Real attenuation depends on gasket integrity and cable feed-through filtering |
| **Shield/screen bag or tent** | Conductive-fabric Faraday bag or tent | Quick, cheap isolation; phone/IoT testing | Modest and frequency-dependent attenuation; verify, don't assume |
| **Faraday cage / screen room** | Room or cabinet with continuous conductive shielding, bonded seams, honeycomb vents, filtered power/data entry | Serious multi-device work | Any unfiltered cable or open seam is a leak path; needs bonding/grounding |
| **Anechoic / semi-anechoic chamber** | Shielded room lined with RF-absorbing material | Real emissions measurement | Lab-grade, expensive; usually institutional |

**Containment reality checks:**

- **Shielding is only as good as its worst seam or cable.** A perfect box with an unfiltered USB cable poking out is an antenna. Use **feed-through filters / bulkhead connectors**, ferrites, and keep the shield continuous.
- **Attenuation is frequency-dependent.** A bag rated at 2.4 GHz may leak badly at 60 GHz or sub‑GHz. Verify with a receiver: transmit a known signal inside, sweep outside, confirm the level drops into the noise.
- **Don't cook your DUT.** A transmitter emitting into a small closed metal box with no proper load can see high VSWR reflections and overheat its PA. Combine shielding with a real load.
- **Grounding matters** for both safety and shielding effectiveness — bond the enclosure.

The goal of all of this: your emissions never reach a neighbour's network, an aircraft, a pacemaker, or a licensed service.

---

## 6. RF exposure / SAR basics (protecting people, including yourself)

RF energy at these frequencies is **non-ionizing** — it does not break chemical bonds like X-rays. The established hazard is **tissue heating**. Regulators cap human exposure two ways:

- **SAR (Specific Absorption Rate)** — power absorbed per kilogram of tissue (W/kg), used for sources close to the body (phones, handhelds).
  - **US (FCC, from IEEE/ANSI C95.1):** partial-body limit **1.6 W/kg averaged over 1 g** of tissue (general population).
  - **EU / ICNIRP:** partial-body (head/trunk) limit **2.0 W/kg averaged over 10 g** of tissue.
- **MPE (Maximum Permissible Exposure)** — field-strength / power-density limits (e.g. **W/m²**) used for sources at a distance (antennas on masts). Limits are frequency-dependent and lower for the *general public* than for *occupational/controlled* exposure.

Primary references: [ICNIRP RF Guidelines (2020)](https://www.icnirp.org/en/publications/article/rf-guidelines-2020.html) · [FCC OET Bulletin 65, RF exposure evaluation](https://www.fcc.gov/general/oet-bulletins-line) · [FCC RF safety FAQ](https://www.fcc.gov/consumers/guides/wireless-devices-and-health-concerns).

**In practice for this catalog:** Wi‑Fi/BLE/sub‑GHz modules run at *milliwatts to a fraction of a watt* — normal use is far below exposure limits. Exposure only becomes a real concern if you **defeat power limits, add a high-gain amplifier/antenna, or stand in the near-field of a strong emitter (especially 5 GHz+ / mmWave / 60 GHz)**. Sensible bench hygiene:

- Don't put an energized transmit antenna against your body, eyes, or head — keep distance, especially at higher frequencies where energy is absorbed more superficially.
- Be extra cautious with **60 GHz** and any external **power amplifier**; small modules feeding a horn or a PA can create real near-field hot spots.
- If you have an implanted medical device (pacemaker/ICD), be conservative around any experimental transmitter.

---

## 7. The amateur ("ham") radio licence — a legitimate path to experiment

If you want to *legally transmit experimental and custom waveforms with real power*, the cleanest route is an **amateur radio licence**. Amateur radio is a licensed service explicitly meant for self-training, experimentation, and technical investigation — including building your own transmitters.

- **US:** governed by **47 CFR Part 97** (<https://www.ecfr.gov/current/title-47/part-97>). Three licence classes — **Technician, General, Amateur Extra** — earned by a multiple-choice exam (no Morse code required since 2007). You get a **call sign** and access to amateur allocations across HF/VHF/UHF/microwave, including **2.4 GHz, 5 GHz, 10 GHz** and higher amateur bands that *overlap* the ISM bands.
- **Spread spectrum / wideband experimentation** is permitted for licensed US amateurs on bands above 222 MHz (§ 97.305/§ 97.311) — this is a real, legal home for custom digital PHY work.
- **The rules you must honour as a licensed amateur:**
  - **Identify** with your call sign at required intervals — no anonymous transmission.
  - **No encryption to obscure meaning** of a message (you may authenticate/experiment within the rules, but not hide content).
  - **No broadcasting, no commercial use, no music**; amateur service is non-commercial.
  - **Stay in your privileges** — band, power (US general limit **1500 W PEP**, but use the *minimum* necessary), and mode for your licence class.
  - **Still no interference and no jamming** — a licence is permission to operate *within* rules, never to disrupt others.
- **Elsewhere:** equivalent licences exist (UK Ofcom Foundation/Intermediate/Full; most countries under ITU/CEPT frameworks, often with reciprocal operating agreements).

A ham licence does **not** authorize transmitting on *non-amateur* bands (you still can't legally emit on cellular, GNSS, or aviation frequencies), and it does **not** override Part 15 certification rules for *unlicensed* devices. But where amateur allocations overlap the bands these chips use, it converts "illegal experiment" into "licensed experiment."

---

## 8. Pre-TX checklist

Run this **every time** before you let a *Latent Radios* device radiate. If any answer is wrong, stop and go conducted (coax + dummy load) instead.

**Legality**
- [ ] I have identified the **exact frequency/band** I will emit on, and it is one I am **authorized** to use here (unlicensed ISM within limits, *or* an amateur band I'm licensed for, *or* a band I hold a licence for).
- [ ] I am **not** transmitting on aeronautical, GNSS, cellular, maritime/aviation distress, public-safety, or any safety-of-life band.
- [ ] My power, bandwidth, duty cycle, and out-of-band emissions are **within the local limits** (FCC Part 15 / ETSI EN 300 328 etc. / national regulator), or the emission is fully contained (§4–5).
- [ ] I am **not** jamming, deauthing, replaying, or spoofing any system I do not own and control.
- [ ] I know the rules of **the country I am physically in** — not just the US/EU defaults.

**Containment**
- [ ] Antenna is replaced by a **dummy load**, *or* the DUT is inside verified shielding, *or* both.
- [ ] Any measurement path uses **correctly-rated attenuators**; no analyzer/SDR front end is exposed to full TX power.
- [ ] I have **verified** containment by transmitting a known signal and confirming it's not detectable outside my setup / not reaching other networks.
- [ ] Cables entering shielding are **filtered/ferrited**; the enclosure is bonded/grounded.

**Safety of people & hardware**
- [ ] No energized TX antenna is near anyone's body/head/eyes; extra distance for PA / 5 GHz+ / 60 GHz.
- [ ] The PA sees a **proper 50 Ω load** (no open/short into a small box) so it won't overheat.
- [ ] Anyone with an implanted medical device is clear of the near field.

**Discipline**
- [ ] I will emit the **minimum power** and **shortest duration** needed to get my measurement.
- [ ] I am **logging** what I transmit (freq, power, time) so I can prove what I did.
- [ ] If I see interference to anyone else, I **stop immediately**.

---

## 9. The three rules that override everything

1. **Never jam.** Deliberately degrading anyone's radio service is illegal on every band and is never part of legitimate research.
2. **Never transmit on bands or services you are not authorized for.** ISM limits, amateur privileges, and licences define *where* — stay strictly inside them.
3. **Never interfere with safety-of-life systems.** Aviation, GNSS, maritime distress, emergency and public-safety radio, and medical devices come before any experiment. When unsure, the safe experiment is a *receive-only* or *conducted* one.

---

## References

- FCC — 47 CFR Part 15 (Radio Frequency Devices): <https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15>
- FCC — 47 CFR Part 97 (Amateur Radio Service): <https://www.ecfr.gov/current/title-47/part-97>
- Communications Act — 47 U.S.C. § 333 (Willful or malicious interference): <https://www.govinfo.gov/link/uscode/47/333>
- FCC — Jammer Enforcement: <https://www.fcc.gov/general/jammer-enforcement>
- FCC — GPS, Wi‑Fi, and Cell Phone Jammers consumer guide: <https://www.fcc.gov/consumers/guides/gps-wi-fi-and-cell-phone-jammers>
- FCC — OET Bulletins (incl. Bulletin 65, RF exposure): <https://www.fcc.gov/general/oet-bulletins-line>
- FCC — Wireless devices and health concerns / RF safety FAQ: <https://www.fcc.gov/consumers/guides/wireless-devices-and-health-concerns>
- ICNIRP — Guidelines for limiting exposure to EMF (100 kHz–300 GHz), 2020: <https://www.icnirp.org/en/publications/article/rf-guidelines-2020.html>
- EU — Radio Equipment Directive 2014/53/EU (RED): <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32014L0053>
- ETSI — EN 300 328 (2.4 GHz wideband data transmission): <https://www.etsi.org/deliver/etsi_en/300300_300399/300328/>
- ETSI — EN 301 893 (5 GHz RLAN): <https://www.etsi.org/deliver/etsi_en/301800_301899/301893/>
- ETSI — EN 300 220 (sub‑GHz SRD): <https://www.etsi.org/deliver/etsi_en/300200_300299/30022001/>
- Ofcom (UK) — Licence-exempt / IR 2030: <https://www.ofcom.org.uk/spectrum/interface-requirements>
- ISED (Canada) — RSS‑247 / RSS‑210: <https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss>
- ARRL — Getting a US amateur radio licence: <https://www.arrl.org/getting-licensed>

---

*Part of the [Latent Radios](../README.md) catalog. See also the [technique index](../docs/techniques.md) for the RX/sensing capabilities that are the safe default for experimentation.*
