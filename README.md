# RZWire

Private editorial publishing workspace for the RZ Token Family.

## Brands

- MGC Coin
- Ranking Platform
- Oasis Coin
- Jewelry Coin

## Application

- Backend: Python 3.11, SQLite, raw HTTP server on port 3001
- Frontend: React and Vite
- AI and image generation: OpenRouter
- Production web server: Nginx

## Local start

Run `setup-rzwire-local.ps1` once, then use `start-rzwire-local.ps1` to start the backend and frontend.

The local frontend is available at `http://localhost:5173` and the backend health endpoint is `http://localhost:3001/api/health`.

Publishing and Google Sheets integrations are disabled by default until RZWire credentials are configured.

## Deployment

The deployment target is locked by `DEPLOYMENT_TARGET.lock`. Use `publish-rzwire-update.ps1` with an explicit file list to commit, push, and deploy future updates safely.

See `deploy/README.md` and `VPS_DEPLOYMENT_STANDARD.md` for operational details. Private keys, environment files, databases, caches, installed dependencies, and generated build output are never committed.
