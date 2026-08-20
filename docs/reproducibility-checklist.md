# Reproducibility checklist for Wi-Fi RF experiments

Wi-Fi sensing and monitor/injection results are notoriously hard to reproduce — a CSI activity-recognition model that hits 98% in one room collapses to guessing in another, and a "works on my card" injection setup fails on a silently-different chip revision. Most of that fragility is *undocumented context*, not bad science. This checklist is the context to capture so someone else (or you, in six months) can actually rerun what you did.

Copy the template at the bottom into your repo's `README` or a `run.yaml` and fill it in per experiment.

## 1. Hardware — pin the exact silicon
- [ ] **Chip + revision**, not just the marketing name. `RTL8812AU` vs `RTL8812BU` behave differently; `BCM43455` vs `BCM43455c0` matters for Nexmon. Record the [FCC ID](https://www.fcc.gov/oet/ea/fccid) if it's a module (it reveals the die — see [wifi-modules-by-integrator.md](wifi-modules-by-integrator.md)).
- [ ] **How you identified it**: `lspci -nn`, `lsusb`, `dmesg | grep -iE 'brcmfmac|ath|mt76|iwlwifi|rtl'`, and the loaded firmware filename.
- [ ] **Host**: SBC/laptop model, CPU arch, USB2 vs USB3 port (USB3 noise and power matter for dongles).
- [ ] **Antennas**: type (omni/patch/Yagi), gain, and physical placement/orientation (for anything spatial — see [antennas-and-rf-frontend.md](antennas-and-rf-frontend.md)).

## 2. Software — pin every version in the stack
- [ ] **Kernel version** (`uname -r`). CSI tools and out-of-tree drivers are kernel-fragile; several ([Intel 5300 tool](walkthroughs/intel-5300-csi.md), Atheros CSI Tool) only run on legacy kernels — see [verification-tier2-csi.md](verification-tier2-csi.md).
- [ ] **Driver**: in-tree name or out-of-tree repo **+ commit hash** (e.g. `morrownr/8812au-20210820 @ <sha>`). "Injection works" often means "with the DKMS driver," not the in-kernel one.
- [ ] **Firmware version string** (e.g. brcmfmac `7_45_189`, iwlwifi `-NN.ucode`). Nexmon CSI is pinned to specific firmware.
- [ ] **Capture/analysis tools + commits**: nexmon_csi, PicoScenes, ESP-IDF version, aircrack-ng, tcpdump, your scripts.

## 3. Environment — describe the RF reality
- [ ] **Location & geometry**: room size, TX/RX positions and separation, a sketch or coordinates for spatial work.
- [ ] **A baseline capture** (empty room / no motion) as the control.
- [ ] **Interference & occupancy**: other APs on-channel, known emitters (microwaves, BT), people present. A [spectral scan](walkthroughs/ath9k-spectral-interference-hunting.md) of the band during capture is gold.
- [ ] **Band/channel/bandwidth** and regulatory domain (`iw reg get`) — DFS and country locks change what's available.

## 4. Procedure — make the capture repeatable
- [ ] **Traffic generation**: CSI needs packets. State exactly how you forced them (`ping -f`, `iperf3 -u -b`, the AP's beacon rate) — sample rate depends on it.
- [ ] **Capture parameters**: channel, bandwidth, `makecsiparams` string (Nexmon), monitor vs injection, duration, packet count.
- [ ] **Ground truth**: how activities/positions were labeled and time-synchronized to the RF capture.
- [ ] **Number of runs / subjects / environments** — single-environment results do not generalize (the [domain-shift problem](honest-limitations-of-wifi-sensing.md)).

## 5. Data — publish it so it's reusable
- [ ] **Format documented**: subcarrier count, antenna/stream layout, complex vs amplitude/phase, endianness, units.
- [ ] **Metadata bundled** with each capture (everything in §1–4), not in a lost email thread. This is the single most-omitted thing in published CSI datasets.
- [ ] **Labels + timestamps** aligned and included.
- [ ] **Calibration state**: raw or sanitized? If sanitized, which method (see [csi-calibration-deep-dive.md](walkthroughs/csi-calibration-deep-dive.md)).
- [ ] A **license** (CC0/CC-BY) and a **checksum**.

## 6. Reporting — claims a reader can check
- [ ] Report accuracy **per environment/subject**, and explicitly the **cross-domain** result (train on A, test on B) — the number that predicts real-world performance.
- [ ] State the **baseline** you beat and the **failure modes** you saw.
- [ ] Provide the code + the exact commands to reproduce, keyed to the versions in §2.

---

## Copy-paste template

```yaml
experiment: <name>
date: <YYYY-MM-DD>
hardware:
  chip: <e.g. BCM43455c0>          # + revision
  fcc_id: <if a module>
  host: <SBC/laptop, arch, USB2/3>
  antennas: <type, gain, placement>
software:
  kernel: <uname -r>
  driver: <repo@commit or in-tree name>
  firmware: <version string>
  tools: [<tool@commit>, ...]
environment:
  location: <room, geometry sketch>
  tx_rx_positions: <coords / separation>
  interference: <APs, emitters, people>
  band_channel_bw: <e.g. 5GHz ch36 80MHz>
  reg_domain: <iw reg get>
procedure:
  traffic: <how packets were forced>
  capture_params: <makecsiparams / monitor / duration / count>
  ground_truth: <labeling + time-sync method>
  runs_subjects_envs: <N / N / N>
data:
  format: <subcarriers x streams, complex?>
  calibration: <raw | method>
  labels: <included? aligned?>
  license: <CC0 / CC-BY>
reporting:
  per_env_accuracy: <...>
  cross_domain_accuracy: <the honest number>
  baseline: <what you compared to>
  code: <repo + commands>
```

See [methodology.md](methodology.md) for how this catalog applies the same discipline to its own claims, and [build-a-reproducible-csi-testbed.md](walkthroughs/build-a-reproducible-csi-testbed.md) for a physical setup that satisfies most of this checklist by construction.
