# Axxis Consultiva

Cópia estática do site axxiscontabilidade.com.br (WordPress + Elementor), servida por nginx.

- `site/` — HTML e assets gerados
- `tools/mirror.py` — regera `site/` a partir do site em produção (`python tools/mirror.py`)
- `tools/extra-assets.txt` — arquivos carregados só via JS que o espelhamento não detecta sozinho

Páginas não copiadas (links ficam sem ação): solicite sua proposta e conteúdos.

## Deploy (Easypanel)

App com source neste repositório, build por **Dockerfile**, porta **80**.
