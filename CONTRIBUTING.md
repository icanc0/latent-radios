# Contributing to Latent Radios

The goal is **completeness with citations**. Every claim about what a chip can do should trace to a repo, paper, talk, datasheet, or a reproduction you did yourself.

## The one rule
**Cite your source.** A capability with no `references[]` entry is a rumor, not a catalog entry. Mark it `status: "theoretical"` until it has one.

## Adding a module

1. Add a prose entry to the right `chips/<vendor>.md` file (keep the section format consistent with existing entries).
2. Add a structured record to [`data/modules.json`](data/modules.json) following [`data/schema.json`](data/schema.json).
3. Run the validator and CSV builder:
   ```bash
   python3 scripts/validate.py      # checks modules.json against schema.json
   python3 scripts/build_csv.py     # regenerates data/modules.csv
   ```

### Record template
```json
{
  "id": "vendor-partnumber",
  "vendor": "Vendor Name",
  "family": "Family / part",
  "part_numbers": ["ABC1234", "ABC1234x"],
  "aliases": ["module name", "board name"],
  "standards": ["802.11n", "802.11ac"],
  "bands": ["2.4GHz", "5GHz"],
  "sdr_tier": 2,
  "sdr_capabilities": ["monitor", "injection", "csi"],
  "firmware": {
    "arch": "e.g. Broadcom D11 ucode + ARM Cortex-M3",
    "openness": "patchable",
    "re_tooling": ["nexmon", "ghidra"]
  },
  "key_projects": [{ "name": "Nexmon CSI", "url": "https://github.com/seemoo-lab/nexmon_csi" }],
  "common_hardware": ["Raspberry Pi 3B+", "some USB dongle"],
  "notes": "What works, what's fragile, band/bandwidth limits.",
  "references": ["https://…"],
  "status": "verified"
}
```

## Scoring guidance
- **`sdr_tier`** = the *highest* rung reachable with public tooling ([docs/taxonomy.md](docs/taxonomy.md)). Don't inflate: an arbitrary‑TX claim from a single conference demo is Tier 4 **with `status: "reported"`**, not a verified daily‑driver.
- **`sdr_capabilities`** = the concrete flags. A chip can be a low tier but still carry several flags.
- **`firmware.openness`**: `open` (source published) › `documented` › `partially-documented` › `patchable` (closed but reversible with known tooling) › `closed` › `unknown`.
- **`status`**: `verified` (you or a maintained project can do it today) › `reported` (a paper/talk showed it) › `theoretical` (plausible, unproven).

## Style
- One vendor per `chips/` file; one tool/framework per `projects/` file.
- Prefer primary sources (the actual repo/paper) over blog roundups.
- Every vendor file ends with an **`## Un‑cataloged / TODO`** list — move parts up into full entries as they're profiled. The list is never supposed to be empty; that's the point.

## Scope reminder
This is a research and reference index for **authorized** use. Don't add operational attack playbooks; do add the capability, the tooling, and the citation. Transmitting experiments belong in a shielded setup — note band/regulatory caveats in `notes`.
