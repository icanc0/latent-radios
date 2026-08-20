# The Linux Wireless Stack, and Where the SDR-ish Hooks Live

A foundational reference for **Latent Radios**. Every capability this catalog tracks — monitor, injection, CSI, spectral scan, raw IQ — is reached by climbing *down* through the Linux wireless stack until you hit the point where the chip's firmware stops cooperating, and then either finding a hook the kernel already exposes (ath9k spectral, radiotap injection) or patching across the firmware boundary (Nexmon). To know *where* a hook can live, you first need to know what each layer is responsible for and, crucially, where the software/firmware split falls. That split is the whole game.

This page maps the layers, explains **SoftMAC vs FullMAC** and why it decides how much SDR-ish surface you get for free, and pins down exactly where monitor mode, radiotap, injection, the ath9k debugfs spectral/CSI hooks, and Nexmon attach.

See also: [firmware reversing](../docs/firmware-reversing.md) for what lies below the boundary, [monitor / injection support by chip](../chips/monitor-injection-support.md) for which parts actually work, and the [glossary](../docs/glossary.md) for term definitions.

---

## The layer cake (diagram-in-prose)

Picture the stack as a vertical stack of boxes. Data and control flow up and down through it; the horizontal lines are ABIs/boundaries where one team's code hands off to another's.

```
┌─────────────────────────────────────────────────────────────────────┐
│  USERSPACE                                                            │
│    iw            wpa_supplicant        hostapd        aircrack-ng     │
│    (config)      (station/EAP)         (AP/auth)      (monitor tools) │
│         │              │                   │               │         │
│         └──────────────┴─────────┬─────────┴───────────────┘         │
│                                  │  libnl (Netlink sockets)          │
╞══════════════════════════════ nl80211 ══════════════════════════════╡  ← userspace/kernel ABI
│  KERNEL                          │                                    │
│                              cfg80211                                 │  ← the registration/config core
│                   (every wireless driver registers here)             │
│                    │                              │                   │
│            ┌───────┴────────┐            ┌────────┴─────────┐         │
│            │   mac80211     │            │  (no mac80211)   │         │
│            │  SoftMAC MLME  │            │                  │         │
│            │  in software   │            │                  │         │
│            └───────┬────────┘            │                  │         │
│         SoftMAC drivers                  │   FullMAC drivers          │
│      ath9k  iwlwifi  b43  rtl8xxxu       │  brcmfmac  mwifiex  ...    │
│            │                              │                  │        │
╞═══════════════════════ THE FIRMWARE BOUNDARY ════════════════════════╡  ← host/chip ABI (opaque)
│  ON-CHIP FIRMWARE / ucode / PHY / RF front-end                       │
│    d11 MAC engine · baseband DSP · ADC/DAC · mixer · PA/LNA          │
└─────────────────────────────────────────────────────────────────────┘
```

Two horizontal lines matter most:

- **nl80211** — the userspace/kernel ABI. Clean, documented, netlink-based. Not where the interesting SDR access lives, but it's how you *drive* the interesting bits (set monitor mode, tune a channel, start a spectral scan).
- **The firmware boundary** — the host/chip ABI. Opaque, vendor-defined, usually undocumented. This is the line reverse engineering fights over. **How high that line sits (how much the firmware hides) is exactly what SoftMAC vs FullMAC decides.**

---

## Layer by layer

### Userspace: `iw`, `wpa_supplicant`, `hostapd`

The tools you type at or that run as daemons. `iw` is the modern configuration/diagnostic CLI (it replaced the old `iwconfig`/WEXT tooling). `wpa_supplicant` handles station-side association and the 4-way handshake/EAP; `hostapd` is its AP-side counterpart (beaconing, authentication). Monitor-mode capture tools (`airodump-ng`, `tcpdump`, `wireshark`) and injection tools (`aireplay-ng`, `packetspammer`, scapy) also live here.

They all talk to the kernel over **nl80211** via **libnl** (netlink sockets). The legacy **Wireless Extensions (WEXT / `iwconfig`)** ioctl API still exists for ancient drivers but is frozen and deprecated — nl80211 is the path everything modern uses. SDR relevance: userspace is where you *initiate* every capability, but it holds none of the mechanism itself.

