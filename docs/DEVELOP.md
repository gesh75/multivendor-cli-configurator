# Developer / operations runbook

How to serve, regenerate, and ship
[multivendor-cli-configurator](https://github.com/gesh75/multivendor-cli-configurator)
without drifting the 70,006-command corpus.

This document supersedes draft PRs #11 and #12.

## Public surfaces

| URL | Artifact | Notes |
|---|---|---|
| https://gesh75.github.io/multivendor-cli-configurator/ | `index.html` + `commands.json` (~18 MB) | Cheatsheet. Vanilla JS. IndexedDB cache-then-revalidate. |
| https://gesh75.github.io/multivendor-cli-configurator/studio.html | `studio.html` + `studio-data.json` | CLI Studio — intent, recipes, migrate, parse, lab, lint, coverage. |
| https://gesh75.github.io/multivendor-cli-configurator/docs/ | `docs/index.html` | This docs site. |
| https://gesh75.github.io/multivendor-cli-configurator/docs/DEVELOP.md | this file | Runbook. |

Zero npm on every public surface. MIT license.

## HTTP only

`index.html` and `studio.html` `fetch()` their JSON. Opening from disk (`file://`)
looks empty. Local serve:

```bash
python3 -m http.server 8000
# http://127.0.0.1:8000/
# http://127.0.0.1:8000/studio.html
# http://127.0.0.1:8000/docs/
```

Cursor Cloud Agents use the same command (see `.cursor/environment.json`).

## URL / state contract (`index.html`)

- Readable params: `?cat=BGP&view=compare&v=Juniper`
- Shareable workspace: `?ws=` (base64 of filters, view, search, favorites, builder queue)
- Search operators: `role:` `category:` `vendor:` plus in-app `?` help
- Persistence: `localStorage` (theme/prefs), `sessionStorage` (Automate conn + secret mode), IndexedDB `mvc-cli-cache` (corpus)
- Secret modes: inline (demo) / `.env` (default) / OS keyring — snippets never write credentials to disk

## Regenerating `commands.json`

Stdlib Python 3 only. No virtualenv.

**Order matters.** `parse.py` rebuilds from intermediates and **drops** DCN /
modern-ops / thin-vendor fills unless those passes run next.

```bash
cd scripts
python3 parse.py
python3 merge_dcn_corpus.py    # if CLI_WORK_DCN_CORPUS is set
python3 parse_modern.py
python3 expand_thin_vendors.py
python3 fix_coverage_gaps.py
python3 clean_titles.py
python3 audit_data_quality.py
python3 check_consistency.py
python3 deep_gap_dig.py
# optional Automate templates (idempotent)
python3 patch_yang_stack_vendors.py
python3 patch_yang_more_vendors.py
```

Then:

```bash
node tests/stress_test.js
```

`check_consistency.py` asserts these figures still appear verbatim in
`README.md` and `docs/index.html`:

- total `70,006`
- roles `43,008` router / `22,848` switch / `4,150` firewall
- `17 vendor`

## GitHub Pages

`.github/workflows/pages.yml` stages a lean `_site/`:

- app: `index.html`, `commands.json`, `studio.html`, `studio-data.json`, `404.html`
- docs: `docs/` (this runbook included)
- tests: browser stress harness
- `.nojekyll` — **required**. Ansible `{{ }}` in snippets trips Jekyll Liquid.
- `scripts/*.json` source dumps stay unpublished.

One-time repo setting (cannot be flipped via API): **Settings → Pages → Source → GitHub Actions**.

## Pitfalls

1. `file://` looks empty — serve over HTTP.
2. `parse.py` last without the fill scripts → corpus shrinks and CI fails.
3. Missing `.nojekyll` → Pages build dies on Jinja.
4. Full-repo Pages artifact → deploy timeout. Use the lean `_site/` workflow.
5. Stale vendor tables in README that `check_consistency.py` does **not** gate (it only checks total / roles / vendor-count phrase). Recompute from `commands.json` when editing the table.

## Open corpus work

- SONiC is the thinnest vendor (459). Path: `expand_thin_vendors.py`.
- Classic Nokia SR OS is still a thin overlay next to SR Linux.
- Studio golden-path already covers both; the 18 MB JSON is the remaining gap.
