#!/usr/bin/env python3
"""
Junos book/reference parser. Handles three file shapes:

1. Day-One book format (encor-style):
   - ## Chapter N: TOPIC
   - ### SECTION HEADING (uppercase / short)
   - ```code blocks```
   - ### Description sentence (sentence-case verb)
   Used by: Beginner's Guide, Exploring the Junos CLI

2. CLI Reference index format:
   - ## category — description (e.g. "## show — Display device information")
   - one big code block listing one command per line
   - no per-command descriptions
   Used by: Junos OS CLI Reference

3. Both files may also have "Operational Mode (`>`)" / "Configuration Mode (`#`)"
   subheadings indicating prompt context.

Output: junos.json with {os, role, vendor, cat, title, cmd, desc}
"""
import re, json, pathlib
from collections import Counter

SRC_DIR = pathlib.Path(__file__).parent / "sources"
OUT = pathlib.Path(__file__).parent / "junos.json"
FILES = [
    "junos-dayone-beginners.md",
    "junos-dayone-cli.md",
    "junos-os-cli-reference.md",
]

# Per-section keyword → category (lowercase substring)
SECTION_RECAT = [
    ("bgp", "BGP"),
    ("ospf", "OSPF"),
    ("isis", "Routing"),
    ("is-is", "Routing"),
    ("mpls", "MPLS"),
    ("rsvp", "MPLS"),
    ("ldp", "MPLS"),
    ("vpls", "MPLS"),
    ("vrf", "MPLS"),
    ("evpn", "BGP"),
    ("vxlan", "VLAN"),
    ("vlan", "VLAN"),
    ("ethernet-switching", "VLAN"),
    ("spanning", "Spanning-Tree"),
    ("rstp", "Spanning-Tree"),
    ("mstp", "Spanning-Tree"),
    ("lacp", "EtherChannel"),
    ("aggregated", "EtherChannel"),
    ("ae0", "EtherChannel"),
    ("link-aggregation", "EtherChannel"),
    ("multicast", "Multicast"),
    ("pim", "Multicast"),
    ("igmp", "Multicast"),
    ("msdp", "Multicast"),
    ("policy-statement", "Routing"),
    ("policy-options", "Routing"),
    ("route-filter", "Routing"),
    ("prefix-list", "Routing"),
    ("routing-options", "Routing"),
    ("static route", "Static"),
    ("routing policies", "Routing"),
    ("firewall filter", "ACL"),
    ("firewall family", "ACL"),
    ("filter-list", "ACL"),
    ("policer", "QoS"),
    ("qos", "QoS"),
    ("class-of-service", "QoS"),
    ("scheduler", "QoS"),
    ("forwarding-class", "QoS"),
    ("security policy", "Firewall"),
    ("security zone", "Firewall"),
    ("security policies", "Firewall"),
    ("security zones", "Firewall"),
    ("security nat", "NAT"),
    ("security ike", "VPN"),
    ("security ipsec", "VPN"),
    ("ipsec", "VPN"),
    ("ike", "VPN"),
    ("nat source", "NAT"),
    ("nat destination", "NAT"),
    ("nat static", "NAT"),
    ("source nat", "NAT"),
    ("destination nat", "NAT"),
    ("static nat", "NAT"),
    ("snmp", "SNMP"),
    ("ntp", "NTP"),
    ("system syslog", "Logging"),
    ("syslog", "Logging"),
    ("logging", "Logging"),
    ("dhcp", "DHCP"),
    ("radius", "AAA"),
    ("tacacs", "AAA"),
    ("authentication", "AAA"),
    ("login class", "AAA"),
    ("login user", "AAA"),
    ("monitor traffic", "Troubleshooting"),
    ("traceroute", "Troubleshooting"),
    ("ping", "Troubleshooting"),
    ("traceoptions", "Troubleshooting"),
    ("show log", "Troubleshooting"),
    ("show route", "Routing"),
    ("show ospf", "OSPF"),
    ("show bgp", "BGP"),
    ("show isis", "Routing"),
    ("show mpls", "MPLS"),
    ("show interface", "Interfaces"),
    ("show interfaces", "Interfaces"),
    ("show chassis", "System"),
    ("show system", "System"),
    ("show security", "Firewall"),
    ("show services", "Troubleshooting"),
    ("show snmp", "SNMP"),
    ("show ntp", "NTP"),
    ("show vlans", "VLAN"),
    ("show ethernet-switching", "VLAN"),
    ("show spanning", "Spanning-Tree"),
    ("show lldp", "Interfaces"),
    ("show arp", "Interfaces"),
    ("show ipv6 neighbors", "Interfaces"),
    ("show dhcp", "DHCP"),
    ("show pim", "Multicast"),
    ("show igmp", "Multicast"),
    ("show route protocol bgp", "BGP"),
    ("show route protocol ospf", "OSPF"),
    ("policies", "Routing"),
    ("firewall filter concepts", "ACL"),
    ("set interfaces", "Interfaces"),
    ("set protocols ospf", "OSPF"),
    ("set protocols bgp", "BGP"),
    ("set protocols rstp", "Spanning-Tree"),
    ("set protocols isis", "Routing"),
    ("set protocols mpls", "MPLS"),
    ("set protocols ldp", "MPLS"),
    ("set protocols rsvp", "MPLS"),
    ("set protocols igmp", "Multicast"),
    ("set protocols pim", "Multicast"),
    ("set firewall", "ACL"),
    ("set vlans", "VLAN"),
    ("set policy-options", "Routing"),
    ("set routing-instances", "MPLS"),
    ("set routing-options", "Routing"),
    ("set security", "Firewall"),
    ("set chassis cluster", "HA"),
    ("set system", "System"),
    ("set snmp", "SNMP"),
    ("user interface", "System"),
    ("operational monitoring", "Troubleshooting"),
    ("routing fundamentals", "Routing"),
    ("routing policies", "Routing"),
    ("troubleshooting policies", "Routing"),
    ("firewall filter", "ACL"),
    ("fundamentals", "System"),
    ("configuration basics", "System"),
]

