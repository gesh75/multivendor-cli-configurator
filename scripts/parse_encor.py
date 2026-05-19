#!/usr/bin/env python3
"""
Dedicated parser for the ENCOR/ENARSI Cisco Press portable command guide.
The book's format puts the description AFTER its code block, as a ### heading.

Pattern:
    ## Chapter N: TOPIC
    ### SECTION HEADING (all-caps)
    ```
    command(s)
    ```
    ### Description sentence (sentence-case verb start)

We:
  - Track current chapter → derives default category
  - Walk blocks; for each fenced block, peek ahead for the next ### heading
    that "looks like a description" (sentence-case, not ALL CAPS, not "Note"/"Caution")
  - Re-categorize per section keyword when chapter is multi-topic (Ch 8, 10, 11)
"""
import re, json, pathlib

SRC = pathlib.Path(__file__).parent / "sources" / "encor-enarsi-cisco-press.md"
OUT = pathlib.Path(__file__).parent / "encor.json"

CHAPTER_CAT = {
    1:  "VLAN",
    2:  "Spanning-Tree",
    3:  "Routing",
    4:  "EIGRP",
    5:  "OSPF",
    6:  "Routing",       # Redistribution & Path Control
    7:  "BGP",
    8:  "System",        # IP Services - multi-topic, refined per section
    9:  "System",        # Device Management
    10: "Security",      # Infrastructure Security - multi-topic
    11: "Troubleshooting", # Network Assurance - multi-topic
    12: "Wireless",
    13: "VPN",           # Overlay tunnels & VRF
}

# Section-keyword overrides (lowercase substring → category)
SECTION_RECAT = [
    ("vlan", "VLAN"),
    ("trunk", "VLAN"),
    ("vtp", "VLAN"),
    ("etherchannel", "EtherChannel"),
    ("port-channel", "EtherChannel"),
    ("spanning", "Spanning-Tree"),
    ("portfast", "Spanning-Tree"),
    ("bpdu", "Spanning-Tree"),
    ("udld", "Spanning-Tree"),
    ("errdisable", "Spanning-Tree"),
    ("loop guard", "Spanning-Tree"),
    ("root guard", "Spanning-Tree"),
    ("inter-vlan", "Routing"),
    ("router-on-a-stick", "Routing"),
    ("eigrp", "EIGRP"),
    ("ospf", "OSPF"),
    ("redistrib", "Routing"),
    ("policy-based rout", "Routing"),
    ("path control", "Routing"),
    ("ip sla", "Troubleshooting"),
    ("bgp", "BGP"),
    ("route reflect", "BGP"),
    ("nat", "NAT"),
    ("pat", "NAT"),
    ("hsrp", "HA"),
    ("vrrp", "HA"),
    ("glbp", "HA"),
    ("dhcp", "DHCP"),
    ("syslog", "Logging"),
    ("logging", "Logging"),
    ("snmp", "SNMP"),
    ("netflow", "Troubleshooting"),
    ("span", "Troubleshooting"),
    ("erspan", "Troubleshooting"),
    ("ntp", "NTP"),
    ("clock", "NTP"),
    ("eem", "Troubleshooting"),
    ("aaa", "AAA"),
    ("radius", "AAA"),
    ("tacacs", "AAA"),
    ("password", "AAA"),
    ("ssh", "System"),
    ("acl", "ACL"),
    ("access list", "ACL"),
    ("access-list", "ACL"),
    ("copp", "Security"),
    ("control plane", "Security"),
    ("urpf", "Security"),
    ("unicast reverse", "Security"),
    ("ping", "Troubleshooting"),
    ("traceroute", "Troubleshooting"),
    ("debug", "Troubleshooting"),
    ("gre", "VPN"),
    ("dmvpn", "VPN"),
    ("ipsec", "VPN"),
    ("isakmp", "VPN"),
    ("vrf", "MPLS"),
    ("tunnel", "VPN"),
    ("wireless", "Wireless"),
    ("wlan", "Wireless"),
    ("dot11", "Wireless"),
    ("interface", "Interfaces"),
    ("static route", "Static"),
    ("default route", "Static"),
    ("ip route", "Static"),
]

