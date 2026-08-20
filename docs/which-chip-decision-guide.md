# Which Chip Should I Use? A Decision Guide

> **Latent Radios** catalogs Wi-Fi and wireless chips that can be pushed up the [SDR ladder](../docs/taxonomy.md) — from black-box radios into monitor, CSI, spectral, and (with real caveats) waveform-capable instruments. This page is the **front door**: tell it your *goal*, it points you at concrete hardware and tooling that is known to work, plus the one reason it is the right call and the catalog pages that go deep.
>
> New here? Skim the [taxonomy and SDR tier ladder](../docs/taxonomy.md) first, then use the [hardware index](../chips/hardware-index.md) to check exact part numbers, revisions, and where to actually buy the thing. Nothing on this page asks you to transmit; the sections that touch TX carry explicit regulatory warnings and defer to [RF safety and legal](../docs/rf-safety-and-legal.md).

---

## How to read this guide

Each goal below gives you:

- **Buy this** — the specific, currently-obtainable hardware that is the path of least resistance.
- **Why** — the single reason it wins for that goal.
- **Tier** — where it lands on the [0–5 SDR ladder](../docs/taxonomy.md) (0 black-box → 5 open/documented PHY or genuine SDR).
- **Watch out** — the gotcha that bites people.
- **Go deep** — the catalog page(s) with commands, drivers, and verification.

There is no single "best" chip. A $6 ESP32 and a $2,000 USRP sit in the same catalog because they answer *different* questions. Pick the row that matches your question, not the highest tier number.

---

## Quick-reference chooser

| Your goal | Buy this | Tier | Rough cost | Go deep |
|---|---|---|---|---|
| CSI, cheapest possible | **ESP32 / ESP32-S3** (ESP32-CSI-Tool) | 2 | ~$6–10 | [espressif](../chips/espressif.md) |
| CSI on a Pi / SBC | **Raspberry Pi + nexmon_csi** (BCM43455c0) | 2 | Pi + $0 (onboard) | [broadcom-cypress](../chips/broadcom-cypress.md), [walkthrough](../docs/walkthroughs/bcm43455c0-raspberry-pi.md) |
| Best / most flexible CSI | **Intel AX210 + PicoScenes** | 2 | ~$25 card | [intel](../chips/intel.md), [picoscenes](../projects/picoscenes.md) |
| Classic 4-antenna CSI | **Intel IWL5300 + Linux 802.11n CSI Tool** | 2 | ~$10–20 used | [intel](../chips/intel.md), [csi-toolchains](../projects/csi-toolchains.md) |
| Monitor + injection that just works | **ath9k AR9271** (USB) | 1 | ~$15 | [qualcomm-atheros](../chips/qualcomm-atheros.md) |
| Monitor + injection, 5 GHz / high throughput | **MT7612U (mt76)** or **RTL8812AU (morrownr)** | 1 | ~$15–25 | [mediatek-ralink](../chips/mediatek-ralink.md), [realtek](../chips/realtek.md) |
| Spectral scan (FFT of the air) | **ath9k AR9280 / AR9380 / AR93xx** | 3 | ~$10–30 | [qualcomm-atheros](../chips/qualcomm-atheros.md), [verification](../docs/verification-tier3-spectral.md) |
| Full PHY on an FPGA (open) | **openwifi (Zynq + AD9361)** | 5 | ~$200–1500 | [openwifi](../projects/openwifi.md) |
| Transmit arbitrary waveforms | **A real SDR** (HackRF / USRP / LimeSDR) | 5 | ~$150–2000 | [true-sdr-comparison](../docs/true-sdr-comparison.md) |
| Reverse a Wi-Fi firmware yourself | **BCM43455c0 + Nexmon** (or AR9271, or BL602) | varies | ~$15–35 | [firmware-reversing](../docs/firmware-reversing.md), [nexmon](../projects/nexmon.md) |
| Sub-GHz (ISM, 433/868/915) | **RTL-SDR** (RX) / **HackRF** or **Flipper Zero** (TX) | 5 / 5 / 1 | ~$30–320 | [lora-subghz](../chips/lora-subghz.md) |
| Sense through walls / presence | **CSI rig (above) + passive-radar mindset** | 2→ | reuse above | [csi-toolchains](../projects/csi-toolchains.md), [techniques](../docs/techniques.md) |

