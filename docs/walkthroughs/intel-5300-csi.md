# The Intel 5300 802.11n CSI Tool, Start to Finish

> The 2011 Halperin *Tool Release* is the paper that launched Wi-Fi channel-state-information (CSI) research. More than a decade later the **Linux 802.11n CSI Tool** (`dhalperi/linux-80211n-csitool`) is still the reference implementation, the one against which every newer extractor — Atheros CSI Tool, Nexmon CSI, PicoScenes, ESP32-CSI — is measured. This walkthrough takes you end-to-end: sourcing an IWL5300, flashing the custom firmware, building the patched `iwlwifi` driver, wiring up the netlink `log_to_file` logger, running an active injection measurement, and parsing the resulting `.dat` in MATLAB/Octave down to the exact bit layout — including the AGC/RSS scaling quirks and the "effective SNR" that most people get wrong.

This is a **Tier-2 SDR** exercise on the [SDR ladder](../taxonomy.md): the IWL5300 hands you calibrated, per-subcarrier complex channel state, but not raw IQ. See the [Intel vendor overview](../../chips/intel.md) for where the `intel-iwl5300` record sits in the catalog, and [CSI toolchains](../../projects/csi-toolchains.md) / [PicoScenes](../../projects/picoscenes.md) for the modern ecosystem this seeded.

---

## 1. What you actually get (and what you don't)

The IWL5300 is a 3×3 MIMO 802.11n NIC. The stock firmware reports beamforming feedback internally; Halperin et al. patched the firmware and driver to **export that beamforming report to userspace** as a channel matrix. Concretely, per received 802.11n (HT-rate) frame you get:

| Property | Value |
|---|---|
| Subcarrier groups | **30** — ~1 group per 2 subcarriers at 20 MHz, ~1 per 4 at 40 MHz (not all 56/114 OFDM tones) |
| Matrix shape | `Ntx × Nrx × 30` complex entries |
| Per-entry resolution | signed **8-bit** real + signed **8-bit** imaginary |
| Antennas | up to 3 RX chains, up to 3 TX streams |
| Side channel | per-antenna RSSI (`rssi_a/b/c`), AGC gain, noise floor, RX-chain permutation, NIC 1 MHz timestamp, rate/flags |

**What it is:** a quantized, gain-normalized estimate of the complex frequency response `H(f)` between each TX/RX antenna pair, at 30 frequency points across the channel. Enough for localization, activity/gesture recognition, respiration sensing, rate adaptation research, and MIMO channel studies.

**What it is not:**
- **Not raw IQ.** You cannot recover the time-domain waveform or arbitrary signals. This is a decoded 802.11n channel estimate, nothing else.
- **Only 30 of the subcarriers**, and only for frames the NIC *successfully decodes* at an HT rate.
- **CSI on encrypted links is unavailable.** Per the project FAQ, the 5300 firmware "did not have enough code room for both the beamforming software paths (required to measure CSI) and the encryption software paths." Measure on open networks or in monitor+injection mode.
- **Absolute phase is not trustworthy** across packets: CFO, sampling-time offset (STO/SFO), and per-packet random phase offsets corrupt it. Amplitude is far more stable than phase; phase-based work must sanitize (linear-fit detrending, antenna-pair conjugate multiplication, etc.).
- The internal reference the firmware normalizes against means **raw CSI has no absolute scale** — you must call `get_scaled_csi()` (see §7) to get physically meaningful units.

---

## 2. Sourcing the hardware

### The card

You need an **Intel WiFi Link 5300** — and *only* the 5300. The custom firmware image is 5300-specific; it will not load on a 5100/5150, 6200/6300, or anything newer. Common markings:

| Part number | Form factor | Notes |
|---|---|---|
| **533AN_HMW** | Half-height Mini PCIe | Most common; fits modern half-size Mini PCIe slots |
| **533AN_MMW** | Full-height Mini PCIe | Older full-size slot |
| Sometimes sold as "5300AGN" / "Ultimate-N 5300" | — | Same silicon |

