# Machine Learning for Wi-Fi CSI Sensing

*Latent Radios — Cycle 5. The model side of Wi-Fi sensing.*

Everywhere else in this catalog we treat a Wi-Fi chip as a **sensor front-end**: firmware patches (Nexmon, the Atheros/Intel CSI tools, ESP32-CSI, PicoScenes) turn a commodity radio into a device that exports **Channel State Information (CSI)** — the per-subcarrier complex channel response `H(f,t)`. This page is about what happens *after* the CSI leaves the NIC: the preprocessing, feature engineering, and neural-network models that turn `H(f,t)` into gestures, activities, identities, vital signs, and localization estimates. For where the CSI comes from and how to capture it, see [`../docs/techniques.md`](../docs/techniques.md) and the CSI toolchains under `../projects/`. For the labelled corpora these models train on, see [`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md).

The core tension of the whole field, and the thread running through this page: **a model that scores 99% on the environment it was trained in typically collapses to near-chance in a new room, on a new person, or at a new orientation.** Most of the interesting engineering — BVP, adversarial domain adaptation, self-supervision, few-shot adaptation — exists to fight that collapse.

---

## 1. What the model actually sees

A CSI capture is a complex tensor `H[n_sub, n_rx, n_tx, t]`:

- **Subcarriers** `n_sub` — 30 (Intel 5300, grouped), 52/56/114/128/242/484/996 (20/40/80/160 MHz OFDM, Atheros/Broadcom/ESP32/AX2xx). More subcarriers = finer frequency-domain resolution of multipath.
- **Antennas** `n_rx × n_tx` — 3×3 on the 5300, up to 4×4 on modern parts. Spatial diversity; the basis for beamforming-projected features (Widar) and angle-of-arrival.
- **Time** `t` — packet index at the injection/probe rate (commonly 100–1000 Hz). Sets the Doppler bandwidth you can observe: motion up to `±rate/2` Hz.

Each entry is complex: **amplitude** `|H|` and **phase** `∠H`. The two carry different information and have very different noise characteristics, which is why they are almost always preprocessed on separate paths.

> **The golden rule of CSI ML:** raw amplitude is usable with light cleaning; **raw phase is garbage** until calibrated. Random phase offsets from CFO, SFO, and PLL desync dwarf the motion-induced phase you want. Nearly every phase failure in the literature traces back to skipping Section 2.2.

---

## 2. Preprocessing: from `H(f,t)` to model input

Preprocessing is where most of the real accuracy is won or lost. A weak model on well-engineered features beats a strong model on raw CSI almost every time.

### 2.1 Amplitude denoising

| Technique | What it removes | Notes |
|---|---|---|
| **Hampel filter** | Impulsive outliers / burst noise | Median-absolute-deviation outlier rejection per subcarrier stream. Standard first step (built into CSIKit). |
| **Low-pass / Butterworth** | High-frequency measurement noise above the motion band | Cutoff set from the physiology: ~2 Hz for breathing, ~20–80 Hz for gestures, higher for fast limbs. |
| **Running-mean / Savitzky–Golay** | Jitter, while preserving edges | Cheap temporal smoothing. |
| **PCA** | Correlated noise across subcarriers; dimensionality | Motion appears in the top few principal components; PC1 often carries the dominant Doppler. The classic "de-noise by dropping PC1 (static) and keeping PC2–PCk" trick from CARM. |
| **DWT (discrete wavelet transform)** | Noise at fine scales; also a multi-resolution feature | Wavelet denoising (soft-thresholding of detail coefficients) preserves transients better than a low-pass. Also used directly as features. |

### 2.2 Phase calibration — the part everyone gets wrong

Measured phase is `∠H_meas = ∠H_true + 2π·k·(δ_SFO)/N + β_CFO + Z`, i.e. a **subcarrier-linear term** (sampling-frequency offset / packet detection delay) plus a **constant term** (carrier-frequency offset, phase-locked-loop) plus noise `Z`. Three families of fixes, in increasing robustness:

1. **Linear transform / phase sanitization** (Sen, IndoTrack): fit a line across subcarrier index `k` and subtract it. Removes the linear SFO term and the constant term, at the cost of also killing any genuinely linear-in-frequency channel structure. Good enough for many amplitude-dominated tasks.
2. **Conjugate multiplication across antennas** (CSI ratio / cross-antenna): the CFO/SFO/PLL terms are **common to all RX chains on the same NIC**. Multiplying the CSI of one antenna by the conjugate of another cancels them, leaving the *relative* channel — the trick behind FarSense's **CSI-ratio** and much respiration sensing. Turns useless phase into a stable, motion-sensitive quantity; the price is you now measure a ratio, not an absolute channel.
3. **Conjugate multiplication across time / reference tap** — subtract a static-path reference to isolate the dynamic (moving-body) reflection before computing Doppler.

Complex-valued networks (Section 3) can sometimes *learn* a calibration internally, but feeding them uncalibrated phase still hurts; calibrate first.

### 2.3 Time–frequency and Doppler features

Raw CSI is a poor model input for motion because the *dynamics* are what matter. Standard engineered representations:

- **Spectrogram / STFT per stream** — short-time Fourier transform of a denoised CSI stream gives a time × frequency image. Feed straight into a 2-D CNN. Simple, strong baseline.
- **Doppler Frequency Shift (DFS) profile** — the CARM/Widar lineage: after removing the static component, the residual Doppler spectrum over time is a direct readout of radial velocity of body parts. Time × Doppler image.
- **Spectrogram + PCA** to pick the most informative stream before imaging.
- **BVP — Body-coordinate Velocity Profile** (Widar3, see Section 4): the flagship *domain-independent* feature; a 20×20×T tensor of velocity components in a body-fixed frame, reconstructed by solving a constrained optimization that fuses DFS from **multiple links/receivers** and geometrically projects out the sensor's position and the user's orientation.

### 2.4 What shape does the network get?

Common input tensors, and the model family they invite:

- `[T, subcarriers]` amplitude image → **CNN** or **CNN+RNN**.
- `[T, freq]` spectrogram / DFS image → **2-D CNN** (ResNet, etc.).
- `[T, feature]` sequence → **LSTM/GRU/Transformer**.
- `[20, 20, T]` BVP → **CNN encoder + GRU** over time (Widar3's own model), or a 3-D CNN.
- Complex `[T, subcarriers]` with real+imag channels → **complex-valued net** or a 2-channel real CNN.

---

## 3. Model families

| Family | Strength | Weakness | Representative use |
|---|---|---|---|
| **MLP** | Trivial baseline, fast | Ignores structure; overfits | SenseFi baseline |
| **2-D CNN** (LeNet, ResNet-18/50, VGG) | Spatial locality on spectrogram/CSI images; transfer from ImageNet backbones | No explicit long-range temporal memory | Activity/gesture from spectrograms; SenseFi's strongest supervised baselines are ResNets |
| **1-D CNN / TCN** | Cheap temporal convolutions, good on-device | Fixed receptive field | Edge HAR, respiration |
| **RNN / LSTM / GRU / BiLSTM** | Explicit temporal dynamics of a gesture | Slow to train, vanishing gradients on long windows | Sequential gestures, gait |
| **CNN-LSTM / CNN-GRU (hybrid)** | CNN extracts per-frame spatial features, RNN models their evolution — the workhorse architecture | Two-stage tuning | Widar3 (CNN+GRU over BVP); most gesture pipelines |
| **Transformer / ViT / self-attention** | Long-range dependencies, parallel training, attention over subcarriers *and* time | Data-hungry; needs augmentation or pretraining to beat CNNs on small CSI sets | THAT (two-stream conv-transformer for HAR), ViT in SenseFi |
| **Complex-valued networks** | Operate on `H` natively, preserving amplitude–phase coupling instead of discarding phase | Immature tooling, harder optimization | SLNet (complex-valued spectrogram learning); phase-aware respiration/localization |
| **GNNs** | Model antenna/link topology or body-joint graphs | Niche, heavier | Multi-link fusion, pose |

**Practical read:** for a fixed, in-domain dataset a well-tuned **ResNet on a spectrogram** or a **CNN-GRU on BVP** is the default. Transformers win when you have scale (pretraining, big multi-environment corpora, augmentation). Complex-valued nets are the research frontier for squeezing information out of phase.

---

## 4. The domain-generalization problem

This is the defining problem of Wi-Fi sensing. A "domain" is a nuisance factor the label should not depend on but the CSI does: **environment/room, receiver placement, user identity, body orientation, and torso position.** Models latch onto these because they are enormously predictive *within* a dataset. Three broad strategies:

### 4.1 Engineer the domain out of the feature — Widar3 / BVP

Widar3 ("Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi", ACM MobiSys 2019; Tsinghua, Intel 5300, 3×3) attacks the problem *before* the model. Instead of learning to ignore orientation/position, it computes a feature that geometrically **cannot** encode them:

- From each Tx–Rx link, estimate the **Doppler Frequency Shift** spectrum (radial velocity of the moving hand toward that link).
- Fuse the DFS from **multiple spatially diverse links** and solve a constrained least-squares assignment that maps the observed radial velocities into a **body-coordinate velocity profile (BVP)** — a `20×20×T` tensor of velocity components on the x/y axes of a frame fixed to the *user's body*, not the sensors.
- Because the projection uses the known link geometry and the estimated torso location/orientation, the resulting BVP of a gesture is (ideally) identical no matter where you stand or which way you face.

A modest **CNN + GRU** on BVP then generalizes "zero-effort" across positions and orientations. The cost: BVP needs **several synchronized receivers** and non-trivial computation; the domain factor it removes best is *orientation/position*, less so a totally new room's multipath. Widar3's public dataset (multi-user, multi-room, multi-orientation, with raw CSI, DFS, and precomputed BVP) is a standard cross-domain benchmark — see [`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md).

