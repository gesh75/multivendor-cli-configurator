# Multivendor Network CLI Tools

> A zero-dependency single-file HTML reference for network engineers —
> **52,000+ CLI commands across 17 vendors & tools** in one searchable,
> comparable, shareable, deep-linkable interface.

🟢 **Live demo:** [gesh75.github.io/multivendor-cli-configurator](https://gesh75.github.io/multivendor-cli-configurator/)
📐 **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

![Architecture](docs/img/architecture.svg)

---

## What's here

**[Cheatsheet](https://gesh75.github.io/multivendor-cli-configurator/)** (`index.html`) —
**52,031 commands** across **17 vendors & tools**, searchable, filterable,
deep-linkable, with three view modes:

- **Cards** (default) — auto-fit grid grouped by category
- **Table** — sortable, exportable to CSV / Markdown / JSON / TXT
- **Compare** — row-aligned, concept-aligned side-by-side matrix. N-vendor
  aware: defaults to the four with deepest coverage (Cisco · Juniper · Arista ·
  FRR) and you filter to any subset of the 17. The view is paginated and
  virtualized so it stays fast even across the full corpus.

Each command card has:
- **Copy / + CLI / See equivalents ↗** — usual operations
- **🔧 Automate** — for common patterns, opens a drawer showing the NETCONF XML,
  ncclient Python snippet, and Ansible task **pre-filled with the values from
  your specific command** (extracts your IP, VLAN, ASN, etc. via regex and
  substitutes into vendor-correct templates).
- **🔐 Secret mode** — pick how generated snippets read credentials: **Inline**
  (literals, demo only), **.env** (python-dotenv, default — safer pasteboard),
  or **keyring** (OS credential store). Toggling re-renders every snippet in
  place, with a companion `.env.example` / `keyring set` one-liner alongside.

Opens in any modern browser. No build, no install, zero JS dependencies.

A legacy `configurator.html` is kept in the repo for archive purposes — a
form-based CLI generator superseded by the cheatsheet's Compare view + Automate
drawer. Not linked from the live site.

---

## Command coverage

### Network vendors

| Vendor | OS | Commands |
|---|---|---|
| **Arista** | EOS | 7,384 |
| **VyOS** | VyOS (full config tree) | 6,286 |
| **Cisco** | IOS / IOS-XE · ASA 9.24 · NX-OS | 4,409 |
| **Huawei** | VRP (bracketed prompts, iStack, Eth-Trunk, OSPF/BGP) | 4,406 |
| **Aruba** | AOS-CX (`1/1/N` interfaces, MSTP/RPVST, VSX) | 4,093 |
| **FRR** | FRRouting (vtysh) — docs **+ verified live on a 10-node Docker FRR lab** | 3,947 |
| **Juniper** | Junos (MX / EX / QFX / SRX) | 3,206 |
| **Extreme** | EXOS (VLAN-centric, STP, OSPF, SummitStacking, MLAG, ACLs) | 2,781 |
| **FortiOS** | Fortinet (`config / set / end` blocks, REST cmdb) | 2,376 |
| **PAN-OS** | Palo Alto firewalls (`set rulebase security ...`, virtual routers) | 1,217 |
| **Mikrotik** | RouterOS (`/path` syntax, firewall filters, queues) | 1,209 |
| **NVIDIA** | Cumulus Linux 5.x with NVUE (`nv set/show`) | 1,149 |
| **Nokia** | SR Linux (declarative `enter candidate` / `commit now`, gNMI) | 1,053 |
| **SONiC** | OCP / Azure SONiC (Click CLI, `show ip ...`) | 442 |
| | **Subtotal** | **43,958** |

### Tools & host OS

| Tool / OS | Surface | Commands |
|---|---|---|
| **Microsoft** | Windows PowerShell networking cmdlets | 3,352 |
| **Linux** | `ip` / `iproute2` / host networking | 2,591 |
| **Wireshark** | `tshark` capture + display filters | 2,130 |
| | **Subtotal** | **8,073** |

**TOTAL: 52,031**

By category (top 10): Interfaces 15,197 · System 6,761 · Protocols 6,418 ·
VLAN 3,959 · Security 2,251 · Routing 2,185 · BGP 1,993 · Misc 1,983 ·
Troubleshooting 1,649 · Firewall 1,595.

By role: router 25,270 · switch 22,625 · firewall 4,136.

---

## Where the data comes from

| Source | Vendor(s) | Commands |
|---|---|---|
| Cisco Press **ENCOR / ENARSI Portable Command Guide** (Empson + Gargano, 2020) | Cisco | ~1,400 |
| **Junos OS CLI Reference** (Juniper Networks, official) | Juniper | ~2,000 |
| **Day One: Beginner's Guide to Learning Junos** + **Exploring the Junos CLI** | Juniper | ~800 |
| **Arista EOS User Guide** (Arista Networks, official) | Arista | ~2,800 |
| **Cisco Secure Firewall ASA 9.24 CLI Reference** (official) | Cisco | ~335 |
| **FRR Master CLI Command Reference** (docs ∪ live capture from a 10-node Docker FRR lab) | FRR | ~2,230 |
| **DCN multivendor corpus** — VyOS, Huawei VRP, Aruba AOS-CX, Extreme EXOS, FortiOS, PAN-OS, RouterOS, NVUE, SR Linux, SONiC, plus Microsoft / Linux / Wireshark | Many | ~38,000 |
| Community markdown + hand-curated seed | All | ~600 |

All sources are publicly available. The Python pipeline under `scripts/` is
reproducible. Two maintenance utilities keep the corpus clean:

- `scripts/audit_data_quality.py` — flags records where description prose has
  leaked into the `title`/`cmd` fields, and can quarantine unrecoverable ones.
- `scripts/clean_titles.py` — derives clean command labels from the `cmd` field
  for any record whose title is prose. Idempotent; writes `.titlebak` backups.

---

## Cheatsheet features

- **3 view modes:** Cards (default) · Table (sortable, exportable) · Compare
  (concept-aligned, N-vendor matrix, paginated/virtualized)
- **Filter rail:** accordion sections for Vendor / OS / Role / Category, with an
  active-filter chip bar and live counts
- **Search prefix operators:** `vendor:juniper ospf` · `os:eos bgp` · `cat:VLAN` · `fav:`
- **Cross-vendor "See equivalents ↗"** per card — drawer with top-N matches per vendor
- **Favorites** (★) persisted in localStorage + dedicated filter
- **CLI Builder drawer** — queue commands across vendors, copy/download as `.txt`
- **Parse Output** — paste raw `show` output, get a structured table
- **Export menu:** `.txt`, `.md`, `.csv`, `.json`
- **Shareable workspace URL** — restores filters, view, search, and CLI Builder queue
- **Deep-link state:** `?cat=BGP&view=compare&v=Juniper`
- **Syntax highlighting** with placeholder pills (`[IP]`, `<vlan>`, …)
- **Keyboard:** `/` search · `c/t/g` views · `b` builder · `s` sidebar · `f` favorites · `Esc`
- **Light/dark mode** toggle, persisted
- **Accessible & discoverable:** valid heading outline, `:focus-visible` rings,
  `aria-live` status, skip link, plus Open Graph / Twitter / JSON-LD metadata,
  favicon, web manifest, `robots.txt` and `sitemap.xml`

---

## Pipeline architecture

```
scripts/sources/*                      # vendor books, docs, exported corpora
            │
            ▼
scripts/parse_*.py                     # per-source parsers
            │
            ▼
scripts/*.json                         # intermediate per-source JSON
            │
            ▼
scripts/parse.py / merge_dcn_corpus.py # merge + dedupe across all sources
            │
            ▼
scripts/clean_titles.py                # repair prose-in-title records (idempotent)
            │
            ▼
commands.json                          # single source of truth
            │
            ▼
index.html  ←─ fetch('commands.json')
```

To add a new source:
1. Drop the source into `scripts/sources/` (gitignored) or add a parser.
2. Run the relevant `parse_*.py` (or `merge_dcn_corpus.py`) to regenerate.
3. Run `python3 scripts/clean_titles.py` and `audit_data_quality.py` to verify quality.
4. Commit + push to `main` — GitHub Pages auto-deploys the live demo.

---

## Tech

Single-file HTML, vanilla JS, no framework. Hosted on GitHub Pages. Python 3 +
standard library only for the parsing pipeline.

---

*Built and maintained by [@gesh75](https://github.com/gesh75).*