These are cheap and plentiful on the used market (eBay/Amazon, pulled from ~2009–2011 laptops). The 5300 has **three antenna u.FL connectors** — for 3×3 CSI you want all three connected. Many laptops only route two antennas; add a third pigtail + antenna if you want full 3-stream measurements.

### The host laptop

Any machine with a Mini PCIe (not M.2) WLAN slot works. Classic choices from the era, known to accept the 5300 without a BIOS whitelist fight, or where the whitelist is easily patched:

- **Lenovo ThinkPad X200 / X201 / T400 / T410 / T510 / W510 / X301** — extremely common CSI-tool hosts. (Note: some ThinkPads enforce a WLAN card *whitelist* in BIOS; the X200/X201 generation generally accepts the 5300, and community BIOS patches exist otherwise.)
- Many 2009–2012 Dell/HP/Acer laptops with Mini PCIe WLAN.

If your only machine is modern (M.2-only), use a **Mini PCIe → USB or Mini PCIe → M.2 A/E-key adapter**, or better, keep a dedicated old laptop / SBC as the CSI node. Two nodes (one TX, one RX) is the standard active-measurement setup.

> Cross-reference: see the [hardware index](../../chips/hardware-index.md) for form-factor and adapter notes shared across the catalog.

---

## 3. Choosing your software path

There are two realistic routes in 2026:

1. **Period-appropriate kernel (original repo).** The upstream `dhalperi` driver targets **upstream kernels 3.2 → 4.2** (Ubuntu 12.04 through ~15.04). This is the cleanest, best-documented path — spin up an old Ubuntu in a VM-with-PCI-passthrough or on the old laptop directly.
2. **Modern fork.** `spanev/linux-80211n-csitool` backports the patches to **kernel 4.15** (tested on Ubuntu 16.04 / 18.04). Beyond ~4.15 the `iwldvm` internals diverge enough that maintaining the patch is painful; most people running "today" pin to 18.04/4.15 in a container or an old install.

The **firmware and the userspace tools (netlink logger + MATLAB parsers) are unchanged** across both routes — only the kernel driver patch differs. Everything below uses the original repo layout; substitute the `spanev` fork's clone URL and check out its branch if you're on 4.15.

> Reality check: don't expect this to build cleanly on a 6.x kernel. If you're on a current distro, the pragmatic move is a dedicated 18.04 install (or a privileged container with the host running an 18.04-era kernel and the card passed through). The `iwldvm` driver this depends on was removed/heavily changed upstream.

---

## 4. Install: firmware + driver + logger

Prereqs (Debian/Ubuntu):

```bash
sudo apt-get update
sudo apt-get install gcc make linux-headers-$(uname -r) git-core iw
```

Stop NetworkManager from fighting you over the interface (adjust `wlan0`):

```bash
echo "iface wlan0 inet manual" | sudo tee -a /etc/network/interfaces
sudo service network-manager restart   # or: sudo restart network-manager on upstart
```

### 4.1 Build the patched iwlwifi driver

The repo tags branches per kernel minor version (`csitool-3.13`, `csitool-4.2`, …). Pick the tag matching your running kernel:

```bash
CSITOOL_KERNEL_TAG=csitool-$(uname -r | cut -d . -f 1-2)
git clone https://github.com/dhalperi/linux-80211n-csitool.git
cd linux-80211n-csitool
git checkout ${CSITOOL_KERNEL_TAG}

# Build only the iwlwifi tree as an out-of-tree module against your running kernel
make -C /lib/modules/$(uname -r)/build M=$(pwd)/drivers/net/wireless/iwlwifi modules

sudo make -C /lib/modules/$(uname -r)/build \
     M=$(pwd)/drivers/net/wireless/iwlwifi \
     INSTALL_MOD_DIR=updates modules_install
sudo depmod
```

(On the `spanev` fork, clone `https://github.com/spanev/linux-80211n-csitool.git` instead and check out its master; it targets 4.15.)

### 4.2 Install the custom firmware

The 5300 loads `iwlwifi-5000-*.ucode`. Replace the stock ucode with the SIGCOMM CSI firmware from the supplementary repo. **Back up the originals first** so you can restore normal Wi-Fi:

