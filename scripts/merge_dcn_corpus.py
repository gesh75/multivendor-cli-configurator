#!/usr/bin/env python3
"""Merge the DCN Network Tool's pre-merged corpus (44,345 entries) into the
cheatsheet's commands.json (29,509 rows), deduplicating by (vendor, normalized cmd).

The source `cli-export.json` is already in cheatsheet schema, so we only need
vendor-name normalization + dedupe.

Paths are configurable (so the pipeline is reproducible on any machine):
  Source   --source     (env CLI_WORK_DCN_CORPUS) → the DCN cli-export.json corpus.
  Cheatsheet --output   (env CLI_WORK_CHEATSHEET) → defaults to the repo-relative
                          commands.json next to this repo's root.
Run with --help to see the resolved defaults on your machine.

Existing cheatsheet rows win on conflict (preserves FRR `live`/`in_docs` flags).
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# Paths are parameterized so the pipeline is reproducible on any machine.
# The cheatsheet defaults to the repo-relative commands.json (derived from
# __file__); the upstream corpus defaults to an overridable external path.
HERE = Path(__file__).resolve().parent
REPO = HERE.parent

DEFAULT_CHEATSHEET = Path(
    os.environ.get("CLI_WORK_CHEATSHEET", str(REPO / "commands.json"))
)
DEFAULT_SOURCE = Path(
    os.environ.get(
        "CLI_WORK_DCN_CORPUS",
        os.path.expanduser(
            "~/02_Projects/Network_Automation/VSS_Code_Georgi/"
            "04_Scripts_Tools/DCN_Network_Tool/cli_corpus/cli-export.json"
        ),
    )
)

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

def main(source: Path = DEFAULT_SOURCE, cheatsheet: Path = DEFAULT_CHEATSHEET):
    if not source.exists():
        print(f"FATAL: source not found: {source}", file=sys.stderr)
        sys.exit(1)
    if not cheatsheet.exists():
        print(f"FATAL: cheatsheet not found: {cheatsheet}", file=sys.stderr)
        sys.exit(1)

    cs  = load_json(cheatsheet)
    src = load_json(source)
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
    backup = cheatsheet.with_suffix(".json.bak")
    if not backup.exists():
        backup.write_text(cheatsheet.read_text())
        print(f"\nbackup: {backup}")
    with open(cheatsheet, "w") as f:
        json.dump(cs, f, separators=(",", ":"))
    sz = cheatsheet.stat().st_size
    print(f"wrote {cheatsheet} ({sz/1024/1024:.2f} MB)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge the DCN Network Tool corpus into the cheatsheet commands.json, "
            "deduplicating by (vendor, normalized cmd). Paths default to the "
            "repo-relative commands.json and an overridable corpus source "
            "(CLI_WORK_DCN_CORPUS env var) so the pipeline is reproducible."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the DCN cli-export.json corpus (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        "--cheatsheet",
        dest="cheatsheet",
        type=Path,
        default=DEFAULT_CHEATSHEET,
        help="Path to the cheatsheet commands.json to merge into (default: %(default)s).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    main(args.source, args.cheatsheet)
