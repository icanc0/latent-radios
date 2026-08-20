# Wardriving & Wi-Fi Survey with Kismet

> **What this walkthrough is.** Kismet turns a single monitor-capable Wi-Fi
> adapter (plus an optional GPS) into a **passive** wireless survey rig: it
> listens, catalogs every access point and client it hears, tags each sighting
> with a location, and hands you a database you can turn into a coverage map, a
> [WiGLE](https://wigle.net/) upload, or a rogue-AP report. Nothing here
> transmits. Nothing here attacks. This is *reconnaissance of the RF you can
> already hear*, done responsibly.
>
> Kismet is not an SDR and this is not a firmware-RE exercise — it is a
> **Tier 1** activity (ordinary 802.11 monitor mode; see
> [../taxonomy.md](../taxonomy.md)). The value is in the survey workflow, the
> geolocation, and what a census of your own airspace teaches you about
> defense. For the adapter that feeds it, cross-reference
> [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md);
> for what an adversary running the same tool can and cannot infer, and how a
> defender responds, read [../defensive-detection-and-privacy.md](../defensive-detection-and-privacy.md).

---

## 0. Ethics and legality — read this before you plug anything in

Wardriving sits on a legal and ethical line, and the line is drawn by two facts
that this walkthrough never crosses:

1. **Kismet in this configuration is receive-only.** It puts the adapter in
   monitor mode and listens. It does **not** deauthenticate clients, does not
   run KARMA/evil-twin, does not probe, does not associate. Observing
   already-radiated RF is broadly comparable to noticing a shop's sign from the
   public sidewalk. **The moment you inject a frame — deauth, disassoc,
   spoofed beacon — you have left "survey" and entered "attack," which is
   illegal on networks you do not own or are not authorized to test.** Do not
   do it. This document deliberately configures no TX.

2. **Payloads are private even when headers are not.** Beacons, probe
   requests, and 802.11 headers are broadcast in the clear by design; that is
   why a passive listener sees SSIDs, BSSIDs, and client MACs. The *contents*
   of associated, encrypted traffic are not yours to collect, crack, or store.
   Capturing WPA handshakes to crack a network you do not control is an attack,
   full stop.

Practical ground rules:

- **Survey your own environment.** Your home, your lab, your employer's estate
  *with written authorization*. A drive through a public area collecting the
  AP census that every AP is already shouting is the classic "wardriving" case
  and is legal in most jurisdictions — but **local law governs, and it varies.**
  Some places restrict interception of communications broadly enough to matter.
  Check [../regulatory-by-region.md](../regulatory-by-region.md) and
  [../rf-safety-and-legal.md](../rf-safety-and-legal.md) for your region before
  you collect, and especially before you *publish*.
- **Client MAC addresses are personal data.** A device MAC (when not
  randomized) is a persistent identifier tied to a person. Treat your Kismet
  database like the PII store it is: minimize retention, do not correlate
  individuals, and do not publish per-client tracks. WiGLE's model is an AP
  census (BSSID + location), not a people-tracking database — keep to that
  spirit. See the privacy discussion in
  [../defensive-detection-and-privacy.md](../defensive-detection-and-privacy.md).
- **Do not deauth to "reveal hidden SSIDs" faster.** A hidden SSID leaks
  naturally when a legitimate client associates (Kismet fills it in
  passively). Forcing it with a deauth is an attack. Wait, or don't learn it.

If you cannot honor all of the above for a given network, it is not yours to
survey.

---

## 1. What Kismet is

Per the project's own description, Kismet is *"an open source sniffer, WIDS,
wardriver, and packet capture tool for Wi-Fi, Bluetooth, BTLE, wireless
thermometers, airplanes, power meters, Zigbee, and more."* Two architectural
points make it the right tool for surveying:

- **It is passive and multi-protocol.** With the right *datasource* it does not
  only see 802.11. Add an Ubertooth or a Sniffle dongle for Bluetooth/BLE, a
  TI CC2531 / nRF52840 for Zigbee, or an RTL-SDR for `rtl_433` sensors and ADS-B
  — Kismet fuses them into one device tree, one map, one log. This walkthrough
  centers on Wi-Fi because that is the monitor-mode path this catalog covers,
  but the survey model is identical for the other radios.
- **Server + web UI, with remote capture.** Kismet runs as a headless server
  that owns the datasources and the log; you point a browser at its web UI. The
  capture side can be split off onto a small remote box (`kismet_cap_linux_wifi`
  streaming to a central server), which is how people build distributed sensor
  fences.

It runs on Linux, macOS, and Windows via WSL. This guide is Linux, because that
is where monitor mode is well-supported.

---

## 2. Pick and prepare a capture adapter

Kismet is only as good as the radio feeding it. You want an adapter that does
**solid monitor mode** across the bands you care about. Injection is *not*
needed for surveying (and we are not using it), so the bar is lower than a
pentest injector — but the same well-supported chips are the safe picks. Full
matrix in
[../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md);
the short list for a survey rig:

| Adapter | Chip | Bands | Driver | Why for surveying |
|---|---|---|---|---|
| Alfa AWUS036ACM / many | **MediaTek MT7612U** | 2.4 + 5 GHz | `mt76x2u` (in-tree) | Best-value 5 GHz monitor over USB; clean mac80211. |
| Alfa AWUS036AXML and kin | **MediaTek MT7921AU** | 2.4/5/6 GHz | `mt7921u` (in-tree) | Modern Wi-Fi 6/6E monitor incl. 6 GHz; no out-of-tree driver. |
| Alfa AWUS036NHA, TL-WN722N **v1** | **Atheros AR9271** | 2.4 GHz only | `ath9k_htc` (in-tree) | Rock-solid classic; 2.4 GHz only, but flawless monitor. |
| PCIe/mini-PCIe reference | **Atheros AR928x** | 2.4 + 5 GHz | `ath9k` (in-tree) | The gold-standard mac80211 monitor radio if you can use PCIe. |
| Alfa AWUS036ACH | **Realtek RTL8812AU** | 2.4 + 5 GHz | out-of-tree `88XXau` | Ubiquitous; needs a DKMS driver — see [rtl8812au-monitor-injection.md](rtl8812au-monitor-injection.md). |

**Prefer an in-tree driver** (`mt76`, `ath9k`, `ath9k_htc`) for a survey rig:
fewer moving parts on a machine you may run headless in a car. Get the exact
chip right by USB ID, not by the label on the box — that failure mode and the
DKMS build for Realtek parts are covered in
[rtl8812au-monitor-injection.md](rtl8812au-monitor-injection.md).

**You do not need to manually set monitor mode.** Modern Kismet takes a
*managed* interface name and creates its own monitor VIF (e.g. `wlan1mon`),
setting the type itself. Handing it an interface you already flipped to monitor
is a common source of confusion — give Kismet the normal `wlan1`.

```bash
# Identify the adapter and confirm the driver bound
lsusb
iw dev                 # note the interface name, e.g. wlan1
ethtool -i wlan1 2>/dev/null | grep driver   # confirm mt76x2u / ath9k_htc / etc.

# Set your regulatory domain so Kismet knows which channels are legal to *listen* on
sudo iw reg set US     # use YOUR country code
```

> **Regulatory note (RX side).** Your regdomain governs which channels the
> stack will tune. This matters for *hearing* 5 GHz DFS channels and the 6 GHz
> band at all. Setting the domain correctly is about legality of tuning, not
> transmission — we transmit nothing here. Details:
> [../regulatory-by-region.md](../regulatory-by-region.md).

---

## 3. Install and first run

Use the project's own repository where possible (distro packages lag). On
Debian/Ubuntu/Raspberry Pi OS:

```bash
# Kismet's official APT repo (see kismetwireless.net/download for the current release codename block)
sudo apt install kismet
```

The installer offers to create a **`kismet` group** — add yourself so you can
run capture without full root:

```bash
sudo usermod -aG kismet "$USER"
# log out/in for the group to take effect
```

Launch the server, pointing it at your adapter:

```bash
kismet -c wlan1
```

Then open the **web UI at `http://localhost:2501`** (2501 is Kismet's default
port). On first launch it forces you to **create an admin login** — that
username/password is written to `~/.kismet/kismet_httpd.conf`
(`httpd_username=` / `httpd_password=`). The server binds `localhost` by
default; if you expose it on a network, put it behind TLS/a tunnel and never
ship the default with no password.

### Configuration files

Kismet reads a stack of configs from `/etc/kismet/`:

| File | Purpose |
|---|---|
| `kismet.conf` | Master config that includes the others. **Do not edit.** |
| `kismet_httpd.conf` | Web server (port, login). |
| `kismet_logging.conf` | Log types, paths, titles. |
| `kismet_alerts.conf` | WIDS alert definitions/thresholds. |
| **`kismet_site.conf`** | **Your override file — put all your customizations here.** |

Everything below that you want to persist (sources, GPS, log settings) goes in
`/etc/kismet/kismet_site.conf`. It overrides the shipped defaults and survives
package upgrades. A minimal survey `kismet_site.conf`:

```ini
# /etc/kismet/kismet_site.conf
source=wlan1:name=survey0
gps=gpsd:host=localhost,port=2947
# keep the sqlite log; drop full-packet pcap to save space on long drives
kis_log_title=survey
```

---

## 4. Datasources — the capture source

A **datasource** is a capture interface. Define it on the command line with
`-c`, or persistently with a `source=` line. The Linux Wi-Fi source syntax
(from the Kismet datasource docs):

```bash
kismet -c wlan1                       # simplest form
```

```ini
# In kismet_site.conf — interface:option,option,...
source=wlan1:name=survey0
source=wlan0:name=fixed6,channel_hop=false,channel=6      # lock to one channel
source=wlan1:name=Card,channels="1,6,11,36HT40+,149VHT80" # explicit channel set
source=wlan1:name=Wifi6e,channel_hop=false,channel=1W6e   # a 6 GHz channel
```

Useful Wi-Fi source options (per the docs):

| Option | Effect |
|---|---|
| `name=` | Friendly name shown in the UI and logs. |
| `channel=` | Lock to one channel (disables hopping for this source). |
| `channels="..."` | Explicit comma-separated channel list (quoted). |
| `add_channels="..."` | Append non-standard channels to the auto list. |
| `channel_hop=true/false` | Enable/disable hopping. |
| `channel_hoprate=` | Hop speed (channels/sec). |
| `ht_channels=` / `vht_channels=` | Include/exclude 40 / 80–160 MHz widths. |
| `band24ghz=` / `band5ghz=` / `band6ghz=` | Restrict to specific bands. |

### Channel hopping vs. dwell — the core survey tradeoff

A single radio can only sit on one channel at a time. Kismet **hops** across
channels so it eventually hears every AP, but any given AP is only "seen" during
the moments its channel is tuned in.

- **Faster hop** = broader census, but you miss beacons and under-count clients
  on each channel (you may never catch a device's brief probe).
- **Slower hop / dwell** = deeper picture per channel, fewer channels covered
  per unit time — bad on a moving survey.
- **Two adapters** = the real answer for a serious rig: e.g. one MT7921AU
  dwelling on the 2.4 GHz DSSS set and one on 5/6 GHz, each its own `source=`.
  Kismet fuses them.

For a driving survey, moderate hopping across the common channels (1/6/11 plus
the popular 5 GHz UNII channels) beats trying to dwell — you are trading depth
for the geographic spread the GPS is giving you anyway.

---

## 5. GPS tagging

Location is what turns a device list into a survey. Kismet supports GPS types
**gpsd, serial (NMEA), tcp, and virtual (fixed)**. The overwhelmingly common
setup is a USB GPS puck driven by `gpsd`:

```bash
sudo apt install gpsd gpsd-clients
# point gpsd at the puck (adjust device); test with cgps or gpsmon
sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock
cgps -s     # confirm a fix before you rely on it
```

```ini
# kismet_site.conf
gps=gpsd:host=localhost,port=2947
```

Direct NMEA serial, no gpsd:

```ini
gps=serial:device=/dev/ttyACM0,name=puck
```

Fixed location for a **stationary** WIDS sensor (so its devices still map to a
point without a live fix):

```ini
gps=virtual:lat=37.7749,lon=-122.4194,alt=15
```

Kismet also accepts a **web/mobile GPS** feed from a phone browser hitting the
UI — handy for a walk-around survey with no puck. Whatever the source, **confirm
a real fix before you trust the tracks**; a `gpsd` with no satellites will tag
everything at 0,0 and quietly ruin a KML.

---

## 6. The web UI — what you actually watch

At `http://localhost:2501` the UI is a live device table plus panels:

- **Devices list** — every AP and client, with BSSID/MAC, manufacturer (OUI
  lookup), type (AP / client / bridge / ad-hoc), encryption (Open / WEP /
  WPA1/2/3), channel, signal (dBm), first/last seen, packet counts. Sort and
  filter here — this *is* your AP census.
- **SSID column** — for hidden networks the SSID is blank until a client
  association leaks it, at which point Kismet backfills it **passively**. That
  is the only sanctioned way to learn a cloaked SSID here.
- **Channels view** — occupancy/utilization per channel: your live picture of
  who is crowding 2.4 GHz and how the 5/6 GHz UNII channels are being used.
- **Signal / RRD graphs** — per-device signal over time; on foot this is a
  crude but effective direction-finder (walk toward rising dBm).
- **Alerts** — Kismet's WIDS surfaces anomalies (see §8).
- **GPS/map status** — current fix and, with location, device positions.

Everything visible in the UI is also in the REST API and the log, so you never
need to babysit the browser during a drive.

---

## 7. Logging and exports

Kismet's primary log is a **`.kismet` file — a SQLite (kismetdb) database** —
holding devices, sightings, GPS tracks, alerts, and (optionally) packets. It
can also write `pcapng` and per-datasource pcap. Control it in
`kismet_logging.conf` / `kismet_site.conf`; logs land in the working directory
named by timestamp and `kis_log_title`.

The kismetdb is the archival truth. Convert it with the bundled `kismetdb_*`
tools:

```bash
# → WiGLE CSV for upload to wigle.net (AP census: BSSID, SSID, crypto, GPS)
kismetdb_to_wiglecsv --in survey-20260820.kismet --out survey.wiglecsv

# → KML track + device points for Google Earth / any GIS
kismetdb_to_kml --in survey-20260820.kismet --out survey.kml

# → device inventory as JSON (scripting, diffing an estate over time)
kismetdb_dump_devices --in survey-20260820.kismet --out devices.json

# → pcapng of captured frames (only if you logged packets, and see the ethics note)
kismetdb_to_pcap --in survey-20260820.kismet --out survey.pcapng
```

### Uploading to WiGLE — responsibly

[WiGLE](https://wigle.net/) is a crowd-sourced database of AP observations
(BSSID + location + metadata). The `.wiglecsv` from above is its native import.
Before you upload:

- WiGLE is an **AP census**, not a people tracker. It is fine to contribute the
  fact that BSSID `xx` was heard near a coordinate — that is what every AP
  broadcasts. Do **not** treat client-MAC tracks as contributable data.
- Respect the choice of anyone who has opted their SSID out of WiGLE (the
  `_nomap` / `_optout` SSID suffix convention) and honor local law on what you
  may publish.
- Strip anything you would not want tied back to a person. The census is the
  point; the surveillance is not.

For a long survey, log the kismetdb and *drop full-packet pcap* (set the log
types to skip `pcapng`) — you get the full device/GPS census at a fraction of
the size and without hoarding others' encrypted payloads.

---

## 8. What a survey teaches you — and the defensive payoff

A passive census of your own airspace answers real questions, and almost every
answer feeds defense (tie-in to
[../defensive-detection-and-privacy.md](../defensive-detection-and-privacy.md)):

- **AP inventory / shadow IT.** Every SSID, BSSID, band, and crypto suite in
  range. Running this across a site you own surfaces **APs nobody
  authorized** — a personal travel router under a desk, a misconfigured
  printer's ad-hoc network, a vendor appliance beaconing an open SSID.
- **Encryption posture.** A one-glance count of Open / WEP / WPA1 / WPA2 / WPA3
  networks. WEP or WPA1 still present on your estate is a finding, not trivia.
- **Rogue / evil-twin detection.** Two BSSIDs advertising *your* corporate SSID,
  or your SSID on a MAC/OUI that is not your AP vendor, is the classic rogue
  signature. Kismet's **`APSPOOF`** alert exists exactly for "this SSID is
  coming from a BSSID it shouldn't." Baseline your legitimate BSSIDs, then let a
  stationary Kismet sensor watch for imposters.
- **Channel planning.** The Channels view shows real-world congestion — why
  drop a device onto channel 6 in a building where 6 is saturated when 5/6 GHz
  is empty?
- **Hidden-SSID reality check.** Cloaking is not security; Kismet backfills the
  name the moment a client associates. Seeing your "hidden" network resolve in a
  passive survey is a useful reminder to your own team.
- **Client-side exposure.** Devices leak **probe requests** naming previously
  joined SSIDs. A survey shows how much your fleet is broadcasting about where
  it has been — the argument for MAC randomization and for disabling
  auto-probe of saved networks. (This is also exactly the leak an attacker
  harvests; see [../defensive-detection-and-privacy.md](../defensive-detection-and-privacy.md).)

**WIDS mode.** Point a fixed Kismet sensor (with a `virtual` GPS location) at
your site and leave it. Its alert engine (`kismet_alerts.conf`) flags
`DEAUTHFLOOD`, `BCASTDISCON`, `DISASSOCTRAFFIC`, `APSPOOF`, `CHANCHANGE`,
`AIRJACKSSID`, and more — the on-air fingerprints of the very attacks §0
forbids you from launching. The survey rig and the defensive sensor are the
same hardware and the same tool, differing only in intent and dwell.

---

## 9. Reproducible minimal survey — end to end

```bash
# 1. Adapter present, driver bound, regdomain set
iw dev; ethtool -i wlan1 | grep driver
sudo iw reg set US            # your country

# 2. GPS up and holding a fix
sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock
cgps -s                        # wait for 3D fix, then Ctrl-C

# 3. Persist the config (once) — /etc/kismet/kismet_site.conf:
#    source=wlan1:name=survey0
#    gps=gpsd:host=localhost,port=2947
#    kis_log_title=survey

# 4. Run the server (Kismet makes its own monitor VIF from wlan1)
kismet                          # sources+gps come from kismet_site.conf
# or ad hoc without editing config:
# kismet -c wlan1 --override wardrive

# 5. Watch http://localhost:2501  (create login on first run)

# 6. Stop with Ctrl-C, then export
kismetdb_to_wiglecsv --in survey-*.kismet --out survey.wiglecsv
kismetdb_to_kml     --in survey-*.kismet --out survey.kml
```

Open `survey.kml` in Google Earth for the coverage map; review `survey.wiglecsv`
before any upload. That is a complete, transmit-free Wi-Fi survey.

> **Tier reminder.** This entire workflow is Tier 1 monitor-mode 802.11 — no
> CSI, no PHY, no IQ, no TX. It is included in *Latent Radios* as the practical,
> responsible bookend to the offensive/sensing chapters: the same cheap radios,
> pointed at understanding and defending your own airspace. Where the boundary
> to real SDR lies: [../true-sdr-comparison.md](../true-sdr-comparison.md).

---

## References

- Kismet — Intro / "what is Kismet": <https://www.kismetwireless.net/docs/readme/intro/kismet/>
- Kismet — Datasources overview: <https://www.kismetwireless.net/docs/readme/datasources/>
- Kismet — Linux Wi-Fi datasource (source syntax, channel options): <https://www.kismetwireless.net/docs/readme/datasources/wifi-linux/>
- Kismet — GPS configuration (gpsd/serial/tcp/virtual): <https://www.kismetwireless.net/docs/readme/gps/>
- Kismet — Logging (kismetdb, pcapng): <https://www.kismetwireless.net/docs/readme/logging/>
- Kismet — Kismetdb tools (to_wiglecsv, to_kml, dump_devices, to_pcap): <https://www.kismetwireless.net/docs/readme/kismetdb/>
- Kismet — Download / install: <https://www.kismetwireless.net/download/>
- WiGLE — wireless network observation database: <https://wigle.net/>
- Monitor-mode & injection support by chip (this catalog): [../../chips/monitor-injection-support.md](../../chips/monitor-injection-support.md)
- The defensive view — detection & privacy (this catalog): [../defensive-detection-and-privacy.md](../defensive-detection-and-privacy.md)
