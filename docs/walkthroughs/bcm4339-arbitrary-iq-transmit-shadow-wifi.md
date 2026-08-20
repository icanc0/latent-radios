# Reproducing arbitrary-IQ transmit on the BCM4339 (Shadow Wi-Fi)

> **Tier 4, made concrete.** This is the crown-jewel demonstration of the whole catalog: a stock 2013-era smartphone Wi-Fi chip loading a user-supplied complex-baseband buffer into its transmit datapath and keying the power amplifier, turning a Nexus 5 into a crude but real transmit-only SDR in the 2.4 / 5 GHz bands. It is also the single easiest way in this catalog to break the law by accident. Read the safety section before you build anything.

- **Paper:** Matthias Schulz, Jakob Link, Francesco Gringoli, Matthias Hollick. *Shadow Wi-Fi: Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi.* Proc. 16th ACM MobiSys 2018, pp. 256–268. DOI [10.1145/3210240.3210333](https://doi.org/10.1145/3210240.3210333).
- **Code:** [`seemoo-lab/mobisys2018_nexmon_software_defined_radio`](https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio) (a Nexmon patch, not a standalone firmware).
- **Silicon:** Broadcom **BCM4339** (Nexus 5) and **BCM43455c0** (Raspberry Pi 3 B+). See [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md) for the chip family and [`../../projects/nexmon.md`](../../projects/nexmon.md) for the framework this rides on.
- **Cross-check:** the Tier-4 evidence bar in [`../../docs/verification-tier4.md`](../../docs/verification-tier4.md) and the regulatory/safety rules in [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md).

---

## 1. What it actually does

Broadcom's ACPHY (802.11ac PHY) has a **sample-play** facility: a block of on-chip **Template RAM** can be streamed through the transmit chain to the DAC and PA, normally used for calibration tones and internally generated waveforms. Shadow Wi-Fi does not build a new radio — it **repurposes this existing sample-play path** and exposes it through three new ioctls:

1. You write raw int16 I/Q pairs into Template RAM.
2. You tell the PHY "play *N* samples starting at offset *X*, on this chanspec, at this gain index, looping or once."
3. The PHY keys the PA and clocks the buffer out through the normal TX RF front end.

The chip becomes an **arbitrary-waveform generator** whose baseband you control sample-by-sample. Because the buffer is small and replays in a loop, the natural output is a short waveform repeated continuously: tones, chirps, OFDM symbols, spoofed/"shadow" 802.11 frames, or arbitrary covert signaling — anything you can fit in the buffer and clock out at the channel's sample rate.

It is **not** a full SDR:

- **TX only.** There is no raw-IQ receive path. The "CSI" half of the *Shadow Wi-Fi* paper (per-subcarrier channel estimates) is a **separate** capability, shipped in the companion [`nexmon_csi`](https://github.com/seemoo-lab/nexmon_csi) project — see [`nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md). CSI is channel-frequency-response data, not full raw RX IQ; do not describe this chip as a receive SDR.
- **Short buffer.** Template RAM is a few kilobytes on these parts, so only short waveforms fit; longer signals must be synthesized as a seamless loop.
- **Crude power control.** The PA is driven by a gain *index*, not a calibrated dBm. Output level is approximate and uneven across frequency.

Where this lands on the ladder: **`sdr_tier: 4` — arbitrary-waveform / raw-IQ TX.** Capability flags exercised: `arbitrary-waveform`, `raw-iq` (transmit side), `covert-channel`, plus `open-firmware` by virtue of the Nexmon patch. It reaches Tier 4, not Tier 5, precisely because RX is limited to CSI and the PHY internals remain reverse-engineered rather than documented.

---

## 2. The three ioctls (the whole public interface)

Defined in the patch's `src/ioctl.c`. These numbers are what you pass to `nexutil -s<num>`:

| # | Name | Purpose |
|---|------|---------|
| **426** | `NEX_WRITE_TEMPLATE_RAM` | Writes arbitrary bytes into Template RAM (the raw IQ sample store). Args: `offset`, `length`, then the payload. Internally calls `wlc_bmac_write_template_ram()` via the `tplatewrptr` / `tplatewrdata` PHY registers. |
| **427** | `NEX_SDR_START_TRANSMISSION` | Starts playback. Takes a **20-byte** struct (see below), sets gain via `exp_set_gains_by_index()`, parks the PHY with `wlc_phy_stay_in_carriersearch_acphy()`, programs the start/stop sample pointers, and triggers playback with `wlc_phy_runsamples_acphy()`. |
| **428** | `NEX_SDR_STOP_TRANSMISSION` | Stops a transmission started by 427. |

**The 20-byte start struct** (five little-endian int32 fields, in order):

| Field | Meaning | Value in the shipped example |
|-------|---------|------------------------------|
| `num_samps` | Number of IQ samples to play | length of your waveform |
| `start_offset` | Template RAM start, in **4-byte units** | `1500/4 = 375` (samples are written starting at byte 1500) |
| `chanspec` | Broadcom chanspec | `0x1001` (`= 4097`) |
| `power_index` | TX gain index (higher = more gain) | `40` |
| `endless` | `0` = play once, `1` = loop forever | `0` |

Each IQ sample is **4 bytes**: an int16 I followed by an int16 Q. To find the true Template RAM size limit on *your* firmware, do not trust a magic number from a blog — disassemble `wlc_bmac_write_template_ram` in your own dump and read the bound it checks (see [`ghidra-setup-wifi-firmware.md`](./ghidra-setup-wifi-firmware.md) and [`../../docs/firmware-reversing.md`](../../docs/firmware-reversing.md) for the workflow). The `256*1024` constant that appears in the repo's `case 777` test path is a debug scratch reference, **not** the sample-play bound — do not cite it as the buffer size.

---

## 3. Which firmware it patches

Shadow Wi-Fi is a **Nexmon patch directory**, applied on top of a specific extracted firmware:

| Target | Chip | Firmware | Nexmon patch path | Install target |
|--------|------|----------|-------------------|----------------|
| Nexus 5 | BCM4339 | `6_37_34_43` | `patches/bcm4339/6_37_34_43/` | `make install-firmware` |
| Raspberry Pi 3 B+ | BCM43455c0 | (43455c0 802.11ac) | patched via same repo | `make install-rpi3plus` |

The **Raspberry Pi 3 B (non-plus)** is explicitly **not supported** — it carries an 802.11n PHY, and the sample-play path this project drives is the 802.11ac ACPHY. For the 43455c0 build path and its quirks, cross-reference [`bcm43455c0-raspberry-pi.md`](./bcm43455c0-raspberry-pi.md).

---

## 4. Building it

Reference environment from the repo README: **Xubuntu 16.04 LTS**, **Android NDK r11c** (the exact version — newer NDKs break Nexmon's toolchain assumptions), and a **rooted Nexus 5 on stock Android 6.0.1 build M4B30Z (Dec 2016)**.

```bash
# 1. Host dependencies
sudo apt-get install git gawk qpdf adb
# On x86_64, Nexmon's ARM toolchain needs 32-bit libs:
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install libc6:i386 libncurses5:i386 libstdc++6:i386

# 2. Android NDK r11c — download and point NDK_ROOT at it
export NDK_ROOT=/path/to/android-ndk-r11c

# 3. Nexmon base
git clone https://github.com/seemoo-lab/nexmon.git
cd nexmon
source setup_env.sh          # sets up the cross toolchain + paths
make                          # extract & prep firmware components
cd utilities && make && cd .. # build nexutil et al.

# 4. Drop the Shadow Wi-Fi patch into the matching firmware dir
cd patches/bcm4339/6_37_34_43/
git clone https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio.git
cd mobisys2018_nexmon_software_defined_radio

# 5. Flash the patched firmware to a rooted, adb-connected Nexus 5
make install-firmware
# (Raspberry Pi 3 B+ instead:  make install-rpi3plus)
```

`nexutil` is Nexmon's ioctl front-end and is what carries the SDR ioctls to the running firmware; it is built in step 3 and pushed to the device by Nexmon's install step. The repo's own source lives in `src/`: `patch.c` (hooks/entry), `ioctl.c` (the three ioctls above), `regulations.c` (the regulatory-bypass patches — see §6), `console.c`, `version.c`, plus `Makefile` and `patch.ld`.

---

## 5. Pushing samples — the transmit workflow

The repo ships a MATLAB toolchain under `payload_generation/` that turns a baseband waveform into a runnable script:

- `generate_frame.m` — top-level: synthesizes an 802.11 (beacon) waveform, scales/quantizes it to int16 IQ, and **emits a bash script** of `nexutil` calls.
- `ieee_80211_encoder.m`, `modx.m` — the OFDM encoder / modulation-mapper helpers.
- `myframe.sh` — a shipped example of the generated output.

The complex samples are scaled by **10000** and packed as `(I<<16) | Q` int16 pairs, then base64-encoded for `nexutil -v`. The generated script does exactly two things:

```bash
# (repeated) load the waveform into Template RAM in 1500-byte chunks, ioctl 426:
nexutil -s426 -b -l1500 -v<base64 chunk>
nexutil -s426 -b -l1500 -v<base64 chunk>
...
# then start playback, ioctl 427, with the 20-byte start struct (base64):
nexutil -s427 -b -l20 -v<base64 20-byte struct>
```

Flags: `-s<n>` selects ioctl *n*; `-b` sets binary/base64 payload mode; `-l<len>` is the payload length in bytes; `-v<data>` is the (base64) value. To stop an endless (`endless=1`) transmission:

```bash
nexutil -s428     # NEX_SDR_STOP_TRANSMISSION
```

To transmit your *own* waveform rather than a beacon: generate int16 I/Q at the channel's sample rate, write it with a sequence of `-s426` chunks, then fire `-s427` with `num_samps` = your sample count, `start_offset` = your Template RAM byte offset / 4, a legal `chanspec`, a conservative `power_index`, and `endless` per your need. Keep the total within the Template RAM bound you read out of your own dump (§2).

---

## 6. What waveforms are feasible — and the limits

- **Instantaneous bandwidth** follows the chanspec's channel bandwidth: up to ~**80 MHz** of complex baseband on an 80 MHz 802.11ac channel (the 4339/43455 ACPHY runs the sample-play DAC at the channel sample rate, ~80 Msps for an 80 MHz channel; ~20 Msps for 20 MHz). Your waveform is confined to that channel's passband within the 2.4/5 GHz bands — this is not a wideband or out-of-band radio.
- **Waveform length** is bounded by Template RAM (a few KB → on the order of a few hundred to low-thousands of complex samples). Longer or continuous signals must be built as a **seamless loop** (`endless=1`); discontinuities at the loop seam show up as spectral splatter.
- **Power** is set by a coarse `power_index` (the example uses `40`), not a calibrated dBm, and is not flat across frequency. Treat absolute level as unknown until you measure it on a spectrum analyzer through a cable and attenuator.
- **Good fits:** CW/multi-tone test signals, chirps within a channel, spoofed/"shadow" 802.11 frames, custom OFDM, and covert-channel signaling (the paper's headline application). **Poor fits:** anything needing wide instantaneous bandwidth, precise calibrated power, phase-coherent MIMO, or receive-side raw IQ.

Because this genuinely emits **operator-authored energy into a licensed shared band**, it meets the Tier-4 bar in [`../../docs/verification-tier4.md`](../../docs/verification-tier4.md): arbitrary baseband in, RF out of the antenna port, demonstrated and independently reproducible on named hardware.

---

## 7. Legal and RF-safety cautions — read this before you power the PA

**This is the most dangerous demo in the catalog to run carelessly.** Two facts make that concrete, both visible in the patch's own `src/regulations.c`:

1. It **NOPs out the regulatory power clamp.** The normal firmware calls `ppr_compare_min(tx_pwr_target, srom_max_txpwr)` to hold TX power to the minimum of the requested and the regulatory/SROM limit. The patch replaces that call with a no-op, so `power_index` is honored **without a regulatory ceiling**.
2. It **unlocks illegal channel configurations.** `wf_chspec_malformed_hook` is forced to return 0 (removing, among others, the rejection of *80 MHz channels in the 2.4 GHz band*), and `wlc_valid_chanspec_ext_hook` adds an allow-list of otherwise-invalid chanspecs (80/40 MHz configs on channels like 6/7/106, band-edge channels 120/140, etc.).

So the firmware will happily transmit **arbitrary energy, at uncapped gain, on channels and bandwidths that are illegal to occupy** — including clobbering adjacent licensed users. Consequences of getting this wrong range from jamming your neighbours' Wi-Fi to interfering with safety-of-life services on nearby bands, and to personal legal liability.

Non-negotiable practice (see [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md) for the full rules):

- **Never transmit over the air on a whim.** Do all bring-up **conducted**: antenna port → coax → attenuator → spectrum analyzer or a second receiver, inside a **shielded enclosure / RF chamber**. A Nexus 5 antenna is not a dummy load.
- **Assume you have no license.** Intentional radiators in 2.4/5 GHz are only unlicensed inside strict power/bandwidth/spectral-mask limits that this patch specifically removes. An arbitrary looped waveform is not a compliant Wi-Fi emission and is not covered by those unlicensed allowances.
- **Use the lowest `power_index` that gives usable SNR** in your measurement setup, and keep `num_samps`/duty cycle minimal.
- **Restore stock firmware** (`make install-firmware` with the unpatched build, or reflash the stock image) when you are done experimenting.
- The repo's own license additionally **forbids use by or on behalf of armed/intelligence/defense agencies** and **requires citing** the *Shadow Wi-Fi* MobiSys 2018 paper (or Schulz's 2018 TU Darmstadt PhD thesis) in any resulting publication.

The point of reproducing this is to understand that a commodity phone radio is one firmware patch away from being a lab signal source — **treat it with the same discipline as a bench transmitter**, not as an app.

---

## 8. Reproduce-and-verify checklist

1. Build Nexmon + the `bcm4339/6_37_34_43` patch exactly as §4; confirm `nexutil -V` reports the patched version string (`src/version.c`).
2. Flash a **short, known** waveform (e.g. a single CW tone) with `-s426`, then `-s427` with `endless=0`.
3. Capture **conducted, inside a shielded setup**, on a spectrum analyzer or SDR RX; confirm the tone appears at the expected offset within the chosen channel.
4. Confirm `-s428` stops an `endless=1` transmission.
5. Log gain index vs. measured level so you can pick a minimum safe `power_index`.
6. Record it against the Tier-4 rubric in [`../../docs/verification-tier4.md`](../../docs/verification-tier4.md) with your measurement trace — that trace is the difference between `status: verified` and hearsay.

---

## References

1. Schulz, Link, Gringoli, Hollick. *Shadow Wi-Fi: Teaching Smartphones to Transmit Raw Signals and to Extract Channel State Information to Implement Practical Covert Channels over Wi-Fi.* MobiSys 2018, pp. 256–268. https://doi.org/10.1145/3210240.3210333
2. Repository: https://github.com/seemoo-lab/mobisys2018_nexmon_software_defined_radio (`README.md`, `src/ioctl.c`, `src/regulations.c`, `payload_generation/generate_frame.m`, `payload_generation/myframe.sh`).
3. Nexmon framework: https://github.com/seemoo-lab/nexmon — and [`../../projects/nexmon.md`](../../projects/nexmon.md).
4. Companion CSI extractor: https://github.com/seemoo-lab/nexmon_csi — and [`nexmon-csi-to-usable-csi.md`](./nexmon-csi-to-usable-csi.md).
5. Matthias Schulz. *Teaching Your Wireless Card New Tricks: Smartphone Performance and Security Enhancements through Wi-Fi Firmware Modifications.* PhD thesis, TU Darmstadt, Feb. 2018.
6. Chip background: [`../../chips/broadcom-cypress.md`](../../chips/broadcom-cypress.md); RE workflow: [`../../docs/firmware-reversing.md`](../../docs/firmware-reversing.md), [`ghidra-setup-wifi-firmware.md`](./ghidra-setup-wifi-firmware.md); safety/legal: [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md); Tier-4 bar: [`../../docs/verification-tier4.md`](../../docs/verification-tier4.md).
