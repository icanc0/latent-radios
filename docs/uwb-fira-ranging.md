# UWB and FiRa: Ranging as a Sensing Radio

*Part of the Latent Radios catalog. Sibling deep-dives: [mmWave & 60 GHz radar](mmwave-60ghz-radar.md), [HaLow & sub-GHz](halow-subghz.md), [techniques](techniques.md), [true-SDR comparison](true-sdr-comparison.md), [taxonomy](taxonomy.md). Chip pages: [other vendors](../chips/other-vendors.md).*

Every other family in this catalog is a **communications** radio you coax into **sensing**. Ultra-wideband (UWB) is the inverse: it is a **ranging/localization** radio whose entire reason to exist is *measuring the channel* — time-of-flight, angle, and the shape of the multipath itself. For most UWB silicon the vendor hands you only a distance in centimetres and calls it a day (tier 0). But one lineage — Qorvo/Decawave's **DW1000 → DW3000 → QM33** — lets an external MCU read the **raw complex channel impulse response (CIR)** straight out of the receiver's correlator. That single register readout is the closest thing in this catalog to a genuine "look at the I/Q of the channel" from a mass-market connectivity chip, and it is what turns a ranging tag into an impulse-radar / gesture / imaging sensor.

This page covers the standard (IEEE 802.15.4z HRP/LRP), the ranging math (TWR, TDoA, PDoA/AoA), the FiRa Consortium interop layer, the chip landscape (Qorvo, NXP Trimension, Apple, Samsung/ST), and exactly where the SDR-ish seam is: **CIR access on the DW3000 class**.

---

## 1. Why UWB is physically different

UWB is not narrowband carrier modulation. The HRP (High Rate Pulse repetition frequency) PHY transmits **sub-nanosecond impulses** across a channel that is **≥ 499.2 MHz wide** — hundreds of times wider than a Wi-Fi 20 MHz channel and wider than any single channel a Wi-Fi CSI chip in this catalog can see.

| Property | Wi-Fi CSI (20–80 MHz) | 60 GHz FMCW radar | **UWB HRP (802.15.4z)** |
|---|---|---|---|
| Instantaneous bandwidth | 20 / 40 / 80 / 160 MHz | 1–4 GHz sweep | **≈ 500 MHz per channel** (channels 5, 9) |
| Range/delay resolution (c/2B) | ~7.5 m (20 MHz) → ~0.9 m (160 MHz) | ~4–15 cm | **~30 cm native; ~10 cm ranging** after leading-edge estimation |
| What you read out | per-subcarrier CFR (freq domain) | range–Doppler map | **CIR = channel *impulse* response (time domain), complex I/Q** |
| Native product | throughput | range map | **time-of-flight distance + AoA** |
| Carrier | 2.4/5/6 GHz | 57–64 GHz | **~6.5 GHz (ch 5) / ~8.0 GHz (ch 9)** |

The bandwidth is the whole story. A ~500 MHz channel resolves multipath components spaced ~0.6 ns / ~20 cm apart, so the CIR you read out of a DW3000 is a **time-domain fingerprint of the room**: direct path, then discrete reflections off walls, furniture and people, each as a complex tap. That is why UWB ranging holds ~10 cm accuracy where Wi-Fi RTT (802.11mc FTM, see [techniques §5](techniques.md)) struggles to a metre — and why the same CIR supports radar-style sensing.

### UWB channels (802.15.4 / 4z HRP)

| Channel | Centre (MHz) | Bandwidth (MHz) | Common use |
|---|---|---|---|
| 5 | 6489.6 | 499.2 | **The workhorse.** Apple U1/U2, most FiRa profiles |
| 9 | 7987.2 | 499.2 | **Second workhorse.** Apple U1/U2, FiRa; avoids some 6 GHz Wi-Fi/UNII overlap |
| 6, 8 | 6988.8 / 7488.0 | 499.2 | Regional / FiRa optional |
| 1–4, 7 | 3494.4–6489.6 | 499.2–1331.2 | Legacy 802.15.4a low band (DW1000 era), largely deprecated for FiRa |

