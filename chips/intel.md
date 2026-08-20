# Intel Wi-Fi (iwlwifi) as an SDR

Intel's Wi-Fi silicon is the birthplace of commodity Wi-Fi sensing. The **IWL5300** carried the first widely-reproduced 802.11n Channel State Information (CSI) tool (Halperin et al., 2011), and more than a decade later the **AX200/AX210** family gave the sensing community its first 802.11ax CSI (Gringoli et al.'s **AX-CSI**, 2021), later joined by **FeitCSI** and the multi-NIC **PicoScenes** platform. Every one of these NICs runs **closed, signed Intel `iwlwifi` microcode** — so Intel's place on the SDR ladder is almost entirely a story of *what channel-state telemetry the firmware can be coerced into exporting*, not of open PHY access.

Unlike Broadcom (nexmon) or Atheros (ath9k), Intel never had a fully open or cleanly patchable ucode. The 5300 tool worked by binary-patching one specific 2010-era `iwlwifi-5000` ucode image; modern AX-series firmware is signed and can only be prodded through its own debug/CSI host-command surface. Intel exposes **no spectral-scan, no raw-IQ, and no arbitrary-waveform TX** through any public tool — so the ceiling for the whole vendor is **tier 2 (CSI)**. What Intel *does* offer that others don't is CSI over very wide channels (up to 160 MHz / ~2000 subcarriers) and, uniquely on the AX210, **CSI in the 6 GHz band**.

See also [../projects/csi-toolchains.md](../projects/csi-toolchains.md) for the cross-vendor CSI tool comparison and [../docs/firmware-reversing.md](../docs/firmware-reversing.md) for the closed-ucode patching background.

## The SDR ceiling for Intel

