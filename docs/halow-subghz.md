# Wi-Fi HaLow (802.11ah) and Sub-GHz Sensing

*Part of the Latent Radios catalog. Sibling deep-dives: [mmWave & 60 GHz radar](mmwave-60ghz-radar.md), [CSI toolchains](../projects/csi-toolchains.md), [Wi-Fi 7 & 6 GHz](wifi7-and-6ghz.md), [true-SDR comparison](true-sdr-comparison.md), [taxonomy](taxonomy.md).*

Everything else in this catalog lives in the crowded 2.4/5/6 GHz Wi-Fi bands. **Wi-Fi HaLow (IEEE 802.11ah)** is the odd one out: it is Wi-Fi that has been dragged down into the **sub-1 GHz ISM band** (902–928 MHz in the US, 863–868 MHz in the EU, 916.5–927.5 MHz in Japan, and various 750–950 MHz allocations elsewhere), with narrow **1 / 2 / 4 / 8 / 16 MHz** channels instead of 20/40/80/160 MHz. That single change — a ~2.7× drop in carrier frequency — is exactly what makes it interesting to anyone thinking about long-range, through-wall RF sensing.

This page covers the silicon (Morse Micro MM6108/MM8108, Newracom NRC7292/NRC7394), the modules and dev kits built on them (Silex, ALFA, Gateworks, Heltec), the state of driver openness, and what the physics of 900 MHz does to the CSI/sensing picture. It is deliberately honest about a gap: **HaLow silicon today is a tier-1 (monitor/injection) target, not a tier-2 CSI target** — no public toolchain extracts per-subcarrier CSI from any HaLow chip the way [Atheros CSI Tool](../projects/csi-toolchains.md), [Nexmon CSI](../projects/nexmon.md), or [PicoScenes](../projects/picoscenes.md) do for mainstream Wi-Fi. Why that gap exists, and where the seams are, is most of the story.

---

## 1. Why sub-GHz changes the sensing picture

The reason to care about HaLow for sensing has nothing to do with throughput (it tops out at tens of Mbps) and everything to do with **propagation**.

| Property | 2.4/5 GHz Wi-Fi | 900 MHz HaLow | Consequence for sensing |
|---|---|---|---|
| Free-space path loss (Friis) | Reference | **~8.5 dB lower** than 2.4 GHz, ~15 dB lower than 5 GHz at the same distance | Same link budget reaches far more of a building; a single node can illuminate a whole house |
| Wall / material penetration | Attenuated hard by concrete, brick, foliage | Diffracts and penetrates far better at longer wavelength (λ ≈ 33 cm vs 12.5 cm / 6 cm) | **Through-wall** and NLoS geometries become practical, not just heroic |
| Wavelength | 12.5 cm (2.4G) / 6 cm (5G) | **~33 cm** | Coarser spatial resolution — worse for fine gesture work, but a human body is still many λ and moves detectably |
| Channel bandwidth | 20–160 MHz | **1–16 MHz** (2/4 MHz typical) | Far fewer subcarriers → coarse range/delay resolution; better SNR per subcarrier and less fading diversity |
| Doppler at 900 MHz | Reference | ~2.7× smaller Doppler shift per m/s | Slower-moving targets produce smaller frequency shifts — needs longer coherent integration |
| Coherence / stability | Fast fading | Longer coherence time and distance | CSI time-series are smoother; good for respiration/occupancy, less rich for micro-Doppler |

The trade is explicit and it is the whole point: **HaLow buys you range and penetration at the cost of bandwidth (delay resolution) and Doppler sensitivity.** A 4 MHz OFDM channel has on the order of ~56 usable data subcarriers (the 802.11ah PHY reuses the 802.11ac numerology downclocked 10×: a 1 MHz channel ≈ 32-point FFT / ~24 data tones; 2 MHz ≈ 64-FFT / ~52 tones; 4 MHz ≈ 128-FFT / ~108 tones; 8 MHz ≈ 256-FFT; 16 MHz ≈ 512-FFT). That is enough for a coarse channel-frequency-response vector, but with ~4× coarser time-of-flight resolution than an equivalent 20 MHz 802.11n channel.

