"""Ajustes de SEO aplicados sobre ./site depois do espelhamento.

Uso: python tools/mirror.py && python tools/seo.py

- title, description, canonical e Open Graph absolutos por página (tools/seo_data.py)
- um H1 por página, textos e subtítulos revisados, alt nas imagens, lazy loading
- schema.org próprio (AccountingService, WebPage, BreadcrumbList, Service, FAQPage)
- limpeza do <head> herdado do WordPress e do documento HTML colado no header
- imagens de compartilhamento 1200x630, compressão das imagens grandes
- sitemap.xml, robots.txt e 404.html
"""
import datetime
import json
import re
import sys
from html import escape, unescape
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seo_data import ALTS, BASE, GLOBAL_REPLACE, HERO_SUB_DEFAULT, LOCKED, ORG, PAGES  # noqa: E402

SITE = Path(__file__).resolve().parent.parent / "site"
TODAY = datetime.date.today().isoformat()
ORG_ID = BASE + "/#organization"
SITE_ID = BASE + "/#website"


def fs(path):
    """Caminho no disco para um caminho do site (com suporte a caminhos longos no Windows)."""
    p = (SITE / path.lstrip("/")).resolve()
    return Path("\\\\?\\" + str(p)) if sys.platform == "win32" else p


def page_url(slug):
    return f"{BASE}/{slug + '/' if slug else ''}"


def abs_url(path):
    return path if path.startswith("http") else BASE + path


# ---------------------------------------------------------------- limpeza

def strip_nested_document(html):
    """O header do Elementor é um bloco HTML com um documento inteiro colado (<html>, <head>, <title>...)."""
    start = html.index(">", html.index("<body")) + 1
    end = html.rindex("</body>")
    body = html[start:end]
    body = re.sub(r"<!DOCTYPE[^>]*>|</?html\b[^>]*>|</?head>|</?body\b[^>]*>", "", body, flags=re.I)
    body = re.sub(r'<meta\s+(?:charset|name="viewport")[^>]*>', "", body, flags=re.I)
    body = re.sub(r"<title>.*?</title>", "", body, flags=re.S | re.I)
    return html[:start] + body + html[end:]


def clean_head(html):
    html = re.sub(r'<meta name="generator"[^>]*>\s*', "", html)
    html = re.sub(r'<link rel="(?:profile|pingback|EditURI|https://api\.w\.org/|shortlink)"[^>]*>\s*', "", html)
    html = re.sub(r'<link rel="alternate"[^>]*(?:rss\+xml|oembed|application/json)[^>]*>\s*', "", html)
    html = re.sub(r'<link rel="(?:preconnect|dns-prefetch)" href="(?:https:)?//fonts\.(?:googleapis|gstatic)\.com"[^>]*>\s*', "", html)
    # Emoji do WordPress: script e CSS desnecessários
    html = re.sub(r"<script\b[^>]*>(?:(?!</script>).)*?(?:_wpemojiSettings|wp-emoji-release)(?:(?!</script>).)*?</script>\s*", "", html, flags=re.S)
    html = re.sub(r"<style id='wp-emoji-styles-inline-css'[^>]*>.*?</style>\s*", "", html, flags=re.S)
    # viewport duplicado
    vp = list(re.finditer(r'<meta name="viewport"[^>]*>\s*', html))
    for m in reversed(vp[1:]):
        html = html[: m.start()] + html[m.end():]
    # schema do Yoast é substituído pelo nosso
    html = re.sub(r'<script type="application/ld\+json" class="yoast-schema-graph">.*?</script>\s*', "", html, flags=re.S)
    return html


# ---------------------------------------------------------------- conteúdo

def replace_once(html, old, new, slug, required=True):
    if old not in html:
        if required:
            print(f"  ! /{slug}: trecho não encontrado: {old[:60]!r}")
        return html
    return html.replace(old, new)


def apply_content(html, slug, cfg):
    for old, new in GLOBAL_REPLACE:
        html = replace_once(html, old, new, slug, required=False)
    for old, new in cfg.get("replace", []):
        html = replace_once(html, old, new, slug)
    if "h1" in cfg:
        html, n = re.subn(r"(<h1\b[^>]*>).*?(</h1>)", lambda m: m.group(1) + cfg["h1"] + m.group(2), html, count=1, flags=re.S)
        if not n:
            print(f"  ! /{slug}: H1 não encontrado")
    if "sub" in cfg:
        html = replace_once(html, f">{HERO_SUB_DEFAULT}<", f">{cfg['sub']}<", slug)
    for pattern, new_html in cfg.get("insert_after", []):
        html, n = re.subn(pattern, lambda m: m.group(0) + "\n" + new_html, html, count=1)
        if not n:
            print(f"  ! /{slug}: ponto de inserção não encontrado: {pattern}")
    return html


