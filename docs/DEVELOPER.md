# Developer & ops runbook

Setup, public interfaces, CI, Pages deploy, and the pitfalls that actually
bite when this repo changes. Architecture and corpus intent live in
[ARCHITECTURE.md](ARCHITECTURE.md). This page is the how-to.

---

## Local setup

No install, no virtualenv, no JS bundler. You need **Python 3** (stdlib) and
**Node 20+** (CI stress suite only).

```bash
# From the repo root — required. file:// blocks fetch('commands.json').
python3 -m http.server 8000
```

Then open:

| URL | What |
|---|---|
| http://localhost:8000/ | Cheatsheet (`index.html` + `commands.json`) |
| http://localhost:8000/docs/ | Animated docs landing page |
| http://localhost:8000/tests/stress_test.html | Browser IDB / boot harness |

Cloud Agent environments start the same server from
`.cursor/environment.json` (port **8000**).

**Constraint:** `index.html` loads the corpus with `fetch("commands.json")`.
Opening the file from disk shows a red empty-state that tells you to serve
it. A prior IndexedDB cache can still render offline after the first HTTP
visit.

---

## Public interfaces

### Deep-link query string

`syncUrl()` / `restoreUrl()` in `index.html` persist filter state via
`history.replaceState`. All values are comma-separated where multi-select
applies.

| Param | Example | Effect |
|---|---|---|
| `v` | `v=Cisco,Juniper` | Vendor filter (`state.vendor`) |
| `os` | `os=nxos,eos` | OS filter (`state.os`) |
| `role` | `role=router` | Role filter |
| `cat` | `cat=BGP,VXLAN` | Category filter |
| `q` | `q=ospf` | Search box |
| `view` | `view=compare` | `cards` (default) · `table` · `compare` |
| `fav` | `fav=1` | Favorites-only |

Omitted params mean “no filter” / cards view. Changing filters resets the
cards cap to 500 and Compare pages to 3.

### Shareable workspace (`?ws=`)

The **Share** button copies
`{origin}{pathname}?ws={base64url}`. Payload fields:

```json
{
  "v": ["Cisco"], "os": [], "role": [], "cat": ["BGP"],
  "q": "neighbor", "view": "compare", "fav": 0,
  "queue": [{"t": "title", "c": "cmd", "v": "Cisco", "o": "ios"}]
}
```

On boot, `tryDecodeWorkspace()` runs **before** `restoreUrl()`. A valid
`ws` wins and overwrites the CLI Builder queue in `localStorage`.

### Search operators

Typed into the search box (`parseQuery()`). Tokens are whitespace-split,
case-insensitive.

| Token | Meaning |
|---|---|
| `vendor:juniper` | Vendor substring match |
| `os:eos` | OS id or `OSLABEL` substring |
| `role:firewall` | Role substring |
| `cat:bgp` / `category:bgp` | Category substring |
| `fav:` | Favorites only (no value required) |

Bare tokens also expand through `NL_INTENT` (e.g. `ospf`, `juniper`,
`switch`) before the remaining words become AND text search over
title / cmd / desc.

### Keyboard (when focus is not in an input)

`/` search · `g` cards · `t` table · `c` compare · `b` Builder drawer ·
`f` favorites · `s` sidebar · `?` help card · `Esc` close drawer / clear
search. Arrow / Enter / Tab work inside the search-suggest list.

### Persistence

| Store | Keys | Notes |
|---|---|---|
| `localStorage` | `cli-fav`, `cli-queue`, `cli-acc`, `cli-recent`, `cli-drawer-w`, `cli-theme`, `cli-side-collapsed` | Favorites, Builder queue, accordion collapse, recent cmds, drawer width, theme, sidebar |
| `sessionStorage` | `auto-conn` | Automate connection form. Password is **not** written unless `_keepPass` is set |
| IndexedDB `mvc-cli-cache` / `payload` | `commands` | Cache-then-revalidate: render from IDB, `HEAD` `commands.json` for ETag / Content-Length, refetch only on change. Badge in the header; click to clear |

### Automate + Parse Output

