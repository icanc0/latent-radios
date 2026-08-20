# Further Reading: The Canon

A curated, grouped bibliography for the *Latent Radios* project — the papers, books, and
repositories that define the field where commodity Wi-Fi/wireless silicon is bent into
software-defined-radio-like instruments. Every entry below is a **primary or near-primary
source**: the paper that released a tool, the thesis that built a framework, the book that
teaches the theory. Where a work has a canonical landing page (a `github.com/seemoo-lab`
repo, a university project page, a free vendor PDF) that URL is given in preference to a
paywalled DOI, because it is the one that survives.

This is the reading list. For the *catalogued chips* those papers act on, see the
[chips index](../chips/hardware-index.md); for the *tools* as living software, see
[`../projects/nexmon.md`](../projects/nexmon.md), [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md),
and [`../projects/picoscenes.md`](../projects/picoscenes.md); for the *labelled data* the
sensing papers produced, see [`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md).

> **Reading order for newcomers.** Start with §5 (SDR foundations) to fix the vocabulary
> — IQ, PHY, subcarriers — then §1 (how firmware is opened) and §2 (how CSI is extracted),
> then §3 (what people *do* with it). §4 and §6 are depth and tooling. The
> [glossary](glossary.md) and [taxonomy](taxonomy.md) are companions throughout.

---

## 1. Firmware reverse-engineering & the Nexmon lineage

The SEEMOO Secure Mobile Networking Lab (TU Darmstadt) work is the spine of this whole
catalogue: it is the body of research that first turned a shipping Broadcom/Cypress Wi-Fi
FullMAC firmware into a *patchable, C-programmable* platform, and then used that leverage
to transmit arbitrary waveforms, jam reactively, and extract CSI. Read these in roughly
chronological order.

| # | Citation | Why it matters | Link |
|---|----------|----------------|------|
| 1.1 | Schulz, M., Wegemer, D., Hollick, M. **"Nexmon: The C-based Firmware Patching Framework."** 2017 (framework release / project site). | The founding tool: a build system that decompiles, patches in C, and re-flashes Broadcom/Cypress `bcmdhd` firmware. Everything downstream depends on it. | <https://nexmon.org> · <https://github.com/seemoo-lab/nexmon> |
| 1.2 | Schulz, M., Wegemer, D., Hollick, M. **"DEMO: Using NexMon, the C-based WiFi Firmware Modification Framework."** *Proc. ACM WiSec 2016.* | The first peer-reviewed presentation of the framework and its patching model. | doi:10.1145/2939918.2942419 |
| 1.3 | **Schulz, M.** *Teaching Your Wireless Card New Tricks: Smartphone Performance and Security Enhancements Through Wi-Fi Firmware Modifications.* PhD thesis, TU Darmstadt, 2018. | The definitive, book-length account of the D11 core, the FullMAC/SoftMAC split, template RAM, and how a phone's Wi-Fi chip is reprogrammed. The single best deep read on the subject. | <https://tuprints.ulb.tu-darmstadt.de/7364/> |
| 1.4 | Schulz, M., Link, J., Gringoli, F., Hollick, M. **"Shadow Wi-Fi: Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi."** *Proc. ACM MobiSys 2018.* | The landmark that proved a commodity smartphone chip can emit **raw IQ / arbitrary waveforms** (Tier 4) and hide a covert channel beneath a legitimate Wi-Fi transmission. The proof that "latent radio" is real, not rhetorical. | doi:10.1145/3210240.3210333 |
| 1.5 | Schulz, M., Gringoli, F., Steinmetzer, D., Koch, M., Hollick, M. **"Massive Reactive Smartphone-Based Jamming using Arbitrary Waveforms and Adaptive Power Control."** *Proc. ACM WiSec 2017.* | Reactive jamming from a phone: sense a target packet and transmit an interfering waveform within the same slot. Demonstrates real-time PHY-level control and adaptive TX power. (Study responsibly; jamming is illegal on licensed/unlicensed bands in most jurisdictions — see the [techniques](techniques.md) regulatory note.) | doi:10.1145/3098243.3098253 |
| 1.6 | **D11 microcode disassembler / `d11-emu`** (SEEMOO / D. Wegemer). Tooling for the Broadcom D11 real-time PHY microcode core. | The D11 ucode is the innermost layer — the real-time engine that shapes symbols. The Nexmon D11 disassembler and emulation work is what makes the deepest PHY tricks (spectral scan, waveform injection) intelligible. | <https://github.com/seemoo-lab/nexmon> (`buildtools`/`patches` D11 tooling) |
| 1.7 | Steinmetzer, D., Wegemer, D., Schulz, M., Widmer, J., Hollick, M. **"Compressive Millimeter-Wave Sector Selection in Off-the-Shelf IEEE 802.11ad Devices."** *Proc. ACM CoNEXT 2017*; and **"Talon Tools: The Framework for Practical Analysis of IEEE 802.11ad Devices."** | Nexmon extended to 60 GHz on the TP-Link Talon AD7200 (QCA9500): reading and steering the mmWave beamforming codebook on a shipping consumer router. | <https://seemoo.de/talon-tools/> · <https://github.com/seemoo-lab/talon-tools> |

**Foundational context for firmware RE.** For the mechanics of *how* one gets into these
binaries — Ghidra loaders, ROM/RAM overlays, symbol recovery — see this repo's
[firmware-reversing guide](firmware-reversing.md) and the
[Ghidra Wi-Fi walkthrough](walkthroughs/ghidra-setup-wifi-firmware.md).

---

## 2. Channel State Information (CSI) tooling — the tool-release papers

CSI — the complex per-subcarrier channel response an OFDM receiver already estimates — is
the raw material of Wi-Fi sensing. Each paper below *released a working extractor* for a
specific chip family. They are the reason "CSI" is a commodity measurement and not a
lab-only exotic. Cross-reference the living toolchains in
[`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) and
[`../projects/picoscenes.md`](../projects/picoscenes.md).

