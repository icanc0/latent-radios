# Build a real-time CSI visualizer

> The tool everyone building Wi-Fi sensing wants on day one: a window that shows
> **live** channel state information as you wave your hand, walk across the room,
> or breathe in front of the antenna. Recorded-file plotting is a solved problem
> ([csiread](https://github.com/citysu/csiread), [CSIKit](https://github.com/Gi-z/CSIKit)).
> Streaming it smoothly at hundreds of packets per second without the GUI hitching
> is where people get stuck. This walkthrough gets you there.
>
> Prerequisites: you can already extract CSI. If not, start at
> [From nexmon_csi capture to usable CSI](nexmon-csi-to-usable-csi.md) (Broadcom/Pi),
> and see [csi-toolchains.md](../../projects/csi-toolchains.md) for every other
> extractor (Intel, Atheros, ESP32, PicoScenes). For turning the pretty picture
> into *trustworthy* numbers, read [CSI calibration deep dive](csi-calibration-deep-dive.md).

This is a **Tier 2** exercise on the [SDR ladder](../taxonomy.md): you are reading
the radio's own per-subcarrier equalizer telemetry, not raw IQ off the antenna.

---

## 1. What "real-time CSI" actually means

Three producers dominate, and each hands you frames over a different transport:

| Source | Transport | Payload | Live tap |
|---|---|---|---|
| **nexmon_csi** (BCM43455c0 / BCM4339 / BCM4358…) | UDP broadcast | bit-packed I/Q block, FFT-ordered | `socket` bound to port **5500** |
| **ESP32-CSI-Tool** / esp-csi | USB serial (UART) | ASCII `CSI_DATA` CSV line | `pyserial` read line |
| **PicoScenes** (Intel AX210, USRP, etc.) | files / plot server | `.csi` frames | PicoScenes `RXSPlotServer` / read frames |
| Intel 5300 (log_to_file) | file / FIFO | Intel beamforming blocks | tail a FIFO |

The visualizer is the same in every case. Only the **acquire → decode** front end
changes. Design the app so that front end is a single generator that yields
`H` arrays of shape `(n_subcarriers,)` (complex), and everything downstream is
transport-agnostic.

> **Transport gotcha (nexmon).** nexmon_csi emits ordinary UDP frames with
> source IP `10.10.10.10`, destination `255.255.255.255`, **UDP dst port 5500**.
> Your capture NIC (the monitor interface `wlan0`) sees them locally; you do
> **not** need the Broadcom radio to also be your host's default route. Either
> `tcpdump -i wlan0 -w -` piped in, or a raw `AF_PACKET`/`AF_INET` socket. The
> simplest cross-platform path is to let `tcpdump` do the L2/L3/UDP stripping and
> read its pcap stream, but a plain UDP socket works if the frames reach the IP
> stack.

---

## 2. Decoding one frame (the only chip-specific part)

### 2.1 nexmon_csi payload → complex vector

A nexmon_csi UDP payload is a fixed nexmon header followed by the CSI block.
The **exact** byte offsets, the `magic` marker, `core`/`spatial-stream` nibble
packing, and — critically — the real/imag ordering and the per-chip encoding are
documented in [nexmon-csi-to-usable-csi.md §1](nexmon-csi-to-usable-csi.md).
**Do not hardcode offsets from memory** — encoding differs by chip:

- `bcm4339` / `bcm43455c0`: interleaved **int16** real & imaginary → 4 bytes/subcarrier.
- `bcm4358` / `bcm4366c0`: a packed **float** (sign / mantissa / exponent) that must be un-packed bit by bit — use a maintained decoder, do not roll your own.

A robust trick that sidesteps the header-offset question for the int16 chips:
the CSI block is the **tail** of the payload and its length is fixed by bandwidth
(`n_sub × 4` bytes), so slice from the end:

```python
import numpy as np

NSUB = {20: 64, 40: 128, 80: 256}   # subcarriers per bandwidth (MHz)

def nexmon_int16_to_csi(payload: bytes, bw_mhz: int = 80) -> np.ndarray:
    """Decode ONE nexmon_csi UDP payload for int16 chips (4339/43455c0).

    The CSI block is the last n_sub*4 bytes of the payload; taking it from the
    tail avoids depending on the exact nexmon header length, which varies by
    firmware generation (see nexmon-csi-to-usable-csi.md for the header table).
    """
    nsub = NSUB[bw_mhz]
    raw = np.frombuffer(payload[-nsub * 4:], dtype=np.int16)  # LE on x86/ARM
    iq = raw.reshape(nsub, 2)
    csi = iq[:, 0].astype(np.float32) + 1j * iq[:, 1].astype(np.float32)
    # If your amplitude looks mirrored/garbled, swap the columns: some builds
    # emit (imag, real). Confirm ordering against the walkthrough, then fix once.
    return np.fft.fftshift(csi)     # FFT-ordered -> subcarrier index order
```

For the **float** chips, or if you would rather not maintain the bit-unpacking,
use a library. [`csiread`](https://github.com/citysu/csiread) ships a
`csiread.Nexmon(pcap, chip='4358', bw=80)` reader and, importantly, a
**`pmsg()`** method for real-time packet-by-packet parsing (as opposed to
`read()`, which slurps a whole file). [`nexcsi`](https://github.com/nexmonster/nexcsi)
(pure-Python) exposes `nexcsi.decode(chip)` with `unpack("csi")` and handles the
per-chip float format for you.

### 2.2 ESP32 serial line → complex vector

esp-csi prints one ASCII line per frame. The column order (from the official
`csi_data_read_parse.py`) is:

```
CSI_DATA,type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,
aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,
local_timestamp,ant,sig_len,rx_state,len,first_word,data
```

The last field, `data`, is a bracketed list of **interleaved int8**, imaginary
first then real (esp-csi builds `complex(real=raw[i*2+1], imag=raw[i*2])`):

```python
import re

def esp32_line_to_csi(line: str) -> np.ndarray | None:
    if not line.startswith("CSI_DATA"):
        return None
    m = re.search(r"\[(.*)\]", line)          # the trailing [ ... ] array
    if not m:
        return None
    raw = np.fromstring(m.group(1), sep=" ", dtype=np.int8)  # or split/int
    raw = raw[: (len(raw) // 2) * 2]          # guard odd counts
    iq = raw.reshape(-1, 2)
    return iq[:, 1].astype(np.float32) + 1j * iq[:, 0].astype(np.float32)
```

For HT20 you get 64 subcarriers (128 int8); esp-csi buffers up to
`CSI_DATA_COLUMNS = 490` amplitude/phase slots for wider/aggregated cases. Note
that ESP32 populates only the used subcarriers — mask out the guard/null bins
before plotting (see [csi-toolchains.md](../../projects/csi-toolchains.md) and
[esp32-csi-motion-detection.md](esp32-csi-motion-detection.md)).

> esp-csi's own `esp_csi_tool.py` already ships a **PyQtGraph** live GUI (three
> `pyqtgraph.PlotWidget`s driven by a 100 ms `QTimer`). Read it as a reference —
> the skeleton below is the same idea, stripped to the essentials so you can
> retarget it to nexmon or PicoScenes.

### 2.3 PicoScenes

[PicoScenes](../../projects/picoscenes.md) writes `.csi` frames and can stream to
its `RXSPlotServer`. `csiread.Picoscenes(...)` parses frames; per-frame you get a
complex `CSI` array and take `np.abs()` / `np.angle()`. The visualizer downstream
is unchanged.

---

## 3. Display calibration (just enough to look right)

Raw CSI is not a measurement — it is what the equalizer left behind. Full
sanitization (CFO/SFO/STO, phase offset, amplitude scaling) is its own subject:
**[CSI calibration deep dive](csi-calibration-deep-dive.md)**. For a *live view*
you want the cheapest transforms that make motion visible without lying:

- **Amplitude**: plot `|H(k)|` directly, or `20·log10(|H|)` for dB. Drop the
  null/guard subcarriers (they are ~0 and blow up the color scale). Optionally
  divide by a captured static-channel reference `H0` so the plot shows *change*.
- **Phase**: raw phase is dominated by the per-packet linear slope from sampling
  time offset (STO) plus a constant offset (CFO/PO). For display, remove the
  linear trend per packet — `np.unwrap` across subcarriers then subtract a
  least-squares line — so real phase structure is not buried under a ramp that
  flips every frame. This is the display-only shortcut; the calibration doc
  explains why the honest quantities are **differential** (conjugate ratio
  across antennas, or across time) and immune to these offsets.

```python
def sanitize_phase(csi: np.ndarray) -> np.ndarray:
    ph = np.unwrap(np.angle(csi))
    k = np.arange(len(ph))
    a, b = np.polyfit(k, ph, 1)          # linear STO ramp + offset
    return ph - (a * k + b)              # detrended phase for display
```

---

## 4. The real-time gotchas (why naive code hitches)

These are the failures that separate a demo that stutters from one that glides:

1. **Never block the GUI thread on I/O.** `socket.recv()` and `serial.readline()`
   block. Run acquisition in a **background thread**; the render loop lives on the
   main/GUI thread. (Blocking reads release the GIL, so a plain `threading.Thread`
   is fine — no multiprocessing needed.)
2. **Decouple with a bounded buffer.** Push decoded frames into a
   `collections.deque(maxlen=N)` or `queue.Queue(maxsize=N)`. Bounded is the point:
   CSI can arrive at 100–1000 pkt/s but your eyes and monitor top out at ~30–60 FPS.
   For a *live* view you want the **latest** frame, so let the buffer drop old ones
   rather than growing unbounded and adding latency.
3. **Render at a fixed rate, drain the buffer each tick.** On each animation
   frame, drain everything queued, keep the newest line for the amplitude/phase
   plots, and append the batch to the waterfall. Do not render one frame per
   packet.
4. **Update artists, don't recreate them.** In matplotlib use
   `line.set_ydata(...)` / `image.set_data(...)` with `blit=True`; never call
   `ax.plot()` inside the loop (it leaks artists and forces full redraws).
5. **Waterfall = pre-allocated ring, not `np.roll`.** Allocate a
   `(T, n_sub)` float array once. Write with a modulo index (`buf[w % T] = row`)
   and display `np.roll(buf, -w, axis=0)` only at render time — or better, keep a
   write pointer and slice. `np.roll` on every packet copies the whole image and
   is a common cause of lag.
6. **PyQtGraph for speed.** matplotlib `FuncAnimation` is fine to ~30 FPS and a
   few hundred subcarriers; beyond that (80 MHz × 4 antennas, dense waterfall),
   [PyQtGraph](https://www.pyqtgraph.org/) with `ImageItem.setImage(...,
   autoLevels=False)` and a `QTimer` is dramatically smoother. Set levels once;
   `autoLevels` per frame is expensive.
7. **Fix the color scale.** Auto-scaling the waterfall every frame makes the
   whole image flicker. Compute `vmin/vmax` from a warm-up window, then freeze.
8. **Backpressure on serial.** ESP32 at high frame rates will overflow the UART
   buffer; read in a tight thread and let the deque drop, or lower the ESP frame
   rate. Log dropped-frame counts so you know when you are display-limited.

---

## 5. Copy-pasteable skeleton (matplotlib)

Three panels — amplitude-vs-subcarrier line, scrolling amplitude waterfall,
detrended phase — fed by a transport-agnostic acquisition thread. Swap the
`acquire()` body for nexmon UDP, ESP32 serial, or PicoScenes; everything else is
identical.

```python
#!/usr/bin/env python3
"""Real-time CSI visualizer (matplotlib). RX-only / passive.
Front end: nexmon_csi UDP:5500 by default. See sections 2.1-2.3 to retarget."""
import socket, threading
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

BW = 80                      # MHz
NSUB = {20: 64, 40: 128, 80: 256}[BW]
WATERFALL_T = 300            # rows of history
UDP_PORT = 5500

buf = deque(maxlen=512)      # bounded: newest frames win
stop = threading.Event()

# ---- acquisition thread (swap this body per transport) --------------------
def acquire():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", UDP_PORT))
    s.settimeout(1.0)
    while not stop.is_set():
        try:
            payload, _ = s.recvfrom(4096)
        except socket.timeout:
            continue
        csi = nexmon_int16_to_csi(payload, BW)   # from section 2.1
        buf.append(csi)
    s.close()

# ---- helpers (sections 2.1 / 3) -------------------------------------------
NSUB_MAP = {20: 64, 40: 128, 80: 256}
def nexmon_int16_to_csi(payload, bw_mhz=80):
    nsub = NSUB_MAP[bw_mhz]
    iq = np.frombuffer(payload[-nsub*4:], dtype=np.int16).reshape(nsub, 2)
    csi = iq[:, 0].astype(np.float32) + 1j*iq[:, 1].astype(np.float32)
    return np.fft.fftshift(csi)

def sanitize_phase(csi):
    ph = np.unwrap(np.angle(csi)); k = np.arange(len(ph))
    a, b = np.polyfit(k, ph, 1); return ph - (a*k + b)

# ---- figure & artists (created ONCE) --------------------------------------
fig, (ax_a, ax_w, ax_p) = plt.subplots(3, 1, figsize=(9, 8))
x = np.arange(NSUB)

(line_a,) = ax_a.plot(x, np.zeros(NSUB)); ax_a.set_ylim(0, 4000)
ax_a.set_title("Amplitude |H(k)|"); ax_a.set_xlabel("subcarrier")

wf = np.zeros((WATERFALL_T, NSUB), np.float32); wptr = 0
im = ax_w.imshow(wf, aspect="auto", origin="lower", vmin=0, vmax=4000,
                 interpolation="nearest")
ax_w.set_title("Amplitude waterfall (time x subcarrier)")

(line_p,) = ax_p.plot(x, np.zeros(NSUB)); ax_p.set_ylim(-np.pi, np.pi)
ax_p.set_title("Detrended phase"); ax_p.set_xlabel("subcarrier")
fig.tight_layout()

def update(_):
    global wptr
    if not buf:
        return line_a, im, line_p
    frames = list(buf); buf.clear()      # drain everything queued this tick
    for f in frames:                     # keep waterfall continuous
        wf[wptr % WATERFALL_T] = np.abs(f); wptr += 1
    latest = frames[-1]                  # newest for the line plots
    line_a.set_ydata(np.abs(latest))
    line_p.set_ydata(sanitize_phase(latest))
    im.set_data(np.roll(wf, -(wptr % WATERFALL_T), axis=0))  # display-time only
    return line_a, im, line_p

if __name__ == "__main__":
    t = threading.Thread(target=acquire, daemon=True); t.start()
    ani = FuncAnimation(fig, update, interval=33, blit=False, cache_frame_data=False)
    try:
        plt.show()
    finally:
        stop.set(); t.join(timeout=2)
```

Run it, then generate traffic the monitor NIC can hear (e.g. `ping -f` your AP,
or the frame injector from your extraction setup). You should see the amplitude
line ripple and the waterfall scroll as you move in front of the antennas.

> `blit=True` is faster but forces you to return every changed artist and does
> not play well with `imshow` color updates on all backends; start with
> `blit=False`, move to PyQtGraph if you need more than ~30 FPS.

---

## 6. Faster path: PyQtGraph (drop-in render loop)

Keep the same `acquire()` thread and `buf`; replace only the render layer. This
is what esp-csi's `esp_csi_tool.py` does, and it scales to 80 MHz × multiple
antennas where matplotlib starts to drop frames.

```python
import numpy as np, pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

NSUB, T = 256, 300
app = QtWidgets.QApplication([])
win = pg.GraphicsLayoutWidget(title="Real-time CSI"); win.show()

p_amp = win.addPlot(row=0, col=0, title="Amplitude |H(k)|")
curve_amp = p_amp.plot(pen="y")
p_wf = win.addPlot(row=1, col=0, title="Waterfall")
img = pg.ImageItem(); p_wf.addItem(img)
img.setLevels((0, 4000))                       # FIX levels; no per-frame autoscale
wf = np.zeros((T, NSUB), np.float32); wptr = 0

def tick():
    global wptr
    if not buf: return
    frames = list(buf); buf.clear()
    for f in frames:
        wf[wptr % T] = np.abs(f); wptr += 1
    curve_amp.setData(np.abs(frames[-1]))
    img.setImage(np.roll(wf, -(wptr % T), axis=0).T, autoLevels=False)

timer = QtCore.QTimer(); timer.timeout.connect(tick); timer.start(33)  # ~30 FPS
QtWidgets.QApplication.instance().exec()
```

`ImageItem` wants `(width, height)` = `(subcarrier, time)`, hence the `.T`. Setting
levels once and passing `autoLevels=False` is the single biggest smoothness win.

---

## 7. Parsing libraries — use them, don't reinvent

| Library | Live tap | Formats | Notes |
|---|---|---|---|
| [csiread](https://github.com/citysu/csiread) | **yes** — `pmsg()` per-packet | Intel 5300, Atheros, Nexmon, ESP32, PicoScenes | Cython-fast; classes `Intel`, `Atheros`, `Nexmon`, `NexmonPull46`, `ESP32`, `Picoscenes`. `read()`/`seek()`/`pmsg()`/`display()`. Amplitude via `np.abs`, `get_scaled_csi()` for Intel. |
| [nexcsi](https://github.com/nexmonster/nexcsi) | payload decode | Nexmon (incl. float chips) | Pure-Python `decode(chip)` handles the packed-float format so you don't. |
| [CSIKit](https://github.com/Gi-z/CSIKit) | no (batch) | Intel 5300/AX200/AX210, Atheros, Broadcom/Nexmon, ESP32, PicoScenes, FeitCSI | Best for offline: `get_reader()` → `read_file()` → `csitools.get_CSI()` returns `(frames, n_sub, n_rx, n_tx)`. Great for validating your live decoder against a known-good parse. |

Validate your streaming decoder by capturing to a file, parsing it with CSIKit,
and diffing against what your live path produced for the same frames.

---

## 8. TX / safety and legal notes

The visualizer itself is **receive-only and passive** — a monitor-mode NIC
listening plus a socket/serial reader. That part is unproblematic. But you cannot
see CSI without *some* transmitter emitting frames the receiver measures:

- **Prefer traffic you are already licensed to emit**: your own AP/station on a
  channel and band your regulatory domain permits (see
  [rf-safety-and-legal.md](../rf-safety-and-legal.md) and
  [regulatory-by-region.md](../regulatory-by-region.md)). A `ping -f` to your own
  AP is enough to drive a lively CSI stream.
- **nexmon_csi frame injection / `makecsiparams`** and any raw-80211 TX
  (ESP32 raw TX, [esp32-raw-80211-tx-promiscuous-rx.md](esp32-raw-80211-tx-promiscuous-rx.md))
  are transmit operations: only on permitted channels/power, and never on
  restricted bands. The int16/float decoding here is purely on the RX side.
- Keep the tool a **viewer**. It shows the channel; it does not authorize you to
  transmit anything you otherwise couldn't.

---

## 9. Where to go next

- **Trust the numbers**: [CSI calibration deep dive](csi-calibration-deep-dive.md)
  — differential quantities, CFO/SFO/STO removal, antenna-ratio phase.
- **Do something with it**: motion/breathing
  ([esp32-csi-breathing-monitor.md](esp32-csi-breathing-monitor.md),
  [esp32-csi-motion-detection.md](esp32-csi-motion-detection.md)), activity
  recognition ([wifi-csi-human-activity-recognition.md](wifi-csi-human-activity-recognition.md)),
  localization ([indoor-localization-wifi.md](../indoor-localization-wifi.md)).
- **Every extractor and how they compare**:
  [csi-toolchains.md](../../projects/csi-toolchains.md) and
  [csi-toolchains-head-to-head.md](../csi-toolchains-head-to-head.md).
- **Reproducible test rig**: [build-a-reproducible-csi-testbed.md](build-a-reproducible-csi-testbed.md).

## References

- nexmon_csi — Secure Mobile Networking Lab: <https://github.com/seemoo-lab/nexmon_csi> (UDP:5500 broadcast transport, per-chip int16/float encoding)
- nexcsi pure-Python decoder: <https://github.com/nexmonster/nexcsi>
- csiread (real-time `pmsg()`, multi-format): <https://github.com/citysu/csiread>
- CSIKit (offline multi-format parser, `csitools.get_CSI`): <https://github.com/Gi-z/CSIKit>
- esp-csi / ESP32-CSI-Tool (CSV `CSI_DATA` format, PyQtGraph `esp_csi_tool.py`): <https://github.com/espressif/esp-csi>
- PicoScenes: <https://ps.zpj.io/>
- PyQtGraph: <https://www.pyqtgraph.org/>
- Matplotlib `FuncAnimation`: <https://matplotlib.org/stable/api/animation_api.html>
