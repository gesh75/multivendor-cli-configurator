'use strict';
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = process.env.QA_BASE_URL || 'http://localhost:9125/index.html';
const VIDEO_DIR = path.join(__dirname);
const OUTPUT_NAME = 'multivendor-cli-demo.webm';
const REHEARSAL = process.argv.includes('--rehearse');

const CURSOR_SVG_DATA_URL = 'data:image/svg+xml;utf8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5" stroke-linejoin="round"/></svg>'
);

async function injectCursor(page) {
  await page.evaluate((svgUrl) => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('img');
    cursor.id = 'demo-cursor';
    cursor.src = svgUrl;
    cursor.alt = '';
    cursor.style.cssText = 'position:fixed;z-index:999999;pointer-events:none;width:28px;height:28px;transition:left .08s linear,top .08s linear;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.4));left:40px;top:40px';
    document.body.appendChild(cursor);
    document.addEventListener('mousemove', (e) => {
      cursor.style.left = e.clientX + 'px';
      cursor.style.top = e.clientY + 'px';
    });
  }, CURSOR_SVG_DATA_URL);
}

async function injectSubtitleBar(page) {
  await page.evaluate(() => {
    if (document.getElementById('demo-subtitle')) return;
    const bar = document.createElement('div');
    bar.id = 'demo-subtitle';
    bar.style.cssText = 'position:fixed;bottom:32px;left:50%;transform:translateX(-50%);z-index:999998;text-align:center;padding:14px 28px;background:rgba(0,0,0,.85);color:#fff;font-family:-apple-system,"Segoe UI",Inter,Roboto,sans-serif;font-size:20px;font-weight:600;letter-spacing:.3px;border-radius:10px;border:1px solid rgba(34,211,238,.4);opacity:0;transition:opacity .3s;pointer-events:none;max-width:80vw';
    bar.textContent = '';
    document.body.appendChild(bar);
  });
}

async function showSubtitle(page, text) {
  await page.evaluate((t) => {
    const bar = document.getElementById('demo-subtitle');
    if (!bar) return;
    if (t) { bar.textContent = t; bar.style.opacity = '1'; } else { bar.style.opacity = '0'; }
  }, text);
  if (text) await page.waitForTimeout(400);
}

async function moveAndClick(page, sel, label, opts = {}) {
  const { post = 700 } = opts;
  const el = page.locator(sel).first();
  if (!(await el.isVisible().catch(() => false))) {
    console.error('SKIP click ' + label + ' (not visible): ' + sel);
    return false;
  }
  try {
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(220);
    const box = await el.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 14 });
      await page.waitForTimeout(280);
    }
    await el.click();
  } catch (e) {
    console.error('FAIL click ' + label + ': ' + e.message); return false;
  }
  await page.waitForTimeout(post);
  return true;
}

