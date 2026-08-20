# Monitor-Mode & Injection Driver Support, by Chip

> The question everyone actually asks: *"Will this card do monitor mode and packet injection on Linux — and does it work on 5 GHz?"*
> This is the practical answer index. It maps chip/family → Linux driver (in-tree name or out-of-tree repo) → monitor? → injection? → 5 GHz? → notes, then explains the caveats that a one-line "yes" hides.

Monitor mode (RX every frame, including ones not addressed to you) and injection (TX arbitrary raw 802.11 frames) are **separate capabilities**. A driver can do one without the other. "Injection works" is also not binary: some drivers inject only management/data at the current associated rate, some rewrite the sequence number or duration field on you, and some silently drop frames above a size or rate. Treat every "yes" below as "yes, with the caveats in the notes."

**How to read the tiers vs. this page.** In the Latent Radios taxonomy this is the **tier-1 floor** (monitor + injection / raw-packet). None of it is CSI (tier 2) or PHY-level (tier 3+). It is the baseline that everything else — [nexmon](../projects/nexmon.md) CSI, [PicoScenes](../projects/picoscenes.md), [openwifi](../projects/openwifi.md) — is measured against. See [../docs/taxonomy.md](../docs/taxonomy.md) and [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md).

---

## Master table

Legend — **M** = monitor, **I** = injection. `✔` solid / mainline-quality · `▲` works with caveats (see notes) · `✘` no / broken · `—` n/a.