FiRa-certified devices concentrate on **channels 5 and 9**; regulatory masks (FCC Part 15, ETSI EN 302 065) permit UWB emission at roughly **−41.3 dBm/MHz EIRP** — deliberately below the noise floor of narrowband receivers, which is what makes UWB coexist with everything and stay low-power.

### HRP vs LRP

802.15.4z defines **two incompatible enhanced UWB PHYs**:

- **HRP-UWB (High Rate PRF)** — impulse radio with ~500 MHz channels, BPRF (Base, ~64 MHz PRF, mandatory/interoperable) and HPRF (Higher, ~124/249 MHz PRF) modes. Adds the **STS (Scrambled Timestamp Sequence)** for cryptographically secure ranging. **This is what Qorvo, NXP Trimension, Apple, Samsung, and FiRa all use.**
- **LRP-UWB (Low Rate PRF)** — a lower-complexity, lower-PRF PHY (the lineage behind some access-control and NXP low-power parts). Not interoperable with HRP; smaller ecosystem. FiRa is HRP-only.

Everything below is HRP unless noted.

---

## 2. Ranging math — how a timing radio measures the world

### 2.1 Two-Way Ranging (TWR)

TWR measures **time-of-flight (ToF)** directly and converts to distance (`d = ToF · c`). No clock synchronisation between devices is needed because everything is derived from round-trip timestamps captured by each chip's precise timestamping unit (~15.65 ps LSB on DW3000).

- **SS-TWR (single-sided):** Initiator sends `POLL`, responder replies `RESP`. `ToF = (T_round − T_reply)/2`. Simple, but the two crystals' clock-offset (tens of ppm) leaks directly into the estimate → error grows with reply delay.
- **DS-TWR (double-sided):** Adds a `FINAL` message so both round trips are measured; the symmetric formula **cancels first-order clock offset**, giving robust ~10 cm accuracy. This is the FiRa default and the one you meet in every DW3000 example (`ex_05*_ds_twr_*`).

```
Initiator          Responder
   |----- POLL ----->|   t_reply1
   |<---- RESP ------|   t_round1
   |----- FINAL ---->|   (carries t_reply1, t_round1 timestamps)
   ToF ≈ (t_round1·t_round2 − t_reply1·t_reply2) / (t_round1+t_round2+t_reply1+t_reply2)
```

### 2.2 TDoA (Time Difference of Arrival)

Infrastructure-side localisation for **many tags, cheaply**. A tag emits a one-way "blink"; a set of **time-synchronised anchors** each timestamps arrival. Differences in arrival time define **hyperbolae**; their intersection is the tag position. The tag never listens → battery lasts years; scaling is limited by anchor sync (wired clock or wireless clock distribution), not by tag count. **DL-TDoA** (downlink) inverts it: anchors transmit, the tag listens and self-locates while staying private.

### 2.3 PDoA / AoA (Phase Difference of Arrival → Angle of Arrival)

With **two (or more) receive antennas** spaced ~λ/2 apart (~1.9 cm at ch 9), the same incoming UWB pulse arrives at a small **phase difference** Δφ across the pair. Angle follows from `θ = arcsin(Δφ·λ / 2πd)`. Combine PDoA (bearing) with TWR (range) and a **single anchor** yields a full 2-D fix and a "point-to-find" direction vector — this is the mechanism behind AirTag/UWB directional arrows and car-key "walk up to unlock." On Qorvo silicon PDoA needs a **dual-RX part** (DW3120/DW3220, QM33120); Apple's U1 uses a **3-antenna array** for 3-D AoA.

### 2.4 The CIR — where ranging becomes a sensing radio

