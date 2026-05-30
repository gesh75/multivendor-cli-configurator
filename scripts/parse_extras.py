#!/usr/bin/env python3
"""
Parse the 9 "wave 2" reference JSONs into the tool's row schema.

Inputs (06_Documentation/):
  - VyOS_CLI_Command_Reference.json           → scripts/vyos.json     (vendor=VyOS,    os=vyos)
  - SONiC_CLI_Command_Reference.json          → scripts/sonic.json    (vendor=SONiC,   os=sonic)
  - Cumulus_NVUE_CLI_Command_Reference.json   → scripts/nvue.json     (vendor=NVIDIA,  os=nvue)
  - PANOS_CLI_Command_Reference.json          → scripts/panos.json    (vendor=PAN-OS,  os=panos)
  - Nokia_SRLinux_CLI_Command_Reference.json  → scripts/srlinux.json  (vendor=Nokia,   os=srlinux)
  - FortiOS_CLI_Command_Reference.json        → scripts/fortios.json  (vendor=FortiOS, os=fortios)
  - Mikrotik_RouterOS_CLI_Command_Reference.json → scripts/routeros.json (vendor=Mikrotik, os=routeros)
  - Cisco_Gaps_CLI_Command_Reference.json     → scripts/cisco_gaps.json (vendor=Cisco, os=ios) — backfills Cisco
  - Juniper_Gaps_CLI_Command_Reference.json   → scripts/juniper_gaps.json (vendor=Juniper, os=junos) — backfills Junos

All produce the tool's row schema: {os, role, vendor, cat, title, cmd, desc}.

No third-party deps. Python 3 stdlib only.
"""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

# Base dir holding the upstream vendor reference JSONs. Override with the
# CLI_WORK_DOCS env var or the --source flag to run off another machine.
DEFAULT_DOCS = pathlib.Path(
    os.environ.get(
        "CLI_WORK_DOCS",
        "/Users/georgigaydarov/02_Projects/Network_Automation/VSS_Code_Georgi/"
        "06_Documentation",
    )
)
# Parsed outputs are written alongside the other parser outputs in scripts/.
DEFAULT_OUTPUT_DIR = HERE

# --- Category normalisation -------------------------------------------------
# Source categories vary per vendor. We map each to the tool's existing
# category taxonomy so Compare view's conceptKey() lines things up.
RAW_CAT_TO_TOOL = {
    # General
    "system": "System",
    "interfaces": "Interfaces",
    "protocols": "Routing",     # default; refined below by keyword
    "security": "Security",     # default; refined below
    "services": "System",
    "firewall": "Firewall",
    "vpn": "VPN",
    "nat": "NAT",
    "qos": "QoS",
    "acl": "ACL",
    "container": "System",
    "high-availability": "HA",
    "ha": "HA",
    "monitor": "Troubleshooting",
    "monitoring": "Troubleshooting",
    "operational": "Troubleshooting",
    "policy": "Routing",
    "policy-options": "Routing",
    "system-services": "System",
    "load-balancing": "HA",
    "load-balance": "HA",
    "natural language": "System",
    "docs": "System",
    "diagnostics": "Troubleshooting",
    "operations": "Troubleshooting",
    # Already-correct labels
    "bgp": "BGP",
    "ospf": "OSPF",
    "isis": "ISIS",
    "eigrp": "EIGRP",
    "mpls": "MPLS",
    "vlan": "VLAN",
    "multicast": "Multicast",
    "routing": "Routing",
}


