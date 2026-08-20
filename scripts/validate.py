#!/usr/bin/env python3
"""Validate data/modules.json against data/schema.json.

Uses the `jsonschema` package when available; otherwise falls back to a
built-in checker covering the constraints that matter (required fields,
id uniqueness/format, tier range, and the capability/band/openness/status
enums). Exit code 0 = valid, non-zero = problems found.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "modules.json"
SCHEMA = ROOT / "data" / "schema.json"

CAP_ENUM = {
    "monitor", "injection", "csi", "spectral-scan", "raw-iq",
    "arbitrary-waveform", "radar", "fmcw", "passive-radar",
    "covert-channel", "open-firmware",
}
BAND_ENUM = {"sub-GHz", "2.4GHz", "5GHz", "6GHz", "60GHz", "UWB"}
OPENNESS_ENUM = {
    "open", "documented", "patchable", "partially-documented", "closed", "unknown",
}
STATUS_ENUM = {"verified", "reported", "theoretical"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def builtin_validate(modules):
    errors = []
    if not isinstance(modules, list):
        return ["top-level JSON must be an array"]
    seen = {}
    for i, m in enumerate(modules):
        where = f"[{i}] id={m.get('id', '?')!r}"
        for req in ("id", "vendor", "family", "sdr_tier", "sdr_capabilities",
                    "firmware", "status"):
            if req not in m:
                errors.append(f"{where}: missing required field '{req}'")
        mid = m.get("id")
        if mid is not None:
            if not ID_RE.match(str(mid)):
                errors.append(f"{where}: id not kebab-case")
            seen[mid] = seen.get(mid, 0) + 1
        tier = m.get("sdr_tier")
        if tier is not None and not (isinstance(tier, int) and 0 <= tier <= 5):
            errors.append(f"{where}: sdr_tier must be an int 0..5, got {tier!r}")
        for cap in m.get("sdr_capabilities", []) or []:
            if cap not in CAP_ENUM:
                errors.append(f"{where}: unknown capability {cap!r}")
        for band in m.get("bands", []) or []:
            if band not in BAND_ENUM:
                errors.append(f"{where}: unknown band {band!r}")
        fw = m.get("firmware", {})
        if isinstance(fw, dict):
            openness = fw.get("openness")
            if openness is None:
                errors.append(f"{where}: firmware.openness is required")
            elif openness not in OPENNESS_ENUM:
                errors.append(f"{where}: unknown firmware.openness {openness!r}")
        else:
            errors.append(f"{where}: firmware must be an object")
        status = m.get("status")
        if status is not None and status not in STATUS_ENUM:
            errors.append(f"{where}: unknown status {status!r}")
    dups = {k for k, v in seen.items() if v > 1}
    if dups:
        errors.append(f"duplicate ids: {sorted(dups)}")
    return errors


def main():
    modules = json.loads(DATA.read_text())
    schema = json.loads(SCHEMA.read_text())

    # id uniqueness is checked in both paths (schema can't express it well).
    ids = [m.get("id") for m in modules if isinstance(m, dict)]
    dups = sorted({i for i in ids if ids.count(i) > 1 and i})

    try:
        import jsonschema
    except ImportError:
        errors = builtin_validate(modules)
        for e in errors:
            print("ERROR:", e)
        if errors:
            sys.exit(1)
        print(f"builtin validator: OK — {len(modules)} modules, no errors")
        return

    try:
        jsonschema.validate(modules, schema)
    except jsonschema.ValidationError as e:
        print(f"SCHEMA ERROR: {e.message}")
        print("  at path:", list(e.absolute_path))
        sys.exit(1)
    if dups:
        print("ERROR: duplicate ids:", dups)
        sys.exit(1)
    print(f"jsonschema: OK — {len(modules)} modules validate against schema.json")


if __name__ == "__main__":
    main()
