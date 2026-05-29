#!/usr/bin/env python3
"""Repair records whose `title` field holds description prose instead of a label.

A known artifact of the parse/merge pipeline: for some records the first
sentence of the description leaked into `title`, leaving a paragraph where a
short command label belongs. The `cmd` field is intact, so we derive a clean
title from it.

Idempotent and safe to re-run after any regeneration. Operates on any file in
the cheatsheet schema ({os,role,vendor,cat,title,cmd,desc}).

Usage:
    python3 scripts/clean_titles.py --dry-run            # report, change nothing
    python3 scripts/clean_titles.py FILE [FILE ...]      # clean given files in place (.bak each)
    python3 scripts/clean_titles.py                      # default: commands.json + tracked per-vendor JSONs
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROSE_RE = re.compile(
    r"\b(this is|it means|for example|note that|in order to|you can|which is|"
    r"such as|we'll see|by contrast|imagine that|halfway through|enable or disable|"
    r"this command|this provides|activates the|access to these)\b",
    re.IGNORECASE,
)
# A real sentence boundary: period + space + a capital NOT followed by another
# capital. Catches "interface. A lifetime" but not `..` placeholders (FRR
# `ARGS.. 10`) or acronym runs.
SENTENCE_BREAK_RE = re.compile(r"(?<!\.)\.\s+[A-Z](?![A-Z])")
# Function words signal natural-language prose. A SHORT curated label like
# "Show running config" has none; a wrapped description has several.
FUNCTION_WORDS = frozenset(
    "the a an of to for on in with that which by into from when as is are be "
    "will can your you this these those and or but if then about".split()
)


def function_word_count(t: str) -> int:
    toks = re.findall(r"[A-Za-z]+", t.lower())
    return sum(1 for w in toks[1:] if w in FUNCTION_WORDS)
# Leading CLI prompt: a hostname/mode token (optionally with (mode) groups,
# which may themselves contain '#') ending in #, > or % then whitespace.
PROMPT_RE = re.compile(r"^[\w.@/+-]+(?:\([^\n]*?\))?\s*[#>%]\s+")
MAX_TITLE = 70


def title_is_prose(title: str, cmd: str = "") -> bool:
    """True when the title is natural-language description rather than a label.

    Conservative by design: short curated labels (e.g. "Show running config",
    "Configure IP address") are NEVER flagged, only sentences/wrapped prose."""
    t = (title or "").strip()
    if "\n" in t:                                   # wrapped multi-line description
        return True
    if PROSE_RE.search(t):                           # explicit prose phrases
        return True
    if len(t) > 60 and SENTENCE_BREAK_RE.search(t):  # contains a real sentence
        return True
    if len(t) > 60 and function_word_count(t) >= 3:  # long & sentence-like
        return True
    return False


# Prose verbs/clauses that should never appear in a CLI command label.
NOT_COMMAND_RE = re.compile(
    r"(?<!\.)\.\s+[A-Z][a-z]|;\s+[a-z]|"  # real sentence / clause boundary
    r"\b(can be|is used|are used|will be|allows|provides|configures|"
    r"specifies|places|bypasses|enters|displays|indicates|determines|"
    r"applies to|refers to|used to|in order|you can|you may|you must|"
    r"you should|you want|of your)\b",
    re.IGNORECASE,
)


def looks_like_command(s: str) -> bool:
    """A usable command label: no sentence punctuation, no prose verbs, not too
    long, and starting like a command rather than an English sentence/heading.

    CLI commands in this corpus start lowercase, with a bracket/slash/digit, or
    are PowerShell-style `Verb-Noun`. Prose and section headings start with a
    capitalized word followed by lowercase text — those are not salvageable."""
    if not s:
        return False
    if NOT_COMMAND_RE.search(s):
        return False
    # High function-word density means the cmd field is prose too (e.g. Juniper
    # tutorial text), not a real command — unsalvageable.
    if function_word_count(s) >= 3:
        return False
    # Length is NOT a prose signal — CLI commands legitimately carry many
    # bracketed option tokens (e.g. `show [ip] bgp [<view|vrf> NAME] ...`).
    first = s[0]
    if first.islower() or first in "[<({/.-" or first.isdigit():
        return True
    return bool(re.match(r"^[A-Z][a-z]+-[A-Z]", s))  # PowerShell cmdlet


def title_from_cmd(cmd: str) -> str:
    """Derive a concise label from the command's first line, or '' if not usable."""
    first = (cmd or "").split("\n")[0].strip()
    if not first:
        return ""
    # Strip a CLI prompt prefix if present (handles nested-paren modes via the
    # last prompt delimiter, e.g. 'switch(Policy-Map (#))# class' -> 'class').
    if PROMPT_RE.match(first):
        m = re.search(r"[#>%]\s+(\S.*)$", first)
        if m:
            first = m.group(1).strip()
    first = re.sub(r"\s+", " ", first)
    if not looks_like_command(first):
        return ""  # cmd itself is prose — unsalvageable, leave for quarantine
    if len(first) > MAX_TITLE:
        first = first[:MAX_TITLE].rstrip() + "…"
    return first


