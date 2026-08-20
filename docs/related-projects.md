# Related Projects & How This Catalog Fits

*Latent Radios* is not the first or only resource in the "commodity radios as measurement instruments" space, and it does not try to be an island. This page is an honest map of the neighborhood: the awesome-lists, tool ecosystems, research groups, and survey literature that this catalog stands on the shoulders of — and a precise statement of the narrow thing this catalog adds that those resources do not.

If you are new here, read this page *before* diving into the chip tables. It will tell you when another project is the better tool for your job, and where to go when you outgrow ours.

**See also in this repo:** [Further reading](../docs/further-reading.md) · [Awesome tools](../projects/awesome-tools.md) · [Project overview / README](../README.md)

---

## TL;DR — what this catalog uniquely adds

Almost every resource below is *deeper* than us on its own axis: aircrack-ng owns attack tooling, PicoScenes owns multi-NIC CSI, SEEMOO owns Broadcom firmware RE, SoapySDR owns the SDR HAL. What none of them do is the thing this catalog exists for:

1. **A single cross-vendor SDR-ladder score (tier 0–5) applied uniformly** to Wi-Fi/wireless silicon — Broadcom, Qualcomm/Atheros, Intel, Espressif, Realtek, MediaTek, Nordic, TI, Silicon Labs, and more — so you can compare an AX210, a BCM43455c0, an ATH9K, and an ESP32 on one honest axis. The other projects each live inside one vendor or one capability.
2. **The firmware-reverse-engineering angle treated as a first-class, cross-vendor discipline** — not "here is a tool for chip X" but "here is what is *knowable and patchable* on chip X, and how you would find out." (See [`../docs/methodology.md`](methodology.md) and [`../docs/techniques.md`](techniques.md).)
3. **A machine-readable database** (the `modules[]` records behind every chip page) — queryable, diffable, mergeable — rather than prose or a wiki table. You can grep it, join it, and build on it.
4. **Per-tier, reproducible verification** — a claim of "tier 3 / spectral-scan" is backed by a documented procedure someone actually ran, not a marketing bullet or a forum anecdote. (See the `verification-tier*` docs and the `docs/walkthroughs/` builds.)

Everything else on this page does one or more of those things *better* than us in its slice. Our value is the unifying frame across slices, plus intellectual honesty about tiers and limits (see [`../docs/honest-limitations-of-wifi-sensing.md`](honest-limitations-of-wifi-sensing.md)).

---

## The awesome-lists and community wikis

These are the broad, community-curated index pages. They are wider than us and constantly updated; they are the right first stop for "what exists at all."

