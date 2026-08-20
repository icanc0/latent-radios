# Verification summary: what we are confident about

> The trust dashboard for *Latent Radios*. The catalog holds **592 records across 104 vendors**, but breadth is not confidence. Confidence comes from the seven adversarial audits that tried to *refute* the catalog's own claims by tracing each to a primary source. This page consolidates all seven into one legible overview: for every audit, the headline finding, how many records held up (`verified`) versus how many were demoted to `reported`/`theoretical` or corrected, the single biggest correction it forced, and the uncertainty that remains after it. If you only read one page before trusting a tier mark, read this one — then open the specific audit it links to.
>
> **The one-sentence summary:** *No capability in the catalog was found to be fabricated — but "verified" was hiding real age, transport, and firmware caveats, and the strongest-claiming records (Tier 3–5, radar/UWB) over-reached about 1 in 5 times, always by attaching a capability the evidence supported one rung weaker.*

Read alongside the methodology that governs scoring: [../docs/methodology.md](../docs/methodology.md). The two rungs whose audits are cited most below: [../docs/verification-tier4.md](../docs/verification-tier4.md) (arbitrary-waveform TX) and [../docs/verification-tier2-csi.md](../docs/verification-tier2-csi.md) (CSI).

---

## The dashboard

Counts are for the **audited population** of each pass, not the whole 592-record catalog — an adversarial audit samples where the risk is, it does not re-derive every row. Where an audit worked at chip-*family* granularity (Tier 1, Tier 3) that is stated. "Corrected" = records the audit changed via merge (tier change, capability strip, band fix, or status downgrade); notes-only clarifications are not counted as corrections.

| Audit | Population | Held up (verified) | Downgraded / reported / theoretical | Corrected | Key caveat that survives the audit | Full audit |
|---|---|---|---|---|---|---|
| **Tier 1 — injection** | ~20 chip families | ~9 families inject reliably (grades A/B) | Intel `iwlwifi`, Marvell `mwifiex`, Realtek `rtw89` → **monitor-only** (grade D/F) | 3 families (injection stripped/downgraded) | Realtek USB injection is real only via the **out-of-tree DKMS driver**, not the in-kernel one | [./verification-tier1-injection.md](./verification-tier1-injection.md) |
| **Tier 2 — CSI** | 5 toolchains/records | **5 / 5 verified** (none fabricated) | 0 | 0 tier changes; 5 notes corrected | IWL5300 & Atheros are **`verified (legacy kernel)`** — native tools frozen at ~2015 kernels; live capture needs **PicoScenes** | [../docs/verification-tier2-csi.md](../docs/verification-tier2-csi.md) |
| **Tier 3 — spectral** | ~48 marks | ath9k (AR92xx/93xx) + ath10k AP chips **verified** | ath11k **reported**; Broadcom, Intel, MediaTek, Realtek marks are **over-marks** | Broadcom + Intel entries → **Tier 2/1** | Genuine Tier 3 is essentially **Qualcomm Atheros only**; "the silicon has an FFT engine" ≠ a public path to it | [./verification-tier3-spectral.md](./verification-tier3-spectral.md) |
| **Tier 4 — arbitrary TX** | 2 Wi-Fi entries | 0 (rung is **`reported`** for both, honestly) | Cross-tech emission = **theoretical**; RTL2832U at Tier 4 = flagged anomaly | 2 (re-anchor + promote) | Reproducible only via the **open-source MobiSys-2018 nexmon SDR** patch (ioctls 426/427/428), device/version-pinned; **this transmits — legal exposure is real** | [../docs/verification-tier4.md](../docs/verification-tier4.md) |
| **Tier 5 — open firmware** | ~21 marks (7 rows) | **openwifi** + true SDRs = genuine Tier 5 | 4 open-*firmware* parts → **Tier 1** | 4 downgrades + 1 affirmation | **Open MAC firmware ≠ open PHY ≠ SDR.** Open *driver* + closed blob is never Tier 5 | [./verification-tier5-openfirmware.md](./verification-tier5-openfirmware.md) |
| **Spot-check batch 1** | 20 records | OK 13, OK-caveat 3 | **4 FIX** (~20%) | 4 (raw-iq, caps, 2× bands) | High-claim records over-reach ~1 in 5; the *structured* field lied while the *prose note* was already honest | [./spot-check-audit-catalog-vs-datasheets.md](./spot-check-audit-catalog-vs-datasheets.md) |
| **Spot-check batch 2** | 18 records | OK 8, OK-caveat 7 | **3 FIX** (~17%) | 3 (bands, arb-waveform, passive-radar) | Same pattern at the **radar/UWB frontier**: chirp≠arbitrary-waveform; active≠passive-radar; enum has no 24 GHz / 76–81 GHz bucket | [./spot-check-audit-catalog-vs-datasheets-batch-2.md](./spot-check-audit-catalog-vs-datasheets-batch-2.md) |

