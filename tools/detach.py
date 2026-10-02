"""Converte site/ (cópia do WordPress já com SEO e desempenho) em public/: site estático
independente, sem WordPress, Elementor ou plugins.

- remove scripts e configurações do WordPress/Elementor/plugins (fica só Swiper + JS próprio)
- junta os CSS dos plugins em /assets/css/base.css e site.css, só com as regras usadas
- renomeia classes, ids e variáveis CSS (elementor-*, e-con, wp-*, hfe-*...) para ax-*
- move imagens, fontes, vídeo e bibliotecas para /assets/
- remove atributos, comentários e marcas do construtor

Uso (migração, uma vez): npm run build:wp && python tools/detach.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from html import unescape
from pathlib import Path

import tinycss2

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site"
OUT = ROOT / "public"
BASE = "https://axxiscontabilidade.com.br"

DROP_INLINE_SCRIPTS = ("elementorFrontendConfig", "EAELImageMaskingConfig", "UltimatePostKitConfig",
                       "WprConfig", "var localize", "lazyloadRunObserver")
WP_THEME_TOKENS = {"home", "page", "hfeed", "hentry", "type-page", "status-publish", "site-main", "page-content"}
FORBIDDEN = re.compile(r"elementor|wp-content|wp-includes|wordpress|wp-json|xmlrpc|al_opt|airlift|bv-|wpr|eael|upk-|"
                       r"\bhfe|\behf|hello-|--wp--|WPHeader|WPFooter|_ext/", re.I)

SITE_JS = """// Comportamentos do site (substitui o JS do construtor antigo)