**What this is good for:** whole-home occupancy, presence and vacancy, coarse localization/zone detection, respiration and gross-motion detection through interior walls, and long-range perimeter/agricultural monitoring where 2.4 GHz simply does not reach. A recent field study by Xu, Mankai & Alouini (2026) using commodity HaLow dongle-class nodes measured a NLoS coverage boundary around **120 m through obstructions** and graceful LoS throughput decay out to **~814 m single-hop**, with mesh relays reaching **>1.1 km** — numbers that are simply unreachable at 2.4 GHz with comparable EIRP.

**What this is bad for:** fine gesture recognition, keystroke inference, or anything needing sub-decimeter delay resolution. Those want wide bandwidth (60 GHz [mmWave radar](mmwave-60ghz-radar.md) or 80/160 MHz [Wi-Fi 6/7 CSI](wifi7-and-6ghz.md)), not HaLow.

---

## 2. The silicon

Two vendors ship essentially all merchant HaLow radios today: **Morse Micro** (Sydney) and **Newracom** (San Jose / Korea). Quantenna/ON, Methods2Business/Silex IP, and others have touched the standard, but the commercially relevant, hobbyist-reachable parts are the four below plus the modules that wrap them.

### 2.1 Morse Micro — MM6108 (in DB) and MM8108 (net-new)

Morse Micro's [MM6108](../chips/other-vendors.md) (already cataloged) was the first widely available HaLow SoC. The **MM8108**, announced at CES 2025 (Jan 8, 2025), is the second generation and the current flagship.

