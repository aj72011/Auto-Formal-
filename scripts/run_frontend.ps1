Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "$PSScriptRoot\..\frontend"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm is required but was not found on PATH. Install Node.js 18+."
}

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
}

npm install
npm run dev -- --host 0.0.0.0 --port 5174
