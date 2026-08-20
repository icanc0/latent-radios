# Changelog — how this catalog grew

*This is the reader-facing history of* Latent Radios: *one paragraph per research cycle, with the module-count milestone each one left behind. It is the narrative companion to the mechanics in [../docs/methodology.md](../docs/methodology.md) and the forward-looking [../docs/roadmap.md](../docs/roadmap.md). Where those two explain* how *the pipeline works and* what's next, *this page records* what actually happened, *cycle by cycle, so you can see the shape of the catalog's growth and judge how mature any slice of it is.*

## Why keep a changelog at all

The catalog is assembled by an automated multi-agent pipeline that runs in discrete **research cycles** (the full provenance model is in [../docs/methodology.md](../docs/methodology.md)). Each cycle fans out ~14 independent investigator agents, one per vendor family or topic; each returns a prose document plus structured `data/modules.json` records with citations, and a deterministic ingest step merges them. Because growth is bursty and uneven — some cycles add hundreds of parts, others deepen or *correct* what's already there — a flat "599 entries" number hides more than it tells. This log restores the shape: which families landed when, when the RE walkthroughs were written, and when the adversarial verification passes began pruning over-claims back down. Read a cycle's paragraph to know how settled its subject matter is.

## The growth curve at a glance

Module counts are cumulative in `data/modules.json` at the close of each cycle. The catalog now stands at **599 modules across 107 vendors**.

| Cycle | Theme | Δ modules | Cumulative | Files |
|------:|-------|----------:|-----------:|------:|
| 0 | Scaffold: taxonomy, schema, methodology, tooling | — | 0 | seed |
| 1 | Core vendor families + first docs/projects | +116 | **116** | 14 |
| 2 | Firmware-RE walkthroughs + adjacent-PHY seeds | +28 | 144 | 14 |
| 3 | Exhaustive per-vendor part sweeps | +217 | **361** | 14 |
| 4 | Adjacent PHYs (BLE/154, LoRa, router SoCs, radar) | +72 | **433** | 14 |
| 5 | Firmware-RE deep dives + RISC-V + CSI-ML | +33 | **466** | 14 |
| 6 | Cellular baseband & GNSS repurposing | +39 | **505** | 16 |
| 7 | Open-firmware classics + stack integration | +14 | **519** | 13 |
| 8 | Module integrators / SoC-integrated / IoT | +73 | **592** | 14 |
| 9 | Consolidation & verification | +7 | **599** | 13 |

