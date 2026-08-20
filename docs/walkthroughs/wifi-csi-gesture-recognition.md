# Gesture recognition with Wi-Fi CSI

A practical companion to the whole-body HAR pipeline in
[`./wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md).
Same physical trick, finer motion: where HAR classifies "walk / fall / sit" from
seconds of coarse torso movement, **gesture recognition** asks a Wi-Fi radio to tell a
swipe from a push, a "circle" from a "zigzag", or one sign-language word from 275 others —
motions that are smaller, faster, and much closer to the noise floor.

Nothing here transmits anything a normal Wi-Fi card doesn't. CSI is estimated from packets
you **receive** (or send to *yourself* to keep a steady probe rate), so there is no new
spectrum-emission beyond ordinary Wi-Fi. The privacy and safety notes at the bottom still
apply — sensing hand motion through walls is exactly the capability people worry about.

**Read alongside**
- [`./wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md) — the end-to-end capture→clean→window→model→eval skeleton this page specializes.
- [`../ml-csi-sensing.md`](../ml-csi-sensing.md) — the model/feature/domain-generalization theory in depth (BVP, DFS, adversarial adaptation).
- [`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md) — capturing CSI on a Raspberry Pi (the live path).
- [`./esp32-csi-breathing-monitor.md`](./esp32-csi-breathing-monitor.md) — the ESP32-CSI capture path, reused here for gestures.
- [`../verification-tier2-csi.md`](../verification-tier2-csi.md) — which chips actually export CSI (the Tier-2 rung of the SDR ladder).
- [`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md) — download links/formats for Widar3, SignFi, WiGest.

---

## 1. Why a hand shows up in the channel

A moving hand is a moving reflector. Each Tx→Rx path that bounces off it has a
time-varying length, so the complex channel `H(f,t)` on every subcarrier picks up:

- **Amplitude modulation** — constructive/destructive interference as the reflected path
  slides in and out of phase with the static (line-of-sight + furniture) paths. This is
  what coarse, RSSI-only systems see.
- **Phase modulation** — the reflected path's phase rotates at `2π·(dℓ/dt)/λ`. After the
  usual CFO/SFO calibration (see [`../ml-csi-sensing.md`](../ml-csi-sensing.md) §2.2), the
  residual phase is a clean readout of path-length change.
- **Doppler** — the time-derivative of that phase *is* a frequency shift proportional to
  the hand's **radial velocity** toward that link: `f_D = (2·v_radial)/λ` for a
  reflected path (`λ ≈ 12.5 cm` at 2.4 GHz, `≈ 5.5 cm` at 5.5 GHz). A hand moving at
  0.5 m/s produces roughly ±8 Hz at 2.4 GHz, ±18 Hz at 5 GHz. **Doppler is the single
  most informative gesture feature**, which is why everything below eventually turns CSI
  into a time–Doppler picture.

Two consequences set the whole design:

1. **You need packets fast enough to see the Doppler.** By Nyquist, a probe/inject rate
   of `R` Hz observes motion up to `±R/2` Hz. Gestures want **≥ 200 Hz, 500–1000 Hz is
   comfortable** — far above the ~100 Hz that suffices for HAR, and *far* above a bare
   beacon rate. You get this by flooding ICMP/UDP from the transmitter to the receiver.
