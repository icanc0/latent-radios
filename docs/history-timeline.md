# A Short History of Turning Wi-Fi Chips into Radios

*Cycle 7 — a narrative timeline tying the catalog together.*

Every entry in this catalog exists because, over roughly two decades, a chain of
reverse-engineers, driver hackers, and academics pried open one more layer of the
Wi-Fi PHY. None of these chips was *designed* to be a software-defined radio. Each
became one because someone refused to accept the vendor's black box — first reading
back a frame, then a per-subcarrier channel estimate, then a spectral snapshot, and
finally injecting an arbitrary waveform. This page is the through-line: how the
community climbed the [SDR ladder](../docs/methodology.md) one rung at a time, and
who pushed it there.

The recurring pattern is worth naming up front. A commodity 802.11 chip hides the
PHY behind opaque firmware running on an on-die microcontroller (a Broadcom "d11"
core, an Atheros/Qualcomm Xtensa or ARC, an Intel microcode blob, an ESP32 Xtensa
LX6). Progress always came from one of three moves: **(1)** the vendor shipped an
open driver that already exposed a register or debugfs hook (ath9k spectral scan);
**(2)** someone reverse-engineered and rewrote the firmware outright (OpenFWWF,
carl9170, ath9k_htc, Nexmon); or **(3)** someone found the internal buffer where the
DSP had already computed what we wanted — the channel estimate — and dumped it before
the firmware discarded it (every CSI tool). The ladder below tracks which move
unlocked which rung.

---

## Timeline at a glance

| Year | Milestone | People / Lab | Chip family | Rung unlocked |
|------|-----------|--------------|-------------|---------------|
| ~2005–2007 | `bcm43xx` / **b43** driver RE | Michael Büsch, Larry Finger, community | Broadcom | Open driver → monitor/inject |
| 2008 | **OpenFWWF** — open Wi-Fi firmware | F. Gringoli, L. Nava (Univ. Brescia) | Broadcom b43 | First fully open, editable PHY-adjacent firmware |
| 2008 | **ath9k** merged into mainline Linux | Atheros + community | Atheros AR9xxx | Open driver, debugfs hooks |
| ~2009–2011 | **carl9170** open USB firmware | Christian Lamparter | Atheros AR9170 (USB) | Open firmware on a shipping part |
| 2011 | **Linux 802.11n CSI Tool** | Halperin, Hu, Sheth, Wetherall (UW) | Intel 5300 | **Rung 2 — CSI** goes mainstream |
| ~2011–2013 | **ath9k spectral scan** exposed | S. Wunderlich, ath9k devs | Atheros AR92xx/AR93xx | **Rung 3 — spectral** |
| ~2013 | **open-ath9k-htc-firmware** opened | Qualcomm Atheros, Oleksij Rempel | AR9271 / AR7010 (USB) | Open firmware, later CSI/injection base |
| 2015 | **Atheros CSI Tool** | Yaxiong Xie, Zhenjiang Li, Mo Li (NTU) | Atheros AR9380/9580 | CSI from a second, cheaper family |
| 2015–2017 | **Nexmon** firmware-patching framework | M. Schulz, D. Wegemer, M. Hollick (SEEMOO, TU Darmstadt) | Broadcom/Cypress | Reusable C toolchain for firmware RE |
| 2018 | **Shadow Wi-Fi** — arbitrary raw TX + covert CSI | Schulz, Link, Gringoli, Hollick | Broadcom (Nexmon) | **Rung 4 — arbitrary-waveform TX** |
| 2019 | **nexmon_csi** | Gringoli, Schulz, Link, Hollick | Broadcom/Cypress (incl. phones) | CSI on billions of consumer devices |
| ~2019–2020 | **ESP32 CSI Toolkit** | Steven M. Hernandez, Eyuphan Bulut (VCU) | Espressif ESP32 | CSI on a $3 standalone MCU |
| ~2020–2021 | **AX-CSI** | Gringoli, Cominelli, Blanco, Widmer | Broadcom 802.11ax | CSI extended to 802.11ax / 160 MHz |
| 2021 | **PicoScenes** platform | Zhiping Jiang et al. | Intel AX200/AX210, QCA9300, IWL5300 | Unified multi-vendor CSI + baseband insight |
| 2020s | **IEEE 802.11bf** WLAN Sensing | IEEE 802.11 TGbf | Standardized | Sensing becomes a spec, not a hack |

