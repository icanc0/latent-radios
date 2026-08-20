# Reversing Broadcom D11 Microcode

> **Scope.** This is a *methodology* walkthrough for the D11 MAC microengine that lives inside every Broadcom/Cypress Wi-Fi chip from the BCM4306 era to the BCM4389. It shows you how to (1) locate the D11 microcode ("ucode") in a firmware dump, (2) disassemble it with **b43-tools**, (3) recognise the SHM and template-RAM conventions the ucode relies on, (4) statically/dynamically analyse and emulate it with **seemoo-lab/d11-emu**, and (5) find where the PHY-facing tricks (spectral capture, CSI export, TX vectors) hook in.
>
> **Accuracy note.** Concrete SHM word addresses, template-RAM slot offsets and ucode PC values are *chip-, PHY- and firmware-version-specific*. This guide names the exact symbols, structs, files and disassembler steps so you can recover the correct offset from **your own** dump. Every concrete number below is either sourced from a linked primary document or shown as a placeholder like `SHM(<offset>)`.

---

## 1. What the D11 actually is

The **D11 core** (sometimes "d11", "PSM" — *Programmable State Machine*, or "the MAC ucode engine") is a small, custom **16-bit microcontroller** that Broadcom places between the host/MAC interface and the analog PHY. It is *not* the ARM CPU on the chip and *not* the PHY. Its whole job is the hard-real-time part of 802.11: acknowledging frames within a SIFS, backoff/CCA, building PLCP headers, driving the PHY registers, timestamping, and shuffling frames through the RX/TX FIFOs.

Key architectural facts, from the Broadcom-v4 reverse-engineering wiki and the SEEMOO "Rolling the D11" paper:

| Property | Value | Notes |
|---|---|---|
| Word size | 16-bit, little-endian | All data memory is addressed in 16-bit words. |
| Instruction width | 64-bit words | Jumps are counted in *instruction numbers* (8-byte units), not byte addresses. |
| Operand width | 12-bit (core rev 5–14), 13-bit (rev 15+) | Determines the `--arch` you pass to the disassembler. |
| Immediates | 10-bit signed (rev 5–14), 11-bit (rev 15+) | |
| Registers | General-purpose `r0..rN`, **offset/base registers** `off0..off6`, SPRs, link/PC registers | Base registers give indexed addressing into SHM. |
| Program store | **ucode** (the instruction stream) | Loaded into the D11 code RAM. |
| Data | **SHM** (shared memory) + **template RAM** | See §4. |
| Condition inputs | RX/TX/PHY/PSM external conditions | Branches test these hardware condition lines. |

The instruction-set reference lives here and is the authoritative ISA document you should keep open while reading disassembly:

- **D11 Microcode ISA** — <http://bcm-v4.sipsolutions.net/802.11/Microcode>
- Register/SHM/SPR conventions — <http://bcm-v4.sipsolutions.net/802.11/>

The core has been revised for ~20 years; **d11-emu** models revisions **15–54** (tested on rev 46 and 54), while **b43-tools** covers everything from core rev 5 up. Cores ≤4 use an older, incompatible format.

---

## 2. Where the ucode lives, and how Broadcom ships it

There are two shipping models, and they map directly onto the SoftMAC/FullMAC split (see §7):

### SoftMAC (b43 / b43legacy era: BCM4306, 4311, 4318, 4320, 43xx-G/N)
There is **no on-chip ARM MAC processor**. The D11 ucode *is* the MAC. The Linux `b43` driver loads the ucode from a firmware file at interface-up. That file is what `b43-fwcutter` extracts from the proprietary Windows/macOS driver — or, for the fully-open case, what **OpenFWWF** builds from source. The ucode is the entire firmware payload; replace it and you replace the MAC.

### FullMAC (brcmfmac / dongle era: BCM4339, 43438, 43455, 4358, 4366, 4375, 4387, …)
An on-chip **ARM core** (Cortex-M3 or Cortex-R4) runs the full MLME. Firmware is a two-part image:

- **ROM** — fixed, mask-programmed. Located at `0x800000` (Cortex-M3) or `0x000f0000` (Cortex-R4) per the Quarkslab teardown.
- **RAM firmware** — loaded by the driver, contains ARM code + data **plus the embedded D11 ucode**. Integrity is only a **CRC32**, *not* a signature — which is exactly why Nexmon patching works.

