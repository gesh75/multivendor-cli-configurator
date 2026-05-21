# LinkedIn Post — drafts

> Three variants for different audiences. Pick one, attach
> `multivendor-cli-demo.mp4`, and ship.

---

## Variant A — The clean, engineer-focused version (recommended)

I built a multivendor CLI reference tool that turns 9,808 commands across Cisco, Juniper, and Arista into something a network engineer can actually use in 30 seconds — not 30 minutes of grepping through PDFs.

What's in it:

- **9,808 commands**, parsed from 7 public sources — Cisco Press ENCOR/ENARSI, ASA 9.24 CLI Reference, IOS OSPF Reference, NX-OS VXLAN/EVPN, Junos OS CLI Reference + two Day One books, Arista EOS User Guide.
- **Concept-aligned Compare view** — Cisco `neighbor`, Junos `peer`, Arista `neighbor` on one row, side-by-side, so I can see the equivalent in 3 clicks instead of 3 tabs.
- **Automate drawer** — every card has a one-click button that produces working NETCONF/YANG XML, ncclient Python, an Ansible task, AND a Netmiko/NAPALM fallback — all pre-filled with the values extracted from the command via regex. No more "did I get the YANG path right?"
- **Operator search** — `vendor:juniper ospf area` does what you'd expect. Autocomplete suggests values.
- **CLI Builder** — queue commands across vendors, export as one config block. Share the whole workspace as a single URL (state encoded in `?ws=…`).
- **Parse Output** — paste raw `show` output, get a structured table (TextFSM-equivalent, 6 builtin parsers).

The engineering choices I'm proud of:

→ **No build, no backend, no framework.** Single 190 KB `index.html` + a 3 MB `commands.json`. Lives on GitHub Pages.
→ **Reproducible pipeline.** Every command can be traced back to its source via a stdlib-only Python parser. `python3 scripts/parse.py` regenerates everything in ~6 seconds.
→ **No credentials touch disk.** Automation snippets use `${conn().host}` interpolation; connection state is sessionStorage only with a redact toggle for safe screenshots.

Built this over evenings + weekends to scratch my own itch as a multi-vendor network architect. Open source. Use it, fork it, send a PR for your vendor of choice.

🟢 Live: https://gesh75.github.io/multivendor-cli-configurator/
📐 Architecture: https://github.com/gesh75/multivendor-cli-configurator/blob/main/ARCHITECTURE.md
💻 Source: https://github.com/gesh75/multivendor-cli-configurator

#NetworkAutomation #Cisco #Juniper #Arista #NETCONF #Ansible #NAPALM #NetDevOps #OpenSource

---

## Variant B — Story-driven (shorter, hooks on a moment)

I got tired of three browser tabs.

Cisco docs in one. Juniper PDFs in another. Arista user guide in a third. Trying to remember how `set protocols bgp group EBGP-PEERS` maps to `router bgp 65001 / neighbor 10.0.0.1 remote-as 65002`. Reading the same OSPF concepts in three different vocabularies.

So I built a tool: one searchable interface, 9,808 commands across all three vendors, with a Compare view that lines up equivalents on one row.

The killer feature isn't the search — it's the **Automate** button. Click it on any command and you get the NETCONF XML + ncclient Python + Ansible task + Netmiko fallback, all pre-filled with the values from your specific command. No more "let me look up the YANG path for the third time today."

Built it as one HTML file. No backend. No login. GitHub-Pages-hosted. Open source.

🟢 https://gesh75.github.io/multivendor-cli-configurator/
💻 https://github.com/gesh75/multivendor-cli-configurator

#NetworkEngineering #NetworkAutomation #Cisco #Juniper #Arista

---

## Variant C — Recruiter-friendly (job-search context)

A weekend project that turned into something I actually use every day.

**Multivendor CLI Reference** — 9,808 Cisco / Juniper / Arista commands, searchable, with a concept-aligned Compare view + one-click NETCONF/YANG/Ansible/Netmiko/NAPALM snippet generation.

The technical bits:
• Reproducible Python pipeline parses 7 public vendor publications into one normalized JSON
• Single-file static HTML — vanilla JS, no framework, no backend — hosted on GitHub Pages
• Architecture documented: https://github.com/gesh75/multivendor-cli-configurator/blob/main/ARCHITECTURE.md

What I learned re-building this for the third time:
1. Cross-vendor concept alignment is harder than it looks — Cisco's `neighbor`, Junos's `peer`, and Arista's `neighbor` all mean the same thing, but lexical similarity won't get you there. You need a small handwritten ontology of stopwords + topic hints.
2. The right level of automation for a CLI reference is **two layers** — 15 hand-mapped YANG patterns for the things that matter (BGP peer, OSPF area, VLAN, NAT, …) + a universal SSH/Netmiko/Ansible/NAPALM fallback for everything else. 100% coverage, with depth where it counts.
3. Static HTML + 3 MB JSON beats a SaaS backend for tools like this. Faster, free to host, no auth fatigue, deep-linkable.

Open to network architect / director-level roles. Reach out if this kind of work is interesting.

🟢 https://gesh75.github.io/multivendor-cli-configurator/

#NetworkArchitect #NetworkAutomation #OpenSource #NetDevOps

---

## Posting checklist

- [ ] Attach `demo/multivendor-cli-demo.mp4` (59 seconds, 8.9 MB, 1920×1080) as the video
- [ ] Use Variant A unless you have a specific story angle (B) or job-search context (C)
- [ ] First 3 lines must hook — LinkedIn truncates after ~200 chars
- [ ] Post Tuesday–Thursday, 8–10 am local for max network engineer reach
- [ ] Reply to the first 5 comments within an hour — boosts algorithmic distribution
- [ ] Cross-post to: r/networking (with the demo gif), Hacker News (Show HN format), Mastodon if you're there
- [ ] Tag a recruiter contact if Variant C is used