---

## The rungs, in order

### Prehistory: opening the driver (mid-2000s)

Before any of this, a Wi-Fi chip was a sealed appliance. The first crack was simply
getting an *open driver*. The `bcm43xx` effort and its successor **b43** (Michael
Büsch, Larry Finger, and a large community) reverse-engineered Broadcom's SoftMAC
parts well enough to give Linux monitor mode and frame injection — **rung 1**. This
mattered less for the specific chips than for the culture it established: the PHY was
a legitimate target for reverse engineering, and monitor+injection was the price of
admission.

Atheros made the same rung far easier. When **ath9k** was merged into the mainline
Linux kernel in 2008, it arrived as a genuinely open driver for a MAC/PHY whose
register layout was documented enough to hack on. ath9k would become the single most
important chip family in the early SDR-repurposing story, precisely because so little
had to be reverse-engineered to reach the interesting registers.

### Rewriting the firmware (2008–2013)

An open *driver* still leaves the on-chip firmware as a black box. The Università di
Brescia group closed that gap. **OpenFWWF** ("Open Firmware for WiFi networks", led by
Francesco Gringoli with Lorenzo Nava, ~2008) was a from-scratch, open-source firmware
for the Broadcom d11 microcontroller that the b43 driver already knew how to load. For
the first time, researchers could edit the code running *on the chip* — change timing,
tinker with the MAC state machine, and read internal state. This is the ancestor of
everything Nexmon later industrialized, and Gringoli reappears at nearly every
subsequent milestone.

Atheros' USB parts got the same treatment. **carl9170** (Christian Lamparter, building
on the earlier "otus" work) was open firmware for the AR9170 802.11n USB dongle, and a
few years later Qualcomm Atheros released the source for the AR9271/AR7010 firmware as
**open-ath9k-htc-firmware** (opened up with help from Oleksij Rempel). An open USB
firmware on a cheap, widely available dongle turned out to be the ideal teaching
platform — you could brick it and re-flash without opening a laptop.

### Rung 2 — Channel State Information (2011, 2015)

The pivotal insight of the 2010s was that the chip's DSP already computes, for every
received frame, a per-subcarrier complex channel estimate — the CSI — in order to
equalize the signal. It normally throws that away. If you can dump it, a Wi-Fi card
becomes a coarse vector network analyzer for the room.

**Daniel Halperin, Wenjun Hu, Anmol Sheth, and David Wetherall** (University of
Washington) shipped the **Linux 802.11n CSI Tool** and documented it in *"Tool Release:
Gathering 802.11n Traces with Channel State Information"* (ACM SIGCOMM CCR, January
2011). It worked by patching the Intel 5300's microcode/driver to report CSI for 30
subcarrier groups across up to 3×3 MIMO streams. This single tool launched the entire
academic field of Wi-Fi sensing — localization, gesture and activity recognition,
respiration monitoring — and it is still one of the most-cited systems papers in the
area.

Four years later, **Yaxiong Xie, Zhenjiang Li, and Mo Li** (NTU Singapore) released the
**Atheros CSI Tool**, alongside *"Precise Power Delay Profiling with Commodity WiFi"*
(MobiCom 2015). Built on ath9k, it exposed finer-grained, per-subcarrier CSI (and
richer timing) on cheap AR9380/AR9580-class cards, breaking the Intel 5300's monopoly
and giving the community a second, independent hardware path.

### Rung 3 — Spectral scan (early 2010s)

CSI tells you about the channel *where a Wi-Fi frame just landed*. Spectral scan gives
you raw FFT bins across the band regardless of what's transmitting — a poor-man's
spectrum analyzer. ath9k already had the hardware; the community (notably Simon
Wunderlich and the ath9k developers) wired the **`spectral_scan`** debugfs interface to
dump the PHY's FFT samples. Suddenly an off-the-shelf laptop card could see
non-Wi-Fi interferers, microwave ovens, and radar. This is the highest rung reachable
on many chips *without* rewriting firmware — the vendor left the door open.

