# Developer & operations guide

How to run, test, regenerate, and ship this repo without inventing behavior.
Every claim below is checked against `index.html`, `scripts/`, and `.github/workflows/`.

For product architecture and the data model, start with [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Local setup

No virtualenv, no npm install, no bundler.

| Need | Why |
|---|---|
| Python 3 | Corpus pipeline + `check_consistency.py` / `deep_gap_dig.py` |
| Node 20+ | `tests/stress_test.js` (also the CI runner) |
| Any modern browser | Cheatsheet, docs site, browser stress harness |

```bash
# from the repo root
python3 -m http.server 8000
# cheatsheet     → http://127.0.0.1:8000/
# live docs      → http://127.0.0.1:8000/docs/
# browser stress → http://127.0.0.1:8000/tests/stress_test.html
```

Cloud Agent / Codespaces: `.cursor/environment.json` already starts that server on port 8000.

Opening `index.html` as a `file://` URL works for a quick look, but `fetch('commands.json')` and the IndexedDB cache path are more reliable over HTTP.

---

## Public interfaces (the page)

### Search operators (`parseQuery` in `index.html`)

Tokens of the form `key:value` are filters. Remaining tokens are AND-matched against `title` + `cmd` + `desc`.

| Token | Effect |
|---|---|
| `vendor:juniper` | Vendor filter (substring, case-insensitive) |
| `os:eos` | OS filter (`ios`, `iosxe`, `nxos`, `asa`, `junos`, `eos`, …) |
| `role:firewall` | Role filter (`router` / `switch` / `firewall`) |
| `cat:bgp` / `category:bgp` | Category filter |
| `fav:` | Favorites only (same as the ★ chip) |

Bare words are also mapped through a small **NL-intent** table (`NL_INTENT`). Only **Cisco / Juniper / Arista** vendor names expand that way; other vendors need `vendor:` or the filter rail.

### Deep-link query string (`syncUrl` / `restoreUrl`)

| Param | Example | Notes |
|---|---|---|
| `v` | `?v=Juniper,Arista` | Comma-separated vendor names (exact) |
| `os` | `?os=junos,eos` | Comma-separated OS keys |
| `role` | `?role=router` | |
| `cat` | `?cat=BGP,OSPF` | Exact category labels |
| `q` | `?q=vendor:juniper%20ospf` | Search box, including operators |
| `view` | `?view=compare` | `cards` (default, omitted) · `table` · `compare` |
| `fav` | `?fav=1` | Favorites-only |
| `ws` | `?ws=<base64url>` | Full workspace: filters + view + search + Builder queue |

`?ws=` wins over the other params when present (`tryDecodeWorkspace` runs first).

### Persistence (nothing is written to disk by the page)

| Store | Key | Contents |
|---|---|---|
| `localStorage` | `cli-fav` | Favorite command ids |
| `sessionStorage` | `auto-conn` | Automate connection fields + secret mode + redact flag |
| IndexedDB `mvc-cli-cache` / store `payload` | `commands` | Cached `commands.json` + ETag + Content-Length |

Secret mode (`inline` · `env` · `keyring`) only changes **generated snippet text**. Credentials stay in `sessionStorage`.

Click the cache badge in the header to clear IndexedDB if a local `commands.json` change is not showing up.

### Keyboard

`/` search · `c` compare · `t` table · `g` cards · `b` Builder · `f` favorites · `s` sidebar · `?` help · `Esc` close/clear.

---

## Do not casually regenerate `commands.json`

`scripts/parse.py` **rebuilds and overwrites** `commands.json` from:

- optional markdown under `scripts/sources/` (**gitignored** — not in a fresh clone)
- the checked-in per-source JSON files under `scripts/*.json`

It does **not** start from the current `commands.json`. A lone `python3 scripts/parse.py` drops later passes:

1. `merge_dcn_corpus.py` — needs an external `cli-export.json` (`CLI_WORK_DCN_CORPUS` or `--source`). The default path is a machine-specific checkout and will fail here.
2. `parse_modern.py` — telemetry / automation / ZTP / optics / hardening fills
3. `expand_thin_vendors.py` — curated SONiC / NVIDIA / SR OS / … rows
4. `fix_coverage_gaps.py` — NX-OS/IOS-XE retag + VXLAN/EVPN/STP/LACP/BFD promotions

**Day-to-day UI or docs work:** leave `commands.json` alone. Run the quality gates below.

**Full rebuild** (only when you have sources **and** the DCN export):

```bash
cd scripts
python3 parse.py
python3 merge_dcn_corpus.py          # requires CLI_WORK_DCN_CORPUS
python3 parse_modern.py
python3 expand_thin_vendors.py
python3 fix_coverage_gaps.py
python3 clean_titles.py
python3 audit_data_quality.py
cd ..
python3 scripts/check_consistency.py
python3 scripts/deep_gap_dig.py
# optional, idempotent, mutates index.html:
python3 scripts/patch_yang_stack_vendors.py
python3 scripts/patch_yang_more_vendors.py
```

Then update any hand-written per-vendor / per-category figures in `README.md` (the CI consistency job only asserts **total**, **per-role**, and **vendor count**).

---

## Quality gates

| Command | Mutates? | In CI? | Fails on |
|---|---|---|---|
| `python3 scripts/check_consistency.py` | no | yes — `consistency` | `70,006` / role counts / `17 vendor` missing from `README.md` or `docs/index.html` |
| `node tests/stress_test.js` | writes `tests/stress_test_results.json` | yes — `stress-test` | perf targets, concept/placeholder correctness, vendor smoke, OS/cat floors, Automate/Netmiko maps |
| `python3 scripts/deep_gap_dig.py` | no | no (floors are duplicated in the Node suite) | OS/cat floors, missing `AUTO_*` vendor keys, silent Cisco fallback, Netmiko/Ansible maps, prose/escaped titles |
| `python3 scripts/audit_data_quality.py` | no unless `--quarantine` | no | report only (exit 0); `--quarantine` drops unrecoverable prose-`cmd` rows |
| `python3 scripts/clean_titles.py --dry-run` | no | no | n/a — re-run without `--dry-run` to repair titles |

`deep_gap_dig.py --warn-only` never fails. `--json out.json` writes the structured report.

Current floors (keep CI stable — do not raise casually):

```
OS:    nxos ≥ 200 · iosxe ≥ 120 · sros ≥ 70 · sonic ≥ 450 · asa ≥ 400
cats:  VXLAN ≥ 250 · EVPN ≥ 490 · Spanning-Tree ≥ 400 · EtherChannel ≥ 250 · BFD ≥ 100
```

Firewall vendors (FortiOS, PAN-OS) are intentionally excluded from L2/L3 Automate completeness.

Browser harness (`tests/stress_test.html`) is **not** in CI — cold/warm boot + IndexedDB only.

---

## CI (`.github/workflows/ci.yml`)

Runs on push/PR to `main`. Two jobs, both `contents: read` only:

1. **Docs match `commands.json`** — `python3 scripts/check_consistency.py`
2. **Node stress + correctness** — `node tests/stress_test.js` on Node 20

A docs-only PR that changes the total or a role count without updating both tracked files will fail job 1. A `lookupConcept` / Automate-map regression will fail job 2.

---

## GitHub Pages (`.github/workflows/pages.yml`)

Trigger: push to `main` or `workflow_dispatch`. The workflow **does not** publish the repo as-is. It stages a lean `_site/`:

- app: `index.html`, `commands.json`, `configurator.html`, icons / manifest / `robots.txt` / `sitemap.xml`, `LICENSE`, `README.md`, `ARCHITECTURE.md`, `.nojekyll`
- `docs/` (this guide + the animated landing page)
- `tests/stress_test.*` (optional public harness)

**Not published:** `scripts/*.json` intermediates (tens of megabytes, not needed at runtime).

### Pitfall: Jekyll vs Ansible `{{ }}`

`index.html` embeds Ansible snippets such as `{{ lookup('env', 'NETDEV_PASS') }}`. Classic GitHub Pages Jekyll treats `{{ }}` as Liquid and breaks the file. `.nojekyll` at the repo root (copied into `_site/`) disables that. Do not remove it.

---

## Common pitfalls

- **Stale local page after editing `commands.json`.** The IndexedDB cache wins until ETag / Content-Length change. Click the cache badge → clear, or use a private window.
- **`CONCEPT_SYNONYMS` order is load-bearing.** First substring-AND match wins. `iface-noshut` must sit above `iface-shutdown`; `default-route` above `static-route`. The Node suite has fixtures for both.
- **No silent Cisco Automate fallback.** `deep_gap_dig.py` and the stress suite fail if `AUTO_*` maps fall back to `AUTO_*.Cisco` or if `openAutomation` is hardcoded to Cisco/Juniper/Arista.
- **`patch_yang_*.py` edit `index.html` in place.** They are idempotent (marker comments) but they are still HTML mutations — review the diff.
- **`expand_thin_vendors.py` / `parse_modern.py` append.** Safe to re-run (dedupe by vendor + normalized cmd) but they grow the corpus; run `check_consistency.py` and refresh hand-written vendor/category tables afterwards.
- **NL search ≠ filter rail.** Typing `huawei` does not auto-select the Huawei vendor chip; use `vendor:huawei` or the rail.
- **Parse Output is Cisco + Junos only.** EOS / FRR / VyOS parsers are still a follow-up (see Architecture).
- **`merge_dcn_corpus.py` existing rows win.** That preserves FRR `live` / `in_docs` flags. Do not invert the merge order.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| CI `consistency` red | `python3 scripts/check_consistency.py` locally — it prints the missing substring. Update `README.md` **and** `docs/index.html`. |
| CI `stress-test` red | `node tests/stress_test.js` — look for `MISS`, `FLOOR`, or `AUTO MAP`. Extract failures mean an `index.html` edit broke a slice the harness scrapes. |
| Pages 404 / empty app | Confirm `commands.json` is next to `index.html` on the deployed artifact; the lean workflow copies both. |
| Pages HTML looks truncated / Liquid errors | `.nojekyll` missing from the published root. |
| `parse.py` wrote a much smaller corpus | Expected if DCN / modern / thin-vendor passes were not re-run. Restore `commands.json` from git and read the regen section above. |
| `merge_dcn_corpus.py` FATAL: source not found | Set `CLI_WORK_DCN_CORPUS` (or `--source`) to a local `cli-export.json`. There is no copy in this repo. |
| Automate drawer shows Cisco XML for a VyOS/FRR card | Open Automate from Compare / equivalents so the vendor list is `AUTO_VENDORS`, not a Cisco-shaped matcher-only path. |
| Browser stress page does nothing | Serve over HTTP (`python3 -m http.server`) so the iframe can load `/index.html`. |