2. **Radial velocity is geometry-dependent.** The *same* gesture produces *different*
   Doppler at each receiver depending on where the receiver sits. That is a curse (it
   makes single-link models environment-specific) and, via multi-link fusion, the cure
   (Widar's BVP, §5).

---

## 2. Three classic systems, and exactly what each measured

These are the papers to cite; they also mark the three tiers of sophistication you can aim
for.

| System | Signal used | Hardware | Gestures | Reported accuracy | The idea it introduced |
|---|---|---|---|---|---|
| **WiGest** (Abdelnasser et al., INFOCOM 2015) | **RSSI only** (not CSI) | Commodity laptop + off-the-shelf AP(s) | 7 motion **primitives** (rising/falling/pause edges) → composite gestures | 87.5% single-AP, up to **96% with 3 APs** | Coarse in-air hand gestures are detectable from raw signal-strength envelopes on unmodified hardware. The honest baseline: no CSI, no Doppler, device-proximal, few classes. |
| **Widar3.0** (Zheng et al., MobiSys 2019; Zhang et al., TPAMI 2021) | CSI → DFS → **BVP** | Intel 5300, 1 Tx + **6 Rx**, 3×3 | 22 gesture types (6-gesture subset is the common benchmark) | ~92% in-domain; **cross-domain 82–92%** "zero-effort" | Compute a **domain-independent** feature (body-coordinate velocity profile) so a model trained in one room/orientation works in another *without* retraining. |
| **SignFi** (Ma et al., IMWUT/UbiComp 2018) | Calibrated CSI amplitude **+ phase** | Intel 5300 (Linux 802.11n CSI Tool), 1 Tx + 3 Rx | **276 sign-language words** | ~98% single-user in-lab; **94.8%** on the 5-user / 150-sign mix; drops across lab↔home | A 9-layer CNN on `200×30×3` complex CSI can separate hundreds of fine hand/arm signs — the high-class-count extreme. |

Takeaways for your own build:

- **WiGest is the reality check.** It proves gestures are visible even in RSSI, but with
  few classes and near a device. If you only have RSSI, aim for WiGest-scale ambition.
- **SignFi is the "just throw CSI at a CNN" archetype** — high accuracy *in one domain*,
  and it degrades exactly where §6 predicts (new environment, new user).
- **Widar3 is the one that takes cross-domain seriously**, at the cost of needing several
  synchronized receivers. Its released dataset ships **raw CSI, DFS, and precomputed BVP**,
  making it the standard cross-domain gesture benchmark.

---

## 3. Capture: getting gesture-grade CSI

Both capture paths from the sibling walkthroughs work; the *only* thing you must change for
gestures is **push the packet rate up** so the Doppler band isn't aliased.

### 3a. nexmon_csi on a Raspberry Pi (BCM43455c0)

Configure the collector as in [`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md),
then flood from the transmitter so CSI frames arrive fast:

```bash
# RX (Pi): collect CSI for one TX MAC on ch 36 / 80 MHz
makecsiparams -c 36/80 -C 1 -N 1 -m AA:BB:CC:DD:EE:FF -b 0x88
nexutil -Ieth0 -s500 -b -l34 -v<base64-from-makecsiparams>
ip link set up dev wlan0
tcpdump -i wlan0 dst port 5500 -w gesture_$(date +%s).pcap

# TX (any host, wired or associated): force a high, steady CSI rate.
# 1000 pkt/s -> observe Doppler up to +/-500 Hz, plenty for a hand.
sudo ping -i 0.001 -s 20 <RX-ip>        # ~1 kHz; use iperf3 -u -b for jitter-free
```

The BCM43455c0 has a **single spatial stream**, so a Pi capture is `1 × T × ~234`
subcarriers per window — enough for a single-link Doppler spectrogram (§4), **not** enough
on its own for Widar-style BVP, which needs spatially diverse links.

### 3b. ESP32-CSI (cheapest, fully in your control)

The ESP-IEEE 802.11 CSI callback ([`./esp32-csi-breathing-monitor.md`](./esp32-csi-breathing-monitor.md))
gives 64 (HT20) subcarriers per received frame. Run the RX in station mode and let the AP
(or a second ESP32) ping-flood it. Two ESP32 boards + a phone hotspot is a <$15 gesture rig.
Its ceiling is low resolution (single stream, 20 MHz), so target WiGest/SignFi-lite class
counts, not 276-way sign language.

### 3c. Labeling — the part that decides your accuracy

Gestures are *discrete events*, so segment them cleanly:

```python
import numpy as np

def segment_by_motion(amp, fs, min_gap_s=0.4, thresh_k=3.0):
    """Split a continuous stream into gesture events by motion energy.
    amp: (T, S) cleaned amplitude. Returns list of (start, end) frame indices."""
    energy = np.var(np.diff(amp, axis=0), axis=1)          # per-frame motion energy
    active = energy > (energy.mean() + thresh_k*energy.std()*0.0 + np.median(energy)*2)
    idx = np.where(active)[0]
    if len(idx) == 0: return []
    gaps = np.where(np.diff(idx) > int(min_gap_s*fs))[0]
    groups = np.split(idx, gaps+1)
    return [(g[0], g[-1]) for g in groups if len(g) > int(0.2*fs)]
```

Better still: **script the session** — display a prompt ("draw O … now"), fix a per-gesture
window (e.g. 1.0–1.5 s), and log the trigger timestamp to a sidecar CSV. Event-triggered
labels beat energy segmentation every time. Balance classes and vary start pose slightly so
the model can't cheat on a resting-hand artifact.

---

## 4. Feature: the Doppler spectrogram (single-link)

This is the workhorse gesture feature and runs on **one** receiver. Pipeline per gesture
window: clean → remove the static path → STFT → time×Doppler image → CNN.

```python
import numpy as np
from scipy.signal import butter, filtfilt, stft

def doppler_spectrogram(csi, fs, fmax=60.0, nperseg=128, overlap=0.9):
    """csi: (T, S) complex CSI for ONE gesture window on ONE link.
    Returns a (freq, time) magnitude spectrogram of hand Doppler."""
    # 1. Pick the most motion-informative subcarrier stream via PCA (CARM trick):
    #    subtract the static/mean channel, then take the top principal component.
    x = csi - csi.mean(axis=0, keepdims=True)          # remove static path (complex)
    # complex PCA: eigenvector of the S x S covariance, largest eigenvalue
    C = (x.conj().T @ x)
    w, V = np.linalg.eigh(C)
    stream = x @ V[:, -1]                                # (T,) dominant complex stream

    # 2. Band-limit to plausible hand Doppler before STFT (kills residual noise)
    b, a = butter(4, fmax/(fs/2), btype="low")
    stream = filtfilt(b, a, stream.real) + 1j*filtfilt(b, a, stream.imag)

    # 3. Short-time FT of the COMPLEX stream -> signed Doppler (approach vs. recede)
    f, t, Z = stft(stream, fs=fs, nperseg=nperseg,
                   noverlap=int(nperseg*overlap), return_onesided=False)
    order = np.argsort(f)                                # -f .. +f
    S = np.abs(Z[order])
    keep = np.abs(f[order]) <= fmax
    return f[order][keep], t, S[keep]                   # (F,), (Tn,), (F, Tn)
```

Why each step matters:

- **Complex STFT, not `|H|` STFT.** Taking the FFT of the complex stream keeps the *sign*
  of the Doppler — a hand moving toward the link (+f) vs. away (−f) look different, and
  that asymmetry separates otherwise-similar gestures (push vs. pull, left-swipe vs.
  right-swipe). A magnitude-only spectrogram throws half of it away.
- **Static-path removal** before the STFT deletes the dominant DC line so the AGC and room
  reflections don't drown the motion.
- **PCA stream selection** (the CARM idea, [`../ml-csi-sensing.md`](../ml-csi-sensing.md) §2)
  collapses 234 subcarriers to the one linear combination carrying the most Doppler energy —
  cheaper and less noisy than imaging every subcarrier.

Feed the resulting `(F, Tn)` image straight into the same tiny 2-D CNN as the HAR page
([`./wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md) §4),
resized/padded to a fixed shape. On a well-collected single-room set this alone hits the
high-90s in-domain — and collapses cross-domain (§6).

