# Techniques: What You Can Actually Do Once a Wi-Fi Chip Is Unlocked

This document is the "verbs" half of Latent Radios. The chip files tell you *which* silicon can be
pried open and *how far up the ladder* it climbs; this file tells you *what to do* with each rung once
you are there. Every technique below is tagged with the **minimum SDR tier** and the **capability
flag(s)** it needs (see [../docs/taxonomy.md](../docs/taxonomy.md) for the ladder and flag
definitions), followed by landmark references and the legal/ethical cautions that apply.

The through-line: almost none of these techniques need a "real" SDR (USRP, HackRF). They run on a
$10 laptop card, a $30 router, or a phone — *provided* the firmware has been patched to expose the
telemetry or waveform hooks the silicon already computes internally. That patching work lives in
[../projects/csi-toolchains.md](../projects/csi-toolchains.md) and the chip files; this file assumes
you have already reached the stated tier and focuses on the signal-processing you build on top.

> **Blanket caution.** Much of what follows transmits, injects, senses people, or interferes with
> spectrum. Transmitting outside association, jamming, and covert emission are regulated (FCC Part 15
> in the US, RED/ETSI in the EU) and several are outright illegal in normal operation. Sensing humans
> raises privacy and, in some jurisdictions, wiretap/surveillance concerns. Treat everything here as
> research to be run in a shielded enclosure, on spectrum you are licensed for, or against your own
> devices with informed consent. The reactive-jamming section repeats this in stronger terms.

---

## Technique map (summary table)

