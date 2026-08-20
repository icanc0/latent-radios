# Verifying Tier-1: Which Chips Actually Inject in 2025?

> An honesty audit of the most-populated rung of the SDR ladder. Tier-1 is defined as
> **monitor + injection / raw-packet** access (see [taxonomy.md](./taxonomy.md)). It is the
> tier we over-populate most aggressively, because "the datasheet says it does 802.11" and
> "the driver has a monitor interface" get silently rounded up to "it injects." They are not
> the same claim. This page separates the chips that *actually* put attacker-controlled 802.11
> frames on the air today from the ones that only *listen*, and issues corrected module records
> for the over-claimers.

Related: [taxonomy.md](./taxonomy.md) · [../chips/monitor-injection-support.md](../chips/monitor-injection-support.md) ·
[verification-tier2-csi.md](./verification-tier2-csi.md) · [verification-tier3-spectral.md](./verification-tier3-spectral.md) ·
[../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../chips/mediatek-ralink.md](../chips/mediatek-ralink.md) ·
[../chips/realtek.md](../chips/realtek.md) · [../chips/intel.md](../chips/intel.md) · [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md)

---

## 1. What "injection works" actually means

Four capabilities get conflated under the Tier-1 label. They fail independently:

| Capability | What it proves | How you test it |
|---|---|---|
| **Monitor RX** | The radio hands the host raw 802.11 frames (incl. not-for-me) with a radiotap header | `airmon-ng start wlan0`; `tcpdump -i wlan0mon -e` shows foreign BSSIDs |
| **Basic injection** | The NIC transmits an attacker-supplied frame verbatim | `aireplay-ng -9 wlan0mon` prints `Injection is working!` |
| **Injection while associated / on a channel with traffic** | The rate control + TX path don't starve or rewrite your frame | `aireplay-ng -9 -i wlan0mon` against a known AP, watch the `x/30` ratio |
| **Injection with control over rate / retries / seq / duration** | The firmware exposes the MAC knobs, not just "send this once" | radiotap TX flags honored; `packetforge-ng` + deauth/fakeauth land |