### 4.2 Learn to be domain-invariant — adversarial domain adaptation (EI and successors)

The learning-based alternative: let the network see the domain, and *penalize* it for encoding it.

**EI** ("Towards Environment Independent Device Free Human Activity Recognition", MobiCom 2018) is the canonical example. It uses an **adversarial / gradient-reversal** setup plus unsupervised losses:

- A **feature extractor** produces an embedding.
- An **activity classifier** is trained to predict the label (minimize activity loss).
- A **domain discriminator** tries to predict which environment/person the sample came from; a **gradient-reversal layer** flips its gradient so the feature extractor is pushed to make domains *indistinguishable*.
- Auxiliary **confidence-control** and **smoothing** constraints stabilize the unlabeled target domain.

The result is an embedding that keeps activity information while discarding environment/subject information — reducing the labelled data needed in each new environment. This DANN-style recipe (feature extractor + label head + adversarial domain head) is now the template for dozens of follow-ups; variants swap in **MMD / CORAL** distribution-alignment losses, **conditional** adversaries, or **metric-learning** objectives.

### 4.3 Signal-level and data-level defenses

- **Static/background removal** (subtract the static-path CSI, keep only the dynamic reflection) removes the most environment-specific component cheaply.
- **Data augmentation** — time warping, subcarrier dropout, adding synthetic multipath, mixing — is the pragmatic, always-worth-it baseline for robustness.
- **Physics-based synthesis** — render CSI from a motion/mesh model to cover unseen orientations, then train on the union.

