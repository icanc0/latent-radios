# Index by capability

A capability-first view of the catalog, generated directly from [`data/modules.json`](../data/modules.json) by [`scripts/build_index.py`](../scripts/build_index.py) — always exactly in sync with the database. For the two most common flags (`monitor`, `injection`) only counts are shown; browse [`data/modules.csv`](../data/modules.csv) for full lists. See [taxonomy.md](taxonomy.md) for meanings and [methodology.md](methodology.md) for scoring.

## Capability totals

| Capability | Count | Meaning |
|---|---:|---|
| `csi` | 91 | Per-subcarrier channel state (Tier 2 sensing) |
| `spectral-scan` | 71 | Raw PHY FFT bins (Tier 3) |
| `raw-iq` | 48 | Time-domain IQ access |
| `arbitrary-waveform` | 33 | Author & transmit baseband IQ (Tier 4) |
| `radar` | 34 | Radar sensing mode |
| `fmcw` | 16 | FMCW ranging radar |
| `passive-radar` | 5 | Passive/bistatic radar |
| `covert-channel` | 46 | Non-native / cross-technology emission |
| `open-firmware` | 44 | Open or documented firmware/PHY |
| `injection` | 321 | Byte-exact frame transmit |
| `monitor` | 459 | RFMON capture of all frames |

