#!/usr/bin/env python3
"""
Cisco ASA 9.24 + Cisco NX-OS VXLAN/BGP-EVPN reference parsers.
Same bold-backtick fenced-code format as the Arista User Guide parser, but
configured per-file (vendor/os/role). Title preferred from ### section heading
because the **`...`** title line is often noisy (Password:, status messages).
"""
import re, json, pathlib, sys
from collections import Counter

HERE = pathlib.Path(__file__).parent

# (filename, vendor, os, default_role, default_cat, source_label)
SOURCES = [
    {
        "src":   HERE / "sources" / "cisco-asa-924-reference.md",
        "out":   HERE / "cisco_asa.json",
        "vendor":"Cisco", "os":"asa", "role":"firewall", "default_cat":"Firewall",
        "label":"ASA 9.24",
    },
    {
        "src":   HERE / "sources" / "cisco-nxos-vxlan-evpn-reference.md",
        "out":   HERE / "cisco_nxos_vxlan.json",
        "vendor":"Cisco", "os":"nxos", "role":"switch", "default_cat":"BGP",
        "label":"NX-OS VXLAN BGP EVPN",
        # Nexus is fabric infrastructure — never a firewall.
        "allowed_roles": {"switch", "router"},
    },
]

TITLE_RE = re.compile(r"^\*\*`([^`]+)`\*\*\s*$")

# Keyword-based category override (longest/most specific match wins).
# Ordered so protocol-specific terms beat generic "show ".
RECAT = [
    ("bgp evpn", "BGP"), ("evpn", "BGP"),
    ("vxlan", "VLAN"), ("vni ", "VLAN"), ("nve ", "VLAN"),
    ("bgp", "BGP"),
    ("ospfv3", "OSPF"), ("ospf", "OSPF"),
    ("isis", "Routing"), ("is-is", "Routing"),
    ("eigrp", "EIGRP"),
    ("rip ", "Routing"),
    ("mpls", "MPLS"), ("ldp", "MPLS"),
    ("pim ", "Multicast"), ("igmp", "Multicast"), ("multicast", "Multicast"),
    ("spanning-tree", "Spanning-Tree"), ("stp ", "Spanning-Tree"),
    ("port-channel", "EtherChannel"), ("etherchannel", "EtherChannel"),
    ("lacp", "EtherChannel"),
    ("vlan", "VLAN"), ("trunk", "VLAN"),
    ("vrrp", "HA"), ("hsrp", "HA"), ("failover", "HA"), ("cluster", "HA"),
    ("ipsec", "VPN"), ("ike", "VPN"), ("crypto", "VPN"),
    ("tunnel-group", "VPN"), ("anyconnect", "VPN"), ("webvpn", "VPN"),
    ("ssl ", "VPN"),
    ("nat ", "NAT"), ("nat\n", "NAT"),
    ("access-list", "ACL"), ("ip access", "ACL"), ("access-group", "ACL"),
    ("object-group", "ACL"), ("policy-map", "QoS"), ("class-map", "QoS"),
    ("service-policy", "QoS"), ("qos", "QoS"),
    ("aaa", "AAA"), ("tacacs", "AAA"), ("radius", "AAA"),
    ("authentication", "AAA"), ("username", "AAA"),
    ("dhcp", "DHCP"),
    ("snmp", "SNMP"),
    ("syslog", "Logging"), ("logging", "Logging"),
    ("ntp", "NTP"), ("clock ", "NTP"),
    ("interface ", "Interfaces"), ("ip address", "Interfaces"),
    ("ipv6 address", "Interfaces"), ("mtu ", "Interfaces"),
    ("loopback", "Interfaces"),
    ("ip route", "Static"), ("ipv6 route", "Static"), ("static route", "Static"),
    ("route-map", "Routing"), ("prefix-list", "Routing"),
    ("zone", "Security"), ("dhcp snooping", "Security"),
    ("arp inspection", "Security"), ("threat-detection", "Security"),
    ("firewall", "Firewall"),
    ("show ", "System"), ("debug ", "Troubleshooting"),
    ("ping ", "Troubleshooting"), ("traceroute", "Troubleshooting"),
    ("packet-tracer", "Troubleshooting"), ("capture ", "Troubleshooting"),
    ("write ", "System"), ("reload", "System"), ("hostname", "System"),
    ("license", "System"), ("boot ", "System"),
]

def categorize(default_cat, title, cmd, section_hdr, chapter_title):
    hay = " ".join([title, cmd, section_hdr, chapter_title]).lower()
    # First pass: protocol-specific terms (skip generic show/debug)
    for k, c in RECAT:
        if k in ("show ", "debug "):
            continue
        if k in hay:
            return c
    # Then generic show/debug fallback
    for k, c in RECAT:
        if k in ("show ", "debug ") and k in hay:
            return c
    return default_cat