---

## 5. Feature: Body-coordinate Velocity Profile (BVP) — the Widar idea

The spectrogram of §4 is **link-relative**: the same gesture at a different orientation
projects onto the link differently, so the picture changes. Widar3's insight is to fuse
several links into an orientation/position-independent representation.

The construction, conceptually (full math in
[`../ml-csi-sensing.md`](../ml-csi-sensing.md) §4.1):

1. From each of the *M* Tx–Rx links, estimate the **Doppler Frequency Shift (DFS)** profile
   over the gesture — the distribution of radial velocities that link sees.
2. Discretize a body-fixed 2-D velocity plane into a `20×20` grid `V` (x/y velocity
   components in the *user's* frame, not any sensor's).
3. Each grid velocity `v` projects onto link *i* as a known radial component
   `f_i(v) = (2/λ)·⟨v, direction_i⟩`, given the link geometry and the estimated torso
   location/orientation. Stack these into an assignment matrix `A_i`.
4. Solve, per time slice, a **sparse non-negative least squares** for the velocity
   distribution `P(v)` whose projection matches every link's measured DFS:
   `min_P Σ_i ‖ A_i·P − DFS_i ‖ + η‖P‖₁,  P ≥ 0`. Sparsity (EMD/L1) picks the physically
   simplest velocity field.
