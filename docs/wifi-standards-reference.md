# 802.11 amendments quick reference (the ones that matter here)

A cheat-sheet of the IEEE 802.11 amendments that recur throughout this catalog —
the PHYs whose pilot/training structure your firmware exposes, the bands your chip
tunes, and the amendments that quietly turned commodity Wi-Fi silicon into a
*sensing* instrument. This is a map, not the territory: the amendment tells you
what a frame *can* carry (an HT-LTF field, an FTM timestamp, a sensing NDP); the
[techniques](techniques.md) and [taxonomy](taxonomy.md) docs tell you how far a
given chip's firmware actually lets you reach up [the SDR ladder](taxonomy.md),
and the [glossary](glossary.md) defines the acronyms (CSI, LTF, NDP, OFDMA, PMF,
FTM) used below.

> **Why an amendment matters for SDR/sensing.** Three things: (1) which **band**
> and **bandwidth** the PHY occupies — that bounds your usable IQ span and range
> resolution; (2) what **training/pilot structure** the frame carries — long
> training fields (LTFs) are what CSI extraction reads, and wider bandwidth =
> more subcarriers = finer channel taps; (3) whether the amendment adds an
> explicit **measurement or sensing primitive** (radio measurement, FTM, secure
> ranging, sensing NDP) that a cooperative or monitor-mode receiver can harvest.
> Higher-order QAM and OFDMA matter less for sensing and more for *injection*
> fidelity — see [techniques](techniques.md).

Publication years below are the amendment's IEEE ratification (rolled into the
base standard at the next revision). Where a standard is still in Task-Group
draft in 2026 it is flagged; treat those rows as **reported/emerging**, not
shipped.

---

## Mainline PHYs (the ones every catalog chip speaks)

| Amend. | Wi-Fi gen | Year | Band(s) | Channel BW | PHY / key adds | Why it matters here |
|---|---|---|---|---|---|---|
| **(legacy)** 802.11-1997 | — | 1997 | 2.4 GHz | ~22 MHz | DSSS / FHSS, 1–2 Mbps | Historical baseline; DSSS still the fallback preamble. |
| **a** | — | 1999 | 5 GHz | 20 MHz | OFDM, 64-FFT, 52 subcarriers, ≤54 Mbps | First OFDM PHY — the template for 11p/11ah down-clocking. |
| **b** | — | 1999 | 2.4 GHz | ~22 MHz | HR-DSSS / CCK, ≤11 Mbps | Non-OFDM; long/short preambles you still see in monitor captures. |
| **g** | — | 2003 | 2.4 GHz | 20 MHz | OFDM (11a in 2.4 GHz), ≤54 Mbps | ERP; the "legacy OFDM" reference for spectral tools. |
| **n** | Wi‑Fi 4 | 2009 | 2.4 + 5 GHz | 20 / 40 MHz | HT, MIMO (≤4 SS), **HT-LTF**, 64-QAM | **The CSI workhorse.** HT-LTFs are what ath9k / Intel 5300 / nexmon CSI read; MIMO gives multiple spatial streams to correlate. See [csi walkthroughs](techniques.md). |
| **ac** | Wi‑Fi 5 | 2013 | 5 GHz | 20/40/80/160 (80+80) MHz | VHT, DL MU-MIMO, 256-QAM, **VHT-LTF** | Wider BW = finer delay resolution; 80/160 MHz CSI (nexmon on BCM43xx) is the high-res sweet spot for passive sensing. |
| **ax** | Wi‑Fi 6 / 6E | 2019 / 2021 (6E) | 2.4 + 5 (+ **6 GHz**) | 20/40/80/160 MHz | HE, **OFDMA**, UL/DL MU-MIMO, 1024-QAM, **HE-LTF**, TWT | 6 GHz opens clean spectrum; OFDMA resource units complicate CSI parsing but add per-RU channel info. HE-LTF longer-symbol modes aid ranging. |
| **be** | Wi‑Fi 7 | ratified 2024/25 (Wi‑Fi 7 cert. Jan 2024) | 2.4 + 5 + 6 GHz | up to **320 MHz** | EHT, 4096-QAM, **Multi-Link Operation (MLO)**, **EHT-LTF** | 320 MHz is the widest contiguous commodity Wi‑Fi channel → best native range/Doppler resolution for sensing; MLO gives simultaneous multi-band channel views. Silicon support still maturing. |