---

## Tier 1 — which chips actually inject

**Headline finding.** "Has a monitor interface" and "the datasheet says 802.11" get silently rounded up to "it injects." They are different claims that fail independently. The ground truth is the aircrack-ng `aireplay-ng -9` gate, and the structural predictor is the driver class: mainline **softMAC** (mac80211) chips can inject; **FullMAC** designs (association + TX scheduling in closed firmware) give the host *no* injection path without firmware RE.

**How the audited families landed.**
- **Reference-grade (A):** `ath9k` (AR9280/9285/9287), `ath9k_htc` (AR9271/AR7010, open firmware), `mt76` (MT7612U, MT7921AU), `rt2800usb` (RT3070/5370). In-tree, blob-free, rate-honoring — these deserve `monitor`+`injection` without hedging.
- **Solid via out-of-tree driver (B):** the big Realtek USB parts (RTL8812AU/8814AU/8821CU/8188EUS). Injection is real, but it lives in the **community DKMS driver**, not the in-kernel `rtw88`/`rtl8xxxu`. This is the most-misfiled group in the catalog.
- **Monitor-only over-claims (D/F) — the corrections:** **Intel `iwlwifi`** (AX200/AX210/9260/8265/7260) captures beautifully but the closed firmware silently drops injected frames — Intel appears *nowhere* in aircrack-ng's recommended list. **Marvell `mwifiex`** and stock **Broadcom `brcmfmac`** are FullMAC: no host injection at all. **Realtek `rtw89`** (Wi-Fi 6/6E) has no mature injection path yet.

**Biggest correction.** Stripping `injection` from **Intel `iwlwifi`** parts (and Marvell, and downgrading `rtw89`): monitor capability was being read as Tier-1 injection. It is not.

**Residual uncertainty.** The A/B/D line moves with kernel and driver releases (in-kernel `rtw88`/`rtw89` monitor/injection is maturing); Broadcom injection *is* legitimate but **only through Nexmon** — a Broadcom `injection` flag that does not name Nexmon is over-claiming the stock chip.

## Tier 2 — CSI (the healthiest rung)

**Headline finding.** All five CSI toolchains reproduce the capability via *some* current public path — **none is fabricated** — so all five stay `verified`. CSI is read-only PHY telemetry, far more widely re-run than arbitrary TX, which is why this is the cleanest audit in the set.

**Counts.** 5 verified, 0 reported, 0 theoretical, **0 tier changes** — but five **notes** corrected so that `verified` stops being misread as "clone-and-go on any modern kernel."

**Biggest correction.** Exposing two age classes hiding under one word: **IWL5300** (Halperin tool, repo archived 2020, "Linux-2.6", caps ~kernel 4.2) and **Atheros AR9300** (Atheros-CSI-Tool ships a whole ~4.1.10 kernel tree to boot) are **`verified (legacy kernel)`**. Their honest 2025 reproduction path is **PicoScenes**, which carries the old NICs onto Ubuntu 22.04. The reproducible core for a newcomer is three tools on current hardware: **Nexmon CSI on a Raspberry Pi**, **ESP32** (no host-kernel dependency — the gold standard), and **Intel AX via FeitCSI** (kernel-agnostic live USB).

**Residual uncertainty.** PicoScenes is *reproducible* but binary/free-for-academic (not auditable source); Nexmon CSI is pinned to firmware string `7_45_189` with Bookworm/64-bit friction; ESP32-C6 802.11ax CSI has HE-LTF subcarrier-ordering quirks (use the 11n path). One logged inversion: on the Atheros part the *Tier-3* rung (`spectral_scan`, mainline) is **more** reproducible than the *Tier-2* CSI rung beneath it.