5. Stack the per-slice `20×20` profiles over time → a `20×20×T` **BVP** tensor.

```python
# Schematic BVP solve for one time slice (Widar-style). Real code: the Widar3 release.
import numpy as np
from scipy.optimize import nnls

def bvp_slice(dfs, A_list):
    """dfs: list of (Fbins,) measured Doppler profiles, one per link.
    A_list: list of (Fbins, 400) projection matrices mapping a 20x20=400 velocity
            grid to each link's Doppler bins (built from link geometry + torso pose).
    Returns a 20x20 velocity profile."""
    A = np.vstack(A_list)                 # (M*Fbins, 400)
    b = np.concatenate(dfs)               # (M*Fbins,)
    p, _ = nnls(A, b)                     # non-negative velocity distribution
    return p.reshape(20, 20)
```

Because steps 3–4 divide out the sensor geometry and the user's facing direction, a
gesture's BVP is (ideally) **the same regardless of where you stand or which way you face**.
Widar3 then trains a modest **CNN + GRU** over the `20×20×T` BVP and generalizes
"zero-effort" across positions and orientations.

The honest cost, and where it stops helping:
- **You need several spatially diverse, time-synchronized receivers** (Widar used six).
  A single Pi or ESP32 cannot produce a real BVP — plan §4 for one-link rigs.
- BVP removes **orientation/position** dependence well; it removes a **brand-new room's
  multipath** far less. Cross-*environment* is still the hard axis (§6).
- The projection needs a torso-location/orientation estimate; errors there smear the BVP.

Widar3's dataset ships raw CSI **and** DFS **and** precomputed BVP, so you can benchmark a
BVP model without implementing steps 1–4 yourself — see
[`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md).

---

## 6. A minimal classifier, and the number that tells the truth

Reuse the training loop from
[`./wifi-csi-human-activity-recognition.md`](./wifi-csi-human-activity-recognition.md) §4
verbatim — a 2-D CNN over the §4 spectrogram (or the §5 BVP), CrossEntropy, Adam. The only
gesture-specific choices are: fixed per-gesture window instead of sliding, and a class head
sized to your gesture count.

```python
import torch, torch.nn as nn

class GestureCNN(nn.Module):
    """Doppler spectrogram (1, F, T) -> gesture logits. ~0.3M params, trains on CPU."""
    def __init__(self, n_cls=6):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((4, 4)))
        self.c = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(32*4*4, n_cls))
    def forward(self, x): return self.c(self.f(x))
```

For BVP, swap in a CNN-per-frame + GRU-over-time (the Widar3 architecture; see the model
table in [`../ml-csi-sensing.md`](../ml-csi-sensing.md) §3).

### The cross-domain problem — read this before you demo

This is the same accuracy cliff HAR faces, and gestures fall harder because the signal is
smaller. **In-domain 95%+ routinely collapses to near-chance in a new room / on a new user /
at a new orientation.** A single-link spectrogram model is especially fragile — it can learn
the room's multipath rather than the motion.

Evaluate with **leave-one-domain-out**, never a random split, and report the *average* over
held-out domains:

```python
def loo_domain_split(samples, labels, domains, held_out):
    tr = [(x, y) for x, y, d in zip(samples, labels, domains) if d != held_out]
    te = [(x, y) for x, y, d in zip(samples, labels, domains) if d == held_out]
    return tr, te
