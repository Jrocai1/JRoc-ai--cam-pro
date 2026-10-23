@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title J-ROC AI CAM PRO - Plug and Play Setup
echo.
echo  J-ROC AI CAM PRO
echo  Windows 11 x64 - Local Repair Bench
echo  ------------------------------------
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher not found.
  echo Install Python 3.12 x64 and enable "Add Python to PATH".
  start "" "https://www.python.org/downloads/windows/"
  pause
  exit /b 1
)

py -3.12 --version
if errorlevel 1 (
  echo ERROR: Python 3.12 is not installed.
  echo Install Python 3.12 x64, then run this launcher again.
  start "" "https://www.python.org/downloads/windows/"
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating isolated Python environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto :failed
)

echo [2/4] Updating pip in the isolated environment...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [3/4] Installing CAM PRO development/runtime requirements...
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto :failed

echo [4/4] Starting local-only dashboard with read-only device discovery...
echo.
echo Browser address: http://127.0.0.1:8787
echo This window must stay open while you use the dashboard.
echo Press Ctrl+C here to stop the service.
echo.
start "" "http://127.0.0.1:8787"
".venv\Scripts\python.exe" dashboard_server.py --port 8787
if errorlevel 1 goto :failed
goto :done

:failed
echo.
echo SETUP OR STARTUP FAILED.
echo Review the error above. No device-changing operation was run.
pause
exit /b 1

:done
endlocal
