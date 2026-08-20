# ESP32 Xtensa Firmware in Ghidra + Capturing CSI

> **Walkthrough scope.** This is a two-part, end-to-end guide. **Part A** is the reverse-engineering track: understanding the Xtensa LX6 core, getting firmware off the chip, dealing with the mask ROM, loading it into Ghidra with the community Xtensa processor module, reconstructing the memory map, and locating the Wi-Fi driver hooks inside Espressif's closed `libpp.a` / `libnet80211.a` blobs. **Part B** is the practical radio track: **you do not need to reverse anything to get a usable SDR-lite capability out of an ESP32.** The ESP-IDF ships a native Channel State Information (CSI) API and a raw 802.11 TX call. Part B shows the minimal code to enable both.
>
> **Bottom line up front:** on the SDR ladder the ESP32 sits at **Tier 2** — you get per-subcarrier complex CSI (LLTF + HT-LTF), promiscuous RX, and arbitrary 802.11 frame injection, all from stock, documented APIs. You do **not** get raw IQ, arbitrary waveform TX, or spectral-scan out of the box; those would require the blob RE in Part A and are still largely unproven. See [`../true-sdr-comparison.md`](../true-sdr-comparison.md) for where that lands versus a real SDR.

Related reading in this catalog: the ESP32 vendor overview in [`../../chips/espressif.md`](../../chips/espressif.md), CSI tooling in [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md), the generic firmware-RE primer in [`../firmware-reversing.md`](../firmware-reversing.md), the Ghidra bring-up guide in [`ghidra-setup-wifi-firmware.md`](ghidra-setup-wifi-firmware.md), and the capability/tier definitions in [`../taxonomy.md`](../taxonomy.md).

---

## 0. What you'll need

