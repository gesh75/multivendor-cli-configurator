# Gap analysis

Verifiable scan of `gesh75/multivendor-cli-configurator` at `a57fd5a`
(plus the three small fixes in this PR). Ranked by blast radius, not
ambition. Out of scope: corpus growth, dependency upgrades, Studio
rewrites, new product features.

## Method (what was proved)

| Check | Result |
|---|---|
| `python3 scripts/check_consistency.py` | totals / roles / `17 vendor` match `commands.json` (70,006) |
| `python3 scripts/audit_data_quality.py` | 0 cmd-prose, 0 title-prose, 0 over-long titles |
| `python3 scripts/deep_gap_dig.py` | 0 critical; 945 empty `desc`; OS/cat/Automate floors hold |
| Corpus integrity (`commands.json`) | 17 vendors, 21 OS labels, 0 empty required fields except `desc`, 0 duplicate `(vendor, cmd)` |
| `.github/workflows/ci.yml` | only `check_consistency.py` + `tests/stress_test.js` |
| Grep of Automate `ncclient` templates | one invalid Python connect line (fixed here) |
| `tests/` vs public surfaces | Node suite extracts from `index.html` only; `studio.html` untested |

What was **not** run (skipped on purpose): full `parse.py` regen (needs
gitignored `scripts/sources/` + fill order; documented foot-gun),
browser IDB harness (`tests/stress_test.html`), live FRR lab capture,
secret scanners beyond repo grep, dependency upgrades.

---

## P0 — fix or gate now

### P0-1 · Automate OSPF snippet is invalid Python

- **File:** `index.html` (AUTO_OSPF → Cisco → `ncclient`, ~line 2067)
- **Evidence:** the template literal is
  `port=port=830,,` — SyntaxError if pasted. Neighbor templates on the
  same page use `port=830,`. No test extracted or parsed Automate
  snippets, so CI was green.
- **Fix in this PR:** correct the connect args; add a Node assertion
  that `index.html` does not contain `port=port=` or `,\s*,` in
  `manager.connect(...)` lines.

### P0-2 · CLI Studio has no automated test

- **Files:** `studio.html`, `studio-data.json`, `tests/stress_test.js`
- **Evidence:** `tests/stress_test.js` only `readFileSync`s `index.html`
  + `commands.json`. Grep of `tests/` for `studio` is empty. Studio is
  a shipped Pages surface (`pages.yml` copies both files; sitemap
  priority 0.9).
- **Not fixed here** (would be a new harness, not a one-line safe
  patch). Recommended next job below.

---

## P1 — next agent / small follow-ups

### P1-1 · README vendor + category table drifted; CI did not see it

- **Files:** `README.md` lines 80–101; `scripts/check_consistency.py`
- **Evidence (pre-fix):** `commands.json` vs README

  | Field | README (was) | `commands.json` |
  |---|---:|---:|
  | Cisco | 22,145 | 22,168 |
  | Extreme | 2,790 | 2,800 |
  | Nokia | 1,125 | 1,131 |
  | Interfaces | 17,490 | 16,941 |
  | Protocols | 10,173 | 10,150 |
  | System | 7,815 | 7,705 |
  | Troubleshooting | 6,513 | 6,501 |
  | Security | 4,369 | 4,370 |
  | VLAN | 4,208 | 4,084 |
  | Routing | 2,806 | 2,793 |
  | BGP | 2,153 | 2,155 |
  | OSPF | 1,604 | 1,606 |
  | VXLAN | 255 | 257 |
  | EVPN | 498 | 499 |

  `docs/DEVELOP.md` already names this: the checker “only checks total /
  roles / vendor-count phrase.” Totals still matched, so CI passed.
- **Fix in this PR:** sync the README figures; gate per-vendor and
  top-10 + VXLAN/EVPN counts in `check_consistency.py` for `README.md`
  only (`docs/index.html` does not restated those cells).

### P1-2 · Quality scripts exist but are not CI jobs

- **Files:** `.github/workflows/ci.yml`; `scripts/deep_gap_dig.py`;
  `scripts/audit_data_quality.py`
