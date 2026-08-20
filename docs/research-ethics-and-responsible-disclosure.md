# Research Ethics & Responsible Disclosure

> **Why this page exists.** Everything else in *Latent Radios* is a capability map: how a commodity Wi‑Fi/BLE/sub‑GHz chip can be pushed off‑label into monitor mode, injection, CSI, spectral capture, and — at the far end — raw‑IQ transmit. Every one of those capabilities is **dual‑use**. The same CSI pipeline that powers a fall detector for an aging parent can count and track people through a wall who never consented to being measured. The same injection patch that lets you stress‑test your own AP is a denial‑of‑service weapon against someone else's. This page is the standard of conduct that keeps this catalog a legitimate security‑research resource rather than an attacker's handbook — written to be *usable*, not preachy.
>
> **This is not legal or IRB advice.** It is field practice and pointers to the primary frameworks. Your jurisdiction, your institution's review board, and your specific facts govern. When those conflict with anything here, they win.

Back to the catalog: [../README.md](../README.md) · Transmit/spectrum law: [../docs/rf-safety-and-legal.md](../docs/rf-safety-and-legal.md) · The defender's view: [../docs/defensive-detection-and-privacy.md](../docs/defensive-detection-and-privacy.md)

---

## 1. The dual‑use reality — name it, don't dodge it

"Dual‑use" is not a disclaimer to bolt on at the end; it is the actual nature of the work. Each rung of the [SDR ladder](../docs/taxonomy.md) is a tool that cuts both ways depending only on **intent, target, and consent**:

| Capability | Protective / legitimate use | Harmful / abusive use | What flips it |
|---|---|---|---|
| **Monitor mode / passive capture** | Auditing your own network, WIDS taps, protocol research | Harvesting MACs, capturing handshakes, mapping who is present | Whose traffic, and whether you're authorized to observe it |
| **Injection (Tier 1)** | Pen‑testing *your* AP, reproducing a CVE, PMF validation | Deauth DoS, evil‑twin, KARMA against others | Target ownership / written authorization |
| **CSI & raw‑PHY sensing (Tier 2–3)** | Fall detection, occupancy for HVAC, consented HCI research | Through‑wall tracking, keystroke inference, covert surveillance | Consent of the people being sensed |
| **Raw‑IQ / arbitrary‑waveform TX (Tier 4–5)** | Conducted lab R&D, licensed amateur experimentation | Jamming, spoofing, replay, off‑band emission | Authorization to *emit*, and containment |

