// Descobre quais seletores CSS são usados em alguma página (desktop e celular).
// Chamado pelo detach.py: node tools/css-usage.mjs <entrada.json> <saida.json>
//   entrada: { root, assets: {caminho novo: arquivo antigo}, pages: [...], tests: [seletor de teste, ...] }
//   saida:   [seletor de teste usado, ...]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [, , inFile, outFile] = process.argv;
const { root, assets, pages, tests } = JSON.parse(fs.readFileSync(inFile, 'utf8'));
const HOST = 'http://site.local';
const VIEWPORTS = [{ width: 1440, height: 900 }, { width: 390, height: 844 }];
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript' };
const readFile = (file) => fs.readFileSync(process.platform === 'win32' ? '\\\\?\\' + path.resolve(file) : file);

const pending = new Set(tests);
const browser = await chromium.launch();
for (const viewport of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport });
  await ctx.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== HOST) return route.abort();
    const p = decodeURIComponent(url.pathname);
    // HTML/CSS/JS já convertidos ficam em public/; imagens e fontes ainda estão no site antigo
    const file = assets[p] ?? path.join(root, p.endsWith('/') ? p + 'index.html' : p);
    try {
      await route.fulfill({ status: 200, body: readFile(file), contentType: MIME[path.extname(file)] ?? 'application/octet-stream' });
    } catch {
      await route.fulfill({ status: 404, body: '' });
    }
  });
  for (const page of pages) {
    const p = await ctx.newPage();
    await p.goto(HOST + page, { waitUntil: 'load' });
    await p.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 40));
      }
    });
    await p.waitForTimeout(300);
    const used = await p.evaluate((list) => list.filter((s) => {
      try {
        return document.querySelector(s) !== null;
      } catch {
        return true; // seletor que o navegador não entende: mantém por segurança
      }
    }), [...pending]);
    used.forEach((s) => pending.delete(s));
    await p.close();
  }
  await ctx.close();
}
await browser.close();
fs.writeFileSync(outFile, JSON.stringify(tests.filter((t) => !pending.has(t))));