FW_PATTERNS = [
    r"\baccess-list\b", r"\bnat\b", r"\bipsec\b", r"\bike\b",
    r"\btunnel-group\b", r"\banyconnect\b", r"\bwebvpn\b",
    r"\bfirewall\b", r"\bobject-group\b", r"\bcrypto\s+map\b",
    # \bvpn\b but NOT inside "EVPN" — use a real boundary
    r"(?<![a-z])vpn(?![a-z])",
]
SW_PATTERNS = [r"\bspanning-tree\b", r"\bswitchport\b", r"\bvlan\b",
               r"\btrunk\b", r"\bport-channel\b", r"\bmlag\b",
               r"\bvxlan\b", r"\bnve\b", r"\bvni\b"]
RT_PATTERNS = [r"\bospf\b", r"\bbgp\b", r"\bisis\b", r"\bis-is\b",
               r"\beigrp\b", r"\bmpls\b", r"\brouter\b",
               r"\bredistribute\b", r"\bip route\b", r"\bipv6 route\b",
               r"\bmulticast\b", r"\bevpn\b"]

def _any_re(patterns, text):
    return any(re.search(p, text) for p in patterns)

def role_of(default_role, title, cmd, section_hdr, chapter_title, allowed_roles=None):
    hay = " ".join([title, cmd, section_hdr, chapter_title]).lower()
    allowed = allowed_roles or {"firewall","switch","router"}
    if "firewall" in allowed and _any_re(FW_PATTERNS, hay):
        return "firewall"
    if "switch" in allowed and _any_re(SW_PATTERNS, hay):
        return "switch"
    if "router" in allowed and _any_re(RT_PATTERNS, hay):
        return "router"
    return default_role

# Drop blocks that are obviously sample output / banners
OUTPUT_PROMPT = re.compile(
    r"^(?:Active|Inactive|Standby|Up|Down|Login:|Username:|Password:|--More--|"
    r"VERSION|Last\s+login|MAC|\d+:\d+:\d+|ciscoasa[#>]|switch[#>]|"
    r"Building\s+config|Cryptochecksum|Tunnel|Step\s+\d|See\s+the|Refer\s+to)",
    re.IGNORECASE,
)

def parse_one(cfg):
    text = cfg["src"].read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    chapter_title = ""
    section_hdr = ""
    pending_title = None
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^##\s+Chapter\s+\d+:\s*(.+?)\s*$", line)
        if m:
            chapter_title = m.group(1).strip()
            section_hdr = chapter_title
            pending_title = None
            i += 1; continue
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            section_hdr = m.group(1).strip()
            i += 1; continue
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            section_hdr = m.group(1).strip()
            # Use the section heading as the next pending title (preferred over noisy **`Password:`** lines)
            pending_title = (section_hdr, "")
            i += 1; continue
        m = TITLE_RE.match(line)
        if m:
            t = m.group(1).strip()
            # Only override section-derived title if the bold-backtick line
            # looks like a real command (contains a verb / config keyword),
            # not a chunk of prose or a status string.
            looks_like_cmd = bool(
                re.match(r"^(show|set|conf|copy|clear|debug|no\s+|ip\s+|ipv6\s+|"
                         r"router|interface|hostname|access-list|crypto|nat|"
                         r"object|policy-map|class-map|service-policy|snmp|"
                         r"logging|aaa|username|tunnel-group|webvpn|vlan|"
                         r"switchport|spanning-tree|port-channel|channel-group|"
                         r"vxlan|nve|evpn|bgp|ospf|eigrp|isis|ntp|dhcp|"
                         r"failover|cluster|context|mode|boot|reload|write|"
                         r"telnet|ssh|http|ftp|tftp|exec|config|enable)\b",
                         t, re.IGNORECASE)
            )
            if pending_title is None or looks_like_cmd:
                pending_title = (t, "")
            i += 1; continue
        if line.strip().startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            # Pull blockquote description (markdown >)
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
            # Drop obvious output samples (single-line prompts/status banners)
            if len(cleaned) <= 2 and OUTPUT_PROMPT.match(first):
                pending_title = None; continue
            title = (pending_title[0] if pending_title else first)[:80]
            cat = categorize(cfg["default_cat"], title, cmd, section_hdr, chapter_title)
            role = role_of(cfg["role"], title, cmd, section_hdr, chapter_title,
                           allowed_roles=cfg.get("allowed_roles"))
            out.append({
                "os": cfg["os"], "role": role, "vendor": cfg["vendor"], "cat": cat,
                "title": title,
                "cmd": cmd,
                "desc": (desc or section_hdr or chapter_title)[:280],
            })
            pending_title = None
            continue
        i += 1
    return out

def write_dedup(items, out_path, label):
    seen = set(); deduped = []
    for it in items:
        key = re.sub(r"\s+", " ", it["cmd"]).lower()
        if key in seen: continue
        seen.add(key); deduped.append(it)
    out_path.write_text(json.dumps(deduped, indent=1, ensure_ascii=False))
    print(f"[{label}] wrote {len(deduped)} entries -> {out_path}")
    print(f"  by cat: {dict(Counter(c['cat'] for c in deduped))}")
    print(f"  by role: {dict(Counter(c['role'] for c in deduped))}")

def main():
    for cfg in SOURCES:
        if not cfg["src"].exists():
            print(f"!! missing source: {cfg['src']}", file=sys.stderr)
            continue
        items = parse_one(cfg)
        write_dedup(items, cfg["out"], cfg["label"])

if __name__ == "__main__":
    main()