> **Honest caveat.** No method fully solves cross-*environment* generalization. BVP handles orientation/position best; adversarial adaptation needs some (even unlabeled) target data; both degrade in a genuinely novel room with different multipath. Report cross-domain splits (leave-one-room-out, leave-one-user-out) or the number is not meaningful.

---

## 5. Self-supervised, contrastive, and few-shot learning

Labels are expensive and don't transfer, so learning without (many) labels is a major theme.

- **Self-supervised pretraining.** Train an encoder on *unlabeled* CSI with a pretext task, then fine-tune a small head on scarce labels. **AutoFi** (geometric self-supervised, from the SenseFi authors) and masked/autoencoder reconstruction on CSI images are representative. SenseFi explicitly benchmarks the "adaptability of unsupervised learning."
- **Contrastive learning (SimCLR/MoCo-style).** Treat augmentations of the same CSI window as positives; pull them together, push others apart. Augmentation choice (subcarrier masking, time crop, jitter) *is* the design. Good for building environment-robust embeddings without labels.
- **Few-shot / meta-learning.** Recognize a new gesture or adapt to a new user from a handful of examples. **RF-Net** (a matching/metric-learning few-shot RF sensing model with a dual-path CNN + attention and an RNN over a per-class prototype) is the reference; **prototypical networks** and **MAML**-style meta-learning are common. This is the practical answer to "I have one enrolment sample per new user."
- **Domain-generalization meta-learning.** Episodic training that simulates domain shift during training (each episode = a held-out domain) so the model learns to adapt fast at test time.

