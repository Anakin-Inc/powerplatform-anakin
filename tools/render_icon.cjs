// Renders the connector icon: the Anakin mark at 64% of a 230x230 #1F302C square.
const fs = require('fs');
const { chromium } = require(process.argv[2]);
const svg = fs.readFileSync(process.argv[3], 'utf8');
const out = process.argv[4];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 230, height: 230 }, deviceScaleFactor: 1 });
  await page.setContent(`<html><body style="margin:0;background:#1F302C;width:230px;height:230px;display:flex;align-items:center;justify-content:center">
    <div style="width:147px;height:147px">${svg.replace('<svg', '<svg width="147" height="147"')}</div></body></html>`);
  await page.screenshot({ path: out, omitBackground: false, clip: { x: 0, y: 0, width: 230, height: 230 } });
  await browser.close();
})();
