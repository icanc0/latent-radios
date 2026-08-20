# Latent Radios — FAQ

Plain-language answers to the questions people actually ask before they buy a
dongle or flash firmware. Every answer links deeper into the catalog. If you
only read one other page first, make it the
[which-chip decision guide](../docs/which-chip-decision-guide.md).

> **One-line summary:** most commodity Wi-Fi chips are locked black boxes
> (tier 0). A handful expose monitor/injection (tier 1), CSI (tier 2),
> spectral scan (tier 3), and a rare few have open firmware or a real open
> PHY (tier 4–5). See [taxonomy](../docs/taxonomy.md) for the ladder.

---

## Can I use my laptop's built-in Wi-Fi for CSI or monitor mode?

**Usually not — and here is why.**

- **CSI:** Channel State Information is only exposed by a *specific short list*
  of chips with a patched driver/firmware. The famous "Intel CSI Tool" is for
  the **Intel 5300**, an 802.11n mini-PCIe card from ~2010 — **not** the
  AX200/AX201/AX210 Wi-Fi 6 parts in current laptops, which have **no public
  CSI path** at all. The Broadcom parts in MacBooks expose CSI only through
  `nexmon_csi`, and only on a few supported chips. So a modern built-in NIC
  almost never gives you CSI out of the box. See
  [Intel](../chips/intel.md), [Broadcom/Cypress](../chips/broadcom-cypress.md),
  and [CSI toolchains](../projects/csi-toolchains.md).
- **Monitor mode:** Many laptop chips *can* enter monitor mode on Linux
  (`ath9k`, some `iwlwifi`, `mt76`), so passive sniffing often works.
  **Injection** is the catch — Intel `iwlwifi` generally will not inject,
  and macOS gives you neither monitor persistence nor injection on the
  built-in card. Injection reliability is a driver/firmware property, not a
  "Wi-Fi card" property.

**Bottom line:** for anything beyond casual sniffing, buy the right external
dongle rather than fighting your built-in NIC. See the next answer and the
[decision guide](../docs/which-chip-decision-guide.md).

---

## What's the cheapest way to get CSI?

Two well-trodden, cheap routes:

| Route | Hardware | Cost | What you get |
|---|---|---|---|
| **ESP32-CSI-Tool** | Any ESP32 dev board | ~$5–10 | 802.11n, 20 MHz, ~64 subcarriers (HT-LTF), per-packet CSI over serial/UDP |
| **nexmon_csi** | Raspberry Pi 3B+/4/Zero 2 W (BCM43455c0) | ~$15–35 | Up to 80 MHz, 256 subcarriers, per-frame CSI |

- The **ESP32** is the single cheapest, most self-contained CSI source —
  microcontroller + radio on one board, no host driver patching. Great for
  breathing/presence demos and teaching.
- The **Pi + nexmon_csi** gives wider bandwidth and more subcarriers, at the
  cost of a firmware-patch build. It runs on the on-board BCM43455c0.

Details and pinouts in [CSI toolchains](../projects/csi-toolchains.md);
the Broadcom chip specifics are in
[Broadcom/Cypress](../chips/broadcom-cypress.md). For research-grade capture
across many NICs, look at **PicoScenes** (also covered in the toolchains doc).

---

## Which USB dongle should I buy for monitor + injection in 2025?

Depends on bands and how much driver pain you tolerate:

| Chip | Example dongle | Bands | Notes |
|---|---|---|---|
| **Atheros AR9271** (`ath9k_htc`) | Alfa AWUS036NHA, TL-WN722N **v1 only** | 2.4 GHz | The gold-standard beginner card: fully open, in-mainline, injection "just works". 802.11n only. |
| **MediaTek MT7612U** (`mt76`) | Alfa AWUS036ACM | 2.4/5 GHz | Best *in-kernel* dual-band option — open `mt76` driver, solid monitor + injection. |
| **Realtek RTL8812AU** | Alfa AWUS036ACH/AC | 2.4/5 GHz | Dual-band, popular, but needs the out-of-tree `morrownr`/aircrack driver. |
| **Realtek RTL8814AU** | Alfa AWUS1900 | 2.4/5 GHz | 4×4, more power/range; same out-of-tree driver caveat. |