## `csi` — Per-subcarrier channel state (Tier 2 sensing) (91)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi — open-PHY 802.11a/g/n baseband on Zynq + AD9361/AD9364 | Analog Devices | 5 (open PHY / SDR) | verified |
| ANTSDR / E310 (openwifi) | MicroPhase | 5 (open PHY / SDR) | verified |
| BCM2711 (Raspberry Pi 4 / 400 / CM4) | Raspberry Pi | 4 (arbitrary-IQ TX) | verified |
| BCM2712 (Raspberry Pi 5 / CM5) | Raspberry Pi | 4 (arbitrary-IQ TX) | reported |
| Mesh Rider / Smart Radio | Doodle Labs | 3 (spectral) | reported |
| AR9003 SoC (ath9k) | Qualcomm | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm | 3 (spectral) | verified |
| AR9003 (ath9k) | Qualcomm | 3 (spectral) | verified |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| AR93xx / QCA955x (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003 / QCA9300) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| AR93xx | Qualcomm Atheros | 3 (spectral) | verified |
| SX-PCEGN | Silex Technology | 3 (spectral) | reported |
| WPEA | SparkLAN | 3 (spectral) | reported |
| AP62xx | AMPAK | 2 (CSI) | reported |
| AP62xx | AMPAK | 2 (CSI) | reported |
| AP63xx | AMPAK | 2 (CSI) | reported |
| AW-CM | AzureWave | 2 (CSI) | reported |
| BCM433x (802.11ac 1x1) | Broadcom | 2 (CSI) | reported |
| BCM434xx (802.11ac 1x1) | Broadcom | 2 (CSI) | reported |
| BCM434xx (Nexmon) | Broadcom | 2 (CSI) | verified |
| BCM43xx (FullMAC / Nexmon) | Broadcom | 2 (CSI) | verified |
| BCM43xx (802.11ac 4x4) | Broadcom | 2 (CSI) | reported |
| BCM4368x (802.11ax FullMAC) | Broadcom | 2 (CSI) | verified |
| CL2x4x / CL6000 Denali | Celeno | 2 (CSI) | reported |
| ESP32 | Espressif | 2 (CSI) | verified |
| ESP32-C3 | Espressif | 2 (CSI) | verified |
| ESP32-C3-WROOM | Espressif | 2 (CSI) | verified |
| ESP32-C (RISC-V) | Espressif | 2 (CSI) | verified |
| ESP32-C6 | Espressif | 2 (CSI) | verified |
| ESP32-C6-WROOM | Espressif | 2 (CSI) | verified |
| ESP32-C (RISC-V) | Espressif | 2 (CSI) | verified |
| ESP32 CSI | Espressif | 2 (CSI) | verified |
| ESP32-S2 | Espressif | 2 (CSI) | verified |
| ESP32-S3 | Espressif | 2 (CSI) | verified |
| ESP32-S3-WROOM | Espressif | 2 (CSI) | verified |
| ESP32-WROOM | Espressif | 2 (CSI) | verified |
| ESP32 (Xtensa LX6) | Espressif | 2 (CSI) | verified |
| ESP8266 | Espressif | 2 (CSI) | reported |
| AX200 (Cyclone Peak) | Intel | 2 (CSI) | verified |
| AX210 (Typhoon Peak) | Intel | 2 (CSI) | verified |
| Wi-Fi 6E AX200/AX210 (iwlwifi) | Intel | 2 (CSI) | verified |
| BE200 (Gale Peak 2) | Intel | 2 (CSI) | reported |
| Ultimate-N 5000-series | Intel | 2 (CSI) | verified |
| Wi-Fi Link 5300 (iwlwifi) | Intel | 2 (CSI) | verified |
| MT7915 / MT7916 (ConnAC Wi-Fi 6) | MediaTek | 2 (CSI) | verified |
| MT798x (Filogic, connac2 SoC) | MediaTek | 2 (CSI) | reported |
| MT7981 / mt7976 (Filogic 820) | MediaTek | 2 (CSI) | verified |
| Filogic (ConnAC2 802.11ax SoC) | MediaTek | 2 (CSI) | reported |
| Filogic | MediaTek | 2 (CSI) | reported |
| Filogic | MediaTek | 2 (CSI) | reported |
| MT7996 (Filogic, connac3) | MediaTek | 2 (CSI) | reported |
| MT7996 (Filogic, connac3) | MediaTek | 2 (CSI) | reported |
| Type 1LD | Murata | 2 (CSI) | reported |
| NXP Trimension UWB | NXP | 2 (CSI) | reported |
| DW1000/DW3000 UWB | Qorvo | 2 (CSI) | verified |
| WiGig 60 GHz (802.11ad) | Qualcomm | 2 (CSI) | reported |
| AR93xx SoC | Qualcomm Atheros | 2 (CSI) | verified |
| QCA6174 (ath10k client 802.11ac) | Qualcomm Atheros | 2 (CSI) | reported |
| AR9x SoC | Qualcomm Atheros | 2 (CSI) | verified |
| QSR (Topaz/Ruby) | Quantenna | 2 (CSI) | reported |
| Ameba D | Realtek | 2 (CSI) | verified |
| Ameba (AmebaLite MCU) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaDplus MCU) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaSmart SoC) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaPro2 SoC) | Realtek | 2 (CSI) | verified |
| u-blox NORA-W (ESP32 carrier) | u-blox | 2 (CSI) | verified |
| u-blox NORA-W | u-blox | 2 (CSI) | verified |
| Wi-Fi IoT modules | Ai-Thinker | 1 (monitor+inject) | reported |
| BCM43xx (FullMAC / Nexmon) | Broadcom | 1 (monitor+inject) | verified |
| Wi-Fi IoT modules | Tuya | 1 (monitor+inject) | reported |

