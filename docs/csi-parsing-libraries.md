# CSI Parsing & Analysis Libraries

*Latent Radios — Cycle 5*

Capturing Channel State Information (CSI) is only half the job. The `.dat` /
`.pcap` / `.csi` blob a NIC or firmware patch spits out is a raw, chip-specific
byte stream: sign-magnitude nibbles, AGC/RSSI headers, permutation vectors,
implicit scaling. This page indexes the software you reach for **after** capture —
the parsers that turn those bytes into a complex `[packets × subcarriers × Rx × Tx]`
tensor, and the analysis/DL toolkits that turn the tensor into a result.

For the *capture-side* firmware and drivers (nexmon_csi, the Intel/Atheros CSI
Tools, PicoScenes, ESP32-CSI-Tool) see **[../projects/csi-toolchains.md](../projects/csi-toolchains.md)**.
For an end-to-end worked example of going from a nexmon pcap to a usable
matrix, see **[../docs/walkthroughs/nexmon-csi-to-usable-csi.md](../docs/walkthroughs/nexmon-csi-to-usable-csi.md)**.

> Scope note: this is a *software* index — `modules[]` is intentionally empty.
> No new silicon is claimed here.

---

## The parsing problem in one paragraph

Every CSI source emits a different container. Intel's iwl5300 writes
length-prefixed "beamforming" records with a 20-byte header, 3-bit exponent
`Nrx×Ntx` scaling, and an antenna **permutation** you must undo. Atheros
(QCA9300/AR9580) logs its own TLV with per-tone 10-bit I/Q. nexmon_csi tunnels
CSI in fake UDP frames inside a **pcap**, byte order and float format varying by
chip (`bcm43455c0` vs `bcm4358` vs `bcm4366c0`) and by patch build. ESP32 prints
CSV lines over serial. PicoScenes uses a self-describing **versioned-segment**
`.csi`/`.mmap`. A parser library's whole value is hiding these differences behind
one `read()` that returns numpy. The rest of the value is *speed* (a single gesture
dataset can be tens of GB) and *correctness of scaling* (get the exponent wrong and
your amplitude is off by orders of magnitude).

---

## Comparison table

