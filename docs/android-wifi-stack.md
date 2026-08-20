# The Android Wi-Fi Stack, and Why SDR-ish Access Is Hard

*Latent Radios — Cycle 7. A map of the Android Wi-Fi software stack, and an honest account of why the SDR-ish access we exploit on Linux laptops (monitor mode, injection, CSI, spectral scan) is almost always walled off on a stock Android phone — plus the narrow paths that reopen it.*

Android phones ship some of the most interesting Wi-Fi silicon on the planet — Broadcom/Cypress `bcm4339`, `bcm4358`, `bcm43455c0`, `bcm4375`, `bcm4389`, `bcm4398`; Qualcomm WCN family; and increasingly integrated SoC modems. Many of those exact chips appear elsewhere in this catalog as tier-1 to tier-3 SDR-ish targets (see [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md), [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md)). The frustration of Android is that the silicon is capable but the software stack, the firmware licensing, and the OS security model conspire to keep it black-boxed. This page explains *why*, layer by layer, and where the doors actually are.

---

## 1. The layers, top to bottom

AOSP's own architecture doc ([source.android.com/docs/core/connect/wifi-overview](https://source.android.com/docs/core/connect/wifi-overview)) lays the stack out as a chain of processes connected by Binder IPC and, at the bottom, by kernel `nl80211`/`cfg80211`. From the app down:

| Layer | Process / component | Role | Where it runs |
|---|---|---|---|
| **App API** | `android.net.wifi.*` (`WifiManager`, `WifiRttManager`, `WifiScanner`, `WifiAwareManager`, `WifiP2pManager`) | Public SDK surface apps call | App process |
| **System service** | `WifiService`, plus `WifiP2pService`, `WifiAwareService`, `WifiRttService` inside `system_server` | Policy, state machine (`ClientModeImpl`), permission checks, config store | `system_server` (privileged) |
| **Control daemon** | **`wificond`** | Native daemon that talks to the kernel driver over **standard `nl80211` commands**; owns scanning offload, PNO, signal polling, some SoftAP control | Standalone native process |
| **Supplicant** | `wpa_supplicant` via the **Supplicant HAL** (AIDL/HIDL) | Association, EAPOL/4-way handshake, key mgmt | Standalone native process |
| **SoftAP** | `hostapd` via the **Hostapd HAL** | AP-mode beaconing / auth | Standalone native process |
| **Vendor HAL** | **Wi-Fi Vendor HAL** (`IWifi`, AIDL/HIDL, backed by vendor `.so`) | Chip bring-up, capability query, RTT, roaming, low-latency/link-layer stats, vendor commands | Vendor partition |
| **Kernel driver** | `cfg80211`/`mac80211` *or* a vendor FullMAC driver (`bcmdhd`/`dhd`, `qcacld`, `wlan`) | `nl80211` endpoint, DMA to chip | Kernel |
| **Firmware** | On-chip RTOS firmware (FullMAC) | 802.11 MAC + PHY, entirely on-chip | Wi-Fi SoC |

The three HAL interfaces AOSP names explicitly are the **Vendor HAL**, the **Supplicant HAL**, and the **Hostapd HAL**. The data path is: `App -> WifiManager -> WifiService -> {wificond, HALs} -> vendor driver -> firmware`, with Binder threading it together above the kernel boundary and netlink below it.

The single most important structural fact for us: **on phones the MAC and PHY live on-chip in FullMAC firmware**, not in `mac80211` on the host. The host driver (`bcmdhd`, `qcacld`) is a thin shuttle. Everything an SDR person wants — raw frame TX, promiscuous RX, PHY registers, spectral samples — is behind the firmware wall, not merely behind an API.

---

## 2. Why monitor mode and CSI are (almost) never available on stock Android

Four independent walls, any one of which is sufficient:

### 2.1 FullMAC firmware is locked and signed
The 802.11 MAC runs inside the chip. The host never sees the PHY. A stock firmware image simply does not expose a "monitor mode" or "dump CSI" command over the `nl80211`/vendor-command surface; those code paths either do not exist or are compiled out. There is no `iw dev wlan0 set type monitor` that the firmware will honor, because the firmware's command dispatch table has no such verb. Firmware is vendor-signed and loaded by the driver at bring-up; you cannot swap in a patched image without both the file (often on a read-only vendor partition) and, on modern SoCs, defeating image-verification. This is the same firmware-opacity problem catalogued for the desktop Broadcom parts in [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) — Android just adds partition and signing locks on top.

### 2.2 No `debugfs`, and the Linux CSI/spectral hooks are absent
On a Linux laptop, ath9k spectral scan and the Intel/Atheros CSI toolchains reach the driver through `debugfs` and custom netlink (see [../projects/csi-toolchains.md](../projects/csi-toolchains.md), [./techniques.md](./techniques.md)). Stock Android kernels mount `debugfs` restricted or not at all, the FullMAC drivers don't implement those interfaces, and unprivileged apps have no path to `/sys/kernel/debug` regardless. The `iw`/`nl80211` verbs that expose vendor knobs on desktop are gated to system UID and, above that, to SELinux.

