const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const [, , url, out, dim] = process.argv;
  const b = await chromium.launch({ executablePath: EXEC, args:['--no-sandbox','--disable-gpu'] });
  const p = await b.newPage({ viewport:{width:1280,height:1000}, deviceScaleFactor:2 });
  await p.goto(url, { waitUntil:'networkidle' });
  await p.waitForFunction(() => document.getElementById('app')?.innerHTML.trim().length > 200, {timeout:15000});
  if (dim && dim !== 'day') { await p.click(`[data-dim="${dim}"]`); await p.waitForTimeout(500); }
  else await p.waitForTimeout(400);
  await p.screenshot({ path: out, fullPage: true });
  console.log('OK '+out+'height='+await p.evaluate(()=>document.body.scrollHeight));
  await b.close();
})();
