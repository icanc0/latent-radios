# The Wi-Fi Sensing Application Catalog

*One consolidated reference tying together the sensing side of Latent Radios.* For every human/environment sensing application people build on Wi-Fi (and adjacent RF), this catalog states the **minimum SDR-ladder tier** and **capability** you actually need, the **best hardware** to attempt it on, the **canonical system or paper** that defined it, an honest **difficulty**, and how far it has matured toward a **product**.

Read this alongside:

- [../docs/techniques.md](../docs/techniques.md) — the signal-processing primitives (CSI, Doppler, ToF/AoA, FMCW) these applications are built from.
- [../projects/wifi-sensing-datasets.md](../projects/wifi-sensing-datasets.md) — public datasets to train/evaluate against before you collect your own.
- [../docs/honest-limitations-of-wifi-sensing.md](../docs/honest-limitations-of-wifi-sensing.md) — **read this before believing any accuracy number below.** Almost every result here is in-domain; cross-person/cross-environment generalization is the field's unsolved problem.

---

## How to read this catalog

**Minimum tier** is the lowest rung of the SDR ladder (see [../docs/taxonomy.md](../docs/taxonomy.md)) at which the application is *possible on commodity Wi-Fi silicon*. Many applications also have a "better on radar/SDR" path at a higher tier that trades accessibility for signal quality.

| Rung | What it gives sensing | Sensing you unlock |
|---|---|---|
| **Tier 1** — monitor + injection | RSSI, packet timing, frame counts | presence, coarse motion, intrusion |
| **Tier 2** — CSI | per-subcarrier amplitude + phase | the bulk of Wi-Fi sensing (activity, gesture, vitals, gait, pose) |
| **Tier 3** — spectral scan | raw FFT bins / interference view | environment/occupancy via band energy, some motion |
| **Tier 4** — raw-IQ / arbitrary-waveform TX | Doppler radar, FMCW, custom probes | Doppler gesture (WiSee), FMCW vitals, ranging |
| **Tier 5** — open PHY | full waveform control | research-grade joint comms+sensing (802.11bf-style) |

**Difficulty** blends SNR sensitivity, calibration burden, sample-rate needs, and — heavily — how badly it fails out-of-domain.

- **Low** — works from RSSI/coarse CSI, robust, little per-deployment tuning.
- **Medium** — needs clean CSI, some denoising, a trained model; degrades across environments.
- **High** — needs phase calibration, multiple antennas/links, careful placement; strong overfitting risk.
- **Very High** — sub-millimetre effects or fine spatial resolution at the edge of what commodity Wi-Fi can resolve; mostly single-subject, single-room, lab-only.

**Maturity** — *Research* (papers, no reproducible product); *Emerging* (startups/standards forming, e.g. IEEE **802.11bf** WLAN Sensing); *Productized* (shipping consumer/enterprise product).

**Capabilities** map to the caps enum: `monitor`, `csi`, `spectral-scan`, `raw-iq`, `fmcw`, `radar`, `arbitrary-waveform`.

---

## Master table