A chip that passes `-9` in an empty room but rewrites your rate, refuses to inject while
associated, or drops frames the moment real traffic appears is **not** a reliable Tier-1
injector — it is a monitor card that occasionally transmits. The aircrack-ng
[injection test](https://www.aircrack-ng.org/doku.php?id=injection_test) (`aireplay-ng -9`)
is the ground-truth gate we use throughout this page; the
[compatibility/driver taxonomy](https://www.aircrack-ng.org/doku.php?id=compatibility_drivers)
is the ground-truth source for *why* a given driver behaves the way it does (vendor blob vs.
peer-modified vendor driver vs. staging vs. mac80211).

**The single most important structural fact:** aircrack-ng's own driver taxonomy states that
*mac80211* (in-tree, softMAC) drivers usually have monitor mode and *may or may not* have
injection, while *vendor* and *staging* drivers frequently do not — and that **FullMAC**
designs (where association and TX scheduling live in closed firmware) give the host no path to
inject at all unless someone reverse-engineers the firmware. That is the line that predicts
almost every entry below.

---

## 2. The verdict table

Reliability grades:

- **A — Reference-grade.** Injects out of the box with an in-tree mainline driver, honors rate
  control, works while traffic is present. This is what "Tier-1" should mean.
- **B — Solid with the right out-of-tree driver.** Injects reliably, but only after installing a
  specific community DKMS driver; the in-kernel driver is monitor-limited or newer/unproven.
- **C — Works, with caveats.** Injects, but with known quirks (rate rewriting, single-stream, 2.4-only, seq issues).
- **D — Monitor yes, injection flaky/no.** Raw RX works; injection is broken, silently dropped, or firmware-gated.
- **F — Neither, natively.** FullMAC/vendor stack: no host injection path without firmware RE (e.g. Nexmon).

| Chip | Driver (2025) | Injection today | Grade | Caveat |
|---|---|---|---|---|
| **Atheros AR9280 / AR9285 / AR9287** (PCIe/miniPCIe) | `ath9k` (mainline, mac80211 softMAC) | Full, honors rate/retry, works associated | **A** | The reference softMAC. Also does spectral scan. Ageing, PCIe/miniPCIe only. |
| **Atheros AR9271** (USB, single-chip) | `ath9k_htc` + [open-ath9k-htc-firmware](https://github.com/qca/open-ath9k-htc-firmware) | Full | **A** | Gold-standard USB injector. **2.4 GHz only, 1×1.** TL-WN722N **v1 only** — v2/v3 are RTL8188EUS. |
| **Atheros AR7010** (USB SoC + AR928x) | `ath9k_htc` + open firmware | Full, dual-band | **A** | Same open-firmware stack as AR9271; pairs an external AR9280/AR9287. |
| **MediaTek/Ralink MT7612U** | `mt76x2u` (mainline mac80211) | Full, dual-band | **A** | Alfa AWUS036ACM. aircrack-ng's long-standing "just works" dual-band USB pick. |
| **MediaTek MT7610U** | `mt76x0u` (mainline) | Works | **B/C** | Single-stream 11ac; fine for injection, modest throughput. |
| **Ralink RT3070 / RT5370 / RT5372** | `rt2800usb` (mainline) | Full, 2.4-only | **A** | The classic cheap injector; 802.11n 2.4 GHz. Still rock-solid. |
| **MediaTek MT7601U** | `mt7601u` (mainline) | Works but constrained | **C** | 1×1 2.4-only; monitor/injection usable but morrownr flags monitor mode as *limited*. Budget/throwaway tier. |
| **MediaTek MT7921AU / MT7921U** | `mt7921u` (mainline, ≥5.18) | Full, tri-band | **A** | Alfa AWUS036AXML/AXM. aircrack-ng's FAQ now calls the AXML the **best-performing** card with a stable driver — WiFi 6E injection. |
| **Realtek RTL8812AU / RTL8821AU** | [aircrack-ng/rtl8812au](https://github.com/aircrack-ng/rtl8812au) (OOT DKMS) | Reliable | **B** | README badges monitor + frame injection as *working*. In-kernel `rtw88` (≥6.14) is newer/less proven — prefer the OOT driver for injection. Alfa AWUS036ACH. |
| **Realtek RTL8814AU** | `morrownr/8814au` (OOT) | Reliable | **B** | 4×4; morrownr rates it the more stable Realtek WiFi-5 option. In-kernel since ~6.16, still maturing. |
| **Realtek RTL8811AU** | aircrack-ng/rtl8812au family (OOT) | Reliable | **B** | 1×1 sibling of 8812au. |
| **Realtek RTL8821CU / RTL8811CU** | [morrownr/8821cu-20210916](https://github.com/morrownr/8821cu-20210916) (OOT) | Reliable via OOT | **B** | README explicitly lists monitor mode + packet injection + aircrack-ng compatibility. In-kernel `rtw88` monitor/injection is flaky — **use the OOT driver.** |
| **Realtek RTL8188EUS / RTL8188EU** | [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) (OOT) | Reliable via OOT | **B** | TL-WN722N **v2/v3**. In-kernel `r8188eu`/`rtl8xxxu` is monitor-limited; injection wants the OOT driver. 2.4-only. |
| **Realtek RTL8192EU / RTL8192CU** | OOT (`8192eu`) / `rtl8xxxu` | Marginal | **C/D** | Injection OOT-only and rate-quirky; in-kernel `rtl8xxxu` monitor-limited. |
| **Realtek RTL8852AU / RTL8852BE (WiFi 6/6E)** | `rtw89` (mainline) | **No reliable injection** | **D** | Monitor is experimental; injection not dependable in mainline as of 2025. Marked injection = over-claim. |
| **Intel AX200 / AX210 / AX211** | `iwlwifi` (mainline) | **Monitor only — injection fails** | **D** | Monitor works with fiddling; injected frames are silently dropped by closed Intel firmware. `aireplay-ng -9` fails. Not in aircrack-ng's recommended list. |
| **Intel Wireless-AC 9260 / 8265 / 7260** | `iwlwifi` | **Monitor only — injection fails** | **D** | Same firmware gate. Widely reported "injection is working!" *never* prints. |
| **Broadcom/Cypress FullMAC** (BCM4339, BCM4345/6/7, BCM43455, BCM4358, BCM4366, CYW43455…) | `brcmfmac` (vanilla) | **None** | **F** | FullMAC: no monitor, no injection from the host. **Nexmon** patches (see below) add monitor + injection on *specific* chips — that path is real and is where those entries earn Tier-1/2. |
| **Qualcomm ath10k FullMAC-ish** (QCA988x/9377/9887) | `ath10k` (mainline) | Partial | **C/D** | Monitor OK; injection works on some firmware builds but rate control is firmware-owned and frames get rewritten/dropped. Not dependable. |
| **Qualcomm ath11k / ath12k** (WCN685x, QCN9074) | `ath11k`/`ath12k` | Monitor partial, injection no | **D** | Newer FullMAC; monitor mode still maturing, no reliable injection. |
| **Marvell 88W8897 / 88W8997** | `mwifiex` (FullMAC) | **None** | **F** | FullMAC vendor stack; no usable monitor, no injection. Any injection flag here is wrong. |

---

## 3. The four honest buckets

### 3a. Gold-standard injectors (grade A — buy these to *inject*)

- **`ath9k` (AR9280/9285/9287, PCIe/miniPCIe)** and **`ath9k_htc` (AR9271 / AR7010, USB).** SoftMAC,
  in-tree, and — uniquely on this list — the USB firmware is **open source**
  ([qca/open-ath9k-htc-firmware](https://github.com/qca/open-ath9k-htc-firmware)): the .fw runs in
  RAM on the AR9271's Tensilica core and is what `ath9k_htc`/`athn` upload. Injection honors rate,
  retry, sequence and duration. The AR9271 is the single most-recommended USB injector in the wild,
  with the enormous caveat that it is **2.4 GHz, 1×1** and that only the **original** TP-Link
  TL-WN722N v1 uses it.
- **`mt76` family (MT7612U, MT7610U, MT7921AU).** Mainline mac80211, no blobs to install, dual/tri-band.
  MT7612U is the dual-band workhorse; MT7921AU is aircrack-ng's current *best-performing* pick per the
  [FAQ](https://www.aircrack-ng.org/doku.php?id=faq).
- **`rt2800usb` (RT3070/RT5370).** Ancient, 2.4-only, and still flawless for injection.

These deserve `monitor` + `injection` in the DB without hedging, and AR92xx/AR93xx additionally
carry `spectral-scan` (see [verification-tier3-spectral.md](./verification-tier3-spectral.md)).

### 3b. "Works with the right out-of-tree driver" (grade B — the Realtek reality)

The big Realtek USB parts **do** inject reliably — but the reliability lives in the *community DKMS
driver*, not the mainline kernel. This is the most-misfiled group in the catalog, because people see
"in-kernel `rtw88` support added in 6.x" and assume the in-kernel path injects. It frequently does not.

| Chip | Inject with this OOT driver | Do **not** rely on |
|---|---|---|
| RTL8812AU / 8821AU / 8811AU | [aircrack-ng/rtl8812au](https://github.com/aircrack-ng/rtl8812au) | in-kernel `rtw88` (monitor-limited, new) |
| RTL8814AU | `morrownr/8814au` | in-kernel (maturing) |
| RTL8821CU / 8811CU | [morrownr/8821cu-20210916](https://github.com/morrownr/8821cu-20210916) | in-kernel `rtw88` (flaky monitor/injection) |
| RTL8188EUS / 8188EU | [aircrack-ng/rtl8188eus](https://github.com/aircrack-ng/rtl8188eus) | in-kernel `r8188eu` / `rtl8xxxu` (monitor-limited) |

Note the aircrack-ng RTL8812AU README itself now carries a deprecation banner nudging users toward
lwfinger's `rtw88` — but for *injection specifically* the OOT driver remains the dependable path in
2025. Catalog entries for these chips keep their `injection` flag **only when annotated** with the
required driver; a bare "injection: yes" is misleading. See
[../chips/monitor-injection-support.md](../chips/monitor-injection-support.md) for install
recipes and DKMS pinning.

### 3c. Monitor yes, injection flaky/no (grade D — the over-claim zone)

- **Intel `iwlwifi` (AX200/AX210/9260/8265/7260…).** This is the headline correction. Intel parts
  capture beautifully in monitor mode, which is why they look like Tier-1. **They do not inject.**
  The closed firmware owns the TX MAC and silently discards host-crafted frames; `aireplay-ng -9`
  does not print `Injection is working!`. Intel appears **nowhere** in aircrack-ng's recommended-card
  list, and the FAQ's top picks are MediaTek/Atheros, never Intel. Treat any Intel `injection` flag as
  wrong.
- **Realtek `rtw89` (RTL8852AU/AE/BE, WiFi 6/6E).** Monitor is experimental and injection is not
  dependable in mainline as of 2025 — unlike the older USB parts, there is no mature OOT injection
  driver to fall back on.
- **In-kernel `rtw88` USB parts (RTL8822BU/CU, RTL8811CU) without the OOT driver.** Monitor present,
  injection unreliable. The fix is 3b, not the mainline driver.
- **`ath10k`/`ath11k`/`ath12k`.** Monitor works; injection is firmware-mediated and rate-rewritten
  when it works at all. Not Tier-1 in the honest sense.

### 3d. FullMAC without firmware RE (grade F)

- **`brcmfmac` (vanilla).** Broadcom/Cypress FullMAC chips give the host *no* monitor and *no*
  injection. The catalog's Broadcom Tier-1/2 entries are legitimate **only** through
  [Nexmon](https://github.com/seemoo-lab/nexmon), which patches the firmware to add a monitor
  interface and frame injection on specific parts (BCM43455c0 on Pi 3B+/Pi 4, BCM4339, BCM4358,
  BCM4366c0, etc. — see [../projects/nexmon.md](../projects/nexmon.md) and
  [../docs/walkthroughs/bcm43455c0-raspberry-pi.md](../docs/walkthroughs/bcm43455c0-raspberry-pi.md)).
  A Broadcom entry that claims injection **without** naming Nexmon is over-claiming: it is the
  *research artifact* that injects, not the stock chip.
- **`mwifiex` (Marvell 88W8897/8997).** FullMAC vendor stack, no usable monitor, no injection.

---

## 4. Ground-truth checklist (reproduce before trusting any Tier-1 label)

```bash
# 0. Identify the actual chip + driver (USB IDs lie; TL-WN722N v2 != v1)
lsusb ; lspci -k ; sudo airmon-ng            # driver column is the truth
ethtool -i wlan0                              # driver + firmware version

# 1. Monitor
sudo airmon-ng start wlan0
sudo tcpdump -i wlan0mon -e -c 20             # foreign BSSIDs => monitor RX real

# 2. Basic injection (the gate)
sudo aireplay-ng -9 wlan0mon                  # want: "Injection is working!"

# 3. Injection against a real AP (rate/assoc path)
sudo aireplay-ng -9 -e <SSID> -a <BSSID> wlan0mon   # watch the x/30 %, ping ms

# 4. Injection that carries state (deauth = does the TX path honor crafted frames)
sudo aireplay-ng --deauth 3 -a <BSSID> -c <CLIENT> wlan0mon
```

If step 2 fails, the chip is **grade D at best** regardless of what the datasheet or a monitor
interface suggest. If steps 2–3 pass but only via an OOT driver, record it as **grade B with the
driver named**. Only in-tree, blob-free, rate-honoring passes earn **grade A**.

---

## 5. Corrected module records

The `modules[]` payload below issues **merge corrections** (same ids) for the clearest
over-claimers surfaced by this audit — Intel `iwlwifi` parts and Marvell `mwifiex` (monitor-only or
neither, `injection` removed), and Realtek `rtw89` RTL8852AU (injection downgraded to reported-none).
Grade-A/B injectors (ath9k, mt76, rt2800usb, the OOT Realtek USB parts) are **left intact** — they
are correctly filed — and are documented here only for the verdict table, not re-emitted. Nexmon-gated
Broadcom entries are **not** downgraded, because their injection claim is real *through Nexmon*; the
fix there is annotation ("via Nexmon"), handled in [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md),
not a capability strip.

---

## References

- aircrack-ng — Injection test (`aireplay-ng -9`): <https://www.aircrack-ng.org/doku.php?id=injection_test>
- aircrack-ng — Compatibility / driver taxonomy (vendor vs. staging vs. mac80211 vs. FullMAC): <https://www.aircrack-ng.org/doku.php?id=compatibility_drivers>
- aircrack-ng — FAQ / recommended cards (AXML best performer; ath9k AR92xx/93xx): <https://www.aircrack-ng.org/doku.php?id=faq>
- morrownr — USB-WiFi chipset guidance (in-kernel vs. OOT, per-chip monitor/injection): <https://github.com/morrownr/USB-WiFi>
- aircrack-ng — RTL8812AU/8821AU OOT driver (monitor + frame injection badges; rtw88 deprecation note): <https://github.com/aircrack-ng/rtl8812au>
- morrownr — RTL8811CU/8821CU OOT driver (monitor + injection + aircrack-ng compatible): <https://github.com/morrownr/8821cu-20210916>
- aircrack-ng — RTL8188EUS OOT driver: <https://github.com/aircrack-ng/rtl8188eus>
- Qualcomm/Atheros — open ath9k_htc firmware (AR9271/AR7010, runs in RAM, ClearBSD): <https://github.com/qca/open-ath9k-htc-firmware>
- kernel.org — ath9k driver: <https://wireless.wiki.kernel.org/en/users/drivers/ath9k>
- kernel.org — iwlwifi driver: <https://wireless.wiki.kernel.org/en/users/drivers/iwlwifi>
- Nexmon (Broadcom FullMAC monitor/injection via firmware patch): <https://github.com/seemoo-lab/nexmon>
