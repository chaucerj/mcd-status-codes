const { chromium } = require('playwright-core');

const EXEC = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1248/chrome-mac-arm64/' +
  'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const [, , url, out, mode] = process.argv;
  const browser = await chromium.launch({
    executablePath: EXEC,
    args: ['--no-sandbox', '--disable-gpu'],
  });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 1000 },
    deviceScaleFactor: 2,
  });
  await page.goto(url, { waitUntil: 'networkidle' });
  // 等待应用把 innerHTML 渲染进 #app
  await page.waitForFunction(
    () => {
      const el = document.getElementById('app');
      return el && el.innerHTML.trim().length > 200;
    },
    { timeout: 15000 }
  );
  await page.waitForTimeout(600);

  if (mode === '1024') {
    await page.screenshot({ path: out, fullPage: true });
  } else {
    await page.screenshot({ path: out, fullPage: true });
  }
  const h = await page.evaluate(() => document.body.scrollHeight);
  console.log('OK ' + out + '  height=' + h);
  await browser.close();
})();
