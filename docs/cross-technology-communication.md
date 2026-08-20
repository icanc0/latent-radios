# Cross-Technology Communication (CTC): Making One Radio Speak Another's Language

The 2.4 GHz ISM band is a shared apartment. Wi-Fi, Bluetooth/BLE, and 802.15.4 (ZigBee,
Thread) all live in it, overlap in frequency, and — by design — cannot understand each
other. Cross-Technology Communication (CTC) is the research line that breaks that wall
*without adding a gateway*: it makes an **unmodified** (or lightly patched) radio of one
standard deliver bits to the receiver of a **different** standard, by exploiting what the two
PHYs happen to share.

This is a **techniques** page, not a chip page. It is the "make one radio impersonate
another" verb from the CTC row of [../docs/techniques.md](../docs/techniques.md), expanded.
Nothing here is new silicon — every chip involved (Broadcom/Cypress Wi-Fi, Nordic/TI BLE,
TI/Silabs 802.15.4) is already in the catalog. What is new is a way to *use* those radios,
and the honest question this page answers is: **which rung of the [SDR ladder](../docs/taxonomy.md)
does each CTC trick actually require, and how fragile is it?**

> **Blanket caution.** Every transmit-side technique below emits energy the regulator did
> not expect from that device: a Wi-Fi card producing a ZigBee-shaped envelope, a BLE radio
> whitening a payload into a foreign waveform, or (Tier 4) a Wi-Fi front-end playing a raw
> IQ buffer. Most of this is legal *as generic Part 15 emission on your own hardware in the
> ISM band* — but concurrent-transmission, out-of-mask spurs, and covert use are exactly the
> regulatory grey zone flagged in [../docs/verification-tier4.md](../docs/verification-tier4.md).
> Treat TX experiments as shielded-enclosure / own-devices work. See **Caveats** at the end.

---

## 1. The one-sentence idea

Two radios that cannot demodulate each other's frames can still **agree on a physical
quantity they both observe**. CTC schemes differ only in *which* quantity:

- **Energy / RSSI over time** — every radio can measure "is the channel busy, how loud?"
- **Packet timing / gaps / lengths** — every MAC can time-stamp what it hears.
- **The actual baseband waveform** — if transmitter A can be coerced into emitting a
  time-domain signal that receiver B's *native demodulator* accepts as a valid B-frame.

The first two are **packet-level** (side-channel) CTC and need nothing but ordinary frames.
The third is **physical-level** (emulation) CTC and is where things get interesting for this
catalog — because "coerce radio A into emitting radio B's waveform" is a spectrum that runs
from *clever payload selection on a stock Wi-Fi card* (Tier 1) all the way to *authoring raw
IQ in Template RAM* (Tier 4).

---

## 2. Taxonomy: packet-level vs physical-level CTC

```
                        CROSS-TECHNOLOGY COMMUNICATION
                                     |
        +----------------------------+-----------------------------+
        |                                                          |
  PACKET-LEVEL (side-channel)                          PHYSICAL-LEVEL (emulation)
  "modulate a legal frame stream"                      "shape the actual waveform"
        |                                                          |
   receiver senses ENERGY / TIMING                    receiver's NATIVE DEMODULATOR
   (RSSI, gaps, lengths, durations)                    decodes it as a real frame
        |                                                          |
   throughput: ~bits/s ... few hundred b/s            throughput: ~native foreign PHY rate
   hardware: Tier 1 (stock frames)                    hardware: Tier 1 emulation  ->  Tier 4 raw IQ
   examples: Esense, GapSense, FreeBee,               examples: WEBee, TwinBee, LEGO-Fi,
             C-Morse, HoWiES, DCTC                              BlueBee, BlueFi, WIDE, Nexmon-SDR
```

### 2a. Packet-level (side-channel) CTC

