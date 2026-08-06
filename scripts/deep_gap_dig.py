#!/usr/bin/env python3
"""
deep_gap_dig.py — exhaustive coverage-gap audit for the configurator corpus + Automate stack.

Reports (and optionally fails CI on) remaining holes across:
  - thin OS floors (nxos / iosxe / sros / sonic / asa)
  - overlay categories (VXLAN / EVPN)
  - L2 promotions (Spanning-Tree / EtherChannel / BFD)
  - Automate AUTO_* vendor keys (no silent Cisco fallback for network vendors)
  - OS_DEV_TYPE / NETMIKO_DEV_TYPE / ANSIBLE_MOD coverage
  - data-quality gates (prose cmd, over-long titles, escaped placeholders)
  - essential-cat presence for network vendors (keyword OR dedicated cat)

Usage:
  python3 scripts/deep_gap_dig.py            # report + exit 1 on critical misses
  python3 scripts/deep_gap_dig.py --json out.json
  python3 scripts/deep_gap_dig.py --warn-only # never fail
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "commands.json"
HTML = ROOT / "index.html"

# Floors after wave-2 fills — keep conservative so CI stays stable.
OS_FLOORS = {
    "nxos": 200,
    "iosxe": 120,
    "sros": 70,
    "sonic": 450,
    "asa": 400,
}
CAT_FLOORS = {
    "VXLAN": 250,
    "EVPN": 490,
    "Spanning-Tree": 400,
    "EtherChannel": 250,
    "BFD": 100,
}

NETWORK_VENDORS = [
    "Cisco",
    "Juniper",
    "Arista",
    "FRR",
    "VyOS",
    "Nokia",
    "Aruba",
    "Huawei",
    "NVIDIA",
    "SONiC",
    "Extreme",
    "Mikrotik",
]
# FortiOS / PAN-OS intentionally excluded from L2/L3 Automate completeness —
# firewall platforms use different primitives.
AUTO_REQUIRED = NETWORK_VENDORS
AUTO_MAPS = [
    "AUTO_IFACE_IPV4",
    "AUTO_STATIC",
    "AUTO_OSPF",
    "AUTO_BGP",
    "AUTO_VLAN",
    "AUTO_HOSTNAME",
    "AUTO_NTP",
    "AUTO_SYSLOG",
]

ESSENTIAL_FOR_SWITCH_FABRIC = {
    # vendor → required cats (dedicated category OR keyword hit acceptable via soft check)
    "Extreme": ["Spanning-Tree", "BGP", "OSPF", "ACL", "EtherChannel"],
    "Cisco": ["Spanning-Tree", "VXLAN", "EVPN", "BFD", "EtherChannel"],
    "Arista": ["Spanning-Tree", "VXLAN", "EVPN", "EtherChannel"],
    "SONiC": ["BGP", "VXLAN", "ACL", "VLAN"],
    "Nokia": ["BGP", "OSPF", "VXLAN", "EVPN"],
}


def extract_auto_vendors(html: str, name: str) -> set[str]:
    keys: set[str] = set()
    # keys inside the const object (first ~80 lines after const)
    m = re.search(rf"const\s+{name}\s*=\s*\{{", html)
    if not m:
        return keys
    chunk = html[m.start() : m.start() + 12000]
    end = chunk.find("\n};")
    if end > 0:
        chunk = chunk[:end]
    for v in NETWORK_VENDORS + ["FortiOS", "PAN-OS", "Microsoft", "Linux", "Wireshark"]:
        if re.search(rf"(?:^|\n)\s*{re.escape(v)}\s*:", chunk):
            keys.add(v)
        if re.search(rf"{re.escape(name)}\.{re.escape(v)}\s*=", html):
            keys.add(v)
    return keys


def extract_object_keys(html: str, const_name: str) -> set[str]:
    m = re.search(rf"const\s+{const_name}\s*=\s*\{{([\s\S]*?)^\}};", html, re.M)
    if not m:
        return set()
    body = m.group(1)
    keys = set()
    for raw in re.findall(r'["\']?([A-Za-z0-9_.-]+)["\']?\s*:', body):
        if raw in ("show", "cfg", "collection", "vtysh"):
            continue
        keys.add(raw.strip("\"'"))
    return keys


def cmd_is_prose(cmd: str) -> bool:
    return bool(
        re.search(
            r"\b(this is|it means|for example|note that|in order to|you can|which is|"
            r"such as|we'll see|by contrast|imagine that|halfway through)\b",
            cmd,
            re.I,
        )
        or re.search(r"\.\s+[A-Z]", cmd)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args()

    data = json.loads(CORPUS.read_text())
    html = HTML.read_text()
    report: dict = {"total": len(data), "critical": [], "warnings": [], "stats": {}}

    os_c = Counter(r.get("os") for r in data)
    cat_c = Counter(r.get("cat") for r in data)
    vendor_c = Counter(r.get("vendor") for r in data)
    report["stats"]["os"] = dict(os_c)
    report["stats"]["cats_focus"] = {k: cat_c.get(k, 0) for k in CAT_FLOORS}
    report["stats"]["vendors"] = dict(vendor_c)

    print(f"Corpus: {len(data):,} commands · {len(vendor_c)} vendors · {len(os_c)} OS labels\n")

    print("=== OS floors ===")
    for o, floor in OS_FLOORS.items():
        n = os_c.get(o, 0)
        ok = n >= floor
        print(f"  {'PASS' if ok else 'FAIL'}  {o}: {n} (floor {floor})")
        if not ok:
            report["critical"].append(f"os floor {o}: {n} < {floor}")

    print("\n=== Category floors ===")
    for c, floor in CAT_FLOORS.items():
        n = cat_c.get(c, 0)
        ok = n >= floor
        print(f"  {'PASS' if ok else 'FAIL'}  {c}: {n} (floor {floor})")
        if not ok:
            report["critical"].append(f"cat floor {c}: {n} < {floor}")

    print("\n=== Automate AUTO_* vendor keys ===")
    for name in AUTO_MAPS:
        present = extract_auto_vendors(html, name)
        missing = [v for v in AUTO_REQUIRED if v not in present]
        ok = not missing
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: missing {missing or '∅'}")
        if missing:
            report["critical"].append(f"{name} missing vendors: {missing}")

    silent_fb = len(re.findall(r"\|\|AUTO_\w+\.Cisco\)\(v\)", html))
    hardcoded = bool(
        re.search(
            r'\[\s*"Cisco"\s*,\s*"Juniper"\s*,\s*"Arista"\s*\]\.filter\(\s*v\s*=>\s*found\.mapping\.render',
            html,
        )
    )
    print("\n=== Automate safety ===")
    print(f"  {'PASS' if silent_fb == 0 else 'FAIL'}  silent Cisco fallbacks: {silent_fb}")
    print(f"  {'PASS' if not hardcoded else 'FAIL'}  openAutomation not C/J/A-only: {not hardcoded}")
    if silent_fb:
        report["critical"].append(f"silent AUTO_*.Cisco fallbacks: {silent_fb}")
    if hardcoded:
        report["critical"].append("openAutomation hardcodes Cisco/Juniper/Arista only")
    if "AUTO_VENDORS" not in html:
        report["critical"].append("openAutomation missing AUTO_VENDORS")
        print("  FAIL  AUTO_VENDORS missing")
    else:
        print("  PASS  AUTO_VENDORS present")
    if 'id="btn-clibuilder"' in html and "Builder" in html[html.find('id="btn-clibuilder"') : html.find('id="btn-clibuilder"') + 200]:
        print("  PASS  Builder navbar label")
    else:
        report["critical"].append("Builder navbar label missing")
        print("  FAIL  Builder navbar label")

    print("\n=== Netmiko / Ansible maps ===")
    netmiko = extract_object_keys(html, "NETMIKO_DEV_TYPE")
    os_dev = extract_object_keys(html, "OS_DEV_TYPE")
    ansible = extract_object_keys(html, "ANSIBLE_MOD")
    for label, have, need in [
        ("NETMIKO_DEV_TYPE vendors", netmiko, set(vendor_c)),
        ("OS_DEV_TYPE os", os_dev, set(os_c)),
        ("ANSIBLE_MOD vendors", ansible, set(vendor_c)),
    ]:
        missing = sorted(need - have)
        # OS_DEV_TYPE may omit nothing critical; report all
        ok = not missing
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: missing {missing or '∅'}")
        if missing:
            # OS map misses are critical; vendor map misses too
            report["critical"].append(f"{label} missing: {missing}")

    print("\n=== Essential fabric cats (dedicated category) ===")
    by_v_cats: dict[str, set[str]] = defaultdict(set)
    for r in data:
        by_v_cats[r.get("vendor", "?")].add(r.get("cat") or "?")
    for v, need in ESSENTIAL_FOR_SWITCH_FABRIC.items():
        missing = [c for c in need if c not in by_v_cats.get(v, set())]
        ok = not missing
        print(f"  {'PASS' if ok else 'FAIL'}  {v}: missing {missing or '∅'}")
        if missing:
            report["critical"].append(f"{v} missing cats: {missing}")

    print("\n=== Data quality ===")
    prose = sum(1 for r in data if cmd_is_prose(r.get("cmd") or ""))
    long_t = sum(1 for r in data if len(r.get("title") or "") > 90)
    esc = sum(
        1
        for r in data
        if any("\\>" in (r.get(f) or "") for f in ("cmd", "title", "desc"))
    )
    empty_desc = sum(1 for r in data if not (r.get("desc") or "").strip())
    for label, n, critical in [
        ("cmd prose", prose, True),
        ("over-long titles", long_t, True),
        ("escaped placeholders", esc, True),
        ("empty desc", empty_desc, False),
    ]:
        ok = n == 0 if critical else True
        print(f"  {'PASS' if (n == 0 if critical else True) else 'FAIL'}  {label}: {n}")
        if critical and n:
            report["critical"].append(f"{label}: {n}")
        if not critical and n:
            report["warnings"].append(f"{label}: {n}")

    print("\n=== Idempotency smoke (dry logic) ===")
    # Re-running promotions on current corpus should be near-zero for retags
    # (reported as warning only — deep dig itself does not mutate).
    report["warnings"].append("run scripts/fix_coverage_gaps.py --dry-run separately")

    print("\n=== Summary ===")
    print(f"  critical: {len(report['critical'])}")
    print(f"  warnings: {len(report['warnings'])}")
    for c in report["critical"]:
        print(f"  ✗ {c}")
    for w in report["warnings"][:12]:
        print(f"  ! {w}")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\nWrote {args.json}")

    if args.warn_only:
        return 0
    return 1 if report["critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
