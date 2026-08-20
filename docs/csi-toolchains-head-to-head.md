# CSI Toolchains Head-to-Head — the opinionated comparison

The [toolchain survey](../projects/csi-toolchains.md) catalogs *what exists*; the [Tier-2 verification audit](../docs/verification-tier2-csi.md) asks *what still reproduces in 2025*. This file is the third leg: **which one should you actually pick, and why.** It compares the six CSI toolchains a newcomer will realistically weigh — the **Linux 802.11n CSI Tool (Intel 5300)**, the **Atheros CSI Tool (ath9k)**, **nexmon_csi (Broadcom)**, **ESP32-CSI**, **AX-CSI / FeitCSI (Intel AX2xx)**, and **PicoScenes** — on the axes that change your day-to-day, not just the spec sheet.

> **Scope discipline.** This is a *decision* document, not new evidence. Every reproducibility claim here follows the verification audit; where the audit says "legacy kernel," so does this file. Nothing below promotes a tool above what the audit verified.

---

## The axes that actually matter

Spec tables lead with bandwidth and subcarrier count. Those matter, but they are rarely what sinks a project. What sinks projects is: the tool won't build on your kernel; the phase is garbage until you write a sanitizer; the capture rate is a tenth of what you assumed; or the "cheap" hardware is EOL and you're bidding on used cards. So the comparison is built on eight axes:

