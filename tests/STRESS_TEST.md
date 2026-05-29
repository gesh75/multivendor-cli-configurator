# v2 Feature Stress Test Report

> Generated against the real **52,313-row** `commands.json` corpus
> (29,509 original + 22,804 merged from the DCN tool's
> `cli-export.json`, adding Microsoft/PowerShell, Linux, and Wireshark
> and back-filling Arista/Huawei/Aruba/FRR/VyOS/FortiOS).
> Last run: **2026-05-27** on macOS / Node v25.8 / Apple Silicon.

Two harnesses cover the v2 surface:

1. **Node** — pure-JS function benchmarks (`tests/stress_test.js`). Extracts
   `extractPlaceholders`, `substitutePlaceholders`, `lookupConcept`, and the
   `CONCEPT_SYNONYMS` table directly from `index.html`, then exercises them
   against the production data file. No mocking, no framework, just
   `process.hrtime.bigint()` + `assert`.
2. **Browser** — `tests/stress_test.html`. Exercises IndexedDB round-trip and
   cold/warm boot via a hidden iframe loading `/index.html`. Open in the
   dev-server tab to run.

## How to reproduce

```bash
cd /tmp/cli-work

# 1. Node test suite (pure JS, no browser needed)
node tests/stress_test.js
# → writes tests/stress_test_results.json + exits non-zero on failure

# 2. Browser test suite (IDB + boot timings)
python3 -m http.server 8765 &
open http://127.0.0.1:8765/tests/stress_test.html
# → results render in-page and on window.__STRESS_RESULTS
```

## Node-side results (median of 5 runs)

| # | Test                                              | Target           | Actual    | Pass |
|---|---------------------------------------------------|------------------|-----------|------|
| 3 | Filter 52,313 rows by `vendor=Cisco`              | < 50 ms          | **0.74 ms** | ✅ |
| 4 | Filter by vendor + cat + role (3-way)             | < 50 ms          | **0.38 ms** | ✅ |
| 5 | Free-text search (`bgp neighbor`, 2 tokens AND)   | < 80 ms          | **18.78 ms** | ✅ |
| 6 | `lookupConcept()` against 52,313 rows             | < 1500 ms total  | **1384 ms** (~26 µs/row, **18,253 tagged**) | ✅ |
| 6b| `lookupConcept()` correctness on canonical inputs | 10 / 10          | **10 / 10** | ✅ |
| 9 | `groupQueueByVendor()` on 4-row queue             | < 5 ms           | **< 0.01 ms** | ✅ |
|10a| `extractPlaceholders()` × 1000                    | < 50 ms          | **1.70 ms** | ✅ |
|10b| `substitutePlaceholders()` × 1000                 | < 50 ms          | **0.65 ms** | ✅ |
|10c| `substitutePlaceholders()` correctness            | 4 / 4            | **4 / 4** | ✅ |

**Result: ALL TESTS PASSED.** Raw timings in `tests/stress_test_results.json`.

## Corpus parity check

All **17** vendors present in the merged `commands.json`:

| Vendor    | Rows  |   | Vendor    | Rows  |
|-----------|-------|---|-----------|-------|
| Arista    | 7,434 |   | FortiOS   | 2,376 |
| VyOS      | 6,286 |   | NVIDIA    | 1,149 |
| Cisco     | 4,551 |   | PAN-OS    | 1,217 |
| Huawei    | 4,406 |   | Mikrotik  | 1,209 |
| Microsoft | 3,352 |   | Nokia     | 1,053 |
| FRR       | 3,963 |   | SONiC     |   445 |
| Juniper   | 3,277 |   | Wireshark | 2,130 |
| Extreme   | 2,781 |   | Linux     | 2,591 |
| Aruba     | 4,093 |   |           |       |
| **TOTAL** | **52,313 rows · 17 vendors** | | |

FRR provenance: **3,963 total / 870 `live` / 1,708 `in_docs`**. The extra
FRR rows came from the DCN tool's expanded scrape and are tagged neither
`live` nor `in_docs` so the badge counter on the UI stays accurate.

## Browser-side targets (open `stress_test.html` to verify)

| # | Test                                              | Target           |
|---|---------------------------------------------------|------------------|
| 1 | Cold boot — empty IndexedDB, fetch + parse 9.5 MB | < 2500 ms        |
| 2 | Warm boot — IDB cache hit + ETag revalidate        | < 600  ms        |
|11 | IDB write+read round-trip on ~10 MB payload       | < 600  ms        |

When run on the same Apple Silicon machine the iframe boot tests typically
finish at **~1.2 s cold / ~0.25 s warm** and IDB at **~80 ms**, but exact
numbers depend on the browser engine and disk so we don't claim a hard number
here — the targets above are the gate.

## Bugs found and fixed during the stress run

Two ordering bugs in `CONCEPT_SYNONYMS` surfaced from the correctness suite
and were fixed in-place (substring-AND patterns are order-sensitive):

1. `"undo shutdown"` matched `iface-shutdown` before `iface-noshut`
   because `"shutdown"` is a substring. Fixed by moving `iface-noshut`
   above `iface-shutdown`.
2. `"ip route 0.0.0.0 ..."` matched `static-route` before `default-route`
   because `["ip route","."]` fires on any IP. Fixed by moving
   `default-route` above `static-route`.

Both have explicit comments in `index.html` documenting the ordering
constraint so future edits don't silently regress.
