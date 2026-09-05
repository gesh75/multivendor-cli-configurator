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

// --- Deep gap dig (OS floors, overlay cats, Automate / Netmiko maps) ---------
{
  const osCount = {};
  const catCount = {};
  for (const d of DATA) {
    osCount[d.os] = (osCount[d.os] || 0) + 1;
    catCount[d.cat] = (catCount[d.cat] || 0) + 1;
  }
  const osFloors = { nxos: 200, iosxe: 120, sros: 70, sonic: 450 };
  const catFloors = { VXLAN: 250, EVPN: 490, 'Spanning-Tree': 400, EtherChannel: 250, BFD: 100 };
  let gapFails = 0;
  for (const [os, floor] of Object.entries(osFloors)) {
    const n = osCount[os] || 0;
    const pass = n >= floor;
    if (!pass) { gapFails++; console.log(`   OS FLOOR MISS: ${os}=${n} < ${floor}`); }
    else console.log(`   OS floor ${os}: ${n} ≥ ${floor}`);
  }
  for (const [cat, floor] of Object.entries(catFloors)) {
    const n = catCount[cat] || 0;
    const pass = n >= floor;
    if (!pass) { gapFails++; console.log(`   CAT FLOOR MISS: ${cat}=${n} < ${floor}`); }
    else console.log(`   Cat floor ${cat}: ${n} ≥ ${floor}`);
  }

  // Extract OS_DEV_TYPE + ANSIBLE_MOD for coverage assertions
  const osDevCode = sliceLines(/^const OS_DEV_TYPE = \{/, /^\};$/);
  const ansibleCode = sliceLines(/^const ANSIBLE_MOD = \{/, /^\};$/);
  const autoGapSandbox = {};
  vm.runInContext(
    osDevCode + '\n' + ansibleCode + '\nthis.OS_DEV_TYPE=OS_DEV_TYPE;this.ANSIBLE_MOD=ANSIBLE_MOD;',
    vm.createContext(autoGapSandbox)
  );
  const { OS_DEV_TYPE, ANSIBLE_MOD } = autoGapSandbox;
  const missingOs = Object.keys(osCount).filter(o => !OS_DEV_TYPE[o]);
  if (missingOs.length) {
    gapFails++;
    console.log(`   OS_DEV_TYPE MISS: ${missingOs.join(',')}`);
  } else {
    console.log(`   OS_DEV_TYPE covers all ${Object.keys(osCount).length} OS labels`);
  }
  const vendors = [...new Set(DATA.map(d => d.vendor))];
  const missingAns = vendors.filter(v => !ANSIBLE_MOD[v]);
  if (missingAns.length) {
    gapFails++;
    console.log(`   ANSIBLE_MOD MISS: ${missingAns.join(',')}`);
  } else {
    console.log(`   ANSIBLE_MOD covers all ${vendors.length} vendors`);
  }

  // OS-aware Netmiko device types (critical gap from prior handoff)
  function devTypeFor(q) {
    return OS_DEV_TYPE[q.os] || NETMIKO_DEV_TYPE[q.vendor] || 'terminal_server';
  }
  const osDevCases = [
    { os: 'nxos', vendor: 'Cisco', want: 'cisco_nxos' },
    { os: 'iosxe', vendor: 'Cisco', want: 'cisco_xe' },
    { os: 'asa', vendor: 'Cisco', want: 'cisco_asa' },
    { os: 'sros', vendor: 'Nokia', want: 'nokia_sros' },
    { os: 'srlinux', vendor: 'Nokia', want: 'nokia_srl' },
    { os: 'ios', vendor: 'Cisco', want: 'cisco_ios' },
  ];
  let osDevOk = 0;
  for (const c of osDevCases) {
    const got = devTypeFor(c);
    if (got === c.want) osDevOk++;
    else { gapFails++; console.log(`   DEVTYPE MISS: ${c.os} → ${got} (wanted ${c.want})`); }
  }
  console.log(`OS-aware device_type: ${osDevOk}/${osDevCases.length}`);

  // Automate maps must include Huawei/NVIDIA/SONiC/Extreme/Mikrotik (no Cisco fallback)
  const moreVendors = ['Huawei', 'NVIDIA', 'SONiC', 'Extreme', 'Mikrotik', 'FRR', 'VyOS', 'Nokia', 'Aruba'];
  const autoMaps = ['AUTO_IFACE_IPV4', 'AUTO_BGP', 'AUTO_OSPF', 'AUTO_VLAN', 'AUTO_HOSTNAME'];
  for (const name of autoMaps) {
    const start = html.indexOf(`const ${name} = {`);
    if (start < 0) { gapFails++; console.log(`   AUTO MAP MISS: ${name}`); continue; }
    const chunk = html.slice(start, start + 14000);
    const end = chunk.indexOf('\n};');
    const body = end > 0 ? chunk.slice(0, end) : chunk;
    const missing = moreVendors.filter(v => !new RegExp(`(?:^|\\n)\\s*${v}\\s*:`).test(body));
    if (missing.length) {
      gapFails++;
      console.log(`   ${name} vendor gaps: ${missing.join(',')}`);
    } else {
      console.log(`   ${name}: stack+more vendors present`);
    }
  }

  // Generated ncclient snippets must be parseable Python (P0-1: port=port=830,,)
  const connectLines = html.split('\n').filter(l => /manager\.connect\(/.test(l));
  const badConnect = connectLines.filter(l => /port=port=/.test(l) || /,\s*,/.test(l));
  if (badConnect.length) {
    gapFails++;
    console.log(`   SNIPPET SYNTAX MISS: ${badConnect.length} manager.connect line(s)`);
    badConnect.slice(0, 3).forEach(l => console.log(`     ${l.trim()}`));
  } else {
    console.log(`   Automate connect snippets: ${connectLines.length} lines, no port=port= / double-comma`);
  }

  // No silent Cisco YANG fallback in AUTO renderers
  const badFb = (html.match(/\|\|AUTO_\w+\.Cisco\)\(v\)/g) || []).length;
  if (badFb) {
    gapFails++;
    console.log(`   Cisco silent-fallback still present: ${badFb}`);
  } else {
    console.log('   No silent AUTO_*.Cisco fallback');
  }

  // openAutomation must offer more than C/J/A for native mappings
  if (/\[\s*"Cisco"\s*,\s*"Juniper"\s*,\s*"Arista"\s*\]\.filter\(v => found\.mapping\.render/.test(html)) {
    gapFails++;
    console.log('   openAutomation still hardcodes Cisco/Juniper/Arista only');
  } else if (!html.includes('AUTO_VENDORS')) {
    gapFails++;
    console.log('   openAutomation missing AUTO_VENDORS list');
  } else {
    console.log('   openAutomation uses AUTO_VENDORS filter');
  }

  // Extreme must have Spanning-Tree after deep dig promotion
  const exStp = DATA.filter(d => d.vendor === 'Extreme' && d.cat === 'Spanning-Tree').length;
  if (exStp < 50) {
    gapFails++;
    console.log(`   Extreme Spanning-Tree too thin: ${exStp}`);
  } else {
    console.log(`   Extreme Spanning-Tree: ${exStp}`);
  }

  // Builder button discoverability
  if (!/id="btn-clibuilder"[^>]*>[\s\S]*?Builder/.test(html)) {
    gapFails++;
    console.log('   Builder navbar label missing');
  } else {
    console.log('   Builder navbar label present');
  }

  results['deep_gap_dig'] = {
    os: osCount,
    cats: Object.fromEntries(Object.keys(catFloors).map(k => [k, catCount[k] || 0])),
    os_dev_ok: `${osDevOk}/${osDevCases.length}`,
    gap_fails: gapFails,
  };
  console.log(`Deep gap dig failures: ${gapFails}`);
  if (gapFails) failures += gapFails;
}

// --- Write results ---------------------------------------------------------
fs.writeFileSync(
  path.join(__dirname, 'stress_test_results.json'),
  JSON.stringify(results, null, 2)
);
console.log(`\nResults written to tests/stress_test_results.json`);
console.log(failures === 0 ? '\nALL TESTS PASSED' : `\n${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