To find ToF, the receiver cross-correlates the incoming signal against the known preamble sequence and builds an **accumulator**: the **channel impulse response**, a vector of **complex (I/Q) taps**, each tap a ~1 ns time bin. The ranging engine only needs the **leading-edge / first-path index** out of this. But the *whole vector is readable*:

- **DW3000 Ipatov accumulator:** ~**1016 complex samples**, **6 bytes each** (int24 I + int24 Q), sampled at ~1 GHz → ~1 ns bins spanning ~1 µs / ~300 m of multipath. Read with `dwt_readaccdata()`. STS reception adds a **second (STS) accumulator** you can read independently — useful for secure-ranging and for a cleaner correlation template.
- **Diagnostics:** `dwt_readdiagnostics()` fills a `dwt_rxdiag_t` with first-path index/amplitudes (`ipatovFpIndex`, F1/F2/F3), peak amplitude, and power — the classic **first-path-vs-peak** ratio that flags NLoS.

That complex CIR **is** a raw-I/Q view of the propagation channel — a UWB analogue of Wi-Fi CSI, but time-domain and ~500 MHz wide. Feed a time-series of CIRs into the usual pipeline and you get **impulse radar, presence/occupancy, respiration, gesture, and coarse imaging** off a $10 ranging chip. This is the capability that earns the DW3000 class its `raw-iq` + `radar` flags and a tier well above the black-box UWB SoCs.

---

## 3. FiRa Consortium — the interoperability layer

802.15.4z standardises the PHY and part of the MAC, but leaves enough open (session setup, scheduling, key management, host API) that two compliant chips will not necessarily interoperate. **FiRa Consortium** (founded 2019 — NXP, Samsung, Bosch, and others; Qorvo joined via Decawave) closes that gap on top of HRP-UWB:

- **FiRa MAC** — profiles and scheduling built on the 4z ranging MAC (controller/controlee roles, ranging rounds/slots, block timing).
- **UCI (UWB Command Interface)** — the standardised **host ⇄ UWB subsystem** control protocol (commands, responses, notifications). This is the layer Android's UWB Jetpack API and Linux UWB stacks speak to the chip. It is the FiRa equivalent of "the driver ABI."
- **Profiles** — e.g. **PACS** (Physical Access Control System, door/badge) and consumer ranging profiles for "Nearby Interaction"-style use.
- **Certification** — an interop-test program; "FiRa Certified" parts (QM33120W, SR150, U100, etc.) are guaranteed cross-vendor.
- **Alignment with CCC Digital Key 3.0** — the Car Connectivity Consortium's phone-as-car-key spec uses HRP-UWB + FiRa/UCI for secure distance-bounded access; automotive parts (NXP SR100T, Qorvo secure SoCs) target it.

**Why FiRa matters to a hacker:** UCI is *documented*, and where the chip lets the host issue raw UCI you can drive ranging sessions, enable **CIR/diagnostics reporting** (FiRa defines RANGING/CIR notifications), and script the radio — even on parts that hide the register map. But UCI is also where locked-down SoCs (Apple, Samsung, NXP secure) draw the line: you get ranging results, not the correlator.

---

## 4. The SDR-ladder mapping for UWB

The catalog ladder (0 black-box → 5 open PHY) maps onto UWB by **how much of the channel the host can see**:

| Tier | UWB meaning | Parts | Flags |
|---|---|---|---|
| **0** | Distance/direction number only; correlator sealed behind UCI/secure FW | Apple **U1/U2**, Samsung **Exynos Connect U100**, NXP **SR040** tag, Qorvo **QM35** SoC | — |
| **1** | Raw frame TX/RX (sniff/inject UWB frames), UCI scriptable, but no CIR | NXP **SR150/SR100T** (via UCI, CIR gated), some secure SoC configs | monitor, injection |
| **3** | **Register-level control + readable complex CIR/STS accumulator** → raw-I/Q channel view, impulse radar | Qorvo **DW3110/DW3120/DW3220**, **DWM3001C**, **QM33110W/QM33120W**; (DW1000, already catalogued) | monitor, raw-iq, radar |

