$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
$python = Join-Path $root ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r backend\requirements.txt

if (-not (Test-Path ".env")) {
    $secret = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
    $envText = Get-Content ".env.example" -Raw
    $envText = $envText.Replace("REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS", $secret.Trim())
    Set-Content -Path ".env" -Value $envText -Encoding utf8
    Write-Host "Created .env with a unique local SECRET_KEY." -ForegroundColor Green
}

Push-Location frontend
try {
    npm ci
} finally {
    Pop-Location
}
Write-Host "Setup complete. Start the backend and frontend using the commands in README.md." -ForegroundColor Green
