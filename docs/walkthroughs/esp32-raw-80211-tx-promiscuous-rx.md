# ESP32 raw 802.11 transmit & promiscuous RX (with code)

*Latent Radios — Cycle 5 walkthrough. The cheapest packet-injection-ish path on the ladder: a $5 board, a sanctioned raw-frame API, one well-known bypass, and a promiscuous sniffer with per-packet RSSI. This is a **Tier 1** capability (monitor + injection), not an SDR. See [`../../chips/espressif.md`](../../chips/espressif.md) for the silicon and [`../../docs/walkthroughs/esp32-xtensa-ghidra.md`](../../docs/walkthroughs/esp32-xtensa-ghidra.md) for tearing the closed Wi-Fi blob apart in Ghidra.*

---

## 1. What you actually get

The ESP32 (and ESP8266, ESP32-S2/S3/C3/C6) Wi-Fi MAC is a closed binary blob (`libnet80211.a`, `libpp.a`) linked against your firmware. You cannot reach the PHY: no raw IQ, no arbitrary waveform, no per-symbol timing control. But the blob exposes two public ESP-IDF entry points that, together, give you a real (if constrained) monitor-and-inject rig:

| Capability | API | Tier flag |
|---|---|---|
| Send a hand-crafted 802.11 frame | `esp_wifi_80211_tx()` | `injection` |
| Receive *every* frame on the current channel, with RSSI/rate/channel metadata | `esp_wifi_set_promiscuous()` + RX callback | `monitor` |
| (separate walkthrough) Per-subcarrier channel state | `esp_wifi_set_csi()` | `csi` → Tier 2 |

This document covers TX + promiscuous RX. CSI (Tier 2) is out of scope here — see the CSI toolchains page and the Nexmon-CSI walkthrough for the CSI story on other silicon.

**Ladder placement:** raw-frame TX + promiscuous RX = **Tier 1**. It is *not* the ath9k-class "true monitor+inject" you get from an atheros card: you cannot RX and TX simultaneously with useful timing, you cannot forge the FCS, you cannot control the modulation at IQ level, and control-frame injection is essentially off the table. It is closer to the ESP8266 `wifi_send_pkt_freedom()` era of tooling — enormously useful for deauth/beacon-flood/probe research and passive sniffing, useless for anything needing a custom PHY.

---

## 2. The sanctioned TX API: `esp_wifi_80211_tx()`

```c
esp_err_t esp_wifi_80211_tx(wifi_interface_t ifx,
                            const void *buffer,
                            int len,
                            bool en_sys_seq);
```