Notes on the mapping:

- **No UWB part reaches tier 4/5 here.** Even the open DW3000 is a **fixed impulse-radio PHY** you configure by registers, not a reprogrammable baseband — you cannot synthesise an arbitrary waveform, and the pulse shaping is silicon. So "arbitrary-waveform" and "open-firmware" are *not* claimed. Firmware openness for the Decawave/QM33 line is **`documented`**: there is no rewritable radio firmware; a public user manual + open C API (`dwt_uwb_driver`) expose the register map directly, which is *more* open than most Wi-Fi firmware but is not an open PHY.
- **`radar`, not `fmcw`.** UWB HRP is **pulsed/impulse** radar, not frequency-modulated continuous-wave. Contrast the [60 GHz FMCW parts](mmwave-60ghz-radar.md).
- **Tier 0 is honest, not dismissive.** Apple U1/U2 do superb 3-antenna AoA and secure ranging — but from an SDR standpoint the host sees only Nearby-Interaction distance+direction. No channel access → tier 0.
- The already-catalogued **`qorvo-dw1000`** (in [other-vendors.md](../chips/other-vendors.md)) is the 802.15.4a/4z-precursor sibling of this line: same CIR-readout trick (`dwt_readaccdata`, ~992/1016-sample accumulator, 4 bytes/sample), no STS. Everything below is **net-new**.

---

## 5. Tooling — how you actually get at the CIR

Because these are register-controlled transceivers driven by an external MCU, "the driver" is a portable C library, not a kernel blob. The reproducible path is: **DWM3001CDK dev kit (DW3110 + nRF52833) + one of the open example firmwares**, flashed over the on-board J-Link, talking `dwt_*` API.

| Layer | What it is | Where |
|---|---|---|
| **`dwt_uwb_driver` / DW3xxx API** | Qorvo's C API — `dwt_initialise`, `dwt_configure`, `dwt_starttx/rx`, **`dwt_readaccdata`** (CIR), **`dwt_readdiagnostics`** | Bundled in the SDKs and the community ports below |
| **Uberi/DWM3001C-starter-firmware** | Clean, comprehensive example set for DWM3001C — every mode as a standalone `ex_*`: SS/DS-TWR, PDoA TX/RX, **RX diagnostics + accumulator readout**, STS, AES, CCA, sniff | github.com/Uberi/DWM3001C-starter-firmware |
| **Uberi/DWM3001CDK-demo-firmware** | Reworked official CDK firmware, USB/UCI control, cleaned build | github.com/Uberi/DWM3001CDK-demo-firmware |
| **foldedtoad/dwm3000** | DWM3000 (DW3110) on a DWS3000 Arduino shield, Zephyr-based; good bring-up reference | github.com/foldedtoad/dwm3000 |
| **Fhilb/DW3000_Arduino** | Minimal DW3000 library for ESP32 — fastest "hello, ranging" | github.com/Fhilb/DW3000_Arduino |
| **thotro/arduino-dw1000** | The classic DW1000 (prior-gen) library, incl. CIR/diagnostics access — 570★, the community's teaching codebase | github.com/thotro/arduino-dw1000 |
| **Zephyr RTOS** | Upstream `ieee802154` / DW3000 driver work; Qorvo ships Zephyr board support for DWM3001CDK | github.com/zephyrproject-rtos/zephyr |
| **Linux `net/ieee802154` + FiRa UCI** | Mainline 802.15.4 netlink stack; FiRa MCPS/UCI drivers (Qorvo "uwb-stack") sit above it for host-driven ranging on Linux SBCs | kernel `net/ieee802154/` |

### Minimal CIR-readout recipe (verified against the example set)

