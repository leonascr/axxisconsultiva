"""Otimizações de desempenho aplicadas sobre ./site depois do seo.py.

Uso: npm run build   (mirror.py -> seo.py -> measure.mjs -> perf.py)

- imagens em WebP no tamanho em que aparecem (medido por tools/measure.mjs), sem srcset gigante
- pré-carregamento da imagem principal (LCP) de cada página
- todos os scripts com defer, mantendo a ordem
- ferramentas externas (GTM, Analytics, Meta Pixel, Clarity) removidas, para configurar uma a uma depois
- fonte de ícones Material Symbols só com os ícones usados
- desfoque (backdrop-filter) removido onde o fundo é liso e o efeito não aparece
- vídeo de fundo recomprimido
"""
import base64
import hashlib
import json
import math
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SIZES = Path(__file__).resolve().parent / "image-sizes.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
RASTER = (".jpg", ".jpeg", ".png", ".webp")
DENSITY = 2          # telas retina / celulares: imagem com o dobro dos pixels exibidos
WEBP_QUALITY = 78
# Fundo liso por trás: o desfoque não muda nada na tela, mas pesa na rolagem
NO_BLUR = ".card-base-v8,.accordion-item-final{-webkit-backdrop-filter:none!important;backdrop-filter:none!important}"
MARKER = '<meta name="x-perf" content="tools/perf.py" />'


def fs(path):
    p = (SITE / path.lstrip("/")).resolve()
    return Path("\\\\?\\" + str(p)) if sys.platform == "win32" else p


def html_files():
    return [fs("/" + p.relative_to(SITE).as_posix()) for p in SITE.rglob("index.html")]


def css_files():
    return [fs("/" + p.relative_to(SITE).as_posix()) for p in SITE.rglob("*.css")]


# ---------------------------------------------------------------- imagens

def short_name(path):
    stem = Path(path).name
    stem = re.sub(r"(\.bv)?(\.(jpe?g|png|webp))+$", "", stem, flags=re.I)
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:50]
    return f"{stem}-{hashlib.md5(path.encode()).hexdigest()[:6]}"


def resize_images(sizes):
    """Gera /_img/<nome>-<largura>.webp para cada imagem medida; devolve {caminho antigo: novo}."""
    mapping, before, after = {}, 0, 0
    for path, use in sizes["images"].items():
        if not path.lower().endswith(RASTER):
            continue
        src = fs(path)
        if not src.exists():
            continue
        with Image.open(src) as im:
            im.load()
            nw, nh = im.size
            # Fundo com background-size: cover pode precisar de mais largura que o elemento
            need = max(use["img"], use["bgW"], round(use["bgH"] * nw / nh) if use["bgH"] else 0) * DENSITY
            target = min(nw, math.ceil(need / 50) * 50) or nw
            out_path = f"/_img/{short_name(path)}-{target}.webp"
            out = fs(out_path)
            if not out.exists():
                img = im if target == nw else im.resize((target, round(nh * target / nw)), Image.LANCZOS)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.getbands() or "transparency" in im.info else "RGB")
                out.parent.mkdir(parents=True, exist_ok=True)
                img.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
        old_size, new_size = src.stat().st_size, out.stat().st_size
        if new_size < old_size * 0.95:
            mapping[path] = out_path
            before += old_size
            after += new_size
        else:
            out.unlink()
    print(f"imagens: {len(mapping)} reduzidas, {before / 1_048_576:.1f} MB -> {after / 1_048_576:.1f} MB")
    return mapping


def variants(path):
    """Formas em que um caminho aparece nos arquivos: cru, url-encoded e com \\/ (JSON do Elementor)."""
    forms = {path, urllib.parse.quote(path, safe="/%")}
    return forms | {f.replace("/", "\\/") for f in forms}


