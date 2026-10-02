#!/usr/bin/env bash
# =============================================================================
#  Instalación de la API StreamHub en EC2 (Amazon Linux 2023).
#  Uso (dentro de la instancia):
#     curl -O https://raw.githubusercontent.com/<usuario>/<repo>/main/backend/deploy/setup_ec2.sh
#     sudo REPO_URL=https://github.com/<usuario>/<repo>.git bash setup_ec2.sh
#  Es idempotente: se puede volver a ejecutar para actualizar.
# =============================================================================
set -euo pipefail

REPO_URL="${REPO_URL:?Define REPO_URL con la URL de tu repositorio}"
BRANCH="${BRANCH:-main}"
APP_DIR=/opt/streamhub
ENV_FILE=/etc/streamhub/api.env

echo "==> Paquetes del sistema"
dnf install -y python3.11 python3.11-pip git nginx postgresql15 >/dev/null

echo "==> Usuario de servicio sin privilegios"
id streamhub &>/dev/null || useradd --system --home "$APP_DIR" --shell /sbin/nologin streamhub

echo "==> Código fuente"
git config --global --add safe.directory "$APP_DIR"  # el repo pertenece al usuario streamhub
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> Entorno virtual y dependencias"
python3.11 -m venv "$APP_DIR/backend/.venv"
"$APP_DIR/backend/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/backend/.venv/bin/pip" install --quiet -r "$APP_DIR/backend/requirements.txt"
chown -R streamhub:streamhub "$APP_DIR"

echo "==> Variables de entorno"
mkdir -p /etc/streamhub
if [ ! -f "$ENV_FILE" ]; then
  cp "$APP_DIR/backend/.env.example" "$ENV_FILE"
  # Genera un secreto JWT aleatorio automáticamente.
  SECRET=$(python3.11 -c "import secrets; print(secrets.token_urlsafe(64))")
  sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$SECRET|" "$ENV_FILE"
  echo "   !! Edita $ENV_FILE con los datos de RDS, S3 y CORS y vuelve a ejecutar este script."
fi
chown root:streamhub "$ENV_FILE"
chmod 640 "$ENV_FILE"

if grep -q "xxxxxxxx\|XXXX\|cambia-esto" "$ENV_FILE"; then
  echo "   !! $ENV_FILE todavía tiene valores de ejemplo. Complétalo y re-ejecuta."
  exit 1
fi

# La app (y Alembic) leen /etc/streamhub/api.env directamente con pydantic-settings.
run_as_app() { (cd "$APP_DIR/backend" && sudo -u streamhub "$@"); }

echo "==> Diagnóstico previo: IAM Role, RDS y S3"
# Si RDS aún no tiene tablas, el diagnóstico avisa; lo importante aquí es la conectividad.
run_as_app .venv/bin/python -m app.diagnostics || echo "   (Si solo faltan tablas, la migración siguiente las crea.)"

echo "==> Migraciones de base de datos (Alembic)"
run_as_app .venv/bin/alembic upgrade head

echo "==> systemd + Nginx"
cp "$APP_DIR/backend/deploy/streamhub-api.service" /etc/systemd/system/streamhub-api.service
cp "$APP_DIR/backend/deploy/nginx-streamhub.conf" /etc/nginx/conf.d/streamhub.conf
# Nuestro sitio debe ser el servidor por defecto del puerto 80: se quita la marca
# default_server del bloque de ejemplo de nginx.conf (si la tuviera).
sed -i 's/ default_server//g' /etc/nginx/nginx.conf
# Si SELinux está en modo enforcing, permitir que Nginx se conecte a Uvicorn.
command -v setsebool >/dev/null && [ "$(getenforce 2>/dev/null)" = "Enforcing" ] && setsebool -P httpd_can_network_connect 1
nginx -t
systemctl daemon-reload
systemctl enable --now nginx streamhub-api
systemctl restart streamhub-api
systemctl reload nginx

sleep 3
echo "==> Health check (a través de Nginx)"
curl -fsS http://127.0.0.1/health && echo
echo "==> Diagnóstico final"
run_as_app .venv/bin/python -m app.diagnostics
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || true)
echo "Listo. Documentación: http://${PUBLIC_IP:-<IP-PUBLICA>}/docs"
