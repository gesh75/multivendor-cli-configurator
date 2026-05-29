#!/usr/bin/env python3
"""Merge the DCN Network Tool's pre-merged corpus (44,345 entries) into the
cheatsheet's commands.json (29,509 rows), deduplicating by (vendor, normalized cmd).

The source `cli-export.json` is already in cheatsheet schema, so we only need
vendor-name normalization + dedupe.

Source : ~/02_Projects/Network_Automation/VSS_Code_Georgi/04_Scripts_Tools/DCN_Network_Tool/cli_corpus/cli-export.json
Target : /tmp/cli-work/commands.json (cheatsheet)

Existing cheatsheet rows win on conflict (preserves FRR `live`/`in_docs` flags).
"""
from __future__ import annotations
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

CHEATSHEET = Path("/tmp/cli-work/commands.json")
SOURCE = Path(os.path.expanduser(
    "~/02_Projects/Network_Automation/VSS_Code_Georgi/"
    "04_Scripts_Tools/DCN_Network_Tool/cli_corpus/cli-export.json"
))

# Normalize divergent vendor labels to the cheatsheet's canonical names.
VENDOR_NORMALIZE = {
    "PaloAlto": "PAN-OS",
    "Palo Alto": "PAN-OS",
    "MikroTik": "Mikrotik",
    "Fortinet": "FortiOS",
    # New vendors keep their source spelling:
    # Microsoft, Linux, Wireshark — added to UI tables separately.
}

# Roles must be one of {router, switch, firewall} for existing UI filters to work.
# Map foreign roles into the closest existing bucket.
ROLE_NORMALIZE = {
    "analyzer": "switch",     # Wireshark — closest cheatsheet bucket
    "host":     "switch",     # Linux/PowerShell
    "endpoint": "switch",
}

def norm_cmd(s: str) -> str:
    """Collapse whitespace so trivial reformatting doesn't create dupes."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def load_json(p: Path):
    with open(p) as f:
        return json.load(f)

def main():
    if not SOURCE.exists():
        print(f"FATAL: source not found: {SOURCE}", file=sys.stderr)
        sys.exit(1)
    if not CHEATSHEET.exists():
        print(f"FATAL: cheatsheet not found: {CHEATSHEET}", file=sys.stderr)
        sys.exit(1)

    cs  = load_json(CHEATSHEET)
    src = load_json(SOURCE)
    print(f"cheatsheet:  {len(cs):>6} rows")
    print(f"source:      {len(src):>6} rows")

    # Build dedup key set from cheatsheet rows.
    keys = set()
    for r in cs:
        keys.add((r.get("vendor", ""), norm_cmd(r.get("cmd", ""))))

    added = 0
    skipped_dupe = 0
    vendor_in = Counter()
    vendor_added = Counter()

    for r in src:
        vraw = r.get("vendor", "")
        v = VENDOR_NORMALIZE.get(vraw, vraw)
        vendor_in[v] += 1
        cmd = r.get("cmd", "")
        if not cmd or not v:
            continue
        k = (v, norm_cmd(cmd))
        if k in keys:
            skipped_dupe += 1
            continue
        keys.add(k)
        role = r.get("role", "")
        role = ROLE_NORMALIZE.get(role, role) or "switch"
        new_row = {
            "os":     r.get("os", ""),
            "vendor": v,
            "role":   role,
            "cat":    r.get("cat", "Misc"),
            "title":  r.get("title", "")[:200] or cmd.split("\n")[0][:120],
            "cmd":    cmd,
            "desc":   r.get("desc", ""),
        }
        cs.append(new_row)
        added += 1
        vendor_added[v] += 1

    print(f"\nadded:       {added:>6} new rows")
    print(f"dedup skip:  {skipped_dupe:>6} (already in cheatsheet)")
    print(f"final size:  {len(cs):>6} rows")

    print("\nper-vendor additions:")
    for v, n in vendor_added.most_common():
        total_src = vendor_in[v]
        print(f"  {v:14s}  +{n:5d}  (of {total_src} source rows)")

    # Backup then write
    backup = CHEATSHEET.with_suffix(".json.bak")
    if not backup.exists():
        backup.write_text(CHEATSHEET.read_text())
        print(f"\nbackup: {backup}")
    with open(CHEATSHEET, "w") as f:
        json.dump(cs, f, separators=(",", ":"))
    sz = CHEATSHEET.stat().st_size
    print(f"wrote {CHEATSHEET} ({sz/1024/1024:.2f} MB)")

if __name__ == "__main__":
    main()
