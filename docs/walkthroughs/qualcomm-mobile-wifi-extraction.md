# Extracting Wi-Fi Data from Qualcomm Mobile Chips (The Hard Road)

> **Cycle 6 — new walkthrough.** Honest scope: this page is about the Qualcomm Wi-Fi silicon actually inside phones and tablets — the WCN39xx combo chips and the QCA6xxx / FastConnect PCIe combos — not the discrete Atheros PCIe cards (AR9300/QCA9300) that the classic CSI tools target. The short version: on stock Android this is **much harder than Broadcom (nexmon) or Intel (iwlwifi)**, and most of what you can realistically get is *diagnostic metadata*, not raw IQ or clean per-subcarrier CSI. Everything optimistic below is marked `reported`/`theoretical` on purpose.

See also: [`../../chips/qualcomm-atheros.md`](../../chips/qualcomm-atheros.md) · [`../../docs/firmware-reversing.md`](../../docs/firmware-reversing.md) · contrast with the easy road: [`./nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md) · [`../../docs/true-sdr-comparison.md`](../../docs/true-sdr-comparison.md) · the sibling cellular story: [`../../chips/cellular-basebands.md`](../../chips/cellular-basebands.md).

---

## 1. Why nexmon does not apply here

[nexmon](https://github.com/seemoo-lab/nexmon) and [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) are patchers for **Broadcom/Cypress** FullMAC firmware (the BCM43xx / CYW43xx D11 cores). They work because SEEMOO reverse-engineered that specific firmware, found the RX path, and injected code that dumps the chip's internal channel estimate out over UDP. None of that transfers to Qualcomm:

- **Different silicon, different firmware.** Qualcomm/Atheros WLAN firmware is a completely separate codebase running on an on-chip microcontroller, driven over Qualcomm's **WMI** (Wireless Module Interface) command/event protocol. There is no nexmon-style patch framework for it, and no public firmware symbol maps of the quality nexmon has for Broadcom.
- **FullMAC + closed firmware.** WCN39xx and QCA6xxx are FullMAC: association, aggregation, rate control and the entire PHY live in the firmware/hardware, and the host only sees cooked 802.11 (or even just Ethernet-framed) packets. The channel estimate the beamformer computes never leaves the chip through any documented interface.
- **Signed / fused images on phones.** Production phones ship secure-boot-chained, vendor-signed WLAN firmware. You generally cannot just drop in a patched `.bin` the way early nexmon targets (Nexus 5 BCM4339) allowed.

So the Broadcom playbook — "patch firmware, get CSI over UDP" — has **no working equivalent** on Qualcomm mobile parts today. What you have instead is one genuinely useful asset: the **host driver is source-available**.

---

## 2. The one big advantage: `qcacld-3.0` is source-available

Qualcomm publishes the Linux/Android WLAN **host** driver as source through the Code Linaro Organization (CLO, formerly CodeAurora Forum / CAF):

- **qcacld-3.0** — *Qualcomm Atheros Connectivity Layer Driver, gen 3* — the cfg80211 host driver for WCN39xx and QCA6xxx combos on Android:
  <https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qcacld-3.0>
- Companion component repos on the same host:
  - `fw-api` — the WMI / firmware-interface headers (the contract between host and firmware).
  - `qca-wifi-host-cmn` (a.k.a. `cmn`) — shared "converged" host code (data path, spectral, etc.).
  - `qcacld-3.0` links against both; production trees vendor them under `drivers/staging/`.

License is a permissive **ISC/BSD-style** grant, so you can read, modify and rebuild it. This is the single lever that makes the hard road passable at all — **you can change what the host asks the firmware for, and how it handles what comes back**, even though you cannot change the firmware.

Two hard caveats:

1. **The driver is not the PHY.** qcacld sends WMI commands and receives WMI events plus a DMA'd data/RX path. If the firmware never emits per-subcarrier CSI over WMI, no amount of driver hacking conjures it. The driver is a *window*, sized by whatever the firmware chooses to expose.
2. **Branch matching is brutal.** qcacld has thousands of tags; a build must match your kernel version *and* the specific firmware branch (e.g. `WLAN.HL.*` for WCN3990-class, `WLAN.HSP.*` for QCA6390-class). Mismatched host/firmware = WMI version mismatch = no init. Getting a clean custom build usually means starting from your device's kernel source tree (vendor kernel), not mainline.

---

## 3. What the driver actually exposes

Ranked from most-real to most-wishful.

### 3.1 Fine Timing Measurement / RTT (802.11mc) — real, Tier ~1 ranging
The cleanest *measurement* you can get on stock, unrooted Android. Qualcomm combos (QCA6174 onward) support **802.11mc FTM**, surfaced through the Android Wi-Fi HAL and the public [`WifiRttManager`](https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager) API. Device support is gated by `android.hardware.wifi.rtt.xml` and firmware. Accuracy is a couple of metres (802.11mc) down to ~0.5 m (802.11az on newer parts). See <https://source.android.com/docs/core/connect/wifi-rtt>. This is *distance/time-of-flight*, not channel state — but it is a legitimate, documented physical-layer observable, no root required.

### 3.2 Link-layer stats, RSSI-per-chain, scan results — real, Tier 0–1
The Qualcomm Wi-Fi HAL (`libwifi-hal-qcom`, on top of qcacld's vendor nl80211 commands) exposes gscan, link-layer stats, and debug ring buffers. Per-antenna RSSI and rate info are available. Coarse, but scriptable and stable.

### 3.3 pktlog — firmware packet logging — real, Tier 1 metadata (the workhorse)
`pktlog` is Qualcomm's firmware diagnostic ring: for each TX/RX PPDU the firmware logs descriptors — MCS/rate, per-chain RSSI, timestamps, aggregation info, TX status. On Android this is pulled by the **`cnss_diag`** userspace daemon (or `athdiag` on older stacks) writing to `/data/vendor/wifi/` (or `/data/misc/wifi/`); on the ath10k lineage the analogous feature is exposed via debugfs and captured into Wireshark. Decode with Qualcomm's pktlog parser tooling or community scripts.

- **What you get:** rich per-packet PHY *metadata*. Enough for rate/link forensics, coarse motion inference from RSSI/rate churn, and PPDU timing.
- **What you do NOT get:** raw IQ, and — in the general case — **not** clean per-subcarrier CSI. Some 802.11ax firmware pktlog variants carry sounding-adjacent fields; whether usable CSI can be recovered from them is `reported`/unverified and firmware-branch-specific. Do not assume it.

### 3.4 Monitor mode / "packet capture mode" — partial, chip- and firmware-dependent
qcacld-3.0 carries a **monitor / packet-capture** feature (build flag around `CONFIG_WLAN_PKT_CAPTURE`, driver `con_mode`/vendor-command controlled) on some QCA6390-class firmware. When present it gives promiscuous 802.11 RX with radiotap-ish metadata — useful, but:
- Availability depends on the exact firmware branch shipped on your device; many production images disable it.
- **Injection is generally not supported** through this path. Treat TX/injection as `theoretical` on mobile Qualcomm unless you have proven it on your specific part.

### 3.5 Raw per-subcarrier CSI to the host — essentially not exposed
Qualcomm firmware computes channel estimates internally for beamforming/rate control, but there is **no documented WMI event that streams per-subcarrier CSI to the host** on shipping mobile firmware. Extracting it would require firmware RE at the nexmon level of effort, which for this silicon **has not been publicly done and published in usable form**. Status: `theoretical`.

---

## 4. The escape hatch: same silicon, different driver (ath11k)

Here is the important nuance the "phone" framing hides. The **QCA6390** (FastConnect 6800) and **WCN6855** (FastConnect 6900) combos are also **mainline-Linux-supported by [`ath11k`](https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html)** — the same driver family as the AP-class IPQ8074 / QCN9074. The mainline kernel doc explicitly lists QCA6390 (v5.10) and WCN6855 (v5.17) among supported parts. This matters because the *same physical chip* is:

- **On Android:** driven by downstream **qcacld-3.0** → FullMAC-cooked, features locked to vendor firmware config.
- **On mainline Linux:** driven by **ath11k** → you inherit the ath9k/ath10k *upstream* feature lineage, notably **monitor mode** and **spectral scan** (raw FFT bins from the PHY, the classic Simon-Wunderlich spectral path). The **Steam Deck** ships a QCA6390 and runs it under ath11k — a convenient, cheap lab target.

So if your goal is spectral / raw-PHY-ish data and you control the platform, the pragmatic move is often *not* to fight the phone: put the same chip (or a QCA6390/WCN6855 M.2 card) on a mainline Linux box and use ath11k. ath11k monitor mode is `verified`; ath11k **spectral scan on the mobile QCA6390/WCN6855 specifically is `reported`** (the feature exists in the driver family; per-part behaviour varies and is worth confirming on your hardware) — versus the AP/IPQ parts where spectral is well-trodden. Still no clean host CSI, but you climb from Tier ~1 to a genuine **Tier 3 spectral** posture without any firmware RE.

```bash
# Mainline Linux box with a QCA6390/WCN6855 (e.g. Steam Deck, or an M.2 FastConnect card)
# 1) Confirm ath11k bound the device
dmesg | grep -i ath11k
# 2) Monitor mode (verified path)
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
sudo iw dev wlan0 set channel 36
# 3) Spectral scan (reported on mobile parts — verify presence first)
ls /sys/kernel/debug/ieee80211/phy0/ath11k/   # look for spectral_* / spectral_scan* knobs
```

Contrast: the venerable [Atheros CSI Tool](https://wands.sg/research/wifi/AtherosCSI/) ([xieyaxiongflyland/Atheros_CSI_tool](https://github.com/xieyaxiongflyland/Atheros_CSI_tool)) and [PicoScenes](https://ps.zpj.io/) do give *true per-subcarrier CSI* — but only on **discrete ath9k SoftMAC PCIe cards** (AR9300 / **QCA9300**), *not* on the phone WCN combos. PicoScenes' supported list is AX210 / AX200 / **QCA9300** / IWL5300 — no WCN mobile part. That QCA9300 lineage lives in [`../../chips/qualcomm-atheros.md`](../../chips/qualcomm-atheros.md); do not confuse it with the WCN39xx/QCA6xxx combos this page is about.

---

## 5. A realistic recipe (rooted Android, custom qcacld build)

If you are committed to the phone itself, expect a rooted-Android + custom-driver-build project. High-level, honest about the friction:

```bash
# 0) Identify the exact part and firmware branch on the device
adb shell 'getprop | grep -iE "wlan|wifi|cnss"'
adb shell 'cat /sys/module/wlan/parameters/* 2>/dev/null'
adb shell 'ls -l /vendor/firmware/wlan/ /vendor/firmware_mnt/image/ 2>/dev/null'  # WLAN.HL.* / WLAN.HSP.*

# 1) Get the matching vendor kernel source + qcacld-3.0 tag
git clone https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qcacld-3.0
#   ...checkout the tag matching your device's kernel + firmware branch (this is the hard part)

# 2) Build the module against the device kernel, toggling features you want, e.g.
#    CONFIG_WLAN_PKT_CAPTURE=y   (monitor/packet-capture, if firmware supports it)
#    pktlog / cnss_diag enabled

# 3) Side-load the .ko (root, SELinux permissive or a matching policy), reload the stack
adb push wlan.ko /vendor/lib/modules/
adb shell 'su -c "rmmod wlan; insmod /vendor/lib/modules/wlan.ko con_mode=4"'  # con_mode/monitor is branch-dependent

# 4) Pull firmware pktlog while running your scenario
adb shell 'su -c "cnss_diag -f -t WLAN"'   # writes pktlog/FW logs under /data/vendor/wifi
adb pull /data/vendor/wifi/  ./pktlog_capture/
```

Reality checks:
- Steps 1–2 are where most attempts die: exact **kernel × qcacld × firmware** version matching, plus SELinux and secure-boot friction on production images.
- `con_mode`/monitor semantics, and whether packet-capture is compiled into the shipped firmware, **vary by branch** — verify on *your* part; treat the snippet as illustrative, not a guarantee.
- You are collecting **metadata (pktlog) and possibly monitored frames**, not IQ or clean CSI. Set expectations accordingly.

For the firmware-RE ambition (getting the internal channel estimate out — the true nexmon-equivalent), see [`../../docs/firmware-reversing.md`](../../docs/firmware-reversing.md); as of this cycle there is **no published, reproducible CSI-off-Qualcomm-mobile-firmware result**, and this remains `theoretical`.

---

## 6. The productized / defensive flip side

Qualcomm itself ships **Wi-Fi sensing as a product** on newer FastConnect / automotive combos (e.g. the QCA6595-class 6E parts): motion/presence detection computed *inside* the firmware and surfaced through a vendor sensing SDK — precisely the raw signal researchers want, exposed only as cooked "presence" events. This is the 802.11bf-aligned, closed, black-box end of the ladder (Tier 0): the chip does the sensing, you get the decision, never the CSI. It is the mirror image of the reverse-engineering effort — the vendor monetising the capability while keeping the substrate closed. Worth cataloguing as the "defensive/productized" data point of this cycle.

---

## 7. Honest tier summary

| Data you want | Path | Root? | Realistic tier | Status |
|---|---|---|---|---|
| Ranging / distance (FTM) | `WifiRttManager` / Wi-Fi HAL | no | ~1 | verified |
| Link stats, per-chain RSSI, scans | Wi-Fi HAL / vendor nl80211 | no | 0–1 | verified |
| Per-PPDU PHY metadata | **pktlog** via `cnss_diag` | usually yes | 1 | reported (widely used) |
| Monitored 802.11 frames | qcacld packet-capture mode | yes | 1 | reported (branch-dependent) |
| Injection / arbitrary TX | — | — | — | theoretical (no known mobile path) |
| Spectral / raw FFT bins | **ath11k** on mainline Linux (QCA6390/WCN6855) | n/a (own box) | 3 | monitor verified; spectral reported on mobile parts |
| True per-subcarrier CSI (this silicon) | discrete **QCA9300**/ath9k only, *not* WCN | n/a | 2 | verified (wrong chip) / mobile = theoretical |
| CSI off mobile Qualcomm firmware | firmware RE | yes | 2+ | theoretical — not publicly achieved |

**Bottom line.** Qualcomm mobile Wi-Fi is the hard road: FullMAC, closed firmware, no nexmon. Your leverage is the **source-available `qcacld-3.0` host driver** and the firmware's **pktlog** diagnostics — good for Tier ~1 metadata, ranging, and (branch permitting) monitor mode. For anything spectral or raw-PHY, the smart play is to run the *same* QCA6390/WCN6855 silicon under **ath11k on mainline Linux** rather than fight the phone. Clean per-subcarrier CSI belongs to the discrete **QCA9300/ath9k** cards, not to the combos in your phone. Anyone promising easy phone-CSI on Qualcomm is overselling it.

## References

- qcacld-3.0 host driver (CLO, source-available): <https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qcacld-3.0>
- ath11k mainline driver (QCA6390, WCN6855 support): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html>
- ath10k driver (pktlog / spectral lineage): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath10k.html>
- Android Wi-Fi RTT (802.11mc/az FTM): <https://source.android.com/docs/core/connect/wifi-rtt> · <https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager>
- PicoScenes (CSI middleware; supports QCA9300, not WCN mobile): <https://ps.zpj.io/>
- Atheros CSI Tool (ath9k / QCA9300 discrete cards): <https://wands.sg/research/wifi/AtherosCSI/> · <https://github.com/xieyaxiongflyland/Atheros_CSI_tool>
- nexmon / nexmon_csi (Broadcom — the method that does *not* transfer): <https://github.com/seemoo-lab/nexmon> · <https://github.com/seemoo-lab/nexmon_csi>
