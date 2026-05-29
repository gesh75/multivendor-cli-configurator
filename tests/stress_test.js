#!/usr/bin/env node
/* Stress test for v2 features.
 * Extracts pure-JS function bodies from index.html and exercises them
 * against the real 29,509-row corpus. DOM/IndexedDB tests live in
 * stress_test.html (browser-only). Exits non-zero on any failure. */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, 'commands.json'), 'utf8'));

console.log(`Corpus: ${DATA.length} rows`);

// --- Extract slices from index.html ----------------------------------------
function slice(startRe, endRe) {
  const s = html.search(startRe);
  if (s < 0) throw new Error('start not found: ' + startRe);
  const tail = html.slice(s);
  const e = tail.search(endRe);
  if (e < 0) throw new Error('end not found: ' + endRe);
  return tail.slice(0, e);
}

// Pull everything we need by evaluating sections in a sandboxed scope.
const sandbox = {};
function include(re_start, re_end_inclusive) {
  // Slice from start to (and including) the line matching re_end.
  const s = html.search(re_start);
  if (s < 0) throw new Error('not found: ' + re_start);
  const tail = html.slice(s);
  const m = tail.match(re_end_inclusive);
  if (!m) throw new Error('end not found: ' + re_end_inclusive);
  const code = tail.slice(0, m.index + m[0].length);
  return code;
}

// Simpler approach: grab each block by line range from anchors.
function sliceLines(startRe, endRe, endInclusive = true) {
  const lines = html.split('\n');
  let s = -1, e = -1;
  for (let i = 0; i < lines.length; i++) {
    if (s < 0 && startRe.test(lines[i])) { s = i; continue; }
    if (s >= 0 && endRe.test(lines[i])) { e = endInclusive ? i + 1 : i; break; }
  }
  if (s < 0 || e < 0) throw new Error('slice not found: ' + startRe + ' ... ' + endRe);
  return lines.slice(s, e).join('\n');
}

const code = [
  html.match(/^const PLACEHOLDER_RE = \/.*\/g;$/m)[0],
  sliceLines(/^function extractPlaceholders\(/, /^}$/),
  sliceLines(/^function substitutePlaceholders\(/, /^}$/),
  sliceLines(/^const CONCEPT_SYNONYMS = \[/, /^\];$/),
  sliceLines(/^function lookupConcept\(/, /^}$/),
  sliceLines(/^const NETMIKO_DEV_TYPE = \{/, /^\};$/),
  // export to sandbox
  'this.extractPlaceholders=extractPlaceholders;',
  'this.substitutePlaceholders=substitutePlaceholders;',
  'this.lookupConcept=lookupConcept;',
  'this.CONCEPT_SYNONYMS=CONCEPT_SYNONYMS;',
  'this.NETMIKO_DEV_TYPE=NETMIKO_DEV_TYPE;',
].join('\n');

// Execute slice in sandbox
const vm = require('vm');
const ctx = vm.createContext(sandbox);
vm.runInContext(code, ctx);

const { extractPlaceholders, substitutePlaceholders, lookupConcept, CONCEPT_SYNONYMS, NETMIKO_DEV_TYPE } = sandbox;
assert(typeof lookupConcept === 'function', 'lookupConcept extracted');
assert(typeof extractPlaceholders === 'function', 'extractPlaceholders extracted');
console.log(`Extracted: ${CONCEPT_SYNONYMS.length} concepts, ${Object.keys(NETMIKO_DEV_TYPE).length} netmiko types`);

// --- Bench helper ----------------------------------------------------------
function bench(name, fn, iters = 1) {
  const samples = [];
  for (let i = 0; i < 5; i++) {
    const t0 = process.hrtime.bigint();
    for (let j = 0; j < iters; j++) fn();
    const t1 = process.hrtime.bigint();
    samples.push(Number(t1 - t0) / 1e6);
  }
  samples.sort((a, b) => a - b);
  return samples[2]; // median of 5
}