The milestone markers the project tracks — **0 → 116 → 361 → 433 → 466 → 505 → 519 → 592 → 599** — are the cumulative totals at the cycles that moved the needle (Cycle 2's intermediate 144 is shown above for completeness). Note the two shapes of a cycle: the big **+217 / +116 / +73** breadth cycles that catalog new silicon, versus the **+7 / +14** cycles whose real work is depth, cross-checking, and *removing* inflated claims rather than adding rows.

## Cycle 0 — scaffold *(seed, 0 modules)*

The foundation, no data yet. This cycle defined the thing the rest would fill: the **SDR ladder** (tiers 0–5, from black-box to open PHY), the orthogonal **capability** flags (monitor, injection, csi, spectral-scan, raw-iq, arbitrary-waveform, radar, fmcw, passive-radar, covert-channel, open-firmware), the **`status`** vocabulary (verified / reported / theoretical), and the JSON Schema every record must satisfy. It also seeded the firmware-reverse-engineering methodology and the tooling conventions (validator, CSV build). Everything downstream is scored against rubrics frozen here — see [../docs/methodology.md](../docs/methodology.md) and `docs/taxonomy.md`.

## Cycle 1 — core vendor families *(116 modules)*

The first real data drop, and the largest single jump the catalog would ever take relative to its base: from nothing to **116 modules**. Investigators profiled the pillars of the Wi-Fi silicon world — Broadcom/Cypress, Qualcomm Atheros, Intel, Realtek, MediaTek/Ralink, Espressif — plus a long tail of smaller vendors. Alongside the chip files came the first supporting docs and project write-ups: Nexmon, the CSI toolchains, the firmware-RE primer, the core techniques, the true-SDR yardstick used for the Tier-5 comparison, the glossary, and the RTL-SDR lineage. After this cycle the catalog's *skeleton* was complete: every major family had at least a stub, and the scoring rubric had been exercised against real parts.

## Cycle 2 — firmware-RE walkthroughs *(144 modules)*

A depth cycle more than a breadth one (**+28**, to 144). Its lasting contribution is the set of reproducible reverse-engineering walkthroughs — Ghidra on the Broadcom D11 microcode, ESP32, ath9k, and the Intel 5300 — that turn the catalog from a list into a *how-to*. It also stood up PicoScenes and openwifi as first-class projects, added the Wi-Fi 7 / 6 GHz, 60 GHz, and HaLow (802.11ah) frontier docs, built the hardware index, and — importantly — ran the first **Tier-4 audit**, the earliest adversarial pass on the strongest (raw-IQ-TX) claims. The pattern of "add parts, then immediately try to refute the boldest ones" starts here.

## Cycle 3 — exhaustive part sweeps *(361 modules)*

The breadth explosion: **+217 modules**, more than doubling the catalog to **361**. Where Cycle 1 planted one representative per family, Cycle 3 went part-number by part-number through Intel, Realtek, Atheros, Broadcom, MediaTek, and the long tail, cataloging concrete SKUs rather than families. New walkthroughs (RTL8812AU, mt76, nRF52, openwifi) and new technique docs (UWB, cross-technology communication, FTM) landed alongside, plus the **Tier-2 CSI audit** that began separating "CSI was demoed once" from "CSI reproduces on a maintained toolchain." This is the cycle that made the catalog *comprehensive* at the SKU level.

## Cycle 4 — adjacent PHYs *(433 modules)*

The scope widened past Wi-Fi (**+72**, to 433). Investigators brought in BLE / 802.15.4, LoRa / sub-GHz, router SoCs, and radar/UWB parts — wireless modules that repurpose to bare radios even though they aren't 802.11. Projects gr-ieee802-11, open-AR9271, nexmon-CSI, and Flipper Zero got write-ups; the technique library gained passive radar, 802.11az ranging, RF-safety-and-legal guidance, and GNU Radio OOT modules; and the **Tier-3 (spectral scan) audit** ran. This cycle is why the catalog's answer to "can this non-Wi-Fi chip act as an SDR?" is often *yes, to some tier* — the scope is "wireless modules usable as an SDR to some extent," not "Wi-Fi only."

## Cycle 5 — firmware-RE deep dives *(466 modules)*

A depth cycle (**+33**, to 466) centered on the hard, chip-specific RE that the ladder's upper rungs demand: BCM4339 (Shadow-Wi-Fi), ESP32 raw TX, mt76, and BL602. It added RISC-V / open-Wi-Fi coverage, the 802.11bf WLAN-sensing standard doc, and a CSI-ML + human-activity-recognition pipeline, plus driver/library indexes and the **which-chip decision guide** that helps a reader pick hardware by goal. Its verification contribution was the **Tier-1 injection audit** — the ground-truth pass on which chips actually inject in practice, not just in theory.

## Cycle 6 — cellular & GNSS repurposing *(505 modules)*

The catalog reached past the ISM bands entirely (**+39**, to 505). Cellular basebands (via diagnostic/debug interfaces) and GNSS receivers repurposed as SDRs joined the database, alongside productized and defensive sensing coverage. This cycle also ran the **Tier-5 open-firmware audit** (which "open firmware" is genuinely open and maintained), added regulatory and RF-front-end reference material, wrote the definitive [../docs/methodology.md](../docs/methodology.md) provenance page, and built the capability index. At 16 files it was the widest cycle by document count.

## Cycle 7 — open-firmware classics & stack integration *(519 modules)*

A consolidation-leaning cycle (**+14**, to 519). It documented the open-firmware classics that predate the modern scene — OpenFWWF, carl9170, AX-CSI — and connected the catalog to the systems that actually run these radios: the Linux and Android wireless stacks. It also added an 802.11 standards reference, a project history, comparison tables, an FAQ, and the first datasheet spot-check audit that cross-checks catalog claims against manufacturer documents.

## Cycle 8 — integrators, SoCs & IoT *(592 modules)*

The last big breadth push (**+73**, to 592). It cataloged the module **integrators** — Murata, AMPAK, AzureWave, Laird — who wrap silicon into shippable modules, plus SoC-integrated and IoT/M2M Wi-Fi parts, and the retro lineage (Prism2/HostAP, rt2x00) that seeded open Wi-Fi firmware in the first place. New sensing docs (gesture/occupancy CSI, honest sensing limits), a second datasheet audit, an awesome-tools index, and a troubleshooting guide rounded it out. After this cycle the *module* layer — not just the chip layer — was covered.

## Cycle 9 — consolidation & verification *(599 modules)*

A deliberate settling cycle (**+7**, to **599**). The additions were minor; the point was to unify and check. It produced a single unified **verification summary** over all five tier audits, a **kernel-source cross-check** that grounds driver claims in real code, a Nexus 5 reference build, a CSI-calibration deep-dive, a testbed and reproducibility checklist, a sensing-application catalog, a research-ethics-and-responsible-disclosure doc, and a seventh part sweep. This is the cycle that turned "we have lots of entries" into "we can defend the entries we have."

## How to read a milestone

The count is a floor, not a grade. A part added in a **breadth** cycle (3, 4, 8) may still carry `status: reported` until a later verification pass reaches it; a part touched in a **depth/consolidation** cycle (5, 6, 9) has usually been traced to a primary source and may have been *downgraded* in the process. When an entry's tier matters to you, ignore which cycle added it and read its `status` and `references[]` directly — that discipline is the whole argument of [../docs/methodology.md](../docs/methodology.md). For where the project is heading next, the live cycle log and vendor queue live in [../docs/roadmap.md](../docs/roadmap.md).

## References

- [../docs/methodology.md](../docs/methodology.md) — how the catalog is built, scored, and adversarially checked (the mechanics this page narrates).
- [../docs/roadmap.md](../docs/roadmap.md) — the canonical cycle log and forward-looking vendor/technique queue; the module-count deltas in the table above are drawn from it.
- `docs/taxonomy.md` — the SDR ladder and capability/status vocabularies frozen in Cycle 0.
- `docs/history-timeline.md` — the *external* timeline of Wi-Fi-as-SDR research (papers, tools, silicon), distinct from this internal build history.
- `docs/verification-summary.md` — the Cycle-9 roll-up of the five per-tier audits.
- `data/modules.json` — the canonical database whose row count this changelog tracks.
