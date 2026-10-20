#!/usr/bin/env node
/* 试玩间 e2e 测试：官方菜单 + 时间驱动探活（三段会话，真实浏览器） */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const URL = 'file://' + require('path').resolve(__dirname, '..', 'docs', 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox', '--disable-gpu'] });
  let pass = 0, total = 0;
  const check = (desc, cond) => { total++; cond ? (pass++, console.log('✓', desc)) : console.log('✗', desc); };
  const setClock = async (page, min) => {
    await page.evaluate(v => {
      const s = document.getElementById('clockSlider');
      s.value = v; s.dispatchEvent(new Event('input'));
    }, min);
  };
  const feedHas = async (page, text) =>
    (await page.locator('#feed').innerHTML()).includes(text);

  // ── 会话 A：10:00 点板烧（无咖啡）→ 201 + 103 晨间咖啡 → 11:40 → 599 ──
  {
    const page = await b.newPage();
    await page.goto(URL);
    await page.evaluate(() => setClock(600));
    await page.click('.mi:has-text("板烧鸡腿堡")');
    await page.click('#submit');
    check('A1: 10:00 提交板烧（新品）→ 201 Created',
      (await page.locator('#verdict').innerHTML()).includes('201 Created'));
    check('A2: 晨间咖啡窗探活 → 103 Hints', await feedHas(page, '103 Hints'));
    await setClock(page, 700);
    check('A3: 拨到 11:40 未采纳 → 599 Timeout', await feedHas(page, '599 Timeout'));
    await page.close();
  }

  // ── 会话 B：12:00 点巨无霸 → 200；15:00 缺口 1287 → 103 补给 ──
  {
    const page = await b.newPage();
    await page.goto(URL);
    await page.evaluate(() => setClock(720));
    await page.click('.mi:has-text("巨无霸")');
    await page.click('#submit');
    check('B1: 12:00 首单巨无霸 → 201 Created（新品优先于 200）',
      (await page.locator('#verdict').innerHTML()).includes('201 Created'));
    await setClock(page, 900);
    check('B2: 15:00 缺口 1287 → 103 补给', await feedHas(page, '缺口 1287'));
    await page.close();
  }

  // ── 会话 C：12:00 双份巨无霸+双份麦辣（1996 kcal）→ 200 + 双指标告警；15:00 → 412；16:05 → 522 ──
  {
    const page = await b.newPage();
    await page.goto(URL);
    await page.evaluate(() => setClock(720));
    await page.click('.mi:has-text("巨无霸")');
    await page.click('.mi:has-text("巨无霸")');
    await page.click('.mi:has-text("麦辣鸡腿汉堡")');
    await page.click('.mi:has-text("麦辣鸡腿汉堡")');
    await page.click('#submit');
    const v = await page.locator('#verdict').innerHTML();
    check('C1: 1996 kcal 大单 → 201 + 双指标告警（状态码不受负荷影响）',
      v.includes('201 Created') && v.includes('热量过载') && v.includes('钠超标'));
    check('C2: 指标告警双 chip（热量过载 P1 + 钠超标 P2）',
      v.includes('热量过载') && v.includes('钠超标'));
    await setClock(page, 900);
    check('C3: 15:00 超预算 → 412 目标否决', await feedHas(page, '412 Denied'));
    await setClock(page, 966);
    check('C4: 16:06 双窗超时 → 522 失联升级', await feedHas(page, '522 Lost'));
    await page.close();
  }

  await b.close();
  console.log(`\ne2e ${pass}/${total} 通过`);
  process.exit(pass === total ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
