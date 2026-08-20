# Community & Resources

*Where to get help, go deeper, and contribute back.* This page is the "who to ask, where to read, how to give back" map for the Latent Radios catalog. Nothing here is a chip record — it is the human infrastructure around firmware reverse-engineering, CSI extraction, monitor/injection, and Wi‑Fi-as-SDR work. Every link below points at a primary source (project org, maintainer, mailing list, or conference series), not a mirror.

> **How to use this page.** If you are stuck on a *specific chip*, start with that chip's file in `../chips/` and the matching project file in `../projects/`, then bring a focused question to the venue below that owns that layer (kernel driver → linux-wireless; firmware patch → Nexmon issues; CSI shape → PicoScenes/CSI-tool trackers; injection → aircrack-ng). Ask with your exact adapter, chipset revision, kernel/driver version, and firmware build — "what NIC + what kernel + what firmware" answers 80% of the follow-up questions before they are asked.

---

## 1. Core GitHub orgs & maintainers

The people and orgs who actually merge the code. Filing a good issue or PR here is the single highest-leverage way to move a problem forward.

### Firmware patching & Wi‑Fi sensing

| Org / maintainer | What they own | Primary link |
|---|---|---|
| **seemoo-lab** (Secure Mobile Networking Lab, TU Darmstadt) | Nexmon firmware-patching framework; `nexmon_csi`; InternalBlue; many BCM/Cypress reversing tools | <https://github.com/seemoo-lab> |
| ↳ Nexmon | C-based firmware patching for Broadcom/Cypress Wi‑Fi (monitor, injection, base) | <https://github.com/seemoo-lab/nexmon> · issues: <https://github.com/seemoo-lab/nexmon/issues> |
| ↳ nexmon_csi | CSI extraction on BCM43xx / Cypress via Nexmon | <https://github.com/seemoo-lab/nexmon_csi> · issues: <https://github.com/seemoo-lab/nexmon_csi/issues> |
| **Zhiping Jiang** — PicoScenes | Cross-platform Wi‑Fi sensing/ISAC middleware (Intel AX2xx, QCA, USRP, and more) | docs: <https://ps.zpj.io/> · org: <https://github.com/wifisensing> · issues: <https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues> |
| **Daniel Halperin** — Linux 802.11n CSI Tool | The original Intel 5300 CSI toolchain (`iwlwifi` patch + `log_to_file`) | <https://dhalperi.github.io/linux-80211n-csitool/> · code: <https://github.com/dhalperi/linux-80211n-csitool> |
| **Yaxiong Xie** — Atheros CSI Tool | CSI on Atheros ath9k (per-subcarrier, no 30-subcarrier cap) | <https://wands.sg/research/wifi/AtherosCSI/> · code: <https://github.com/xieyaxiongfly/Atheros-CSI-Tool> |
| **open-sdr** — openwifi | Full open-source 802.11 SDR stack on Xilinx Zynq (FPGA PHY + Linux mac80211) | <https://github.com/open-sdr/openwifi> |

### Drivers, injection & adapters