| Technique | Min tier | Capability flag(s) | What the silicon must expose | Landmark ref |
|---|---|---|---|---|
| Monitor / injection recon | 1 | `monitor`, `injection` | Raw 802.11 RX/TX, channel hop | Aircrack-ng / nexmon |
| CSI presence & occupancy | 2 | `csi` | Per-subcarrier H(f) amplitude | E-eyes (MobiCom'14) |
| CSI respiration / heart-rate | 2 | `csi` | Fine-grained phase over time | Vital-Radio, FarSense |
| CSI gesture / activity | 2 | `csi` | Amplitude+phase, multi-antenna | WiSee, CARM, Widar3.0 |
| CSI indoor localization | 2 | `csi` | Phase across subcarriers/antennas | SpotFi, Widar2.0 |
| CSI fall detection | 2 | `csi` | Time-series amplitude/DFS | WiFall, Aryokee |
| Device-free pose / skeleton | 2 | `csi` | Dense CSI, multi-link | Person-in-WiFi |
| Passive / bistatic Wi-Fi radar | 2–3 | `passive-radar`, `raw-iq` | Reference + surveillance IQ | Chetty (TWS 2011) |
| Spectrum monitoring | 3 | `spectral-scan` | FFT bins regardless of frames | Atheros spectral scan |
| 802.11mc FTM ranging | 1 | `radar`/`fmcw` (ToF) | Hardware FTM timestamping | Wi-Fi RTT (Android 9) |
| FMCW-style ranging | 4 | `fmcw`, `arbitrary-waveform` | IQ chirp TX + coherent RX | WiTrack (NSDI'14) |
| Cross-technology comm (CTC) | 4 | `arbitrary-waveform`, `covert-channel` | Payload/IQ shaping of TX | WEBee (SIGCOMM'17) |
| Covert channels | 1–4 | `covert-channel` | Timing/CSI/waveform control | (see section) |
| Reactive jamming | 4 | `arbitrary-waveform`, `injection` | Sub-µs listen-then-TX on PHY | Schulz (WiSec'17) |

---

## 1. Monitor mode & frame injection — the ground floor

**Tier 1 · `monitor` + `injection`.** Before any "sensing" story, the baseline SDR-ish capability is
turning the NIC into a promiscuous 802.11 transceiver: receive every frame in the air regardless of
BSSID, hop channels, and craft/replay arbitrary frames (deauth, beacons, malformed headers, custom
management frames). This is the rung that the Aircrack-ng suite, `mdk4`, Scapy, and the nexmon
injection patches operate at. It is a prerequisite mindset for everything else — most CSI and radar
toolchains ride on a monitor-mode capture pipeline, and CTC/jamming ride on the injection path.

- **Unlock:** monitor is native on many mac80211 drivers; injection often needs a patched driver or
  firmware (nexmon for Broadcom, patched `ath9k`, Realtek out-of-tree drivers). See the chip files.
- **Refs:** Aircrack-ng suite docs; nexmon (`https://github.com/seemoo-lab/nexmon`).
- **Caution:** Deauth/disassoc injection is a denial-of-service against networks you may not own.
  Injecting on channels/bands you are not licensed for violates spectrum rules.

---

## 2. CSI-based sensing — the workhorse of Wi-Fi sensing

**Tier 2 · `csi`.** Channel State Information is the per-OFDM-subcarrier complex channel response
H(f) = amplitude ∠ phase that the receiver estimates from the preamble to equalize each packet. The
silicon computes it for every frame; unlocking tier 2 means dumping that matrix (N_subcarriers ×
N_rx × N_tx) to userspace instead of discarding it. The extraction toolchains (Intel 5300 CSI Tool,
Atheros CSI Tool, nexmon_csi, ESP32-CSI, PicoScenes) are catalogued in
[../projects/csi-toolchains.md](../projects/csi-toolchains.md). Everything in this section is the
signal processing you layer on top of that CSI stream.

The canonical pipeline: **sanitize** (remove CFO/SFO/STO phase offsets, unwrap, conjugate-multiply
across antennas to cancel random phase), **extract a feature** (amplitude variance, Doppler
frequency shift / DFS, time-of-flight, angle-of-arrival), then **classify or track**.

### 2.1 Presence, occupancy & motion detection

The simplest use: variance/entropy of CSI amplitude over a short window rises sharply when a body
moves in the link. **E-eyes** (Wang et al., MobiCom 2014) used CSI amplitude histograms to recognize
in-home daily activities and locations. Presence detection is robust enough to ship in commercial
"Wi-Fi motion" products.

- **Refs:** E-eyes, *Device-free Location-oriented Activity Identification*, MobiCom 2014
  (`https://dl.acm.org/doi/10.1145/2639108.2639143`).
- **Caution:** occupancy sensing of spaces/people without notice is a privacy issue; some
  jurisdictions treat it as surveillance.

### 2.2 Respiration & heart-rate

Chest displacement of millimetres periodically modulates CSI phase/amplitude at 0.2–0.5 Hz
(breathing) and ~1 Hz (heartbeat). FFT/peak-tracking on a stationary subject recovers vital signs.
**CARM** established the CSI-speed/CSI-activity model linking Doppler to body-part velocity;
**FarSense** (Zhang et al., 2019) introduced the **CSI-ratio** (dividing CSI of two antennas) to
cancel the amplitude noise and phase offset, roughly doubling the sensing range for respiration. MIT's
**Vital-Radio** (Adib et al., CHI 2015) did the same with an FMCW radio rather than commodity CSI.

- **Refs:** FarSense (`https://dl.acm.org/doi/10.1145/3351279`); CARM, *Understanding and Modeling of
  WiFi Signal Based Human Activity Recognition*, MobiCom 2015; Vital-Radio, CHI 2015.
- **Caution:** heart/respiration data is health-adjacent; handle under the same care as medical data.

### 2.3 Gesture & activity recognition

Motion imparts a **Doppler frequency shift** on the multipath; different gestures produce different
DFS signatures. The landmark line:

- **WiSee** (Pu et al., MobiCom 2013) — the origin story: extracted micro-Doppler from
  (USRP-based, but OFDM-Wi-Fi-shaped) signals to recognize nine whole-body gestures through walls.
- **WiHear** (Wang et al., MobiCom 2014) — "hearing" mouth motion / lip-reading via CSI.
- **CARM** (2015) — modelled the CSI↔velocity relationship, enabling activity classification.
- **SignFi** (Ma et al., 2018) — 276 sign-language gestures with a CNN on Intel-5300 CSI.
- **Widar 3.0** (Zheng et al., MobiSys 2019) — the **Body-coordinate Velocity Profile (BVP)**, a
  domain-independent feature giving **zero-effort cross-domain** gesture recognition (92.7% in-domain,
  82.6–92.4% cross-domain, no retraining). This is the reference dataset/method the field builds on.

- **Refs:** WiSee (`https://dl.acm.org/doi/10.1145/2500423.2500436`); Widar3.0
  (`https://dl.acm.org/doi/10.1145/3307334.3326081`, dataset at
  `https://tns.thss.tsinghua.edu.cn/widar3.0/`); SignFi
  (`https://dl.acm.org/doi/10.1145/3191755`).
- **Caution:** gesture/activity inference of non-consenting people is covert behavioral surveillance.

### 2.4 Indoor localization & tracking

CSI carries **Angle-of-Arrival** (phase slope across antennas) and **Time-of-Flight** (phase slope
across subcarriers). **SpotFi** (Kotaru et al., SIGCOMM 2015) ran a super-resolution (MUSIC) joint
AoA/ToF estimate on Intel-5300 CSI to localize to tens of centimetres with a single AP.
**Widar/Widar2.0** (Qian et al., MobiSys 2018) tracked a moving person's location *and* velocity
device-free from one or two links using the Doppler-AoA-ToF geometry.

- **Refs:** SpotFi (`https://dl.acm.org/doi/10.1145/2785956.2787487`); Widar2.0
  (`https://dl.acm.org/doi/10.1145/3210240.3210321`).
- **Caution:** device-free tracking of people is location surveillance; consent/notice apply.

### 2.5 Fall detection

A fall is a fast, high-energy, then-quiescent DFS event with a distinctive time signature —
attractive for elder-care because it is device-free and camera-free. **WiFall** (Han et al.) and
later **Aryokee** (RF-based, MIT) demonstrated robust fall classification.

- **Refs:** WiFall, *Device-free fall detection*, IEEE TMC 2017; RF-based fall detection (Aryokee),
  UbiComp 2018.
- **Caution:** a safety-of-life classifier must be validated before reliance; false negatives harm.

### 2.6 Device-free pose / skeleton estimation

The high end of CSI sensing: regress a full 2D/3D human skeleton from CSI. **Person-in-WiFi** (Wang
et al., ICCV 2019) trained on synchronized camera+CSI to produce body segmentation and keypoints from
Wi-Fi alone; DensePose-from-WiFi (2022) extended this to dense body-surface mapping.

- **Refs:** Person-in-WiFi (`https://arxiv.org/abs/1904.00276`).
- **Caution:** "seeing" body pose through walls is the most invasive rung here; strong consent
  requirement, and note the reputational/ethical debate these papers triggered.

---

## 3. Passive & bistatic Wi-Fi radar

**Tier 2–3 · `passive-radar` + `raw-iq`.** Instead of your own CSI, use an *illuminator of
opportunity* — someone else's (or your own) AP continuously beaconing. One antenna captures the
**reference** signal (direct path from the AP), a second captures the **surveillance** channel
(reflections off moving targets). Cross-ambiguity processing (cross-correlation over range/Doppler,
with CLEAN/adaptive-filter suppression of the strong direct path) yields a range-Doppler map of moving
scatterers — a true passive radar built from Wi-Fi energy. Chetty et al. demonstrated **through-wall**
personnel detection this way; Tan et al. built real-time passive Wi-Fi radar from a standalone AP.

Commodity-card variants approximate this at tier 2 by treating CSI time-series as the surveillance
channel; a genuine range-Doppler map wants coherent raw IQ (tier 3+, usually a real SDR reference
receiver or a spectral-scan-capable card as the sensor).

- **Refs:** Chetty et al., *Through-the-Wall Sensing of Personnel Using Passive Bistatic WiFi Radar*,
  IEEE TGRS 2012 (`https://ieeexplore.ieee.org/document/6020778/`); Tan et al., *Passive WiFi Radar
  for Human Sensing Using a Stand-Alone Access Point*, IEEE TGRS 2020.
- **Caution:** covertly detecting people behind walls is exactly the surveillance capability privacy
  law worries about; and if you inject your own illuminator you are back under TX rules.

---

## 4. Spectrum monitoring via spectral scan

**Tier 3 · `spectral-scan`.** Some PHYs expose the FFT bins from their internal spectral engine —
power per frequency bin across the channel, computed whether or not a valid 802.11 frame is present.
This turns the NIC into a cheap, narrow (per-channel, ~20–80 MHz) spectrum analyzer that can see
microwave ovens, Bluetooth/BLE hoppers, ZigBee, cordless phones, radar (DFS), and jammers.

The reference implementation is the **Atheros ath9k spectral scan** (`spectral_scan_ctl`,
FFT bins via a debugfs/relay interface; visualized by tools like `speccy`/`Ath9k-Spectral`). Broadcom
FullMAC parts expose a similar engine that nexmon has partially surfaced. Intel and others compute
spectral data internally but rarely expose it.

- **Refs:** Linux `ath9k` spectral-scan docs
  (`https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan`); nexmon.
- **Caution:** passive receive-only spectrum monitoring is generally lawful, but acting on what you
  see (e.g. to target jamming) is not.

---

## 5. Ranging: 802.11mc FTM and FMCW-style methods

### 5.1 802.11mc Fine Timing Measurement (FTM / Wi-Fi RTT)

**Tier 1 conceptually, but needs hardware ToF timestamping.** FTM (added in IEEE 802.11mc, 2016) is a
standardized two-way time-of-flight exchange: an initiator and responder trade timestamped frames, and
distance = ½·c·(RTT − responder turnaround). It is *not* a firmware hack — it is a blessed feature —
but it is the standards-track cousin of everything else here and gives metre-level ranging on
**commodity** hardware. Android exposes it as **Wi-Fi RTT** (`WifiRttManager`, API 28 / Android 9),
requiring an AP that advertises FTM responder support. **802.11az** (Next-Gen Positioning) tightens
this with secure, higher-accuracy ranging.

- **Refs:** Android Wi-Fi RTT (`https://developer.android.com/develop/connectivity/wifi/wifi-rtt`);
  IEEE 802.11-2016 §FTM; 802.11az.
- **Caution:** benign; ranging others' devices en masse can still be a tracking concern.

### 5.2 FMCW-style ranging / true chirp radar

**Tier 4 · `fmcw` + `arbitrary-waveform`.** For fine ranging you author a **frequency-modulated
continuous-wave chirp** as a baseband IQ buffer, transmit it, and coherently mix the echo — classic
radar. MIT's **WiTrack** (Adib et al., NSDI 2014) did exactly this in the Wi-Fi band with a custom
FMCW front-end: 3D body localization to ~10–13 cm (x/y) and ~21 cm (z), through walls, device-free —
the "gold standard" that commodity CSI methods try to approximate without arbitrary TX. Reaching this
on a Wi-Fi *chip* (rather than a USRP) requires the rare arbitrary-waveform-TX unlock (tier 4); most
parts cannot, which is precisely why CSI/Doppler methods dominate the commodity literature.

- **Refs:** WiTrack (`https://witrack.csail.mit.edu/witrack-paper.pdf`, NSDI 2014); WiTrack2.0
  (multi-person), NSDI 2015.
- **Caution:** wideband chirps sweep across channels/bands you are unlikely to be licensed for.

---

## 6. Cross-technology communication (CTC) & covert channels

**Tier 4 · `arbitrary-waveform` + `covert-channel`** (payload-shaping variants can reach down to
tier 1). CTC makes a Wi-Fi radio *emit a waveform another standard's receiver decodes* — no gateway,
no extra hardware. The seminal trick is **physical-layer emulation**: **WEBee** (Li & He, SIGCOMM
2017) hand-crafts a Wi-Fi OFDM **payload** whose resulting time-domain signal approximates a ZigBee
(802.15.4 O-QPSK) chip sequence, so a stock ZigBee node decodes it — >99% reliability at ~126 kbps,
thousands of times faster than packet-timing CTC, with *no firmware change* on either side (the shaping
is entirely in the transmitted bytes, so this variant is remarkably low-tier). Follow-ons broaden the
matrix:

- **BlueBee** — WiFi/BLE ↔ ZigBee via PHY emulation.
- **BlueFi** (Li et al., MobiSys 2021) — BLE → Wi-Fi.
- **WIDE** / **NNCTC** — digital-emulation and neural-network-shaped CTC with far better packet
  reception than WEBee.
- **LongBee / LoRa-targeted CTC** — reaching LPWAN receivers.

True arbitrary-waveform TX (tier 4, e.g. via nexmon's IQ-injection on some Broadcom parts, or an
open-firmware ESP-class radio) generalizes this to authoring *any* baseband buffer — the same hook
that FMCW radar and reactive jamming rely on.

**Covert channels** are the adversarial cousin: encode data where it is not expected — inter-frame
timing, CSI perturbations a colluding receiver reads, spectral notches, or a CTC waveform hidden in an
otherwise-normal Wi-Fi packet. These range from tier 1 (timing) to tier 4 (waveform).

- **Refs:** WEBee, *Physical-Layer Cross-Technology Communication via Emulation*, SIGCOMM 2017
  (`https://experts.umn.edu/en/publications/webee-physical-layer-cross-technology-communication-via-emulation/`);
  BlueFi (`https://dl.acm.org/doi/10.1145/3458864.3466865`); Tsinghua CTC hub
  (`https://tns.thss.tsinghua.edu.cn/sun/researches/Cross-TechnologyCommunication.html`).
- **Caution:** emulating another standard's waveform can transmit on spectrum/in a manner your device
  is not certified for; covert channels are, by definition, an exfiltration/evasion technique — legit
  only in authorized research or your own devices.

---

## 7. Reactive jamming (defensive & research framing only)

**Tier 4 · `arbitrary-waveform` + `injection`.** A **reactive** jammer listens for a specific
in-flight signal (a preamble, a target MAC, a UDP port) and emits interference *only* during that
transmission — far stealthier and more energy-efficient than a constant jammer, and able to be
**selective** (corrupt one flow while others pass). Doing this on a Wi-Fi *chip* requires running code
on the chip's real-time PHY processor with sub-microsecond listen-then-transmit latency plus
arbitrary-waveform TX — a capability Schulz et al. demonstrated with **nexmon** jamming firmware on a
Nexus 5 (Broadcom BCM4339), reacting within the same frame and even ACK-spoofing to defeat
retransmission. The USRP/GNU Radio equivalent (protocol-aware reactive jammer, ~80 ns reaction) shows
the same on a real SDR.

Why it belongs in a *defensive/research* catalog: it is the sharpest demonstration that an unlocked
commodity Wi-Fi chip has crossed fully into SDR territory (author a waveform, time it to the PHY), and
it is essential for studying jamming resilience, building reactive-jamming *detectors*, and testing
anti-jamming (frequency-hopping, spread-spectrum) defenses.

- **Refs:** Schulz et al., *Massive Reactive Smartphone-Based Jamming using Arbitrary Waveforms and
  Adaptive Power Control*, ACM WiSec 2017 (`https://dl.acm.org/doi/10.1145/3098243.3098253`); nexmon.
- **⚠ Strong caution.** Jamming is **illegal to operate** in essentially every jurisdiction (in the
  US, 47 U.S.C. §333 and FCC prohibitions carry serious criminal/civil penalties) — there is no
  hobbyist exemption, and "reactive/selective" does not change that. Run **only** inside a fully
  RF-shielded enclosure (Faraday cage / anechoic chamber) against your own equipment. Never operate
  over the air. Publish and build detectors, not weapons.

---

## Cross-references

- Ladder and capability-flag definitions: [../docs/taxonomy.md](../docs/taxonomy.md)
- The CSI extraction toolchains that make tier 2 real: [../projects/csi-toolchains.md](../projects/csi-toolchains.md)

## Selected references (primary)

- Pu et al., **WiSee**, MobiCom 2013 — `https://dl.acm.org/doi/10.1145/2500423.2500436`
- Adib et al., **WiTrack**, NSDI 2014 — `https://witrack.csail.mit.edu/witrack-paper.pdf`
- Wang et al., **E-eyes**, MobiCom 2014 — `https://dl.acm.org/doi/10.1145/2639108.2639143`
- Wang et al., **CARM**, MobiCom 2015
- Kotaru et al., **SpotFi**, SIGCOMM 2015 — `https://dl.acm.org/doi/10.1145/2785956.2787487`
- Ma et al., **SignFi**, IMWUT 2018 — `https://dl.acm.org/doi/10.1145/3191755`
- Qian et al., **Widar2.0**, MobiSys 2018 — `https://dl.acm.org/doi/10.1145/3210240.3210321`
- Zheng et al., **Widar3.0**, MobiSys 2019 — `https://dl.acm.org/doi/10.1145/3307334.3326081`
- Zhang et al., **FarSense**, IMWUT 2019 — `https://dl.acm.org/doi/10.1145/3351279`
- Wang et al., **Person-in-WiFi**, ICCV 2019 — `https://arxiv.org/abs/1904.00276`
- Chetty et al., **Passive Bistatic WiFi Radar**, IEEE TGRS 2012 — `https://ieeexplore.ieee.org/document/6020778/`
- Li & He, **WEBee**, SIGCOMM 2017 — `https://experts.umn.edu/en/publications/webee-physical-layer-cross-technology-communication-via-emulation/`
- Schulz et al., **Reactive smartphone jamming**, WiSec 2017 — `https://dl.acm.org/doi/10.1145/3098243.3098253`
- Android **Wi-Fi RTT / FTM** — `https://developer.android.com/develop/connectivity/wifi/wifi-rtt`
