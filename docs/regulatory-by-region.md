# RF Regulatory Quick-Reference, by Region

> **Orientation, not legal advice.** This page is a fast mental map of who regulates
> what in the bands this repository touches (2.4 / 5 / 6 GHz ISM & U-NII, sub-GHz
> 433 / 868 / 915–920 MHz, 60 GHz, GPS L1, and cellular). Limits are summarized at a
> responsible high level and change often. **Before you transmit anything, check the
> current rules from your own national regulator** — the actual binding numbers live in
> the eCFR, ETSI ENs, Ofcom IRs, and MIC/ARIB standards, not here.
>
> This is a companion to [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md),
> which covers the ethics, RF-exposure, and safety framing. Read that first if you have
> not. See also [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md) for the
> "why receive-mostly" argument that underpins everything below.

The whole point of this project — firmware-repurposed Wi-Fi/wireless chips — is that a
chip which was *type-certified as a Wi-Fi radio* can, once you patch its firmware, emit
things the certification never covered (arbitrary waveforms, out-of-mask energy,
continuous carriers, injection at odd rates). **The certification does not travel with the
new behavior.** A device legal to *operate* as a Wi-Fi card can become an illegal
*intentional radiator* the moment your firmware makes it do something outside the granted
authorization. This page exists so you know which line you are standing near.

---

## The universal rules (true almost everywhere)

These hold across essentially every jurisdiction on Earth. If you remember nothing else,
remember these five:

1. **No jamming. Ever.** Deliberately transmitting to deny, degrade, or disrupt others'
   communications is illegal in effectively every country — no license, band, or power
   level makes it legal. In the US it is barred outright by the Communications Act (see
   below); most other regulators treat it identically. This includes "just my own house"
   Wi-Fi/cellular/GPS jammers sold online.
2. **No unauthorized transmission.** Transmitting requires *either* operating within a
   license-exempt allocation *and* within that allocation's technical limits, *or* holding
   a license (amateur, experimental, commercial) that authorizes it. "License-exempt" is
   not "rule-exempt."
3. **No interference to safety-of-life services.** GNSS (GPS/Galileo/GLONASS/BeiDou),
   aeronautical, maritime distress, and emergency-services spectrum are protected with the
   highest priority. Interfering with them can carry criminal, not just administrative,
   penalties.
4. **Type-approval / conformity matters.** Many countries make it illegal to *operate* an
   intentional radiator that lacks the local conformity mark (FCC ID in the US, CE/UKCA
   marking + supplier declaration in EU/UK, the giteki 技適 mark in Japan). Custom
   firmware voids the original grant's assumptions.
