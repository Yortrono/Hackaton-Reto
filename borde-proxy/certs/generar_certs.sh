#!/usr/bin/env bash
set -euo pipefail

CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CERTS_DIR"

echo "=== Generando Autoridad Certificadora (CA) Soberana Local ==="
openssl genrsa -out ca.key 4096 2>/dev/null
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
    -subj "/C=VE/ST=Distrito Capital/L=Caracas/O=Soberania Digital/OU=Infraestructura/CN=CA Raiz Soberana" 2>/dev/null

echo "=== Generando Clave Privada y Certificado para Servidor (TLS 1.3) ==="
openssl genrsa -out server.key 2048 2>/dev/null

cat << 'EOF' > server_cert.cnf
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C = VE
ST = Distrito Capital
L = Caracas
O = Republica Bolivariana de Venezuela
OU = Borde Perimetral
CN = localhost

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = portal.gob.local
IP.1 = 127.0.0.1
EOF

openssl req -new -key server.key -out server.csr -config server_cert.cnf 2>/dev/null

cat << 'EOF' > v3.ext
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = portal.gob.local
IP.1 = 127.0.0.1
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 825 -sha256 -extfile v3.ext 2>/dev/null

rm -f server.csr server_cert.cnf v3.ext

chmod 644 ca.crt server.crt
chmod 600 ca.key server.key

echo "=== Certificados generados exitosamente en: $CERTS_DIR ==="