def demote_h1(html, slug, cfg):
    for marker, css_old, css_new in cfg.get("demote", []):
        m = re.search(marker, html)
        if not m:
            print(f"  ! /{slug}: H1 secundário não encontrado: {marker}")
            continue
        i = html.index("<h1", m.start())
        j = html.index("</h1>", i)
        html = html[:i] + "<h2" + html[i + 3: j] + "</h2>" + html[j + 5:]
        html = html.replace(css_old, css_new)
    return html


def fix_headings(html):
    # Títulos dos carrosséis vinham como H4 logo abaixo de um H2 (estilo é pela classe)
    return re.sub(r'<h4 class="carousel-item-title">(.*?)</h4>', r'<h3 class="carousel-item-title">\1</h3>', html, flags=re.S)


def fix_images(html, slug):
    body_start = html.index("<body")
    count = 0

    def repl(m):
        nonlocal count
        tag = m.group(0)
        count += 1
        src = (re.search(r'\bsrc="([^"]*)"', tag) or [None, ""])[1]
        if not re.search(r'\balt="[^"]+"', tag):
            alt = next((v for k, v in ALTS.items() if k in src), None)
            if alt:
                tag = re.sub(r'\s*\balt=""', "", tag)
                tag = tag.replace("<img", f'<img alt="{escape(alt)}"', 1)
            else:
                print(f"  ! /{slug}: imagem sem alt: {src[-70:]}")
        # As duas primeiras imagens (logo do header) carregam normalmente; o resto, sob demanda
        if count > 2 and "loading=" not in tag:
            tag = tag.replace("<img", '<img loading="lazy"', 1)
        return tag

    return html[:body_start] + re.sub(r"<img\b[^>]*>", repl, html[body_start:])


# ---------------------------------------------------------------- meta tags

def set_tag(html, pattern, new_tag):
    if re.search(pattern, html):
        return re.sub(pattern, lambda m: new_tag, html, count=1)
    return html.replace("</head>", new_tag + "\n</head>", 1)


def meta_prop(prop, value):
    return f'<meta property="{prop}" content="{escape(value)}" />'


def make_og_image(slug, src):
    """Gera /og/<slug>.jpg (1200x630), formato aceito por todas as redes."""
    name = (slug or "home") + ".jpg"
    try:
        im = Image.open(fs(src.split("?")[0])).convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"  ! /{slug}: og:image {src}: {e}")
        return None
    w, h = im.size
    scale = max(1200 / w, 630 / h)
    im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    left, top = (im.width - 1200) // 2, (im.height - 630) // 2
    out = fs(f"/og/{name}")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.crop((left, top, left + 1200, top + 630)).save(out, "JPEG", quality=85, optimize=True, progressive=True)
    return f"/og/{name}"


def pick_og_source(html, cfg):
    if cfg.get("og_image"):
        return cfg["og_image"]
    m = re.search(r'<meta property="og:image" content="(/[^"]+)"', html)
    if m and re.search(r"\.(jpe?g|png|webp)$", m.group(1).split("?")[0]):
        return m.group(1)
    body = html[html.index("<body"):]
    for src in re.findall(r'<img\b[^>]*\bsrc="(/(?:wp-content|_ext)/[^"]+\.(?:jpe?g|webp))"', body):
        try:
            if Image.open(fs(src)).size[0] >= 800:
                return src
        except Exception:  # noqa: BLE001
            continue
    return PAGES[""]["og_image"]