def rewrite_references(mapping):
    lookup = {}
    for old, new in mapping.items():
        for v in variants(old):
            lookup[v] = new.replace("/", "\\/") if "\\/" in v else new
    if not lookup:
        return
    pattern = re.compile("|".join(re.escape(k) for k in sorted(lookup, key=len, reverse=True)))
    for f in html_files() + css_files():
        text = f.read_text(encoding="utf-8")
        new = pattern.sub(lambda m: lookup[m.group(0)], text)
        if f.name == "index.html":
            # srcset/sizes antigos ainda apontariam para as versões gigantes
            new = re.sub(r'<img\b[^>]*\bsrc="/_img/[^>]*>',
                         lambda m: re.sub(r'\s+(?:srcset|sizes)="[^"]*"', "", m.group(0)), new)
        if new != text:
            f.write_text(new, encoding="utf-8")


def preload_lcp(html, slug, sizes, mapping):
    info = sizes["lcp"].get(slug) or {}
    # Só imagens: o LCP pode ser um vídeo, e preload "as=image" de um .mp4 baixaria o arquivo à toa
    desk, mob = (mapping.get(info.get(v), info.get(v)) if (info.get(v) or "").lower().endswith(RASTER) else None
                 for v in ("desktop", "mobile"))
    tags = []
    if desk and desk == mob:
        tags.append(f'<link rel="preload" as="image" href="{desk}" fetchpriority="high" />')
    else:
        if desk:
            tags.append(f'<link rel="preload" as="image" href="{desk}" fetchpriority="high" media="(min-width: 768px)" />')
        if mob:
            tags.append(f'<link rel="preload" as="image" href="{mob}" fetchpriority="high" media="(max-width: 767px)" />')
    for url in {desk, mob} - {None}:
        # Se a imagem principal é um <img>, ela não pode ficar com carregamento adiado
        html = re.sub(rf'<img\b[^>]*\bsrc="{re.escape(url)}"[^>]*>',
                      lambda m: m.group(0).replace(' loading="lazy"', "").replace("<img", '<img fetchpriority="high"', 1), html)
    return html.replace("<title>", "".join(t + "\n" for t in tags) + "<title>", 1) if tags else html


# ---------------------------------------------------------------- scripts

TRACKERS = r"googletagmanager|google-analytics|gtag\(|fbq\(|facebook\.net|clarity\.ms|clarity\("


def remove_trackers(html):
    """Remove GTM e demais ferramentas externas (Analytics, Meta Pixel, Clarity...): serão configuradas uma a uma depois."""
    html = re.sub(rf"<script\b[^>]*>(?:(?!</script>).)*?(?:{TRACKERS})(?:(?!</script>).)*?</script>\s*", "", html, flags=re.S)
    html = re.sub(rf"<script\b[^>]*\bsrc=\"[^\"]*(?:{TRACKERS})[^\"]*\"[^>]*>\s*</script>\s*", "", html)
    html = re.sub(rf"<noscript>(?:(?!</noscript>).)*?(?:{TRACKERS})(?:(?!</noscript>).)*?</noscript>\s*", "", html, flags=re.S)
    html = re.sub(rf"<link\b[^>]*(?:preconnect|dns-prefetch)[^>]*(?:{TRACKERS})[^>]*>\s*", "", html)
    return html


def defer_scripts(html):
    """defer em todos os scripts; os inline viram data: URI para manter a ordem de execução."""
    def repl(m):
        attrs, body = m.group(1), m.group(2)
        if re.search(r'\btype="(?!text/javascript")', attrs):
            return m.group(0)  # JSON-LD, speculationrules, templates
        if re.search(r"\bsrc=", attrs):
            return m.group(0) if re.search(r"\b(defer|async)\b", attrs) else f"<script defer{attrs}>{body}</script>"
        if not body.strip():
            return m.group(0)
        data = base64.b64encode(body.encode("utf-8")).decode("ascii")
        return f'<script defer{attrs} src="data:text/javascript;charset=utf-8;base64,{data}"></script>'
    return re.sub(r"<script\b([^>]*)>(.*?)</script>", repl, html, flags=re.S)


# ---------------------------------------------------------------- fonte de ícones