SKIP_DESC = {"note", "caution", "tip", "warning", "important", "best practice"}
DESC_STARTERS = re.compile(
    r"^(creates?|configures?|configuring|sets?|setting|displays?|displaying|"
    r"enables?|enabling|disables?|disabling|removes?|removing|specifies?|"
    r"moves?|returns?|exits?|adds?|adding|assigns?|permits?|denies?|"
    r"defines?|verif|matches?|matching|forces?|forcing|notes?|caution|"
    r"this\b|to\b|use\b|when\b|if\b|after\b|step|increase|propagat|maps?|"
    r"identif|associat|filters?|advertis|generat|propagates?|clears?|saves?|"
    r"reduces?|lowers?|raises?|loads?|writes?|copies|sends?|forwards?|"
    r"allows?|prevents?|restricts?|limits?|tracks?|checks?|monitors?|tells?|"
    r"resets?|restarts?|reloads?|reboots?|powers?|requires?|let'?s|"
    r"the\b|now\b|here|in this|by default|provides?|introduc|because|since|"
    r"in fact|imagine|notice|but|so\b|that's|there|with|you\b|do\b|using|"
    r"first|next|then|finally|enters?|switches?|navigates?|jumps?|select"
    r")\b",
    re.IGNORECASE,
)

def looks_like_section(h: str) -> bool:
    h = h.strip()
    if not h: return True
    if h.lower() in SKIP_DESC: return False
    letters = [c for c in h if c.isalpha()]
    if not letters: return True
    uc_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if uc_ratio > 0.55: return True
    # words that mark a Day One section header
    for sig in ("CONFIGURING","VERIFYING","TROUBLESHOOTING","COMMANDS","CONFIGURATION","EXAMPLE","OVERVIEW","FUNDAMENTALS","MONITORING","BUILDING","MODES"):
        if sig in h.upper() and uc_ratio > 0.35:
            return True
    return False

def looks_like_description(h: str) -> bool:
    if not h.strip(): return False
    if h.strip().lower() in SKIP_DESC: return False
    if looks_like_section(h): return False
    if DESC_STARTERS.match(h.strip()): return True
    if len(h) < 240 and h[0:1].isupper() and " " in h:
        return True
    return False