---

## 6. Public toolkits and benchmarks

| Toolkit | What it is | Link |
|---|---|---|
| **SenseFi** (`xyanchen/WiFi-CSI-Sensing-Benchmark`) | The reference **benchmark + PyTorch library** for DL WiFi sensing. Ships MLP, LeNet, ResNet-18/50/101, RNN, GRU, LSTM, BiLSTM, CNN+GRU, ViT, and self-supervised training. Bundles four datasets (UT-HAR, NTU-Fi HAR, NTU-Fi HumanID, Widar-BVP). Paper: Yang et al., *SenseFi: A Library and Benchmark on Deep-Learning-Empowered WiFi Human Sensing*, **Patterns (Cell Press) 2023**. | https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark |
| **CSIKit** (`Gi-z/CSIKit`) | The **parsing + feature** front-end. Reads Atheros, Intel 5300/AX200/AX210 (incl. FeitCSI), Broadcom BCM4339/4358/43455c0/4366c0 (Nexmon), ESP32, and PicoScenes/USRP. Extracts CSI amplitude (dB), RSSI, phase; Hampel/low-pass/running-mean filtering; heatmap visualization. Feeds TensorFlow/PyTorch — it prepares data, it is not itself a classifier. | https://github.com/Gi-z/CSIKit |
| **Widar3 release** | Raw CSI + DFS + precomputed **BVP** and the CNN-GRU reference model. The standard cross-domain gesture benchmark. | http://tns.thss.tsinghua.edu.cn/widar3.0/ |
| **PicoScenes** | Capture platform; also a common data source into the ML pipeline (see `../projects/picoscenes.md`). | — |

**SenseFi dataset shapes** (useful when wiring a model input): UT-HAR `1×250×90`, 7 classes; NTU-Fi HAR `3×114×500`, 6 classes; NTU-Fi HumanID `3×114×500`, 14 classes; Widar `22×20×20` (BVP), 22 gestures.

---

## 7. Task → typical model → dataset

| Task | Typical feature | Typical model | Common dataset(s) |
|---|---|---|---|
| Coarse activity recognition (HAR) | Denoised amplitude / spectrogram | ResNet-18, CNN-LSTM | UT-HAR, NTU-Fi HAR, SignFi-env |
| Gesture recognition (in-domain) | Spectrogram / DFS | CNN-GRU, ViT | SignFi, Widar (in-domain) |
| **Cross-domain** gesture | **BVP** | CNN + GRU (Widar3) | **Widar3** |
| Sign / fine hand gesture | Amplitude+phase image | Deep CNN (9-layer) | SignFi |
| Person identification / gait | Amplitude sequence | ResNet / BiLSTM | NTU-Fi HumanID, WiWho-style gait sets |
| Fall detection | Spectrogram + threshold/attention | CNN, CNN-LSTM | FallDeFi-style, custom |
| Respiration / heart rate | **CSI-ratio** phase, FFT peak | Peak-tracking + light CNN/regression | FarSense-style, custom vitals |
| Localization / tracking | Sanitized phase, AoA/ToF | CNN regressor / hybrid model-based | IndoTrack/Widar-loc-style |
| Pose / skeleton estimation | Multi-antenna amplitude+phase | CNN encoder–decoder (WiFi→keypoints) | Person-in-WiFi / WiPose-style |
| Few-shot new user/gesture | Learned embedding | RF-Net / prototypical net | Widar, custom enrolment sets |
| Self-supervised pretrain → HAR | Augmented CSI pairs | Contrastive / AutoFi encoder | Unlabeled CSI + small labelled head |

