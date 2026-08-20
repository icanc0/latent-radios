# Atheros ath9k: Spectral Scan + CSI, Hands-On

*Two Tier-2/Tier-3 "SDR-lite" superpowers hiding in cheap, decade-old Atheros
802.11n cards. No firmware patch required for either — the raw-PHY plumbing was
left in the mainline `ath9k` driver (spectral scan) and exposed by a well-known
research driver fork (CSI). This is the reproducible bring-up guide for both.*

> Cross-links: driver/PHY background in
> [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md) ·
> CSI toolchain survey in [../../projects/csi-toolchains.md](../../projects/csi-toolchains.md) ·
> PicoScenes (a modern superset for the QCA9300) in
> [../../projects/picoscenes.md](../../projects/picoscenes.md) ·
> ladder definitions in [../taxonomy.md](../taxonomy.md) ·
> where Tier-4 begins in [../verification-tier4.md](../verification-tier4.md).

---

## 0. TL;DR — what you get and what it costs

| Capability | Ladder rung | Firmware patch? | Cost of card | Public tooling |
|---|---|---|---|---|
| **Spectral scan** (per-bin FFT magnitude of the 20/40 MHz channel) | **Tier 3** (spectral/raw-PHY scan) | **No** — mainline `ath9k`/`ath9k_htc` | ~$8 (AR9271 USB) to ~$25 (AR9380 PCIe) | in-kernel debugfs + `speccy`/`fft_eval` |
| **CSI** (per-subcarrier complex `H` for every received packet) | **Tier 2** (CSI) | **No** — but needs the modified `ath9k` from the Atheros-CSI-Tool | ~$25 (AR9380/QCA9300 PCIe) | Atheros-CSI-Tool driver + `recvCSI` userspace |

Both features are **RX-only** raw-PHY reads. Neither is arbitrary-waveform TX,
so this card stays firmly below Tier 4 — see
[../verification-tier4.md](../verification-tier4.md) for why "reading the PHY" is
not "being an SDR." The value here is that the measurements are *real,
per-subcarrier, and free*.

The two features live in **different driver builds**:

- **Spectral scan** works on a *stock, mainline* kernel (any recent distro) as
  long as the spectral Kconfig symbols are enabled — they are, in essentially
  every distro kernel.
- **CSI** requires you to *replace* `ath9k` with Yaxiong Xie's modified driver.
  You cannot get CSI from the mainline driver. You *can* get spectral scan from
  either.

---

## Part A — Spectral Scan (Tier 3, works on a stock kernel)

### A.1 What the hardware actually reports

Atheros AR92xx/AR93xx PHYs contain a spectral-scan engine that dumps the
**magnitude of each FFT bin** across the current channel: `|i| + |q|` per
subcarrier, **56 bins in HT20** and **128 bins in HT40**. This is not full raw
IQ (you get magnitude, not phase, and it is per-bin, not a continuous stream) —
which is exactly why it scores Tier 3 rather than Tier 4. But it is a genuine
power-spectral-density view of the band, updated in real time, from an $8 card.

Bin counts are fixed in the kernel header
`drivers/net/wireless/ath/spectral_common.h`:

```c
#define SPECTRAL_HT20_NUM_BINS      56
#define SPECTRAL_HT20_40_NUM_BINS   128
```

### A.2 Prerequisites

- A card driven by `ath9k` (PCIe/miniPCIe) or `ath9k_htc` (USB, e.g. the AR9271
  TP-Link TL-WN722N **v1** or Alfa AWUS036NHA — beware later hardware revs that
  quietly switched to Realtek silicon; see
  [../../chips/hardware-index.md](../../chips/hardware-index.md)).
- A kernel built with the spectral Kconfig symbols. On a modern kernel these are:
  - `CONFIG_ATH9K_COMMON_SPECTRAL`
  - `CONFIG_ATH9K_DEBUGFS` (for PCIe cards) and/or `CONFIG_ATH9K_HTC_DEBUGFS`
    (for USB AR9271/AR7010)
- `debugfs` mounted (it is, by default, at `/sys/kernel/debug` — you need root).

