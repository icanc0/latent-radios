# PlutoSDR for Wi-Fi experiments — the $150 true-SDR route into 802.11

> Every other walkthrough in *Latent Radios* pries a **closed** Wi-Fi radio open from the outside — patch Broadcom firmware ([Nexmon](../../projects/nexmon.md)), poke undocumented Atheros registers ([ath9k spectral/CSI](./atheros-ath9k-spectral-csi.md)), catch a debug IQ stream that was never meant to escape ([RTL-SDR](../../projects/rtl-sdr-lineage.md)). This page goes the other direction. The **ADALM-PLUTO** is a genuine, full-duplex transceiver SDR: it hands you raw baseband I/Q, and *you* build the 802.11 PHY on top in software. It is the cheapest board on which you can honestly say "I own every sample." This is the affordable end of **Tier 5** — the same rung as [`gr-ieee802-11` on a USRP](../../projects/gr-ieee802-11.md) — reached for roughly the price of a mid-range Wi-Fi router.

The Pluto is the board most Wi-Fi-sensing researchers reach for when they outgrow CSI extraction and want to touch the waveform itself. This walkthrough takes it from an out-of-the-box USB device to **receiving and decoding real 802.11a/g frames** with GNU Radio, covers the frequency-range "hack" that is *mandatory* if you want to reach 5 GHz Wi-Fi at all, walks the full-duplex loopback path for safe transmit experiments, explains why the Pluto itself cannot run [openwifi](../../projects/openwifi.md) (and which Pluto-shaped board can), and ends — as every page here does — with an honest account of where a $150 SDR loses to the $3 chip already in your laptop. For the tier framing across all SDR platforms, see [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md).

