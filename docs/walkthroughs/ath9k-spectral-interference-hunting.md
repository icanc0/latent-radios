# Interference Hunting with ath9k Spectral Scan

**Tier 3 (spectral) — passive, receive-only. No transmission, no legal-RF exposure.**

Wi-Fi cards built on the Qualcomm Atheros `ath9k` PCIe silicon (AR92xx / AR93xx / AR95xx / AR946x)
expose the radio's raw FFT engine through `debugfs`. That FFT is normally used by the driver for
DFS/radar detection and channel-quality estimation, but the same samples let you **see the 2.4 GHz
and 5 GHz bands as a spectrum analyzer would** — including energy that is *not* Wi-Fi.

This guide is the interference-hunting counterpart to the general spectral/CSI walkthrough
([../../docs/walkthroughs/atheros-ath9k-spectral-csi.md](../../docs/walkthroughs/atheros-ath9k-spectral-csi.md)).
Where that document explains how the FFT engine works and how to derive CSI-like data, this one is
narrowly practical: **use `spectral_scan` to find, plot, and identify a real RF interferer** —
a microwave oven, a Bluetooth/BLE device, a 2.4 GHz analog video sender, a wireless camera, a
cordless phone, or a Zigbee node — by its signature on a live waterfall. For which cards carry this
engine, see [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md).

---

## 1. What you need

- **A PCIe/mini-PCIe/M.2 `ath9k` card.** Spectral scan is a full-MAC PCIe-driver feature.
  The USB `ath9k_htc` parts (AR7010/AR9271/AR9280-USB) do **not** expose `spectral_scan`.
  Known-good families: AR9280, AR9285, AR9287, AR9227 (2.4 GHz-class, HT20/HT40) and
  AR9380/AR9382/AR9462/AR9485/AR9565/AR9580/AR9590 (dual-band, 2.4 + 5 GHz).
- **A recent mainline kernel with `ath9k` + `CONFIG_ATH9K_DEBUGFS=y`** (default in most distros).
- **Root**, and `debugfs` mounted:
  ```bash
  sudo mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
  ```
- The control tree lives at (substitute your PHY index — check `ls /sys/kernel/debug/ieee80211/`):
  ```
  /sys/kernel/debug/ieee80211/phy0/ath9k/
  ```

The relevant knobs (kernel `ath9k` spectral-scan documentation):

| File | Purpose |
|------|---------|
| `spectral_scan_ctl` | Mode/trigger register: write `background`, `chanscan`, `manual`, `trigger`, or `disable` |
| `spectral_scan0` | **relayfs** stream of binary FFT samples — you `cat`/read this |
| `spectral_count` | Number of FFT frames to collect per trigger (manual mode) |
| `spectral_period` | Time between spectral scan entry points |
| `spectral_fft_period` | FFT-frame delivery interval within a scan |
| `spectral_short_repeat` | Short vs. full repeat control (sampling duration) |

Modes:
- **`disable`** — engine off (always return to this when done).
- **`background`** — sample the *current operating channel* during idle periods. Good for watching
  one channel continuously while associated.
- **`chanscan`** — collect samples on *each channel visited during a scan* (`iw ... scan`). This is
  the fastest way to sweep the whole band once.
- **`manual`** — arm the engine, then write `trigger` to grab `spectral_count` frames from whatever
  channel the radio is currently parked on. Best for a deliberate, fixed-channel dwell.

---

## 2. Sweep the whole band once (chanscan)

Interferers rarely sit on the channel you happen to be associated to, so start with a full sweep.

```bash
DEV=wlan0
PHY=phy0
CTL=/sys/kernel/debug/ieee80211/$PHY/ath9k

sudo sh -c "echo chanscan > $CTL/spectral_scan_ctl"
sudo iw dev $DEV scan                       # visits every allowed channel, sampling each
sudo cat $CTL/spectral_scan0 > /tmp/sweep.bin
sudo sh -c "echo disable > $CTL/spectral_scan_ctl"
ls -l /tmp/sweep.bin
```

`sweep.bin` now holds a stream of TLV FFT records spanning every channel the scan touched. Feed it to
a viewer (Section 4). A wideband, always-on emitter (video sender, camera) will show up as a solid
block on one channel; a hopper (Bluetooth) will be smeared across many.

> Note: each FFT snapshot only covers the ~20 MHz (HT20) or ~40 MHz (HT40) the radio is tuned to.
> "Seeing the whole band" always means **hopping the tuner** — either via `chanscan` or by manually
> retuning between manual captures.

