# Qualcomm Atheros Wi-Fi as a Software-Defined Radio

Atheros (acquired by Qualcomm in 2011) built the most **open, hacker-friendly** Wi-Fi
silicon of the 802.11n era. Two architectural quirks make the ath5k/ath9k/ath10k line
the darling of the wireless-sensing research community:

1. **The PCIe/PCI parts are SoftMAC.** AR5416, the AR92xx, and the AR93xx carry **no
   on-chip protocol CPU running a closed blob** — the MAC/PHY registers are driven
   directly from the fully open `ath5k`/`ath9k` mac80211 driver in the host kernel.
   You do not have to reverse-engineer firmware to change PHY behaviour; you patch an
   open GPL driver. This is why CSI and spectral-scan on these chips were unlocked "in
   software, without any firmware modification."
2. **The one part with real firmware is fully open.** The `ath9k_htc` **USB** devices
   (AR9271 single-chip, AR7010 bridge + AR9280/AR9287 radio) run a Tensilica Xtensa
   firmware whose complete source Qualcomm released as
   [`qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware) — a
   genuine Tier-5 "the PHY is yours" target.

Against the SDR ladder, this family owns two crown jewels:

- **Tier 3 — Spectral scan.** Every AR92xx/AR93xx (`ath9k`) and every QCA988x/998x
  (`ath10k`), plus the AR9271 over `ath9k_htc`, can dump raw baseband **FFT bins**
  through `debugfs` (`spectral_scan_ctl` / `spectral_scan0`, relayfs `FFT_SAMPLE_*`
  records). That turns a $12 Wi-Fi card into a real-time 2.4/5 GHz spectrum analyzer —
  see [`../docs/techniques.md`](../docs/techniques.md).
- **Tier 2 — CSI.** The [Atheros-CSI-Tool](https://github.com/xieyaxiongfly/Atheros-CSI-Tool)
  by **Yaxiong Xie** (Mo Li's WANDS group) exposes per-subcarrier complex CSI
  (amplitude **and** phase) from any `ath9k` 802.11n NIC. `PicoScenes` extends this to
  the AR9300/QCA9300 with arbitrary carrier tuning and 2.5–80 MHz baseband sampling.
  Full tool matrix in [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md).

Firmware reversing context (Xtensa toolchains, Ghidra) lives in
[`../docs/firmware-reversing.md`](../docs/firmware-reversing.md).

---

## The families at a glance

| Family | Driver | Bus | Silicon era | On-chip firmware | Peak tier | Unlock |
|---|---|---|---|---|---|---|
| AR52xx/AR54xx | `ath5k` | PCI/PCIe | 11a/b/g | none (SoftMAC) | 1 | open driver |
| AR5416 / AR5008 | `ath9k` | PCIe | 11n gen-1 | none (SoftMAC) | 1 | open driver |
| AR9271 / AR7010 | `ath9k_htc` | USB | 11n | **open Xtensa** | 3 → 5 | open FW + spectral |
| AR9280/85/87 (AR9002) | `ath9k` | PCIe | 11n | none (SoftMAC) | 3 | spectral + CSI |
| AR9380/82/90/85/62 (AR9003) | `ath9k` | PCIe | 11n gen-2 | none (SoftMAC) | 3 | spectral + CSI |
| AR9580 (AR9003) | `ath9k` | PCIe | 11n 3×3 | none (SoftMAC) | 3 | spectral + CSI |
| QCA988x/998x | `ath10k` | PCIe | 11ac | **closed Xtensa** | 3 | spectral |
| QCA6174 / WCN3990 | `ath10k`/snoc | PCIe/SoC | 11ac mobile | closed | 1 | monitor |
| QCA6390 / WCN685x | `ath11k` | PCIe/SoC | 11ax/6E | closed | 1 (2–3 reported) | monitor |
| QCA6490 | `ath11k`/mobile | SoC | 11ax 6E | closed | 1 (theoretical) | — |

---

## ath5k / AR5416 (AR5008) — Tier 1, the softMAC foundation

The `ath5k` driver covers the 802.11a/b/g AR5210…AR5414 parts; **AR5416** (with the
AR5133 radio = the **AR5008** chipset) was the first Atheros 802.11n MAC/baseband and
moved to `ath9k`. All are **SoftMAC with no protocol firmware**, so full monitor mode,
channel hopping and arbitrary 802.11 frame **injection** work out of the box — this is
the aircrack-ng/Kismet workhorse of its generation. AR5416 predates the spectral-scan
register interface (added for AR92xx), so it stays **Tier 1**. CSI is not exposed by the
Atheros-CSI-Tool for the pre-AR9002 baseband.

## AR9271 / AR7010 — Tier 3 today, **Tier 5 firmware**

The AR9271 is a single-chip USB 802.11n 1×1 2.4 GHz SoC (Tensilica Xtensa, "Magpie"
platform); the AR7010 is a USB/PCIe bridge SoC ("K2") that fronts an AR9280 or AR9287
radio. Both run the `ath9k_htc` split-MAC firmware.

- **Why it matters:** Qualcomm released the **complete firmware source** as
  [`qca/open-ath9k-htc-firmware`](https://github.com/qca/open-ath9k-htc-firmware)
  (Xtensa under MIT, eCos under GPLv2). Mathy Vanhoef's
  [modwifi-ath9k-htc](https://github.com/vanhoefm/modwifi-ath9k-htc) forks it for
  **continuous/reactive jamming, arbitrary frame injection with timing control, and
  raw TX** — demonstrated Tier-4-flavoured waveform tricks from patched firmware.
- **Spectral scan** works over `ath9k_htc` (needs `ATH9K_COMMON_SPECTRAL` +
  `ATH9K_HTC_DEBUGFS`) → **Tier 3**.
- **Hardware you can buy:** TP-Link **TL-WN722N v1** (v2/v3 are RTL8188EUS — no monitor
  mode!), **Alfa AWUS036NHA**, Alfa AWUS036NH (AR9271 variants), many "Atheros AR9271"
  no-name USB dongles. These are the canonical Kali monitor+injection adapters.

## AR9002 family — AR9280 / AR9285 / AR9287 — Tier 3

PCIe SoftMAC 802.11n. **AR9280** = 2×2 dual-band; **AR9285** = 1×1 2.4 GHz;
**AR9287** = 2×2 2.4 GHz. All three expose the **spectral-scan FFT interface**
(Tier 3) and per-subcarrier **CSI** through the Atheros-CSI-Tool (Tier 2). Common in
2009–2012 laptops (mini-PCIe) and early routers. AR9280/AR9287 are also the radios sat
behind an AR7010 USB bridge.

## AR9003 family — AR9380 / AR9382 / AR9390 / AR9485 / AR9462 / AR9580 — Tier 3

The second-gen 11n baseband (`ar9003_*` in the driver) is where CSI is best supported:

- **AR9380** (3×3), **AR9382** (2×2), **AR9390** — the desktop/router "QCA9300" family.
  **PicoScenes** supports this NIC with *arbitrary carrier-frequency tuning across the
  full 2.4 GHz-wide span, 2.5–80 MHz baseband sampling, and 0–66 dB manual Rx gain* —
  the most flexible receiver in the whole ath9k line, though still short of raw-IQ
  streaming, so **Tier 3**.
- **AR9485** — 1×1 2.4 GHz low-cost mini-PCIe; **AR9462** — 2×2 dual-band + Bluetooth
  combo (very common in 2012–2014 laptops); **AR9580** — 3×3 desktop/router PCIe, one
  of the **explicitly tested** Atheros-CSI-Tool targets (alongside AR9590, AR9344,
  QCA9558 SoC).

All AR9003 parts do **spectral scan** (Tier 3) and **CSI** (Tier 2) with no firmware
mod. The `ar9003_csi.c` patch in the Atheros-CSI-Tool is the reference implementation.

## QCA988x / QCA998x (`ath10k`) — Tier 3, closed firmware

The 802.11ac generation moved to a **FullMAC-ish design with a closed Tensilica Xtensa
firmware blob** (`ath10k` loads QCA's `firmware-N.bin` / board files). Ben Greear's
**ath10k-ct** is a patched *binary* firmware+driver, not open source, but adds knobs.

- **QCA9880 / QCA9882 / QCA9884** — 11ac wave-1 3×3/2×2 (the AP/router workhorse,
  Compex WLE900VX, WLE600VX, etc.).
- **QCA9980 / QCA9984 / QCA9888** — 11ac wave-2 4×4/2×2 (Compex WLE1216, WLE900V5).
- **Spectral scan** is supported by `ath10k` → **Tier 3** (`spectral_bins` 64/128/256;
  QCA9984/QCA9888 needed a kernel fix to strip an 8-byte segment header). **CSI** is
  *not* exposed by mainline `ath10k`; research extractions exist but are not turnkey →
  **reported/theoretical**. Monitor+injection are limited by the closed firmware.

## Mobile QCA — QCA6174 / QCA6390 / QCA6490 / WCN3990 / WCN685x

Phone/laptop connectivity SoCs, all **closed firmware**:

- **QCA6174** — 11ac 2×2, `ath10k` (PCIe) or `ath10k`/snoc; in countless laptops.
- **WCN3990** — 11ac mobile, `ath10k`/snoc (integrated in Snapdragon 8-series; the
  QCA6174-class phone radio).
- **QCA6390 / WCN6855 / WCN6856 (WCN685x, FastConnect 6800/6900)** — 11ax / 6E,
  `ath11k`. `ath11k` inherits a `spectral` path for some parts and there is community
  interest in CSI, but on mobile parts this is **reported at best** → Tier 1 practically,
  2–3 aspirational.
- **QCA6490** — 11ax 6E mobile combo; monitor/PHY telemetry **theoretical**.

These are catalogued for completeness and to mark the frontier: climbing past Tier 1 on
them means reversing closed Xtensa/ARM firmware — see
[`../docs/firmware-reversing.md`](../docs/firmware-reversing.md).

---

## How to unlock each rung (ath9k)

```bash
# Tier 3 — spectral / FFT spectrum analyzer (AR92xx/AR93xx, QCA988x, AR9271)
echo chanscan   > /sys/kernel/debug/ieee80211/phy0/ath9k/spectral_scan_ctl
iw dev wlan0 scan
cat  /sys/kernel/debug/ieee80211/phy0/ath9k/spectral_scan0 > samples.bin   # FFT_SAMPLE_*
echo disable    > /sys/kernel/debug/ieee80211/phy0/ath9k/spectral_scan_ctl
# 56 bins in HT20, 128 in HT40; decode with FFT_eval / fft_eval_json

# Tier 2 — CSI (Atheros-CSI-Tool kernel + userspace, AR9003 recommended)
#   build the patched ath9k, then read the netlink CSI feed with recv_csi
```

Decoders/loaders: [FFT_eval](https://github.com/simonwunderlich/FFT_eval),
Bastian Bloessl's [ath9k spectrum-scanning writeup](https://www.bastibl.net/ath9k-spectrum-scanning/),
[CSIKit](https://gi-z.github.io/CSIKit/) (parses Atheros CSI).

## Summary — SDR tier by part

| Part | Driver | Bands | Spectral (T3) | CSI (T2) | Mon/Inj (T1) | Firmware |
|---|---|---|---|---|---|---|
| AR5416 / AR5008 | ath9k | 2.4/5 | ✕ | ✕ | ✓ | none (softMAC) |
| **AR9271** | ath9k_htc | 2.4 | ✓ | ~ | ✓ | **open Xtensa** |
| AR9280 | ath9k | 2.4/5 | ✓ | ✓ | ✓ | none |
| AR9285 | ath9k | 2.4 | ✓ | ✓ | ✓ | none |
| AR9287 | ath9k | 2.4 | ✓ | ✓ | ✓ | none |
| AR9380/82/90 | ath9k | 2.4/5 | ✓ | ✓ (PicoScenes) | ✓ | none |
| AR9462 | ath9k | 2.4/5 | ✓ | ✓ | ✓ | none |
| AR9485 | ath9k | 2.4 | ✓ | ✓ | ✓ | none |
| AR9580 | ath9k | 2.4/5 | ✓ | ✓ (tested) | ✓ | none |
| QCA9880/82/84 | ath10k | 2.4/5 | ✓ | ~ | limited | closed Xtensa |
| QCA9980/84/88 | ath10k | 2.4/5 | ✓ | ~ | limited | closed Xtensa |
| QCA6174 / WCN3990 | ath10k | 2.4/5 | ~ | ✕ | limited | closed |
| QCA6390 / WCN685x | ath11k | 2.4/5/6 | ~ | ~ | limited | closed |
| QCA6490 | ath11k | 2.4/5/6 | ✕ | ✕ | limited | closed |

`✓` verified with public tooling · `~` reported/experimental · `✕` not available

---

## Un-cataloged / TODO (feeds the next cycle)

- **AR9344 / QCA9558 / AR9590** — Atheros SoCs explicitly *tested* by the CSI Tool but
  not yet profiled as their own records (embedded router SoCs, `ath9k` on AHB bus).
- **AR9160 / AR9130 / AR9132** — first-gen 11n router MAC/SoCs (AP81/AP83 reference).
- **AR9382 vs AR9390** exact SKU/antenna differences and which laptops shipped them.
- **QCA9377 / QCA9886 / QCA9887** — later `ath10k` 11ac 1×1 combo parts (spectral?).
- **QCA9500 / IPQ4018 / IPQ4019 / IPQ8064** — integrated-radio router SoCs on `ath10k`.
- **QCA9990 / QCA9994** — 4×4 11ac wave-2 (Wave-2 spectral header quirks).
- **WCN6855 vs WCN6856** feature split; **QCN9074 / QCN6122** 11ax radio cards on `ath11k`.
- **QCA6595 / QCA6696 / WCN7850** — Wi-Fi 7 / next-gen mobile (`ath12k`) — firmware fully closed, RE status unknown.
- ath10k **CSI** research extractions — confirm whether any reached turnkey/public-tool status.
- `ath11k` **spectral** on desktop cards (QCN9074) — verify FFT dump path end-to-end.
