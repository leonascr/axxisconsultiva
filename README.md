# Axxis Consultiva

Site estático de axxiscontabilidade.com.br (copiado do WordPress + Elementor), servido por nginx.

- `site/` — HTML e assets gerados (todas as imagens, fontes e bibliotecas são locais)
- `tools/mirror.py` — copia o site em produção para `site/`
- `tools/seo.py` — ajustes de SEO (títulos, descriptions, schema, sitemap, fontes...)
- `tools/seo_data.py` — **textos de SEO por página**: título, description, H1, subtítulos e trechos revisados
- `tools/measure.mjs` — mede em que tamanho cada imagem aparece (gera `tools/image-sizes.json`)
- `tools/perf.py` — desempenho: imagens WebP no tamanho certo, scripts com defer, vídeo comprimido
- `tools/extra-assets.txt` — arquivos carregados só via JS que o espelhamento não detecta sozinho

Ferramentas externas (GTM, Analytics, Meta Pixel, Clarity) estão **desligadas** por enquanto:
o `perf.py` remove todas. Para religar uma, ela deve ser adicionada depois do build.

## Preparar o ambiente (uma vez)

```
pip install -r requirements.txt
npm install
npx playwright install chromium
```

## Regerar o site

```
npm run build
```

Roda em sequência: `mirror.py` → `seo.py` → `measure.mjs` → `perf.py`.
Para mudar um título ou texto de SEO, edite `tools/seo_data.py` e rode o build.
A página de academias (`empresas-do-fitness`) está em `LOCKED`: os textos dela não são alterados.

Páginas não copiadas (links ficam sem ação): solicite sua proposta e conteúdos.

## Rodar localmente

```
npm start
```

e abrir http://localhost:3000.

## Deploy (Easypanel)

App com source neste repositório, build por **Dockerfile**, porta **80**. Domínio `axxiscontabilidade.com.br`
(e `www.axxiscontabilidade.com.br`, que o nginx redireciona para o domínio principal).

Depois de apontar o domínio: enviar `https://axxiscontabilidade.com.br/sitemap.xml` no Google Search Console.
