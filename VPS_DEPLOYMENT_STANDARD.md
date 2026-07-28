# RZWire VPS deployment standard

RZWire uses a locked, project-specific, explicit-file deployment workflow.

## Target protection

`DEPLOYMENT_TARGET.lock` is the authority for the project ID, VPS address, SSH port, remote folder, and service names. `deploy-to-vps.ps1` refuses any mismatch and also refuses the known VPS and remote folder belonging to the other project.

## Workspace key

The project-specific private key is `.deploy_rzwire_vps_key` in the project root. It is ignored by Git and must never be pasted into chat or copied into the repository.

If normal PowerShell needs the key permissions corrected:

```powershell
icacls ".\.deploy_rzwire_vps_key" /inheritance:r
icacls ".\.deploy_rzwire_vps_key" /grant:r "$($env:COMPUTERNAME)\$($env:USERNAME):(R)"
```

If a sandboxed Codex process cannot read that key, use a temporary copy:

```powershell
Copy-Item ".\.deploy_rzwire_vps_key" "$env:TEMP\rzwire_deploy_key_codex" -Force
icacls "$env:TEMP\rzwire_deploy_key_codex" /inheritance:r
icacls "$env:TEMP\rzwire_deploy_key_codex" /grant:r "$($env:COMPUTERNAME)\$($env:USERNAME):(R)"
powershell -ExecutionPolicy Bypass -File .\deploy-to-vps.ps1 -SshKeyPath "$env:TEMP\rzwire_deploy_key_codex" -Files "backend/handlers/example.py,frontend/src/components/Example.jsx"
```

## Explicit deployment

Never rely on Git auto-detection. Name every application file being deployed:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy-to-vps.ps1 -Files "backend/handlers/example.py,frontend/src/components/Example.jsx"
```

To verify the list without changing the VPS, add `-DryRun`.

To test, commit, push to GitLab, and deploy the same explicit files to the VPS:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-rzwire-update.ps1 -Message "Describe the update" -Files "backend/handlers/example.py,frontend/src/components/Example.jsx"
```

## Verification

Every deployment checks both services and the backend health endpoint. Manual verification is:

```powershell
ssh -i .\.deploy_rzwire_vps_key root@137.74.160.38 "systemctl is-active rzwire-backend; systemctl is-active nginx; curl -fsS http://127.0.0.1:3001/api/health"
```