| Item | Notes |
|---|---|
| ESP32 dev board | Any classic **ESP32** (Xtensa LX6 dual-core), e.g. ESP32-DevKitC / WROOM-32 / WROVER. The **-S2/-S3** are also Xtensa (LX7); **-C3/-C6/-H2** are RISC-V — see [`esp32-xtensa-ghidra.md` note below](#a1-the-core-xtensa-lx6). |
| USB cable + host | Linux/macOS/Windows; a real data cable, not charge-only. |
| ESP-IDF | **v5.x** for new work (Part B code targets IDF 5.x). The StevenMHernandez CSI Toolkit pins **v4.3** — keep a second checkout for it. |
| Python 3 + `esptool` | Ships inside ESP-IDF; also `pip install esptool`. |
| Ghidra | **11.0 or newer** (native Xtensa) *or* older Ghidra + the `yath/ghidra-xtensa` module (Part A). |
| Xtensa toolchain | `xtensa-esp32-elf-objdump` etc., installed by IDF's `install.sh`. Handy for cross-checking Ghidra. |

Everything below uses **absolute repo URLs and exact commands**. Regulatory notes for the TX section are in [§B4](#b4-safety-and-regulatory-tx).

---

# Part A — Reverse-engineering the firmware

## A1. The core: Xtensa LX6

The classic ESP32 runs **two Tensilica Xtensa LX6** cores (`PRO_CPU` / `APP_CPU`). Xtensa is a **configurable 32-bit RISC-ish** ISA: variable-length instructions (mostly 24-bit, with 16-bit "narrow" encodings when the *density* option is present), and — importantly for RE — an optional **windowed register file** (`CALL8`/`CALL4`/`CALL12`/`ENTRY`/`RETW`). The ESP32 build enables windowing, MAC16, and the loop option, which is exactly the set of features the community Ghidra modules historically struggled with.

| Variant | Core | ISA | This guide applies? |
|---|---|---|---|
| ESP32 (classic) | 2× Xtensa LX6 | Xtensa, windowed | **Yes** (primary target) |
| ESP32-S2 | 1× Xtensa LX7 | Xtensa, windowed | Mostly (different ROM/peripherals) |
| ESP32-S3 | 2× Xtensa LX7 | Xtensa, windowed | Mostly |
| ESP32-C3 / C6 / H2 | RISC-V | RV32IMC | **No** — use a RISC-V processor module instead |
| ESP8266 | 1× Xtensa LX106 | Xtensa, **no** windowing | Partially (simpler; older loaders) |

**Windowing is the single biggest gotcha.** If your decompiler shows garbage stack frames or "missing" arguments, it's almost always because the register-window semantics (`ENTRY` rotates the window; `a0`/`a1` meaning shifts) aren't fully modeled. Verify against `objdump` when a function looks wrong.

## A2. Getting the firmware

You have three routes, in increasing order of "I don't have the source":

**(1) You built it — just use the ELF.** `idf.py build` leaves a fully-symboled `build/<project>.elf`. Load *that* into Ghidra for the easiest possible experience: the ELF is Xtensa, has your symbols, **and** — because the linker pulled objects out of the closed `.a` blobs — it also contains the Wi-Fi driver functions **with their names** (`ppTask`, `wDev_ProcessFiq`, `ieee80211_output`, …). This is by far the best way to *study the blobs*, because Espressif ships the archives stripped of source but **not** of symbols.

**(2) Read the whole flash off the chip.** Vendor firmware, someone else's product, or a board you can't rebuild:

```bash
# Identify chip + flash size
esptool.py --port /dev/ttyUSB0 flash_id

# Dump the entire 4 MB SPI flash (adjust size for 8/16 MB parts)
esptool.py --port /dev/ttyUSB0 --baud 921600 read_flash 0x0 0x400000 flash.bin
```

`flash.bin` is a partitioned image (bootloader @ `0x1000`, partition table @ `0x8000`, one or more app partitions). It is **not** directly a flat memory image — the app image has a segment header, and code/data are split across IROM/DROM/IRAM/DRAM regions. Two good ways to make it Ghidra-friendly:

- **`esp32knife`** ([BlackVS/esp32knife](https://github.com/BlackVS/esp32knife)) parses the partition table and re-emits each app partition as an **ELF** (`partN.*.elf`) with segments placed at their correct load addresses — import that ELF, not the raw partition.
- **`esp32_image_parser`** / the [ESP-Firmware-Toolbox](https://github.com/wilco375/ESP-Firmware-Toolbox) do the equivalent and can also dump the partition table.

**(3) You only have `app.bin` + bootloader.** Same as (2) but for a single partition; feed the app image to `esp32knife`/`esp32_image_parser` to get segment addresses, or import raw and set the base manually (see [§A5](#a5-memory-map)).

> **Read-protection reality check.** If the device set the flash-encryption or secure-boot eFuses, `read_flash` returns ciphertext (or nothing). That's a hardware key-in-eFuse situation and out of scope here — you're then in glitching/side-channel territory, not Ghidra.

## A3. The ROM situation

The ESP32 has a **large mask ROM** (~448 KB across two regions) containing the first-stage bootloader, a big chunk of libc, flash/SPI routines, and — crucially — **many functions the Wi-Fi and BT stacks call into**. When you disassemble a flash dump you will see calls jumping into ROM address space with no target defined. You cannot dump the mask ROM's *source*, but you do **not** need to reverse it, because **Espressif publishes the ROM symbol addresses** as linker scripts:

- [`components/esp_rom/esp32/ld/esp32.rom.ld`](https://github.com/espressif/esp-idf/blob/master/components/esp_rom/esp32/ld/esp32.rom.ld) and its siblings (`esp32.rom.libgcc.ld`, `esp32.rom.newlib*.ld`) map hundreds of named ROM functions to fixed addresses.

Turn that into Ghidra labels: convert each `PROVIDE(name = 0xADDR);` line into an address/name pair and feed it to Ghidra's built-in **`ImportSymbolsScript`** (Script Manager → search "ImportSymbols"). After that, ROM calls resolve to `memcpy`, `SPIRead`, `ets_printf`, `rom_phy_*`, etc., and the disassembly becomes readable. This is the accurate, source-linked way to annotate the ROM — no guessing at offsets.

## A4. Loading it into Ghidra with the Xtensa module

Ghidra **11.0+ ships native Xtensa support** — if you're on a current Ghidra, an Xtensa ELF/binary is recognized without any add-on. For older Ghidra, or if you want the community SLEIGH, install the maintained module:

- **`yath/ghidra-xtensa`** — the actively maintained community processor module: <https://github.com/yath/ghidra-xtensa>
- **`Ebiroll/ghidra-xtensa`** — a fork with ESP-oriented tweaks and image-loader notes: <https://github.com/Ebiroll/ghidra-xtensa> (its README explicitly notes that *Ghidra 11.0 now includes Xtensa support, so this repo may not be needed*).

Install the community module (pick the release matching your Ghidra, or build):

```bash
# Option A: drop a matching prebuilt release zip via
#   Ghidra → File → Install Extensions → +   (then restart)

# Option B: source install into the Processors tree
cd <ghidra>/Ghidra/Processors
git clone https://github.com/yath/ghidra-xtensa Xtensa
cd Xtensa && make        # builds the SLEIGH .sla from the .slaspec
# restart Ghidra
```

Then import:

- **ELF (routes 1 & 2-via-esp32knife):** File → Import; Ghidra auto-selects Xtensa; accept, then run auto-analysis. Segments land at the right addresses automatically.
- **Raw binary:** choose language **`Xtensa:LE:32:default`** (little-endian), and set the base address yourself — see next section.

**Known limits of the community SLEIGH** (be skeptical here): windowed-register call semantics, the MAC16 multiply-accumulate ops, and the zero-overhead `LOOP` instruction have historically been incompletely modeled. Symptoms: wrong function boundaries after `CALL8`, bogus locals, or undefined bytes mid-function. Cross-check anything load-bearing with `xtensa-esp32-elf-objdump -d`. Native Ghidra 11.x handles more of these but is not perfect either.

## A5. Memory map

For a **raw** load you must place bytes at the right virtual addresses or nothing cross-references. These are the documented ESP32 embedded-memory regions (from the *ESP32 Technical Reference Manual*, "System and Memory", and the ESP-IDF [Memory Types](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/memory-types.html) guide — **use the TRM as the authority, don't trust magic numbers from a blog**):

| Region | Address range | Bus | Contents |
|---|---|---|---|
| Internal ROM 0 | `0x4000_0000`–`0x4005_FFFF` | I | Mask ROM (bootloader, libc, PHY helpers) |
| Internal ROM 1 | `0x3FF9_0000`–`0x3FF9_FFFF` | D | Mask ROM data |
| Internal SRAM 0 | `0x4007_0000`–`0x4009_FFFF` | I | **IRAM** (cache + hot code) |
| Internal SRAM 1 | `0x3FFE_0000`–`0x3FFF_FFFF` (D) / `0x400A_0000`–`0x400B_FFFF` (I) | D/I | dual-mapped |
| Internal SRAM 2 | `0x3FFA_E000`–`0x3FFD_FFFF` | D | **DRAM** (heap, `.bss`) |
| Flash, mapped IROM | `0x400D_0000`–`0x40BF_FFFF` | I | XIP instruction cache window |
| Flash, mapped DROM | `0x3F40_0000`–`0x3F7F_FFFF` | D | const data cache window |

Practical rule: the **app image's `.text`/IROM segment** is what you usually want, and its load address comes straight out of the image header (esp32knife prints it). If you loaded a whole-flash blob raw, the executable app code will *not* be at a nice address — that's why the ELF route is strongly preferred. Add the ROM regions as **overlay/uninitialized** blocks and apply the symbol import from [§A3](#a3-the-rom-situation) so ROM calls resolve.

## A6. Finding the Wi-Fi driver hooks (the closed `net80211`/`pp` blobs)

The ESP32 Wi-Fi stack is **closed-source precompiled archives** shipped in [`espressif/esp32-wifi-lib`](https://github.com/espressif/esp32-wifi-lib) (mirrored into IDF at `components/esp_wifi/lib/esp32/`):

| Blob | Role |
|---|---|
| `libpp.a` | "packet processor" — the low-level MAC/PHY glue: `ppTask`, `wDev_ProcessFiq`, TX/RX descriptors, rate control |
| `libnet80211.a` | the 802.11 MLME/MAC: `ieee80211_output`, `ieee80211_input`, scan/auth/assoc, `ieee80211_freedom_output` |
| `libcore.a`, `libphy.a`, `librtc.a` | core scheduler, PHY calibration, RF/RTC |

**Key fact that makes this tractable:** these `.a` files are **Xtensa ELF object archives with symbol tables intact** — only the *source* is withheld. So you can read the function names directly:

```bash
# List the object members and their symbols
ar t  libnet80211.a
xtensa-esp32-elf-nm  libnet80211.a | grep -i freedom      # -> ieee80211_freedom_output
xtensa-esp32-elf-objdump -d libpp.a > libpp.disasm        # full Xtensa disassembly

# Or extract one object and drop it straight into Ghidra:
ar x libnet80211.a ieee80211_output.o     # then File -> Import (Xtensa, symbols present)
```

Because the symbols survive, "finding the hooks" is really **finding the function you care about by name and reading its body**, rather than blind offset-hunting. Two concrete, documented starting points:

- **Injection hook — `ieee80211_freedom_output`.** [Jeija's `esp32free80211`](https://github.com/Jeija/esp32free80211) found (by disassembling `libnet80211.a`) that this function can be coerced into emitting arbitrary frames. That work is now **obsolete for users** because Espressif exposed the supported `esp_wifi_80211_tx()` API (Part B), but it's the canonical example of the RE path from blob → capability.
- **RX/PHY path — `ppTask` / `wDev_ProcessFiq`.** The [**esp32-open-mac**](https://github.com/esp32-open-mac/esp32-open-mac) project reverse-engineered the undocumented Wi-Fi MAC peripheral by tracing `hal_mac_*` / `wdev_mac_*` and the FIQ handler, then letting the blob initialize the hardware, killing the Wi-Fi FreeRTOS task, and substituting their own IRQ handler for a **blob-free** TX/RX MAC. Their writeups ([intro](https://esp32-open-mac.be/posts/0001-introduction/), [road ahead](https://esp32-open-mac.be/posts/0005-the-road-ahead/), [WPA crypto accel](https://esp32-open-mac.be/posts/0010-wpa/)) are the best available map of the descriptor rings and MAC registers — the exact structures you'd want when you go looking in your own dump.

**Speed up identification with FIDB.** Tarlogic's guide ["Function Identification in ESP32 Firmware Using Ghidra FIDB"](https://www.tarlogic.com/blog/esp32-firmware-using-ghidra-fidb/) shows how to build a Ghidra **Function ID database** from a symboled IDF build (including the `.a` blobs) and then auto-name matching functions in a *stripped* third-party firmware. This is the highest-leverage trick for vendor-firmware RE: reverse once (your own build), recognize everywhere.

> **Accuracy note.** Do not hardcode addresses like "`ieee80211_freedom_output` is at `0x400xxxxx`." The address depends on the exact blob version and how the linker placed it. Locate it in *your* image via `nm`/FIDB, then follow the calls.

---

# Part B — Capturing CSI (no RE required)

This is the reason the ESP32 is in an SDR catalog at all: Espressif exposes **supported** APIs for per-subcarrier CSI, promiscuous RX, and raw frame TX. All references below are the official [ESP-IDF Wi-Fi Vendor Features guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/wifi-driver/wifi-vendor-features.html).

## B1. What CSI the ESP32 actually gives you

Every received 802.11 frame carries training fields the receiver uses to equalize the channel. The ESP32 hands you the estimated **channel frequency response per subcarrier**, as pairs of `int8`:

- **Format:** each subcarrier = **2 bytes**, `[imag, real]` (imaginary first, then real), signed 8-bit. Amplitude = `sqrt(re²+im²)`, phase = `atan2(im, re)`.
- **Fields present** depend on the packet and your config: **LLTF** (legacy long training field, always available on 11b/g/n), **HT-LTF** (present on 11n frames), and **STBC-HT-LTF** (when STBC is used).
- **Subcarrier indices:** `0..31, -32..-1` for a **20 MHz / non-HT** capture; `0..63, -64..-1` for **40 MHz / HT**. Guard/null subcarriers are included in the buffer.
- **`first_word_invalid`:** a hardware quirk — when true, the **first four bytes** of `buf` are garbage; skip them.

That is genuine per-subcarrier complex channel state → **SDR ladder Tier 2 (`csi`)**. What you do **not** get: raw ADC IQ samples, an FFT/spectral-scan register readout (unlike Atheros `ath9k` — see [`atheros-ath9k-spectral-csi.md`](atheros-ath9k-spectral-csi.md)), or arbitrary-waveform TX. Phase is uncalibrated (CFO/SFO/PBD offsets per packet), so cross-packet phase needs the usual sanitization — see [`../../projects/wifi-sensing-datasets.md`](../../projects/wifi-sensing-datasets.md) and [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md).

## B2. The native CSI API — minimal sketch

Enable it in `idf.py menuconfig` → **Component config → Wi-Fi → WiFi CSI(Channel State Information)** = **y**, then:

```c
#include "esp_wifi.h"
#include "esp_log.h"

// Called from the WiFi task for every received frame's CSI. Keep it SHORT —
// heavy work here degrades Wi-Fi. Copy out and signal a queue instead.
static void csi_cb(void *ctx, wifi_csi_info_t *info)
{
    const wifi_pkt_rx_ctrl_t *rx = &info->rx_ctrl;    // rssi, noise_floor, rate, channel, timestamp, ant...
    int8_t *csi = info->buf;                            // [imag, real] int8 pairs
    int     len = info->len;                            // bytes
    int     start = info->first_word_invalid ? 4 : 0;   // skip 4 garbage bytes if flagged

    // Emit a CSV line the ESP32-CSI-Tool way: metadata + the raw CSI array
    printf("CSI_DATA," MACSTR ",%d,%d,%d,[", MAC2STR(info->mac),
           rx->rssi, rx->rate, rx->channel);
    for (int i = start; i < len; i++) printf("%d ", csi[i]);
    printf("]\n");
}

void enable_csi(void)
{
    wifi_csi_config_t cfg = {
        .lltf_en           = true,   // legacy LTF subcarriers
        .htltf_en          = true,   // HT LTF subcarriers (11n)
        .stbc_htltf2_en    = true,   // STBC HT-LTF
        .ltf_merge_en      = true,
        .channel_filter_en = true,
        .manu_scale        = false,  // let HW auto-scale; set true + .shift to fix gain
        .shift             = 0,
    };
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_cb, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
}
```

**Getting frames to measure.** A **connected station** only sees CSI from its AP; a disconnected station sees nothing. So for a passive sensor, add promiscuous mode so *every* frame on the channel produces CSI:

```c
esp_wifi_set_promiscuous(true);
esp_wifi_set_channel(6, WIFI_SECOND_CHAN_NONE);   // lock to one channel
```

For an **active** link that generates a steady, controlled packet stream (best for sensing), pair two ESP32s — one AP, one STA pinging it — which is exactly the topology the CSI Toolkit ships.

## B3. The turnkey path — ESP32 CSI Toolkit

If you'd rather not write firmware, use **StevenMHernandez/ESP32-CSI-Tool** — the de-facto reference collector (also covered in [`../../projects/csi-toolchains.md`](../../projects/csi-toolchains.md)):

- Repo: <https://github.com/StevenMHernandez/ESP32-CSI-Tool> · Docs: <https://stevenmhernandez.github.io/ESP32-CSI-Tool/>
- **Pins ESP-IDF v4.3** (keep a separate IDF checkout for it).

Three subprojects: `active_sta` (station that requests packets), `active_ap` (the AP peer), and `passive` (listen-only on a channel, default ch 3). Build/flash/collect:

```bash
git clone https://github.com/StevenMHernandez/ESP32-CSI-Tool
cd ESP32-CSI-Tool/active_ap        # or active_sta / passive

idf.py menuconfig
#   Component config > Wi-Fi > WiFi CSI(Channel State Information)   [*]
#   Serial flasher config > Custom baud rate value                  921600
#   Component config > Common ESP32-related > UART console baud     921600
#   FreeRTOS > Tick rate (Hz)                                       1000

idf.py flash monitor           # ctrl+] to exit

# Log CSI to CSV (grep the marker the firmware prints)
idf.py monitor | grep "CSI_DATA" > my_capture.csv
# ...or with host timestamps:
idf.py monitor | python ../python_utils/serial_append_time.py > my_capture.csv
```

Each line is `CSI_DATA,<metadata...>,[<int8 imag/real pairs>]`, ready for Python/MATLAB/R. Companion Android tooling exists ([Android-ESP32-CSI](https://github.com/StevenMHernandez/Android-ESP32-CSI), [labelling app](https://github.com/StevenMHernandez/Android-CSI-Labelling-App)) if you want to collect off a phone.

**Expected output / verification.** Within a second of flashing you should see a stream of `CSI_DATA,` lines. Sanity checks: RSSI in `rx_ctrl` tracks distance; waving your hand between the two boards perturbs the amplitude across subcarriers; the CSI array length is stable per rate (≈128 bytes for a 20 MHz HT frame incl. nulls). No lines → CSI not enabled in menuconfig, wrong channel, or (station mode) not associated.

## B4. Raw 802.11 TX / injection

The ESP32 will transmit an **arbitrary 802.11 frame** you hand it — any addresses, any type — via a supported API:

```c
esp_err_t esp_wifi_80211_tx(wifi_interface_t ifx,
                            const void *buffer,  // full raw 802.11 frame (you build the header)
                            int len,
                            bool en_sys_seq);    // true = driver overwrites the seq number
```

- You control **rate** via `esp_wifi_config_80211_tx_rate()` and **bandwidth** via `esp_wifi_set_bandwidth()`.
- **`en_sys_seq` rule:** before the Wi-Fi connection is set up, either value works; **after** association you *must* pass `true` or you get `ESP_ERR_INVALID_ARG`.
- Minimal working example (broadcast beacons carrying a custom SSID/payload): [`Jeija/esp32-80211-tx`](https://github.com/Jeija/esp32-80211-tx). This supersedes the old blob-hacking [`esp32free80211`](https://github.com/Jeija/esp32free80211).

**Limits to be honest about.** This is *frame* injection, not *waveform* injection: the PHY still builds a standards-compliant OFDM/DSSS symbol from your bytes at one of the supported MCS/legacy rates. You cannot emit an arbitrary I/Q waveform, a non-802.11 chirp, or a custom preamble from the supported API — that would require the Part-A blob RE (esp32-open-mac territory) and remains **theoretical/experimental**, not a stock capability. So: **arbitrary frames yes; arbitrary waveform no.**

### B4. Safety and regulatory (TX)

Injection puts real energy on shared 2.4 GHz spectrum. Transmitting forged management/data frames (deauth, spoofed beacons, injecting onto networks you don't own) is **illegal in most jurisdictions** and violates the rules for the licence-exempt band. Test **only** on your own equipment, ideally in an RF-shielded enclosure or at minimum on a quiet channel with your own AP/STA, and keep TX power/duty cycle low. Do not disrupt other users. Nothing here authorizes interfering with third-party networks.

---

## C. Where the ESP32 lands (capability summary)

| Capability | ESP32 | How |
|---|---|---|
| Monitor / promiscuous RX | ✅ verified | `esp_wifi_set_promiscuous()` |
| Injection (arbitrary frames) | ✅ verified | `esp_wifi_80211_tx()` |
| CSI (per-subcarrier complex) | ✅ verified | `esp_wifi_set_csi()` — LLTF+HT-LTF, `int8` I/Q |
| Spectral / raw-PHY scan | ❌ | no exposed FFT-bin register readout |
| Raw IQ / arbitrary waveform | ❌ (theoretical) | would need blob RE / open-MAC |
| Open firmware | ⚠️ partial | app is open; `libpp`/`libnet80211`/`libphy` are closed blobs |

**SDR tier: 2** (highest rung reachable with public tooling = CSI). The classic ESP32 catalog record is [`espressif-esp32`](../../chips/espressif.md); this walkthrough adds the hands-on RE + CSI method, not a new chip — so `modules[]` below is intentionally empty.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Ghidra decompiler shows broken stack frames after calls | Xtensa **windowed-register** modeling gap — verify against `xtensa-esp32-elf-objdump -d`; try native Ghidra 11.x. |
| Calls jump into `0x4000xxxx` with no target | ROM functions — import [`esp32.rom.ld`](https://github.com/espressif/esp-idf/blob/master/components/esp_rom/esp32/ld/esp32.rom.ld) symbols via `ImportSymbolsScript` ([§A3](#a3-the-rom-situation)). |
| Raw flash load has code at odd addresses | You imported the partitioned blob raw — run `esp32knife` and import the emitted **ELF** instead. |
| `read_flash` returns identical/garbage bytes | Flash encryption / secure-boot eFuses set — not recoverable via Ghidra. |
| No `CSI_DATA` lines | CSI not enabled in menuconfig; wrong `esp_wifi_set_channel`; station not associated (use promiscuous or the active AP/STA pair). |
| `esp_wifi_80211_tx` returns `ESP_ERR_INVALID_ARG` | You're associated and passed `en_sys_seq=false` — pass `true`. |
| CSI first few values look wrong | Honor `first_word_invalid` and skip the first 4 bytes. |

## References

**Xtensa / Ghidra tooling**
- yath/ghidra-xtensa (maintained processor module): <https://github.com/yath/ghidra-xtensa>
- Ebiroll/ghidra-xtensa (ESP fork; notes native Ghidra 11 Xtensa support): <https://github.com/Ebiroll/ghidra-xtensa>
- Tarlogic — Function Identification in ESP32 Firmware Using Ghidra FIDB: <https://www.tarlogic.com/blog/esp32-firmware-using-ghidra-fidb/>
- Olof Åstrand — RE of ESP32 flash dumps with Ghidra/IDA: <https://olof-astrand.medium.com/reverse-engineering-of-esp32-flash-dumps-with-ghidra-or-ida-pro-8c7c58871e68>

**Firmware extraction**
- esptool documentation (`read_flash`, `flash_id`): <https://docs.espressif.com/projects/esptool/>
- esp32knife (partition → ELF): <https://github.com/BlackVS/esp32knife>
- ESP-Firmware-Toolbox: <https://github.com/wilco375/ESP-Firmware-Toolbox>
- ESP32 ROM symbol linker script: <https://github.com/espressif/esp-idf/blob/master/components/esp_rom/esp32/ld/esp32.rom.ld>
- ESP-IDF Memory Types (memory map): <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/memory-types.html>

**Closed Wi-Fi blobs + open-MAC RE**
- espressif/esp32-wifi-lib (the `.a` blobs): <https://github.com/espressif/esp32-wifi-lib>
- esp32-open-mac project + writeups: <https://github.com/esp32-open-mac/esp32-open-mac> · <https://esp32-open-mac.be/posts/0001-introduction/> · <https://esp32-open-mac.be/posts/0005-the-road-ahead/> · <https://esp32-open-mac.be/posts/0010-wpa/>
- Jeija/esp32free80211 (`ieee80211_freedom_output` RE): <https://github.com/Jeija/esp32free80211>

**CSI + raw TX (Part B)**
- ESP-IDF Wi-Fi Vendor Features (CSI + `esp_wifi_80211_tx`): <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/wifi-driver/wifi-vendor-features.html>
- ESP-IDF `esp_wifi` API reference: <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_wifi.html>
- StevenMHernandez/ESP32-CSI-Tool: <https://github.com/StevenMHernandez/ESP32-CSI-Tool> · <https://stevenmhernandez.github.io/ESP32-CSI-Tool/>
- Jeija/esp32-80211-tx (raw injection example): <https://github.com/Jeija/esp32-80211-tx>
