#!/usr/bin/env python3
"""Fail if the docs have drifted from the real corpus in commands.json.

The command count, per-role breakdown, and vendor count are repeated by hand
across README.md and docs/index.html. This checker recomputes them from the
single source of truth (commands.json) and asserts every derived figure still
appears verbatim in those files, so a stale number fails CI instead of shipping.

Design notes:
- Hard failures are the raw numeric facts (total count, per-role counts, vendor
  count) — these are what actually drift and each is matched as a substring, so
  surrounding wording can change freely without tripping CI.
- The rounded marketing form (e.g. "69,000+") and the ~MB size are advisory
  warnings only, since those are phrasing/rounding choices that flip on small
  changes and shouldn't gate a merge.

Stdlib only. Run from anywhere: `python3 scripts/check_consistency.py`.
Exit 0 = consistent, 1 = drift found (details printed), 2 = usage/IO error.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "commands.json"

# Files that restate corpus figures. All get the same hard numeric checks.
TRACKED = ("README.md", "docs/index.html")


def fmt(n: int) -> str:
    return f"{n:,}"


def rounded_thousands(n: int) -> str:
    return f"{(n // 1000) * 1000:,}+"


def main() -> int:
    if not CORPUS.exists():
        print(f"ERROR: {CORPUS} not found", file=sys.stderr)
        return 2
    try:
        data = json.loads(CORPUS.read_text())
    except (ValueError, OSError) as exc:
        print(f"ERROR: cannot read {CORPUS}: {exc}", file=sys.stderr)
        return 2

    total = len(data)
    roles = Counter(row.get("role", "?") for row in data)
    vendors = sorted({row.get("vendor", "?") for row in data})
    size_mb = round(CORPUS.stat().st_size / (1024 * 1024))

    print("Corpus (source of truth: commands.json)")
    print(f"  total commands : {fmt(total)}")
    print(f"  rounded form   : {rounded_thousands(total)}")
    print("  roles          : " + " · ".join(f"{r} {fmt(c)}" for r, c in roles.most_common()))
    print(f"  vendors        : {len(vendors)}")
    print(f"  size           : ~{size_mb} MB")
    print()

    # Read each tracked file exactly once.
    contents: dict[str, str | None] = {}
    for rel in TRACKED:
        path = ROOT / rel
        contents[rel] = path.read_text() if path.exists() else None

    # Hard requirements: the raw numeric facts must appear verbatim.
    required = [fmt(total)] + [fmt(c) for c in roles.values()] + [f"{len(vendors)} vendor"]

    failures: list[str] = []
    for rel, text in contents.items():
        if text is None:
            failures.append(f"{rel}: file missing")
            continue
        for value in required:
            if value not in text:
                failures.append(f"{rel}: missing {value!r}")

    # Advisory only — phrasing/rounding, not raw facts.
    for rel, text in contents.items():
        if text is None:
            continue
        if rounded_thousands(total) not in text:
            print(f"WARNING: {rel} does not contain rounded form "
                  f"{rounded_thousands(total)!r}")
    docs = contents.get("docs/index.html")
    if docs is not None and f"~{size_mb} MB" not in docs:
        print(f"WARNING: docs/index.html does not mention '~{size_mb} MB' "
              f"(commands.json is now ~{size_mb} MB)")

    if failures:
        print("\nDRIFT DETECTED — docs are out of sync with commands.json:\n")
        for f in failures:
            print(f"  ✗ {f}")
        print("\nUpdate the file(s) above (and the profile hub) to the corpus figures.")
        return 1

    print("OK — README.md and docs/index.html match commands.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
