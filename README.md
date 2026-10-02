# Axxis Consultiva

Site da Axxis Contabilidade Consultiva (axxiscontabilidade.com.br): HTML, CSS e JS estáticos,
servidos por nginx. Não depende de WordPress, Elementor ou plugins.

## Estrutura

```
public/
  index.html, <página>/index.html   páginas (título, description e dados estruturados no <head>)
  404.html, robots.txt, sitemap.xml
  assets/
    css/base.css, css/site.css      estilos comuns a todas as páginas
    js/site.js                      fundos sob demanda e vídeo de fundo
    img/, img/og/                   imagens (WebP) e imagens de compartilhamento
    fonts/, video/                  fontes (Outfit, Sora, ícones) e vídeo
    vendor/swiper/                  biblioteca dos carrosséis
nginx.conf                          redirects (www, http->https, páginas antigas) e cache
Dockerfile                          imagem nginx com public/
```

Cada página tem também um `<style>` próprio no `<head>` e os blocos de conteúdo com seus estilos e scripts.
Ferramentas externas (Analytics, GTM, Meta Pixel, Clarity) estão desligadas e serão adicionadas uma a uma.

## Rodar localmente

```
npm start
```

e abrir http://localhost:3000.

## Deploy (Easypanel)

App com source neste repositório, build por **Dockerfile**, porta **80**. Domínio `axxiscontabilidade.com.br`
(e `www.axxiscontabilidade.com.br`, que o nginx redireciona para o domínio principal).

Depois de apontar o domínio: enviar `https://axxiscontabilidade.com.br/sitemap.xml` no Google Search Console.

## Histórico

O site foi migrado do WordPress com ferramentas usadas uma única vez (cópia, SEO, otimização de imagens e
conversão para HTML independente). Elas estão no histórico do git, commit `868c7c6`, pasta `tools/`.