- **15 YANG/CLI patterns** in `AUTOMATION_MAPPINGS`: `iface-ipv4`,
  `static-route`, `ospf-network`, `bgp-neighbor`, `vlan`,
  `switchport-access`, `ntp-server`, `syslog-host`, `hostname`,
  `interface-desc`, `loopback`, `default-route`, `trunk-port`,
  `aaa-radius`, `portchannel`. Matchers are IOS/Junos-shaped; other
  vendors render from Compare / equivalents via `AUTO_*` maps.
- **Secret mode** (`connState.secretMode`): `inline` · `env` (default) ·
  `keyring`. Toggling re-renders every snippet.
- **Parse Output** (`SHOW_PARSERS`): Cisco/EOS BGP summary, IP route,
  interface brief, OSPF neighbor; Junos BGP summary and route terse.
  EOS/FRR/VyOS parsers are still a follow-up.

---

## Corpus pipeline (what to run)

Sources under `scripts/sources/` are gitignored. Intermediate
`scripts/*.json` stay in-tree; **do not** publish them on Pages.

```bash
cd scripts
# Per-source parsers only when those books/exports changed
python3 parse.py                  # merge + dedupe → ../commands.json
python3 parse_modern.py           # telemetry / ZTP / optics / hardening
python3 expand_thin_vendors.py    # SONiC / NVIDIA / Huawei / SR OS / … fills
python3 fix_coverage_gaps.py      # NX-OS/IOS-XE retag, VXLAN/EVPN/STP/BFD/LACP
python3 clean_titles.py           # idempotent; writes *.titlebak
python3 audit_data_quality.py     # prose-in-title quarantine
python3 check_consistency.py      # docs figures vs corpus (CI)
python3 deep_gap_dig.py           # OS/cat/Automate floors (local gate)
# Optional, idempotent HTML patches (skip if marker comments exist)
python3 patch_yang_stack_vendors.py   # FRR · VyOS · Nokia · Aruba
python3 patch_yang_more_vendors.py    # Huawei · NVIDIA · SONiC · Extreme · Mikrotik
```

`deep_gap_dig.py --warn-only` never fails. `--json out.json` dumps the
report. Current floors (fail if below):

| Kind | Floor |
|---|---|
| OS `nxos` / `iosxe` / `sros` / `sonic` / `asa` | 200 / 120 / 70 / 450 / 400 |
| Cats `VXLAN` / `EVPN` / `Spanning-Tree` / `EtherChannel` / `BFD` | 250 / 490 / 400 / 250 / 100 |

Automate maps must include every network vendor in `AUTO_REQUIRED`
(FortiOS / PAN-OS are excluded — different primitives). Silent
`||AUTO_*.Cisco` fallbacks are a hard fail.

After any corpus edit, **update the hand-copied figures** in `README.md`
and `docs/index.html` (total, per-role counts, “17 vendor”).
`check_consistency.py` only substring-matches those facts. The README
per-vendor table is **not** gated — refresh it from `commands.json` or it
will drift.

---

## CI

`.github/workflows/ci.yml` on `push`/`pull_request` to `main`:

| Job | Command | Intent |
|---|---|---|
| Docs match commands.json | `python3 scripts/check_consistency.py` | Hard-fail if total / role counts / vendor-count phrase are missing from `README.md` or `docs/index.html` |
| Node stress + correctness | `node tests/stress_test.js` | Extracts `lookupConcept`, placeholders, Netmiko/Ansible maps from `index.html`; benches filters; asserts OS/cat floors, Automate vendor keys, no Cisco fallback |

Run the same two commands locally before opening a PR. The Node suite
rewrites `tests/stress_test_results.json`.

`deep_gap_dig.py` is **not** a CI job. Overlapping floors live inside
`stress_test.js` so a thin NX-OS/VXLAN/Automate regression still fails
the Node job.

Browser IDB/boot timings are **manual**: serve the repo and open
`/tests/stress_test.html`. See [../tests/STRESS_TEST.md](../tests/STRESS_TEST.md).

---

## GitHub Pages deploy

`.github/workflows/pages.yml` runs on **push to `main`** (and
`workflow_dispatch`). It does **not** rsync the whole repo.

Staged into `_site/`:

- App: `index.html`, `commands.json`, `configurator.html`, `favicon.svg`,
  `og-image.png`, `manifest.webmanifest`, `robots.txt`, `sitemap.xml`,
  `LICENSE`, `README.md`, `ARCHITECTURE.md`, `.nojekyll`
- `docs/` (landing + assets + this runbook)
- `tests/stress_test.html`, `tests/stress_test.js`, `tests/STRESS_TEST.md`,
  `tests/stress_test_results.json`

**Not published:** `scripts/*.json` source dumps (keeps the artifact lean).

`.nojekyll` is required. GitHub’s Jekyll pass treats Ansible
`{{ lookup('env', ...) }}` in the Automate snippets as Liquid and the
Pages build dies. The marker file disables Jekyll.

Live URLs:

- App: https://gesh75.github.io/multivendor-cli-configurator/
- Docs: https://gesh75.github.io/multivendor-cli-configurator/docs/

---

## Common pitfalls

1. **`file://` looks empty.** Serve over HTTP. The empty-state copy in
   `loadCommandsWithCache()` is the canonical hint.
2. **Stale totals fail CI**, even if the app is fine. Re-run
   `check_consistency.py` after editing `commands.json` or the two tracked
   docs files.
3. **Per-vendor README counts can lie.** CI does not check them. Recount
   from `commands.json` when you expand a vendor.
4. **Do not reintroduce `||AUTO_*.Cisco`.** Huawei / NVIDIA / SONiC /
   Extreme / Mikrotik / FRR / VyOS / Nokia / Aruba have CLI-first
   renderers. A Cisco YANG snippet on the wrong platform is the failure
   mode these patches exist to prevent.
5. **`CONCEPT_SYNONYMS` order is load-bearing.** `"undo shutdown"` must
   hit `iface-noshut` before `iface-shutdown`; default route before
   generic static. The Node suite has explicit cases.
6. **Idempotent patch scripts.** `patch_yang_*.py` no-op when their
   marker comments are already in `index.html`. Re-running them is safe;
   deleting the marker and re-running rewrites the helpers.
7. **`fix_coverage_gaps.py` / `expand_thin_vendors.py` mutate
   `commands.json` in place.** Dry-run / inspect the printed summary
   before committing a 18 MB JSON swing.
8. **Empty `desc` is a warning, not a gate.** `deep_gap_dig.py` currently
   reports hundreds of empty descriptions; do not treat that as a CI
   failure.
9. **Keep the two Architecture files in sync.** Root `ARCHITECTURE.md`
   and `docs/ARCHITECTURE.md` are copies. Pages ships both (root copy
   inside `_site/`, docs copy under `_site/docs/`).

---

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| Red “Failed to load commands.json” | `file://` or missing `commands.json` next to `index.html` | `python3 -m http.server` from repo root |
| Pages build error mentioning Liquid / `{{` | Jekyll parsing Ansible snippets | Confirm `.nojekyll` is in the staged `_site/` |
| CI “DRIFT DETECTED” | README / docs landing missing a formatted count | `python3 scripts/check_consistency.py` prints the missing token |
| CI stress fail on `lookupConcept` time | Accidental O(n²) edit in `index.html` | Target is `< 1800 ms` over the full corpus (was ~2.9 s before the 2026-07 index) |
| CI stress fail on OS/cat floors | Corpus edit dropped NX-OS / VXLAN / … | `python3 scripts/deep_gap_dig.py` then `expand_thin_vendors.py` / `fix_coverage_gaps.py` |
| Automate emits Cisco XML for Huawei/SONiC | Missing `AUTO_*` vendor key or silent fallback | `deep_gap_dig.py`; re-apply `patch_yang_more_vendors.py` only if the marker is gone |
| Stale command set after a Pages deploy | IndexedDB cache-then-revalidate | Click the header cache badge → clear; hard-refresh |
| Share URL does not restore Builder queue | `ws` decode failed (truncated URL) | Check console `workspace decode failed`; payload is base64url JSON |

---

## Related

- [ARCHITECTURE.md](ARCHITECTURE.md) — pipeline stages, row schema, Automate maps
- [../README.md](../README.md) — coverage table and feature list
- [../tests/STRESS_TEST.md](../tests/STRESS_TEST.md) — how to reproduce the Node + browser suites
