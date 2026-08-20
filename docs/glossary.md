# Glossary

A tight, alphabetical reference for every term used across **Latent Radios**. Definitions are scoped to how the term is used in this project — turning commodity Wi-Fi and wireless silicon into partial software-defined radios by reverse-engineering firmware and tapping the PHY telemetry the chip already computes. For how these terms are organized into the SDR ladder and capability flags, see [taxonomy](../docs/taxonomy.md).

---

### Arbitrary waveform (TX)
The ability to hand the radio a baseband IQ buffer you authored and have the front-end transmit it, rather than only emitting standards-compliant 802.11 frames. This is **rung 4** of the SDR ladder; on commodity Wi-Fi chips it is usually reached by abusing template/scratch RAM or an unused TX path in patched firmware, and is rare and fragile.

### Baseband
The signal at (or near) zero frequency, before it is mixed up to the RF carrier — i.e. the IQ representation of what is actually being transmitted or received. "Baseband processor" often refers to the DSP/PHY block of the chip that turns bits into IQ and back; owning the baseband is what separates a true SDR from a frame-level radio.

### Beamforming feedback
The compressed channel/steering information a receiver sends back to a transmitter (per 802.11n/ac/ax sounding) so the transmitter can steer energy toward it. Because this feedback encodes per-subcarrier channel state, it is an alternate, sometimes standardized, path to CSI-like data even on chips that do not expose raw CSI.

### Blob (firmware)
A closed, vendor-signed binary firmware image loaded onto the chip at boot (e.g. `brcmfmac43455-sdio.bin`) with no source and no official documentation. Climbing the SDR ladder almost always means reverse-engineering or patching a blob; `firmware.openness` in this catalog rates how tractable a given blob is.

### brcmfmac
The mainline Linux kernel driver for Broadcom/Cypress **FullMAC** Wi-Fi parts (the SDIO/PCIe/USB FMAC family). It is the host-side counterpart that loads the firmware blob and is the driver Nexmon-patched firmware runs underneath. See [Broadcom/Cypress chips](../chips/broadcom-cypress.md).

### Covert channel
A communication path that hides data inside a medium not intended to carry it — e.g. modulating CSI, timing, or spectral emissions so a second device can read a message no standard receiver would notice. A capability flag (`covert-channel`) in this catalog and a common research use of low-rung SDR access.

### Cross-technology communication (CTC)
Techniques that let one radio standard talk directly to another (e.g. Wi-Fi emitting a waveform a ZigBee or Bluetooth receiver decodes) by carefully shaping the legal Wi-Fi output so its energy pattern is legible to the foreign PHY. A key application of arbitrary-waveform and injection capabilities.

### CSI (Channel State Information)
The per-OFDM-subcarrier complex channel response — amplitude **and** phase for each subcarrier — that the receiver estimates to equalize an incoming frame. Exposing it is **rung 2** of the ladder and the workhorse of Wi-Fi sensing (motion, presence, gesture, respiration). See [CSI toolchains](../projects/csi-toolchains.md).

### D11 ucode
The microcode that runs on Broadcom's "d11" MAC engine — a small, custom in-silicon core that handles time-critical 802.11 MAC tasks alongside the main ARM CPU. Patching d11 ucode (via `b43`/`b43-tools` and Nexmon) is how many low-level RX/TX and CSI features are unlocked on Broadcom parts.

### DFS (Dynamic Frequency Selection)
The regulatory requirement that Wi-Fi devices on certain 5 GHz channels detect radar and vacate, which forces the chip to run a radar/energy detector on the PHY. That built-in detector is one of the telemetry surfaces this project taps for spectral and radar-like sensing.

### DMA ring
A circular buffer in shared memory, described by descriptors, that the chip's DMA engine uses to move frames (and sometimes raw telemetry) between the radio and the host without CPU copying. Finding and re-tasking RX DMA rings is a common way to exfiltrate CSI or raw samples in firmware patches.

### FMCW (Frequency-Modulated Continuous Wave)
A radar waveform that sweeps frequency linearly over time so that the echo delay appears as a frequency offset, giving range (and, with motion, velocity). A capability flag here for chips (notably 60 GHz parts) that can either natively run FMCW or be coerced into radar-like operation.

### FTM (802.11mc / Fine Timing Measurement)
The 802.11mc ranging protocol in which two stations exchange timestamped frames to measure round-trip time and hence distance. Chips that expose FTM timestamps give sub-meter ranging and a timing surface useful for positioning and passive-sensing work.

