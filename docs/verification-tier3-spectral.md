# Verifying the Tier-3 (Spectral Scan) Claims

> **Adversarial reproduction audit.** Companion to [`verification-tier4.md`](./verification-tier4.md) (arbitrary-waveform TX) and [`verification-tier2-csi.md`](./verification-tier2-csi.md) (CSI). Where those audits asked "can you *transmit* an arbitrary waveform?" and "can you read *per-subcarrier* channel state?", this one asks a narrower, falsifiable question:
>
> **On this chip, today, can an ordinary person get raw baseband FFT bins out of the receiver — a spectrum-analyzer trace — using only public tooling and stock (or lightly patched) kernels?**
>
> Tier 3 on [the ladder](./taxonomy.md) means *spectral / raw-PHY scan*: the radio hands you FFT magnitude bins across the channel, not just decoded packets (Tier 1) or equalized channel estimates (Tier 2). It is the rung where a Wi-Fi part starts to behave like a cheap spectrum analyzer. It is **also the rung most often over-claimed**, because "the silicon has an FFT engine" gets conflated with "there is a public path to the FFT output." Those are not the same statement, and the gap between them is exactly what this audit measures.

The catalog currently marks **~48 parts Tier 3**. This document scrutinizes the four families those marks lean on — **ath9k**, **ath9k_htc**, **ath10k/ath11k**, and **Nexmon/Broadcom** — plus the **Intel/iwlwifi** entries, and emits corrected module records (same ids → they merge) for the over-marks.

**TL;DR of the audit:**

