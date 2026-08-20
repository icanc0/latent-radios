# 802.11mc FTM / Wi-Fi RTT: Round-Trip Time as a Ranging Primitive

Most of this catalog is about coercing a Wi-Fi chip into handing you a signal it computes
internally but never meant to export — per-subcarrier [CSI](../projects/csi-toolchains.md),
[spectral FFT bins](techniques.md), raw IQ. **Fine Timing Measurement (FTM)** is the one
distance-sensing primitive that Wi-Fi silicon exposes *on purpose*, through a standardized,
vendor-blessed API. You do not patch firmware to get it. You call `WifiRttManager.startRanging()`
or `esp_wifi_ftm_initiate_session()` and the chip hands you a **time-of-flight distance in
millimetres**.

That makes FTM the odd one out on the [SDR ladder](taxonomy.md). It is not a rung you climb by
reverse-engineering — it is a **cooperative ranging service** built into the MAC. But it belongs
in this catalog because it answers the same question CSI localization answers ("where is this
radio?") with a completely different, and often complementary, physical observable: the **round-trip
propagation time** rather than the channel's frequency response. This file covers what FTM measures,
the Android and ESP-IDF APIs that expose it, which chips and access points actually implement it,
how it stacks up against RSSI trilateration and CSI, its accuracy ceiling, and where 802.11az takes
it next.

> **Where FTM sits.** The [techniques map](techniques.md) tags "802.11mc FTM ranging" as **tier 1,
> ToF ranging** — it needs hardware FTM timestamping but *no* firmware patch and *no* monitor/raw
> access. It is honestly a narrow, closed-firmware primitive, not a general SDR. Its power is that
> it ships in phones and routers you already own.

---

## 1. What FTM actually measures

FTM (defined in **IEEE 802.11-2016**, the standard the **802.11mc** maintenance task group
produced) measures the **round-trip time (RTT)** of a frame exchange between two stations and
converts it to distance via the speed of light. The exchange is deliberately two-sided so that the
*responder's* processing delay cancels out and neither clock needs to be synchronized to the other.

### The FTM burst

An **initiator** (the station that wants to know the distance — a phone, a laptop) asks a
**responder** (typically an access point) for a ranging measurement. The responder sends an
`FTM` action frame and captures two hardware timestamps; the initiator captures two more:

```
   Initiator (STA)                         Responder (AP)
        │                                        │
        │   t1  ─────────  FTM_1  ──────────►    │  t2   (RX at responder)
        │       (TX at initiator's PHY)          │
        │                                        │
        │   t4  ◄─────────  ACK  ───────────     │  t3   (TX of ACK at responder)
        │       (RX at initiator's PHY)          │
        │                                        │
        │   next burst carries t2,t3 back to the initiator
        ▼                                        ▼

   RTT      = (t4 − t1) − (t3 − t2)
   ToF      = RTT / 2
   distance = c · ToF          (c ≈ 0.29979 m/ns)
```

The genius of the four-timestamp scheme is that `(t3 − t2)` — the time the frame spent *inside the
responder* — is subtracted out, so the responder's turnaround latency and the two devices' clock
offsets do not corrupt the result. Only the **timestamp resolution and calibration of each PHY**
matter. A single burst is noisy; the standard sends a **burst of N measurements** (typically 8–32
frame pairs) and the initiator averages them, reporting both a mean distance and a standard
deviation.

### Why timing resolution is everything

Light travels ~**0.3 metres per nanosecond**. Because RTT is halved to get one-way distance, a
**1 ns** timestamp error becomes a **~15 cm** distance error — and raw MAC timestamps are far
coarser than 1 ns. FTM's accuracy therefore comes from two things:

1. **Sub-nanosecond PHY timestamping.** The chip timestamps against the arrival of the preamble
   (the L-LTF / HE-LTF training field), not the MAC-visible frame, and interpolates within the
   sample clock.
2. **Channel bandwidth.** Time resolution is fundamentally limited by signal bandwidth
   (≈ 1 / BW). A 20 MHz channel resolves ~50 ns (15 m) per sample; **80 MHz** cuts that to ~12.5 ns
   and **160 MHz** to ~6.25 ns *before* interpolation and averaging. Wider channels are why FTM on
   802.11ac/ax/az reaches metre-level, and why 802.11az emphasises 80/160 MHz and 6 GHz.

Multipath is the enemy: in NLOS or heavy-reflection environments the first arrival is attenuated and
the estimator may lock onto a reflected path, biasing distance *long*. This is the same problem UWB
solves with 500 MHz-wide pulses (see [`qorvo-dw1000`](../chips/other-vendors.md) — UWB's ~10 cm vs
FTM's ~1 m is almost entirely a bandwidth story).

---

## 2. The Android Wi-Fi RTT API (`WifiRttManager`)

Android has shipped a public FTM API since **Android 9 (API 28)**, marketed as **Wi-Fi RTT**. It is
the most widely deployed FTM stack on earth. The app is always the **initiator**; the AP is the
**responder**.

### Core classes

| Class | Role |
|---|---|
| `WifiRttManager` | System service (`Context.WIFI_RTT_RANGING_SERVICE`). `startRanging()`, `isAvailable()`, `ACTION_WIFI_RTT_STATE_CHANGED`. |
| `RangingRequest` | Builder — `addAccessPoint(ScanResult)`, `addAccessPoints(List)`, `addWifiAwarePeer(MacAddress/PeerHandle)`. Batches up to a capped number of peers per burst. |
| `RangingResult` | Per-peer result — `getDistanceMm()`, `getDistanceStdDevMm()`, `getRssi()`, `getStatus()`, `getNumAttemptedMeasurements()`, `getNumSuccessfulMeasurements()`, `getRangingTimestampMillis()`. |
| `RangingResultCallback` | `onRangingResults(List<RangingResult>)` / `onRangingFailure(int)`. |
| `ResponderLocation` | (API 29+) civic + geospatial location an AP advertises via LCI/LCR — lat/lon/altitude straight from the AP. |

### Feature gate, permissions, discovery

```kotlin
// 1. Hardware must implement FTM
if (!packageManager.hasSystemFeature(PackageManager.FEATURE_WIFI_RTT)) return
val mgr = getSystemService(Context.WIFI_RTT_RANGING_SERVICE) as WifiRttManager
if (!mgr.isAvailable) return

// 2. Only range APs that advertise the FTM responder bit
val responders = wifiManager.scanResults.filter { it.is80211mcResponder() }
//    (Android 15+: it.is80211azNtbResponder() for 802.11az)

// 3. Range them
val req = RangingRequest.Builder().addAccessPoints(responders).build()
mgr.startRanging(req, executor, object : RangingResultCallback() {
    override fun onRangingResults(results: List<RangingResult>) {
        results.filter { it.status == RangingResult.STATUS_SUCCESS }.forEach {
            val d = it.distanceMm; val sigma = it.distanceStdDevMm  // millimetres
        }
    }
    override fun onRangingFailure(code: Int) { /* wifi off, throttled, no permission */ }
})
```

**Permissions.** `ACCESS_WIFI_STATE` + `CHANGE_WIFI_STATE`, plus the runtime-dangerous
`NEARBY_WIFI_DEVICES` (API 33+, with `neverForLocation` flag if you don't use it to locate) or
`ACCESS_FINE_LOCATION` (API ≤ 32). Wi-Fi and location scanning must be on, and the app must be in
the foreground or a foreground service — Android **throttles** background ranging aggressively to
protect battery and privacy.

**Privacy asymmetry.** Only the *initiator* learns the distance; the responding AP never learns the
phone's position. This is the opposite of RSSI-fingerprint positioning, where the infrastructure
tracks you.

**Two peer types.** Besides station-to-AP, Android supports **station-to-Wi-Fi-Aware-peer** ranging
(`addWifiAwarePeer`), i.e. phone-to-phone FTM over NAN — useful for peer ranging without any AP.

The same stack exists below the app layer in AOSP (`IWifiRttController` HAL) and in Linux
**`mac80211`** via `NL80211_CMD_PEER_MEASUREMENT` / `nl80211` peer-measurement (`iw ... measurement
ftm`), which is how `ath10k`, `ath11k` and `mt76` expose FTM on Linux.

---

## 3. FTM vs RSSI trilateration vs CSI

FTM is one of three commodity-Wi-Fi ways to answer "where is this device?" They fail differently, so
research systems increasingly fuse them.

| | **RSSI trilateration** | **FTM / Wi-Fi RTT** | **CSI localization** |
|---|---|---|---|
| Physical observable | Received power (dBm) | Round-trip **time of flight** | Per-subcarrier complex channel **H(f)** |
| Distance model | Log-distance path loss (needs calibration per env) | Direct: `c·RTT/2` | AoA/ToF via [SpotFi](techniques.md)/MUSIC across subcarriers+antennas |
| Typical accuracy | 3–10 m, unstable | **1–2 m** (LOS, ≥3 APs) | 0.3–1 m (dense AP + phase-calibrated) |
| Infra requirement | Any AP (passive) | AP must be an **FTM responder** | Patched NIC to export CSI; AP need not cooperate |
| Client requirement | Any Wi-Fi | FTM-capable chip + OS API | Patched/CSI-capable NIC ([nexmon](../projects/nexmon.md), Intel [AX-CSI](../chips/intel.md)) |
| Multipath behaviour | Corrupts power badly | Biases *long* in NLOS | Can *resolve* paths (its strength) |
| Who is exposed | Infra can track client | **Client-private** (initiator-only) | Depends on who holds the CSI |
| Standardized? | No (heuristic) | **Yes** — 802.11-2016 / 11az, public OS API | No — reverse-engineered per chip |

**Rule of thumb.** RSSI is free but coarse; FTM is a clean standardized range but needs cooperating
APs and gives you *distance only* (no angle); CSI gives the richest picture (angle + multipath
resolution) but demands a reverse-engineered NIC. FTM + CSI is a natural pairing: FTM anchors
absolute range, CSI supplies angle and sub-wavelength motion.

---

## 4. Accuracy and limits

- **Headline number.** Google and independent measurements put multilateration accuracy at
  **±1–2 m** with 3+ FTM APs; well-calibrated LOS single-link ranging reaches **~0.3–1 m**. Field
  studies (e.g. Navigine, and the Wi-Fi RTT indoor-positioning literature) report **50 % of fixes
  within ~0.3 m and 95 % within ~1 m** under good LOS geometry.
- **The calibration bias is real.** Every responder has a fixed timestamp offset (cable/PHY delay)
  that shows up as a constant distance error of **several metres** until calibrated out. The
  canonical academic verification — Ibrahim et al., *"Verification: Accuracy Evaluation of WiFi Fine
  Time Measurements on an Open Platform"* (MobiCom 2018) — showed accuracy is excellent **once a
  per-device constant offset is removed**, and poor before. Any deployment must calibrate each AP.
- **Bandwidth-bound.** 20 MHz FTM is markedly worse than 80/160 MHz; this is physics, not
  implementation.
- **NLOS is the failure mode.** Through-wall and multipath-dominated links bias long; FTM has no
  intrinsic first-path discrimination the way UWB or wideband CSI does.
- **Throttling / availability.** Android rate-limits ranging; and the practical ceiling is **AP
  penetration** — most consumer APs are *not* FTM responders, so you rarely find 3 in range outside
  an instrumented building.
- **Not a sensing radar.** FTM ranges a *cooperative* peer. It is not passive radar and does not
  image the environment; you cannot range a person who is not carrying a responding radio.

---

## 5. IEEE 802.11az — Next-Generation Positioning (NGP)

802.11az (ratified as an amendment, rolling into the 802.11 baseline) is the purpose-built
positioning standard that supersedes the 802.11mc FTM bolt-on. It keeps the RTT idea but fixes its
scaling, security and accuracy problems.

- **Two modes.** **NTB (non-trigger-based)** — lightweight, the initiator drives, exposed on Android
  15 via `is80211azNtbResponder()` and `CHARACTERISTICS_KEY_BOOLEAN_NTB_INITIATOR`. **TB
  (trigger-based)** — the AP triggers and can range **many stations at once** (MU), including
  *passive* clients that only listen, enabling scalable venue-wide location.
- **HE-LTF sounding + more spatial streams.** 11az ranges on the HE (802.11ax) preamble across up to
  160 MHz and multiple spatial streams. Android surfaces exactly these knobs on `RangingResult`:
  `get80211azInitiatorTxLtfRepetitionsCount()`, `get80211azNumberOfTxSpatialStreams()`, etc. — more
  LTF repetitions and streams average down the noise, so the API even lets you estimate confidence
  from them.
- **Secure LTF.** 11az randomizes the LTF sequence (I2R/R2I keys) so an attacker cannot spoof or
  replay an early-arriving frame to forge a shorter distance — closing the ranging-spoof attack that
  plagues open FTM. This matters for security use (keyless entry, secure proximity).
- **6 GHz-native.** 11az is designed for Wi-Fi 6E/7 and the clean, wide 6 GHz channels — more
  bandwidth and less congestion than 2.4/5 GHz means better time resolution. See
  [wifi7-and-6ghz.md](wifi7-and-6ghz.md).
- **Accuracy target.** Sub-metre (design goal ~0.1–1 m), a step beyond 11mc, and with far better
  scaling and lower airtime cost.

Android added 802.11az NTB in **API 35 (Android 15)**; the app code path is identical to 11mc — you
just also accept `is80211azNtbResponder()` APs into the same `RangingRequest`.

---

## 6. Chip & access-point support table

Roles: **I** = FTM initiator (the client that measures distance), **R** = FTM responder (the AP/peer
that answers). Statuses reflect vendor documentation and shipping-device behaviour, not lab
re-verification here.

### Client / initiator silicon (phones, laptops, MCUs)

| Chip / platform | Vendor | Role | Std | Notes |
|---|---|---|---|---|
| [AX200 / AX201](../chips/intel.md), [AX210/AX211](../chips/intel.md) | Intel | **I** (+R) | 11mc | Documented FTM on Linux (`nl80211` peer-measurement) and Windows "Wi-Fi location"; AX210 adds 6 GHz. Backbone of most laptop FTM research. |
| Wireless-AC 8260/8265, 9260/9560 | Intel | **I** | 11mc | Earlier Intel parts with FTM initiator support in firmware/driver. |
| [BE200/BE201](../chips/intel.md) | Intel | **I** (+R) | 11mc/az | Wi-Fi 7; carries 11az groundwork. |
| BCM4375 | Broadcom | **I** | 11mc | Galaxy S10/S20, Pixel 4 — early Android RTT phones. |
| BCM4389 / BCM4398 | Broadcom | **I** | 11mc/az | Pixel 6/7/8, Galaxy S22+ flagship combo chips. |
| FastConnect 6700/6900 (WCN6855/WCN7850) | Qualcomm | **I** (+R) | 11mc/az | Flagship Android SoC Wi-Fi; 11az on Wi-Fi 6E/7 parts. See [`qualcomm-wcn7850`](../chips/qualcomm-atheros.md). |
| [ESP32-S2/S3/C3/C6/C2](../chips/espressif.md) | Espressif | **I + R** | 11mc | `esp_wifi_ftm_initiate_session()`; `WIFI_EVENT_FTM_REPORT` returns `rtt_raw`, `rtt_est`, `dist_est` (cm). Cheapest way to *both* ends. |
| [ESP32 (classic)](../chips/espressif.md) | Espressif | **R only** | 11mc | Original ESP32 answers FTM as SoftAP but is not a reliable initiator. |

### Access-point / responder infrastructure

| AP / platform | Vendor | Role | Std | Notes |
|---|---|---|---|---|
| Google Wifi (2016), Nest Wifi (2019) | Google | **R** | 11mc | Reference FTM responders Android RTT was validated against. Google Wifi = Qualcomm IPQ4019. |
| Nest Wifi Pro (2022) | Google | **R** | 11mc (+az) | Wi-Fi 6E mesh; listed among RTT-capable APs. |
| `ath10k` APs (QCA9880/9888/9984) | Qualcomm/Atheros | **R** | 11mc | FTM responder support in ath10k firmware/mac80211 — the OpenWrt route to a DIY responder. See [`qualcomm-qca9984`](../chips/qualcomm-atheros.md). |
| `ath11k` / `mt76` APs | Qualcomm / MediaTek | **R** (+I) | 11mc/az | Newer Linux drivers expose FTM via `nl80211` peer-measurement. |
| Cisco Catalyst 9100 series | Cisco | **R** | 11mc | Enterprise FTM/Hyperlocation responders. |
| Aruba 500/630 series | HPE Aruba | **R** | 11mc/az | Enterprise APs advertising FTM (some 11az). |
| Compulab / instrumented OpenWrt testbeds | — | **R** | 11mc | Common academic responder rigs built on ath10k. |

> Support facts here trace to Android's developer/CTS documentation, Intel and Espressif
> documentation, and the Linux `mac80211`/`nl80211` FTM implementation. Exact firmware builds vary
> by device; the `is80211mcResponder()` / `is80211azNtbResponder()` scan bits are the ground truth at
> runtime.

---

## 7. The cheap experimenter's path: ESP32 FTM

For anyone who wants to *build* an FTM system rather than consume the Android API, the ESP32 line is
the lowest-cost full stack: a single ~$5 board can be the **responder**, another the **initiator**,
and you read raw RTT out of the event report.

```c
// Initiator side (ESP32-S3 / C3 / C6)
wifi_ftm_initiate_args_t args = { .frm_count = 32, .burst_period = 2 };  // 32 frames
esp_wifi_ftm_initiate_session(&args);
// ... in the event handler:
// WIFI_EVENT_FTM_REPORT -> ftm_report_data_t: rtt_raw (ns), rtt_est (ns), dist_est (cm)
```

Espressif ships an official `examples/wifi/ftm` demo (a CLI where one board runs `ftm -I` and
another `ap` + `ftm -s`). The **raw** `rtt_raw` needs a per-board **calibration offset** subtracted
before `dist_est` is trustworthy — the same constant-bias problem as every FTM stack. With
calibration, indoor LOS accuracy in the ~0.5–2 m range is typical; it is a superb teaching and
prototyping platform precisely because you own both endpoints and can see the raw numbers. The
ESP32 chips themselves are already catalogued (see [`../chips/espressif.md`](../chips/espressif.md)),
so no new module records are emitted for them here.

---

## 8. Research use: indoor positioning and sensing

- **Indoor positioning.** FTM's marquee application: multilaterate against 3+ responder APs for
  ±1–2 m fixes without the fingerprint survey RSSI positioning demands. Fused with pedestrian dead
  reckoning (IMU) and floor-plan constraints it drives room-level navigation. The
  [Wi-Fi sensing datasets](../projects/wifi-sensing-datasets.md) collection includes RTT traces.
- **FTM + CSI fusion.** FTM gives absolute range, CSI gives angle-of-arrival and fine motion; joint
  systems (SpotFi-style AoA anchored by FTM range) beat either alone. This is why a phone that has
  *both* an RTT API and (on rooted/patched builds) CSI is a compact localization testbed.
- **Ranging-based sensing.** Continuous FTM to a fixed peer yields a **range-over-time** series;
  breathing and coarse motion perturb the first-path length at the millimetre-to-centimetre scale,
  and research has used FTM (and especially 11az's cleaner timestamps) for proximity, occupancy and
  crowd-flow sensing. It is weaker than [CSI sensing](techniques.md) for fine vitals but needs no
  firmware patch.
- **Security / secure proximity.** 11az secure LTF makes FTM a candidate for relay-resistant
  keyless entry and device pairing — the Wi-Fi analogue of UWB secure ranging
  ([`qorvo-dw1000`](../chips/other-vendors.md)).

---

## 9. Regulatory & safety note

Unlike most of this catalog, FTM requires **no off-label transmission**: initiator and responder
exchange ordinary, association-scoped 802.11 management/action frames within the stock RF envelope.
There is no injected waveform, no elevated EIRP, no jamming — running FTM is as compliant as running
Wi-Fi. The privacy considerations are the ones to weigh: FTM can localize a *cooperating* device to
metre level, so positioning deployments that log user location fall under the same consent and
data-handling rules as any indoor-location system. FTM cannot range a device that is not actively
responding, which bounds its surveillance potential compared with passive CSI sensing.

---

## References

- Android — *Wi-Fi RTT (802.11mc / 802.11az) developer guide*: https://developer.android.com/develop/connectivity/wifi/wifi-rtt
- AOSP — *Wi-Fi RTT (source/HAL)*: https://source.android.com/docs/core/connect/wifi-rtt
- `WifiRttManager` API reference: https://developer.android.com/reference/android/net/wifi/rtt/WifiRttManager
- IEEE Std 802.11-2016 (incorporates 802.11mc / FTM): https://standards.ieee.org/ieee/802.11/5536/
- IEEE 802.11az (Next-Generation Positioning) working group: https://www.ieee802.org/11/Reports/tgaz_update.htm
- Ibrahim, Liu, Jawahar, Nguyen, Gruteser, Howard, Yu, Bai — *"Verification: Accuracy Evaluation of WiFi Fine Time Measurements on an Open Platform"*, MobiCom 2018: https://dl.acm.org/doi/10.1145/3241539.3241555
- Espressif ESP-IDF — Wi-Fi FTM API & `examples/wifi/ftm`: https://github.com/espressif/esp-idf/tree/master/examples/wifi/ftm
- Espressif ESP-IDF Wi-Fi driver guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi/index.html
- Linux `nl80211` peer-measurement / FTM (`NL80211_CMD_PEER_MEASUREMENT`): https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/uapi/linux/nl80211.h
- Wikipedia — *IEEE 802.11mc / Wi-Fi RTT*: https://en.wikipedia.org/wiki/IEEE_802.11mc

**Cross-links:** [techniques.md](techniques.md) · [chips/intel.md](../chips/intel.md) ·
[chips/espressif.md](../chips/espressif.md) · [chips/qualcomm-atheros.md](../chips/qualcomm-atheros.md) ·
[chips/other-vendors.md](../chips/other-vendors.md) (UWB comparison) ·
[wifi7-and-6ghz.md](wifi7-and-6ghz.md) · [taxonomy.md](taxonomy.md)
