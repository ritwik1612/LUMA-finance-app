$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv .venv
    & $pythonPath -m pip install -r requirements.txt
}
Write-Host 'Luma Finance is starting at http://127.0.0.1:8000/dashboard'
& $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000
