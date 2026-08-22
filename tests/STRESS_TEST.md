# Feature stress test

Node + browser harnesses for the live `commands.json` corpus
(**70,006** rows · **17** vendors · **21** OS labels). Last Node run:
**2026-08-22** in CI-equivalent `node tests/stress_test.js` (all passed).

Two harnesses cover the surface:

1. **Node** — `tests/stress_test.js`. Extracts `extractPlaceholders`,
   `substitutePlaceholders`, `lookupConcept`, `CONCEPT_SYNONYMS`,
   `NETMIKO_DEV_TYPE`, `OS_DEV_TYPE`, and `ANSIBLE_MOD` from `index.html`,
   then benches them against the production corpus. Also asserts OS/cat
   floors and Automate vendor coverage (no silent Cisco fallback).
   `process.hrtime.bigint()` + `assert`. **This is a CI job**
   (`.github/workflows/ci.yml`).
2. **Browser** — `tests/stress_test.html`. IndexedDB round-trip and
   cold/warm boot via a hidden iframe loading `/index.html`. Manual only.

## How to reproduce

```bash
# From the repo root (not /tmp)

# 1. Node suite — same command CI runs
node tests/stress_test.js
# → writes tests/stress_test_results.json + exits non-zero on failure

# 2. Browser suite (IDB + boot timings)
python3 -m http.server 8000
# open http://127.0.0.1:8000/tests/stress_test.html
# → results render in-page and on window.__STRESS_RESULTS
```

`file://` cannot load `commands.json`; serve over HTTP. See
[docs/DEVELOPER.md](../docs/DEVELOPER.md).

## Node-side results (median of 5 runs, 2026-08-22)

| # | Test | Target | Actual | Pass |
|---|---|---|---|---|
| 3 | Filter 70,006 rows by `vendor=Cisco` | < 50 ms | **1.24 ms** | ✅ |
| 4 | Filter by vendor + cat + role (3-way) | < 50 ms | **0.67 ms** | ✅ |
| 5 | Free-text search (`bgp neighbor`, 2 tokens AND) | < 80 ms | **16.72 ms** | ✅ |
| 6 | `lookupConcept()` against 70,006 rows | < 1800 ms | **461 ms** (16,987 tagged) | ✅ |
| 6b | `lookupConcept()` correctness on canonical inputs | 10 / 10 | **10 / 10** | ✅ |
| 9 | `groupQueueByVendor()` on 4-row queue | < 5 ms | **< 0.01 ms** | ✅ |
| 10a | `extractPlaceholders()` × 1000 | < 50 ms | **1.39 ms** | ✅ |
| 10b | `substitutePlaceholders()` × 1000 | < 50 ms | **1.09 ms** | ✅ |
| 10c | `substitutePlaceholders()` correctness | 4 / 4 | **4 / 4** | ✅ |

`lookupConcept` used to take ~2.9 s; the 2026-07 index rewrite brought it
under 500 ms on this corpus. The CI gate stays at 1800 ms so a laptop
runner still passes.

**Result: ALL TESTS PASSED.** Machine-specific timings also land in
`tests/stress_test_results.json` (rewritten every run).

## Corpus parity (from the same run)

| Vendor | Rows | Vendor | Rows |
|---|---|---|---|
| Cisco | 22,168 | FortiOS | 2,383 |
| Arista | 7,397 | Linux | 2,592 |
| VyOS | 6,289 | Wireshark | 2,130 |
| Huawei | 4,425 | PAN-OS | 1,224 |
| Aruba | 4,106 | Mikrotik | 1,216 |
| FRR | 3,949 | NVIDIA | 1,168 |
| Microsoft | 3,352 | Nokia | 1,131 |
| Juniper | 3,217 | SONiC | 459 |
| Extreme | 2,800 | | |
| **TOTAL** | | | **70,006 · 17 vendors** |

FRR provenance: **3,949 total / 870 `live` / 1,705 `in_docs`**.

Overlay / OS floors asserted by the suite (and by
`scripts/deep_gap_dig.py`): NX-OS 200 · IOS-XE 125 · SR OS 72 · SONiC 459
· VXLAN 257 · EVPN 499 · Spanning-Tree 845 · EtherChannel 518 · BFD 133.

## Browser-side targets (open `stress_test.html`)

| # | Test | Target |
|---|---|---|
| 1 | Cold boot — empty IndexedDB, fetch + parse ~18 MB | < 2500 ms |
| 2 | Warm boot — IDB cache hit + ETag revalidate | < 600 ms |
| 11 | IDB write+read round-trip on the payload | < 600 ms |

Numbers depend on the browser engine and disk. On a fast laptop these
typically land well under the gates (~1.2 s cold / ~0.25 s warm / ~80 ms
IDB when the file was ~10 MB). Re-measure after a corpus jump.

## Ordering bugs the suite exists to protect

`CONCEPT_SYNONYMS` is order-sensitive (first substring-AND match wins):

1. `"undo shutdown"` must hit `iface-noshut` before `iface-shutdown`.
2. `"ip route 0.0.0.0 ..."` must hit `default-route` before `static-route`.

Both have comments in `index.html`. Do not reorder those entries without
updating `tests/stress_test.js`.
