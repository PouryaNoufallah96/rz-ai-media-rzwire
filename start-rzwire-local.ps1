$ErrorActionPreference = 'Stop'
$Workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Workspace 'backend'
$Frontend = Join-Path $Workspace 'frontend'
$Python = Join-Path $Workspace '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python)) {
  Write-Host 'RZWire local environment is missing. Run: .\setup-rzwire-local.ps1' -ForegroundColor Yellow
  exit 1
}

Write-Host 'Starting RZWire backend at http://localhost:3001' -ForegroundColor Cyan
Start-Process -FilePath $Python -ArgumentList 'server.py' -WorkingDirectory $Backend -WindowStyle Hidden
Write-Host 'Starting RZWire frontend...' -ForegroundColor Cyan
Set-Location -LiteralPath $Frontend
npm.cmd run dev