def categorize(default_cat: str, section_hdr: str, cmd: str) -> str:
    hay = (section_hdr + " " + cmd).lower()
    for k, c in SECTION_RECAT:
        if k in hay:
            return c
    return default_cat

def role_of(cmd: str) -> str:
    c = cmd.lower()
    if any(k in c for k in ["security zone","security policies","security nat","security ike","security ipsec","chassis cluster","srx"]):
        return "firewall"
    if any(k in c for k in ["ethernet-switching","vlans vlan","spanning-tree","rstp","mstp","set vlans","virtual-chassis","poe"]):
        return "switch"
    return "router"

def is_command_line(line: str) -> bool:
    l = line.strip()
    if not l: return False
    # strip "[edit ...]" annotation prefix
    l = re.sub(r"^\[edit[^\]]*\]\s*", "", l)
    if len(l) > 280: return False
    # exclude lines that are clearly prose
    if re.search(r"[.!?,]\s+\w+", l) and not l.startswith(("set ","show ","run ","delete ","edit ","commit","rollback","load","save","help ","monitor","ping","traceroute","clear","request","restart","configure","activate","deactivate","annotate","insert","copy","protect","rename","replace","wildcard","top","up","exit","end","file ","start ","ssh ","telnet ","test ","scp ")):
        # has sentence punctuation followed by a word → likely prose
        if not re.match(r"^(set|show|run|delete|edit|commit|rollback|load|save|monitor|ping|traceroute|clear|request|restart|configure|help|file|test|start|telnet|ssh|scp|annotate|protect|wildcard|deactivate|activate|insert|copy|rename|replace|top\s|up$|exit$|end$)", l, re.IGNORECASE):
            return False
    if re.match(r"^(set|show|run|delete|edit|commit|rollback|load|save|monitor|ping|traceroute|clear|request|restart|configure|help|file|test|start|telnet|ssh|scp|annotate|protect|wildcard|deactivate|activate|insert|copy|rename|replace|top|up|exit|end|\?|<|>)", l, re.IGNORECASE):
        return True
    # Allow indented children of an "edit"/"set" parent block
    if re.match(r"^(authentication|family|address|description|unit|disable|tunnel|local|remote|set\b)", l, re.IGNORECASE):
        return True
    return False

