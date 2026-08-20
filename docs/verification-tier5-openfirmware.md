# Verifying the Tier-5 (open firmware / open PHY) claims

> Adversarial audit, Cycle 6. Companion to [`verification-tier4.md`](verification-tier4.md) and [`verification-tier5-openfirmware.md`](verification-tier5-openfirmware.md). Tier definitions live in [`taxonomy.md`](taxonomy.md); the openwifi project has its own page at [`../projects/openwifi.md`](../projects/openwifi.md).

The catalog marks ~21 parts **Tier 5** ("open/documented PHY or genuine SDR"). Tier 5 is the top of the ladder and the most easily inflated, because three very different things get sloppily lumped under the word *"open"*:

1. **Open firmware** — the source of the *MAC microcontroller* code is published and rebuildable (OpenFWWF, open-ath9k-htc-firmware, carl9170fw).
2. **Open PHY** — the baseband/modem itself is open and reconfigurable (openwifi's Verilog; a real SDR you program).
3. **Open *driver*, closed firmware** — the Linux driver is GPL but the on-chip blob is proprietary (ath10k, brcmfmac, iwlwifi, mt76). This is *not* open firmware and must never be counted toward Tier 5.

The load-bearing claim of this audit: **open MAC firmware does not equal an open PHY, and it does not equal an SDR.** A chip whose only "open" property is its MAC microcode has a *fixed silicon PHY* — you can retime and rewrite frames, but you cannot synthesize an arbitrary waveform or read raw IQ. That is **Tier 1**, plus the `open-firmware` capability flag — not Tier 5. Only category (2) earns Tier 5, and it earns it because the PHY is open, not because a chip was cleverly repurposed.

---

## Verdict table

| Part / claim | Project (primary source) | Open MAC firmware? | Open PHY / raw IQ? | Upstream last commit | Tier 5 justified? | Honest tier |
|---|---|---|---|---|---|---|
| Broadcom **BCM4306 / BCM4311 / BCM4318** (G-PHY) | OpenFWWF + b43-tools | **Yes** (GPL D11 microcode) | **No** — fixed G-PHY silicon | OpenFWWF microcode frozen ~2011–2012; b43-tools **2026-05-22** | **No** | **Tier 1** + `open-firmware` |
| Atheros **AR9271** (USB 11n) | open-ath9k-htc-firmware | **Yes** (Tensilica MAC fw) | **No** — ath9k PHY closed | **2023-11-03** (dormant) | **No** | **Tier 1** + `open-firmware`¹ |
| Atheros **AR7010** (USB bridge + AR928x) | open-ath9k-htc-firmware | **Yes** | **No** | **2023-11-03** (dormant) | **No** | **Tier 1** + `open-firmware`¹ |
| Atheros **AR9170** (USB 11n) | carl9170fw | **Yes** | **No** — fixed PHY | **2026-08-07** (active) | **No** | **Tier 1** + `open-firmware` |
| **openwifi** (Zynq-7000/MPSoC + AD9361/AD9364) | open-sdr/openwifi | **Yes** (also open low-MAC) | **Yes** — open Verilog PHY, raw IQ/CSI | **2026-08-14** (active) | **Yes** ✅ | **Tier 5** (SDR *implementing* Wi-Fi) |
| True SDRs (USRP / HackRF / bladeRF / LimeSDR / Pluto) + `gr-ieee802-11` | GNU Radio OOT | n/a — you write the PHY | **Yes** | active | **Yes** ✅ | **Tier 5** (different category) |
| ath10k / brcmfmac / iwlwifi / mt76 | vendor blobs | **No** (open *driver*, closed fw) | **No** | n/a | **No** | per-chip, **never** Tier 5 on openness alone |

¹ ath9k-family chips separately expose FFT **spectral-scan** (a PHY *diagnostic*, potentially Tier 3) documented in [`../chips/qualcomm-atheros.md`](../chips/qualcomm-atheros.md). That capability comes from the silicon PHY, **not** from the open firmware, and does not upgrade the open-firmware claim to Tier 5.

---

## The genuinely-open-firmware Wi-Fi chips (Tier 1, not Tier 5)

### OpenFWWF — Broadcom b43 D11 microcode

[OpenFWWF](http://netweb.ing.unibs.it/~openfwwf/) ("Open FirmWare for WiFi networks", University of Brescia) is a **from-scratch GPL replacement for the Broadcom D11 MAC microcode** that the mainline `b43` driver loads. It is real, genuinely-open firmware — but three facts deflate the Tier-5 reading:

- **It only covers old G-PHY silicon.** The published microcode targets the LP/G-PHY D11 cores found in **BCM4306, BCM4311 (rev 1), BCM4318** (ucode rev ~5). It does **not** run on N-PHY / HT chips (BCM4321, BCM43224, BCM4331, …) and has nothing to do with the FullMAC `brcmfmac` parts that [nexmon](../projects/csi-toolchains.md) patches for CSI. So the "open firmware Broadcom" claim is confined to ~2004-era 54g cards.
- **It is effectively frozen.** The microcode itself has seen no substantive release since roughly **2011–2012**. What *is* alive is the toolchain: **b43-tools** (Michael Büsch — `b43-asm`/`b43-dasm` assembler/disassembler, `ssb-sprom`), last commit **2026-05-22**. A live assembler for a dead firmware is a research convenience, not evidence of an open PHY.
- **The PHY stays closed silicon.** OpenFWWF lets you rewrite the *MAC* state machine — this is exactly what the Brescia "Wireless MAC Processor" work exploited: custom backoff, TDMA, precise TX timing, deterministic injection. You never touch the modem. **No raw IQ, no arbitrary waveform, no CSI.** That is Tier 1 with an `open-firmware` flag, not Tier 5.

Most `b43` users never run OpenFWWF at all — they run the proprietary Broadcom blob extracted by `b43-fwcutter`. Do not conflate "b43 is an open driver" (true) with "b43 firmware is open" (only true for these three G-PHY parts, via OpenFWWF).

### open-ath9k-htc-firmware — Atheros AR9271 / AR7010

[qca/open-ath9k-htc-firmware](https://github.com/qca/open-ath9k-htc-firmware) is the **open MAC firmware** (mixed ClearBSD / MIT / GPLv2, Tensilica Xtensa target) that Linux `ath9k_htc` and OpenBSD `athn` load into the USB 11n dongles:

- **AR9271** — single-chip 2.4 GHz 1×1 (the famous injection radio in the Alfa AWUS036NHA).
- **AR7010** — USB/PCIe bridge SoC paired with an **AR9280/AR9287** companion (2×2, dual-band).

This is genuinely open, rebuildable firmware (`cmake` + Xtensa toolchain). But: last commit **2023-11-03**, ~409 commits, ~79 open issues — **upstream is dormant**, alive mostly through distro forks. And again the PHY is Atheros silicon: the open firmware buys you rock-solid **monitor + injection** (Tier 1) and MAC-timing control, nothing at the IQ level. The ath9k *family* spectral-scan FFT (Tier-3-ish) is a separate silicon feature, strongest on the PCIe AR92xx/AR93xx siblings, and is orthogonal to the firmware being open. **Not Tier 5.**

### carl9170fw — Atheros AR9170

[chunkeey/carl9170fw](https://github.com/chunkeey/carl9170fw) (Christian Lamparter) is the open firmware for the **AR9170** USB 11n devices, loaded by the `carl9170` driver. Notably it is the **best-maintained of the open MAC firmwares** — last commit **2026-08-07** (toolchain bump to gcc 16.2.0), built via KConfig + CMake. Maintenance is real; the ceiling is not. Same story as above: open MAC microcode over a fixed PHY → **monitor + injection, Tier 1** + `open-firmware`. No IQ, no arbitrary waveform.

---

## The one that *is* legitimately Tier 5: openwifi

[open-sdr/openwifi](https://github.com/open-sdr/openwifi) (IDLab, imec/Ghent — Xianjun Jiao et al.) is a **Linux `mac80211`-compatible full-stack 802.11a/g/n design built on SDR**, and it is Tier 5 for the *right* reason: **the PHY itself is open**. The OFDM baseband is open Verilog running in the Zynq FPGA fabric; the low-MAC (DCF/CSMA-CA, 10 µs SIFS) is open RTL; the front end is an **AD9361/AD9364** (70 MHz–6 GHz) fed real IQ. You can read raw IQ and CSI, inject/fuzz, and — because it is HDL — literally rewrite the modem. Very active: last commit **2026-08-14** (1,120+ commits; PR #506 added compact Buildroot images). Licensing is **AGPLv3** with a commercial option.

Verified supported boards (from the [README](https://github.com/open-sdr/openwifi/blob/master/README.md)):

| Board | RF frontend | Zynq class | Vivado paid license |
|---|---|---|---|
| Xilinx ZC706 | FMCOMMS2/3/4 | Z-7045 | Required |
| Xilinx ZED (Zedboard) | FMCOMMS2/3/4 | Z-7020 | Not required |
| Xilinx ZC702 | FMCOMMS2/3/4 | Z-7020 | Not required |
| ADRV9364-Z7020 | on-board AD9364 | Z-7020 | Not required |
| ADRV9361-Z7035 | on-board AD9361 | Z-7035 | Required |
| Xilinx ZCU102 | FMCOMMS2/3/4 | ZU9 MPSoC | Required |
| AntSDR / ANTSDR-E200/E310, SDRPi, NeptuneSDR, LibreSDR | enhanced PlutoSDR-class AD936x | Z-7020/7035 | mixed |

**Crucial framing:** openwifi is an **SDR that implements Wi-Fi**, not a commodity Wi-Fi chip repurposed as an SDR. It belongs on the same shelf as USRP/HackRF/bladeRF/LimeSDR/PlutoSDR running [`gr-ieee802-11`](../projects/gnuradio-oot-modules.md) — legitimately Tier 5, but achieved by *building* the PHY, which is the opposite of this catalog's usual thesis (extracting SDR behavior from a locked commodity radio). See [`../docs/true-sdr-comparison.md`](true-sdr-comparison.md).

---

## The trap: "open driver, closed firmware" is not open firmware

Several widely-deployed chips ship a **GPL Linux driver** and are casually described as "open." Their on-chip firmware is a **proprietary blob** — they contribute nothing to a Tier-5 open-firmware claim:

| Driver / chip family | Driver | On-chip firmware | Reality |
|---|---|---|---|
| `ath10k` (QCA988x/9880/9887/99xx) | open | **closed blob** | open driver only |
| `ath11k` (QCN90xx/WCN685x) | open | **closed blob** | open driver only |
| `brcmfmac` (BCM43xx FullMAC) | open | **closed blob** (nexmon *patches* it) | open driver only |
| `iwlwifi` (Intel AX2xx/BE2xx) | open | **closed ucode** | open driver only |
| `mt76` (MT76xx / MT79xx) | open | **closed blob** | open driver only |

`nexmon` on `brcmfmac` is the important nuance: it **patches** a closed blob (impressive, and the basis of nexmon-CSI), but it is not *open* firmware — you get documented offsets and injectable patches, not published source. That is [`patchable`](taxonomy.md), tracked on its own merits in [`../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md), and it does not promote those parts to Tier 5.

---

## Corrected records emitted

Four downgrades and one affirmation (`modules[]`, merged by id):

- **`broadcom-bcm4318`**, **`atheros-ar9271`**, **`atheros-ar7010`**, **`atheros-ar9170`** — demoted from any Tier-5/open-PHY reading to **Tier 1**, `openness: open` (the *firmware* is open), `open-firmware` capability retained, with notes stating open MAC firmware ≠ open PHY.
- **`openwifi-ad9361`** — affirmed **Tier 5**, `openness: open`, flagged as an SDR-implementing-Wi-Fi to keep it distinct from repurposed commodity chips.

## Sources

- OpenFWWF (University of Brescia): http://netweb.ing.unibs.it/~openfwwf/
- b43-tools (Michael Büsch, assembler/disassembler): https://github.com/mbuesch/b43-tools — last commit 2026-05-22
- b43 driver docs: https://wireless.docs.kernel.org/en/latest/en/users/drivers/b43.html
- open-ath9k-htc-firmware: https://github.com/qca/open-ath9k-htc-firmware — last commit 2023-11-03
- carl9170fw: https://github.com/chunkeey/carl9170fw — last commit 2026-08-07
- openwifi: https://github.com/open-sdr/openwifi — last commit 2026-08-14; README: https://github.com/open-sdr/openwifi/blob/master/README.md
- gr-ieee802-11: https://github.com/bastibl/gr-ieee802-11
