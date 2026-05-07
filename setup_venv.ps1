# Create a dedicated .venv in this repo and install requirements.txt
# Usage (from repo root):  pwsh -ExecutionPolicy Bypass -File .\setup_venv.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$venv = Join-Path $PSScriptRoot '.venv'
$venvPy = Join-Path $venv 'Scripts\python.exe'
$req = Join-Path $PSScriptRoot 'requirements.txt'

if (-not (Test-Path $req)) {
    Write-Error "requirements.txt not found at $req"
    exit 1
}

Write-Host 'Creating venv (.venv)...'
if (-not (Test-Path $venvPy)) {
    & python -m venv .venv
}
if (-not (Test-Path $venvPy)) {
    Write-Error "Failed to create venv at $venv"
    exit 1
}

Write-Host 'Installing dependencies (requirements.txt)...'
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt

Write-Host 'Done.'
Write-Host '  Double-click Launch-GUI.bat  — or —  cd here and run: .\.venv\Scripts\python.exe run_gui.py'
