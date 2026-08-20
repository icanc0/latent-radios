# OpenFWWF — Open FirmWare for WiFi networks (the original open Wi-Fi firmware)

*Cycle 7 — new file. The genuine open-firmware Wi-Fi experience on old Broadcom SoftMAC cards.*

**OpenFWWF** (Open FirmWare for WiFi networks) is a from-scratch, GPL-licensed
reimplementation of the MAC microcode ("ucode") that runs on the **D11**
microcontroller inside Broadcom BCM43xx **SoftMAC** Wi-Fi chips. It was written
at the *Università degli Studi di Brescia* (Dept. of Information Engineering,
the group around Francesco Gringoli) and published at
`http://netweb.ing.unibs.it/~openfwwf/`. Where Nexmon (see
[`nexmon.md`](./nexmon.md)) *patches* Broadcom's closed firmware, OpenFWWF
*replaces* it: the MAC ucode is source you can read, edit, assemble, and load.

This makes OpenFWWF the canonical **tier‑5 open‑firmware** entry for Wi-Fi — but
with an important honest caveat carried throughout this page: **only the MAC is
open. The PHY (baseband/radio) is still a closed hardware block** configured
through opaque "initvals" register dumps. You get an open, hackable *MAC state
machine*; you do **not** get an open PHY, CSI, or raw IQ. See
[`../../docs/verification-tier5-openfirmware.md`](../docs/verification-tier5-openfirmware.md)
for how this "open firmware, closed PHY" split is scored.

---

## 1. What runs where: the D11 and SoftMAC

Broadcom BCM43xx SoftMAC parts split the work:

- The **PHY** (802.11b DSSS / 802.11g OFDM baseband) is a fixed silicon block.
- The **D11 core** is a small, specialized microcontroller with its own
  instruction set. It runs the time-critical **MAC** — DIFS/SIFS/slot timing,
  backoff, ACK generation, RX filtering, TX descriptor handling — from ucode
  that the host driver **uploads at interface bring-up** (the ucode is *not* in
  on-card flash; it is loaded fresh every time). This upload model is exactly
  why replacing it is feasible: swap the file the driver uploads.
- The Linux **b43** driver (SoftMAC, uses `mac80211`) does association,
  encryption plumbing, and everything non-real-time on the host CPU.

Because the MAC lives in re-uploadable ucode on a documented-enough CPU, Brescia
could write a clean MAC from scratch. Contrast FullMAC parts (brcmfmac), where
the MAC is buried in a large closed firmware image — not OpenFWWF territory.

---

## 2. Which cards work

OpenFWWF targets the **low-cost 802.11b/g** BCM43xx generation driven by **b43**
(*not* b43legacy) with the **G‑PHY** and the matching D11 core/ucode revision.
Historically confirmed working silicon:

| Chip | Bus / typical form factor | PHY | Notes |
|------|---------------------------|-----|-------|
| **BCM4306** | PCI / miniPCI / CardBus | B/G | Early rev needs b43legacy; later rev (BCM4306/3) is b43 + OpenFWWF |
| **BCM4311 rev 1** | PCI/PCIe | G | The classic OpenFWWF target; later revs shift ucode rev |
| **BCM4318** | PCI / CardBus / USB (AirForce One 54g) | G | Very widely used, the "it just works" card |
| **BCM4320** | USB | B/G | b43(legacy)-class USB part |

