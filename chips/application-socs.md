# Application SoCs with Integrated Wi-Fi (SBC / TV-box / Router-class SoCs)

> **The one rule for this whole page:** an application processor (Amlogic S905, Rockchip RK3588, an i.MX8, a Raspberry Pi's BCM2711) **almost never contains a Wi-Fi radio.** The Wi-Fi is a *separate die* — either a chip soldered next to the SoC, or a Broadcom/Cypress/Realtek/NXP die inside an AMPAK/USI/AzureWave module wired over SDIO/PCIe. **The SDR tier of the board is the tier of that Wi-Fi die, nothing more.** So every record here is scored by its die and cross-references the die's own catalog entry. We invent **no** new capabilities for a SoC — a Pi is interesting for SDR only because it carries a `broadcom-bcm43455c0`.

This is the "boards you already own" page. It answers: *I have this SBC / TV box — can its Wi-Fi do monitor / CSI / anything?* Usually the honest answer is **Tier 1 (monitor+inject) if you're lucky, Tier 0 if the vendor firmware is locked**, with exactly one bright spot — the Raspberry Pi, whose CYW43455 is the reference Nexmon platform.

See also: [broadcom-cypress.md](broadcom-cypress.md) (the Pi/AP6xxx dies), [mediatek-ralink.md](mediatek-ralink.md) (TV-SoC combos), [router-ap-socs.md](router-ap-socs.md) (IPQ/MT76xx integrated-radio routers), [other-vendors.md](other-vendors.md) (WiLink, NXP/Marvell, XRadio, AMPAK integrator note), and the walkthrough [../docs/walkthroughs/bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md).

---

## How to read a board's Wi-Fi

1. **Find the Wi-Fi part, not the SoC.** `lspci`/`dmesg | grep -i -E 'brcmfmac|wl|mwifiex|moal|rtl|xradio|8189|cyw'`, read the FCC ID on the module can, or check the board's schematic. The silkscreen usually reads `AP6256`, `RTL8189FTV`, `IW416`, `XR829`, etc.
2. **AP6xxx / USI / Fn-Link / AzureWave / Murata are *packages*, not silicon.** An `AP6256` is a Cypress `CYW43456`-class die; an `AP6275P` is a Broadcom `BCM43752`; an `AP6398S` is a `BCM4359`. Map the module to its die (see the AMPAK integrator note in [other-vendors.md](other-vendors.md)), then look the die up.
3. **Score by the die.** A board carrying a `CYW43455` inherits Tier 4 *potential*; a board carrying an `XR829` is stuck at Tier 0–1 because the die's firmware is closed and unreversed.
4. **But firmware lock still bites.** A TV box may carry a perfectly nexmon-able die yet run a signed, locked vendor image — effectively Tier 0 until you get root and swap the firmware blob.

---

## Master pairing table

| Platform / board family | Application SoC | Typical Wi-Fi part | Underlying die → catalog id | Bus | Best rung (as-shipped) | Repurpose notes |
|---|---|---|---|---|---|---|
| **Raspberry Pi 4 / 400 / CM4** | BCM2711 | on-board **CYW43455** | `broadcom-bcm43455c0` | SDIO | **Tier 4** | **The** Nexmon/`nexmon_csi` platform — monitor, injection, CSI @80 MHz *verified*; arbitrary-IQ *reported* |
| **Raspberry Pi 5 / CM5** | BCM2712 | on-board **CYW43455** | `broadcom-bcm43455c0` | SDIO | Tier 4 (die) | Same die as Pi 4; Nexmon builds for the 6.x kernel exist but are less battle-tested → *reported* |
| **Raspberry Pi 3B+ / CM3+** | BCM2837B0 | **CYW43455** | `broadcom-bcm43455c0` | SDIO | Tier 4 | Same die/story as Pi 4 |
| **Raspberry Pi 3B / Zero W / CM3** | BCM2837 / BCM2835 | **BCM43438 / BCM43430a1** | `broadcom-bcm43438` / `broadcom-bcm43430` | SDIO | Tier 1 | 1×1 11n; Nexmon monitor+inject only |
| **Raspberry Pi Zero 2 W** | BCM2710A1 | **BCM43436b0** | `broadcom-bcm43436` | SDIO | Tier 1 | Nexmon monitor+inject (`9_88_4_65`) |
| **Amlogic S905 / S9xx TV boxes** | S905X2/3/4, S912, S905Y4 | AP6xxx, RTL8189FTV, **W155S1**, on-die W1/W2 | `broadcom-bcm43455c0` / `realtek-*` / `amlogic-w2` | SDIO | Tier 0–1 | Locked TV firmware ⇒ often Tier 0; ODROID/Khadas/Armbian expose monitor if die allows |
| **Rockchip RK3399 SBCs** | RK3399 | **AP6256 / AP6255 / AP6398S** | `broadcom-bcm43455c0` / `broadcom-bcm4359` | SDIO | Tier 1 | AP6256 = CYW43456-class → `brcmfmac`; Nexmon *theoretically* applicable, not standard |
| **Rockchip RK3588(S) SBCs** | RK3588 / RK3588S | **AP6275P**, AIC8800, RTL8852BE | `broadcom-*` (BCM43752) / vendor | SDIO/PCIe | Tier 1 | BCM43752 Wi-Fi 6 die has **no** public Nexmon port; AIC8800 vendor-driver only |
| **NXP i.MX 8M / 8M Plus / Mini** | i.MX8MP etc. | **88W8987 / IW416 / IW612 / 88W9098** | `marvell-88w8897` / `nxp-iw416` / `nxp-iw61x` / `nxp-88w9098` | SDIO/PCIe | Tier 1 | `mwifiex`/`moal` net-monitor; 88W8897 line RE'd by Project Zero |
| **TI Sitara AM335x/437x/57x/64x** | AM3358 etc. | **WL1837MOD / WL1835MOD** | `ti-wl18xx` (older: `ti-wl12xx`) | SDIO | Tier 1 | Open `wlcore` mac80211 monitor — verified; closed FW blob |
| **Allwinner sunxi (H3/H5/H6/H616/A64…)** | H616, H6, A64 | **XR829 / XR819**, RTL8189FTV, RTL8723DS, AP6256 | `allwinner-xr829` / `realtek-*` / `broadcom-*` | SDIO | Tier 0–1 | XRadio parts closed + weak, no CSI/Nexmon; Realtek dongles do monitor |
| **MediaTek smart-TV SoCs** | MT58xx/MT96xx (Pentonic) | integrated **MT7668 / MT7663**-class | `mediatek-mt7663` / MT7668 (see [mediatek-ralink.md](mediatek-ralink.md)) | on-die | Tier 0–1 | Locked TV firmware; die can monitor but path rarely exposed |

**Rule of thumb:** on this whole page, only the **Raspberry Pi row** clears Tier 1, and only because someone already did the firmware RE (Nexmon) on its exact die.

---

## Raspberry Pi — the exception that proves the rule

The BCM27xx application processors (BCM2711 on the Pi 4, BCM2712 on the Pi 5) have **no radio**. Every Wi-Fi-capable Pi solders a Cypress/Infineon combo next to the SoC:

- **Pi 3B+, 4, 400, CM4 → CYW43455** (`broadcom-bcm43455c0`) — Cortex-R4 + D11, the flagship Nexmon target. Monitor, injection, `nexmon_csi` up to 80 MHz, and the WiSec'17 arbitrary-IQ/reactive-jamming work all run here. **This is the cheapest genuinely-SDR-ish Wi-Fi you can buy.**
- **Pi 3B, Zero W, CM3 → BCM43438 / BCM43430a1** (`broadcom-bcm43438` / `broadcom-bcm43430`) — 1×1 11n, Nexmon monitor+inject only.
- **Pi Zero 2 W → BCM43436b0** (`broadcom-bcm43436`).
- **Pi Pico W → CYW43439** (`cypress-cyw43439`) — MCU, not an application SoC, but same family.

### `nexmon_csi` on a Pi 4 (verified path)

```bash
# On Raspberry Pi OS (kernel 5.4 / 5.10 branches are the well-trodden ones)
git clone https://github.com/seemoo-lab/nexmon_csi.git
cd nexmon_csi
# set up the toolchain / build (see repo README for the exact branch matching your firmware)
source setup_env.sh          # from the nexmon base repo
make                          # patches firmware 7_45_189 for the bcm43455c0
make install-firmware         # flashes the patched brcmfmac blob

# Configure a capture: channel 36, 80 MHz, 1 core, 1 spatial stream
mcp -C 1 -N 1 -c 36/80 | tr -d '\n' ; echo      # (older) or:
makecsiparams -c 36/80 -C 1 -N 1                 # emits base64 params
nexutil -Iwlan0 -s500 -b -l34 -v<PARAMS_FROM_ABOVE>
ip link set wlan0 up
tcpdump -i wlan0 dst port 5500 -w csi.pcap       # CSI arrives as UDP to :5500
```

Parse `csi.pcap` with **CSIKit** (`pip install csikit`) — see [../projects/csi-toolchains.md](../projects/csi-toolchains.md) and the walkthrough [../docs/walkthroughs/nexmon-csi-to-usable-csi.md](../docs/walkthroughs/nexmon-csi-to-usable-csi.md).

**Pi 5 caveat:** the Pi 5 carries the *same* CYW43455 die, so the capability ceiling is identical, but the stock image ships a newer kernel/`brcmfmac`. Nexmon community builds targeting the 6.x kernel exist and are improving; treat CSI on the Pi 5 as **reported**, monitor/inject as workable. If CSI matters and you want zero friction, use a **Pi 4**.

> **TX safety:** monitor and CSI are receive-only and legal to run. The Tier-4 *arbitrary-waveform / reactive-jamming* capability the die inherits from the WiSec'17 work is **transmit** — it radiates non-standard energy in 2.4/5 GHz and is illegal outside a shielded enclosure / licensed test setup. Do not key the PA on the air. See [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md).

---

## Amlogic (S905 / S9xx TV boxes and SBCs)

Amlogic Meson SoCs power the cheap Android-TV-box ecosystem and boards like **ODROID-C2/C4/N2**, **Khadas VIM** series, and **Radxa Zero**. Wi-Fi is either:

- an **external SDIO module** — `AP6xxx` (Broadcom/Cypress dies), `RTL8189FTV`/`RTL8723DS` (Realtek), or the Amlogic-branded **W155S1** module can — or
- **Amlogic's own in-package combo**, the **W1** (Wi-Fi 5) / **W2** (Wi-Fi 6, `amlogic-w2`) families in newer reference designs (S905W2, S905Y4, A311D2 boards).

**Reality:** consumer TV boxes run **locked, signed vendor firmware** — effectively Tier 0 until rooted and re-imaged (Armbian/CoreELEC). Once on a mainline-ish kernel with `brcmfmac`, a 43455-class module *could* accept Nexmon, but this is not a beaten path. The Amlogic W1/W2 dies are closed vendor-driver parts with no public monitor+CSI route. Score any given board by **which module can it actually carries** — cross-reference `broadcom-bcm43455c0`, the Realtek parts in [realtek.md](realtek.md), or `amlogic-w2`.

## Rockchip (RK3399 / RK3588 SBCs)

Rockchip ships **no Wi-Fi silicon of its own** — every RK-based SBC pairs an external module (see `rockchip-realtek-combo-pairing` in [other-vendors.md](other-vendors.md)):

- **RK3399** (RockPro64, NanoPi M4/NEO4, Khadas Edge, Orange Pi 4): commonly **AP6256** (Cypress CYW43456-class, 1×1 11ac), **AP6255**, or **AP6398S** (`BCM4359`, 2×2). AP6256 rides `brcmfmac`, so Nexmon is *theoretically* portable — but nobody ships a turnkey RK3399 `nexmon_csi`. Tier 1 as-shipped.
- **RK3588 / RK3588S** (Orange Pi 5, Radxa Rock 5A/5B, Khadas Edge2, NanoPC-T6): **AP6275P** (Broadcom **BCM43752** Wi-Fi 6), **AIC8800** (AICSemi), or PCIe **RTL8852BE**. The BCM43752 Wi-Fi 6 die has **no** public Nexmon port; AIC8800 is vendor-driver-only. Tier 1, sometimes Tier 0.

If you need CSI on a Rockchip board, the pragmatic move is to **ignore the built-in module and plug in a USB adapter** with a known-good die (an Alfa `RTL8812AU` for monitor/inject, or an Intel AX210 via `ax-csi`) — see [realtek.md](realtek.md) and the Intel path.

## NXP i.MX (with NXP / Marvell Wi-Fi)

i.MX 8M / 8M Plus / 8M Mini application processors (NXP EVKs, **Variscite**, **Toradex Verdin/Colibri**, **Compulab**, **phyBOARD**) carry an NXP/Marvell "Avastar"-lineage combo on the SoM: **88W8987**, **IW416** (`nxp-iw416`), **IW612** tri-radio (`nxp-iw61x`), or **88W9098** (`nxp-88w9098`, Wi-Fi 6). These run the `mwifiex` (mainline) or `moal`/`mlan` (NXP out-of-tree) drivers, whose firmware lives in `linux-firmware/nxp`. Net-monitor works; the 88W8897/89xx line was famously reverse-engineered by **Project Zero** (see [other-vendors.md](other-vendors.md)), but there is **no public CSI/Nexmon-equivalent** for these parts — Tier 1. Cross-reference `marvell-88w8897` / `marvell-mwifiex-878x`, `nxp-iw416`, `nxp-iw61x`, `nxp-88w9098`.

## TI Sitara (with WiLink WL18xx)

TI **Sitara** application processors (AM335x, AM437x, AM57x, AM64x) — the **BeagleBone** family (via the WL1835 cape), TI EVMs, industrial gateways — pair the **WiLink 8** module (**WL1835MOD / WL1837MOD**, `ti-wl18xx`; older Sitara used **WL12xx**, `ti-wl12xx`). WiLink's win is the **open `wlcore` mac80211 driver**: standard `iw dev wlanX interface add monX type monitor` works, so **monitor is verified**. The firmware blob itself is closed and there's no CSI/spectral path — Tier 1.

## Allwinner (sunxi)

Allwinner H3/H5/H6/H616/H618/A64/A133 boards (Orange Pi, Banana Pi, Pine A64, various Armbian targets) pair one of:

- **XRadio XR819 / XR829** (`allwinner-xr829`) — Allwinner's own SDIO combo, **closed, weak, and infamously buggy** in mainline; no monitor-quality path, no CSI, no Nexmon. Tier 0–1.
- **Realtek RTL8189FTV / RTL8723DS** — SDIO Realtek parts; monitor/inject as per [realtek.md](realtek.md). Tier 1.
- **AMPAK AP6xxx** — Broadcom/Cypress dies on higher-end boards; score by die.

Practically, sunxi Wi-Fi is a "get on the network" radio, not an SDR. For sensing, add a USB dongle.

## MediaTek smart-TV SoCs

MediaTek's TV SoC lines (Pentonic **MT58xx/MT96xx**, older MT5xxx) integrate a MediaTek connectivity combo of the **MT7668 / MT7663**-class (see the combo rows in [mediatek-ralink.md](mediatek-ralink.md)). The die *can* do `mt76`-style monitor/inject, but consumer TVs run **locked firmware** that never exposes it — treat as Tier 0 unless rooted onto a mainline `mt76` stack, then Tier 1. (Distinct from MediaTek's `Filogic` **router** SoCs, which are covered in [router-ap-socs.md](router-ap-socs.md).)