In the FullMAC image the D11 ucode is a blob *inside* the ARM firmware. At bring-up the **ARM copies the ucode into the D11 code RAM**, often after an unpacking step. On the BCM43438/BCM43455 the ucode is stored **7-byte-packed** and the ARM expands it to 8-byte instruction words before writing it to the D11 — see b43-tools PR #4 (§6), which reproduces that packing so you can round-trip it.

**Practical takeaway:** on SoftMAC you already have a `.fw` file that *is* ucode. On FullMAC you must carve the ucode out of the RAM firmware blob and possibly unpack it before a disassembler will make sense of it.

---

## 3. Tooling: b43-tools and its lineage

**b43-tools** (Michael Büsch, `mbuesch/b43-tools`) is the assembler/disassembler suite for Broadcom "AirForce" BCM43xx ucode, core rev ≥5. It is the direct descendant of the tooling built for the b43 driver and the **OpenFWWF** project, and it is the same `b43-asm` that both OpenFWWF and (a forked v3 of it) d11-emu depend on.

Contents:

| Tool | Purpose |
|---|---|
| `assembler/b43-asm` | Assemble `.asm` ucode → binary. Expands "virtual" pseudo-instructions to real ones. |
| `disassembler/b43-dasm` | Disassemble binary ucode → `.asm`. |
| `disassembler/b43-ivaldump`, `brcm80211-ivaldump`, `brcm80211-fwconv` | Dump/convert initvals and brcmsmac-format firmware. |
| `fwcutter` (companion project `b43-fwcutter`) | Carve ucode + initvals out of a proprietary driver. |

Build:

```bash
git clone https://github.com/mbuesch/b43-tools
cd b43-tools/assembler && make        # produces b43-asm
cd ../disassembler   && make          # produces b43-dasm
# optionally: sudo make install
```

Disassemble a ucode binary. The critical flag is `--arch`, which selects the operand width and must match the core revision (`5` for rev 5–14, `15` for rev 15+):

```bash
# SoftMAC-style raw ucode (already 8-byte instruction words)
b43-dasm ucode.fw ucode.asm --arch 15   # try 15 for modern cores; 5 for classic

# Re-assemble to verify a round-trip
b43-asm ucode.asm ucode.rebuilt.bin --format raw
```

A clean round-trip (`b43-dasm` → `b43-asm` → byte-identical binary, modulo the known NAP-argument warnings on some packed images) is your proof that you picked the right `--arch` and unpacking.

> **d11-emu needs a specific assembler.** The emulator expects **b43-asm "v3"** as shipped inside Nexmon (`nexmon/buildtools/b43/assembler`). Build that one and put it on your `PATH` before running the emulator's tests, or the `.asm` test fixtures won't assemble.

---

## 4. Reading a disassembly: SHM and template-RAM conventions

Raw disassembly is a wall of `mov`, `add`, `jext`/`jnext` (jump-on-external-condition), `orx`/`srx` (bitfield ops) and `call`/`ret`. The structure only appears once you recognise the two memory regions the ucode talks to.

### 4.1 SHM — Shared Memory
SHM is the scratch RAM shared between the D11 and the host/ARM. It holds live MAC state: the current channel, TSF, per-queue backoff, retry counters, key table indices, and — crucially for us — the **RX/TX FIFO bookkeeping**. The Quarkslab teardown documents the RX path removing a frame from a **linked list `rx_fifo` located in SHM** shared by the MCU and the D11.

How to recognise SHM access in disassembly:

- SHM is addressed as `SHM(<word_offset>)` operands, or indirectly through the **offset/base registers** `off0..off6` (`[off3 + k]` style indexed reads). Watch for a register being loaded with a base and then reused across a routine — that base is a struct pointer into SHM.
- To attach *meaning* to a raw offset, cross-reference the Nexmon **`d11.h`** header for the same chip. It defines the hardware-facing structs — `d11rxhdr`, `wlc_d11rxhdr`, the `PhyRxStatus_N` words, `RxStatus1/2`, and the RX flags (`RXS_FCSERR`, `RXS_PHYRXST_VALID`, `RXS_CHAN_5G`, …). When you see the ucode assemble those exact bitfields, you've found the RX-status writer.
  - `patches/bcm43455c0/7_45_154/nexmon/include/d11.h` in `seemoo-lab/nexmon`.
