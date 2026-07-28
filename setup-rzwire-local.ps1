$ErrorActionPreference = 'Stop'
$Workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw 'Python 3.11 or newer is required.' }

& $Python.Source -m venv (Join-Path $Workspace '.venv')
& (Join-Path $Workspace '.venv\Scripts\python.exe') -m pip install -r (Join-Path $Workspace 'backend\requirements.txt')
Set-Location -LiteralPath (Join-Path $Workspace 'frontend')
npm install
Write-Host 'RZWire is ready. Run .\start-rzwire-local.ps1' -ForegroundColor Green