# Run once per held-out user (and per room, per orientation); publish the MEAN, not the best.
```

What actually moves the cross-domain number, cheapest first:
- **Static-path removal + signed Doppler** (§4) already discards the most room-specific part.
- **Data augmentation** — time-warp the gesture, drop random subcarriers, add synthetic
  multipath, jitter the start pose. Always worth it.
- **A domain-invariant feature (BVP, §5)** for orientation/position — if you can afford the
  receivers.
- **Adversarial domain adaptation** (DANN / gradient reversal, the EI recipe) or **few-shot
  fine-tuning** on a handful of target-domain gestures.
- **More diverse training data** beats every clever loss — collect across rooms, users,
  orientations. This is the finding the whole field keeps rediscovering.

Publish **in-domain AND cross-domain accuracy side by side**, plus a confusion matrix
(swipe-left vs. swipe-right and push vs. pull are the classic confusions a magnitude-only
spectrogram cannot fix — another reason to keep the Doppler sign in §4).

---

## 7. Reproducibility & ethics checklist

- [ ] State the **probe/inject rate** (Hz) — it sets your Doppler bandwidth; too low aliases the gesture.
- [ ] Report bandwidth, subcarrier count, receiver count, and whether features are single-link spectrogram or multi-link BVP.
- [ ] Segmentation method (event-triggered vs. energy) and per-gesture window length.
- [ ] **Leave-one-domain-out** protocol; publish in-domain **and** cross-domain, averaged over folds.
- [ ] Normalization fit on train only; fixed seeds; confusion matrix, not just top-1.
- [ ] **Consent and containment.** Hand/arm sensing through walls is privacy-sensitive; capture only in spaces you control, with informed consent. See [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md). The high packet-flood rate is ordinary Wi-Fi traffic on your own channel — no arbitrary-waveform TX, no new emission risk — but keep it on a channel and network you're authorized to use.

---

## References

- **WiGest** — H. Abdelnasser, M. Youssef, K. A. Harras, "WiGest: A Ubiquitous WiFi-based Gesture Recognition System," *IEEE INFOCOM* 2015: <https://ieeexplore.ieee.org/document/7218525> · arXiv: <https://arxiv.org/abs/1501.04301>
- **Widar3.0** — Y. Zheng et al., "Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi," *ACM MobiSys* 2019: <https://dl.acm.org/doi/10.1145/3307334.3326081> · Project/dataset: <http://tns.thss.tsinghua.edu.cn/widar3.0/> · Extended: Y. Zhang et al., "Widar3.0: Zero-Effort Cross-Domain Gesture Recognition With Wi-Fi," *IEEE TPAMI* 2021: <https://ieeexplore.ieee.org/document/9516988>
- **SignFi** — Y. Ma, G. Zhou, S. Wang, H. Zhao, W. Jung, "SignFi: Sign Language Recognition Using WiFi," *Proc. ACM IMWUT* (UbiComp) 2018: <https://dl.acm.org/doi/10.1145/3191755> · Code & data: <https://github.com/yongsen/SignFi>
- **CARM** (CSI-speed model / Doppler lineage) — W. Wang, A. X. Liu, M. Shahzad, K. Ling, S. Lu, "Understanding and Modeling of WiFi Signal Based Human Activity Recognition," *ACM MobiCom* 2015: <https://dl.acm.org/doi/10.1145/2789168.2790093>
- **EI** (adversarial domain-independent HAR) — W. Jiang et al., "Towards Environment Independent Device Free Human Activity Recognition," *ACM MobiCom* 2018: <https://dl.acm.org/doi/10.1145/3241539.3241548>
- **SenseFi** benchmark/library — J. Yang et al., *Patterns* 2023: <https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark> · <https://arxiv.org/abs/2207.07859>
- **CSIKit** parsing/cleaning — G. Forbes: <https://github.com/Gi-z/CSIKit>
- **nexmon_csi** — Schulz, Wegemer, Hollick (SEEMOO Lab): <https://github.com/seemoo-lab/nexmon_csi>
- Sibling pages: [HAR pipeline](./wifi-csi-human-activity-recognition.md) · [ML for CSI sensing](../ml-csi-sensing.md) · [nexmon CSI capture](./nexmon-csi-to-usable-csi.md) · [ESP32 CSI](./esp32-csi-breathing-monitor.md)