Straight from the ESP-IDF header doc-comment ([`esp_wifi.h`](https://github.com/espressif/esp-idf/blob/master/components/esp_wifi/include/esp_wifi.h)):

- **Supported frame types:** *"Currently only support for sending beacon / probe request / probe response / action and non-QoS data frame."* Everything else (auth, assoc, deauth, disassoc, RTS/CTS/ACK, QoS-data) is rejected by an internal sanity check — see §3.
- **Length:** *"the len must be <= 1500 Bytes and >= 24 Bytes."* 24 bytes is the minimum 802.11 MAC header; 1500 is the payload ceiling.
- **`en_sys_seq`:** if `false`, the 802.11 sequence-number field in your buffer is sent as-is; if `true`, the driver overwrites it with its own running sequence counter. *"if esp_wifi_80211_tx is called before the Wi-Fi connection has been set up, both en_sys_seq==true and en_sys_seq==false are fine. However, if the API is called after the Wi-Fi connection has been set up, en_sys_seq must be true, otherwise ESP_ERR_INVALID_ARG is returned."*
- **`ifx`:** `WIFI_IF_STA` or `WIFI_IF_AP`. The frame goes out on the **channel that interface is currently on** (`esp_wifi_set_channel()`), at the interface's configured TX rate.

### FCS: appended by hardware, not by you

The 4-byte 802.11 FCS (CRC-32) is computed and appended by the MAC hardware. **Do not put an FCS in your buffer** — your `buffer`/`len` describe the frame *up to but not including* the FCS. (Reported/consensus behavior across every raw-TX project; it also matches the `len` ceiling being the frame body rather than the on-air PSDU.) The practical consequence for a latent-SDR: you **cannot inject a frame with a deliberately-wrong FCS**, which rules out a whole class of fuzzing/robustness tests that an ath9k card handles trivially.

### What the driver silently overwrites

- **Sequence number** when `en_sys_seq == true` (mandatory once associated).
- **Duration/ID** may be recomputed by the MAC for some subtypes.
- **The transmit rate** is not in the frame — set it out-of-band with `esp_wifi_config_80211_tx_rate()` (must be called after `esp_wifi_init()` and before `esp_wifi_start()`; the header warns you *"Can not set 80211 tx rate under 11A/11AC/11AX protocol"*, i.e. legacy 11b/g/n rates only).

### Return codes to check

`ESP_OK`, `ESP_ERR_WIFI_IF` (bad interface), `ESP_ERR_INVALID_ARG` (bad len, or `en_sys_seq==false` while associated, **or a rejected frame subtype**), `ESP_ERR_WIFI_NO_MEM`.

---

## 3. The subtype filter, and the community bypass

The blob gates `esp_wifi_80211_tx()` behind a function:

```c
int ieee80211_raw_frame_sanity_check(int32_t arg, int32_t arg2, int32_t arg3);
```

It inspects the frame's type/subtype and returns non-zero (→ `ESP_ERR_INVALID_ARG`) for anything outside the beacon/probe/action/non-QoS-data whitelist. That is why a raw **deauth** (subtype 0xC0) bounces.

**The bypass** exploits the fact that this symbol is *weak* in the SDK library: define your own strong copy in application code and the linker uses yours instead. Every ESP32 "Wi-Fi attack" project does exactly this. From [`risinek/esp32-wifi-penetration-tool`](https://github.com/risinek/esp32-wifi-penetration-tool) (`components/wsl_bypasser/wsl_bypasser.c`):

```c
// This override is picked up by the linker instead of the SDK's weak symbol.
// It is never *called* by us — it just makes every frame "pass" the check.
int ieee80211_raw_frame_sanity_check(int32_t arg, int32_t arg2, int32_t arg3) {
    return 0;
}
```

With that single function present anywhere in your link, `esp_wifi_80211_tx()` will hand *any* subtype to the MAC — deauth, disassoc, auth-flood, etc. The same project's canonical broadcast-deauth template and call:

```c
static const uint8_t deauth_frame_default[] = {
    0xc0, 0x00,                         // frame control: type=mgmt, subtype=deauth
    0x3a, 0x01,                         // duration
    0xff, 0xff, 0xff, 0xff, 0xff, 0xff, // addr1 = destination (broadcast)
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // addr2 = source (fill with AP BSSID)
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // addr3 = BSSID
    0xf0, 0xff,                         // sequence/fragment
    0x02, 0x00                          // reason code 0x0002 = invalid authentication
};

ESP_ERROR_CHECK(esp_wifi_80211_tx(WIFI_IF_AP, frame_buffer, size, false));
```

> **This is where "latent radio" meets "regulated transmitter."** Injecting deauth/disassoc frames is jamming-by-protocol and is illegal against networks you do not own/operate in most jurisdictions (see [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md)). The bypass is documented here so you can *recognize* it in the wild and reproduce research on your own bench RF-isolated setup — not to attack third-party networks. Restrict any subtype experiments to a shielded box or a network you administer.

**Honest note on the bypass:** it only relaxes the *software* subtype gate. It does **not** unlock control frames with useful timing (ACK/RTS spoofing), does not give you FCS control, and the MAC still owns backoff/queueing — so you cannot, e.g., inject a perfectly-timed ACK to hijack a transaction. It is a management/data-frame forger, nothing more.

---

## 4. Promiscuous RX: sniffing with metadata

```c
esp_err_t esp_wifi_set_promiscuous(bool en);
esp_err_t esp_wifi_set_promiscuous_rx_cb(wifi_promiscuous_cb_t cb);
esp_err_t esp_wifi_set_promiscuous_filter(const wifi_promiscuous_filter_t *filter);
esp_err_t esp_wifi_set_promiscuous_ctrl_filter(const wifi_promiscuous_filter_t *filter);
```

Enable promiscuous mode, register a callback, and every frame received on the **current channel** is delivered to you. There is one radio: you sniff a single 20/40 MHz channel at a time and **hop manually** with `esp_wifi_set_channel()`.

### The callback and the packet struct

```c
void sniffer_cb(void *buf, wifi_promiscuous_pkt_type_t type);
```

`buf` is a `wifi_promiscuous_pkt_t *`. From [`esp_wifi_types_native.h`](https://github.com/espressif/esp-idf/blob/master/components/esp_wifi/include/local/esp_wifi_types_native.h):

```c
typedef struct {
    signed   rssi:8;            // RSSI of packet, unit: dBm
    unsigned rate:5;            // PHY rate (non-HT only)
    unsigned :1;                // reserved
    unsigned sig_mode:2;        // 0: 11bg, 1: 11n, 3: 11ac
    unsigned :16;               // reserved
    unsigned mcs:7;             // HT MCS index (0-76)
    unsigned cwb:1;             // channel bandwidth 0:20MHz 1:40MHz
    unsigned :16;               // reserved
    unsigned aggregation:1;     // 0: MPDU  1: AMPDU
    unsigned stbc:2;            // space-time block code
    unsigned fec_coding:1;      // LDPC flag
    unsigned sgi:1;             // short guard interval
    unsigned :8;                // reserved (noise floor on some builds)
    unsigned ampdu_cnt:8;       // aggregation count
    unsigned channel:4;         // primary channel the pkt arrived on
    unsigned secondary_channel:4; // 0:none 1:above 2:below
    unsigned :8;                // reserved
    unsigned timestamp:32;      // local RX time, microseconds
    unsigned :32;               // reserved
    unsigned :31;               // reserved
    unsigned ant:1;             // RX antenna (0 or 1)
    unsigned sig_len:12;        // length of packet INCLUDING FCS
    unsigned :12;               // reserved
    unsigned rx_state:8;        // packet state, 0 == no error
} wifi_pkt_rx_ctrl_t;

typedef struct {
    wifi_pkt_rx_ctrl_t rx_ctrl; // per-packet radiotap-like metadata
    uint8_t payload[0];         // the 802.11 frame; sig_len bytes, incl. FCS
} wifi_promiscuous_pkt_t;
```

Key gotchas:
- **`sig_len` includes the 4-byte FCS.** The actual MAC frame is `sig_len - 4` bytes; the last 4 bytes of `payload` are the FCS the hardware validated.
- **`rssi` is per-packet, signed dBm** — this is what makes the ESP32 a legitimate cheap survey/monitoring tool.
- **`channel`** in the struct is the channel *you had it parked on*; it does not free-scan.

### The type enum and the filter

```c
typedef enum {
    WIFI_PKT_MGMT,   // management frame
    WIFI_PKT_CTRL,   // control frame
    WIFI_PKT_DATA,   // data frame
    WIFI_PKT_MISC,   // other (MIMO etc.) — often truncated payload
} wifi_promiscuous_pkt_type_t;

typedef struct { uint32_t filter_mask; } wifi_promiscuous_filter_t;

#define WIFI_PROMIS_FILTER_MASK_ALL        (0xFFFFFFFF)
#define WIFI_PROMIS_FILTER_MASK_MGMT       (1)
#define WIFI_PROMIS_FILTER_MASK_CTRL       (1<<1)
#define WIFI_PROMIS_FILTER_MASK_DATA       (1<<2)
#define WIFI_PROMIS_FILTER_MASK_MISC       (1<<3)
#define WIFI_PROMIS_FILTER_MASK_DATA_MPDU  (1<<4)
#define WIFI_PROMIS_FILTER_MASK_DATA_AMPDU (1<<5)
#define WIFI_PROMIS_FILTER_MASK_FCSFAIL    (1<<6)
```

The ESP-IDF default filter passes everything except `WIFI_PKT_MISC`; the *control-frame* sub-filter (`esp_wifi_set_promiscuous_ctrl_filter`) defaults to *"filter none control packet."* Set `WIFI_PROMIS_FILTER_MASK_FCSFAIL` if you want to see corrupt frames too.

---

## 5. Minimal Arduino sketch — sniff + inject a beacon

Board: any ESP32 dev board, Arduino-ESP32 core installed. This sniffs management frames (printing RSSI + source MAC) **and** every 2 s beacons a fake SSID. It uses only the sanctioned API, so no bypass is needed (beacon is whitelisted).

```cpp
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include <string.h>

// ---- 802.11 beacon template: 24B mgmt hdr + fixed params + SSID/rate IEs ----
static uint8_t beacon[128] = {
  /* 0  */ 0x80, 0x00,                         // FC: mgmt, subtype=beacon
  /* 2  */ 0x00, 0x00,                         // duration
  /* 4  */ 0xff,0xff,0xff,0xff,0xff,0xff,      // addr1 dest = broadcast
  /* 10 */ 0xde,0xad,0xbe,0xef,0x00,0x01,      // addr2 src  = our BSSID
  /* 16 */ 0xde,0xad,0xbe,0xef,0x00,0x01,      // addr3 BSSID
  /* 22 */ 0x00, 0x00,                         // seq (driver overwrites)
  /* 24 */ 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00, // timestamp
  /* 32 */ 0x64, 0x00,                         // beacon interval (100 TU)
  /* 34 */ 0x01, 0x04,                         // cap info (ESS)
  /* 36 */ 0x00, 0x07, 'L','A','T','E','N','T','!', // SSID IE (tag 0, len 7)
  /* 45 */ 0x01, 0x04, 0x82,0x84,0x8b,0x96,    // supported rates IE
  /* 51 */ 0x03, 0x01, 0x06                    // DS param: channel 6
};                                             // total length = 54 bytes
static const int beacon_len = 54;

static void sniff_cb(void *buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  auto *p = (wifi_promiscuous_pkt_t *)buf;
  const uint8_t *f = p->payload;                 // 802.11 frame
  int rssi = p->rx_ctrl.rssi;
  Serial.printf("MGMT rssi=%d ch=%u len=%u src=%02x:%02x:%02x:%02x:%02x:%02x\n",
    rssi, p->rx_ctrl.channel, p->rx_ctrl.sig_len,
    f[10],f[11],f[12],f[13],f[14],f[15]);        // addr2
}

void setup() {
  Serial.begin(115200);
  nvs_flash_init();
  esp_event_loop_create_default();
  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  esp_wifi_init(&cfg);
  esp_wifi_set_storage(WIFI_STORAGE_RAM);
  esp_wifi_set_mode(WIFI_MODE_AP);               // need an active iface for TX
  esp_wifi_start();
  esp_wifi_set_channel(6, WIFI_SECOND_CHAN_NONE);

  wifi_promiscuous_filter_t filt = { .filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT };
  esp_wifi_set_promiscuous_filter(&filt);
  esp_wifi_set_promiscuous_rx_cb(&sniff_cb);
  esp_wifi_set_promiscuous(true);
}

void loop() {
  // beacon is a whitelisted subtype -> no sanity-check bypass required.
  esp_err_t e = esp_wifi_80211_tx(WIFI_IF_AP, beacon, beacon_len, false);
  if (e != ESP_OK) Serial.printf("tx err 0x%x\n", e);
  delay(2000);
}
```

Point a laptop's Wi-Fi scanner at it: the SSID `LATENT!` appears on channel 6, and the serial console prints RSSI for every beacon/probe the ESP32 hears. That is monitor + injection on a $5 board.

### The ESP-IDF equivalent (component `main.c`)

Same calls, but in a `void app_main(void)` with `ESP_ERROR_CHECK(...)` around each; register `sniff_cb` identically. Add the `wsl_bypasser`-style override from §3 **only** if you need non-whitelisted subtypes, and only on an isolated bench.

---

## 6. Honest limits (what keeps this at Tier 1)

- **No true simultaneous monitor+inject.** One radio, one channel; TX briefly takes the medium. You cannot reliably sniff a frame and inject a response inside a SIFS window the way ath9k/`packetspammer` can.
- **No FCS control.** Hardware always appends a correct CRC-32. Corrupt-FCS injection and FCS fuzzing are impossible.
- **No control frames with timing** even after the bypass — no ACK/RTS/CTS spoofing that depends on microsecond scheduling.
- **No arbitrary IQ / no arbitrary waveform.** The PHY only emits standard 802.11b/g/n symbols; you cannot synthesize a chirp, a non-802.11 waveform, or a custom preamble. That is the Tier 4/5 line the ESP32 never crosses.
- **Rate/channel are coarse.** Legacy rates only via `esp_wifi_config_80211_tx_rate`; 20/40 MHz channelization only.
- **Blob-gated.** All of this rides on a closed MAC library. What you *can* discover about the PHY lives in the blob — reverse it in Ghidra per [`../../docs/walkthroughs/esp32-xtensa-ghidra.md`](../../docs/walkthroughs/esp32-xtensa-ghidra.md).
- **CSI is a separate door.** For per-subcarrier channel state (Tier 2), use `esp_wifi_set_csi_config()` + `esp_wifi_set_csi_rx_cb()`, not promiscuous mode — covered in the CSI toolchains material.

**Mapping to the ladder:** `firmware.openness = closed` (public API, closed PHY); `sdr_tier = 1`; capability flags earned here = `monitor`, `injection`. It does **not** earn `raw-iq`, `arbitrary-waveform`, `spectral-scan`, or `open-firmware`. The chip can reach Tier 2 (`csi`) via a different API, documented elsewhere.

---

## 7. Verification checklist

1. Flash the §5 sketch; confirm the fake SSID is visible from a second device (proves TX path).
2. Confirm serial RSSI values track distance/orientation (proves the metadata is real, not stubbed).
3. Toggle `WIFI_PROMIS_FILTER_MASK_DATA` and confirm data frames start arriving with larger `sig_len` (proves the filter mask works).
4. Try to inject a deauth **without** the §3 override → expect `ESP_ERR_INVALID_ARG` (0x102). Add the override on an isolated bench → the error disappears. That before/after is the cleanest proof of what the sanity check gates.

---

## References

- ESP-IDF Wi-Fi API reference — `esp_wifi_80211_tx`, promiscuous APIs: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi.html>
- ESP-IDF header `esp_wifi.h` (doc-comments for the TX API, `en_sys_seq`, rate config): <https://github.com/espressif/esp-idf/blob/master/components/esp_wifi/include/esp_wifi.h>
- ESP-IDF header `esp_wifi_types_native.h` (`wifi_pkt_rx_ctrl_t`, `wifi_promiscuous_pkt_t`): <https://github.com/espressif/esp-idf/blob/master/components/esp_wifi/include/local/esp_wifi_types_native.h>
- `risinek/esp32-wifi-penetration-tool` — `wsl_bypasser` (the `ieee80211_raw_frame_sanity_check` weak-symbol override + deauth template): <https://github.com/risinek/esp32-wifi-penetration-tool>
- ESP-IDF "Wi-Fi Sniffer Mode" / promiscuous docs: <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi.html>
- Espressif silicon and firmware openness: [`../../chips/espressif.md`](../../chips/espressif.md)
- Reversing the closed Xtensa Wi-Fi blob in Ghidra: [`../../docs/walkthroughs/esp32-xtensa-ghidra.md`](../../docs/walkthroughs/esp32-xtensa-ghidra.md)
- RF safety & legality of injection/deauth: [`../../docs/rf-safety-and-legal.md`](../../docs/rf-safety-and-legal.md)