**Reading the PHY column for SDR work:** each generation adds a longer/richer
**LTF** (HT-LTF → VHT-LTF → HE-LTF → EHT-LTF). CSI extraction is fundamentally
"dump the per-subcarrier channel estimate the receiver already computed from the
LTF." Wider channel + more subcarriers + more spatial streams = a richer channel
tensor. That is the whole reason Wi‑Fi sensing rides these amendments — see
[taxonomy](taxonomy.md) tier 2 (CSI) and tier 3 (spectral).

---

## Sub-GHz — long-range / narrowband

| Amend. | Name | Year | Band | Channel BW | Adds | Why it matters here |
|---|---|---|---|---|---|---|
| **ah** | Wi‑Fi **HaLow** | 2016 | sub-1 GHz (863–928 MHz, regional) | **1 / 2 / 4 / 8 / 16 MHz** | Down-clocked 11ac OFDM (10× slower clock → 1 MHz min channel), long range, low power IoT | Narrow channels + sub-GHz propagation = through-wall sensing candidate and an unusual, cheap sub-GHz OFDM front end. The 1/2 MHz modes are the narrowest OFDM in the family. See [techniques](techniques.md) on down-clocked PHYs. |

---

## 60 GHz — mmWave (DMG / EDMG)

| Amend. | Name | Year | Band | Channel BW | Adds | Why it matters here |
|---|---|---|---|---|---|---|
| **ad** | **WiGig** (DMG) | 2012 | 60 GHz | **2.16 GHz** | Single-carrier + OFDM, beamforming/beam training, ≤~7 Gbps | The huge instantaneous bandwidth = **cm-scale range resolution**. 802.11ad radios (e.g. TP-Link Talon AD7200 / QCA9500) are the classic "commodity 60 GHz radar / FMCW / gesture-sensing" hack platform. Tier 3–4 territory when firmware allows raw beam/CSI dumps. |
| **ay** | EDMG | 2021 | 60 GHz | up to **8.64 GHz** (4× 2.16 channel bonding) | MIMO + channel bonding at 60 GHz, ≥100 Gbps | Even wider aperture → finer radar/imaging resolution; still exotic in accessible silicon (2026). Reported, rarely reproduced. |

> mmWave note: 802.11ad/ay are the amendments people mean when they say "use a
> Wi-Fi chip as a radar." The 2.16 GHz channel is a ready-made FMCW-adjacent
> aperture; see the radar/fmcw/passive-radar entries in [taxonomy](taxonomy.md).

---

## Vehicular

| Amend. | Name | Year | Band | Channel BW | Adds | Why it matters here |
|---|---|---|---|---|---|---|
| **p** | WAVE / DSRC | 2010 | 5.9 GHz (ITS) | **10 MHz** (half-clocked 11a) | OMA outside-BSS, low-latency V2X | A licensed-band, half-clocked OFDM variant — relevant when a chip/driver exposes the 10 MHz mode (unusual bandwidth for monitor/injection experiments). Later contested by C-V2X. |

---

## Roaming / measurement (the "k/v/r" trio — one of them is sensing-adjacent)

| Amend. | Name | Year | Adds | Why it matters here |
|---|---|---|---|---|
| **k** | Radio Resource Measurement (RRM) | 2008 | Neighbor reports, **beacon report, channel-load, noise histogram, STA statistics, frame/measurement requests** | **Sensing-adjacent.** 11k standardizes *asking a station to measure and report the RF environment* — noise histograms and channel load are coarse spectrum sensing you can get without touching firmware. A soft on-ramp before tier-3 spectral. |
| **v** | Wireless Network Management (WNM) | 2011 | BSS Transition Mgmt, TIM broadcast, sleep/timing services, directed roaming | Steering/roaming plumbing; occasionally abused for tracking/management-frame games. Little direct SDR value. |
| **r** | Fast BSS Transition (FT) | 2008 | Pre-authentication key caching for sub-50 ms roams | Roaming only; listed for completeness — no sensing role. |

---

## Security (defensive — matters because it *blocks* an attack primitive)

| Amend. | Name | Year | Adds | Why it matters here |
|---|---|---|---|---|
| **w** | Protected Management Frames (PMF) | 2009 | Cryptographic protection of **deauth / disassoc / action** management frames | **Defensive.** PMF is what defeats classic deauth/disassoc *injection* — the tier-1 "monitor+injection" party trick. If a network mandates PMF (802.11ax makes it mandatory in many modes), your injection-based deauth won't stick. Relevant to the ethics/limits discussion; see [techniques](techniques.md). |

---

## Positioning / timing / sensing (the amendments this whole catalog orbits)

