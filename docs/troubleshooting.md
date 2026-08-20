# Troubleshooting: when it doesn't work

> The fix-it page. You bought the "right" dongle, followed a walkthrough, and
> `iw` still says `type managed`, or `nexmon_csi` spits out zeros, or DKMS
> refuses to build. This page is a **symptom → cause → fix** index for the
> failures that eat the most hours, with the exact commands to confirm each
> diagnosis. It assumes Linux; where a fault is chip-specific it points back
> into the catalog.

Nothing here is SDR-tier magic — it is the plumbing you have to get right
*before* monitor/injection ([tier 1](taxonomy.md)), CSI ([tier 2](taxonomy.md)),
or spectral scan ([tier 3](taxonomy.md)) can work at all. For which chips even
*have* the capability you are chasing, start at
[../chips/monitor-injection-support.md](../chips/monitor-injection-support.md);
for the plain-language "will my card do this" questions, see the
[FAQ](../docs/faq.md).

---

## The master symptom table

| Symptom | Most likely cause | First fix to try | Deeper section |
|---|---|---|---|
| `iw dev … set type monitor` errors `Operation not supported` | Driver has no monitor support (Intel-ish / stock brcmfmac / rtw89) | Confirm driver with `ethtool -i`; if unsupported, buy a supported chip | [§1](#1-monitor-mode-wont-enable) |
| Monitor iface flaps back to `managed`; disconnects | NetworkManager / wpa_supplicant grabbing the interface | `sudo airmon-ng check kill` (or stop NM) | [§1](#1-monitor-mode-wont-enable) |
| `airmon-ng start` says "monitor mode enabled" but sniffing gets nothing | Interface renamed (`wlan0mon`), wrong iface passed to airodump | Use the name airmon printed; `iw dev` to list | [§1](#1-monitor-mode-wont-enable) |
| `aireplay-ng --test` → `0/30` / `no answer` | No AP on that channel / channel mismatch / wrong driver | Lock the channel first; move near an AP; check driver injects | [§2](#2-injection-test-fails) |
| Injection "works" but rates/retries wrong, frames dropped | Firmware rewrites radiotap fields (iwlwifi, rtw88, ath10k stock) | Use a mac80211-honest driver (ath9k, mt76) | [§2](#2-injection-test-fails) |
| `nexmon_csi` → all-zero / NaN / garbage CSI | Firmware ↔ kernel `brcmfmac` version mismatch | Match nexmon build to your exact firmware/kernel | [§3](#3-nexmon_csi-gives-garbage--no-packets) |
| `nexmon_csi` loads but **no** UDP CSI frames arrive | `makecsiparams` filter wrong; no matching traffic; monitor iface down | Rebuild the param string; generate traffic; `ip link set up` | [§3](#3-nexmon_csi-gives-garbage--no-packets) |
| Flashing patched firmware silently reverts / won't take | RSA-signed firmware (recent brcmfmac) rejects unsigned patch | Use a supported chip/firmware combo; don't force-sign | [§3](#3-nexmon_csi-gives-garbage--no-packets) |
| `dkms build` → `Bad return status` / can't find kernel source | Kernel headers for the *running* kernel not installed | Install `linux-headers-$(uname -r)` and rebuild | [§4](#4-dkms-build-fails) |
| Module builds but won't load: `Required key not available` | Secure Boot rejecting unsigned out-of-tree module | Enroll a MOK and sign, or disable Secure Boot | [§4](#4-dkms-build-fails) |
| 5 GHz / 6 GHz channels missing from `iw list` | Regulatory domain `00` (world) or DFS lockout | Set `iw reg set <CC>`; understand DFS refuses TX | [§5](#5-5-ghz-or-6-ghz-channels-missing) |
| ESP32 CSI callback fires never / returns empty | No packets to measure CSI *on* | Send/receive traffic (ping flood, ICMP, sounding) | [§6](#6-esp32-csi-is-empty) |
| `brcmfmac` / `ath10k` / driver: `Direct firmware load … failed -2` | Firmware file missing or revision doesn't match chip stepping | Install the exact blob for your chip revision | [§7](#7-firmware-wont-load) |

The rest of the page expands each cluster with the confirming command and the
actual fix.

---

## 1. Monitor mode won't enable

### 1a. The driver simply doesn't support it

Monitor mode is a **driver** capability, not a "Wi-Fi card" one. Confirm which
driver is bound before blaming anything else:

```bash
ethtool -i wlan0            # driver= line is the truth
# or
ls -l /sys/class/net/wlan0/device/driver
```

- Stock **brcmfmac** (Broadcom in Raspberry Pi / most laptops-in-a-Mac): **no**
  monitor without the [nexmon](../projects/nexmon.md) firmware patch.
- **rtw89** (RTL8852/8832): monitor is variable, injection essentially absent
  (2025) — see [realtek](../chips/realtek.md).
- **iwlwifi** (Intel): monitor usually *works* for passive sniffing, but
  injection is limited — see [intel](../chips/intel.md).

If `iw dev wlan0 set type monitor` returns **`command failed: Operation not
supported (-95)`**, the driver has no monitor path. No config flag fixes that;
you need a supported chip. The gold-standard cards are **ath9k / ath9k_htc**
and the **mt76** family — see the
[master table](../chips/monitor-injection-support.md#master-table).

### 1b. NetworkManager / wpa_supplicant is fighting you

Classic symptom: monitor mode "turns on," then the interface drops back to
managed or keeps disconnecting a second later. A userspace daemon is re-taking
the card. The canonical fix:

```bash
sudo airmon-ng check          # list interfering processes
sudo airmon-ng check kill     # kill NetworkManager + wpa_supplicant
```

`check kill` stops (not just SIGKILLs blindly) the daemons that reassociate the
card. On a systemd box you can also do it surgically and reversibly:

```bash
sudo systemctl stop NetworkManager wpa_supplicant
# … do your work …
sudo systemctl start NetworkManager wpa_supplicant
```

Or tell NetworkManager to leave one interface alone permanently, in
`/etc/NetworkManager/conf.d/unmanaged.conf`:

```ini
[keyfile]
unmanaged-devices=interface-name:wlan1
```

then `sudo systemctl reload NetworkManager`.

### 1c. The manual (no-airmon) path

`airmon-ng` is convenient but opaque. When it misbehaves, drop to `iw`:

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
iw dev wlan0 info            # must show: type monitor
```

If that sequence works but `airmon-ng` didn't, the difference is usually that
`airmon-ng` created a **new** interface (e.g. `wlan0mon`) and you were still
pointing tools at `wlan0`. Always feed the *exact* name `iw dev` reports to
`airodump-ng` / `tcpdump`.

### 1d. Nothing captured even in monitor mode

You are locked to the wrong channel, or hopping when you meant to stare:

```bash
sudo iw dev wlan0 set channel 6           # 2.4 GHz ch 6
sudo iw dev wlan0 set channel 36 HT20     # 5 GHz needs a width hint
```

Monitor RX only sees the channel you are parked on. If `iw` refuses a 5 GHz
channel here, jump to [§5](#5-5-ghz-or-6-ghz-channels-missing) — it is a
regulatory problem, not a monitor problem.

---

## 2. Injection test fails

Injection (raw TX) is separate from monitor (raw RX); a card can do one and not
the other. The standard self-test:

```bash
sudo aireplay-ng --test wlan0mon
```

### `--test` reports `0/30` or "no answer"

Read the failure literally — the test sends probes and counts AP replies:

1. **No AP is in range on your channel.** `--test` needs a real AP to answer.
   Lock the interface to a channel where an AP actually beacons
   (`iw dev … set channel N`) or point it at one:
   `aireplay-ng --test -e <SSID> -a <BSSID> wlan0mon`. An empty channel always
   reads as "injection broken" when the radio is fine.
2. **Channel mismatch** between your monitor iface and the target AP. airodump
   hops; a locked test does not. Set the channel explicitly on **both** the
   monitor interface and the tool.
3. **Rate mismatch / DFS channel.** On 5 GHz DFS channels the driver may accept
   monitor but refuse to *transmit* until radar detection passes — injection
   fails there by design. Test on a non-DFS channel (36/40/44/48 or 149–165 in
   most regions).

### It injects, but frames are malformed / rates ignored

Some drivers accept injection then **rewrite** the radiotap-specified rate,
retry, sequence number, or duration. This is a *driver/firmware* property:

- **ath9k / ath9k_htc** and **rt2x00**, **mt76**: honest mac80211 injection,
  honour your radiotap header. Prefer these.
- **iwlwifi** (Intel), stock **ath10k**, **rtw88/rtw89**: partial — fields get
  rewritten or large/odd frames are dropped. For ath10k the
  [`ath10k-ct`](https://github.com/greearb/ath10k-ct) (Candela) firmware widens
  what injects.
- The **aircrack-ng/rtl8812au** out-of-tree driver injects well but is
  non-mainline; on the in-tree `rtw88` path the same chip injects *worse*. See
  the [RTL8812AU walkthrough](../docs/walkthroughs/rtl8812au-monitor-injection.md)
  for the exact driver choice.

### Wrong driver bound entirely

Two chips that look identical need different drivers (the TL-WN722N v1 vs v2/v3
is the classic trap — AR9271 vs RTL8188EUS). `lsusb` and `ethtool -i` are
authoritative; silkscreen and marketing names are not. Confirm the USB
vendor:product, map it to the chip in the
[Realtek](../chips/realtek.md) / [Atheros](../chips/qualcomm-atheros.md) pages,
and bind the matching driver.

---

## 3. `nexmon_csi` gives garbage / no packets

`nexmon_csi` is a **firmware patch** for specific Broadcom/Cypress chips. Most
failures are version-coupling problems, not CSI-parsing problems. Full
happy-path in the [nexmon-csi walkthrough](../docs/walkthroughs/nexmon-csi-to-usable-csi.md)
and project page [../projects/nexmon.md](../projects/nexmon.md).

### 3a. All-zero / NaN / nonsense CSI values

Almost always a **firmware ↔ kernel mismatch**. The patched firmware and the
`brcmfmac` driver in your running kernel must be the pair nexmon was built
against. When they drift, the driver still loads the firmware but the CSI IOCTL
layout no longer matches, and you get zeros or noise.

- Confirm the chip and firmware revision:

  ```bash
  dmesg | grep -i brcmfmac        # shows firmware version + chip (e.g. 43455c0)
  ```

- Build nexmon for the **exact** firmware string and kernel you are on. The
  Raspberry Pi path is chip-and-OS-version-specific — a BCM43455c0 on one
  Raspberry Pi OS release needs the nexmon branch for that release. See
  [bcm43455c0-raspberry-pi](../docs/walkthroughs/bcm43455c0-raspberry-pi.md).
- After flashing the patched `.bin`, the running driver must reload it:
  `sudo modprobe -r brcmfmac && sudo modprobe brcmfmac`, then re-check `dmesg`.

### 3b. Firmware loads but **no** CSI UDP frames arrive

nexmon_csi delivers CSI as UDP frames on the monitor interface. If you see
none:

1. **`makecsiparams` string is wrong.** The base64 param blob encodes channel,
   bandwidth, and the MAC/frame filter. A filter that matches nothing yields
   silence. Regenerate it and be explicit:

   ```bash
   # channel 36, 80 MHz, first core/stream, filter on one MAC
   mcp=$(makecsiparams -c 36/80 -C 1 -N 1 -m aa:bb:cc:dd:ee:ff)
   nexutil -Iwlan0 -s500 -b -l34 -v"$mcp"
   ```

   Channel/bandwidth in the param **must** match the channel the interface is
   actually on. Mismatch → no capture.

2. **No matching traffic exists.** CSI is measured *on received frames*. If
   nothing you're filtering for is transmitting, there is nothing to sound.
   Ping the target, or widen the filter to capture ambient beacons, then narrow.

3. **Monitor interface is down / wrong iface.** `sudo ip link set wlan0 up`,
   confirm `iw dev wlan0 info` shows `type monitor`, and sniff the right one:

   ```bash
   tcpdump -i wlan0 dst port 5500 -w csi.pcap
   ```

### 3c. Patched firmware won't take / silently reverts

Recent Broadcom firmware images are **RSA-signed**, and the driver rejects an
unsigned modified blob — the flash appears to succeed but the stock firmware
runs. There is no honest "just sign it" step for signed vendor firmware. The
fix is to use a chip/firmware generation nexmon actually supports (the well-worn
BCM4339, BCM43455c0, BCM4358, BCM4366c0 targets) rather than forcing a signed
part. See the supported-target list on [../projects/nexmon.md](../projects/nexmon.md)
and [broadcom-cypress](../chips/broadcom-cypress.md).

---

## 4. DKMS build fails

Out-of-tree drivers (aircrack-ng/rtl8812au, morrownr's 88x2bu/8821cu, etc.)
build against your kernel via DKMS. Two failure families dominate.

### 4a. Missing / mismatched kernel headers

`dkms build` needs the headers for the **running** kernel, not the newest
installed one. Symptom: `Bad return status for module build`, or a log
complaining it can't find `/lib/modules/$(uname -r)/build`.

```bash
uname -r                                   # note the exact running kernel
# Debian/Ubuntu/Kali/Raspberry Pi OS:
sudo apt install "linux-headers-$(uname -r)"
# Fedora:
sudo dnf install kernel-devel-$(uname -r)
# Arch:
sudo pacman -S linux-headers
```

If you just ran a big `apt upgrade`, you may be *running* an old kernel while
headers installed for a new one. **Reboot** so `uname -r` matches the installed
headers, then rebuild:

```bash
sudo dkms status
sudo dkms build -m rtl8812au -v <ver>
sudo dkms install -m rtl8812au -v <ver>
```

New mainline kernels also break old OOT drivers at the source level (changed
mac80211 / cfg80211 APIs). If the build errors deep in the driver's `.c` files
rather than at the headers step, you need a **newer branch** of that driver —
`git pull` the repo, or switch to the in-tree path (mt76 / rtw88) as the
[monitor-injection page](../chips/monitor-injection-support.md) recommends.

### 4b. Secure Boot rejects the unsigned module

Symptom: it *builds and installs* fine, but `modprobe` fails with **`Required
key not available`** or `Key was rejected by service`, and `dmesg` shows
`Lockdown: … unsigned module loading is restricted`.

Confirm Secure Boot state:

```bash
mokutil --sb-state          # "SecureBoot enabled" → this is your problem
```

Two fixes:

1. **Enroll a Machine Owner Key (MOK) and sign the module** — keeps Secure Boot
   on. On Debian/Ubuntu, DKMS can auto-sign if you generate and enroll a MOK:

   ```bash
   sudo mokutil --import /var/lib/dkms/mok.pub    # set a one-time password
   sudo reboot                                    # complete enrollment in MOK Manager at boot
   ```

   After enrollment, DKMS-signed modules load. (Path/keys vary by distro; some
   ship `/var/lib/shim-signed/mok/`.)
2. **Disable Secure Boot** in firmware — simplest, at the cost of the Secure
   Boot protection. Only do this on a machine where that trade-off is acceptable.

---

## 5. 5 GHz (or 6 GHz) channels missing

The card supports 5 GHz, but `iw list` shows the 5 GHz channels as
`(disabled)` or `no IR`, and you can't set them.

### 5a. Regulatory domain is unset (world / `00`)

An unconfigured stack defaults to **country `00`**, the most restrictive
*world* domain — many 5 GHz and all 6 GHz channels are locked out. Check and
set it:

```bash
iw reg get                       # shows current domain; 00 = world/unset
sudo iw reg set US               # your actual, legal country code
iw list | sed -n '/Frequencies/,/valid/p'   # re-check what's now allowed
```

For persistence, set the regulatory country in
`/etc/default/crda` (older) or via `iw reg set` in a boot unit / `wpa_supplicant`
`country=` — and make sure `wireless-regdb` and `crda`/kernel regdb are
installed, or the kernel can't apply any domain. Do **not** set a permissive
domain you are not entitled to; see [rf-safety-and-legal](../docs/rf-safety-and-legal.md)
and [regulatory-by-region](../docs/regulatory-by-region.md).

### 5b. DFS channels: listen yes, transmit no

5 GHz channels **52–144** in most regions are **DFS** (radar-shared). A
compliant driver will let you *monitor* (RX) them passively but refuses
**injection/AP TX** until it has done radar detection — which a monitor
interface does not perform. Symptom: monitor works on ch 52, injection on ch 52
fails. This is correct behaviour, not a bug. For active TX use non-DFS
channels: **36/40/44/48** (UNII-1) and **149–165** (UNII-3) in most regions.

### 5c. `no IR` flag

`iw list` marking a channel `no IR` ("no Initiating Radiation") means the
regdb forbids *starting* transmission there (you may only join an existing
network). It blocks injection and beaconing on that channel — again a
regulatory rule, handled by choosing a channel without the flag.

---

## 6. ESP32 CSI is empty

The [ESP32 CSI](../chips/espressif.md) path (`wifi_csi_info_t` callback via
`esp_wifi_set_csi`) is genuinely open — but the callback only fires **when a
packet is received**. "Empty CSI" almost always means "no packets to measure."

### Cause: nothing is triggering a measurement

CSI is a per-frame side effect. With no RX traffic between the ESP32 and its
peer, the callback never runs. Fixes:

- **Generate deterministic traffic.** In the common two-ESP32 (or
  ESP32-as-station + AP) setup, have one side send a steady stream — a ping
  flood from the AP side, or periodic frames from the sender — so each RX frame
  yields a CSI record:

  ```bash
  # from a host on the same AP, hammer the ESP32 station:
  sudo ping -f -i 0.005 <esp32-ip>
  ```

- **Confirm the callback is actually registered and enabled:**

  ```c
  esp_wifi_set_csi_rx_cb(csi_cb, NULL);
  esp_wifi_set_csi(true);
  wifi_csi_config_t c = { .lltf_en = true, .htltf_en = true,
                          .stbc_htltf2_en = true, .ltf_merge_en = true,
                          .channel_filter_en = false, .manu_scale = false };
  esp_wifi_set_csi_config(&c);
  ```

- **Association state.** In station mode the ESP32 must be *connected* (or in
  promiscuous/CSI-on-sniffed-frames mode) for frames to arrive. A device stuck
  reconnecting produces sporadic-to-zero CSI. Check the Wi-Fi event log.
- **Buffer overrun drops records.** If your callback does heavy work (printf
  over slow UART), records are dropped and the stream looks empty/gappy. Push
  raw CSI to a queue and format off the callback.

See [../projects/csi-toolchains.md](../projects/csi-toolchains.md) for the
ESP-CSI tooling and the [ML/CSI sensing](../docs/ml-csi-sensing.md) notes on
what a healthy CSI stream should look like.

---

## 7. Firmware won't load

Driver binds but the radio never comes up; `dmesg` shows a firmware error.

### 7a. `Direct firmware load … failed with error -2`

`-2` is ENOENT — the file isn't where the driver looks (`/lib/firmware/...`).
The driver names the exact path it wanted:

```bash
dmesg | grep -i firmware
# e.g. brcmfmac: Direct firmware load for brcm/brcmfmac43455-sdio.bin failed
```

Install the linux-firmware package (or drop the correct blob at that path) and
reload the module:

```bash
sudo apt install firmware-atheros firmware-realtek firmware-misc-nonfree  # Debian names vary
sudo modprobe -r brcmfmac && sudo modprobe brcmfmac
```

### 7b. Revision mismatch (right chip family, wrong stepping)

A chip has hardware **revisions/steppings** (e.g. BCM43455 `c0` vs earlier), and
each wants its matching firmware. Loading the wrong-revision blob gives
`wrong revision`, a CRC/version complaint, or a radio that loads but behaves
erratically. Read the revision the driver detected in `dmesg` and install the
blob for **that** stepping — this is exactly the coupling that also bites
[nexmon](#3-nexmon_csi-gives-garbage--no-packets). For Atheros USB, the
`ath9k_htc` firmware (`htc_9271.fw`, `htc_7010.fw`) must live in
`/lib/firmware/ath9k_htc/`; a missing/renamed blob presents identically.

### 7c. NVRAM / board file missing (embedded/SDIO parts)

SDIO Broadcom parts (Raspberry Pi, many SoMs) need a **board-specific NVRAM/txt**
alongside the firmware (`brcmfmac43455-sdio.txt`, plus a board-name variant).
Missing NVRAM → the radio loads but calibration/regulatory is wrong or it fails
to associate. Install the board file for your exact hardware; these ship in the
board vendor's firmware overlay, not always in generic `linux-firmware`.

---

## When none of this works: escalate deliberately

1. **Re-confirm the chip.** Ninety percent of "impossible" cases are the wrong
   chip assumption. `lsusb` / `lspci -nn` / `ethtool -i`, then look it up in the
   [hardware index](../chips/hardware-index.md).
2. **Check the capability actually exists.** If the
   [monitor-injection table](../chips/monitor-injection-support.md) says your
   chip is `✘` for what you want, no amount of config will conjure it —
   substitute an ath9k, mt76, or a nexmon-supported Broadcom part.
3. **Isolate driver vs. firmware vs. userspace.** `dmesg` for the first two,
   `airmon-ng check` for the third. Fix them in that order.
4. **Match versions exactly** for anything patched (nexmon, OOT DKMS drivers):
   firmware ↔ kernel ↔ driver-branch is a triple that must agree.

Related reading: [FAQ](../docs/faq.md) ·
[which-chip decision guide](../docs/which-chip-decision-guide.md) ·
[RTL8812AU monitor/injection walkthrough](../docs/walkthroughs/rtl8812au-monitor-injection.md) ·
[nexmon-csi walkthrough](../docs/walkthroughs/nexmon-csi-to-usable-csi.md) ·
[Linux wireless stack](../docs/linux-wireless-stack.md).

---

## References

- aircrack-ng suite (`airmon-ng`, `aireplay-ng`) documentation — <https://www.aircrack-ng.org/documentation.html>
- Linux `iw` / mac80211 / cfg80211 — <https://wireless.wiki.kernel.org/en/users/documentation/iw>
- wireless-regdb & regulatory domain handling — <https://wireless.wiki.kernel.org/en/developers/regulatory>
- nexmon_csi (Seemoo Lab) — <https://github.com/seemoo-lab/nexmon_csi>
- nexmon firmware patching framework — <https://github.com/seemoo-lab/nexmon>
- ESP-IDF Wi-Fi CSI API (`esp_wifi_set_csi`) — <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guide/wifi.html#wi-fi-channel-state-information>
- ESP-CSI reference toolkit — <https://github.com/espressif/esp-csi>
- DKMS — <https://github.com/dell/dkms>
- Secure Boot module signing / `mokutil` — <https://wiki.debian.org/SecureBoot>
- aircrack-ng/rtl8812au out-of-tree driver — <https://github.com/aircrack-ng/rtl8812au>
- morrownr USB Wi-Fi guidance & drivers — <https://github.com/morrownr/USB-WiFi>
- ath10k-ct (Candela) firmware/driver — <https://github.com/greearb/ath10k-ct>