def apply_meta(html, slug, cfg):
    url = page_url(slug)
    locked = slug in LOCKED
    title = cfg.get("title") or unescape(re.search(r"<title>(.*?)</title>", html, re.S).group(1)).strip()
    desc = cfg.get("description")
    if not desc:
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        desc = unescape(m.group(1)) if m else ""
    if not locked:
        assert len(title) <= 60, f"/{slug}: title com {len(title)} caracteres"
        assert 70 <= len(desc) <= 160, f"/{slug}: description com {len(desc)} caracteres"

    html = set_tag(html, r"<title>.*?</title>", f"<title>{escape(title, quote=False)}</title>")
    html = set_tag(html, r'<meta name="description"[^>]*>', f'<meta name="description" content="{escape(desc)}" />')
    html = set_tag(html, r'<link rel="canonical"[^>]*>', f'<link rel="canonical" href="{url}" />')
    html = set_tag(html, r'<meta property="og:title"[^>]*>', meta_prop("og:title", title))
    html = set_tag(html, r'<meta property="og:description"[^>]*>', meta_prop("og:description", desc))
    html = set_tag(html, r'<meta property="og:url"[^>]*>', meta_prop("og:url", url))
    html = set_tag(html, r'<meta property="og:type"[^>]*>', meta_prop("og:type", "website"))
    html = re.sub(r'<meta property="og:image(?::[a-z]+)?"[^>]*>\s*', "", html)
    html = re.sub(r'<meta name="twitter:(?:title|description|image)"[^>]*>\s*', "", html)

    og = make_og_image(slug, pick_og_source(html, cfg))
    og_tags = ""
    if og:
        og_tags = "\n".join([
            meta_prop("og:image", BASE + og), meta_prop("og:image:width", "1200"),
            meta_prop("og:image:height", "630"), meta_prop("og:image:type", "image/jpeg"),
            f'<meta name="twitter:image" content="{BASE + og}" />',
        ])
    twitter = f'<meta name="twitter:title" content="{escape(title)}" />\n<meta name="twitter:description" content="{escape(desc)}" />'
    html = html.replace("</head>", f"{og_tags}\n{twitter}\n</head>", 1)
    return html, title, desc, og


# ---------------------------------------------------------------- schema.org

def extract_faq(html):
    soup = BeautifulSoup(html, "html.parser")
    items, seen = [], set()
    for el in soup.find_all(class_=re.compile(r"(accordion|faq).*item", re.I)):
        q = el.find(class_=re.compile(r"header|question|title|pergunta", re.I))
        a = el.find(class_=re.compile(r"content|answer|body|resposta", re.I))
        if not q or not a:
            continue
        qt = re.sub(r"\s+", " ", q.get_text(" ", strip=True)).strip(" +-")
        at = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if qt and at and qt not in seen:
            seen.add(qt)
            items.append((qt, at))
    return items


def schema_graph(slug, cfg, title, desc, og, faq):
    url = page_url(slug)
    org = {
        "@type": "AccountingService", "@id": ORG_ID, "name": ORG["name"], "alternateName": ORG["alternateName"],
        "url": BASE + "/", "description": ORG["description"],
        "logo": {"@type": "ImageObject", "@id": BASE + "/#logo", "url": BASE + ORG["logo"], "width": 512, "height": 512},
        "image": BASE + "/og/home.jpg", "telephone": ORG["telephone"], "email": ORG["email"], "taxID": ORG["taxID"],
        "address": {"@type": "PostalAddress", **ORG["address"]},
        "areaServed": [{"@type": "City", "name": "Brasília"}, {"@type": "Country", "name": "Brasil"}],
        "sameAs": ORG["sameAs"],
        "parentOrganization": {"@type": "Organization", "name": ORG["parent"]["name"], "url": ORG["parent"]["url"]},
    }
    website = {"@type": "WebSite", "@id": SITE_ID, "url": BASE + "/", "name": ORG["name"], "inLanguage": "pt-BR", "publisher": {"@id": ORG_ID}}
    page_type = {"about": "AboutPage", "home": "WebPage"}.get(cfg["kind"], "WebPage")
    webpage = {
        "@type": page_type, "@id": url + "#webpage", "url": url, "name": title, "description": desc,
        "isPartOf": {"@id": SITE_ID}, "about": {"@id": ORG_ID}, "inLanguage": "pt-BR", "dateModified": TODAY,
    }
    if og:
        webpage["primaryImageOfPage"] = {"@type": "ImageObject", "url": BASE + og, "width": 1200, "height": 630}
    graph = [org, website, webpage]

    if slug:
        crumbs = [("Início", BASE + "/")]
        if cfg.get("parent"):
            crumbs.append((cfg["parent"][1], page_url(cfg["parent"][0])))
        crumbs.append((cfg["name"], url))
        graph.append({
            "@type": "BreadcrumbList", "@id": url + "#breadcrumb",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)],
        })
        webpage["breadcrumb"] = {"@id": url + "#breadcrumb"}
    if cfg.get("service"):
        graph.append({
            "@type": "Service", "@id": url + "#service", "name": cfg["service"], "serviceType": cfg["service"],
            "description": desc, "url": url, "provider": {"@id": ORG_ID},
            "areaServed": {"@type": "Country", "name": "Brasil"},
        })
        webpage["mainEntity"] = {"@id": url + "#service"}
    if faq:
        graph.append({
            "@type": "FAQPage", "@id": url + "#faq", "isPartOf": {"@id": url + "#webpage"},
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq],
        })
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{data.replace("</", "<\\/")}</script>'


# ---------------------------------------------------------------- imagens