# Keyword overrides applied to the actual command string. Order matters —
# first match wins. Same idea as the existing categorize() in parse.py.
_KEYWORD_OVERRIDES = [
    (re.compile(r"\b(bgp|neighbor)\b", re.I), "BGP"),
    (re.compile(r"\bospf6|ospfv3\b", re.I),    "OSPFv3"),
    (re.compile(r"\bospf\b", re.I),            "OSPF"),
    (re.compile(r"\b(isis|is-is|openfabric)\b", re.I), "ISIS"),
    (re.compile(r"\beigrp\b", re.I),           "EIGRP"),
    (re.compile(r"\b(mpls|ldp|rsvp-te|segment-routing)\b", re.I), "MPLS"),
    (re.compile(r"\bvxlan|evpn|vtep\b", re.I), "BGP"),  # VXLAN/EVPN is BGP family
    (re.compile(r"\b(igmp|pim|mld|mroute|multicast)\b", re.I), "Multicast"),
    (re.compile(r"\b(vrrp|hsrp|carp|vpc|chassis-cluster)\b", re.I), "HA"),
    (re.compile(r"\b(stp|spanning-tree|rstp|mstp|pvst)\b", re.I), "Spanning-Tree"),
    (re.compile(r"\b(port-channel|lacp|lag|bond|ether-channel)\b", re.I), "EtherChannel"),
    (re.compile(r"\b(vlan|trunk|access)\b", re.I), "VLAN"),
    (re.compile(r"\b(nat|natfw)\b", re.I),     "NAT"),
    (re.compile(r"\bqos|policer|shaper|police|priority-queue\b", re.I), "QoS"),
    (re.compile(r"\b(vpn|ipsec|gre tunnel|wireguard|l2tp|pptp|sstp|openvpn)\b", re.I), "VPN"),
    (re.compile(r"\b(acl|access-list|filter|prefix-list|community-list)\b", re.I), "ACL"),
    (re.compile(r"\b(firewall|security policy|rulebase)\b", re.I), "Firewall"),
    (re.compile(r"\b(dhcp|dhcpv6)\b", re.I),   "DHCP"),
    (re.compile(r"\b(rip|ripng)\b", re.I),     "RIP"),
    (re.compile(r"\bbfd\b", re.I),             "BFD"),
    (re.compile(r"\b(static[-\s]+route|static route|route-static)\b", re.I), "Routing"),
    (re.compile(r"\b(aaa|tacacs|radius|local-user|user-management)\b", re.I), "AAA"),
    (re.compile(r"\b(syslog|logging)\b", re.I), "Logging"),
    (re.compile(r"\bsnmp\b", re.I),            "SNMP"),
    (re.compile(r"\bntp\b", re.I),             "NTP"),
    (re.compile(r"\b(wireless|wifi|wlan|ssid)\b", re.I), "Wireless"),
    (re.compile(r"\b(interface|port|ether|sub-interface|loopback|vlan-interface)\b", re.I), "Interfaces"),
    (re.compile(r"\b(show|display|ping|traceroute|debug|monitor|diag|diagnose)\b", re.I), "Troubleshooting"),
]


def normalize_category(raw: str, command: str, default: str = "System") -> str:
    # Keyword overrides win over the raw label — they're more specific.
    for pat, cat in _KEYWORD_OVERRIDES:
        if pat.search(command or ""):
            return cat
    if raw:
        key = raw.lower().strip()
        if key in RAW_CAT_TO_TOOL:
            return RAW_CAT_TO_TOOL[key]
    return default


# --- Command sanitisation ---------------------------------------------------
_BACKSLASH_BRACKETS = re.compile(r"\\([<>])")          # \< → <, \> → >
_RST_INLINE_REF = re.compile(r"\{[a-z]+\}`([^`]+)`")    # {rfc}`3623` → 3623
_BACKTICK_DOUBLE = re.compile(r"``([^`]+)``")
_BACKTICK_SINGLE = re.compile(r"`([^`]+)`")
_MULTI_WS = re.compile(r"\s+")


_HUAWEI_PROMPT = re.compile(r"^\[[^\]]+\]\s+")  # `[Huawei] command…` / `[Huawei-GigabitEthernet0/0/1] …`

def clean_command(s: str, multi_sep: str = " -> ", strip_prompt: bool = False) -> str:
    """Clean up vendor-specific encoding artefacts in the command field."""
    if not s:
        return ""
    out = _BACKSLASH_BRACKETS.sub(r"\1", s)        # \<name\> → <name>
    # FortiOS / Aruba / Huawei use ' -> ' as line separator on a single line.
    # Split it so the rendered card shows the command block as multiple lines.
    if multi_sep in out:
        out = "\n".join(p.strip() for p in out.split(multi_sep) if p.strip())
    if strip_prompt:
        # Huawei VRP: rows often start with `[Huawei]` or `[Huawei-Iface]` —
        # the device prompt indicator. Drop it so the cmd is paste-runnable
        # AT the matching VRP view.
        out = "\n".join(_HUAWEI_PROMPT.sub("", ln) for ln in out.split("\n"))
    return out.strip()


