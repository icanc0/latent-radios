#!/usr/bin/env python3
"""Flatten data/modules.json into data/modules.csv for spreadsheet use.

List fields are joined with '; '. Nested firmware/* fields are hoisted to
fw_* columns. Rows are sorted by (vendor, id) for stable diffs.
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "modules.json"
OUT = ROOT / "data" / "modules.csv"

COLUMNS = [
    "id", "vendor", "family", "part_numbers", "aliases", "standards", "bands",
    "sdr_tier", "sdr_capabilities", "fw_arch", "fw_openness", "fw_re_tooling",
    "key_projects", "common_hardware", "status", "references", "notes",
]


def join(seq):
    return "; ".join(seq or [])


def main():
    modules = json.loads(SRC.read_text())
    rows = []
    for m in modules:
        fw = m.get("firmware", {}) or {}
        rows.append({
            "id": m.get("id", ""),
            "vendor": m.get("vendor", ""),
            "family": m.get("family", ""),
            "part_numbers": join(m.get("part_numbers")),
            "aliases": join(m.get("aliases")),
            "standards": join(m.get("standards")),
            "bands": join(m.get("bands")),
            "sdr_tier": m.get("sdr_tier", ""),
            "sdr_capabilities": join(m.get("sdr_capabilities")),
            "fw_arch": fw.get("arch", ""),
            "fw_openness": fw.get("openness", ""),
            "fw_re_tooling": join(fw.get("re_tooling")),
            "key_projects": join([p.get("name", "") for p in m.get("key_projects", []) or []]),
            "common_hardware": join(m.get("common_hardware")),
            "status": m.get("status", ""),
            "references": join(m.get("references")),
            "notes": (m.get("notes", "") or "").replace("\n", " ").strip(),
        })

    rows.sort(key=lambda r: (str(r["vendor"]).lower(), str(r["id"])))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} — {len(rows)} rows")


if __name__ == "__main__":
    main()