### `nl80211` — the userspace ↔ kernel API

A netlink family: a structured, extensible message protocol between userspace and `cfg80211`. Commands like `NL80211_CMD_SET_INTERFACE` (switch a netdev to `NL80211_IFTYPE_MONITOR`), `NL80211_CMD_SET_CHANNEL`, `NL80211_CMD_TRIGGER_SCAN`, and vendor-specific commands (`NL80211_CMD_VENDOR`) cross here. Some research CSI/telemetry paths (and some FullMAC vendor extensions) surface data back to userspace as **vendor netlink events** or over a **connector/generic-netlink** socket rather than through the normal data path.

### `cfg80211` — the configuration and registration core

The in-kernel heart of the stack. **Every** wireless driver — SoftMAC or FullMAC — registers a `struct wiphy` with cfg80211. It owns the regulatory database (channel/power/DFS rules), interface-type management, the scan/connect state machine as seen from userspace, and it translates nl80211 requests into driver callbacks. It does **not** implement 802.11 itself. SDR relevance: cfg80211 is what decides whether a given interface type (monitor) is even *permitted*, and it enforces the regulatory limits that any TX experiment must respect ([RF safety and legal](../docs/rf-safety-and-legal.md)).

### `mac80211` — the SoftMAC framework (present for some drivers, absent for others)

A large kernel library that implements the 802.11 **MLME** (management/link-layer) and much of the MAC in *software on the host CPU*: association, authentication, sequencing, rate control, aggregation bookkeeping, fragmentation, power-save, and — importantly for us — **monitor-interface handling, radiotap parsing/generation, and injection**. Drivers that use mac80211 are called **SoftMAC** drivers. mac80211 sits on top of cfg80211 and presents a uniform `ieee80211_ops` interface downward to the driver.

Because so much of the MAC is *in open kernel source* here, SoftMAC is where the SDR-ish surface is richest: the code that builds/receives raw frames is code you can read, hook, and patch without touching firmware.

### The driver + the firmware boundary

