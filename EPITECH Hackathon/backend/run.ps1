$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $python) {
  & $python -m uvicorn main:app --port 8001
} else {
  python -m uvicorn main:app --port 8001
}
