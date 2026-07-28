#!/usr/bin/env bash
set -euo pipefail

# Run once on a new Ubuntu/Debian VPS as root.
RZWIRE_DEPLOY_PATH="${RZWIRE_DEPLOY_PATH:-/var/www/rzwire}"

apt-get update
apt-get install -y nginx python3 python3-venv python3-pip rsync curl ca-certificates gnupg

# Vite 8 requires a current Node.js release. Ubuntu 24.04's default Node package
# is older, so install Node.js 22 from the signed NodeSource repository.
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
printf '%s\n' 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main' \
  > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y nodejs

id -u rzwire >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin rzwire
mkdir -p "$RZWIRE_DEPLOY_PATH" "$RZWIRE_DEPLOY_PATH/backend/data"
chown -R rzwire:rzwire "$RZWIRE_DEPLOY_PATH"

if [ ! -f "$RZWIRE_DEPLOY_PATH/backend/.env" ]; then
  install -m 600 -o rzwire -g rzwire \
    "$RZWIRE_DEPLOY_PATH/deploy/rzwire-production.env.example" \
    "$RZWIRE_DEPLOY_PATH/backend/.env"
fi

install -m 644 "$RZWIRE_DEPLOY_PATH/deploy/rzwire-backend.service" /etc/systemd/system/rzwire-backend.service
install -m 644 "$RZWIRE_DEPLOY_PATH/deploy/rzwire-nginx.conf" /etc/nginx/sites-available/rzwire
ln -sfn /etc/nginx/sites-available/rzwire /etc/nginx/sites-enabled/rzwire
rm -f /etc/nginx/sites-enabled/default

python3 -m venv "$RZWIRE_DEPLOY_PATH/.venv"
"$RZWIRE_DEPLOY_PATH/.venv/bin/pip" install --upgrade pip
"$RZWIRE_DEPLOY_PATH/.venv/bin/pip" install -r "$RZWIRE_DEPLOY_PATH/backend/requirements.txt"

systemctl daemon-reload
systemctl enable rzwire-backend
nginx -t
systemctl enable nginx
systemctl restart nginx

echo "Bootstrap complete. Review $RZWIRE_DEPLOY_PATH/backend/.env, then run deploy/release-rzwire.sh."
