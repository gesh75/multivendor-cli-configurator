#!/usr/bin/env python3
"""Audit commands.json for data-quality defects flagged in the UI audit report.

Detects records where descriptive prose has leaked into the `title` or `cmd`
fields (a known artifact of chunking tutorial text from the Juniper source) and
records with implausibly long titles.

Usage:
    python3 scripts/audit_data_quality.py                 # report only (safe)
    python3 scripts/audit_data_quality.py --report out.json
    python3 scripts/audit_data_quality.py --quarantine    # write cleaned file + backup

Quarantine removes records whose `cmd` field itself contains prose (these are
unrecoverable — the command is garbage). Title-only prose is reported but NOT
removed, because the command may still be valid; fix those upstream in the
parse_*.py generators instead. A timestamped .bak is always written first.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "commands.json"

# Phrases that only appear in sentences, never in a CLI command or a terse title.
PROSE_RE = re.compile(
    r"\b(this is|it means|for example|note that|in order to|you can|which is|"
    r"such as|we'll see|by contrast|imagine that|halfway through)\b",
    re.IGNORECASE,
)
# A sentence boundary (". X") mid-field is a strong prose signal.
SENTENCE_BREAK_RE = re.compile(r"\.\s+[A-Z]")
MAX_TITLE_LEN = 90


def cmd_is_prose(cmd: str) -> bool:
    return bool(PROSE_RE.search(cmd) or SENTENCE_BREAK_RE.search(cmd))


def title_is_prose(title: str) -> bool:
    return bool(PROSE_RE.search(title) or (len(title) > 60 and SENTENCE_BREAK_RE.search(title)))


def audit(records: list[dict]) -> dict:
    cmd_prose, title_prose, long_title = [], [], []
    for i, d in enumerate(records):
        title = (d.get("title") or "").strip()
        cmd = (d.get("cmd") or "").strip()
        if cmd_is_prose(cmd):
            cmd_prose.append(i)
        if title_is_prose(title):
            title_prose.append(i)
        if len(title) > MAX_TITLE_LEN:
            long_title.append(i)
    return {"cmd_prose": cmd_prose, "title_prose": title_prose, "long_title": long_title}


def by_vendor(records: list[dict], idxs: list[int]) -> dict:
    counts: dict[str, int] = {}
    for i in idxs:
        v = records[i].get("vendor", "?")
        counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit commands.json data quality.")
    ap.add_argument("--report", metavar="FILE", help="write full flagged-index report to FILE (JSON)")
    ap.add_argument("--quarantine", action="store_true",
                    help="remove records whose cmd field is prose; writes a .bak first")
    args = ap.parse_args()

    records = json.loads(DATA.read_text(encoding="utf-8"))
    flags = audit(records)

    print(f"Total records: {len(records):,}")
    print(f"  cmd-field prose (unrecoverable): {len(flags['cmd_prose']):,}")
    print(f"  title-field prose (fix upstream): {len(flags['title_prose']):,}")
    print(f"  over-long titles (>{MAX_TITLE_LEN} chars): {len(flags['long_title']):,}")
    print(f"\ncmd-prose by vendor: {by_vendor(records, flags['cmd_prose'])}")
    print(f"title-prose by vendor: {by_vendor(records, flags['title_prose'])}")

    print("\nSample cmd-prose records:")
    for i in flags["cmd_prose"][:8]:
        d = records[i]
        print(f"  [{d.get('vendor')}/{d.get('cat')}] cmd={d.get('cmd','')[:70]!r}")

    if args.report:
        Path(args.report).write_text(json.dumps({
            "total": len(records),
            "flags": flags,
            "samples": {k: [records[i] for i in v[:25]] for k, v in flags.items()},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nFull report written to {args.report}")

    if args.quarantine:
        drop = set(flags["cmd_prose"])
        if not drop:
            print("\nNothing to quarantine.")
            return 0
        # Non-clobbering backup: never overwrite an existing .bak.
        bak = DATA.with_suffix(".prequarantine.json")
        n = 1
        while bak.exists():
            bak = DATA.with_suffix(f".prequarantine.{n}.json")
            n += 1
        shutil.copy2(DATA, bak)
        cleaned = [d for i, d in enumerate(records) if i not in drop]
        DATA.write_text(json.dumps(cleaned, ensure_ascii=False), encoding="utf-8")
        print(f"\nBackup: {bak}")
        print(f"Quarantined {len(drop):,} cmd-prose records → {len(cleaned):,} remain.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
