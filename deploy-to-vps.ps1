#!/usr/bin/env pwsh
# RZWire locked, explicit-file VPS deployment.
# Uploads only the paths supplied through -Files. Production secrets, SQLite
# data, caches, build outputs, and the workspace SSH key are never deployable.

param(
    [Parameter(Mandatory = $true)]
    [string]$Files,
    [string]$VpsIP = "137.74.160.38",
    [int]$VpsPort = 22,
    [string]$VpsUser = "root",
    [string]$SshKeyPath = "",
    [string]$ProjectRoot = "",
    [string]$RemoteRoot = "/var/www/rzwire",
    [switch]$DryRun,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Continue"

if (-not $ProjectRoot) { $ProjectRoot = $PSScriptRoot }
if (-not $SshKeyPath) { $SshKeyPath = Join-Path $ProjectRoot ".deploy_rzwire_vps_key" }

function Step([string]$Message) { Write-Host "`n>>> $Message" -ForegroundColor Cyan }
function Ok([string]$Message) { Write-Host "    [OK] $Message" -ForegroundColor Green }
function Warn([string]$Message) { Write-Host "    [!!] $Message" -ForegroundColor Yellow }
function Die([string]$Message) { Write-Host "    ERROR: $Message" -ForegroundColor Red; exit 1 }

function Read-DeployLock([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { Die "Deployment lock missing: $Path" }
    $result = @{}
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2) { $result[$parts[0].Trim()] = $parts[1].Trim() }
        }
    }
    return $result
}

function Normalize-RelativePath([string]$Path) {
    $normalized = ($Path.Trim() -replace "\\", "/").TrimStart("./")
    if (-not $normalized -or $normalized.StartsWith("/") -or $normalized -match "(^|/)\.\.(/|$)") {
        Die "Unsafe or invalid project path: $Path"
    }
    return $normalized
}

function Test-Deployable([string]$Path) {
    if ($Path -eq "DEPLOYMENT_TARGET.lock") { return $true }
    if ($Path -notmatch "^(backend|frontend|deploy)/") { return $false }
    if ($Path -eq "backend/.env" -or $Path -like "backend/data/*") { return $false }
    if ($Path -like "*/.venv/*" -or $Path -like "*/node_modules/*" -or $Path -like "*/dist/*") { return $false }
    if ($Path -like "*/__pycache__/*" -or $Path -like "*.pyc" -or $Path -like "*.pkl") { return $false }
    if ($Path -like "*.log" -or $Path -like "*.pid" -or $Path -like "*.env") { return $false }
    return $true
}

Set-Location -LiteralPath $ProjectRoot
$lock = Read-DeployLock (Join-Path $ProjectRoot "DEPLOYMENT_TARGET.lock")

$required = @("project_id", "vps_ip", "vps_port", "remote_root", "backend_service", "frontend_service")
foreach ($name in $required) {
    if (-not $lock[$name]) { Die "Deployment lock is missing '$name'." }
}

if ($lock["project_id"] -ne "rzwire") { Die "This folder is not locked as the RZWire project." }
if ($VpsIP -eq $lock["forbid_vps_ip"]) { Die "Refusing forbidden VPS $VpsIP." }
if ($RemoteRoot -eq $lock["forbid_remote_root"]) { Die "Refusing forbidden remote folder $RemoteRoot." }
if ($VpsIP -ne $lock["vps_ip"]) { Die "Target mismatch: expected VPS $($lock['vps_ip']), got $VpsIP." }
if ([string]$VpsPort -ne $lock["vps_port"]) { Die "Port mismatch: expected $($lock['vps_port']), got $VpsPort." }
if ($RemoteRoot -ne $lock["remote_root"]) { Die "Path mismatch: expected $($lock['remote_root']), got $RemoteRoot." }

$requested = @($Files -split "," | ForEach-Object { Normalize-RelativePath $_ } | Sort-Object -Unique)
if ($requested.Count -eq 0) { Die "-Files must contain at least one explicit project file." }