| Org / maintainer | What they own | Primary link |
|---|---|---|
| **aircrack-ng** | `aircrack-ng` suite, `airmon-ng`, injection test (`aireplay-ng --test`), patched drivers | <https://github.com/aircrack-ng/aircrack-ng> · site: <https://www.aircrack-ng.org/> |
| **morrownr** | The de‑facto reference for USB Wi‑Fi adapters + out-of-tree drivers (8821au, 8852bu, 88x2bu…) and the "which adapter for monitor mode" guide | <https://github.com/morrownr> · adapter guide: <https://github.com/morrownr/USB-WiFi> |
| **Felix Fietkau (nbd)** & the **mt76** devs | `mt76` mainline driver for MediaTek (spectral scan, monitor, some CSI research builds) | <https://github.com/openwrt/mt76> · maintained via linux-wireless |
| **ath9k / ath10k / ath11k** kernel devs | Atheros/QCA mainline drivers (ath9k spectral scan + relayfs, the classic hacker's chip) | mainline kernel `drivers/net/wireless/ath/` via linux-wireless |
| **OpenWrt** | Downstream home for mt76/ath drivers, adapter compatibility, and real-world firmware/driver testing | <https://github.com/openwrt/openwrt> · forum: <https://forum.openwrt.org/> |
| **Kismet (Mike Kershaw / dragorn)** | Wireless capture/IDS, remote capture, datasource ecosystem | <https://www.kismetwireless.net/> · <https://github.com/kismetwireless/kismet> |

### Adjacent RF / SDR tooling (the "true SDR" neighbors)

| Org / maintainer | What they own | Primary link |
|---|---|---|
| **Great Scott Gadgets (Michael Ossmann)** | HackRF One, YARD Stick One, GreatFET, Ubertooth; and the free SDR course | <https://greatscottgadgets.com/> · <https://github.com/greatscottgadgets> |
| **Bastille Research** | Wireless offensive-security research: MouseJack, KeySniffer, nRF/keyboard tooling | <https://www.bastille.net/research> · <https://github.com/BastilleResearch> |
| **GNU Radio project** | The SDR DSP framework everything OOT plugs into (see `../projects/gnuradio-oot-modules.md`) | <https://www.gnuradio.org/> · <https://github.com/gnuradio/gnuradio> |
| **Osmocom** | rtl-sdr, gr-osmosdr, and a deep well of RF reverse-engineering projects | <https://osmocom.org/> · <https://gitea.osmocom.org/> |

---

## 2. Forums, mailing lists & chat

Pick the venue that matches the *layer* you are working at.

### Mailing lists (kernel & driver layer)

- **linux-wireless** — the mailing list for every mainline Wi‑Fi driver (ath9k/ath1xk, mt76, iwlwifi, brcmfmac, rtw88/rtw89). This is where driver bugs and patches actually get resolved.
  - Subscribe / archives: <http://vger.kernel.org/vger-lists.html#linux-wireless>
  - Patch queue (see what's in flight, review, respond): <https://patchwork.kernel.org/project/linux-wireless/list/>
  - Lore archive (searchable, linkable threads): <https://lore.kernel.org/linux-wireless/>
- **ath11k / ath12k & vendor lists** — several QCA drivers have dedicated `@lists.infradead.org` lists linked from the driver `MAINTAINERS` entry; use `get_maintainer.pl` (below) to find the right one.

### Issue trackers (project layer — often the fastest answer)

- Nexmon: <https://github.com/seemoo-lab/nexmon/issues> · nexmon_csi: <https://github.com/seemoo-lab/nexmon_csi/issues>
- PicoScenes: <https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues>
- aircrack-ng: <https://github.com/aircrack-ng/aircrack-ng/issues>
- openwifi: <https://github.com/open-sdr/openwifi/issues>
- morrownr driver repos: file against the specific driver repo (e.g. `8821au-20210708`, `rtl8852bu`) — include `dmesg` output.

### Reddit & web forums (broad help, hardware buying advice, "is this normal?")

- **r/RTLSDR** — <https://www.reddit.com/r/RTLSDR/> — beginner-friendly SDR, cheap-hardware community; good for RTL/HackRF adjacent questions.
- **r/SDR** — <https://www.reddit.com/r/SDR/> — broader software-defined radio.
- **r/hacking / r/AskNetsec / r/HowToHack** — offensive wireless context (use responsibly; see `../docs/rf-safety-and-legal.md`).
- **r/openwrt** and the **OpenWrt forum** — <https://forum.openwrt.org/> — real answers on which chipset does monitor mode / spectral scan on which router.
- **RTL-SDR.com blog** — <https://www.rtl-sdr.com/> — long-running news hub for SDR projects, including many Wi‑Fi-chip-as-SDR write-ups.

### Chat

- **GNU Radio** Matrix/Discord and mailing list, linked from <https://www.gnuradio.org/> (see also `../projects/gnuradio-oot-modules.md`).
- Many kernel/driver maintainers are reachable on OFTC/Libera IRC channels (e.g. `#kernelnewbies`, project-specific channels) — check the project README before pinging.

> **Etiquette that gets you answered.** Search the archive/tracker first; post a minimal reproducer; state exact hardware + `uname -r` + driver/firmware version; paste `dmesg`/logs as text, not screenshots; and never top-post on the kernel lists. On linux-wireless, plain-text email only — HTML mail is silently dropped.

---

## 3. Conferences & talk archives

Where this field is published and demoed. Proceedings and recorded talks are often the *best* primary sources for a technique.

| Venue | Focus | Where to look |
|---|---|---|
| **ACM WiSec** (Security & Privacy in Wireless and Mobile Networks) | The home venue for Wi‑Fi sensing, CSI attacks, PHY-layer security, firmware reversing | series/proceedings: <https://dl.acm.org/conference/wisec> |
| **ACM MobiSys** | Mobile systems; much of the CSI/sensing systems work lands here | <https://www.sigmobile.org/mobisys/> · proceedings: <https://dl.acm.org/conference/mobisys> |
| **ACM MobiCom** | Mobile computing/networking; foundational CSI + ISAC papers | <https://www.sigmobile.org/mobicom/> · <https://dl.acm.org/conference/mobicom> |
| **USENIX Security / NDSS / IEEE S&P** | Wireless attacks with broad security impact (KRACK, FragAttacks, etc.) — talks + papers free online | <https://www.usenix.org/conferences> · <https://www.ndss-symposium.org/> |
| **DEF CON — RF Hackers Sanctuary / Wireless Village** | Hands-on wireless hacking, CTFs, tooling demos | <https://rfhackers.com/> · <https://defcon.org/> · media archive: <https://media.defcon.org/> |
| **Chaos Communication Congress (CCC)** | Deep RF/firmware reversing talks; full video archive | <https://media.ccc.de/> |
| **GNU Radio Conference (GRCon)** | SDR DSP, OOT modules, applications | <https://www.gnuradio.org/grcon/> |

**Landmark talks/papers worth starting from** (find via the venues above): the Nexmon papers (Schulz, Wegemer, Hollick), *"Free Your CSI"* / nexmon_csi (Gringoli et al., WiSec), the Halperin *"Tool release: gathering 802.11n traces with channel state information"* note (ACM SIGCOMM CCR), and the Atheros-CSI-Tool paper (Xie, Li, WANDS group). These are the canonical citations behind most entries in `../projects/csi-toolchains.md`.

---

## 4. Books, courses & self-study

### Free, high-quality, and directly relevant

- **PySDR: A Guide to SDR and DSP using Python** — Marc Lichtman. The best free on-ramp to IQ, FFTs, and DSP intuition. <https://pysdr.org/>
- **Software-Defined Radio for Engineers** — Travis F. Collins et al. (Analog Devices). Free PDF, rigorous. <https://www.analog.com/en/resources/technical-books/software-defined-radio-for-engineers.html>
- **Software Defined Radio with HackRF** — Michael Ossmann's free video course; the standard practical intro. <https://greatscottgadgets.com/sdr/>
- **The GNU Radio wiki & tutorials** — <https://wiki.gnuradio.org/index.php?title=Tutorials>

### Books (paid, but foundational)

- **802.11 Wireless Networks: The Definitive Guide** — Matthew Gast (O'Reilly). The reference for what the frames/PHYs actually are.
- **The Art of Software Security Assessment** / **Practical Reverse Engineering** (Dang, Gazet, Bachaalany) — for the firmware-RE muscle behind Nexmon-style work; pairs with `../docs/firmware-reversing.md`.
- **Ghidra Book: The Definitive Guide** (Eagle & Nance) — matches the tooling in `../docs/walkthroughs/ghidra-setup-wifi-firmware.md`.

### In-repo learning path

Read in this order for a working mental model: `../docs/taxonomy.md` (the tier ladder) → `../docs/glossary.md` → `../docs/techniques.md` → `../docs/firmware-reversing.md` → a concrete walkthrough (`../docs/walkthroughs/atheros-ath9k-spectral-csi.md` or `../docs/walkthroughs/intel-5300-csi.md`) → `../docs/true-sdr-comparison.md` for honest expectations vs. a real SDR. Safety and legality first: `../docs/rf-safety-and-legal.md`.

---

## 5. How to contribute upstream

Fixes flow *upstream* — into the kernel, into aircrack, into the project that owns the code — not just into forks. Here is how to do it well at each layer.

### To the Linux kernel (driver/PHY bugs, new chip support)

1. Read `Documentation/process/submitting-patches.rst` and `submitting-drivers.rst`: <https://www.kernel.org/doc/html/latest/process/submitting-patches.html>
2. Find the right maintainers and list for the file you touched:
   ```sh
   scripts/get_maintainer.pl -f drivers/net/wireless/ath/ath9k/
   ```
3. Build against the correct tree — wireless work goes through **wireless / wireless-next** (see the linux-wireless wiki: <https://wireless.wiki.kernel.org/>), not directly to Linus.
4. Send patches with `git send-email` in plain text to **linux-wireless@vger.kernel.org**, CC the maintainers, and follow the thread on <https://patchwork.kernel.org/project/linux-wireless/list/>. Expect review rounds — that is normal and good.

### To aircrack-ng

- Contribution guide: <https://github.com/aircrack-ng/aircrack-ng/blob/master/CONTRIBUTING.md>
- Fork → feature branch → PR against `master`; include a description of the adapter/driver you tested on. Injection/monitor changes should note the exact chipset.

### To Nexmon / nexmon_csi / PicoScenes / openwifi

- These take GitHub PRs. Nexmon patches are C files under the chip's `patches/` tree — mirror the existing directory layout for your firmware version and document how you located any offsets (never hard-code a magic address without showing the derivation; see `../docs/firmware-reversing.md`).
- For PicoScenes, open a tracker issue first to align on hardware/format before a large change: <https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues>.

### To adapter/driver knowledge (morrownr, OpenWrt)

- New confirmed monitor/injection/spectral results for a specific USB dongle or router chipset are genuinely valuable — file them against the relevant morrownr driver repo or the OpenWrt device page with your test method.

### To *this* catalog (Latent Radios)

- See **[CONTRIBUTING.md](../CONTRIBUTING.md)** for the record schema, the `sdr_tier` 0–5 ladder, the `status` honesty rule (`verified` / `reported` / `theoretical`), and how to add a chip or project file.
- The bar: **primary sources with real URLs**, honest tiers, and — for anything involving transmit — the safety/legal notes required by `../docs/rf-safety-and-legal.md`. Never invent register offsets; show how they were found.

---

## 6. Quick-reference index

- **Deeper reading list:** [further-reading.md](./further-reading.md)
- **Contribution rules & schema:** [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Safety & legal (read before any TX):** [../docs/rf-safety-and-legal.md](./rf-safety-and-legal.md)
- **Chip families:** [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) · [../chips/intel.md](../chips/intel.md) · [../chips/realtek.md](../chips/realtek.md) · [../chips/other-vendors.md](../chips/other-vendors.md) · [../chips/hardware-index.md](../chips/hardware-index.md)
- **Projects:** [../projects/openwifi.md](../projects/openwifi.md) · [../projects/csi-toolchains.md](../projects/csi-toolchains.md) · [../projects/nexmon.md](../projects/nexmon.md) · [../projects/gnuradio-oot-modules.md](../projects/gnuradio-oot-modules.md)

---

### References

- Nexmon framework — <https://github.com/seemoo-lab/nexmon>
- nexmon_csi — <https://github.com/seemoo-lab/nexmon_csi>
- Secure Mobile Networking Lab (SEEMOO), TU Darmstadt — <https://github.com/seemoo-lab>
- PicoScenes documentation — <https://ps.zpj.io/> and org <https://github.com/wifisensing>
- PicoScenes issue tracker — <https://github.com/wifisensing/PicoScenes-Issue-Tracker/issues>
- Linux 802.11n CSI Tool (Halperin) — <https://dhalperi.github.io/linux-80211n-csitool/>
- Atheros CSI Tool (Xie/Li, WANDS) — <https://wands.sg/research/wifi/AtherosCSI/>
- openwifi — <https://github.com/open-sdr/openwifi>
- aircrack-ng — <https://www.aircrack-ng.org/> and <https://github.com/aircrack-ng/aircrack-ng>
- morrownr USB-WiFi — <https://github.com/morrownr/USB-WiFi>
- mt76 driver — <https://github.com/openwrt/mt76>
- linux-wireless list — <http://vger.kernel.org/vger-lists.html#linux-wireless>
- linux-wireless patchwork — <https://patchwork.kernel.org/project/linux-wireless/list/>
- linux-wireless lore archive — <https://lore.kernel.org/linux-wireless/>
- linux-wireless wiki — <https://wireless.wiki.kernel.org/>
- Kernel submitting-patches — <https://www.kernel.org/doc/html/latest/process/submitting-patches.html>
- Great Scott Gadgets — <https://greatscottgadgets.com/>
- Bastille Research — <https://www.bastille.net/research>
- Kismet — <https://www.kismetwireless.net/>
- GNU Radio — <https://www.gnuradio.org/>
- ACM WiSec series — <https://dl.acm.org/conference/wisec>
- ACM MobiSys — <https://www.sigmobile.org/mobisys/>
- DEF CON RF Hackers Sanctuary — <https://rfhackers.com/>
- media.ccc.de — <https://media.ccc.de/>
- PySDR — <https://pysdr.org/>
- Software-Defined Radio for Engineers — <https://www.analog.com/en/resources/technical-books/software-defined-radio-for-engineers.html>
- Software Defined Radio with HackRF (Ossmann) — <https://greatscottgadgets.com/sdr/>
- r/RTLSDR — <https://www.reddit.com/r/RTLSDR/> · r/SDR — <https://www.reddit.com/r/SDR/>
- RTL-SDR.com — <https://www.rtl-sdr.com/>