# A heading is a "description" if it starts with one of these verbs (sentence case)
DESC_STARTERS = re.compile(
    r"^(creates?|configures?|configuring|sets?|setting|setting up|"
    r"displays?|displaying|enables?|enabling|disables?|disabling|removes?|removing|"
    r"specifies?|moves?|returns?|exits?|adds?|adding|assigns?|permits?|denies?|"
    r"defines?|verif|matches?|matching|forces?|forcing|notes?|caution|the\b|"
    r"this\b|to\b|use\b|when\b|if\b|after\b|step|increase|propagat|maps?|mapping|"
    r"identif|associat|filters?|advertis|generat|propagates?|clears?|saves?|"
    r"reduces?|lowers?|raises?|loads?|writes?|copies|copy|sends?|forwards?|"
    r"allows?|prevents?|restricts?|limits?|tracks?|checks?|monitors?|tells?|"
    r"resets?|restarts?|reloads?|reboots?|powers?|encrypts?|hashes?|signs?|"
    r"requires?|optionally|important|warning|tip|best practice|globally|"
    r"locally|automatically|manually|either|each|all|same|the\s|by default|"
    r"another way|provides?|introduc|because|since|note that|caution that)\b",
    re.IGNORECASE,
)
SKIP_DESC = {"note", "caution", "tip", "warning", "important", "best practice"}
def looks_like_section(h: str) -> bool:
    h = h.strip()
    if not h: return True
    if h.lower() in SKIP_DESC: return False  # not section, but also not description
    # If mostly uppercase → section heading
    letters = [c for c in h if c.isalpha()]
    if not letters: return True
    uc_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if uc_ratio > 0.6: return True
    # Common section signal words
    for w in ("CONFIGURATION","CONFIGURING","VERIFYING","TROUBLESHOOTING","EXAMPLE","COMMANDS","ENABLING","DISABLING","ESTABLISHING","FOR"):
        if w in h.upper() and h.upper().count(w) and uc_ratio > 0.4:
            return True
    return False
def looks_like_description(h: str) -> bool:
    if not h.strip(): return False
    if h.strip().lower() in SKIP_DESC: return False
    if looks_like_section(h): return False
    if DESC_STARTERS.match(h.strip()): return True
    # Fallback: sentence-case, < 200 chars, contains a verb-ish
    if len(h) < 200 and h[0].isupper() and " " in h:
        return True
    return False

def categorize(default_cat: str, section_hdr: str, cmd: str) -> str:
    hay = (section_hdr + " " + cmd).lower()
    for key, cat in SECTION_RECAT:
        if key in hay:
            return cat
    return default_cat

def role_of(cmd: str) -> str:
    c = cmd.lower()
    if "switchport" in c or "vlan " in c or "spanning-tree" in c or "vtp " in c or "etherchannel" in c:
        return "switch"
    if "security zone" in c or "nameif" in c or "ipsec" in c or "isakmp" in c or "dmvpn" in c or "nhrp" in c:
        return "firewall"
    return "router"

def looks_like_command(line: str) -> bool:
    l = line.strip()
    if not l: return False
    if len(l) > 250: return False
    # Skip prompts, output text
    if re.match(r"^[\w@-]+(\(config[^)]*\))?[#>%]\s*$", l): return False
    # Must start with a likely command verb or config keyword
    return bool(re.match(
        r"^(no\s+)?(show|configure|conf|interface|int|ip|ipv6|router|vlan|switchport|"
        r"spanning-tree|hostname|copy|write|reload|monitor|clear|debug|ping|traceroute|"
        r"set|enable|disable|access-list|access-group|line|service|standby|vrrp|hsrp|"
        r"snmp-server|logging|ntp|aaa|crypto|key|tunnel|description|shutdown|mtu|speed|"
        r"duplex|channel-group|port-channel|policy-map|class-map|service-policy|"
        r"match|police|control-plane|tacacs|radius|username|password|secret|"
        r"track|address-family|af-interface|topology|exit-address-family|exit|end|"
        r"network|neighbor|redistribute|distance|distribute-list|prefix|prefix-list|"
        r"route-map|area|passive-interface|default-information|authentication|"
        r"vrf|errdisable|udld|loopguard|portfast|bpdu|trunk|"
        r"flow|sampler|template|ip access-list|ipv6 access-list|"
        r"event manager|policy|class|"
        r"dns-server|domain-name|lease|host|exclude|excluded|"
        r"\w+\s+[A-Za-z0-9])",
        l, re.IGNORECASE
    ))

