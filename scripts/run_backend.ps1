Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating backend virtual environment..."
    python -m venv .venv
}

Write-Host "Installing backend dependencies..."
.\.venv\Scripts\python -m pip install -r requirements.txt

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Created backend/.env from template. Add HF_API_KEY before formalize calls."
}

Write-Host "Starting backend on http://localhost:8001"
.\.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
