'use strict';
// Long-form feature walkthrough. Designed to be resilient — every click has a
// 3-second fail-fast timeout, every drawer/modal has a forced JS-level close
// after use, and every section starts from a clean state.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = process.env.QA_BASE_URL || 'http://localhost:9127/index.html';
const VIDEO_DIR = path.join(__dirname);
const OUTPUT_NAME = 'multivendor-cli-demo.webm';

const CURSOR_SVG = 'data:image/svg+xml;utf8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5" stroke-linejoin="round"/></svg>'
);

async function injectOverlays(page) {
  await page.evaluate((svg) => {
    if (!document.getElementById('demo-cursor')) {
      const c = document.createElement('img');
      c.id = 'demo-cursor'; c.src = svg; c.alt = '';
      c.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;width:28px;height:28px;transition:left .08s linear,top .08s linear;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.45));left:40px;top:40px';
      document.body.appendChild(c);
      document.addEventListener('mousemove', (e) => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
    }
    if (!document.getElementById('demo-subtitle')) {
      const bar = document.createElement('div');
      bar.id = 'demo-subtitle';
      bar.style.cssText = 'position:fixed;bottom:34px;left:50%;transform:translateX(-50%);z-index:2147483645;text-align:center;padding:16px 32px;background:rgba(8,12,20,.92);color:#fff;font-family:-apple-system,"Segoe UI",Inter,Roboto,sans-serif;font-size:22px;font-weight:600;letter-spacing:.3px;border-radius:12px;border:1px solid rgba(34,211,238,.45);box-shadow:0 12px 36px rgba(0,0,0,.5);opacity:0;transition:opacity .25s;pointer-events:none;max-width:84vw;line-height:1.35';
      document.body.appendChild(bar);
    }
    if (!document.getElementById('demo-stepbadge')) {
      const badge = document.createElement('div');
      badge.id = 'demo-stepbadge';
      badge.style.cssText = 'position:fixed;top:18px;left:18px;z-index:2147483645;padding:8px 14px;background:linear-gradient(135deg,#22d3ee,#7c3aed);color:#fff;font-family:-apple-system,"Segoe UI",Inter,Roboto,sans-serif;font-size:13px;font-weight:700;letter-spacing:.5px;border-radius:999px;box-shadow:0 6px 18px rgba(124,58,237,.5);opacity:0;transition:opacity .25s;text-transform:uppercase';
      document.body.appendChild(badge);
    }
  }, CURSOR_SVG);
}

async function step(page, badge, subtitle) {
  await page.evaluate(({b, s}) => {
    const sb = document.getElementById('demo-stepbadge');
    const tb = document.getElementById('demo-subtitle');
    if (sb) { sb.textContent = b || ''; sb.style.opacity = b ? '1' : '0'; }
    if (tb) { tb.textContent = s || ''; tb.style.opacity   = s ? '1' : '0';   }
  }, { b: badge, s: subtitle });
  await page.waitForTimeout(320);
}

// Force every overlay / drawer / menu CLOSED via direct state manipulation
// so the next section starts from a clean baseline.
async function clean(page) {
  await page.evaluate(() => {
    // Parser modal (inline display style)
    const po = document.getElementById('parser-overlay');
    if (po) po.style.display = 'none';
    // Drawer system
    ['drawer','drawer-overlay','equiv-drawer','auto-drawer','helpcard','export-menu'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('open');
    });
    // Per-card overflow menus
    document.querySelectorAll('.actbtn-menu.open').forEach(m => m.classList.remove('open'));
    // Search autocomplete
    const sg = document.getElementById('search-suggest');
    if (sg) sg.classList.remove('open');
  });
  await page.waitForTimeout(200);
}

async function move(page, sel) {
  const el = page.locator(sel).first();
  if (!(await el.isVisible().catch(() => false))) return false;
  const box = await el.boundingBox();
  if (!box) return false;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 14 });
  await page.waitForTimeout(220);
  return true;
}