### Rung 4 — arbitrary waveforms and the Nexmon era (2015–2019)

The **Secure Mobile Networking Lab (SEEMOO)** at TU Darmstadt — **Matthias Schulz,
Daniel Wegemer, and Matthias Hollick** — generalized firmware hacking into a reusable
toolchain. **Nexmon** (developed ~2015–2017; foundational reference is Schulz's 2018
dissertation, *"Teaching Your Wireless Card New Tricks"*) let you write firmware patches
in **C** — not disassembly — against Broadcom/Cypress chips, from Raspberry Pi radios
to the Wi-Fi cores inside iPhones and Galaxy phones. It industrialized what OpenFWWF
had done by hand.

Nexmon's most radical result was **Shadow Wi-Fi** (Schulz, Link, Gringoli, Hollick,
MobiSys 2018): teaching a *smartphone* Wi-Fi chip to transmit **arbitrary raw
baseband samples** and to extract CSI, enough to build a practical physical-layer
covert channel underneath ordinary Wi-Fi traffic. Arbitrary-waveform TX from a
commodity Wi-Fi chip is **rung 4** — the point where "Wi-Fi card" and "software radio"
genuinely overlap.

Then Nexmon democratized rung 2. **nexmon_csi** (Gringoli, Schulz, Link, Hollick —
*"Free Your CSI"*, WiNTECH 2019) delivered CSI extraction across a wide range of
Broadcom/Cypress chipsets, including those in phones and the Raspberry Pi. CSI went
from two special research NICs to *billions* of consumer devices.

### Making it cheap and standalone (2019–2021)

Two developments pushed sensing out of the lab. **Espressif's ESP32** — a ~$3
microcontroller with an integrated Xtensa CPU and Wi-Fi — turned out to expose CSI
through its official SDK. **Steven M. Hernandez and Eyuphan Bulut** (Virginia
Commonwealth University) packaged this as the **ESP32 CSI Toolkit** (~2019–2020),
making a self-contained, batteryable CSI sensor that needs no host PC. Meanwhile
**AX-CSI** (Gringoli, Cominelli, Blanco, Widmer, ~2020–2021) carried CSI extraction
forward to **802.11ax** on Broadcom silicon, coping with wider 160 MHz channels and
denser subcarrier grids.

**PicoScenes** (Zhiping Jiang et al., published in the *IEEE Internet of Things
Journal*, ~2021–2022) then unified the fragmented landscape: one platform driving
Intel AX200/AX210, QCA9300, and the venerable IWL5300, with an emphasis on
*understanding* Wi-Fi baseband design rather than treating each chip as a one-off hack.
It represents the maturation of the field — the accumulated reverse-engineering of a
decade turned into reusable infrastructure.

### From hack to standard: 802.11bf (2020s)

The final turn is that the standards body noticed. The IEEE **802.11bf** ("WLAN
Sensing") task group set out to make sensing a *first-class, standardized* capability —
defining how devices negotiate measurements and report channel information, in both
sub-7 GHz and 60 GHz (mmWave) bands. What began as dumping a buffer the firmware meant
to discard is on its way to being a documented feature of the protocol. The catalog's
long arc — black box → open driver → CSI → spectral → arbitrary TX → *standard* — closes
here.

---

## The through-line

Read the table top to bottom and one pattern dominates: **each step pried open a
little more of the PHY, and almost never by inventing new silicon.** The hardware was
always capable; the work was in reverse-engineering firmware, finding the right buffer,
or convincing an open driver to hand back what it already knew.

- **Monitor/inject (rung 1)** came from open *drivers* (b43, ath9k).
- **CSI (rung 2)** came from finding the DSP's existing channel estimate (Intel 5300,
  Atheros, then Nexmon everywhere).