| Generation | Codename | Std | MIMO | Bands | CSI tool | Tier | Firmware |
|---|---|---|---|---|---|---|---|
| IWL4965 | Kilmer Peak | 11n | 2x3 | 2.4/5 | none | 1 | closed |
| **IWL5300** | Shirley Peak | 11n | 3x3 | 2.4/5 | **Linux 802.11n CSI Tool** | **2** | patched ucode |
| IWL5100/5150 | Shirley Peak | 11n | 1x2/2x2 | 2.4(/5) | none (wrong #chains) | 1 | closed |
| IWL6200/6300 | Centrino Adv/Ult-N | 11n | 2x2/3x3 | 2.4/5 | none public | 1 | closed |
| IWL7260/7265 | Wilkins/Stone Peak | 11ac | 2x2 | 2.4/5 | none | 1 | closed |
| IWL8260/8265 | Windstorm Peak | 11ac | 2x2 | 2.4/5 | none | 1 | closed |
| IWL9260/9560 | Thunder/Jefferson Pk | 11ac | 2x2 | 2.4/5 | none public | 1 | closed |
| **AX200/AX201** | Cyclone Peak | 11ax | 2x2 | 2.4/5 | **AX-CSI / FeitCSI / PicoScenes** | **2** | closed/patched |
| **AX210/AX211** | Typhoon Peak | 11ax (6E) | 2x2 | 2.4/5/**6** | **AX-CSI / FeitCSI / PicoScenes** | **2** | closed/patched |
| **BE200** | Gale Peak 2 | 11be (Wi-Fi 7) | 2x2 | 2.4/5/6 | reported (FeitCSI "likely") | 2* | closed/signed |

\*BE200 CSI is not yet a verified public workflow — see below.

---

## IWL5300 — the original 802.11n CSI Tool (tier 2)

The Intel WiFi Link 5300 (Shirley Peak, mini-PCIe part numbers **533AN_MMW / 533AN_HMW**, 3x3:3 MIMO, 2.4 + 5 GHz) is the single most-cited device in the entire Wi-Fi-sensing literature. Daniel Halperin, Wenjun Hu, Anmol Sheth and David Wetherall released the **Linux 802.11n CSI Tool** in November 2010 and announced it in the January 2011 *SIGCOMM CCR* ("Tool Release: Gathering 802.11n Traces with Channel State Information").

**What it exports.** For every received 802.11n packet the patched firmware reports the estimated channel matrix **H** for **30 subcarrier groups** (roughly one group per two OFDM subcarriers of a 20/40 MHz channel), each entry a complex number with **signed 8-bit real and 8-bit imaginary** resolution, for every Tx×Rx antenna pair (up to 3×3). It also reports per-chain RSSI, noise floor, AGC gain and the rate/antenna-selection (`rate_n_flags`) — enough to reconstruct absolute channel gain. This is genuine per-subcarrier **amplitude *and* phase**, which is what puts it on rung 2.

**How it's unlocked.** The tool ships a **binary-modified `iwlwifi-5000` ucode** (the "connector" firmware) plus a patched `iwlwifi`/`mac80211` driver and a `netlink`/`connector` userspace path (`log_to_file`) that streams CSI records to disk; Matlab/Octave `read_bfee` scripts parse them. Setting the NIC's monitor/injection and a fixed rate via the modified `iwl_connector` is part of the recipe. It is pinned to old kernels (the classic recipe is Ubuntu 10.04 / kernel 2.6.36, with community backports to ~4.x). Only the **3-antenna 5300** works — the firmware hard-codes 3 receive chains, so 5100/5150 do not.

**Firmware/RE.** The ucode runs on Intel's proprietary Wireless-MAC microcontroller; the ISA is undocumented. The "reversing" here was a targeted **binary patch** of the CSI-reporting and rate/antenna paths in one specific ucode image — hence `openness: patchable` for this exact part, even though Intel never documented anything.

- Project: https://dhalperi.github.io/linux-80211n-csitool/
- Source: https://github.com/dhalperi/linux-80211n-csitool
- Paper (CCR 2011): https://dl.acm.org/doi/10.1145/1925861.1925870

---

## AX200 / AX201 — Wi-Fi 6, and CSI is back (tier 2)

The **AX200** (Cyclone Peak, M.2/mini-PCIe discrete) and **AX201** (the CNVi companion soldered next to 10th-gen+ Intel CPUs) are 2×2 802.11ax parts, 2.4 + 5 GHz. After nearly a decade with no successor to the 5300 tool, three efforts reopened Intel CSI:

- **AX-CSI** (Francesco Gringoli et al., WiNTECH '21, *"AX-CSI: Enabling CSI Extraction on Commercial 802.11ax Wi-Fi Platforms"*) — the research-grade extractor. It taps the channel estimate the AX-series firmware already computes for its own equalizer/beamformer and pushes it out through a modified firmware + patched `iwlwifi`. It handles **all OFDM formats (11a/g/n/ac/ax)** and up to **160 MHz HE frames with ~1992 subcarriers in a single packet** — an order of magnitude more subcarriers than the 5300. Reported to cover **AX200/AX201/AX210/AX211**. `status: reported` (paper + released code).
- **FeitCSI** (Miroslav Hutar, KuskoSoft, MIT-licensed) — the first turn-key open tool with a GUI/CLI that does **CSI extraction *and* arbitrary 802.11 frame injection** for 11a/g/n/ac/ax across **20/40/80/160 MHz**, up to **512 subcarriers at 16-bit signed** precision, on stock-ish AX200/AX210. Architecture-portable (x86-64 and ARM). `status: verified`.
- **PicoScenes** (Zhiping Jiang & Rui Li, Xidian Univ.) — the heavyweight middleware that treats AX200/AX210 as one of many CSI front-ends (also IWL5300, QCA9300, USRP), with **multi-NIC concurrent capture (up to 27 NICs)**, full frame injection and a rich parsing SDK. `status: verified`.

**Ceiling = tier 2.** All three give per-subcarrier complex CSI; none gives spectral bins, raw IQ, or arbitrary baseband TX. FeitCSI/PicoScenes injection is *frame*-level (rung-1 capability), not IQ-level, so it does not raise the tier.

**Firmware/RE.** AX-series ucode is **closed and cryptographically signed**; the `csi`/channel-estimation debug surface these tools ride was not meant for users. AX-CSI distributes a patched firmware build; FeitCSI leans on the in-kernel iwlwifi CSI/debug host-command path that reached mainline (see nexmon_csi issue #207 noting "CSI extraction for latest Intel Wi-Fi is available in Linux kernel"). Practically `openness: closed`, unlockable only through the vendor's own debug hooks → treated as `patchable` for CSI purposes.

- AX-CSI paper: https://dl.acm.org/doi/10.1145/3477086.3480833 · PDF: https://ans.unibs.it/assets/documents/axcsi.pdf
- FeitCSI: https://feitcsi.kuskosoft.com/ · https://github.com/KuskoSoft/FeitCSI
- PicoScenes: https://ps.zpj.io/
- Parsing (all Intel formats): https://github.com/Gi-z/CSIKit

---

## AX210 / AX211 — Wi-Fi 6E, CSI in 6 GHz (tier 2)

The **AX210** (Typhoon Peak, discrete M.2) and **AX211** (CNVi, 12th-gen+ platforms) add the **6 GHz band (5945–7125 MHz)** and 160 MHz channels. All three toolchains support them, and PicoScenes is (per its authors) the **first and only public platform to do 802.11ax CSI *and* packet injection in the 6 GHz band** using the AX210. FeitCSI likewise captures 6 GHz CSI when the NIC supports it. This is Intel's most capable sensing device today: 6 GHz + 160 MHz + phase-coherent CSI, still tier 2. Same closed/signed firmware story as AX200.

- 6 GHz walkthrough: https://zpj.io/wifi-sensing-in-the-6-ghz-band_eng/
- https://feitcsi.kuskosoft.com/ · https://github.com/KuskoSoft/FeitCSI

---

## BE200 — Wi-Fi 7 (tier 2, reported/unverified)

The **BE200** (Gale Peak 2, M.2) is Intel's first Wi-Fi 7 (802.11be) part: 2×2, 2.4/5/6 GHz, up to **320 MHz** channels and 4K-QAM. No published tool yet confirms 320 MHz 11be CSI extraction; FeitCSI's authors note only a "high possibility that the newest Intel NIC is also supported," and AX-CSI/PicoScenes documentation stops at AX210/AX211. Treat BE200 CSI as `status: reported`/emerging until a verified capture appears. Firmware is closed and signed like the AX series.

- Product brief: https://cdrdv2-public.intel.com/761674/761674_Intel_Wi-Fi_7_BE200_GalePeak2_Product_Brief_Rev1p1.pdf

---

## Everything else (tier 1: monitor/injection only)

The remaining `iwlwifi` parts have **no public CSI/PHY path** and are useful only as ordinary `mac80211` monitor/injection radios (and even that is historically weaker than ath9k on Intel):

- **IWL4965** (Kilmer Peak) — Intel's first 802.11n draft part; no CSI tool.
- **IWL5100 / 5150** (Shirley Peak) — 1×2 / 2×2 siblings of the 5300; the CSI ucode's hard-coded 3-chain layout excludes them.
- **IWL6200 / 6300** (Centrino Advanced-N 6200 / Ultimate-N 6300) — the 6300 is a 3×3 11n part and is *occasionally* floated as a 5300 stand-in, but no maintained public CSI firmware exists for it.
- **IWL7260 / 7265** (Wilkins/Stone Peak), **8260 / 8265** (Windstorm Peak), **9260 / 9560** (Thunder/Jefferson Peak) — 802.11ac generations; monitor/injection only, no CSI tooling.

All run closed, increasingly signed `iwlwifi` ucode (LMAC + UMAC firmware split on the 7000-series and later). Reverse-engineering effort has gone almost entirely to Broadcom (nexmon) and Atheros instead — see [../docs/firmware-reversing.md](../docs/firmware-reversing.md).

## Un-cataloged / TODO

- **IWL3945 / 3160 / 3165 / 3168** — early and low-end parts; confirm none have any PHY telemetry path.
- **IWL6250 (Kilmer Peak 6250), 6235, 100/105/135** — fill in exact codenames, MIMO configs, band support.
- **AX411 / AX415 / AX1690 / AX1675** (Killer-branded Typhoon/Garfield Peak variants) — confirm they are AX200/AX210-class silicon and whether AX-CSI/FeitCSI bind to them.
- **BE201 / BE202 / BE1750 / BE1790** (Killer Wi-Fi 7 variants) — Gale Peak siblings; verify CSI status alongside BE200.
- **AX-CSI exact mechanism** — confirm whether it patches signed firmware or rides a vendor debug image; nail the per-format subcarrier tables (HE20/40/80/160) and bit resolution vs FeitCSI's 16-bit/512.
- **In-kernel iwlwifi CSI host command** — document exactly which mainline kernel/firmware versions expose the `csi`/channel-estimation notification FeitCSI depends on, and which NIC PCI IDs it gates on.
- **Killer/Rivet vs Intel firmware** — determine if Killer NICs use identical `iwlwifi-*.ucode` blobs (they should) so tool support transfers.
- **FTM / 802.11mc ranging** — several iwlwifi parts expose Fine Timing Measurement; assess whether the ToF/phase data there is separately exploitable.
