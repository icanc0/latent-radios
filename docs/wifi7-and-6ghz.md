# Wi-Fi 6E/7 (802.11ax/be) and the 6 GHz Band: What Is Reachable

> **Scope.** This is the "research frontier" chapter of Latent Radios. Cycle 1
> catalogued the mature 802.11n/ac/ax generations where monitor, injection and
> CSI are solved problems. Here we look at the *newest* silicon — Wi-Fi 6E and
> Wi-Fi 7 (802.11be) — and ask, honestly, how far up
> [the SDR ladder](taxonomy.md) you can actually climb *today* with public
> tooling. The short answer: the drivers have arrived, monitor mode is landing,
> **but CSI/raw-PHY access has largely *not* caught up**, and the 6 GHz band adds
> a regulatory wrinkle that quietly disables the very modes researchers want.

Related reading: [`intel.md`](../chips/intel.md),
[`qualcomm-atheros.md`](../chips/qualcomm-atheros.md),
[`mediatek-ralink.md`](../chips/mediatek-ralink.md),
[`broadcom-cypress.md`](../chips/broadcom-cypress.md),
[`projects/nexmon.md`](../projects/nexmon.md),
[`projects/picoscenes.md`](../projects/picoscenes.md),
[`projects/csi-toolchains.md`](../projects/csi-toolchains.md),
[`docs/verification-tier4.md`](verification-tier4.md).

---

## 1. What Wi-Fi 6E and Wi-Fi 7 actually change at the PHY

Before scoring reachability it helps to be precise about *why* these standards
are hard for the repurposing community.

| Feature | Wi-Fi 6 (11ax) | Wi-Fi 6E | Wi-Fi 7 (11be) | Why it matters for SDR-ish use |
|---|---|---|---|---|
| Max channel width | 160 MHz | 160 MHz | **320 MHz** | 320 MHz spans two 160 MHz segments (often non-contiguous, "320-2"). CSI/IQ buffers, DMA rings and radiotap plumbing all have to double. Most CSI tools cap at 160 MHz. |
| New spectrum | — | **5.925–7.125 GHz (6 GHz)** | 6 GHz | ~1.2 GHz of clean spectrum, but gated by **AFC / power classes (LPI, VLP, SP)** and country regs. Injection/active TX here is legally fraught. |
| Modulation | 1024-QAM | 1024-QAM | **4096-QAM (4K-QAM)** | Denser constellation → higher SNR/EVM demands; a monitor NIC that decodes 4K-QAM must have near-reference RF. Irrelevant to *passive* IQ capture, relevant to demod. |
| Sub-carriers | 2 kHz spacing (256/512/1024-tone) | same | up to **4096-tone** FFT at 320 MHz | A full-band CSI record is now up to ~4000 complex coefficients per stream — bigger than any legacy CSI format was designed for. |
| Multi-link | — | — | **MLO** (Multi-Link Operation) | One logical STA aggregates 2–3 radios/links. mac80211's monitor/CSI model is single-link; MLO breaks the "one netdev = one PHY" assumption that CSI toolchains lean on. |
| Punctured preamble | optional | optional | **preamble puncturing** | Sub-channels can be masked mid-channel. Any raw-PHY extractor must track the puncturing bitmap to interpret sub-carriers. |

The takeaway: every axis that makes 11be fast (wider, denser, multi-link) also
makes it *harder* to shoehorn into the legacy monitor/CSI plumbing that the
community built for 11n/ac. This is the core reason tooling lags silicon by
years.

---

## 2. The reachability scorecard

Scores use the Latent Radios ladder (0 black-box → 5 open PHY). "Public tooling
today" means code you can clone and run, not a paper demo.

