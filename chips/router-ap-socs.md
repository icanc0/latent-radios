# Router / AP SoC Platforms and Their Latent Radios (The OpenWrt Angle)

Home routers, mesh nodes and enterprise access points are the single most *available* carriers of repurposable Wi-Fi silicon. They ship by the tens of millions, land on second-hand markets for a few dollars, and — crucially — a large fraction of them run [OpenWrt](https://openwrt.org), which gives you a mainline Linux `mac80211` stack and open source Wi-Fi drivers on top of the vendor firmware blob. That combination is what turns a `$15` router into a Tier‑1/2/3 latent radio.

This page maps the *SoC/radio platform* layer: which router chips reach which rung of [the SDR ladder](../docs/taxonomy.md) under OpenWrt, and which are dead-ends. It is deliberately platform-centric — the individual PHY/radio dies (QCA9880, MT7915, MT7981, etc.) are catalogued elsewhere; here we care about the *board you can actually buy* and what the driver exposes. See [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) and [../chips/mediatek-ralink.md](../chips/mediatek-ralink.md) for the die-level detail, and [../docs/verification-tier3-spectral.md](../docs/verification-tier3-spectral.md) for how the spectral-scan claims below are validated.

> **The one rule that decides everything:** *the driver, not the chip, sets the tier.* Two boards with identical silicon reach different rungs depending on whether they run `ath10k`/`mt76` (open, `mac80211`) or a Broadcom `wl.ko`/`dhd` FullMAC blob (closed, no monitor). Buy for the driver.

---

## How OpenWrt exposes the radio

OpenWrt boards fall into three driver worlds, and the world determines the ceiling:

| Driver | Vendors / SoCs | mac80211? | Monitor/inject | CSI | Spectral | Ceiling |
|---|---|---|---|---|---|---|
| **ath9k** | AR9xxx SoCs, external AR93xx | yes (SoftMAC) | yes | via Atheros-CSI-Tool | **yes (native FFT)** | **Tier 3** |
| **ath10k** | IPQ4019 integrated; QCA988x/9888/9984 external | yes (FullMAC-ish + mac80211) | yes | Nexmon-style patches | **yes (`spectral_scan_ctl`)** | **Tier 3** |
| **ath11k** | IPQ8074/6018/5018, QCN9074 | yes | yes | reported | **yes (spectral)** | **Tier 3** |
| **ath12k** | IPQ9574, QCN92xx (Wi‑Fi 7) | yes | yes | WIP | spectral WIP | Tier 1→3 (maturing) |
| **mt76** | MT76x0/x2, MT7603/7615/7915, MT7621/7622/7628 integrated, Filogic MT7981/7986/7988 | yes (SoftMAC) | **yes** | reported (mt76 CSI) | limited | Tier 1→2 |
| **brcmfmac / wl / dhd** | Broadcom BCM47xx/BCM49xx router radios | FullMAC blob | **no** | no | no | **Tier 0** |
| **rtlwifi / vendor** | RTL819x integrated | partial | limited | no | no | Tier 0→1 |
| *(none — no radio)* | RTL838x/930x switches, Lantiq/MaxLinear GRX/PRX | — | — | — | — | **N/A** |

The practical takeaway: **Atheros = spectral‑scan gold standard, MediaTek = monitor/inject everywhere plus emerging CSI, Broadcom router silicon = closed and inert, Realtek/Lantiq switch-gateway silicon = literally no radio.**

---

## Qualcomm / Atheros IPQ — the good stuff

The IPQ "Internet Processor" line is the reason people flash OpenWrt for radio work. Most IPQ SoCs carry an *integrated* Atheros Wi-Fi MAC/baseband driven by an open `ath10k`/`ath11k` driver, and Atheros is the one vendor that shipped a documented **spectral scan** (raw per-bin FFT) path all the way from `ath9k`.

### IPQ40xx "Dakota" — IPQ4018 / 4019 / 4028 / 4029
Quad Cortex‑A7 with an **on-die 2×2 802.11ac (5 GHz) + 2×2 802.11n (2.4 GHz)** radio presented to Linux as an `ath10k` device (internal `qca4019`/`qca9888`-class baseband). Under OpenWrt's `ipq40xx` target you get:
- **Monitor + injection** (Tier 1) out of the box via `mac80211`.
- **Spectral scan** (Tier 3): `echo chanscan > /sys/kernel/debug/ieee80211/phyX/ath10k/spectral_scan_ctl` then read `spectral_scan0`, decode with [`FFT_eval`](https://github.com/simonwunderlich/FFT_eval). The [`ath10k-ct`](https://github.com/greearb/ath10k-ct) firmware from Candela improves stability and station counts.

The 4028/4029 are the industrial-temperature siblings; radio-wise identical. This is the cheapest genuinely Tier‑3-capable integrated router SoC. Boards: Fritz!Box 4040, Linksys EA6350v3, GL.iNet B1300, ZyXEL NBG6617.

### IPQ806x — IPQ8064 / 8065
Dual Krait application processor with **no integrated Wi-Fi** — it is a *host* that pairs with external `ath10k` radios (QCA9880/QCA9980/QCA9984, catalogued as `qualcomm-qca9880`). The SoC itself contributes nothing to the RF path; the tier is whatever the mini-PCIe radio you plug in reaches (typically Tier 3 via QCA9880 spectral). Classic boards: Netgear R7500/R7800 (Nighthawk X4/X4S), TP-Link Archer C2600/AD7200, Linksys EA8500.

### IPQ807x "Hawkeye" — IPQ8072 / 8074
Quad/dual Cortex‑A53, **integrated 802.11ax (Wi‑Fi 6)** 4×4+4×4 handled by `ath11k`. OpenWrt's `qualcommax` (formerly `ipq807x`) target gives monitor/injection and **ath11k spectral scan** (Tier 3). This is the highest-throughput integrated Atheros spectral platform in wide circulation. Boards: Netgear RAX120, Xiaomi AX9000, Dynalink DL-WRX36, Zyxel NBG7815.

### IPQ60xx "Cypress" — IPQ6000 / 6010 / 6018
Quad Cortex‑A53, **integrated Wi‑Fi 6** dual-band, `ath11k`. Same monitor/inject/spectral (Tier 3) story as IPQ807x at lower cost and power. Very common in cheap Wi‑Fi 6 routers — Redmi AX5, Cudy, GL.iNet AXT1800/AX1800. One of the best value Tier‑3 targets today.

### IPQ50xx "Maple" — IPQ5018
Dual Cortex‑A53 **Wi‑Fi 6** with an integrated dual-band radio (`ath11k`) and typically a companion **QCN9074** (`ath11k`) for the 6 GHz / additional band. Spectral scan is available on the `ath11k` path (less field-tested than IPQ8074, hence *reported*). Boards: many 2023-era mesh nodes.

### IPQ95xx "Waikiki" — IPQ9574
Quad Cortex‑A73, **integrated Wi‑Fi 7 (802.11be)** driven by `ath12k`. Monitor/injection work; **spectral and CSI in `ath12k` are still maturing** as of 2026, so treat spectral as reported/WIP rather than a shipped feature. The frontier platform for anyone chasing 320 MHz-wide latent-radio capture.

> **Verify, don't assume.** A board advertised as "IPQ8074" may still ship a locked bootloader or a stripped OEM `ath11k` firmware. Confirm the `spectral_scan_ctl` debugfs node exists on *your* OpenWrt build before claiming Tier 3 — the procedure is in [../docs/verification-tier3-spectral.md](../docs/verification-tier3-spectral.md).

---

## MediaTek / Ralink + Filogic — monitor/inject everywhere, CSI emerging

MediaTek's `mt76` is a clean SoftMAC `mac80211` driver, so **monitor mode and frame injection are reliable across the entire family** (Tier 1 baseline). What MediaTek historically lacked was Atheros-grade spectral; that gap is now partly filled by **out-of-tree CSI patches for `mt76` (MT7915 / Filogic)**, which push the newer parts to a *reported* Tier 2.

### Ralink-lineage MIPS
- **MT7620** — MIPS 24KEc with **integrated 2.4 GHz 802.11n**. Monitor/inject supported; older driver generations were flaky, so Tier 1 *reported*. Ubiquitous in `$10` routers.
- **MT7621** — dual-core 1004Kc, the workhorse router SoC, but with **no integrated radio**. It *hosts* `mt76` PCIe/USB radios (MT7603 2.4 GHz + MT7612/MT7615 5 GHz). Tier is set by the companion radio; the SoC itself is Tier 0. Extremely common (hundreds of board models).
- **MT7628 / MT7688** — MIPS 24KEc with **integrated 2.4 GHz 11n** (`mt76`). Reliable monitor/injection (Tier 1). The cheapest MediaTek integrated radio you can buy.

### ARM class
- **MT7622** — Cortex‑A53 with an **integrated 4×4 2.4 GHz 802.11n** radio (`mt76`), usually paired with an **MT7915** for 5 GHz Wi‑Fi 6. The integrated radio is Tier 1; the companion MT7915 is where CSI (Tier 2, reported) lives. Boards: Linksys E8450 / Belkin RT3200 (the beloved cheap Wi‑Fi 6 OpenWrt target).
- **MT7623 / MT7629** — application/gateway SoCs with **no integrated Wi‑Fi**; host external `mt76` radios.

### Filogic (Wi‑Fi 6 / 6E)
- **MT7981 "Filogic 820"** — dual-band Wi‑Fi 6, integrated `mt76` radio (`mt7981`/`mt7976` companion). Already catalogued as `mediatek-mt7981-filogic`; referenced here as the entry-level Filogic Tier‑1/2 platform.
- **MT7986 "Filogic 830"** — quad A53, Wi‑Fi 6, `mt76`. Monitor/inject (Tier 1) plus reported CSI (Tier 2). Boards: Banana Pi BPI-R3, GL.iNet MT6000 (Flint 2), Zyxel EX5601.
- **MT7988 "Filogic 880"** — Wi‑Fi 6E (adds 6 GHz), `mt76`. Same monitor/inject + reported CSI story with a 6 GHz band. Boards: Banana Pi BPI-R4.

> The `mt76` CSI path is **out-of-tree and evolving** — mark any CSI result from a Filogic board *reported*, and cite the exact patch/commit, because the relay/debugfs format has changed across revisions.

---

## Broadcom — the closed continent

Broadcom router silicon is the cautionary tale. The application SoCs are capable ARM parts, but their Wi-Fi is a **FullMAC radio driven by a closed `wl.ko` / `dhd` blob** (or the SDK `nvram`/`wl` userspace). There is **no monitor mode, no injection, no CSI, no spectral** from stock, and — unlike the mobile BCM43xx parts that [Nexmon](../projects/nexmon.md) targets — the *router-class* radios (BCM4360/4366/6710/6715/6755) are **not covered by Nexmon**. OpenWrt runs on the CPU (`bcm53xx`, `bcm4908` targets) but the radio stays dark.

- **BCM47094** (Northstar+, dual A9) — hosts BCM4360/BCM4366 5 GHz `ac` radios via `wl`. Tier 0. Boards: Netgear R8000P, Asus RT-AC88U.
- **BCM4908 / BCM4906 / BCM4912** — Wi‑Fi 5/6 router SoCs; closed radio. OpenWrt boots the CPU (Ethernet/switch usable) but Wi‑Fi is blob-only. Tier 0. Boards: Asus GT-AC5300, RT-AX88U.
- **BCM6710 / BCM6715 / BCM6755** — Broadcom Wi‑Fi 6/6E/7 radios, entirely closed, no public off-the-floor path. Tier 0 (reported).

**Recommendation:** unless you have a specific Nexmon-covered *mobile* Broadcom part, treat Broadcom routers as inert for latent-radio work and spend the money on an IPQ60xx or Filogic board instead.

---

## Realtek — mostly *switches*, not radios

A common trap: **RTL838x / RTL839x / RTL930x are managed Ethernet switch SoCs**, not Wi‑Fi chips. OpenWrt's `realtek` target supports them beautifully — as switches. They contain **no radio whatsoever**; there is nothing to repurpose. They are listed here only to prevent mis-cataloguing.

The genuine Realtek radio in the router world is the older **RTL819x** family (RTL8196/8197 MIPS SoCs with an integrated 2.4 GHz 802.11n MAC). Realtek's driver stack is closed and its OpenWrt/`mac80211` support historically poor; monitor mode is limited and injection unreliable, so it caps around Tier 0→1 (*reported*). Not worth chasing when MediaTek exists.

---

## Lantiq / MaxLinear — DSL/GPON gateways with no latent radio

The Lantiq (now MaxLinear) **GRX330 / GRX350 (xRX500 "Grand River")** and **PRX300/PRX120** are xDSL/GPON *gateway* SoCs. They are supported by OpenWrt's `lantiq`/`xrx500` targets, but they contain **no integrated Wi‑Fi**; the radio on those gateways is always an *external* Realtek or Qualcomm die on the board. Nothing to repurpose at the SoC level — evaluate the attached radio instead.

---

## Practical: getting a spectrum trace off an Atheros router

```sh
# 1. Flash OpenWrt for your target (example: ipq40xx / ipq807x / qualcommax)
#    Confirm the driver and debugfs node exist:
ls /sys/kernel/debug/ieee80211/phy0/ath10k/     # or .../ath11k/
#    -> you want to see: spectral_scan_ctl  spectral_count  spectral_bins ...

# 2. Put the interface in a state that lets the FFT run and pick a mode:
iw phy phy0 interface add mon0 type monitor
ip link set mon0 up
echo background > /sys/kernel/debug/ieee80211/phy0/ath10k/spectral_scan_ctl
echo trigger    > /sys/kernel/debug/ieee80211/phy0/ath10k/spectral_scan_ctl

# 3. Sweep channels while capturing raw FFT samples:
cat /sys/kernel/debug/ieee80211/phy0/ath10k/spectral_scan0 > /tmp/fft.bin
echo disable > /sys/kernel/debug/ieee80211/phy0/ath10k/spectral_scan_ctl

# 4. Decode/visualize on a workstation:
git clone https://github.com/simonwunderlich/FFT_eval && cd FFT_eval && make
./fft_eval_json /tmp/fft.bin   # or the ncurses viewer
```

`ath11k` uses the same `spectral_scan_ctl` interface under `.../ath11k/`. This is a genuine raw-PHY spectral capability — Tier 3 — and is what makes Atheros routers uniquely valuable. Full validation methodology (sample-format sanity checks, dBm calibration caveats) is in [../docs/verification-tier3-spectral.md](../docs/verification-tier3-spectral.md).

---

## Buying guide — tier at a glance

| Platform | Driver | Bands | Best rung | Notes |
|---|---|---|---|---|
| IPQ40xx (4018/19/28/29) | ath10k | 2.4/5 | **Tier 3** | cheapest integrated spectral |
| IPQ806x (8064/65) | ext ath10k | 2.4/5 | Tier 3* | *via external QCA9880 |
| IPQ807x (8072/74) | ath11k | 2.4/5 | **Tier 3** | Wi‑Fi 6, high throughput |
| IPQ60xx (6000/10/18) | ath11k | 2.4/5 | **Tier 3** | best value Wi‑Fi 6 |
| IPQ5018 | ath11k | 2.4/5 | Tier 3 (rep.) | + QCN9074 companion |
| IPQ9574 | ath12k | 2.4/5/6 | Tier 1→3 (WIP) | Wi‑Fi 7 frontier |
| MT7621 | ext mt76 | — | Tier 0 (host) | sets tier via companion |
| MT7622 | mt76 | 2.4(+5 via MT7915) | Tier 1 (2 rep.) | E8450/RT3200 |
| MT7628/7688 | mt76 | 2.4 | Tier 1 | cheapest mt76 |
| MT7981 (Filogic 820) | mt76 | 2.4/5 | Tier 1→2 | see `mediatek-mt7981-filogic` |
| MT7986 (Filogic 830) | mt76 | 2.4/5 | Tier 1→2 (rep.) | BPI-R3, Flint 2 |
| MT7988 (Filogic 880) | mt76 | 2.4/5/6 | Tier 1→2 (rep.) | BPI-R4, Wi‑Fi 6E |
| BCM47094 / 490x | wl/dhd | 2.4/5 | **Tier 0** | closed, no monitor |
| BCM6710/6715/6755 | wl/dhd | 2.4/5/6 | **Tier 0** | closed Wi‑Fi 6E/7 |
| RTL819x | vendor | 2.4 | Tier 0→1 (rep.) | poor mac80211 support |
| RTL838x/930x | *(none)* | — | **N/A** | switch ASIC, no radio |
| Lantiq/MaxLinear GRX/PRX | *(none)* | — | **N/A** | gateway, external radio |

---

## Regulatory & safety notes

Everything spectral/monitor above is **receive-only** and legal to run anywhere. The moment you use **injection** (Tier 1) or push a radio into any **arbitrary-waveform test mode**, you are transmitting, and you are bound by your local RF regulator (FCC Part 15 in the US, ETSI EN 300 328 / EN 301 893 in the EU). Router power amplifiers can emit well above the levels a bare chip would — always transmit into a dummy load or a shielded enclosure when experimenting, keep to the ISM/UNII bands the hardware was certified for, and never inject on DFS channels without radar avoidance. Reflashing OEM firmware also voids the device's regulatory certification; the certification travels with the *stock* firmware.

---

## References

- OpenWrt targets: [ipq40xx](https://openwrt.org/docs/techref/targets/ipq40xx), [ipq806x](https://openwrt.org/docs/techref/targets/ipq806x), [mediatek](https://openwrt.org/docs/techref/targets/ramips), [bcm53xx](https://openwrt.org/docs/techref/targets/bcm53xx), [realtek](https://openwrt.org/docs/techref/targets/realtek), [lantiq](https://openwrt.org/docs/techref/targets/lantiq)
- ath10k driver / spectral: <https://wireless.wiki.kernel.org/en/users/drivers/ath10k>
- ath11k driver: <https://wireless.wiki.kernel.org/en/users/drivers/ath11k>
- ath9k spectral (reference implementation): <https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan>
- ath10k-ct firmware: <https://github.com/greearb/ath10k-ct>
- mt76 driver: <https://github.com/openwrt/mt76>
- FFT_eval spectral decoder: <https://github.com/simonwunderlich/FFT_eval>
- Broadcom FullMAC limitation context (Nexmon covers mobile, not router chips): <https://github.com/seemoo-lab/nexmon>
- Cross-links: [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../chips/mediatek-ralink.md](../chips/mediatek-ralink.md) · [../docs/verification-tier3-spectral.md](../docs/verification-tier3-spectral.md)