Prices are order-of-magnitude, mid-2020s street prices; check the [hardware index](../chips/hardware-index.md) for live sourcing notes and revision traps.

---

## "I want CSI, as cheaply as possible"

**Buy this:** an **ESP32** (or ESP32-S3 / ESP32-C-series) dev board and flash the [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool). If you already own a **Raspberry Pi 3B+/4/Zero 2 W** (or any board with the **BCM43455c0**), install **[nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)** instead and spend nothing extra.

**Why:** Espressif *documents* a CSI callback in its SDK — you get subcarrier amplitude/phase from a supported API, not a hack. It is the lowest-friction, lowest-cost entry to real channel data anywhere in the catalog.

**Tier:** 2 (CSI). **Cost:** ~$6–10 for an ESP32; $0 marginal on a Pi you own.

**Watch out:**
- ESP32 CSI is **20 MHz, single antenna, 2.4 GHz** (classic ESP32); throughput and subcarrier count are modest. Great for presence/motion, less so for high-resolution imaging.
- On the Pi, CSI capture is a **specific chip revision** (BCM43455**c0**) and needs the matching nexmon_csi build — the [Pi walkthrough](../docs/walkthroughs/bcm43455c0-raspberry-pi.md) pins the versions. Other Broadcom parts need different builds ([broadcom-cypress](../chips/broadcom-cypress.md)).
- Turn raw frames into usable matrices with the [nexmon-csi-to-usable-csi walkthrough](../docs/walkthroughs/nexmon-csi-to-usable-csi.md).

**Go deep:** [espressif](../chips/espressif.md) · [broadcom-cypress](../chips/broadcom-cypress.md) · [csi-toolchains](../projects/csi-toolchains.md)

---

## "I want the best / most flexible CSI"