| # | Citation | Chip / platform | Link |
|---|----------|-----------------|------|
| 2.1 | Halperin, D., Hu, W., Sheth, A., Wetherall, D. **"Tool Release: Gathering 802.11n Traces with Channel State Information."** *ACM SIGCOMM Computer Communication Review*, 41(1), 2011. | **Intel Wi-Fi Link 5300 (`iwl5300`).** The origin of commodity CSI research — 30-subcarrier CSI from a laptop NIC. Cited by essentially every sensing paper since. | doi:10.1145/1925861.1925870 · <https://dhalperi.github.io/linux-80211n-csitool/> |
| 2.2 | Xie, Y., Li, Z., Li, M. **"Precise Power Delay Profiling with Commodity Wi-Fi."** *Proc. ACM MobiCom 2015.* | **Atheros AR9xxx (ath9k).** The "Atheros CSI Tool" — 56/114 subcarriers, richer than the 5300, and open on a widely available chipset. | <https://wands.sg/research/wifi/AtherosCSI/> · doi:10.1145/2789168.2790124 |
| 2.3 | Gringoli, F., Schulz, M., Link, J., Hollick, M. **"Free Your CSI: A Channel State Information Extraction Platform for Modern Wi-Fi Chipsets."** *Proc. ACM WiNTECH 2019.* | **Broadcom/Cypress via Nexmon (`nexmon_csi`).** CSI from phones, Raspberry Pi (BCM43455c0), and other modern chips — the bridge from the 5300 era to current hardware, including 80 MHz bandwidth. | doi:10.1145/3349623.3355477 · <https://github.com/seemoo-lab/nexmon_csi> |
| 2.4 | Gringoli, F., Cominelli, M., Blanco, A., Widmer, J. **"AX-CSI: Enabling CSI Extraction on Commercial 802.11ax Wi-Fi Platforms."** *Proc. ACM WiNTECH 2021.* | **802.11ax (Wi-Fi 6, Broadcom).** Pushes CSI extraction into HE / OFDMA-era PHYs with up to 2048 subcarriers at 160 MHz. | doi:10.1145/3477086.3480833 |
| 2.5 | Jiang, Z., Luan, T. H., Ren, X., Lv, D., Hao, H., Wang, J., et al. **"Eliminating the Barriers: Demystifying Wi-Fi Baseband Design and Introducing the PicoScenes Wi-Fi Sensing Platform."** *IEEE Internet of Things Journal*, 9(6), 2022. | **Unified multi-vendor platform** (Intel AX200/AX210, QCA, and SDR back-ends). The most capable single CSI toolchain today; also a superb tutorial on Wi-Fi baseband internals. | doi:10.1109/JIOT.2021.3104666 · <https://ps.zpj.io> |
| 2.6 | Hernandez, S. M., Bulut, E. **"Lightweight and Standalone IoT Based WiFi Sensing for Active Repositioning and Mobility."** *Proc. IEEE WoWMoM 2020.* | **ESP32.** The "ESP32-CSI-Tool" — CSI from a \$5 microcontroller, standalone and battery-friendly; the democratiser of sensing hardware. See [`../chips/espressif.md`](../chips/espressif.md). | <https://stevenmhernandez.github.io/ESP32-CSI-Tool/> |
| 2.7 | Forbes, G. et al. **"CSIKit: Python CSI processing and analysis."** (Tooling library.) | Reads Nexmon, 5300, Atheros, and ESP32 CSI formats into a common Python representation — the practical glue for anyone working across the extractors above. | <https://github.com/Gi-z/CSIKit> |

