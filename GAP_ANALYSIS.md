# Gap analysis + improvement plan

Verifiable scan of `gesh75/multivendor-cli-configurator` on
`cursor/gap-scan-multivendor-cli-configurator-d2db` (base `main` @ `a57fd5a`).
Stdlib Python + Node only. No corpus rewrite. No dependency upgrades.

## Method (what was proved)

| Check | Command | Result |
|---|---|---|
| Docs ↔ corpus totals/roles | `python3 scripts/check_consistency.py` | **pass** (totals). Vendor **table** was stale — see P0-2. |
| Data-quality audit | `python3 scripts/audit_data_quality.py` | **pass** (0 cmd-prose / title-prose / long titles) |
| Coverage floors | `python3 scripts/deep_gap_dig.py` | **pass** (0 critical). Advisory: 945 empty `desc`. |
| Script compile | `python3 -m compileall scripts` | **pass** |
| Node stress + correctness | `node tests/stress_test.js` | run after the three fixes below |
| Vendor/cat recount | `Counter` over `commands.json` (70,006 rows) | README table + category line drifted |

`commands.json` is internally consistent: 17 vendors, 21 OS labels, 0 empty
`title`/`cmd`, 0 duplicate `(vendor, cmd)` pairs, 0 missing required keys.

## P0 — fix now (file + evidence)

### P0-1 · Broken Automate snippet (correctness) — **fixed in this PR**

- **File:** `index.html` (Cisco `AUTO_OSPF` `ncclient` template, was line 2067)
- **Evidence:** generated Python was
  `manager.connect(host=..., port=port=830,, username=...)`.
  That is a `SyntaxError` if a user copies the Automate drawer. Sibling
  templates (e.g. `AUTO_STATIC` at line 1955) omit `port` and do not double
  the comma. No existing test scanned snippet source.
- **Fix:** drop the broken `port=port=830,,` fragment; add a smoke check in
  `tests/stress_test.js` that fails on `port=port`, `,,`, or `==` inside
  `manager.connect(` lines.

### P0-2 · README vendor table drifted off `commands.json` (docs + missing gate) — **fixed in this PR**

- **File:** `README.md` (vendor table, lines 80–97) vs `commands.json`
- **Evidence:** `check_consistency.py` only asserted the **total** `70,006`,
  role counts, and the phrase `17 vendor`. `docs/DEVELOP.md` already called
  this out as an unguarded pitfall. Recount:

  | Vendor | README claimed | Corpus |
  |---|---:|---:|
  | Cisco | 22,145 | **22,168** (+23) |
  | Extreme | 2,790 | **2,800** (+10) |
  | Nokia | 1,125 | **1,131** (+6) |
  | *(table sum)* | 69,967 | **70,006** |

  Category one-liner was also stale (Interfaces 17,490 vs **16,941**, etc.).
- **Fix:** rewrite the three vendor cells and the top-10 category line from
  the live corpus. `check_consistency.py` now regex-matches each
  `| **Vendor** | … | N |` row in README.

### P0-3 · User-facing hero banner still said 52,031 (docs) — **fixed in this PR**

- **File:** `docs/assets/hero.svg` (README + docs landing banner)
- **Evidence:** `<desc>` and the on-art counter still read `52,031 commands`
  while `docs/index.html` (same illustration, inlined) and every gated
  figure say `70,006`. `check_consistency.py` does not read SVG.
- **Fix:** `52,031` → `70,006` in the two strings. No new gate (SVG
  phrasing is advisory, same as the rounded `70,000+` form).

No other P0 found: `deep_gap_dig.py` is green, no secret files / API keys,
`.nojekyll` is present, Pages inventory files all exist.

## P1 — next (small, evidence-backed)