def subset_material_symbols():
    """Baixa a Material Symbols só com os ícones usados no site (de ~340 KB para poucos KB)."""
    pages = {f: f.read_text(encoding="utf-8") for f in html_files()}
    imports = {m for t in pages.values() for m in re.findall(r"@import url\('(/_ext/fonts\.googleapis\.com/[^']+)'\)", t)}
    for imp in imports:
        css = fs(imp).read_text(encoding="utf-8")
        if "Material Symbols" not in css:
            continue
        names = set()
        for text in pages.values():
            if imp not in text:
                continue
            classes = re.findall(r"\.([\w-]+)\s*\{[^}]*font-family:\s*['\"]Material Symbols", text)
            for cls in set(classes) | {"material-symbols-outlined"}:
                names |= set(re.findall(rf'class="[^"]*\b{re.escape(cls)}\b[^"]*"[^>]*>\s*([a-z0-9_]+)\s*<', text))
        if not names:
            continue
        url = ("https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,400,0,0"
               f"&icon_names={','.join(sorted(names))}&display=block")
        try:
            sub = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode()
            font_url = re.search(r"url\((https://[^)]+)\)", sub).group(1)
            font = urllib.request.urlopen(urllib.request.Request(font_url, headers={"User-Agent": UA}), timeout=30).read()
        except Exception as e:  # noqa: BLE001
            print(f"  ! Material Symbols: subset não baixado ({e}); mantida a fonte completa")
            continue
        font_path = f"/_ext/fonts.gstatic.com/material-symbols-subset-{hashlib.md5(font).hexdigest()[:8]}.woff2"
        fs(font_path).write_bytes(font)
        css_path = "/_ext/fonts.googleapis.com/material-symbols-subset.css"
        fs(css_path).write_text(sub.replace(font_url, font_path), encoding="utf-8")
        for f, text in pages.items():
            if imp in text:
                f.write_text(text.replace(imp, css_path), encoding="utf-8")
        print(f"ícones: Material Symbols reduzida a {len(names)} ícones ({len(font) / 1024:.0f} KB)")


# ---------------------------------------------------------------- vídeo

def compress_videos(min_bytes=2_000_000):
    """Gera <nome>-web.mp4 ao lado do original; devolve {caminho antigo: novo} para trocar as referências."""
    try:
        import imageio_ffmpeg
    except ImportError:
        print("  ! vídeos não comprimidos: pip install imageio-ffmpeg")
        return {}
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    mapping = {}
    for p in [p for p in SITE.rglob("*.mp4") if not p.stem.endswith("-web")]:
        rel = "/" + p.relative_to(SITE).as_posix()
        f = fs(rel)
        before = f.stat().st_size
        if before < min_bytes:
            continue
        out_rel = rel[: -len(".mp4")] + "-web.mp4"
        out = fs(out_rel)
        # Vídeo de fundo: sem áudio, 1280 px de largura, carregamento progressivo
        subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(f), "-an", "-vf", "scale='min(1280,iw)':-2",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "28", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)
        if out.stat().st_size < before * 0.9:
            mapping[rel] = out_rel
            print(f"vídeo: {p.name} {before / 1_048_576:.1f} MB -> {out.stat().st_size / 1_048_576:.1f} MB")
        else:
            out.unlink()
    return mapping


def main():
    if MARKER in fs("/index.html").read_text(encoding="utf-8"):
        sys.exit("site/ já passou pelo perf.py. Rode o build completo: npm run build")
    if not SIZES.exists():
        sys.exit("tools/image-sizes.json não existe. Rode antes: node tools/measure.mjs")
    sizes = json.loads(SIZES.read_text(encoding="utf-8"))

    mapping = resize_images(sizes)
    rewrite_references({**mapping, **compress_videos()})
    subset_material_symbols()

    for f in html_files():
        rel = f.parent.relative_to(fs("/")).as_posix()
        slug = "/" if rel == "." else f"/{rel}/"
        html = f.read_text(encoding="utf-8")
        html = html.replace("</head>", f"{MARKER}\n<style>{NO_BLUR}</style>\n</head>", 1)
        html = preload_lcp(html, slug, sizes, mapping)
        html = remove_trackers(html)
        html = defer_scripts(html)
        f.write_text(html, encoding="utf-8")
    print(f"scripts: defer e ferramentas externas removidas em {len(html_files())} páginas")


if __name__ == "__main__":
    main()
