# Prism2 & HostAP: where monitor mode and injection were born

> Latent Radios — Cycle 8 (history + RE walkthrough). The historical taproot of everything else in this
> catalog. Before "put the card in monitor mode" and "inject a deauth" were one-liners, someone had to
> invent the idea that a commodity 802.11 client card could be told to *hand you raw frames* and
> *transmit frames you built by hand*. That someone was, in large part, Jouni Malinen, and the hardware
> was the Intersil Prism2.
>
> See also: [../../docs/history-timeline.md](../../docs/history-timeline.md) ·
> [../../docs/glossary.md](../../docs/glossary.md) ·
> [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md) ·
> [../../chips/hardware-index.md](../../chips/hardware-index.md)

## Why this file exists

Every "Tier 1" (monitor + injection) entry in this catalog — the RTL8812AU walkthrough, the ath9k cards,
the Nexmon patches on Broadcom — inherits a capability model that did not exist in consumer Wi-Fi until
roughly 2001-2003. Monitor mode (receive *all* 802.11 frames, including management/control, with a
radio-metadata header) and raw injection (transmit an arbitrary, driver-supplied 802.11 frame) were not
part of the original product plan for any of these chips. They were unlocked by a small group of drivers
built around one FullMAC 802.11b family: **Intersil Prism2/2.5/3**. This entry documents that lineage and
files net-new catalog records for the chips involved, plus the **Agere/Lucent Hermes ("Orinoco")** family
as the instructive counter-example — the card that could *listen* but essentially could not *inject*.

None of these are SDRs in the raw-IQ sense (they are closed-firmware FullMAC 802.11b parts, forever
**Tier 1** on our ladder). Their importance is conceptual: they are the ancestors of the software
interface — monitor virtual interfaces, radiotap-framed injection, pcap link types — that the *real*
firmware-RE SDRs in this catalog still expose today.

## The hardware: the Intersil Prism family