- **MM8108 highlights:** world-first sub-GHz **256-QAM at 8 MHz** for up to **43.33 Mbps**; 5×5 mm BGA (vs MM6108's 6×6 mm QFN48); adds a **USB 2.0 host interface** alongside SDIO 2.0 and SPI, plus a **MIPI RFFE** for multi-radio front-end coordination; integrated PA and high-linearity LNA; 850–950 MHz programmable.
- **Interfaces matter for hacking:** the new USB interface means MM8108 can appear as a **USB HaLow dongle** (Morse's MM8108-RD09 reference design), the friendliest possible host attachment — no SDIO/SPI device-tree surgery.
- **Firmware/driver posture:** Morse publishes a **GPL-2.0 mac80211-based Linux driver**, an **OpenWrt SDK**, a **hostap** fork, and an **MM-IoT-SDK** for the on-chip MCU — all on GitHub. But the **radio firmware ships as closed binary blobs** (plus per-module "BCF" board-config files hosted in a `morse-firmware` repo). So the *host driver* is open and auditable; the *PHY/MAC firmware* running on the SoC is not. Driver/firmware release 1.16.4+ supports both MM6108 and MM8108 (MM8108 feature parity was still catching up as of the 1.16.x line).

### 2.2 Newracom — NRC7292 (in DB) and NRC7394 (net-new)

Newracom's [NRC7292](../chips/other-vendors.md) is the part the open-source community actually cut its teeth on, because Newracom's **`nrc7292_sw_pkg`** driver is unusually open (see §3). The **NRC7394** is the newer, lower-cost, lower-power generation.

| | NRC7292 | NRC7394 |
|---|---|---|
| Package | QFN | 6×6 mm 48-QFN |
| Channels | 1/2/4 MHz | 1/2/4 MHz, 750–950 MHz |
| Host MCU | ARM **Cortex-M3**, 752 KB SRAM, no on-chip flash | ARM **Cortex-M3**, standalone-capable |
| On-chip PA | External FEM (e.g. Qorvo RFFM6901 on ALFA HAT) | **Integrated PA, up to +17 dBm** |
| PHY throughput | 150 Kbps – 15 Mbps | Improved efficiency, similar rate class |
| Positioning | First commercial 802.11ah SoC | Cost/power-optimized successor |
| Driver | `nrc7292_sw_pkg` (GPL-2.0) — also lists model variants 7292/7393/7394 | Same package/branch supports it |

Both run **host mode** (Linux driver over CSPI/SDIO/UART/USB) or **standalone mode** (your app runs on the Cortex-M3 with no external host — the WiFi MAC/PHY firmware is still a closed Newracom binary, `uni_s1g.bin` / `nrc7292_cspi.bin`).

### 2.3 Net-new module records

The chips reach hobbyists mainly as pre-integrated modules and Raspberry-Pi-attachable kits:

| Product | Vendor | Silicon | Form factor | Notes |
|---|---|---|---|---|
| **SX-NEWAH / SX-NEWAH-EVK** | Silex Technology | NRC7292 | M.2 / eval board | "Industry-first" 802.11ah module; RPi reference platform; up to ~1.5 km |
| **AHPI7292S** | ALFA Network | NRC7292 + Qorvo RFFM6901 FEM | Raspberry Pi HAT | ~$70; first HaLow RPi HAT; host + standalone; well-documented community bring-up |
| **GW16167** | Gateworks | MM8108 | M.2 card | Second-gen Morse silicon on an M.2 for embedded gateways |
| **GW16146** | Gateworks | NRC7292 | Mini-PCIe | Earlier Newracom-based radio module |
| **HT-HC01 / HT-HC32** | Heltec | HaLow module + ESP32-S3 | Camera dev board | HaLow + ESP32-S3 host, integrated camera; >1 km, up to 32 Mbps |

For SDR/sensing experimentation, the **ALFA AHPI7292S HAT** (open-ish Newracom driver) and the **MM8108 USB dongle reference designs** (friendliest host attach) are the two most practical starting points.

---

## 3. Driver and firmware openness

This is where HaLow diverges sharply from the rest of the catalog, and it cuts both ways.

**The good news — the host drivers are open.** Newracom's `nrc7292_sw_pkg` is **GPL-2.0** and genuinely readable. Independent analysis (the `nrc7292-analysis` project) confirms it is a real **mac80211/cfg80211 driver**: it implements `ieee80211_ops`, bridges into the Linux wireless stack via `nrc-mac80211.c`, and talks to the chip over **CSPI** (a custom SPI framing, start byte `0x50`, with burst and direction bits) via a HIF layer and a **WIM** (Wireless Interface Module) control protocol. Morse Micro's driver is likewise a GPL mac80211 driver. Because both are mac80211-based, **monitor mode with radiotap headers and packet injection follow for free** — the standard `iw dev … set monitor`, `airmon`-style flows, and Wireshark capture all apply once the S1G channel plumbing is configured.

**The catch — mainline mac80211 barely knows about S1G.** 802.11ah's 1/2/4/8/16 MHz S1G channelization, the S1G PHY headers, and the sub-GHz regulatory rules are **not fully supported in the upstream kernel**. So both vendors ship **out-of-tree** and pair the driver with **patched kernel + patched `hostap` + patched `wireless-regdb`**. The community [`droidifi/newracom-s1g`](https://github.com/droidifi/newracom-s1g) project packages exactly this: a coordinated `linux-5.10.x-S1G` branch across kernel, hostapd/wpa_supplicant, wireless-regdb, and the Newracom driver, to get "native" S1G into the standard stack rather than a bolt-on. **Neither Morse nor Newracom is fully mainlined** as of this writing, though because the sources are GPL the path exists, and Morse has been actively upstreaming pieces.

**The bad news for SDR — the firmware is closed.** On both vendors the actual **PHY/MAC firmware blob** (`uni_s1g.bin`, Morse's binaries + BCF board-config files) is closed and, unlike Broadcom, has **no Nexmon-class RE toolchain**. There is no published Ghidra loader, no patching framework, no documented ucode. So the openness you get is at the **driver/host** layer, not the **firmware/PHY** layer — precisely the opposite of the Broadcom situation where the driver is closed but Nexmon cracks the firmware.

| Layer | Newracom NRC7292/7394 | Morse MM6108/MM8108 |
|---|---|---|
| Linux host driver | **Open, GPL-2.0, mac80211** | **Open, GPL-2.0, mac80211** |
| hostapd/wpa_supplicant | Patched fork (open) | Patched fork (open) |
| On-chip app SDK | Cortex-M3 standalone SDK (documented) | MM-IoT-SDK (documented) |
| Radio PHY/MAC firmware | **Closed blob** (`uni_s1g.bin`) | **Closed blob** + BCF |
| Public firmware RE tooling | **None** | **None** |

---

## 4. What you can actually do today: monitor, sniff, inject

Because the drivers are mac80211-based, **tier-1 SDR capability (monitor + injection) is verified and reachable today.** The Newracom package explicitly supports a **sniffer mode** (local and remote), and monitor frames carry **radiotap** with RF metadata. Concretely, on an ALFA AHPI7292S / Raspberry Pi:

```bash
# Newracom host-mode bring-up (Raspberry Pi, out-of-tree package)
git clone https://github.com/newracom/nrc7292_sw_pkg
cd nrc7292_sw_pkg/package/evk/sw_pkg/nrc_pkg
# Install the device-tree overlay + firmware (uni_s1g.bin) per the package README,
# then start in sniffer/monitor mode via the provided start script:
sudo python3 ./start.py 0 0 US   # args: <STA/AP/SNIFFER mode> <security> <country>
# The package's sniffer mode brings up a monitor interface; capture with:
sudo tcpdump -i nrc0 -w halow.pcap
# or open nrc0 directly in Wireshark and dissect S1G frames.
```

Channel selection has to speak S1G. US HaLow channelization sits in **902–928 MHz**, numbered by bandwidth class (e.g. 1 MHz channels 1,3,5…; 2 MHz channels 2,6,10…; 4 MHz channels 8,16…; a single 8 MHz channel). A pure-spectrum sanity check needs no HaLow radio at all: [`lmlsna/halow_scanner`](https://github.com/lmlsna/halow_scanner) uses an **[RTL-SDR](../projects/rtl-sdr-lineage.md)** to FFT the 902–928 MHz band and rank HaLow channels by noise floor — useful for picking a clean channel before a capture, but it only measures **energy**, it does not demodulate HaLow.

**What you do *not* get today:** there is **no public per-subcarrier CSI export** from any HaLow chip. The vendor drivers do not expose a CSI report path the way `ath9k`'s CSI Tool or Nexmon do, and no third party has reverse-engineered one. Newracom's "Wi-Fi HaLow sensor solution" is about IoT **sensor nodes** (temperature, occupancy PIR, etc. transported over HaLow), **not** RF/CSI sensing of the channel. Morse's occupancy/fall-detection demos pair HaLow for connectivity with a **separate [60 GHz mmWave radar](mmwave-60ghz-radar.md)** front-end doing the actual sensing. So as of now:

- **CSI (tier 2): not available on HaLow** with public tooling. Would require either firmware RE (no toolchain exists) or a vendor-exposed CSI API (not shipped).
- **Spectral scan (tier 3): not exposed.**
- **FTM / ranging:** requested by the community; **not yet in the shipping Linux drivers**. When it lands it enables coarse time-of-flight ranging, which at 4–8 MHz is meter-class, not centimeter-class.

---

## 5. HaLow CSI: the physics if the seam ever opens

If a CSI path were reverse-engineered (or a vendor shipped one), here is what the data would look like, and why it is worth wanting despite the caveats.

- **Subcarrier count** scales with bandwidth: ~24 (1 MHz) / ~52 (2 MHz) / ~108 (4 MHz) / ~234 (8 MHz) data tones. A 4 MHz capture gives a channel-frequency-response vector comparable in *length* to legacy 20 MHz 802.11n CSI — but spanning **1/5 the bandwidth**, so ~5× coarser delay resolution.
- **SNR per tone is higher** (narrow channel, low path loss) and **fading is flatter** (fewer resolvable multipath taps within a narrow band), so the CSI time-series are **smooth and stable** — ideal for slow-varying phenomena (respiration ~0.2–0.5 Hz, occupancy, presence, gross limb motion) sensed **through interior walls** where 2.4 GHz CSI would be buried in the noise floor.
- **Doppler is ~2.7× compressed** vs 2.4 GHz, so micro-Doppler signatures (fingers, subtle gestures) are much weaker; you compensate with **longer coherent integration**, which HaLow's long coherence time actually permits.

The research consensus (see the 802.11bf WLAN-sensing surveys and the HaLow field-characterization work in the references) is that **sub-GHz sensing trades spatial/Doppler richness for penetration and coverage** — a genuinely different operating point from the rest of this catalog, and the reason people keep asking Newracom and Morse for a CSI hook. Until that hook exists, HaLow's honest tier is **1**.

---

## 6. Summary scorecard

| Chip / part | Rung reachable today | Firmware | Public tooling |
|---|---|---|---|
| Morse **MM6108** / **MM8108** | **Tier 1** (monitor, injection) | Closed blob + BCF; open GPL driver | Morse GPL mac80211 driver, OpenWrt SDK, hostap fork |
| Newracom **NRC7292** / **NRC7394** | **Tier 1** (monitor, injection, sniffer) | Closed blob (`uni_s1g.bin`); open GPL driver | `nrc7292_sw_pkg`, `droidifi/newracom-s1g`, `nrc7292-analysis` |
| Any HaLow, spectrum only | Passive energy scan | n/a | `halow_scanner` + RTL-SDR |

**Bottom line.** HaLow is the catalog's most physically interesting sensing band and, simultaneously, its least developed reverse-engineering target. The drivers are open (mac80211), monitor and injection work today, and the propagation physics are tailor-made for long-range and through-wall work. But there is **no public CSI, spectral, or firmware-RE path**, and the PHY firmware is a closed blob with no Nexmon-equivalent. That combination — open host, closed PHY, killer physics — makes HaLow the single most inviting **open problem** in this catalog for anyone wanting to build the first sub-GHz Wi-Fi CSI toolchain.

---

## References

**Silicon & datasheets**
- Morse Micro MM8108 product page & datasheet — https://www.morsemicro.com/chips/ , https://www.morsemicro.com/resources/datasheets/modules/MM8108-MF15457_Data_Sheet.pdf
- Morse Micro MM8108 launch (CES 2025) — https://www.morsemicro.com/2025/01/08/morse-micro-introduces-the-smallest-fastest-lowest-power-and-farthest-reaching-wi-fi-chip-in-the-world/
- MM8108 SoC overview — https://www.cnx-software.com/2025/01/14/morse-micro-mm8108-wifi-halow-soc-supports-up-to-43-33-mbps-transfer-rate-improves-range-and-power-efficiency/
- Newracom NRC7394 product brief — https://newracom.com/hubfs/Resources%20Documents/Product%20Brief%20(NRC7394)(NEWRACOM).pdf , https://www.cnx-software.com/2023/06/29/newracom-nrc7394-wifi-halow-soc-delivers-higher-power-efficiency-and-cost-effectiveness/
- Newracom NRC7292 product page — https://newracom.com/products/nrc7292

**Drivers & openness**
- Newracom `nrc7292_sw_pkg` (GPL-2.0 Linux host driver) — https://github.com/newracom/nrc7292_sw_pkg
- `droidifi/newracom-s1g` native S1G kernel/hostap/regdb integration — https://github.com/droidifi/newracom-s1g
- NRC7292 driver architecture analysis (mac80211/CSPI/WIM) — https://oyongjoo.github.io/nrc7292-analysis/2025/06/17/nrc7292-architecture-overview/
- Morse Micro GitHub update (driver, OpenWrt, MCU SDK, firmware binaries) — https://community.morsemicro.com/t/github-update-october-2025/965
- Gateworks NRC7292 driver fork — https://github.com/Gateworks/nrc7292

**Modules & dev kits**
- Silex SX-NEWAH (NRC7292 module) — https://www.silextechnology.com/connectivity-solutions/embedded-wireless/sx-newah
- ALFA AHPI7292S HaLow Raspberry Pi HAT — https://www.cnx-software.com/2022/04/03/add-wifi-halow-to-raspberry-pi-with-alfa-network-ahpi7292s-hat/ , https://www.beyondlogic.org/evaluating-the-alfa-network-ahpi7292s-nrc7292/
- Gateworks GW16167 (MM8108 M.2) — https://www.gateworks.com/products/wireless-options/gw16167-mm8108-802-11ah-halow-wifi-m2-card/
- Heltec HT-HC32 HaLow camera board — https://heltec.org/project/ht-hc32/

**Sensing & spectrum**
- Xu, Mankai, Alouini, "Wi-Fi HaLow (IEEE 802.11ah) for Long-Range Monitoring Links" (2026) — https://arxiv.org/abs/2605.17349
- `lmlsna/halow_scanner` — RTL-SDR HaLow channel scanner — https://github.com/lmlsna/halow_scanner , https://www.rtl-sdr.com/halow_scanner-an-rtl-sdr-based-802-11ah-halow-channel-scanner/
- Newracom Wi-Fi HaLow sensor solution — https://newracom.com/blog/newracom-introduces-first-wi-fi-halow-sensor-solution
- 802.11bf WLAN sensing overview (context for CSI-based sensing) — https://arxiv.org/pdf/2207.04859