| Library | Lang / accel | Chips & input formats | Role | Maintenance | License | Link |
|---|---|---|---|---|---|---|
| **CSIKit** | Python (numpy) | Intel IWL5300, Intel AX200/AX210 (incl. FeitCSI), Atheros 802.11n, Broadcom BCM4339/4358/43455c0/4366c0 (nexmon), ESP32, USRP via PicoScenes | Universal reader + CLI, viz, CSV/JSON export, metrics | Active | MIT | [Gi-z/CSIKit](https://github.com/Gi-z/CSIKit) |
| **csiread** | Cython → C | Intel 5300 (Linux 802.11n Tool), Atheros (+ AtherosPull10), Nexmon (+ NexmonPull46), ESP32, PicoScenes (experimental) | Fast batch/real-time parser (~15× vs MATLAB) | Active | MIT | [citysu/csiread](https://github.com/citysu/csiread) |
| **nexcsi** | Python (numpy) | nexmon_csi pcap: Raspberry Pi (bcm43455c0), Nexus 5 (bcm4339), Nexus 6P (bcm4358), RT-AC86U (bcm4366c0) | Minimal, fast nexmon_csi pcap decoder | Low but usable | (see repo) | [nexmonster/nexcsi](https://github.com/nexmonster/nexcsi) |
| **PicoScenes MATLAB Toolbox (PMT)** + Python parsers | MATLAB (mex) / Python | PicoScenes `.csi`: Intel AX210/AX200, QCA9300, IWL5300, USRP, HackRF | Reference reader for the richest COTS/SDR CSI format | Active (with platform) | Free for academic use | [ps.zpj.io](https://ps.zpj.io/) |
| **SenseFi** (WiFi-CSI-Sensing-Benchmark) | Python / PyTorch | Pre-processed CSI tensors: UT-HAR, NTU-Fi HAR/HumanID, Widar-BVP | DL model + dataset **benchmark** (analysis, not parsing) | Paper-release, light upkeep | MIT | [xyanchen/WiFi-CSI-Sensing-Benchmark](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) |
| **Widar3.0 BVP toolset** | MATLAB | Intel 5300 CSI → DFS (Doppler) → BVP (Body-coordinate Velocity Profile) | Feature-engineering pipeline for cross-domain gesture | Research release (static) | Academic (dataset terms) | [Widar3.0](http://tns.thss.tsinghua.edu.cn/widar3.0/) |
| **Intel 5300 CSI Tool MATLAB scripts** | MATLAB / C | iwl5300 `.dat` beamforming logs | Canonical `read_bf_file` / `get_scaled_csi` reference implementation | Archived (read-only, 2020) | Dual (see FAQ) | [dhalperi/linux-80211n-csitool-supplementary](https://github.com/dhalperi/linux-80211n-csitool-supplementary) |
| **Atheros CSI Tool user-space + MATLAB** | C / MATLAB | QCA9300 / AR9580 CSI logs | `read_log_file` reference reader, RX/TX apps | Static | GPL-family (see repo) | [xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP](https://github.com/xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP) |
| **gr-ieee802-11** (GNU Radio) | C++ / Python (GNU Radio) | SDR IQ (USRP etc.) → decoded OFDM + per-frame CSI/equalizer taps | SDR-side "ground-truth" CSI from a full soft PHY | Maintained | GPLv3 | [bastibl/gr-ieee802-11](https://github.com/bastibl/gr-ieee802-11) |

---

## Per-tool notes

### CSIKit — the Swiss-army reader (Python)
The most format-agnostic option and usually the right first stop. A single
`get_reader()` sniffs the file and returns the matching backend for Intel 5300,
Intel AX200/AX210 (including the newer **FeitCSI** capture format), Atheros,
Broadcom/nexmon (`bcm4339`, `bcm4358`, `bcm43455c0`, `bcm4366c0`), ESP32, and
USRP-via-PicoScenes. Ships both a CLI and a library, plus matplotlib
visualisation, CSV/JSON export, and built-in metrics (RSSI, amplitude/phase,
some activity-detection helpers). Pure-numpy, so slower than csiread on huge
batches, but the breadth and the "just point it at a file" ergonomics make it the
default teaching/prototyping tool. `pip install CSIKit`. **Status: verified** —
formats and API confirmed against the repo.

```python
from CSIKit.reader import get_reader
reader = get_reader("log.all_csi.6.7.6.dat")   # backend auto-selected
csi = reader.read_file("log.all_csi.6.7.6.dat", scaled=True)
# CLI:  csikit --graph --graph_type all_subcarriers file.dat
#       csikit --csv file.dat
```

### csiread — when the dataset is big (Cython/C)
Same format coverage philosophy, engineered for throughput: the parsers are
written in Cython and compile to C, reported at **≥15× faster than the MATLAB
reference** on read + scaling. Exposes seven classes — `Intel`, `Atheros`,
`AtherosPull10`, `Nexmon`, `NexmonPull46`, `ESP32`, `Picoscenes` (the last
experimental) — each with a common `read()` / `seek()` / `pmsg()` / `display()`
surface, so you can do offline batch (`read`) or online per-packet (`pmsg`, e.g.
off a live socket or FIFO) with the same code. `csiread.utils` carries scaling and
phase-sanitisation helpers. This is the workhorse for building training sets from
gesture/activity captures. `pip install csiread`. **Status: verified.**

```python
import csiread
csidata = csiread.Nexmon("trace.pcap", chip="43455c0", bw=80)
csidata.read()
csi = csidata.csi            # complex64 [packets, subcarriers]
```

### nexcsi — a lean nexmon_csi pcap decoder (Python)
Does exactly one thing well: decode `nexmon_csi` pcaps into numpy structured
arrays. Device presets (`raspberrypi` → bcm43455c0, `nexus5` → bcm4339,
`nexus6p` → bcm4358, `rtac86u` → bcm4366c0) select the right byte order / float
unpacking, and `unpack()` optionally zeroes null and pilot subcarriers so you
don't feed garbage tones to a model. Returns RSSI, frame-control, MACs and the
complex CSI in one array. Fewer bells than CSIKit but a clean dependency-light
choice when nexmon is your only source. `pip install nexcsi`. **Status: verified**
(device presets/API confirmed; confirm license in-repo before redistribution).

```python
from nexcsi import decoder
samples = decoder("raspberrypi").read_pcap("trace.pcap")
csi = decoder("raspberrypi").unpack(samples["csi"], zero_nulls=True, zero_pilots=True)
```

### PicoScenes MATLAB Toolbox (PMT) + Python — the richest format
PicoScenes' own `.csi` container is self-describing ("versioned-segment", forward
compatible), and it is the only mainstream format carrying **802.11ax up to
160 MHz** (AX210/AX200) and QCA9300 arbitrary-carrier/baseband captures, plus
USRP/HackRF SDR CSI. PMT parses these with a drag-and-drop MATLAB workflow; a
Python interface exists, and both `csiread.Picoscenes` and CSIKit can read the
format for pure-Python pipelines. If your capture side is PicoScenes, prefer PMT
(or the vendor Python parser) as the reference decoder and treat the others as
convenience readers. Free for academic use; distributed with the platform via
Debian packaging. See [../projects/csi-toolchains.md](../projects/csi-toolchains.md)
and the PicoScenes docs. **Status: verified** for hardware/format coverage;
PMT itself is closed-source.

### SenseFi — the DL benchmark (PyTorch, *analysis not parsing*)
Not a parser: SenseFi ingests **already-parsed** CSI tensors and provides a
reproducible benchmark of sensing models — MLP, LeNet, ResNet-18/50/101, RNN/GRU/
LSTM/BiLSTM, CNN+GRU, and ViT — over four public datasets: UT-HAR (`1×250×90`),
NTU-Fi HAR and HumanID (`3×114×500`), and Widar in `22×20×20` BVP form. Use it to
sanity-check a new dataset against known baselines or to lift a backbone for your
own task. PyTorch ≥1.12, MIT-licensed; published in *Patterns* (Cell Press, 2023).
**Status: verified.**

### Widar3.0 BVP toolset — domain-independent features (MATLAB)
The pipeline behind cross-domain gesture recognition: Intel-5300 CSI → **DFS**
(Doppler Frequency Spectrum, 121 bins) → **BVP** (Body-coordinate Velocity Profile,
`20×20`), a feature designed to be invariant to room/position/orientation. The
released MATLAB code plus the large labelled dataset (mirrored on IEEE DataPort and
Tsinghua/Baidu disks) are the standard starting point for reproducing BVP-based
work; downstream, the BVP tensors are exactly what SenseFi's "Widar" split
consumes. Research release, effectively static; governed by the dataset's academic
terms. **Status: reported** (code released, minimal ongoing maintenance).

### Intel 5300 CSI Tool MATLAB scripts — the reference nobody replaced
Halperin et al.'s supplementary repo carries the canonical MATLAB decoders,
`read_bf_file.m` (parse the beamforming log) and `get_scaled_csi.m` (undo the
`Nrx×Ntx` 3-bit exponent scaling, AGC and antenna permutation to get properly-
scaled complex CSI). Every later Intel-5300 reader — CSIKit's and csiread's
included — is effectively a re-implementation of these two files, which is why they
remain worth reading even though the repo was **archived read-only in 2020**. If
your amplitudes look wrong, compare against `get_scaled_csi` output. Licensing is
described in the project FAQ. **Status: verified** (canonical, archived).

### Atheros CSI Tool user-space + MATLAB — the QCA9300/AR9580 reference
Yaxiong Xie's user-space package (with `hostapd`, RX/TX utilities and a `matlab/`
folder, e.g. `read_log_file`) is the reference reader for Atheros CSI logs. It
defines the per-tone 10-bit I/Q layout that CSIKit's and csiread's `Atheros`
backends mirror. Documentation lives at the NTU WANDS site. Effectively static;
consult the repo for exact license terms. **Status: reported.**

### gr-ieee802-11 / GNU-Radio route — CSI from a full soft PHY
When you want CSI without trusting a black-box NIC estimator — or you're validating
a Tier-3/4 claim on the SDR side — a GNU Radio 802.11a/g/p receiver such as
`gr-ieee802-11` decodes OFDM from raw IQ and exposes the per-frame channel
estimate / equaliser taps, i.e. CSI derived from a fully open PHY. Slower and
narrower-band than a COTS NIC, but every step is inspectable. See
[../projects/gr-ieee802-11.md](../projects/gr-ieee802-11.md) and
[../projects/openwifi.md](../projects/openwifi.md) for the FPGA-side equivalent.
**Status: verified** (project maintained).

---

## Choosing one

| If you… | Reach for |
|---|---|
| have a mixed pile of `.dat` / `.pcap` / ESP32 CSVs and want it *read now* | **CSIKit** |
| are building a multi-GB training set and care about parse time | **csiread** |
| only ever capture with nexmon and want zero extra deps | **nexcsi** |
| capture with PicoScenes / need 802.11ax 160 MHz or SDR CSI | **PMT** (+ csiread/CSIKit for Python) |
| already have tensors and want model baselines | **SenseFi** |
| need domain-invariant gesture features (BVP/DFS) | **Widar3.0 toolset** |
| must verify scaling/permutation against ground truth | **Intel** / **Atheros** reference MATLAB |
| distrust the NIC's estimator and want an open-PHY CSI | **gr-ieee802-11** |

## Common gotchas

- **Scaling & permutation (Intel):** always run the equivalent of
  `get_scaled_csi`; skipping the exponent/permutation step gives plausible-looking
  but physically wrong amplitudes.
- **Null/pilot/guard subcarriers (nexmon, all OFDM):** the raw array includes DC,
  guard and pilot tones. Zero or drop them (`zero_nulls`/`zero_pilots` in nexcsi,
  helpers in `csiread.utils`) before modelling.
- **Chip/bandwidth argument (nexmon):** the same pcap unpacks differently for
  `43455c0` vs `4358` and for 20/40/80 MHz — pass the right `chip`/`bw`.
- **Phase is dirty:** carrier-frequency offset, sampling-time offset and random
  phase per packet mean raw phase is rarely usable directly; use a sanitisation
  step (linear-fit removal / conjugate-multiplication across antennas).
- **Coordinate the reader with the capture build:** a parser only matches the
  firmware/patch that produced the file — keep capture and parse versions paired,
  and cross-check against the walkthrough in
  [../docs/walkthroughs/nexmon-csi-to-usable-csi.md](../docs/walkthroughs/nexmon-csi-to-usable-csi.md).

## References

- CSIKit — https://github.com/Gi-z/CSIKit · https://pypi.org/project/CSIKit/
- csiread — https://github.com/citysu/csiread · https://csiread.readthedocs.io/
- nexcsi — https://github.com/nexmonster/nexcsi
- PicoScenes platform & MATLAB Toolbox — https://ps.zpj.io/
- SenseFi / WiFi-CSI-Sensing-Benchmark — https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark · paper (*Patterns*, 2023) https://doi.org/10.1016/j.patter.2023.100703
- Widar3.0 — http://tns.thss.tsinghua.edu.cn/widar3.0/
- Intel 5300 802.11n CSI Tool — https://github.com/dhalperi/linux-80211n-csitool-supplementary · https://dhalperi.github.io/linux-80211n-csitool/
- Atheros CSI Tool (user-space) — https://github.com/xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP · https://wands.sg/research/wifi/AtherosCSI/
- gr-ieee802-11 — https://github.com/bastibl/gr-ieee802-11
