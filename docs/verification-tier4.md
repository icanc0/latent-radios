# Verifying the Tier-4 (arbitrary-waveform TX) claims

> An adversarial audit of every entry the catalog marks **Tier 4 — arbitrary waveform transmit** on a repurposed Wi-Fi chip. Tier 4 is the hard rung of the ladder in [taxonomy.md](taxonomy.md): *software authors a baseband IQ buffer and the chip transmits it through the Wi-Fi RF front-end — not an 802.11 frame, an arbitrary signal.* Claims at this rung are the easiest to overstate, so each one is traced to a **primary source**, checked for **reproducibility with public tooling**, and given a **recommended tier/status**. Corrected `modules[]` records are emitted for the entries that need to change.

## What the catalog currently asserts

At the start of this audit the database held these Tier-4 (or arbitrary-waveform-flagged) Wi-Fi-lineage entries:

| id | tier | status | flags of interest | cited evidence |
|----|------|--------|-------------------|----------------|
| `broadcom-bcm4339` | 4 | reported | `arbitrary-waveform`, `raw-iq` | WiSec 2017 reactive jammer |
| `broadcom-bcm43455c0` | 3 | verified | (none — no arbitrary-waveform) | nexmon / nexmon_csi |

Two non-Wi-Fi Tier-4 entries (`microchip-at86rf215`, a transceiver with a datasheet-documented I/Q radio mode; and true SDRs) are **out of scope** — they do not depend on Wi-Fi firmware reverse-engineering and are independently justified. One Wi-Fi-adjacent entry, `realtek-rtl2832u`, is flagged as an anomaly below.

The headline question: **is `broadcom-bcm4339` at Tier 4 / `reported` justified, or is it resting on a jamming demo that nobody can reproduce?**

## The primary sources

Everything traces to the SEEMOO Lab (TU Darmstadt) / Francesco Gringoli (UniBS) **Nexmon** line of work. The two load-bearing papers and their code:

