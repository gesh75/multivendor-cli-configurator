#!/usr/bin/env python3
"""
fix_coverage_gaps.py — corpus repair pass for identified coverage gaps.

Idempotent transforms on commands.json:
  1. Retag NX-OS / IOS-XE rows mislabeled as ios
  2. Promote VXLAN / EVPN keyword hits into dedicated categories
  3. Collapse duplicate taxonomy (STP→Spanning-Tree, VRRP→HA)
  4. Unescape mangled placeholders (<name\\> → <name>)
  5. Shorten over-long titles derived from cmd when title is a dump

Writes commands.json in-place (compact). Prints a change summary.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "commands.json"

NXOS_HINT = re.compile(
    r"\b(?:"
    r"feature\s+(?:nxapi|bash-shell|nv\s+overlay|vn-segment|vn-segment-vlan-based|interface-vlan|lacp|vpc|bgp|ospf|pim|nv\s+overlay\s+evpn)|"
    r"nve\s+\d+|vlan\s+vn-segment|evpn\s+multisite|vpc\s+domain|vdc\s+|fabric\s+forwarding|"
    r"member\s+vni|peer-keepalive|peer-gateway|auto-recovery|"
    r"nv\s+overlay\s+evpn|route-target\s+both\s+auto\s+evpn"
    r")\b",
    re.I,
)

IOSXE_HINT = re.compile(
    r"\b(?:"
    r"guestshell|netconf-yang|restconf|telemetry\s+ietf|"
    r"platform\s+software|sdwan|iosxe|ios-xe|"
    r"yang-push|encode-kvgpb|gnxi"
    r")\b",
    re.I,
)

VXLAN_HINT = re.compile(
    r"\b(?:"
    r"vxlan|nve\b|vni\b|vn-segment|overlay\s+interface|"
    r"interface\s+nve|source-interface\s+nve|member\s+vni|"
    r"vxlan\s+flood|vxlan\s+vlan|vxlan\s+vni"
    r")\b",
    re.I,
)

EVPN_HINT = re.compile(
    r"\b(?:"
    r"evpn\b|l2vpn\s+evpn|address-family\s+l2vpn\s+evpn|"
    r"route-type\s+[25]\b|type-5|type-2|"
    r"rd\s+auto|route-target\s+both\s+auto\s+evpn|"
    r"advertise\s+l2vpn\s+evpn|retain\s+route-target|"
    r"mac-vrf|ip-vrf|vtep"
    r")\b",
    re.I,
)

ESC_PH = re.compile(r"<([^<>\\]+)\\>")


def norm_title_from_cmd(cmd: str, limit: int = 72) -> str:
    first = (cmd or "").strip().split("\n", 1)[0].strip()
    first = re.sub(r"\s+", " ", first)
    if len(first) <= limit:
        return first
    return first[: limit - 1].rstrip() + "…"


def blob(d: dict) -> str:
    return " ".join(
        [
            d.get("cmd", ""),
            d.get("title", ""),
            d.get("desc", ""),
            d.get("cat", ""),
        ]
    )


def main() -> None:
    data = json.load(open(OUT))
    stats = {
        "nxos_retag": 0,
        "iosxe_retag": 0,
        "vxlan_cat": 0,
        "evpn_cat": 0,
        "stp_collapse": 0,
        "vrrp_collapse": 0,
        "placeholder_fix": 0,
        "title_shorten": 0,
    }

    for d in data:
        # 1) OS retag (Cisco only)
        if d.get("vendor") == "Cisco" and d.get("os") == "ios":
            text = blob(d)
            if NXOS_HINT.search(text):
                d["os"] = "nxos"
                if d.get("role") == "router":
                    d["role"] = "switch"
                stats["nxos_retag"] += 1
            elif IOSXE_HINT.search(text):
                d["os"] = "iosxe"
                stats["iosxe_retag"] += 1

        # 2) VXLAN / EVPN category promotion (don't clobber already-correct cats)
        cat = d.get("cat") or ""
        if cat not in ("VXLAN", "EVPN"):
            text = blob(d)
            if EVPN_HINT.search(text):
                d["cat"] = "EVPN"
                stats["evpn_cat"] += 1
            elif VXLAN_HINT.search(text):
                d["cat"] = "VXLAN"
                stats["vxlan_cat"] += 1

        # 3) Taxonomy collapse
        if cat == "STP" or d.get("cat") == "STP":
            d["cat"] = "Spanning-Tree"
            stats["stp_collapse"] += 1
        if d.get("cat") == "VRRP":
            d["cat"] = "HA"
            stats["vrrp_collapse"] += 1

        # 4) Placeholder unescape in cmd/title/desc
        for field in ("cmd", "title", "desc"):
            val = d.get(field)
            if not val or "\\" not in val:
                continue
            fixed = ESC_PH.sub(r"<\1>", val)
            # also strip stray backslash before >
            fixed2 = fixed.replace("\\>", ">")
            if fixed2 != val:
                d[field] = fixed2
                stats["placeholder_fix"] += 1

        # 5) Shorten pathological titles (>90) using first cmd line
        title = d.get("title") or ""
        if len(title) > 90:
            d["title"] = norm_title_from_cmd(d.get("cmd") or title)
            stats["title_shorten"] += 1

    if "--dry-run" in sys.argv:
        print("[dry-run]", stats, "total", len(data))
        return

    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("fixed:", stats, "total:", len(data))


if __name__ == "__main__":
    main()