The honest asymmetry from the [defensive chapter](../docs/defensive-detection-and-privacy.md#L19) carries an ethical weight: **injection is loud and catchable, passive sniffing is quiet, and passive sensing is invisible.** The less detectable a capability is, the more the burden falls on *your* ethics rather than on a victim's ability to notice — because no one is going to catch you. Invisibility raises the standard of care; it does not lower it.

A useful test before you build or publish anything: **"If the person on the other side of this could see exactly what I'm doing, would the arrangement survive?"** Consented sensing survives it. A pen‑test under contract survives it. Through‑wall monitoring of a neighbor does not. That question resolves most cases faster than any legal analysis.

---

## 2. Consent & privacy when you sense *people*

CSI‑based sensing is the part of this catalog with the sharpest ethical edge, because — uniquely — it needs **nothing from the subject**. No app, no packet sent at them, no device they own, no "recording light." An ordinary AP or laptop measures the channel that a human body perturbs. The subject cannot consent to, opt out of, or even detect a measurement they have no way of knowing is happening. That is precisely why consent has to be supplied *by the researcher*, deliberately.

### 2.1 The tiers of consent

- **Participants you recruit** — explicit, informed, revocable consent (see IRB, §5). They know what is measured, why, for how long, where the data goes, and how to withdraw.
- **Bystanders / non‑participants in the sensing volume** — the hard case. Wi‑Fi sensing does not respect the walls of your study. Anyone in an adjacent room, a hallway, or the flat next door can perturb the same multipath. You must either **geometrically confine** the sensing (siting, low power, absorptive/shielded boundaries) so non‑participants are not measurably in it, or obtain their consent too. "They happened to walk through" is a data‑minimization and consent failure, not a footnote.
- **Through‑wall / cross‑tenancy sensing of people who did not agree** — treat this as an **ethical red line**, the sensing analog of wiretapping. This repo takes that position explicitly ([defensive chapter §7.4](../docs/defensive-detection-and-privacy.md#L197)). There is essentially no research question that justifies non‑consensual through‑wall monitoring of identifiable individuals in their own space.

### 2.2 Practical consent hygiene for a sensing study

- **Notice at the boundary** — signage/announcement at every entrance to the sensing area ("Wi‑Fi sensing research in progress; measurements of movement are being recorded in this room"), so someone can decline by not entering.
- **Data minimization** — capture the *derived feature you actually need* (e.g. a motion/occupancy label) rather than raw CSI you'll never use, and set retention deliberately. Raw CSI is richer and more re‑identifying than most people assume.
- **Purpose limitation** — data gathered for "fall detection" is not a free pass to later train a gait‑identification model. New purpose → new consent / new review.
- **No secondary sensing** — do not use a deployed "smart home" sensing product's channel to infer things the household didn't sign up for (identity, count of guests, sexual activity, health events). Vendors building 802.11bf products inherit this obligation; opt‑out, on‑device processing, and no cross‑tenant sensing should be defaults, not features.

### 2.3 Special categories

Sensing can reveal **health information** (respiration, heart rate, gait indicative of disease, falls), **occupancy patterns** (when a home is empty — directly useful to burglars/stalkers), and **behavioral/biometric** signals. In the EU these are frequently "special category" data under **GDPR Art. 9** with a higher bar; in the US, health inferences can trigger sectoral rules. The point isn't the citation — it's that *what CSI reveals is often more sensitive than the researcher intends*, so classify your outputs by their **most sensitive** possible inference, not their nominal purpose.

---

## 3. The legal lines you don't get to cross

Research ethics and the law are separate constraints; you need to satisfy both. The spectrum/transmit side is covered in depth in [rf-safety-and-legal.md](../docs/rf-safety-and-legal.md) — the essentials, framed as ethics:

- **RX vs TX is the master distinction.** Receiving/sensing adds no energy to shared spectrum and is broadly (not universally) legal; **transmitting** is a regulated act with legal, safety‑of‑life, and human‑exposure dimensions. If your question can be answered by listening or by **conducted** bench testing (coax + dummy load, no radiation), that is both the safer *and* the more ethical experiment. Reception still has limits — decrypting or acting on protected/private communications (cellular, and more in the UK) is restricted even though tuning a receiver is not.
- **Jamming is the bright red line — always illegal.** Deliberately degrading, blocking, or overriding authorized radio communication (deauth floods, broadband noise, GPS/cell blockers, standards‑aware reactive jamming) is prohibited on **every** band, licensed or not, with no hobby or amateur exemption (US: 47 U.S.C. § 333; equivalents worldwide). It is never part of legitimate research. Note that some "defensive" measures — WIPS **air termination / containment** — are themselves spoofed‑deauth and are legally fraught for the same reason.
- **No unauthorized networks or devices.** Injection, evil‑twin, KARMA, replay, and spoofing against any system you do not **own or have written permission** to test are, in most countries, computer‑misuse offenses *in addition to* any spectrum violation. "It was only a test" is not a defense.
- **Safety‑of‑life bands are off‑limits, full stop** — aviation/GNSS/maritime‑distress/public‑safety. No experiment outranks them.

The clean, legal path for *emitting* custom waveforms with real power is an **amateur radio licence** on amateur allocations that overlap the ISM bands (US 47 CFR Part 97) — see [rf-safety-and-legal.md §7](../docs/rf-safety-and-legal.md). It converts "illegal experiment" into "licensed experiment"; it does not authorize jamming or off‑band emission.

---

## 4. Responsible disclosure of firmware & driver vulnerabilities

Reverse‑engineering Wi‑Fi firmware and drivers to reach a higher tier routinely surfaces **real vulnerabilities** — memory‑safety bugs in the D11 microcode or the host driver, parser flaws reachable over the air, protocol weaknesses. Wi‑Fi's biggest disclosures (KRACK, FragAttacks, Dragonblood) came out of exactly this kind of work. How you handle a finding is the difference between security research and reckless endangerment.

### 4.1 Coordinated Vulnerability Disclosure (CVD) — the norm

The consensus model, formalized in **ISO/IEC 29147** (disclosure) and **ISO/IEC 30111** (handling) and operationalized by the **CERT/CC Guide to Coordinated Vulnerability Disclosure**:

1. **Notify the vendor / a coordinator first**, privately, with enough detail to reproduce and fix.
2. **Give a reasonable remediation window** before public release — the widely‑adopted default is **90 days** (Google Project Zero style), with limited grace for an imminent patch. The clock protects users against foot‑dragging while still giving a good‑faith vendor time to ship.
3. **Publish** once fixed or the window lapses — enough for defenders to act, not a turnkey weapon (see §4.4).

Use a neutral **coordinator** — **CERT/CC** or a national CSIRT — when the vendor is unresponsive, hostile, or when the bug is **multi‑vendor**. Chipset/PHY bugs are almost always multi‑vendor (the same Broadcom/Qualcomm/MediaTek core ships in dozens of brands), and a coordinator is far better placed than a lone researcher to reach twenty vendors and synchronize a release date. That is exactly how KRACK and FragAttacks were run.

### 4.2 The vendor‑notification norm, concretely

- **Find the channel first**: a `security.txt` at `/.well-known/security.txt` (**RFC 9116**) names the vendor's contact and policy; failing that, a published VDP/bug‑bounty program, a `psirt@`/`security@` address, or the coordinator route.
- **Report with care**: a clear write‑up, reproduction steps, affected versions/part numbers, and your proposed disclosure date. Encrypt if a PGP key is offered.
- **Label sensitivity** with the **Traffic Light Protocol (TLP)** (FIRST) so everyone knows how far your report may travel (`TLP:RED` → named recipients only, etc.).
- **Keep records** of every contact and date — the timeline is your evidence of good faith if disclosure becomes contentious.
- **Be reachable and patient, but hold the line**: extend for a vendor genuinely engineering a fix; do not extend indefinitely for silence. Users' exposure is the thing the clock protects.

### 4.3 Getting a CVE — the identifier process

A **CVE ID** is the public, deduplicated name for the vulnerability; it is how defenders track and patch it. Under the current **CVE Program** (cve.org) structure:

- **If the affected vendor is a CNA** (CVE Numbering Authority — many chip/OS vendors are), report to them; they assign the CVE within their scope.
- **Otherwise**, request an ID from a CNA whose scope covers it, or from a **CNA of Last Resort** — **MITRE** for much of the ecosystem, or a coordinator like **CERT/CC** (itself a CNA/Root). cve.org has a public "Report/Request" form for non‑CNAs.
- **Timing**: reserve the CVE early (it can stay embargoed), and let it go public in coordination with the patch and your write‑up — not before the fix, unless the window has lawfully expired.
- A CVE is *not* a severity judgment; pair it with a **CVSS** vector (FIRST) so downstream users can prioritize.

### 4.4 Minimize harm in what you publish

- **Test only against your own devices/networks.** Never validate a firmware bug against third‑party hardware or live networks you don't control.
- **Don't exfiltrate real user data**, even to prove impact — synthesize it.
- **Proof‑of‑concept, not point‑and‑click.** For the riskiest findings (wormable, pre‑auth, safety‑relevant), publish enough for defenders and patch authors to act while withholding a weaponized, victim‑ready exploit. This is a judgment call, and erring toward defenders is the ethical default.
- **Credit and coordinate** with the vendor's advisory; contradictory timelines confuse the users you're trying to protect.

### 4.5 Legal guardrails for the researcher

- **CFAA (US)** — DOJ's **2022 policy** directs prosecutors not to charge **good‑faith security research**. Guidance, not immunity; scope and good faith still matter.
- **DMCA §1201 (US)** — the Copyright Office's recurring **security‑research exemption** permits good‑faith circumvention of device firmware access controls for research within its limits — directly relevant to the reverse‑engineering this whole catalog depends on.
- **Computer Misuse Act (UK)** and many equivalents are **less researcher‑friendly** — no blanket safe harbor; know your jurisdiction before you touch anything you don't own.
- **A written safe harbor beats an after‑the‑fact argument.** Prefer targets with a published VDP offering safe harbor (the **disclose.io** template is the common one). Spectrum law is *separate* — flawless disclosure ethics never authorize transmitting off‑band or jamming.

---

## 5. IRB / ethics‑board review for human‑subjects sensing

The moment your research **collects data about identifiable people** — which most Wi‑Fi sensing does — it is likely **human‑subjects research** and needs review *before* you collect anything, not after.

### 5.1 The frameworks

- **The Belmont Report** — the three foundational principles: **Respect for Persons** (informed, voluntary consent), **Beneficence** (maximize benefit, minimize harm), **Justice** (fair distribution of burdens/benefits). Every board decision traces back to these.
- **The Common Rule (US, 45 CFR 46)** — the federal regulation for human‑subjects research at institutions that receive federal funding (and adopted more broadly). Defines *human subject*, *research*, consent requirements, and IRB review levels (exempt / expedited / full board).
- **The Menlo Report** — Belmont adapted for **information and communications technology research**, adding **Respect for Law and Public Interest** and directly addressing networked/measurement research where subjects may be remote, numerous, or unaware. This is the most on‑point framework for RF sensing and is what program committees (IEEE S&P, USENIX Security, PETS, IMC) increasingly expect you to have engaged with.
- **GDPR / national data‑protection law** for EU subjects — lawful basis, special‑category rules (Art. 9), data‑subject rights, DPIA for high‑risk processing.

### 5.2 What a board will actually press you on (and you should pre‑empt)

- **Consent**: is it informed, voluntary, revocable? How do you handle **bystanders/non‑participants** who enter the sensing volume (§2)?
- **Minimization & retention**: why this data, for how long, and why not less?
- **Re‑identification risk**: can raw CSI, timing, or MACs re‑identify a "de‑identified" subject? (Often yes.)
- **Storage & access**: encryption at rest, access controls, breach plan.
- **Vulnerable populations & sensitive inference**: children, patients, health/occupancy inferences that could enable stalking or discrimination.
- **Deception/observation without consent**: rarely justifiable for RF sensing of individuals; expect to justify it hard or drop it.

### 5.3 The independent researcher without an IRB

Hobbyists and unaffiliated researchers have no board — which does **not** remove the obligation, it moves it onto you. Practical substitute:

- **Sense only yourself and consenting housemates**, in your own space, with the sensing volume physically confined.
- **Apply the Belmont/Menlo questions to yourself** as a checklist before collecting.
- **Find an ethics reviewer** — a colleague, a university contact, or a community mentor — for anything involving other people. Many venues now require an ethics statement and may **desk‑reject** work that plainly harmed non‑consenting people; "I had no IRB" is not an excuse there.

---

## 6. Dataset ethics — anonymization, consent, release

Wi‑Fi sensing runs on datasets, and this repo indexes many ([wifi-sensing-datasets.md](../projects/wifi-sensing-datasets.md)). Collecting or releasing one carries its own duties.

### 6.1 Collection

- **Consent covers the release**, not just the capture. If subjects agreed to an internal study, you cannot publish the raw data to the world without consent that anticipated it.
- **Log the provenance**: who consented to what, when, and the retention/deletion terms. A dataset without a consent record is a liability you can't clear later.

### 6.2 "Anonymization" — treat it as *de‑identification*, and be honest about limits

- **Strip and pseudonymize obvious identifiers** — MAC addresses (hash/rotate; note that **sequence‑number and IE fingerprinting defeat naive MAC anonymization**, see [defensive chapter §6](../docs/defensive-detection-and-privacy.md#L147)), device names, SSIDs, timestamps precise enough to correlate with external logs, location.
- **Understand that CSI is behaviorally rich.** Gait, presence patterns, and household routines can act as quasi‑identifiers even with every label removed. Anonymization reduces risk; it rarely eliminates re‑identification. Say so in the dataset card rather than overclaiming "fully anonymized."
- **Consider k‑anonymity/aggregation** for released features, and withhold raw traces when a derived feature suffices.

### 6.3 Release

- **Dataset documentation** (a *datasheet for datasets* / model‑card‑style doc): how it was collected, consent basis, who is in it, known biases, permitted uses, and prohibited uses.
- **License / use restrictions** that forbid re‑identification and non‑consensual‑surveillance applications.
- **Access control** for higher‑risk data (request‑and‑agree gating rather than an open bucket).
- **A deletion path** — honor withdrawal of consent, and design so you *can* remove a subject.

---

## 7. A pre‑work ethics checklist

Run this before you collect, build, or publish. A "no" means stop and rethink, not proceed carefully.

**Sensing people**
- [ ] Every person measurably in the sensing volume has **consented**, or is geometrically/again excluded — including bystanders and adjacent‑room / cross‑wall non‑participants.
- [ ] I classified my outputs by their **most sensitive** possible inference (health, occupancy, identity) and handle them at that level.
- [ ] I capture the **minimum** derived data needed, with a defined **retention** and deletion plan.
- [ ] Human‑subjects work has **IRB/ethics review** (or a documented independent‑researcher substitute) *before* collection.

**Transmitting / injecting**
- [ ] I am acting only on hardware/networks I **own or have written authorization** to test.
- [ ] I am **not** jamming, deauthing others, replaying, or spoofing any system I don't control.
- [ ] Any emission is on a band I'm **authorized** for, within limits, or fully **conducted/contained** — and never on a safety‑of‑life band. (See [rf-safety-and-legal.md](../docs/rf-safety-and-legal.md).)

**Disclosing a vulnerability**
- [ ] I found the vendor's **security contact** (`security.txt`/VDP/PSIRT) or a **coordinator** (CERT/CC) for multi‑vendor bugs.
- [ ] I set a **reasonable window** (≈90 days) and will disclose responsibly at the end whether or not a fix ships.
- [ ] I tested **only my own** devices, exfiltrated **no real user data**, and will publish **PoC over weaponized exploit** for high‑risk findings.
- [ ] I reserved/coordinated a **CVE** and paired it with a severity vector.

**Publishing**
- [ ] My write‑up helps **defenders** act without shipping a victim‑ready weapon or a surveillance recipe.
- [ ] Released data has **consent that covers release**, a **de‑identification honesty statement**, documentation, and a **deletion path**.

---

## 8. This repository's stance

*Latent Radios* documents **capabilities and their honest limits** for defenders, researchers, hobbyists, and builders. It does not publish turnkey attack payloads, victim‑targeting tooling, or instructions for non‑consensual surveillance of people. **Through‑wall sensing of non‑consenting individuals is an ethical red line**, not a feature to celebrate — which is why the [defensive chapter](../docs/defensive-detection-and-privacy.md) and this page exist alongside the capability maps. The catalog is more useful, not less, for being clear about the line it will not help you cross.

---

## References

**Disclosure & CVE process**
- CERT/CC — Guide to Coordinated Vulnerability Disclosure: <https://vuls.cert.org/confluence/display/CVD>
- CERT/CC — CVD guide (SEI report): <https://insights.sei.cmu.edu/library/the-cert-guide-to-coordinated-vulnerability-disclosure/>
- ISO/IEC 29147 (vulnerability disclosure): <https://www.iso.org/standard/72311.html>
- ISO/IEC 30111 (vulnerability handling): <https://www.iso.org/standard/69725.html>
- CVE Program (records, CNAs, request an ID): <https://www.cve.org/>
- FIRST — CVSS (severity scoring): <https://www.first.org/cvss/>
- FIRST — Traffic Light Protocol (TLP): <https://www.first.org/tlp/>
- RFC 9116 — `security.txt` (a file for security contact info): <https://www.rfc-editor.org/rfc/rfc9116>
- Google Project Zero — disclosure policy (90‑day norm): <https://googleprojectzero.blogspot.com/p/vulnerability-disclosure-policy.html>
- disclose.io — safe‑harbor / VDP framework: <https://disclose.io/>

**Legal guardrails**
- US DOJ — CFAA charging policy (good‑faith security research), 2022: <https://www.justice.gov/opa/pr/department-justice-announces-new-policy-charging-cases-under-computer-fraud-and-abuse-act>
- US Copyright Office — DMCA §1201 rulemaking / security‑research exemption: <https://www.copyright.gov/1201/>
- Communications Act — 47 U.S.C. § 333 (willful/malicious interference; jamming): <https://www.govinfo.gov/link/uscode/47/333>
- FCC — Jammer enforcement: <https://www.fcc.gov/general/jammer-enforcement>

**Human‑subjects & research ethics frameworks**
- The Belmont Report (HHS OHRP): <https://www.hhs.gov/ohrp/regulations-and-policy/belmont-report/index.html>
- The Common Rule — 45 CFR 46 (HHS OHRP): <https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/index.html>
- The Menlo Report — ethical principles for ICT research (DHS): <https://www.dhs.gov/sites/default/files/publications/CSD-MenloPrinciplesCORE-20120803_1.pdf>
- ACM Code of Ethics and Professional Conduct: <https://www.acm.org/code-of-ethics>
- EU GDPR (incl. Art. 9 special categories): <https://gdpr-info.eu/>

**Wi‑Fi disclosures that used coordinated, multi‑vendor CVD**
- KRACK (Vanhoef & Piessens, CCS 2017): <https://www.krackattacks.com/>
- FragAttacks (Vanhoef, 2021): <https://www.fragattacks.com/>
- Dragonblood (WPA3/SAE, Vanhoef & Ronen): <https://wpa3.mathyvanhoef.com/>

---

*Part of the [Latent Radios](../README.md) catalog. Read with [rf-safety-and-legal.md](../docs/rf-safety-and-legal.md) (what's legal to transmit/receive where you live) and [defensive-detection-and-privacy.md](../docs/defensive-detection-and-privacy.md) (detecting misuse and resisting ambient sensing). Not legal or IRB advice.*