---

## 3. Dwell on a suspect channel (manual + trigger)

Once the sweep points you at a channel, park there and stare at it. Put the interface into monitor
mode so it stays on the channel you choose and does not try to associate:

```bash
DEV=wlan0
CTL=/sys/kernel/debug/ieee80211/phy0/ath9k

sudo ip link set $DEV down
sudo iw dev $DEV set type monitor
sudo ip link set $DEV up
sudo iw dev $DEV set channel 11            # e.g. the noisy channel from the sweep

sudo sh -c "echo 128 > $CTL/spectral_count"      # frames per trigger
sudo sh -c "echo manual > $CTL/spectral_scan_ctl"
sudo sh -c "echo trigger > $CTL/spectral_scan_ctl"
sudo cat $CTL/spectral_scan0 > /tmp/ch11.bin
sudo sh -c "echo disable > $CTL/spectral_scan_ctl"
```

For a **live waterfall**, loop the trigger/read cycle into a growing file (or a FIFO) and let the
viewer poll it:

```bash
CTL=/sys/kernel/debug/ieee80211/phy0/ath9k
sudo sh -c "echo manual > $CTL/spectral_scan_ctl"
while sleep 0.1; do
  sudo sh -c "echo trigger > $CTL/spectral_scan_ctl"
  sudo cat $CTL/spectral_scan0 >> /tmp/live.bin
done
# Ctrl-C to stop, then:  sudo sh -c "echo disable > $CTL/spectral_scan_ctl"
```