Verification methodology for CSI claims (what "Tier 2" actually requires to be believed)
is written up in [verification-tier2-csi.md](verification-tier2-csi.md).

---

## 3. Wi-Fi sensing — surveys & landmark systems

What CSI and radio reflections are *for*: seeing motion, gesture, breathing, pose, and
identity through and around walls. The landmarks below defined problems; the surveys map
the field. Datasets from many of these live in
[`../projects/wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md).

### Landmark systems

- **WiSee** — Pu, Q., Gupta, S., Gollakota, S., Patel, S. **"Whole-Home Gesture Recognition Using Wireless Signals."** *Proc. ACM MobiCom 2013.* The paper that put Doppler-based whole-home gesture recognition on the map. doi:10.1145/2500423.2500436
- **See Through Walls with Wi-Fi** — Adib, F., Katabi, D. **"See Through Walls with WiFi!"** *Proc. ACM SIGCOMM 2013.* MIT's demonstration that ordinary Wi-Fi frequencies reveal motion behind walls. doi:10.1145/2486001.2486039
- **WiTrack** — Adib, F., Kabelac, Z., Katabi, D., Miller, R. C. **"3D Tracking via Body Radio Reflections."** *Proc. USENIX NSDI 2014.* FMCW radar built from Wi-Fi-band signals for decimetre 3D body tracking. <https://witrack.csail.mit.edu/>
- **CARM** — Wang, W., Liu, A. X., Shahzad, M., Ling, K., Lu, S. **"Understanding and Modeling of WiFi Signal Based Human Activity Recognition."** *Proc. ACM MobiCom 2015.* The CSI-speed model linking activities to CSI dynamics. doi:10.1145/2789168.2790093
- **SpotFi** — Kotaru, M., Joshi, K., Bharadia, D., Katti, S. **"SpotFi: Decimeter Level Localization Using WiFi."** *Proc. ACM SIGCOMM 2015.* Angle-of-arrival + time-of-flight super-resolution on commodity CSI. doi:10.1145/2785956.2787487
- **Widar / Widar2.0 / Widar3.0** — Qian, K., Wu, C., Yang, Z., Liu, Y., Jamieson, K. **"Widar: Decimeter-Level Passive Tracking via Velocity Monitoring with Commodity Wi-Fi"** (*MobiHoc 2017*); **"Widar2.0"** (*MobiSys 2018*); Zheng, Y., et al. **"Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi"** (Widar3.0, *MobiSys 2019*). The passive-tracking-to-cross-domain-gesture arc; Widar3.0's dataset is a community benchmark. <http://tns.thss.tsinghua.edu.cn/widar3.0/>
- **FarSense** — Zeng, Y., Wu, D., Xiong, J., Yi, E., Gao, R., Zhang, D. **"FarSense: Pushing the Range Limit of WiFi-based Respiration Sensing with CSI Ratio of Two Antennas."** *Proc. ACM IMWUT/UbiComp 2019.* The CSI-ratio trick that cancels noise and extends respiration-sensing range. doi:10.1145/3351279
- **Person-in-WiFi** — Wang, F., Zhou, S., Panev, S., Han, J., Huang, D. **"Person-in-WiFi: Fine-Grained Person Perception Using WiFi."** *Proc. IEEE/CVF ICCV 2019.* Body segmentation and pose from Wi-Fi alone. arXiv:1904.00276
- **DensePose From WiFi** — Geng, J., Huang, D., De la Torre, F. **"DensePose From WiFi."** *arXiv preprint*, 2022/2023. Dense human body surface estimation using only three transmit/receive Wi-Fi antennas — the piece that reached the popular press. arXiv:2301.00250

### Surveys & tutorials

- Ma, Y., Zhou, G., Wang, S. **"WiFi Sensing with Channel State Information: A Survey."** *ACM Computing Surveys*, 52(3), 2019. The standard CSI-sensing survey. doi:10.1145/3310194
- Yousefi, S., Narui, H., Dayal, S., Ermon, S., Valaee, S. **"A Survey on Behavior Recognition Using WiFi Channel State Information."** *IEEE Communications Magazine*, 55(10), 2017. Pairs a survey with the widely reused SignFi/activity dataset and a deep-learning baseline. doi:10.1109/MCOM.2017.1700082
- Liu, J., Liu, H., Chen, Y., Wang, Y., Wang, C. **"Wireless Sensing for Human Activity: A Survey."** *IEEE Communications Surveys & Tutorials*, 22(3), 2020. Broad cross-technology view (Wi-Fi, RFID, radar). doi:10.1109/COMST.2019.2934489
- Restuccia, F. **"IEEE 802.11bf: Toward Ubiquitous Wi-Fi Sensing."** *arXiv preprint*, 2021. The forward-looking reference on Wi-Fi sensing becoming a *standardised* PHY feature rather than a firmware hack. arXiv:2103.14918
- Chen, Y., et al. **"Awesome WiFi CSI Sensing"** (curated living bibliography). A continuously updated companion to the surveys above. <https://github.com/Marsrocky/Awesome-WiFi-CSI-Sensing>

---

## 4. Spectrum, spectral scan & (passive) radar

Between "packets" (Tier 1) and "CSI" (Tier 2) sits the ability to look at the *raw spectrum*
— FFT bins off the PHY — and, beyond that, to treat the reflections as a radar return.
See [true-sdr-comparison.md](true-sdr-comparison.md) for where these land against a real SDR.

- **Atheros `ath9k` spectral scan** — Wunderlich, S., Randolf, B. et al. The `ath9k`/`ath9k_htc`
  and `ath10k` **spectral scan** feature exposes per-bin FFT magnitudes from the PHY,
  the closest thing to a free "spectrum analyser mode" on commodity Wi-Fi. Kernel docs and
  the `spectral_scan` debugfs interface; visualiser: <https://github.com/simonwunderlich/FFT_eval>.
  This is the Tier-3 anchor for the Atheros family in [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md).
- **Nexmon spectral analysis** — Schulz et al. extended spectral-scan-style raw-PHY readout to
  Broadcom chips as part of the Nexmon ecosystem (see §1). The mechanism is documented in
  this repo's [techniques](techniques.md) and [tier-3 discussion](taxonomy.md).
- **Passive Wi-Fi radar** — Chetty, K., Smith, G. E., Woodbridge, K. **"Through-the-Wall Sensing of Personnel Using Passive Bistatic WiFi Radar at Standoff Distances."** *IEEE Transactions on Geoscience and Remote Sensing*, 50(4), 2012. The reference for treating ambient Wi-Fi as a bistatic radar illuminator — the theoretical basis for the `passive-radar` capability flag. doi:10.1109/TGRS.2011.2164411
- **FMCW from Wi-Fi-band signals** — the WiTrack line (§3) and Adib, F., Mao, H., Kabelac, Z., Katabi, D., Miller, R. C. **"Smart Homes that Monitor Breathing and Heart Rate"** (*CHI 2015*) are the canonical FMCW-radar-built-from-radio-reflections works; they justify the `fmcw`/`radar` flags. doi:10.1145/2702123.2702200
- **RF-Capture / RF-Pose** — Adib, F., et al. **"Capturing the Human Figure Through a Wall"** (*SIGGRAPH Asia 2015*) and Zhao, M., et al. **"Through-Wall Human Pose Estimation Using Radio Signals"** (*CVPR 2018*). MIT's imaging-through-walls line; adjacent to, but often confused with, commodity-Wi-Fi sensing. <http://rfpose.csail.mit.edu/>

---

## 5. SDR foundations — the theory this whole catalogue rests on

Before "latent radio" means anything you need the vocabulary of real SDR: IQ sampling, the
digital PHY, OFDM, the Nyquist/quadrature picture. These are the texts and tools to build
that foundation.

- **Collins, T. F., Getz, R., Pyzocha, D., Brannon, K.** *Software-Defined Radio for Engineers.*
  Analog Devices / Artech House, 2018. **Free, complete PDF** — the best single from-zero
  SDR textbook, built around the ADALM-PLUTO. Read chapters 1–3 first.
  <https://www.analog.com/en/resources/education-library/software-defined-radio-for-engineers.html>
- **GNU Radio.** The open signal-processing framework and flowgraph environment that is the
  lingua franca of SDR. Project + tutorials: <https://www.gnuradio.org> · wiki tutorials
  <https://wiki.gnuradio.org/index.php/Tutorials>. OOT modules relevant here are catalogued in
  [`../projects/gnuradio-oot-modules.md`](../projects/gnuradio-oot-modules.md).
- **The RTL-SDR story.** How a \$20 DVB-T dongle (Realtek RTL2832U) was discovered by
  Eric Fry and Antti Palosaari to expose raw 8-bit IQ, and how Osmocom's `rtl-sdr` driver
  turned it into the device that created the modern hobbyist-SDR movement.
  Osmocom project: <https://osmocom.org/projects/rtl-sdr/wiki> · community history:
  <https://www.rtl-sdr.com/about-rtl-sdr/>. Full lineage in
  [`rtl-sdr-lineage.md`](../projects/rtl-sdr-lineage.md).
- **Ossmann, M.** *Software Defined Radio with HackRF.* Great Scott Gadgets — the classic
  free video course that pairs theory with a transmit-capable SDR.
  <https://greatscottgadgets.com/sdr/>
- **Lyons, R. G.** *Understanding Digital Signal Processing*, 3rd ed., Prentice Hall, 2010.
  The standard DSP reference behind everything above (mixing, filtering, FFTs, decimation).
- **Ettus Research / USRP Hardware Driver (UHD).** The professional-grade SDR reference
  platform and its host driver, the yardstick a "latent radio" is measured against.
  <https://kb.ettus.com/> · <https://github.com/EttusResearch/uhd>

For a side-by-side of a commodity Wi-Fi chip's "SDR" capabilities against a genuine SDR,
see [true-sdr-comparison.md](true-sdr-comparison.md).

---

## 6. Essential repositories

The living code. If a paper above released a tool, its repo is here; the others are the
platforms and reference implementations you actually clone.

| Repository | What it is | URL |
|-----------|------------|-----|
| `seemoo-lab/nexmon` | The C firmware-patching framework (§1). | <https://github.com/seemoo-lab/nexmon> |
| `seemoo-lab/nexmon_csi` | Nexmon-based CSI extractor for Broadcom/Cypress (§2.3). | <https://github.com/seemoo-lab/nexmon_csi> |
| `dhalperi/linux-80211n-csitool` | The original Intel 5300 CSI Tool (§2.1). | <https://github.com/dhalperi/linux-80211n-csitool-supplementary> |
| `wifi-sensing / PicoScenes` | Unified multi-vendor CSI platform (§2.5). | <https://ps.zpj.io> |
| `StevenMHernandez/ESP32-CSI-Tool` | Standalone CSI from the ESP32 (§2.6). | <https://github.com/StevenMHernandez/ESP32-CSI-Tool> |
| `Gi-z/CSIKit` | Cross-format CSI parsing/analysis in Python (§2.7). | <https://github.com/Gi-z/CSIKit> |
| `open-sdr/openwifi` | Jiao, X., et al. **"openwifi: a free and open-source IEEE 802.11 SDR implementation on SoC"** (*IEEE VTC 2020*). A *full* open Wi-Fi PHY+MAC on FPGA — the genuine Tier-5 SDR reference in this space. See [`../projects/openwifi.md`](../projects/openwifi.md). | <https://github.com/open-sdr/openwifi> |
| `gnuradio/gnuradio` | The SDR signal-processing framework (§5). | <https://github.com/gnuradio/gnuradio> |
| `osmocom/rtl-sdr` | The driver that started hobbyist SDR (§5). | <https://gitea.osmocom.org/sdr/rtl-sdr> |
| `Marsrocky/Awesome-WiFi-CSI-Sensing` | Curated, maintained sensing bibliography (§3). | <https://github.com/Marsrocky/Awesome-WiFi-CSI-Sensing> |
| `seemoo-lab/talon-tools` | Nexmon for 60 GHz 802.11ad (§1.7). | <https://github.com/seemoo-lab/talon-tools> |

---

## How to cite this catalogue's claims

Every capability tier and firmware-openness label in *Latent Radios* should trace back to a
source in this list or to a primary datasheet/repo cited on the chip's own page. When a claim
rests on a single conference demo or an unreproduced blog post, it is marked `reported` or
`theoretical` in the module record, never `verified`. The verification method for the two
tiers most often over-claimed is written up separately:
[Tier-4 (arbitrary waveform)](verification-tier4.md) and
[Tier-2 (CSI)](verification-tier2-csi.md).

*Note on links and DOIs:* landing-page URLs (project sites, GitHub, the free Analog Devices
PDF, arXiv abstracts) were preferred as the most durable pointers; DOIs are given for
paywalled conference/journal papers where they are the canonical identifier. A few DOIs are
reproduced from citation records rather than re-fetched live in this session — resolve the
DOI or search the exact title/venue if a link drifts.
