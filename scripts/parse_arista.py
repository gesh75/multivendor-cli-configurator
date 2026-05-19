#!/usr/bin/env python3
"""
Arista EOS User Guide parser.

Format:
    ## Chapter N: TOPIC
    ### Subsection title
    **`command name`** *`mode`*

    ```
    command syntax line(s)
    ```

    > Description starting with the command name...
"""
import re, json, pathlib
from collections import Counter

SRC = pathlib.Path(__file__).parent / "sources" / "arista-eos-user-guide.md"
OUT = pathlib.Path(__file__).parent / "arista.json"

# Chapter → default category
CHAPTER_CAT = {
    1:  "System",        # Overview
    2:  "System",        # Booting the Switch
    3:  "System",        # Initial Configuration and Recovery
    4:  "System",        # Administering the Switch
    5:  "Interfaces",    # 7130 Platform Layer 1
    6:  "NTP",           # Timing Protocols
    7:  "System",        # Switch Environment Control
    8:  "System",        # Upgrades and Downgrades
    9:  "Security",      # Security (multi-topic; refined per command)
    10: "QoS",           # Quality of Service and Traffic Management
    11: "Interfaces",    # Interface Configuration
    12: "Interfaces",    # Layer 1 Configuration
    13: "VLAN",          # Layer 2 Configuration
    14: "Routing",       # Layer 3 Configuration (multi-topic; refined)
    15: "DHCP",          # IP Services (DHCP/DNS/NAT mostly)
    16: "Routing",       # Routing Protocols (multi-topic: BGP/OSPF/etc)
    17: "Multicast",     # Multicast
    18: "VLAN",          # VXLANs
    19: "BGP",           # EVPN (rides on BGP)
    20: "MPLS",          # MPLS
    21: "MPLS",          # RSVP-TE
    22: "Troubleshooting", # Visibility and Monitoring
    23: "Troubleshooting",
    24: "Troubleshooting",
}

# Section / command-keyword overrides (lowercase substring → category)
RECAT = [
    # routing protocols
    ("bgp", "BGP"),
    ("evpn", "BGP"),
    ("ospf", "OSPF"),
    ("ospfv3", "OSPF"),
    ("isis", "Routing"),
    ("is-is", "Routing"),
    ("rip ", "Routing"),
    ("eigrp", "EIGRP"),
    # MPLS family
    ("mpls", "MPLS"),
    ("ldp", "MPLS"),
    ("rsvp", "MPLS"),
    ("traffic-engineering", "MPLS"),
    ("te tunnel", "MPLS"),
    # multicast
    ("pim ", "Multicast"),
    ("igmp", "Multicast"),
    ("msdp", "Multicast"),
    ("multicast", "Multicast"),
    # L2
    ("spanning-tree", "Spanning-Tree"),
    ("rstp", "Spanning-Tree"),
    ("mstp", "Spanning-Tree"),
    ("portfast", "Spanning-Tree"),
    ("bpdu", "Spanning-Tree"),
    ("mlag", "EtherChannel"),
    ("port-channel", "EtherChannel"),
    ("port channel", "EtherChannel"),
    ("channel-group", "EtherChannel"),
    ("lacp", "EtherChannel"),
    ("lag ", "EtherChannel"),
    ("vlan", "VLAN"),
    ("vxlan", "VLAN"),
    ("trunk", "VLAN"),
    ("dot1q", "VLAN"),
    ("storm-control", "VLAN"),
    # interfaces
    ("interface ethernet", "Interfaces"),
    ("interface port-channel", "Interfaces"),
    ("interface loopback", "Interfaces"),
    ("interface management", "Interfaces"),
    ("interface vlan", "Interfaces"),
    ("ip address", "Interfaces"),
    ("ipv6 address", "Interfaces"),
    ("mtu", "Interfaces"),
    ("speed ", "Interfaces"),
    ("duplex ", "Interfaces"),
    ("link-flap", "Interfaces"),
    # IP services
    ("dhcp", "DHCP"),
    ("dns", "System"),
    ("nat", "NAT"),
    ("ntp", "NTP"),
    ("snmp", "SNMP"),
    ("sflow", "Troubleshooting"),
    ("netflow", "Troubleshooting"),
    ("syslog", "Logging"),
    ("logging", "Logging"),
    # AAA
    ("aaa", "AAA"),
    ("tacacs", "AAA"),
    ("radius", "AAA"),
    ("authentication", "AAA"),
    ("role ", "AAA"),
    ("username", "AAA"),
    # ACL/Security
    ("access-list", "ACL"),
    ("access-group", "ACL"),
    ("ip access", "ACL"),
    ("mac access", "ACL"),
    ("ipv6 access", "ACL"),
    ("control-plane", "Security"),
    ("dhcp snooping", "Security"),
    ("arp inspection", "Security"),
    ("urpf", "Security"),
    ("port-security", "Security"),
    ("storm control", "VLAN"),
    # HA / FHRP
    ("vrrp", "HA"),
    ("varp", "HA"),
    ("ip virtual-router", "HA"),
    # routing
    ("ip route", "Static"),
    ("ipv6 route", "Static"),
    ("static route", "Static"),
    ("route-map", "Routing"),
    ("prefix-list", "Routing"),
    ("ip prefix-list", "Routing"),
    # diagnostics / monitoring
    ("show ", "System"),  # generic show fallback (overridden by per-protocol matches above when relevant)
    ("debug ", "Troubleshooting"),
    ("monitor", "Troubleshooting"),
    ("ping ", "Troubleshooting"),
    ("traceroute", "Troubleshooting"),
    ("tcpdump", "Troubleshooting"),
    ("ethanalyzer", "Troubleshooting"),
    ("packet-capture", "Troubleshooting"),
    ("event-monitor", "Troubleshooting"),
    ("event-handler", "Troubleshooting"),
    ("event handler", "Troubleshooting"),
    ("schedule ", "System"),
    # cluster / chassis
    ("chassis", "System"),
    ("environment", "System"),
    ("power", "System"),
    ("ztp", "System"),
    ("aboot", "System"),
    ("reload", "System"),
    ("boot", "System"),
    ("clock", "NTP"),
    ("ptp", "NTP"),
    # QoS
    ("qos", "QoS"),
    ("class-map", "QoS"),
    ("policy-map", "QoS"),
    ("service-policy", "QoS"),
    ("policer", "QoS"),
    ("dscp", "QoS"),
    ("cos ", "QoS"),
    ("queue", "QoS"),
]