- **Evidence:** CI YAML has two jobs. `ARCHITECTURE.md` / `docs/DEVELOP.md`
  list `deep_gap_dig.py` as a regen gate. `audit_data_quality.py`
  **always exits 0** even if it finds prose (report-only). The Node
  suite already duplicates most deep-gap floors, so this is coverage
  duplication, not a current red check.

### P1-3 · CHANGELOG claims an AEGIS pre-change gate Studio does not have

- **Files:** `CHANGELOG.md` (“AEGIS-style pre-change (risk, blast,
  rollback) · Harden tab”); `studio.html` `runLint()` / `TITLES.lint`
- **Evidence:** `runLint()` is seven regex heuristics (NTP / AAA / SSH /
  syslog / BGP / BFD / secret). No blast-radius or rollback UI. The
  lint lede itself says “Heuristic lint before AEGIS”.

### P1-4 · Studio vendor labels diverge from the 70k corpus

- **File:** `studio-data.json`
- **Evidence:** Studio vendors include `Fortinet` (6) and `Palo Alto`
  (5). Corpus labels are `FortiOS` and `PAN-OS`. Migrate / coverage
  therefore cannot align those rows with cheatsheet filters.

### P1-5 · Studio Migrate “Copy” copies the diff, not the target CLI

- **File:** `studio.html` `runMigrate()` + `bindCards()`
- **Evidence:** the button sets `data-copy="${esc(body)}"` but
  `bindCards` copies `pre.cli.textContent`, which is the unified diff.

### P1-6 · `parse_extras.py` hard-codes a laptop path

- **File:** `scripts/parse_extras.py` `DEFAULT_DOCS`
- **Evidence:** default is
  `/Users/georgigaydarov/02_Projects/Network_Automation/.../06_Documentation`.
  Overridable via `CLI_WORK_DOCS` / `--source`, but a cold clone fails
  closed with a username in-tree.

### P1-7 · `parse.py` last without fill scripts shrinks the corpus

- **Files:** `scripts/parse.py` (writes `commands.json`); `docs/DEVELOP.md`
  pitfall #2
- **Evidence:** `parse.py` rebuilds from intermediates and does not
  apply `parse_modern.py` / `expand_thin_vendors.py` /
  `fix_coverage_gaps.py`. Running it alone is a foot-gun; no CI job
  regenerates, so this is DX, not a live break.

---

## P2 — later / delete or ignore

| Gap | Evidence | Bias |
|---|---|---|
| Duplicate `ARCHITECTURE.md` vs `docs/ARCHITECTURE.md` | `diff` is empty; image `docs/img/architecture.svg` is correct from repo root, **broken** from `docs/` (would resolve `docs/docs/img/...`) | delete one or symlink; fix the docs-relative image |
| `tests/STRESS_TEST.md` still says **52,313** rows (2026-05-27) | file header + vendor table (Cisco 4,551) vs live 70,006 / Cisco 22,168 | rewrite from `stress_test_results.json` or delete the frozen table |
| `tests/stress_test.js` comments say “29,509-row corpus” | line 3 | comment-only |
| Legacy `configurator.html` still in Pages artifact | `pages.yml` `cp` list; README says “not linked from the live site” | drop from `_site/` (keep in git) |
| 945 empty `desc` | `deep_gap_dig.py` warning | fill later; do not block |
| Studio Netmiko `device_type` only special-cases junos / eos / nxos | `studio.html` `snippets()` else `cisco_ios` | map from `OS_DEV_TYPE` or drop the claim |
| No offline service worker for Studio | `CHANGELOG.md` “Still open” | skip unless someone asks |
| Thin SONiC (459) / SR OS (72) | floors pass; CHANGELOG already tracks | corpus work, not this scan |

---

## Fixes in this PR (≤3, all safe)

1. Repair `AUTO_OSPF` Cisco `ncclient` connect args in `index.html`.
2. Gate snippet syntax in `tests/stress_test.js` so P0-1 cannot regress.
3. Sync README vendor/category figures and extend
   `check_consistency.py` so that table cannot drift again.

No drive-by refactors. No `parse.py` regen. `configurator.html` left
alone (archive).

---

## Recommended next agent job

Add a Node smoke harness that loads `studio-data.json` (schema + vendor
label parity with `commands.json`) and extracts `lookupConcept` /
`runLint` / migrate-copy from `studio.html` — do not grow the 70k
corpus.
