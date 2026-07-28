param(
  [Parameter(Mandatory = $true)]
  [string]$Message,
  [Parameter(Mandatory = $true)]
  [string]$Files,
  [switch]$SkipVps
)

$ErrorActionPreference = 'Stop'
$Workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Workspace '.venv\Scripts\python.exe'
$FileList = @($Files -split ',' | ForEach-Object { ($_.Trim() -replace '\\', '/') } | Where-Object { $_ } | Sort-Object -Unique)

if ($FileList.Count -eq 0) {
  throw 'Provide an explicit comma-separated -Files list.'
}

foreach ($File in $FileList) {
  if ($File.StartsWith('/') -or $File -match '(^|/)\.\.(/|$)') {
    throw "Unsafe project path: $File"
  }
}

if (-not (Test-Path -LiteralPath $Python)) {
  throw 'Local Python environment is missing. Run .\setup-rzwire-local.ps1 first.'
}

Push-Location (Join-Path $Workspace 'backend')
try {
  & $Python -m unittest discover -s . -p 'test_*.py'
  if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed. Nothing was pushed.' }
} finally {
  Pop-Location
}

Push-Location (Join-Path $Workspace 'frontend')
try {
  & npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed. Nothing was pushed.' }
} finally {
  Pop-Location
}

Push-Location $Workspace
try {
  git add -- $FileList
  if ($LASTEXITCODE -ne 0) { throw 'Git could not stage the explicit file list.' }
  git diff --cached --quiet
  if ($LASTEXITCODE -eq 0) {
    Write-Host 'No project changes to publish.' -ForegroundColor Yellow
    exit 0
  }

  git commit -m $Message
  if ($LASTEXITCODE -ne 0) { throw 'Git commit failed. Nothing was pushed.' }
  git push origin main
  if ($LASTEXITCODE -ne 0) { throw 'GitLab push failed. The VPS deployment was not triggered.' }

  Write-Host 'RZWire was pushed to GitLab.' -ForegroundColor Green

  if (-not $SkipVps) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Workspace 'deploy-to-vps.ps1') -Files ($FileList -join ',')
    if ($LASTEXITCODE -ne 0) { throw 'GitLab was updated, but the VPS deployment failed.' }
    Write-Host 'The same explicit files were deployed to the locked RZWire VPS.' -ForegroundColor Green
  }
} finally {
  Pop-Location
}