**Recommendations:**
- **Beginner / aircrack-ng course:** AR9271. Nothing else is this painless.
- **One card, both bands, mainline driver:** an `mt76` MT7612U part.
- **Avoid** buying "TL-WN722N" blind — only the **v1** is AR9271; v2/v3 are
  Realtek and behave differently.
- Wi-Fi 6 USB (MT7921AU / RTL8852) monitor+injection is still **immature** in
  2025 — fine for STA use, not for reliable injection.

See [Qualcomm/Atheros](../chips/qualcomm-atheros.md),
[Realtek](../chips/realtek.md), [other vendors](../chips/other-vendors.md)
(MediaTek), and pick with the
[decision guide](../docs/which-chip-decision-guide.md).

---

## Can a Wi-Fi chip *really* transmit arbitrary signals? ("Shadow Wi-Fi" caveats)

**Short answer: sort of — with big caveats. A commodity Wi-Fi chip is not a
general-purpose arbitrary-waveform generator.** Two very different things get
conflated:

1. **Payload/subcarrier shaping on a commodity OFDM radio.**
   You cannot drive the DAC directly through closed firmware. Instead you craft
   the OFDM symbol content (subcarrier values, and the frame payload that feeds
   them) so the *emitted spectrum approximates* a target — tones, a spoofed
   waveform, or a covert channel hidden in a normal-looking frame. You are
   boxed in by the Wi-Fi PHY: fixed sample rates (20/40/80 MHz), cyclic prefix,
   scrambler, pilot tones, mandatory preamble, and the chip's own PA/filters.
   This is the mechanism behind covert-channel and "fake signal" demos (e.g.
   the `nexmon` line of work). It is **approximation within Wi-Fi
   constraints**, not clean IQ playback. See
   [nexmon](../projects/nexmon.md) and
   [techniques](../docs/techniques.md).
2. **A genuine open PHY on real SDR hardware — `openwifi`.**
   This is tier 5: an open-source 802.11 baseband running on a Zynq
   FPGA + AD9361 front-end. It *can* transmit real arbitrary waveforms —
   but that is an **SDR**, not a repurposed commodity Wi-Fi chip. See
   [openwifi](../projects/openwifi.md).

**Honest framing:** "Shadow Wi-Fi" / "my $10 dongle is a HackRF" claims almost
always mean case (1). Useful and clever; not a substitute for an SDR. The gap
is quantified in the [true-SDR comparison](../docs/true-sdr-comparison.md).
And note case (1) is **transmit** — read the legal answer below first.

---

## Is any of this legal?

**Not legal advice — but the RX/TX split is the thing to understand.**
Full treatment in [RF safety and legal](../docs/rf-safety-and-legal.md).

- **Receive-only (monitor, CSI, spectral scan, passive radar):** listening is
  generally low-risk, *but* capturing and decrypting **other people's**
  traffic can violate wiretap / computer-misuse laws (US ECPA, UK CMA, etc.).
  Sensing your **own** environment and RF you're authorized to receive is the
  safe lane.
- **Transmit (injection, deauth, arbitrary waveforms):** heavily regulated.
  Injecting frames into **your own** test network in-band and at legal power
  is usually fine for research; **deauth/jamming is illegal** — the FCC has
  issued large fines (e.g. the Marriott Wi-Fi blocking case). Emitting
  non-compliant or **off-band** signals violates FCC Part 15 (and equivalents
  worldwide), and modifying a certified transmitter's behavior can void its
  compliance entirely.

**Rule of thumb:** RX for sensing = usually OK; TX = assume it's regulated and
check before you key up. Details, power limits, and citations in
[RF safety and legal](../docs/rf-safety-and-legal.md).

---

## Can I turn my phone into an SDR?

**No — not the phone's own radios.**

- The **cellular baseband** is a locked, signed, certified black box with no
  monitor/CSI/raw-IQ API. There is no supported path to turn it into an SDR.
  See the [cellular baseband notes](../chips/cellular-basebands-as-sdrs.md).
