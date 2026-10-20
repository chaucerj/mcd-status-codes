#!/usr/bin/env node
/* 试玩间 v4 e2e：Agent 对话点餐 + 时间轴探活（真实浏览器） */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const PAGE_URL = 'file://' + require('path').resolve(__dirname, '..', 'docs', 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox', '--disable-gpu'] });
  let pass = 0, total = 0;
  const check = (desc, cond) => { total++; cond ? (pass++, console.log('✓', desc)) : console.log('✗', desc); };
  const page = await b.newPage({ viewport: { width: 900, height: 1000 } });
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto(PAGE_URL);

  // T1 欢迎语
  check('T1 Agent 开场欢迎', (await page.locator('#msgs').textContent()).includes('值班运维 Agent'));

  // T2 对话推荐：20块吃什么
  await page.fill('#chatIn', '20块吃什么');
  await page.click('#chatSend');
  const lastAgent = await page.locator('.msg.agent .bubble').last().innerHTML();
  check('T2 组合卡出现（主餐+确认按钮）', lastAgent.includes('就这样下单') && lastAgent.includes('kcal'));

  // T3 确认下单 → 状态码出现
  await page.click('[data-act="confirm"]');
  const all1 = await page.locator('#msgs').textContent();
  check('T3 确认后返回状态码判定', /20[0-9]|429|206|404/.test(all1));

  // T4 时间轴拨到 10:00 → 晨间咖啡探活 103
  await page.evaluate(() => setClock(600));
  const feed1 = await page.locator('#msgs').textContent();
  check('T4 拨到 10:00 → 103 咖啡窗探活', feed1.includes('103 Hints'));

  // T5 拨到 11:40 → 599
  await page.evaluate(() => setClock(700));
  check('T5 拨到 11:40 → 599 Timeout', (await page.locator('#msgs').textContent()).includes('599 Timeout'));

  // T6 对话：来杯咖啡 → 推荐饮品 → 确认
  await page.fill('#chatIn', '来杯咖啡');
  await page.click('#chatSend');
  await page.click('[data-act="confirm"]');
  const all2 = await page.locator('#msgs').textContent();
  check('T6 咖啡推荐可确认下单', /200 OK|201 Created|429|206/.test(all2));

  // T7 深夜场景 → 408
  await page.fill('#chatIn', '深夜饿了');
  await page.click('#chatSend');
  await page.click('[data-act="confirm"]');
  check('T7 深夜提交 → 408 Timeout', (await page.locator('#msgs').textContent()).includes('408 Timeout'));

  check('T8 无 JS 运行时错误', pageErrors.length === 0);
  if (pageErrors.length) console.log('JS errors:', pageErrors.slice(0, 3));

  await b.close();
  console.log(`\ne2e ${pass}/${total} 通过`);
  process.exit(pass === total ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