5. **Receiving is much safer than transmitting — but not unconditionally free.** Passive RX
   is legal in most places for most bands, which is exactly why this repo leans
   receive-first (monitor, CSI, spectral scan, passive-radar). Caveats: some countries
   restrict *receiving* certain bands (e.g., cellular, or "any service not addressed to
   you"), and even where reception is legal, *acting on* or *divulging* intercepted content
   can be a separate offense (e.g., US 47 U.S.C. § 605). **Listening is the low-risk path;
   default to it.**

Everything specific to a chip in [../chips/](../chips/hardware-index.md) that reaches
**Tier 4–5** (arbitrary-waveform / raw-IQ TX, per [taxonomy.md](../docs/taxonomy.md))
lives on the *transmit* side of rule 2 and is where you must be most careful. Tier 0–3
work (diagnostics, CSI, spectral, monitor) is overwhelmingly receive-side.

---

## United States — FCC

The FCC administers civilian spectrum under the **Communications Act of 1934** (Title 47,
U.S. Code) via rules in **Title 47 of the Code of Federal Regulations (CFR)**.

### Part 15 — unlicensed / license-exempt devices (47 CFR Part 15)

Part 15 is the home of Wi-Fi, Bluetooth, Zigbee, most ISM gear, and the bands this repo
cares about. The bargain of Part 15 §15.5: your device **must accept any interference**
received and **must not cause harmful interference** — and if it does, you shut it down.
There is no protection and no entitlement.

Key sections and the bands they govern:

| Rule section | Band | Rough limit (typical modes) | Notes |
|---|---|---|---|
| **§15.247** | 902–928 MHz, 2400–2483.5 MHz, 5725–5850 MHz | 1 W (30 dBm) max conducted; up to 4 W (36 dBm) EIRP with 6 dBi antenna | Digital-modulation / frequency-hopping. Point-to-point 2.4 GHz links may trade antenna gain above 6 dBi for TX power at 1 dB per 3 dB (a relaxation); 900 MHz & 5.8 GHz P2P trade at a stricter ratio. |
| **§15.249** | 902–928, 2400–2483.5, 5725–5875 MHz | ~50 mV/m field strength (much lower, ~0.75 mW EIRP class) | Low-power option; common for simple remotes/telemetry. |
| **§15.231 / §15.240** | 433 MHz region, 315 MHz, etc. | Periodic / low-duty field-strength limits | US 433 MHz is *not* a general ISM playground; 433.05–434.79 is primarily amateur 70 cm and constrained Part 15 periodic devices. |
| **§15.407** | U-NII: 5150–5250 (U-NII-1), 5250–5350 (U-NII-2A), 5470–5725 (U-NII-2C), 5725–5850 (U-NII-3) | ~30 dBm + PSD limits; higher EIRP outdoors in some sub-bands | **DFS** (radar avoidance) mandatory in U-NII-2A/2C; **TPC** required in parts. |
| **§15.407 (2020 6 GHz order)** | U-NII-5–8: 5925–7125 MHz | **LPI** (low-power indoor): 5 dBm/MHz PSD, 30 dBm max EIRP, indoor only, no external antenna. **Standard-power**: up to 23 dBm/MHz PSD, but only under **AFC** control. **VLP** (very-low-power) portable also defined. | Wi-Fi 6E/7 band. AFC = Automated Frequency Coordination protects incumbents. |
| **§15.255** | 57–71 GHz | Up to 40 dBm average / 43 dBm peak EIRP (with emission-mask & elevation conditions) | The 60 GHz band (802.11ad/ay). Very high EIRP is *allowed* precisely because oxygen absorption kills range — see [../chips/](../chips/hardware-index.md) 60 GHz entries. |

Practical reading for this repo: patched Wi-Fi firmware that **stays inside** the granted
channel plan, power, and emission mask is operating in the same envelope as the stock
radio. Firmware that emits **out-of-band energy, a continuous unmodulated carrier, or
injection outside the digital-modulation assumptions** of §15.247/§15.407 is no longer
covered by the device's grant, even if the average power looks small.

### Part 97 — Amateur Radio (47 CFR Part 97)

A licensed amateur (Technician / General / Extra) may build, modify, and experiment with
transmitters on amateur allocations — including **70 cm (420–450 MHz, covers 433)**,
**33 cm (902–928, shared with Part 15)**, **13 cm (2390–2450)**, **9 cm / 5 cm (parts of
5 GHz)**, and millimeter bands. This is the *legitimate* route to Tier 4–5 arbitrary-TX
experimentation. Constraints: you must **transmit only within your privileges**, **identify
your station** (call sign) at required intervals, **not encrypt to obscure meaning**, **not
broadcast** or transmit music/commercial content, and stay within power limits (up to
1500 W PEP on many bands, far lower where shared). Amateur privileges do **not** authorize
transmitting on Wi-Fi/cellular/GPS *service* frequencies as those services — they authorize
*amateur* operation on *amateur* allocations that happen to overlap.

### Jammers are flatly illegal

Signal jammers (Wi-Fi, cellular, GPS, Bluetooth, "universal") are illegal to **import,
market, sell, or operate** in the US, for **anyone** including private individuals, with no
"personal use" exception. The prohibition rests on the Communications Act:

- **47 U.S.C. § 301** — you may not transmit without a license/authorization.
- **47 U.S.C. § 302a** — bans manufacture, import, sale, or shipment of devices that fail
  to comply with FCC regulations (jammers cannot comply).
- **47 U.S.C. § 333** — "No person shall willfully or maliciously interfere with or cause
  interference to any radio communications of any station licensed or authorized" under the
  Act or operated by the US government.

The FCC pursues this actively; penalties include large fines and equipment seizure. GPS
jammers are treated especially harshly because of the safety-of-life dimension.

Primary sources: [eCFR Title 47 Part 15](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15),
[eCFR Title 47 Part 97](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97),
[FCC Jammer Enforcement](https://www.fcc.gov/general/jammer-enforcement),
[47 U.S.C. § 333](https://www.law.cornell.edu/uscode/text/47/333).

---

## Europe — CEPT / ETSI (EU + EEA, broadly EFTA)

In Europe, spectrum harmonization is set by **CEPT** (and the EU via the RE Directive
2014/53/EU); the **Harmonised Standards** written by **ETSI** define the technical
conformity a device demonstrates for CE marking. **ERC Recommendation 70-03** is the
umbrella catalogue for Short-Range Devices (SRDs). Europe generally expresses microwave
limits as **EIRP** and sub-GHz SRD limits as **ERP** (dipole reference; ERP ≈ EIRP − 2.15 dB).

| ETSI standard | Band | Typical limit | Notes |
|---|---|---|---|
| **EN 300 328** | 2400–2483.5 MHz | **100 mW (20 dBm) EIRP** | Wi-Fi/BT. Much lower than US 2.4 GHz — a device legal in the US at 30 dBm is illegal here. Adaptivity (LBT/duty) required. |
| **EN 301 893** | 5150–5350 MHz | 5150–5250: **200 mW EIRP indoor**; 5250–5350: **200 mW indoor**, DFS + TPC | Indoor-only in this range. |
| **EN 301 893** | 5470–5725 MHz | **1 W (30 dBm) EIRP**, DFS + TPC | Outdoor permitted; radar protection mandatory. |
| **EN 303 687** | 5945–6425 MHz (lower 6 GHz) | **LPI: 200 mW (23 dBm) EIRP, 10 dBm/MHz PSD, indoor**; **VLP: 25 mW EIRP** portable/outdoor | Wi-Fi 6E in the EU is only the *lower* 6 GHz sub-band (unlike the full US 5925–7125). |
| **EN 300 220** | 433.05–434.79 MHz | typ. **10 mW ERP**, duty-cycle limited | The classic "433 MHz" SRD band in Europe (remotes, sensors). |
| **EN 300 220** | 863–870 MHz (the "868 MHz" band) | typ. **25 mW (14 dBm) ERP** with **0.1 % / 1 % duty cycle**; 869.4–869.65 MHz allows **500 mW @ 10 % duty** | LoRa/Sigfox/Z-Wave/EnOcean home here. Sub-band-specific duty cycles are the real constraint, not just power. |
| **EN 302 567 / EN 305 550** | 57–71 GHz | up to **40 dBm EIRP** (band-plan dependent) | 60 GHz / WiGig. |

Note the sharp US↔EU divergence: **915 MHz is a US ISM band; Europe's SRD workhorse is
868 MHz** (a device firmware-tuned to 915 MHz may be *illegal to transmit* in the EU and
vice-versa). And **EU 2.4 GHz caps at 100 mW EIRP vs. the US's 1 W conducted / 4 W EIRP** —
a frequent trap for people flashing region-agnostic firmware.

Primary sources: [ETSI EN 300 328](https://www.etsi.org/deliver/etsi_en/300300_300399/300328/),
[ETSI EN 301 893](https://www.etsi.org/deliver/etsi_en/301800_301899/301893/),
[ETSI EN 303 687](https://www.etsi.org/deliver/etsi_en/303600_303699/303687/),
[ETSI EN 300 220](https://www.etsi.org/deliver/etsi_en/300200_300299/30022001/),
[ERC Recommendation 70-03 (ECO documentation)](https://www.ecodocdb.dk/).

---

## United Kingdom — Ofcom

Post-Brexit the UK still **broadly mirrors CEPT/ETSI** for these bands, but the binding
document is Ofcom's **Interface Requirement IR 2030** ("UK Interface Requirements for
licence-exempt SRDs") plus IR 2005/2006/2007 for Wi-Fi/RLANs. Conformity marking is
**UKCA** (with CE still accepted during the transition arrangements). Practically:

- **2.4 GHz Wi-Fi**: 100 mW EIRP, licence-exempt (as EN 300 328).
- **5 GHz RLAN**: 5150–5350 indoor 200 mW; 5470–5725 at 1 W with DFS — as EN 301 893.
- **6 GHz**: lower 6 GHz (5925–6425) adopted for licence-exempt LPI/VLP Wi-Fi.
- **Sub-GHz SRD**: 433 MHz and 863–870 MHz per IR 2030, aligned with EN 300 220 power/duty.
- **Jamming / unauthorized TX**: offences under the **Wireless Telegraphy Act 2006** —
  operating a transmitter without a licence or exemption, and deliberate interference, are
  criminal offences enforced by Ofcom.

Primary source: [Ofcom UK Interface Requirements (IR 2030 etc.)](https://www.ofcom.org.uk/spectrum/information/uk-interface-requirements).

---

## Japan — MIC / ARIB

Japan's **Ministry of Internal Affairs and Communications (MIC)** regulates spectrum under
the Radio Law; **ARIB** (Association of Radio Industries and Businesses) writes the
technical standards. A distinctive, strictly enforced feature: **any transmitter must carry
the giteki (技適 / Technical Conformity) mark.** Operating an uncertified transmitter —
including a foreign Wi-Fi device without Japanese certification, or a firmware-modified one
whose certification no longer applies — is an offence, even for otherwise "harmless" ISM use.

| Band | Standard | Notes |
|---|---|---|
| **2.4 GHz** | ARIB STD-T66 | ~10 mW/MHz limit; Wi-Fi/BT. |
| **5 GHz — W52 (5150–5250), W53 (5250–5350)** | ARIB STD-T71 | Indoor-only; W53 requires DFS. |
| **5 GHz — W56 (5470–5725)** | ARIB STD-T71 | Outdoor permitted, DFS. |
| **5.8 GHz — W58 (5770–5850)** | (DSRC/ETC) | Reserved for road-tolling/ITS, **not** general Wi-Fi. |
| **6 GHz** | ARIB (per MIC 6 GHz rollout) | Lower 6 GHz opened for Wi-Fi 6E LPI/VLP. |
| **920 MHz band (915–928 MHz)** | **ARIB STD-T108** | Japan's LPWA/RFID band (LoRa, Wi-SUN, passive RFID). Replaced the legacy 950 MHz band. Channels with specified-low-power (~20 mW) or, with additional registration, up to 250 mW. This is the Japanese analogue of the US 915 MHz / EU 868 MHz SRD band — and again, **not interchangeable**: firmware set to 915 MHz US limits will violate T108 channelization/duty rules. |
| **GPS L1 etc.** | receive-only | No licence to receive; transmitting/jamming illegal. |

Primary sources: [ARIB (English)](https://www.arib.or.jp/english/),
[MIC — Radio Use Web / Tele (spectrum policy)](https://www.tele.soumu.go.jp/e/index.htm).

---

## The receive-only bands: GNSS and cellular

Two band groups in this repo are **essentially receive-only for anyone without a specific
license**, and the honest tier ceiling reflects it (see
[../chips/cellular-basebands.md](../chips/cellular-basebands.md) and the GNSS entries in
[../chips/hardware-index.md](../chips/hardware-index.md)).

- **GNSS / GPS L1 (1575.42 MHz), L2, L5, and the Galileo/GLONASS/BeiDou equivalents.**
  Receiving is unlicensed and legal worldwide; it is how every phone gets a fix. What you
  can extract from a repurposed GNSS chip is **measurement data** — raw pseudorange/carrier-
  phase/Doppler observables, sometimes raw IQ on research front-ends — which is Tier 0–2
  *receive* territory, never transmit. **Transmitting on GNSS frequencies is one of the most
  dangerous and heavily prosecuted RF acts there is**: even a low-power GPS "personal privacy
  device" has knocked out airport approaches. Do not. There is no hobbyist exception.

- **Cellular (LTE/5G/legacy) bands.** These are **licensed spectrum owned by carriers.**
  A phone transmits only because it is an authenticated device on that carrier's network,
  under the carrier's authorization. Standing up your own base station (IMSI-catcher, rogue
  eNB/gNB, uplink transmitter) without an experimental license is illegal in essentially
  every country and is exactly the safety-of-life / lawful-interception line regulators guard
  hardest. What a baseband realistically gives a reverse-engineer is **diagnostic/measurement
  access** (e.g., Qualcomm `diag`/QCSuper, cell/signal logs, occasionally raw layer-1 metrics)
  — Tier 0–1, receive/monitor side. Do not confuse "I can read the modem's diagnostics" with
  "I can transmit"; the second is a different legal universe. Even *receiving* others'
  cellular content can be an offence (interception laws) separate from spectrum rules.

The takeaway for this catalog: cellular basebands and GNSS chips are **not** paths to
arbitrary IQ. They are paths to *data*. The repo tags them low-tier for that reason — see
the honest-tier discipline in [../docs/taxonomy.md](../docs/taxonomy.md).

---

## Consolidated per-band table

Power figures are **typical headline limits, rounded** — sub-bands, duty-cycle rules,
antenna-gain trades, DFS/TPC/AFC conditions, and indoor/outdoor splits all move the real
number. Treat this as a map, not a datasheet. "Licensed?" = whether *unlicensed/licence-
exempt* operation is generally available to the public in that region.

| Band | Region | Licence-exempt TX? | Typical power ceiling | Notes |
|---|---|---|---|---|
| **433 MHz** | US | Restricted (Part 15 periodic) / amateur 70 cm | very low field-strength | Not a general ISM band in the US. |
| **433 MHz** | EU/UK | Yes (SRD) | ~10 mW ERP, duty-limited | EN 300 220 / IR 2030. |
| **433 MHz** | Japan | Largely no (amateur/limited) | — | Not a general SRD band; 920 MHz is the LPWA band. |
| **868 MHz** | EU/UK | Yes (SRD) | 25 mW ERP (500 mW @ 10 % in 869.4–869.65) | Duty cycle is the real limit. LoRa/Z-Wave. |
| **902–928 MHz (915)** | US | Yes (Part 15 §15.247) | 1 W conducted / up to 4 W EIRP | US ISM workhorse. |
| **915–928 MHz (920)** | Japan | Yes (ARIB T108) | ~20 mW (up to 250 mW w/ registration) | Wi-SUN/LoRa/RFID; channelized. |
| **sub-GHz** | (universal) | — | — | 915 ≠ 868 ≠ 920: **not interchangeable across regions.** |
| **2.4 GHz** | US | Yes (§15.247) | 1 W conducted / 4 W EIRP (P2MP) | Antenna-gain trade for P2P. |
| **2.4 GHz** | EU/UK | Yes (EN 300 328) | **100 mW EIRP** | ~16 dB lower than US — common trap. |
| **2.4 GHz** | Japan | Yes (T66) | ~10 mW/MHz | Giteki mark required. |
| **5 GHz (U-NII/W52–56)** | US | Yes (§15.407) | ~30 dBm + PSD; higher EIRP outdoors | DFS/TPC in radar sub-bands. |
| **5 GHz** | EU/UK | Yes (EN 301 893) | 200 mW indoor (5.15–5.35) / 1 W (5.47–5.725) | Indoor-only lower band; DFS. |
| **5 GHz** | Japan | Yes (T71) | W52/W53 indoor, W56 outdoor | W58 = DSRC, off-limits for Wi-Fi. |
| **6 GHz** | US | Yes (§15.407, 2020) | LPI 30 dBm EIRP indoor / Std-power via AFC | Full 5925–7125. |
| **6 GHz** | EU/UK | Yes (EN 303 687) | LPI 200 mW indoor / VLP 25 mW | Lower 6 GHz only (5945–6425). |
| **6 GHz** | Japan | Yes (MIC) | LPI/VLP | Lower 6 GHz. |
| **60 GHz** | US | Yes (§15.255) | up to 40 dBm avg EIRP | High EIRP OK — O₂ absorption limits range. |
| **60 GHz** | EU/UK | Yes (EN 302 567) | up to ~40 dBm EIRP | Band-plan dependent. |
| **GPS L1 (1575.42 MHz)** | All | **RX only** (no licence to receive) | TX **prohibited** | Safety-of-life; jamming heavily prosecuted. |
| **Cellular (LTE/5G)** | All | **No** (carrier-licensed) | TX only as an authorized network device | Rogue base stations illegal everywhere. |

---

## How to actually check (do this, don't guess)

- **US** — read the exact section in the [eCFR Title 47](https://www.ecfr.gov/current/title-47);
  the FCC's [Equipment Authorization / OET](https://www.fcc.gov/oet) pages for grants.
- **EU** — the relevant [ETSI Harmonised Standard](https://www.etsi.org/standards) for your
  band + national administration's implementation; [ERC/REC 70-03](https://www.ecodocdb.dk/).
- **UK** — [Ofcom IR 2030 and RLAN IRs](https://www.ofcom.org.uk/spectrum/information/uk-interface-requirements).
- **Japan** — [MIC/Tele](https://www.tele.soumu.go.jp/e/index.htm) and the applicable
  [ARIB standard](https://www.arib.or.jp/english/); confirm the giteki requirement.
- **Anywhere else** — find your **national spectrum regulator** and its national frequency
  allocation table. Assume nothing carries over from the US/EU numbers above.

When in doubt: **receive, don't transmit** (rule 5), keep any experimentation inside a
licence you actually hold (Part 97 / equivalents), and never point Tier 4–5 firmware at
GNSS, cellular, or safety-of-life spectrum. The safest lab is a shielded enclosure /
[../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md)-compliant setup where your
emissions never reach the outside world in the first place.

---

## References

- [eCFR — 47 CFR Part 15 (Radio Frequency Devices)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15)
- [eCFR — 47 CFR Part 97 (Amateur Radio Service)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97)
- [FCC — Jammer Enforcement](https://www.fcc.gov/general/jammer-enforcement)
- [47 U.S.C. § 333 (willful/malicious interference)](https://www.law.cornell.edu/uscode/text/47/333)
- [47 U.S.C. § 302a (devices)](https://www.law.cornell.edu/uscode/text/47/302a)
- [FCC — Office of Engineering and Technology](https://www.fcc.gov/oet)
- [ETSI EN 300 328 (2.4 GHz wideband)](https://www.etsi.org/deliver/etsi_en/300300_300399/300328/)
- [ETSI EN 301 893 (5 GHz RLAN)](https://www.etsi.org/deliver/etsi_en/301800_301899/301893/)
- [ETSI EN 303 687 (6 GHz WAS/RLAN)](https://www.etsi.org/deliver/etsi_en/303600_303699/303687/)
- [ETSI EN 300 220 (sub-GHz SRD, 25–1000 MHz)](https://www.etsi.org/deliver/etsi_en/300200_300299/30022001/)
- [CEPT ERC Recommendation 70-03 (ECO Documentation DB)](https://www.ecodocdb.dk/)
- [Ofcom — UK Interface Requirements](https://www.ofcom.org.uk/spectrum/information/uk-interface-requirements)
- [ARIB (English)](https://www.arib.or.jp/english/)
- [MIC — Telecommunications / spectrum (English)](https://www.tele.soumu.go.jp/e/index.htm)
- Companion pages in this repo: [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md), [../docs/taxonomy.md](../docs/taxonomy.md), [../chips/cellular-basebands.md](../chips/cellular-basebands.md)

> Reiterating the header: **orientation only, not legal advice, and not exhaustive.**
> Regulations change, sub-band conditions abound, and the binding text is your national
> regulator's — go read it before you key up.
