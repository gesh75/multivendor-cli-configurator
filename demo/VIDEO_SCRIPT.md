# Demo Video — Shot List & Script

> Target length: **90 seconds**. Format: 1920×1080 screen recording with cursor.
> Voice-over optional — captions will carry the message either way.
> Output: `demo/multivendor-cli-demo.mp4` + `multivendor-cli-demo.webm`.

---

## Voice / caption track

| t (sec) | Beat | What's on screen | Caption / V-O |
|---:|---|---|---|
| 00–05 | **Hook** | Static intro frame: title, sub, GitHub URL | "9,808 CLI commands. 3 vendors. One static HTML file." |
| 05–12 | **Land on the site** | Open `gesh75.github.io/multivendor-cli-configurator/` — cards view, full sidebar | "No backend. No login. Search 9,808 commands across Cisco, Juniper, Arista." |
| 12–22 | **Search shortcut** | Press `/`, type `vendor:juniper ospf area`, cards filter live | "Operator search — `vendor:`, `os:`, `cat:`, `role:`. Autocomplete suggests values." |
| 22–32 | **Compare view (killer feature)** | Press `c`, scroll to a row where all three vendors line up (e.g. BGP peer) | "Concept-aligned compare — Cisco `neighbor`, Junos `peer`, Arista `neighbor` on one row." |
| 32–45 | **⚡ Automate (YANG)** | Click `⋯` → Automate (YANG) on a `bgp neighbor` card. Drawer slides in. Type a new ASN into the floating params panel; show snippets re-render live. | "Click Automate. Values extracted from the command. NETCONF XML, ncclient Python, Ansible task — all pre-filled, all live." |
| 45–55 | **🔧 Automate (SSH)** | Switch to a `show interfaces` card. Click ⋯ → Automate (SSH). Show Netmiko / Ansible / NAPALM tabs. | "Universal fallback. Every command becomes Netmiko, Ansible, or NAPALM with one click." |
| 55–65 | **📊 Parse Output** | Click 📊, pick "Cisco IOS BGP summary", click Insert sample, click Parse →. Structured table renders. | "Paste raw `show` output. TextFSM-lite parsers give you a structured table." |
| 65–75 | **CLI Builder + Share** | Add 3 mixed-vendor commands to CLI Builder. Open the drawer, copy all. Click 🔗 Share — clipboard toast. | "Mix vendors in the CLI Builder. Share a URL — the whole workspace travels in one link." |
| 75–82 | **Architecture flash** | Cut to `ARCHITECTURE.md` rendered on GitHub showing the SVG | "Reproducible pipeline. Stdlib-only Python parsers. One JSON file is the truth." |
| 82–90 | **Outro** | Repo URL + tagline; mouse hovers the GitHub icon | "Open source, GitHub-Pages-hosted. github.com/gesh75/multivendor-cli-configurator" |

---

## Recording plan (using the local `ui-demo` skill)

```bash
# 1. Pre-flight — site is on GitHub Pages, but record against the local copy for crisp loads.
cd /tmp/cli-deploy
python3 -m http.server 9125 &

# 2. Use the skill (writes to demo/multivendor-cli-demo.webm)
#    ui-demo runs Playwright with a visible cursor and natural pacing.
claude /skill ui-demo \
  --url   http://localhost:9125/index.html \
  --steps demo/STEPS.json \
  --out   demo/multivendor-cli-demo.webm \
  --width 1920 --height 1080

# 3. Convert to mp4 for LinkedIn upload
ffmpeg -i demo/multivendor-cli-demo.webm \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
  -movflags +faststart demo/multivendor-cli-demo.mp4
```

`demo/STEPS.json` (Playwright steps, paired with the timecodes above):

```json
[
  {"goto":  "http://localhost:9125/index.html"},
  {"wait":  1500},
  {"hover": "#q"},                      {"type": "#q", "text": "vendor:juniper ospf area"},
  {"wait":  1500},
  {"press": "c"},
  {"wait":  1500},
  {"scrollIntoView": ".cmp-row[data-concept='BGP:peer']"},
  {"wait":  1500},
  {"click": ".card .actbtn-more > button"},
  {"click": ".actbtn-menu-item.native"},
  {"wait":  1500},
  {"fill":  "#pp-host", "value": "10.0.0.99"},
  {"wait":  1500},
  {"press": "Escape"},
  {"click": "#btn-parser"},
  {"select":"#parser-template", "value": "cisco-bgp-summary"},
  {"click": "#parser-insert-sample"},
  {"click": "#parser-run"},
  {"wait":  2000},
  {"press": "Escape"},
  {"click": ".grid:nth-of-type(1) .card:nth-of-type(1) button:nth-of-type(2)"},
  {"click": ".grid:nth-of-type(2) .card:nth-of-type(1) button:nth-of-type(2)"},
  {"click": ".grid:nth-of-type(3) .card:nth-of-type(1) button:nth-of-type(2)"},
  {"click": "#btn-clibuilder"},
  {"wait":  1200},
  {"click": "#btn-share"}
]
```

---

## Thumbnail (1280×720)

- Headline: **"9,808 CLI commands · 3 vendors · 1 HTML file"**
- Sub: "Cisco · Juniper · Arista — cross-vendor compare + native YANG automation"
- Background: Compare view screenshot with the BGP row highlighted
- Bottom-right: GitHub mark + `gesh75/multivendor-cli-configurator`

Save as `demo/thumbnail.png`.

---

## Captions file (`demo/captions.vtt`)

```
WEBVTT

00:00.000 --> 00:05.000
9,808 CLI commands. 3 vendors. One static HTML file.

00:05.000 --> 00:12.000
No backend. No login. Search across Cisco, Juniper, Arista.

00:12.000 --> 00:22.000
Operator search — vendor:, os:, cat:, role:. Autocomplete suggests values.

00:22.000 --> 00:32.000
Concept-aligned compare — Cisco "neighbor", Junos "peer", Arista "neighbor", same row.

00:32.000 --> 00:45.000
Click Automate. NETCONF XML, ncclient Python, Ansible task — all pre-filled, all live.

00:45.000 --> 00:55.000
Universal fallback: every command becomes Netmiko, Ansible, or NAPALM.

00:55.000 --> 01:05.000
Paste raw show output. TextFSM-lite parsers give you a structured table.

01:05.000 --> 01:15.000
Mix vendors in the CLI Builder. Share a URL — the whole workspace travels in one link.

01:15.000 --> 01:22.000
Reproducible pipeline. Stdlib-only Python parsers. One JSON file is the truth.

01:22.000 --> 01:30.000
Open source. github.com/gesh75/multivendor-cli-configurator
```