async function typeSlowly(page, sel, text, label, charDelay = 38) {
  const el = page.locator(sel).first();
  if (!(await el.isVisible().catch(() => false))) {
    console.error('SKIP type ' + label); return false;
  }
  await moveAndClick(page, sel, label, { post: 200 });
  await el.fill('');
  await el.pressSequentially(text, { delay: charDelay });
  await page.waitForTimeout(400);
  return true;
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
    await injectCursor(page); await injectSubtitleBar(page);
    await page.waitForTimeout(800);

    // 1. HOOK
    await showSubtitle(page, '9,808 CLI commands · 3 vendors · 1 HTML file');
    await page.waitForTimeout(3000);

    // 2. SEARCH
    await showSubtitle(page, 'Operator search — vendor: · os: · cat: · role:');
    await typeSlowly(page, '#q', 'vendor:juniper ospf area', 'search');
    await page.waitForTimeout(1500);

    // 3. COMPARE
    await page.locator('#q').fill('');
    await page.waitForTimeout(400);
    await showSubtitle(page, 'Press  c  — Concept-aligned Compare view');
    await page.keyboard.press('c');
    await page.waitForTimeout(1800);
    await page.evaluate(() => window.scrollTo({ top: 700, behavior: 'smooth' }));
    await page.waitForTimeout(2200);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await page.waitForTimeout(1200);

    // 4. AUTOMATE
    await page.keyboard.press('g');
    await page.waitForTimeout(800);
    await showSubtitle(page, '⚡ Automate — NETCONF · ncclient · Ansible · NAPALM');
    await typeSlowly(page, '#q', 'interface ip address', 'search-ipaddr');
    await page.waitForTimeout(1200);
    const more = page.locator('.card .actbtn-more > button').first();
    if (await more.isVisible().catch(()=>false)) {
      await moveAndClick(page, '.card .actbtn-more > button', 'overflow-menu');
      await page.waitForTimeout(700);
      const native = page.locator('.actbtn-menu-item.native').first();
      const fallback = page.locator('.actbtn-menu-item.fallback').first();
      if (await native.isVisible().catch(()=>false)) {
        await moveAndClick(page, '.actbtn-menu-item.native', 'automate-yang');
      } else if (await fallback.isVisible().catch(()=>false)) {
        await moveAndClick(page, '.actbtn-menu-item.fallback', 'automate-ssh');
      }
    }
    await page.waitForTimeout(3000);
    const tabJ = page.locator('.auto-tabs .tab-juniper');
    if (await tabJ.isVisible().catch(()=>false)) await moveAndClick(page, '.auto-tabs .tab-juniper', 'juniper-tab', {post:1500});
    const tabA = page.locator('.auto-tabs .tab-arista');
    if (await tabA.isVisible().catch(()=>false)) await moveAndClick(page, '.auto-tabs .tab-arista', 'arista-tab', {post:1500});
    await page.keyboard.press('Escape');
    await page.waitForTimeout(700);

    // 5. PARSE OUTPUT
    await showSubtitle(page, '📊 Parse raw  show  output into a structured table');
    await moveAndClick(page, '#btn-parser', 'open-parser', {post:900});
    const tmpl = page.locator('#parser-template');
    if (await tmpl.isVisible().catch(()=>false)) {
      try { await tmpl.selectOption({ index: 1 }); } catch(_) {}
      await page.waitForTimeout(500);
    }
    await moveAndClick(page, '#parser-insert-sample', 'insert-sample', {post:900});
    await moveAndClick(page, '#parser-run', 'parse-run', {post:2500});
    await page.keyboard.press('Escape');
    await page.waitForTimeout(700);

    // 6. CLI BUILDER + SHARE
    await showSubtitle(page, '⌘ CLI Builder — mix vendors · 🔗 Share workspace URL');
    await page.locator('#q').fill('');
    await page.waitForTimeout(400);
    await typeSlowly(page, '#q', 'bgp', 'search-bgp');
    await page.waitForTimeout(1000);
    const addC = page.locator('.card.cisco .actbtn.primary').first();
    if (await addC.isVisible().catch(()=>false)) await moveAndClick(page, '.card.cisco .actbtn.primary', 'add-cisco', {post:600});
    const addJ = page.locator('.card.juniper .actbtn.primary').first();
    if (await addJ.isVisible().catch(()=>false)) await moveAndClick(page, '.card.juniper .actbtn.primary', 'add-juniper', {post:600});
    const addA = page.locator('.card.arista .actbtn.primary').first();
    if (await addA.isVisible().catch(()=>false)) await moveAndClick(page, '.card.arista .actbtn.primary', 'add-arista', {post:600});
    await moveAndClick(page, '#btn-clibuilder', 'open-cli-builder', {post:1800});
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    await moveAndClick(page, '#btn-share', 'share', {post:1800});

    // 7. OUTRO
    await showSubtitle(page, 'Open source · github.com/gesh75/multivendor-cli-configurator');
    await page.waitForTimeout(3000);
    await showSubtitle(page, '');
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
      catch (e) { console.error('ERROR copy video:', e.message); }
    }
    await browser.close();
  }
})();
