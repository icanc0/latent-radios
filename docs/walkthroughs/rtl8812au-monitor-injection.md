# RTL8812AU (Alfa AWUS036ACH): monitor mode + injection, the reliable way

The Alfa AWUS036ACH is the default "does it do monitor mode and injection on
2.4 **and** 5 GHz?" dongle in most pentest kits. It is built on the Realtek
**RTL8812AU** (2x2 802.11ac, USB 3.0). This walkthrough gets you from a
freshly plugged-in adapter to a verified-injecting monitor interface on a
modern Linux box, and catalogs the failure modes that eat the most time.

Chip background and the SDR-ladder placement for this part live in
[../../chips/realtek.md](../../chips/realtek.md). This is a **Tier 1** part
(in-kernel/monitor + injection); it does not expose CSI or raw PHY through any
public firmware path, so nothing here promises more than honest 802.11
monitor/injection.

> **Scope note.** Monitor and injection here are ordinary 802.11 operations,
> not true SDR. Everything below is receive-and-frame-injection within the
> Wi-Fi PHY. For the boundary between this and real IQ capture, see
> [../true-sdr-comparison.md](../true-sdr-comparison.md).

---

## 0. Regulatory / safety note (read before any TX)

Injection is **transmission**. `aireplay-ng`, deauth, and any active test key
your radio on real spectrum.

- Only inject on networks/spectrum you are authorized to test.
- Your **regulatory domain** gates channels, power, and whether 5 GHz DFS
  channels are usable at all. Set it explicitly (Section 7); do not rely on
  the adapter's factory default (often `country 00`, the most restrictive
  world domain).
- On 5 GHz **DFS** channels (52–144 in most regions) a compliant stack must
  perform radar detection before transmitting. In monitor mode you can
  *listen* passively, but the driver/regdb will typically refuse **injection**
  on DFS channels. Do not "fix" this by forcing a permissive domain you are
  not entitled to.

---

## 1. Identify the exact chip (8812au vs 8811au vs 8812bu)

Three visually similar Alfa/clone adapters need three different drivers. Get
the USB ID first — `lsusb` is authoritative, silkscreen and marketing names
are not.

```bash
lsusb
# then, for the vendor:product string, see which chip it maps to
```

| Chip | Typical `lsusb` IDs | Radio | Common adapters | Driver to use |
|------|--------------------|-------|-----------------|---------------|
| **RTL8812AU** | `0bda:8812`, `0bda:881a/881b/881c`, vendor rebrands (`0b05:17d2` ASUS USB-AC56, `2357:0101/0103` TP-Link, `0846:9052` Netgear A6210) | 2x2 11ac, 2.4+5 GHz | **Alfa AWUS036ACH / AWUS036AC**, ASUS USB-AC56, TP-Link Archer T4U **v1** | `aircrack-ng/rtl8812au` (module `88XXau`) |
| **RTL8811AU** | `0bda:8811`, `0bda:0811`, `0bda:a811`, `0bda:c811` (Alfa AWUS036ACS) | 1x1 11ac, 2.4+5 GHz | Alfa AWUS036ACS, many nano dongles | same `88XXau` driver (8811au is in-family) |
| **RTL8812BU** | `0bda:b812`, `2357:0115` (TP-Link Archer T3U) | 2x2 11ac (different silicon) | TP-Link Archer T3U / T4U **v2/v3** | **different** driver: `morrownr/88x2bu-20210702` (module `88x2bu`) — the `88XXau` driver will **not** bind it |

The single most common mistake: a TP-Link "Archer T4U" that is actually a
**v2/v3 = RTL8812BU**, flashed against the 8812AU driver, then reported as
"broken." Check the `lsusb` ID, not the box.

> **Clone with an unknown ID.** If `lsusb` shows a Realtek-looking device
> whose ID is not in the driver's `supported-device-IDs`, the module loads but
> never claims the interface. You then either add the ID to the driver source
> and rebuild, or (aircrack-ng driver) many builds already match on the broad
> Realtek ranges. Confirm with `dmesg | grep -i 88` after plugging in.

---

## 2. Why the in-kernel driver is not enough

There are two mainline Realtek drivers people expect to "just work," and
neither gives you dependable monitor + injection on this chip:

- **`rtw88`** — the modern in-tree Realtek driver — covers RTL8821CE/8822BE/
  8822CE/8723DE-class parts. It **does not** handle RTL8812AU at all. If you
  came here because "rtw88 didn't pick up my adapter," that is expected: wrong
  family.
- **`rtl8xxxu`** — the community in-tree USB driver — gained *experimental*
  RTL8812AU/RTL8821AU support in recent kernels (roughly 5.10+). It is
  connectivity-oriented: association works on some units, but monitor mode and
  frame **injection** are not dependable, VHT/5 GHz behavior is partial, and
  it is explicitly flagged experimental. It is fine for getting online, not
  for pentest RF work.

So for reliable monitor + injection you install an **out-of-tree** driver and
stop the in-kernel one from grabbing the device (Section 6, blacklist).

### Which out-of-tree driver

