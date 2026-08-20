# Cross-Checking the Catalog Against Current Linux Kernel Source

> **A driver-grounded verification pass.** Every other audit in this repo asks "does the *chip* have the capability?" This one asks a colder, more falsifiable question: **does the mainline Linux driver that actually binds to this chip today expose that capability at all?** Firmware can have an FFT engine and a CSI buffer; if the in-tree driver never surfaces them, an ordinary user on a stock kernel cannot reach them. That gap is exactly what a catalog can silently get wrong.
>
> Method companion: [../docs/methodology.md](../docs/methodology.md). Practical monitor/injection index: [../chips/monitor-injection-support.md](../chips/monitor-injection-support.md). Tier-by-tier reproduction audits: [`verification-tier1-injection.md`](./verification-tier1-injection.md), [`verification-tier2-csi.md`](./verification-tier2-csi.md), [`verification-tier3-spectral.md`](./verification-tier3-spectral.md).

**Baseline:** mainline `torvalds/linux` at `master` (kernel 6.16-era tree), file paths read 2026-08. Where a capability lives *only* in an out-of-tree fork (nexmon firmware, MediaTek's vendor `mt76`, Intel AX-CSI, ath10k-CT), that is called out explicitly — the catalog entry may still be legitimately "verified," but **not via the in-tree driver**, and that distinction is the whole point of this page.

---

## 1. How to check a driver claim yourself

Three cheap checks settle most disputes before you ever touch the silicon:

```bash
# (a) What interface types + capabilities does the bound driver advertise?
iw phy | sed -n '/Supported interface modes/,/Supported commands/p'
#   -> look for "* monitor" ; absence means no monitor mode, full stop.

# (b) Is the spectral / CFR debugfs surface even present?
sudo mount -t debugfs none /sys/kernel/debug 2>/dev/null
find /sys/kernel/debug/ieee80211/phy*/ -name 'spectral_scan_ctl' -o -name 'cfr*' 2>/dev/null
#   ath9k/ath10k/ath11k -> .../ath9k/spectral_scan_ctl (or ath10k/, ath11k/)
#   ath11k CFR          -> .../enable_cfr  + relayfs cfr_capture
#   iwlwifi / mt76 / rtw* / brcmfmac -> nothing (no spectral/CFR node)

# (c) Was the option compiled in at all?
zgrep -E 'ATH(9K|10K|11K)_(DEBUGFS|SPECTRAL|COMMON_SPECTRAL)|CFG80211|MAC80211' /proc/config.gz
```

The **driver source itself** is the ground truth, and each row below cites the file that decides the answer. Two structural facts drive most of the findings:

- **Monitor mode** is a `mac80211` property: a driver advertises `NL80211_IFTYPE_MONITOR` in its `wiphy->interface_modes`. If it does, monitor works; injection quality is a separate, firmware-dependent question (`IEEE80211_TX_CTL_INJECTED` handling).
- **Spectral scan and CSI/CFR are *not* mac80211 features.** They are per-driver debugfs/relayfs extensions. Their presence is decided by a single file existing in the driver directory: `spectral.c`, or (for ath11k) `cfr.c`. **No file, no capability** — regardless of what the firmware can do internally.

---

## 2. Verdict table

Legend: `✔` in-tree and works · `▲` present but caveated/firmware-gated · `✘` not exposed by the in-tree driver · `OOT` exists only out-of-tree. **Verdict** compares the driver reality to the catalog's marks.

| Chip / family | Kernel driver | Deciding mainline file(s) | Mon | Inj | Spec | CSI/CFR | Catalog says | Verdict |
|---|---|---|:--:|:--:|:--:|:--:|---|---|
| AR9280/9285/9287, AR9220/9223/9227 | `ath9k` | `ath/ath9k/spectral.c`, `ath/spectral_common.h` | ✔ | ✔ | ✔ | ✔ OOT¹ | T3 mon,inj,csi,spectral | **OK** |
| AR9380/9382/9462/9485/9580 | `ath9k` | same | ✔ | ✔ | ✔ | ✔ OOT¹ | T3 mon,inj,csi,spectral | **OK** |
| AR9271 / AR7010 (USB) | `ath9k_htc` | `ath/ath9k/htc_drv_debug.c` (needs `ATH9K_HTC_DEBUGFS`) | ✔ | ✔ | ▲ | ✘ | T1 mon,inj,open-fw | **OK** |
| AR9170 | `carl9170` | `ath/carl9170/` (open fw) | ✔ | ✔ | ✘ | ✘ | T1 mon,inj,open-fw | **OK** |
| QCA9880/9984/9888/9882/9886 | `ath10k` | `ath/ath10k/spectral.c` (`ATH10K_SPECTRAL`) | ✔ | ▲ | ✔ | ✘ | T3 mon,(inj),spectral | **OK** |
| **QCA6174** (client 11ac) | `ath10k` | `ath/ath10k/` — **no CSI/CFR source**; spectral fw-gated | ▲ | ▲ | ▲ | ✘ | **T2 mon,csi** | **FIX** ↓ |
| **QCN9074** (Wi-Fi 6E) | `ath11k` | `ath/ath11k/spectral.c` **+ `cfr.c`** | ▲ | ▲ | ✔ | ▲ (CFR) | **T3 mon,spectral** | **FIX** +csi |
| **WCN6855** (FastConnect 6900) | `ath11k` | `ath/ath11k/spectral.c` **+ `cfr.c`** | ▲ | ✘ | ✔ | ▲ (CFR, gated) | **T3 mon,spectral** | **FIX** +csi |
| IPQ8074 (Hawkeye) | `ath11k` | `ath/ath11k/spectral.c`, `cfr.c` | ✔ | ▲ | ✔ | ▲ (CFR) | T3 mon,inj,spectral | **OK** (CFR note) |
| WCN7850 / QCN9274 (Wi-Fi 7) | `ath12k` | `ath/ath12k/dp_mon.c` — **no `spectral.c`, no `cfr.c`** | ▲ | ✘ | ✘ | ✘ | T1 mon | **OK** |
| Intel AX200/AX201 | `iwlwifi` | `intel/iwlwifi/` — no spectral/CSI node | ✔ | ▲ | ✘ | ✘ / OOT² | T2 mon,inj,csi | **OK-caveat²** |
| Intel AX210/AX211 | `iwlwifi` | same | ✔ | ▲ | ✘ | ✘ / OOT² | T2 mon,inj,csi | **OK-caveat²** |
| Intel 9260 | `iwlwifi` | same | ✔ | ▲ | ✘ | ✘ | T1 mon | **OK** |
| MT7612U | `mt76` (`mt76x2u`) | `mediatek/mt76/mt76x2/` | ✔ | ✔ | ✘ | ✘ | T1 mon,inj | **OK** |
| MT7921(AU/E) | `mt76` (`mt7921`) | `mediatek/mt76/mt7921/` | ✔ | ✔ | ✘ | ✘ | T1 mon,inj | **OK** |
| MT7915 / MT7916 | `mt76` (`mt7915`) | `mediatek/mt76/mt7915/` — **no `vendor.c`/CSI in tree** | ✔ | ✔ | ✘ | ✘ / OOT³ | T2 mon,inj,csi | **OK-caveat³** |
| MT7925 / MT7927 (Wi-Fi 7) | `mt76` (`mt7925`) | `mediatek/mt76/mt7925/` | ✔ | ✔ | ✘ | ✘ | T1 mon,inj | **OK** |
| RTL8852AE/BE/CE (Wi-Fi 6/6E) | `rtw89` | `realtek/rtw89/core.c` (`IEEE80211_TX_CTL_INJECTED`) | ✔ | ▲ | ✘ | ✘ | T1 mon | **OK** |
| RTL8822/8821 (rtw88) | `rtw88` | `realtek/rtw88/` | ✔ | ▲ | ✘ | ✘ | T1 mon(,inj) | **OK** |
| BCM43455c0/4356/4359/43602/4364 | `brcmfmac` | `broadcom/brcm80211/brcmfmac/feature.h` (`BRCMF_FEAT_MONITOR*`); **no inj/spectral/CSI** | ▲ | ✘ | ✘ | ✘ / OOT⁴ | T1–T2 mon,inj,csi | **OK-caveat⁴** |

¹ ath9k CSI = the **Atheros CSI Tool** (out-of-tree patched driver), not a mainline debugfs node. ² Intel CSI = **AX-CSI** (Gringoli et al.), out-of-tree + debug firmware; mainline `iwlwifi` exposes no CSI or spectral. ³ MT7915 CSI = MediaTek's **out-of-tree vendor `mt76`** (`mt7915/vendor.c`, nl80211 vendor cmd) in the OpenWrt MTK feed; the in-tree `mt7915` has no CSI. ⁴ Broadcom injection/CSI = **[nexmon](../projects/nexmon.md)** firmware patches; stock `brcmfmac` gives monitor-only, and only when the firmware advertises `BRCMF_FEAT_MONITOR_FMT_RADIOTAP`.

---

## 3. The three mismatches, in detail

### 3.1 QCA6174 — `csi` is not reachable through `ath10k` (FIX, downgrade)

The catalog marked `qualcomm-qca6174` **Tier 2 with `csi`**. There is **no CSI or CFR source file anywhere in `drivers/net/wireless/ath/ath10k/`** — the only per-subcarrier-adjacent surface ath10k has is `spectral.c` (magnitude FFT bins, not equalized channel estimates), and even that is firmware-image-gated and typically absent on the QCA6174 *client* firmware found in laptops/phones (see [`verification-tier3-spectral.md`](./verification-tier3-spectral.md) §"QCA9887/QCA9377/QCA6174 — partial"). CFR capture is an **ath11k** feature (`cfr.c`), introduced for Wi-Fi 6 silicon; it does not exist for ath10k parts. There is no public, reproducible QCA6174 CSI path on a mainline kernel.

**Correction:** drop `csi`, downgrade to **Tier 1 (`monitor`)**, keep `status: reported` (monitor itself is flaky per-firmware on this client part). AP-class ath10k (QCA988x/9984/9888) is **unaffected** — those remain verified Tier 3 spectral.

### 3.2 QCN9074 and WCN6855 — `cfr.c` is a real, undercredited CSI path (FIX, add `csi`)

`drivers/net/wireless/ath/ath11k/cfr.c` implements **Channel Frequency Response (CFR)** capture — the ath11k equivalent of per-subcarrier CSI. It correlates firmware DBR (Direct Buffer Ring) DMA events with TX capture notifications and streams the result to userspace via **relayfs** (`cfr_capture`), toggled through debugfs `enable_cfr` / `cfr_unassoc`. It is runtime-gated by `ab->hw_params.cfr_support` and the firmware service bit `WMI_TLV_SERVICE_CFR_CAPTURE_SUPPORT`, so it is **not guaranteed on every ath11k board** — but the in-tree path exists, which is more than the catalog credited these entries with (they listed only `monitor,spectral-scan`).

**Correction:** add `csi` to `qualcomm-qcn9074` and `qualcomm-wcn6855`, keep Tier 3 and `status: reported`, and note the CFR gating honestly (verify `hw_params.cfr_support` per firmware; userspace decode tooling for ath11k CFR is nascent compared to FFT_eval for spectral). IPQ8074 (`qualcomm-ipq8074`) shares the same `cfr.c` path and should be read the same way, though its record already sits at verified Tier 3 spectral and is left unchanged here.

### 3.3 Out-of-tree capabilities that are *correctly* marked but wrongly attributed

These are **not** catalog errors in tier/status — the capability is real and often verified — but the cross-check surfaces that the enabling code is **not** the in-tree driver, which matters for anyone expecting it to "just work" on a stock kernel:

- **MT7915 `csi`** — in-tree `mt7915` has no `vendor.c` and no CSI node. The CSI vendor command lives in **MediaTek's out-of-tree `mt76`** (OpenWrt `mtk-openwrt-feeds`). A mainline kernel gives you monitor+injection but **no CSI** on this part. Flagged as caveat, not downgraded.
- **Intel AX200/AX210 `csi`** — mainline `iwlwifi` exposes neither CSI nor spectral (its debug surface is tracing, monitor sniffing, and firmware dumps). CSI comes from **AX-CSI** with a debug firmware, out-of-tree. The dedicated `intel-ax210-csi` record already documents this; the plain AX200/AX210 records inherit the same caveat. Injection on iwlwifi is `▲` (firmware rewrites header fields) per [../chips/monitor-injection-support.md](../chips/monitor-injection-support.md).
- **Broadcom `injection`/`csi`** — `feature.h` confirms mainline `brcmfmac` can do **monitor** (`BRCMF_FEAT_MONITOR`, `_FMT_RADIOTAP`, `_FMT_HW_RX_HDR`) when the firmware advertises it, but there is **no injection, no spectral, no CSI** in `brcmfmac`. Every Broadcom tier-1/2 mark above the monitor floor is a **[nexmon](../projects/nexmon.md)** firmware-patch capability. The catalog family strings already say "Nexmon," so the marks stand — but "brcmfmac" alone never gets you there.

---

## 4. What the cross-check confirms (no change)

- **ath9k / ath9k_htc / ath10k spectral** is the solid ground it has always been: `spectral.c` is present in-tree for both, `spectral_common.h` defines the TLV format, and `FFT_eval` decodes it. Every ath9k Tier-3 mark checks out.
- **ath12k (Wi-Fi 7 QCA: WCN7850, QCN9274)** has monitor datapath code (`dp_mon.c`) but **no `spectral.c` and no `cfr.c`** — so there is no in-tree spectral or CSI for Wi-Fi 7 QCA yet. The catalog's Tier-1 (monitor-only) marks for these are correct and appropriately conservative; do not let the ath11k spectral/CFR story leak forward onto ath12k parts.
- **mt76 monitor/injection** (MT7612U, MT7921, MT7915, MT7925) is genuine in-tree mac80211 — the strongest "buy it and it works" story for tiers 0–1. Only the **CSI** claim needs the vendor-tree caveat.
- **rtw88/rtw89 monitor** is real; `rtw89/core.c` even carries injection plumbing (`rtw89_core_tx_update_injection`, honoring `IEEE80211_TX_CTL_INJECTED` with custom rate selection), though real-world injection quality remains weak — consistent with the catalog's conservative monitor-only marks on the RTL8852 family.

---

## 5. Takeaways for maintaining the catalog

1. **A capability above the monitor floor should name the file that exposes it.** For ath-family that is literally `spectral.c` / `cfr.c`; if you cannot point at the in-tree file (or an explicitly-named out-of-tree fork), the mark is unsupported.
2. **"ath10k has CSI" is the recurring trap.** CSI/CFR entered the QCA line at **ath11k** (`cfr.c`). Anything on ath10k claiming `csi` is almost certainly conflating spectral (which ath10k does have) with channel estimates (which it does not).
3. **Wi-Fi 7 QCA (ath12k) is monitor-only in-tree today** — no spectral, no CFR. Re-check when `ath12k/spectral.c` or `ath12k/cfr.c` first appears.
4. **Distinguish "verified via out-of-tree" from "verified in mainline."** Both are legitimate `verified` for the catalog, but the notes field should say which — a stock-kernel user's experience depends entirely on it.

## References

- ath11k CFR: `drivers/net/wireless/ath/ath11k/cfr.c` — https://github.com/torvalds/linux/blob/master/drivers/net/wireless/ath/ath11k/cfr.c
- ath11k spectral: `drivers/net/wireless/ath/ath11k/spectral.c` — https://github.com/torvalds/linux/blob/master/drivers/net/wireless/ath/ath11k/spectral.c
- ath10k spectral: `drivers/net/wireless/ath/ath10k/spectral.c` — https://github.com/torvalds/linux/blob/master/drivers/net/wireless/ath/ath10k/spectral.c
- ath12k directory (no spectral/cfr): https://github.com/torvalds/linux/tree/master/drivers/net/wireless/ath/ath12k
- mt7915 directory (no vendor/CSI in tree): https://github.com/torvalds/linux/tree/master/drivers/net/wireless/mediatek/mt76/mt7915
- brcmfmac feature flags: `drivers/net/wireless/broadcom/brcm80211/brcmfmac/feature.h` — https://github.com/torvalds/linux/blob/master/drivers/net/wireless/broadcom/brcm80211/brcmfmac/feature.h
- rtw89 core (monitor/injection): `drivers/net/wireless/realtek/rtw89/core.c` — https://github.com/torvalds/linux/blob/master/drivers/net/wireless/realtek/rtw89/core.c
- Kernel wireless driver docs: https://wireless.docs.kernel.org/en/latest/en/users/drivers.html
- FFT_eval (spectral decoder): https://github.com/simonwunderlich/FFT_eval
