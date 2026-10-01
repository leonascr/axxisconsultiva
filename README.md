# Axxis Consultiva

Site estático de axxiscontabilidade.com.br (copiado do WordPress + Elementor), servido por nginx.

- `site/` — HTML e assets gerados (todas as imagens, fontes e bibliotecas são locais)
- `tools/mirror.py` — copia o site em produção para `site/`
- `tools/seo.py` — aplica os ajustes de SEO sobre `site/` (títulos, descriptions, schema, sitemap, imagens...)
- `tools/seo_data.py` — **textos de SEO por página**: título, description, H1, subtítulos e trechos revisados
- `tools/extra-assets.txt` — arquivos carregados só via JS que o espelhamento não detecta sozinho

## Regerar o site

```
python tools/mirror.py
python tools/seo.py
```

O `seo.py` precisa rodar sobre uma cópia recém-gerada pelo `mirror.py` (ele se recusa a rodar duas vezes).

Para mudar um título ou texto de SEO, edite `tools/seo_data.py` e rode os dois comandos.
A página de academias (`empresas-do-fitness`) está em `LOCKED`: os textos dela não são alterados.

Páginas não copiadas (links ficam sem ação): solicite sua proposta e conteúdos.

## Rodar localmente

```
npx serve site -l 3000
```

## Deploy (Easypanel)

App com source neste repositório, build por **Dockerfile**, porta **80**. Domínio `axxiscontabilidade.com.br`
(e `www.axxiscontabilidade.com.br`, que o nginx redireciona para o domínio principal).

Depois de apontar o domínio: enviar `https://axxiscontabilidade.com.br/sitemap.xml` no Google Search Console.