---

## 8. A default recipe (and the pitfalls)

**Recipe.** (1) Parse with CSIKit. (2) Hampel + low-pass on amplitude; **CSI-ratio or linear-fit** calibration on phase. (3) Static-path removal, then STFT/DFS → time-frequency image (or reconstruct BVP if you have multiple receivers and want cross-domain). (4) Train a ResNet or CNN-GRU with heavy augmentation. (5) Evaluate with **leave-one-domain-out** splits. (6) If cross-domain is weak, add adversarial domain-invariance (EI-style) or self-supervised pretraining; if labels are scarce in new domains, add few-shot adaptation (RF-Net/prototypical).

**Pitfalls that quietly inflate accuracy:**

- **Random train/test split instead of by-domain split.** The single most common way papers report 99% that doesn't hold up. Split by room/user/orientation.
- **Feeding uncalibrated phase.** Section 2.2. It "works" on the training set because the offsets are constant within a capture session, then fails.
- **Leakage through continuous windows.** Overlapping sliding windows put near-identical frames in both train and test. De-correlate splits at the *session* level.
- **Ignoring the hardware.** Number of subcarriers, antenna count, and packet rate set the ceiling on spatial and Doppler resolution; a model tuned on 3×3 Intel-5300 30-subcarrier data will not transfer unchanged to 4×4 AX210 484-subcarrier data. Retrain and re-tune input shapes.
- **Class-balanced test, deployment-imbalanced reality** (falls, intrusions are rare) — report precision/recall, not just accuracy.

---

## References

- J. Yang, X. Chen, D. Wang, H. Zou, C. X. Lu, S. Sun, L. Xie. *SenseFi: A Library and Benchmark on Deep-Learning-Empowered WiFi Human Sensing.* Patterns (Cell Press), 2023. Code: https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark — Paper: https://arxiv.org/abs/2207.07859
- Y. Zheng, Y. Zhang, K. Qian, G. Zhang, Y. Liu, C. Wu, Z. Yang. *Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi (Widar3.0).* ACM MobiSys 2019. Dataset: http://tns.thss.tsinghua.edu.cn/widar3.0/
- W. Jiang, C. Miao, F. Ma, S. Yao, et al. *Towards Environment Independent Device Free Human Activity Recognition (EI).* ACM MobiCom 2018. https://dl.acm.org/doi/10.1145/3241539.3241548
- G. Forbes (Gi-z). *CSIKit: Python CSI processing and visualisation tools.* https://github.com/Gi-z/CSIKit
- W. Wang, A. X. Liu, M. Shahzad, K. Ling, S. Lu. *Understanding and Modeling of WiFi Signal-Based Human Activity Recognition (CARM).* ACM MobiCom 2015. (DFS/PCA feature lineage.)
- J. Zheng et al. *FarSense: Pushing the Range Limit of WiFi-based Respiration Sensing with CSI Ratio.* IMWUT 2019. (CSI-ratio phase calibration.)
- S. Zheng, J. Yang, et al. *RF-Net: A Unified Meta-Learning Framework for RF-Enabled One-Shot Human Activity Recognition.* ACM SenSys 2020. (Few-shot.)
- J. Yang, X. Chen, H. Zou, D. Wang, L. Xie. *AutoFi: Towards Automatic WiFi Human Sensing via Geometric Self-Supervised Learning.* IEEE IoT-J 2023. (Self-supervised.)
- Y. Ma, G. Zhou, S. Wang. *WiFi Sensing with Channel State Information: A Survey.* ACM Computing Surveys 2019. (Preprocessing/DWT/PCA background.)

*Sibling pages: capture and physics in [`../docs/techniques.md`](../docs/techniques.md); datasets in [`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md); CSI extraction toolchains under `../projects/`.*