- **`aircrack-ng/rtl8812au`** — this is the driver to use for monitor +
  injection. Its README states monitor mode and frame injection work, and it
  is the branch the aircrack-ng project maintains for exactly this workflow.
- **`morrownr/8812au-20210820`** — an excellent *connectivity* driver (AP mode,
  USB3 tuning, secure-boot MOK helper), but its own README now states
  **"Monitor mode is not supported"** and steers monitor-mode users toward
  MediaTek mt7612u / mt7921au adapters. Use it if you want a rock-solid client
  driver; do **not** expect it to be your injection driver.

Bottom line for a pentest dongle: **install the aircrack-ng driver.**

---

## 3. Prerequisites

```bash
# Debian/Ubuntu/Kali/Parrot
sudo apt update
sudo apt install -y build-essential dkms git bc \
    linux-headers-$(uname -r) iw aircrack-ng usbutils

# Fedora
sudo dnf install -y dkms git bc kernel-devel-$(uname -r) iw aircrack-ng
```

DKMS matters because it **rebuilds the module automatically on every kernel
update** — without it, the first `apt upgrade` that bumps your kernel silently
leaves you with no driver.

Confirm headers match your running kernel:

```bash
uname -r
ls /usr/src/linux-headers-$(uname -r) 2>/dev/null && echo "headers OK"
```

---

## 4. Install the driver (aircrack-ng/rtl8812au via DKMS)

```bash
git clone -b v5.6.4.2 https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au
sudo make dkms_install
```

`make dkms_install` registers the source under `/var/lib/dkms/rtl8812au/…`,
builds `88XXau.ko` against your current kernel, and installs it. Verify:

```bash
dkms status                 # expect: rtl8812au/5.6.4.2, <kernel>: installed
modinfo 88XXau | head       # sanity: filename, version, vermagic
```

Then re-plug the adapter (or `sudo modprobe 88XXau`) and check it bound:

```bash
sudo modprobe 88XXau
dmesg | grep -iE '88XXau|rtl8812|rtl8821' | tail
ip link       # you should see a new wlanN interface
```

**Remove / reinstall** (do this before every driver upgrade, and after a
kernel jump that broke the build):

```bash
sudo make dkms_remove          # from the source tree
# or:  sudo dkms remove rtl8812au/5.6.4.2 --all
```

### morrownr connectivity driver (alternative, not for injection)

```bash
git clone https://github.com/morrownr/8812au-20210820.git
cd 8812au-20210820
sudo ./install-driver.sh       # DKMS + optional MOK enroll, interactive
# tune options later:
sudo ./edit-options.sh         # writes /etc/modprobe.d/8812au.conf
```

Module is `8812au`, config lives at `/etc/modprobe.d/8812au.conf`. Again: use
this for a solid client, not for `aireplay-ng`.

---

## 5. Enter monitor mode

Two equivalent paths. `airmon-ng` is the batteries-included one; the manual
`iw` sequence is what it runs under the hood and is better when you want a
predictable interface name.

### Option A — airmon-ng (recommended for a quick start)

```bash
sudo airmon-ng check          # list processes that will fight you
sudo airmon-ng check kill     # stop NetworkManager/wpa_supplicant
sudo airmon-ng start wlan0    # creates wlan0mon in monitor mode
iw dev                        # confirm type monitor
```

`check kill` is not optional theater — NetworkManager will yank the interface
back to managed mode and hop channels under you if left running. Restore
networking later with `sudo systemctl start NetworkManager` (or `airmon-ng`
does not auto-restore; bring services back yourself).

### Option B — manual iw

```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
iw dev wlan0 info             # type should read "monitor"
```

Set a fixed TX power if injection range is weak (respect your regdomain
limits; value is in mBm, so 3000 = 30 dBm):

```bash
sudo iw wlan0 set txpower fixed 3000
```

---

## 6. Verify injection (the step people skip)

Monitor mode succeeding does **not** prove injection works. Test it:

```bash
# with an AP in range on the current channel:
sudo aireplay-ng --test wlan0mon
# or the numeric form:
sudo aireplay-ng -9 wlan0mon
```

