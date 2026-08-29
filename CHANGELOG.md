# Changelog

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

### Research backlog (not in this drop)

- Grow SONiC (459) and classic Nokia SR OS
- Merge draft docs PRs #11 / #12 (developer runbook)
- ISIS / SR-MPLS / IPv6 BGP recipes
- TextFSM / TTP export of parse tables
- Service worker so Studio works fully offline
- Wire Studio recipes into AEGIS pre-change validation
