# End-to-end: a Wi-Fi CSI human-activity-recognition (HAR) pipeline

This walkthrough takes you from raw Channel State Information (CSI) to a trained,
evaluated activity classifier — with runnable code at every step. It is deliberately
minimal but real: no pseudo-code, no invented tensors. Everything here runs against
either a live [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) capture on a
Raspberry Pi or a public dataset (UT-HAR, Widar3.0, SignFi).

CSI-based sensing is the *receive-side* twin of the SDR ladder that the rest of this
catalog documents: a Tier-2 chip (see [`../verification-tier2-csi.md`](../verification-tier2-csi.md))
hands you per-subcarrier complex channel estimates, and machine learning turns those
into "someone is walking / falling / gesturing." This page is the ML half of that story.

**Related pages**
- [`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md) — capturing and cleaning CSI on a Pi (prerequisite for the live path).
- [`../ml-csi-sensing.md`](../ml-csi-sensing.md) — models, losses, and the domain-generalization literature in depth.
- [`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md) — dataset index (formats, sizes, download links, licenses).
- [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md) — CSIKit, PicoScenes, Nexmon CSI, ESP32-CSI-Tool.
- [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md) — the BCM43455c0 that nexmon_csi targets.

> **Scope note.** HAR here means coarse whole-body/gesture classification, not
> imaging or identification. Sensing people through Wi-Fi has obvious privacy
> implications; only capture in spaces you control and with informed consent. See
> [`../rf-safety-and-legal.md`](../rf-safety-and-legal.md). No transmission is
> involved in this pipeline — CSI is estimated from packets you passively receive
> (or from packets you send to *yourself*), so there is no new spectrum-emission
> risk beyond normal Wi-Fi operation.

---

## 0. The pipeline at a glance

```
 ┌─ source ──────────┐   ┌─ clean ────────┐   ┌─ window ───┐   ┌─ model ──────┐   ┌─ eval ───────────┐
 │ nexmon_csi pcap   │   │ drop null SCs  │   │ sliding    │   │ CNN / LSTM   │   │ in-domain acc    │
 │  or               │──▶│ amplitude+phase│──▶│ windows,   │──▶│ (PyTorch)    │──▶│ cross-domain acc │
 │ UT-HAR / Widar /  │   │ Hampel + LPF   │   │ per-window │   │              │   │ (the honest one) │
 │ SignFi .mat/.csv  │   │ phase sanitize │   │ labels     │   │              │   │ confusion matrix │
 └───────────────────┘   └────────────────┘   └────────────┘   └──────────────┘   └──────────────────┘
```

Two batteries-included libraries do most of the heavy lifting, and this guide leans on both:

| Library | What it gives you | License | Repo |
|---|---|---|---|
| **CSIKit** (Glenn Forbes) | Parses nexmon / Intel 5300 / Atheros / ESP32 / PicoScenes captures into amplitude & phase, plus CLI plotting | MIT | [github.com/Gi-z/CSIKit](https://github.com/Gi-z/CSIKit) |
| **SenseFi** (Yang et al., *Patterns* 2023) | PyTorch dataloaders + reference models (MLP, LeNet, ResNet18/50/101, RNN/GRU/LSTM/BiLSTM, CNN+GRU, ViT) for UT-HAR, NTU-Fi, Widar | MIT | [github.com/xyanchen/WiFi-CSI-Sensing-Benchmark](https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark) |

If you just want a leaderboard-style baseline, SenseFi's `run.py` is one command (Step 5b).
The rest of this page shows what happens underneath so you can adapt it to *your own* Pi capture.

```bash
python3 -m venv csi && source csi/bin/activate
pip install "torch>=2.0" numpy scipy scikit-learn matplotlib
pip install CSIKit            # parsing/cleaning
# SenseFi is used from a git checkout, not pip:
git clone https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark
```

---

## 1. Pick a source

You have two realistic starting points. Do the **dataset path first** even if your goal
is the Pi — it lets you debug the model with clean, labeled data before you fight with
live capture noise.

### 1a. Live: nexmon_csi on a Raspberry Pi

The BCM43455c0 (Pi 3B+/4/Zero 2 W, [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md))
with the nexmon_csi patch emits one UDP frame of CSI per received Wi-Fi frame. Follow
[`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md) end-to-end first; the
short version:

```bash
# configure: 80 MHz on ch 36, 256 subcarriers, listen for a specific TX MAC
makecsiparams -c 36/80 -C 1 -N 1 -m AA:BB:CC:DD:EE:FF -b 0x88
nexutil -Ideth0 -s500 -b -l34 -v<base64-from-makecsiparams>
ip link set up dev wlan0
# capture to pcap
tcpdump -i wlan0 dst port 5500 -vv -w walk_run_$(date +%s).pcap
```

To get *labeled* data, script the session: print a countdown, have the subject perform
one activity per fixed interval, and record start/stop timestamps to a sidecar CSV. You
label windows by timestamp in Step 3.

At 80 MHz nexmon_csi reports **256 subcarriers per antenna core**; the usable ones after
dropping guard/null/pilot subcarriers are ~234 (see Step 2). The BCM43455c0 exposes a
single spatial stream, so a live Pi capture is `1 × T × ~234` per window — narrower than
the 3×3 MIMO of the Intel-5300 datasets, which matters for accuracy.

### 1b. Public datasets (recommended for first run)

| Dataset | Hardware | Classes | Per-sample shape (as used by SenseFi) | Domain axis (why cross-domain is hard) |
|---|---|---|---|---|
| **UT-HAR** (Yousefi 2017) | Intel 5300, 30 SC × 3×3 | 7 (lie down, fall, walk, run, sit down, stand up, empty) | `1 × 250 × 90` | single room, few subjects — no built-in domain split |
| **NTU-Fi HAR** | Atheros, 114 SC × 3 | 6 | `3 × 114 × 500` | rooms/receivers |
| **Widar3.0** (Zheng 2019) | Intel 5300, 6 receivers | 22 gestures | BVP `22 × 20 × 20` velocity profiles | user × room × orientation (16 domains) |
| **SignFi** (Ma 2018) | Intel 5300 | 276 sign gestures | `200 × 30 × 3×3` complex | lab vs home, 5 users |

Full download/format notes: [`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md).
UT-HAR ships as plain CSV traces (amplitude only, already 90-column) in
[ermongroup/Wifi_Activity_Recognition](https://github.com/ermongroup/Wifi_Activity_Recognition);
SenseFi redistributes a pre-sliced `.csv`/`.npy` version under `Data/`.

The `90` in UT-HAR is `30 subcarriers × 3 receive antennas`, amplitude only — the original
release already discarded phase. That is why UT-HAR examples below use amplitude-only input.

---

## 2. Load & clean CSI (amplitude and phase)

This mirrors [`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md), but as a
reusable Python function. Parse with CSIKit, then apply four corrections in order:
**(1)** drop null/pilot subcarriers, **(2)** compute amplitude & phase, **(3)** sanitize
phase (remove the linear CFO/SFO slope), **(4)** denoise amplitude (Hampel outlier
removal + low-pass).

```python
import numpy as np
from scipy.signal import butter, filtfilt
from CSIKit.reader import get_reader
from CSIKit.util import csitools

def load_nexmon_pcap(path):
    """Return complex CSI array of shape (frames, subcarriers) from a nexmon pcap."""
    reader = get_reader(path)
    data   = reader.read_file(path)
    # get_CSI returns (matrix, n_frames, n_subcarriers); keep complex for phase
    csi, n_frames, n_sub = csitools.get_CSI(data, metric="amplitude")
    # csi is (frames, sub, rx, tx); nexmon BCM43455c0 -> rx=tx=1
    complex_csi = np.stack([f.csi_matrix for f in data.frames])  # complex
    return complex_csi.reshape(n_frames, -1)                     # (T, sub)

# --- 2.1 drop the subcarriers that carry no channel estimate -------------------
# 80 MHz 802.11ac: nulls at DC and band edges, plus pilots. Indices below are the
# 802.11ac 80 MHz guard/null set; VERIFY against your capture by plotting the mean
# amplitude per subcarrier — nulls sit near zero. (Do NOT trust a hard-coded list
# blindly; nexmon's subcarrier order depends on the FFT layout for your channel BW.)
NULL_SC_80MHZ = np.array([-128,-127,-126,-125,-124,-123,-1,0,1,123,124,125,126,127])
def drop_null_subcarriers(csi, bw_bins=256):
    keep = np.setdiff1d(np.arange(-bw_bins//2, bw_bins//2), NULL_SC_80MHZ)
    idx  = keep + bw_bins//2
    return csi[:, idx]

# --- 2.2 amplitude and phase ---------------------------------------------------
def amp_phase(csi):
    return np.abs(csi), np.angle(csi)   # amplitude (linear), wrapped phase [-pi, pi]

# --- 2.3 phase sanitization ----------------------------------------------------
# Raw CSI phase is corrupted by carrier freq offset (CFO), sampling freq offset (SFO)
# and packet detection delay -> a per-packet linear slope + constant across subcarriers.
# The standard fix (Wang et al. "PhaseFi") removes the best-fit line across subcarriers.
def sanitize_phase(phase):
    T, S = phase.shape
    k = np.arange(S)
    out = np.empty_like(phase)
    for t in range(T):
        p = np.unwrap(phase[t])                 # undo 2*pi wraps across subcarriers
        a = (p[-1] - p[0]) / (S - 1)            # slope from CFO/SFO
        b = p.mean()                            # constant offset
        out[t] = p - (a * k + b)                # linearly detrended phase
    return out

# --- 2.4 amplitude denoise: Hampel outlier removal + Butterworth low-pass ------
def hampel(x, k=7, n_sigma=3.0):
    """Replace spikes with local median (per time series). x: (T,)"""
    x = x.copy(); L = 1.4826
    for i in range(len(x)):
        lo, hi = max(0, i-k), min(len(x), i+k+1)
        med = np.median(x[lo:hi]); mad = L * np.median(np.abs(x[lo:hi]-med))
        if mad and abs(x[i]-med) > n_sigma*mad:
            x[i] = med
    return x

def denoise_amp(amp, fs=100.0, cutoff=10.0):
    b, a = butter(4, cutoff/(fs/2), btype="low")
    out = np.empty_like(amp)
    for s in range(amp.shape[1]):
        col = hampel(amp[:, s])
        out[:, s] = filtfilt(b, a, col)         # zero-phase LPF: human motion < ~10 Hz
    return out
```

Notes that matter for correctness:

- **Verify the null-subcarrier list against your own capture.** Plot mean amplitude per
  subcarrier index; the nulls are the near-zero bins. Hard-coded indices are
  bandwidth- and layout-specific — this is exactly the "show HOW to find the value in
  the reader's own dump" rule from the rest of the catalog.
- **`fs` is your CSI rate**, i.e. how many frames/sec the TX sends (set by your ping/iperf
  flood or the AP beacon rate), *not* the Wi-Fi symbol rate. Estimate it from packet
  timestamps: `fs ≈ (n_frames-1)/(t_last - t_first)`.
- **UT-HAR is amplitude-only and pre-cleaned**, so for the dataset path you skip 2.1–2.3
  and load the CSV directly (Step 3). Keep this function for the live Pi path.

---

## 3. Window & label

Activities live in time, so we classify fixed-length windows rather than single packets.
Use a sliding window with overlap; label each window by the activity active during it.

```python
def sliding_windows(x, win=250, stride=125):
    """x: (T, F) -> (N, win, F). 250 frames @ ~100 Hz ~= 2.5 s; 50% overlap."""
    return np.stack([x[i:i+win] for i in range(0, len(x)-win+1, stride)])

def label_windows(starts, win, stride, T, intervals):
    """intervals: list of (t0, t1, class_id) in FRAME index. Majority-vote label/window."""
    labels = []
    for i in range(0, T-win+1, stride):
        seg = np.zeros(win, dtype=int)
        for (t0, t1, c) in intervals:
            lo, hi = max(0, t0-i), min(win, t1-i)
            if hi > lo: seg[lo:hi] = c
        labels.append(np.bincount(seg).argmax())
    return np.array(labels)
```

For UT-HAR you don't slide anything yourself — the redistributed set is already sliced to
`1 × 250 × 90` samples with integer labels 0–6. Load it directly:

```python
import numpy as np, glob, os

def load_ut_har(root):
    """SenseFi layout: <root>/UT_HAR/data/*.csv, <root>/UT_HAR/label/*.csv"""
    X, Y = {}, {}
    for split in ("train", "val", "test"):
        x = np.loadtxt(glob.glob(f"{root}/UT_HAR/data/X_{split}*.csv")[0])
        y = np.loadtxt(glob.glob(f"{root}/UT_HAR/label/y_{split}*.csv")[0])
        X[split] = x.reshape(len(x), 1, 250, 90).astype("float32")
        Y[split] = y.astype("int64")
    return X, Y
```

Always **normalize per training-set statistics** and apply the same to val/test — never
fit the scaler on the whole set (that leaks). Amplitude scale drifts with distance and
gain, so standardize:

```python
mu, sd = X["train"].mean(), X["train"].std()
for s in X: X[s] = (X[s] - mu) / (sd + 1e-8)
```

---

## 4. Model — a minimal but real CNN and LSTM (PyTorch)

Two baselines. The CNN treats a window as a 1-channel image `(1, 250, 90)`; the LSTM
treats it as a sequence of 90-dim feature vectors over 250 time steps. Both are small
enough to train on CPU in minutes for UT-HAR.

```python
import torch, torch.nn as nn

class CSICNN(nn.Module):
    """Input (B,1,250,90) -> logits (B,n_cls). ~0.3M params."""
    def __init__(self, n_cls=7):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.c = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(32*4*4, n_cls))
    def forward(self, x): return self.c(self.f(x))

class CSILSTM(nn.Module):
    """Input (B,1,250,90) -> treat as (B,250,90) sequence -> logits."""
    def __init__(self, n_cls=7, feat=90, hidden=128):
        super().__init__()
        self.rnn = nn.LSTM(feat, hidden, num_layers=2, batch_first=True, dropout=0.3)
        self.head = nn.Linear(hidden, n_cls)
    def forward(self, x):
        x = x.squeeze(1)                 # (B,250,90)
        out, _ = self.rnn(x)
        return self.head(out[:, -1])     # last time step
```

Training loop — plain, no framework:

```python
from torch.utils.data import TensorDataset, DataLoader

def make_loader(X, Y, bs=64, shuffle=False):
    ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(Y))
    return DataLoader(ds, batch_size=bs, shuffle=shuffle)

def train(model, tr, va, epochs=30, lr=1e-3, dev="cpu"):
    model.to(dev); opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    for ep in range(epochs):
        model.train()
        for xb, yb in tr:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad(); loss = lossf(model(xb), yb); loss.backward(); opt.step()
        acc = evaluate(model, va, dev)
        print(f"epoch {ep+1:2d}  val_acc {acc:.3f}")
    return model

@torch.no_grad()
def evaluate(model, loader, dev="cpu"):
    model.eval(); correct = total = 0
    for xb, yb in loader:
        pred = model(xb.to(dev)).argmax(1).cpu()
        correct += (pred == yb).sum().item(); total += len(yb)
    return correct / total

if __name__ == "__main__":
    X, Y = load_ut_har("WiFi-CSI-Sensing-Benchmark/Data")
    mu, sd = X["train"].mean(), X["train"].std()
    for s in X: X[s] = (X[s] - mu) / (sd + 1e-8)
    tr = make_loader(X["train"], Y["train"], shuffle=True)
    va = make_loader(X["val"],   Y["val"])
    te = make_loader(X["test"],  Y["test"])
    model = train(CSICNN(7), tr, va, epochs=30)
    print("TEST:", evaluate(model, te))
```

**Raw vs. features.** The code above feeds cleaned amplitude directly (raw-ish) and lets
the CNN learn features — the modern default and what SenseFi benchmarks. Classic pipelines
instead hand-engineered features per window (spectrogram via STFT, PCA of the subcarrier
covariance, DWT energy, mean/var/entropy) and fed an SVM/random forest. Feature engineering
still helps in low-data regimes and for interpretability; see
[`../ml-csi-sensing.md`](../ml-csi-sensing.md) for the STFT/DWT recipes and the
Doppler/velocity-profile features (BVP) that Widar uses.

---

## 5. Evaluate — and the honest part

### 5a. In-domain (the flattering number)

With the standard UT-HAR train/val/test split (all from the same room and small subject
pool), the tiny CNN above reaches roughly **90–96%** test accuracy; SenseFi's ResNet18/GRU
report similar high-90s on UT-HAR and NTU-Fi. Add a confusion matrix — fall vs. sit-down and
run vs. walk are the usual confusions:

```python
from sklearn.metrics import confusion_matrix, classification_report
yt = np.concatenate([yb.numpy() for _, yb in te])
yp = np.concatenate([model(xb).argmax(1).detach().numpy() for xb, _ in te])
print(confusion_matrix(yt, yp))
print(classification_report(yt, yp, digits=3))
```

### 5b. One-command SenseFi baseline (sanity check)

```bash
cd WiFi-CSI-Sensing-Benchmark
python run.py --model ResNet18 --dataset UT_HAR_data
python run.py --model GRU      --dataset NTU-Fi_HAR
```

If your hand-rolled numbers are wildly off SenseFi's, suspect normalization or a
train/test leak before you suspect the model.

### 5c. Cross-domain: the accuracy collapse

**This is the single most important slide in Wi-Fi sensing, and most demos hide it.**
A model trained in room A on subjects {1,2,3} facing north will *not* keep its accuracy in
room B, on subject 4, facing east. In-domain 95% routinely collapses to **40–70% (often
near chance for hard splits)** cross-domain. Causes:

- **Multipath is environment-specific.** The CNN learns the room's reflections, not the
  motion. Change the furniture and the "signature" changes.
- **Subject physiology & style** shift amplitude/Doppler distributions.
- **Orientation & position** rotate the whole feature geometry.
- **Hardware**: different NIC, antenna spacing, AGC, CFO behavior.

Measure it honestly with a **leave-one-domain-out** protocol instead of a random split.
Widar3.0 is built for exactly this — it ships explicit `user / room / orientation` domain
labels:

```python
# Leave-one-user-out on Widar (schematic): train on users != held_out, test on held_out
def loo_split(samples, domains, held_out):
    tr = [s for s, d in zip(samples, domains) if d != held_out]
    te = [s for s, d in zip(samples, domains) if d == held_out]
    return tr, te
# report the AVERAGE over every held-out domain, not the best one.
```

Report the mean over all held-out folds, and always publish both the in-domain and
cross-domain numbers side by side.

### 5d. What actually helps cross-domain

- **Domain-invariant inputs.** Widar's **Body-coordinate Velocity Profile (BVP)** projects
  CSI-Doppler into a body-relative velocity space that cancels much of the orientation/room
  dependence — that is why Widar is distributed as BVP tensors, not raw CSI.
- **Domain adaptation / adversarial training** (DANN-style gradient reversal), **few-shot
  fine-tuning** on a handful of target-domain samples, and **data augmentation** (subcarrier
  dropout, time warping, adding synthetic multipath).
- **More diverse training data** beats every clever loss. Collect across rooms/subjects.

Details and references in [`../ml-csi-sensing.md`](../ml-csi-sensing.md).

---

## 6. Deploy

Three realistic targets, cheapest first.

### 6a. On-Pi inference (edge)

Export to TorchScript and run on the same Pi that captures CSI — no cloud round-trip:

```python
scripted = torch.jit.script(model.eval())
scripted.save("csi_har.pt")
```

```python
# infer_live.py — ring-buffer the last `win` CSI frames, classify continuously
import torch, numpy as np, collections
model = torch.jit.load("csi_har.pt").eval()
buf = collections.deque(maxlen=250)
labels = ["lie","fall","walk","run","sit","stand","empty"]
def on_frame(complex_csi_row):                 # call from your nexmon UDP reader
    amp = np.abs(complex_csi_row)              # + your Step-2 cleaning
    buf.append(amp)
    if len(buf) == 250:
        x = torch.from_numpy(np.stack(buf)[None, None].astype("float32"))
        print(labels[model(x).argmax(1).item()])
```

For the live path, wire `on_frame` into a small UDP listener on port 5500 (the nexmon_csi
sink) and apply the **same normalization statistics** you saved from training. Quantize
(`torch.ao.quantization`) if you need more headroom on a Pi Zero 2 W. A 2-layer CNN infers
in well under the 2.5 s window budget on a Pi 4, so classification keeps up with capture.

### 6b. The reality check before you deploy

- **You trained in domain A.** Section 5c applies to your product too. Either constrain
  deployment to the trained environment, or collect target-domain data and fine-tune.
- **CSI rate must match.** If training data was ~100 Hz and your AP only beacons at 10 Hz,
  windows won't align — force a steady CSI rate with an `iperf`/`ping -f` flood from the TX.
- **Calibration drift.** AGC and temperature shift amplitude scale over hours; re-estimate
  normalization or use per-window standardization at inference.

### 6c. Retrain loop

Log misclassified windows (with consent), periodically re-fit on the growing target-domain
set, and re-export. This closes the gap 5c opens far more reliably than any single-shot
model.

---

## 7. Reproducibility checklist

- [ ] Fix seeds (`torch.manual_seed`, `np.random.seed`) and report hardware.
- [ ] Report the **split protocol** (random vs. leave-one-domain-out) — not just accuracy.
- [ ] Publish **in-domain AND cross-domain** numbers.
- [ ] State CSI rate, bandwidth, subcarrier count, and cleaning steps (Step 2).
- [ ] Normalization fit on train only.
- [ ] Confusion matrix, not just top-line accuracy.

---

## References

- SenseFi library & paper — Jianfei Yang et al., "SenseFi: A library and benchmark on deep-learning-empowered WiFi human sensing," *Patterns* (Cell Press), 2023. Code: <https://github.com/xyanchen/WiFi-CSI-Sensing-Benchmark> · Paper: <https://www.cell.com/patterns/fulltext/S2666-3899(23)00020-9> · Preprint: <https://arxiv.org/abs/2207.07859>
- CSIKit — Glenn Forbes, CSI parsing/visualization toolkit: <https://github.com/Gi-z/CSIKit>
- nexmon_csi — Schulz, Wegemer, Hollick (SEEMOO Lab): <https://github.com/seemoo-lab/nexmon_csi>
- UT-HAR / Yousefi et al., "A Survey on Behavior Recognition Using WiFi Channel State Information," *IEEE Communications Magazine*, 2017: <https://arxiv.org/abs/1708.01468> · Data: <https://github.com/ermongroup/Wifi_Activity_Recognition>
- Widar3.0 — Zheng et al., "Zero-Effort Cross-Domain Gesture Recognition with Wi-Fi," *MobiSys* 2019: <http://tns.thss.tsinghua.edu.cn/widar3.0/> · Paper: <https://dl.acm.org/doi/10.1145/3307334.3326081>
- SignFi — Ma, Zhou, Wang, Wang, "SignFi: Sign Language Recognition Using WiFi," *Proc. ACM IMWUT* 2018: <https://github.com/yongsen/SignFi> · Paper: <https://dl.acm.org/doi/10.1145/3191755>
- PhaseFi phase-sanitization background — Wang et al., "PhaseFi: Phase Fingerprint for Indoor Localization with a Deep Learning Approach," *IEEE GLOBECOM* 2015: <https://ieeexplore.ieee.org/document/7417517>
- PyTorch: <https://pytorch.org/docs/stable/index.html>