A healthy result reports `Injection is working!` and a percentage of ACKs
received from nearby APs. `0%`/"no answer" usually means: wrong channel (the
card is not on the AP's channel), or the driver is the in-kernel `rtl8xxxu`
(no injection), or you are on a DFS/regulatory-blocked channel.

### Blacklist the in-kernel driver if it keeps grabbing the device

If `dmesg` shows `rtl8xxxu` claiming the adapter instead of `88XXau`:

```bash
echo 'blacklist rtl8xxxu' | sudo tee /etc/modprobe.d/blacklist-rtl8xxxu.conf
sudo update-initramfs -u        # Debian/Ubuntu/Kali
# reboot or: sudo modprobe -r rtl8xxxu && sudo modprobe 88XXau
```

---

## 7. Channel / bandwidth control (incl. 5 GHz + VHT)

Monitor-mode channel control is via `iw`, on the **monitor** interface.

```bash
# 2.4 GHz, 20 MHz
sudo iw dev wlan0mon set channel 6

# 2.4 GHz, HT40+
sudo iw dev wlan0mon set channel 6 HT40+

# 5 GHz, simple channel set
sudo iw dev wlan0mon set channel 36

# 5 GHz VHT80 by frequency: set freq <control-freq> <width> <center-freq>
# ch36 @ 80 MHz => control 5180, segment center 5210:
sudo iw dev wlan0mon set freq 5180 80 5210
```

For wide-channel captures the **center frequency** is the gotcha: `set freq`
takes the control-channel frequency, the width, and the 80/160-MHz segment
center frequency — not two edge frequencies. Get them wrong and the card sits
on the wrong slice and captures nothing.

Set your regulatory domain so the allowed channels/power are correct:

```bash
sudo iw reg set US        # your actual country code
iw reg get                # confirm; check DFS flags per channel
```

Channels shown with `(radar detection)` / `NO-IR` in `iw reg get` /
`iw list` are DFS or no-initiate: passive listen may work, injection will be
refused. That refusal is correct behavior, not a bug.

---

## 8. Common failure modes (ranked by how much time they waste)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Module builds, `modprobe` says "Key was rejected by service", no interface | **Secure Boot** rejecting the unsigned DKMS module | Enroll a MOK key and sign the module, or disable Secure Boot in firmware. morrownr's installer offers `sudo mokutil --import /var/lib/dkms/mok.pub`; on Ubuntu/Debian, `sudo mokutil --import <cert>` then set a one-time password and complete enrollment at the blue MOK screen on reboot. |
| Adapter enumerates then drops, `dmesg` shows resets/`-71`/undervolt | **USB3 power / enumeration**: 2x2 11ac on USB3 draws real current; bus-powered hubs and long cables brown out | Plug directly into a rear/mainboard USB3 port or a **powered** hub; avoid USB 3.1 **Gen 2** ports (some hosts mis-negotiate the AU chip there). |
| `dmesg` shows 2.4 GHz throughput/interference tanking near a USB3 SSD/hub | Well-known **USB3 radiated noise at 2.4 GHz** | Move the adapter onto an extension cable away from USB3 devices; use a different port. |
| Driver worked, `apt upgrade` bumped the kernel, now nothing | DKMS did not rebuild (missing headers) or the driver predates the new kernel API | `sudo apt install linux-headers-$(uname -r)`; `sudo dkms autoinstall`; if the build errors on a new kernel (6.x API churn), pull the latest driver commit / a fixup branch and reinstall. |
| Monitor mode sets, but interface flips back to managed / channel keeps changing | **NetworkManager / wpa_supplicant** still running | `sudo airmon-ng check kill` before working; re-enable services afterward. |
| `aireplay-ng --test` = 0%, monitor otherwise fine | On wrong channel, on a DFS/`NO-IR` channel, or bound by `rtl8xxxu` | Match the AP's channel (Section 7); pick a non-DFS channel to prove injection; blacklist `rtl8xxxu` (Section 6). |
| `lsusb` shows the device but no `wlanN` appears | Chip is actually **8812BU** (wrong driver), or a **clone ID** not in `supported-device-IDs` | Re-check the ID against Section 1; install the 8812BU driver or add the ID and rebuild. |
| Two identical adapters, confusing interface names | Same USB ID, non-deterministic `wlanN` ordering | Use `airmon-ng` output / `iw dev` MACs to disambiguate, or a udev rule by USB path. |

---

## 9. Quick reference (copy/paste)

```bash
# identify
lsusb

# install (monitor+injection driver)
sudo apt install -y build-essential dkms git bc linux-headers-$(uname -r) iw aircrack-ng
git clone -b v5.6.4.2 https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au && sudo make dkms_install
dkms status

# monitor
sudo airmon-ng check kill
sudo airmon-ng start wlan0

# verify injection
sudo aireplay-ng --test wlan0mon

# 5 GHz VHT80 example (ch36)
sudo iw dev wlan0mon set freq 5180 80 5210

# regulatory
sudo iw reg set US && iw reg get
```

---

## References

- aircrack-ng RTL8812AU driver (monitor + injection) — <https://github.com/aircrack-ng/rtl8812au>
- morrownr 8812au-20210820 driver (connectivity; monitor mode "not supported" per README) — <https://github.com/morrownr/8812au-20210820>
- morrownr 88x2bu-20210702 driver (for the RTL8812BU look-alikes) — <https://github.com/morrownr/88x2bu-20210702>
- aircrack-ng wiki — compatibility / injection testing — <https://www.aircrack-ng.org/doku.php?id=compatibility_drivers> and <https://www.aircrack-ng.org/doku.php?id=aireplay-ng>
- airmon-ng documentation — <https://www.aircrack-ng.org/doku.php?id=airmon-ng>
- Linux `iw` (nl80211) — <https://wireless.wiki.kernel.org/en/users/documentation/iw>
- Chip entry and tier rationale — [../../chips/realtek.md](../../chips/realtek.md)
- Where 802.11 monitor/injection stops and real SDR begins — [../true-sdr-comparison.md](../true-sdr-comparison.md)