"Prism" (PRoprietary Integrated Sub-system for Mobile) began at **Harris Semiconductor**, which spun its
semiconductor business off as **Intersil** in 1999. Intersil sold the Prism line to **GlobespanVirata** in
2003, which was absorbed by **Conexant** in early 2004 ([Wikipedia: Prism chipset](https://en.wikipedia.org/wiki/Prism_(chipset))).

The Prism2/2.5/3 generation is **802.11b only** (2.4 GHz, DSSS/CCK, up to 11 Mbps). It is a **FullMAC**
design: the 802.11 MAC state machine runs as loadable firmware on an on-chip microcontroller (the
"station firmware"), and the host talks to it through a documented register/record interface. That last
detail is the whole story — Intersil documented the **HFA384x host interface** (the RID read/write "record"
API and the command/buffer registers) well enough that outsiders could write a full driver, *including
modes Intersil never shipped a product feature for.*

| Generation | Common MAC/baseband part(s) | Form | Band / std | Notes |
|---|---|---|---|---|
| Prism (1) | HFA3860 + companions | reference design | 2.4 GHz, 802.11 (1-2 Mbps) | pre-11b; rare |
| **Prism 2** | HFA3841 (MAC) + HFA3861 (baseband) + HFA3783 IF + HFA3683 RF | multi-chip; PCMCIA/PCI | 2.4 GHz, 802.11b | the wardriving card |
| **Prism 2.5** | ISL3874 (integrated MAC/baseband) | mini-PCI, embedded | 2.4 GHz, 802.11b | Soekris/embedded favorite |
| **Prism 3** | ISL3871 / ISL3872 / ISL3873 | single-chip, cost-reduced, USB | 2.4 GHz, 802.11b | cheap late-era 11b, incl. USB |
| Prism GT | ISL3880 / ISL3886 | PCI/CardBus | 2.4 GHz, 802.11g | successor; different firmware; `p54`/`prism54` |
| Prism Duette | ISL3877 + dual-band RF | — | 2.4 + 5 GHz, 802.11a/b | dual-band variant |
| Prism Nitro | (11b + frame-bursting) | — | 2.4 GHz, 802.11b+ | marketing/perf tweak, same family |

All Prism2/2.5/3 cards run the **HFA384x station firmware** (loadable; flashable from the host with
`prism2_srec`). The firmware image comes in "primary" (bootstrap) and "station"/"tertiary" flavors; some
station-firmware builds specifically enabled the **Host AP** operating mode. That firmware knob is what
Malinen's driver was named after.

## HostAP: the driver that changed the model

Around **2001-2002**, Jouni Malinen (j@w1.fi) released the **Host AP driver for Intersil Prism2/2.5/3**
([w1.fi/hostap](https://w1.fi/hostap/)). Three things made it historic:

1. **Master mode (the name).** Prism2 firmware could run in a "Host AP" mode where the *host* generates
   beacons, handles association, and does AP management, rather than a fixed vendor AP firmware. HostAP
   let an ordinary client card *become an access point* — the first widely usable soft-AP on commodity
   Wi-Fi, years before this was normal. `iwconfig wlan0 mode Master`.
2. **Monitor mode with a radio header.** HostAP exposed a true monitor mode that delivered *every* 802.11
   frame — management, control, data — up to userspace, prepended with the **Prism2 capture header**
   (per-frame signal, noise, rate, channel). In libpcap this became `DLT_PRISM_HEADER` (link type 119),
   the direct ancestor of today's `DLT_IEEE802_11_RADIO` (radiotap, 127). This is where "put the card in
   monitor mode" comes from as an everyday phrase.
3. **Raw injection.** The driver would transmit host-supplied 802.11 frames. Combined with monitor RX,
   this is the complete Tier-1 primitive (`monitor` + `injection`) that this whole catalog is scored on.

Malinen's work did not stop at the driver. The AP-management code grew into **`hostapd`** (user-space AP
daemon, copyright from 2002, [w1.fi/hostapd](https://w1.fi/hostapd/)) and the client-side authentication
logic into **`wpa_supplicant`** — both of which became *the* Linux/BSD reference implementations and ship
on effectively every modern system. So the same person and codebase that first exposed monitor+injection
on Prism2 also wrote the WPA supplicant now running on billions of devices. The Prism2 Host AP driver is
listed among `hostapd`'s original supported drivers, alongside MadWifi and, later, mac80211
([Wikipedia: hostapd](https://en.wikipedia.org/wiki/Hostapd)).

### Contemporary HostAP commands (historical; deprecated Wireless-Extensions era)

```sh
# Load the driver (PCMCIA / PCI / PLX-bridged PCI variants)
modprobe hostap_cs      # or hostap_pci / hostap_plx

# Flash / update station firmware on the card (loadable HFA384x firmware)
prism2_srec -f wlan0 pk010101.hex   # primary + station S-record images

# Modes via Wireless Extensions
iwconfig wlan0 mode Master          # be an AP (the "Host AP" mode)
iwconfig wlan0 mode Monitor         # raw capture
# Choose the capture framing (Prism2 header vs. bare 802.11)
iwpriv  wlan0 monitor_type 0        # 802.11 frames only
iwpriv  wlan0 monitor_type 1        # prepend Prism2 capture header (signal/noise/rate)
iwpriv  wlan0 monitor 2             # enable monitor with header

# Diagnostics / RID inspection
hostap_diag wlan0
```

## The sibling drivers: wlan-ng and airjack

HostAP was not alone; two other Prism2 codebases defined the pentest/wardriving era:

- **linux-wlan-ng** (AbsoluteValue Systems / Solomon Peachy et al., [linux-wlan.org](http://www.linux-wlan.org/)).
  An earlier, independent Prism2/2.5/3 driver (PCMCIA/PCI/**USB** via `prism2_usb`) whose `wlanctl-ng`
  control interface offered an explicit sniff/capture command — for many people this was the *first* way
  to get raw 802.11 capture on Linux:

  ```sh
  wlanctl-ng wlan0 lnxreq_wlansniff channel=6 enable=true prismheader=true
  ```

- **AirJack** (Mike Lynn / "Abaddon", ~2002). A Prism2 driver focused squarely on **injection**. It
  shipped the attack tools that made 802.11 injection concrete and notorious: `wlan_jack` (deauth flood),
  `essid_jack` (reveal cloaked SSIDs), `monkey_jack` (layer-2 man-in-the-middle by inserting a rogue AP),
  and `kraker_jack`. AirJack is the reason "you can just forge a deauth frame" entered the security
  vocabulary. Its capabilities were later folded into the general-purpose injection stacks (void11,
  and ultimately **aircrack-ng**).

Together with Kismet (the passive IDS/wardriving sniffer that consumed `DLT_PRISM_HEADER` capture) and,
on Windows, NetStumbler, these tools made **Prism2 THE card of the early-2000s wardriving/pentest era**:
cheap, widely available (Senao/EnGenius, D-Link DWL-650, Linksys WPC11, Netgear MA401, Compaq WL110,
Zcomax), open-driver, and — crucially — able to both *hear everything* and *say anything*.

## The counter-example: Agere/Lucent Hermes ("Orinoco")

The other giant 802.11b family of the era was the **Lucent/Agere Hermes** chipset, sold as **WaveLAN**
and then **Orinoco** (Gold/Silver) cards — and, famously, the radio inside the *original Apple AirPort*,
Dell TrueMobile 1150, and Compaq WL110. On Linux it was driven by `orinoco_cs`/`hermes` (Pavel Roskin,
David Gubler, Dominik Brodowski, building on Jean Tourrilhes' WaveLAN work).

Hermes is the instructive contrast:

- **Monitor: yes (with a patch).** Stock firmware had no monitor mode, but the community "**Shmoo**"
  monitor-mode patch to `orinoco_cs` unlocked raw capture. Orinoco was, on Windows, the card NetStumbler
  was practically built around, and a first-class Kismet source on Linux.
- **Injection: essentially no.** The Hermes firmware is a fully closed, opaque proprietary MAC that would
  not transmit arbitrary host-supplied frames. There was no open host-record interface comparable to the
  Prism2 HFA384x, so no equivalent of AirJack/HostAP raw TX ever materialized reliably.

That single asymmetry — **Prism2 could inject, Orinoco basically could not** — is why Prism2 (not the more
common Orinoco) became the pentester's card, and it is the earliest concrete illustration of the thesis
running through this whole catalog: *what you can do with a radio is set by how open its firmware/host
interface is, not by the antenna.* Orinoco is a Tier-1-for-monitor, no-injection part; Prism2 is full
Tier 1.

## From Prism2 to modern mac80211 (how we got the one-liner)

The Prism2-era stack was **Wireless Extensions** (`iwconfig`, `iwpriv`) plus per-driver FullMAC logic. The
capabilities pioneered there were then generalized:

1. **Capture framing standardized.** `DLT_PRISM_HEADER` → **radiotap** (`DLT_IEEE802_11_RADIO`), a
   flexible, extensible per-frame metadata header now used everywhere.
2. **SoftMAC + a common stack.** Around 2007 the kernel gained **mac80211** (a SoftMAC framework) with the
   **cfg80211/nl80211** configuration API, replacing the Wireless-Extensions patchwork. Monitor virtual
   interfaces and **radiotap-framed injection** became first-class, driver-independent features.
3. **The tools followed.** aircrack-ng, `iw`, and `airmon-ng` now express on *any* capable card exactly
   what HostAP/wlan-ng/AirJack expressed only on Prism2:

   ```sh
   # Modern equivalent of "iwconfig wlan0 mode Monitor"
   iw dev wlan0 interface add mon0 type monitor
   ip link set mon0 up
   # or: airmon-ng start wlan0

   # Modern equivalent of the AirJack injection primitive: verify TX injection works
   aireplay-ng --test mon0
   ```

So the everyday incantation "start monitor, test injection, capture with a radiotap header" is a direct,
if much cleaner, descendant of the Prism2/HostAP toolchain. Every firmware-RE SDR later in this catalog
(Nexmon on Broadcom, CSI extractors, ath9k spectral scan) plugs into *this* interface — which exists
because Prism2 proved a commodity client card could be talked into monitor and injection at all.

## Where these sit on the SDR ladder

All records here are **Tier 1** at most: FullMAC 802.11b radios with closed on-chip MAC firmware. They
have **no** CSI export, spectral scan, raw-IQ, or arbitrary-waveform path — do not confuse their
historical importance with SDR depth. Their tier reflects reality: `monitor` (+`injection` for Prism2/GT)
and nothing above it. They belong in the catalog as the **origin** of the software model that the genuine
firmware-RE SDRs exploit, and as a caution: an open *host/driver interface* (Prism2) buys you far more
than a faster but sealed one (Hermes).

## References

- Host AP driver for Intersil Prism2/2.5/3 (Jouni Malinen) — https://w1.fi/hostap/
- hostapd (author Jouni Malinen; supported drivers incl. Host AP) — https://w1.fi/hostapd/
- wpa_supplicant — https://w1.fi/wpa_supplicant/
- Prism chipset (history, Intersil→GlobespanVirata→Conexant; packet-capture use; p54) — https://en.wikipedia.org/wiki/Prism_(chipset)
- hostapd (Wikipedia; Host AP among supported drivers) — https://en.wikipedia.org/wiki/Hostapd
- linux-wlan-ng (AbsoluteValue Systems) — http://www.linux-wlan.org/
- aircrack-ng (modern injection lineage / compatibility) — https://www.aircrack-ng.org/
- Linux wireless (mac80211 / cfg80211 / nl80211) — https://wireless.wiki.kernel.org/
- Cross-refs: [../../docs/history-timeline.md](../../docs/history-timeline.md), [../../docs/glossary.md](../../docs/glossary.md), [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md)