1. **Bandwidth / subcarriers** — frequency resolution (delay/range resolution).
2. **Achievable CSI rate** — packets-per-second of CSI, which sets your Doppler/temporal bandwidth. **This is packet-arrival-limited, not an ADC sample rate** — you get one CSI snapshot per received frame, so the real ceiling is *how fast you can make frames arrive and be logged*.
3. **Phase quality / calibration burden** — raw CSI phase is never usable as-is; the question is *how much* work.
4. **Ease of setup (1–5)** — 1 = boot a museum kernel or build a whole old tree; 5 = clone-and-go.
5. **Hardware cost & availability** — and whether it is still *buyable new*.
6. **Kernel / firmware fragility** — the single biggest predictor of whether you'll reproduce a result next year.
7. **Output format & tooling** — and whether [CSIKit](https://github.com/Gi-z/CSIKit) already parses it.
8. **Best-use recommendation** — the one sentence you came for.

### A word on "sampling rate" before the numbers

CSI is **not** streamed at a fixed rate the way a true SDR streams IQ. Each received/injected OFDM frame yields **one** CSI matrix. So your effective sample rate is set by traffic: a ping-flood or an injected frame train drives it, and the practical ceiling is imposed by whatever is slowest — the NIC's report path, the host CPU, or the transport (netlink, UDP, or a UART). The figures below are **order-of-magnitude engineering guidance** (what people routinely sustain), not measured maxima, and every one of them assumes *you* generate the traffic. Treat them as "plan around this," not "guaranteed."

---

## Head-to-head table

| Axis | **Intel 5300** (Halperin) | **Atheros** (ath9k, Xie) | **nexmon_csi** (Broadcom) | **ESP32-CSI** | **AX-CSI / FeitCSI** (Intel AX2xx) | **PicoScenes** (platform) |
|---|---|---|---|---|---|---|
| **Std / BW** | 11n, 20/40 MHz | 11n, 20/40 MHz | 11a/g/n/ac, ≤80 MHz | 11n (C6: 11ax), 20/40 MHz | 11a…**ax**, ≤160 MHz, **6 GHz** (AX210) | 11a…ax, ≤160 MHz, **6 GHz** (AX210) |
| **Subcarriers / streams** | **30 grouped**, int8, ≤3×3 | **56 @20 / 114 @40**, full-precision, ≤3×3 | per-SC, int16, **≤4×4** (RT-AC86U) | ≤**52/64**, int8 pairs, **1×1** | up to **1992/pkt**, multi-antenna | full per-SC, all formats, **≤27 NICs** concurrent |
| **Achievable CSI rate** (packet-limited) | ~1 kHz typical (ping-flood; netlink); papers commonly ≤2 kHz | ~1–few kHz (injection-driven) | Pi-CPU/UDP bound — commonly hundreds Hz to ~1–2 kHz; **drops at high rate** | **Serial-bound: ~100 Hz** typical over UART; higher via UDP | high (injection-controlled); 160 MHz frames are large, so throughput-limited | high, injection-controlled; best rate control of the six |
| **Phase quality / calibration** | Grouped + int8 → coarse; CFO/SFO/STO **and** inter-RX-chain offsets → **sanitization mandatory** | **Cleanest raw** of the 11n three (uncompressed, full precision); still needs CFO/SFO/STO removal | per-SC but **null/pilot gaps + AGC amplitude scaling + per-core phase offset** → calibration mandatory; varies by chip | 1×1 (no cross-antenna phase to fix) but CFO/SFO present; unwrap needed; **C6 11ax LTF-ordering quirk** | rich; multi-antenna phase needs sanitization; FeitCSI exposes clean plumbing | best metadata for calibration; still physics-limited (needs sanitization) |
| **Ease of setup (1–5)** | **1** — archived tool, ≤kernel 4.x, EOL card | **1–2** native (ships a whole ~4.1.10 kernel tree to boot); **4** via PicoScenes | **3** — maintained `Makefile.rpi`, but firmware pinning + Bookworm/64-bit friction | **5** — `idf.py build flash`; no host kernel at all | **4** (FeitCSI: source+binary+**live USB**); bare AX-CSI **2** | **4** — apt/`.deb` on Ubuntu 22.04→24.04 |
| **Hardware cost / availability** | Used mini-PCIe ~$10–30, **EOL**; needs a laptop with the slot | AR95xx/QCA9558 ~$10–25, **abundant** | Pi 4 ~$35–55; RT-AC86U ~$150 for 4×4 — **current** | **~$3–8 dev board — cheapest on earth** | AX200/AX210 M.2 ~$15–25 — **in production** | cost of chosen NIC(s); USRP path is $$$; SW free-academic |
| **Kernel/firmware fragility** | **Extreme** — repo archived 2020, un-buildable on 6.x | **High native** (kernel fork); spectral rung is mainline & fine | **Medium** — pinned µcode `7_45_189`; maintained | **Lowest** — vendor API, no kernel dependency | **Low** via FeitCSI (kernel-agnostic, carries own µcode); AX-CSI research release is pinned | **Low–medium** — binary, tracks a supported Ubuntu LTS |
| **Output & tooling** | netlink `.dat`; `read_bf_file.m`; **CSIKit** | custom binary log; **CSIKit** | UDP/pcap int16; nexmon parsers; **CSIKit** | **CSV over serial/UDP**; csiparser; **CSIKit** | FeitCSI format + **GUI**; **CSIKit** reads FeitCSI | unified `.csi` container; MATLAB/Python toolbox; **CSIKit** |
| **Reproducible today?** (per audit) | **No (native)** — legacy kernel, or via PicoScenes | **No (native CSI)** — legacy fork; **spectral_scan is mainline**; CSI via PicoScenes | **Yes**, on current Pi (pinning discipline) | **Yes — easiest of all** | **Yes** — via FeitCSI (live USB) | **Yes** — the rescue platform for 5300/QCA9300 |

*(Rate figures are packet-arrival-limited, traffic-driven engineering guidance — see the note above — not fixed hardware sample rates.)*

---

## Reading between the columns

A few things the table implies but is worth saying out loud.

- **"Subcarriers" is not "phase you can use."** The Intel 5300's 30 *grouped* int8 values look thin next to the Atheros 56/114 full-precision per-subcarrier dump — and in practice they are. The 5300 is the *reference format* (a decade of datasets), not the *best* format. If you are choosing on raw 11n signal quality, Atheros wins the phase-fidelity argument among the classic three; nexmon wins on bandwidth and MIMO.

- **Every one of these needs a phase sanitizer.** None hands you carrier-clean phase. CFO (carrier frequency offset), SFO (sampling frequency offset), and STO (symbol timing offset) rotate the phase packet-to-packet; the standard fixes (linear-fit / conjugate-multiply across antennas, unwrap, per-subcarrier detrend) live in [../docs/techniques.md](../docs/techniques.md). "Needs calibration?" is therefore **yes for all six** — the column above rates *how much*, and where extra chip-specific gotchas bite (nexmon's null/pilot gaps and AGC amplitude scaling; the ESP32-C6 11ax LTF-ordering quirk).

- **The rate ceiling is usually the transport, not the radio.** ESP32's ~100 Hz-over-UART is a *serial* limit, not a Wi-Fi one — push CSI over UDP and it rises. nexmon's high-rate packet drops are a *Pi CPU / UDP* limit. Plan your Doppler budget around the transport you'll actually use.

- **Fragility, not capability, is what you'll fight.** The audit's core finding: the 5300 and Atheros *native* tools are `verified (legacy kernel)` — the capability is real, but you cannot `git clone` and run them on a 2025 machine. That is why two "classic" choices below are really "…via PicoScenes."

---

## Which should I pick? — verdict by use case

**"I want the cheapest possible CSI, or one standalone battery sensor, or a classroom set."**
→ **ESP32-CSI.** $3–8, a vendor-blessed API, zero firmware reversing, no host kernel to break. You trade away MIMO (1×1) and subcarrier count (≤52/64), and you accept ~100 Hz over serial. It is the reproducibility gold standard and the right first tool for almost everyone learning CSI. Use the mature **802.11n (HT-LTF)** path; treat ESP32-C6 802.11ax CSI as experimental (LTF-ordering caveat).

**"I want real bandwidth and MIMO on hardware I can buy today, for the best price."**
→ **nexmon_csi on a Raspberry Pi 4** (43455c0, ≤80 MHz), or a **Netgear/Asus RT-AC86U** (4366c0) when you need **4×4**. It is the strongest *maintained* firmware-patched commodity path. Budget for the setup tax: pin firmware `7_45_189`, expect friction on 64-bit Bookworm (the 32-bit image or a nexmonster/zeroby0 fork is the smoother road), and plan a calibration step for AGC amplitude scaling and null subcarriers.

**"I want the highest-fidelity, uncompressed 802.11n phase."**
→ **Atheros**, on the physics. But do **not** boot the 4.1.10 kernel fork on a fresh project — run the same silicon (**QCA9300 / AR9300 family**) under **PicoScenes** for a current-OS CSI path. Bonus, and a nice inversion: if you also want raw FFT bins, the **`ath9k spectral_scan`** (Tier-3) rung is *mainline* and works on a current kernel out of the box — more reproducible than the CSI rung beneath it.

**"I need Wi-Fi 6 / 6 GHz, one NIC, minimal fuss."**
→ **FeitCSI** on an **Intel AX210** (6 GHz) or AX200. Source + prebuilt binaries + a **live-USB distro** that carries its own patched microcode, so you sidestep kernel-version roulette entirely; it also does frame injection. This is the packaged, maintained descendant of the AX-CSI research patch — cite/reproduce via FeitCSI, not bare AX-CSI.

**"I'm building a research platform — many NICs, most PHY formats, MIMO arrays, 6 GHz, tight rate control."**
→ **PicoScenes.** One framework spanning IWL5300 / QCA9300 / AC9260 / AX200 / AX210 plus USRP/SoapySDR front-ends, up to 27 NICs concurrent, a unified `.csi` container, and a real parsing SDK. Accept the two honest costs: it is **binary, free-for-academic-use** (a reproducible path, not an auditable-source one) and it is **pinned to a supported Ubuntu LTS** (you follow its distro, it doesn't follow yours).

**"I specifically need to reproduce legacy IWL5300 datasets / the de-facto reference format."**
→ The **Linux 802.11n CSI Tool** *format* is immortal — every parser (CSIKit) still reads the old `.dat` files. For **live** capture, do not start new work on the archived native tool; use **PicoScenes** (IWL5300 support on Ubuntu 22.04) or a pinned ≤4.x kernel, and remember the card is **EOL**.

**"I can't patch firmware at all (compliance / locked environment)."**
→ Out of scope for these six, but the honest pointer is **beamforming-feedback ("pseudo-CSI") sniffing** (Wi-BFI) documented in the [survey](../projects/csi-toolchains.md) — monitor-mode only, no firmware patch, CSI-like features.

---

## One-line summary

- **Learning / cheapest / standalone:** ESP32-CSI (easiest, but 1×1).
- **Best buyable-hardware value with MIMO+BW:** nexmon_csi on a Pi (mind the pinning).
- **Cleanest 11n phase:** Atheros — but via PicoScenes on a modern kernel.
- **Wi-Fi 6 / 6 GHz, easy:** FeitCSI on AX210.
- **Research platform, everything at once:** PicoScenes.
- **Legacy reference format:** Intel 5300 — format lives forever; capture via PicoScenes.

Whatever you pick, **budget for phase sanitization** ([../docs/techniques.md](../docs/techniques.md)) and **let [CSIKit](https://github.com/Gi-z/CSIKit) read the output** — it parses all six formats, so your downstream code doesn't have to care which radio produced the data.

## Safety and legal note

CSI extraction is **receive-only** — you are reading channel estimates the radio already computed — so it does not carry the transmit-side legal exposure of arbitrary-waveform TX. Two caveats persist: (1) several of these tools (nexmon, FeitCSI, ath9k) also enable **injection/monitor** on the same card, which *is* regulated — do not transmit on channels/powers you are not licensed for; and (2) CSI is a **sensing** capability (presence, motion, breathing, gait). Capturing it about non-consenting people raises privacy and, in some jurisdictions, wiretap questions independent of RF rules. Sense your own space, or a lab, with consent. See [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md).

## See also

- [../projects/csi-toolchains.md](../projects/csi-toolchains.md) — the full toolchain survey (formats, subcarrier counts, every link) this comparison distills.
- [../docs/verification-tier2-csi.md](../docs/verification-tier2-csi.md) — the reproducibility audit whose verdicts this file must not exceed.
- [../docs/techniques.md](../docs/techniques.md) — phase sanitization (CFO/SFO/STO), the calibration every tool here needs.
- [CSIKit (Gi-z)](https://github.com/Gi-z/CSIKit) — the universal parser that reads all six output formats.

## References

1. Halperin et al. — *Tool Release: Gathering 802.11n Traces with CSI*, ACM SIGCOMM CCR 2011: <https://dhalperi.github.io/linux-80211n-csitool/> · repo (archived 2020): <https://github.com/dhalperi/linux-80211n-csitool>
2. Xie, Li — *Atheros CSI Tool* (ath9k): <https://github.com/xieyaxiongfly/Atheros-CSI-Tool> · guide: <https://wands.sg/research/wifi/AtherosCSI/>
3. `ath9k` `spectral_scan` (mainline): <https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath9k/spectral_scan.html>
4. Gringoli, Schulz, Link, Hollick — *Free Your CSI* (nexmon_csi, WiNTECH 2019): <https://github.com/seemoo-lab/nexmon_csi> · DOI: <https://doi.org/10.1145/3349623.3355477>
5. Espressif — *ESP-WIFI-CSI* + `esp-csi`: <https://github.com/espressif/esp-csi> · toolkit: <https://github.com/StevenMHernandez/ESP32-CSI-Tool>
6. Gringoli, Cominelli, Blanco, Widmer — *AX-CSI*, ACM WiNTECH 2021: <https://ans.unibs.it/assets/documents/axcsi.pdf> · DOI: <https://doi.org/10.1145/3477086.3480833>
7. KuskoSoft — *FeitCSI* (source + binary + live USB): <https://github.com/KuskoSoft/FeitCSI> · <https://feitcsi.kuskosoft.com/> · IEEE 2025: <https://ieeexplore.ieee.org/document/10944229/>
8. Jiang et al. — *PicoScenes*: <https://ps.zpj.io/> · arXiv: <https://arxiv.org/pdf/2010.10233>
9. `CSIKit` (Gi-z) — universal parser for all six formats: <https://github.com/Gi-z/CSIKit>