```c
/* After a good frame reception (DWT_INT_RXFCG): */
dwt_readdiagnostics(&rx_diag);          /* first-path index, F1/F2/F3, peak */
uint16_t fp = rx_diag.ipatovFpIndex >> 6;   /* leading-edge bin (Q6 fixed-pt) */

/* Read complex CIR samples around the first path.
 * DW3000 Ipatov accumulator: 1016 complex samples, 6 bytes each (I24,Q24).
 * accum_data must be (nsamples*6 + 1) bytes: a dummy byte precedes the data. */
uint8_t accum_data[NS*6 + 1];
dwt_readaccdata(accum_data, sizeof(accum_data), fp - 2);   /* start 2 bins early */
/* Parse int24 I,Q per sample -> complex CIR taps -> magnitude/phase per ~1 ns bin */
```

Time-stamp this per reception and stack the CIR vectors → a slow-time × fast-time matrix, i.e. an **impulse range–time map**. Micro-motion (breathing, a hand) shows as phase modulation of a stable tap; a moving person shows as a migrating/appearing tap. That is UWB radar built from a ranging chip.

### Safety & regulatory notes (any TX)

- UWB emission is legal only under the **spectral mask** (≈ −41.3 dBm/MHz EIRP, FCC Part 15 subpart F / ETSI EN 302 065) and only in the **permitted bands** (US: 3.1–10.6 GHz with in/outdoor limits; EU: ch 9 / 8.0 GHz emphasised, with DAA/LDC mitigations on some sub-bands). The dev kits ship compliant; **do not raise TX power, defeat duty-cycle/LDC limits, or use unshielded external PAs.**
- **Continuous-wave / continuous-frame test modes** (`dwt_configcwmode`) exist for calibration and radiate a persistent tone — bench/shielded use only.
- **Secure-ranging (STS) is a safety feature, not a toy:** distance-bounding protects car keys and locks. Do not deploy relay/distance-manipulation experiments against systems you do not own; keep them on the bench.

---

## 6. The chip landscape (net-new records)

Grouped by vendor. Full structured entries are in `modules[]`; the table is the quick map.

### 6.1 Qorvo / Decawave — the open, CIR-readable line ⭐

The only UWB lineage that hands the host a raw channel view.

| Part | Role | 4z / FiRa | RX paths | CIR access | Tier | Note |
|---|---|---|---|---|---|---|
| **DW3110 / DW3210** | HRP transceiver, single-RX | 4z HRP, ch 5/9, STS | 1 | ✅ Ipatov+STS accumulator | 3 | The `DWM3000` module's chip; TWR + radar |
| **DW3120 / DW3220** | HRP transceiver, dual-RX | 4z HRP, STS | 2 | ✅ | 3 | Adds **PDoA/AoA**; single-anchor range+bearing |
| **DWM3001C (module)** | DW3110 + nRF52833 + IMU | 4z HRP | 1 | ✅ (via `dwt_*`) | 3 | **The hackable dev board** (DWM3001CDK) |
| **QM33110W / QM33120W** | FiRa-Certified DW3000-class | 4z HRP, **FiRa cert** | 1 / 2 | ✅ | 3 | Current-gen; QM33120W = dual-RX AoA |
| **QM35xxx (SoC)** | Integrated secure UWB SoC | 4z HRP, FiRa, UCI | — | ✖ (sealed) | 0 | Cortex-M + SE; host sees UCI only |

### 6.2 NXP Trimension — secure, FiRa, mostly sealed

| Part | Role | 4z / FiRa | Host view | Tier | Note |
|---|---|---|---|---|---|
| **SR150** | Full-featured IC (Cortex-M33), AoA | 4z HRP, FiRa | UCI (CIR gated) | 1 | Phones/anchors; raw frames via UCI, CIR not openly exposed |
| **SR040** | Tag-optimised, low-power | 4z HRP, FiRa | UCI, distance | 0 | Responder role; minimal exposure |
| **SR100T** | Automotive, CCC Digital Key 3.0 | 4z HRP, FiRa/CCC | secure UCI | 0 | Car access, distance-bounded, locked |
| **OL23D0** | Consumer low-power UWB | 4z HRP, FiRa | UCI | 0 | Trimension IoT/wearable class |

