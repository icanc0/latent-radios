# From nexmon_csi capture to usable CSI

The companion walkthrough, [bcm43455c0-raspberry-pi.md](./bcm43455c0-raspberry-pi.md), ends the moment a `.pcap` lands on disk. That file is *not* channel state information yet — it is a stream of UDP frames each carrying a bit-packed, chip-specific, FFT-ordered block of I/Q values that still contain every hardware impairment the radio introduced. This document is the analysis half: how to unpack that pcap, turn the bytes into per-subcarrier complex numbers, index the subcarriers correctly for 20/40/80 MHz, remove the phase and amplitude artifacts that make raw CSI nearly useless, and end with a reproducible amplitude/phase heatmap.

Everything here is Tier 2 territory on the [SDR ladder](../taxonomy.md): the [BCM43455c0](../../chips/broadcom-cypress.md) is not giving you raw IQ off the antenna, it is giving you the equalizer's view of the channel — one complex gain per OFDM subcarrier per received frame. See [csi-toolchains.md](../../projects/csi-toolchains.md) for how nexmon_csi sits among the other extractors, and [techniques.md](../techniques.md) for what you can *do* with the sanitized result (sensing, ranging, presence detection).

> **Scope note.** The capture side (`makecsiparams`, `nexutil`, `tcpdump -w`) is covered in the Pi walkthrough. This document assumes you already have a `capture.pcap` produced by a nexmon_csi-patched firmware.

---

## 1. What is actually in the pcap

nexmon_csi does not write a custom file format. The patched firmware fabricates ordinary **UDP frames** in the chip and injects them up the network stack; you capture them with `tcpdump`/`libpcap` like any other traffic. So a nexmon_csi pcap is a perfectly normal Ethernet → IPv4 → UDP capture, and each UDP payload is one CSI record.

Frame addressing (as emitted by the firmware):

| Field | Value |
|---|---|
| Source IP | `10.10.10.10` |
| Destination IP | `255.255.255.255` (broadcast) |
| UDP destination port | `5500` |
| Transport | UDP |

### The CSI UDP payload

After the UDP header, the payload is a fixed header followed by the CSI block. Byte layout as produced by current `master` (the "pull-46 / pull-256" generation of the firmware):

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 2 | `magic` | `0x1111` marker |
| 2 | 1 | `rssi` | int8 RSSI of the triggering frame (dBm) |
| 3 | 1 | `fctl` | 802.11 frame-control byte |
| 4 | 6 | `src_mac` | source MAC of the frame that triggered extraction (last bytes used as filter) |
| 10 | 2 | `seq` | 802.11 sequence number |
| 12 | 2 | `core_spatial` | low 3 bits = **core** (RX chain), next 3 bits = **spatial stream** |
| 14 | 2 | `chanspec` | Broadcom chanspec (channel + bandwidth + sideband) |
| 16 | 2 | `chip_version` | chip id, e.g. `0x03bb`-class for 43455c0 |
| 18 | 4·Nfft | `csi` | Nfft complex values, chip-specific packing |

`Nfft` follows the bandwidth: **64** subcarriers for 20 MHz, **128** for 40 MHz, **256** for 80 MHz — four bytes per subcarrier either way. That four-bytes-per-value is the source of endless confusion, because *what those four bytes mean depends on the chip*.

### Two on-wire number formats

nexmon_csi runs on several Broadcom parts and they do not agree on how a complex CSI sample is encoded:

- **Interleaved int16 (raw)** — `bcm43455c0` (Raspberry Pi 3B+/4/Zero 2 W), `bcm4339` (Nexus 5). Each subcarrier is `int16 real, int16 imag`, little-endian. You just reinterpret the bytes as `int16` and pair them. No decompression.
- **Compressed exponent/mantissa float** — `bcm4358` (Nexus 6P, some ASUS), `bcm4366c0` (RT-AC86U). Each 32-bit word packs sign bits plus a mantissa and exponent; the exponent is applied as a bit-shift on the mantissa. Widths differ by chip family (roughly 9-bit mantissa / 5-bit exponent vs. 12-bit mantissa / 6-bit exponent). This is what `utils/matlab/unpack_float.c` in [seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) exists to decode, and it is why you must tell every parser *which chip* produced the file.

The practical consequence: **never** unpack a Nexus-6P/RT-AC86U capture with a "just cast to int16" routine, and never assume a Raspberry Pi capture needs float decompression. Pick the parser mode by chip.