### FullMAC vs SoftMAC
Two split points for the 802.11 MAC. **FullMAC** runs the MAC state machine in chip firmware (host sends high-level commands — e.g. brcmfmac, most mobile parts), making the MAC opaque but patchable in firmware; **SoftMAC** runs the MAC in the host driver over `mac80211` (e.g. ath9k, many Atheros parts), exposing more control to the host without touching firmware. The split dictates whether you attack the driver or the blob.

### Injection
Transmitting arbitrary, hand-crafted 802.11 frames (spoofed addresses, malformed fields, custom rates) rather than only protocol-generated ones. Together with monitor mode it is **rung 1** of the ladder and the foundation of most Wi-Fi tooling.

### IQ samples
Paired **In-phase (I)** and **Quadrature (Q)** values that together represent a complex baseband sample — the amplitude and phase of the signal at an instant. Raw IQ is the native currency of true SDRs; getting IQ off a Wi-Fi chip (`raw-iq`) is the top of what this project chases.

### iwlwifi
The mainline Linux driver for Intel Wi-Fi hardware. Intel parts are largely FullMAC with tightly closed firmware, so `iwlwifi`-based CSI/telemetry work historically depended on a specific vendor CSI tool rather than open firmware patching. See [Intel chips](../chips/intel.md).

### MAC vs PHY
The two lowest 802.11 layers. The **PHY** (physical layer) turns bits into RF waveforms and back — OFDM, modulation, channel estimation — and is where CSI, spectral scans and IQ live; the **MAC** (medium access control) handles addressing, framing, acknowledgements and channel access. SDR value lives in the PHY; frame-level tools live at the MAC.

### Monitor mode / RFMON
A radio mode in which the interface receives **all** 802.11 frames on a channel — regardless of destination — and passes them up with PHY metadata, without associating to any network. It is the RX half of rung 1 and the prerequisite for sniffing, CSI capture and injection workflows. (See also **RFMON**, its formal name.)

### mt76
The mainline Linux driver family for MediaTek/Ralink Wi-Fi parts. Several mt76-supported chips expose spectral/scan and CSI-adjacent features from the host side, making them attractive without deep firmware reversing. See [MediaTek/Ralink chips](../chips/mediatek-ralink.md).

### Nexmon
The C-based firmware-patching framework for Broadcom/Cypress Wi-Fi chips that lets you inject compiled patches into the closed firmware blob to add monitor mode, injection, CSI extraction and more. It is the single most important tool for climbing the ladder on Broadcom silicon. See [the Nexmon project](../projects/nexmon.md).

### OFDM subcarrier
One of the many narrowband, orthogonally-spaced tones that an OFDM symbol is spread across (e.g. 56 usable tones in a 20 MHz 802.11 channel). CSI is reported **per subcarrier**, so subcarrier count sets the frequency resolution of any Wi-Fi sensing.

### OTP (One-Time-Programmable memory)
On-chip fuse memory holding per-device configuration — calibration, MAC address, regulatory and feature-enable bits — written once at manufacture. OTP contents can gate which PHY features the firmware will allow, so reading/understanding OTP is sometimes part of unlocking a chip.

### Passive radar
Sensing that detects and locates targets from the reflections of transmitters it does not control — using ambient Wi-Fi (or other) illumination and comparing a reference copy against surveillance copies of the signal. A capability flag (`passive-radar`) enabled by CSI or raw-IQ access plus a reference channel.

### PlutoSDR / HackRF / USRP (SDR reference)
Three canonical "true" software-defined radios used in this catalog as the yardstick: **ADALM-PlutoSDR** (AD936x-based, ~70 MHz–6 GHz, cheap dev board), **HackRF One** (1 MHz–6 GHz half-duplex, 8-bit), and **USRP** (Ettus, the research-grade family). They deliver open baseband IQ end-to-end — rung 5 by construction — and mark what a repurposed Wi-Fi chip is measured against. See [true-SDR comparison](../docs/true-sdr-comparison.md).

### Promiscuous mode
A NIC mode that accepts all frames addressed to the network the interface has joined (regardless of unicast destination), passing them to the host. Weaker than monitor mode — the interface is still associated and still filters at the MAC — but often conflated with it.