The driver moves frames and commands between the kernel and the chip over PCIe/SDIO/USB, and loads the firmware blob (e.g. `brcmfmac43455-sdio.bin`, iwlwifi `.ucode`, ath9k's on-chip code/EEPROM). Below the driver is the **firmware boundary**: the d11/MAC engine, baseband DSP, converters, and RF front-end. Everything above the boundary is (in principle) inspectable kernel source; everything below is vendor silicon + blob. The catalog's `firmware.openness` rates how tractable that blob is per part.

---

## Layer → responsibility → SDR relevance

| Layer | What it does | SDR relevance |
|---|---|---|
| **Userspace tools** (`iw`, `wpa_supplicant`, `hostapd`, aircrack-ng, scapy) | Configure interfaces, run association/AP daemons, capture and craft frames | Where you *initiate* monitor/injection/scan; holds none of the mechanism |
| **`nl80211`** (+ libnl) | Netlink control ABI: set iftype, channel, trigger scan, vendor cmds/events | The knob you turn to arm a capability; research telemetry often flows back as vendor-netlink/connector events |
| **`cfg80211`** | Driver registration (`wiphy`), regulatory DB, interface-type policy, scan/connect state | Decides whether monitor is *allowed*; enforces reg limits on any TX experiment |
| **`mac80211`** (SoftMAC only) | Software MLME/MAC: assoc, rates, aggregation, **monitor iface, radiotap, injection** | **Richest free surface** — the raw-frame RX/TX path is open kernel source you can hook/patch |
| **SoftMAC driver** (ath9k, iwlwifi, b43, rtl8xxxu, mt76…) | Host half of the MAC/PHY glue; DMA rings; loads firmware; **debugfs hooks** | Where per-chip telemetry taps attach — e.g. ath9k spectral/CSI debugfs, iwlwifi CSI firmware path |
| **FullMAC driver** (brcmfmac, mwifiex, qca wcn…) | Thin shim: forwards cfg80211 ops to firmware over a control channel | Little exposed by default; capability depends on firmware — the Nexmon target |
| **Firmware boundary** | Host/chip ABI (ioctl/IOVAR/command ring) — opaque, vendor-defined | The line reverse engineering crosses; how much it hides = SoftMAC vs FullMAC |
| **On-chip firmware / ucode / PHY / RF** | d11 MAC engine, baseband DSP, ADC/DAC, mixer, PA/LNA — the actual radio | The true SDR lives here; reachable only by patching (Nexmon, b43, custom iwlwifi ucode) |

---

## SoftMAC vs FullMAC — the split that decides everything

The single most useful question about any Wi-Fi part in this catalog is: **does its driver use mac80211 (SoftMAC) or does it bypass mac80211 and talk cfg80211 directly (FullMAC)?**

- **SoftMAC** — the MLME/MAC runs on the *host* in `mac80211`. The chip firmware handles only the hard-real-time PHY/lower-MAC bits. Because the frame-building, monitor, and injection logic is open kernel C, SoftMAC parts expose the most SDR-ish surface *for free* and are the friendliest to patch. Classic SoftMAC drivers: **ath9k**, **iwlwifi**, **b43/b43legacy**, **rtl8xxxu / rtl8187**, **mt76**, **carl9170**, **p54**.
- **FullMAC** — the MLME/MAC runs *inside the chip firmware*. The driver is a thin translator that forwards cfg80211 requests down a command channel. The host sees far less; monitor and injection exist only if the firmware chooses to implement them. FullMAC drivers: **brcmfmac** (Broadcom/Cypress), **mwifiex** (Marvell), **qtnfmac**, most mobile and many USB parts, and `wilc`/`qca` FMAC families.

Why it matters, concretely:

- **Monitor mode** is a first-class `mac80211` interface type — on SoftMAC it usually "just works." On FullMAC it depends entirely on firmware support, which is often absent or crippled. This is why so much reverse-engineering effort (Nexmon) targets FullMAC Broadcom parts: the capability that's free on ath9k has to be *added* to a bcm43xx blob.
- **Injection** is implemented in `mac80211`'s TX path (it interprets a radiotap header on the outgoing frame). SoftMAC → the injection code is present and hookable. FullMAC → you're at the firmware's mercy.
- **CSI / spectral** telemetry is computed in the baseband either way, but SoftMAC drivers give you a place to *land* it in open source (a debugfs file, a relay channel) without a firmware patch. On FullMAC you generally must patch firmware to exfiltrate it.

Rule of thumb for this catalog: **SoftMAC parts tend to sit higher on the SDR ladder out of the box; FullMAC parts need a firmware patch to get there.** (Caveats exist — iwlwifi is SoftMAC but firmware-heavy, so its CSI required custom ucode; ath10k/ath11k push more MAC into firmware than ath9k despite still using mac80211.)

---

## Where monitor mode, radiotap, and injection actually live

**Monitor mode.** A monitor interface is `NL80211_IFTYPE_MONITOR`, created via nl80211 (`iw dev wlan0 interface add mon0 type monitor`, or `iw wlan0 set monitor`). For SoftMAC, `mac80211` implements the monitor netdev: it delivers received frames up with a **radiotap** header prepended and (per configured monitor flags) can pass otherwise-filtered frames. For FullMAC, the driver must ask its firmware to enter a promiscuous/monitor state — often unsupported.

**Radiotap.** The de-facto header format (defined at radiotap.org) prepended to 802.11 frames on capture and interpreted on injection. It carries PHY metadata — channel/frequency, signal (dBm antenna signal), rate/MCS, timestamp, flags, and antenna info — as a self-describing, extensible bitmap of present fields. In-kernel it is produced/parsed by `mac80211` (RX radiotap assembly in the monitor path; TX radiotap parsing in `ieee80211_parse_tx_radiotap()` on the inject path). Vendor namespace fields in radiotap are one channel some research CSI tools use to smuggle per-subcarrier data alongside a captured frame.

**Injection.** You inject by writing a radiotap-prefixed 802.11 frame to a monitor interface. `mac80211` parses the radiotap to pull the requested TX parameters (rate/MCS, retries, no-ack, etc.), strips it, and hands the raw 802.11 frame to the driver's TX path. Whether the chip honors the requested rate/timing is firmware-dependent, but the *mechanism* is open kernel code on SoftMAC. The canonical documentation is the kernel's **mac80211 injection** page. Injection needs the interface in monitor (or a monitor VIF alongside a managed one) and appropriate regulatory/permission state.

Everything in this section is a **SoftMAC** story. The equivalent on a FullMAC part is "hope the firmware exposes it, or patch it in."

---

## Where the ath9k debugfs spectral / CSI hooks attach

**ath9k** (Atheros 802.11n, `AR92xx/AR93xx/AR95xx`) is the reference example of a driver that hangs an SDR-ish telemetry tap directly off the SoftMAC driver via **debugfs** — no firmware patch required. This is why it recurs throughout the catalog as the easy on-ramp to tiers 2–3.

**Spectral scan (tier 3).** The chip's baseband has an FFT/spectral engine (built for DFS radar detection and rate adaptation). ath9k re-tasks it and dumps the raw FFT bins to userspace through debugfs files under the phy:

```
/sys/kernel/debug/ieee80211/phyN/ath9k/spectral_scan_ctl     # arm: "background"/"manual"/"chanscan"/"trigger"/"disable"
/sys/kernel/debug/ieee80211/phyN/ath9k/spectral_count        # how many samples
/sys/kernel/debug/ieee80211/phyN/ath9k/spectral_short_repeat
/sys/kernel/debug/ieee80211/phyN/ath9k/spectral_bins
/sys/kernel/debug/ieee80211/phyN/ath9k/spectral_scan0        # binary FFT sample stream (read this)
```

Typical flow: `echo chanscan > spectral_scan_ctl`, then trigger a scan (e.g. `iw dev wlan0 scan`), then read the binary samples from `spectral_scan0` and parse the per-bin magnitudes (the `fft_eval` / `spectral_scan` tooling decodes them). The exact `phyN` index and whether the mount is at `/sys/kernel/debug` depends on your system (`mount -t debugfs none /sys/kernel/debug` if unmounted). This tap lives entirely in the **driver**, above the firmware boundary — that's what makes it robust. See [tier-3 spectral verification](../docs/verification-tier3-spectral.md).

**CSI (tier 2).** Vanilla ath9k does **not** export per-subcarrier CSI through debugfs. CSI on this family comes from the **Atheros CSI Tool** (Yaxiong Xie / Mo Li, NTU), which patches the ath9k *driver plus on-chip code* to capture the channel estimate the receiver already computes and deliver it to userspace. It is the SoftMAC-driver-modification path (analogous in spirit to what Nexmon does for FullMAC), not a stock debugfs hook. The comparable Intel path is the **Linux 802.11n CSI Tool** (Halperin et al.) on the Intel 5300, which needs *custom iwlwifi firmware* and ships CSI up a connector-netlink socket — a reminder that even a SoftMAC part (iwlwifi) can require a firmware swap when the telemetry lives below the boundary. See [CSI toolchains](../projects/csi-toolchains.md) and [tier-2 CSI verification](../docs/verification-tier2-csi.md).

Takeaway: **spectral** is a stock, driver-level debugfs hook (no patch); **CSI** on ath9k/Intel needs a driver+firmware modification. Both attach at or just below the SoftMAC driver — never in mac80211 itself.

---

## How Nexmon slots under `brcmfmac`

Broadcom/Cypress parts (bcm43xx, the Raspberry Pi's bcm43430/43455, many phones) are **FullMAC** and driven by **brcmfmac**. By the split above, that means monitor/injection/CSI are firmware decisions — and the stock firmware mostly says no. **Nexmon** (SEEMOO Lab, TU Darmstadt) is the framework that changes the firmware's mind.

Where it sits:

- Nexmon does **not** replace brcmfmac and does **not** live in mac80211 (there is no mac80211 in this path). It **patches the Broadcom firmware blob** — the ARM firmware and the **d11 ucode** on the MAC engine — that brcmfmac loads at boot. The patched `.bin` is dropped in place of the vendor blob; brcmfmac loads it unmodified-driver-side.
- The patches *add* the capability the blob lacked: a working **monitor mode** (frames pushed up as radiotap), **frame injection**, and, via **nexmon_csi**, extraction of per-subcarrier **CSI** from the baseband. Because there's no SoftMAC layer to interpret radiotap, the patched firmware itself has to assemble/parse it and route frames to a monitor-capable interface.
- Control and data cross the existing **firmware boundary** using brcmfmac's normal channels — Broadcom **IOVARs/ioctls** (and in some configs a UDP/netlink exfil path for CSI). So userspace still uses familiar `iw`/`ioctl` idioms; the new behavior is entirely below the boundary. Nexmon's toolchain also provides the patching framework, the `libnexmon`/`nexutil` userspace glue, and a b43-adjacent ucode assembler for the d11 core.

In stack terms: **Nexmon reaches *below* the firmware boundary and rebuilds the missing MAC features inside the blob, so that a FullMAC part gains the monitor/injection/CSI surface that a SoftMAC part gets for free above the boundary.** That is the whole reason a Raspberry Pi's Wi-Fi can be coaxed into CSI sensing at all. See [firmware reversing](../docs/firmware-reversing.md), the Nexmon project notes, and [monitor / injection support](../chips/monitor-injection-support.md) for which Broadcom parts are actually covered.

---

## Practical: which stack am I on?

```bash
# What driver backs the interface?
readlink /sys/class/net/wlan0/device/driver        # -> .../ath9k, .../brcmfmac, .../iwlwifi ...
ethtool -i wlan0                                    # driver: field

# SoftMAC? Then mac80211 is loaded and the phy shows up under ieee80211.
lsmod | grep mac80211
ls /sys/kernel/debug/ieee80211/                     # phyN dirs exist for mac80211 drivers

# Does the driver expose debugfs telemetry (ath9k spectral)?
ls /sys/kernel/debug/ieee80211/phy0/ath9k/          # spectral_scan_ctl, spectral_scan0 ...

# Can it even do monitor?
iw phy phy0 info | sed -n '/Supported interface modes/,/Band/p'   # look for "* monitor"
```

- Driver is **ath9k / iwlwifi / b43 / rtl8xxxu / mt76** and `mac80211` is loaded → **SoftMAC**: monitor/injection likely free; look for driver debugfs taps.
- Driver is **brcmfmac / mwifiex** and `mac80211` is *absent* → **FullMAC**: capability depends on firmware; Nexmon (Broadcom) is the way up.

---

## References

- Linux kernel — mac80211 subsystem documentation: <https://wireless.wiki.kernel.org/en/developers/documentation/mac80211>
- Linux kernel — cfg80211 documentation: <https://wireless.wiki.kernel.org/en/developers/documentation/cfg80211>
- Linux kernel — nl80211 API: <https://wireless.wiki.kernel.org/en/developers/documentation/nl80211>
- Linux kernel — mac80211 packet injection: <https://www.kernel.org/doc/html/latest/networking/mac80211-injection.html>
- The Radiotap header format: <https://www.radiotap.org/>
- ath9k spectral scan (kernel wireless wiki): <https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan>
- ath9k driver page: <https://wireless.wiki.kernel.org/en/users/drivers/ath9k>
- Atheros CSI Tool (Yaxiong Xie): <https://wands.sg/research/wifi/AtherosCSI/> and <https://github.com/xieyaxiongflyer/Atheros-CSI-Tool>
- Linux 802.11n CSI Tool, Intel 5300 (Halperin et al.): <https://dhalperi.github.io/linux-80211n-csitool/>
- Nexmon firmware patching framework: <https://github.com/seemoo-lab/nexmon>
- nexmon_csi (CSI extraction on Broadcom/Cypress): <https://github.com/seemoo-lab/nexmon_csi>
- `iw` / nl80211 tooling: <https://wireless.wiki.kernel.org/en/users/documentation/iw>
- hostap (wpa_supplicant / hostapd): <https://w1.fi/>

---

*Foundational reference — no chip records (`modules[]` empty). For the parts these hooks apply to, cross-reference [monitor / injection support](../chips/monitor-injection-support.md), [firmware reversing](../docs/firmware-reversing.md), and the [glossary](../docs/glossary.md).*
