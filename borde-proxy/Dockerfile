FROM openresty/openresty:alpine

# Copiar librerías Lua instaladas localmente (100% Offline / Air-Gapped)
COPY site/ /usr/local/openresty/site/

# Crear directorios de ejecución
RUN mkdir -p /usr/local/openresty/nginx/lua /etc/nginx/certs /var/run /usr/local/openresty/nginx/logs

# Copiar configuración principal y scripts Lua de borde
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY lua/ /usr/local/openresty/nginx/lua/
COPY default_policy.json /usr/local/openresty/nginx/default_policy.json

# Copiar certificados TLS 1.3
COPY certs/server.crt /etc/nginx/certs/server.crt
COPY certs/server.key /etc/nginx/certs/server.key
COPY certs/ca.crt /etc/nginx/certs/ca.crt

EXPOSE 80 443

CMD ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]
