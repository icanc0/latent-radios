# Wi-Fi Sensing in the Wild: the Productized Side

> **Scope note.** Everywhere else in this catalog, "Wi-Fi sensing" means *you* prying CSI, spectral, or raw-PHY data out of a chip you bought for connectivity. This page is the mirror image: the same physics (CSI amplitude/phase perturbation, micro‑Doppler, time‑reversal focusing) shipped as a **closed, vendor-controlled feature** inside consumer routers, mesh nodes, set-top boxes, and medical/eldercare appliances. From an SDR-repurposing standpoint almost everything here is **Tier 0** — the sensing happens in firmware or the cloud and the user never touches the underlying observables. The interesting story is not "what can I hack" but "what did the research become, who deployed it at scale, and what does ambient sensing mean for consent." See [`../docs/techniques.md`](../docs/techniques.md) for the underlying methods, [`../docs/80211bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md) for the standards track, and [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md) for the ML pipelines that most of these products actually run.

## Why this is a different animal from the rest of the catalog

The DIY side of this project extracts CSI from a Broadcom/Atheros/Intel/Espressif chip using patched firmware (Nexmon, Atheros CSI Tool, ESP32-CSI). The **productized** side inverts the whole trust model:

- The vendor already has the raw CSI (or richer PHY telemetry) — they wrote the firmware.
- The heavy lifting is **ML** (classification, denoising, person/pet discrimination, activity segmentation), often run in the cloud on uploaded feature vectors, not raw IQ.
- The end user gets a **binary or scored event** ("motion in living room", "fall detected", "breathing 14 bpm"), never the channel matrix.
- The differentiator is **calibration + models + deployment scale**, not RF access. Cognitive Systems' moat is 20M+ homes of labeled ground truth, not a clever firmware patch.

This matters for the catalog because it sets the ceiling: the same silicon that a hobbyist can coax to Tier 2 CSI is, in the carrier's hands, a whole-home radar — and the asymmetry is entirely software and data.

## The commercial landscape

### The standards push: IEEE 802.11bf (WLAN Sensing)

802.11bf is the industry's attempt to stop everyone from reverse-engineering CSI out of `11n/ac/ax` management frames and instead **standardize a sensing service** at the MAC/PHY: negotiated sensing sessions, sounding sequences, defined measurement reports (CSI, and in the DMG/60 GHz path, beamforming/reflection measurements), roles (initiator/responder), and — critically — a **consent/negotiation framework** baked into the protocol. It targets both sub‑7 GHz (2.4/5/6 GHz, CSI-based) and 60 GHz (mmWave, reflection/Doppler). The commercial subtext: turn ad-hoc "Wi-Fi sensing" into a licensable, interoperable feature that chip vendors (Qualcomm, Broadcom, MediaTek, Celeno/Renesas) and platform vendors can certify against. The draft has been progressing for years; treat "shipping certified 11bf silicon at scale" as **near-term/emerging**, not a mass-market reality yet. Detailed protocol treatment lives in [`../docs/80211bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md).

### The two scaled incumbents

**Cognitive Systems — WiFi Motion™.** The dominant embedded player. WiFi Motion runs as firmware + cloud analytics inside third-party routers and mesh systems; the company advertises **150+ partners** and **20M+ homes/environments** enabled, with Tier‑1 ISP deployments across North America, Europe, and Asia. It has historically been the sensing engine behind several carrier and mesh offerings and is the technology most people mean when a carrier app suddenly grows a "Home Motion" toggle. Use cases: whole-home motion/presence without cameras, occupancy for automation/energy, and "fall risk / anomaly" detection. Technique: CSI-derived motion features from standard 802.11 traffic; the chip is whatever the OEM shipped (Qualcomm/Broadcom/MediaTek Wi-Fi 5/6). *(Verified from cognitivesystems.com, Aug 2026.)*