| Resource | What it is | Where it beats us | Where we differ |
|---|---|---|---|
| **RTL-SDR.com blog + Osmocom rtl-sdr wiki** ([rtl-sdr.com](https://www.rtl-sdr.com/), [osmocom.org/projects/rtl-sdr/wiki](https://osmocom.org/projects/rtl-sdr/wiki)) | The de-facto community hub for cheap DVB-T dongles as SDRs, plus a decade of application write-ups | Breadth of *receive-only* SDR applications, hardware buying advice, driver setup | We cover Wi-Fi *transceiver* silicon (TX-capable, tier 4/5 ambitions), not RX dongles |
| **"Awesome SDR" curated lists** (search GitHub topics [`software-defined-radio`](https://github.com/topics/software-defined-radio)) | Link farms of SDR hardware, DSP libraries, decoders | Coverage of the general-purpose SDR toolchain (GNU Radio ecosystem, decoders) | We are narrowly about *Wi-Fi/wireless-NIC* silicon repurposed via firmware, not USRP/HackRF-class radios |
| **Awesome WiFi / WiFi-security lists** (various GitHub repos) | Indexes of Wi-Fi tooling, papers, CTF material | Attack tooling breadth, learning paths | We score *chips*, not tools, and we grade sensing/SDR capability rather than pentest utility |

Honest note: the "awesome-\*" repos churn — slugs and maintainers change. Treat them as indexes to *reach* primary sources, and always confirm the primary repo/paper yourself. That is exactly the discipline our per-record `references[]` enforces.

---

## The aircrack-ng ecosystem (monitor mode & injection)

- **aircrack-ng** — [aircrack-ng.org](https://www.aircrack-ng.org/) · [github.com/aircrack-ng/aircrack-ng](https://github.com/aircrack-ng/aircrack-ng)
- **Kismet** — [kismetwireless.net](https://www.kismetwireless.net/)
- **Wireshark** (radiotap dissection) — [wireshark.org](https://www.wireshark.org/)
- The Linux `mac80211` monitor-mode + `nl80211`/`iw` stack — [wireless.wiki.kernel.org](https://wireless.wiki.kernel.org/)

This ecosystem *is* the ground truth for **tier 1 (monitor + injection)**. When we assign a chip tier 1, the operational meaning is "aircrack-ng-style monitor/injection works," and the practical test is `aireplay-ng --test` or `iw dev ... set monitor`. We deliberately do **not** re-document their tooling — see [`../docs/verification-tier1-injection.md`](verification-tier1-injection.md) and [`../projects/awesome-tools.md`](../projects/awesome-tools.md), which point straight at them.

What we add on top: aircrack-ng cares whether injection *works*; we care *why it does or doesn't at the firmware level*, and whether the same chip can be pushed past tier 1 into CSI (tier 2) or spectral (tier 3). The aircrack-ng compatibility notes and the kernel driver source (`drivers/net/wireless/…`) are our cross-check for the monitor/injection column — see [`../chips/monitor-injection-support.md`](../chips/monitor-injection-support.md).

---

## SEEMOO / Secure Mobile Networking Lab (the firmware-RE core)

TU Darmstadt's SEEMOO lab is the intellectual anchor of the whole Broadcom/Cypress side of this catalog.

- **nexmon** — C firmware-patching framework for Broadcom/Cypress — [github.com/seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon)
- **nexmon_csi** — CSI extraction on BCM43455c0 and friends — [github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)
- **InternalBlue** — Bluetooth (Broadcom/Cypress) RE framework — [github.com/seemoo-lab/internalblue](https://github.com/seemoo-lab/internalblue)
- Lab homepage — [seemoo.de](https://www.seemoo.tu-darmstadt.de/)

nexmon is not a competitor to this catalog; it is a *primary source* for it. Our Broadcom/Cypress pages ([`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md)) and our nexmon project page ([`../projects/nexmon.md`](../projects/nexmon.md)) exist to *situate* nexmon's per-chip reality inside the cross-vendor ladder: nexmon proves tier 1–3 is reachable on specific BCM parts, and demonstrates covert-channel and jammer work that touches the higher tiers. We add the comparison to *other* vendors nexmon doesn't cover, and the honest tiering of exactly which chip/firmware pairs have been shown to do what. The reproducible build is in [`../docs/walkthroughs/bcm43455c0-raspberry-pi.md`](walkthroughs/bcm43455c0-raspberry-pi.md).

---

## PicoScenes and the CSI-toolchain lineage

**PicoScenes** — [github.com/wifisensing](https://github.com/wifisensing) · docs at [ps.zpj.io](https://ps.zpj.io/) — is the most complete modern Wi-Fi **CSI / ISAC** middleware. It unifies CSI extraction across Intel AX210/AX200, Atheros AR9300, Intel 5300, plus HackRF and USRP SDRs, up to 160 MHz and into the 6 GHz band, with a real plugin/scripting layer.

Predecessor and sibling CSI toolchains (all real, all primary sources we cite):

- **Linux 802.11n CSI Tool** (Halperin et al., Intel IWL5300) — [dhalperi.github.io/linux-80211n-csitool](https://dhalperi.github.io/linux-80211n-csitool/)
- **Atheros CSI Tool** (Xie et al., ath9k) — [wands.sg/research/wifi/AtherosCSI](https://wands.sg/research/wifi/AtherosCSI/)
- **ESP32-CSI-Tool** (Hernandez) — [github.com/StevenMHernandez/ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool)
- **nexmon_csi** (above)

These *are* tier 2. PicoScenes is broader and better-engineered than anything we would write, and for actually *collecting* CSI you should use it or one of the tools above — see [`../projects/csi-toolchains.md`](../projects/csi-toolchains.md) and the end-to-end [`../docs/walkthroughs/nexmon-csi-to-usable-csi.md`](walkthroughs/nexmon-csi-to-usable-csi.md). What we add: PicoScenes answers "how do I get CSI from a supported NIC?"; we answer "which of the 592 chips can produce CSI *at all*, at what tier, and with what firmware effort" — the map, not the vehicle. Our tier-2 verification is [`../docs/verification-tier2-csi.md`](verification-tier2-csi.md).

---

## The general SDR abstraction layer: SoapySDR, GNU Radio, hamlib

When a Wi-Fi chip is pushed to tier 4/5 (arbitrary waveform / open PHY), it starts to look like a real SDR — and the mature SDR software stack becomes the destination:

- **SoapySDR** (vendor-neutral SDR hardware abstraction) — [github.com/pothosware/SoapySDR/wiki](https://github.com/pothosware/SoapySDR/wiki)
- **GNU Radio** (flowgraph DSP framework) — [gnuradio.org](https://www.gnuradio.org/)
- **Hamlib** (radio-control abstraction) — [hamlib.github.io](https://hamlib.github.io/)
- **Osmocom** (GSM/SDR umbrella) — [osmocom.org](https://osmocom.org/)
- SDR apps: **SDRangel** ([github.com/f4exb/sdrangel](https://github.com/f4exb/sdrangel)), **Gqrx** ([gqrx.dk](https://gqrx.dk/)), **CubicSDR**
- Reference SDR hardware for comparison: **HackRF** (Great Scott Gadgets — [greatscottgadgets.com/hackrf](https://greatscottgadgets.com/hackrf/)), **USRP/UHD** (Ettus/NI — [github.com/EttusResearch/uhd](https://github.com/EttusResearch/uhd)), **LimeSDR**, **PlutoSDR**.

We do **not** duplicate this stack — we point to it. The honest framing this catalog insists on: a repurposed Wi-Fi NIC is almost never a drop-in SoapySDR device. Tier 5 is rare and hard-won. Most "Wi-Fi as SDR" lives at tiers 1–3, and calling it a "genuine SDR" is exactly the bravado we grade against (see [`../docs/taxonomy.md`](taxonomy.md) and [`../docs/glossary.md`](glossary.md)). Where a chip genuinely reaches raw-IQ/arbitrary-waveform territory, our [`../docs/verification-tier4.md`](verification-tier4.md) and [`../docs/verification-tier5-openfirmware.md`](verification-tier5-openfirmware.md) document the evidence, and the SDR stack above is where you take it next.

---

## The WiFi-sensing survey literature

The sensing research corpus is both a source of chip capability claims and a reality check on them. Key entry points (use these to reach the reference lists, which are gold):

- **Ma, Zhou, Wang — "WiFi Sensing with Channel State Information: A Survey,"** *ACM Computing Surveys*, 2019. The most-cited umbrella survey; its bibliography is effectively a directory of CSI-based sensing work. [DOI 10.1145/3310194](https://doi.org/10.1145/3310194)
- **Yousefi et al. — "A Survey on Behavior Recognition Using WiFi CSI,"** *IEEE Communications Magazine*, 2017. [DOI 10.1109/MCOM.2017.1700082](https://doi.org/10.1109/MCOM.2017.1700082)
- **IEEE 802.11bf** — the WLAN *sensing* amendment; the standards effort that formalizes "Wi-Fi as radar." Track via the [IEEE 802.11 Task Group bf](https://www.ieee802.org/11/) pages.
- Foundational systems papers routinely cited from the above: FIFA/WiSee/WiVi, SignFi, Widar/Widar2.0/Widar3.0, Person-in-WiFi, and the RF-Pose line.

What we add: the surveys tell you *what has been demonstrated in research*; they rarely tell you *which commodity chip you can buy today to reproduce it, and at what firmware cost*. Our sensing-focused docs — [`../docs/ml-csi-sensing.md`](ml-csi-sensing.md) and the deliberately skeptical [`../docs/honest-limitations-of-wifi-sensing.md`](honest-limitations-of-wifi-sensing.md) — translate the literature into "which tier of hardware you actually need, and what will not work." Many headline sensing results depend on a specific NIC (IWL5300, AX210) or on SDR-grade hardware, not on an arbitrary router; the catalog makes that dependency explicit.

---

## Kernel source as the cross-check

A theme running through Cycle 9: the Linux kernel wireless drivers are our most reliable, least-hyped source of ground truth. When a datasheet or forum post claims a capability, we check it against:

- `drivers/net/wireless/…` (ath9k, ath10k/ath11k, iwlwifi, brcmfmac, mt76, rtw88/rtw89, …)
- `iw`/`nl80211` reported feature flags and monitor/injection support
- ath9k's in-tree **spectral scan** (`relayfs` FFT dumps) — the reference implementation behind many tier-3 claims; see [`../docs/walkthroughs/atheros-ath9k-spectral-csi.md`](walkthroughs/atheros-ath9k-spectral-csi.md) and [`../docs/verification-tier3-spectral.md`](verification-tier3-spectral.md).

The upstream driver tree at [git.kernel.org](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless) is a primary source no vendor marketing can override. Grounding tiers in code the maintainers actually merged is a large part of what separates this catalog from a link list.

---

## Where each project wins (quick reference)

| If you want to… | Go to | Not primarily us |
|---|---|---|
| Crack WPA / do monitor+injection attacks | aircrack-ng, Kismet | ✓ |
| Collect CSI from a supported NIC, today | PicoScenes, nexmon_csi, ESP32-CSI-Tool | ✓ |
| Patch Broadcom/Cypress firmware | SEEMOO nexmon | ✓ |
| Run a real SDR flowgraph | GNU Radio + SoapySDR | ✓ |
| Buy a general-purpose SDR | HackRF / USRP / RTL-SDR community | ✓ |
| Read the sensing research frontier | ACM/IEEE CSI surveys, 802.11bf | ✓ |
| **Compare 592 Wi-Fi chips on one honest SDR-capability axis** | **this catalog** | — |
| **Know the firmware-RE reachability per chip, per tier, with verification** | **this catalog** | — |
| **Query a machine-readable chip capability DB** | **this catalog** | — |

We are the connective tissue and the honest scorecard. For everything downstream of "which chip, at what tier," the projects above are the tools you should actually reach for — and this catalog's job is done well if it hands you off to the right one quickly.

---

## References

- RTL-SDR community: <https://www.rtl-sdr.com/> · Osmocom rtl-sdr wiki: <https://osmocom.org/projects/rtl-sdr/wiki>
- aircrack-ng: <https://www.aircrack-ng.org/> · <https://github.com/aircrack-ng/aircrack-ng>
- Kismet: <https://www.kismetwireless.net/> · Linux wireless wiki: <https://wireless.wiki.kernel.org/>
- SEEMOO nexmon: <https://github.com/seemoo-lab/nexmon> · nexmon_csi: <https://github.com/seemoo-lab/nexmon_csi> · InternalBlue: <https://github.com/seemoo-lab/internalblue> · Lab: <https://www.seemoo.tu-darmstadt.de/>
- PicoScenes: <https://github.com/wifisensing> · <https://ps.zpj.io/>
- Linux 802.11n CSI Tool: <https://dhalperi.github.io/linux-80211n-csitool/>
- Atheros CSI Tool: <https://wands.sg/research/wifi/AtherosCSI/>
- ESP32-CSI-Tool: <https://github.com/StevenMHernandez/ESP32-CSI-Tool>
- SoapySDR: <https://github.com/pothosware/SoapySDR/wiki> · GNU Radio: <https://www.gnuradio.org/> · Hamlib: <https://hamlib.github.io/> · Osmocom: <https://osmocom.org/>
- HackRF: <https://greatscottgadgets.com/hackrf/> · USRP UHD: <https://github.com/EttusResearch/uhd> · SDRangel: <https://github.com/f4exb/sdrangel> · Gqrx: <https://gqrx.dk/>
- Ma, Zhou, Wang, *WiFi Sensing with CSI: A Survey*, ACM Computing Surveys 2019: <https://doi.org/10.1145/3310194>
- Yousefi et al., *A Survey on Behavior Recognition Using WiFi CSI*, IEEE Comms Mag 2017: <https://doi.org/10.1109/MCOM.2017.1700082>
- IEEE 802.11 working group (incl. 802.11bf sensing TG): <https://www.ieee802.org/11/>
- Linux kernel wireless drivers: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless>

*In-repo companions:* [Further reading](../docs/further-reading.md) · [Awesome tools](../projects/awesome-tools.md) · [README](../README.md) · [Taxonomy](taxonomy.md) · [Methodology](methodology.md)