| Chip / family | Bands | Linux driver | In-tree? | M | I | 5 GHz | Notes |
|---|---|---|---|---|---|---|---|
| Atheros AR92xx (AR9280/9285/9287) | 2.4/5 | **ath9k** | in-tree | ✔ | ✔ | ✔ | The reference PCIe/mini-PCIe card. Best-in-class injection, honours user rate/retry. Fully mac80211. |
| Atheros AR9271 / AR7010 | 2.4 only | **ath9k_htc** | in-tree | ✔ | ✔ | ✘ | The classic USB penetration-testing chip (Alfa AWUS036NHA, TL-WN722N **v1**). Needs `ath9k_htc` firmware blob. 2.4 GHz only. |
| Qualcomm QCA988x/9880/9887/9888 | 2.4/5 | **ath10k** (`ath10k_pci`) | in-tree | ✔ | ▲ | ✔ | Monitor solid. Injection depends on firmware branch; `ath10k-ct` (Candela) firmware widens what works. Some rate-set limits. |
| Qualcomm QCA6174/9377/9984 | 2.4/5 | **ath10k** | in-tree | ▲ | ▲ | ✔ | 6174/9377 (common in laptops) monitor is flaky per-firmware; injection unreliable. Not a first choice. |
| Qualcomm QCN9074/IPQ80xx (WiFi 6) | 2.4/5/6 | **ath11k** | in-tree | ▲ | ▲ | ✔ | Monitor improving over kernels; injection partial. AP/embedded silicon, few USB options. |
| Qualcomm WCN785x (WiFi 7) | 2.4/5/6 | **ath12k** | in-tree | ▲ | ✘ | ✔ | Early. Monitor landing per-release; injection not there yet (2025). |
| MediaTek MT7601U | 2.4 only | **mt7601u** | in-tree | ✔ | ▲ | ✘ | Old cheap dongle; superseded by mt76 core. |
| MediaTek MT7610U/MT7612U | 2.4/5 | **mt76x0u / mt76x2u** (mt76) | in-tree | ✔ | ✔ | ✔ | **Top 2025 pick for a 5 GHz USB injector.** morrownr now steers monitor-mode users here. Solid mac80211 injection. |
| MediaTek MT7612E/MT7615/MT7915 | 2.4/5(/6) | **mt76x2e / mt7615 / mt7915** (mt76) | in-tree | ✔ | ✔ | ✔ | PCIe/AP parts. mt7915 = WiFi-6; strong monitor, injection good. |
| MediaTek MT7921AU/MT7921U (WiFi 6) | 2.4/5/6 | **mt7921u** (mt76) | in-tree | ✔ | ✔ | ✔ | **The modern do-everything USB WiFi-6 dongle.** In-tree, monitor + injection work. morrownr-recommended. |
| MediaTek MT7922/MT7925 (WiFi 6E/7) | 2.4/5/6 | **mt7921 / mt7925** (mt76) | in-tree | ✔ | ▲ | ✔ | Laptop M.2. Monitor good; injection generally works, newest parts still stabilising. |
| Intel 3945/4965/5xxx/6xxx (iwlegacy/iwlwifi) | 2.4/5 | **iwlwifi** | in-tree | ✔ | ▲ | ✔ | Monitor works. Injection historically limited/partial; firmware rewrites fields. Not a pen-test card. |
| Intel 7260 → AX210/AX211/BE200 | 2.4/5/6 | **iwlwifi** | in-tree | ✔ | ▲ | ✔ | Monitor yes (great for sniffing). Injection **limited** — some frames go, rates/retries not fully honoured; no reliable raw injection. |
| Realtek RTL8187L | 2.4 only | **rtl8187** | in-tree | ✔ | ✔ | ✘ | The *original* aircrack dongle (Alfa AWUS036H). 2.4 only, legacy. |
| Realtek RTL8188EUS/RTL8188EU | 2.4 only | **r8188eu** (in-tree) / **rtl8188eus** (aircrack-ng) | both | ✔ | ▲ | ✘ | In-tree `r8188eu` monitor OK; injection quality better on the out-of-tree aircrack-ng/rtl8188eus fork. TL-WN722N **v2/v3** are this chip. |
| Realtek RTL8812AU/RTL8821AU/RTL8814AU | 2.4/5 | **aircrack-ng/rtl8812au** (OOT) | out-of-tree | ✔ | ✔ | ✔ | Classic 5 GHz USB injector (Alfa AWUS036ACH). **Repo now marked DEPRECATED**, points at rtw88. Injection works but non-mainline; DKMS breakage on new kernels is common. |
| Realtek RTL8812AU (mac80211 path) | 2.4/5 | **rtw88** (lwfinger / in-tree) | both | ▲ | ▲ | ✔ | mac80211 driver; kernel 6.14 ships an in-kernel 8812au. Monitor OK; **injection is weaker than the vendor-fork** driver. |
| Realtek RTL8811CU/RTL8821CU | 2.4/5 | **morrownr/8821cu-20210916** (OOT) | out-of-tree | ▲ | ▲ | ✔ | morrownr repo focuses on managed/AP use; monitor+injection work but not the repo's priority. Also `rtw88` in newer kernels. |
| Realtek RTL8812BU/RTL8822BU | 2.4/5 | **morrownr/88x2bu-20210702** (OOT) / **rtw88** | both | ▲ | ▲ | ✔ | rtw88 is mac80211 (kernel 5.4+). Monitor works; injection partial. |
| Realtek RTL8852AU/RTL8852BU (WiFi 6) | 2.4/5/6 | **morrownr/rtl8852bu** (OOT) / **rtw89** | both | ▲ | ✘ | ✔ | rtw89 is mac80211 but **injection is essentially not supported** as of 2025; monitor variable. Buy MediaTek instead if you need injection. |
| Ralink RT2500/RT2800 USB/PCI | 2.4/(5) | **rt2x00** (`rt2800usb`/`rt2800pci`) | in-tree | ✔ | ✔ | ▲ | Old but honest mac80211 injection. RT3572/RT5572 add 5 GHz. Slow, but reliable for teaching. |
| Broadcom/Cypress BCM43xx (43430/43436/43455/4358/4366) | 2.4/5 | **brcmfmac + nexmon** patch | patched | ▲ | ▲ | ▲ | Stock `brcmfmac` = **no** monitor/injection. **[nexmon](../projects/nexmon.md)** firmware patches add monitor (and injection on some) — this is the Pi/mobile-SoC path, not a plug-and-play dongle. See [nexmon](../projects/nexmon.md). |