foreach ($path in $requested) {
    if (-not (Test-Deployable $path)) { Die "File is outside the RZWire deployment allow-list: $path" }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ($path -replace "/", "\")))) {
        Die "Local file does not exist: $path"
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RZWire VPS Deploy (locked per-file)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VPS:        $VpsUser@$VpsIP`:$VpsPort"
Write-Host "  RemoteRoot: $RemoteRoot"
Write-Host "  Files:      $($requested.Count) explicit path(s)"
Write-Host "  DryRun:     $DryRun"

foreach ($path in $requested) { Write-Host "    $path" }
if ($DryRun) { Warn "Dry run complete; no remote changes made."; exit 0 }
if (-not (Test-Path -LiteralPath $SshKeyPath)) { Die "Workspace SSH key not found: $SshKeyPath" }

$sshOptions = @(
    "-i", $SshKeyPath,
    "-p", [string]$VpsPort,
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "LogLevel=ERROR"
)
$scpOptions = @(
    "-i", $SshKeyPath,
    "-P", [string]$VpsPort,
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "LogLevel=ERROR"
)
$target = "${VpsUser}@${VpsIP}"

Step "Testing the locked VPS connection"
$connection = ssh @sshOptions $target "echo RZWIRE_SSH_OK" 2>&1
if ($LASTEXITCODE -ne 0 -or ($connection -join " ") -notmatch "RZWIRE_SSH_OK") {
    Die "SSH connection failed: $($connection -join ' ')"
}
Ok "SSH access verified"

Step "Verifying the remote project identity"
$identityCommand = "if [ -f '$RemoteRoot/DEPLOYMENT_TARGET.lock' ]; then grep -qx 'project_id=rzwire' '$RemoteRoot/DEPLOYMENT_TARGET.lock' && grep -qx 'vps_ip=$VpsIP' '$RemoteRoot/DEPLOYMENT_TARGET.lock' && echo MATCH || echo MISMATCH; elif [ -d '$RemoteRoot' ] && find '$RemoteRoot' -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null | grep -q .; then echo UNLOCKED_NONEMPTY; else echo EMPTY; fi"
$identity = (ssh @sshOptions $target $identityCommand 2>&1 | Select-Object -Last 1).Trim()
if ($LASTEXITCODE -ne 0) { Die "Could not verify the remote project identity." }
if ($identity -eq "MISMATCH") { Die "Remote lock belongs to a different target." }
if ($identity -eq "UNLOCKED_NONEMPTY") { Die "Remote folder is non-empty but has no RZWire lock." }
if ($identity -eq "EMPTY" -and $requested -notcontains "DEPLOYMENT_TARGET.lock") {
    Die "First deployment must explicitly include DEPLOYMENT_TARGET.lock."
}
Ok "Remote identity is safe ($identity)"

$ordered = @($requested | Sort-Object { if ($_ -eq "DEPLOYMENT_TARGET.lock") { 0 } else { 1 } }, { $_ })
Step "Uploading explicit files"
foreach ($path in $ordered) {
    $localPath = Join-Path $ProjectRoot ($path -replace "/", "\")
    $remotePath = "$RemoteRoot/$path"
    $remoteDirectory = $remotePath -replace "/[^/]+$", ""
    ssh @sshOptions $target "mkdir -p '$remoteDirectory'" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Could not create $remoteDirectory." }
    scp @scpOptions $localPath "${target}:$remotePath" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Upload failed: $path" }
    Ok $path
}

if ($SkipRestart) { Warn "Files uploaded; restart and build skipped."; exit 0 }

$backendChanged = @($requested | Where-Object { $_ -like "backend/*" })
$frontendChanged = @($requested | Where-Object { $_ -like "frontend/*" })
$deployChanged = @($requested | Where-Object { $_ -like "deploy/*" })
$backendService = $lock["backend_service"]
$frontendService = $lock["frontend_service"]

if ($deployChanged -contains "deploy/rzwire-backend.service") {
    Step "Applying the backend service definition"
    ssh @sshOptions $target "install -m 644 '$RemoteRoot/deploy/rzwire-backend.service' /etc/systemd/system/rzwire-backend.service && systemctl daemon-reload" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Backend service installation failed." }
    Ok "Backend service definition applied"
}

if ($deployChanged -contains "deploy/rzwire-nginx.conf") {
    Step "Applying the RZWire web-server configuration"
    ssh @sshOptions $target "install -m 644 '$RemoteRoot/deploy/rzwire-nginx.conf' /etc/nginx/sites-available/rzwire && ln -sfn /etc/nginx/sites-available/rzwire /etc/nginx/sites-enabled/rzwire && rm -f /etc/nginx/sites-enabled/default && nginx -t && systemctl reload nginx" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Web-server configuration failed." }
    Ok "Web-server configuration applied"
}

if ($backendChanged.Count -gt 0) {
    Step "Checking and restarting the backend"
    $backendCommand = "cd '$RemoteRoot' && python3 -m compileall -q backend && chown -R rzwire:rzwire backend && systemctl restart '$backendService' && systemctl is-active '$backendService'"
    $backendResult = ssh @sshOptions $target $backendCommand 2>&1
    Write-Host ($backendResult -join "`n")
    if ($LASTEXITCODE -ne 0 -or $backendResult -notcontains "active") { Die "Backend verification failed." }
    Ok "Backend active"
}

if ($frontendChanged.Count -gt 0) {
    Step "Building and reloading the frontend"
    $frontendCommand = "cd '$RemoteRoot/frontend' && npm ci && npm run build && chown -R rzwire:rzwire '$RemoteRoot/frontend' && nginx -t && systemctl reload '$frontendService' && systemctl is-active '$frontendService'"
    $frontendResult = ssh @sshOptions $target $frontendCommand 2>&1
    Write-Host ($frontendResult -join "`n")
    if ($LASTEXITCODE -ne 0 -or $frontendResult -notcontains "active") { Die "Frontend verification failed." }
    Ok "Frontend active"
}

Step "Final VPS verification"
$verifyCommand = "systemctl is-active '$backendService'; systemctl is-active '$frontendService'; curl -fsS http://127.0.0.1:3001/api/health"
$verification = ssh @sshOptions $target $verifyCommand 2>&1
Write-Host ($verification -join "`n")
if ($LASTEXITCODE -ne 0 -or @($verification | Where-Object { $_ -eq "active" }).Count -lt 2) {
    Die "Final service or health verification failed."
}

Write-Host "`nRZWire deployment complete: http://$VpsIP" -ForegroundColor Green