def parse():
    text = SRC.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    out = []
    chapter = 0
    section_hdr = ""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # chapter detect
        m = re.match(r"^## Chapter (\d+):\s*(.+?)\s*$", line)
        if m:
            chapter = int(m.group(1))
            section_hdr = m.group(2).strip()
            i += 1
            continue
        # h2/h3
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            h = m.group(1).strip()
            if looks_like_section(h):
                section_hdr = h
            i += 1
            continue
        # fenced code block
        if line.strip() == "```":
            block = []
            i += 1
            while i < n and lines[i].strip() != "```":
                block.append(lines[i])
                i += 1
            i += 1  # past closing ```
            # Look ahead for description heading (next non-empty h3 that looks like a description)
            desc = ""
            j = i
            while j < n and j < i + 6:
                ln = lines[j].strip()
                if not ln: j += 1; continue
                hm = re.match(r"^#{2,3}\s+(.+?)\s*$", ln)
                if hm:
                    cand = hm.group(1).strip()
                    if looks_like_description(cand):
                        desc = cand
                    break
                else:
                    # hit non-heading content; stop searching
                    break
                j += 1
            # Now process the block content
            # Strategy: if block has multiple independent commands on separate lines (no indent), split.
            # Otherwise treat the whole block as one multi-line command.
            cleaned_lines = [l for l in block if l.strip()]
            if not cleaned_lines:
                continue
            has_indent = any(l.startswith(" ") or l.startswith("\t") for l in cleaned_lines)
            if has_indent or len(cleaned_lines) <= 1:
                # one multi-line entry
                cmd = "\n".join(cleaned_lines).rstrip()
                if looks_like_command(cleaned_lines[0]):
                    cat = categorize(CHAPTER_CAT.get(chapter,"System"), section_hdr, cmd)
                    out.append({
                        "os":"ios","role":role_of(cmd),"vendor":"Cisco","cat":cat,
                        "title": cmd.split("\n")[0][:70],
                        "cmd": cmd,
                        "desc": (desc or section_hdr)[:240],
                    })
            else:
                # multiple independent commands
                for cl in cleaned_lines:
                    if not looks_like_command(cl): continue
                    cmd = cl.strip()
                    cat = categorize(CHAPTER_CAT.get(chapter,"System"), section_hdr, cmd)
                    out.append({
                        "os":"ios","role":role_of(cmd),"vendor":"Cisco","cat":cat,
                        "title": cmd[:70],
                        "cmd": cmd,
                        "desc": (desc or section_hdr)[:240],
                    })
            continue
        i += 1
    return out

def main():
    items = parse()
    # dedupe within this source on normalized cmd
    seen = set(); deduped = []
    for it in items:
        key = re.sub(r"\s+", " ", it["cmd"]).lower()
        if key in seen: continue
        seen.add(key); deduped.append(it)
    OUT.write_text(json.dumps(deduped, indent=1, ensure_ascii=False))
    from collections import Counter
    print(f"wrote {len(deduped)} ENCOR/ENARSI entries -> {OUT}")
    print("by cat:", dict(Counter(c["cat"] for c in deduped)))
    print("by role:", dict(Counter(c["role"] for c in deduped)))

if __name__ == "__main__":
    main()