---

## Per-driver detail

### ath9k / ath9k_htc — the gold standard
`ath9k` (PCIe AR92xx) and `ath9k_htc` (USB AR9271/AR7010) remain the drivers everything else is compared to. Both are fully mac80211, honour the rate/retry/duration you set with `radiotap` headers, and inject cleanly. `ath9k_htc` is **2.4 GHz only** — this is the single most common surprise. The **TL-WN722N v1** and **Alfa AWUS036NHA** are AR9271; later revisions of the WN722N are *not* (see below). AR9271 needs the `htc_9271.fw` firmware in `/lib/firmware/ath9k_htc/`.

```
sudo airmon-ng start wlan0          # or: iw dev wlan0 set type monitor
iw dev wlan0 info                   # confirm "type monitor"
sudo aireplay-ng --test wlan0       # injection self-test
```

### ath10k / ath11k / ath12k — capable but firmware-gated
`ath10k` monitor is dependable; **injection depends on the firmware image**. The stock QCA firmware is conservative; the community **`ath10k-ct`** (Candela Tech) firmware/driver pair (`github.com/greearb/ath10k-ct`) enables more rate-sets and higher-density monitor/AP behaviour and is the usual choice when injection or many-VIF monitor is needed. `ath11k` (WiFi-6, QCN9074) monitor support has matured across recent kernels; injection is partial. `ath12k` (WiFi-7) is early — treat injection as unavailable in 2025.

### mt76 — the modern recommendation
The in-tree **mt76** family is now the pragmatic answer for "a USB adapter that does monitor + injection + 5 GHz out of the box." No DKMS, no vendor fork: it's mainline mac80211.
- **MT7612U** (`mt76x2u`) — WiFi-5, dual-band, the reliable 5 GHz injector.
- **MT7921AU** (`mt7921u`) — WiFi-6, dual-band + 6 GHz-capable silicon, in-tree, monitor + injection.
- **MT7915** (`mt7915e`, PCIe) — WiFi-6 AP silicon, strong monitor/injection for lab work.

morrownr's own chipset guide now marks MT7612U and MT7921AU as recommended-for-Linux with monitor mode, explicitly steering monitor-mode users toward MediaTek rather than Realtek.

### iwlwifi — monitor yes, injection no (really)
Intel `iwlwifi` (7260 through AX210/AX211/BE200) does **monitor mode** well and is excellent for passive sniffing on any band including 6 GHz on AX210. **Injection is the weak point**: the firmware is closed and rewrites header fields (sequence numbers, sometimes duration), does not honour arbitrary rates/retries, and drops many raw frames. Some `aireplay-ng` attacks appear to "work" but are unreliable. Do not buy an Intel card *for* injection — use it for capture.

### The Realtek out-of-tree reality
This is where most confusion lives. There are three overlapping worlds:

1. **aircrack-ng/rtl8812au** (`github.com/aircrack-ng/rtl8812au`) — supports **RTL8812AU / RTL8821AU / RTL8814AU**, monitor + frame injection both work, dual-band. **The README now carries a DEPRECATION notice** and points users to `lwfinger/rtw88`. Still the best-injecting driver for these chips, but expect kernel-version breakage and DKMS rebuilds.
2. **morrownr drivers** (`github.com/morrownr/8812au-20210629`, `88x2bu-20210702`, `8821cu-20210916`, `rtl8852bu`, etc.) — maintained, tracked to modern kernels (through 6.x/7.x), but **oriented to managed-client / AP use**. Recent 8812au morrownr branches state **monitor mode is not supported** and refer users to MediaTek. So "morrownr" is *not* automatically a monitor/injection driver — check the specific repo.
3. **rtw88 / rtw89** (mac80211; `lwfinger/rtw88`, and increasingly in-tree — kernel 6.14 ships an in-kernel 8812au) — the "correct" long-term path. `rtw88` covers 8821au/8822bu/8812bu/8814au and is kernel-5.4+; `rtw89` covers the WiFi-6 8852 parts. **Monitor works; injection is weaker than the vendor forks, and on rtw89/8852 injection is effectively unavailable in 2025.**

