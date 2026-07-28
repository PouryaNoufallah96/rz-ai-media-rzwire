#!/usr/bin/env bash
set -euo pipefail

RZWIRE_DEPLOY_PATH="${RZWIRE_DEPLOY_PATH:-/var/www/rzwire}"
cd "$RZWIRE_DEPLOY_PATH"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt

cd frontend
npm ci
npm run build

chown -R rzwire:rzwire "$RZWIRE_DEPLOY_PATH"
systemctl restart rzwire-backend
nginx -t
systemctl reload nginx