```bash
git clone https://github.com/dhalperi/linux-80211n-csitool-supplementary.git

# Back up whatever 5000-series ucode the distro shipped
for f in /lib/firmware/iwlwifi-5000-*.ucode; do sudo mv "$f" "$f.orig"; done

# Install and symlink the CSI firmware to the name the driver requests
sudo cp linux-80211n-csitool-supplementary/firmware/iwlwifi-5000-2.ucode.sigcomm2010 /lib/firmware/
sudo ln -s iwlwifi-5000-2.ucode.sigcomm2010 /lib/firmware/iwlwifi-5000-2.ucode
```

> The driver requests a specific API version of the 5000 ucode (`iwlwifi-5000-N.ucode`). If your driver asks for a different `N`, symlink the sigcomm image to that name. `dmesg | grep iwlwifi` shows exactly which file it tried to load.

### 4.3 Build the netlink logger

CSI records are shipped from the kernel to userspace over a **Netlink connector** channel; `log_to_file` drains it to a `.dat`:

```bash
make -C linux-80211n-csitool-supplementary/netlink
```

### 4.4 Load and smoke-test

```bash
sudo modprobe -r iwlwifi mac80211
sudo modprobe iwlwifi connector_log=0x1     # 0x1 enables the CSI connector log
dmesg | tail -20                            # confirm the sigcomm2010 ucode loaded, no errors
```

`connector_log=0x1` is the module parameter that turns on CSI export. Confirm the interface exists (`ip link`, `iw dev`).

---

## 5. Passive capture (associated / monitor)

Simplest sanity check: associate to (or just listen near) an **open** 802.11n network on the same channel and log whatever HT frames the NIC decodes.

```bash
sudo linux-80211n-csitool-supplementary/netlink/log_to_file /tmp/csi.dat
# ...generate/receive some 802.11n traffic (ping the AP, load a page)...
# Ctrl-C to stop
ls -l /tmp/csi.dat     # should be non-empty and growing during traffic
```

Remember: no CSI on encrypted frames, and only for frames decoded at an **HT (802.11n) rate**. If the link falls back to legacy 802.11a/g rates you'll get nothing. This is exactly why the canonical workflow uses **injection** — it gives you deterministic HT frames at a rate you control.

---

## 6. Active measurement: monitor + injection

The classic setup is **two nodes**: a transmitter injecting HT frames at a fixed rate, and a receiver in monitor mode logging CSI for each. The supplementary repo's `injection/` directory has the scripts.

### Receiver (the CSI node)

```bash
cd linux-80211n-csitool-supplementary/injection
sudo ./setup_monitor_csi.sh 64 HT20        # channel 64, HT20; use your channel/bandwidth
sudo ../netlink/log_to_file /tmp/rx_csi.dat
```

`setup_monitor_csi.sh` puts the interface in monitor mode and tunes it to the given channel/bandwidth (via `iw`).

### Transmitter (the injector)

```bash
cd linux-80211n-csitool-supplementary/injection
sudo ./setup_inject.sh 64 HT20             # same channel/bandwidth as the RX

# Force the injection (monitor TX) rate. The debugfs node moves between
# kernel versions, so locate it dynamically rather than hardcoding a path:
echo 0x4101 | sudo tee $(find /sys/kernel/debug -name monitor_tx_rate)

# random_packets <count> <delay_us> <?>  -- inject N HT frames
sudo ./random_packets 1 100 1
```

The `monitor_tx_rate` value is an Intel rate/flags word. `0x4101`-style values select an HT rate with a chosen number of spatial streams/antennas; the **number of TX streams you inject determines `Ntx`** in the resulting records (inject with 1/2/3 antennas to measure 1×3, 2×3, 3×3 channels). The high bits are the HT-rate and antenna-selection flags interpreted by the 5300 firmware — consult `setup_inject.sh` and the repo issues for the exact encoding for your desired stream count.

You can also flip TX and RX roles or run bidirectionally. Each side runs its own `log_to_file`.