## Tier 3 — spectral scan

**Headline finding.** Genuine Tier 3 — a public path to raw baseband FFT bins — is essentially **Qualcomm Atheros only**. The recipe (debugfs `spectral_scan_ctl` → `spectral_scan0` relay → `FFT_eval`) is real and five-minute-reproducible on `ath9k`/`ath10k`; nobody else has an equivalent public relay.

**How the ~48 marks landed.**
- **Verified:** `ath9k` AR92xx/AR93xx (PCIe), `ath10k` QCA988x/9984/9888 (AP chips).
- **With caveats / reported:** `ath9k_htc` AR9271/AR7010 (needs `CONFIG_ATH9K_HTC_DEBUGFS`, USB-transport-limited); `ath11k` (in-tree but newer, `reported`); `ath10k` client parts (QCA6174/9377) firmware-gated.
- **Over-marks (downgraded):** **Broadcom "Nexmon spectral"** — Nexmon ships CSI/SDR/jammer but **no spectral extractor**; those marks were CSI mislabeled as spectral → **Tier 2**. **Intel `iwlwifi`** — the debug surface is prints/tracing/monitor/fw-debug, **no FFT anywhere** → **Tier 2/1**. MediaTek `mt76` and Realtek expose no ath-style FFT relay.

**Biggest correction.** Killing the two clean myths: **Broadcom** (CSI ≠ spectral) and **Intel** (no spectral scan is exposed on iwlwifi at all), both downgraded off Tier 3.

**Residual uncertainty.** `ath11k` spectral is real but under-exercised (`reported`); `ath10k` client-firmware coverage is uneven — verify before assuming; the feature silently dies on minimal/embedded kernels compiled without the debugfs option.

## Tier 4 — arbitrary-waveform TX

**Headline finding.** Tier 4 on the Broadcom/Nexmon parts **is justified** — but for the right reason. The reproducible proof is the **open-source MobiSys-2018 "Shadow Wi-Fi" nexmon SDR** patch (arbitrary `int16` I/Q → Template RAM via ioctls **426/427/428**), *not* the binary-only WiSec-2017 jammer the catalog had been citing.

**Counts.** 2 Wi-Fi entries, both **Tier 4 / `reported`** (research patch, device/version-pinned — not a turnkey `nexutil` feature). Cross-technology (Wi-Fi→ZigBee/BLE) emission stays **theoretical** for these chips.

**Biggest correction.** Two moves: (1) **re-anchoring** BCM4339's evidence from the un-reproducible binary jammer to the full-source SDR patch; (2) **promoting `broadcom-bcm43455c0` from Tier 3 → 4** — the identical patch supports it on a Raspberry Pi 3B+, making the **Pi the most reproducible Tier-4 Wi-Fi target in the catalog** (cheap, current, in-production). Also trimmed: `raw-iq` removed from BCM4339 (Nexmon exposes frequency-domain CSI, not time-domain IQ RX).

**Residual uncertainty.** Status stays `reported`, not `verified`: BCM4339's demo target is an EOL Nexus 5 on a specific 2016 image; both targets require exact firmware-string matching; the front-end is Wi-Fi-grade, not instrument-grade (bounded Template-RAM depth, band-limited). One flagged anomaly for maintainers: **`realtek-rtl2832u` sits at Tier 4 but cannot transmit** — RTL-SDR is RX-only; the ladder has no clean rung for real-SDR-class raw-IQ *receive*.

**Safety.** Everything at this rung **transmits** non-compliant energy. Reactive jamming is illegal against networks you do not own in essentially every jurisdiction. Reproduce only in a shielded enclosure / on a wired, attenuated, terminated bench, on frequencies and powers you are licensed to use.

## Tier 5 — open firmware / open PHY

**Headline finding.** Three different things get sloppily lumped under "open," and only one earns Tier 5: **open MAC firmware ≠ open PHY ≠ SDR.** A chip whose only open property is its MAC microcode has a *fixed silicon PHY* — you can retime and rewrite frames (Tier 1 + `open-firmware`) but you cannot synthesize an arbitrary waveform or read raw IQ.

