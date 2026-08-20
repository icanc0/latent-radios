# Broadcom / Cypress / Infineon Wi-Fi & Combo Chips (BCM43xx / CYW43xx)

This is the home turf of **[Nexmon](../projects/nexmon.md)**. Broadcom's FullMAC Wi-Fi silicon is closed, but its architecture is unusually *reachable*: the physical layer is driven by a re-writable **D11 microcode** engine, and everything above it runs as **patchable ARM firmware** loaded from a file on the host. Because the RAM firmware is loaded by the driver at every boot, you can slip C and assembly patches into it without ever touching a mask ROM — which is exactly what Nexmon does. That single fact has turned a decade of cheap phones, Raspberry Pis and home routers into monitor-mode sniffers, CSI receivers, spectral analyzers and — on a lucky few parts — arbitrary-waveform transmitters and reactive jammers.

Two distinct eras live under the "BCM43xx" label:

- **b43 / OpenFWWF era (SoftMAC, ~2003–2010):** BCM4306/4318/4321/43224/43225. The host CPU runs mac80211; the chip runs only D11 ucode. For a subset of these, **[OpenFWWF](http://netweb.ing.unibs.it/~openfwwf/)** is a *fully open* replacement microcode — a genuine open-firmware MAC. See [../projects/rtl-sdr-lineage.md](../projects/rtl-sdr-lineage.md) for how this compares to other open-radio lineages.
- **FullMAC / Nexmon era (~2011–present):** BCM4329 → BCM4389. The MAC/PHY control loop moved *onto* an on-die ARM (Cortex-M3, then Cortex-R4, then Cortex-M7). This is the substrate Nexmon patches.

See also: [../projects/csi-toolchains.md](../projects/csi-toolchains.md), [../docs/firmware-reversing.md](../docs/firmware-reversing.md), [../docs/techniques.md](../docs/techniques.md).

---

## The D11 + ARM architecture (why these chips are climbable)

A modern Broadcom FullMAC chip has three programmable layers:

1. **The PHY** — an analog/mixed-signal front-end plus baseband DSP blocks, configured through hundreds of "radio" and "PHY" registers.
2. **The D11 core** — a small custom 16-bit RISC ("the ucode engine") sitting between MAC and PHY. It handles hard-real-time work (ACK timing, backoff, RX/TX descriptor shuffling) and template RAM. On SoftMAC parts this *is* the firmware; on FullMAC parts it is a co-processor. Broadcom ships the D11 ucode as an opaque blob; **[d11-emu](https://github.com/seemoo-lab/d11-emu)** reverse-engineers and emulates it.
3. **The application ARM** — a Cortex-M3 (older/low-power), **Cortex-R4** (the classic Nexmon targets: 4339, 43455c0, 4358, 4366), or Cortex-M7 / dual-core (4375/4387/4389). Firmware is split between a **ROM** (e.g. 640 KiB) and a **RAM** overlay (e.g. 768 KiB on the BCM4339) that the **BCMDHD** (Android) or **brcmfmac** (Linux/Pi) driver uploads at init.

**How Nexmon patches it:** you write C that is cross-compiled for the ARM and *linked against the reverse-engineered symbol table of the stock RAM firmware*; a patcher rewrites branch targets and appends new code into free RAM/flashpatch regions. Real-time PHY tricks are written in D11 assembly. The result is a drop-in replacement `.bin` the normal driver loads — no hardware mod, no exploit. `firmware.openness` for these parts is therefore **patchable**, not open: you never get Broadcom's source, but you can add arbitrary code. Tooling: **nexmon** (its own IDA/Ghidra-assisted build system), **b43-tools** (the D11 assembler/disassembler), **ghidra/ida/radare2** for the ARM. Details in [../docs/firmware-reversing.md](../docs/firmware-reversing.md).

### The SDR ladder, as it plays out on Broadcom

| Rung | Mechanism on Broadcom | Where it's real |
|-----|-----------------------|-----------------|
| 1 Monitor+Inject | Nexmon `monitor`/`inject` patch, or mac80211 on b43 | Almost every Nexmon-supported part |
| 2 CSI | `nexmon_csi`: dump per-subcarrier complex channel state from the PHY's channel estimator | 4339, 43455c0, 4358, 4366c0 (official); ported to more |
| 3 Spectral scan | Reuse the PHY FFT engine to stream raw bins (`makecsiparams`/spectral patch) | 4339, 43455c0 (research) |
| 4 Arbitrary waveform TX | Load an IQ sample buffer into the TX template path and key the PA — basis for **reactive jamming** | 4339 (Nexus 5), 43455c0 (Pi) — WiSec'17 |
| 5 Open PHY | Fully open replacement firmware | Only the OpenFWWF SoftMAC parts (4306/4318/…) |

---

## b43 / OpenFWWF era — the only genuinely *open* firmware

**BCM4306, BCM4318 (AirForce One 54g), BCM4311, BCM4320, BCM4321, BCM43224, BCM43225.** These are SoftMAC 802.11b/g (and draft-n for 4321/43224/43225) parts. The Linux **b43** driver runs mac80211, so monitor mode and injection are native and trivial (tier 1). The interesting part is **OpenFWWF** (Open FirmWare for WiFi), a clean-room open D11 microcode from Univ. of Brescia that *replaces* Broadcom's proprietary ucode — you compile the MAC yourself with **b43-tools**. That makes 4306/4311(rev1)/4318/4320 genuine **open-firmware** radios (tier 5 by openness), historically used to prototype new MAC protocols (TDMA, custom ACK policies). The catch: the PHY is an ancient 11g block, so there is no CSI/IQ story — "the PHY is yours" only in the sense that the *MAC timing* is. BCM43224/43225 are 11n MIMO parts that run under b43 with **proprietary** ucode (OpenFWWF never covered them), so they sit at tier 1. The D11 assembler heritage here (`b43-tools/assembler`) is the same toolchain Nexmon later reused for PHY tricks.

---

## The Nexmon flagships

### BCM4339 — Nexus 5 (the reference platform)
The single most-hacked Broadcom chip. 1×1 802.11ac, Cortex-R4, RAM firmware `6_37_34_43`. Everything Nexmon can do was first demonstrated here: monitor+injection, **nexmon_csi** (up to 80 MHz), **spectral analysis**, and — uniquely — **arbitrary-waveform transmission and reactive jamming** (Schulz et al., WiSec 2017: IQ buffers keyed out the front-end in 2.4 & 5 GHz with adaptive power control). That puts the Nexus 5 at **tier 4**. Also the basis of the **nexmon covert channel** work. If you want to *do PHY research on a phone*, this is the board.

### BCM43455c0 / BCM4345 / CYW43455 — Raspberry Pi 3B+, 4, 400, Zero 2 W (CM4)
The most *available* Nexmon target — a $35 Pi. 1×1 11ac, Cortex-R4. nexmon monitor/injection (fw `7_45_206`/`7_45_189`), **nexmon_csi** at up to 80 MHz (fw `7_45_189`), and the WiSec'17 jamming/arbitrary-IQ work was also brought up on the Pi 3B+ 43455c0 — **tier 4** (arbitrary-waveform *reported* on Pi, CSI/monitor *verified*). The default catalog entry for "SDR-ish Wi-Fi on hardware you already own." (Note: the Pi Zero 2 W actually carries a **BCM43436**, below; the Pi 3B/Zero W carry **BCM43430**.)

### BCM4358 — Nexus 6P / Galaxy S6 / Note 5
2×2 11ac, Cortex-R4. nexmon monitor/injection (fw `7_112_201_3_sta`) and **nexmon_csi** (fw `7_112_300_14_sta`, up to 80 MHz, 2 streams) — **tier 2** verified. (The Nexus **6**, by contrast, uses a **BCM4356**.)

### BCM4366 / BCM4366c0 — home routers
4×4 11ac Wave-2, the biggest PHY in this list. Found in **Netgear R8000/R8500 (Nighthawk X6/X8)**, **Asus RT-AC88U / RT-AC3100 / RT-AC5300**, and **Asus RT-AC86U (4366c0)**. `nexmon_csi` officially supports **bcm4366c0** on the RT-AC86U (fw `10_10_122_20`) — 4 cores × 4 streams of CSI at up to 80 MHz makes it the highest-dimensionality CSI receiver in the family — **tier 2**. Great for sensing/HAR research on mains power.

---

## The rest of the FullMAC line (map to devices)

| Chip | Streams / std | Carrier hardware | Nexmon status |
|------|---------------|------------------|---------------|
| **BCM4329** | 1×1 11n combo | iPhone 4, iPad 1, Kindle | historical, minimal |
| **BCM4330** | 1×1 11n combo | Galaxy S3, Nexus 7 (2012), Raspberry Pi *A/B (early)* via USB no | limited/experimental |
| **BCM4334** | 1×1 11n | Galaxy S4 (GT-i9500), iPhone 5c/5s | limited |
| **BCM4335** | 1×1 11ac | Galaxy S4 LTE-A, HTC One (M7), Nexus 7 (2013) | monitor/inject (early nexmon) |
| **BCM43430a1** | 1×1 11n | **Raspberry Pi 3B / Zero W / CM3** | monitor+inject `7_45_41_46` (tier 1) |
| **BCM43436b0** | 1×1 11n | **Raspberry Pi Zero 2 W** | monitor+inject `9_88_4_65` (tier 1) |
| **BCM4356** | 2×2 11ac | Nexus 6, some tablets | injection reported |
| **BCM4359** | 2×2 11ac | Galaxy S8 / Note 8 (some SKUs) | monitor/inject reported |
| **BCM4375 / 4375b1** | 2×2 11ax | **Galaxy S10 / S20** | monitor+inject `18_41_8_9_sta` (tier 1), CSI ported |
| **BCM4389 / 4389c1** | 2×2 11ax | **Pixel 6/7/7 Pro**, Galaxy S21 | monitor+inject `20_101_57` (tier 1) |
| **BCM4387** | 2×2 11ax | **iPhone 12/13**, Apple Silicon Macs | Apple-custom, RE only (tier 1 theoretical) |
| **BCM43012 / CYW43012** | 1×1 11n low-power | IoT modules, wearables | RE early (tier 0–1) |
| **BCM43596** | 2×2 11ac + 11ad companion | high-end routers | not ported (theoretical) |
| **CYW4373 / CYW4373E** | 1×1 11ac USB combo | Murata 1YN, USB dongles, Pi HATs | monitor/inject plausible via brcmfmac |
| **CYW89459** | 2×2 11ac + 802.11p | automotive V2X modules | closed, theoretical |

**Cypress / Infineon lineage note:** In 2016 Broadcom sold its IoT Wi-Fi line to **Cypress**, which rebranded BCM43xx → **CYW43xx** (e.g. BCM43455 → CYW43455, BCM43012 → CYW43012, plus new parts like **CYW43439** on the Pi Pico W and **CYW4373**). **Infineon** acquired Cypress in 2020, so these same dies now ship under the Infineon name. The silicon and Nexmon-ability are unchanged; only the logo on the datasheet moved. The classic BCM-branded parts (4339, 4358, 4366, 4375, 4387, 4389) stayed with Broadcom.

---

## Nexmon-family tooling recap

- **nexmon** — the C firmware-patching framework (monitor, injection, and the build system). [github.com/seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon); active community fork [kimocoder/nexmon](https://github.com/kimocoder/nexmon). See [../projects/nexmon.md](../projects/nexmon.md).
- **nexmon_csi** — per-frame CSI extraction (4339/43455c0/4358/4366c0). [github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi). Post-processing via **CSIKit** ([gi-z.github.io/CSIKit](https://gi-z.github.io/CSIKit/)). See [../projects/csi-toolchains.md](../projects/csi-toolchains.md).
- **Nexmon spectral / arbitrary-waveform TX** — spectral-scan patch and the WiSec'17 IQ-transmit/reactive-jamming firmware (Nexus 5, Pi 3B+).
- **d11-emu** — emulates/RE's the D11 ucode itself. [github.com/seemoo-lab/d11-emu](https://github.com/seemoo-lab/d11-emu).
- **b43-tools / OpenFWWF** — the open D11 assembler and open SoftMAC firmware for the 4306/4318-era parts.

---

## Summary table (SDR tier by chip)

| id | Part | Tier | Top capability | Firmware | RE status |
|----|------|------|----------------|----------|-----------|
| broadcom-bcm4306 | BCM4306 | 5 | open MAC (OpenFWWF) | D11 ucode, no ARM | open |
| broadcom-bcm4318 | BCM4318 | 5 | open MAC (OpenFWWF) | D11 ucode, no ARM | open |
| broadcom-bcm4321 | BCM4321 | 1 | monitor/inject (b43) | D11 ucode | closed |
| broadcom-bcm43224 | BCM43224 | 1 | monitor/inject (b43) | D11 ucode | closed |
| broadcom-bcm43225 | BCM43225 | 1 | monitor/inject (b43) | D11 ucode | closed |
| broadcom-bcm4339 | BCM4339 | 4 | arbitrary-waveform TX / jam | D11 + Cortex-R4 | patchable |
| broadcom-bcm43455c0 | BCM43455c0 | 4 | arbitrary-waveform / CSI | D11 + Cortex-R4 | patchable |
| broadcom-bcm4358 | BCM4358 | 2 | CSI (2×2) | D11 + Cortex-R4 | patchable |
| broadcom-bcm4366c0 | BCM4366c0 | 2 | CSI (4×4) | D11 + Cortex-R4 | patchable |
| broadcom-bcm43430 | BCM43430 | 1 | monitor/inject | D11 + Cortex-M3 | patchable |
| broadcom-bcm43436 | BCM43436 | 1 | monitor/inject | D11 + Cortex-M3 | patchable |
| broadcom-bcm4335 | BCM4335 | 1 | monitor/inject | D11 + Cortex-R4 | patchable |
| broadcom-bcm4356 | BCM4356 | 1 | injection | D11 + Cortex-R4 | patchable |
| broadcom-bcm4359 | BCM4359 | 1 | monitor/inject | D11 + Cortex-R4 | patchable |
| broadcom-bcm4375 | BCM4375b1 | 1 | monitor/inject (+CSI port) | D11 + Cortex-M7 | patchable |
| broadcom-bcm4389 | BCM4389c1 | 1 | monitor/inject | D11 + dual-core | patchable |
| broadcom-bcm4387 | BCM4387 | 1 | RE only | Apple-custom | closed |
| broadcom-bcm4329 | BCM4329 | 1 | monitor (historical) | D11 + Cortex-M3 | patchable |
| broadcom-bcm4330 | BCM4330 | 1 | monitor (experimental) | D11 + Cortex-M3 | patchable |
| broadcom-bcm4334 | BCM4334 | 1 | monitor (experimental) | D11 + Cortex-M3 | patchable |
| cypress-cyw43012 | CYW43012 | 1 | RE early | D11 + Cortex-M3 | partially-documented |
| broadcom-bcm43596 | BCM43596 | 0 | none public | D11 + ARM | closed |
| cypress-cyw4373 | CYW4373 | 1 | monitor (plausible) | D11 + ARM | closed |
| cypress-cyw89459 | CYW89459 | 0 | none public | D11 + ARM | closed |

---

## Un-cataloged / TODO (feeds the next cycle)

- **BCM4360 / BCM4352** — 3×3 11ac PCIe/router PHYs (Netgear R7000, many AC1900 USB adapters via `bcmwl`/`wl`); b43 unsupported, only the proprietary `wl` driver — CSI potential unexplored.
- **BCM43602** — 3×3 11ac router chip (Netgear R7000P, Fritz!Box); D11 + ARM, no Nexmon port yet.
- **BCM43340 / BCM43341 / BCM43342** — combo parts in older tablets; firmware family close to 4334.
- **BCM43362 / BCM43364** — Cypress/Broadcom IoT (Photon, WICED boards); SoftAP firmware, RE potential.
- **BCM43438** — the *original* Pi 3 / Pi Zero W silicon marking (vs 43430a1 in nexmon); confirm die identity.
- **CYW43439 / CYW4343W** — Pi Pico W and countless IoT boards; brcmfmac support exists, monitor/CSI unverified — high-value future target given ubiquity.
- **CYW54591 / CYW55572** — Wi-Fi 6/6E Infineon combo parts; architecture likely Cortex-M7, no public RE.
- **BCM4377 / BCM4378** — Apple Silicon Mac Wi-Fi (pre-4387); `brcmfmac`-driven on Asahi Linux — firmware openness worth profiling.
- **BCM43012 vs CYW43012** — confirm whether they are the same die; wearable/low-power PHY telemetry unknown.
- **BCM4390 / BCM4398** — newest Wi-Fi 7 flagships (Pixel 9, Galaxy S24/S25); no Nexmon port, ROM layout unknown.
- Confirm exact **Cortex core** (M3 vs R4 vs M7) and ROM base per part — several entries above are inferred from the Nexmon symbol maps and need datasheet confirmation.
- **802.11ad / 60 GHz** Broadcom parts (BCM20130-class) — did any ship? 60 GHz FMCW-radar repurposing would be a distinct scope.