async function click(page, sel, label, post = 700) {
  // Don't pre-check visibility — let Playwright auto-scroll the element into view.
  // Fail fast (3s) so a missing element doesn't stall the whole recording.
  const el = page.locator(sel).first();
  try {
    await el.scrollIntoViewIfNeeded({ timeout: 2000 });
    await page.waitForTimeout(140);
    const box = await el.boundingBox().catch(() => null);
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
      await page.waitForTimeout(180);
    }
    await el.click({ timeout: 3000 });
  } catch (e) {
    console.error('SKIP ' + label + ': ' + (e.message || '').slice(0, 80));
    return false;
  }
  await page.waitForTimeout(post);
  return true;
}

async function search(page, text) {
  const q = page.locator('#q');
  await q.click({ timeout: 3000 }).catch(()=>{});
  await q.fill('');
  await page.waitForTimeout(220);
  await q.pressSequentially(text, { delay: 42 });
  await page.waitForTimeout(600);
  // Dismiss the autocomplete dropdown so it doesn't block subsequent card clicks
  await page.evaluate(() => {
    const sg = document.getElementById('search-suggest');
    if (sg) sg.classList.remove('open');
  });
  await page.waitForTimeout(180);
}

async function clearSearch(page) {
  await page.evaluate(() => {
    const q = document.getElementById('q');
    if (q) {
      q.value = '';
      q.dispatchEvent(new Event('input', {bubbles:true}));
    }
  });
  await page.waitForTimeout(280);
}