### 2.3 SELinux + the permission model
Android runs enforcing SELinux. Even a shell with `CAP_NET_ADMIN` is confined by policy: raw sockets on `wlan0`, netlink families, and the driver's char devices sit in domains an app or `adb shell` domain can't touch. The public `android.net.wifi` API deliberately exposes no promiscuous-capture or per-subcarrier-CSI method — the surface stops at scans, RSSI, RTT, and connection control. There is no supported bytecode path from an app to raw PHY.

### 2.4 Regulatory / product hardening
Vendors ship firmware tuned for FCC/ETSI compliance and battery life, with debug/monitor features stripped for the retail SKU. Injection and arbitrary-waveform TX are exactly the capabilities a compliance team removes first.

Net: on a stock, unrooted, retail phone the practical SDR tier is **0 (black box)**. You get an association-managing appliance, not a radio you can drive.

---

## 3. What IS available on stock Android (and it's more than nothing)

The public API deliberately offers *derived measurements* rather than raw signals. For passive-sensing and ranging work these are genuinely useful, and they need no root:

### 3.1 `WifiRttManager` — 802.11mc Fine Time Measurement (FTM)
Added in **API 28 (Android 9)**. Requires the `android.hardware.wifi.rtt` feature (`FEATURE_WIFI_RTT`) and the permissions `ACCESS_FINE_LOCATION` and `CHANGE_WIFI_STATE`. `startRanging(RangingRequest, ...)` runs an asynchronous burst of round-trip-time exchanges against FTM-capable APs (or, on newer APIs, aware peers) and returns `RangingResult` objects carrying a distance estimate in millimetres, a standard deviation, and RSSI. This is time-of-flight ranging built on the IEEE **802.11mc FTM** protocol — the one genuinely SDR-adjacent primitive the OS hands you, because it exposes propagation timing rather than just link state. Depth, math, and accuracy caveats live in [./ftm-rtt-ranging.md](./ftm-rtt-ranging.md). Reference: [developer.android.com/reference/android/net/wifi/rtt/WifiRttManager](https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager).

### 3.2 `WifiScanner` and the scan/RSSI APIs
`WifiScanner` (a privileged/system API on many builds) and the public `WifiManager` scan results give you, per BSSID: RSSI, frequency/channel, capabilities, and — via `ScanResult.informationElements` on newer APIs — raw IEs including vendor-specific elements. `WifiManager.getScanResults()` and the `SCAN_RESULTS_AVAILABLE_ACTION` broadcast are the unprivileged path. Location permission is mandatory (scan results are a location signal). RSSI-over-time and IE fingerprinting are the workhorses of app-level Wi-Fi sensing.

### 3.3 Link-layer stats and RSSI polling
`WifiManager.getConnectionInfo()` (deprecated in favor of `NetworkCapabilities`/`WifiInfo` callbacks) yields the connected-link RSSI, link speed, frequency, and — on capable HALs — TX/RX rate and, through the Vendor HAL's link-layer-stats, richer counters exposed to `system_server` but generally not to apps.

### 3.4 Aware (NAN) and P2P
`WifiAwareManager` (NAN) supports neighbor discovery and, with RTT, peer-to-peer ranging; `WifiP2pManager` (Wi-Fi Direct) exposes its own discovery. Neither gives raw PHY, but both surface timing/topology signal.

**The honest boundary:** everything in this section is *processed* — a scalar RSSI, a distance estimate, a parsed IE. None of it is raw I/Q, per-subcarrier CSI, or injectable frames. You are consuming the firmware's decisions, not driving the radio.

---

## 4. The rooted / custom-firmware paths (where the wall has a door)

Root alone is not enough — the firmware still can't do monitor mode. What you need is **patched firmware**, and that is exactly what nexmon provides. Full treatment in [../projects/nexmon.md](../projects/nexmon.md); the Android-specific reality:

### 4.1 nexmon on rooted Nexus/Pixel with Broadcom
**nexmon** ([github.com/seemoo-lab/nexmon](https://github.com/seemoo-lab/nexmon)) is a C-based firmware-patching framework for Broadcom/Cypress chips. On a rooted phone it recompiles the chip's firmware with added command handlers, giving **monitor mode with radiotap headers, frame injection, and CSI extraction** — capabilities the retail firmware omits. Documented device/chip pairings include:

| Device | Chip | Capability via nexmon |
|---|---|---|
| Nexus 5 | `bcm4339` | monitor, injection, **CSI** (nexmon_csi) |
| Nexus 6 | `bcm4356` | monitor, injection |
| Nexus 6P | `bcm4358` / `bcm43582` | monitor, injection, **CSI** |
| Pixel 7 / 7 Pro | `bcm4389c1` (5/8/9) | monitor, injection (newer patch set) |
| Pixel 8 | `bcm4398d0` (5/8/9) | patch set present, capability-dependent |

**nexmon_csi** ([github.com/seemoo-lab/nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)) extracts CSI of OFDM 802.11a/(g)/n/ac frames at up to 80 MHz, per frame, delivered as UDP packets you filter with `makecsiparams` by source MAC and frame type. On phones the supported pairings are Nexus 5 (`bcm4339`, fw `6_37_34_43`, interleaved int16 I/Q) and Nexus 6P (`bcm4358`, fw `7_112_300_14_sta`, float format). The same repo also drives the Raspberry Pi `bcm43455c0` and Asus `bcm4366c0` — see [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md).

Requirements are non-trivial and honest to state:
- **Root** (Magisk on modern devices) and a **rooted/custom OS** (LineageOS historically) so the patched firmware image on the vendor/`/vendor/firmware` path can be replaced.
- **Device-specific kernel headers** and the **Android NDK** toolchain to compile the driver-side `nexutil`/loader and, where needed, an `nexmon`-aware `dhd` module.
- SELinux typically must be permissive or carry custom policy for the loader and monitor interface to work.
- Firmware-version lock-step: a patch targets one exact firmware build string; an OTA that bumps the firmware breaks it until the patch is re-based.

This yields a genuine **tier-1 (monitor + injection)** and, on the CSI pairings, **tier-2** device — the highest an Android phone reaches without replacing the radio.

### 4.2 Custom kernels and vendor drivers
Beyond nexmon, rooted paths include: building a custom kernel that mounts `debugfs` and enables driver debug knobs; loading a `bcmdhd`/`dhd` module with monitor-mode Kconfig enabled (only useful in concert with cooperating firmware); and, on a few older Qualcomm/Atheros SoftMAC-ish parts, more of the desktop `nl80211` surface. In practice Qualcomm WCN parts on Android are FullMAC (`qcacld`) and far less open than the nexmon-Broadcom lineage; there is no Qualcomm analog to nexmon with comparable phone coverage.

### 4.3 External radio instead of the internal chip
The pragmatic escape hatch: ignore the phone's radio and attach a USB SDR or a monitor-capable USB Wi-Fi dongle (Atheros `ath9k_htc`, certain Realtek) via USB-OTG, running Termux/Linux userland. You get real monitor/injection/spectral — but from added hardware, not the phone's own SoC. This is out of scope as "SDR-ish access to the phone's chip," yet it is the most reliable field answer.

---

## 5. Bottom line for the catalog

- **Stock, unrooted phone:** tier **0**. Public API = scans, RSSI, IEs, and FTM ranging. No raw PHY, no injection, no CSI. `openness: closed`.
- **The one SDR-adjacent stock primitive:** `WifiRttManager` FTM — timing, not I/Q. See [./ftm-rtt-ranging.md](./ftm-rtt-ranging.md).
- **Rooted + nexmon-patched Broadcom (Nexus 5/6P, some Pixels):** tier **1–2** — monitor, injection, and (on specific pairings) CSI. `openness: patchable`. See [../projects/nexmon.md](../projects/nexmon.md).
- **Everything higher** (spectral I/Q, arbitrary waveform) requires either firmware RE beyond current public phone patches or external hardware.

The walls — FullMAC signed firmware, no `debugfs`, enforcing SELinux, a deliberately narrow API, and regulatory hardening — are real and mostly independent. nexmon is the notable, well-documented door, and it is chip-and-firmware-specific by construction.

---

## References

- AOSP — Wi-Fi overview / architecture: <https://source.android.com/docs/core/connect/wifi-overview>
- AOSP — Wi-Fi HAL: <https://source.android.com/docs/core/connect/wifi-hal>
- AOSP — `wificond`/Wi-Fi framework: <https://source.android.com/docs/core/connect/wifi-infrastructure>
- Android developer — `WifiRttManager`: <https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager>
- Android developer — Wi-Fi RTT (location) guide: <https://developer.android.com/develop/connectivity/wifi/wifi-rtt>
- Android developer — `WifiManager`: <https://developer.android.com/reference/android/net/wifi/WifiManager>
- Android developer — `WifiScanner`: <https://developer.android.com/reference/android/net/wifi/WifiScanner>
- nexmon (firmware-patching framework): <https://github.com/seemoo-lab/nexmon>
- nexmon_csi (CSI extraction): <https://github.com/seemoo-lab/nexmon_csi>
- SELinux on Android: <https://source.android.com/docs/security/features/selinux>
- Related catalog pages: [../projects/nexmon.md](../projects/nexmon.md) · [./ftm-rtt-ranging.md](./ftm-rtt-ranging.md) · [../chips/broadcom-cypress.md](../chips/broadcom-cypress.md) · [../chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) · [../projects/csi-toolchains.md](../projects/csi-toolchains.md)
