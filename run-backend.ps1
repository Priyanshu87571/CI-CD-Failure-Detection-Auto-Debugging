$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path ".env")) { throw "Missing .env. Run .\setup.ps1 first." }
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
