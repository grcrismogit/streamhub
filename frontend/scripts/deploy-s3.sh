#!/usr/bin/env bash
# Compila la SPA y sube SOLO el contenido de dist/ al bucket del frontend.
# Uso: BUCKET=streamhub-frontend-XXXX VITE_API_URL=http://<IP-ELASTICA> bash scripts/deploy-s3.sh
set -euo pipefail
BUCKET="${BUCKET:?Define BUCKET}"
: "${VITE_API_URL:?Define VITE_API_URL (URL pública de la API en EC2)}"
cd "$(dirname "$0")/.."

npm ci
npm run build

# 1) Assets con hash en el nombre → caché larga e inmutable.
aws s3 sync dist/ "s3://$BUCKET/" --delete --exclude "index.html" \
  --cache-control "public, max-age=31536000, immutable"
# 2) index.html sin caché → los usuarios siempre reciben la última versión.
aws s3 cp dist/index.html "s3://$BUCKET/index.html" \
  --cache-control "no-cache, no-store, must-revalidate" --content-type "text/html; charset=utf-8"

echo "Desplegado en s3://$BUCKET"