## `spectral-scan` — Raw PHY FFT bins (Tier 3) (71)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| Airspy R2 / Mini / HF+ Discovery | Airspy | 5 (open PHY / SDR) | verified |
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| HackRF One | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| HackRF | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| KrakenSDR coherent RTL-SDR array | KrakenRF | 5 (open PHY / SDR) | verified |
| ANTSDR / E310 (openwifi) | MicroPhase | 5 (open PHY / SDR) | verified |
| RTL2832U + R820T2/R828D | Realtek | 5 (open PHY / SDR) | verified |
| RSP1A / RSPdx-R2 | SDRplay | 5 (open PHY / SDR) | verified |
| BCM2711 (Raspberry Pi 4 / 400 / CM4) | Raspberry Pi | 4 (arbitrary-IQ TX) | verified |
| BCM2712 (Raspberry Pi 5 / CM5) | Raspberry Pi | 4 (arbitrary-IQ TX) | reported |
| Mesh Rider / Smart Radio | Doodle Labs | 3 (spectral) | reported |
| Ubertooth (CC2400 + LPC17xx) | Great Scott Gadgets | 3 (spectral) | verified |
| IPQ40xx (ath10k) | Qualcomm | 3 (spectral) | verified |
| IPQ40xx Dakota | Qualcomm | 3 (spectral) | verified |
| IPQ50xx Maple | Qualcomm | 3 (spectral) | reported |
| IPQ60xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| IPQ60xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| IPQ60xx Cypress | Qualcomm | 3 (spectral) | verified |
| IPQ806x (network SoC) | Qualcomm | 3 (spectral) | reported |
| IPQ807x (ath11k) | Qualcomm | 3 (spectral) | reported |
| IPQ807x (ath11k) | Qualcomm | 3 (spectral) | reported |
| IPQ807x (ath11k) | Qualcomm | 3 (spectral) | reported |
| IPQ807x Hawkeye | Qualcomm | 3 (spectral) | verified |
| IPQ95xx Waikiki | Qualcomm | 3 (spectral) | reported |
| QCA639x / FastConnect 6800 | Qualcomm | 3 (spectral) | reported |
| AR9003 SoC (ath9k) | Qualcomm | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm | 3 (spectral) | verified |
| AR9003 (ath9k) | Qualcomm | 3 (spectral) | verified |
| QCA98xx (ath10k) | Qualcomm | 3 (spectral) | verified |
| QCA98xx (ath10k) | Qualcomm | 3 (spectral) | verified |
| QCA98xx (ath10k) | Qualcomm | 3 (spectral) | verified |
| QCA99xx (ath10k) | Qualcomm | 3 (spectral) | verified |
| QCN50xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| QCN50xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| QCN60xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| QCN90xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| QCN90xx (ath11k) | Qualcomm | 3 (spectral) | reported |
| WCN685x / FastConnect 6900 | Qualcomm | 3 (spectral) | reported |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9002 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9002) | Qualcomm Atheros | 3 (spectral) | verified |
| AR93xx / QCA955x (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 SoC (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003 / QCA9300) | Qualcomm Atheros | 3 (spectral) | verified |
| AR9003 (ath9k) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| ath9k (AR9003) | Qualcomm Atheros | 3 (spectral) | verified |
| AR93xx | Qualcomm Atheros | 3 (spectral) | verified |
| ath10k (11ac wave-1) | Qualcomm Atheros | 3 (spectral) | verified |
| ath10k (11ac wave-2) | Qualcomm Atheros | 3 (spectral) | verified |
| SX-PCEGN | Silex Technology | 3 (spectral) | reported |
| WPEA | SparkLAN | 3 (spectral) | reported |
| WPEQ | SparkLAN | 3 (spectral) | reported |
| SimpleLink CC13xx/CC26xx | Texas Instruments | 3 (spectral) | verified |
| CC24xx transceiver | Texas Instruments | 3 (spectral) | verified |
| AR93xx SoC | Qualcomm Atheros | 2 (CSI) | verified |
| AR9x SoC | Qualcomm Atheros | 2 (CSI) | verified |
| CC111x/CC251x + RfCat | Great Scott Gadgets | 1 (monitor+inject) | verified |
| Gecko wireless modules (BGM/MGM/FGM) | Silicon Labs | 1 (monitor+inject) | verified |
| EFR32 Flex/Mighty Gecko | Silicon Labs | 1 (monitor+inject) | verified |

## `raw-iq` — Time-domain IQ access (48)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| Airspy R2 / Mini / HF+ Discovery | Airspy | 5 (open PHY / SDR) | verified |
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADALM-PLUTO (PlutoSDR) | Analog Devices | 5 (open PHY / SDR) | verified |
| MAX2771 GNSS RF front-end | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi — open-PHY 802.11a/g/n baseband on Zynq + AD9361/AD9364 | Analog Devices | 5 (open PHY / SDR) | verified |
| USRP B200/B210/N210/N310 | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| HackRF One | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| HackRF | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| BGT24 24 GHz radar transceiver | Infineon | 5 (open PHY / SDR) | verified |
| KrakenSDR coherent RTL-SDR array | KrakenRF | 5 (open PHY / SDR) | verified |
| LimeSDR / LimeSDR Mini | Lime Microsystems | 5 (open PHY / SDR) | verified |
| ANTSDR / E310 (openwifi) | MicroPhase | 5 (open PHY / SDR) | verified |
| bladeRF 2.0 micro xA4 / xA9 | Nuand | 5 (open PHY / SDR) | verified |
| RTL2832U + R820T2/R828D | Realtek | 5 (open PHY / SDR) | verified |
| RSP1A / RSPdx-R2 | SDRplay | 5 (open PHY / SDR) | verified |
| Arbe imaging radar | Arbe Robotics | 4 (arbitrary-IQ TX) | reported |
| HackRF PortaPack | Great Scott Gadgets | 4 (arbitrary-IQ TX) | verified |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV 60 GHz FMCW radar (Google Soli) | Infineon | 4 (arbitrary-IQ TX) | verified |
| AT86RF215 dual-band 802.15.4g + I/Q radio | Microchip | 4 (arbitrary-IQ TX) | verified |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| SE41xx GPS L1 RF front-end | Skyworks | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| mmWave single-chip FMCW radar (IWR/AWR) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| Uhnder digital radar | Uhnder | 4 (arbitrary-IQ TX) | reported |
| MAX2769 | Analog Devices | 3 (spectral) | verified |
| XENSIV radar | Infineon | 3 (spectral) | verified |
| NXP 77 GHz automotive radar transceiver | NXP | 3 (spectral) | reported |
| DW3000-series HRP-UWB transceiver | Qorvo | 3 (spectral) | verified |
| DW3000-series HRP-UWB transceiver (dual-RX, PDoA/AoA) | Qorvo | 3 (spectral) | reported |
| DWM3001C UWB module / DWM3001CDK dev kit | Qorvo | 3 (spectral) | verified |
| QM33xxx FiRa-Certified HRP-UWB transceiver | Qorvo | 3 (spectral) | reported |
| SE4110 / SE4120 | Skyworks | 3 (spectral) | reported |

## `arbitrary-waveform` — Author & transmit baseband IQ (Tier 4) (33)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADALM-PLUTO (PlutoSDR) | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi — open-PHY 802.11a/g/n baseband on Zynq + AD9361/AD9364 | Analog Devices | 5 (open PHY / SDR) | verified |
| USRP B200/B210/N210/N310 | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| HackRF One | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| HackRF | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| BGT24 24 GHz radar transceiver | Infineon | 5 (open PHY / SDR) | verified |
| LimeSDR / LimeSDR Mini | Lime Microsystems | 5 (open PHY / SDR) | verified |
| ANTSDR / E310 (openwifi) | MicroPhase | 5 (open PHY / SDR) | verified |
| bladeRF 2.0 micro xA4 / xA9 | Nuand | 5 (open PHY / SDR) | verified |
| HackRF PortaPack | Great Scott Gadgets | 4 (arbitrary-IQ TX) | verified |
| XENSIV 60 GHz FMCW radar (Google Soli) | Infineon | 4 (arbitrary-IQ TX) | verified |
| AT86RF215 dual-band 802.15.4g + I/Q radio | Microchip | 4 (arbitrary-IQ TX) | verified |
| BCM2711 (Raspberry Pi 4 / 400 / CM4) | Raspberry Pi | 4 (arbitrary-IQ TX) | verified |
| BCM2712 (Raspberry Pi 5 / CM5) | Raspberry Pi | 4 (arbitrary-IQ TX) | reported |
| Uhnder digital radar | Uhnder | 4 (arbitrary-IQ TX) | reported |
| RTC6705 5.8 GHz analog-FM video Tx | Richwave | 3 (spectral) | verified |
| SimpleLink CC13xx/CC26xx | Texas Instruments | 3 (spectral) | verified |
| Flipper Zero Sub-GHz (TI CC1101) | Flipper Devices | 1 (monitor+inject) | verified |
| CC111x/CC251x + RfCat | Great Scott Gadgets | 1 (monitor+inject) | verified |
| LoRa (SX127x/SX126x) + FSK/OOK | Semtech | 1 (monitor+inject) | verified |
| EFR32 Flex/Mighty Gecko | Silicon Labs | 1 (monitor+inject) | verified |
| EFR32 Series 2 (xG21/22/23/24/25/27/28) | Silicon Labs | 1 (monitor+inject) | reported |
| CCxxxx sub-GHz transceiver | Texas Instruments | 1 (monitor+inject) | verified |
| CC25xx 2.4 GHz transceiver | Texas Instruments | 1 (monitor+inject) | verified |

## `radar` — Radar sensing mode (34)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| USRP B200/B210/N210/N310 | Ettus Research | 5 (open PHY / SDR) | verified |
| BGT24 24 GHz radar transceiver | Infineon | 5 (open PHY / SDR) | verified |
| KrakenSDR coherent RTL-SDR array | KrakenRF | 5 (open PHY / SDR) | verified |
| Arbe imaging radar | Arbe Robotics | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV 60 GHz FMCW radar (Google Soli) | Infineon | 4 (arbitrary-IQ TX) | verified |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| mmWave single-chip FMCW radar (IWR/AWR) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| Uhnder digital radar | Uhnder | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 3 (spectral) | verified |
| NXP 77 GHz automotive radar transceiver | NXP | 3 (spectral) | reported |
| DW3000-series HRP-UWB transceiver | Qorvo | 3 (spectral) | verified |
| DW3000-series HRP-UWB transceiver (dual-RX, PDoA/AoA) | Qorvo | 3 (spectral) | reported |
| DWM3001C UWB module / DWM3001CDK dev kit | Qorvo | 3 (spectral) | verified |
| QM33xxx FiRa-Certified HRP-UWB transceiver | Qorvo | 3 (spectral) | reported |
| CL2x4x / CL6000 Denali | Celeno | 2 (CSI) | reported |
| 802.11ad WiGig router (QCA9500) | Netgear | 2 (CSI) | reported |
| DW1000/DW3000 UWB | Qorvo | 2 (CSI) | verified |
| WiGig 802.11ad (Sparrow) | Qualcomm Atheros | 2 (CSI) | verified |
| 802.11ad WiGig router (Sparrow / QCA9500-class) | TP-Link | 2 (CSI) | verified |

## `fmcw` — FMCW ranging radar (16)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| BGT24 24 GHz radar transceiver | Infineon | 5 (open PHY / SDR) | verified |
| Arbe imaging radar | Arbe Robotics | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV radar | Infineon | 4 (arbitrary-IQ TX) | reported |
| XENSIV 60 GHz FMCW radar (Google Soli) | Infineon | 4 (arbitrary-IQ TX) | verified |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| NXP automotive radar | NXP | 4 (arbitrary-IQ TX) | reported |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (1st gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| AWR mmWave (2nd gen) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| mmWave single-chip FMCW radar (IWR/AWR) | Texas Instruments | 4 (arbitrary-IQ TX) | verified |
| NXP 77 GHz automotive radar transceiver | NXP | 3 (spectral) | reported |
| CL2x4x / CL6000 Denali | Celeno | 2 (CSI) | reported |

## `passive-radar` — Passive/bistatic radar (5)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ADALM-PLUTO (PlutoSDR) | Analog Devices | 5 (open PHY / SDR) | verified |
| USRP B200/B210/N210/N310 | Ettus Research | 5 (open PHY / SDR) | verified |
| KrakenSDR coherent RTL-SDR array | KrakenRF | 5 (open PHY / SDR) | verified |
| bladeRF 2.0 micro xA4 / xA9 | Nuand | 5 (open PHY / SDR) | verified |
| RTL2832U + R820T2/R828D | Realtek | 5 (open PHY / SDR) | verified |

## `covert-channel` — Non-native / cross-technology emission (46)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| BCM43xx D11 SoftMAC (OpenFWWF open firmware) | Broadcom | 5 (open PHY / SDR) | verified |
| HackRF PortaPack | Great Scott Gadgets | 4 (arbitrary-IQ TX) | verified |
| RTC6705 5.8 GHz analog-FM video Tx | Richwave | 3 (spectral) | verified |
| AP62xx | AMPAK | 2 (CSI) | reported |
| ESP32 | Espressif | 2 (CSI) | verified |
| ESP32-C3 | Espressif | 2 (CSI) | verified |
| ESP32-C6 | Espressif | 2 (CSI) | verified |
| ESP32-S2 | Espressif | 2 (CSI) | verified |
| ESP32-S3 | Espressif | 2 (CSI) | verified |
| ESP8266 | Espressif | 2 (CSI) | reported |
| Type 1LD | Murata | 2 (CSI) | reported |
| NXP Trimension UWB | NXP | 2 (CSI) | reported |
| 3db UWB | 3db Access | 1 (monitor+inject) | reported |
| ASR58xx | ASR Microelectronics | 1 (monitor+inject) | reported |
| BK72xx | Beken | 1 (monitor+inject) | verified |
| BK72xx | Beken | 1 (monitor+inject) | verified |
| BK72xx | Beken | 1 (monitor+inject) | reported |
| BK72xx | Beken | 1 (monitor+inject) | reported |
| Sub-GHz/2.4 GHz carrier modules over Semtech/TI/SiLabs die | Ebyte/NiceRF | 1 (monitor+inject) | verified |
| RFM69 GFSK/OOK module (Semtech SX1231) | HopeRF | 1 (monitor+inject) | verified |
| RFM9xW LoRa module (Semtech SX127x) | HopeRF | 1 (monitor+inject) | verified |
| nRF24 (Enhanced ShockBurst) | Nordic Semiconductor | 1 (monitor+inject) | verified |
| nRF51 | Nordic Semiconductor | 1 (monitor+inject) | verified |
| nRF5x RADIO peripheral | Nordic Semiconductor | 1 (monitor+inject) | verified |
| NXP Trimension UWB | NXP | 1 (monitor+inject) | reported |
| NXP Trimension UWB | NXP | 1 (monitor+inject) | reported |
| PHY62xx | PhyPlus | 1 (monitor+inject) | reported |
| Ameba (AmebaZ) | Realtek | 1 (monitor+inject) | verified |
| Ameba (AmebaZ2) | Realtek | 1 (monitor+inject) | verified |
| LR11xx LoRa Connect | Semtech | 1 (monitor+inject) | reported |
| SX126x LoRa/FSK transceiver | Semtech | 1 (monitor+inject) | verified |
| LoRa (SX127x/SX126x) + FSK/OOK | Semtech | 1 (monitor+inject) | verified |
| SX128x 2.4 GHz LoRa/FLRC/GFSK transceiver | Semtech | 1 (monitor+inject) | verified |
| EZRadioPRO Si443x / Si4438 sub-GHz transceiver | Silicon Labs | 1 (monitor+inject) | verified |
| EZRadioPRO Si446x sub-GHz transceiver | Silicon Labs | 1 (monitor+inject) | verified |
| STM32WL LoRa SoC (SX126x radio + Cortex-M4/M0+) | STMicroelectronics | 1 (monitor+inject) | verified |
| TLSR (825x / 827x / 921x) | Telink Semiconductor | 1 (monitor+inject) | verified |
| CC120x high-performance sub-GHz FSK transceiver | Texas Instruments | 1 (monitor+inject) | verified |
| CC25xx 2.4 GHz transceiver | Texas Instruments | 1 (monitor+inject) | verified |

## `open-firmware` — Open or documented firmware/PHY (44)

| Chip / family | Vendor | Tier | Status |
|---|---|---|---|
| ZC706 + FMCOMMS (openwifi) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq UltraScale+ (ZCU102 + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7000 (ZedBoard + AD-FMCOMMS2/3/4) | AMD/Xilinx | 5 (open PHY / SDR) | verified |
| ADRV9361-Z7035 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| ADRV9364-Z7020 (openwifi) | Analog Devices | 5 (open PHY / SDR) | verified |
| openwifi on Zynq-7020 + AD9361 (LibreSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi on Zynq-7020 + AD9361 (NeptuneSDR clone) | Analog Devices | 5 (open PHY / SDR) | reported |
| openwifi — open-PHY 802.11a/g/n baseband on Zynq + AD9361/AD9364 | Analog Devices | 5 (open PHY / SDR) | verified |
| BCM43xx (SoftMAC / b43) | Broadcom | 5 (open PHY / SDR) | verified |
| BCM43xx D11 SoftMAC (OpenFWWF open firmware) | Broadcom | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| USRP | Ettus Research | 5 (open PHY / SDR) | verified |
| HackRF | Great Scott Gadgets | 5 (open PHY / SDR) | verified |
| ANTSDR / E310 (openwifi) | MicroPhase | 5 (open PHY / SDR) | verified |
| HackRF PortaPack | Great Scott Gadgets | 4 (arbitrary-IQ TX) | verified |
| Mesh Rider / Smart Radio | Doodle Labs | 3 (spectral) | reported |
| Ubertooth (CC2400 + LPC17xx) | Great Scott Gadgets | 3 (spectral) | verified |
| CC24xx transceiver | Texas Instruments | 3 (spectral) | verified |
| 802.11ad WiGig router (QCA9500) | Netgear | 2 (CSI) | reported |
| WiGig 60 GHz (802.11ad) | Qualcomm | 2 (CSI) | reported |
| WiGig 802.11ad (Sparrow) | Qualcomm Atheros | 2 (CSI) | verified |
| Ameba D | Realtek | 2 (CSI) | verified |
| Ameba (AmebaLite MCU) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaDplus MCU) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaSmart SoC) | Realtek | 2 (CSI) | verified |
| Ameba (AmebaPro2 SoC) | Realtek | 2 (CSI) | verified |
| 802.11ad WiGig router (Sparrow / QCA9500-class) | TP-Link | 2 (CSI) | verified |
| BCM43xx SoftMAC (AirForce) | Broadcom | 1 (monitor+inject) | verified |
| BCM43xx (D11 MAC, G-PHY) | Broadcom | 1 (monitor+inject) | verified |
| BCM434xx FullMAC | Broadcom | 1 (monitor+inject) | verified |
| BCM43xx Wi-Fi 7 | Broadcom | 1 (monitor+inject) | reported |
| CC111x/CC251x + RfCat | Great Scott Gadgets | 1 (monitor+inject) | verified |
| nRF5x RADIO peripheral | Nordic Semiconductor | 1 (monitor+inject) | verified |
| nRF53 | Nordic Semiconductor | 1 (monitor+inject) | verified |
| nRF54L | Nordic Semiconductor | 1 (monitor+inject) | reported |
| Atheros ath9k_htc (USB bridge SoC) | Qualcomm Atheros | 1 (monitor+inject) | verified |
| AR9170 | Qualcomm Atheros | 1 (monitor+inject) | verified |
| Atheros ath9k_htc (USB 802.11n) | Qualcomm Atheros | 1 (monitor+inject) | verified |
| Ameba (Ameba1 MCU) | Realtek | 1 (monitor+inject) | verified |
| Ameba (AmebaZ MCU) | Realtek | 1 (monitor+inject) | verified |
| STM32WL LoRa SoC (SX126x radio + Cortex-M4/M0+) | STMicroelectronics | 1 (monitor+inject) | verified |
| TLSR (825x / 827x / 921x) | Telink Semiconductor | 1 (monitor+inject) | verified |
| W60x | Winner Micro | 0 (black box) | reported |
| W80x | Winner Micro | 0 (black box) | reported |

## `injection` — Byte-exact frame transmit (321)

321 modules across 63 vendors. Top: Qualcomm Atheros (36), Broadcom (32), Intel (29), MediaTek (29), Realtek (19), Espressif (14), Texas Instruments (13), Ralink (11), Qualcomm (8), u-blox (7). Full list in [`data/modules.csv`](../data/modules.csv).

## `monitor` — RFMON capture of all frames (459)

459 modules across 75 vendors. Top: Realtek (54), Qualcomm (48), Broadcom (43), Qualcomm Atheros (37), Intel (37), MediaTek (33), Espressif (17), Texas Instruments (13), Ralink (11), u-blox (9). Full list in [`data/modules.csv`](../data/modules.csv).

## By tier

| Tier | Name | Count |
|---|---|---:|
| 0 | black box | 94 |
| 1 | monitor+inject | 334 |
| 2 | CSI | 59 |
| 3 | spectral | 61 |
| 4 | arbitrary-IQ TX | 19 |
| 5 | open PHY / SDR | 25 |

*592 modules total.*