**Origin Wireless — "AI Sensing," time-reversal heritage.** Origin's academic roots are in **time-reversal** signal processing (focusing multipath energy back to its source to get a sharp spatial "resonance" that is extremely sensitive to environmental change). Commercially it now brands the approach **AI Sensing℠**, stresses **"100% uncompressed CSI"** (i.e. it wants the full, un-quantized channel matrix rather than the compressed beamforming feedback many chips expose), and ships it as **TruShield℠** (security/intrusion), **TruPresence** (occupancy), plus historical consumer products marketed under the **Hex Home / Hex Family Care** lines for intrusion, presence, breathing, and fall detection. Same physics-to-product path: rich CSI in, event out. *(Verified from originwirelessai.com, Aug 2026.)*

### Mesh/router platform sensing

**Plume — Sense.** Plume bundles motion sensing ("Sense") into its cloud-managed HomePass service delivered through ISP-supplied Plume/adapt mesh pods and partner routers. It reuses the same Wi-Fi CSI motion primitive, wrapped in Plume's cloud (person/pet, room-level, alerts, automation triggers). The chip basis is the pod's own Wi‑Fi 5/6 silicon; the value-add is Plume's cloud and its large managed-Wi-Fi install base.

**eero (Amazon).** eero has shipped motion/presence-style sensing features on its mesh; sensing has been powered by embedded engines of the Cognitive-Systems type running on the mesh nodes' Wi‑Fi radios. Same pattern: OEM Wi-Fi 6/6E silicon + licensed or in-house motion engine + cloud/app surface.

### Silicon that was purpose-built for sensing

**Celeno → Renesas — Wi-Fi Doppler Imaging.** Celeno (acquired by **Renesas** in 2022) built Wi-Fi 6 access-point silicon (the **CL2400** family) with an explicitly marketed **"Wi-Fi Doppler Imaging"** sensing mode — on-chip Doppler/CSI processing to detect motion, count/locate people, and feed presence to smart-home/HVAC and security. This is the closest thing on this page to "a Wi-Fi chip designed from the start to also be a sensor," and it's a natural home for 802.11bf. It's still closed firmware — Tier 0 for repurposing — but it's the chip **basis** other people's products sit on. See the module record below and [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md) / [`../chips/other-vendors.md`](../chips/other-vendors.md) for adjacent connectivity silicon.

