# Public Wi-Fi Sensing / CSI Datasets & Reproducibility

*A curated index of open Channel-State-Information (CSI) datasets, the exact
hardware and tool that captured each one, and how to load them — so you can
reproduce a Wi-Fi-sensing paper today without owning a single NIC.*

Every dataset in this catalog is downstream of one of a small number of CSI
extraction tools. Before trusting a dataset's numbers (subcarrier count, phase
sanitization, timestamp jitter) you need to know **which tool produced it**,
because the tool defines the format, the calibration quirks, and the ceiling on
what the raw data can tell you. That lineage is documented in
[csi-toolchains.md](csi-toolchains.md); this file is the *data* companion to it.

---

## 1. Why start with datasets instead of hardware

The classic Wi-Fi-sensing rigs — an **Intel 5300** running the Linux 802.11n
CSI Tool, or an **Atheros AR9xxx** running the Atheros CSI Tool — are getting
hard to source and require a patched kernel from ~2011-2016. The good news is
that the field is unusually generous with public data: most landmark papers
ship their raw `.mat`/`.dat`/`.csv` traces. You can validate a model, benchmark
a new architecture, or learn the CSI format end-to-end before spending a cent on
silicon. When you *do* buy hardware, the dataset you trained on tells you
exactly which chip + tool to match so your captures are format-compatible.

The tool lineage that matters:

| Tool | Chip family | Format / rate | Catalog page |
|------|-------------|---------------|--------------|
| Linux 802.11n CSI Tool (Halperin) | Intel 5300 | 30 subcarriers × up to 3×3 streams, `.dat` | [intel.md](../chips/intel.md), [intel-5300-csi.md](../docs/walkthroughs/intel-5300-csi.md) |
| Atheros CSI Tool (Xie) | Atheros AR9380/9580 etc. | up to 56 (20 MHz) / 114 (40 MHz) subcarriers | [qualcomm-atheros.md](../chips/qualcomm-atheros.md), [atheros-ath9k-spectral-csi.md](../docs/walkthroughs/atheros-ath9k-spectral-csi.md) |
| Nexmon CSI (SEEMOO) | Broadcom/Cypress BCM43455c0, BCM4339, BCM4358, BCM4366c0 | 64/128/256 subcarriers (20/40/80 MHz), UDP | [nexmon.md](nexmon.md), [broadcom-cypress.md](../chips/broadcom-cypress.md) |
| ESP32-CSI-Tool (Hernandez) | Espressif ESP32 | ≤64 subcarriers (HT20; 52 usable), CSV | [espressif.md](../chips/espressif.md) |
| PicoScenes (Jiang) | Intel AX2xx, QCA9300, others | unifying multi-NIC capture/format | [picoscenes.md](picoscenes.md) |

See [csi-toolchains.md](csi-toolchains.md) for the reverse-engineering history
of each tool and the firmware hooks they rely on.

---

## 2. The master index

Every row is a **publicly downloadable** dataset. "Subcarriers" is the number
per antenna stream as the tool reports it (this includes null/guard carriers for
Nexmon and ESP32 — see notes). Sizes are approximate. License column is the
headline term; always read the actual license before redistribution or
commercial use.

