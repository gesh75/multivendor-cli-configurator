#!/usr/bin/env python3
"""
Parse community-sourced Cisco markdown cheatsheets into commands.json.
Schema: { os, role, vendor, cat, title, cmd, desc }
"""
import json, re, hashlib, pathlib, sys

SRC_DIR = pathlib.Path(__file__).parent / "sources"
OUT_FILE = pathlib.Path(__file__).parent.parent / "commands.json"

# Heuristic category map. Order matters: first match wins.
CAT_KEYWORDS = [
    ("BGP",         ["bgp", "ebgp", "ibgp", "as-path", "route-map.*bgp", "neighbor.*remote-as"]),
    ("OSPF",        ["ospf", "ospfv3", "router-id", "lsa", "designated router", "passive-interface"]),
    ("EIGRP",       ["eigrp", "feasible", "successor"]),
    ("Static",      ["static route", "ip route ", "ipv6 route", "default route", "default gateway"]),
    ("VLAN",        ["vlan", "trunk", "access vlan", "voice vlan", "dot1q", "vtp ", "switchport"]),
    ("Spanning-Tree", ["spanning-tree", "stp ", "rapid-pvst", "mst ", "portfast", "bpduguard", "rstp"]),
    ("EtherChannel",["etherchannel", "port-channel", "channel-group", "lacp", "pagp"]),
    ("Interfaces",  ["interface ", "no shutdown", "shutdown", "description", "mtu ", "speed ", "duplex", "loopback"]),
    ("NAT",         ["nat ", "pat ", "ip nat ", "overload", "xlate"]),
    ("ACL",         ["access-list", "access-group", "permit ", "deny ", "ip access-list"]),
    ("DHCP",        ["dhcp", "ip helper", "dhcp pool"]),
    ("HA",          ["hsrp", "vrrp", "glbp", "standby ", "failover"]),
    ("VPN",         ["crypto ", "ipsec", "ike", "isakmp", "vpn", "tunnel"]),
    ("AAA",         ["aaa ", "tacacs", "radius", "authentication", "authorization"]),
    ("SNMP",        ["snmp-server", "snmp "]),
    ("NTP",         ["ntp ", "clock"]),
    ("Logging",     ["logging ", "syslog"]),
    ("QoS",         ["class-map", "policy-map", "service-policy", "qos", "dscp", "cos "]),
    ("Multicast",   ["multicast", "igmp", "pim ", "msdp"]),
    ("MPLS",        ["mpls", "ldp", "vrf ", "rd ", "route-target"]),
    ("Security",    ["port-security", "dhcp snooping", "arp inspection", "storm-control"]),
    ("Troubleshooting", ["ping ", "traceroute", "debug ", "show tech", "show log", "monitor capture"]),
    ("Routing",     ["show ip route", "show route", "ip routing"]),
    ("System",      ["hostname", "show version", "show running", "copy running", "reload", "show inventory", "show env", "show cpu", "show mem"]),
]

# OS inference heuristic
def detect_os(cmd: str, hint: str = "") -> str:
    c = (cmd + " " + hint).lower()
    if any(k in c for k in ["set interfaces", "set protocols", "set system", "show configuration", "commit"]):
        return "junos"
    if "no switchport" in c and "/" in c and "ip address" in c:
        return "nxos"  # NX-OS uses CIDR on physical, requires no switchport
    if "feature " in c.split("\n")[0] if c else False:
        return "nxos"
    if "nameif" in c or "security-level" in c:
        return "asa"
    if "configure session" in c or "ip virtual-router" in c:
        return "eos"
    return "ios"

# Role inference
def detect_role(cmd: str, sec_path: str) -> str:
    c = (cmd + " " + sec_path).lower()
    if any(k in c for k in ["zone", "policy.*permit", "nameif", "security-level", "vpn", "ipsec", "ike", "failover"]):
        return "firewall"
    if any(k in c for k in ["vlan ", "switchport", "spanning-tree", "trunk", "vtp ", "port-channel"]):
        return "switch"
    return "router"