| # | Application | Min tier | Capability | Best commodity hardware | Canonical system(s) | Difficulty | Maturity |
|---|---|---|---|---|---|---|---|
| 1 | Presence / occupancy | 1 | `monitor` (RSSI); `csi` better | any monitor-mode NIC; ESP32 for CSI | FreeDetector; commercial "Wi-Fi Motion" | Low | **Productized** |
| 2 | People counting / crowd density | 2 | `csi` | Intel 5300, Atheros ath9k, ESP32 | Electronic Frog Eye (INFOCOM'14); CrossCount | Medium | Emerging |
| 3 | Motion / intrusion detection | 1 | `monitor`; `csi` better | any monitor NIC; mesh routers | PADS; Origin Wireless TR; 802.11bf | Low | **Productized** |
| 4 | Activity recognition (ADL) | 2 | `csi` | Intel 5300, bcm43455c0 (Nexmon), ESP32 | CARM (MobiCom'15); E-eyes (MobiCom'14) | Medium | Research |
| 5 | Gesture recognition | 2 | `csi` (commodity); `raw-iq` for Doppler | Intel 5300, Atheros; USRP for WiSee | WiGest (INFOCOM'15); WiSee (MobiCom'13); Widar3.0 | Medium–High | Research |
| 6 | Fall detection | 2 | `csi` | Intel 5300, bcm43455c0, ESP32 | WiFall; RT-Fall (TMC'17); FallDeFi | Medium | Emerging |
| 7 | Respiration / breathing | 2 | `csi`; `fmcw` far better | Nexmon CSI on Pi; TI mmWave for FMCW | UbiBreathe; PhaseBeat; Vital-Radio (FMCW) | Medium–High | **Productized** (radar) |
| 8 | Heart-rate | 2 (hard) | `csi`; `fmcw` strongly preferred | TI IWR/AWR mmWave; Intel 5300 for CSI | Vital-Radio (CHI'15); TensorBeat | High | Emerging (radar productized) |
| 9 | Sleep monitoring / staging | 2 | `csi`; `fmcw` | Nexmon CSI; mmWave/UWB radar | Liu et al. INFOCOM'15; RF-Sleep (ICML'17) | High | **Productized** (radar) |
| 10 | Gait recognition / identity | 2 | `csi` | Intel 5300, Atheros ath9k | WiWho (IPSN'16); WifiU (UbiComp'16) | High | Research |
| 11 | Localization / passive tracking | 2 | `csi` (phase, multi-antenna) | Intel 5300 (3×3), Atheros; FTM-capable NICs | SpotFi (SIGCOMM'15); Widar/Widar2.0 | High | Emerging (FTM productized) |
| 12 | Pose estimation / imaging | 2 | `csi` (rich, many subcarriers) | Intel 5300 arrays; FMCW radar for RF-Pose | Person-in-WiFi (ICCV'19); WiPose; DensePose-from-WiFi | Very High | Research |
| 13 | Keystroke / typing inference | 2 | `csi` (high packet rate) | Intel 5300 (high injection rate) | WiKey (MobiCom'15); WindTalker | Very High | Research (security PoC) |
| 14 | Material / liquid sensing | 2 | `csi`; UWB/RFID variants | Intel 5300 CSI; DW1000/DW3000 UWB; RFID | TagScan (MobiCom'17); LiquID (MobiSys'18, UWB) | Very High | Research |

> **The tier-2 gravity well.** Note how nearly everything collapses onto **Tier 2 / CSI**. That is the whole reason this catalog lives next to a chip catalog: the single most valuable capability to unlock on any Wi-Fi chip is *CSI export*, and the walkthroughs that get you there ([Nexmon CSI → usable CSI](../docs/walkthroughs/nexmon-csi-to-usable-csi.md), [Atheros ath9k spectral+CSI](../docs/walkthroughs/atheros-ath9k-spectral-csi.md)) are the on-ramp to two-thirds of this table.

---

## Application deep-dives

### The presence / motion family (Tier 1 → 2)

These are the **easiest and most productized** — they detect *that* something moved, not *what*.

**1. Presence / occupancy.** Is the room occupied? A moving body perturbs the multipath channel; even RSSI variance over a sliding window separates empty from occupied. CSI raises reliability (still vs. subtle motion like breathing). This is the load-bearing feature behind consumer "Wi-Fi Motion": **Cognitive Systems / Plume Motion**, **Origin Wireless (Hex Home / time-reversal)**, and **Xandar Kardian**. Standardized under **IEEE 802.11bf** WLAN Sensing. *Difficulty Low; Productized.*

**3. Motion / intrusion detection.** Same primitive tuned for alarms: detect an intruder's motion across a link with no wearable. **PADS** ("Omnidirectional Passive Human Detection") showed device-free detection from CSI amplitude+phase; commercial mesh systems ship this today as security features. Failure modes (pets, HVAC, curtains) are exactly the [honest-limitations](../docs/honest-limitations-of-wifi-sensing.md) content. *Difficulty Low; Productized.*

**2. People counting / crowd density.** Counting bodies is much harder than detecting one. **Electronic Frog Eye: Counting Crowd Using WiFi** (Xi et al., IEEE INFOCOM 2014) used the *percentage of nonzero CSI variance* (the "PEM" monotonic relation) to estimate crowd size. **CrossCount** (Ibrahim et al.) counts via a deep model over link-blockage. Accuracy is a count *range*, not a headcount, and degrades with density. *Difficulty Medium; Emerging (retail/occupancy analytics).*

Hardware: any monitor-mode NIC for RSSI presence; step up to **ESP32** (cheap CSI) or **Intel 5300 / Atheros ath9k** for CSI counting.

### Activity, gesture, and HCI (Tier 2, occasionally Tier 4)

**4. Activity recognition (activities of daily living).** Classify walk / sit / stand / fall / cook, etc. The two foundational systems:

- **E-eyes** (Wang, Liu, Wu, Yang, Chen, *Device-free Location-oriented Activity Identification Using Fine-grained WiFi Signatures*, MobiCom 2014) — CSI amplitude histograms as location/activity fingerprints.
- **CARM** (Wang, Liu, Shahzad, Ling, Lu, *Understanding and Modeling of WiFi Signal Based Human Activity Recognition*, MobiCom 2015) — the **CSI-speed ↔ CSI-activity** model relating Doppler of body parts to CSI power; still the reference model for principled CSI activity work.

*Difficulty Medium; Research.* This is the sweet spot of the [ml-csi-sensing](../docs/ml-csi-sensing.md) guide.

**5. Gesture recognition.** Two lineages:

- **Doppler / SDR lineage — WiSee** (Pu, Gupta, Gollakota, Patel, *Whole-Home Gesture Recognition Using Wireless Signals*, MobiCom 2013). Extracts micro-Doppler from OFDM using a **USRP** — this is genuinely a **Tier 4 (`raw-iq`)** application, not commodity CSI. It is the classic demonstration that a repurposed radio does radar-style gesture sensing.
- **Commodity CSI lineage — WiGest** (Abdelnasser, Youssef, Harras, INFOCOM 2015; RSSI-based), **WiFinger**, **WiG**, and **Widar3.0** (Zheng et al., *Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi*, MobiSys 2019) — Widar3.0 introduced the **Body-coordinate Velocity Profile (BVP)**, a domain-independent feature, and released a large public gesture dataset (see [../projects/wifi-sensing-datasets.md](../projects/wifi-sensing-datasets.md)).

*Difficulty Medium–High; Research.* Cross-user generalization is the crux; Widar3.0's BVP is the most serious attempt at it.

### Contactless vital signs (Tier 2 CSI, Tier 4 FMCW is the "real" answer)

Sub-millimetre chest displacement (breathing ≈ mm, heartbeat ≈ 0.2–0.5 mm) is at the very edge of commodity Wi-Fi. **CSI phase** methods work in controlled setups; **FMCW radar** is what actually ships.

**7. Respiration / breathing.**
- Commodity CSI: **UbiBreathe** (Abdelnasser et al., MobiHoc 2015, RSSI), **PhaseBeat** (Wang et al., ICDCS 2017, CSI phase-difference), **FullBreathe**, **TR-BREATH** (time-reversal). Needs a still subject and good placement.
- Radar (the productized path): **Vital-Radio** (Adib, Mao, Kabelac, Katabi, Miller, *Smart Homes that Monitor Breathing and Heart Rate*, CHI 2015) using **FMCW** — spun into **Emerald**. TI **IWR/AWR mmWave** dev kits reproduce this today.

*Difficulty Medium–High. Productized in the radar branch; CSI branch is Research.*

**8. Heart-rate.** Harder than respiration because the heartbeat signal is an order of magnitude smaller and buried under the respiration harmonic. Best commodity attempts: **TensorBeat** (Xu et al., *Tensor Decomposition for Monitoring Multi-Person Breathing Beatings with Commodity WiFi*, tensor-decomposition on CSI) and PhaseBeat. **FMCW / mmWave (Vital-Radio)** is far more reliable. *Difficulty High; Emerging (radar productized, CSI research).*

**9. Sleep monitoring / staging.** Vital signs + posture + motion over a night. **Liu et al.** (*Tracking Vital Signs During Sleep Leveraging Off-the-shelf WiFi*, MobiHoc/INFOCOM 2015) did commodity-CSI sleep vitals. **RF-Sleep** (Zhao, Yue, Katabi et al., *Learning Sleep Stages from Radio Signals*, ICML 2017) staged sleep from RF using a custom FMCW radio + adversarial domain-invariant model. Productized broadly today via **mmWave/UWB** sleep radars (and Google **Nest/Soli**-style sensing). *Difficulty High; Productized in the radar branch.*

Hardware note: for any vital-signs work, start with **Nexmon CSI on a Raspberry Pi (bcm43455c0)** for the commodity path ([walkthrough](../docs/walkthroughs/bcm43455c0-raspberry-pi.md)), but expect a **TI mmWave FMCW** kit to outperform it dramatically. See tier-4 verification: [../docs/verification-tier4.md](../docs/verification-tier4.md).

### Identity, localization, and imaging (Tier 2, high phase fidelity)

**10. Gait recognition / person identification.** Gait cadence and torso Doppler are semi-biometric. **WiWho** (Zeng, Pathak, Mohapatra, *WiFi-Based Person Identification in Smart Spaces*, IPSN 2016) and **WifiU** (Wang, Zhou, Wu, Ni, *Gait Recognition Using WiFi Signals*, UbiComp 2016) identify small closed sets (≈ 2–20 people) in-domain. Does **not** generalize to open-world identity; treat as convenience personalization, not authentication. *Difficulty High; Research.*

**11. Localization / passive tracking.** Locate/track a device or a body without a wearable.
- **SpotFi** (Kotaru, Joshi, Bharadia, Katti, *Decimeter Level Localization Using WiFi*, SIGCOMM 2015) — super-resolution **AoA + ToF** from CSI on the Intel 5300 (3×3), the reference for CSI localization.
- **Widar / Widar2.0** (Qian et al., MobiHoc 2017 / MobiSys 2018) — *device-free* passive tracking via a velocity/Doppler model, single-link in 2.0.
- Productized branch: **802.11mc FTM (Fine Timing Measurement / RTT)** ranging in modern APs/phones.

*Difficulty High.* Needs multi-antenna CSI **phase** and sanitization (see [techniques.md](../docs/techniques.md) on CSI phase calibration). Emerging via FTM.

**12. Pose estimation / RF imaging.** Reconstruct a skeleton — or a dense body surface — from RF.
- **Person-in-WiFi** (Wang, Zhu et al., *Fine-grained Person Perception using WiFi*, ICCV 2019) — segmentation + joints from CSI, teacher-student supervised by a camera.
- **WiPose** (Jiang et al., *Towards 3D Human Pose Construction Using WiFi*, MobiCom 2020) — 3D skeleton from CSI.
- **DensePose From WiFi** (Geng, Huang, De la Torre, arXiv:2301.00250, 2023) — dense UV body map from three-antenna CSI.
- Radar cousin: **RF-Pose / RF-Pose3D** (Zhao et al., CVPR/SIGCOMM 2018), FMCW.

*Difficulty Very High; Research.* These are heavily camera-supervised and in-domain; the reproducibility caveats in [honest-limitations](../docs/honest-limitations-of-wifi-sensing.md) apply most sharply here.

### Security side-channels (Tier 2, high sample rate)

**13. Keystroke / typing inference.** CSI perturbations from finger/hand micro-motion leak what someone types. **WiKey** (Ali, Liu, Wang, Shahzad, *Keystroke Recognition Using WiFi Signals*, MobiCom 2015) classified keys in a controlled single-user setup; **WindTalker** (Li et al., CCS 2016) inferred mobile PINs from a rogue AP. Requires **high packet/injection rate** for CSI temporal resolution and is extremely sensitive to setup — a genuine privacy concern but not a turnkey attack. *Difficulty Very High; Research (security PoC).* This is why the injection-rate discussion in [../docs/verification-tier1-injection.md](../docs/verification-tier1-injection.md) matters here.

### Material and liquid sensing (Tier 2 CSI, or UWB/RFID)

**14. Material / liquid identification.** Different materials have distinct complex permittivity, changing attenuation/phase of a signal passing through them.
- **TagScan** (Wang, Xie et al., *Simultaneous Target Imaging and Material Identification with Commodity RFID Devices*, MobiCom 2017) — RFID.
- **LiquID** (Dhekne, Gowda, Zhao, Hassanieh, Choudhury, *A Wireless Liquid IDentifier*, MobiSys 2018) — **UWB** (impulse radio), identifies liquids by their dielectric signature.
- Wi-Fi CSI variants ("material identification with commodity Wi-Fi") exist but are the least mature. Adjacent UWB hardware in the catalog: **DW1000 / DW3000**.

*Difficulty Very High; Research.* Highly sensitive to container geometry and placement.

---

## Hardware cheat-sheet (which chip for which job)

| If you want… | Use | Tier | Why | Getting-started doc |
|---|---|---|---|---|
| Cheapest CSI, embedded | **ESP32** (ESP32 CSI Toolkit) | 2 | Trivial CSI export, tiny/cheap; low subcarrier count | [../chips/espressif.md](../chips/espressif.md) |
| Best-documented commodity CSI | **Intel 5300** (Linux 802.11n CSI Tool) | 2 | 30-subcarrier × 3×3, huge legacy corpus (SpotFi, WiKey, CARM) | [../chips/intel.md](../chips/intel.md) |
| CSI **and** spectral scan | **Atheros ath9k** (Atheros CSI Tool) | 2–3 | Open driver, per-packet CSI + spectral FFT | [../docs/walkthroughs/atheros-ath9k-spectral-csi.md](../docs/walkthroughs/atheros-ath9k-spectral-csi.md) |
| CSI on a self-contained SBC | **bcm43455c0** on Raspberry Pi (Nexmon CSI) | 2 | Full 80 MHz CSI on a $35 board | [../docs/walkthroughs/bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md) |
| Doppler-radar gesture | **USRP / any raw-IQ SDR** | 4 | WiSee-style micro-Doppler needs `raw-iq` | [../docs/verification-tier4.md](../docs/verification-tier4.md) |
| Reliable vitals / sleep / pose | **TI IWR/AWR mmWave FMCW** | 4 | mm-scale displacement, range-Doppler | [../docs/verification-tier4.md](../docs/verification-tier4.md) |
| Liquid / material ID | **DW1000 / DW3000 UWB** | — | wideband dielectric signature | [../chips/other-vendors.md](../chips/other-vendors.md) |

Turn raw CSI into something usable with [../docs/walkthroughs/nexmon-csi-to-usable-csi.md](../docs/walkthroughs/nexmon-csi-to-usable-csi.md), then model it per [../docs/ml-csi-sensing.md](../docs/ml-csi-sensing.md).

---

## Cross-cutting reality check

Every accuracy figure in the source papers should be read as **"achievable in the authors' room, with their subjects, on their hardware."** Before quoting any of the systems above, apply the four filters from [honest-limitations-of-wifi-sensing.md](../docs/honest-limitations-of-wifi-sensing.md):

1. **Domain gap.** In-domain 95% routinely becomes 50–70% cross-environment/cross-person. Widar3.0's BVP and RF-Sleep's adversarial training exist *specifically because* naive models don't transfer.
2. **Ground-truth leakage.** Camera-supervised systems (pose, some activity) can encode camera-view bias, not RF physics.
3. **Subject count.** Almost all vital-signs, gait, and keystroke results are **single-subject**. Multi-person separation (TensorBeat, multi-target FMCW) is a distinct, harder problem.
4. **Silicon quirks.** CSI phase needs per-chip sanitization; amplitude scaling and AGC differ across the chips above. What trains on an Intel 5300 rarely runs unchanged on an ESP32.

For sensing that must be robust, the honest ordering is: **radar/FMCW (Tier 4) > multi-antenna commodity CSI (Tier 2, calibrated) > single-link CSI > RSSI (Tier 1)** — inverse to how cheap/accessible each is.

---

## References

Cited by full title / authors / venue / year for verifiability; stable URLs where confidently known.

- Xi et al. **Electronic Frog Eye: Counting Crowd Using WiFi.** IEEE INFOCOM 2014.
- Wang, Liu, Wu, Yang, Chen. **E-eyes: Device-free Location-oriented Activity Identification Using Fine-grained WiFi Signatures.** ACM MobiCom 2014.
- Wang, Liu, Shahzad, Ling, Lu. **Understanding and Modeling of WiFi Signal Based Human Activity Recognition (CARM).** ACM MobiCom 2015.
- Pu, Gupta, Gollakota, Patel. **Whole-Home Gesture Recognition Using Wireless Signals (WiSee).** ACM MobiCom 2013.
- Abdelnasser, Youssef, Harras. **WiGest: A Ubiquitous WiFi-based Gesture Recognition System.** IEEE INFOCOM 2015.
- Zheng, Zhang, Qian, Yang, Liu et al. **Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi (Widar3.0).** ACM MobiSys 2019. Dataset: <http://tns.thss.tsinghua.edu.cn/widar3.0/>
- Wang, Wu et al. **WiFall: Device-free Fall Detection by Wireless Networks.** IEEE INFOCOM 2014 / IEEE TMC.
- Wang, Wu, Ni. **RT-Fall: A Real-Time and Contactless Fall Detection System with Commodity WiFi Devices.** IEEE TMC 2017.
- Abdelnasser, Harras, Youssef. **UbiBreathe: A Ubiquitous non-Invasive WiFi-based Breathing Estimator.** ACM MobiHoc 2015.
- Wang, Zhou, Wu, Yang, Liu. **PhaseBeat: Exploiting CSI Phase Data for Vital Sign Monitoring with Commodity WiFi Devices.** IEEE ICDCS 2017.
- Adib, Mao, Kabelac, Katabi, Miller. **Smart Homes that Monitor Breathing and Heart Rate (Vital-Radio).** ACM CHI 2015.
- Xu, Wang, Wu et al. **TensorBeat: Tensor Decomposition for Monitoring Multi-Person Breathing Beatings with Commodity WiFi.**
- Liu, Wang, Chen, Yang. **Tracking Vital Signs During Sleep Leveraging Off-the-shelf WiFi.** ACM MobiHoc / IEEE INFOCOM 2015.
- Zhao, Yue, Manoharan, Katabi et al. **Learning Sleep Stages from Radio Signals (RF-Sleep).** ICML 2017.
- Zeng, Pathak, Mohapatra. **WiWho: WiFi-Based Person Identification in Smart Spaces.** ACM/IEEE IPSN 2016.
- Wang, Zhou, Wu, Ni. **Gait Recognition Using WiFi Signals (WifiU).** ACM UbiComp 2016.
- Kotaru, Joshi, Bharadia, Katti. **SpotFi: Decimeter Level Localization Using WiFi.** ACM SIGCOMM 2015.
- Qian, Wu, Zhou, Yang. **Widar: Decimeter-Level Passive Tracking via Velocity Monitoring with Commodity Wi-Fi.** ACM MobiHoc 2017. (Widar2.0, MobiSys 2018.)
- Wang, Guo et al. **Person-in-WiFi: Fine-grained Person Perception using WiFi.** IEEE/CVF ICCV 2019.
- Jiang, Xue et al. **Towards 3D Human Pose Construction Using WiFi (WiPose).** ACM MobiCom 2020.
- Geng, Huang, De la Torre. **DensePose From WiFi.** arXiv:2301.00250, 2023. <https://arxiv.org/abs/2301.00250>
- Zhao, Li, Tian, Katabi et al. **Through-Wall Human Pose Estimation Using Radio Signals (RF-Pose).** IEEE/CVF CVPR 2018.
- Ali, Liu, Wang, Shahzad. **Keystroke Recognition Using WiFi Signals (WiKey).** ACM MobiCom 2015.
- Li, Zhang et al. **When CSI Meets Public WiFi: Inferring Your Mobile Phone Password via WiFi Signals (WindTalker).** ACM CCS 2016.
- Wang, Xie, Wang. **TagScan: Simultaneous Target Imaging and Material Identification with Commodity RFID Devices.** ACM MobiCom 2017.
- Dhekne, Gowda, Zhao, Hassanieh, Choudhury. **LiquID: A Wireless Liquid IDentifier.** ACM MobiSys 2018.
- IEEE 802.11bf Task Group — **WLAN Sensing** standardization.