> ### ⚠️ Safety & regulatory note — you are transmitting
> Injection is **active RF transmission**. You are legally responsible for it. Only inject on frequencies/power you're licensed to use: in most of the world the 2.4 GHz and parts of 5 GHz ISM/U-NII bands are license-exempt **for compliant devices**, but raw injection bypasses the normal regulatory/DFS logic. Concretely:
> - **Avoid DFS/radar channels.** The 5300 AP/IBSS/monitor paths do **not** implement radar detection; injecting on radar-required channels can be illegal and disruptive. Prefer non-DFS channels (e.g. 2.4 GHz ch 1/6/11, or U-NII-1 ch 36–48 where permitted).
> - Keep TX power low, use a shielded/quiet setup, and don't jam nearby production Wi-Fi.
> - Injection into an operational network you don't own may violate local law. Use your own isolated link.

---

## 7. Parsing the `.dat`: bit layout, scaling, effective SNR

The MATLAB/Octave parsers live in `linux-80211n-csitool-supplementary/matlab/`. Core flow:

```matlab
csi_trace = read_bf_file('/tmp/rx_csi.dat');   % cell array, one struct per CSI record
csi_entry = csi_trace{1};
csi       = get_scaled_csi(csi_entry);         % Ntx x Nrx x 30 complex, scaled to unit noise
```

### 7.1 The record struct (from `read_bfee.c`)

Each record parsed by `read_bfee.c` / `read_bf_file.m` has these fields — **locate the exact byte layout in `read_bfee.c` in your checkout rather than trusting any hardcoded offset here**, since it's the authoritative source:

| Field | Meaning |
|---|---|
| `timestamp_low` | Low 32 bits of the NIC's **1 MHz** clock; wraps ~every 4300 s (~72 min) |
| `bfee_count` | Running count of beamforming records the driver has seen |
| `Nrx` | Number of RX antennas represented |
| `Ntx` | Number of TX antennas / spatial streams (set by the injector's rate) |
| `rssi_a`, `rssi_b`, `rssi_c` | Per-RX-chain RSSI, in dB relative to an internal reference (before AGC removal) |
| `noise` | Noise-floor estimate (dBm); `-127`/absent in monitor mode → treated as `-92 dBm` |
| `agc` | AGC gain applied, in dB |
| `perm` | How the NIC permuted the 3 antennas into the 3 RF chains, e.g. `[3 2 1]` = antenna C→chain A, B→B, A→C (usually decreasing RSSI order) |
| `rate` | The rate/flags word the frame was sent at |
| `csi` | `Ntx × Nrx × 30` complex matrix, raw (unscaled) 8-bit values |

**Bit layout of the CSI payload** (again, read it from `read_bfee.c`): the payload is bit-packed, not byte-aligned. For each of the 30 subcarrier groups the firmware emits a **3-bit** gap, then `Nrx×Ntx` complex samples, each an **8-bit signed real** followed by an **8-bit signed imaginary** (16 bits/sample). The parser walks a bit index, reconstructing each byte that straddles a byte boundary as `(payload[idx/8] >> rem) | (payload[idx/8 + 1] << (8 - rem))`. The expected payload length is `(30 * (Nrx*Ntx*8*2 + 3) + 7) / 8` bytes — `read_bfee.c` checks this and warns on mismatch (a good corruption sanity check).

### 7.2 Why you must call `get_scaled_csi()`

The raw `csi` matrix is normalized to an **internal firmware reference** — it carries relative shape but no absolute magnitude. `get_scaled_csi.m` converts it to a proper channel matrix `H` in **linear voltage units, normalized so noise has unit power** (i.e., the output magnitude² is effectively an SNR). It does this by:

1. Computing total received signal power from the RSSIs. `get_total_rss.m` sums the per-chain RSSIs in the linear domain (`dbinv(rssi_a) + …`), converts back to dB, then subtracts a **magic constant of 44** *and* the `agc` value: `db(rssi_mag,'pow') - 44 - agc`. That constant + AGC subtraction is the calibration that turns the relative RSSI into an absolute received-power figure in dBm. (This is the "subtract a magic constant" the FAQ warns about — don't reinvent it, call `get_total_rss`.)
2. Scaling the raw CSI so its total power matches that measured RSS (dividing by the mean per-subcarrier CSI power, hence the `/30`).
3. Dividing by the noise power (thermal noise defaulting to **-92 dBm** in monitor mode when `noise == -127`) so the result is in SNR units.
4. Applying a **TX-count correction**: multiply by `√2` for `Ntx=2`, and by `√(dbinv(4.5))` for `Ntx=3`. Note the quirk — Intel (and others) **approximate the factor-of-3 TX power split as 4.5 dB** rather than the exact `10·log10(3) ≈ 4.77 dB`. `get_scaled_csi` faithfully reproduces the NIC's approximation so the scaled CSI matches the hardware's own view. The comments also account for the ±1 quantization error of the 8-bit coefficients (`scale * Nrx * Ntx` of quantization-noise power).

After `get_scaled_csi`, `abs(csi).^2` is (roughly) the per-subcarrier, per-antenna-pair SNR in linear units — that's the whole point.

### 7.3 The "effective SNR" quirk

`get_eff_SNRs.m` collapses the 30-subcarrier channel into a small set of numbers predicting how each 802.11n rate would perform. It returns a **7×4 matrix of effective SNRs in linear (power) space**:

- **4 columns** = modulations **BPSK, QPSK, 16-QAM, 64-QAM**.
- **7 rows** = antenna/spatial-stream selections (the combinations for 1, 2, or 3 spatial streams across the 3 antennas).

The subtlety people miss: **effective SNR is not the mean SNR.** Because a coded OFDM symbol fails if *any* subcarrier is too weak, `get_eff_SNRs` uses a modulation-specific *effective-SNR mapping* (an averaging in BER/capacity space, not linear-power space) to produce a single number that actually predicts packet delivery. Averaging raw per-subcarrier SNRs linearly will **overestimate** performance on frequency-selective channels. Use `get_eff_SNRs` (per the SIGCOMM 2010 "Predictable 802.11 Packet Delivery" methodology), not `mean(abs(csi).^2)`, when you want a delivery/rate prediction.

### 7.4 Octave note

The parsers are plain enough to run under **GNU Octave** (free) as well as MATLAB — handy for scripted/headless pipelines. `read_bf_file` depends on the compiled `read_bfee` MEX (`mex read_bfee.c` in MATLAB, or `mkoctfile --mex read_bfee.c` under Octave).

---

## 8. Expected output & verification

A healthy capture looks like:

```matlab
>> csi_trace = read_bf_file('/tmp/rx_csi.dat');
>> length(csi_trace)              % number of CSI records logged
ans = 1287
>> e = csi_trace{100}
   e.Nrx = 3, e.Ntx = 1, e.rate = ..., e.perm = [3 2 1]
>> size(get_scaled_csi(e))
ans =  1  3  30                   % Ntx x Nrx x 30
```

Verification checklist:

- `dmesg` shows `iwlwifi-5000-2.ucode.sigcomm2010` loaded with no firmware/API-mismatch errors.
- `/tmp/*.dat` grows only while HT traffic is present.
- `Nrx == 3` (all three antennas connected) and `Ntx` matches the stream count you injected.
- `perm` is a permutation of `[1 2 3]` (not garbage) — a corrupted stream shows impossible perms/length warnings from `read_bfee`.
- Plot `db(abs(squeeze(get_scaled_csi(e))).')` across the 30 subcarriers — you should see a smooth-ish frequency-selective curve, not noise, when a real link is present.

---

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `.dat` stays empty | No HT frames decoded. Confirm open network / injection is on the **same channel + bandwidth**; confirm `connector_log=0x1` was set on modprobe. |
| Firmware fails to load in `dmesg` | The driver requested a different `iwlwifi-5000-N.ucode` API number. Re-point the symlink to the requested `N`. |
| Driver won't build | Wrong `csitool-X.Y` tag for your kernel, or kernel too new. Pin to a supported kernel (≤4.2 upstream, or 4.15 on the `spanev` fork). |
| `monitor_tx_rate` path not found | Mount debugfs (`sudo mount -t debugfs none /sys/kernel/debug`) and re-run the `find`. Path moves between kernels — never hardcode it. |
| No CSI on your home Wi-Fi | It's encrypted. The 5300 CSI firmware can't do CSI + crypto. Use an open AP or injection. |
| Only `Nrx == 2` | Third antenna not connected/routed. Add the third u.FL pigtail + antenna. |
| Card not detected / BIOS error | Laptop WLAN whitelist. Use a whitelist-free machine (e.g. ThinkPad X200/X201) or a Mini PCIe adapter. |
| Can't associate as AP on 5 GHz | Expected — the firmware has no DFS/radar detection; AP/IBSS on radar channels is unsupported. |

---

## 10. Where to go next

- **Modern extractors** compared in [CSI toolchains](../../projects/csi-toolchains.md): Atheros CSI Tool (114 subcarriers, ath9k — see the [ath9k spectral/CSI walkthrough](./atheros-ath9k-spectral-csi.md)), **Nexmon CSI** (Broadcom, up to 256 tones on 80 MHz), **PicoScenes** (unifies 5300 + Atheros + modern chips — see [PicoScenes](../../projects/picoscenes.md)), and ESP32-CSI.
- **Public datasets** built on the 5300 are cataloged in [Wi-Fi sensing datasets](../../projects/wifi-sensing-datasets.md).
- **Phase-sanitization and sensing techniques** (linear detrending, conjugate-multiplication, Hampel filtering) in [techniques](../techniques.md).
- Where the 5300 sits on the capability ladder vs. true SDRs: [true-SDR comparison](../true-sdr-comparison.md) and the [Intel chip overview](../../chips/intel.md).

---

## References

1. D. Halperin, W. Hu, A. Sheth, D. Wetherall. **"Tool Release: Gathering 802.11n Traces with Channel State Information."** *ACM SIGCOMM Computer Communication Review* 41(1):53, Jan 2011. https://doi.org/10.1145/1925861.1925870
2. **Linux 802.11n CSI Tool** — project site. https://dhalperi.github.io/linux-80211n-csitool/
3. Installation instructions. https://dhalperi.github.io/linux-80211n-csitool/installation.html
4. FAQ / Things to Know / Troubleshooting (effective SNR, AGC, permutation, encryption limitation). https://dhalperi.github.io/linux-80211n-csitool/faq.html
5. Driver repo: `dhalperi/linux-80211n-csitool`. https://github.com/dhalperi/linux-80211n-csitool
6. Supplementary repo (firmware, `netlink/log_to_file`, `matlab/`, `injection/`): `dhalperi/linux-80211n-csitool-supplementary`. https://github.com/dhalperi/linux-80211n-csitool-supplementary
7. `read_bfee.c` (record struct + bit-unpacking of the 30×Nrx×Ntx matrix). https://github.com/dhalperi/linux-80211n-csitool-supplementary/blob/master/matlab/read_bfee.c
8. `get_scaled_csi.m` (RSS/noise scaling, Ntx `√(dbinv(4.5))` quirk). https://github.com/dhalperi/linux-80211n-csitool-supplementary/blob/master/matlab/get_scaled_csi.m
9. `get_total_rss.m` (RSSI combining, `-44 - agc` calibration constant). https://github.com/dhalperi/linux-80211n-csitool-supplementary/blob/master/matlab/get_total_rss.m
10. Modern kernel fork (4.15 / Ubuntu 18.04): `spanev/linux-80211n-csitool`. https://github.com/spanev/linux-80211n-csitool
11. D. Halperin, W. Hu, A. Sheth, D. Wetherall. **"Predictable 802.11 Packet Delivery from Wireless Channel Measurements"** (effective-SNR methodology). *ACM SIGCOMM* 2010. https://doi.org/10.1145/1851182.1851203
12. Linux kernel docs — mac80211 packet injection semantics. https://docs.kernel.org/networking/mac80211-injection.html