def first_sentence(desc: str, cap: int = 220) -> str:
    if not desc:
        return ""
    s = _RST_INLINE_REF.sub(r"\1", desc)
    s = _BACKTICK_DOUBLE.sub(r"\1", s)
    s = _BACKTICK_SINGLE.sub(r"\1", s)
    s = _MULTI_WS.sub(" ", s).strip()
    parts = re.split(r"(?<=[.!?])\s+", s)
    out = parts[0]
    if len(out) < 80 and len(parts) > 1:
        out = (out + " " + parts[1]).strip()
    if len(out) > cap:
        out = out[: cap - 1].rstrip() + "…"
    return out


def title_from_command(cmd: str, cap: int = 90) -> str:
    """Cards show `title` as the headline. We use the first non-empty line of
    the command (post-clean), truncated to a sensible width."""
    if not cmd:
        return ""
    first = cmd.splitlines()[0]
    if len(first) > cap:
        first = first[: cap - 1].rstrip() + "…"
    return first


# --- SONiC special handling -------------------------------------------------
# SONiC's reference has a mix of real CLI commands (`show bgp summary`,
# `config bgp startup neighbor ...`) and header-style strings pulled from
# the markdown TOC (`Show Management Interface`). We drop the latter — they
# aren't paste-runnable and would just clutter results.
_SONIC_CLI_OPENERS = re.compile(r"^\s*(show|config|sudo|sonic-installer|sonic-cli|sonic-clear|monitor|debug|ping|ping6|traceroute|traceroute6|tail|cat|systemctl|docker|redis-cli)\s+", re.I)


def looks_like_sonic_cli(cmd: str) -> bool:
    return bool(_SONIC_CLI_OPENERS.match(cmd or ""))


# --- Vendor configs ---------------------------------------------------------
# Each entry tells the parser how to convert rows from a given file into the
# tool's row schema. `extra` is a free-form dict for vendor-specific knobs.
VENDORS = {
    "vyos": {
        "file": "VyOS_CLI_Command_Reference.json",
        "out":  "vyos.json",
        "os":   "vyos",
        "vendor": "VyOS",
        "role": "router",
        "default_cat": "System",
        "filter": None,
    },
    "sonic": {
        "file": "SONiC_CLI_Command_Reference.json",
        "out":  "sonic.json",
        "os":   "sonic",
        "vendor": "SONiC",
        "role": "switch",
        "default_cat": "System",
        "filter": looks_like_sonic_cli,
    },
    "nvue": {
        "file": "Cumulus_NVUE_CLI_Command_Reference.json",
        "out":  "nvue.json",
        "os":   "nvue",
        "vendor": "NVIDIA",
        "role": "switch",
        "default_cat": "System",
        "filter": None,
    },
    "panos": {
        "file": "PANOS_CLI_Command_Reference.json",
        "out":  "panos.json",
        "os":   "panos",
        "vendor": "PAN-OS",
        "role": "firewall",
        "default_cat": "Firewall",
        "filter": None,
    },
    "srlinux": {
        "file": "Nokia_SRLinux_CLI_Command_Reference.json",
        "out":  "srlinux.json",
        "os":   "srlinux",
        "vendor": "Nokia",
        "role": "switch",
        "default_cat": "System",
        "filter": None,
    },
    "fortios": {
        "file": "FortiOS_CLI_Command_Reference.json",
        "out":  "fortios.json",
        "os":   "fortios",
        "vendor": "FortiOS",
        "role": "firewall",
        "default_cat": "Firewall",
        "filter": None,
    },
    "routeros": {
        "file": "Mikrotik_RouterOS_CLI_Command_Reference.json",
        "out":  "routeros.json",
        "os":   "routeros",
        "vendor": "Mikrotik",
        "role": "router",
        "default_cat": "System",
        "filter": None,
    },
    "exos": {
        "file": "Extreme_EXOS_CLI_Command_Reference.json",
        "out":  "exos.json",
        "os":   "exos",
        "vendor": "Extreme",
        "role": "switch",
        "default_cat": "System",
        "filter": None,
    },
    "aoscx": {
        "file": "Aruba_AOSCX_CLI_Command_Reference.json",
        "out":  "aoscx.json",
        "os":   "aoscx",
        "vendor": "Aruba",
        "role": "switch",
        "default_cat": "System",
        "filter": None,
    },
    "vrp": {
        "file": "Huawei_VRP_CLI_Command_Reference.json",
        "out":  "vrp.json",
        "os":   "vrp",
        "vendor": "Huawei",
        "role": "router",
        "default_cat": "System",
        "filter": None,
        "strip_prompt": True,
    },
    # Cisco/Juniper gaps merge into the existing OS labels, NOT a new OS.
    "cisco_gaps": {
        "file": "Cisco_Gaps_CLI_Command_Reference.json",
        "out":  "cisco_gaps.json",
        "os":   "ios",
        "vendor": "Cisco",
        "role": "router",
        "default_cat": "System",
        "filter": None,
    },
    "juniper_gaps": {
        "file": "Juniper_Gaps_CLI_Command_Reference.json",
        "out":  "juniper_gaps.json",
        "os":   "junos",
        "vendor": "Juniper",
        "role": "router",
        "default_cat": "System",
        "filter": None,
    },
}