- The **initvals** (dumped with `b43-ivaldump`) seed SHM at load time; diffing initvals against a running dump tells you which offsets are constants vs. live state.

**Never hardcode an SHM offset from another chip.** The layout shifts between PHYs and firmware builds. Recover *your* offset by finding the routine that reads/writes it and matching the surrounding bit-manipulation to a `d11.h` struct field.

### 4.2 Template RAM
Template RAM holds pre-built frame **templates** — the ACK, CTS, beacon and probe-response skeletons the D11 can emit within a SIFS without host involvement — and, ahead of each transmit, the **PLCP/PHY header + TX descriptor ("TX header" / `d11txh`)** that tells the PHY *how* to modulate the outgoing frame (rate, power, antenna, bandwidth). The ucode fills template RAM, then points the PHY/DMA at it.

How to recognise template-RAM work:

- Look for a routine that writes a contiguous run of words (the PLCP + MAC header) and then triggers TX via an external-condition branch or a PHY-register poke. That contiguous writer is your TX-header builder.
- Cross-reference the Nexmon TX header struct (`d11txh` / `wlc_d11txh` in the chip's headers) to name the fields (MAC control, PHY control words `PhyTxControlWord`, rate fallback, `XtraFrameTypes`, fragment thresholds).
- Nexmon's **frame-injection** patch works precisely by writing a crafted TX header into template RAM and kicking the D11 — reading that patch is the fastest way to learn the convention for a given chip. See `../../projects/nexmon.md`.

---

## 5. Emulating and instrumenting with d11-emu

Static disassembly gets you the *shape*; **seemoo-lab/d11-emu** (Rust) gets you *behaviour*. It implements the D11 ISA (rev 15–54), executes real ucode, and — paired with a Nexmon debug patch — extracts live state from a physical chip so you can compare emulated vs. real register/SHM contents. It comes from the SEEMOO paper *"Rolling the D11: An Emulation Game for the Whole BCM43 Family"* (Link, Breuer, Gringoli, Hollick; ACM WiNTECH '23).

### 5.1 Standalone emulation (no hardware)

```bash
# prerequisites: rustup/cargo; b43-asm v3 from nexmon on PATH; lcov (optional, coverage)
git clone https://github.com/seemoo-lab/d11-emu
cd d11-emu
cargo build --release
cargo test                                   # runs the .asm fixtures in tests/
cargo run --release -- /path/to/ucode.bin    # emulate a ucode image
```

In standalone mode you get the interactive CLI, single-stepping, register/SHM inspection and coverage analysis — but *not* state extraction (there's no real chip to pull from).

### 5.2 State extraction against a real BCM43455c0

Hardware: a **Raspberry Pi 3 Model B+ or Pi 4 Model B** (both carry the BCM43455c0), running a Nexmon firmware built with the debug patch **`seemoo-lab/wintech23_nexmon_d11debug`**.

1. Build and flash the debug firmware (this is a Nexmon patch; follow the base Nexmon build in `../bcm43455c0-raspberry-pi.md`):
   ```bash
   # inside a working nexmon tree, after `source setup_env.sh` and `make` at top level
   sudo apt install libnl-genl-3-dev
   # clone the patch into the patches dir per its README, then:
   make
   sudo -E make install-firmware
   ```
2. Point the emulator at the Pi by editing `src/config.rs`:
   ```rust
   const TARGET_IP_ADDRESS: &str = "192.168.x.y";
   const TARGET_SSH_KEY_LOCATION: &str = "/home/you/.ssh/id_ed25519";
   ```
3. **Set a ucode breakpoint.** The debug patch's mechanism: insert *two* microcode lines at the target point in the `.asm` — the first loads a breakpoint **id**, the second `call`s the stop routine. Re-assemble, `make install-firmware`, reload. When the D11 hits it, the patch halts and the d11-emu utility pulls the full D11 state (registers + SHM) over SSH so you can seed or check the emulator.

This closes the loop: disassemble → hypothesise → emulate → break on the real chip → diff. Coverage output (`lcov`) tells you which ucode paths your stimulus actually exercised.

---

## 6. Carving and unpacking ucode from a FullMAC blob

For dongle/FullMAC chips the ucode is buried in the RAM firmware (e.g. `brcmfmac43455-sdio.bin`). Workflow:

1. **Find the ucode region.** In a Nexmon-supported chip, the ucode block is a named region in the patch's linker/`definitions` (look for `ucode`/`d11` symbols and the ROM/RAM map in `../firmware-reversing.md`). Otherwise, scan the blob for the characteristic 8-byte-word instruction density and a valid `--arch 15` disassembly — the region that produces sane, self-consistent disassembly (real `ret`s, dense external-condition jumps) is the ucode.
2. **Unpack if needed.** BCM43438/BCM43455 store ucode **7-byte-packed**; the ARM expands 7→8 bytes before loading the D11. Reproduce that with the Perl helper from **b43-tools PR #4** ("Added script to prepare bcm43438 ucode for disassembling", DanielAW):
   - Forward (unpack) advances the source pointer by 7 bytes per instruction and emits 8-byte words; reverse re-packs 8→7. Expect benign NAP-argument warnings on re-assembly; the image still runs on the Pi.
3. **Disassemble** the unpacked region with `b43-dasm … --arch 15`.

> Do not copy a memory map from another chip. The ucode base, size and packing are per-chip. Derive them from the chip's own Nexmon definitions or by the disassemble-and-check method above.

---

## 7. SoftMAC vs FullMAC — why the reversing target differs

| | **SoftMAC** (b43) | **FullMAC** (brcmfmac) |
|---|---|---|
| Example chips | BCM4306, 4311, 4318, 4320 | BCM43438, 43455c0, 4339, 4358, 4366, 4375, 4387 |
| On-chip CPU | none — D11 is the MAC | ARM Cortex-M3 / R4 runs the MLME |
| Where the MAC logic is | **entirely in D11 ucode** | split: MLME in ARM firmware, hard-real-time in **D11 ucode as a co-processor** |
| Firmware shipped as | a ucode `.fw` file loaded by the driver | ARM RAM blob (CRC32, unsigned) **with ucode embedded** |
| Open-source replacement | **OpenFWWF** replaces the ucode wholesale | none for ARM; **Nexmon** *patches* ARM firmware + ucode |
| To reverse the ucode | disassemble the `.fw` directly | carve/unpack ucode out of the RAM blob first (§6) |

**OpenFWWF** (Open FirmWare for WiFi networks; Gringoli et al., Univ. of Brescia) is the SoftMAC endgame: a **fully open-source D11 ucode**, GPLv2, built with `b43-asm`, that *replaces* Broadcom's proprietary ucode on BCM4306/4311/4318/4320 and turns the card into a programmable MAC testbed. If you want to *understand* the D11 ISA by reading complete, commented source rather than disassembly, OpenFWWF is the reference implementation — read `../../projects/openwifi.md` for how programmable-MAC testbeds compare.

On FullMAC there is no open ucode; the D11 is a co-processor to the ARM, so you *patch* rather than *replace*. Nexmon injects C into the ARM firmware and hand-written ucode into the D11 — see `../../projects/nexmon.md` and the ARM-side reversing in `../broadcom-d11-ucode.md`'s companion `../../docs/firmware-reversing.md`.

---

## 8. Where the PHY-facing SDR tricks hook in

The whole reason to reverse the D11 is that it is the last programmable stop before the PHY. Three high-value hook points:

- **Spectral / raw-PHY capture.** The D11 (or an ARM patch that drives the same PHY registers) programs the PHY to dump raw ADC/FFT samples into SHM/host memory instead of decoding a frame. On the ath9k side this is the `spectral_scan` control; on Broadcom the equivalent is exposed by Nexmon's spectral tooling. In disassembly, find the routine that pokes the **PHY register file** and then streams a fixed-length sample buffer — that's the capture path. Contrast with the SoftMAC b43 spectral support in `../../docs/techniques.md`.
- **CSI export.** Per-subcarrier complex channel state is a by-product of PHY equalisation. **Nexmon CSI** extracts it by patching the RX path to copy the PHY's channel estimate out before it's discarded. The hook is in the RX-status writer you located via `d11.h` (§4.1): the CSI patch tees the PHY estimate into a host-visible buffer right where `RXS_PHYRXST_VALID` is set. See `../../projects/csi-toolchains.md`.
- **TX vector / arbitrary waveform.** The **TX header / PHY control words** in template RAM (§4.2) are the rate/power/antenna vector h(anded to the PHY. Rewriting them — as Nexmon frame injection does — lets you emit non-standard frames; pushing further toward arbitrary I/Q requires PHY-register-level control that the D11 mediates. This is the frontier tracked in `../../docs/verification-tier4.md`.

For each of these, the reproducible method is the same: disassemble → find the PHY-register or template-RAM routine → confirm against the Nexmon patch that already does it for a related chip → emulate/break with d11-emu to verify the offset on *your* firmware.

---

## 9. Suggested end-to-end path

1. Read the ISA (`bcm-v4.sipsolutions.net/802.11/Microcode`) and skim OpenFWWF source for a mental model.
2. Get a ucode image: SoftMAC `.fw`, or carve+unpack a FullMAC blob (§6).
3. `b43-dasm --arch {5|15}`; confirm with a `b43-asm` round-trip.
4. Map SHM and template-RAM offsets against the chip's Nexmon `d11.h`/`d11txh` (§4).
5. Bring up d11-emu standalone; run your ucode; single-step the routine of interest.
6. If you have a Pi 3B+/4B, flash `wintech23_nexmon_d11debug`, set a two-line breakpoint, extract live state, and diff against the emulator.

---

## 10. Safety and regulatory notes

Everything up to §5.1 (disassembly, emulation) is passive and carries no RF risk. The moment you **flash modified ucode/firmware and transmit** (frame injection, altered TX vectors, spectral routines that key the PA, or any arbitrary-waveform experiment) you are operating a radio transmitter:

- Transmit only into a **shielded enclosure / RF cage or a wired coax setup with attenuators and a dummy load**. Do not radiate custom waveforms over the air on shared Wi-Fi bands.
- Modified TX power/rate vectors can exceed the module's certified EIRP and violate local spectrum rules (FCC Part 15 / ETSI EN 300 328 / your national regulator). Regulatory certification is void once you replace the firmware.
- Keep a known-good stock firmware to restore. On the Pi, that means keeping the original `brcmfmac43455-sdio.bin` so you can revert with `make restore` / reinstall the distro firmware package.

---

## References

- Michael Büsch, **b43-tools** (assembler/disassembler for BCM43xx ucode, core rev ≥5) — <https://github.com/mbuesch/b43-tools>
- b43-tools PR #4, *Prepare bcm43438 ucode for disassembling* (7-byte packing) — <https://github.com/mbuesch/b43-tools/pull/4>
- **D11 Microcode ISA reference**, bcm-v4 reverse-engineering wiki — <http://bcm-v4.sipsolutions.net/802.11/Microcode>
- bcm-v4 wiki index (SHM, registers, DMA, initvals) — <http://bcm-v4.sipsolutions.net/802.11/>
- **OpenFWWF** — Open FirmWare for WiFi networks (open D11 ucode for SoftMAC) — <https://github.com/fullstory/openfwwf>
- **seemoo-lab/d11-emu** — BCM43 D11 emulation framework — <https://github.com/seemoo-lab/d11-emu>
- **seemoo-lab/wintech23_nexmon_d11debug** — Nexmon D11 debug/state-extraction patch — <https://github.com/seemoo-lab/wintech23_nexmon_d11debug>
- Link, Breuer, Gringoli, Hollick, *Rolling the D11: An Emulation Game for the Whole BCM43 Family*, ACM WiNTECH '23 — <https://dl.acm.org/doi/10.1145/3615453.3616520>
- **seemoo-lab/nexmon** — C-based firmware patching framework; `d11.h`, TX header structs, injection/CSI patches — <https://github.com/seemoo-lab/nexmon>
- Nexmon `d11.h` (bcm43455c0) — <https://github.com/seemoo-lab/nexmon/blob/master/patches/bcm43455c0/7_45_154/nexmon/include/d11.h>
- Quarkslab, *Reverse-engineering Broadcom wireless chipsets* (ROM/RAM map, D11↔ARM, rx_fifo/SHM) — <https://blog.quarkslab.com/reverse-engineering-broadcom-wireless-chipsets.html>

### Related pages in this catalog
- `../../projects/nexmon.md` — the ARM-side patching framework
- `../../projects/openwifi.md` — programmable-MAC testbeds
- `../../projects/csi-toolchains.md` — CSI extraction
- `../bcm43455c0-raspberry-pi.md` — building/flashing Nexmon on the Pi
- `../broadcom-d11-ucode.md` — (this file)
- `../../docs/firmware-reversing.md`, `../../docs/verification-tier4.md`, `../../docs/techniques.md`
