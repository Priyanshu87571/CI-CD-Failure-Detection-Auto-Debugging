$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) { throw "Missing frontend dependencies. Run .\setup.ps1 from the project root first." }
npm run dev