**Counts.** ~21 marks reviewed. **Genuine Tier 5:** `openwifi` (open Verilog PHY on Zynq + AD9361/AD9364, actively maintained) and true SDRs (USRP/HackRF/bladeRF/LimeSDR/Pluto). **Four downgrades:** OpenFWWF Broadcom G-PHY (BCM4318), open-ath9k-htc (AR9271, AR7010), carl9170fw (AR9170) → **Tier 1 + `open-firmware`**.

**Biggest correction.** The four downgrades from any Tier-5/open-PHY reading to **Tier 1**: their firmware is genuinely open and rebuildable, but the PHY stays closed silicon. Separately, the "open driver, closed firmware" trap (`ath10k`, `ath11k`, `brcmfmac`, `iwlwifi`, `mt76`) contributes **nothing** to a Tier-5 claim — and Nexmon *patches* a closed blob (`patchable`), which is not *open* firmware.

**Residual uncertainty.** `openwifi` is Tier 5 by *building* the PHY — the opposite of this catalog's usual thesis (extracting SDR behavior from a locked commodity radio), so it belongs on the SDR shelf, framed as "an SDR that implements Wi-Fi." Upstream health varies: carl9170fw is active (2026), open-ath9k-htc is dormant (2023), OpenFWWF microcode is frozen (~2011) though its toolchain lives on.

## Spot-check audits — the meta-verification passes

Two sampling audits (**38 records total**, deliberately weighted toward the strongest structured claims) measured the catalog's own accuracy against primary sources.

**Headline finding.** ~**17–20%** of high-claim records carried a *structured* claim contradicted by their primary source — but with a consistent, correctable signature: in nearly every FIX the **prose `notes` field was already honest** while the machine-readable `sdr_capabilities`/`bands` over-reached. Structured spot-checking catches exactly this class of defect.

**The recurring failure signatures.**
1. **Capability inflation past the enum's meaning** — `raw-iq` on an ath9k part that only yields CSI + FFT magnitude (`atheros-ar9380`); `arbitrary-waveform`/`radar` on a 60 GHz beam-steering part (`qualcomm-qca9500`); `arbitrary-waveform` on a fractional-N **chirp** generator (`ti-iwr6843`); `passive-radar` on an **active** UWB transmitter (`qorvo-dw1000`). A flag must drop to the adjacent, weaker rung the evidence actually supports.
2. **Band over-reach / mis-bucketing** — RX-only SDRs topping out near 1.7 GHz tagged `2.4GHz` (`airspy-r2-hfplus`, `rtlsdr-rtl2832u` → `["sub-GHz"]`); a 24 GHz K-band radar tagged `2.4GHz`, a literal 10× error (`infineon-bgt24ltr11` → `[]`). The `bands` enum has no bucket for 1–2 GHz L-band, 24 GHz, or 76–81 GHz, which is the root cause.

**Biggest correction.** 7 records fixed across the two batches: `qualcomm-qca9500` was the largest single move (tier 3→2, capabilities reduced, status verified→`reported`).

**Residual uncertainty.** 4% and 3.5% samples of the catalog — absence of a FIX outside the sample is **not** evidence of correctness; the value is *calibration* of error kinds and rates in high-claim rows, not exhaustive validation. Several `OK (caveat)` rows still await a future cycle (e.g. add `802.11a` to `intel-iwl5300`/`realtek-rtl8720dn`; annotate the `sub-GHz` cellular-band convention) and a schema change should add `24GHz`/`76-81GHz` band buckets and split `arbitrary-waveform` (IQ) from "arbitrary bitstream/analog baseband."

---

## What we are confident about

