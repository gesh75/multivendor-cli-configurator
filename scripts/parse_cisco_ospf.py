#!/usr/bin/env python3
"""
Cisco IOS IP Routing: OSPF Command Reference parser.
Same bold-backtick format as the Arista EOS User Guide but Cisco-flavored.
All 113 commands → vendor=Cisco, os=ios, cat=OSPF (no recat needed — they're all OSPF).
"""
import re, json, pathlib
from collections import Counter

SRC = pathlib.Path(__file__).parent / "sources" / "cisco-ios-ospf-reference.md"
OUT = pathlib.Path(__file__).parent / "cisco_ospf.json"

TITLE_RE = re.compile(r"^\*\*`([^`]+)`\*\*\s*$")

def parse():
    text = SRC.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    section_hdr = "OSPF"
    pending_title = None
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            section_hdr = m.group(1).strip()
            i += 1; continue
        m = TITLE_RE.match(line)
        if m:
            pending_title = m.group(1).strip()
            i += 1; continue
        if line.strip().startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            # Description (markdown blockquote)
            desc = ""
            j = i
            while j < n and j < i + 6:
                ln = lines[j].strip()
                if not ln: j += 1; continue
                qm = re.match(r"^>\s*(.+?)\s*$", lines[j])
                if qm:
                    parts = [qm.group(1)]
                    k = j + 1
                    while k < n:
                        qq = re.match(r"^>\s*(.+?)\s*$", lines[k])
                        if qq: parts.append(qq.group(1)); k += 1
                        else: break
                    desc = " ".join(parts).strip()
                break
            cleaned = [l for l in block if l.strip()]
            if not cleaned:
                pending_title = None; continue
            cmd = "\n".join(cleaned).rstrip()
            first = cleaned[0].strip()
            # Skip obvious output samples
            if re.match(r"^(Active|Up|Down|Login:|Username:|--More--|Area\s+\d|i\s*\[)", first):
                pending_title = None; continue
            title = pending_title or first[:80]
            out.append({
                "os":"ios","role":"router","vendor":"Cisco","cat":"OSPF",
                "title": title[:80],
                "cmd": cmd,
                "desc": (desc or section_hdr)[:280],
            })
            pending_title = None
            continue
        i += 1
    return out

def main():
    items = parse()
    # dedupe within this source
    seen = set(); deduped = []
    for it in items:
        key = re.sub(r"\s+", " ", it["cmd"]).lower()
        if key in seen: continue
        seen.add(key); deduped.append(it)
    OUT.write_text(json.dumps(deduped, indent=1, ensure_ascii=False))
    print(f"wrote {len(deduped)} Cisco OSPF entries → {OUT}")
    print("titles sample:", [c["title"][:50] for c in deduped[:5]])

if __name__ == "__main__":
    main()