> **Version caveat.** The header layout above is the widely deployed pull-46/pull-256 firmware. Older nexmon_csi commits used a slightly different/shorter header (this is exactly why `csiread` ships both a `Nexmon` class *and* a `NexmonPull46`/`NexmonPull256` class). Match your parser to the firmware commit you flashed. When in doubt, `tcpdump -x` a single packet and confirm the `0x1111` magic lands where you expect.

---

## 2. Unpacking: three toolchains

All three read the pcap directly — you do not pre-process with Wireshark.

### nexcsi (fastest to first plot)

[nexmonster/nexcsi](https://github.com/nexmonster/nexcsi) is a small, dependency-light NumPy library. You select a **device** (which encodes both the chip's number format and its null/pilot subcarrier tables) and get a structured array back:

```python
from nexcsi import decoder

device = "raspberrypi"           # also: nexus5, nexus6p, rtac86u
samples = decoder(device).read_pcap("capture.pcap")

# samples is a NumPy structured array:
#   samples['rssi'], samples['fctl'], samples['mac'],
#   samples['seq'], samples['core'], samples['spatial'],
#   samples['chan_spec'], samples['chip_version'], samples['csi'] (raw)

# Decode raw CSI -> complex64, shape (n_packets, Nfft):
csi = decoder(device).unpack(samples['csi'])

# Optionally zero the subcarriers that carry no usable channel info:
csi = decoder(device).unpack(samples['csi'], zero_nulls=True, zero_pilots=True)
```

The null/pilot subcarrier index tables live in the dtype metadata, so you can also *delete* those columns rather than zero them:

```python
import numpy as np
nulls  = csi.dtype.metadata['nulls']
pilots = csi.dtype.metadata['pilots']
csi = np.delete(csi, csi.dtype.metadata['nulls'],  axis=1)  # order matters; see §4
```

### csiread (fast C core, batch pipelines)

[citysu/csiread](https://github.com/citysu/csiread) is a Cython-accelerated reader with a uniform API across Intel/Atheros/nexmon. For nexmon you name the chip and bandwidth explicitly:

```python
import csiread

csidata = csiread.Nexmon("capture.pcap", chip="43455c0", bw=80)
csidata.read()
csi = csidata.csi          # complex, shape (n_packets, Nfft)
# csidata.rssi, csidata.fc, csidata.seq, csidata.core, csidata.spatial ...
```

For current `master` firmware use the pull variant, which tracks the newer header:

```python
csidata = csiread.NexmonPull46("capture.pcap", chip="43455c0", bw=80)   # a.k.a. NexmonPull256
csidata.read()
```

`csiread` also exposes `seek()` / `pmsg()` for streaming and huge files, and `display(i)` to dump one record for sanity checks. (Its `Nexmon.group` for reshaping by core/spatial stream is documented as experimental — verify against your own capture.)

### SEEMOO MATLAB (reference implementation)

The `utils/matlab/` folder of [seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) is the canonical reference. `csireader.m` parses the pcap, and the `unpack_float` MEX (compiled from `unpack_float.c`) decompresses the exponent/mantissa format for the 4358/4366c0. If a Python result looks wrong, this is the ground truth to diff against.

---

## 3. From bytes to a channel: the complex value

After unpacking, `csi[p, k]` is one complex number: the estimated channel gain `H = a·e^{jφ}` at packet `p`, subcarrier `k`, for a single (core, spatial-stream) pair.

- **Amplitude** `|H|` = `np.abs(csi)` — how much that subcarrier was attenuated. Sensitive to multipath and to the receiver's AGC (see §6).
- **Phase** `∠H` = `np.angle(csi)` — the propagation phase, but buried under carrier/sampling/timing offsets (see §5) and wrapped to `(-π, π]`.

A single record from a 20 MHz Pi capture is a length-64 complex vector. Stack `n_packets` of them and you have an `n_packets × 64` matrix — a spectrogram-like object with subcarriers on one axis and time (packets) on the other. That matrix is what the rest of this document cleans up.

**One capture mixes RX chains and streams.** The `core` and `spatial` fields tell you which RX antenna/stream each record belongs to. Always separate them before analysis — do not average a core-0 record with a core-1 record. A typical first step:

```python
core0 = csi[(samples['core'] == 0) & (samples['spatial'] == 0)]
```

---

## 4. Subcarrier indexing (20 / 40 / 80 MHz)

This is where most silent errors happen. The unpacked columns come out in **FFT-bin order** (bin 0 = DC first, then positive, then wrapped negative frequencies). Human subcarrier indices run **−Nfft/2 … +Nfft/2−1** with DC at 0. Convert with an `fftshift` along the subcarrier axis:

```python
import numpy as np
csi = np.fft.fftshift(csi, axes=1)      # now column j -> subcarrier (j - Nfft/2)
```

After the shift, column `j` is subcarrier index `k = j − Nfft/2`. Now the standard 802.11 OFDM null/pilot tables apply. These are the values nexcsi encodes in its metadata (they follow the VHT subcarrier plan):

| Bandwidth | Nfft | Subcarrier range | DC / guard **nulls** | **Pilots** |
|---|---:|---|---|---|
| 20 MHz | 64 | −32 … +31 | ±{29,30,31,32-edge}, DC 0 → indices −32,−31,−30,−29, 0, +29,+30,+31 | ±7, ±21 |
| 40 MHz | 128 | −64 … +63 | −64…−59, −1,0,+1, +59…+63 | ±11, ±25, ±53 |
| 80 MHz | 256 | −128 … +127 | −128…−123, −1,0,+1, +123…+127 | ±11, ±39, ±75, ±103 |

Notes that bite people:

- **DC null width grows with bandwidth.** 20 MHz nulls only subcarrier 0; 40/80 MHz null the three center bins {−1, 0, +1}. The DC tone always carries LO leakage, never channel info — drop it.
- **Guard bands are hard zeros.** Edge subcarriers are unmodulated. Their "CSI" is noise/near-zero; keeping them wrecks any normalization that divides by amplitude.
- **Pilots are modulated but with a known reference,** so their phase behaves differently from data subcarriers. Exclude them from phase detrending unless you are specifically using them as references.
- **Deletion order.** If you `np.delete` nulls and pilots, delete against the *original* index set in one call (as nexcsi's metadata provides) or delete the higher indices first — otherwise the second delete operates on shifted columns. Zeroing (`zero_nulls`/`zero_pilots`) sidesteps this and keeps a fixed 64/128/256 width, which is friendlier for stacking into a matrix.

For a first analysis, keep the **data subcarriers only** (56 for 20 MHz, 108 for 40 MHz, 234 for 80 MHz once pilots are also removed) and remember the index-to-frequency map: subcarrier spacing is 312.5 kHz, so subcarrier `k` sits at `f_center + k·312.5 kHz`.

---

## 5. Phase sanitization

Raw CSI phase is almost never usable as-is. Three offsets dominate, all of which the transmitter/receiver introduce and none of which relate to the physical channel:

- **CFO — Carrier Frequency Offset.** TX and RX local oscillators are never identical. Residual CFO after the receiver's correction rotates the *entire* subcarrier vector by a constant phase that also drifts packet-to-packet. Appears as a per-packet phase **offset** (constant across `k`).
- **SFO — Sampling Frequency Offset.** ADC/DAC clocks differ, so the FFT window is sampled slightly off. This produces a phase **slope** that is linear in subcarrier index `k`.
- **PDD / STO — Packet Detection Delay / Symbol Timing Offset.** The receiver picks a frame-start sample that is off by an integer number of samples; a timing shift of `τ` in the time domain is a linear phase ramp `−2π k Δf τ` in the frequency domain. Also linear in `k`, and it changes every packet, so it dominates packet-to-packet phase jitter.

Because SFO and PDD are both **linear in `k`** and CFO is a **constant in `k`**, the classic remedy (Halperin's linear transformation, reused throughout the CSI-sensing literature) is: unwrap, fit a line across subcarriers, and subtract it. What survives is the *relative* phase across subcarriers with the linear and constant nuisance terms removed.

```python
import numpy as np

def sanitize_phase(csi_row, sc_index):
    """csi_row: complex vector for one packet (data subcarriers only).
       sc_index: matching signed subcarrier indices (e.g. -28..-1,1..28)."""
    phase = np.unwrap(np.angle(csi_row))          # undo (-pi, pi] wrapping
    # Least-squares line phase ~ a*k + b  (a: SFO+STO slope, b: CFO offset)
    a, b = np.polyfit(sc_index, phase, 1)
    return phase - (a * sc_index + b)             # detrended, relative phase

sc = np.arange(-28, 29); sc = sc[sc != 0]         # 20 MHz data subcarriers, DC removed
clean = np.array([sanitize_phase(row, sc) for row in csi_data])
```

Caveats and alternatives:

- **Unwrap before fitting**, always. A `polyfit` on wrapped phase fits garbage. And unwrap *per packet*, along the subcarrier axis — not across time.
- **Linear detrending destroys absolute ToF.** The slope you subtract *is* the time-of-flight signature. If you are doing ranging/FTM-style work, do not blindly detrend — see [ftm-rtt-ranging.md](../ftm-rtt-ranging.md).
- **CSI ratio / conjugate multiplication** is the robust alternative when you have ≥2 RX chains (which the Pi's single-antenna 43455c0 does not, but multi-antenna parts do). Because CFO/SFO/PDD are shared across cores that ride the same RF LO/clock, multiplying one core's CSI by the conjugate of another's cancels the common offsets without any fitting. This is the basis of many robust sensing pipelines and avoids the ToF-destroying assumption above.
- **Wrap-around at guard edges.** Include only contiguous data subcarriers in the fit; feeding the fit across the DC gap or into near-zero guard bins skews the slope.

---

## 6. Amplitude calibration

nexmon_csi amplitude is **relative, not absolute**. There is no calibrated conversion to received power at the antenna connector. The dominant artifact is the receiver's **AGC (automatic gain control)**: between frames the AGC changes the front-end gain, so `|H|` for one packet can be several dB above or below the next even with an unchanged channel. Raw amplitude therefore shows step changes that are receiver behavior, not channel.

Practical calibration steps, cheapest first:

- **Per-packet normalization.** Divide each packet's amplitude vector by its own mean (or L2 norm) across data subcarriers. Removes packet-to-packet AGC/gain steps, keeps the *shape* of the frequency response — usually enough for sensing.
- **RSSI referencing.** The header `rssi` (int8, dBm) is the AGC's own power estimate for that frame. Scaling CSI amplitude by `10**(rssi/20)` re-imposes a coarse absolute reference so packets are comparable, at the cost of RSSI's own quantization/noise.
- **Guard/null exclusion.** Compute any normalization statistic over data subcarriers only. Including near-zero guard bins pulls the mean down and injects noise.
- **Compressed-float autoscale.** For 4358/4366c0, the exponent/mantissa unpack has an autoscale option; be consistent (same scaling for every packet) or you re-introduce a per-packet gain step exactly like the AGC problem.
- **Amplitude denoising.** A short moving-average or Hampel filter across time per subcarrier removes impulsive AGC glitches; a low-pass across the subcarrier axis smooths measurement noise but blurs sharp nulls — pick per task.

For most people the honest summary is: **normalize amplitude per packet, sanitize phase per packet, then work with the cleaned matrix.** Absolute-power claims from nexmon CSI should be treated with suspicion.

---

## 7. Common artifacts checklist

Before trusting a plot, confirm each of these:

- **Null subcarriers are zeros.** Guard bands + DC come out as ~0. Zero (not remove) if you need a fixed-width matrix; remove if downstream code expects only data subcarriers. Never divide by them.
- **The DC tone spikes.** LO leakage makes the center subcarrier(s) an outlier in amplitude and a phase discontinuity. Drop {0} at 20 MHz, {−1,0,+1} at 40/80 MHz.
- **Pilots look "different."** Their phase/amplitude follows a known reference, not the data. Exclude from detrending; expect them to stand out on a heatmap.
- **Mixed cores/streams.** If your heatmap has interleaved "good/bad" rows, you are plotting multiple RX chains stacked together — filter by `core`/`spatial` first (§3).
- **Wrong chip mode.** Structured but nonsensical values (huge integers, or tiny floats) usually mean int16-vs-float mismatch. Re-check the `device`/`chip` argument.
- **Wrong firmware/header generation.** Off-by-a-few-bytes fields (RSSI reading as garbage, magic not at offset 0) mean `Nexmon` vs `NexmonPull46` mismatch.
- **FFT ordering not shifted.** If DC/nulls appear at the *edges* of your subcarrier axis instead of the center, you forgot `fftshift`.
- **Dropped/duplicated packets.** UDP over the capture path can drop frames under load; sequence numbers are non-monotonic gaps, not evenly spaced time. Do not assume a constant sample rate — use arrival order, or timestamp if you need real time.

---

## 8. Minimal end-to-end: amplitude & phase heatmap

Reproducible from a single Raspberry Pi (43455c0) 20 MHz capture. Requires `pip install nexcsi numpy matplotlib`.

```python
import numpy as np
import matplotlib.pyplot as plt
from nexcsi import decoder

DEVICE = "raspberrypi"        # 43455c0 -> interleaved int16
PCAP   = "capture.pcap"

# 1. Read + unpack to complex64, zeroing nulls & pilots.
samples = decoder(DEVICE).read_pcap(PCAP)
csi = decoder(DEVICE).unpack(samples['csi'], zero_nulls=True, zero_pilots=True)

# 2. One RX chain only (Pi is single-core, but be explicit).
if 'core' in samples.dtype.names:
    sel = samples['core'] == 0
    csi = csi[sel]

# 3. FFT-shift so DC is centered: column j -> subcarrier j - Nfft/2.
Nfft = csi.shape[1]                       # 64 for 20 MHz
csi = np.fft.fftshift(csi, axes=1)
sc_index = np.arange(-Nfft // 2, Nfft // 2)

# 4. Data-subcarrier mask (drop the zeros we planted).
data_mask = ~np.all(csi == 0, axis=0)     # columns that are all-zero are nulls/pilots
csi_d   = csi[:, data_mask]
sc_d    = sc_index[data_mask]

# 5. Amplitude: per-packet normalization to kill AGC steps.
amp = np.abs(csi_d)
amp = amp / amp.mean(axis=1, keepdims=True)

# 6. Phase: unwrap + linear detrend (remove CFO/SFO/PDD) per packet.
def sanitize(row, k):
    ph = np.unwrap(np.angle(row))
    a, b = np.polyfit(k, ph, 1)
    return ph - (a * k + b)
phase = np.array([sanitize(r, sc_d) for r in csi_d])

# 7. Heatmaps: subcarrier (x) vs packet/time (y).
fig, ax = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
im0 = ax[0].imshow(amp, aspect='auto', origin='lower',
                   extent=[sc_d[0], sc_d[-1], 0, amp.shape[0]], cmap='viridis')
ax[0].set(title='Normalized amplitude', xlabel='Subcarrier', ylabel='Packet index')
fig.colorbar(im0, ax=ax[0], label='|H| (norm.)')

im1 = ax[1].imshow(phase, aspect='auto', origin='lower',
                   extent=[sc_d[0], sc_d[-1], 0, phase.shape[0]], cmap='twilight')
ax[1].set(title='Sanitized phase', xlabel='Subcarrier')
fig.colorbar(im1, ax=ax[1], label='∠H (rad)')

fig.tight_layout()
fig.savefig("csi_heatmap.png", dpi=150)
```

What a healthy result looks like: the amplitude panel shows smooth frequency-selective fading (bright and dark bands that drift as the channel changes — e.g. someone walking through the link), the null/pilot columns are absent, and the phase panel — after detrending — shows a flat-ish, low-variance field rather than the random ±π confetti you get from raw `np.angle`. If the phase panel is still confetti, your unwrap or fit is running across the wrong axis.

---

## 9. Where this connects

- Capture side and firmware flashing: [bcm43455c0-raspberry-pi.md](./bcm43455c0-raspberry-pi.md).
- nexmon_csi among the other CSI extractors (Atheros CSI Tool, Intel 5300/Halperin, PicoScenes, ESP32-CSI): [csi-toolchains.md](../../projects/csi-toolchains.md).
- What sanitized CSI is *for* — sensing, presence, gesture, ranging: [techniques.md](../techniques.md).
- The BCM43455c0 and its nexmon_csi siblings (4358, 4366c0, 4339): [broadcom-cypress.md](../../chips/broadcom-cypress.md).

## References

- [seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) — the firmware patch, `makecsiparams`, and the MATLAB `utils/` reference decoder (`csireader.m`, `unpack_float`).
- [nexmonster/nexcsi](https://github.com/nexmonster/nexcsi) — NumPy pcap reader/unpacker with per-device null/pilot metadata (`raspberrypi`, `nexus5`, `nexus6p`, `rtac86u`).
- [citysu/csiread](https://github.com/citysu/csiread) — Cython-accelerated multi-format CSI reader; `Nexmon`, `NexmonPull46`/`NexmonPull256` classes for old vs current firmware headers.
- F. Gringoli, M. Schulz, J. Link, M. Hollick, "Free Your CSI: A Channel State Information Extraction Platform for Modern Wi-Fi Chipsets," ACM WiNTECH 2019 — the nexmon_csi paper.
- D. Halperin et al., "Tool Release: Gathering 802.11n Traces with Channel State Information," ACM SIGCOMM CCR 2011 — origin of the linear phase-sanitization transform reused above.
