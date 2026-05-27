#!/usr/bin/env python3
"""
Parse the FRR CLI Command Reference (06_Documentation/FRR_CLI_Command_Reference.json)
into the tool's row schema {os, role, vendor, cat, title, cmd, desc}.

Input shape (per-row):
  {
    "daemon":       "bgpd",
    "command":      "router bgp AS-NUMBER view NAME",
    "description":  "Make a new BGP view...",
    "source_file":  "bgpd.rst"
  }

Output: scripts/frr.json — same envelope as encor.json / junos.json / arista.json.
Then `parse.py` merges it into ../commands.json on next run.

No third-party deps; Python 3 stdlib only.
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
from collections import Counter

# --- Paths -------------------------------------------------------------------

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_INPUT = pathlib.Path(
    "/Users/georgigaydarov/02_Projects/Network_Automation/VSS_Code_Georgi/"
    "06_Documentation/FRR_CLI_Command_Reference.json"
)
OUTPUT = HERE / "frr.json"

# --- Daemon → category map ---------------------------------------------------
# Categories deliberately align with existing categories used by other parsers
# so the Compare view's conceptKey() can line up FRR `router bgp` with Cisco
# `router bgp` and Junos `set protocols bgp`.

DAEMON_TO_CAT: dict[str, str] = {
    "bgpd":            "BGP",
    "bgp-linkstate":   "BGP",            # variant; stays in BGP bucket
    "bmp":             "BGP",            # BMP is a BGP monitoring feature
    "ospfd":           "OSPF",
    "ospf6d":          "OSPFv3",
    "isisd":           "ISIS",
    "fabricd":         "OpenFabric",
    "pim":             "Multicast",
    "pimv6":           "Multicast",
    "ripd":            "RIP",
    "ripngd":          "RIPng",
    "ldpd":            "MPLS",
    "babeld":          "Babel",
    "eigrpd":          "EIGRP",
    "bfd":             "BFD",
    "vrrp":            "VRRP",
    "vnc":             "VNC",
    "nhrpd":           "NHRP",
    "pathd":           "Segment Routing",
    "pbr":             "PBR",
    "rpki":            "RPKI",
    "sharp":           "Troubleshooting",
    "staticd":         "Routing",
    "routemap":        "Routing",        # route-maps are routing policy
    "filter":          "AAA",            # access-lists / prefix-lists policy
    "zebra":           "Routing",
    "ipv6":            "Interfaces",     # ipv6 nd / interface-level
    "basic":           "System",
    "vtysh":           "System",
    "mgmtd":           "System",
    "extlog":          "System",
}

# --- Placeholder substitution to make `cmd` paste-runnable -------------------
# `title` keeps the FRR signature with placeholders intact. `cmd` is a filled
# example so the row's Copy button gives the user something runnable.

# Order matters: longer/more specific patterns first.
_PLACEHOLDER_PASSES: list[tuple[re.Pattern, str]] = [
    # IPv4 prefix
    (re.compile(r"\bA\.B\.C\.D/M\b"),            "10.0.0.0/24"),
    (re.compile(r"\bA\.B\.C\.D\b"),              "10.0.0.1"),
    # IPv6
    (re.compile(r"\bX:X::X:X/M\b"),              "2001:db8::/64"),
    (re.compile(r"\bX:X::X:X\b"),                "2001:db8::1"),
    # MAC
    (re.compile(r"\bH\.H\.H\b"),                 "0050.5681.1234"),
    (re.compile(r"\bHH:HH:HH:HH:HH:HH\b"),       "00:50:56:81:12:34"),
    # Common literal placeholders
    (re.compile(r"\bAS-NUMBER\b"),               "65001"),
    (re.compile(r"\bASN\b"),                     "65001"),
    (re.compile(r"\bROUTER-ID\b"),               "1.1.1.1"),
    (re.compile(r"\bIFNAME\b"),                  "eth0"),
    (re.compile(r"\bINTERFACE\b"),               "eth0"),
    (re.compile(r"\bVRF-?NAME\b", re.IGNORECASE),"VRF1"),
    (re.compile(r"\bVIEW-?NAME\b", re.IGNORECASE),"VIEW1"),
    (re.compile(r"\bRD\b"),                      "65001:1"),
    (re.compile(r"\bRT\b"),                      "65001:1"),
    (re.compile(r"\bCOMMUNITY\b"),               "65001:100"),
    (re.compile(r"\bLINE\b"),                    "DESCRIPTION"),
    (re.compile(r"\bWORD\b"),                    "MYWORD"),
    (re.compile(r"\bNAME\b"),                    "MYNAME"),
    # Numeric range like (1-600) or (0-4294967295) → middle-ish/first sensible
    (re.compile(r"\((\d+)-(\d+)\)"),
        lambda m: str(min(int(m.group(2)), max(int(m.group(1)), 10)))),
    # Choice groups: `[a | b | c]` → `a` (no brackets); `<a | b>` → `a`
    (re.compile(r"\[([^\[\]|]+?)(?:\s*\|\s*[^\[\]]+)?\]"),
        lambda m: m.group(1).strip()),
    (re.compile(r"<([^<>|]+?)(?:\s*\|\s*[^<>]+)?>"),
        lambda m: m.group(1).strip()),
]


def fill_placeholders(cmd: str) -> str:
    """Best-effort substitute placeholders so the cmd is paste-runnable."""
    out = cmd
    for pat, repl in _PLACEHOLDER_PASSES:
        out = pat.sub(repl, out)
    return out.strip()


# --- Description tidying -----------------------------------------------------

_RST_DIRECTIVE = re.compile(
    r"\n\s*\.\.\s+(code-block|sourcecode|note|warning|tip|seealso)::.*?(?=\n\S|\Z)",
    re.DOTALL,
)
_BACKTICK_DOUBLE = re.compile(r"``([^`]+)``")
_BACKTICK_SINGLE = re.compile(r"`([^`]+)`")


def first_sentence(desc: str, cap: int = 220) -> str:
    """Strip RST artifacts and return first 1–2 sentences, capped at `cap`."""
    if not desc:
        return ""
    s = _RST_DIRECTIVE.sub("", desc)
    s = _BACKTICK_DOUBLE.sub(r"\1", s)
    s = _BACKTICK_SINGLE.sub(r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    # First sentence — first period followed by space/end. Keep up to 2 if short.
    parts = re.split(r"(?<=[.!?])\s+", s)
    out = parts[0]
    if len(out) < 80 and len(parts) > 1:
        out = (out + " " + parts[1]).strip()
    if len(out) > cap:
        out = out[: cap - 1].rstrip() + "…"
    return out


# --- Role inference ----------------------------------------------------------
# FRR is a routing stack used on Linux hosts / clab / SONiC / Cumulus / VyOS-FRR.
# All commands map to role="router" — the only role FRR ships in.

def role_for(_daemon: str) -> str:
    return "router"


def cat_for(daemon: str) -> str:
    d = (daemon or "").lower().strip()
    if d in DAEMON_TO_CAT:
        return DAEMON_TO_CAT[d]
    # Fallback by fuzzy match on the daemon name
    if "bgp"   in d: return "BGP"
    if "ospf6" in d: return "OSPFv3"
    if "ospf"  in d: return "OSPF"
    if "isis"  in d: return "ISIS"
    if "rip"   in d: return "RIP"
    if "pim"   in d or "mld" in d or "igmp" in d: return "Multicast"
    if "ldp"   in d or "mpls" in d: return "MPLS"
    if "bfd"   in d: return "BFD"
    if "vrrp"  in d: return "VRRP"
    if "vrf"   in d: return "Routing"
    return "System"


# --- Main --------------------------------------------------------------------

def main(input_path: pathlib.Path = DEFAULT_INPUT) -> int:
    if not input_path.exists():
        print(f"error: FRR source not found: {input_path}", file=sys.stderr)
        return 1

    src = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(src, list):
        print("error: expected top-level list", file=sys.stderr)
        return 1

    rows: list[dict] = []
    seen: set[str] = set()
    daemon_counter: Counter = Counter()
    cat_counter: Counter = Counter()

    for entry in src:
        cmd_sig = (entry.get("command") or "").strip()
        if not cmd_sig:
            continue
        daemon = (entry.get("daemon") or "").strip().lower()
        desc = entry.get("description") or ""
        source_file = entry.get("source_file") or ""

        cat = cat_for(daemon)
        title = cmd_sig                       # keep placeholders for the title
        cmd = fill_placeholders(cmd_sig)      # paste-runnable version
        short_desc = first_sentence(desc)

        # Add daemon as a breadcrumb so the desc is never blank for empty source descs.
        if short_desc:
            short_desc = f"{cat} > {short_desc}"
        else:
            short_desc = f"{cat} > daemon: {daemon}" if daemon else cat

        key = re.sub(r"\s+", " ", cmd).lower()
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "os": "frr",
            "role": role_for(daemon),
            "vendor": "FRR",
            "cat": cat,
            "title": title,
            "cmd": cmd,
            "desc": short_desc,
        })
        daemon_counter[daemon] += 1
        cat_counter[cat] += 1

    OUTPUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"wrote {len(rows)} FRR rows → {OUTPUT}")
    print("\nTop daemons:")
    for d, n in daemon_counter.most_common(15):
        print(f"  {d:20s} {n}")
    print("\nBy category:")
    for c, n in cat_counter.most_common():
        print(f"  {c:20s} {n}")

    # Show 3 sample rows
    print("\nSample rows:")
    for r in rows[:3]:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    src_arg = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    sys.exit(main(src_arg))
