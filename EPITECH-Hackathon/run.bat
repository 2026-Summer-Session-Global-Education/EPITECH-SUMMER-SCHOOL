@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Starting Relationship Extraction Tool...

for %%I in ("%~dp0.") do set "PROJECT_ROOT=%%~fI"
set "VENV_DIR=%PROJECT_ROOT%\backend\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "REQUIREMENTS_FILE=%BACKEND_DIR%\requirements.txt"
set "OLLAMA_TIMEOUT_SECONDS=600"
set "OLLAMA_VULKAN=1"
set "OLLAMA_IGPU_ENABLE=1"
set "GGML_VK_VISIBLE_DEVICES=0"
set "OLLAMA_NUM_GPU_LAYERS=16"

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=python"
  ) else (
    echo Python 3 was not found. Please install Python 3 and rerun this script.
    pause
    exit /b 1
  )
)

where ollama >nul 2>nul
if not errorlevel 1 (
  start "Ollama" /min cmd /c "ollama serve"
) else (
  echo Ollama was not found. The app will still run with fallback extraction.
)

if not exist "%VENV_PY%" (
  echo Creating Python virtual environment...
  %PYTHON_CMD% -m venv "%VENV_DIR%"
)

if not exist "%VENV_PY%" (
  echo Failed to create Python virtual environment.
  pause
  exit /b 1
)

echo Installing backend dependencies...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
"%VENV_PY%" -m pip install -r "%REQUIREMENTS_FILE%"

if errorlevel 1 (
  echo Dependency installation failed. Please check your network connection and Python setup.
  pause
  exit /b 1
)

start "Backend API" /D "%BACKEND_DIR%" cmd /k ""%VENV_PY%" -m uvicorn main:app --host 0.0.0.0 --port 8001"
timeout /t 2 >nul
start "Frontend" /min /D "%PROJECT_ROOT%" cmd /c ""%VENV_PY%" -m http.server 8000 --bind 0.0.0.0"
timeout /t 1 >nul
start "" "http://127.0.0.1:8000/frontend/index.html"

echo.
echo Frontend opened: http://127.0.0.1:8000/frontend/index.html
echo From another PC on the same network, open: http://THIS_PC_IP:8000/frontend/index.html
echo Backend API: http://THIS_PC_IP:8001
echo.
pause