The transmitter never leaves its own standard. It sends **perfectly legal frames** and
modulates information into a property the foreign receiver can measure *without decoding
them*: the pattern of channel-busy energy (Esense), deliberate silent gaps (GapSense),
the phase/timing of periodic beacons (FreeBee), or subtle, standard-compliant perturbations
of an ongoing traffic stream (C-Morse). The receiver runs an **energy/RSSI sampler or a
timer**, not a demodulator.

- **Pros:** works on genuinely unmodified commodity radios, both ends; robust; needs only
  Tier 1 (and often not even injection — just the ability to shape a traffic stream).
- **Cons:** brutally low throughput — from a few bits per second (timing schemes) to a few
  hundred b/s at best — because one "symbol" costs one or more whole packets or gaps.

### 2b. Physical-level (emulation) CTC

The transmitter crafts its **own** standard-compliant transmission such that the emitted
**time-domain waveform** is close enough to a target foreign waveform that the target's
*unmodified hardware demodulator* locks onto it and outputs a valid frame. The receiver does
nothing special — it thinks it heard one of its own kind.

The magic is entirely on the transmit side, and it comes in two grades:

1. **Payload-selection emulation (Tier 1 hardware).** Keep using the source radio's normal
   modulator, but *choose the payload bits* so that after the source PHY's own
   modulation/whitening/IFFT, the resulting samples approximate the target waveform. WEBee,
   TwinBee, LEGO-Fi, BlueBee, and BlueFi all do this. Remarkably, this needs **no firmware
   arbitrary-waveform hook at all** — a stock Wi-Fi or BLE transmitter, driven with a
   carefully computed frame, is doing the emulation. The cost is *quantization error*: the
   source PHY can only produce a discrete set of waveforms, so the emulation is approximate
   and therefore lossy/fragile (Section 6).

2. **Raw-IQ emulation (Tier 4 hardware).** If you *can* author baseband IQ — e.g. Nexmon's
   SDR patch writing Template RAM on a BCM4339 (Section 5) — you sidestep quantization
   entirely and emit the *exact* foreign waveform. This is the cleanest CTC and the only one
   that needs to climb the ladder, and it inherits every Tier-4 caveat.

### 2c. Directionality is not free

CTC is inherently **asymmetric**. Emitting a foreign waveform (TX-side emulation) and
*decoding* a foreign waveform (RX-side) are different problems needing different capabilities:

- **High-rate radio -> low-rate radio** (Wi-Fi/BLE emulating ZigBee) is the "easy" direction:
  the fast, wideband source has enough time/frequency resolution to *sculpt* the slow
  target's waveform. This is WEBee/BlueBee's direction.
- **Low-rate radio -> high-rate radio** (ZigBee -> Wi-Fi) or *receiving* a foreign PHY needs
  the receiver to expose PHY telemetry it normally hides — CSI (Tier 2), spectral bins
  (Tier 3), or raw IQ (Tier 4/5). WIDE decodes ZigBee at a Wi-Fi receiver via digital
  emulation; BlueFi deliberately makes Wi-Fi both *emit and receive* Bluetooth, and that RX
  path is why it is more than a party trick.

---

## 3. Where each CTC style sits on the SDR ladder