def optimize_images(max_width=1920, min_bytes=200_000):
    saved = 0
    for path in (fs("/wp-content/uploads"), fs("/_ext")):
        for f in path.rglob("*"):
            if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp") or f.stat().st_size < min_bytes:
                continue
            before = f.stat().st_size
            im = Image.open(f)
            im.load()
            if im.width > max_width:
                im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
            tmp = f.with_name(f.name + ".tmp")
            fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[f.suffix.lower()]
            if fmt == "JPEG":
                im.convert("RGB").save(tmp, fmt, quality=82, optimize=True, progressive=True)
            elif fmt == "WEBP":
                im.save(tmp, fmt, quality=80, method=6)
            else:
                im.save(tmp, fmt, optimize=True)
            if tmp.stat().st_size < before * 0.95:
                tmp.replace(f)
                saved += before - f.stat().st_size
            else:
                tmp.unlink()
    print(f"imagens: {saved / 1_048_576:.1f} MB economizados")


# ---------------------------------------------------------------- arquivos do site

def write_sitemap():
    priority = {"home": "1.0", "service": "0.9", "sector": "0.8", "about": "0.7", "page": "0.7", "legal": "0.3"}
    urls = "".join(
        f"  <url><loc>{page_url(s)}</loc><lastmod>{TODAY}</lastmod><priority>{priority[c['kind']]}</priority></url>\n"
        for s, c in PAGES.items()
    )
    fs("/sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n', encoding="utf-8")
    fs("/robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")


def write_404():
    links = [("", "Início"), ("nossas-solucoes", "Nossas Soluções"), ("areas-de-atuacao", "Áreas de Atuação"), ("sobre-nos", "Sobre Nós")]
    items = "".join(f'<a href="/{s + "/" if s else ""}">{n}</a>' for s, n in links)
    fs("/404.html").write_text(f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, follow" />
<title>Página não encontrada | Axxis Contabilidade</title>
<link rel="icon" href="/wp-content/uploads/2025/08/cropped-Logo-Antiga-Axxis-1080-x-1350-px-2-32x32.png" />
<style>
  body {{ margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #000425; color: #efefef; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; text-align: center; padding: 24px; box-sizing: border-box; }}
  img {{ width: 180px; margin-bottom: 32px; }}
  h1 {{ font-size: clamp(28px, 5vw, 44px); margin: 0 0 12px; }}
  h1 span {{ color: #ff6d00; }}
  p {{ color: #b8bdd0; margin: 0 0 32px; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }}
  a {{ color: #efefef; text-decoration: none; border: 1px solid rgba(255,255,255,.2); border-radius: 6px; padding: 10px 18px; }}
  a:first-child {{ background: #ff6d00; border-color: #ff6d00; }}
</style>
</head>
<body>
<main>
  <img src="/wp-content/uploads/al_opt_content/IMAGE/axxiscontabilidade.com.br/wp-content/uploads/2026/01/Design-sem-nome-14.png.bv.webp" alt="Axxis Contabilidade Consultiva" />
  <h1>Página <span>não encontrada</span></h1>
  <p>O endereço que você acessou não existe ou mudou de lugar.</p>
  <nav>{items}</nav>
</main>
</body>
</html>
""", encoding="utf-8")


MARKER = '<meta name="x-seo" content="tools/seo.py" />'


def main():
    if MARKER in fs("/index.html").read_text(encoding="utf-8"):
        sys.exit("site/ já passou pelo seo.py. Rode antes: python tools/mirror.py")
    for slug, cfg in PAGES.items():
        path = fs(f"/{slug}/index.html" if slug else "/index.html")
        html = path.read_text(encoding="utf-8")
        html = html.replace("</head>", MARKER + "\n</head>", 1)
        html = strip_nested_document(html)
        html = clean_head(html)
        if slug not in LOCKED:
            html = apply_content(html, slug, cfg)
        html = demote_h1(html, slug, cfg)
        if cfg.get("css"):
            html = html.replace("</head>", f"<style>{cfg['css']}</style>\n</head>", 1)
        html = fix_headings(html)
        html = fix_images(html, slug)
        html, title, desc, og = apply_meta(html, slug, cfg)
        faq = extract_faq(html)
        html = html.replace("</head>", schema_graph(slug, cfg, title, desc, og, faq) + "\n</head>", 1)
        h1s = len(re.findall(r"<h1\b", html))
        if h1s != 1:
            print(f"  ! /{slug}: {h1s} H1")
        path.write_text(html, encoding="utf-8")
        print(f"/{slug:32} title {len(title):2}  desc {len(desc):3}  faq {len(faq)}")
    write_sitemap()
    write_404()
    optimize_images()


if __name__ == "__main__":
    main()