const results = {};
let failures = 0;
function check(name, target, actual) {
  const pass = actual < target;
  if (!pass) failures++;
  results[name] = { target_ms: target, actual_ms: +actual.toFixed(2), pass };
  console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}: ${actual.toFixed(2)}ms (target <${target}ms)`);
}

// --- T3: Filter by vendor=Cisco --------------------------------------------
{
  const t = bench('vendor-filter', () => {
    const r = DATA.filter(d => d.vendor === 'Cisco');
    if (r.length === 0) throw new Error('empty');
  });
  check('T3 vendor filter (29.5K rows)', 50, t);
}

// --- T4: 3-way filter -------------------------------------------------------
{
  const t = bench('triple-filter', () => {
    DATA.filter(d => d.vendor === 'Juniper' && d.cat === 'BGP' && d.role === 'router');
  });
  check('T4 vendor+cat+role filter', 50, t);
}

// --- T5: Free-text search ---------------------------------------------------
{
  const tokens = ['bgp', 'neighbor'];
  const t = bench('text-search', () => {
    DATA.filter(d => {
      const h = (d.title + ' ' + d.cmd + ' ' + d.desc).toLowerCase();
      return tokens.every(tok => h.includes(tok));
    });
  });
  check('T5 free-text search "bgp neighbor"', 80, t);
}

// --- T6: lookupConcept over full corpus -------------------------------------
{
  let hits = 0;
  const t = bench('concept-lookup-30k', () => {
    hits = 0;
    for (const d of DATA) {
      const c = lookupConcept(d.title + ' ' + d.cmd);
      if (c) hits++;
    }
  });
  check('T6 lookupConcept × full corpus', 1800, t);
  console.log(`   → ${hits} concept-tagged rows`);
  results['T6_concept_hits'] = hits;
}

// --- T6b: lookupConcept correctness ----------------------------------------
const conceptCases = [
  { in: 'router bgp 65001 neighbor 10.0.0.2 remote-as 65002', want: 'bgp-peer' },
  { in: 'standby 1 ip 10.0.0.1', want: 'fhrp-vip' },
  { in: 'set vrrp-group 1 virtual-address 10.0.0.1', want: 'fhrp-vip' },
  { in: 'display bgp peer', want: 'bgp-summary' },
  { in: 'show ip bgp summary', want: 'bgp-summary' },
  { in: 'undo shutdown', want: 'iface-noshut' },
  { in: 'switchport mode trunk', want: 'vlan-trunk' },
  { in: 'set system host-name r1', want: 'sys-hostname' },
  { in: 'ip route 0.0.0.0 0.0.0.0 1.1.1.1', want: 'default-route' },
  { in: 'snmp-server community public', want: 'snmp-host' },
];
let conceptOK = 0;
for (const c of conceptCases) {
  const r = lookupConcept(c.in);
  if (r && r.concept === c.want) conceptOK++;
  else console.log(`   MISS: "${c.in}" → ${r ? r.concept : 'null'} (wanted ${c.want})`);
}
console.log(`Concept correctness: ${conceptOK}/${conceptCases.length}`);
if (conceptOK < conceptCases.length) failures++;
results['T6b_concept_correctness'] = `${conceptOK}/${conceptCases.length}`;

// --- T10: extractPlaceholders / substitutePlaceholders ---------------------
{
  // Pick 1000 rows that actually have placeholders
  const phRows = [];
  for (const d of DATA) {
    if (/[\[<]/.test(d.cmd)) phRows.push(d);
    if (phRows.length >= 1000) break;
  }
  console.log(`PH sample: ${phRows.length} rows with placeholders`);
  const t = bench('extract-ph-1000', () => {
    for (const d of phRows) extractPlaceholders(d.cmd);
  });
  check('T10a extractPlaceholders × 1000', 50, t);

  const subVals = { 'IP': '10.0.0.1', 'VLAN_NO': '100', 'ASN': '65001', 'INTERFACE': 'eth0' };
  const t2 = bench('substitute-ph-1000', () => {
    for (const d of phRows) substitutePlaceholders(d.cmd, subVals);
  });
  check('T10b substitutePlaceholders × 1000', 50, t2);
}

// --- T10c: round-trip correctness ------------------------------------------
{
  const samples = [
    { in: 'interface [INTERFACE]\n ip address [IP] [MASK]', vals: { INTERFACE: 'eth0', IP: '10.0.0.1', MASK: '255.255.255.0' },
      want: 'interface eth0\n ip address 10.0.0.1 255.255.255.0' },
    { in: 'vlan <VLAN_NO>', vals: { VLAN_NO: '100' }, want: 'vlan 100' },
    { in: 'no placeholders here', vals: {}, want: 'no placeholders here' },
    // Missing value leaves placeholder intact
    { in: 'ip address [IP]', vals: {}, want: 'ip address [IP]' },
  ];
  let ok = 0;
  for (const s of samples) {
    const got = substitutePlaceholders(s.in, s.vals);
    if (got === s.want) ok++;
    else console.log(`   PH MISS: ${JSON.stringify(s.in)} → ${JSON.stringify(got)} (wanted ${JSON.stringify(s.want)})`);
  }
  console.log(`PH correctness: ${ok}/${samples.length}`);
  if (ok < samples.length) failures++;
  results['T10c_ph_correctness'] = `${ok}/${samples.length}`;
}

// --- T9 (logic only): groupQueueByVendor simulation ------------------------
// Compile path is mostly string concat; we benchmark the grouping step.
{
  // Build a fake 4-vendor queue (one row from each major vendor)
  const queue = [];
  for (const v of ['Cisco', 'Juniper', 'Arista', 'FRR']) {
    const r = DATA.find(d => d.vendor === v);
    if (r) queue.push(r);
  }
  const t = bench('group-queue-by-vendor', () => {
    const by = new Map();
    for (const d of queue) {
      if (!by.has(d.vendor)) by.set(d.vendor, []);
      by.get(d.vendor).push(d);
    }
  });
  check('T9 groupQueueByVendor (4 rows)', 5, t);
  results['T9_queue_vendors'] = queue.map(d => d.vendor);
}

// --- Vendor coverage smoke check -------------------------------------------
{
  const expected = ['Cisco','Juniper','Arista','FRR','VyOS','SONiC','NVIDIA','PAN-OS','Nokia','FortiOS','Mikrotik','Extreme','Aruba','Huawei','Microsoft','Linux','Wireshark'];
  const found = {};
  for (const d of DATA) found[d.vendor] = (found[d.vendor] || 0) + 1;
  let ok = 0;
  for (const v of expected) {
    if (found[v] > 0) ok++;
    else console.log(`   VENDOR MISS: ${v}`);
  }
  console.log(`Vendor coverage: ${ok}/${expected.length}`);
  if (ok < expected.length) failures++;
  results['vendor_coverage'] = found;
}

// --- FRR live flag smoke ----------------------------------------------------
{
  const frr = DATA.filter(d => d.vendor === 'FRR');
  const live = frr.filter(d => d.live === true);
  const docs = frr.filter(d => d.in_docs === true);
  console.log(`FRR: ${frr.length} total, ${live.length} live, ${docs.length} in_docs`);
  results['frr'] = { total: frr.length, live: live.length, in_docs: docs.length };
  if (frr.length === 0 || live.length === 0) failures++;
}

// --- Write results ---------------------------------------------------------
fs.writeFileSync(
  path.join(__dirname, 'stress_test_results.json'),
  JSON.stringify(results, null, 2)
);
console.log(`\nResults written to tests/stress_test_results.json`);
console.log(failures === 0 ? '\nALL TESTS PASSED' : `\n${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