- **Atheros ath9k (AR92xx/AR93xx PCIe)** and **ath10k (QCA 802.11ac)** are the *real* Tier-3 story. Reproducible today on a stock mainline kernel with `CONFIG_ATH9K_DEBUGFS` / `CONFIG_ATH10K_SPECTRAL`, a couple of `echo` commands into debugfs, and [`FFT_eval`](https://github.com/simonwunderlich/FFT_eval). **Verified.**
- **ath9k_htc (AR9271 / AR7010 USB)** works but is second-class: it needs `CONFIG_ATH9K_HTC_DEBUGFS` and rides the HTC/USB transport. Reproducible, with caveats. **Reported → verified.**
- **ath11k (IPQ8074/QCN9074/WCN6855, Wi-Fi 6)** has spectral in-tree (`CONFIG_ATH11K_SPECTRAL`) and FFT_eval added an ath11k mode. Newer, less battle-tested. **Reported.**
- **Broadcom via Nexmon**: **no public open spectral extractor exists.** Nexmon ships CSI, SDR, and jammer projects — *not* a spectral analyzer. Vendor `wl` firmware has a spectral engine, but that is a closed-firmware feature, not a reverse-engineered off-the-ground-floor path. Any Broadcom Tier-3 mark riding "Nexmon spectral" is an **over-mark** → downgrade to Tier 2 (CSI is the verified capability).
- **Intel / iwlwifi**: **no spectral scan is exposed anywhere.** The driver's debug surface is prints, tracing, air-sniffing (monitor), and firmware debugging — no FFT, no spectrum analyzer, no debugfs relay. Any Intel Tier-3 mark is an **over-mark** → downgrade.

---

## 1. What "reproducible spectral scan" actually requires

For an ath-family device the mechanism is identical across ath9k/ath10k/ath11k and is documented in the mainline kernel wireless docs. The chip's baseband already computes an FFT for its own AGC/DFS purposes; the spectral feature *relays those bins to userspace* through a `relayfs` file. The reproduction recipe is:

1. **Kernel built with the spectral debugfs option** — `CONFIG_ATH9K_DEBUGFS` and/or `CONFIG_ATH9K_HTC_DEBUGFS` (which select `ATH9K_COMMON_SPECTRAL`), or `CONFIG_ATH10K_SPECTRAL` / `CONFIG_ATH11K_SPECTRAL`. Most desktop distros ship these **on**; some minimal/embedded kernels do not — the first place a Tier-3 claim silently dies.
2. **debugfs mounted** and the PHY present at `/sys/kernel/debug/ieee80211/phyN/`.
3. **A mode written** to `spectral_scan_ctl`, the scan **triggered**, and the binary TLV stream **read** from the `spectral_scan0` relay file.
4. **A decoder** — `FFT_eval` — to turn the TLV blob into magnitude-vs-frequency.

If any of steps 1–4 has no public path for a given chip, the Tier-3 mark is unsupported. That is the whole test.

### Canonical ath9k reproduction (the gold standard)

```bash
# 0. Confirm the option is compiled in
zgrep -E 'ATH9K_(DEBUGFS|COMMON_SPECTRAL)' /proc/config.gz

# 1. Put the interface on a channel (spectral rides the RX chain)
sudo ip link set wlan0 up
sudo iw dev wlan0 set channel 6

PHY=/sys/kernel/debug/ieee80211/phy0/ath9k

# 2. Arm and trigger a chanscan (or 'background' / 'manual')
echo chanscan  | sudo tee $PHY/spectral_scan_ctl
sudo iw dev wlan0 scan            # drives the sweep in chanscan mode
# ...or for a fixed channel:
# echo background | sudo tee $PHY/spectral_scan_ctl
# echo trigger    | sudo tee $PHY/spectral_scan_ctl

# 3. Pull the raw TLV samples out of the relay file
sudo cat $PHY/spectral_scan0 > /tmp/samples.bin
echo disable | sudo tee $PHY/spectral_scan_ctl

# 4. Decode / visualize
./fft_eval_ath9k /tmp/samples.bin
```

The four modes on `spectral_scan_ctl` are **`disable`**, **`background`** (endless sampling on the current channel during HW idle), **`manual`** (returns a configured count after a `trigger`), and **`chanscan`** (returns samples per channel during a normal `iw scan`). Tuning knobs live alongside it: `spectral_count`, `spectral_period`, `spectral_fft_period`, `spectral_short_repeat`. This is verbatim the mainline-documented interface.

### The data format (don't invent offsets)

Samples arrive as **TLV records** (`fft_sample_tlv` header: `type`, `length`) defined in `drivers/net/wireless/ath/spectral_common.h`, followed by a per-type body in `drivers/net/wireless/ath/ath9k/spectral.h`. HT20 yields one bin block; HT40 yields separate **`lower_bins`** and **`upper_bins`**. The distinct sample types (`FFT_SAMPLE_HT20`, `FFT_SAMPLE_HT20_40`, `FFT_SAMPLE_ATH10K`, and the ath11k variant) are enumerated in that header — **read the header for the exact struct layout and magnitudes; do not hard-code magic offsets from memory.** `FFT_eval` already parses all of these.

For a full, screenshot-level walkthrough see [`walkthroughs/atheros-ath9k-spectral-csi.md`](./walkthroughs/atheros-ath9k-spectral-csi.md).

---

## 2. Verdict table

| Chip / family | Driver | Spectral reproducible today? | How | Caveat |
|---|---|---|---|---|
| **AR9280 / AR9285 / AR9287** (AR928x, PCIe/mini-PCIe) | ath9k | **Yes — verified** | debugfs `spectral_scan_ctl` + FFT_eval | Needs `CONFIG_ATH9K_DEBUGFS`. AR9285 is 1×1 (single bin block); still supported. |
| **AR9227 / AR9220 / AR9223** | ath9k | **Yes — verified** | same | The original chips FFT_eval was written for. |
| **AR9380 / AR9382 / AR9390** (AR93xx, 3×3) | ath9k | **Yes — verified** | same | Best signal quality of the ath9k line. |
| **AR9462 / AR9485 / AR9565** (later 1×1/2×2) | ath9k | **Yes — verified** | same | Low-cost single-stream parts; spectral still exposed. |
| **AR9271 / AR7010** (USB, e.g. TL-WN722N v1) | ath9k_htc | **Yes — with caveats** | needs `CONFIG_ATH9K_HTC_DEBUGFS` | Rides HTC-over-USB; lower sample throughput and more timing jitter than PCIe. Second-class but real. |
| **QCA9880 / QCA988x** (AR988x, 802.11ac) | ath10k | **Yes — verified** | `spectral_scan_ctl`, `spectral_bins` (64/128/256) + FFT_eval | Firmware-dependent; `spectral_count` may be ignored on 20/40 MHz, VHT80 works. |
| **QCA9984 / QCA9888** (AP-class 11ac) | ath10k | **Yes — verified** | same | The workhorse AP chips; 160 MHz-capable. |
| **QCA9887 / QCA9377 / QCA6174** (client 11ac) | ath10k | **Partial / firmware-dependent** | debugfs *may* be present | Mobile/client firmware often omits or gates spectral; QCA6174 in phones is unreliable. Do not assume without testing. |
| **IPQ8074 / QCN9074 / WCN6855** (Wi-Fi 6) | ath11k | **Reported** | `CONFIG_ATH11K_SPECTRAL` + FFT_eval ath11k mode | In-tree but newer; not surfaced in the driver overview doc, and platform/firmware coverage is uneven. |
| **BCM4339 / BCM43455c0 / BCM4358 / BCM4366c0** | brcmfmac + Nexmon | **No (open path)** — over-mark | — | Nexmon ships CSI/SDR/jammer, **not** a spectral extractor. Vendor `wl` has a closed spectral engine only. **Downgrade → Tier 2 (CSI).** |
| **Intel AX210 / AX200 / 9260 / 7265 / 5300** | iwlwifi | **No** — over-mark | — | iwlwifi debug surface = prints/tracing/air-sniffing/fw-debug. **No FFT, no spectral relay anywhere.** CSI exists on 5300 (Halperin) / AX210 (PicoScenes); spectral does not. **Downgrade.** |
| **MediaTek MT7612/MT7615/MT7921** | mt76 | **No public FFT relay** — flag | — | mt76 exposes PHY/DFS debug but **no ath-style `spectral_scan0` relay** to userspace. Treat any Tier-3 mark as unverified. |
| **Realtek RTL88xx** (rtw88/rtw89/out-of-tree) | rtw88/rtl8812au | **No** | — | No public spectral/FFT interface. Monitor+injection only. |

---

## 3. Family-by-family findings

### 3.1 ath9k (AR92xx / AR93xx PCIe) — the real thing, VERIFIED

The mainline docs are unambiguous: spectral analysis is available on **"AR92xx and AR93xx"** devices, reporting **"FFT data as generated by the radio's baseband."** Control is entirely under `/sys/kernel/debug/ieee80211/phy0/ath9k/` (`spectral_scan_ctl`, `spectral_scan0`, `spectral_count`, `spectral_period`, `spectral_fft_period`, `spectral_short_repeat`). `FFT_eval` was *written for* these chips. Reproduction is a five-minute exercise on any distro that ships `CONFIG_ATH9K_DEBUGFS` (Debian/Ubuntu/Fedora do).

**Verdict:** Tier-3 marks on AR9220/AR9223/AR9227, AR9280/AR9285/AR9287, AR9380/AR9382/AR9390, and the later AR9462/AR9485/AR9565 are **correct and verified**. No correction needed; keep `spectral-scan` + `open-firmware`-adjacent framing (driver is open, firmware blob is not, but the interface is public).

### 3.2 ath9k_htc (AR9271 / AR7010 USB) — real, but second-class

The same doc says you need **"one or both of `ATH9K_DEBUGFS` and `ATH9K_HTC_DEBUGFS`"** — the HTC option explicitly enables the USB (HTC) devices. So the AR9271 (1×1, the TL-WN722N **v1** chipset) and AR7010-fronted AR928x USB sticks **can** do spectral. The caveat is transport: FFT bins are streamed over the HTC/USB firmware path, which is slower and jitterier than a PCIe DMA relay, and the option is more often compiled *out* on minimal kernels. It reproduces, but it is not the equal of PCIe ath9k.

**Verdict:** Tier-3 is defensible for AR9271/AR7010 provided the mark carries a "`CONFIG_ATH9K_HTC_DEBUGFS` required; USB-transport limited" annotation. Where the catalog marked it a clean Tier 3 with no caveat, annotate (record below).

### 3.3 ath10k (QCA 802.11ac) — VERIFIED on AP chips, firmware-gated on clients

The ath10k spectral interface mirrors ath9k under `/sys/kernel/debug/ieee80211/phy0/ath10k/`, adding `spectral_bins` (64/128/256 FFT resolution) and returning **`FFT_SAMPLE_ATH10K`** TLVs decoded by FFT_eval. Reproduction on **QCA988x / QCA9984 / QCA9888** is well-trodden and **verified**. The honest caveat, straight from the docs, is that `spectral_count` **"may be ignored for 20 MHz and 40 MHz"** channels while VHT80 behaves — and that the whole feature is **firmware-image-dependent**. Client-class parts (QCA9377, QCA6174 in laptops/phones) frequently ship firmware that does not expose it. Mark those **partial/unverified**, not clean Tier 3.

### 3.4 ath11k (Wi-Fi 6) — REPORTED, newer

Spectral is implemented in ath11k (`CONFIG_ATH11K_SPECTRAL`) and **FFT_eval gained an ath11k decode path**, so IPQ8074/QCN9074/WCN6855 can produce FFT bins on recent kernels. It is *not* described in the driver's user-facing overview doc, coverage across platforms/firmware is uneven, and it is far less exercised than ath9k/ath10k. **Reported**, not verified — flag accordingly if any ath11k part was stamped a confident Tier 3.

### 3.5 Broadcom / Nexmon — the headline over-mark

This is the load-bearing myth. **Nexmon does not provide a spectral analyzer.** Its project set is Monitor Mode + Frame Injection (core), **CSI** (`nexmon_csi`), **SDR** (`nexmon.org/sdr`), and **jammer** (`nexmon.org/jammer`). None is a spectral/FFT extractor. `nexmon_csi` supports BCM4339/BCM43455c0/BCM4358/BCM4366c0 — and what it yields is **CSI (Tier 2)**, not raw spectral bins.

Broadcom silicon *does* have a spectral engine, reachable on some vendor firmwares via `wl` (e.g. `wl phy` spectral analysis on certain Asus/DD-WRT builds). But that is a **closed-firmware vendor feature**, not a reverse-engineered, publicly documented off-the-ground path — it fails the Tier-3 "public path to the FFT output" test the same way a locked calibration mode would. Under [the taxonomy](./taxonomy.md), that is Tier 2 with a *theoretical* spectral note, not Tier 3.

**Verdict:** every Broadcom entry marked Tier 3 on the strength of "Nexmon spectral" is an **over-mark**. Downgrade to **Tier 2**, keep `csi`, drop `spectral-scan`, and record the vendor-`wl` spectral engine as `status: reported/theoretical` in prose. Corrected records below.

### 3.6 Intel / iwlwifi — no spectral, anywhere

Intel is the cleanest over-mark to kill. The iwlwifi documentation's entire debug surface is **Prints, Tracing, Air sniffing (monitor), and Firmware Debugging** — there is **no spectral scan, no FFT, no spectrum-analyzer, no `spectral_scan0` relay**. Intel firmware is closed and the baseband FFT is never surfaced to users. CSI *is* obtainable on specific Intel parts (the classic IWL5300 via the Halperin CSI Tool; AX200/AX210 via PicoScenes) — but **CSI is Tier 2 and spectral is not CSI.** There is no public route to Intel FFT bins.

**Verdict:** any Intel/iwlwifi entry at Tier 3 is wrong. Downgrade to **Tier 2** (parts with a real CSI toolchain: 5300, AX200, AX210) or **Tier 1** (parts with only monitor mode). Drop `spectral-scan` in all cases. Corrected records below.

### 3.7 MediaTek (mt76) and Realtek — flag, not verified

`mt76` exposes DFS/PHY debug hooks but **no ath-style userspace FFT relay**; there is no `FFT_eval`-class public decode path. Realtek (rtw88/rtw89 and the out-of-tree `rtl8812au` line) offers monitor+injection only. Neither supports a reproducible Tier-3 spectral scan today. If any MT76xx or RTL88xx entry carries a Tier-3 mark, treat it as **unverified** and demote to its real Tier 1/2 evidence.

---

## 4. Scoreboard: where the ~48 Tier-3 marks stand

| Bucket | Reproducible? | Action |
|---|---|---|
| ath9k AR92xx/AR93xx (PCIe) | **Verified** | Keep Tier 3. |
| ath9k_htc AR9271/AR7010 (USB) | **With caveats** | Keep Tier 3 **+ annotate** (`ATH9K_HTC_DEBUGFS`, USB-limited). |
| ath10k QCA988x/QCA9984/QCA9888 | **Verified** | Keep Tier 3. |
| ath10k QCA9377/QCA6174 (client) | **Firmware-gated** | Annotate → *partial*. |
| ath11k IPQ8074/QCN9074/WCN6855 | **Reported** | Keep, mark `status: reported`. |
| Broadcom "Nexmon spectral" | **No open path** | **Downgrade → Tier 2 (CSI).** |
| Intel iwlwifi | **No** | **Downgrade → Tier 2/1.** |
| MediaTek mt76 / Realtek | **No** | **Downgrade / flag unverified.** |

The audit's headline: the genuine Tier-3 population is essentially **Qualcomm Atheros ath9k + ath10k (+ nascent ath11k)**. The over-marks cluster on **Intel** (no spectral at all) and **Broadcom** (CSI mislabeled as spectral). Corrected module records for those over-marks follow in `modules[]` and merge on id.

---

## 5. Regulatory / safety note

Spectral scan is **receive-only** — it reads the baseband FFT, it does not transmit — so it carries none of the TX-emission risk that gates Tier-4 work. The only practical caution: `background` mode keeps the radio sampling and can starve normal Wi-Fi traffic on that interface, and `chanscan` piggybacks on active scans that briefly leave your channel. Neither raises legal issues. (Contrast with [`verification-tier4.md`](./verification-tier4.md), where arbitrary TX absolutely does.)

---

## 6. References

- ath9k spectral scan — mainline kernel wireless docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
- ath10k spectral — mainline kernel wireless docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath10k/spectral.html>
- ath11k driver docs (supported devices; spectral in-tree via `CONFIG_ATH11K_SPECTRAL`): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html>
- iwlwifi driver docs (debug surface — no spectral/FFT): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html>
- `FFT_eval` — spectral sample decoder/visualizer (ath9k/ath9k_htc/ath10k/ath11k): <https://github.com/simonwunderlich/FFT_eval>
- Nexmon (Monitor/Injection; CSI/SDR/jammer projects — no spectral extractor): <https://github.com/seemoo-lab/nexmon>
- `nexmon_csi` (CSI, Tier 2 — not spectral): <https://github.com/seemoo-lab/nexmon_csi>
- Taxonomy / SDR ladder: [`taxonomy.md`](./taxonomy.md)
- Reproducible ath9k spectral + CSI walkthrough: [`walkthroughs/atheros-ath9k-spectral-csi.md`](./walkthroughs/atheros-ath9k-spectral-csi.md)
- Sibling audits: [`verification-tier4.md`](./verification-tier4.md), [`verification-tier2-csi.md`](./verification-tier2-csi.md)
- Chip pages: [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md), [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md), [`../chips/intel.md`](../chips/intel.md)