**Practical takeaway for Realtek:** if you have an 8812AU/8814AU card and need injection today, the aircrack-ng fork still injects best; for a card you'll keep across kernel upgrades, rtw88's mac80211 driver is less fragile but injects less. New WiFi-6 Realtek (8852) is a poor injection choice. See [../chips/realtek.md](../chips/realtek.md) and the hands-on [../docs/walkthroughs/rtl8812au-monitor-injection.md](../docs/walkthroughs/rtl8812au-monitor-injection.md).

### brcmfmac + nexmon — the patched path
Stock `brcmfmac` gives you **neither** monitor nor injection on Broadcom/Cypress FullMAC parts. The **[nexmon](../projects/nexmon.md)** project patches the on-chip firmware to expose monitor mode (and injection on supported chips such as BCM43455c0 on the Raspberry Pi). This is firmware reverse-engineering, not a dongle you plug in — but it's how you get monitor/injection *and* CSI out of a Pi or a rooted phone. Walkthrough: [../docs/walkthroughs/bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md).

### rt2x00 — old, slow, honest
`rt2800usb`/`rt2800pci` inject correctly through mac80211. RT3572/RT5572 variants add 5 GHz. Throughput is poor and these are legacy, but they're a dependable teaching/injection reference when you already own one.

---

## The aircrack-ng compatibility reality

The aircrack-ng project's own [compatibility guide](https://www.aircrack-ng.org/doku.php?id=compatibility_drivers) frames drivers in four buckets rather than promising per-chip support:

- **Vendor drivers** (Realtek's own, Broadcom's own): *"do not and will not support monitor mode."*
- **Peer-modified vendor drivers** (the morrownr / aircrack-ng forks): *"may support monitor mode but there could be caveats."*
- **Staging drivers**: quality unknown until mainlined.
- **mac80211 / in-kernel drivers**: *"chances are monitor mode is supported. Injection may or may not be supported."*

That last line is the whole story: **monitor ≈ solved on any mac80211 driver; injection is the differentiator.** Verify, don't assume, with the built-in self-test:

```
sudo airmon-ng start wlan0
sudo aireplay-ng --test wlan0mon      # "Injection is working!" or a list of APs that answered
```

If `--test` reports 0/30 or hangs, the driver "supports" injection only on paper. Also run `airmon-ng check kill` first — NetworkManager/wpa_supplicant reclaiming the interface is the #1 false negative.

---

## Which USB dongle *actually* works in 2025

A short, honest buy-list. Prefer **in-tree mac80211** so a kernel update doesn't brick you.

| Goal | Buy | Chip / driver | Why |
|---|---|---|---|
| 2.4 GHz, bulletproof, in-tree | Alfa AWUS036NHA | AR9271 / `ath9k_htc` | Best injection ever shipped in USB; 2.4-only. |
| 2.4 + 5 GHz, zero-hassle, in-tree | Any MT7612U adapter (Alfa AWUS036ACM) | MT7612U / `mt76x2u` | In-tree, monitor + injection + 5 GHz, no DKMS. **Default recommendation.** |
| WiFi-6, dual-band, in-tree, futureproof | MT7921AU adapter | MT7921AU / `mt7921u` | In-tree WiFi-6, monitor + injection, morrownr-approved. |
| You already own an 8812AU (AWUS036ACH) | keep it | RTL8812AU / aircrack-ng fork | Injects well, but DKMS + deprecation; not what to buy new. |
| Passive 6 GHz sniffing (no injection) | Intel AX210 M.2 | AX210 / `iwlwifi` | Great monitor incl. 6 GHz; injection unreliable — capture only. |