// Imagens de fundo das seções só carregam quando a seção se aproxima da tela
(function () {
  var sections = document.querySelectorAll('.ax-con.ax-parent:not(.ax-lazyloaded)');
  if (!('IntersectionObserver' in window)) {
    sections.forEach(function (s) { s.classList.add('ax-lazyloaded'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add('ax-lazyloaded');
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: '200px 0px' });
  sections.forEach(function (s) { io.observe(s); });
})();

// Vídeos de fundo: só baixam quando visíveis (no celular ficam ocultos)
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('video[data-src]').forEach(function (v) {
    if (v.offsetParent === null) return;
    v.src = v.dataset.src;
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  });
});
"""
EXTRA_CSS = ".ax-background-video-container video{width:100%;height:100%;object-fit:cover}"


# ---------------------------------------------------------------- arquivos

def lp(p):
    p = Path(p).resolve()
    return Path("\\\\?\\" + str(p)) if sys.platform == "win32" else p


def read_text(p):
    return lp(p).read_text(encoding="utf-8")


def write(p, data):
    f = lp(p)
    f.parent.mkdir(parents=True, exist_ok=True)
    (f.write_bytes if isinstance(data, bytes) else lambda d: f.write_text(d, encoding="utf-8"))(data)


def page_files():
    slugs = re.findall(r"<loc>https?://[^/]+(/[^<]*)</loc>", read_text(SRC / "sitemap.xml"))
    return [(s, (s.strip("/") + "/index.html") if s != "/" else "index.html") for s in slugs]


# ---------------------------------------------------------------- nomes

# Cada origem ganha um prefixo próprio: nomes iguais de plugins diferentes não podem colidir
# (ex.: .wpr-flex e .e-flex virando ambos .ax-flex escondia as camadas dos banners)
PREFIXES = [(r"^elementor[-_]", "ax-"), (r"^e-(?=con|flex|parent|child|grid|lazyloaded|no-lazyload)", "ax-"),
            (r"^(?:hfe|ehf)-", "axh-"), (r"^wpr-", "axr-"), (r"^eael-", "axe-"), (r"^upk-", "axu-"),
            (r"^she-", "axs-"), (r"^wp-", "axw-")]
GENERATED = ("ax-", "axh-", "axr-", "axe-", "axu-", "axs-", "axw-", "theme-")
_renamed = {}  # nome novo -> nome antigo


def rename_token(t):
    if t == "elementor":
        n = "ax"
    else:
        n = t
        for pattern, prefix in PREFIXES:
            n = re.sub(pattern, prefix, n)
        n = n.replace("elementor", "ax").replace("hello-", "theme-")
    if n == t:
        return t
    if _renamed.setdefault(n, t) != t:
        n = f"{n}-{hashlib.md5(t.encode()).hexdigest()[:4]}"
        _renamed.setdefault(n, t)
    return n


def is_wp_token(t):
    return (rename_token(t) != t or t in WP_THEME_TOKENS
            or re.match(r"(?:page|post)-\d|page-id-|page-template|ehf-|hfeed", t) is not None)


def css_rename(css):
    css = re.sub(r"([.#])(-?[_a-zA-Z][\w-]*)", lambda m: m.group(1) + rename_token(m.group(2)), css)
    css = re.sub(r"--e-", "--ax-", css).replace("--wp--", "--axw--")
    css = re.sub(r"--(wpr|eael|upk)-", lambda m: {"wpr": "--axr-", "eael": "--axe-", "upk": "--axu-"}[m.group(1)], css)
    css = re.sub(r"(?<![a-z0-9])(wpr|eael|upk|hfe|ehf)-",
                 lambda m: {"wpr": "axr-", "eael": "axe-", "upk": "axu-", "hfe": "axh-", "ehf": "axh-"}[m.group(1)], css)
    return re.sub(r"elementor", "ax", css, flags=re.I)


# ---------------------------------------------------------------- assets

class Assets:
    """Mapeia caminhos antigos (wp-content, _ext, _img, og) para /assets/..."""

    def __init__(self):
        self.new_for_old, self.old_for_new, self.css_queue = {}, {}, []

    @staticmethod
    def _clean(name):
        name = name.lower().replace(".bv", "")
        stem, ext = os.path.splitext(name)
        stem = re.sub(r"\.(png|jpe?g|webp|gif)$", "", stem)
        stem = stem.replace("elementor", "ax").replace("-scaled", "")
        stem = re.sub(r"[^a-z0-9.-]+", "-", stem).strip("-.")[:80]
        return stem, ext

    def _new_path(self, path):
        stem, ext = self._clean(path.rsplit("/", 1)[-1])
        name = stem + ext
        if "/cdnjs.cloudflare.com/ajax/libs/" in path:
            lib = path.split("/ajax/libs/")[1].split("/")[0]
            return f"/assets/vendor/{lib}/" + ("webfonts/" if "/webfonts/" in path else "") + name
        if "/cdn.jsdelivr.net/npm/" in path:
            lib = path.split("/npm/")[1].split("/")[0].split("@")[0]
            return f"/assets/vendor/{lib}/{name}"
        if "fonts.googleapis.com" in path:
            return f"/assets/fonts/google-{stem}{ext}"
        if ext in (".woff2", ".woff", ".ttf", ".otf", ".eot") or (ext == ".svg" and "font" in path):
            return f"/assets/fonts/{name}"
        if ext == ".css":
            return f"/assets/css/{name}"
        if ext in (".mp4", ".webm"):
            return f"/assets/video/{name.replace('-web.', '.')}"
        if path.startswith("/og/"):
            return f"/assets/img/og/{name}"
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico"):
            return f"/assets/img/{name}"
        return f"/assets/misc/{name}"

    def map(self, ref):
        path = urllib.parse.unquote(ref.split("?")[0].split("#")[0])
        if path in self.new_for_old:
            return self.new_for_old[path]
        new = self._new_path(path)
        if new in self.old_for_new and self.old_for_new[new] != path:
            stem, ext = os.path.splitext(new)
            new = f"{stem}-{hashlib.md5(path.encode()).hexdigest()[:6]}{ext}"
        self.new_for_old[path], self.old_for_new[new] = new, path
        if new.endswith(".css"):
            self.css_queue.append((path, new))
        return new


# Para em aspas, inclusive as codificadas (&quot;) de style="background-image:url(&quot;...&quot;)"
PATH_RE = re.compile(r"(https?://(?:www\.)?axxiscontabilidade\.com\.br)?(/(?:wp-content|wp-includes|_ext|_img|og)/(?:(?!&quot;|&#0?39;)[^\s\"'()<>,\\])+)")


def rewrite_paths(text, assets):
    return PATH_RE.sub(lambda m: (m.group(1) or "") + assets.map(m.group(2)), text)


# ---------------------------------------------------------------- CSS dos plugins

LINK_RE = re.compile(r"<link\b(?=[^>]*\brel=[\"']stylesheet[\"'])[^>]*>\s*")
STYLE_RE = re.compile(r"<style\b([^>]*)>(.*?)</style>\s*", re.S)


def attr(tag, name):
    m = re.search(rf"\b{name}=[\"']([^\"']*)[\"']", tag)
    return m.group(1) if m else None


def stylesheet_nodes(html):
    """[(kind, chave, conteúdo/href, no_head, match)] na ordem do documento."""
    body_at = html.index("<body")
    nodes = []
    for m in LINK_RE.finditer(html):
        href = attr(m.group(0), "href") or ""
        nodes.append(("link", attr(m.group(0), "id") or href, href, m.start() < body_at, m))
    for m in STYLE_RE.finditer(html):
        content = m.group(2)
        nodes.append(("style", hashlib.md5(content.encode()).hexdigest(), content, m.start() < body_at, m))
    return sorted(nodes, key=lambda n: n[4].start())


def collect_global_css(pages):
    """CSS do WordPress/plugins comum a todas as páginas -> (base, site, chaves globais)."""
    per_page = {slug: stylesheet_nodes(read_text(SRC / f)) for slug, f in pages}
    head_styles = [set(n[1] for n in nodes if n[0] == "style" and n[3]) for nodes in per_page.values()]
    global_styles = set.intersection(*head_styles)
    link_src = {}
    for nodes in per_page.values():
        for kind, key, href, _, _ in nodes:
            if kind == "link" and "/wp-content/" in href and ("al_opt" not in href or key not in link_src):
                link_src[key] = href
    canonical = max((n for s, n in per_page.items() if s != "/"), key=len)
    order, seen = [], set()
    for nodes in [canonical] + list(per_page.values()):
        for kind, key, val, head, _ in nodes:
            is_global = (kind == "link" and key in link_src) or (kind == "style" and key in global_styles)
            if is_global and key not in seen:
                seen.add(key)
                order.append((kind, key, val, head))
    first_page_style = next((n[4].start() for n in canonical if n[0] == "style" and n[3] and n[1] not in global_styles), None)
    base, after = [], []
    for kind, key, val, head in order:
        css = read_text(SRC / urllib.parse.unquote(link_src[key].split("?")[0]).lstrip("/")) if kind == "link" else val
        node = next((n for n in canonical if n[1] == key), None)
        before_page = node is not None and head and first_page_style is not None and node[4].start() < first_page_style
        (base if before_page else after).append(f"/* {key} */\n{css}")
    return "\n".join(base), "\n".join(after), set(link_src) | global_styles


# ---------------------------------------------------------------- páginas

SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>\s*", re.S)


def fix_scripts(html):
    uses_swiper, custom_js = False, []

    def repl(m):
        nonlocal uses_swiper
        attrs, body = m.group(1), m.group(2)
        src = attr(attrs, "src") or ""
        if "application/ld+json" in attrs:
            return m.group(0)
        if "speculationrules" in attrs:
            return ""
        if src:
            if "swiper" in src:
                uses_swiper = True
                return ""  # vai para o <head> com defer
            if "/wp-content/" in src or "/wp-includes/" in src:
                return ""
            return m.group(0)
        if any(k in body for k in DROP_INLINE_SCRIPTS):
            return ""
        # Ganchos do Elementor nos scripts próprios: o init já roda no DOMContentLoaded
        # if (jQuery) { gancho do Elementor } else { init no carregamento }  ->  só o init
        body = re.sub(r"if\s*\([^)]*jQuery[^)]*\)\s*\{\s*(?:window\.)?jQuery\(window\)\.on\([^;]*\);\s*\}\s*else\s*\{([^{}]*)\}", r"\1", body)
        body = re.sub(r"(?:window\.)?jQuery\(window\)\.on\(\s*['\"]elementor/frontend/init['\"]\s*,\s*function\s*\(\)\s*\{\s*"
                      r"elementorFrontend\.hooks\.addAction\([^{]*\{[^{}]*\}\s*\);\s*\}\s*\);", "", body)
        body = re.sub(r"if\s*\([^)]*jQuery[^)]*\)\s*\{\s*(?:window\.)?jQuery\(window\)\.on\(\s*['\"]elementor/frontend/init['\"]\s*,\s*\w+\s*\);\s*\}", "", body)
        body = re.sub(r"(?:window\.)?jQuery\(window\)\.on\(\s*['\"]elementor/frontend/init['\"]\s*,", "document.addEventListener('DOMContentLoaded',", body)
        body = re.sub(r"^[ \t]*//[^\n]*elementor[^\n]*\n", "", body, flags=re.I | re.M)
        if re.search(r"elementor|jQuery", body, re.I):
            print(f"  ! script próprio ainda cita elementor/jQuery: {body.strip()[:80]!r}")
        custom_js.append(body)
        return f"<script>{body}</script>\n"

    return SCRIPT_RE.sub(repl, html), uses_swiper, custom_js


def add_video_sources(html, assets):
    """O vídeo de fundo era montado pelo JS do Elementor a partir de data-settings."""
    for m in re.finditer(r'data-settings="([^"]*background_video_link[^"]*)"', html):
        link = json.loads(unescape(m.group(1))).get("background_video_link", "")
        path = re.sub(r"^https?://[^/]+", "", link)
        if not path:
            continue
        i = html.find("<video", m.end())
        new = assets.map(path)
        html = html[:i] + f'<video data-src="{new}" preload="none"' + html[i + len("<video"):]
    return html


def restructure_styles(html, global_keys):
    nodes = [n for n in stylesheet_nodes(html) if n[1] in global_keys]
    for n in reversed(nodes):
        html = html[: n[4].start()] + html[n[4].end():]
    head_end = html.index("</head>")
    page_styles = [m for m in STYLE_RE.finditer(html[:head_end])]
    site_link = '<link rel="stylesheet" href="/assets/css/site.css" />\n'
    base_link = '<link rel="stylesheet" href="/assets/css/base.css" />\n'
    if page_styles:
        last = page_styles[-1].end()
        html = html[:last] + site_link + html[last:]
        first = page_styles[0].start()
        return html[:first] + base_link + html[first:]
    return html.replace("</head>", base_link + site_link + "</head>", 1)


def outside_code(html, fn_markup, fn_style=None):
    """Aplica fn_markup ao HTML fora de <script>/<style> e fn_style ao conteúdo dos <style>."""
    out, pos = [], 0
    for m in re.finditer(r"<(script|style)\b[^>]*>.*?</\1>", html, re.S):
        out.append(fn_markup(html[pos:m.start()]))
        block = m.group(0)
        if m.group(1) == "style" and fn_style:
            i, j = block.index(">") + 1, block.rindex("</style>")
            block = block[:i] + fn_style(block[i:j]) + block[j:]
        out.append(block)
        pos = m.end()
    out.append(fn_markup(html[pos:]))
    return "".join(out)


def clean_markup(markup, drop_unused=None):
    markup = re.sub(r"<!--(?!\[if).*?-->", "", markup, flags=re.S)
    markup = re.sub(r"\s(?:data-(?:id|element_type|e-type|widget_type|settings|start|end|elementor-[\w-]+|bv-[\w-]+)|bv[-_][\w-]+)=(?:\"[^\"]*\"|'[^']*')", "", markup)
    markup = re.sub(r'\sitemscope(?:="")?|\sitemtype="https://schema\.org/WP\w+"', "", markup)
    markup = re.sub(r'\sstyle="([^"]*)"', lambda m: f' style="{css_rename(m.group(1))}"', markup)

    def classes(m):
        q, val = m.group(1), m.group(2)
        tokens = []
        for t in val.split():
            n = rename_token(t)
            # Classes vindas do construtor (já renomeadas para ax-*) que nenhum CSS/JS usa saem do HTML
            generated = is_wp_token(t) or t == "ax" or t.startswith(GENERATED)
            if drop_unused is not None and generated and n not in drop_unused:
                continue
            tokens.append(n)
        return f" class={q}{' '.join(dict.fromkeys(tokens))}{q}" if tokens else ""
    markup = re.sub(r"\sclass=([\"'])(.*?)\1", classes, markup)
    return re.sub(r"\sid=([\"'])(.*?)\1", lambda m: f" id={m.group(1)}{rename_token(m.group(2))}{m.group(1)}", markup)


def transform_page(html, assets, global_keys):
    html = add_video_sources(html, assets)
    html, uses_swiper, custom_js = fix_scripts(html)
    html = restructure_styles(html, global_keys)
    html = rewrite_paths(html, assets)
    html = re.sub(r'<meta name="x-(?:seo|perf)"[^>]*>\s*', "", html)
    # ids das tags <style>/<link>/<script> eram nomes de plugins e não servem para nada
    html = re.sub(r"<(style|link|script)\b([^>]*?)\s+id=([\"'])[^\"']*\3", r"<\1\2", html)
    html = outside_code(html, clean_markup, css_rename)
    head = '<script defer src="/assets/js/site.js"></script>\n'
    if uses_swiper:
        head = f'<script defer src="{assets.map("/_ext/cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js")}"></script>\n' + head
    html = html.replace("</head>", head + "</head>", 1)
    return re.sub(r"\n\s*\n+", "\n", html), "\n".join(custom_js)


# ---------------------------------------------------------------- limpeza do CSS

STATE_PSEUDO = re.compile(
    r"::?(?:before|after|placeholder|selection|marker|first-letter|first-line|backdrop|-webkit-[\w-]+|-moz-[\w-]+|-ms-[\w-]+)"
    r"|:(?:hover|focus-within|focus-visible|focus|active|visited|link|target|checked|disabled|enabled|invalid|valid|"
    r"required|optional|placeholder-shown|autofill|indeterminate|default|read-only|read-write|empty)(?![\w-])")
DYNAMIC = re.compile(r"\.(?:active|open|opened|show|shown|is-[\w-]+|current[\w-]*|visible|scrolled|sticky|expanded|"
                     r"collapsed|toggled|selected|loaded|ax-lazyloaded|swiper-[\w-]+|menu-open|hover)(?![\w-])")


def test_selector(sel):
    t = DYNAMIC.sub("", STATE_PSEUDO.sub("", sel))
    t = re.sub(r"(^|[\s>+~(,])(?=[\s>+~),]|$)", r"\1*", t)
    return t.strip() or "*"


def split_selectors(prelude):
    parts = [[]]
    for tok in prelude:
        if tok.type == "literal" and tok.value == ",":
            parts.append([])
        else:
            parts[-1].append(tok)
    return [tinycss2.serialize(p).strip() for p in parts if tinycss2.serialize(p).strip()]


def parse_rules(css):
    return tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)


def collect_tests(rules, out):
    for r in rules:
        if r.type == "qualified-rule":
            out.update(test_selector(s) for s in split_selectors(r.prelude))
        elif r.type == "at-rule" and r.content is not None and r.lower_at_keyword in ("media", "supports", "container", "layer"):
            collect_tests(tinycss2.parse_rule_list(r.content, skip_comments=True, skip_whitespace=True), out)


def purge(rules, used):
    """Lista de (cabeçalho, corpo ou sub-regras) só com os seletores usados."""
    out = []
    for r in rules:
        if r.type == "qualified-rule":
            keep = [s for s in split_selectors(r.prelude) if test_selector(s) in used]
            if keep:
                out.append(("rule", ",".join(keep), r.content))
        elif r.type == "at-rule":
            kw = r.lower_at_keyword
            if kw in ("media", "supports", "container", "layer") and r.content is not None:
                inner = purge(tinycss2.parse_rule_list(r.content, skip_comments=True, skip_whitespace=True), used)
                if inner:
                    out.append(("block", f"@{r.at_keyword}{tinycss2.serialize(r.prelude)}".rstrip(), inner))
            elif kw != "charset":
                out.append(("at", r.lower_at_keyword, r))
    return out


def declarations(content):
    return [d for d in tinycss2.parse_declaration_list(content, skip_comments=True, skip_whitespace=True) if d.type == "declaration"]


def decl_text(d):
    return f"{d.name}:{tinycss2.serialize(d.value).strip()}{' !important' if d.important else ''}"


def render(items, keep_var, fonts, animations):
    out = []
    for kind, head, body in items:
        if kind == "rule":
            decls = [decl_text(d) for d in declarations(body) if not d.name.startswith("--") or d.name in keep_var]
            if decls:
                out.append(f"{head}{{{';'.join(decls)}}}")
        elif kind == "block":
            inner = render(body, keep_var, fonts, animations)
            if inner:
                out.append(f"{head}{{{inner}}}")
        elif head == "font-face":
            fam = next((tinycss2.serialize(d.value).strip().strip("'\"").lower() for d in declarations(body.content) if d.name == "font-family"), "")
            if fam in fonts:
                out.append(f"@font-face{{{';'.join(decl_text(d) for d in declarations(body.content))}}}")
        elif head in ("keyframes", "-webkit-keyframes"):
            name = tinycss2.serialize(body.prelude).strip()
            if name in animations:
                out.append(tinycss2.serialize([body]))
        else:
            out.append(tinycss2.serialize([body]))
    return "\n".join(out)


def used_names(texts):
    joined = "\n".join(texts)
    fonts = set()
    for m in re.finditer(r"font(?:-family)?\s*:([^;}{]+)", joined):
        fonts |= {f.strip().strip("'\"").lower() for f in m.group(1).split(",")}
    anims = set(re.findall(r"[\w-]+", " ".join(re.findall(r"animation(?:-name)?\s*:([^;}{]+)", joined))))
    return fonts, anims


def keep_vars(items_list, other_texts):
    """Variáveis CSS referenciadas por var(); repete até estabilizar (variáveis que usam variáveis)."""
    keep = set(re.findall(r"var\(\s*(--[\w-]+)", "\n".join(other_texts)))
    while True:
        refs = set(keep)
        for items in items_list:
            for txt in _decl_texts(items, keep):
                refs |= set(re.findall(r"var\(\s*(--[\w-]+)", txt))
        if refs == keep:
            return keep
        keep = refs


def _decl_texts(items, keep):
    for kind, head, body in items:
        if kind == "rule":
            for d in declarations(body):
                if not d.name.startswith("--") or d.name in keep:
                    yield decl_text(d)
        elif kind == "block":
            yield from _decl_texts(body, keep)


# ---------------------------------------------------------------- principal

def main():
    if OUT.exists() and any(OUT.iterdir()):
        print("public/ já existe: os arquivos serão sobrescritos (sobras antigas são listadas no final)")
    pages = page_files()
    assets = Assets()
    base_css, site_css, global_keys = collect_global_css(pages)
    base_css = css_rename(rewrite_paths(base_css, assets))
    site_css = css_rename(rewrite_paths(site_css, assets)) + "\n" + EXTRA_CSS

    html_out, js_texts = {}, [SITE_JS]
    for slug, f in pages + [("/404.html", "404.html")]:
        html, js = transform_page(read_text(SRC / f), assets, global_keys) if f != "404.html" else (rewrite_paths(read_text(SRC / f), assets), "")
        html_out[f] = html
        js_texts.append(js)

    # CSS de terceiros referenciado (Google Fonts, Font Awesome, Swiper): copia com caminhos novos
    vendor_css = {}
    while assets.css_queue:
        old, new = assets.css_queue.pop()
        vendor_css[new] = rewrite_paths(read_text(SRC / old.lstrip("/")), assets)

    # Fase 1: grava páginas e CSS ainda completo para medir o que é usado
    for f, html in html_out.items():
        write(OUT / f, html)
    for new, css in vendor_css.items():
        write(OUT / new.lstrip("/"), css)
    write(OUT / "assets/js/site.js", SITE_JS)
    write(OUT / "assets/css/base.css", base_css)
    write(OUT / "assets/css/site.css", site_css)
    # Font Awesome: só os ícones usados (o arquivo completo traz ~2.000)
    purgeable = {new: css for new, css in vendor_css.items() if "/vendor/font-awesome/" in new}
    parsed = {"base": parse_rules(base_css), "site": parse_rules(site_css)}
    parsed.update({new: parse_rules(css) for new, css in purgeable.items()})
    tests = set()
    for rules in parsed.values():
        collect_tests(rules, tests)
    asset_files = {new: str(SRC / old.lstrip("/")) for new, old in assets.old_for_new.items() if not new.endswith(".css")}
    with tempfile.TemporaryDirectory() as tmp:
        inp, outp = Path(tmp) / "in.json", Path(tmp) / "out.json"
        inp.write_text(json.dumps({"root": str(OUT), "assets": asset_files, "pages": [s for s, _ in pages], "tests": sorted(tests)}), encoding="utf-8")
        subprocess.run(["node", str(ROOT / "tools" / "css-usage.mjs"), str(inp), str(outp)], check=True)
        used = set(json.loads(outp.read_text(encoding="utf-8")))
    print(f"css: {len(used)} de {len(tests)} seletores em uso")

    # Fase 2: CSS só com o que é usado (regras, fontes, animações e variáveis)
    items = {k: purge(rules, used) for k, rules in parsed.items()}
    other_css = ([re.sub(r"<script\b.*?</script>", "", h, flags=re.S) for h in html_out.values()]
                 + [css for new, css in vendor_css.items() if new not in purgeable] + js_texts)
    keep_var = keep_vars(list(items.values()), other_css)
    fonts, anims = used_names(other_css + [t for it in items.values() for t in _decl_texts(it, keep_var)])
    rendered = {k: render(it, keep_var, fonts, anims) for k, it in items.items()}
    base_final, site_final = rendered.pop("base"), rendered.pop("site")
    write(OUT / "assets/css/base.css", base_final)
    write(OUT / "assets/css/site.css", site_final)
    for new, css in rendered.items():
        license_header = re.match(r"\s*(/\*!.*?\*/)", purgeable[new], re.S)
        vendor_css[new] = (license_header.group(1) + "\n" if license_header else "") + css
        write(OUT / new.lstrip("/"), vendor_css[new])
        print(f"css: {new} {len(purgeable[new]) // 1024} KB -> {len(vendor_css[new]) // 1024} KB")
    print(f"css: base.css {len(base_css) // 1024} KB -> {len(base_final) // 1024} KB, site.css {len(site_css) // 1024} KB -> {len(site_final) // 1024} KB")

    # Fase 3: tira das páginas as classes antigas que nenhum CSS/JS usa
    all_css = "\n".join([base_final, site_final] + [s for h in html_out.values() for s in re.findall(r"<style\b[^>]*>(.*?)</style>", h, re.S)] + list(vendor_css.values()))
    used_tokens = set(re.findall(r"[.#](-?[_a-zA-Z][\w-]*)", all_css)) | set(re.findall(r"[\w-]+", "\n".join(js_texts)))
    for f, html in html_out.items():
        html = outside_code(html, lambda m: clean_markup(m, used_tokens))
        html_out[f] = html
        write(OUT / f, html)

    # Fase 4: copia só os arquivos referenciados
    referenced = set()
    for text in list(html_out.values()) + [base_final, site_final] + list(vendor_css.values()):
        referenced |= set(re.findall(r"/assets/(?:(?!&quot;|&#0?39;)[^\s\"'()<>,\\])+", text))
    copied = 0
    for new in sorted(referenced):
        old = assets.old_for_new.get(urllib.parse.unquote(new))
        if old and not new.endswith(".css"):
            src = SRC / old.lstrip("/")
            if lp(src).exists():
                write(OUT / new.lstrip("/"), lp(src).read_bytes())
                copied += 1
            else:
                print(f"  ! arquivo não encontrado: {old}")
    for name in ("robots.txt", "sitemap.xml"):
        shutil.copyfile(lp(SRC / name), lp(OUT / name))
    print(f"assets: {copied} arquivos copiados")

    # Conferência: nada do WordPress/Elementor pode sobrar
    leftovers = {}
    for p in OUT.rglob("*"):
        if p.suffix in (".html", ".css", ".js", ".xml", ".txt"):
            for m in FORBIDDEN.finditer(read_text(p)):
                leftovers.setdefault(m.group(0).lower(), set()).add(p.relative_to(OUT).as_posix())
    for k, v in sorted(leftovers.items()):
        print(f"  ! sobrou '{k}' em {len(v)} arquivo(s): {sorted(v)[:3]}")
    # Arquivos de conversões anteriores que nada mais referencia (podem ser apagados)
    keep = {"/" + f for f in html_out} | {"/robots.txt", "/sitemap.xml", "/assets/js/site.js"}
    stale = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*")
                   if p.is_file() and "/" + p.relative_to(OUT).as_posix() not in referenced | keep)
    if stale:
        print(f"  {len(stale)} arquivo(s) sem uso em public/ (sobras): " + ", ".join(stale[:5]) + (" ..." if len(stale) > 5 else ""))
    print("pronto: public/")


if __name__ == "__main__":
    main()