1. **Buildkite PR check fails with no in-repo pipeline.**
   `buildkite/multivendor-cli-configurator` failed this PR in ~2s
   (build #15) and also failed merged PR #13; `main` build #11 passed.
   There is no `.buildkite/` / `pipeline.yml` in the repo. GitHub Actions
   `ci.yml` is the real gate and is green on this branch. Either add a
   checked-in pipeline or drop the required Buildkite context on pull_request.
2. **`tests/STRESS_TEST.md` is a 52,313-row report.** Header, vendor table,
   and timings predate the 70,006 corpus. `tests/stress_test_results.json`
   was later refreshed; the markdown was not. Misleading for anyone
   reproducing CI.
3. **`scripts/deep_gap_dig.py` is not a CI job.** `.github/workflows/ci.yml`
   runs `check_consistency.py` + `tests/stress_test.js` only. The Node suite
   already duplicates most floors, so this is a second gate, not a hole —
   wire it only if you want a Python-only path.
4. **945 empty `desc` fields** (`deep_gap_dig.py` warning): VyOS 742, FRR 170,
   Cisco 29, SONiC 4. Not quarantined (cmd/title are intact). Fill or
   generate from `title` if Studio/cheatsheet empty-state bothers you.
5. **`scripts/parse.py` will silently rewrite `commands.json`** from
   intermediates and **drop** DCN / modern-ops / thin-vendor fills if those
   passes are skipped (`docs/DEVELOP.md` pitfall #2). No
   `--dry-run` / refuse-if-shrink guard. Smallest fix: refuse to write if
   `len(cmds)` is below the current file’s length unless `--force`.
6. **`scripts/merge_dcn_corpus.py` defaults `CLI_WORK_DCN_CORPUS` to a
   personal `~/02_Projects/Network_Automation/...` path.** Fine as an
   override, confusing as a default. Point the default at
   `scripts/sources/` (gitignored) or require `--source`.
7. **Category / overlay counts are still unguarded.** This PR synced the
   README one-liner; `check_consistency.py` does not pin
   `Interfaces 16,941` etc. Add only if the line keeps drifting.
8. **SONiC (459) and classic SR OS (72) stay at the floor.** Known product
   gap (`CHANGELOG.md` / `docs/DEVELOP.md`). Out of scope here.

## P2 — later / laziness

- **Duplicate architecture docs:** root `ARCHITECTURE.md` and
  `docs/ARCHITECTURE.md` are byte-identical (134 lines). Pages copies the
  root file; README links `docs/ARCHITECTURE.md`. Pick one.
- **`configurator.html` still ships in the Pages artifact**
  (`.github/workflows/pages.yml`) while README says it is archive-only and
  unlinked. Drop it from `_site/` or leave it.
- **`.gitignore` still lists `demo/node_modules/`, `demo/package*.json`,
  `demo/page@*.webm`** — the `demo/` tree is gone.
- **Stress-test labels still say “29.5K rows”** (`tests/stress_test.js`
  T3 name). Cosmetic.
- **`hostkey_verify=False` in every ncclient snippet** — demo-only, but
  easy to paste onto a real box. A one-line comment already exists in
  places; not a secret leak.
- **Browser harness (`tests/stress_test.html`) is not in CI.** Node suite
  covers the extractable functions; IDB/boot timings stay manual.
- No `SECURITY.md` / `CODEOWNERS` / Dependabot (there are no npm deps).

## Dead code / do not delete without a reason

| Path | Verdict |
|---|---|
| `configurator.html` | Explicit archive. Keep in git; optional Pages drop (P2). |
| `scripts/*.json` intermediates | Pipeline inputs. Unpublished (Pages comment). Keep. |
| Duplicate `ARCHITECTURE.md` | Safe to collapse later. |
| `demo/` gitignore entries | Safe to delete. |

## What this PR changed (≤3 concrete fixes)

1. Repair the OSPF ncclient snippet + snippet-syntax smoke test.
2. Sync README vendor/category figures and gate the vendor table in
   `check_consistency.py`.
3. Correct `docs/assets/hero.svg` from 52,031 → 70,006.

## Skipped (out of scope)

- Regenerating `commands.json` or growing SONiC / SR OS.
- Filling 945 empty descriptions.
- Adding `deep_gap_dig.py` as a third CI job (already covered by Node).
- Deleting `configurator.html` or merging the two architecture files.
- Browser / Playwright coverage of `index.html` / `studio.html`.
- Dependency upgrades (none broken; UI has zero npm).

## Next recommended agent job

Add a `--dry-run` / refuse-if-shrink guard to `scripts/parse.py` so a
partial pipeline cannot silently overwrite the 70,006-row corpus.