| CTC style | Example | Min **tier** | Capability flag(s) | What the silicon must expose |
|---|---|---|---|---|
| Energy/RSSI side-channel | Esense, HoWiES | **1** | `covert-channel` | Send frames; RX energy/RSSI sampling |
| Timing / gap side-channel | GapSense, FreeBee | **1** | `covert-channel` | Frame TX timing; RX carrier-sense timer |
| Traffic-perturbation side-channel | C-Morse, DCTC | **1** | `covert-channel` | Shape an ongoing legal traffic stream |
| Symbol-level payload encoding | Symbol-level CTC (ICDCS'18) | **1** | `covert-channel` | Full payload control within a frame |
| PHY emulation, payload-selected | WEBee, TwinBee, LEGO-Fi | **1** | `covert-channel` (+`injection`) | Byte-exact payload; source modulator does the rest |
| PHY emulation from BLE | BlueBee, BlueFi (TX) | **1** | `covert-channel` | BLE payload/whitening control |
| Foreign-PHY reception at Wi-Fi | WIDE, BlueFi (RX) | **2–3** | `csi` / `spectral-scan` | Subcarrier or raw spectral telemetry |
| Raw-IQ emulation (exact waveform) | Nexmon SDR emitting any PHY | **4** | `arbitrary-waveform`, `covert-channel` | Author time-domain IQ buffer + key TX |

The headline, and the honest point of this page: **almost all famous CTC is Tier 1.** The
cleverness is in the *math of payload selection*, not in unlocking the radio. Only the
raw-IQ variant is a true climb up the ladder, and only the reception side forces you into
Tier 2+.

---

## 4. Physical-level emulation, the flagship trick (WEBee and its family)

**WEBee** (Li & He, MobiCom 2017) is the paper that made "one radio speaks another's PHY" a
field. Target: make a **stock 802.11 Wi-Fi** transmitter emit a signal that a **stock 802.15.4
ZigBee** receiver decodes as a legitimate ZigBee frame.

**How the emulation works (conceptually):**

1. A ZigBee (O-QPSK/DSSS) frame has a known target **time-domain baseband waveform** `T[n]`.
2. A Wi-Fi 802.11 OFDM symbol is built by an IFFT over subcarriers whose values are set by
   the **payload bits** (through the constellation mapper). So the transmitted Wi-Fi
   time-domain samples `W[n]` are a *function of the payload you choose*.
3. WEBee solves the inverse problem: **pick the Wi-Fi payload** whose resulting `W[n]` is the
   closest achievable approximation to `T[n]`. Because the source hardware still runs its own
   normal modulator, no firmware waveform hook is needed — this is why WEBee runs on
   commodity Wi-Fi.
4. The ZigBee receiver's correlator/demodulator is tolerant enough that "close enough"
   decodes as the intended ZigBee symbol.

**The catch — quantization/emulation error.** The Wi-Fi PHY can only produce a *discrete*
set of `W[n]` (finite constellation, finite subcarriers, whitening, CP), so `W[n]` can only
*approximate* `T[n]`. The residual is emulation noise. WEBee's raw single-shot symbol error
rate is high; it leans on ZigBee's coding and on retransmission to get a usable channel.
This is the fragility that every follow-up paper attacks.

**The family that fixes/extends WEBee:**

| Work | Venue | Contribution over WEBee |
|---|---|---|
| **TwinBee** (Chen, Li, He) | INFOCOM 2018 | Symbol-level coding + chip-combining to knock down the emulation-error floor; makes WEBee-style CTC *reliable*, not just possible. |
| **LEGO-Fi** (Guo, He, Zheng, Yu, Liu) | INFOCOM 2019 | *Transmitter-transparent* CTC: reassembles ordinary, unmodified Wi-Fi packets and uses **cross-demapping** at the ZigBee side, so the Wi-Fi TX need not run a special emulation payload at all. |
| **BlueBee** (Jiang, Yin, Liu, Li, Kim, He) | SenSys 2017 | Same emulation idea but source = **BLE** (GFSK) -> ZigBee; ~10,000× faster than prior packet-level BLE↔ZigBee CTC, using BLE payload/whitening to shape the target. |
| **BlueFi** (Cho & Shin) | SIGCOMM 2021 | "Bluetooth over WiFi": a **Wi-Fi** chip that both **emits and receives** Bluetooth/BLE by PHY emulation — notable because it tackles the harder *reception* direction, not just TX. |
| **WIDE** (Guo, He, Zhang, Jiang) | IPSN 2019 | *Digital emulation* for the reverse/RX direction — decoding ZigBee at a Wi-Fi-class receiver by emulating the target in the digital domain; pushes CTC past the "high→low only" limit. |

All of the emulation-TX works remain **Tier 1** on our ladder: they run on stock or
lightly-driven radios and their genius is in payload math. The reception works (WIDE, BlueFi
RX) are the ones that quietly require **PHY telemetry** — the same subcarrier/spectral hooks
this catalog tracks for CSI and spectral scan (Tier 2–3).

---

## 5. The honest Tier-4 path: arbitrary-waveform CTC via Nexmon

Everything in Section 4 is *approximate* because the source PHY quantizes the waveform. If
instead you can write a **raw baseband IQ buffer** and have the RF front-end play it verbatim,
CTC stops being emulation and becomes exact synthesis — you simply generate the target PHY's
ideal samples and transmit them.

That primitive exists on exactly one Wi-Fi-lineage part in this catalog with reproducible
open source: the **Broadcom BCM4339**, via SEEMOO Lab's **Shadow Wi-Fi / MobiSys 2018 SDR**
Nexmon patch. As documented in [../docs/verification-tier4.md](../docs/verification-tier4.md),
that patch adds three ioctls — `NEX_WRITE_TEMPLATE_RAM` (426), `NEX_SDR_START_TRANSMISSION`
(427), `NEX_SDR_STOP_TRANSMISSION` (428) — that write interleaved `int16` I/Q into Template
RAM and play `sample_count` samples on a chosen `chanspec`. Whatever samples you place there
are what leaves the antenna, so you can author a ZigBee, LoRa-ish, or arbitrary narrowband
waveform, bounded by:

- **TX-only** (no time-domain IQ receive in that patch),
- **Template-RAM depth** (short waveform, replayed via the loop flag — not a streaming SDR),
- **Wi-Fi-grade DAC / TX filter** (band-limited, low dynamic range vs a HackRF/USRP).

For CTC this is the *reference-quality* transmitter: no quantization error, so it is the
cleanest way to inject a foreign PHY — at the cost of needing a specific chip, a specific
firmware patch, and the full Tier-4 regulatory scrutiny. It is the only rung on this page
where "make one radio speak another" is a **radio** trick rather than a **payload-math**
trick. See the audit in verification-tier4.md before trusting any Tier-4 CTC claim.

Reference implementation:
<https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio>

---

## 6. Caveats — read before believing any CTC demo

- **Emulation error is real and dominant.** Payload-selection CTC (WEBee & kin) has a high
  *pre-coding* symbol error rate; published throughput numbers assume the paper's coding,
  chip-combining, and retransmission. A naive re-implementation will look far worse than the
  headline. TwinBee exists precisely because WEBee alone is fragile.
- **CFO, timing, and multipath break it.** The approximation `W[n] ≈ T[n]` is computed in an
  idealized channel. Carrier-frequency offset between the impersonating TX and the foreign
  RX, sample-timing drift, and multipath all erode the already-thin margin. Bench demos in a
  cable/chamber setup are not field performance.
- **Direction matters more than vendors admit.** High-rate→low-rate emulation (Wi-Fi/BLE →
  ZigBee) is the well-trodden, easy direction. Reception of a foreign PHY, or low→high-rate,
  needs PHY telemetry (CSI/spectral/raw-IQ) and is genuinely harder — treat any "bidirectional
  CTC on stock hardware" claim with the skepticism it deserves and check which direction is
  actually demonstrated.
- **Regulatory.** A Wi-Fi card deliberately shaped to a ZigBee envelope, or a Tier-4 raw-IQ
  emission, is a device transmitting a waveform its type-acceptance never covered. Generic
  ISM Part 15 emission on your own gear is one thing; concurrent transmission, out-of-mask
  spurs, jamming-adjacent behavior, and covert channels are the regulated/prohibited zone
  called out in techniques.md and verification-tier4.md. Do TX work in a shielded enclosure
  or on spectrum you are licensed for, against your own devices.
- **`covert-channel` is the right flag, not `arbitrary-waveform`.** Tag payload-selection CTC
  parts as `covert-channel` at **Tier 1** — inflating them to `arbitrary-waveform`/Tier 4 is
  exactly the kind of bravado this catalog forbids. Reserve `arbitrary-waveform` for the
  Nexmon raw-IQ path (Section 5), which earns it.
- **Reproducibility ladder.** WEBee/BlueBee/TwinBee/LEGO-Fi/WIDE/BlueFi are peer-reviewed with
  code or detailed methods, but re-deriving the emulation tables is nontrivial and hardware-/
  channel-specific. Status for CTC techniques in this catalog: **reported** (published,
  demonstrated by authors) unless you have personally reproduced end-to-end, in which case
  **verified**. Nothing here should be marked verified on the strength of a paper alone.

---

## 7. See also

- [../docs/techniques.md](../docs/techniques.md) — the CTC row and the full technique/tier map.
- [../docs/verification-tier4.md](../docs/verification-tier4.md) — the Nexmon arbitrary-waveform
  audit that the Tier-4 CTC path depends on.
- [../docs/taxonomy.md](../docs/taxonomy.md) — the SDR ladder and capability-flag definitions.
- [../projects/nexmon.md](../projects/nexmon.md) — the firmware framework behind the raw-IQ path.

---

## References (primary sources)

| Paper | Authors | Venue / Year | DOI |
|---|---|---|---|
| Esense: communication through energy sensing | K. Chebrolu, A. Dhekne | MobiCom 2009 | [10.1145/1614320.1614330](https://doi.org/10.1145/1614320.1614330) |
| FreeBee: Cross-technology Communication via Free Side-channel | S. M. Kim, T. He | MobiCom 2015 | [10.1145/2789168.2790098](https://doi.org/10.1145/2789168.2790098) |
| C-Morse: Cross-technology communication with transparent Morse coding | Z. Yin, W. Jiang, S. M. Kim, T. He | INFOCOM 2017 | [10.1109/INFOCOM.2017.8057107](https://doi.org/10.1109/INFOCOM.2017.8057107) |
| WEBee: Physical-Layer Cross-Technology Communication via Emulation | Z. Li, T. He | MobiCom 2017 | [10.1145/3117811.3117816](https://doi.org/10.1145/3117811.3117816) |
| BlueBee: a 10,000x Faster Cross-Technology Communication via PHY Emulation | W. Jiang, Z. Yin, R. Liu, Z. Li, S. M. Kim, T. He | SenSys 2017 | [10.1145/3131672.3131678](https://doi.org/10.1145/3131672.3131678) |
| TwinBee: Reliable Physical-Layer Cross-Technology Communication with Symbol-Level Coding | Y. Chen, Z. Li, T. He | INFOCOM 2018 | [10.1109/INFOCOM.2018.8485816](https://doi.org/10.1109/INFOCOM.2018.8485816) |
| Symbol-Level Cross-Technology Communication via Payload Encoding | S. Wang, S. M. Kim, T. He | ICDCS 2018 | [10.1109/ICDCS.2018.00056](https://doi.org/10.1109/ICDCS.2018.00056) |
| LEGO-Fi: Transmitter-Transparent CTC with Cross-Demapping | X. Guo, Y. He, X. Zheng, Z. Yu, Y. Liu | INFOCOM 2019 | [10.1109/INFOCOM.2019.8737659](https://doi.org/10.1109/INFOCOM.2019.8737659) |
| WIDE: physical-level CTC via digital emulation | X. Guo, Y. He, J. Zhang, H. Jiang | IPSN 2019 | [10.1145/3302506.3310388](https://doi.org/10.1145/3302506.3310388) |
| BlueFi: Bluetooth over WiFi | H.-W. Cho, K. G. Shin | SIGCOMM 2021 | [10.1145/3452296.3472920](https://doi.org/10.1145/3452296.3472920) |
| Teaching Smartphones to Transmit Raw Signals … (Shadow Wi-Fi / Nexmon SDR) | M. Schulz, J. Link, F. Gringoli, M. Hollick | MobiSys 2018 | [10.1145/3210240.3210333](https://doi.org/10.1145/3210240.3210333) |

Nexmon SDR (arbitrary-waveform TX) reference code:
<https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio>