### 6.3 Apple, Samsung, ST — closed application silicon

| Part | Vendor | Exposure | Tier | Note |
|---|---|---|---|---|
| **U1** | Apple | Nearby Interaction API: distance + 3-D direction only | 0 | 3-antenna AoA; iPhone 11+/AirTag/Watch; no channel access |
| **U2** | Apple | same API, better range/power | 0 | iPhone 15+; 2nd-gen, closed |
| **Exynos Connect U100** | Samsung | Android UWB API / UCI | 0 | Galaxy phones, SmartTag2; FiRa, AoA; closed FW |

*STMicroelectronics is a FiRa member and has shown UWB silicon, but no widely-shipping merchant standalone UWB IC is confirmed as of this writing — recorded here as context, not as a catalogued part (accuracy over bravado).*

---

## 7. Where UWB sits vs the rest of the catalog

- **vs Wi-Fi CSI** ([techniques §2](techniques.md)): UWB gives a **time-domain, ~500 MHz** channel view (great delay resolution, native ToF) where Wi-Fi gives a **frequency-domain, ≤160 MHz** one (richer subcarriers, but coarser range). UWB wins at ranging/geometry; Wi-Fi wins at ubiquity and Doppler richness.
- **vs 802.11mc FTM / Wi-Fi RTT** ([techniques §5](techniques.md)): same *goal* (round-trip ToF), but UWB's bandwidth and picosecond timestamping put it an order of magnitude ahead on accuracy and multipath rejection.
- **vs 60 GHz FMCW radar** ([mmWave](mmwave-60ghz-radar.md)): FMCW has more bandwidth (finer range) and easier Doppler, but tiny range and no comms. UWB reaches tens of metres, penetrates better, and is a real data/ranging link too.
- **The catalog lesson repeats:** the interesting seam is always *"can the host read the PHY's internal state?"* For Wi-Fi that is CSI; for UWB it is the **CIR accumulator**. Qorvo's DW3000/QM33 line is the one UWB family that says yes.

---

## References (primary)

- IEEE 802.15.4z-2020 (Enhanced UWB PHYs, HRP/LRP, STS): https://standards.ieee.org/ieee/802.15.4z/7862/
- FiRa Consortium — technology & specifications (MAC, UCI, profiles, certification): https://www.firaconsortium.org/
- Qorvo DW3110 product page: https://www.qorvo.com/products/p/DW3110
- Qorvo DWM3001CDK dev kit: https://www.qorvo.com/products/p/DWM3001CDK
- Qorvo QM33120WA (FiRa-Certified): https://www.qorvo.com/products/p/QM33120WA
- Qorvo Ultra-Wideband overview: https://www.qorvo.com/products/ultra-wideband
- NXP Trimension UWB portfolio (SR040 / SR150 / SR100T / OL23D0): https://www.nxp.com/products/wireless-connectivity/secure-ultra-wideband-uwb:UWB-TRIMENSION
- Apple Nearby Interaction framework: https://developer.apple.com/documentation/nearbyinteraction
- Android UWB (Jetpack) developer guide: https://developer.android.com/develop/connectivity/uwb
- Car Connectivity Consortium — Digital Key: https://carconnectivity.org/digital-key/
- Uberi/DWM3001C-starter-firmware (open examples incl. CIR/diagnostics): https://github.com/Uberi/DWM3001C-starter-firmware
- foldedtoad/dwm3000 (DW3110 on Zephyr/Arduino shield): https://github.com/foldedtoad/dwm3000
- thotro/arduino-dw1000 (prior-gen DW1000 CIR library): https://github.com/thotro/arduino-dw1000

*Cross-links: [other-vendors chip page (DW1000/DW3000 entry)](../chips/other-vendors.md) · [techniques (ranging, radar, CSI)](techniques.md) · [taxonomy](taxonomy.md).*