See [`../../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md) for the
full Broadcom/Cypress chip table, core revisions, and the b43 vs. b43legacy
split. Common commodity hardware carrying these chips: Linksys WPC54G /
WMP54G, Dell TrueMobile 1300, Apple AirPort (BCM4306), Buffalo and ASUS
miniPCI cards.

**Match the ucode revision to the chip.** The generated ucode filename carries a
revision number (e.g. `ucode5.fw`) that must correspond to the D11 core revision
your card exposes. Loading a mismatched revision is the #1 failure mode. Check
which file b43 requests for *your* card (see §5) before overwriting anything.

---

## 3. The toolchain: b43-tools (the D11 assembler)

You cannot build OpenFWWF without **b43-tools**, Michael Büsch's toolkit for the
Broadcom 43xx D11 microcode. Verified upstream: **https://github.com/mbuesch/b43-tools**
(mirror of `git.bues.ch`). It contains:

- **`assembler/`** → **`b43-asm`**: the D11 **assembler** (this is the tool
  OpenFWWF's Makefile calls to turn `.asm` ucode source into a loadable `.fw`).
- **`disassembler/`** → **`b43-dasm`**: the D11 **disassembler** (for staring at
  Broadcom's *proprietary* ucode, the reverse-engineering companion).
- **`fwcutter/`** → **`b43-fwcutter`**: extracts the stock proprietary firmware
  out of a Broadcom driver blob (this is how you get the *original* `ucode*.fw`
  and `*initvals*.fw` files to back up and to compare against).
- `debug/`, `ssb_sprom/`: SPROM and debugging helpers.

Build the assembler:

```bash
git clone https://github.com/mbuesch/b43-tools
cd b43-tools/assembler
make                       # produces the b43-asm binary
sudo cp b43-asm /usr/local/bin/   # put it on PATH so OpenFWWF's Makefile finds it
# (optionally also build disassembler/ and fwcutter/ the same way)
```

The D11 instruction set that `b43-asm` targets is documented at
`http://bcm-v4.sipsolutions.net/802.11/Microcode` (arithmetic/logic, branch,
data-transfer, and bitwise instruction summaries). Use that as your ISA
reference when editing ucode. For the reverse-engineering workflow on the
*proprietary* ucode (offsets, SHM layout, register conventions) see
[`../../docs/firmware-reversing.md`](../docs/firmware-reversing.md) — and note
the project rule: **never guess ucode offsets; find them** with `b43-dasm` and
the SHM/register docs, not from memory.

---

## 4. Building the ucode

```bash
# grab the OpenFWWF source (canonical location; see references for archive note)
wget http://netweb.ing.unibs.it/~openfwwf/openfwwf-5.2.tar.gz
tar xzf openfwwf-5.2.tar.gz
cd openfwwf-5.2

# with b43-asm on your PATH:
make                       # assembles the .asm MAC source into firmware
```

`make` runs `b43-asm` over the OpenFWWF MAC source and emits the loadable
firmware set: the microcode image plus the PHY/radio **initvals** blobs the b43
driver uploads alongside it (the exact filenames carry the ucode revision, e.g.
`ucode5.fw` together with the `b0g0initvals5.fw` / `b0g0bsinitvals5.fw`-style
initval files). Do **not** assume the revision number — read it off your own
card's firmware requests (next section) and build/install the matching set.

> The initvals are Broadcom's closed PHY register sequences carried unchanged —
> this is precisely where "open firmware, closed PHY" bites: OpenFWWF ships the
> MAC as source but still needs the opaque PHY init table to bring the radio up.

---

## 5. Loading it in place of the proprietary ucode

b43 uploads firmware from `/lib/firmware/b43/` (b43legacy uses
`/lib/firmware/b43legacy/`). The plan: find out what your card requests, back it
up, drop OpenFWWF's files in, reload.

```bash
# 1. See exactly which files b43 wants for THIS card:
sudo modprobe -r b43
sudo modprobe b43
dmesg | grep -i b43          # logs the firmware filename/revision it loads
ls /lib/firmware/b43/        # the stock (fwcutter-extracted) ucode*.fw + initvals

# 2. Back up the proprietary firmware you are about to shadow:
sudo cp -a /lib/firmware/b43 /lib/firmware/b43.stock

# 3. Install the OpenFWWF build (matching revision) over it:
sudo cp ucode5.fw *initvals5.fw /lib/firmware/b43/    # names per YOUR card's rev

# 4. Reload and confirm the open ucode came up:
sudo modprobe -r b43 && sudo modprobe b43
dmesg | tail                 # look for a clean firmware load, no revision mismatch
```

If b43 refuses to bring the interface up, the usual cause is a **ucode-revision
mismatch** (§2) — restore `/lib/firmware/b43.stock` and rebuild against the
revision `dmesg` actually asked for. Keeping the stock tree lets you flip back
instantly, which you want when experimenting.

---

