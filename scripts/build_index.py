#!/usr/bin/env python3
"""Generate docs/index-by-capability.md from data/modules.json.

A capability-first view of the catalog. The two most common flags (monitor,
injection) are summarized by count; the rest get full tables. Regenerate after
every research cycle so the index stays exactly in sync with the database.
"""
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
m = json.loads((ROOT / "data" / "modules.json").read_text())

TIERNAME = {0: "black box", 1: "monitor+inject", 2: "CSI", 3: "spectral",
            4: "arbitrary-IQ TX", 5: "open PHY / SDR"}
CAP_ORDER = ["csi", "spectral-scan", "raw-iq", "arbitrary-waveform", "radar",
             "fmcw", "passive-radar", "covert-channel", "open-firmware",
             "injection", "monitor"]
CAP_DESC = {
    "csi": "Per-subcarrier channel state (Tier 2 sensing)",
    "spectral-scan": "Raw PHY FFT bins (Tier 3)",
    "raw-iq": "Time-domain IQ access",
    "arbitrary-waveform": "Author & transmit baseband IQ (Tier 4)",
    "radar": "Radar sensing mode", "fmcw": "FMCW ranging radar",
    "passive-radar": "Passive/bistatic radar",
    "covert-channel": "Non-native / cross-technology emission",
    "open-firmware": "Open or documented firmware/PHY",
    "injection": "Byte-exact frame transmit",
    "monitor": "RFMON capture of all frames",
}
BIG = {"monitor", "injection"}


def row(x):
    return (f"| {x.get('family','')} | {x.get('vendor','')} | "
            f"{x['sdr_tier']} ({TIERNAME[x['sdr_tier']]}) | {x.get('status','')} |")


out = ["# Index by capability\n",
       "A capability-first view of the catalog, generated directly from "
       "[`data/modules.json`](../data/modules.json) by "
       "[`scripts/build_index.py`](../scripts/build_index.py) — always exactly in "
       "sync with the database. For the two most common flags (`monitor`, "
       "`injection`) only counts are shown; browse [`data/modules.csv`]"
       "(../data/modules.csv) for full lists. See [taxonomy.md](taxonomy.md) for "
       "meanings and [methodology.md](methodology.md) for scoring.\n"]

counts = collections.Counter(c for x in m for c in x.get("sdr_capabilities", []))
out += ["## Capability totals\n", "| Capability | Count | Meaning |", "|---|---:|---|"]
out += [f"| `{c}` | {counts.get(c,0)} | {CAP_DESC[c]} |" for c in CAP_ORDER] + [""]

for c in CAP_ORDER:
    have = sorted([x for x in m if c in x.get("sdr_capabilities", [])],
                  key=lambda x: (-x["sdr_tier"], str(x.get("vendor", "")).lower(),
                                 str(x.get("id", ""))))
    out.append(f"## `{c}` — {CAP_DESC[c]} ({len(have)})\n")
    if c in BIG:
        byv = collections.Counter(x["vendor"] for x in have)
        out.append(f"{len(have)} modules across {len(byv)} vendors. Top: " +
                   ", ".join(f"{v} ({n})" for v, n in byv.most_common(10)) +
                   ". Full list in [`data/modules.csv`](../data/modules.csv).\n")
        continue
    out += ["| Chip / family | Vendor | Tier | Status |", "|---|---|---|---|"]
    out += [row(x) for x in have] + [""]

by = collections.defaultdict(list)
for x in m:
    by[x["sdr_tier"]].append(x)
out += ["## By tier\n", "| Tier | Name | Count |", "|---|---|---:|"]
out += [f"| {t} | {TIERNAME[t]} | {len(by[t])} |" for t in range(6)]
out += [f"\n*{len(m)} modules total.*\n"]

(ROOT / "docs" / "index-by-capability.md").write_text("\n".join(out))
print(f"wrote docs/index-by-capability.md ({len(m)} modules)")