Verify the symbols are on in your running kernel:

```bash
# Distro kernels usually ship these =y or =m already
zcat /proc/config.gz 2>/dev/null | grep -i spectral
grep -i spectral /boot/config-$(uname -r)
```

Confirm the debugfs directory exists once the card is up (`phyN` and the
`ath9k` vs `ath9k_htc` subdir name depend on your device):

```bash
sudo mount -t debugfs none /sys/kernel/debug 2>/dev/null   # usually already mounted
ls /sys/kernel/debug/ieee80211/phy0/ath9k/       # PCIe
ls /sys/kernel/debug/ieee80211/phy0/ath9k_htc/   # USB AR9271
```

You should see `spectral_scan_ctl`, `spectral_scan0`, `spectral_count`,
`spectral_period`, `spectral_fft_period`, and `spectral_short_repeat`.

### A.3 The debugfs control surface

Everything lives under `/sys/kernel/debug/ieee80211/phyN/ath9k[_htc]/`:

| File | Meaning |
|---|---|
| `spectral_scan_ctl` | write a **mode** (`disable`/`background`/`manual`/`chanscan`) or `trigger` |
| `spectral_scan0` | **read** the TLV binary FFT samples out of this relayfs file |
| `spectral_count` | how many samples to collect per trigger/channel |
| `spectral_fft_period` | PHY hands an FFT frame to the MAC every `(fft_period+1)*4 µs` |
| `spectral_period` | inter-scan spacing, `period*256*Tclk` (Tclk = 44 MHz HT20 / 88 MHz HT40) |
| `spectral_short_repeat` | `1` = 4 µs short mode, `0` = 204 µs mode |

**The four modes** (write to `spectral_scan_ctl`):

- `disable` — off.
- `background` — endless samples from the current channel during idle time;
  you still write `trigger` to arm it.
- `manual` — after you write `trigger`, return `spectral_count` samples from the
  **current** channel.
- `chanscan` — return `spectral_count` samples **per channel** while a normal
  `iw ... scan` walks the band. This is the easy full-band sweep.

### A.4 Two ways to capture

**(1) Full-band sweep via `chanscan`** — the canonical recipe from the kernel
docs. The scan does the channel-hopping for you:

```bash
IF=wlan0
PHY=/sys/kernel/debug/ieee80211/phy0/ath9k     # use ath9k_htc for USB AR9271

sudo ip link set $IF up
echo chanscan | sudo tee $PHY/spectral_scan_ctl
sudo iw dev $IF scan                            # sweeps channels; PHY dumps FFT per channel
sudo cat $PHY/spectral_scan0 > samples.bin
echo disable  | sudo tee $PHY/spectral_scan_ctl
```

**(2) Stare at one channel via `manual`** — pin a channel, then trigger:

```bash
sudo iw dev $IF set channel 6            # or 'iw dev wlan0 set freq 2437'
echo   64      | sudo tee $PHY/spectral_count
echo manual    | sudo tee $PHY/spectral_scan_ctl
echo trigger   | sudo tee $PHY/spectral_scan_ctl
sudo cat $PHY/spectral_scan0 > samples.bin
echo disable   | sudo tee $PHY/spectral_scan_ctl
```

