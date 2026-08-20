# Verifying the Tier-2 (CSI) claims: what actually reproduces in 2025

> The [Tier-4 audit](verification-tier4.md) asked whether the catalog's *arbitrary-waveform TX* marks survive contact with public tooling. This is its Tier-2 twin. **Tier 2** in [taxonomy.md](taxonomy.md) is *PHY telemetry / Channel State Information*: the chip hands software the complex per-OFDM-subcarrier channel estimate **H** (amplitude **and** phase) that it computed to equalize a packet. The claim is easy to *state* — "chip X does CSI" — and much harder to *reproduce*, because CSI almost always rides on a **firmware patch bound to a specific microcode string** and **a driver bound to a specific kernel**. A tool that built cleanly in 2015 on Ubuntu 14.04 / kernel 3.13 is not, on that evidence alone, reproducible on a 2025 machine running kernel 6.x. This document traces each Tier-2 toolchain in [../projects/csi-toolchains.md](../projects/csi-toolchains.md) to its repo and issue tracker and asks one adversarial question: **does it build and run today, on buyable hardware, or is the catalog's `verified` mark really `verified (legacy kernel)`?**

## What the catalog currently asserts

At the start of this audit the database held these Tier-2 (CSI-defining) Wi-Fi-lineage records, all `status: verified`:

| id | tier | flags | tool of record | chip(s) |
|----|------|-------|----------------|---------|
| `intel-iwl5300-csi` | 2 | monitor, csi | Linux 802.11n CSI Tool (Halperin) | Intel IWL5300 |
| `atheros-ar9300-csi` | 3 | monitor, injection, csi, spectral-scan | Atheros CSI Tool (Xie) | AR9580/9590/9344, QCA9558 |
| `broadcom-bcm43455c0-nexmon-csi` | 2 | monitor, injection, csi | Nexmon CSI (SEEMOO) | BCM4339/43455c0/4358/4366c0 |
| `espressif-esp32-csi` | 2 | monitor, csi | esp-csi / ESP32-CSI-Tool | ESP32 family |
| `intel-ax210-csi` | 2 | monitor, injection, csi | AX-CSI / FeitCSI / PicoScenes | Intel AX200/AX210 |

The headline question: **for how many of these does "verified" still mean "I can `git clone` and reproduce it on a current machine," versus "it was demonstrated once on a kernel you can no longer easily run"?**

The short answer, worked out below: **the CSI *capability* is real for all five** — none is fabricated. But **two of them (IWL5300, Atheros) are `verified (legacy kernel)`**: their *native* toolchains are frozen against kernels from ~2015 and do not build on 6.x. What keeps their claims honestly reproducible in 2025 is a **rescue platform, PicoScenes**, which repackages IWL5300 and QCA9300 support against a current Ubuntu LTS. The other three (Nexmon on the Pi, ESP32, Intel AX via FeitCSI) reproduce on current, buyable hardware directly.

---

## Tool-by-tool audit

### 1. Linux 802.11n CSI Tool (Halperin) — Intel IWL5300 → **verified (legacy kernel)**

The original commodity-CSI tool (Halperin, Hu, Sheth, Wetherall; SIGCOMM CCR 2011). It is two pieces: a **binary-patched Intel 5300 microcode** blob that turns on the CSI report, and a **modified `iwlwifi`** driver plus a `log_to_file` netlink consumer.

**Reproducibility today: no, not on a current kernel.**

