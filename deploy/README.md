# RZWire deployment

Target VPS: Ubuntu 24.04 at `137.74.160.38:22` as the deployment administrator. The application itself runs as the restricted `rzwire` system user at `/var/www/rzwire`.

Initial public address: `http://137.74.160.38` (HTTP only). A domain and HTTPS can be added later; neither is required for the first launch.

## One-time VPS preparation

1. Copy this project to `/var/www/rzwire` on the new Ubuntu/Debian VPS.
2. Create `/var/www/rzwire/backend/.env` from `deploy/rzwire-production.env.example`. Do not commit it. Keep publishing and Sheets disabled until their new RZWire connections are supplied.
3. Run `bash /var/www/rzwire/deploy/bootstrap-rzwire-vps.sh` as root.
4. When DNS is ready, replace the IP in `/etc/nginx/sites-available/rzwire` with the final RZWire domain and add SSL.

## Locked project updates

The authoritative target is stored in the root `DEPLOYMENT_TARGET.lock`. The update script refuses a mismatched VPS, remote folder, port, or project identity and blocks the known target belonging to the other project.

Always deploy an explicit file list:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy-to-vps.ps1 -Files "backend/handlers/example.py,frontend/src/components/Example.jsx"
```

To run local checks, update GitLab, and then deploy the same explicit application files to the locked VPS:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-rzwire-update.ps1 -Message "Describe the update" -Files "backend/handlers/example.py,frontend/src/components/Example.jsx"
```

GitLab CI independently verifies the backend tests and frontend production build. The direct workspace deployment is responsible for updating the VPS, preventing two deployments from racing each other.

Never store VPS passwords, SSH private keys, API keys, or `.env` files in GitLab repository files.