---

## Bottom line

- **Want SDR-ish Wi-Fi on a cheap board today?** Buy a **Raspberry Pi 4** and run `nexmon_csi`. Everything else on this page is Tier 0–1.
- **Have some other SBC/TV box?** Identify the *module*, map it to its *die*, and read that die's entry. The SoC name (S905, RK3588, i.MX8) tells you nothing about SDR capability.
- **Locked TV/box firmware** can drop an otherwise-capable die to Tier 0 — rooting + a mainline `brcmfmac`/`mt76`/`mwifiex` stack is the prerequisite to any monitor mode.

## References

- Nexmon framework — https://github.com/seemoo-lab/nexmon
- `nexmon_csi` (CSI on BCM43455c0 etc.) — https://github.com/seemoo-lab/nexmon_csi
- CSIKit post-processing — https://github.com/Gi-z/CSIKit
- Raspberry Pi hardware/config docs — https://www.raspberrypi.com/documentation/computers/configuration.html
- linux-sunxi Wi-Fi (XR819/XR829, Realtek, AP6xxx pairings) — https://linux-sunxi.org/Wifi
- Linux `wl18xx` / `wlcore` (WiLink 8) driver — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/ti/wl18xx
- NXP Wi-Fi firmware in linux-firmware — https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/nxp
- Armbian (Amlogic/Rockchip/Allwinner boards, driver/module docs) — https://www.armbian.com/
- Radxa Rock 5 (RK3588, AP6275P) docs — https://docs.radxa.com/en/rock5/rock5b
- Pine64 RockPro64 (RK3399, AP6256) wiki — https://wiki.pine64.org/wiki/RockPro64
- WiSec'17 "Massive Reactive Smartphone-Based Jamming" (Pi/Nexus arbitrary-IQ) — https://dl.acm.org/doi/10.1145/3098243.3098254