def parse_dayone(path: pathlib.Path, default_cat: str):
    """encor-style parser: description heading AFTER code block."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    chapter_label = ""
    section_hdr = ""
    mode_prompt = ""  # ">" or "#"
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^## .*Chapter\s+\d+:\s*(.+?)\s*$", line)
        if m:
            chapter_label = m.group(1)
            section_hdr = chapter_label
            i += 1; continue
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            h = m.group(1).strip()
            # detect mode subheaders
            if "operational mode" in h.lower(): mode_prompt = ">"
            elif "configuration mode" in h.lower(): mode_prompt = "#"
            elif looks_like_section(h):
                section_hdr = h
            i += 1; continue
        # bold subheader like "**Operational Mode (`>`)**"
        bm = re.match(r"^\*\*(.+?)\*\*\s*$", line)
        if bm:
            h = bm.group(1).strip()
            if "operational mode" in h.lower(): mode_prompt = ">"
            elif "configuration mode" in h.lower(): mode_prompt = "#"
            i += 1; continue
        if line.strip() == "```" or re.match(r"^```\s*\S*\s*$", line) or re.match(r"^```\s*`\[", line):
            # opening fence (may have trailing edit-marker text)
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            # peek for description
            desc = ""
            j = i
            while j < n and j < i + 6:
                ln = lines[j].strip()
                if not ln: j += 1; continue
                hm = re.match(r"^#{2,4}\s+(.+?)\s*$", ln)
                if hm:
                    cand = hm.group(1).strip()
                    if looks_like_description(cand):
                        desc = cand
                    break
                qm = re.match(r"^>\s+(.+)$", lines[j])  # blockquote description (markdown >)
                if qm:
                    desc = qm.group(1).strip()
                    break
                break
            cleaned = [l for l in block if l.strip() and not l.strip().startswith("`[edit")]
            if not cleaned: continue
            has_indent = any(l.startswith(" ") or l.startswith("\t") for l in cleaned)
            if has_indent or len(cleaned) == 1:
                cmd = "\n".join(cleaned).rstrip()
                if is_command_line(cleaned[0]):
                    cat = categorize(default_cat, section_hdr, cmd)
                    out.append({
                        "os":"junos","role":role_of(cmd),"vendor":"Juniper","cat":cat,
                        "title": cmd.split("\n")[0][:80].strip(),
                        "cmd": cmd,
                        "desc": (desc or section_hdr)[:240],
                    })
            else:
                for cl in cleaned:
                    if not is_command_line(cl): continue
                    cmd = cl.strip()
                    cat = categorize(default_cat, section_hdr, cmd)
                    out.append({
                        "os":"junos","role":role_of(cmd),"vendor":"Juniper","cat":cat,
                        "title": cmd[:80],
                        "cmd": cmd,
                        "desc": (desc or section_hdr)[:240],
                    })
            continue
        i += 1
    return out

def parse_index_ref(path: pathlib.Path):
    """For the CLI Reference: ## category — desc, then one big code block of commands.
    Each non-empty line = one command. No per-command description.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    section_hdr = ""
    default_cat = "System"
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^##\s+(\S+)\s*[—-]+\s*(.+?)\s*$", line)
        if m:
            section_hdr = m.group(1) + " - " + m.group(2)
            verb = m.group(1).lower()
            # default category from verb
            if verb in {"show", "clear", "request", "restart", "monitor", "test", "file", "ssh", "telnet", "start", "help"}:
                default_cat = "System"
            elif verb in {"ping","traceroute"}:
                default_cat = "Troubleshooting"
            elif verb in {"set","delete","deactivate","activate","commit","rollback","load","save","annotate","copy","insert","protect","rename","replace","wildcard"}:
                default_cat = "System"
            i += 1; continue
        m = re.match(r"^###?\s+(.+?)\s*$", line)
        if m:
            h = m.group(1).strip()
            if looks_like_section(h):
                section_hdr = h
            i += 1; continue
        if line.strip().startswith("```"):
            block = []; i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            # Each line = one command. No description.
            for cl in block:
                cmd = cl.strip()
                if not cmd: continue
                # Some lines have an embedded quote artifact: 'show access-security router"show ...'
                if '"' in cmd:
                    for part in cmd.split('"'):
                        part = part.strip()
                        if part and is_command_line(part) and len(part) >= 4:
                            cat = categorize(default_cat, section_hdr, part)
                            out.append({
                                "os":"junos","role":role_of(part),"vendor":"Juniper","cat":cat,
                                "title": part[:80],
                                "cmd": part,
                                "desc": section_hdr[:240],
                            })
                    continue
                if is_command_line(cmd) and len(cmd) >= 3:
                    cat = categorize(default_cat, section_hdr, cmd)
                    out.append({
                        "os":"junos","role":role_of(cmd),"vendor":"Juniper","cat":cat,
                        "title": cmd[:80],
                        "cmd": cmd,
                        "desc": section_hdr[:240],
                    })
            continue
        i += 1
    return out

def main():
    items = []
    # Day One books (encor-style)
    for fname, defcat in [
        ("junos-dayone-beginners.md", "System"),
        ("junos-dayone-cli.md", "System"),
    ]:
        p = SRC_DIR / fname
        if not p.exists(): continue
        new = parse_dayone(p, defcat)
        items.extend(new)
        print(f"  parsed {fname}: {len(new)} entries")
    # CLI Reference index
    p = SRC_DIR / "junos-os-cli-reference.md"
    if p.exists():
        new = parse_index_ref(p)
        items.extend(new)
        print(f"  parsed junos-os-cli-reference.md: {len(new)} entries")
    # dedupe
    seen = set(); deduped = []
    for it in items:
        key = re.sub(r"\s+", " ", it["cmd"]).lower()
        if key in seen: continue
        seen.add(key); deduped.append(it)
    OUT.write_text(json.dumps(deduped, indent=1, ensure_ascii=False))
    print(f"\nwrote {len(deduped)} Junos entries -> {OUT}")
    print("by cat:", dict(Counter(c["cat"] for c in deduped)))
    print("by role:", dict(Counter(c["role"] for c in deduped)))

if __name__ == "__main__":
    main()