# Vendor inference (we're mostly Cisco from these sources, but be safe)
def detect_vendor(cmd: str, source_name: str) -> str:
    c = cmd.lower()
    if "set " in c and any(k in c for k in ["interfaces ge-", "protocols ospf", "routing-options"]):
        return "Juniper"
    if "configure session" in c or "ip virtual-router" in c:
        return "Arista"
    return "Cisco"

def categorize(cmd: str, section: str) -> str:
    text = (cmd + " " + section).lower()
    for cat, keys in CAT_KEYWORDS:
        for k in keys:
            if re.search(k, text):
                return cat
    return "System"

def clean(s: str) -> str:
    # strip prompts, leading "$ " or "# " from shell, leading bullets
    s = re.sub(r"^[\s]*[$#>][\s]?", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.MULTILINE)
    return s.rstrip()

def short_title(cmd: str, fallback: str) -> str:
    first = cmd.strip().split("\n")[0]
    first = re.sub(r"\s+#.*$", "", first)  # strip inline comment
    if len(first) > 70: first = first[:67] + "..."
    return first or fallback or "command"

# headings: track h2/h3/h4/h5 path
def parse_markdown(path: pathlib.Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    headings = {}  # level -> title
    items = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if m:
            lvl = len(m.group(1))
            title = re.sub(r"[`*_:🌐📘🚀📑]", "", m.group(2)).strip()
            # collapse emoji/special chars
            title = re.sub(r"[^\w\s\-\(\)\/.,]", "", title).strip()
            headings[lvl] = title
            # clear deeper levels
            for k in list(headings):
                if k > lvl: del headings[k]
            i += 1
            continue
        # detect fenced code blocks
        m2 = re.match(r"^```(\w*)\s*$", line)
        if m2:
            lang = m2.group(1).lower()
            block = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            # Only keep blocks that look like config (filter out python/bash unless small)
            if lang in {"python", "json", "yaml", "javascript", "js", "html"}:
                continue
            code = clean("\n".join(block)).strip()
            if not code: continue
            if len(code) > 1500: continue  # skip huge dumps
            # Split very long blocks into sub-commands by blank lines or by ! separators if it's clearly multiple
            chunks = [c.strip() for c in re.split(r"\n\s*\n", code) if c.strip()]
            for chunk in chunks:
                # Skip pure prose blocks
                if not any(re.search(r"\b(show|interface|ip|router|vlan|set|access-list|hostname|configure|switchport|spanning-tree|crypto|snmp|logging|ntp|aaa|debug|enable|copy|write|reload|monitor|clear|ping|traceroute)\b", l, re.I) for l in chunk.split("\n")):
                    continue
                section = " > ".join(headings.get(k, "") for k in sorted(headings) if headings.get(k))
                items.append({
                    "src": path.name,
                    "section": section,
                    "cmd": chunk,
                })
            continue
        # Markdown table: detect "Command|Description" or "Commands|...|" header followed by separator
        if "|" in line and i+1 < n and re.match(r"^\s*[-:\s|]+\s*$", lines[i+1]) and any(h in line.lower() for h in ["command", "syntax", "snippet"]):
            i += 2  # skip header + separator
            while i < n and "|" in lines[i] and lines[i].strip():
                row = lines[i].split("|")
                if len(row) >= 2:
                    raw_cmd = row[0].strip()
                    desc = row[1].strip() if len(row) >= 2 else ""
                    # strip backticks/prompts
                    cmd = re.sub(r"^`+|`+$", "", raw_cmd)
                    cmd = re.sub(r"^[Rr]\d+(\(config[^)]*\))?[#>]\s*", "", cmd)
                    cmd = re.sub(r"^[Ss]witch(\(config[^)]*\))?[#>]\s*", "", cmd)
                    cmd = re.sub(r"^[Hh]ost(\(config[^)]*\))?[#>]\s*", "", cmd)
                    cmd = cmd.strip()
                    desc = re.sub(r"`([^`]+)`", r"\1", desc)  # remove inline backticks in desc
                    if cmd and len(cmd) < 250 and re.search(r"\b(show|interface|ip|ipv6|router|vlan|set|access-list|hostname|configure|switchport|spanning-tree|crypto|snmp|logging|ntp|aaa|debug|enable|copy|write|reload|monitor|clear|ping|traceroute|no |service|line|standby|vrrp|hsrp)\b", cmd, re.I):
                        section = " > ".join(headings.get(k, "") for k in sorted(headings) if headings.get(k))
                        items.append({"src": path.name, "section": section + " | " + (desc or ""), "cmd": cmd})
                i += 1
            continue
        # Blockquote with inline backticks: > ``R1(config)#ip route ...``
        bq = re.match(r"^>\s*`{1,2}([^`]+)`{1,2}\s*$", line)
        if bq:
            raw_cmd = bq.group(1).strip()
            cmd = re.sub(r"^[Rr]\d+(\(config[^)]*\))?[#>]\s*", "", raw_cmd)
            cmd = re.sub(r"^[Ss]witch(\(config[^)]*\))?[#>]\s*", "", cmd)
            cmd = cmd.strip()
            if cmd and re.search(r"\b(show|interface|ip|ipv6|router|vlan|set|access-list|hostname|configure|switchport|spanning-tree|crypto|snmp|logging|ntp|aaa|debug|enable|copy|write|reload|monitor|clear|ping|traceroute|no )\b", cmd, re.I):
                section = " > ".join(headings.get(k, "") for k in sorted(headings) if headings.get(k))
                items.append({"src": path.name, "section": section, "cmd": cmd})
        i += 1
    return items

def main():
    raw = []
    for md in sorted(SRC_DIR.glob("*.md")):
        try:
            items = parse_markdown(md)
            raw.extend(items)
            print(f"  parsed {md.name}: {len(items)} blocks", file=sys.stderr)
        except Exception as e:
            print(f"  ! {md.name}: {e}", file=sys.stderr)

    # Convert to schema
    cmds = []
    seen = set()
    for it in raw:
        cmd = it["cmd"]
        sec = it["section"]
        # dedup key on normalized command
        key = re.sub(r"\s+", " ", cmd).lower()
        if key in seen: continue
        seen.add(key)
        os = detect_os(cmd, sec)
        role = detect_role(cmd, sec)
        vendor = detect_vendor(cmd, it["src"])
        cat = categorize(cmd, sec)
        title = short_title(cmd, sec.split(" > ")[-1] if sec else "")
        cmds.append({
            "os": os, "role": role, "vendor": vendor, "cat": cat,
            "title": title, "cmd": cmd,
            "desc": sec or "",
        })

    # Merge with the hand-curated dataset extracted from cheatsheet.html
    seed_path = pathlib.Path(__file__).parent / "seed.json"
    if seed_path.exists():
        seed = json.loads(seed_path.read_text())
        for s in seed:
            key = re.sub(r"\s+", " ", s["cmd"]).lower()
            if key not in seen:
                seen.add(key); cmds.append(s)
        print(f"  merged seed: {len(seed)} curated entries", file=sys.stderr)

    OUT_FILE.write_text(json.dumps(cmds, indent=1, ensure_ascii=False))
    print(f"\nwrote {len(cmds)} commands -> {OUT_FILE}")
    # quick stats
    from collections import Counter
    print("\nBy OS:", dict(Counter(c["os"] for c in cmds)))
    print("By role:", dict(Counter(c["role"] for c in cmds)))
    print("By cat:", dict(Counter(c["cat"] for c in cmds)))

if __name__ == "__main__":
    main()