**Buy this:** an **Intel Wi-Fi 6/6E card — AX200 / AX210 / AX211 — driven by [PicoScenes](https://ps.zpj.io/)**. If you want the classic research baseline instead, an **Intel IWL5300** with the [Linux 802.11n CSI Tool](https://dhalperi.github.io/linux-80211n-csitool/).

**Why:** PicoScenes is the most capable CSI framework in the catalog — it unifies Intel AX2xx, IWL5300, QCA, and several USB NICs behind one API, exposes wide bandwidth (up to 160 MHz on AX210) and multi-antenna MIMO CSI, and ships a MATLAB/plotting toolchain. The AX210 gives you **6 GHz + 160 MHz** channel measurements that the older tools cannot touch.

**Tier:** 2 (CSI), but with far richer dimensionality (bandwidth × spatial streams) than the cheap options.

**Watch out:**
- PicoScenes needs its **patched driver/firmware stack and a supported kernel** — follow [picoscenes](../projects/picoscenes.md) exactly; mismatched kernel/firmware is the #1 failure.
- **IWL5300** is the gold-standard *reproducible* CSI source (4 antennas via the "connector" hack, 30 subcarrier groups) but is 802.11n-era, 2.4/5 GHz, and increasingly hard to source — check [intel](../chips/intel.md) for the exact card variants and antenna wiring.
- CSI values are **arbitrary-scaled and phase-offset**; calibrate before you trust phase. See [verification-tier2-csi](../docs/verification-tier2-csi.md).

**Go deep:** [intel](../chips/intel.md) · [picoscenes](../projects/picoscenes.md) · [csi-toolchains](../projects/csi-toolchains.md) · [verification-tier2-csi](../docs/verification-tier2-csi.md)

---

## "I want monitor + injection that just works"

**Buy this:** an **Atheros AR9271** USB adapter (the driver is mainline **ath9k_htc** with open firmware). For 5 GHz, higher throughput, or newer builds, a **MediaTek MT7612U** (mainline **mt76**) or a **Realtek RTL8812AU** with the community **[morrownr/8812au](https://github.com/morrownr/8812au-20210629)** driver.

**Why:** These three cover the "packet-injection pentest / research NIC" space with the least pain. **AR9271** is the folklore-grade "it just works" card because its firmware is open and the driver is in-tree — no DKMS, no out-of-tree breakage. **mt76** parts are in-mainline too and add clean 5 GHz + AC rates. **RTL8812AU** is everywhere and cheap; morrownr's driver is the actively-maintained way to make it behave.

**Tier:** 1 (monitor + injection / raw packet).

**Watch out:**
- **AR9271 is 2.4 GHz, 802.11n only.** If you need 5 GHz or AC/AX, go MediaTek or Realtek.
- **Realtek** out-of-tree drivers are a moving target: match the driver branch to your kernel, expect occasional breakage on kernel upgrades, and prefer **morrownr's** repos over abandoned forks. mt76 avoids this by being mainline.
- "Injection works" is **per-driver and per-mode** — verify with `aireplay-ng --test` / `aircrack-ng` against a known target you own, not by assumption.

**Go deep:** [qualcomm-atheros](../chips/qualcomm-atheros.md) · [mediatek-ralink](../chips/mediatek-ralink.md) · [realtek](../chips/realtek.md) · [hardware-index](../chips/hardware-index.md)

---

## "I want spectral scan (an FFT of the channel)"

**Buy this:** an **Atheros ath9k** card with spectral support — **AR9280 / AR9285 / AR9287 (PCIe)** or **AR9380 / AR93xx**. Enable the kernel's `ath9k` **spectral_scan** debugfs interface.

**Why:** ath9k exposes the radio's built-in **FFT engine** through `debugfs`, giving you per-subcarrier magnitude bins across the channel — a genuine spectrum view of Wi-Fi bands from a $10–30 NIC. This is the cheapest Tier-3 (raw-PHY-ish) capability in the catalog and the classic basis for tools like `speccy`/FFT-eval.

**Tier:** 3 (spectral / raw-PHY).

**Watch out:**
- Spectral scan is a **capability of specific ath9k silicon and kernel builds** — not every "Atheros" card has it. Cross-check the exact part in [qualcomm-atheros](../chips/qualcomm-atheros.md).
- Output is **relative magnitude**, tied to the current channel/bandwidth; it is not a calibrated, absolute-power spectrum analyzer. Sanity-check as in [verification-tier3-spectral](../docs/verification-tier3-spectral.md).
- Modes: `chanscan`, `background`, `manual` — pick the one that matches whether you want to sweep or stare.

**Go deep:** [qualcomm-atheros](../chips/qualcomm-atheros.md) · [verification-tier3-spectral](../docs/verification-tier3-spectral.md) · [techniques](../docs/techniques.md)

---

## "I want to transmit arbitrary waveforms"

**Buy this:** honestly, **a real SDR** — **HackRF One**, **Ettus USRP (B2xx)**, **LimeSDR**, or **BladeRF**. If you specifically want to explore Wi-Fi-chip waveform injection as a *research* exercise, the **BCM4339 "Shadow Wi-Fi" / Nexmon arbitrary-transmission** work is the one credible-but-caveated path in the catalog.

**Why:** Wi-Fi chips are built to emit *802.11 frames*, not arbitrary IQ. A genuine SDR gives you a clean TX chain, documented sample rates, and legal-band flexibility — it is the right tool for waveform TX, full stop. The Nexmon **Shadow-Wi-Fi** results show a Broadcom PHY *can* be coaxed toward non-standard emissions, but it is fragile, chip-specific, and nowhere near a general DAC.

**Tier:** 5 for a real SDR; the BCM4339 path is best thought of as **aspirational Tier-4** with heavy asterisks.

**Watch out — regulatory, read this:**
- **Transmitting is regulated.** In most jurisdictions you may transmit only in permitted bands, at permitted power, usually only with a licence or under specific licence-exempt rules. Arbitrary-waveform TX in Wi-Fi bands can violate those rules **and** jam others. Use a **shielded enclosure / RF cage or wired attenuated setup**, or an amateur band you are licensed for. See [rf-safety-and-legal](../docs/rf-safety-and-legal.md) and [verification-tier4](../docs/verification-tier4.md) before energizing anything.
- The BCM4339 approach depends on a **specific chip + firmware patch**; treat any result as unverified until you reproduce it on your own dump per [firmware-reversing](../docs/firmware-reversing.md).
- For most people the honest answer is: **buy the SDR.** The Wi-Fi-chip TX path is a research curiosity, not a tool.

**Go deep:** [true-sdr-comparison](../docs/true-sdr-comparison.md) · [nexmon](../projects/nexmon.md) · [broadcom-cypress](../chips/broadcom-cypress.md) · [verification-tier4](../docs/verification-tier4.md) · [rf-safety-and-legal](../docs/rf-safety-and-legal.md)

---

## "I want to reverse-engineer Wi-Fi firmware myself"

**Buy this — pick by how much scaffolding you want:**

- **Most tooling / community:** **BCM43455c0** (Raspberry Pi 3B+/4/Zero 2 W) + **[Nexmon](https://github.com/seemoo-lab/nexmon)**. You inherit a whole patching framework, symbol maps, and a live target.
- **Most open silicon:** **Atheros AR9271** — open **ath9k_htc** firmware source, so you can read the real thing instead of guessing.
- **Modern RISC-V, fully open:** **BL602 / BL604** (Bouffalo Lab) — open-ish stack, RISC-V core, great for learning without a black box fighting you.

**Why:** Reversing is 80% about your target's *openness and existing scaffolding*. Nexmon hands you a patch framework and years of prior symbol-recovery on Broadcom parts; AR9271 lets you compare your reversing against actual firmware source; BL602 gives you a modern, documented RISC-V core where the toolchain is friendly.

**Tier:** the *point* is to climb tiers yourself — these are the springboards.

**Watch out:**
- Start with the **[Ghidra setup for Wi-Fi firmware](../docs/walkthroughs/ghidra-setup-wifi-firmware.md)** and the ISA-specific walkthroughs (**[BCM43455c0](../docs/walkthroughs/bcm43455c0-raspberry-pi.md)**, **[ESP32 Xtensa in Ghidra](../docs/walkthroughs/esp32-xtensa-ghidra.md)**). Wrong base address / wrong ISA variant wastes days.
- **Never invent addresses or offsets.** Recover them from *your own* dump using named symbols/structs; the [firmware-reversing](../docs/firmware-reversing.md) method shows how to anchor to real signatures rather than folklore constants.
- Broadcom ROM/RAM split and firmware versioning matter — a patch for one firmware string will silently misbehave on another.

**Go deep:** [firmware-reversing](../docs/firmware-reversing.md) · [nexmon](../projects/nexmon.md) · [qualcomm-atheros](../chips/qualcomm-atheros.md) · [risc-v-wifi](../chips/risc-v-wifi.md) · [ghidra-setup walkthrough](../docs/walkthroughs/ghidra-setup-wifi-firmware.md)

---

## "I want sub-GHz (433 / 868 / 915 MHz ISM, LoRa, remotes)"

**Buy this:**

- **Receive-only, cheapest:** an **RTL-SDR** (RTL2832U dongle). Best $30 in radio.
- **Receive + transmit, flexible:** a **HackRF One** (1 MHz–6 GHz, half-duplex TX/RX).
- **Field / portable, guided:** a **Flipper Zero** for sub-GHz remotes and simple protocols (bounded, appliance-style, not a general SDR).

**Why:** These are *purpose-built* for sub-GHz work, so you skip the whole Wi-Fi-chip-repurposing exercise. RTL-SDR covers RX across the ISM bands; HackRF adds legal-band TX; Flipper is the point-and-shoot option for remotes and access-control fobs.

**Tier:** RTL-SDR / HackRF are Tier 5 (genuine SDRs). Flipper is more like Tier 1 — capable but bounded firmware, not raw IQ.

**Watch out:**
- **RTL-SDR does not transmit.** For TX you need HackRF/LimeSDR/USRP or a dedicated ISM transceiver — and **TX in ISM bands is still regulated** (duty cycle, power). See [rf-safety-and-legal](../docs/rf-safety-and-legal.md).
- For the *chip*-repurposing angle (LoRa/sub-GHz transceivers with open firmware), the catalog's sub-GHz chip coverage — SX127x/SX126x, CC1101, nRF-class — lives in [lora-subghz](../chips/lora-subghz.md).
- Flipper's legality and capability vary by region and firmware; stay within bands and devices you own.

**Go deep:** [lora-subghz](../chips/lora-subghz.md) · [true-sdr-comparison](../docs/true-sdr-comparison.md) · [rf-safety-and-legal](../docs/rf-safety-and-legal.md)

---

## "I want to sense through walls / detect presence and motion"

**Buy this:** whatever gives you **CSI** most cheaply from the section above — an **ESP32** or a **Pi + nexmon_csi** to start, an **Intel AX210/IWL5300** rig when you want resolution — and then bring a **passive-radar / channel-perturbation mindset** on top.

**Why:** "Through-wall" and presence sensing in this catalog is a *software* achievement on top of *CSI* hardware. Motion and occupancy shift the multipath channel; CSI amplitude/phase time series expose that. You don't buy a "wall radar" — you buy a CSI source and process it. For true bistatic passive radar you pair an RX chain with an illuminator of opportunity, which is where real SDRs and the passive-radar techniques come in.

**Tier:** starts at 2 (CSI); passive-radar constructions reach toward Tier 3+ depending on the RX chain.

**Watch out — expectations and ethics:**
- **"Through walls" is marketing-adjacent.** Real results are coarse presence/motion/breathing detection through drywall, not imaging through concrete. Calibrate and validate before believing any classifier — [verification-tier2-csi](../docs/verification-tier2-csi.md).
- Phase is unstable across packets/NICs; the sensing literature leans on amplitude and careful phase-sanitization. The [csi-toolchains](../projects/csi-toolchains.md) and [techniques](../docs/techniques.md) pages cover the standard pipeline (denoise → phase-clean → feature → classify).
- **Sensing people has privacy and legal weight.** Sense only spaces and subjects you are authorized to; see [rf-safety-and-legal](../docs/rf-safety-and-legal.md).
- The 802.11-based sensing standard and where it points hardware are discussed in [techniques](../docs/techniques.md).

**Go deep:** [csi-toolchains](../projects/csi-toolchains.md) · [picoscenes](../projects/picoscenes.md) · [techniques](../docs/techniques.md) · [verification-tier2-csi](../docs/verification-tier2-csi.md)

---

## Cross-cutting gotchas (read before you buy anything)

1. **Revisions and part numbers are load-bearing.** "A Raspberry Pi" is not enough — CSI needs the **BCM43455c0** revision; "an Atheros card" is not enough — spectral needs specific ath9k silicon. Confirm the exact part in the [hardware index](../chips/hardware-index.md) before purchase; sellers relabel and re-spin constantly.
2. **Driver ↔ kernel coupling breaks setups.** Mainline (ath9k, mt76) survives kernel upgrades; out-of-tree Realtek/PicoScenes stacks need version-matching. Pin your kernel or accept maintenance.
3. **Tier number is not quality.** A Tier-2 IWL5300 is more useful for CSI research than a Tier-1 anything. Match the *goal*, not the ladder height.
4. **Anything that transmits is regulated.** Every TX-capable path here — arbitrary waveforms, sub-GHz TX, even injection at the edge — sits under real rules. Default to shielded/attenuated setups and read [rf-safety-and-legal](../docs/rf-safety-and-legal.md) and [verification-tier4](../docs/verification-tier4.md).
5. **Verify, don't assume.** Every claimed capability has a verification page: [CSI](../docs/verification-tier2-csi.md), [spectral](../docs/verification-tier3-spectral.md), [TX/waveform](../docs/verification-tier4.md). If you can't reproduce the measurement, you don't have the capability.

---

## Still not sure? Two-question triage

- **"Do I need to transmit?"**
  - *No* → you almost certainly want a **CSI, monitor, or spectral** Wi-Fi chip above. Cheap and legal.
  - *Yes* → strongly prefer a **real SDR**; the Wi-Fi-chip TX paths are research curiosities with regulatory teeth.
- **"Do I care about the channel (CSI) or the packets (frames)?"**
  - *Channel / sensing* → ESP32 → Pi+nexmon_csi → Intel AX210/PicoScenes, in ascending order of resolution and cost.
  - *Packets / injection* → AR9271 (2.4 GHz, just works) → MT7612U / RTL8812AU (5 GHz, AC).

---

### See also

- [Hardware index](../chips/hardware-index.md) — exact parts, revisions, sourcing.
- [Taxonomy & SDR tier ladder](../docs/taxonomy.md) — what the tiers and capability flags mean.
- [True-SDR comparison](../docs/true-sdr-comparison.md) — when to stop repurposing and buy a real radio.
- [Glossary](../docs/glossary.md) — CSI, spectral scan, injection, and friends, defined.

*Recommendations reflect the state of the catalog and community tooling as of this cycle. Prices, driver names, and chip availability drift — treat the linked chip and project pages as the authoritative, maintained detail, and this page as the map.*