To watch a channel you are actively *using* (e.g. debugging your own AP's link) without leaving it,
use `background` mode instead of `manual` and just keep reading `spectral_scan0` — normal traffic
provides the idle windows the engine samples in.

---

## 4. Plotting: FFT sample format and the tools

`spectral_scan0` emits packed, big-endian **TLV** records. The layout is fixed by the kernel
(`drivers/net/wireless/ath/spectral_common.h`):

- A 3-byte TLV header: `type` (`1` = `ATH_FFT_SAMPLE_HT20`, `2` = `ATH_FFT_SAMPLE_HT20_40`) and a
  big-endian `length`.
- Then per-sample metadata: `max_exp`, `freq`, `rssi`, `noise`, `max_magnitude`, `max_index`,
  `bitmap_weight`, `tsf`.
- Then the bins: **56 bins** for HT20, **128 bins** for HT40 (each an unsigned magnitude byte).

Per-bin power (the formula FFT_eval uses) is, in essence:

```
bin_dBm ≈ noise + rssi + 20*log10(bin_magnitude << max_exp) - 10*log10(Σ (bin_magnitude << max_exp)²)
bin_freq_MHz ≈ center_freq - (bandwidth/2) + bandwidth * (bin_index / num_bins)
```

You almost never parse this by hand — use an existing viewer:

- **`simonwunderlich/FFT_eval`** — the reference GTK visualizer. Reads a captured sample file and
  draws the spectrum / accumulated waterfall. HT20-focused; the standard first tool to reach for.
- **`bcopeland/speccy`** — reads the relayfs stream **live** and renders a scrolling waterfall in a
  window; the most convenient for real-time hunting.
- **`LorenzoBianconi/ath_spectral`** — alternate parser/plotter, handles HT20/HT40.

Typical FFT_eval run:

```bash
git clone https://github.com/simonwunderlich/FFT_eval
cd FFT_eval && make
./fft_eval /tmp/sweep.bin        # or /tmp/ch11.bin / /tmp/live.bin
```

If you only want a quick static picture and would rather script it, a short Python reader can
`struct.unpack` the TLV stream above and feed a `matplotlib` `imshow` waterfall (time on Y, the
bins' frequencies on X, `bin_dBm` as color). The kernel struct is the authoritative layout — do not
guess field offsets, unpack them in the documented order.

---

## 5. Reading interferer signatures

The point of the waterfall is pattern recognition. On a time-vs-frequency plot (Y = time scrolling
down, X = frequency across the band, color = power), the common 2.4 GHz offenders look like this:

| Emitter | Signature on the waterfall | Tell-tale details |
|---------|----------------------------|-------------------|
| **Microwave oven** | Broad "hump" of energy, ~15–20 MHz wide, that **pulses on/off periodically** and drifts in frequency. Usually strongest in the **upper half of the band (~2450–2470 MHz, ch 9–11)**. | On/off period tied to mains: roughly half-cycle cadence (~8–10 ms on, ~8–10 ms off), producing regular horizontal stripes. Sloppy magnetron → frequency wander between bursts. |
| **Classic Bluetooth** | Narrow (~1 MHz) spikes **scattered pseudo-randomly across the whole band** over time — a "starfield" of dots. | Frequency-hopping (1600 hops/s over 79 channels). No fixed home; density rises during active audio/file transfer. |
| **Bluetooth LE** | Same scatter but sparser, with **three brighter columns at ~2402, 2426, 2480 MHz** (advertising channels 37/38/39). | BLE uses 2 MHz channels; idle beacons hit only the three adv channels, so those columns persist while the rest is quiet. |
| **Analog video sender / FPV / wireless AV / baby monitor** | A **solid, continuous horizontal band ~16–18 MHz wide parked on one fixed frequency** (commonly 2410/2430/2450/2470 MHz). Always on. | No on/off structure and no hopping — the giveaway is a persistent, unbroken block that Wi-Fi (bursty) never produces. |
| **Wireless (analog) camera** | Same as video sender: a fixed, always-on wide carrier, often with a slightly brighter center (FM carrier peak). | Continuous; may show a faint symmetric FM shoulder pattern. |
| **2.4 GHz cordless phone** | Either a **narrow persistent carrier** (analog/FHSS-off) or **slow, patterned hopping** across a few MHz. | Appears when a call is active; DECT phones are at 1.9 GHz and will **not** appear here. |
| **Zigbee / 802.15.4 sensor** | Very narrow (~2 MHz), **low-duty bursts on one fixed channel** (Zigbee ch 11–26 → 2405–2480 MHz). | Sparse, periodic packets; sits between Wi-Fi channels (e.g. Zigbee 15/20/25/26 in the Wi-Fi 1/6/11 gaps). |
| **Wi-Fi (for contrast)** | **Bursty** OFDM energy filling a 20/40/80 MHz channel, aligned to standard channel centers, with idle gaps. | The burst-and-gap texture and channel-aligned width distinguish it from every continuous or hopping interferer above. |

Practical read-out workflow:

1. **Continuous vs. bursty vs. hopping** is the first cut. Continuous solid block → analog
   video/camera/carrier. Bursty channel-aligned → Wi-Fi. Scattered narrow dots → Bluetooth/BLE.
2. **Periodic pulsing at mains cadence** → microwave oven. Walk toward the kitchen; the level should
   rise as you approach.
3. **Which half of the band?** Microwaves and many video senders favor the upper channels (9–13);
   move your AP to channel 1 to dodge them.
4. **Confirm with distance/on-off.** Toggle the suspect device (start/stop a Bluetooth stream, open
   the microwave door, unplug the camera) and watch the waterfall change in real time — this is the
   single most reliable confirmation.

---

## 6. Limitations and cleanup

- **Only what the tuner covers.** One capture sees ~20/40 MHz. Whole-band awareness requires
  `chanscan` or manual channel hopping — a fast hopper can be missed on a single narrow dwell.
- **Uncalibrated.** The dBm values are relative/estimated, not lab-accurate absolute power. Use them
  for *relative* comparison and pattern ID, not compliance measurement.
- **RX only.** Nothing here transmits, so there is no legal-emission or RF-exposure concern
  (see [../../docs/rf-safety-and-legal.md](../../docs/rf-safety-and-legal.md) for the general
  framing). The only side effect is that `manual`/`chanscan` retune the radio, so you will drop any
  association while sweeping — do it on a spare interface if the link must stay up.
- **Always disable when finished:**
  ```bash
  sudo sh -c "echo disable > /sys/kernel/debug/ieee80211/phy0/ath9k/spectral_scan_ctl"
  ```

---

## References

- ath9k spectral scan — kernel wireless documentation: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
- Kernel FFT sample TLV layout — `drivers/net/wireless/ath/spectral_common.h`: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/ath/spectral_common.h>
- `simonwunderlich/FFT_eval` (reference visualizer): <https://github.com/simonwunderlich/FFT_eval>
- `bcopeland/speccy` (live waterfall): <https://github.com/bcopeland/speccy>
- `LorenzoBianconi/ath_spectral`: <https://github.com/LorenzoBianconi/ath_spectral>
- Companion walkthrough: [../../docs/walkthroughs/atheros-ath9k-spectral-csi.md](../../docs/walkthroughs/atheros-ath9k-spectral-csi.md)
- Card support matrix: [../../chips/qualcomm-atheros.md](../../chips/qualcomm-atheros.md)
