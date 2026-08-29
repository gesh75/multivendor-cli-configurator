# Changelog

## 2026-08-29 — Studio finish (docs + remaining plan)

Closes the research backlog called out when CLI Studio landed on Pages.

### Docs site

- `docs/index.html` now has **Studio**, **Status**, **Develop**, and **Changelog** sections.
- Added [`docs/DEVELOP.md`](docs/DEVELOP.md) — developer/ops runbook (HTTP-only serve, regen order, CI, Pages inventory, pitfalls). **Supersedes draft PRs #11 and #12.**
- Quickstart no longer implies `file://`. Full regen pipeline (merge / expand / gap-fix / consistency / deep-gap) is documented.
- Sitemap includes the runbook.

### Studio plan items now shipped

| Item | Where |
|---|---|
| IS-IS L2, SR-MPLS node-SID, IPv6 eBGP recipes | Studio recipes + golden-path corpus |
| TextFSM / TTP export of parse tables | Parse tab |
| Hardening lint (NTP / AAA / SSH / syslog / BFD / secrets) | Harden tab |
| AEGIS-style pre-change (risk, blast, rollback) | Harden tab |
| SONiC + classic SR OS golden-path growth | Studio corpus (full `commands.json` still thin) |

### Still open

- Grow SONiC (459) and classic SR OS in the 70,006-row JSON
- Offline service worker for Studio
- Wiring Studio recipes into the air-gapped AEGIS repo (this gate is a client-side cousin, not a replacement)

## 2026-08-29 — CLI Studio on GitHub Pages

Shipped a second static surface next to the 70,006-command cheatsheet. Still zero npm. Still GitHub Pages.

### Live

- **[CLI Studio](https://gesh75.github.io/multivendor-cli-configurator/studio.html)** — intent, recipes, migrate, parse, FRR lab map, hardening lint, coverage matrix
- Cheatsheet header now links to Studio
- Parse Output on the cheatsheet gains **EOS / FRR / VyOS** BGP summary parsers (the follow-up called out in `ARCHITECTURE.md`)
- Auto-detect for Cisco BGP no longer steals every `local AS number` paste

### Studio tools

| Tab | What it does |
|---|---|
| Intent | English → concept → N-vendor CLI |
| Recipes | Parameterized BGP / OSPF / EVPN / LACP / ACL / NTP / BFD / STP / gNMI |
| Migrate | Paste one vendor, emit the others as a unified diff |
| Parse | Cisco, Junos, EOS, FRR, VyOS show-output tables |
| Lab | 10-node FRR Clos; live-flagged commands |
| Lint | NTP / AAA / SSH / syslog / BFD / secret heuristics |
| Coverage | Honest golden-path matrix across 17 vendors |

Snippets per command: CLI, RESTCONF curl, gNMI get, Netmiko, Nornir, NETCONF. Credentials via `$NET_*` env — nothing stored.

### Hosting

`studio.html` + `studio-data.json` + `404.html` are now in the lean `_site/` Pages artifact.