def categorize(default_cat: str, title: str, cmd: str, section_hdr: str) -> str:
    hay = (title + " " + cmd + " " + section_hdr).lower()
    # First, prefer exact protocol match (BGP/OSPF/etc)
    for k, c in RECAT:
        if k == "show " or k == "debug ":  # generic - skip on first pass
            continue
        if k in hay:
            return c
    # Then fall back to generic show/debug
    for k, c in RECAT:
        if k in ("show ", "debug ") and k in hay:
            return c
    return default_cat

def role_of(title: str, cmd: str, section_hdr: str) -> str:
    hay = (title + " " + cmd + " " + section_hdr).lower()
    # Arista is primarily switching, but EOS does L3, VXLAN, EVPN, MPLS — keep mostly switch/router split
    if any(k in hay for k in ["spanning-tree","vlan","trunk","mlag","port-channel","switchport","storm-control","stp","vxlan"]):
        return "switch"
    if any(k in hay for k in ["zone","security policy","firewall policy"]):
        return "firewall"
    # routing/L3 protocols → router
    if any(k in hay for k in ["ospf","bgp","isis","mpls","ldp","rsvp","router","redistribute","ip route","ipv6 route"]):
        return "router"
    # everything else (system, AAA, NTP, SNMP, etc) → switch (Arista default)
    return "switch"

# Title-line regex: `**`command name`** *`mode`*` (mode optional)
TITLE_RE = re.compile(r"^\*\*`([^`]+)`\*\*\s*(?:\*`([^`]+)`\*)?\s*$")

def parse():
    text = SRC.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    chapter = 0
    section_hdr = ""
    pending_title = None  # (name, mode)
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^##\s+Chapter\s+(\d+):\s*(.+?)\s*$", line)
        if m:
            chapter = int(m.group(1))
            section_hdr = m.group(2).strip()
            pending_title = None
            i += 1; continue
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            section_hdr = m.group(1).strip()
            pending_title = None
            i += 1; continue
        # Bold-backtick command title line
        m = TITLE_RE.match(line)
        if m:
            pending_title = (m.group(1).strip(), (m.group(2) or "").strip())
            i += 1; continue
        # Fenced code block
        if line.strip().startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            # Look for description (markdown blockquote starting with >)
            desc = ""
            j = i
            while j < n and j < i + 6:
                ln = lines[j].strip()
                if not ln: j += 1; continue
                qm = re.match(r"^>\s*(.+?)\s*$", lines[j])
                if qm:
                    # gather contiguous blockquote lines
                    parts = [qm.group(1)]
                    k = j + 1
                    while k < n:
                        qq = re.match(r"^>\s*(.+?)\s*$", lines[k])
                        if qq:
                            parts.append(qq.group(1)); k += 1
                        else:
                            break
                    desc = " ".join(parts).strip()
                    break
                else:
                    break
            # Process block
            cleaned = [l for l in block if l.strip()]
            if not cleaned:
                pending_title = None
                continue
            cmd = "\n".join(cleaned).rstrip()
            # Skip blocks that are clearly output samples (start with prompt/login/status text)
            first = cleaned[0].strip()
            if re.match(r"^(Active|Inactive|Standby|Up|Down|Login:|Username:|Password:|switch>|switch#|switch\(|--More--|VERSION|Last login|MAC)", first):
                pending_title = None
                continue
            if not pending_title:
                # no preceding title — try to use first line as title (and skip if it looks like output)
                title = first[:80]
                pending_title = (title, "")
            title, mode = pending_title
            default = CHAPTER_CAT.get(chapter, "System")
            cat = categorize(default, title, cmd, section_hdr)
            out.append({
                "os":"eos","role":role_of(title, cmd, section_hdr),"vendor":"Arista","cat":cat,
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
    # dedupe
    seen = set(); deduped = []
    for it in items:
        key = re.sub(r"\s+", " ", it["cmd"]).lower()
        if key in seen: continue
        seen.add(key); deduped.append(it)
    OUT.write_text(json.dumps(deduped, indent=1, ensure_ascii=False))
    print(f"wrote {len(deduped)} Arista entries -> {OUT}")
    print("by cat:", dict(Counter(c["cat"] for c in deduped)))
    print("by role:", dict(Counter(c["role"] for c in deduped)))

if __name__ == "__main__":
    main()
