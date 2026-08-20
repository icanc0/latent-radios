# The Defensive View — Detecting Misuse & Protecting Privacy

> **Scope of this chapter.** The rest of *Latent Radios* catalogs how commodity Wi‑Fi, Bluetooth, and other RF chips can be pushed off‑label — monitor mode, injection, CSI, spectral capture, occasional raw‑IQ. This chapter is the counterweight: how a defender **detects** that misuse, and how the general public can **resist the privacy loss** that ambient RF sensing creates. Nothing here is exotic. Most of it runs on the same cheap hardware the offensive chapters use; the difference is intent and configuration.
>
> Read this alongside [techniques.md](techniques.md) (what the attacks actually do at the PHY/MAC layer), [sensing-applications.md](../projects/wifi-sensing-productized.md) (what CSI-based sensing can infer about people), and [rf-safety-and-legal.md](rf-safety-and-legal.md) (what is legal to transmit, receive, and research where you live).

---

## 1. Threat model: what a defender is actually up against

Three distinct capabilities from the catalog map to three distinct defensive problems:

| Offensive capability (see catalog) | What the attacker gains | Defensive problem | Detectable? |
|---|---|---|---|
| **Frame injection / deauth** (Tier 1) | Forge management frames, knock clients off, evil-twin, KARMA | Active, on-air, produces anomalous frames | **Yes** — the frames are observable |
| **Monitor mode / passive capture** (Tier 1) | Silent sniffing, handshake capture, MAC harvesting | Passive receive, transmits nothing | **Barely** — near-invisible on-air |
| **CSI / raw-PHY sensing** (Tier 2–3) | Through-wall motion, presence, breathing, gesture, keystroke inference | Passive *measurement of the physical channel*, no packet touches the victim | **No, not directly** — this is the hard privacy problem |

The uncomfortable truth up front: **injection is loud and catchable, passive sniffing is quiet and mostly uncatchable, and passive sensing is invisible.** A defensive posture that only chases deauth floods is fighting the easiest third of the problem. This chapter treats all three honestly.

---

## 2. Detecting rogue frame injection & deauth attacks

### 2.1 Why deauth works at all

802.11 **management frames** (beacons, probe req/resp, authentication, association, deauthentication, disassociation) were historically sent **unauthenticated and unencrypted**. A deauthentication or disassociation frame is a single spoofed frame with the victim's MAC as source (or the AP's), reason code set, that any injection-capable radio can forge (`aireplay-ng --deauth`, `mdk4 d`, `scapy` `Dot11Deauth`). The client dutifully tears down the session. Repeat at a few frames/second and the client is held off the network — a trivial denial of service, and the front half of most evil‑twin / handshake‑capture / KARMA flows.

Related forgeable-frame attacks a WIDS should watch for: **disassociation floods**, **authentication/association floods** (resource exhaustion at the AP), **spoofed CSA** (Channel Switch Announcement — herds clients to an attacker channel), **beacon flooding / fake APs** (`mdk4 b`), **evil twin / karma** (AP answering every probed SSID), and **PMF downgrade / SA‑Query floods**.

### 2.2 Detection heuristics (what a WIDS keys on)

Deauth/rogue-frame detection is fundamentally **statistical and heuristic** — there is no cryptographic signature to check on a legacy frame, so detectors reason about *rate, direction, and consistency*:

- **Deauth/disassoc rate anomaly** — legitimate deauths are rare and bursty around roaming/shutdown. A sustained stream (dozens/sec) to one client or broadcast (`FF:FF:FF:FF:FF:FF`) is the classic signature. Kismet raises `DEAUTHFLOOD` / `BCASTDISCON` on exactly this.
- **Reason-code implausibility** — floods often reuse a single canned reason code, or codes that don't match the session state.
- **Sequence-number / timing discontinuity** — a spoofing radio rarely reproduces the victim's monotonic 802.11 sequence counter or the AP's beacon timing; gaps, resets, or duplicate SNs from a "known" MAC betray a second transmitter.
- **RSSI / signal-fingerprint mismatch** — the real AP sits at a stable received-signal level and (with CSI-capable taps) a stable channel fingerprint. A forged frame claiming to be that AP but arriving at a different RSSI or from a different PHY fingerprint is a strong rogue indicator. This is the most robust heuristic because it keys on physics, not header bytes.
- **PHY-layer / radiotap tells** — mismatched supported-rates, data rate, or capability bits versus the genuine device's historical profile.
- **BSSID/SSID collision** — two transmitters advertising the same BSSID (evil twin) or an AP answering SSIDs it never legitimately serves (KARMA).