| Chip | Vendor | Class | Linux driver | Monitor | Injection | CSI | Tier | Honest status |
|---|---|---|---|---|---|---|---|---|
| AX210 *(present in catalog)* | Intel | 11ax 6E | `iwlwifi` | yes | limited | **yes (PicoScenes/FeitCSI)** | 2 | 6E CSI up to 160 MHz including 6 GHz — the current best-in-class commodity CSI |
| **BE200 / BE201** | Intel | 11be | `iwlwifi` (≥6.5) | yes | limited | **not yet** | 1 | Driver solid; no CSI port. See §3 |
| **WCN7850 / WCN7851** (FastConnect 7800) | Qualcomm | 11be | `ath12k` (≥6.3) | landing (2025) | no | no public | 1 | Monitor merged mid-2025; no CSI/spectral tool |
| **QCN9274 / QCN6274** | Qualcomm | 11be AP | `ath12k` | partial | no | no public | 1 | AP silicon; ath11k had spectral, ath12k not yet |
| MT7925 *(present)* / **MT7927** (Filogic 360/380) | MediaTek | 11be | `mt76`/`mt7925` | yes | yes | **not on 11be yet** | 1 | mt76 monitor/inject good; CSI only on older mt76 parts |
| **MT7902** | MediaTek | 11ax 6E | `mt76` (mt7921-based) | yes | yes | via MtkCSIdump? untested | 1 | 6E combo, reuses mt7921 code |
| **BCM4398** | Broadcom | 11be mobile | vendor blob | **nexmon (Pixel 8)** | not yet | no | 1 | Nexmon monitor+radiotap only |
| **BCM6756** | Broadcom | 11ax/6E AP | closed SDK | no | no | no | 0 | Proprietary AP firmware, no open tooling |

Nothing on this list reaches **tier 3+** (spectral / raw-IQ / arbitrary
waveform) with public tooling as of mid-2026. The frontier is: *get CSI back to
where AX210 already is, but on 320 MHz and 11be preambles.*

---

## 3. Intel BE200 / BE201 — the driver is ready, the CSI is not

**What they are.** BE200 (M.2 2230/1216) and BE201 (CNVio2, soldered, requires an
Intel host MAC) are Intel's first-generation Wi-Fi 7 client radios, internally
the **"Gale" (`gl`)** family. 2×2, up to 320 MHz, 4K-QAM, MLO, tri-band
(2.4/5/6 GHz).

**Kernel/driver status (verified).** Supported by upstream `iwlwifi` from
**Linux 6.5**; the wider Intel Wi-Fi 7 line (BE200/201/202/211/213) is covered by
the Linux driver package 24.20+. They load closed firmware blobs from
`/lib/firmware/`: `iwlwifi-gl-*.ucode` **plus a `iwlwifi-gl-*.pnvm`** platform
NVM blob — a common failure mode is the driver binding but Wi-Fi 7 rates never
appearing because the `.pnvm` is missing/old.

```bash
# Confirm the part and firmware the kernel actually loaded
lspci -nnk | grep -A3 -i network        # look for 8086:272b (BE200) etc.
dmesg | grep -i iwlwifi | grep -iE 'gl|pnvm|api'
ls -l /lib/firmware/iwlwifi-gl-*
```

**Monitor / injection.** `iwlwifi` supports mac80211 monitor mode, but as on all
Intel parts injection is **restricted** (the firmware polices TX). This is the
same limitation documented for AX200/AX210 in [`intel.md`](../chips/intel.md).

**CSI — the honest gap.** The two tools that give AX200/AX210 real 11ax CSI —
**[PicoScenes](../projects/picoscenes.md)** and **FeitCSI** — both explicitly
list AX200/AX210 and say only that "the newest Intel NIC *might* also be
supported." **Neither ships verified BE200/BE201 CSI.** The AX210 CSI path relied
on reverse-engineering a specific firmware notification format; the Gale firmware
is a new blob and that work has not been publicly reproduced. So:

- AX210: **tier 2**, CSI to 160 MHz including the 6 GHz band (PicoScenes is "the
  first and only" platform doing 6 GHz CSI/injection on commodity hardware).
- BE200/BE201: **tier 1** today. Monitor works; CSI is *unknown/unverified*. If
  you need commodity Intel CSI right now, **buy an AX210, not a BE200.**

This BE200-vs-AX210 delta is the single most important practical fact in this
chapter.

---

## 4. Qualcomm FastConnect 7800 (WCN7850/7851) and QCN AP chips — `ath12k`

**What they are.** WCN7850 (and the electrically-equivalent **WCN7851**, sold as
**FastConnect 7800**, module part **QCNCM865**) is a 2×2 tri-band 11be client
radio, 320 MHz, 4K-QAM, MLO. The **QCN9274/QCN6274** are the 4×4/scaled-down AP
siblings on the same architecture.

**Driver status (verified).** `ath12k` landed in **Linux 6.3**, initially for
QCN9274 and WCN7850 over PCIe; it is a clean restart forked from `ath11k` and
uses `mac80211`. It needs Qualcomm firmware + `board-2.bin` from `linux-firmware`
(`ath12k/WCN7850/…`). PCI IDs show as `17cb:1107` "WCN785x Wi-Fi 7 320MHz 2x2
[FastConnect 7800]".

**Monitor.** For the first two years ath12k had **no monitor mode**. Monitor-mode
support for WCN7850 was posted to the ath12k list and merged through
**2025** (adds the RX monitor SRNG rings, IRQ config and ring-processing the
early driver lacked). Treat monitor as **reported/landing** — check your exact
kernel:

```bash
modinfo ath12k | grep -i version
iw list | sed -n '/Supported interface modes/,/^\s*[A-Za-z]/p'   # is "monitor" listed?
```

**Injection / CSI / spectral.** No public injection path. **No CSI tool.**
ath11k exposed a **spectral scan** (FFT) debugfs interface on some parts; that
code has **not** been brought forward to ath12k, so even spectral is not
available on WCN7850/QCN9274 yet. Firmware is a closed Qualcomm blob (no
Nexmon-equivalent for these). **Tier 1**, and only because monitor is arriving.

---

## 5. MediaTek Filogic — `mt76`, the most open of the modern stacks

MediaTek's `mt76` is fully upstream and open-source on the *driver* side (the
on-chip firmware remains a blob), which historically made it the friendliest
modern family for monitor/inject and even CSI.