| Dataset | Task | Chip / capture tool | Subcarriers | Size | Link | License |
|---------|------|---------------------|-------------|------|------|---------|
| **SignFi** | 276-class sign-language recognition | Intel 5300 / Linux 802.11n CSI Tool | 30 | ~6.1 GB (4 `.mat` files) | [github.com/yongsen/SignFi](https://github.com/yongsen/SignFi) | Non-commercial research (W&M) |
| **Widar3.0** | 22-class cross-domain hand gesture | Intel 5300 / Linux 802.11n CSI Tool (1 Tx, 6 Rx) | 30 | ~325 GB raw / 3.4 GB BVP | [tns.thss.tsinghua.edu.cn/widar3.0](https://tns.thss.tsinghua.edu.cn/widar3.0/) · [IEEE DataPort](https://ieee-dataport.org/open-access/widar-30-wifi-based-activity-recognition-dataset) | CC (IEEE DataPort open-access) |
| **UT-HAR (Yousefi)** | 7-class coarse activity (lie/fall/walk/run/sit/stand/pickup) | Intel 5300 / Linux 802.11n CSI Tool | 30 | ~340 MB | [github.com/ermongroup/Wifi_Activity_Recognition](https://github.com/ermongroup/Wifi_Activity_Recognition) | MIT |
| **FallDeFi** | Fall vs. daily-activity detection | Intel 5300 / Linux 802.11n CSI Tool | 30 | ~ hundreds of traces, several environments | [github.com/dmsp123/FallDeFi](https://github.com/dmsp123/FallDeFi) | MIT (S. Palipana, 2017) |
| **WiAR** | 16-class activity + gesture | Intel 5300 / Linux 802.11n CSI Tool (5 GHz, 20 MHz) | 30 | ~ few GB (per-activity `.mat`) | [github.com/linteresa/WiAR](https://github.com/linteresa/WiAR) | Academic use (see repo) |
| **NTU-Fi HAR** | 6-class activity (box/circle/clean/fall/run/walk) | Atheros AR9580 / Atheros CSI Tool | 114 (40 MHz) | ~ 1.2k samples | [github.com/xyanchen/WiFi-CSI-Sensing-Benchmark](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) | Research (SenseFi) |
| **NTU-Fi HumanID** | 14-class gait person-ID (t-shirt/coat/backpack) | Atheros AR9580 / Atheros CSI Tool | 114 (40 MHz) | ~840 samples | [github.com/xyanchen/WiFi-CSI-Sensing-Benchmark](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) | Research (SenseFi) |
| **Nexmon-CSI captures** | format reference + community sensing sets | Broadcom BCM43455c0 (Pi) / Nexmon CSI | 64/128/256 | varies | [github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) | Cite Nexmon + WiNTECH'19 |
| **ESP32-CSI-Tool samples** | edge activity/presence | Espressif ESP32 / ESP32-CSI-Tool | ≤64 (52 usable) | CSV, small | [github.com/StevenMHernandez/ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool) | MIT |
| **MM-Fi** | Multi-modal 27-action HAR / pose | Intel 5300 CSI + RGB-D + LiDAR + mmWave | 30 (CSI) | large (multimodal) | [github.com/ybhbingo/MMFi_dataset](https://github.com/ybhbingo/MMFi_dataset) | Research (NTU) |
| **OPERAnet** | Multi-modal HAR (RF + vision) | Intel 5300 + PicoScenes + UWB + Kinect | 30 (Intel CSI) | ~8 hrs, ~ tens of GB | [Zenodo 10.5281/zenodo.5616432](https://doi.org/10.5281/zenodo.5616432) | CC BY 4.0 |

> **Reproducibility shortcut:** the
> [WiFi-CSI-Sensing-Benchmark (SenseFi)](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark)
> repo repackages **UT-HAR, NTU-Fi HAR, NTU-Fi HumanID, SignFi, and Widar** into
> ready-to-load tensors with PyTorch dataloaders and reference MLP/CNN/RNN/ViT
> baselines. If your goal is "train a model tonight," start there rather than
> parsing raw `.dat` files.

---

## 3. Dataset deep-dives

### 3.1 SignFi — sign language, Intel 5300
- **Authors / venue:** Ma, Zhou, Wang, Xu — *SignFi: Sign Language Recognition
  Using WiFi*, IMWUT/UbiComp 2018 ([ACM 10.1145/3191755](https://dl.acm.org/doi/10.1145/3191755)).
- **Capture:** Intel 5300 NIC via the Linux 802.11n CSI Tool; 1 Tx antenna,
  3 Rx antennas, **30 subcarriers**, 200 packets per gesture instance.
- **Contents:** four `.mat` files hosted on Box —
  - Lab, 276 signs, 1 user: 5,520 instances (downlink 1.44 GB + uplink 1.33 GB),
  - Home, 276 signs, 1 user: 2,760 instances (1.37 GB),
  - Lab, 150 signs, 5 users: 7,500 instances (1.93 GB).
- **Load it:** each `.mat` has `csid_*` (complex CSI, shape `200 × 30 × 3 × Ninst`)
  and `label_*`. MATLAB source (CNN in the paper) ships in the repo.
- **License:** non-commercial educational/research use only (College of
  William & Mary); redistribution needs written approval.
- **Canonical repo:** [github.com/yongsen/SignFi](https://github.com/yongsen/SignFi)
  (the `huangshunliang/signFi` copy is a mirror/fork).

### 3.2 Widar3.0 — cross-domain gesture, Intel 5300
- **Authors / venue:** Zhang, Zheng, et al. (Tsinghua TNS) — *Zero-Effort
  Cross-Domain Gesture Recognition with Wi-Fi*, MobiSys 2019; extended in TPAMI.
- **Capture:** Intel 5300, **1 Tx / 6 Rx** synchronized receivers around the
  subject, 5.8 GHz, **30 subcarriers**, ~1000 Hz packet rate.
- **Scale:** 258K gesture instances, 8,620 minutes, **75 domains** (16 users ×
  positions × orientations × rooms). This is the reference benchmark for
  *domain generalization* in Wi-Fi sensing.
- **Derived features:** the authors publish **DFS** (Doppler Frequency Shift)
  spectrograms and the domain-independent **BVP** (Body-coordinate Velocity
  Profile). Raw CSI is ~325 GB; the BVP tensors are ~3.4 GB — most papers use
  BVP.
- **Get it:** primary at [tns.thss.tsinghua.edu.cn/widar3.0](https://tns.thss.tsinghua.edu.cn/widar3.0/);
  mirrored (with DOI + license) on
  [IEEE DataPort](https://ieee-dataport.org/open-access/widar-30-wifi-based-activity-recognition-dataset).
  Predecessors *Widar* (localization) and *Widar2.0* exist but Widar3.0 is the
  one to use for gesture.

### 3.3 UT-HAR / Yousefi — the HAR benchmark, Intel 5300
- **Origin:** Yousefi, Narui, et al. — *A Survey on Behavior Recognition Using
  WiFi Channel State Information*, IEEE Comms Mag 2017. Data + LSTM code in
  [ermongroup/Wifi_Activity_Recognition](https://github.com/ermongroup/Wifi_Activity_Recognition).
- **Capture:** Intel 5300 / Linux 802.11n CSI Tool, **30 subcarriers × 3
  antennas** (90 amplitude + 90 phase columns per packet), ~1 kHz.
- **Contents:** 557 continuous recordings, 6 participants, **7 activities**
  (lie down, fall, walk, run, sit down, stand up, pick up). Note it ships as
  *continuous* CSI, not pre-segmented windows — the common "UT-HAR" tensor used
  in benchmarks is a sliding-window re-cut (as done in SenseFi).
- **Gotcha:** because segmentation is done downstream, two papers citing
  "UT-HAR" may not use identical splits. When comparing, state your window size
  and stride. The SenseFi packaging fixes one convention.

### 3.4 FallDeFi — fall detection, Intel 5300
- **Authors / venue:** Palipana, Rojas, Agrawal, Pesch — *FallDeFi: Ubiquitous
  Fall Detection using Commodity Wi-Fi Devices*, IMWUT/UbiComp 2018
  ([ACM 10.1145/3161183](https://dl.acm.org/doi/10.1145/3161183)).
- **Capture:** two Linux laptops with Intel 5300 NICs (802.11n), external
  omni antennas, **30 subcarriers**. The method leans on
  spectrogram/power-burst features that survive environment change.
- **Data:** falls plus daily activities across several rooms/setups; the repo
  ([dmsp123/FallDeFi](https://github.com/dmsp123/FallDeFi), MIT license) holds an
  `Activity` folder plus a "Link to the data set" pointer and MATLAB processing
  code.

### 3.5 WiAR — public activity dataset, Intel 5300
- **Origin:** Guo et al. — *WiAR: A Public Dataset for WiFi-based Activity
  Recognition*, IEEE Access 2019. Repo:
  [linteresa/WiAR](https://github.com/linteresa/WiAR) (also mirrored at
  `LexieLH/WiAR-dataset`).
- **Capture:** Intel 5300 / Linux 802.11n CSI Tool, 5 GHz, 20 MHz, **30
  subcarriers**, 1 Tx / 3 Rx.
- **Contents:** **16 activities** (coarse actions + gestures) × **10
  volunteers** × 30 repetitions × 3 indoor environments. Files prefixed
  `input_*` carry `[timestamp | 90 amplitude | 90 phase]` per packet.

### 3.6 NTU-Fi (HAR + HumanID) — Atheros, higher resolution
- **Origin:** packaged and benchmarked in **SenseFi** — Yang, Chen, et al. —
  *SenseFi: A library and benchmark on deep-learning-empowered WiFi human
  sensing*, Patterns 2023
  ([Cell 10.1016/j.patter.2023.100703](https://www.cell.com/patterns/fulltext/S2666-3899(23)00040-5)).
- **Capture:** **Atheros AR9580** via the **Atheros CSI Tool** — this is the key
  distinction from the Intel-5300 datasets: **114 subcarriers** (40 MHz), 3
  antenna streams, ~500 Hz. Higher subcarrier resolution → finer frequency
  selectivity than the 30-subcarrier Intel sets.
- **Two tasks:** *NTU-Fi HAR* (6 activities: box, circle, clean, fall, run,
  walk) and *NTU-Fi HumanID* (14-person gait ID, captured with the subject
  wearing a t-shirt / coat / backpack to test clothing robustness).
- **Access:** the ready-to-load version lives in
  [WiFi-CSI-Sensing-Benchmark](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark).

### 3.7 Nexmon-CSI — Broadcom / Raspberry Pi
- **Origin:** Gringoli, Schulz, Link, Hollick — *Free Your CSI: A Channel State
  Information Extraction Platform For Modern Wi-Fi Chipsets*, WiNTECH 2019.
- **Capture tool:** [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi),
  supporting **BCM4339** (Nexus 5), **BCM43455c0** (Raspberry Pi 3B+/4B),
  **BCM4358** (Nexus 6P), **BCM4366c0** (Asus RT-AC86U). Emits CSI over UDP;
  **64/128/256 subcarriers** for 20/40/80 MHz — *including* guard/null carriers,
  which hold garbage and must be masked before use. BCM4339/43455c0 return
  interleaved `int16` I/Q; BCM4358/4366c0 return a sign/mantissa/exponent float
  form.
- **Why it matters for datasets:** unlike Intel/Atheros, this runs on a **$35
  Raspberry Pi**, so most *new* (post-2020) community CSI datasets are Nexmon
  captures. The repo itself is the format reference; verify the exact null-carrier
  mask for your chip/bandwidth against the repo's `README` before parsing.
- Full RE background: [nexmon.md](nexmon.md) and the walkthrough
  [bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md).

### 3.8 ESP32-CSI-Tool — the cheapest entry point
- **Origin:** Hernandez & Bulut — the ESP32-CSI-Tool project
  ([repo](https://github.com/StevenMHernandez/ESP32-CSI-Tool),
  [site](https://stevenmhernandez.github.io/ESP32-CSI-Tool/), MIT). Backed by
  the ESP-IDF `wifi_csi` API.
- **Capture:** a **$5 ESP32** in active-station, active-AP, or passive-listen
  mode; CSI written as **CSV** (easy to parse, no kernel patch). For a standard
  HT20 frame the ESP32 exposes up to **64 subcarriers** (LLTF), of which ~52 are
  usable data/pilot carriers.
- **Trade-off:** single antenna, coarser and noisier than Intel/Atheros/Nexmon,
  but unbeatable for classroom kits and dense sensor grids. Good for
  presence/occupancy and coarse activity; weak for fine gesture. See
  [espressif.md](../chips/espressif.md).

### 3.9 Multi-modal sets (RF + vision + depth)
- **MM-Fi** ([ybhbingo/MMFi_dataset](https://github.com/ybhbingo/MMFi_dataset)):
  40 subjects, 27 actions, synchronized **Intel-5300 CSI + RGB-D + LiDAR +
  mmWave radar**. Use when you want cross-modal supervision or CSI→pose.
- **OPERAnet** ([Zenodo](https://doi.org/10.5281/zenodo.5616432), CC BY 4.0):
  ~8 hours of HAR with Intel-5300 CSI (captured via **PicoScenes**), UWB,
  passive Wi-Fi radar, and Kinect ground truth. Good for sensor-fusion and for
  benchmarking CSI against a labeled vision reference.

---

## 4. Aggregators, portals & where to browse more

| Resource | What it is |
|----------|-----------|
| [Awesome-WiFi-CSI-Sensing](https://github.com/NTUMARS/Awesome-WiFi-CSI-Sensing) | Living index of papers **and** datasets; the best jumping-off list |
| [WiFi-CSI-Sensing-Benchmark / SenseFi](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) | Packaged UT-HAR, NTU-Fi, SignFi, Widar + baselines |
| [Gi-z/CSI-Data](https://github.com/Gi-z/CSI-Data) | Community collation of CSI samples/datasets across tools |
| [IEEE DataPort — WiFi/CSI](https://ieee-dataport.org/) | Search "CSI" / "WiFi sensing"; hosts Widar3.0 and others with DOIs + licenses |
| [Zenodo](https://zenodo.org/) | DOI-versioned datasets (OPERAnet, many newer captures) |
| Kaggle | Search "WiFi CSI" — mostly re-hosts of UT-HAR/derived tensors; treat provenance skeptically, prefer the primary repo |

> **On Kaggle/re-hosts:** many Kaggle "WiFi CSI" datasets are un-attributed
> copies of UT-HAR or SignFi with lossy pre-processing baked in. For any
> published result, cite and download the **primary** repo/DOI above, not the
> Kaggle mirror — the mirror's segmentation and normalization are usually
> undocumented.

---

## 5. Reproducibility checklist

Before you trust a number you got from someone else's CSI dataset:

1. **Identify the tool, not just the chip.** "Intel 5300" alone doesn't fix the
   format — the Linux 802.11n CSI Tool applies AGC and reports 30 subcarriers in
   a specific packed struct. Atheros gives 56/114. Nexmon includes null
   carriers. See [csi-toolchains.md](csi-toolchains.md).
2. **Mask null/guard subcarriers** for Nexmon and ESP32 data before feeding a
   model — they carry non-physical values.
3. **Phase is not calibrated.** Intel/Atheros/Nexmon raw phase carries CFO, SFO
   and a random per-packet offset. Most datasets store *raw* CSI; papers apply
   linear-fit phase sanitization or conjugate-multiplication (see
   [techniques.md](../docs/techniques.md)). State which one you used.
4. **Pin the segmentation.** For continuous sets (UT-HAR, FallDeFi), window size
   and stride change accuracy by several points. Report them.
5. **Respect the license.** SignFi and several NTU sets are research-only.
   OPERAnet/Widar (DataPort) are CC-style. Check before redistributing or
   commercializing.
6. **Match capture geometry when you extend a set.** Widar3.0's power comes from
   its 6-receiver layout; a single-Rx capture is not comparable.

---

## 6. Cross-references
- Tool internals & RE history → [csi-toolchains.md](csi-toolchains.md)
- Chip pages: [Intel](../chips/intel.md) · [Qualcomm/Atheros](../chips/qualcomm-atheros.md) · [Broadcom/Cypress](../chips/broadcom-cypress.md) · [Espressif](../chips/espressif.md)
- Capture walkthroughs: [Intel 5300 CSI](../docs/walkthroughs/intel-5300-csi.md) · [Atheros ath9k spectral/CSI](../docs/walkthroughs/atheros-ath9k-spectral-csi.md) · [BCM43455c0 on a Pi](../docs/walkthroughs/bcm43455c0-raspberry-pi.md)
- Unifying capture framework → [picoscenes.md](picoscenes.md)
- Signal-processing methods (phase sanitization, DFS, BVP) → [techniques.md](../docs/techniques.md)

---

## References
1. Y. Ma, G. Zhou, S. Wang, H. Zhao, W. Jung, "SignFi: Sign Language Recognition Using WiFi," *Proc. ACM IMWUT* 2(1), 2018. https://dl.acm.org/doi/10.1145/3191755 — repo https://github.com/yongsen/SignFi
2. Y. Zhang, Y. Zheng, K. Qian, et al., "Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi" (Widar3.0), *MobiSys* 2019. https://tns.thss.tsinghua.edu.cn/widar3.0/ — IEEE DataPort https://ieee-dataport.org/open-access/widar-30-wifi-based-activity-recognition-dataset
3. S. Yousefi, H. Narui, S. Dayal, S. Ermon, S. Valaee, "A Survey on Behavior Recognition Using WiFi Channel State Information," *IEEE Comms Mag*, 2017. https://github.com/ermongroup/Wifi_Activity_Recognition
4. S. Palipana, D. Rojas, P. Agrawal, D. Pesch, "FallDeFi: Ubiquitous Fall Detection using Commodity Wi-Fi Devices," *Proc. ACM IMWUT* 2(4), 2018. https://dl.acm.org/doi/10.1145/3161183 — repo https://github.com/dmsp123/FallDeFi
5. L. Guo, et al., "WiAR: A Public Dataset for WiFi-based Activity Recognition," *IEEE Access*, 2019. https://github.com/linteresa/WiAR
6. J. Yang, X. Chen, H. Zou, et al., "SenseFi: A library and benchmark on deep-learning-empowered WiFi human sensing," *Patterns* 4(3), 2023. https://www.cell.com/patterns/fulltext/S2666-3899(23)00040-5 — repo https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark
7. F. Gringoli, M. Schulz, J. Link, M. Hollick, "Free Your CSI: A Channel State Information Extraction Platform For Modern Wi-Fi Chipsets," *ACM WiNTECH* 2019. https://github.com/seemoo-lab/nexmon_csi
8. S. M. Hernandez, E. Bulut, "Lightweight and Standalone IoT Based WiFi Sensing for Active Repositioning and Mobility" / ESP32-CSI-Tool. https://github.com/StevenMHernandez/ESP32-CSI-Tool · https://stevenmhernandez.github.io/ESP32-CSI-Tool/
9. J. Yang, et al., "MM-Fi: Multi-Modal Non-Intrusive 4D Human Dataset for Versatile Wireless Sensing," *NeurIPS Datasets & Benchmarks*, 2023. https://github.com/ybhbingo/MMFi_dataset
10. M. J. Bocus, et al., "OPERAnet: A Multimodal Activity Recognition Dataset Acquired from Radio Frequency and Vision-based Sensors," *Scientific Data*, 2022. https://doi.org/10.5281/zenodo.5616432 · https://arxiv.org/abs/2110.04239
11. NTUMARS, "Awesome-WiFi-CSI-Sensing" (curated paper + dataset index). https://github.com/NTUMARS/Awesome-WiFi-CSI-Sensing
12. Gi-z, "CSI-Data" community collation. https://github.com/Gi-z/CSI-Data

*Last verified against primary sources: 2026-08-20.*
