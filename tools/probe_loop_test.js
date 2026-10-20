#!/usr/bin/env node
/* 试玩间 v4 e2e：Agent 对话点餐 + 时间轴探活闭环（真实浏览器，三会话） */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const PAGE_URL = 'file://' + require('path').resolve(__dirname, '..', 'docs', 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox', '--disable-gpu'] });
  let pass = 0, total = 0;
  const check = (d, c) => { total++; c ? (pass++, console.log('✓', d)) : console.log('✗', d); };
  const setClock = (page, min) => page.evaluate(v => setClock(v), min);
  const chat = async (page, text) => { await page.fill('#chatIn', text); await page.click('#chatSend'); };
  const msgsText = page => page.locator('#msgs').textContent();

  // ── 会话 1：交互后 103 出现 → 采纳 → 闭环 → 599 被抑制（因果连贯核心证明）──
  {
    const page = await b.newPage({ viewport: { width: 900, height: 1000 } });
    await page.goto(PAGE_URL);
    await chat(page, '早上来杯咖啡');          // 进入值班状态（首次交互）
    await setClock(page, 600);
    await page.waitForTimeout(150);
    check('1a: 10:00 晨间 103 探活带「采纳」按钮',
      await page.locator('[data-adopt="morning_103"]').count() === 1);
    await page.click('[data-adopt="morning_103"]');
    const m1 = await msgsText(page);
    check('1b: 闭环消息出现（探活闭环完成 + 判定）', m1.includes('探活闭环完成'));
    await setClock(page, 700);
    await page.waitForTimeout(150);
    check('1c: 咖啡已采纳 → 11:40 无 599（因果连贯）',
      !(await msgsText(page)).includes('599 Timeout'));
    await page.close();
  }

  // ── 会话 2：交互但不采纳 → 599 照常 + 文案回链 103 ──
  {
    const page = await b.newPage({ viewport: { width: 900, height: 1000 } });
    await page.goto(PAGE_URL);
    await chat(page, '随便来个汉堡');          // 进入值班状态，不采纳咖啡建议
    await setClock(page, 600);
    await page.waitForTimeout(150);
    await setClock(page, 700);
    await page.waitForTimeout(150);
    const feed = await msgsText(page);
    check('2a: 不采纳 → 11:40 出现 599', feed.includes('599 Timeout'));
    check('2b: 599 文案回链 103 建议', feed.includes('采纳了那杯 15 kcal 的咖啡就不会有这条 599'));
    await page.close();
  }

  // ── 会话 3：15:00 补给窗 103 → 采纳 → 闭环 → 缺口收敛 ──
  {
    const page = await b.newPage({ viewport: { width: 900, height: 1000 } });
    await page.goto(PAGE_URL);
    await chat(page, '随便推荐');
    await setClock(page, 900);
    await page.waitForTimeout(150);
    check('3a: 15:00 补给窗 103 带采纳按钮',
      await page.locator('[data-adopt="snack_103"]').count() === 1);
    await page.click('[data-adopt="snack_103"]');
    const m3 = await msgsText(page);
    check('3b: 补给闭环消息出现', m3.includes('探活闭环完成'));
    await setClock(page, 950);
    await page.waitForTimeout(150);
    const feed3 = await msgsText(page);
    const snack103Count = (feed3.match(/减脂补给窗：缺口 1800/g) || []).length;
    check('3c: 采纳后不再重复下发同缺口 103（探活原文+闭环回显共 2 次，无第三次）', snack103Count === 2);
    await page.close();
  }

  await b.close();
  console.log(`\n闭环 e2e ${pass}/${total} 通过`);
  process.exit(pass === total ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