| Part | Marketing | Driver | Notes |
|---|---|---|---|
| **MT7925** *(present in catalog)* | Filogic 360 | `mt76`/`mt7925` | 11be 2×2, STA/AP/P2P/**monitor** |
| **MT7927** | Filogic 380 | `mt76`/`mt7925` (+MT6639 BT) | 11be; a combo module that is architecturally an MT7925 Wi-Fi die on PCIe |
| **MT7902** | — | `mt76` (based on `mt7921`) | 11ax **6E** client; "initial support based on MT7921" merged to mt76 |

**Monitor / injection (verified).** The `mt7925` driver advertises Station, AP,
P2P **and monitor** modes; `mt76` parts are among the better commodity injectors.
MT7902 reuses the mature `mt7921` code path.

**MT7927 upstreaming (reported, 2025→2026).** MT7927 support is being added to
`mt76` on top of `mt7925` and was through its ~4th review round on
linux-wireless; out-of-tree **DKMS** packages exist for kernels 6.17+ if your
distro is behind:

```bash
# Out-of-tree MediaTek Wi-Fi 7 (MT7927/MT6639) while waiting for upstream
git clone https://github.com/jetm/mediatek-mt7927-dkms
# or the tracking fork with prebuilt firmware:
git clone https://github.com/morrownr/mt76
```

**CSI — the frontier.** There *is* a real MediaTek CSI project,
**[MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump)**, which extracts CSI on
mt76 chips **without firmware modification** — but it targets the older
MT7915/MT7921 generation. As of mid-2026 it does **not** cover the 11be
MT7925/MT7927 at 320 MHz. This is arguably the most tractable open research
target on this whole page: the driver is open, monitor works, and a working
older-gen CSI extractor exists to port from. **Tier 1 today, plausible tier 2
soon.**

---

## 6. Broadcom BCM4398 / BCM6756 — Nexmon reaches the phone, not the AP

**BCM4398** is Broadcom's 11be mobile combo (2×2 SDB, 320 MHz, 5–7 GHz, 4K-QAM,
dual-core BT 5.2), shipping in flagship phones (e.g. Pixel 8-class). **BCM6756**
is a Wi-Fi 6/6E **AP** SoC on Broadcom's closed router SDK.

**Nexmon status (verified).** [`nexmon`](../projects/nexmon.md) lists
**BCM4398d05,8,9** with firmware `24_671_6_9` on a rooted **Pixel 8**, enabling
**Monitor Mode + RadioTap headers**. Frame **injection is not listed** for
BCM4398 (unlike many older Broadcom parts), and **`nexmon_csi` does not support
any Wi-Fi 7 chip** — the CSI extraction framework tops out at the 11ac/11ax
BCM43xx generation. Firmware is **patchable** via the Nexmon toolchain (the D11
ucode + ARM firmware model from the older parts still applies), but nobody has
published an 11be CSI patch. **BCM4398: tier 1** (monitor only, on a rooted
phone).

**BCM6756** and the Broadcom AP line run proprietary firmware with no Nexmon
foothold — **tier 0, black-box** for our purposes. If you want an open 6E AP for
sensing, an MT7916-class MediaTek AP is the pragmatic choice (see §7).

---

## 7. If you need results *now* on 6 GHz / Wi-Fi-adjacent CSI

Because the newest silicon is stuck at tier 1, the practical advice is to step
back one rung:

- **6 GHz CSI, commodity, today:** Intel **AX210** with
  [PicoScenes](../projects/picoscenes.md) or **FeitCSI** — the only public path
  to CSI + injection across the full 5945–7125 MHz 6 GHz range, up to 160 MHz.
- **11ax CSI from an AP:** the **ZTECSITool** release (June 2025) provides
  customized firmware for **MT7916**-based ZTE AX3000 APs, 160 MHz / 512
  sub-carriers / 16-bit — see [`wifi-sensing-datasets.md`](../projects/wifi-sensing-datasets.md).
- **MediaTek CSI to build on:** [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump)
  on MT7915/MT7921 (no firmware mod).
- **True SDR baseline for 6 GHz research:** a USRP/[bladeRF](../chips/hardware-index.md)-class
  radio if you need honest raw IQ rather than vendor-filtered CSI — see
  [`true-sdr-comparison.md`](true-sdr-comparison.md).

---

## 8. The 6 GHz regulatory wrinkle (read before you TX)

The 6 GHz band is **not** an open playground. Regulators define **LPI**
(Low-Power Indoor), **VLP** (Very-Low-Power) and **Standard Power** (AFC-gated)
classes. Two consequences that bite researchers:

1. **Drivers refuse TX until the regulatory domain says 6 GHz is allowed**, and
   many default `world`/`00` domains keep 6 GHz **NO-IR** (no initiating
   radiation) — so *active* injection silently does nothing even when monitor
   works. Check with `iw reg get` and your channel's flags in `iw list`.
2. **Injecting arbitrary frames in 6 GHz can be illegal** in a way that 2.4 GHz
   hobbyist experiments were not, because AFC coordinates incumbents (fixed
   links, satellite). **Passive monitor/CSI is fine; TX is a compliance
   question.** Keep active experiments in a shielded enclosure or on a spectrum
   licence. See [`docs/verification-tier4.md`](verification-tier4.md) for the
   tier-4 safety/regulatory checklist.

---

## 9. Research frontier — what's genuinely open

| Open problem | Best starting point | Why it's tractable |
|---|---|---|
| **CSI on BE200/201** | Port the AX210 firmware-notification RE (PicoScenes/FeitCSI) to the Gale `gl` blob | Same vendor, same tooling, only the firmware format changed |
| **CSI on MT7925/MT7927 @ up to 320 MHz** | Port [MtkCSIdump](https://github.com/MtkWifiRev/MtkCSIdump) forward on open `mt76` | Driver is open, monitor works, older-gen extractor exists |
| **Bring spectral scan to `ath12k`** | Forward-port the ath11k spectral/FFT debugfs code | Proven design one generation back |
| **11be CSI on BCM4398** | Extend `nexmon_csi` to the newer D11/ARM firmware | Nexmon monitor already works on Pixel 8 |
| **Beamforming-feedback sensing (no CSI needed)** | **Wi-BFI** style extraction of compressed BF feedback from the air | Works on *any* 11ax/be traffic in monitor mode — sidesteps closed CSI entirely |
| **MLO-aware capture model** | mac80211 monitor semantics for multi-link | The single-netdev assumption in every CSI tool needs rethinking for 11be |

The through-line: **Wi-Fi 7 silicon is broadly reachable at tier 1 (monitor,
sometimes injection) but stalled below tier 2 (CSI).** Closing that gap on even
one of these families — most plausibly MediaTek, given the open driver — would be
a genuine, publishable contribution to the field.

---

## References

- Intel iwlwifi / BE200 support — Linux Wireless docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html>
- Intel Wireless Wi-Fi Drivers for Linux (BE200/201/202/211/213, pkg 24.20): <https://www.intel.com/content/www/us/en/download/824804/intel-wireless-wi-fi-drivers-for-linux.html>
- PicoScenes — 802.11ax CSI on Intel AX200/AX210, 6 GHz injection/CSI: <https://ps.zpj.io/> and <https://zpj.io/picoscenes-supports-csi-extraction-from-802-11ax-frames/>
- FeitCSI — Intel AX200/AX210 CSI/injection tool: <https://feitcsi.kuskosoft.com/>
- ath12k driver (Linux 6.3, QCN9274/WCN7850) — Phoronix: <https://www.phoronix.com/news/Qualcomm-Ath12k-Linux-6.3>; kernel docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath12k.html>
- ath12k monitor mode for WCN7850 (LWN): <https://lwn.net/Articles/1018318/>
- Qualcomm FastConnect 7800 product page: <https://www.qualcomm.com/wi-fi/products/fastconnect/fastconnect-7800>
- MediaTek MT7927 (Filogic 380) mt76 support (LWN): <https://lwn.net/Articles/1063834/>; Phoronix: <https://www.phoronix.com/news/MediaTek-MT7927-WiFi-Linux>
- MediaTek MT7902 initial mt76 support (LWN): <https://lwn.net/Articles/1030810/>
- MT7927 DKMS (out-of-tree): <https://github.com/jetm/mediatek-mt7927-dkms>; morrownr mt76: <https://github.com/morrownr/mt76>
- MtkCSIdump — CSI on MediaTek mt76 (no firmware mod): <https://github.com/MtkWifiRev/MtkCSIdump>
- Broadcom BCM4398 product page: <https://www.broadcom.com/products/wireless/wireless-lan-bluetooth/bcm4398>
- Nexmon (BCM4398 monitor on Pixel 8): <https://github.com/seemoo-lab/nexmon> ; nexmon_csi: <https://github.com/seemoo-lab/nexmon_csi>
- ZTECSITool — 802.11ax CSI from MT7916 AP (arXiv 2506.16957): <https://arxiv.org/html/2506.16957v1>
- Wi-BFI — beamforming-feedback extraction (arXiv 2309.04408): <https://arxiv.org/pdf/2309.04408>
- "Enabling CSI Extraction on Commercial 802.11ax" (ACM): <https://dl.acm.org/doi/10.1145/3477086.3480833>
