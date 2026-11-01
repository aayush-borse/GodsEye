@echo off
setlocal
cd /d "%~dp0"
if not exist "frontend\dist\index.html" (
  echo [GOD'S EYE] Building React frontend...
  cd frontend
  call npm install
  if errorlevel 1 exit /b 1
  call npm run build
  if errorlevel 1 exit /b 1
  cd ..
)
echo [GOD'S EYE] Starting FastAPI...
uv run python run.py
pause