### Radiotap
The de-facto header format prepended to received frames in monitor mode to carry PHY metadata — channel, rate, RSSI, MCS, timestamps, sometimes vendor CSI/telemetry namespaces. It is how per-frame PHY information reaches userspace tools like Wireshark.

### RFMON
"Radio-frequency monitor" — the formal name for monitor mode (see **Monitor mode / RFMON**): the interface captures raw 802.11 frames on a channel without associating, delivering them with radiotap metadata.

### RSSI (Received Signal Strength Indicator)
A coarse, single-number estimate of received power for a frame, reported by essentially every Wi-Fi chip. It is the lowest-fidelity PHY telemetry — useful for crude ranging and presence but far below CSI, which resolves power and phase per subcarrier.

### SDR (Software-Defined Radio)
A radio whose signal processing — modulation, demodulation, filtering — is done in software on general-purpose samples (IQ) rather than fixed hardware, ideally with direct access to baseband. This project asks, for each commodity chip, **how far up the SDR ladder** it can be pushed with public tooling.

### Spectral scan
A PHY feature that reports raw FFT bin magnitudes across the channel — the spectrum itself, whether or not a decodable frame is present. It is **rung 3** of the ladder, natively exposed by some Atheros (ath9k/ath10k) and other parts and used for interference hunting and non-Wi-Fi signal detection.

### Template RAM
On-chip memory that stores prebuilt frame/waveform templates the MAC/PHY streams out during transmission (e.g. ACK templates). Because its contents drive what the front-end emits, writing custom samples into template/scratch RAM is a known route toward arbitrary-waveform TX on otherwise-locked chips.

### Tuner
The RF front-end block (or separate chip) that selects and downconverts the desired band to baseband/IF — the analog gateway between antenna and ADC. In the RTL-SDR lineage the tuner (e.g. R820T) paired with a demod chip is exactly what made cheap DVB-T dongles into SDRs. See [RTL-SDR lineage](../projects/rtl-sdr-lineage.md).

### ucode (microcode)
Small, purpose-built instruction streams executed by a dedicated in-silicon engine (e.g. Broadcom's d11 MAC core) to meet hard real-time MAC/PHY deadlines the main CPU cannot. Patching ucode reaches deeper into the radio than patching the ARM firmware alone. (See also **D11 ucode**.)

### Xtensa
The Tensilica Xtensa (and LX-series) configurable CPU architecture, notably the core inside Espressif's ESP32/ESP8266. Because Espressif ships relatively open SDKs and the Xtensa toolchain is well understood, these parts are unusually accessible for CSI and low-level RF experiments. See [Espressif chips](../chips/espressif.md).

---

## Summary table

| Term | One-line meaning | Ladder / flag tie-in |
|---|---|---|
| Monitor mode / RFMON | Capture all frames on a channel, unassociated | Rung 1 (`monitor`) |
| Injection | Transmit arbitrary 802.11 frames | Rung 1 (`injection`) |
| CSI | Per-subcarrier amplitude + phase | Rung 2 (`csi`) |
| Beamforming feedback | Standardized channel report, CSI-like | Rung 2 path |
| Spectral scan | Raw FFT bins across channel | Rung 3 (`spectral-scan`) |
| Arbitrary waveform | TX an authored IQ buffer | Rung 4 (`arbitrary-waveform`) |
| IQ samples / raw-IQ | Complex baseband, native SDR currency | Rung 4-5 (`raw-iq`) |
| Open PHY / ucode+blob open | Documented/open firmware, PHY is yours | Rung 5 (`open-firmware`) |
| FMCW | Swept-frequency radar waveform | `fmcw`, `radar` |
| Passive radar | Sense via reflections of others' TX | `passive-radar` |
| Covert channel / CTC | Hide/relay data across an unintended medium | `covert-channel` |
| Nexmon / D11 ucode / b43-tools | Broadcom firmware/ucode patching | RE tooling |
| brcmfmac / iwlwifi / mt76 | Host drivers (Broadcom / Intel / MediaTek) | Attack surface |
| RSSI / radiotap / DFS / FTM | Telemetry surfaces the chip already exposes | Data sources |
| OTP / template RAM / DMA ring | On-chip structures you re-task in firmware | Unlock mechanics |
| PlutoSDR / HackRF / USRP | True-SDR yardsticks | Rung 5 reference |

For the full ladder-and-flags model these terms plug into, see [taxonomy](../docs/taxonomy.md).
