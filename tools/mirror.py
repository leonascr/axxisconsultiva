"""Espelha axxiscontabilidade.com.br como site estático em ./site.

Remove a camada de otimização do Airlift (scripts/CSS adiados, imagens lazy em
placeholder SVG) e reconstrói o HTML original do WordPress/Elementor, baixando
os assets do próprio domínio para servir localmente.

Uso: python tools/mirror.py
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import escape, unescape
from pathlib import Path

ORIGIN = "https://axxiscontabilidade.com.br"
OWN_HOSTS = {"axxiscontabilidade.com.br", "www.axxiscontabilidade.com.br"}
# Assets hospedados no site do grupo e referenciados pelo site
EXTRA_HOSTS = {"grupoaxxis.com.br": "/_ext/grupoaxxis"}
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# Páginas que não são copiadas; links para elas ficam sem ação
DEAD_SLUGS = {
    "solicite-sua-proposta",
    "form-solicite-sua-proposta",
    "conteudos-axxis",
    "conteudos-axxis-2",
}
SKIP_PREFIXES = ("wp-json", "wp-admin", "wp-login", "xmlrpc.php", "feed", "comments", "wp-content", "wp-includes", "category", "tag", "author")

ASSET_EXT = re.compile(r"\.(css|js|mjs|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|otf|eot|mp4|webm|json|pdf)$", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl()


def page_slug(url):
    """Retorna o slug ('' para home) se a URL for uma página do site, senão None."""
    u = urllib.parse.urlsplit(url)
    if u.netloc not in OWN_HOSTS:
        return None
    path = u.path.strip("/")
    if path.startswith(SKIP_PREFIXES) or ASSET_EXT.search(path):
        return None
    return path


def local_asset_path(url):
    """Mapeia URL absoluta de asset para o caminho local (root-relative) ou None."""
    u = urllib.parse.urlsplit(url)
    if u.netloc in OWN_HOSTS:
        return urllib.parse.unquote(u.path)
    if u.netloc in EXTRA_HOSTS:
        return EXTRA_HOSTS[u.netloc] + urllib.parse.unquote(u.path)
    return None


# ---------------------------------------------------------------- de-Airlift

def json_array_after(html, marker):
    i = html.find(marker)
    if i < 0:
        return []
    arr, _ = json.JSONDecoder().raw_decode(html, html.find("[", i))
    return arr


def render_attrs(attrs, drop=("defer", "async", "bv_inline_delayed", "data-cfasync")):
    out = []
    for k, v in attrs.items():
        if k in drop or v is False or v is None:
            continue
        out.append(k if v is True else f'{k}="{escape(str(v), quote=True)}"')
    return (" " + " ".join(out)) if out else ""


def decode_placeholder(data_uri):
    """Extrai a URL real de um placeholder SVG do Airlift (bv-img-url)."""
    try:
        svg = base64.b64decode(data_uri.split("base64,", 1)[1]).decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(r'bv-img-url="([^"]+)"', svg)
    return unescape(m.group(1)) if m else None


def deoptimize(html):
    scripts = {s["bv_unique_id"]: s for s in json_array_after(html, "var scriptAttrs = ")}
    styles = {s["bv_unique_id"]: s for s in json_array_after(html, "var linkStyleAttrs = ")}

    # Scripts e CSS do próprio Airlift
    html = re.sub(r'<script\b[^>]*\bbv-exclude="true"[^>]*>.*?</script>', "", html, flags=re.S)
    html = re.sub(r'<script\b[^>]*\bid="bv-[^"]*"[^>]*>.*?</script>', "", html, flags=re.S)
    html = re.sub(r'<style\b[^>]*\bclass="bv-critical-css"[^>]*>.*?</style>', "", html, flags=re.S)
    html = re.sub(r'<style\b[^>]*\bid="bv-balanced-font-css"[^>]*>.*?</style>', "", html, flags=re.S)
    html = re.sub(r'<link\b[^>]*(?:class="bv-preload"|id="bv-preloaded")[^>]*>\s*', "", html)

    # Marcadores <template id> -> <link>/<script src> originais, na mesma posição
    def template(m):
        tid = m.group(1)
        if tid in styles:
            return f"<link{render_attrs(styles[tid]['attrs'])} />"
        s = scripts.get(tid)
        if s and s["attrs"].get("src") and not s["attrs"]["src"].startswith("data:"):
            return f"<script{render_attrs(s['attrs'])}></script>"
        return ""
    html = re.sub(r'<template id="?([^">\s]+)"?></template>', template, html)

    # Scripts inline adiados -> scripts normais
    def inline_script(m):
        attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))
        keep = {k: v for k, v in attrs.items() if k == "id"}
        return f"<script{render_attrs(keep)}>"
    html = re.sub(r'<script\b([^>]*\btype="bv_inline_delayed_js"[^>]*)>', inline_script, html)

    # CSS inline adiado -> CSS normal
    html = re.sub(r'(<style\b[^>]*?)\s+type="bv_inline_delayed_css"', r"\1", html)

    # Imagens em placeholder -> URL real
    def placeholder(m):
        real = decode_placeholder(m.group(2))
        return f"{m.group(1)}{real}" if real else m.group(0)
    html = re.sub(r'(\bsrc=["\']|url\((?:&quot;|["\'])?)(data:image/svg\+xml;base64,[A-Za-z0-9+/=]+)', placeholder, html)
    html = re.sub(r'\s*\bbv-image-(?:lazyload|preloaded)\b', "", html)
    return html


# ---------------------------------------------------------------- reescrita

# Para em aspas, inclusive as codificadas (&quot; / &#039;) usadas em data-settings do Elementor
URL_RE = re.compile(r"https?:(?://|\\/\\/)(?:www\.)?(?:axxiscontabilidade\.com\.br|grupoaxxis\.com\.br)(?:(?!&quot;|&#0?39;|&#34;)[^\s\"'<>()])*")
# Arquivos carregados dinamicamente (chunks do webpack do Elementor etc.), descobertos rodando a cópia
EXTRA_ASSETS = Path(__file__).resolve().parent / "extra-assets.txt"


def rewrite(text, assets, pages, *, escaped_ok=True):
    """Troca URLs absolutas do site por caminhos locais e registra o que baixar."""
    def repl(m):
        raw = m.group(0)
        esc = "\\/" in raw
        url = raw.replace("\\/", "/").rstrip(".,;")
        tail = raw[len(raw.rstrip(".,;")):]
        url = url.replace("http://", "https://")
        u = urllib.parse.urlsplit(url)
        slug = page_slug(url)
        if slug is not None:
            if slug.strip("/") in DEAD_SLUGS:
                new = "#"
            else:
                pages.add(slug)
                new = "/" + (slug + "/" if slug else "") + (f"#{u.fragment}" if u.fragment else "")
        else:
            lp = local_asset_path(url)
            if lp is not None and u.netloc in OWN_HOSTS and u.path.startswith(("/wp-content/", "/wp-includes/")) and not ASSET_EXT.search(u.path):
                # Diretório base de assets (ex.: config do Elementor): só torna relativo
                new = urllib.parse.quote(lp, safe="/%")
                return (new.replace("/", "\\/") if esc else new) + tail
            if lp is None or not ASSET_EXT.search(u.path):
                # Não é arquivo estático (wp-json, feed, xmlrpc, domínio do grupo): mantém absoluto
                return raw
            assets.add(urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, "", "")))
            new = urllib.parse.quote(lp, safe="/%") + (f"?{u.query}" if u.query else "")
        if esc:
            new = new.replace("/", "\\/")
        return new + tail
    return URL_RE.sub(repl, text)


def rewrite_css(css, base_url, assets, pages):
    # url(relativo) -> absoluto antes de reescrever
    def absolutize(m):
        q, ref = m.group(1), m.group(2)
        if ref.startswith(("data:", "http:", "https:", "//", "#")):
            return m.group(0)
        return f"url({q}{urllib.parse.urljoin(base_url, ref)}{q})"
    css = re.sub(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", absolutize, css)
    css = re.sub(r"@import\s+(['\"])([^'\"]+)\1", lambda m: m.group(0) if m.group(2).startswith("http") else f"@import {m.group(1)}{urllib.parse.urljoin(base_url, m.group(2))}{m.group(1)}", css)
    return rewrite(css, assets, pages)


def save(path, data):
    dest = OUT / path.lstrip("/")
    if sys.platform == "win32":
        # Alguns caminhos do Airlift passam do limite de 260 caracteres do Windows
        dest = Path("\\\\?\\" + str(dest.resolve()))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def main():
    pages, done = {""}, set()
    assets, fetched_assets = set(), set()
    failed = []

    while pages - done:
        for slug in sorted(pages - done):
            done.add(slug)
            url = f"{ORIGIN}/{slug + '/' if slug else ''}"
            try:
                body, final = fetch(url)
            except urllib.error.HTTPError as e:
                failed.append((url, e.code))
                continue
            html = deoptimize(body.decode("utf-8"))
            found = set()
            html = rewrite(html, assets, found)
            pages |= {p for p in found if p not in DEAD_SLUGS}
            save(f"{slug}/index.html" if slug else "index.html", html.encode("utf-8"))
            print(f"página  /{slug}")

    if EXTRA_ASSETS.exists():
        assets |= {ORIGIN + line.strip() for line in EXTRA_ASSETS.read_text().splitlines() if line.strip().startswith("/")}

    def get_asset(url):
        try:
            data, _ = fetch(url)
            return url, data, None
        except Exception as e:  # noqa: BLE001
            return url, None, e

    with ThreadPoolExecutor(12) as pool:
        while assets - fetched_assets:
            batch = sorted(assets - fetched_assets)
            fetched_assets |= set(batch)
            for url, data, err in pool.map(get_asset, batch):
                if err:
                    failed.append((url, err))
                    continue
                lp = local_asset_path(url)
                if lp.endswith(".css"):
                    data = rewrite_css(data.decode("utf-8", "replace"), url, assets, set()).encode("utf-8")
                elif lp.endswith((".js", ".mjs")):
                    data = rewrite(data.decode("utf-8", "replace"), assets, set()).encode("utf-8")
                save(lp, data)
            print(f"assets  {len(fetched_assets)}")

    print(f"\n{len(done)} páginas, {len(fetched_assets)} assets")
    for url, err in failed:
        print("FALHOU", url, err, file=sys.stderr)


if __name__ == "__main__":
    main()
