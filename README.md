# Multivendor Network CLI Tools

> Two zero-dependency single-file HTML tools for network engineers — **Cisco · Juniper · Arista · FRR**
> in one searchable, shareable, deep-linkable interface.

🟢 **Live demo:** [gesh75.github.io/multivendor-cli-configurator](https://gesh75.github.io/multivendor-cli-configurator/)
📐 **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

![Architecture](docs/img/architecture.svg)

---

## What's here

**[Cheatsheet](https://gesh75.github.io/multivendor-cli-configurator/)** (`index.html`) —
11,542 commands searchable, filterable, deep-linkable, with three view modes:

- **Cards** (default) — auto-fit grid grouped by category
- **Table** — sortable, exportable to CSV / Markdown / JSON / TXT
- **Compare** — row-aligned Cisco · Juniper · Arista · FRR side-by-side (n-vendor aware — filter to any subset)

Each command card has:
- **Copy / + CLI / See equivalents ↗** — usual operations
- **🔧 Automate** — *new*. For 10 of the most common patterns, opens a drawer showing the NETCONF XML, ncclient Python snippet, and Ansible task **pre-filled with the values from your specific command** (extracts your IP, VLAN, ASN, etc. via regex and substitutes into vendor-correct templates).
- **🔐 Secret mode** — pick how generated snippets read credentials: **Inline** (literals, demo only), **.env** (python-dotenv, default — safer pasteboard), or **keyring** (OS credential store). Toggling re-renders every snippet in place. A companion `.env.example` or `keyring set` one-liner appears alongside the code so engineers can copy both halves.

Opens in any modern browser. No build, no install, zero JS dependencies.

A legacy `configurator.html` is kept in the repo for archive purposes — it's a form-based CLI generator that was superseded by the cheatsheet's Compare view + Automate drawer. Not linked from the live site.

---

## Command coverage

| Vendor | OS | Commands |
|---|---|---|
| **Cisco** | IOS / IOS-XE (3,512) · ASA 9.24 (352) · NX-OS (67) | 3,931 |
| **Juniper** | Junos (MX / EX / QFX / SRX) | 3,007 |
| **Arista** | EOS | 2,869 |
| **FRR** | FRRouting (vtysh) — official docs **+ commands verified live on a 10-node Docker FRR lab**. ~870 rows tagged `● live` (368 doc + live, 502 live-only / undocumented). | 2,210 |
| **TOTAL** | | **12,017** |

By category (top 10): System 2,320 · Interfaces 1,166 · BGP 1,080 · Troubleshooting 1,017 ·
Routing 905 · VLAN 635 · OSPF 635 · Multicast 541 · MPLS 315 · AAA 279.

By role: router 8,254 · switch 2,811 · firewall 477.

---

## Where the data comes from

| Source | Vendor | Commands |
|---|---|---|
| Cisco Press **ENCOR / ENARSI Portable Command Guide** (Empson + Gargano, 2020) | Cisco | ~1,400 |
| **Junos OS CLI Reference** (Juniper Networks, 2025 official) | Juniper | ~2,000 |
| **Day One: Beginner's Guide to Learning Junos** (Juniper Ambassadors, 2020) | Juniper | ~530 |
| **Day One: Exploring the Junos CLI**, 2nd Ed. (Goralski et al., 2015) | Juniper | ~260 |
| **Arista EOS User Guide** v4.36.0F (Arista Networks, 2026 official) | Arista | ~2,800 |
| **Cisco Secure Firewall ASA 9.24 CLI Reference** (Books 1–3, official) | Cisco | ~335 |
| **Cisco IOS OSPF Command Reference** | Cisco | ~110 |
| **VXLAN BGP EVPN NX-OS Command Reference** | Cisco | ~60 |
| **FRR Master CLI Command Reference** (FRRouting docs ∪ live capture from 10-node Docker FRR lab) | FRR | ~2,230 |
| Community markdown (grplyler, r7perezyera, hyprblaze, cmdref.net, INSRapperswil…) | All | ~400 |
| Hand-curated seed | All | 187 |

All sources are publicly available. The Python pipeline (`scripts/parse_*.py`) is reproducible.

---

## Cheatsheet features

- **3 view modes:** Cards (default) · Table (sortable, exportable) · Compare (concept-aligned, 3-column Cisco | Juniper | Arista)
- **Filter rail:** accordion sections for Vendor / OS / Role / Category, with active-filter chip bar
- **Search prefix operators:** `vendor:juniper ospf` · `os:eos bgp` · `cat:VLAN` · `fav:`
- **Cross-vendor "See equivalents ↗"** per card — opens drawer with top-N matches per vendor in same category
- **Favorites** (★) persisted in localStorage + dedicated filter
- **CLI Builder drawer** — queue commands across vendors, copy/download as `.txt` (resizable)
- **Export menu:** `.txt`, `.md` (tables grouped by category), `.csv`, `.json`
- **Deep-link state:** `?cat=BGP&view=compare&v=Juniper` — shareable filter URLs
- **Syntax highlighting** with placeholder pills (`[IP]`, `<vlan>`, etc.)
- **Keyboard:** `/` search · `c/t/g` views · `b` builder · `s` sidebar · `f` favorites · `Esc`
- **Light/dark mode** toggle, persisted

## Configurator features

- 3-zone resizable layout (drag the gutters)
- Per-section ✓/○ completion badges in the sidebar, with on/off toggles to include/exclude each block in the output
- **⇄ Compare** — split the CLI panel into two vendor columns side-by-side from the same form data
- **⇪ Import** — paste an existing Cisco IOS config, parser reverse-engineers it into the form (handles hostname, interfaces, static routes, OSPF, BGP, ACLs, VLANs)
- Inline `?` tooltips on ambiguous fields (wildcard masks, admin distance, prefix length, etc.)
- ACL rules as a compact inline table (Seq · Action · Proto · Source · Dest · Port)
- Section anchor links inside generated CLI — click `! --- OSPF ---` to jump the form
- Light / dark theme toggle with state label

---

## Pipeline architecture

```
06_Documentation/*.md                  # vendor books (Cisco Press / Day One / Arista User Guide)
            │
            ▼
scripts/parse_*.py                     # per-source parsers
            │
            ▼
scripts/{encor,junos,arista}.json      # intermediate per-source JSON
            │
            ▼
scripts/parse.py                       # merges + dedupes against community markdown + curated seed
            │
            ▼
commands.json                          # single source of truth (~1.6 MB)
            │
            ▼
cheatsheet.html  ←─ fetch('commands.json')
```

To add a new source:
1. Drop the markdown into `scripts/sources/` (or a new vendor book at the repo root)
2. Either run an existing parser, or write a new `parse_<name>.py` (format-specific)
3. Re-run `python3 scripts/parse.py` to regenerate `commands.json`
4. Commit + push — GitHub Pages auto-deploys

---

## Tech

Single-file HTML, vanilla JS, no framework. Hosted on GitHub Pages. Python 3 + only the
standard library for the parsing pipeline. MIT-friendly intent.

---

*Built and maintained by [@gesh75](https://github.com/gesh75).*
