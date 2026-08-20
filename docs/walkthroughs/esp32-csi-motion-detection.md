# ESP32 CSI Motion Detection — the "Hello World" of Wi-Fi Sensing

*Cycle 9 — new walkthrough. The gentlest possible on-ramp to Wi-Fi sensing: one
cheap ESP32 dev board, ~120 lines of Arduino, and a moving human. No SDR, no
firmware patching, no monitor mode. If you have never touched CSI before, start
here.*

Related pages: [../../chips/espressif.md](../../chips/espressif.md) ·
[../../docs/walkthroughs/wifi-csi-people-counting-occupancy.md](../../docs/walkthroughs/wifi-csi-people-counting-occupancy.md)
(the next step up)

---

## What you will build

A single ESP32 that watches the Wi-Fi channel and lights an LED (and prints
`MOTION` / `still` over serial) when a person moves nearby. No camera, no PIR
sensor, no wearable. The ESP32 measures **Channel State Information (CSI)** — the
per-subcarrier complex channel response the radio already estimates for every
packet it decodes — and flags the moment the channel starts wobbling.

This is deliberately the *simplest* thing that works. It is a binary
motion / no-motion detector built on one number per packet. It is not people
counting, not localization, not gesture recognition. Those are the next rungs;
this is rung zero. See [Limits](#limits-read-before-you-believe-it) before you
trust it for anything.

**Why the ESP32?** Unlike almost every other Wi-Fi chip in this catalog, CSI on
the ESP32 requires *no reverse engineering at all*. Espressif ships a public,
documented CSI API in ESP-IDF (`esp_wifi_set_csi_rx_cb`). That is why the ESP32
sits at the friendly end of the ladder in
[../../chips/espressif.md](../../chips/espressif.md): tier-2 CSI is a supported
vendor feature, not a hack.

---

## Why this works (in one paragraph)

Between the transmitter and your ESP32 the radio wave takes many paths at once:
one straight line plus dozens of reflections off walls, floor, furniture, and
**you**. At the receiver these copies add up with different delays and phases —
constructive here, destructive there — which is why the channel response is
different on every OFDM subcarrier. That whole interference pattern is the
"multipath." When a body moves through the room it changes the length of the
reflected paths by centimetres, and centimetres are a large fraction of a
2.4 GHz wavelength (~12.5 cm). So the subcarrier amplitudes **shift and shimmer**
whenever something moves, and sit **almost frozen** when the room is still.
Motion detection is therefore just: *measure how much the channel is shimmering,
and threshold it.* That is the entire idea.

```
   TX ──────── direct path ──────────► ESP32 (RX)
     \                                  ▲
      \___ reflection off wall ________/|
       \__ reflection off YOU ________/ |
                    ▲                    |
              you move  ──►  path length changes  ──►  CSI amplitude wobbles
```

---

## What CSI looks like on the ESP32

For every packet the ESP32 successfully receives, the CSI callback hands you a
buffer of signed bytes. Each subcarrier is **two `int8_t` values** — an imaginary
part and a real part — i.e. one complex number `H = re + j·im`. The buffer length
`len` is *bytes*, so the number of subcarriers is `len / 2`.

For a normal 20 MHz packet you get up to 64 LLTF subcarriers (`len` up to 128);
HT packets add HT-LTF subcarriers. Some of those subcarriers are always junk:
the **DC subcarrier** in the middle and the **guard subcarriers** at the band
edges carry no useful energy, and `first_word_invalid` tells you the first few
bytes may be garbage. The recipe below simply skips them.

We only need the **amplitude** per subcarrier:

```
amplitude_k = sqrt(re_k² + im_k²)
```

Amplitude is the beginner-friendly choice because it needs **no phase
calibration**. Raw CSI *phase* on the ESP32 is corrupted by carrier frequency
offset, sampling offset, and random packet-to-packet rotations; using it well
requires sanitization (see the people-counting walkthrough). Amplitude just
works. `re² + im²` is symmetric, so you do not even need to know whether the
buffer stores `[im, re]` or `[re, im]` — for amplitude it makes no difference.

---

## The metric: windowed standard deviation of amplitude

The simplest robust motion score:

1. **Per packet** → average the amplitude over a band of stable subcarriers into
   a single scalar `A`. (One number per packet. Easy to reason about.)
2. **Over a sliding window** of the last `W` packets → compute the **standard
   deviation** of `A`.
3. Still room → `A` barely changes → std is tiny. Someone moving → `A` jitters →
   std jumps. **Threshold** the std to get a boolean.

That is it. Standard deviation (or variance) of amplitude is the "hello world"
motion feature and it is what the sketch below computes. A slightly more
sensitive variant — compute the variance *per subcarrier* over the window and
then average across subcarriers — is noted at the end as your first upgrade.

Auto-calibration: for the first few seconds, assume the room is empty, record the
baseline distribution of the metric, and set the threshold a comfortable margin
above it (`mean + K·std`). This adapts to your specific room, distance, and board
without you hand-tuning a magic number.

---

## Hardware & setup

You need **one** ESP32 dev board (classic ESP32, ESP32-S2, or ESP32-S3 — a
$5 DevKitC is perfect) and a source of steady received packets. Pick one:

- **Setup A (recommended — one board + your home Wi-Fi).** The ESP32 joins your
  router as a normal station and continuously **pings the router**. Every ping
  reply is a received packet → one CSI sample. A 20 ms ping interval gives ~50
  CSI samples/second, plenty for human motion (which lives around 0.5–2 Hz).
  This is the setup the sketch below uses. Nothing but the ESP32 needs code.

- **Setup B (two boards, no router).** Flash any stock SoftAP example onto a
  second ESP32; the sensing ESP32 connects to it and pings `192.168.4.1` exactly
  as in Setup A. Useful when you have no router handy or want a clean,
  interference-controlled link.

> **Why ping at all?** CSI is only produced for packets the ESP32 *receives*.
> A connected station on an idle network hears little beyond ~10 beacons/second —
> too slow. Pinging forces a steady, reliable downlink stream (the echo replies)
> so the CSI callback fires at a predictable rate. This is the same
> traffic-generation trick Espressif's official
> [esp-csi](https://github.com/espressif/esp-csi) examples use.

**Toolchain.** Arduino IDE with the *arduino-esp32* core (v2.x or v3.x), or PlatformIO.
The sketch is Arduino, but it calls the ESP-IDF `esp_wifi_*` and `esp_ping`
functions directly — arduino-esp32 is built on ESP-IDF, so those headers are
already available. No extra libraries to install.

---

## The complete sketch (copy-paste)

```cpp
// ESP32 CSI motion detector — the "hello world" of Wi-Fi sensing.
// Arduino-ESP32 core (v2.x/v3.x). Board: any classic ESP32 / S2 / S3.
//
// It joins your Wi-Fi, pings the router to create a steady packet stream,
// measures CSI amplitude jitter, auto-calibrates to an empty room, and
// lights the LED + prints "MOTION" when the channel starts shimmering.

#include <WiFi.h>
#include "esp_wifi.h"
#include "ping/ping_sock.h"     // ESP-IDF ping session (bundled, no extra lib)

// ---------- user config ----------
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASS = "YOUR_PASSWORD";
#define LED_PIN     2            // built-in LED on many DevKitC boards
#define WIN         64           // sliding window length (packets)
#define CAL_SAMPLES 200          // ~4 s of calibration at 50 Hz
#define K_SIGMA     5.0f         // threshold = baseline_mean + K*baseline_std
// ---------------------------------

// Shared ring buffer of per-packet average amplitudes.
// Single producer (Wi-Fi task, in csi_cb) + single consumer (loop). Good enough
// for a demo; add a lock/queue if you build on this.
volatile float ampBuf[WIN];
volatile uint32_t widx = 0;
volatile uint32_t total = 0;

// ---- CSI callback: runs in the Wi-Fi task. Keep it short. ----
void csi_cb(void* ctx, wifi_csi_info_t* info) {
  if (!info || !info->buf || info->len < 16) return;
  const int8_t* d = info->buf;
  int nSub = info->len / 2;          // two int8 (im, re) per subcarrier

  // Average amplitude over a band of *stable* subcarriers.
  // Skip the first few (first_word_invalid / edge guards) and DC (~index 32).
  float sum = 0.0f; int cnt = 0;
  for (int k = 6; k < nSub - 3 && k <= 58; k++) {
    if (k >= 31 && k <= 33) continue;         // skip DC neighbourhood
    int i = 2 * k;
    float im = (float)d[i];
    float re = (float)d[i + 1];
    sum += sqrtf(re * re + im * im);
    cnt++;
  }
  if (cnt == 0) return;
  float A = sum / cnt;

  ampBuf[widx] = A;
  widx = (widx + 1) % WIN;
  total++;
}

void enable_csi() {
  // Classic-ESP32 CSI config (arduino-esp32 2.x/3.x on ESP32/S2/S3).
  // Designated initializers so field order never bites you.
  wifi_csi_config_t cfg = {};
  cfg.lltf_en          = true;
  cfg.htltf_en         = true;
  cfg.stbc_htltf2_en   = true;
  cfg.ltf_merge_en     = true;
  cfg.channel_filter_en= true;
  cfg.manu_scale       = false;
  cfg.shift            = 0;
  ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
  ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(&csi_cb, NULL));
  ESP_ERROR_CHECK(esp_wifi_set_csi(true));
}

void start_ping() {
  ip_addr_t target;
  ipaddr_aton(WiFi.gatewayIP().toString().c_str(), &target);  // ping the router
  esp_ping_config_t pc = ESP_PING_DEFAULT_CONFIG();
  pc.target_addr  = target;
  pc.count        = ESP_PING_COUNT_INFINITE;
  pc.interval_ms  = 20;      // ~50 received replies per second
  pc.timeout_ms   = 300;
  esp_ping_callbacks_t cbs = {};        // no per-ping callbacks needed
  esp_ping_handle_t h;
  ESP_ERROR_CHECK(esp_ping_new_session(&pc, &cbs, &h));
  ESP_ERROR_CHECK(esp_ping_start(h));
}

// ---- calibration + detection state ----
bool  calibrated = false;
float thresh = 0.0f;
float calAcc = 0.0f, calAccSq = 0.0f; uint32_t calN = 0;

float window_std() {
  float m = 0; for (int i = 0; i < WIN; i++) m += ampBuf[i]; m /= WIN;
  float v = 0; for (int i = 0; i < WIN; i++) { float e = ampBuf[i]-m; v += e*e; }
  return sqrtf(v / WIN);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.printf("\nconnected, ip=%s gw=%s\n",
                WiFi.localIP().toString().c_str(),
                WiFi.gatewayIP().toString().c_str());
  enable_csi();
  start_ping();
  Serial.println("hold still — calibrating empty room...");
}

void loop() {
  delay(100);                         // evaluate ~10x/second
  if (total < WIN) return;            // wait for a full window
  float s = window_std();

  if (!calibrated) {
    calAcc += s; calAccSq += s * s; calN++;
    if (calN >= CAL_SAMPLES / 10) {   // loop runs ~10 Hz, so /10 of CAL_SAMPLES
      float m  = calAcc / calN;
      float sd = sqrtf(calAccSq / calN - m * m);
      thresh = m + K_SIGMA * sd;
      calibrated = true;
      Serial.printf("calibrated. baseline_std=%.3f threshold=%.3f\n", m, thresh);
    }
    return;
  }

  bool motion = s > thresh;
  digitalWrite(LED_PIN, motion ? HIGH : LOW);
  Serial.printf("%-6s  std=%.3f  thr=%.3f\n", motion ? "MOTION" : "still", s, thresh);
}
```

**Run it.** Fill in `WIFI_SSID` / `WIFI_PASS`, flash, open the serial monitor at
115200. Stand out of the way for the ~4 s calibration line, then walk around: the
LED should light and the log should print `MOTION`. Stop, and it settles back to
`still` within a second or two.

---

## Tuning knobs (all near the top of the sketch)

| Knob | Effect |
|---|---|
| `K_SIGMA` | Higher = fewer false alarms, less sensitive. Start at 5, drop toward 3 for a jumpier detector. |
| `WIN` | Longer window = smoother, slower to react and slower to relax. 64 packets ≈ 1.3 s at 50 Hz. |
| `pc.interval_ms` | Smaller = more CSI/sec (finer time resolution) but more airtime. 20 ms ≈ 50 Hz. |
| Subcarrier band (`k = 6 … 58`) | Widen for more signal, narrow to the cleanest middle subcarriers to cut noise. |
| `CAL_SAMPLES` | Longer, quieter calibration → a more trustworthy baseline threshold. |

If it *never* triggers: confirm CSI is flowing by printing `info->len` in the
callback (you should see a steady stream). If `len` is always 0 or the callback
never fires, your ping is not producing replies — check that the ping target is
reachable and that you are actually associated.

If it triggers *constantly*: your baseline was captured while something was
moving, or the link is very noisy — raise `K_SIGMA`, lengthen `CAL_SAMPLES`, and
re-flash while the room is genuinely empty.

---

## Limits (read before you believe it)

This is a toy, and being honest about a toy's limits is the whole point of this
catalog.

- **Binary only.** It says "something moved," not *what*, *who*, *where*, or *how
  many*. A cat, a fan, a curtain in a draft, and a person all read as "motion."
- **It cannot see stillness.** A person sitting perfectly still becomes invisible
  within a couple of seconds — the channel re-settles and the std collapses back
  to baseline. This is the single biggest gotcha: **absence of motion ≠ absence
  of a person.** Presence detection is a much harder problem.
- **One link, one blurry view.** You have exactly one TX→RX path. Coverage is a
  fuzzy blob around the line between the two radios, not a room map. Motion far
  off-axis may be missed; motion right on the link line dominates.
- **Geometry-dependent thresholds.** Move the board, change the furniture, or
  change the distance to the AP and the baseline shifts — hence the
  auto-calibration. It does not transfer between rooms.
- **Needs a steady packet stream.** No traffic, no CSI. If the ping stops (AP
  drops it, board roams, network hiccups) the detector goes blind. Real
  deployments must monitor the sample rate.
- **Amplitude only.** We threw away phase, which is where finer information
  (velocity, direction, breathing) lives — precisely because raw ESP32 phase
  needs sanitizing. That is a feature for a beginner and a ceiling for anything
  serious.
- **Environmental drift & interference.** Microwave ovens, other 2.4 GHz
  devices, temperature, and slow furniture rearrangement all nudge the channel.
  A fixed threshold drifts; production systems use adaptive baselines.

For a sober, broader treatment of what Wi-Fi sensing can and cannot do, see the
honest-limitations page in this catalog. This sketch is a demo of the
*mechanism*, not a security product.

---

## Where to go next

1. **Per-subcarrier variance.** Instead of collapsing to one scalar per packet,
   keep a short history *per subcarrier*, compute each subcarrier's variance over
   the window, then average (or take the median) across subcarriers. This is more
   sensitive and more robust to the odd flaky subcarrier — your first real
   upgrade, and still a dozen lines.
2. **Log the CSI, analyze offline.** Print `mac`, `rx_ctrl.rssi`,
   `rx_ctrl.rate`, and the amplitude vector as CSV; capture a few minutes;
   plot amplitude-vs-time in Python. Seeing the shimmer with your own eyes is the
   moment CSI "clicks."
3. **From motion to counting/occupancy.** Once a single-number detector feels
   easy, step up to
   [../../docs/walkthroughs/wifi-csi-people-counting-occupancy.md](../../docs/walkthroughs/wifi-csi-people-counting-occupancy.md),
   which adds multiple subcarriers, phase sanitization, and a learned model to
   estimate *how many* people are present rather than just *whether* something
   moved.
4. **The reference implementations.** Espressif's
   [esp-csi](https://github.com/espressif/esp-csi) repo has polished
   active-AP/active-STA examples and a real-time plotting UI — the natural place
   to graduate to once this sketch makes sense.
5. **Where the ESP32 sits in the bigger picture.** See
   [../../chips/espressif.md](../../chips/espressif.md) for the full ESP32 CSI
   capability breakdown and how it compares to the RE-required CSI on Broadcom
   (Nexmon) and Atheros parts.

---

## References

- ESP-IDF Wi-Fi API reference — `esp_wifi_set_csi_config`,
  `esp_wifi_set_csi_rx_cb`, `esp_wifi_set_csi`, `wifi_csi_info_t`,
  `wifi_csi_cb_t`:
  <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html>
- ESP-IDF Wi-Fi driver guide — Channel State Information section (config fields,
  subcarrier layout, `first_word_invalid`, receive requirements):
  <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi-driver/index.html>
- Espressif `esp-csi` — official CSI examples and real-time tooling:
  <https://github.com/espressif/esp-csi>
- ESP-IDF ICMP echo (ping session) API used for traffic generation:
  <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/protocols/icmp_echo.html>
- Y. Ma, G. Zhou, S. Wang, "WiFi Sensing with Channel State Information: A
  Survey," *ACM Computing Surveys* 52(3), 2019:
  <https://dl.acm.org/doi/10.1145/3310194>

*Doc-only scope: no catalog module records are added or changed by this page.*