Primary upstreams: **[wiki.analog.com/university/tools/pluto](https://wiki.analog.com/university/tools/pluto)** (Analog Devices), **[bastibl/gr-ieee802-11](https://github.com/bastibl/gr-ieee802-11)** (Bastian Bloessl / WIME Project), and **[analogdevicesinc/gr-iio](https://github.com/analogdevicesinc/gr-iio)** (the GNU Radio ↔ Pluto bridge).

---

## 1. What the Pluto is, and where it sits (read this first)

The ADALM-PLUTO ("PlutoSDR") is a self-contained, USB-powered learning SDR built from two chips:

- **Analog Devices AD9363** "RF agile transceiver" — a 12-bit direct-conversion transceiver, **one TX and one RX channel, full-duplex**, tunable **325–3800 MHz** at the spec-graded default, up to **61.44 MSPS** conversion and **20 MHz** channel bandwidth.
- **Xilinx Zynq-7010** SoC (dual Cortex-A9 + a small 7-series FPGA fabric) that runs an embedded Linux, formats the I/Q into a **libiio** stream, and pushes it over **USB 2.0** to the host.

That combination — full-duplex, TX-capable, 12-bit, tunes across the 2.4 GHz ISM band — for ~US$150–230 is why it is the entry point to real 802.11 signal work. Compared to the [`gr-ieee802-11` reference platforms](../../projects/gr-ieee802-11.md): it is cheaper than a USRP B210, and unlike a **HackRF** (8-bit, half-duplex) it is **12-bit and full-duplex**, which matters enormously for the transmit-into-a-cable loopback in §6.

> **The honest tier placement.** The Pluto is *above* this catalog's ladder, not a contestant on it — the ladder grades non-SDR silicon reaching *upward*, and the Pluto is already a true SDR (`raw-iq` + `arbitrary-waveform`, ladder Tier 5 by construction). What makes it *interesting* to this repo is that with `gr-ieee802-11` layered on top it becomes a fully open 802.11 PHY you can read and edit — the yardstick every Nexmon/ath9k/mt76 hack is measured against. See the existing catalog record `analog-adalm-pluto` and [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md).

---

## 2. The frequency-range "hack" — and why 5 GHz Wi-Fi *requires* it

Out of the box the Pluto tunes **325–3800 MHz**. That covers the entire **2.4 GHz** Wi-Fi band (channels 1–14, 2.412–2.484 GHz) comfortably. It does **not** cover **5 GHz** Wi-Fi (U-NII, 5.15–5.85 GHz) — those channels are above the 3.8 GHz ceiling. So if your experiment is 5 GHz 802.11, the "hack" is not optional; it is a prerequisite.

The AD9363 and the wider-range **AD9364** are the **same silicon die**; the AD9363 is simply *spec-graded and guaranteed* over the narrower 325–3800 MHz window. Re-flagging the Pluto's device-tree `compatible` string as an AD9364 lifts the driver's software limits to the AD9364 envelope — **70–6000 MHz**, single channel. From the [Analog Devices "customizing the Pluto" wiki](https://wiki.analog.com/university/tools/pluto/users/customizing), over SSH to the device (default `root` / `analog`):

```bash
# SSH into the Pluto (it enumerates as a USB network device at 192.168.2.1)
ssh root@192.168.2.1

# --- classic method (older firmware) ---
fw_setenv attr_name compatible
fw_setenv attr_val ad9364
reboot

# --- newer firmware (v0.32+) uses a single variable ---
fw_setenv compatible ad9364
reboot
```

After reboot, `iio_attr -a -c ad9361-phy` (or the IIO Oscilloscope) reports the widened tuning range and **1r1t** operation.

> ### What the hack does *not* buy you
> - **It is out of spec at the edges.** Near 70 MHz and near 6 GHz the front-end is **uncalibrated and unguaranteed** — gain flatness, LO phase noise, and image rejection all degrade. Datasheet performance only holds inside the original 325–3800 MHz. For 2.4 GHz Wi-Fi you are inside spec; for 5 GHz U-NII you are in the extended, best-effort region.
> - **It does not reach Wi-Fi 6E.** The **6 GHz** band (5.925–7.125 GHz) sits at and beyond the AD9364's 6000 MHz top edge — treat 6 GHz Wi-Fi as **out of reach** on a Pluto.
> - **It does not add a second channel or bandwidth.** Still 1×1, still 20 MHz max BW. See §7.

---

## 3. Host software stack — libiio and gr-iio

The Pluto speaks **libiio**; GNU Radio talks to it through **gr-iio**, which provides **PlutoSDR Source / PlutoSDR Sink** blocks (and the equivalent **FMComms2/3/4** blocks). Per the [ADI GNU Radio wiki](https://wiki.analog.com/resources/tools-software/linux-software/gnuradio), gr-iio is **bundled inside GNU Radio itself from 3.10 onward**; on older GNU Radio you build it from [analogdevicesinc/gr-iio](https://github.com/analogdevicesinc/gr-iio) (it needs `libiio` and `libad9361-iio`).

```bash
# Debian/Ubuntu: GNU Radio 3.10 already ships gr-iio + libiio
sudo apt install gnuradio gnuradio-dev libiio-dev libad9361-dev \
                 iio-utils cmake build-essential python3-numpy python3-opengl

# One-time SIMD kernel tuning (real-time throughput win at 10–20 Msps)
volk_profile

# Confirm the host sees the Pluto (USB context)
iio_info -u usb:            # lists ad9361-phy, cf-ad9361-lpc, etc.
iio_attr -a -c ad9361-phy   # shows rx/tx LO, sample rate, bandwidth attrs
```

If you prefer the SoapySDR ecosystem, **SoapyPlutoSDR** exposes the same radio as a Soapy device, and gr-ieee802-11's UHD source can be swapped for a Soapy source instead — but gr-iio is the canonical, in-tree path and the one used below.

---

## 4. Receiving and decoding 802.11 with `gr-ieee802-11`

`gr-ieee802-11` is Bastian Bloessl's GNU Radio out-of-tree module implementing a full **802.11a/g/p OFDM transceiver in software** (see [../../projects/gr-ieee802-11.md](../../projects/gr-ieee802-11.md) for the deep dive). Its README officially targets **Ettus USRP N210 / B210**, and it does **not** mention the Pluto — but because the receiver chain is just DSP fed by a GNU Radio source block, **swapping the UHD source for a PlutoSDR source is a supported community workflow**, not a fork. Match the module's `maint-*` branch to your GNU Radio version.

```bash
# gr-foo first (gr-ieee802-11 links against it)
git clone -b maint-3.10 https://github.com/bastibl/gr-foo
cd gr-foo && mkdir build && cd build && cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig && cd ../..

# then gr-ieee802-11
git clone -b maint-3.10 https://github.com/bastibl/gr-ieee802-11
cd gr-ieee802-11 && mkdir build && cd build && cmake .. && make -j"$(nproc)"
sudo make install && sudo ldconfig

# generate the hierarchical PHY block once so the examples can import it
grcc ../examples/wifi_phy_hier.grc
```

**Wiring the Pluto into `examples/wifi_rx.grc`:**

1. Open `wifi_rx.grc` in GNU Radio Companion and **delete the UHD: USRP Source** block.
2. Drop in a **PlutoSDR Source** block. Set:
   - **Device URI:** `usb:` (or `ip:192.168.2.1`)
   - **LO / center frequency:** `2412000000` (channel 1) — or a 5 GHz U-NII channel *only if you applied the §2 AD9364 hack*.
   - **Sample rate:** `20000000` for 802.11a/g (20 MHz), or `10000000` for 802.11p (10 MHz).
   - **RF bandwidth:** match the sample rate (20 MHz / 10 MHz).
   - **Gain mode:** start with `slow_attack` AGC, then pin **manual** gain once you have a signal.
3. Confirm the flowgraph's `samp_rate` variable equals the Pluto rate — the OFDM sync blocks assume samples-per-symbol derived from it.
4. Keep the **gr-foo Wireshark Connector → PCAP** tail; decoded frames appear in Wireshark with radiotap headers (open the FIFO with `wireshark -k -i /tmp/...` or read the pcap). Add the **constellation sink** (`python3-opengl`) to *watch* the BPSK/QPSK/16-/64-QAM clouds tighten as SNR and the equalizer settle — a live view of the PHY no NIC exposes.

Point the antenna at a nearby AP or a phone hotspot on **channel 1** and you should see beacons and data frames decode. Verification: management/beacon frames with a valid FCS in Wireshark, and tightening constellation clusters on the sink.

> **The USB 2.0 sample-rate ceiling — the Pluto's real RX limit.** The AD9363 can *convert* 20 MSPS, but the Pluto's **USB 2.0 High-Speed** link cannot *stream* it losslessly: 20 MSPS × 2 (I/Q) × 2 bytes ≈ **80 MB/s**, well above USB 2.0's ~40 MB/s effective ceiling. Expect **overruns (`RX overflow`/`aU`)** at a sustained 20 Msps. Mitigations, in order of preference: run the **802.11p 10 Msps** mode (comfortably within budget and a first-class `gr-ieee802-11` target); use **burst/one-shot IQ capture** to a file (`iio_readdev`) and decode offline; or enlarge the Pluto's kernel IIO buffers. For continuous, real-time 20 MHz 802.11a/g decode, a USB 3.0 B210/bladeRF is the more comfortable radio — the Pluto shines at 10 Msps and at capture-then-decode.

---

## 5. Capture-then-decode (no real-time pressure)

The most reliable Pluto workflow sidesteps real-time entirely — grab a burst of raw I/Q to disk, then run the software PHY offline where CPU and USB timing no longer race the air:

```bash
# Capture 2 Msamples of raw complex I/Q at channel 1, 20 MHz, to a file
iio_readdev -u usb: -b 2000000 -s 2000000 cf-ad9361-lpc > wifi_ch1.iq

# then decode offline: replace the PlutoSDR Source in wifi_rx.grc with a
# "File Source" (Complex, repeat off) reading wifi_ch1.iq at samp_rate = 20e6
```

This is also the honest way to *learn the PHY*: single-step the sync-short / sync-long / FFT / equalizer / Viterbi chain on a fixed buffer, exactly the visibility the sealed silicon in the rest of this catalog denies you.

---

## 6. Transmitting — full-duplex loopback, into a cable only

The Pluto's standout advantage over a HackRF for this work is that it is **full-duplex 1×1**: it can transmit and receive **at the same time**, so you can feed its own TX straight back into its own RX through a cable and attenuator and watch `gr-ieee802-11` decode what it just encoded — a complete, emissions-free 802.11 link on one desk.

> ### ⚠️ Regulatory / RF-safety warning — read before you enable any TX
>
> A Pluto running `wifi_tx.grc` is an **uncertified intentional radiator**. Transmitting 802.11 over the air with it is trivially easy to do **illegally**, and "it was easy" is not a defense.
>
> - **No equipment authorization.** A commercial Wi-Fi NIC has passed FCC Part 15 (US) / ETSI EN 300 328 (2.4 GHz) / EN 301 893 (5 GHz U-NII) and carries an ID. A Pluto running a GNU Radio flowgraph has passed **nothing**. Operating it as a transmitter in these bands is unlawful in most jurisdictions regardless of power.
> - **Weak output filtering.** The AD9363 front-end has minimal harmonic/spurious filtering; without an external bandpass filter it will splatter energy into adjacent channels and harmonics.
> - **Never** use TX for deauth, beacon spoofing, evil-twin, or jamming — separate criminal offenses on top of the spectrum violation.
>
> **Do this instead — conducted, not radiated.** Connect **Pluto TX → SMA cable → 30–60 dB attenuator → Pluto RX** (a shielded/anechoic enclosure is the alternative). Use the **lowest TX gain** (largest TX attenuation) that still decodes. If you must radiate, do it under an **amateur license** in an amateur allocation, or a formal **experimental license**, inside an RF-shielded chamber. The cabled loopback below covers essentially all the learning value with **zero emissions**.

Two zero/near-zero-emission TX paths:

1. **Pure simulation — `examples/wifi_loopback.grc`.** Wires the TX chain straight into the RX chain through a simulated channel, **no radio at all**. The fastest confidence check that your install encodes what it decodes.
2. **Real hardware, cabled full-duplex.** Open `wifi_tx.grc` (and a paired `wifi_rx`), replace the sinks/sources with a **PlutoSDR Sink** and **PlutoSDR Source** on the *same* device URI (`usb:`), set matching center frequency and sample rate, and set a **high TX attenuation** (e.g. `tx_hardwaregain = -50` dB). With TX and RX SMA ports joined by cable + attenuator, the Pluto's full-duplex path lets you transmit real 802.11 frames and decode them on the same board — a self-contained conducted link.

---

## 7. Running openwifi on the "Pluto path" — and why not on the Pluto itself

A natural question: the Pluto is a Zynq + AD936x board, and [openwifi](../../projects/openwifi.md) is an open 802.11a/g/n stack for Zynq + AD936x — so can the Pluto run openwifi? **No.** The Pluto's **Zynq-7010** has too little FPGA fabric (programmable logic) to fit the full openwifi baseband (OFDM PHY + DCF low-MAC). openwifi's smallest supported parts are **Zynq-7020**.

The "Pluto-form-factor" way to run openwifi is a **Zynq-7020 + AD9361/AD9363** board — most directly the **MicroPhase AntSDR E200 / E310v2** (catalog id `microphase-antsdr-openwifi`), which is a Pluto-shaped, low-cost board that openwifi ships prebuilt images for. Because the 7020 is covered by free Vivado **WebPACK**, you can even rebuild the PHY without a paid license. Community clones (**LibreSDR**, **NeptuneSDR**) are also 7020+AD9361 in a Pluto-ish form factor, with the usual "works, with caveats" disclaimer on clone RF quality.

The distinction is worth internalizing:

| | Pluto + `gr-ieee802-11` (§4) | AntSDR/openwifi |
|---|---|---|
| Where the PHY runs | **Host CPU** (GNU Radio flowgraph) | **FPGA fabric** (Verilog) |
| Real-time MAC (SIFS/ACK) | **No** — host latency ≫ 16 µs SIFS | **Yes** — DCF in FPGA, meets SIFS |
| Can act as a real STA/AP | No (analysis / single-link only) | Yes (`hostapd`, associates to real APs) |
| Edit the modem | Edit Python/C++ DSP blocks | Edit Verilog + resynthesize |
| Board | Pluto (Zynq-7010) | AntSDR E200/E310 (Zynq-7020) |

So the Pluto gives you the *whole PHY in editable software but no real-time MAC*; the Pluto-adjacent 7020 board gives you the *whole PHY+MAC in FPGA* at the cost of a Vivado/HDL toolchain. See [../../projects/openwifi.md](../../projects/openwifi.md) and [openwifi-zynq-bringup.md](./openwifi-zynq-bringup.md).

---

## 8. Limits vs the Wi-Fi chip already in your laptop

This is the crux the whole catalog is built on. The Pluto buys you total, open access to the 802.11 waveform — and pays for it everywhere else.

| Dimension | Pluto + `gr-ieee802-11` | Commercial Wi-Fi NIC (~$3) |
|---|---|---|
| **PHY access** | Total — every sample, every block, arbitrary waveforms | Sealed; narrow windows via firmware RE |
| **Instantaneous BW** | **~20 MHz max** — so 802.11a/g (20 MHz) and 802.11p (10 MHz) only. **Cannot do 40/80/160 MHz** → **no full-rate 802.11n/ac/ax** | 20/40/80/160 MHz native; ac/ax/be line rates |
| **Sustained RX rate** | USB 2.0 ceiling → overruns at 20 Msps; 10 Msps comfortable; capture-then-decode preferred | Dedicated PHY, no host bus in the loop |
| **Real-time MAC** | **None** — no SIFS-timed ACK, no hardware CSMA/CA; cannot properly join a contending BSS | Full hardware MAC (ACK, RTS/CTS, backoff, aggregation) |
| **Latency (air→app)** | milliseconds (USB + host DSP) | microseconds (on-chip) |
| **Bands** | 2.4 GHz stock; 5 GHz U-NII **only after the AD9364 hack** (out of spec at edges); **no 6 GHz** | Whatever the silicon does — up to Wi-Fi 6E/7, 60 GHz |
| **Channels** | 1×1 | 1×1 up to 8×8 MIMO with hardware beamforming |
| **Calibration** | Uncalibrated at extended range; DC offset / I/Q imbalance need nulling | Factory-calibrated within its band |
| **Cost / power** | ~$150–230 + a busy laptop CPU (watts) | ~$3, already installed, milliwatts |

The headline limit is the pair **~20 MHz bandwidth** and **no real-time MAC**: because the Pluto captures only a 20 MHz slice and cannot meet 802.11's microsecond ACK deadlines from a host over USB, it is a superb **analysis / single-link / waveform-authoring** radio and a poor **network participant** — and it structurally **cannot decode full-rate 802.11ac/ax**, whose 80/160 MHz channels are 4–8× wider than it can see at once. The $3 chip in your laptop does all of that in real time, certified, on milliwatts — while hiding the PHY the Pluto lays bare. That trade — **total open access at low speed and narrow bandwidth** vs. **narrow sealed access at full speed and full bandwidth** — is the entire subject of this repository. See [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md).

---

## 9. Quick reference — Pluto Wi-Fi cheat sheet

| Task | Setting |
|---|---|
| 2.4 GHz Wi-Fi ch 1 / 6 / 11 | LO `2412` / `2437` / `2462` MHz (in-spec, no hack) |
| 5 GHz Wi-Fi (U-NII) | **Apply §2 AD9364 hack first**, then LO 5180–5825 MHz (out of spec) |
| 6 GHz Wi-Fi 6E | **Not supported** (≥5.925 GHz, at/above AD9364's 6 GHz top) |
| 802.11a/g | samp_rate `20e6`, RF BW `20e6` (USB2-marginal → capture-then-decode) |
| 802.11p | samp_rate `10e6`, RF BW `10e6` (comfortable real-time) |
| Device URI | `usb:` or `ip:192.168.2.1` |
| Safe TX | Full-duplex loopback: TX → cable → 30–60 dB attenuator → RX, high TX atten |
| Run full open PHY+MAC | Not on Pluto (Z7010 too small) → AntSDR E200/E310 + openwifi |

---

## 10. References (primary)

- **ADALM-PLUTO overview** — Analog Devices University: <https://wiki.analog.com/university/tools/pluto>
- **Customizing the Pluto (AD9364 frequency-range change)** — <https://wiki.analog.com/university/tools/pluto/users/customizing>
- **AD9363 datasheet / product page** — <https://www.analog.com/en/products/ad9363.html>
- **gr-iio (PlutoSDR / FMComms GNU Radio blocks)** — <https://github.com/analogdevicesinc/gr-iio> and <https://wiki.analog.com/resources/tools-software/linux-software/gnuradio>
- **libiio** — <https://github.com/analogdevicesinc/libiio>
- **`gr-ieee802-11`** (802.11a/g/p OFDM transceiver) — B. Bloessl et al., <https://github.com/bastibl/gr-ieee802-11>; companion `gr-foo` <https://github.com/bastibl/gr-foo>; WIME Project <https://www.wime-project.net>
- B. Bloessl, M. Segata, C. Sommer, F. Dressler, "An IEEE 802.11a/g/p OFDM Receiver for GNU Radio," *ACM SIGCOMM SRIF '13*. DOI: 10.1145/2491246.2491248.
- **openwifi** (FPGA open 802.11, the Pluto-adjacent 7020 path) — <https://github.com/open-sdr/openwifi>
- ADALM-PLUTO launch coverage — <https://www.rtl-sdr.com/adalm-pluto-new-149-tx-capable-sdr-325-3800-mhz-range-12-bit-adc-20-mhz-bandwidth/>

*Regulatory references to consult before any transmission:* FCC 47 CFR Part 15 (US, unlicensed); ETSI EN 300 328 (2.4 GHz); ETSI EN 301 893 (5 GHz U-NII / DFS). Conduct all TX experiments into a cable + attenuator or a shielded chamber.

## See also

- [../../projects/gr-ieee802-11.md](../../projects/gr-ieee802-11.md) — the software 802.11 PHY the Pluto runs
- [../../projects/openwifi.md](../../projects/openwifi.md) — FPGA open 802.11 (why the Pluto's Z7010 is too small)
- [../../docs/true-sdr-comparison.md](../../docs/true-sdr-comparison.md) — the true-SDR yardstick and where the Pluto sits
- [./openwifi-zynq-bringup.md](./openwifi-zynq-bringup.md) — bringing up openwifi on a Zynq board