// Hard reset: clears every filter set (vendor / os / role / cat / favs) AND search.
// Without this, the per-card 'Open in Compare' button leaves state.cat locked,
// so later searches return zero results inside an unrelated category.
async function resetAll(page) {
  await page.evaluate(() => {
    if (typeof state === 'undefined') return;
    state.vendor.clear(); state.os.clear(); state.role.clear(); state.cat.clear();
    state.showFavOnly = false;
    state.q = '';
    const q = document.getElementById('q'); if (q) q.value = '';
    if (typeof renderChips === 'function') renderChips();
    if (typeof renderActiveBar === 'function') renderActiveBar();
    if (typeof render === 'function') render();
  });
  await page.waitForTimeout(420);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    recordVideo: { dir: VIDEO_DIR, size: { width: 1920, height: 1080 } },
    viewport: { width: 1920, height: 1080 }
  });
  const page = await ctx.newPage();

  try {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await injectOverlays(page);
    await page.waitForTimeout(900);

    // ── INTRO ─────────────────────────────────────────────────────────
    await step(page, 'Multivendor CLI Reference', 'A single-file static tool for Cisco · Juniper · Arista');
    await page.waitForTimeout(3000);

    // ── STATS BAR ────────────────────────────────────────────────────
    await step(page, 'Stats', '9,808 commands · 3 vendors · 26 categories — fetched from one JSON');
    await move(page, '#stat-total');
    await page.waitForTimeout(2400);

    // ── SIDEBAR FILTERS (pan over, don't click — more reliable) ──────
    await step(page, 'Sidebar filters', 'Filter by vendor, OS, role, category — all with live counts');
    await move(page, '#acc-vendor');
    await page.waitForTimeout(1400);
    await move(page, '#acc-os');
    await page.waitForTimeout(1400);
    await move(page, '#acc-role');
    await page.waitForTimeout(1400);
    await move(page, '#acc-cat');
    await page.waitForTimeout(1800);

    // ── OPERATOR SEARCH ───────────────────────────────────────────────
    await clean(page);
    await step(page, 'Operator search', 'Press / and use vendor: · os: · cat: · role: prefixes');
    await search(page, 'vendor:juniper ospf area');
    await page.waitForTimeout(2400);

    // ── AUTOCOMPLETE ──────────────────────────────────────────────────
    await step(page, 'Autocomplete', 'Type vendor: and the dropdown suggests values with live counts');
    await clearSearch(page);
    await search(page, 'vendor:');
    await page.waitForTimeout(2400);
    await clearSearch(page);

    // ── CARDS ─────────────────────────────────────────────────────────
    await step(page, 'Cards view', 'Title · description · syntax-highlighted code · vendor badges · actions');
    await search(page, 'bgp neighbor');
    await page.waitForTimeout(2500);

    // ── COPY action ──────────────────────────────────────────────────
    await step(page, 'Copy', 'One-click copy of any command');
    await click(page, '.card .actbtn:has-text("Copy")', 'copy', 1500);

    // ── +CLI action ──────────────────────────────────────────────────
    await step(page, '+ CLI', 'Queue commands across vendors — mix Cisco · Juniper · Arista');
    await click(page, '.card.cisco .actbtn.primary', 'add-cisco', 700);
    await click(page, '.card.juniper .actbtn.primary', 'add-juniper', 700);
    await click(page, '.card.arista .actbtn.primary', 'add-arista', 1000);

    // ── CLI BUILDER drawer ────────────────────────────────────────────
    await step(page, 'CLI Builder', 'Live drawer — copy all, download .txt, mix-vendor runbook ready');
    await click(page, '#btn-clibuilder', 'open-cli', 2500);
    await page.waitForTimeout(1200);
    await clean(page);

    // ── FAVORITES ────────────────────────────────────────────────────
    await step(page, 'Favorites', 'Star any card — persists in localStorage');
    await click(page, '.card .star', 'star', 1300);
    await click(page, '.card:nth-of-type(2) .star', 'star-2', 1300);
    await clearSearch(page);

    // ── ↔ COMPARE per-card ───────────────────────────────────────────
    await step(page, '↔ Compare', 'Card-level shortcut: jump to Compare view, scoped to this concept');
    await search(page, 'router ospf');
    await page.waitForTimeout(1500);
    await click(page, '.card .actbtn:has-text("Compare")', 'compare', 2500);

    // ── COMPARE VIEW explained ───────────────────────────────────────
    await step(page, 'Compare view', 'Cisco · Juniper · Arista lined up on one row by concept');
    await page.evaluate(() => window.scrollTo({top:300,behavior:'smooth'}));
    await page.waitForTimeout(2400);
    await page.evaluate(() => window.scrollTo({top:0,behavior:'smooth'}));
    await page.waitForTimeout(1000);

    // ── TABLE VIEW ───────────────────────────────────────────────────
    await page.keyboard.press('t');
    await page.waitForTimeout(1200);
    await step(page, 'Table view', 'Sortable · Title and Command stay sticky as you scroll right');
    await page.waitForTimeout(2400);
    // Demonstrate horizontal scroll
    await page.evaluate(() => {
      const wrap = document.querySelector('.tblwrap');
      if (wrap) wrap.scrollTo({left: 400, behavior:'smooth'});
    });
    await page.waitForTimeout(2200);

    // ── Back to cards + full reset ───────────────────────────────────
    await page.keyboard.press('g');
    await page.waitForTimeout(1000);
    await clean(page);
    await resetAll(page);

    // ── ⚡ AUTOMATE (YANG) — flagship feature ────────────────────────
    await step(page, '⚡ Automate (YANG)', 'Native NETCONF / YANG snippets — model-driven, values pre-filled');
    await search(page, 'interface ip address');
    await page.waitForTimeout(1500);
    // Prefer a native YANG card; fall back to any Automate
    let opened = await click(page, '.card .actbtn.auto.native', 'open-yang', 2200);
    if (!opened) opened = await click(page, '.card .actbtn.auto', 'open-auto', 2200);

    await step(page, 'Parameter editor', 'Edit Host / User / Password — every snippet re-renders live');
    const hostI = page.locator('.auto-params input').first();
    if (await hostI.isVisible().catch(()=>false)) {
      await hostI.click({timeout:3000}).catch(()=>{});
      await hostI.fill('');
      await hostI.pressSequentially('10.10.99.1', {delay: 45});
      await page.waitForTimeout(1600);
    }

    await step(page, 'NETCONF · ncclient · Ansible', 'All three flavours rendered with your values');
    await page.evaluate(() => {
      const db = document.querySelector('.auto-drawer .db');
      if (db) db.scrollTo({top: 200, behavior:'smooth'});
    });
    await page.waitForTimeout(2400);

    await step(page, 'Switch vendor', 'Same intent — Cisco, Juniper, Arista equivalents in one click');
    await click(page, '.auto-tabs .tab-juniper', 'tab-j', 1800);
    await click(page, '.auto-tabs .tab-arista', 'tab-a', 1800);
    await clean(page);

    // ── 🔧 AUTOMATE (SSH fallback) ───────────────────────────────────
    await resetAll(page);
    await step(page, '🔧 Automate (SSH)', 'Universal fallback: Netmiko · Ansible · NAPALM for every command');
    await search(page, 'show version');
    await page.waitForTimeout(1300);
    await click(page, '.card .actbtn.auto.fallback', 'open-ssh', 2000);
    await page.waitForTimeout(2000);
    await clean(page);

    // ── ↗ EQUIVALENTS via ⋯ ─────────────────────────────────────────
    await resetAll(page);
    await step(page, '↗ See equivalents', 'Overflow menu reveals top cross-vendor matches in this category');
    await search(page, 'ospf area');
    await page.waitForTimeout(1500);
    if (await click(page, '.card .actbtn-more > button', 'overflow', 800)) {
      await click(page, '.actbtn-menu-item:has-text("equivalents")', 'equiv', 2500);
      await page.waitForTimeout(1500);
    }
    await clean(page);

    // ── 📊 PARSE OUTPUT ──────────────────────────────────────────────
    await step(page, '📊 Parse Output', 'Paste raw show output — built-in TextFSM-style parsers structure it');
    await click(page, '#btn-parser', 'open-parser', 1100);
    try { await page.locator('#parser-template').selectOption({ index: 1 }); } catch(_) {}
    await page.waitForTimeout(700);
    if (await click(page, '#parser-insert-sample', 'sample', 900)) {
      await click(page, '#parser-run', 'parse-run', 2800);
    }
    await page.waitForTimeout(1200);
    await clean(page);

    // ── 🔗 SHARE ─────────────────────────────────────────────────────
    await clearSearch(page);
    await step(page, '🔗 Share workspace', 'Filters + view + CLI queue all encoded into one URL');
    await click(page, '#btn-share', 'share', 2200);
    await clean(page);

    // ── EXPORT ───────────────────────────────────────────────────────
    await step(page, 'Export', 'TXT · Markdown · CSV · JSON — current filter set');
    await click(page, '#btn-export', 'export-open', 2200);
    await clean(page);

    // ── THEME ────────────────────────────────────────────────────────
    await step(page, 'Theme', 'Dark · Light — persisted across sessions');
    await click(page, '#btn-theme', 'theme', 1600);
    await click(page, '#btn-theme', 'theme-back', 1200);

    // ── HELP ─────────────────────────────────────────────────────────
    await step(page, 'Keyboard shortcuts', '/ search · c compare · t table · g cards · b builder · f favs');
    await click(page, '#btn-help', 'help', 2400);
    await clean(page);

    // ── OUTRO ────────────────────────────────────────────────────────
    await step(page, 'Open source', 'github.com/gesh75/multivendor-cli-configurator');
    await page.waitForTimeout(3500);
    await step(page, '', '');
    await page.waitForTimeout(500);

  } catch (err) {
    console.error('DEMO ERROR:', err.message);
  } finally {
    await ctx.close();
    const video = page.video();
    if (video) {
      const src = await video.path();
      const dest = path.join(VIDEO_DIR, OUTPUT_NAME);
      try { fs.copyFileSync(src, dest); console.log('Video saved:', dest); }
      catch (e) { console.error('ERROR copy:', e.message); }
    }
    await browser.close();
  }
})();