| Artifact | What it is | Source code? | DOI / URL |
|----------|-----------|--------------|-----------|
| **Shadow Wi-Fi** (MobiSys 2018) — Schulz, Link, Gringoli, Hollick | *"Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi."* The paper that actually demonstrates arbitrary IQ TX. | **Full C source** — [`mobisys2018_nexmon_software_defined_radio`](https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio) | [10.1145/3210240.3210333](https://doi.org/10.1145/3210240.3210333) |
| **Massive Reactive Smartphone-Based Jamming** (WiSec 2017) — Schulz, Gringoli, Steinmetzer, Koch, Hollick | Reactive jammer + adaptive power, built on the same arbitrary-waveform primitive. | **Binary firmware only** — [`wisec2017_nexmon_jammer_demo_app`](https://github.com/seemoo-lab/wisec2017_nexmon_jammer_demo_app) ships blobs, not the patch source; APK withheld. | [10.1145/3098243.3098253](https://doi.org/10.1145/3098243.3098253) |
| **DEMO: Demonstrating Reactive Smartphone-Based Jamming** (WiSec 2017) | Live demo companion to the above. | — | (WiSec '17 demo track) |
| **Nexmon** base framework — Schulz, Wegemer, Hollick | The firmware-patching framework everything is built on. | Open | <https://github.com/seemoo-lab/nexmon> |

The catalog was citing the **weaker** of the two (the binary-only jammer) as the Tier-4 proof. The **reproducible** proof — full source, documented ioctls — is the MobiSys 2018 SDR patch, and it was not referenced at all.

## What was actually demonstrated (claim by claim)

### Claim A — "BCM4339 transmits arbitrary IQ waveforms" → TRUE, and reproducible in source

The `mobisys2018_nexmon_software_defined_radio` patch adds **three ioctls** to the D11 firmware (numbers and semantics straight from the repo README, not invented here):

| ioctl | # | Function |
|-------|---|----------|
| `NEX_WRITE_TEMPLATE_RAM` | 426 | Write a block of I/Q samples into the chip's **Template RAM** (`I` and `Q` are `int16`, interleaved), at a given offset. |
| `NEX_SDR_START_TRANSMISSION` | 427 | Key the TX chain and play `sample_count` samples from an offset, with `chanspec` (channel/BW/band), power index, and loop control. |
| `NEX_SDR_STOP_TRANSMISSION` | 428 | Halt an in-progress transmission. |

This is a genuine Tier-4 primitive: whatever `int16` I/Q you place in Template RAM is what comes out of the antenna, so it is an **arbitrary baseband buffer**, not an 802.11 frame. That is the line between Tier 4 and mere frame injection (Tier 1). The repo's `generate_frame.m` MATLAB script is only an *example* that happens to synthesize a beacon; nothing constrains the buffer to be Wi-Fi.

**Honest limits** (the reader should not expect a HackRF):

- **TX-only.** No time-domain IQ *receive* is provided (see the `raw-iq` correction below).
- **Bandwidth / sample rate** follow the PHY's native rate for the selected `chanspec` (20/40/80 MHz channels); the paper/repo do not publish a turnkey Msps figure, so none is asserted here.
- **Waveform length is bounded by Template-RAM depth** — enough for a short waveform, replayed via the loop flag, not a continuous streamed SDR.
- **Low dynamic range / band-limited** front-end; the TX filter and DAC are Wi-Fi-grade, not instrument-grade.

**Reproducibility:** the source builds, but the demonstrated target is a **rooted Nexus 5 on stock firmware 6.0.1 (M4B30Z, Dec 2016)** — a 2013 end-of-life phone that is now hard to source with exactly that image. That device dependency, not any secrecy in the method, is why the arbitrary-TX rung stays `reported` rather than `verified` for this chip.

### Claim B — the same primitive on the Raspberry Pi (BCM43455c0) → the catalog UNDER-rated this

The single most important finding of this audit: **the identical MobiSys 2018 SDR patch explicitly supports the `bcm43455c0` on a Raspberry Pi 3B+** (the README is emphatic that the plain 3B is *not* supported), with **full public source**. That makes the Raspberry Pi the **most reproducible Tier-4 Wi-Fi target in the entire catalog** — current, cheap, in-production hardware — yet the catalog listed it at **Tier 3** with no arbitrary-waveform flag.

So the evidence that justifies BCM4339's Tier 4 *equally and more strongly* justifies BCM43455c0's. The recommendation is to promote `broadcom-bcm43455c0` **3 → 4**, add `arbitrary-waveform` + `covert-channel`, while keeping its monitor/injection/CSI/spectral rungs at their existing `verified` standing (spelled out in the note). This is the corrected record emitted below.

Reproducibility sketch (RPi 3B+, the practical path):

```bash
# Prereqs: Raspberry Pi 3B+ (bcm43455c0), Raspberry Pi OS, matching nexmon build env
git clone https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio
cd mobisys2018_nexmon_software_defined_radio
# follow the repo's step-by-step: build nexmon base, then the SDR firmware patch
# for the bcm43455c0 target, then load the patched firmware and use nexutil +
# the provided host tools to push int16 I/Q into Template RAM (ioctl 426) and
# key TX (ioctl 427). Confirm on a spectrum analyzer / second SDR that the
# emitted waveform matches the authored buffer.
```

The firmware version string of the shipped `bcm43455c0` blob must match your image exactly (nexmon's usual constraint), the same way [the Pi CSI walkthrough](walkthroughs/bcm43455c0-raspberry-pi.md) requires. Because this rung has not been independently reproduced *at scale* in the wild, its status is `reported`, not `verified`.

### Claim C — "reactive jamming on a smartphone" → real research result, NOT the reproducible route

The WiSec 2017 jammer is a legitimate, peer-reviewed result: it **listens** for a target frame and, *within the same air-time*, keys an **arbitrary jamming waveform** with adaptive power (and can spoof ACKs). But as Tier-4 *evidence for the catalog* it is the wrong thing to cite, because:

- the repo ships **binary firmware only** — the patch source is not published;
- the firmware is **deliberately hobbled** to only jam frames carrying the MAC addresses `NEXMON` / `JAMMER`, to prevent misuse;
- the demo **APK is withheld**;
- the experiment needs **three to four Nexus 5 handsets**.

It therefore supports Tier 4 as an *application* of arbitrary TX, at `reported`, but it is a lab artifact, not a reproducible primitive. The reproducible primitive is Claim A/B. This audit **re-anchors** the BCM4339 record's evidence from the jammer to the Shadow Wi-Fi SDR.

### Claim D — "covert channel over Wi-Fi" → justified as `reported`

The MobiSys 2018 paper's own title carries it: raw TX (Claim A) plus CSI extraction on the receive side is used to build **practical covert channels over Wi-Fi** (SEEMOO's `nexmon.org/covert_channel`). This is a demonstrated capability on the same BCM4339 / BCM43455c0 firmware, so the `covert-channel` flag is warranted at `reported`. It is *not* a separate radio capability — it is arbitrary-TX + CSI applied to hiding information.

### Claim E — "Wi-Fi → non-Wi-Fi cross-technology emission (ZigBee/BLE/LoRa)" → THEORETICAL for these chips

Arbitrary IQ TX means cross-technology emulation is *possible in principle* on these Broadcom parts, and the taxonomy lists CTC as a Tier-4 motivation. But **nexmon does not ship a Wi-Fi→ZigBee/BLE demo**, so no `verified`/`reported` cross-tech emission should be attributed to Broadcom here — it is `theoretical`. The canonical cross-technology result, **WEBee** (Li & He, MobiCom 2017, [10.1145/3117811.3117816](https://doi.org/10.1145/3117811.3117816)), is a *different* technique: it shapes ordinary 802.11 **payload bytes** so the OFDM output approximates a ZigBee frame — commodity-hardware injection cleverness, **not** raw-IQ Template-RAM TX and not a firmware-reversing result. It is cited here only to keep the two techniques from being conflated.

## Anomaly flagged (not corrected here): `realtek-rtl2832u` at Tier 4

`realtek-rtl2832u` is scored **Tier 4** with flags `[raw-iq, monitor, spectral-scan]` — **none of which is `arbitrary-waveform`, and the RTL2832U cannot transmit at all.** By the taxonomy's own definition Tier 4 *is* arbitrary-waveform TX, so an RX-only dongle sitting at Tier 4 is internally inconsistent. The likely intent was "this is a real-SDR-class *receiver*," which the TX-oriented ladder has no clean rung for (full time-domain raw-IQ RX is richer than Tier-3 spectral bins but is not TX). This is a **taxonomy decision for the maintainers**, not a data fix this audit should make unilaterally, so no corrected record is emitted for it — but it is logged here so the Tier-4 set is honest. Recommendation: either add an explicit note to that record ("Tier 4 denotes real-SDR-class raw-IQ *receive*, not TX"), or introduce an RX-side rung.

## Verdict table

| Claim | Chip / firmware | Primary evidence | Reproducible with public tooling? | Recommended tier / status |
|-------|-----------------|------------------|-----------------------------------|---------------------------|
| Arbitrary IQ waveform TX | **BCM4339** / Nexus 5, fw 6.0.1 M4B30Z | Shadow Wi-Fi, MobiSys 2018 — **full source** (ioctls 426/427/428, int16 I/Q → Template RAM) | Buildable in source; blocked mainly by EoL Nexus-5 availability | **Tier 4 / reported** — justified; re-anchor evidence to the SDR patch |
| Arbitrary IQ waveform TX | **BCM43455c0** / RPi 3B+ | Same MobiSys 2018 SDR patch, explicitly supports RPi 3B+ | **Yes — current, cheap hardware; strongest case** | **Tier 3 → 4 / reported** — promote; add `arbitrary-waveform`, `covert-channel` |
| Reactive jamming (listen-and-jam) | BCM4339 / Nexus 5 | Massive Reactive Jamming, WiSec 2017 | **No** — binary-only firmware, hobbled to NEXMON/JAMMER MACs, APK withheld, needs 3–4 phones | Supports Tier 4 as `reported` *application*; not the primitive to cite |
| Covert channel over Wi-Fi | BCM4339 / BCM43455c0 | Shadow Wi-Fi title + `nexmon.org/covert_channel` | Partially (built on the SDR primitive) | Flag `covert-channel` / **reported** |
| Wi-Fi → ZigBee/BLE cross-tech emission | Broadcom D11 | none in nexmon; WEBee is a different technique | No (not shipped for these chips) | **theoretical** — do **not** flag on Broadcom |
| "Tier 4" on an RX-only dongle | RTL2832U | RTL-SDR (RX only) | N/A — cannot TX | **Anomaly** — flagged for maintainers, not corrected here |
| `raw-iq` flag on BCM4339 | BCM4339 | — | Nexmon exposes **frequency-domain CSI**, not time-domain IQ RX | **Remove** `raw-iq` from BCM4339 |

## Bottom line

- **Tier 4 for the Broadcom/Nexmon parts is justified** — but for the right reason. The reproducible proof is the **MobiSys 2018 Shadow Wi-Fi "nexmon SDR"** patch (arbitrary `int16` I/Q → Template RAM via ioctls 426/427/428), **not** the binary-only WiSec 2017 jammer the catalog was citing.
- **The catalog under-rated the Raspberry Pi.** `broadcom-bcm43455c0` should be **Tier 4**, and it is the *most* reproducible Tier-4 Wi-Fi target — cheap, current hardware, full source.
- **Two overclaims trimmed:** `raw-iq` removed from BCM4339 (no time-domain IQ RX in nexmon); cross-technology emission stays `theoretical` for Broadcom.
- **Status stays `reported`** for the arbitrary-TX rung on both chips (research patch, device/version-pinned, not a turnkey `nexutil` feature), consistent with the [taxonomy](taxonomy.md) convention that `status` tracks the tier-defining capability while the lower rungs remain independently `verified`.

## Safety and regulatory note (read before any TX)

Everything above **transmits**. Writing arbitrary I/Q into a Wi-Fi front-end and keying it emits energy that will *not* be a compliant 802.11 signal — it can occupy spectrum outside normal Wi-Fi masks, exceed duty-cycle/power rules, and interfere with licensed and unlicensed users. **Reactive jamming is illegal to operate against networks you do not own** in essentially every jurisdiction (e.g. it violates the U.S. Communications Act; jammer operation and marketing are prohibited by the FCC, and equivalent bans exist under CEPT/ETSI regimes). Reproduce arbitrary-waveform TX or jamming **only** inside a shielded enclosure / RF anechoic chamber or on a wired, attenuated, terminated bench setup, on frequencies and at powers you are licensed to use. The SEEMOO authors themselves hobbled the public jammer firmware for exactly this reason. Nothing here is authorization to transmit on the air.

## See also

- [taxonomy.md](taxonomy.md) — the tier ladder these verdicts are scored against (Tier 4 definition).
- [../projects/nexmon.md](../projects/nexmon.md) — the firmware-patching framework underlying every claim here.
- [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) — the BCM4339 / BCM43455c0 vendor overview.
- [walkthroughs/bcm43455c0-raspberry-pi.md](walkthroughs/bcm43455c0-raspberry-pi.md) — Pi nexmon setup (the firmware-version-matching discipline that the SDR patch also requires).
- [true-sdr-comparison.md](true-sdr-comparison.md) — why even a working Tier-4 Wi-Fi chip is not a HackRF (bandwidth, dynamic range, buffer depth).

## References

1. Schulz, Link, Gringoli, Hollick — *Shadow Wi-Fi: Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi*, ACM MobiSys 2018. DOI: <https://doi.org/10.1145/3210240.3210333>
2. `mobisys2018_nexmon_software_defined_radio` (the reproducible arbitrary-TX patch, full source, ioctls 426/427/428): <https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio>
3. Schulz, Gringoli, Steinmetzer, Koch, Hollick — *Massive Reactive Smartphone-Based Jamming using Arbitrary Waveforms and Adaptive Power Control*, ACM WiSec 2017. DOI: <https://doi.org/10.1145/3098243.3098253>
4. `wisec2017_nexmon_jammer_demo_app` (binary-only jammer firmware, hobbled to NEXMON/JAMMER MACs): <https://github.com/seemoo-lab/wisec2017_nexmon_jammer_demo_app>
5. Nexmon framework: <https://github.com/seemoo-lab/nexmon> · project pages `nexmon.org/sdr`, `nexmon.org/jammer`, `nexmon.org/covert_channel`
6. Schulz, Wegemer, Hollick — *The Nexmon Firmware Analysis and Modification Framework*, Computer Communications, 2018.
7. `nexmon_csi` (receive-side CSI used for the covert channel) — Gringoli, Schulz, Link, Hollick, WiNTECH 2019. Repo: <https://github.com/seemoo-lab/nexmon_csi> · DOI: <https://doi.org/10.1145/3349623.3355477>
8. Li, He — *WEBee: Physical-Layer Cross-Technology Communication via Emulation*, ACM MobiCom 2017 (distinct payload-shaping technique, cited for contrast). DOI: <https://doi.org/10.1145/3117811.3117816>
