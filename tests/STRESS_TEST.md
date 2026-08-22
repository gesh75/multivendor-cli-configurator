# Feature stress test

> Exercises the **live** `commands.json` (currently **70,006** rows · **17** vendors)
> plus functions sliced out of `index.html`. Last Node refresh is checked into
> `tests/stress_test_results.json`. The same script is the CI `stress-test` job.

Two harnesses cover the surface:

1. **Node** — `tests/stress_test.js`. Extracts `extractPlaceholders`,
   `substitutePlaceholders`, `lookupConcept`, `CONCEPT_SYNONYMS`,
   `NETMIKO_DEV_TYPE`, `OS_DEV_TYPE`, and `ANSIBLE_MOD` from `index.html`, then
   runs them against the production corpus. No mocking. Exits non-zero on
   failure. Also asserts OS/cat floors and Automate vendor-map coverage (the
   same floors `scripts/deep_gap_dig.py` reports).
2. **Browser** — `tests/stress_test.html`. IndexedDB round-trip and cold/warm
   boot via a hidden iframe loading `/index.html`. **Not** in CI.

Developer setup and the other quality gates: [docs/DEVELOP.md](../docs/DEVELOP.md).

## How to reproduce

```bash
# from the repo root

# 1. Node suite (this is what CI runs)
node tests/stress_test.js
# → writes tests/stress_test_results.json + exits non-zero on failure

# 2. Browser suite (IDB + boot timings) — serve over HTTP
python3 -m http.server 8765
# open http://127.0.0.1:8765/tests/stress_test.html
# → results render in-page and on window.__STRESS_RESULTS
```

## Node-side targets

| # | Test | Target |
|---|---|---|
| 3 | Filter all rows by `vendor=Cisco` | < 50 ms |
| 4 | Filter by vendor + cat + role (3-way) | < 50 ms |
| 5 | Free-text search (`bgp neighbor`, 2 tokens AND) | < 80 ms |
| 6 | `lookupConcept()` against the full corpus | < 1800 ms |
| 6b | `lookupConcept()` correctness on canonical inputs | 10 / 10 |
| 9 | `groupQueueByVendor()` on 4-row queue | < 5 ms |
| 10a | `extractPlaceholders()` × 1000 | < 50 ms |
| 10b | `substitutePlaceholders()` × 1000 | < 50 ms |
| 10c | `substitutePlaceholders()` correctness | 4 / 4 |
| — | All 17 vendors present | 17 / 17 |
| — | FRR has `live` rows | > 0 |
| — | OS floors (`nxos`/`iosxe`/`sros`/`sonic`) | ≥ floors |
| — | Overlay cats (VXLAN/EVPN/STP/LACP/BFD) | ≥ floors |
| — | `OS_DEV_TYPE` / `ANSIBLE_MOD` cover every OS / vendor | no misses |
| — | OS-aware Netmiko `device_type` (nxos/xe/asa/sros/srl/ios) | 6 / 6 |
| — | `AUTO_*` maps include stack + more vendors (no Cisco fallback) | no misses |

Latest checked-in medians (see `stress_test_results.json`): vendor filter
**~0.9 ms**, 3-way filter **~0.7 ms**, text search **~17 ms**,
`lookupConcept` **~467 ms** (~17k concept-tagged rows).

## Corpus snapshot (from the last Node run)

| Vendor | Rows | Vendor | Rows |
|---|---|---|---|
| Cisco | 22,168 | FortiOS | 2,383 |
| Arista | 7,397 | Wireshark | 2,130 |
| VyOS | 6,289 | PAN-OS | 1,224 |
| Huawei | 4,425 | Mikrotik | 1,216 |
| Aruba | 4,106 | NVIDIA | 1,168 |
| FRR | 3,949 | Nokia | 1,131 |
| Microsoft | 3,352 | SONiC | 459 |
| Juniper | 3,217 | | |
| Extreme | 2,800 | | |
| Linux | 2,592 | | |
| **TOTAL** | | | **70,006 · 17 vendors** |

FRR provenance: **3,949** total / **870** `live` / **1,705** `in_docs`.
Rows tagged neither keep the UI live-badge counter honest.

Overlay cats in the same snapshot: VXLAN 257 · EVPN 499 · Spanning-Tree 845 ·
EtherChannel 518 · BFD 133.

## Browser-side targets (open `stress_test.html`)

| # | Test | Target |
|---|---|---|
| 1 | Cold boot — empty IndexedDB, fetch + parse ~18 MB | < 2500 ms |
| 2 | Warm boot — IDB cache hit + ETag revalidate | < 600 ms |
| 11 | IDB write+read round-trip on the corpus payload | < 600 ms |

On a fast local machine the iframe boot tests typically finish well under
those gates; exact numbers depend on the browser engine and disk so CI does
not claim a hard number — the targets above are the manual gate.

## Ordering bugs the suite still guards

Two `CONCEPT_SYNONYMS` ordering bugs (substring-AND is first-match-wins)
have fixtures so they cannot silently regress:

1. `"undo shutdown"` must match `iface-noshut` before `iface-shutdown`.
2. `"ip route 0.0.0.0 ..."` must match `default-route` before `static-route`.

Both have comments in `index.html` next to the table.