- The upstream repo [`dhalperi/linux-80211n-csitool`](https://github.com/dhalperi/linux-80211n-csitool) self-describes as *"802.11n CSI Tool based on iwlwifi and **Linux-2.6**"* and was **archived (read-only) on 2020-06-27** — it is explicitly not maintained.
- The modified driver ships as a compat/backports tree targeting **kernel 3.x–4.x** (the practical ceiling users hit is around 4.2; it does not compile against 5.x/6.x `mac80211`/`cfg80211` without a substantial port that nobody has published). The netlink `connector` path and the `iwl_connector` glue depend on driver internals that mainline has since rewritten.
- It requires the **exact patched 5300 microcode** — you cannot swap in a stock `iwlwifi-5000` blob — and the IWL5300 itself is an **EOL 2008-era mini-PCIe card** (still findable used, but not new).

**Practical path in 2025:** boot a pinned legacy kernel (Ubuntu 14.04/16.04-era, kernel ≤4.x) in a VM/old laptop, **or** use **PicoScenes**, which carries IWL5300 support forward onto Ubuntu 22.04 (§6). The CSI format itself (30 subcarrier groups, int8 real/imag, ≤3×3) is understood by every downstream parser ([CSIKit](https://github.com/Gi-z/CSIKit)), so old `.dat` captures remain fully usable — it is *live capture on a modern host* that is broken.

**Verdict:** the capability is genuinely `verified` (a decade of reproduced results), but for the **native tool** it is `verified (legacy kernel)`. It stays in the catalog at Tier 2; the note is corrected to say so and to point at PicoScenes as the current path.

### 2. Atheros CSI Tool (Xie) — ath9k → **verified (legacy kernel)** for CSI; spectral-scan is *more* reproducible than its CSI

Built on the open `ath9k` SoftMAC driver, so the CSI hook lives in driver source (`ar9003_csi.c`), not a firmware blob — which sounds like it should age well. It does not, for a subtle reason.

**Reproducibility today: the native tool, no; but note the split.**

- The repo [`xieyaxiongfly/Atheros-CSI-Tool`](https://github.com/xieyaxiongfly/Atheros-CSI-Tool) is not a patch you apply to *your* kernel — it ships an **entire modified kernel source tree** (the repo contains `arch/`, `drivers/`, `fs/`, … — a whole Linux tree, ~4.1.10-era). You are expected to **build and boot that specific old kernel**. The [OpenWRT variant](https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src) is likewise pinned to an old Chaos-Calmer/LEDE base. Neither has been forward-ported to a 5.x/6.x tree, and the CSI hook has not landed in mainline `ath9k`.
- **The important nuance:** this record is **Tier 3**, and its tier-defining rung is **`spectral-scan`, not CSI**. Spectral scan (`ath9k` debugfs `spectral_scan`) **is in mainline** and works on a current kernel on the same silicon — so the *Tier-3* claim is reproducible today out of the box, while the *Tier-2* CSI claim underneath it is the legacy-kernel one. That inversion (the higher rung ages better than the lower) is worth stating in the record.
- **PicoScenes** supports this silicon as **"QCA9300"** and delivers per-subcarrier CSI on Ubuntu 22.04 — the current reproducible CSI path for Atheros, replacing the 4.1.10 kernel fork.

**Hardware:** AR9580 / AR9280 / QCA9558 cards are cheap and abundant (unlike the IWL5300), so the *hardware* side is healthy; only the *native software* is frozen.

**Verdict:** `verified` overall (tier unchanged at 3), but the note is corrected: **spectral_scan reproduces on mainline today; the Atheros-CSI-Tool CSI path is `verified (legacy kernel)` (~4.1.10 fork); current CSI is via PicoScenes.**

### 3. Nexmon CSI (SEEMOO) — Broadcom BCM43455c0 on Raspberry Pi → **verified, reproducible today (with pinning discipline)**

The most widely deployed *modern* commodity-CSI path, and the one that survives contact with 2025 best among the firmware-patched tools — because its hardware ([Raspberry Pi](https://github.com/seemoo-lab/nexmon_csi)) is current and the project tracks it.

**Reproducibility today: yes, on current Pi hardware, with caveats.**

- [`seemoo-lab/nexmon_csi`](https://github.com/seemoo-lab/nexmon_csi) lists support for **Raspberry Pi 3B+, 4B, and 5**, and now ships a **`Makefile.rpi` for recent Raspberry Pi OS kernels that no longer requires a modified `brcmfmac` driver** (kernels 4.19 / 5.4 / 5.10 are referenced; discussion [#395](https://github.com/seemoo-lab/nexmon_csi/discussions) covers recent kernels and the Pi 5). This is the crucial difference from IWL5300/Atheros: **the maintainers ported it forward.**
- **The pitfalls are real and are the bulk of its 171 open issues.** The BCM43455c0 firmware patch is **pinned to microcode string `7_45_189`** — your Pi's shipped `brcmfmac43455-sdio.bin` version must match, or the patched blob will not load. On current **64-bit Raspberry Pi OS (Bookworm)** users routinely hit toolchain/firmware-path mismatches and fall back to the 32-bit image or a friendlier fork ([nexmonster / zeroby0](https://github.com/seemoo-lab/nexmon_csi)) with a one-liner installer. The tracker's dominant themes are *data-quality* (amplitude scaling, dropped packets, null subcarriers) rather than *"won't build"* — which is itself evidence that people **are** building it.

**Verdict:** stays `verified` at Tier 2 — this is the **strongest commodity firmware-patched CSI story in the catalog**. The note is corrected only to record the firmware pinning (`7_45_189`), the Bookworm/64-bit friction, and Pi 5 support.

### 4. ESP32 CSI (esp-csi / ESP32-CSI-Tool / native ESP-IDF API) → **verified, the reproducibility gold standard**

The only Tier-2 path with an **official vendor CSI API** and — decisively for this audit — **no host-kernel dependency at all**. The CSI runs on the MCU; the host just reads CSV/serial. There is no `iwlwifi`, no `brcmfmac`, no kernel version to pin.

**Reproducibility today: yes, the easiest of all six.**

- The native `wifi_csi_info_t` callback is documented in current **ESP-IDF** (the *ESP-WIFI-CSI* guide), and [`espressif/esp-csi`](https://github.com/espressif/esp-csi) is actively maintained (200+ commits), advertising CSI across the **whole current line: ESP32 / S2 / S3 / C3 / C5 / C6 / C61**. Because it is a vendor API, a `git clone` + `idf.py build flash` reproduces it on today's SDK.
- **The one honest caveat is Wi-Fi 6:** ESP32-**C6** 802.11ax CSI has reported **HE-LTF subcarrier-ordering / null-subcarrier quirks** (tracked in esp-idf issues, e.g. #14271-class reports); the mature, unquestionably-reproducible path is 802.11n (HT-LTF) CSI on the classic ESP32. 1×1 only, ≤52/64 subcarriers.

**Verdict:** stays `verified` at Tier 2, and should be flagged in prose as **the most reproducible Tier-2 entry in the catalog** — the reference point the others are measured against.

### 5. AX-CSI / FeitCSI — Intel AX200/AX210 (Wi-Fi 6/6E) → **verified, reproducible today via FeitCSI**

Two things share this record. **AX-CSI / IAX** (Gringoli, Cominelli, Blanco, Widmer; WiNTECH'21) is the *research* microcode patch that first pulled CSI off commercial 802.11ax silicon. **FeitCSI** (KuskoSoft) is the *packaged, maintained* descendant that makes it reproducible.

**Reproducibility today: yes — and this one was engineered specifically to defeat version-pinning.**

- [`KuskoSoft/FeitCSI`](https://github.com/KuskoSoft/FeitCSI) ships **source, prebuilt binaries, and a live-USB distribution**, and states it works on **any Linux architecture with no restriction to a specific kernel version** because it carries its own patched microcode and driver plumbing rather than depending on the host's `iwlwifi`. It supports **AX200 and AX210** (with "high possibility" newer Intel NICs work) and is backed by a **2025 IEEE paper**, *"Enhancing CSI-based Wireless Sensing with Open Source Linux 802.11ax CSI Tool"* ([doc 10944229](https://ieeexplore.ieee.org/document/10944229/)). AX210 adds **6 GHz** CSI; FeitCSI also does **frame injection**.
- **Bare AX-CSI** (the UNIBS research release) is the more version-pinned artifact; for reproduction, FeitCSI (or PicoScenes, §6) is the path to cite, the same way the Tier-4 audit re-anchored BCM4339 from the binary jammer to the source SDR patch.
- **Hardware is current and cheap:** AX200/AX210 M.2 cards are in-production commodity parts.

**Verdict:** stays `verified` at Tier 2. Note corrected to name **FeitCSI (live USB, kernel-agnostic) as the reproducible path** and AX-CSI as the underlying research primitive.

### 6. PicoScenes — the rescue platform that keeps three legacy claims alive

PicoScenes (Zhiping Jiang) is not one chip's tool; it is a **maintained multi-NIC platform**, and this audit's most load-bearing finding is that **it is what makes the IWL5300 and QCA9300 CSI claims reproducible in 2025 at all.**

- **Actively maintained:** `.deb` / `apt`-distributed, installs in ~10 minutes, **officially on Ubuntu 22.04 (transitioning to 24.04)**, site last updated **2025-04-29**. It absorbs the driver/firmware-version pain and tracks the distro so *you* do not have to boot a museum kernel.
- **Supported NICs:** **IWL5300, QCA9300 (AR9300 family), AX200, AX210**, plus **USRP / SoapySDR** front-ends. So it independently reproduces four of this catalog's Tier-2 silicon lines on a single current OS.
- **Caveats to be honest about:** it is **binary, free-for-academic-use** (not fully open source), so it is a *reproducible* path but not an *auditable-source* one; and it is pinned to the **supported Ubuntu LTS** — you follow its distro, not the reverse.

PicoScenes is why `intel-iwl5300-csi` and `atheros-ar9300-csi` stay `verified` rather than sliding to `reported`: the capability has a living, current-hardware-and-OS reproduction path even though each chip's *original* tool is frozen.

---

## Verdict table

| Tool | Chip(s) | Reproducible **today** on a current kernel? | Caveat |
|------|---------|---------------------------------------------|--------|
| **Linux 802.11n CSI Tool** (Halperin) | Intel IWL5300 | **No (native)** — repo archived 2020, "Linux-2.6", driver caps ~kernel 4.2 | Legacy kernel ≤4.x, or **use PicoScenes**. IWL5300 is EOL hardware. |
| **Atheros CSI Tool** (Xie) — CSI | AR9580/9590/9344, QCA9558 | **No (native)** — ships a whole ~4.1.10 kernel tree to boot | Legacy kernel, or **use PicoScenes** (QCA9300). Hardware cheap & plentiful. |
| **Atheros** — `spectral_scan` (Tier-3 rung) | same | **Yes** — in mainline `ath9k` debugfs | The higher rung ages *better* than its CSI; works on current kernels. |
| **Nexmon CSI** (SEEMOO) | BCM43455c0 (Pi 3B+/4B/5) | **Yes** — `Makefile.rpi` for recent kernels; no modified `brcmfmac` needed | Firmware pinned `7_45_189`; Bookworm/64-bit friction; 171 open issues (mostly data-quality). |
| **ESP32 CSI** (native ESP-IDF) | ESP32 / S2/S3 / C3/C5/C6/C61 | **Yes — easiest of all** | No host-kernel dependency; vendor API. C6 11ax LTF-ordering quirks; use 11n path. |
| **FeitCSI** (KuskoSoft) | Intel AX200 / AX210 | **Yes** — source + binary + live USB, kernel-agnostic | Carries own patched µcode; 6 GHz on AX210. Backed by 2025 IEEE paper. |
| **AX-CSI / IAX** (research) | Intel AX200/AX210 | Partially | Version-pinned research release; reproduce via **FeitCSI** or PicoScenes instead. |
| **PicoScenes** (Jiang) | IWL5300, QCA9300, AX200, AX210, USRP | **Yes** — apt/.deb on Ubuntu 22.04 (→24.04) | Binary, free-academic (not open source); pinned to supported Ubuntu LTS. |

## Corrected records (emitted below, same ids → they merge)

None of the five needs a **status downgrade** — every CSI capability is genuinely reproducible via *some* current path, so all stay `verified`. What changes is the **notes**, to stop `verified` from being read as "clone-and-go on any modern machine":

- **`intel-iwl5300-csi`** — note now states the native Halperin tool is **legacy-kernel-only** (archived 2020, ≤4.x) and names **PicoScenes** as the current path; flags the IWL5300 as EOL hardware.
- **`atheros-ar9300-csi`** — note now splits the rungs: **`spectral_scan` reproduces on mainline `ath9k` today**, while the **Atheros-CSI-Tool CSI path is `verified (legacy kernel)`** (~4.1.10 kernel fork); current CSI via **PicoScenes (QCA9300)**.
- **`broadcom-bcm43455c0-nexmon-csi`** — note now records **firmware pinning `7_45_189`**, the **`Makefile.rpi` recent-kernel path**, **Pi 5** support, and the 64-bit **Bookworm** friction; remains the strongest firmware-patched commodity CSI story.
- **`espressif-esp32-csi`** — note now flags it as **the most reproducible Tier-2 entry** (no host-kernel dependency, vendor API, C61 added) and records the **ESP32-C6 802.11ax LTF-ordering caveat**.
- **`intel-ax210-csi`** — note now names **FeitCSI (live USB, kernel-agnostic, 2025 IEEE paper) as the reproducible path** and AX-CSI as the underlying research primitive; **PicoScenes** as the multi-NIC alternative.

## Bottom line

- **No Tier-2 CSI claim in the catalog is fabricated** — all five reproduce via *some* public path, so all stay `verified`. This is a healthier picture than the Tier-4 audit found, because CSI (read-only PHY telemetry) is far more widely re-run than arbitrary TX.
- **But `verified` was hiding two age classes.** The **IWL5300** and **Atheros** *native* tools are `verified (legacy kernel)` — frozen against ~2015 kernels, un-buildable on 6.x. Their honest reproduction path in 2025 is **PicoScenes**, the platform that carries the old NICs onto a current Ubuntu LTS. This is the CSI-side analogue of the Tier-4 finding that the reproducible primitive was not the tool the catalog was citing.
- **The reproducible core is three tools on current hardware:** **Nexmon CSI on a Raspberry Pi** (firmware-pinned but maintained), **ESP32** (no kernel dependency — the gold standard), and **Intel AX via FeitCSI** (kernel-agnostic live USB). These are where a newcomer should start.
- **One nice inversion, logged for the maintainers:** on the Atheros part the *Tier-3* rung (`spectral_scan`, mainline) is **more** reproducible than the *Tier-2* rung (CSI, legacy fork) beneath it — a reminder that `sdr_tier` tracks the highest rung, not the freshness of each rung's tooling.

## Safety and regulatory note

CSI extraction is **receive-only** — you are reading channel estimates off frames the radio already demodulates — so it does **not** raise the transmit-side legal exposure of the [Tier-4 audit](verification-tier4.md). Two honest caveats remain: (1) several tools (Nexmon, FeitCSI, ath9k injection) also enable **frame injection / monitor** on the same hardware, which *is* regulated — do not transmit on channels/powers you are not licensed for; and (2) CSI is a **sensing** capability (presence, motion, breathing, gait, keystroke inference), so capturing it about people who have not consented raises privacy and, in some jurisdictions, wiretap/consent questions independent of RF rules. Sense your own space, or a lab, with consent.

## See also

- [../projects/csi-toolchains.md](../projects/csi-toolchains.md) — the full toolchain survey these verdicts audit (formats, subcarrier counts, links).
- [taxonomy.md](taxonomy.md) — the Tier-2 definition these claims are scored against.
- [verification-tier4.md](verification-tier4.md) — the sibling arbitrary-waveform-TX audit this parallels.
- [../projects/picoscenes.md](../projects/picoscenes.md) — the rescue platform that keeps IWL5300/QCA9300 CSI reproducible.
- [../projects/nexmon.md](../projects/nexmon.md) — the firmware-patching framework under Nexmon CSI.
- [../chips/intel.md](../chips/intel.md) · [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) · [../chips/espressif.md](../chips/espressif.md) — the silicon.

## References

1. Halperin, Hu, Sheth, Wetherall — *Tool Release: Gathering 802.11n Traces with Channel State Information*, ACM SIGCOMM CCR 2011. Tool: <https://dhalperi.github.io/linux-80211n-csitool/> · repo (archived 2020-06-27, "based on iwlwifi and Linux-2.6"): <https://github.com/dhalperi/linux-80211n-csitool> · supplementary: <https://github.com/dhalperi/linux-80211n-csitool-supplementary>
2. Xie, Li — *Atheros CSI Tool* (ath9k, ships a ~4.1.10 kernel tree): <https://github.com/xieyaxiongfly/Atheros-CSI-Tool> · OpenWRT: <https://github.com/xieyaxiongfly/Atheros_CSI_tool_OpenWRT_src> · guide: <https://wands.hk/external/wifi/AtherosCSI/index.html>
3. `ath9k` `spectral_scan` (mainline, current kernels): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
4. Gringoli, Schulz, Link, Hollick — *Free Your CSI: A Channel State Information Extraction Platform For Modern Wi-Fi Chipsets* (Nexmon CSI, WiNTECH 2019). Repo (firmware `7_45_189`, `Makefile.rpi`, Pi 3B+/4B/5, 171 open issues): <https://github.com/seemoo-lab/nexmon_csi> · DOI: <https://doi.org/10.1145/3349623.3355477>
5. Espressif — *ESP-WIFI-CSI* native API + `esp-csi` (ESP32 / S2/S3 / C3/C5/C6/C61, actively maintained): <https://github.com/espressif/esp-csi> · toolkit: <https://github.com/StevenMHernandez/ESP32-CSI-Tool>
6. Gringoli, Cominelli, Blanco, Widmer — *AX-CSI: Enabling CSI Extraction on Commercial 802.11ax Wi-Fi Platforms*, ACM WiNTECH 2021. Paper: <https://ans.unibs.it/assets/documents/axcsi.pdf> · DOI: <https://doi.org/10.1145/3477086.3480833>
7. KuskoSoft — *FeitCSI* (source + binary + live USB, kernel-agnostic, AX200/AX210, 6 GHz): <https://github.com/KuskoSoft/FeitCSI> · <https://feitcsi.kuskosoft.com/> · IEEE 2025 paper: <https://ieeexplore.ieee.org/document/10944229/>
8. Jiang et al. — *PicoScenes* (multi-NIC platform; IWL5300/QCA9300/AX200/AX210/USRP; Ubuntu 22.04→24.04, updated 2025-04-29): <https://ps.zpj.io/> · arXiv: <https://arxiv.org/pdf/2010.10233>
9. `CSIKit` (Gi-z) — universal parser for all formats above (old `.dat` captures remain usable): <https://github.com/Gi-z/CSIKit>