> **Note on USB (`ath9k_htc`) cards:** the AR9271 firmware exposes the same
> debugfs surface, but a few HTC firmware builds report samples less reliably in
> `background` mode. `chanscan`/`manual` are the safe choices. The open firmware
> source is at [qca/open-ath9k-htc-firmware](https://github.com/qca/open-ath9k-htc-firmware);
> the [vanhoefm/modwifi-ath9k-htc](https://github.com/vanhoefm/modwifi-ath9k-htc/wiki/Spectral-Scan)
> fork documents spectral behaviour and hosts patches worth reading if you build
> your own firmware.

### A.5 Sample format — how to parse `spectral_scan0`

The relayfs file is a stream of **TLV records**. The wrapper and the HT20 record
are defined in `drivers/net/wireless/ath/spectral_common.h` (read *your* kernel's
copy — the layout is stable but check it rather than trusting a magic offset):

```c
enum ath_fft_sample_type {
        ATH_FFT_SAMPLE_HT20 = 1,
        ATH_FFT_SAMPLE_HT20_40,
        ATH_FFT_SAMPLE_ATH10K,
        ATH_FFT_SAMPLE_ATH11K,
};

struct fft_sample_tlv {
        u8 type;            /* see ath_fft_sample_type */
        __be16 length;      /* bytes that follow, big-endian */
} __packed;

struct fft_sample_ht20 {
        struct fft_sample_tlv tlv;
        u8 max_exp;
        __be16 freq;            /* channel centre, MHz */
        s8 rssi;
        s8 noise;
        __be16 max_magnitude;
        u8 max_index;
        u8 bitmap_weight;
        __be64 tsf;
        u8 data[SPECTRAL_HT20_NUM_BINS];   /* 56 bins */
} __packed;
```

`fft_sample_ht20_40` is the HT40 analogue with lower/upper channel RSSI+noise and
a `data[128]` array. **Everything multi-byte is big-endian** (`__be16/__be64`) —
byte-swap on a little-endian host.

**Converting a bin to power.** Each bin value is scaled by a per-sample exponent.
The community-standard reconstruction (used by `fft_eval`) is, per bin `k`:

```
power_k  =  (bin[k] << max_exp)^2
sum      =  Σ_k power_k
dBm_k    =  noise + rssi + 20*log10(bin[k] << max_exp) - 10*log10(sum)
```

i.e. bins are shifted left by `max_exp`, squared, and normalised against the
frame's total energy, then anchored to the reported `rssi`/`noise` in dBm. Use
`freq`, the bin index, and the channel width to place each bin on the frequency
axis (HT20 spans ±10 MHz around `freq`; the exact per-802.11 subcarrier mapping
is discussed in Bastian Bloessl's writeup, linked below).

### A.6 Reference parsing/plotting tools

Do not hand-roll the parser unless you must — two mature tools already read this
exact TLV stream:

```bash
# speccy — live spectrogram (ncurses/waterfall)
git clone https://github.com/bcopeland/speccy
cd speccy && make

# fft_eval — parse a captured file or live-plot (part of the ath spectral tooling)
git clone https://github.com/simonwunderlich/FFT_eval
cd FFT_eval && make
./fft_eval samples.bin
```

- **`speccy`** ([bcopeland/speccy](https://github.com/bcopeland/speccy)) drives
  the debugfs interface itself and renders a live waterfall.
- **`fft_eval`** ([simonwunderlich/FFT_eval](https://github.com/simonwunderlich/FFT_eval))
  parses a captured `spectral_scan0` dump and is the reference for the dBm math
  above.
- Bastian Bloessl's [ath9k spectrum-scanning writeup](https://www.bastibl.net/ath9k-spectrum-scanning/)
  has a matplotlib parser and a careful discussion of frequency-to-bin mapping.

### A.7 Expected output & verification

- A `samples.bin` of nonzero size after `chanscan` + `iw scan`.
- `fft_eval samples.bin` prints per-frame `freq`, `rssi`, `noise`, and a bin
  histogram. Sanity check: park a known emitter (a microwave oven, a Bluetooth
  device, a beaconing AP on channel 6) and confirm the bump lands where it
  should.
- `speccy` shows a live waterfall that reacts within ~1 s when you start/stop a
  nearby transmitter.

### A.8 Spectral troubleshooting

| Symptom | Cause / fix |
|---|---|
| `spectral_scan_ctl` missing | Kconfig symbol off, or you're on a Realtek "WN722N v2/v3" — check `ethtool -i wlan0` shows `ath9k`/`ath9k_htc`. |
| `spectral_scan0` reads 0 bytes | You never wrote `trigger`, or the interface was down, or no `iw scan` ran in `chanscan` mode. |
| Only noise, no signal | Wrong channel in `manual` mode; set the channel *before* triggering. |
| USB card stalls in `background` | Use `chanscan`/`manual` on `ath9k_htc`; see the modwifi firmware notes. |
| Garbage bins | You forgot the big-endian byte-swap, or mixed HT20 (56-bin) and HT40 (128-bin) records — dispatch on `tlv.type`. |

---

## Part B — CSI (Tier 2, needs the modified driver)

### B.1 What CSI is here

For **every received 802.11n frame**, the Atheros-CSI-Tool reports the estimated
complex channel `H` — one complex number per OFDM subcarrier per TX×RX antenna
pair. On a 3×3 card in HT40 that is up to `3 × 3 × 114` complex coefficients per
packet. That is per-subcarrier amplitude *and phase*, which is the whole basis of
Wi-Fi sensing (presence, breathing, gesture, localization). It is Tier 2 because
you get the channel estimate, not the raw PHY samples or TX control.

### B.2 Supported hardware

The tool is built on `ath9k`, so *in principle* any Atheros 802.11n NIC works; in
practice the **validated** parts are:

| Chip | Form factor | Streams | Notes |
|---|---|---|---|
| **AR9380 / QCA9300** | miniPCIe/PCIe | 3×3 | The de-facto card; also the one [PicoScenes](https://www.wifisensing.io/building-applications/platforms/picoscenes) supports (11ac superset). Catalogued as `atheros-ar9300-csi`. |
| **AR9580** | PCIe | 3×3 | Catalogued as `atheros-ar9580`. |
| **AR9590** | PCIe | 3×3 | Validated by the tool authors (net-new below). |
| **AR9344** | SoC (router) | 2×2 | OpenWRT path (net-new below). |
| **QCA9558** | SoC (router) | 3×3 | OpenWRT path (net-new below). |
| **AR9271** | USB | 1×1 | HTC/USB; needs the open HTC firmware, single stream. See `atheros-ar9271`. |

The AR9380/QCA9300 3×3 miniPCIe card in a PCIe adapter is the standard, cheapest,
best-documented choice.

### B.3 Which repo, which kernel — read this before cloning

CSI is **not** in mainline `ath9k`. You replace the driver. Pick the fork that
matches the kernel you can live with — this is the #1 source of pain:

| Repo | Base | Use it when |
|---|---|---|
| [xieyaxiongfly/Atheros-CSI-Tool](https://github.com/xieyaxiongfly/Atheros-CSI-Tool) | **Linux 4.1.10** (full kernel tree) | The original PC/Ubuntu path. Rock-solid but an ancient kernel. |
| [xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src](https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src) | OpenWRT | Router SoCs (AR9344/QCA9558). Has the [project wiki](https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src/wiki). |
| [xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP](https://github.com/xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP) | userspace only | `recvCSI` / `sendData` / `hostapd` + MATLAB parser. You need this regardless of driver fork. |
| [itskalvik/Atheros-CSI-Tool](https://github.com/itskalvik/Atheros-CSI-Tool) | **Linux 4.15.0** | Newer kernel on modern-ish Ubuntu (16.04/18.04-era). |
| [wldhg/ath9k-csitool-r2](https://github.com/wldhg/ath9k-csitool-r2) | **Linux 5.4** (Banana Pi R2) | Newest kernel; ARM/BPI-R2 target. |

> **Kernel-version caution.** The original driver is a *whole kernel tree* pinned
> at 4.1.10 — you build and boot that kernel, not just a module against your
> running one. Trying to compile the 4.1.10 `ath9k` against a modern (6.x) kernel
> **will not work**: the `cfg80211`/`mac80211` internal APIs changed repeatedly.
> If you want a recent kernel, use the 4.15 (itskalvik) or 5.4 (wldhg) forks, and
> even those are frozen — treat this as "boot a dedicated, known-good kernel on a
> spare machine/VM/router," not "patch my daily driver." A modern superset that
> tracks current kernels is **PicoScenes** ([../../projects/picoscenes.md](../../projects/picoscenes.md));
> reach for it if you need the QCA9300 on a 5.x/6.x kernel.

### B.4 Build & install (Ubuntu / 4.1.10 path)

Follow the authors' [Install Ubuntu version](https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src/wiki/Install-Ubuntu-version-of-Atheros-CSI-tool)
wiki page; the shape of it:

```bash
# 1. deps
sudo apt install git build-essential libncurses5-dev libncursesw5-dev \
                 libnl-dev libnl-3-dev libnl-genl-3-dev libssl-dev bc

# 2. get the kernel tree (contains the modified ath9k)
git clone https://github.com/xieyaxiongfly/Atheros-CSI-Tool.git
cd Atheros-CSI-Tool

# 3. seed a config from your running kernel, then enable ath9k + debugfs
cp /boot/config-$(uname -r) .config
make olddefconfig
make menuconfig        # ensure ATH9K (m/y), ATH9K_DEBUGFS, mac80211 are enabled

# 4. build & install (use ~2x core count for -j)
make -j$(($(nproc)*2))
sudo make modules_install
sudo make install
sudo update-grub

# 5. reboot INTO the new kernel, then verify
uname -r               # expect 4.1.10+
```

After reboot the modified `ath9k` loads automatically for a supported card. There
is no separate firmware step for the PCIe parts (AR9271 USB still pulls its HTC
firmware from `/lib/firmware`).

### B.5 Userspace: `recvCSI` / `sendData`

```bash
git clone https://github.com/xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP.git
cd Atheros-CSI-Tool-UserSpace-APP

# receiver
cd recvCSI && make && cd ..
# sender (injects packets so the RX has something to estimate H from)
cd sendData && make && cd ..
```

Bring the two ends up (one card RX, one TX; or use any nearby 11n traffic):

```bash
# RX host
sudo ./recvCSI/recvCSI my_csi.dat
# TX host (or a monitor-mode injector on another Atheros card)
sudo ./sendData/sendData wlan0 100 1000     # 100 pkts, 1000-byte payload (see tool help)
```

The driver delivers CSI to userspace through the **`/dev/CSI_dev` character
device** (not a socket). `recvCSI` opens `/dev/CSI_dev`, reads fixed-size records,
and writes them to your `.dat` file.

### B.6 CSI record format

Each record is a **23-byte status header** followed by the packed CSI payload.
The header struct (from `recvCSI/csi_fun.h`) is:

```c
typedef struct {
    u_int64_t tstamp;      /* h/w timestamp */
    u_int16_t channel;     /* channel, Hz */
    u_int8_t  chanBW;      /* 0 = 20 MHz, 1 = 40 MHz */
    u_int8_t  rate;        /* MCS / rate */
    u_int8_t  nr;          /* # RX antennas */
    u_int8_t  nc;          /* # TX antennas */
    u_int8_t  num_tones;   /* # subcarriers */
    u_int8_t  noise;       /* noise floor */
    u_int8_t  phyerr;      /* 0 if frame OK */
    u_int8_t  rssi;        /* combined RSSI */
    u_int8_t  rssi_0, rssi_1, rssi_2;  /* per-chain RSSI */
    u_int16_t payload_len; /* bytes */
    u_int16_t csi_len;     /* bytes of packed CSI */
    u_int16_t buf_len;     /* total record bytes */
} csi_struct;
```

**Unpacking the CSI matrix** (`fill_csi_matrix` in `csi_fun.c`): each complex
coefficient is stored as **two 10-bit signed values** (imag then real). The parser
reads 16 bits at a time, masks with `(1 << 10) - 1`, sign-extends via
`bit_convert()` (two's complement), and iterates subcarrier → TX antenna → RX
antenna to fill `COMPLEX csi_matrix[nr][nc][num_tones]`, where:

```c
typedef struct { int real; int imag; } COMPLEX;
```

Multi-byte header fields are read with an explicit `is_big_endian()` check, so the
same parser works on either host endianness. The MATLAB reference reader lives in
the `matlab/` directory of the UserSpace-APP repo; `read_csi()` there returns the
same `nr × nc × num_tones` complex tensor for plotting/processing.

### B.7 Expected output & verification

- `ls -l /dev/CSI_dev` exists after the modified `ath9k` loads (if it doesn't,
  the wrong driver is bound — see below).
- `recvCSI` prints a growing packet count while `sendData` runs; your `.dat`
  file grows.
- Load `my_csi.dat` in the MATLAB/Python reader: amplitude across the ~56 (HT20)
  or ~114 (HT40) subcarriers should be a smooth-ish curve, and it should
  **change visibly when you wave a hand between the antennas** — the classic CSI
  sanity check.

### B.8 CSI troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Failed to open the device .../dev/CSI_dev` | The modified `ath9k` isn't loaded (you booted the wrong kernel, or a supported card isn't bound). `uname -r` must show the CSI kernel; `ethtool -i wlanX` must show `ath9k`. |
| Kernel won't compile on a modern host | You're building the 4.1.10 tree against new toolchain/kernel APIs. Boot the pinned kernel, or use the 4.15 / 5.4 forks, or move to PicoScenes. |
| No records although `sendData` runs | RX and TX not on the same channel/BW; frames failing CRC (`phyerr != 0`); antennas disconnected. |
| CSI all zeros / constant | Estimating on management frames only, or `num_tones`/`chanBW` mismatch in your parser. Dispatch on the header's `chanBW`. |
| Works but you need a current kernel / 11ac | Use [PicoScenes](https://www.wifisensing.io/building-applications/platforms/picoscenes) with the QCA9300 — same silicon, maintained stack. |

---

## C. Regulatory / safety note

Both features in this guide are **receive-only** and passive: spectral scan reads
the ADC's FFT engine, CSI reads the per-packet channel estimate. Neither
transmits anything beyond ordinary Wi-Fi (the `sendData` helper emits standard
802.11n frames on your licensed-exempt band, subject to the same rules as any
Wi-Fi NIC). Injection via `sendData` should stay on channels and power levels
legal in your region and off networks you don't own. There is **no
arbitrary-waveform TX path here** — if that's what you need, this card can't do it
(see [../verification-tier4.md](../verification-tier4.md) and
[../true-sdr-comparison.md](../true-sdr-comparison.md)).

---

## References

- ath9k spectral scan — Linux Wireless docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
- Kernel header `spectral_common.h` (bin counts, TLV structs): <https://github.com/torvalds/linux/blob/master/drivers/net/wireless/ath/spectral_common.h>
- `speccy` (live spectral visualiser): <https://github.com/bcopeland/speccy>
- `fft_eval` (sample parser, dBm math): <https://github.com/simonwunderlich/FFT_eval>
- Bastian Bloessl, "Spectrum Scanning with WiFi Cards": <https://www.bastibl.net/ath9k-spectrum-scanning/>
- open-ath9k-htc-firmware (AR7010/AR9271): <https://github.com/qca/open-ath9k-htc-firmware>
- modwifi-ath9k-htc spectral wiki: <https://github.com/vanhoefm/modwifi-ath9k-htc/wiki/Spectral-Scan>
- Atheros-CSI-Tool (kernel 4.1.10 driver, Yaxiong Xie et al.): <https://github.com/xieyaxiongfly/Atheros-CSI-Tool>
- Atheros CSI Tool userspace apps (`recvCSI`/`sendData`/MATLAB): <https://github.com/xieyaxiongfly/Atheros-CSI-Tool-UserSpace-APP>
- OpenWRT source + project wiki: <https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src/wiki>
- itskalvik fork (kernel 4.15.0): <https://github.com/itskalvik/Atheros-CSI-Tool>
- wldhg fork (kernel 5.4, BPI-R2): <https://github.com/wldhg/ath9k-csitool-r2>
- WANDS AtherosCSI project site: <https://wands.hk/AtherosCSI/index.html>
- PicoScenes (modern QCA9300 CSI on current kernels): <https://www.wifisensing.io/building-applications/platforms/picoscenes>
- "Hands-on Wireless Sensing with Wi-Fi: A Tutorial" (CSI tool comparison): <https://tns.thss.tsinghua.edu.cn/~guoxuan/assets/pdf/Paper-Hands-On.pdf>