def parse_one(
    key: str,
    cfg: dict,
    docs_dir: pathlib.Path,
    output_dir: pathlib.Path,
) -> int:
    src_path = docs_dir / cfg["file"]
    if not src_path.exists():
        print(f"  ! {key}: source missing → {src_path}", file=sys.stderr)
        return 0
    raw = json.loads(src_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print(f"  ! {key}: expected list, got {type(raw).__name__}", file=sys.stderr)
        return 0

    rows: list[dict] = []
    seen: set[str] = set()
    cats: Counter = Counter()

    for entry in raw:
        cmd_raw = (entry.get("command") or "").strip()
        if not cmd_raw:
            continue
        if cfg["filter"] is not None and not cfg["filter"](cmd_raw):
            continue
        cmd = clean_command(cmd_raw, strip_prompt=cfg.get("strip_prompt", False))
        if not cmd:
            continue
        raw_cat = entry.get("category") or ""
        cat = normalize_category(raw_cat, cmd, cfg["default_cat"])
        title = title_from_command(cmd)
        short_desc = first_sentence(entry.get("description") or "")
        if short_desc:
            short_desc = f"{cat} — {short_desc}"
        elif raw_cat:
            short_desc = f"{cat} · {raw_cat}"
        else:
            short_desc = cat

        # Dedup on normalized command (within this vendor — global dedupe
        # happens later in parse.py).
        dedupe_key = re.sub(r"\s+", " ", cmd).lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        rows.append({
            "os": cfg["os"],
            "role": cfg["role"],
            "vendor": cfg["vendor"],
            "cat": cat,
            "title": title,
            "cmd": cmd,
            "desc": short_desc,
        })
        cats[cat] += 1

    out_path = output_dir / cfg["out"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    top = ", ".join(f"{c}({n})" for c, n in cats.most_common(5))
    print(f"  ✓ {key:14s} {len(rows):5d} rows → {cfg['out']:18s} top: {top}")
    return len(rows)


def main(
    docs_dir: pathlib.Path = DEFAULT_DOCS,
    output_dir: pathlib.Path = DEFAULT_OUTPUT_DIR,
) -> int:
    if not docs_dir.exists():
        print(f"error: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1
    total = 0
    print(f"parse_extras: processing {len(VENDORS)} vendor sources")
    for key, cfg in VENDORS.items():
        total += parse_one(key, cfg, docs_dir, output_dir)
    print(f"\ntotal new rows emitted: {total}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse the wave-2 vendor reference JSONs into the tool's row "
            "schema. Paths default to an overridable docs base (CLI_WORK_DOCS "
            "env var) and repo-relative output so the pipeline is reproducible."
        )
    )
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=DEFAULT_DOCS,
        help="Directory holding the vendor reference JSONs (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write the parsed *.json outputs (default: %(default)s).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.source, args.output))
