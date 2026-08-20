# People Counting & Occupancy with Wi-Fi CSI

*Latent Radios — Cycle 8. How commodity Wi-Fi channel-state information (CSI) is turned into a "how many people are in this space" estimate, why the accuracy ceiling is real, and what that means when the same trick ships inside a building-management product.*

Counting people from Wi-Fi is the archetypal **device-free** sensing task: the humans carry nothing, opt into nothing, and are sensed as *perturbations of the channel* between an ordinary transmitter and receiver. It sits one rung of ambition above presence detection (is anyone here?) and one rung below activity recognition (see [`wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md)). Unlike those, counting has a hard, physics-imposed ceiling — this page is mostly about *where* that ceiling is and *why*.

> This is a **sensing/analysis** walkthrough, not a firmware-RE exploit. The "radio" here is a stock NIC in monitor/CSI mode; the SDR-ladder tier of the underlying chip is unchanged. For the extraction toolchains, see [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md). For the epistemics of "my model got 95%," read [`../../docs/sensing-limitations-and-pitfalls.md`](../../docs/honest-limitations-of-wifi-sensing.md) **before** you trust any number below.

---

## 1. The core idea in one paragraph

An empty room has a stable multipath channel. Each person is a large, wet, RF-absorbing/scattering obstacle that (a) shadows some paths, (b) creates new reflections, and (c) — if moving or even just breathing — modulates the channel over time. CSI captures per-subcarrier complex gain `H(f,t)`, so it sees these perturbations at fine granularity (dozens of subcarriers) rather than the single scalar RSSI gives you. **Counting** is then a regression: map some statistic of `H` (its variance, entropy, dominant-eigenvalue count, Doppler spread) to an integer *N*. The catch — foreshadowing Section 5 — is that this statistic **saturates**: the marginal channel change from the 8th person is far smaller than from the 1st.

---

## 2. The three approaches

### 2.1 Hand-crafted statistical mapping (the "Electronic Frog Eye" school)

The founding device-free-counting work, **Xi *et al.*, "Electronic Frog Eye: Counting Crowd Using WiFi" (IEEE INFOCOM 2014)**, observed that the *dispersion* of CSI grows monotonically with crowd size. Their key feature is **PEM (Percentage of nonzero Elements)** in a quantized/thresholded CSI matrix — busier channels light up more elements — and they fit the count with a **Grey Verhulst model**, an explicitly *S-shaped (saturating)* growth curve. That choice of a saturating fit is itself the first honest admission of the ceiling. Reported operating range was into the tens of people (queue/gathering scenarios) with coarse accuracy, not per-head exactness.

The RSSI-only cousin is the **Mostofi group** line, which counts people using *only received power*:

- **Depatla, Muralidharan & Mostofi, "Occupancy Estimation Using Only WiFi Power Measurements" (IEEE JSAC, 2015)** — a *probabilistic* model of how bodies both **block the line-of-sight** and **scatter** into it, fit with a **Kullback–Leibler-divergence** matching between measured and predicted power distributions. Demonstrated counting **up to ~9 people** in indoor and outdoor areas with a single link and no training on the crowd itself.
- Follow-ons extend the physics rather than the ML: **"Crowd Counting Through Walls Using WiFi" (PerCom 2018)**, **"Passive Crowd Speed Estimation and Head Counting Using WiFi" (SECON 2018)**, and **"Counting a Stationary Crowd Using Off-the-Shelf WiFi" (MobiSys 2021)** — the last is important because *stationary* crowds defeat motion-based methods and must be counted from **breathing-induced micro-Doppler**, a much weaker signal.

**When to use:** interpretable, trains once (or not at all), degrades gracefully. **Cost:** coarse; needs a physical/statistical model per geometry.

### 2.2 Cross-environment / calibration-light methods

**Di Domenico *et al.*, "A Trained-once Crowd Counting Method Using Differential WiFi Channel State Information" (3rd Int'l Workshop on Physical Analytics, 2016)** targets the transfer problem head-on: instead of raw CSI (environment-specific), it classifies on the **differential/temporal change** of CSI so a single trained model generalizes across rooms. This is the pragmatic middle ground between hand-crafted features and heavy deep nets.

### 2.3 Deep-learning regressors / classifiers

**Liu *et al.*, "DeepCount: Crowd Counting with WiFi via Deep Learning" (arXiv:1903.05316, 2019)** feeds CSI into a **CNN** (spatial subcarrier structure) plus **LSTM** (temporal dependence), framed as classification over occupancy bins. Reported **~86.4% accuracy for up to 5 people**, rising toward **~90%** when an activity-recognition "amendment" tracks room **entry/exit events** and corrects the running count — a telling design: the deep net alone plateaus, and the extra accuracy comes from *counting doors, not bodies*. Many later works follow the same recipe (spectrogram/CSI-image + CNN, sometimes attention or GNNs), and almost all cap their evaluation at a **handful of people**.

**When to use:** best raw accuracy in a *fixed, trained* environment. **Cost:** large labeled datasets, poor transfer, opaque failure modes (see the pitfalls doc — deep counters are prime candidates for latching onto a confounder like a ceiling fan or an HVAC duty cycle correlated with occupancy).

---

## 3. Capture setup (reproducible)

You need a TX–RX Wi-Fi link spanning the space, a way to force a steady packet stream, and a CSI extractor. See [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) for the full matrix; the usual suspects:

| Extractor | Chip / NIC | Subcarriers | Notes |
|---|---|---|---|
| Linux 802.11n CSI Tool (Halperin) | Intel 5300 | 30 (grouped) | The classic; 2.4/5 GHz, 3×3. |
| Atheros CSI Tool | ath9k (AR9xxx) | 56 (20 MHz) | Finer than Intel; open driver. |
| Nexmon CSI | Broadcom/Cypress bcm43xx (e.g. RPi, Nexus) | up to 256 (80 MHz) | Widest bandwidth on commodity gear; cross-reference `../../projects/nexmon.md`. |
| ESP32 CSI Toolkit | ESP32 | 64 (HT-LTF) | Cheap, self-contained TX+RX pairs; great for building sensor nodes. |

**Rig:**

1. **Geometry.** One TX, one (or several) RX, positioned so the monitored area lies in/around the line-of-sight and dominant reflectors. More spatially separated RX antennas/links → more independent looks → higher ceiling.
2. **Packet injection / traffic.** Force a constant rate so CSI is sampled evenly. A simple flood, e.g.:
   ```bash
   # generate a steady stream for CSI sampling (adjust iface / target)
    sudo ping -i 0.01 192.168.1.1        # ~100 pkt/s
   # or, with the Atheros/Intel tools, use their bundled packet sender
   ```
   Sample **10–100 Hz**. Breathing-based (stationary-crowd) methods need clean sampling around 0.1–0.5 Hz bands, so higher, jitter-free rates help.
3. **Baseline.** Record an **empty-room** segment for calibration/normalization — nearly every method is differential against "empty."
4. **Ground truth.** Log true counts (a clicker, a camera you then delete, or scripted entries/exits) time-synced to the CSI stream.

---

## 4. Features that actually carry the count

Ranked roughly by how commonly they appear:

- **CSI amplitude variance / standard deviation** across subcarriers and over a time window — the workhorse; rises with occupancy and motion.
- **CSI entropy** and **PEM** (percentage of nonzero/above-threshold elements) — dispersion proxies (Electronic Frog Eye).
- **Eigenvalues of the CSI covariance matrix** — the count of "significant" eigen-directions tracks the number of distinct scatterers/paths, which loosely tracks people.
- **KL / EMD divergence** between the current power/CSI distribution and the empty baseline (Mostofi).
- **Doppler / micro-Doppler spectrograms** — motion energy; for stationary crowds, the *respiration* lines.
- **Autocorrelation & temporal-difference features** — used by transfer-friendly methods to strip environment bias.
- **Denoising first:** PCA/low-rank projection, Hampel/median filtering, and CSI-ratio or conjugate-multiplication tricks to kill CFO/PBD phase noise before any of the above.

---

## 5. The accuracy ceiling — and why counting > a few is hard

This is the section that separates honest deployments from demo-ware.

1. **Saturation / diminishing returns.** The channel perturbation is *sub-additive*. Person 1 blocks a strong path and changes the channel a lot; by person 8 the room is already "RF-busy," so the marginal statistic barely moves. Every classic method fits an **S-curve** (Grey Verhulst, log-like) precisely because the feature-vs-count relation flattens. Beyond the knee, distinct counts become statistically indistinguishable.
2. **Occlusion / shadowing.** People stand behind people. RF, like light, is blocked — a person in another's shadow adds almost nothing. Dense crowds hide their own members.
3. **It's an aggregate, not a headcount.** CSI sees *bulk* channel change, not individuals. There is no clean per-person signature to sum; you are regressing a blurry scalar onto an integer.
4. **Motion dependence.** Many methods implicitly need people to *move*. Still occupants (seated, sleeping) collapse the signal toward "empty," which is why stationary-crowd counting is a separate, harder research line relying on faint breathing modulation.
5. **Environment non-transfer.** A model trained in room A fails in room B: different multipath, furniture, link geometry. This is the dominant real-world failure and the reason "trained-once/differential" methods exist. A reported 95% is a *within-environment, within-session* number until proven otherwise.
6. **Confounders.** HVAC, fans, doors, elevators, and even weather perturb CSI on schedules that can correlate with occupancy — a deep net will happily learn the *confounder* instead of the people. (See [`../../docs/sensing-limitations-and-pitfalls.md`](../../docs/honest-limitations-of-wifi-sensing.md).)

**Practical envelope, stated honestly:**

| Regime | Realistic capability |
|---|---|
| Presence (0 vs ≥1) | Robust, high accuracy, transfers reasonably. |
| Low counts (1–~5), moving, trained in place | Good — DeepCount-class ~85–90%. |
| Mid counts (~5–10) | Degrading; per-integer accuracy poor, coarse bins OK. |
| Crowds (tens), queues/gatherings | Only *coarse density/tier* estimates (Frog-Eye-style), not exact heads. |
| Stationary crowd | Special methods, weak signal, lab-grade only. |

The single most important honest move is to **report counts as bins with confidence, not exact integers**, and to **always evaluate cross-session/cross-environment**.

---

## 6. Occupancy sensing in real buildings — and the privacy problem

Occupancy estimation is a **shipping product category**, not just a paper topic. It drives HVAC/lighting setback, desk/room utilization analytics, safety egress, and retail footfall. The Mostofi group even published **"Occupancy Analytics in Retail Stores Using Wireless Signals" (SECON 2019)**. Most *commercial* building-occupancy sensors today use PIR, thermal arrays (e.g. Butlr), depth/ToF, or mmWave radar rather than Wi-Fi CSI — partly because CSI's accuracy ceiling (Section 5) makes exact counts unreliable, and partly for the privacy story below. But the trajectory is clear:

- **IEEE 802.11bf (WLAN Sensing)** is standardizing Wi-Fi sensing — including **presence and people counting** — as a first-class capability of future APs. When that lands, *every* enterprise AP is a potential occupancy sensor with no add-on hardware. This is the moment CSI counting moves from hobby driver to infrastructure.

**Why this is a privacy issue, not a feature bullet:**

- **No opt-in, no device.** Device-free sensing works on people carrying nothing. There is no phone to leave at home, no app to deny permission to. Consent frameworks built around "your device" don't apply.
- **Through walls.** "Crowd Counting Through Walls Using WiFi" is a published result. Occupancy of a *neighboring* space can be inferred.
- **Occupancy is behavior.** Even a coarse count over time reveals presence patterns, schedules, meeting sizes, whether a home is empty — data attractive to advertisers, insurers, landlords, and burglars.
- **Function creep.** The same AP firmware that "counts people for HVAC" is a hair away from activity inference. The count is the thin end.

**Defensive / governance guidance:** see [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md) for the legal and consent framing, and treat any occupancy deployment as **surveillance infrastructure**: disclose it, data-minimize (store bins/aggregates, not raw CSI traces, which can leak far more than counts), retain briefly, and give occupants a real notice. Vendors marketing CSI occupancy should publish what is sensed, at what granularity, and what is *not* possible — a defensive spec, not a capability brochure. The [pitfalls doc](../../docs/honest-limitations-of-wifi-sensing.md) is the antidote to occupancy dashboards that present a saturating, environment-specific estimate as ground truth.

---

## 7. Where this sits on the SDR ladder

Nowhere new. People counting is an **application of CSI (Tier 2)** capability on whatever chip you extracted it from — Intel 5300, ath9k, a Nexmon-patched Broadcom (`../../projects/nexmon.md`), or an ESP32 (`../../chips/espressif.md`). The counting is post-processing; it neither raises nor lowers the die's tier. Cross-reference those chip entries for the actual radio capabilities; this document only adds a *use case* on top of the CSI they already expose.

---

## References

- W. Xi *et al.*, "Electronic Frog Eye: Counting Crowd Using WiFi," IEEE INFOCOM 2014 — https://ieeexplore.ieee.org/document/6848020
- S. Depatla, A. Muralidharan, Y. Mostofi, "Occupancy Estimation Using Only WiFi Power Measurements," IEEE JSAC 33(7), 2015 — https://doi.org/10.1109/JSAC.2015.2430272 (group copy & related work: https://web.ece.ucsb.edu/~ymostofi/publications.html)
- S. Depatla, Y. Mostofi, "Crowd Counting Through Walls Using WiFi," IEEE PerCom 2018 — https://web.ece.ucsb.edu/~ymostofi/publications.html
- B. Korany, Y. Mostofi, "Counting a Stationary Crowd Using Off-the-Shelf WiFi," ACM MobiSys 2021 — https://web.ece.ucsb.edu/~ymostofi/publications.html
- S. Depatla, Y. Mostofi, "Occupancy Analytics in Retail Stores Using Wireless Signals," IEEE SECON 2019 — https://web.ece.ucsb.edu/~ymostofi/publications.html
- S. Liu, Y. Zhao, F. Xue, B. Chen, X. Chen, "DeepCount: Crowd Counting with WiFi via Deep Learning," arXiv:1903.05316, 2019 — https://arxiv.org/abs/1903.05316
- S. Di Domenico, M. De Sanctis, E. Cianca, G. Bianchi, "A Trained-once Crowd Counting Method Using Differential WiFi Channel State Information," 3rd Int'l Workshop on Physical Analytics, 2016 — https://dl.acm.org/doi/10.1145/2935651.2935657
- IEEE 802.11bf WLAN Sensing Task Group — https://www.ieee802.org/11/Reports/tgbf_update.htm
- Linux 802.11n CSI Tool (Halperin, Intel 5300) — https://dhalperi.github.io/linux-80211n-csitool/
- Atheros CSI Tool — https://wands.sg/research/wifi/AtherosCSI/
- Nexmon CSI (Broadcom/Cypress) — https://github.com/seemoo-lab/nexmon_csi
- ESP32 CSI Toolkit — https://stevenmhernandez.github.io/ESP32-CSI-Tool/
- Related in-catalog: [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md), [`../../docs/sensing-limitations-and-pitfalls.md`](../../docs/honest-limitations-of-wifi-sensing.md), [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md), [`wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md)