> **Honest limitation.** Every one of these is evadable by a careful attacker who rate-limits, clones sequence numbers, and matches TX power. Detection raises the cost and catches the 95% of tooling that doesn't bother — it is not a cryptographic guarantee. The guarantee comes from PMF (§2.4).

### 2.3 Open-source blue-team tooling

| Tool | Role | Notes |
|---|---|---|
| **[nzyme](https://www.nzyme.org/)** ([source](https://github.com/nzymedefense/nzyme)) | Full WiFi WIDS/"network defense" platform | Distributed **taps** (cheap Wi‑Fi adapters/Raspberry Pi in monitor mode) feed a central node; alarms on deauth/disassoc anomalies, tracks unknown transmitters ("bandits"), rogue/evil-twin and unexpected-BSSID detection, and does signal-track / trilateration of transmitters. The most complete open blue-team option today. |
| **[Kismet](https://www.kismetwireless.net/)** | Sniffer + alerting engine | Long-standing; alerts include `DEAUTHFLOOD`, `BCASTDISCON`, `DISASSOCTRAFFIC`, `APSPOOF`, `CHANCHANGE`, `AIRJACKSSID`, cryptographically-weak and probe anomalies. Logs to a DB for later forensics; pairs well as a tap source. |
| **Wireshark / tshark** | Manual triage & forensics | Deauth = `wlan.fc.type_subtype == 0x0c`, disassoc = `0x0a`, filter a suspect BSSID and watch rate/reason-code/SN. Indispensable for confirming a WIDS alarm. |
| **airodump-ng (aircrack-ng)** | Quick live view | Shows a client dropping/re-associating repeatedly; not an alerting system but fast ground truth. |
| **OpenWIPS-ng** | Historical modular WIPS | From the aircrack-ng author; largely unmaintained but architecturally instructive (sensor → server → interface, plugin detectors). |

Commercial WIPS overlays (**Cisco Adaptive Wireless IPS / aWIPS**, **Aruba RFProtect**, **Arista/Mojo Wireless Manager**, **Extreme AirDefense**, **Cisco Meraki Air Marshal**, **WatchGuard WIPS**) automate the same heuristics with dedicated scanning radios and containment ("air termination") — themselves a spoofed-deauth capability, so containment is legally fraught (the FCC has fined operators for jamming/blocking guest hotspots).

### 2.4 802.11w (PMF) — the actual fix for deauth, and its limits

**802.11w-2009 / Protected Management Frames (PMF)** is the real mitigation, not a heuristic. It cryptographically protects a subset of management frames using the existing session keys:

- **Protects** deauthentication, disassociation, and *robust* action frames — so a forged deauth from an off-path attacker is rejected as unauthenticated. This kills the classic deauth DoS.
- **SA Query mechanism** — if an AP receives an *association/reassociation* request purporting to come from an already-associated client, it issues an encrypted **SA Query** to the real client. If the real client answers (proving it holds the keys), the spoofed association is discarded. This blocks the "spoofed re-association tears down the session" variant.
- **WPA3 makes PMF mandatory**; WPA2 offers it as optional/required (`ieee80211w=1` optional, `=2` required in `hostapd`/`wpa_supplicant`).

**Limits — be blunt about these:**

- PMF **does not protect pre-association frames**: beacons (legacy), probe requests/responses, and the initial authentication/association exchange are still forgeable. So **evil-twin, KARMA, beacon floods, and auth/assoc floods survive PMF.** *(Beacon protection was added later in 802.11 REVme / optional WPA3 to close the beacon-spoofing/CSA gap, but deployment is thin.)*
- An **association/auth flood** against the AP is still possible and can exhaust resources; some stacks are vulnerable to **SA-Query floods** themselves.
- **Downgrade**: a client that also accepts non-PMF networks can be lured to a rogue open/WPA2-no-PMF twin.
- **RF-layer jamming** (wideband noise, or standards-aware reactive jamming) bypasses *all* frame-level protection — it attacks the PHY, not the MAC. No MAC-layer control frame is involved to authenticate. This is a spectrum/physical problem, not a Wi‑Fi one (see [rf-safety-and-legal.md](rf-safety-and-legal.md)).

**Net:** turn PMF on everywhere (mandate WPA3 where the client fleet allows), and keep a WIDS running for the classes PMF cannot cover.

---

## 3. Detecting monitor-mode & rogue devices

### 3.1 Passive sniffers are nearly invisible — say so plainly

A radio in **monitor mode doing pure passive capture transmits nothing**. There is no frame to detect, no ARP to answer, no probe to fingerprint. The classic wired-LAN "promiscuous NIC" detectors (crafted ARP/ICMP that only a promiscuous stack answers — e.g. `nmap --script sniffer-detect`, L0phtcrack's AntiSniff) **do not apply to a Wi‑Fi monitor interface**, which is off-network and receive-only. Anyone who tells you they can reliably spot a silent Wi‑Fi sniffer across the room is overselling.

What *is* sometimes possible, with heavy caveats:

- **Local Oscillator (LO) leakage** — every superheterodyne receiver leaks a tiny amount of its LO back out the antenna. Specialized, expensive "hidden receiver" detectors exploit this; it is impractical at Wi‑Fi scale and range and is not a blue-team-at-home technique.
- **The sniffer eventually transmits** — most real attacks don't stay passive. The moment the adversary injects (deauth to force a handshake), spins up an evil twin, or the device beacons/probes on a second interface, it becomes visible to §2 tooling. Defense-in-depth assumes the passive phase is undetectable and catches the *active* phase.

### 3.2 Rogue AP / evil-twin / unauthorized-transmitter detection

This is the tractable half and where nzyme/Kismet/WIPS earn their keep:

- **Rogue AP** — an unexpected BSSID advertising your SSID, or *any* AP on your managed premises not in the authorized list. WIPS platforms maintain an allow-list and alarm on the rest; nzyme flags unexpected BSSIDs/fingerprints per monitored SSID.
- **Evil twin** — same SSID/BSSID as a legitimate AP but **different PHY fingerprint or RSSI/location** (§2.2). Signal-strength trilateration across multiple taps (nzyme) can even *locate* the rogue transmitter.
- **KARMA / MANA** — an AP that answers *every* SSID in probe requests. Detectable as one BSSID responding to implausibly many distinct SSIDs.
- **RF/PHY-layer device fingerprinting (research-grade)** — transmitter hardware imperfections (carrier frequency offset, I/Q imbalance, phase noise, transient turn-on) form a per-radio "RF fingerprint." Deep-learning RF-fingerprinting (e.g. DARPA RFMLS-style work) can distinguish two radios sending byte-identical frames, catching a spoofer that clones all header fields. Still lab/enterprise-grade, sensitive to channel and receiver drift, not a consumer tool — but it is the direction robust rogue-device detection is heading.

**Practical home/SMB posture:** enable WPA3+PMF, hide nothing behind "SSID hiding" (it doesn't help), run a single nzyme or Kismet tap if you care, keep an inventory of your own BSSIDs, and treat any duplicate SSID at a wrong signal level as hostile until proven otherwise.

---

## 4. The privacy threat of ambient Wi‑Fi sensing

This is the part of the catalog that should worry a *non-consenting third party* the most, and it has almost no clean defense.

### 4.1 What passive sensing extracts — without touching you

Because a Wi‑Fi receiver measures the **channel state information (CSI)** of every frame it hears, and human bodies perturb multipath, an observer needs **no cooperation from the victim and sends nothing at the victim**. From ambient traffic alone, published research has demonstrated:

- **Presence & occupancy counting** through interior walls,
- **Coarse motion / activity recognition** (walking, falling, sitting) — the productized end of this is fall-detection and "Wi‑Fi motion,"
- **Respiration and heart-rate** estimation at rest,
- **Gesture and gross pose** (MIT's WiVi / RF-Capture line — coarse through-wall silhouettes),
- **Keystroke / typing inference** (WiKey-class work) under controlled conditions.

See [sensing-applications.md](../projects/wifi-sensing-productized.md) for the capability detail and honest accuracy bounds. The privacy point here: **the sensing apparatus is an ordinary AP or laptop the victim can't see, on the far side of a wall, doing something that looks identical to normal networking.** There is no "recording light."

### 4.2 Standardization raises the stakes

**IEEE 802.11bf (WLAN Sensing)** is standardizing sensing as a first-class Wi‑Fi service, meaning future commodity APs will expose calibrated sensing measurements *by design* rather than as a firmware hack. The task group explicitly names **privacy and security as open concerns** ([survey, Restuccia, arXiv:2103.14918](https://arxiv.org/abs/2103.14918)). Once sensing is a standard feature, the "you needed a reverse-engineered firmware to do this" barrier — the entire premise of the offensive chapters — disappears for the sensing use case. Defenders should plan for a world where every AP is a sensor.

---

## 5. Defending against ambient sensing (and why it's hard)

There is no equivalent of "turn on PMF" here. The channel is a physical medium; you cannot authenticate multipath. The defenses are physical, obfuscatory, or policy-based — all partial.

### 5.1 Channel obfuscation with a reconfigurable surface — IRShield

The most convincing technical countermeasure to date is **IRShield** (Staat, Mulzer, Roth, Moonsamy, Heinrichs, Kronberger, Sezgin, Paar — **IEEE S&P 2022**, [arXiv:2112.01967](https://arxiv.org/abs/2112.01967)). It deploys an **Intelligent Reflecting Surface (IRS / RIS)** — a passive array of tunable reflecting elements — near the protected space and continuously randomizes its configuration. This actively **scrambles the wireless channel** an eavesdropper measures, injecting synthetic multipath variation that masks the human-motion signal. In their experiments against a state-of-the-art Wi‑Fi motion detector, **IRShield drove the attacker's detection rate to ≤5%**, as a plug-and-play add-on that leaves legitimate communication working. This is the reference result for "you can obfuscate CSI-based sensing without shutting off Wi‑Fi."

### 5.2 Deliberate signal obfuscation / cover motion — PhyCloak and friends

**PhyCloak** (Qiao, Chen — **USENIX NSDI 2016**, [paper](https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/qiao)) takes a different angle: a dedicated device distorts the Doppler/CSI signature in real time so that **unauthorized** sensing is defeated while **authorized** sensing (that knows the distortion) still works — a privacy-preserving "obfuscate to everyone but the keyholder" model. Related ideas: injecting **artificial cover motion** (fans, spoofed movement, randomized RF reflectors) to bury the real signal in noise, and transmitting decoy/jamming waveforms tuned to the sensing band. All raise the attacker's SNR bar; none are provably secure, and aggressive versions edge into "intentional interference," which is regulated (see [rf-safety-and-legal.md](rf-safety-and-legal.md)).

### 5.3 Physical and geometric measures

- **RF shielding** — conductive paint, window film, or (extreme) a Faraday enclosure attenuates the leakage that a through-wall sensor needs. Effective but coarse and impractical for whole homes.
- **Geometry / siting** — keeping APs and untrusted devices away from exterior walls, reducing transmit power to what coverage requires, and minimizing the multipath that leaks outward. Marginal but free.
- **Turning radios off** — the only complete defense for a given period is no RF. Worth stating plainly because everything else is partial.

### 5.4 Policy, consent, and standards

Because the technical defenses are weak, the durable protections are **legal and normative**: sensing of identifiable individuals should require **consent and notice**; 802.11bf and vendor "Wi‑Fi motion" products should ship privacy controls (opt-out, on-device processing, no cross-tenant sensing). Defenders and researchers should treat non-consensual through-wall sensing of people as an **ethical red line**, the sensing analog of wiretapping — and this repo takes that position (§7).

> **Honest bottom line.** Against a determined passive sensor, today's best deployable defense (IRShield-class channel randomization) reduces but does not eliminate the leak, and most homes have *no* defense deployed at all. Do not let §5 read as "solved." It is not.

---

## 6. MAC randomization and its limits

MAC randomization is the one privacy control most people actually have — and it leaks in more ways than users assume.

### 6.1 What it does

To stop passive **location tracking** (retail analytics, stalkers) that keys on a device's globally-unique MAC in probe requests and traffic, modern OSes substitute a **random, locally-administered MAC**:

- **iOS 8+** randomized probe-request MACs; **iOS 14+ / iPadOS 14+** use a **per-network "Private Wi‑Fi Address."**
- **Android 10+** randomizes per-network by default (per-SSID persistent, or per-connection non-persistent).
- **Windows 10/11** supports per-network and per-connection random hardware addresses.

### 6.2 Where it fails — the important part

Randomization is defeated by several well-documented linkage attacks; treat it as **friction, not anonymity**:

- **Global address leakage / broken implementations** — Martin *et al.* ("A Study of MAC Address Randomization in Mobile Devices and When it Fails," **PoPETs 2017**, [arXiv:1703.02874](https://arxiv.org/abs/1703.02874)) found devices frequently emitting their **true global MAC** where a random one should be used, and — the sharpest finding — a **low-level control-frame flaw letting an observer track 100% of randomizing devices regardless of vendor**, plus a passive technique defeating randomization on ~96% of Android phones.
- **Sequence-number linkage** — the 802.11 header's 12-bit sequence number increments monotonically per device across frames. It keeps counting *through* a MAC change, so consecutive randomized identities can be stitched back together by their SN continuity.
- **Information-element fingerprinting** — the exact set/order of IEs in a probe request (supported rates, HT/VHT capabilities, vendor-specific tags, WPS UUID-E) forms a fairly stable fingerprint. Vanhoef *et al.* ("Why MAC Address Randomization is Not Enough," **AsiaCCS 2016**, [paper](https://papers.mathyvanhoef.com/asiaccs2016.pdf)) also showed **active attacks** — e.g. abusing RTS/CTS and scrambler-seed/timing behavior — that force or link devices past randomization, plus reversing the **WPS UUID‑E** back to the real MAC.
- **Timing / inter-frame patterns** and **preferred-network-list (SSID) probes** — a device that still directed-probes for named SSIDs advertises a near-unique network history.

### 6.3 Practical guidance

Keep per-network randomization **on**; prefer OS versions that stop directed SSID probing; understand it defeats *casual* retail-analytics tracking but **not** a determined observer exploiting SN linkage or IE fingerprints. Real anonymity from RF tracking requires powering the radio off, not randomizing its label.

---

## 7. Responsible disclosure & research ethics

The techniques cataloged in *Latent Radios* are dual-use. What keeps this a defensible security-research resource rather than an attacker's handbook is **how findings are disclosed and how research is conducted.**

### 7.1 Coordinated Vulnerability Disclosure (CVD)

- **Report to the vendor / a coordinator first**, give a reasonable remediation window, then publish — the model formalized in **ISO/IEC 29147** (vulnerability disclosure) and **ISO/IEC 30111** (vulnerability handling), and in the **CERT/CC Guide to Coordinated Vulnerability Disclosure** ([SEI/CERT](https://vuls.cert.org/confluence/display/CVD)). Use **CERT/CC** or a national CSIRT as a neutral coordinator when a vendor is unresponsive or many vendors are affected (Wi‑Fi PHY/chipset bugs — KRACK, FragAttacks, Dragonblood — were multi-vendor and coordinated this way).
- **90-day default clock** (Google Project Zero style) — a widely-adopted norm balancing user protection against vendor foot-dragging; disclose after the window whether or not a fix ships, with limited grace for imminent patches.
- **Minimize harm** — test against your **own** devices/networks, never third parties; don't exfiltrate real user data; publish enough to let defenders act without shipping a turnkey weapon (proof-of-concept over point-and-click exploit for the riskiest findings).

### 7.2 Legal guardrails for researchers

- **CFAA (US)** — the DOJ's **May 2022 policy** directs prosecutors **not** to charge **good-faith security research** ([DOJ announcement](https://www.justice.gov/opa/pr/department-justice-announces-new-policy-charging-cases-under-computer-fraud-and-abuse-act)). It is prosecutorial guidance, not immunity — scope and good faith still matter.
- **DMCA §1201 (US)** — the Copyright Office's recurring **security-research exemption** permits good-faith circumvention of access controls (including device firmware) for research, within its stated limits ([copyright.gov/1201](https://www.copyright.gov/1201/)). Relevant directly to the firmware reverse-engineering this whole catalog depends on.
- **Computer Misuse Act (UK)** and equivalents elsewhere are **less researcher-friendly**; there is active reform debate but no blanket safe harbor. Know your jurisdiction.
- **Spectrum law is separate and strict** — even flawless disclosure ethics don't authorize **transmitting** off-band or jamming. Receiving is broadly permissible in many places; transmitting is licensed and enforced. See [rf-safety-and-legal.md](rf-safety-and-legal.md) and [regulatory-by-region.md](regulatory-by-region.md).

### 7.3 Safe harbor & program norms

Prefer targets with a published **security.txt** / **VDP** offering a **safe harbor** (the [disclose.io](https://disclose.io/) framework is the common template). A written safe harbor that authorizes your testing is worth more than any after-the-fact legal argument.

### 7.4 This repository's stance

*Latent Radios* documents **capabilities and their honest limits** for defenders, researchers, and hobbyists. It does not publish turnkey attack payloads, victim-targeting tooling, or instructions for non-consensual surveillance of people. **Through-wall sensing of non-consenting individuals is treated as an ethical red line**, not a feature to celebrate — which is the reason this defensive chapter exists.

---

## 8. Defender's quick-reference

| Threat | First-line defense | Detection tooling | Residual risk (be honest) |
|---|---|---|---|
| Deauth / disassoc DoS | **PMF (802.11w), mandate WPA3** | nzyme, Kismet (`DEAUTHFLOOD`) | PHY-layer jamming, pre-assoc floods |
| Evil twin / rogue AP | Authorized-BSSID inventory, WPA3-only | nzyme, Kismet (`APSPOOF`), WIPS | Downgrade to a rogue open twin |
| KARMA / auto-probe answering | Disable auto-join to open SSIDs; per-network randomization | Kismet, nzyme | Users manually joining rogue SSID |
| Passive sniffing | Assume it's happening; encrypt everything (WPA3, TLS) | *Largely undetectable while passive* | Handshake capture → offline crack (use strong/SAE) |
| CSI / through-wall sensing | IRShield-class IRS obfuscation; siting; radios off | *Not directly detectable* | **No complete defense deployed at scale** |
| MAC-based tracking | Per-network MAC randomization | — | SN linkage, IE/UUID‑E fingerprinting |
| Rogue transmitter location | Multi-tap RSSI trilateration | nzyme signal tracks | Low-power / mobile evaders |

---

## 9. References

- nzyme — WiFi defense/WIDS platform: <https://www.nzyme.org/> · source <https://github.com/nzymedefense/nzyme>
- Kismet wireless sniffer & alerting: <https://www.kismetwireless.net/>
- IEEE 802.11w / Protected Management Frames & WPA3 mandate — Wi‑Fi Alliance security: <https://www.wi-fi.org/discover-wi-fi/security>
- Staat et al., **IRShield: A Countermeasure Against Adversarial Physical-Layer Wireless Sensing**, IEEE S&P 2022 — <https://arxiv.org/abs/2112.01967>
- Qiao & Chen, **PhyCloak: Obfuscating Sensing from Communication Signals**, USENIX NSDI 2016 — <https://www.usenix.org/conference/nsdi16/technical-sessions/presentation/qiao>
- Restuccia, **IEEE 802.11bf: Toward Ubiquitous Wi‑Fi Sensing** (survey) — <https://arxiv.org/abs/2103.14918>
- Martin et al., **A Study of MAC Address Randomization in Mobile Devices and When it Fails**, PoPETs 2017 — <https://arxiv.org/abs/1703.02874>
- Vanhoef et al., **Why MAC Address Randomization is Not Enough**, AsiaCCS 2016 — <https://papers.mathyvanhoef.com/asiaccs2016.pdf>
- CERT/CC **Guide to Coordinated Vulnerability Disclosure** — <https://vuls.cert.org/confluence/display/CVD>
- ISO/IEC 29147 (vulnerability disclosure) — <https://www.iso.org/standard/72311.html>
- US DOJ, **CFAA charging policy** (good-faith security research), 2022 — <https://www.justice.gov/opa/pr/department-justice-announces-new-policy-charging-cases-under-computer-fraud-and-abuse-act>
- US Copyright Office, **DMCA §1201** rulemaking / security-research exemption — <https://www.copyright.gov/1201/>
- **disclose.io** safe-harbor framework — <https://disclose.io/>

*Cross-links: [techniques.md](techniques.md) · [sensing-applications.md](../projects/wifi-sensing-productized.md) · [rf-safety-and-legal.md](rf-safety-and-legal.md) · [regulatory-by-region.md](regulatory-by-region.md) · [csi-toolchains.md](../projects/csi-toolchains.md) · [wifi-sensing-datasets.md](../projects/wifi-sensing-datasets.md)*