- **Phone Wi-Fi:** monitor mode needs root **plus** a supported Broadcom chip
  **plus** a `nexmon` build — historically a few devices (e.g. Nexus 5 /
  BCM4339, Nexus 6P / BCM4358). Most modern phones: no go. See
  [nexmon](../projects/nexmon.md).
- **What actually works:** plug an **external** SDR (RTL-SDR, HackRF, etc.)
  into the USB-C/OTG port and run an SDR app. The phone becomes a *host and
  screen* for a real SDR — it is not itself the SDR.

---

## How accurate is Wi-Fi sensing, really?

Depends entirely on the task — and lab numbers rarely survive contact with a
new room:

- **Presence / gross motion detection:** robust, often >90% in controlled
  settings. This is the mature, deployable end.
- **Breathing / heart-rate / fine activity:** demonstrated in papers, but
  sensitive to geometry, and it needs CSI sanitization — commodity CSI carries
  CFO/SFO, AGC jumps, and random phase offsets that must be corrected before
  the physiology is visible.
- **Cross-environment / cross-person generalization:** typically **poor**.
  Models overfit to a specific room and layout; move the furniture and
  accuracy drops. This is the field's main open problem (and part of the
  motivation for the 802.11bf sensing standard).
- **Localization:** meter-level from raw CSI; **sub-meter** only with
  FTM/RTT time-of-flight and several APs — see
  [FTM/RTT ranging](../docs/ftm-rtt-ranging.md).

Treat impressive demo videos as an **upper bound**, not a deployment estimate.
Toolchain and dataset pointers in
[CSI toolchains](../projects/csi-toolchains.md).

---

## Where do I start?

Pick the lane that matches your goal, then follow its walkthrough:

| Goal | Start here |
|---|---|
| Monitor + injection basics | AR9271 dongle + aircrack-ng — [Qualcomm/Atheros](../chips/qualcomm-atheros.md) |
| Cheapest CSI | [ESP32-CSI-Tool](../projects/csi-toolchains.md) |
| Better CSI | Pi + [nexmon_csi](../projects/csi-toolchains.md) |
| Spectral scan | [ath9k spectral/CSI walkthrough](../docs/walkthroughs/atheros-ath9k-spectral-csi.md) |
| Classic Intel CSI | [Intel 5300 CSI walkthrough](../docs/walkthroughs/intel-5300-csi.md) |
| Firmware reverse-engineering | [Ghidra + Wi-Fi firmware setup](../docs/walkthroughs/ghidra-setup-wifi-firmware.md), [firmware reversing](../docs/firmware-reversing.md) |
| A real open PHY | [openwifi](../projects/openwifi.md) |

Then use the [decision guide](../docs/which-chip-decision-guide.md) to choose a
chip, and [methodology](../docs/methodology.md) to understand how entries in
this catalog are rated. New to the vocabulary? The
[glossary](../docs/glossary.md) defines CSI, LTF, injection, spectral scan,
and the rest.

---

## References

- ESP32-CSI-Tool — https://github.com/StevenMHernandez/ESP32-CSI-Tool
- nexmon_csi — https://github.com/seemoo-lab/nexmon_csi
- nexmon (framework) — https://github.com/seemoo-lab/nexmon
- Intel 5300 CSI Tool (Halperin et al.) — https://dhalperi.github.io/linux-80211n-csitool/
- Atheros CSI Tool (Xie Yaxiong) — https://wands.sg/research/wifi/AtherosCSI/
- PicoScenes — https://ps.zpj.io/
- openwifi — https://github.com/open-sdr/openwifi
- aircrack-ng — https://www.aircrack-ng.org/
- morrownr Realtek USB drivers — https://github.com/morrownr
- mt76 driver — https://github.com/openwrt/mt76
- FCC enforcement, Wi-Fi blocking (Marriott) — https://docs.fcc.gov/public/attachments/DA-14-1444A1.pdf
- IEEE 802.11bf (WLAN sensing) — https://www.ieee802.org/11/Reports/tgbf_update.htm