def clean_records(records: list[dict]) -> tuple[int, list[int], list[dict]]:
    """Repair salvageable titles in place; return (fixed, unfixable_indices, samples)."""
    fixed = 0
    unfixable_idx = []
    samples = []
    for i, d in enumerate(records):
        if not isinstance(d, dict):
            continue
        title = d.get("title", "")
        if title_is_prose(title, d.get("cmd", "")):
            new = title_from_cmd(d.get("cmd", ""))
            if new:
                if len(samples) < 8:
                    samples.append((d.get("vendor"), title[:50], new))
                d["title"] = new
                fixed += 1
            else:
                unfixable_idx.append(i)  # cmd is prose too — nothing to salvage
    return fixed, unfixable_idx, samples


def process(path: Path, dry: bool, drop_unfixable: bool) -> tuple[int, int]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  skip {path.name}: {e}")
        return 0, 0
    if not isinstance(records, list):
        print(f"  skip {path.name}: not a record array")
        return 0, 0
    fixed, unfixable_idx, samples = clean_records(records)
    drop_n = len(unfixable_idx) if drop_unfixable else 0
    extra = f", {len(unfixable_idx)} unfixable (cmd also prose){' — dropped' if drop_unfixable else ' — kept'}"
    print(f"{path.name}: {fixed} repaired / {len(records)} records{extra if unfixable_idx else ''}")
    for v, old, new in samples:
        print(f"    [{v}] {old!r} -> {new!r}")
    changed = fixed or drop_n
    if changed and not dry:
        bak = path.with_suffix(path.suffix + ".titlebak")
        if not bak.exists():
            shutil.copy2(path, bak)
        if drop_unfixable and unfixable_idx:
            drop = set(unfixable_idx)
            records = [d for i, d in enumerate(records) if i not in drop]
        # commands.json is loaded over HTTP; keep it compact like the original.
        compact = path.name == "commands.json"
        path.write_text(
            json.dumps(records, ensure_ascii=False, **({} if compact else {"indent": 2})),
            encoding="utf-8",
        )
    return fixed, drop_n


def default_targets() -> list[Path]:
    targets = [ROOT / "commands.json"]
    # Tracked per-vendor parsed outputs that may carry prose titles.
    for name in ("arista.json", "cisco_asa.json", "external_merged.json", "junos.json"):
        p = ROOT / "scripts" / name
        if p.exists():
            targets.append(p)
    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair prose-in-title records.")
    ap.add_argument("files", nargs="*", help="files to clean (default: commands.json + tracked JSONs)")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--keep-unfixable", action="store_true",
                    help="do NOT drop records whose cmd is also prose (default: drop them)")
    args = ap.parse_args()

    drop = not args.keep_unfixable
    targets = [Path(f) for f in args.files] if args.files else default_targets()
    tf = td = 0
    for p in targets:
        f, d = process(p, args.dry_run, drop)
        tf += f
        td += d
    verb = "[dry-run] would repair" if args.dry_run else "Repaired"
    print(f"\n{verb} {tf} title(s); {'would drop' if args.dry_run else 'dropped'} {td} unfixable record(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