## 6. What you can experiment with

OpenFWWF's value is a **hackable, real MAC state machine on real 11b/g silicon**
that actually associates and passes traffic. Because you own the MAC source you
can change behavior that is normally frozen in the NIC:

- **Custom MAC timing** — edit SIFS/slot/DIFS handling, IFS values, and the
  backoff logic directly in ucode. Great for teaching/measuring CSMA/CA and for
  deliberate protocol violations in a lab.
- **TDMA MACs** — replace CSMA/CA contention with a time-slotted schedule; OpenFWWF
  was the substrate for a family of TDMA-on-commodity-hardware experiments.
- **ACK policy** — change or suppress ACK generation, alter ACK timeout, forge
  early/So-called "block" acknowledgement behavior for MAC research.
- **Covert / side channels** — modulate information into MAC-layer timing
  (inter-frame gaps, backoff choices) — a genuine covert-channel primitive that
  needs no PHY access, which is why this earns the `covert-channel` capability.
- **Full frame injection / custom control frames** at MAC level, timestamps, and
  instrumented counters in shared memory (SHM).

OpenFWWF is also the historical foundation of the **Wireless MAC Processor
(WMP)** line of work (Brescia/Palermo — Tinnirello, Bianchi, Gallo, Garlisi,
Gringoli et al.), which turned the ucode into a programmable MAC "engine" driven
by state machines — the clearest demonstration of why an *open MAC* matters even
when the PHY stays closed.

---

## 7. Honest limits

- **11b/g only.** DSSS up to 11 Mbps and OFDM up to 54 Mbps on 2.4 GHz. No
  802.11n/ac/ax, no 40/80 MHz, no MIMO. This is ancient PHY.
- **Closed PHY.** You edit the MAC; the baseband is a black box configured by
  opaque initvals. No PHY parameter you cannot express as an existing register
  write is reachable.
- **No CSI.** Unlike Atheros ath9k or the Intel 5300 tool, these parts expose no
  channel-state export. Do not expect per-subcarrier data.
- **No raw IQ, no arbitrary waveform.** You cannot synthesize samples; you can
  only make the fixed PHY send/receive standard 11b/g frames on MAC command.
- **Aging hardware.** BCM4306/4311/4318/4320 cards are PCI/CardBus/early-USB and
  increasingly hard to source; modern kernels still ship b43 but you need the
  physical NIC.

Net: OpenFWWF is a **tier‑5 open‑firmware** platform on the *firmware-openness*
axis — the whole MAC is auditable, buildable source — while sitting near the
bottom of the *RF-flexibility* axis. It is the reference example for why those
two axes must be scored separately; see
[`../../docs/verification-tier5-openfirmware.md`](../docs/verification-tier5-openfirmware.md).

---

## 8. References

- OpenFWWF project (Univ. di Brescia): `http://netweb.ing.unibs.it/~openfwwf/`
  — canonical source and the `openfwwf-5.2.tar.gz` tarball. *(The university host
  has been intermittently offline; consult the Internet Archive Wayback Machine
  snapshot of this URL if it does not resolve.)*
- b43-tools (D11 assembler/disassembler/fwcutter), Michael Büsch:
  `https://github.com/mbuesch/b43-tools`
- b43 driver, Linux wireless docs:
  `https://wireless.docs.kernel.org/en/latest/en/users/drivers/b43.html`
- Broadcom BCM43xx D11 microcode / ISA reference:
  `http://bcm-v4.sipsolutions.net/802.11/Microcode`
- b43 SPROM & general reverse-engineering wiki: `http://bcm-v4.sipsolutions.net/`

### See also (this catalog)
- [`../../chips/broadcom-cypress.md`](../chips/broadcom-cypress.md) — the BCM43xx chip/core-revision table
- [`./nexmon.md`](./nexmon.md) — patching *closed* Broadcom firmware (the modern counterpart)
- [`../../docs/verification-tier5-openfirmware.md`](../docs/verification-tier5-openfirmware.md) — scoring open-firmware vs. open-PHY
- [`../../docs/firmware-reversing.md`](../docs/firmware-reversing.md) — finding offsets in D11 ucode (never guess them)