**Traps to avoid**
- **TL-WN722N**: only **v1** is AR9271 (`ath9k_htc`, great). **v2/v3** are RTL8188EUS — different driver, 2.4-only, weaker injection. Check the version on the box/FCC ID.
- **RTL8852 (WiFi-6) USB adapters**: `rtw89` gives you a working client but injection is essentially absent in 2025. Don't buy for pen-testing.
- **"Kali-compatible" listings**: marketing, not a guarantee. Match the *chip*, not the label.
- **Onboard-Windows-driver "multi-state" dongles**: eject the CD-ROM emulation with `usb_modeswitch`; some never enumerate cleanly on Linux.

---

## Verifying it yourself (any card)

```
# 1. Identify the actual chip (label lies; chip doesn't)
lsusb            # USB: match idVendor:idProduct on WikiDevi / linux-hardware.org
lspci -k         # PCIe: shows bound driver under "Kernel driver in use"

# 2. Can it enter monitor?
sudo airmon-ng check kill
sudo iw dev wlan0 set type monitor && sudo ip link set wlan0 up
iw dev wlan0 info | grep type          # -> "type monitor"

# 3. Does it actually inject?
sudo aireplay-ng --test wlan0

# 4. Does 5 GHz tune?
iw phy | grep -A2 '5[0-9][0-9][0-9] MHz'   # are 5 GHz channels listed & not disabled?
sudo iw dev wlan0 set channel 36
```

Regulatory note: some 5 GHz channels are DFS/no-IR (`no IR` in `iw list`), and your `regdomain` (`iw reg get`) may block channels or TX entirely. That is a *policy* limit, not a driver one. **Any injection is a transmit** — you are legally responsible for it; test into a controlled/owned network, mind band/power rules, and see [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md).

---

## Cross-references

- Chip-level Realtek detail: [../chips/realtek.md](../chips/realtek.md)
- Hands-on Realtek injection setup: [../docs/walkthroughs/rtl8812au-monitor-injection.md](../docs/walkthroughs/rtl8812au-monitor-injection.md)
- Atheros/Qualcomm chips: [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · MediaTek: [../chips/mediatek-ralink.md](../chips/mediatek-ralink.md) · Intel: [../chips/intel.md](../chips/intel.md) · Broadcom/Cypress: [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md)
- Adapter part numbers: [../chips/hardware-index.md](../chips/hardware-index.md)
- Firmware-patch path for monitor/injection: [../projects/nexmon.md](../projects/nexmon.md)
- Where tier-1 sits vs. CSI/PHY: [../docs/taxonomy.md](../docs/taxonomy.md) · [../docs/true-sdr-comparison.md](../docs/true-sdr-comparison.md)

## References

1. Aircrack-ng — *Compatibility drivers*: <https://www.aircrack-ng.org/doku.php?id=compatibility_drivers>
2. Aircrack-ng — *Which adapter?*: <https://www.aircrack-ng.org/doku.php?id=compatible_cards>
3. morrownr/USB-WiFi (chipset & monitor-mode guidance): <https://github.com/morrownr/USB-WiFi>
4. morrownr/8812au-20210629 (monitor-mode notes; MediaTek steer): <https://github.com/morrownr/8812au-20210629>
5. aircrack-ng/rtl8812au (RTL8812AU/8821AU/8814AU, monitor+injection, deprecation notice): <https://github.com/aircrack-ng/rtl8812au>
6. lwfinger/rtw88 (mac80211 Realtek USB, kernel 5.4+): <https://github.com/lwfinger/rtw88>
7. lwfinger/rtw89 (Realtek 8852 WiFi-6): <https://github.com/lwfinger/rtw89>
8. greearb/ath10k-ct (Candela firmware/driver for wider ath10k support): <https://github.com/greearb/ath10k-ct>
9. Linux `mt76` driver (in-tree): <https://wireless.wiki.kernel.org/en/users/drivers/mediatek>
10. Linux `ath9k` / `ath9k_htc` (in-tree): <https://wireless.wiki.kernel.org/en/users/drivers/ath9k>
11. Linux `iwlwifi` (in-tree; injection limitations): <https://wireless.wiki.kernel.org/en/users/drivers/iwlwifi>
12. nexmon (Broadcom/Cypress monitor+injection via firmware patch): <https://github.com/seemoo-lab/nexmon>