**Qualcomm / Broadcom / MediaTek.** All three have sensing hooks in their carrier/AP Wi-Fi 6/6E/7 stacks (Qualcomm's Networking Pro / "Wi-Fi Sensing," etc.) intended to be the OEM-facing plumbing for 11bf. From the catalog's perspective these are the same chips covered in [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md) and [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md) — the sensing feature is a firmware/SDK entitlement, not a user-accessible SDR path.

### Health, sleep, breathing, and eldercare appliances

**Aerial.ai.** Wi-Fi-sensing software (motion inferred from "distortion of the WiFi signals") targeting **eldercare & wellness, remote patient monitoring, sleep tracking, presence, security, and energy management**, deployed through ISP/router partners as an embedded + cloud/edge ("hybrid") stack. Chip basis: the partner router's Wi-Fi radio. *(Verified from aerial.ai, Aug 2026.)*

**Sleep/breathing monitors.** The breathing/sleep use case is the same CSI micro-Doppler signal (chest-wall motion modulates multipath at ~0.2–0.5 Hz) that Origin (Hex), Aerial, and various academic groups demonstrate. Commercially this shows up both as a Wi-Fi feature and — importantly — as a **different radio entirely**: many "contactless sleep/breathing" consumer products (e.g. bedside monitors) actually use **60 GHz mmWave FMCW radar or UWB**, *not* Wi-Fi CSI. Don't conflate them.

**Xandar Kardian — the honest caveat.** Xandar Kardian is frequently name-dropped alongside "Wi-Fi sensing," but its **XK300/XK family are mmWave impulse/UWB-class radar** vital-sign sensors (presence, respiration, heart rate, fall) for eldercare/hospitality/HVAC — a *radar* product, not a Wi-Fi CSI product. It belongs on this page as a market-adjacent competitor and a reminder that "ambient presence sensing" is a **multi-radio** category (Wi-Fi CSI vs. 60 GHz FMCW vs. UWB vs. PIR), not a Wi-Fi monopoly.

### Presence-for-HVAC and fall detection as product categories

Two use cases are pulling the whole market:

- **Presence-for-HVAC / building automation.** Occupancy without cameras or PIR blind spots is attractive for lighting, HVAC setback, and energy analytics. This is the pitch behind Celeno/Renesas Doppler Imaging, Plume/eero occupancy, and Xandar Kardian's building line.
- **Fall detection & elder-care.** The emotionally and regulatorily loaded one. Wi-Fi-based fall detection (Origin/Hex, Aerial, Cognitive's "fall risk") competes with radar (Xandar Kardian, Vayyar), wearables, and PERS pendants. Wi-Fi's appeal is *no wearable, no camera, whole-home*; its weakness is *false alarms, per-home calibration, and the fact that the same sensor that catches a fall also logs every time you move.*

## Product → technique → chip basis → use case

| Product / Vendor | Sensing technique | Radio / chip basis | Primary use case | Delivery | Repurpose tier |
|---|---|---|---|---|---|
| **WiFi Motion™ / Cognitive Systems** | CSI motion features from standard 802.11 traffic | OEM Wi‑Fi 5/6 (Qualcomm/Broadcom/MediaTek) in partner routers & mesh | Whole-home motion/presence, security, "fall risk", occupancy/energy | Embedded firmware + cloud, carrier app | 0 (closed) |
| **AI Sensing / TruShield / TruPresence — Origin Wireless** (Hex Home / Hex Family Care) | Time-reversal focusing, **uncompressed CSI** | OEM Wi‑Fi radios / dedicated Hex sensors | Intrusion/security, presence, breathing, fall detection | Embedded + cloud | 0 (closed) |
| **Plume Sense** | Wi‑Fi CSI motion | Plume/partner mesh pods (Wi‑Fi 5/6/6E) | Motion alerts, person/pet, room-level, automation | Cloud-managed (HomePass) | 0 (closed) |
| **eero motion/presence** | Wi‑Fi CSI motion (Cognitive-class engine) | eero mesh nodes (Wi‑Fi 6/6E) | Home presence/motion, automation | Embedded + Amazon cloud/app | 0 (closed) |
| **Aerial.ai** | Wi‑Fi CSI motion, ML (edge+cloud) | Partner router Wi‑Fi radio | Eldercare, RPM, sleep tracking, presence, energy | Embedded SW + hybrid cloud | 0 (closed) |
| **Celeno → Renesas "Wi‑Fi Doppler Imaging"** (CL2400) | On-chip **Doppler/CSI** sensing mode | Purpose-built Wi‑Fi 6 AP SoC | People counting/localization, presence-for-HVAC, security | Chip feature / SDK (OEM-facing) | 0 (closed firmware; *chip basis* for others) |
| **Qualcomm / Broadcom / MediaTek Wi‑Fi Sensing hooks** | CSI / 802.11bf sounding | Carrier/AP Wi‑Fi 6/6E/7 silicon | Plumbing for 11bf sensing services | Firmware/SDK entitlement | 0 (closed) |
| **Xandar Kardian XK300/XK** *(non-Wi‑Fi, for contrast)* | **mmWave impulse / UWB radar** | Dedicated radar sensor (not Wi‑Fi) | Vital signs, presence, fall, HVAC | Standalone sensor | n/a (not a Wi‑Fi chip) |
| **Generic "contactless sleep/breathing" monitors** *(mixed)* | Wi‑Fi CSI **or** 60 GHz FMCW **or** UWB | Wi‑Fi radio *or* dedicated 60 GHz/UWB radar | Sleep stage, respiration, HR | Appliance + cloud | 0 / varies |

*Tier column = SDR-repurposing tier per this catalog's ladder — uniformly 0 because the user never gets the observables. It is **not** a rating of sensing quality.*

## The privacy / consent problem

Ambient Wi-Fi sensing is the most **stealth-capable** biometric surveillance channel in a normal home, and the productization above makes several things true at once:

- **No opt-in surface exists at the RF layer.** CSI-based motion works on *any* device associated to (or even just near) the AP. A guest, a child, a neighbor whose signal bleeds through a wall — none of them consented, none of them can see it's happening, and there is no LED or shutter. This is exactly the gap **802.11bf tries to close** with an explicit negotiation/consent framework — but that only governs *standardized* sensing between cooperative devices, not the vendor already parsing CSI from your own AP's firmware.
- **The carrier/OEM holds the raw channel.** The asymmetry noted at the top is the whole privacy story: the same 20M-home install base that makes the models good also means a single vendor can, in principle, infer occupancy patterns, sleep/wake cycles, breathing rate, and presence-vs-absence across millions of homes — data that is medical-adjacent (respiration, fall, "anomaly") but usually sits outside HIPAA because it's a "router feature."
- **Function creep.** A feature sold as "motion for automation" is, unchanged, a **presence/absence log** (useful to burglars, stalkers, insurers, landlords) and an **activity-of-daily-living monitor** (useful, and dangerous, for eldercare and for coercive control). Fall detection and breathing monitoring cross into health data that most privacy policies were not written for.
- **Cross-tenant and through-wall leakage.** Because the signal is ambient RF, sensing does not respect apartment walls the way a camera's field of view does. Multi-dwelling deployments raise questions no consumer sensor answered before.
- **Regulatory vacuum.** As of 2026 there is no clean regulatory home for "the router that watches you breathe." It is not a camera (no clear video-surveillance law), often not a "medical device" (marketed as wellness), and the data may be processed abroad. See [`../docs/rf-safety-and-legal.md`](../docs/rf-safety-and-legal.md) and [`../docs/regulatory-by-region.md`](../docs/regulatory-by-region.md) for the adjacent legal terrain.

**Bottom line for this catalog:** the DIY, firmware-hacking half of Latent Radios and the commercial half are the same capability with opposite consent postures. Understanding the productized side is the honest way to understand what the Tier‑2 CSI you extracted by hand is *worth* — and why "it's just a router" is not a privacy answer.

## References

- Cognitive Systems — WiFi Motion (product + partner/scale claims): <https://www.cognitivesystems.com/wifi-motion/> *(verified Aug 2026)*
- Origin Wireless — AI Sensing / TruShield / TruPresence (uncompressed CSI, time-reversal heritage): <https://www.originwirelessai.com/> *(verified Aug 2026)*
- Aerial.ai — Wi‑Fi sensing for eldercare/RPM/sleep: <https://aerial.ai/> *(verified Aug 2026)*
- Plume — Sense / HomePass: <https://www.plume.com/>
- eero (Amazon) mesh & features: <https://eero.com/>
- Renesas — Celeno acquisition & Wi‑Fi sensing (Wi‑Fi Doppler Imaging, CL2400): <https://www.renesas.com/> and Celeno legacy materials
- Xandar Kardian (mmWave/UWB radar vital-sign sensors, for contrast): <https://www.xandar.com/>
- IEEE 802.11bf Task Group (WLAN Sensing): <https://www.ieee802.org/11/Reports/tgbf_update.htm>

*Related in this catalog:* [`../docs/techniques.md`](../docs/techniques.md) · [`../docs/80211bf-wlan-sensing.md`](../docs/802-11bf-wlan-sensing.md) · [`../docs/ml-csi-sensing.md`](../docs/ml-csi-sensing.md) · [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) · [`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md)
