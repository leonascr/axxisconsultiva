// Mede em que tamanho cada imagem aparece (desktop e celular) e qual é o maior elemento
// de cada página (LCP). O perf.py usa o resultado para gerar imagens no tamanho certo.
//
// Uso: node tools/measure.mjs   (gera tools/image-sizes.json)
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.join(ROOT, 'site');
const OUT = path.join(ROOT, 'tools', 'image-sizes.json');
const HOST = 'http://site.local';
const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } };
const MIME = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.gif': 'image/gif', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.mp4': 'video/mp4',
};

// Caminhos longos (Airlift) passam do limite do Windows sem o prefixo \\?\
const readSite = (file) => fs.readFileSync(process.platform === 'win32' ? '\\\\?\\' + file : file);

const slugs = [...readSite(path.join(SITE, 'sitemap.xml')).toString().matchAll(/<loc>https?:\/\/[^/]+(\/[^<]*)<\/loc>/g)].map((m) => m[1]);
const images = {};
const lcp = {};

function note(p, kind, w, h) {
  const key = decodeURIComponent(p);
  const cur = (images[key] ??= { img: 0, bgW: 0, bgH: 0 });
  if (kind === 'img') cur.img = Math.max(cur.img, Math.round(w));
  else { cur.bgW = Math.max(cur.bgW, Math.round(w)); cur.bgH = Math.max(cur.bgH, Math.round(h)); }
}

const browser = await chromium.launch();
for (const [vname, viewport] of Object.entries(VIEWPORTS)) {
  const ctx = await browser.newContext({ viewport });
  // Serve site/ direto do disco; terceiros (GTM etc.) são bloqueados
  await ctx.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== HOST) return route.abort();
    let file = path.join(SITE, decodeURIComponent(url.pathname));
    if (url.pathname.endsWith('/')) file = path.join(file, 'index.html');
    try {
      await route.fulfill({ status: 200, body: readSite(file), contentType: MIME[path.extname(file).toLowerCase()] ?? 'application/octet-stream' });
    } catch {
      await route.fulfill({ status: 404, body: '' });
    }
  });
  for (const slug of slugs) {
    const page = await ctx.newPage();
    await page.addInitScript(() => {
      window.__lcp = null;
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) window.__lcp = e.url || null;
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    });
    await page.goto(HOST + slug, { waitUntil: 'load' });
    await page.waitForTimeout(800);
    const lcpUrl = await page.evaluate(() => window.__lcp);
    // Rola a página inteira para carregar imagens sob demanda e carrosséis
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 500) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 60));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(500);
    const found = await page.evaluate(() => {
      const out = [];
      const local = (u) => {
        try {
          const x = new URL(u, location.href);
          return x.origin === location.origin ? x.pathname : null;
        } catch {
          return null;
        }
      };
      for (const img of document.images) {
        const r = img.getBoundingClientRect();
        const p = local(img.currentSrc || img.src);
        if (p && r.width) out.push(['img', p, r.width, r.height]);
      }
      for (const el of document.querySelectorAll('*')) {
        const bg = getComputedStyle(el).backgroundImage;
        if (!bg || bg === 'none') continue;
        const r = el.getBoundingClientRect();
        if (!r.width) continue;
        for (const m of bg.matchAll(/url\("?([^")]+)"?\)/g)) {
          const p = local(m[1]);
          if (p) out.push(['bg', p, r.width, r.height]);
        }
      }
      return out;
    });
    for (const [kind, p, w, h] of found) note(p, kind, w, h);
    const lcpPath = lcpUrl && lcpUrl.startsWith(HOST) ? decodeURIComponent(new URL(lcpUrl).pathname) : null;
    (lcp[slug] ??= {})[vname] = lcpPath;
    await page.close();
  }
  await ctx.close();
  console.log(`medido: ${vname}`);
}
await browser.close();

const sorted = Object.fromEntries(Object.entries(images).sort(([a], [b]) => a.localeCompare(b)));
fs.writeFileSync(OUT, JSON.stringify({ images: sorted, lcp }, null, 1));
console.log(`${Object.keys(sorted).length} imagens medidas em ${slugs.length} páginas -> tools/image-sizes.json`);
