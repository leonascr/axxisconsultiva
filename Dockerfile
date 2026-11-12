FROM nginx:1.27-alpine
# O nginx.conf entra como template: na subida, a imagem oficial troca ${CONSULTIVA_CHAVE} pelo valor
# do Easypanel e grava o resultado em /etc/nginx/conf.d/default.conf. O filtro limita a troca às
# variáveis CONSULTIVA_*, para nenhuma outra variável de ambiente mexer na configuração. Sem a
# variável no painel, o valor padrão vazio mantém o nginx de pé (o formulário só é recusado).
ENV NGINX_ENVSUBST_FILTER=^CONSULTIVA_
ENV CONSULTIVA_CHAVE=""
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY public/ /usr/share/nginx/html/
EXPOSE 80
