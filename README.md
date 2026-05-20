# Multivendor Network CLI Tools

> Two zero-dependency single-file HTML tools for network engineers — **Cisco · Juniper · Arista**
> in one searchable, shareable, deep-linkable interface.

🟢 **Live demo:** https://gesh75.github.io/multivendor-cli-configurator/

---

## What's here

| Tool | URL | What it does |
|---|---|---|
| **Cheatsheet** | [`/cheatsheet.html`](https://gesh75.github.io/multivendor-cli-configurator/cheatsheet.html) | **7,711 commands** searchable, filterable, with row-aligned cross-vendor compare view. Each command has vendor / OS / role / category metadata. |
| **Configurator** | [`/`](https://gesh75.github.io/multivendor-cli-configurator/) (`index.html`) | GUI form → live CLI generator. Pick vendor + role (router / switch / firewall), fill in interfaces / OSPF / BGP / ACLs / NAT, get production-ready config in your target dialect. Side-by-side vendor diff included. |

Both open in any modern browser. No build, no install, no JavaScript dependencies.

---

## Command coverage

| Vendor | OS | Commands |
|---|---|---|
| **Cisco** | IOS / IOS-XE · NX-OS · ASA | 2,036 |
| **Juniper** | Junos (MX / EX / QFX / SRX) | 2,895 |
| **Arista** | EOS | 2,836 |
| **TOTAL** | | **7,711** |

By category (top 10): System 2,086 · Routing 700 · VLAN 618 · Troubleshooting 525 ·
BGP 453 · Interfaces 396 · OSPF 359 · MPLS 290 · Multicast 284 · AAA 236.

By role: router 4,816 · switch 2,742 · firewall 153.

---

## Where the data comes from

| Source | Vendor | Commands |
|---|---|---|
| Cisco Press **ENCOR / ENARSI Portable Command Guide** (Empson + Gargano, 2020) | Cisco | ~1,400 |
| **Junos OS CLI Reference** (Juniper Networks, 2025 official) | Juniper | ~2,000 |
| **Day One: Beginner's Guide to Learning Junos** (Juniper Ambassadors, 2020) | Juniper | ~530 |
| **Day One: Exploring the Junos CLI**, 2nd Ed. (Goralski et al., 2015) | Juniper | ~260 |
| **Arista EOS User Guide** v4.36.0F (Arista Networks, 2026 official) | Arista | ~2,800 |
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