- **Spectral (rung 3)** came from a debugfs hook the vendor left open (ath9k).
- **Arbitrary TX / raw IQ (rung 4)** required *rewriting the firmware* (OpenFWWF →
  Nexmon → Shadow Wi-Fi).
- **Rung 5** — a fully open or documented PHY — remains rare on Wi-Fi silicon; the
  genuinely open designs live in the [true-SDR comparison](../docs/true-sdr-comparison.md)
  and openwifi worlds, which is exactly why they matter.

A few threads recur throughout: **Francesco Gringoli** (OpenFWWF → nexmon_csi →
AX-CSI), **SEEMOO / Matthias Schulz** (Nexmon → Shadow Wi-Fi → nexmon_csi), and the
**ath9k** family as the workhorse that made rungs 2 and 3 approachable. If you want to
*do* any of this today, start with the two hubs this history feeds into: the
**[Nexmon project notes](../projects/nexmon.md)** for firmware patching, and the
**[CSI toolchains guide](../projects/csi-toolchains.md)** for pulling channel
estimates. The **[methodology page](../docs/methodology.md)** defines the ladder every
milestone above is scored against.

---

## References

Primary sources, roughly in the order they appear above.

- b43 driver — Linux Wireless: <https://wireless.wiki.kernel.org/en/users/drivers/b43>
- OpenFWWF (Univ. Brescia) — <https://netweb.ing.unibs.it/~openfwwf/>
- ath9k driver — Linux Wireless: <https://wireless.wiki.kernel.org/en/users/drivers/ath9k>
- carl9170 firmware — <https://wireless.wiki.kernel.org/en/users/drivers/carl9170>
- open-ath9k-htc-firmware — <https://github.com/qca/open-ath9k-htc-firmware>
- Halperin, Hu, Sheth, Wetherall, *"Tool Release: Gathering 802.11n Traces with Channel State Information,"* ACM SIGCOMM CCR, Jan. 2011 — <https://dhalperi.github.io/linux-80211n-csitool/>
- ath9k spectral scan — <https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan>
- Xie, Li, Li, *"Precise Power Delay Profiling with Commodity WiFi,"* MobiCom 2015 — Atheros CSI Tool: <https://wands.sg/research/wifi/AtherosCSI/> (mirror: <https://github.com/xieyaxiongfly/Atheros-CSI-Tool>)
- Nexmon firmware-patching framework (SEEMOO, TU Darmstadt) — <https://github.com/seemoo-lab/nexmon>
- Schulz, *"Teaching Your Wireless Card New Tricks,"* Ph.D. dissertation, TU Darmstadt, 2018 — <https://tuprints.ulb.tu-darmstadt.de/7243/>
- Schulz, Link, Gringoli, Hollick, *"Shadow Wi-Fi,"* MobiSys 2018 — <https://doi.org/10.1145/3210240.3210333>
- Gringoli, Schulz, Link, Hollick, *"Free Your CSI: A Channel State Information Extraction Platform for Modern Wi-Fi Chipsets,"* WiNTECH 2019 — <https://github.com/seemoo-lab/nexmon_csi>
- ESP32 CSI Toolkit (Hernandez & Bulut, VCU) — <https://github.com/StevenMHernandez/ESP32-CSI-Tool>
- Gringoli, Cominelli, Blanco, Widmer, *"AX-CSI: Enabling CSI Extraction on Commercial 802.11ax Wi-Fi Platforms,"* WiNTECH 2021 — <https://doi.org/10.1145/3477086.3480833>
- Jiang et al., *"Eliminating the Barriers: Demystifying Wi-Fi Baseband Design and Bringing Up PicoScenes Wi-Fi Sensing Platform,"* IEEE IoT Journal, 2021 — <https://ps.zpj.io/>
- Restuccia, *"IEEE 802.11bf: Toward Ubiquitous Wi-Fi Sensing,"* and IEEE 802.11 TGbf — <https://www.ieee802.org/11/Reports/tgbf_update.htm>

*See also:* [firmware-reversing.md](../docs/firmware-reversing.md) ·
[true-sdr-comparison.md](../docs/true-sdr-comparison.md) ·
[projects/openwifi.md](../projects/openwifi.md)