| Amend. | Name | Year | Band | Adds | Why it matters here |
|---|---|---|---|---|
| **mc** (REVmc → 802.11-2016) | Fine Timing Measurement (FTM) | 2016 | all Wi-Fi bands | **FTM**: two-way time-of-flight ranging via timestamped action-frame exchange | The first *standardized* ranging primitive in Wi‑Fi. FTM turns any compliant pair of radios into a ToF rangefinder — accuracy bounded by channel bandwidth (wider = better). Firmware/driver exposure of FTM timestamps is a tier-2/3 capability. |
| **az** | Next Generation Positioning (NGP) | 2022/23 | sub-7 GHz + 60 GHz | **Secure LTF (RSTA/ISTA)**, phase-based & enhanced ToF ranging, reduced overhead, multi-user ranging | The "serious" positioning amendment: sub-meter, secured against spoofing, scalable to many clients. Rides HE/EHT LTFs. Where FTM is a rangefinder, 11az is an infrastructure positioning system — high sensing relevance, limited open firmware exposure so far. |
| **bf** | **WLAN Sensing** | TG draft, ~2025+ (emerging) | sub-7 GHz + DMG 60 GHz | Standardized **sensing measurement**: sensing NDP announcements, CSI feedback formats, sounding schedules — for motion/presence/gesture/vital-sign sensing | **The amendment that makes CSI sensing first-class.** 802.11bf takes what nexmon/ath9k/5300 hacks did informally (harvest CSI, infer motion) and standardizes the sounding + feedback. Watch this space: once silicon ships 11bf, several tier-2 CSI hacks become supported features. Status: **reported/emerging** — verify against the current 802.11bf draft before citing specifics. |

---

## How to use this table with the rest of the repo

1. **Identify the PHY your chip speaks** (n/ac/ax/be for the CSI-rich mainline; ad/ay for mmWave radar; ah for sub-GHz narrowband). That sets your ceiling on bandwidth → resolution.
2. **Check the LTF** — CSI extraction reads the training fields; more/longer LTFs and wider BW = richer channel data. Cross-reference [taxonomy](taxonomy.md) tiers 2–5.
3. **Check for a measurement/sensing primitive** — 11k (coarse), FTM/11mc (ranging), 11az (secure ranging), 11bf (sensing). These are the *standardized* on-ramps that don't always require deep firmware RE.
4. **Mind PMF (11w)** if your technique relies on management-frame injection.
5. Map acronyms in [glossary](glossary.md); map techniques to firmware reality in [techniques](techniques.md).

### Band / bandwidth quick index

| Band | Amendments | Max channel BW seen |
|---|---|---|
| sub-1 GHz | ah (+ p at 5.9 GHz ITS) | 16 MHz (ah); 10 MHz (p) |
| 2.4 GHz | b, g, n, ax, be | 40 MHz |
| 5 GHz | a, n, ac, ax, be | 160 MHz |
| 6 GHz | ax (6E), be | 320 MHz (be) |
| 60 GHz | ad, ay | 2.16 GHz (ad) / 8.64 GHz (ay) |

*(Bandwidths are per-PHY maxima; regulatory domain and specific silicon may restrict them. UWB positioning, though "sensing-adjacent," lives in IEEE 802.15.4z, not 802.11, and is out of scope here.)*

---

### References

- IEEE 802.11-2020 base standard (rolls up a/b/g/n/ac and REVmc/FTM): <https://standards.ieee.org/ieee/802.11/7028/>
- IEEE 802.11ax-2021 (Wi-Fi 6/6E, HE, OFDMA): <https://standards.ieee.org/ieee/802.11ax/7180/>
- IEEE 802.11be Task Group (Wi-Fi 7, EHT): <https://www.ieee802.org/11/Reports/tgbe_update.htm>
- IEEE 802.11ah-2016 (HaLow, sub-1 GHz): <https://standards.ieee.org/ieee/802.11ah/5514/>
- IEEE 802.11ad-2012 (DMG, 60 GHz): <https://standards.ieee.org/ieee/802.11ad/4527/>
- IEEE 802.11ay-2021 (EDMG, 60 GHz): <https://standards.ieee.org/ieee/802.11ay/7311/>
- IEEE 802.11az-2022 (Next Gen Positioning): <https://www.ieee802.org/11/Reports/tgaz_update.htm>
- IEEE 802.11bf Task Group (WLAN Sensing): <https://www.ieee802.org/11/Reports/tgbf_update.htm>
- IEEE 802.11p / WAVE overview: <https://standards.ieee.org/ieee/802.11p/3953/>
- Wi-Fi Alliance generation naming (Wi-Fi 4/5/6/7): <https://www.wi-fi.org/discover-wi-fi>
- Related in this repo: [taxonomy.md](taxonomy.md) · [techniques.md](techniques.md) · [glossary.md](glossary.md)