- **Nothing in the catalog is fabricated.** Every capability audited traces to a real primary source. The corrections are about *tier*, *transport*, *age*, and *status* — not invention.
- **The Tier-1 injectors are solid:** `ath9k`, `ath9k_htc`, `mt76`, `rt2800usb` in-tree; the big Realtek USB parts via their OOT DKMS drivers.
- **CSI is the most trustworthy rung.** All five toolchains reproduce; ESP32 and Nexmon-on-Pi and FeitCSI-on-Intel are the newcomer-friendly, current-hardware paths.
- **Genuine spectral scan = Qualcomm Atheros `ath9k`/`ath10k`.** Reproducible in five minutes on a stock kernel.
- **Arbitrary-waveform TX is real on Broadcom via the open-source nexmon SDR patch** — and the Raspberry Pi (BCM43455c0) is the most reproducible target.
- **`openwifi` is the one genuine open-PHY Tier 5** among the RE'd parts (the rest are open-*firmware*, i.e. Tier 1).

## What remains uncertain

- **`verified` is not "plug-and-play."** For Tier ≥ 2 it usually means a patched firmware, a pinned kernel, or an out-of-tree driver. The IWL5300/Atheros CSI tools are `verified (legacy kernel)` and need PicoScenes to run on a modern host.
- **Firmware/kernel drift is the dominant risk.** Exact firmware strings must match; in-kernel driver maturation keeps moving the Realtek injection and ath11k spectral lines.
- **The `bands` and `sdr_capabilities` enums are lossy at the frontier** (no 24 GHz / 76–81 GHz bucket; `arbitrary-waveform` conflates IQ authoring with arbitrary bitstreams). Some "caveat" rows are enum limits, not defects.
- **~1 in 5 high-claim records over-reached in a structured field.** The spot-checks sampled where the risk is; the true whole-catalog rate on ordinary records is lower, but unmeasured outside the samples.
- **For anything you will buy or build on, open the record's `references[]` and prefer `status: verified`.** `reported`/`theoretical` map the frontier, they do not promise reproduction.

---

## See also

- [../docs/methodology.md](../docs/methodology.md) — how records are generated, scored, and why the correction machinery exists.
- [../docs/verification-tier2-csi.md](../docs/verification-tier2-csi.md) · [../docs/verification-tier4.md](../docs/verification-tier4.md) — the two most-cited audits above.
- [./verification-tier1-injection.md](./verification-tier1-injection.md) · [./verification-tier3-spectral.md](./verification-tier3-spectral.md) · [./verification-tier5-openfirmware.md](./verification-tier5-openfirmware.md) — the rest of the tier audits.
- [./spot-check-audit-catalog-vs-datasheets.md](./spot-check-audit-catalog-vs-datasheets.md) · [./spot-check-audit-catalog-vs-datasheets-batch-2.md](./spot-check-audit-catalog-vs-datasheets-batch-2.md) — the two datasheet spot-checks.
- [./taxonomy.md](./taxonomy.md) — the SDR ladder the tiers are scored against.
- [../chips/monitor-injection-support.md](../chips/monitor-injection-support.md) — install recipes behind the Tier-1 verdicts.

## References (audit primary sources, consolidated)

- aircrack-ng — injection test & driver taxonomy: <https://www.aircrack-ng.org/doku.php?id=injection_test> · <https://www.aircrack-ng.org/doku.php?id=compatibility_drivers>
- kernel.org wireless — ath9k/ath10k/ath11k/iwlwifi spectral & debug docs: <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
- SEEMOO Nexmon + nexmon_csi + MobiSys-2018 SDR patch: <https://github.com/seemoo-lab/nexmon> · <https://github.com/seemoo-lab/nexmon_csi> · <https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio>
- Halperin 802.11n CSI Tool (archived): <https://github.com/dhalperi/linux-80211n-csitool> · Atheros CSI Tool: <https://github.com/xieyaxiongfly/Atheros-CSI-Tool>
- PicoScenes (multi-NIC rescue platform): <https://ps.zpj.io/> · FeitCSI: <https://github.com/KuskoSoft/FeitCSI> · Espressif esp-csi: <https://github.com/espressif/esp-csi>
- FFT_eval (spectral decoder): <https://github.com/simonwunderlich/FFT_eval>
- openwifi (open-PHY Tier 5): <https://github.com/open-sdr/openwifi> · carl9170fw: <https://github.com/chunkeey/carl9170fw> · open-ath9k-htc-firmware: <https://github.com/qca/open-ath9k-htc-firmware> · OpenFWWF: <http://netweb.ing.unibs.it/~openfwwf/>
