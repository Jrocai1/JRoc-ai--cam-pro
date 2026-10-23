@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.12 or newer from python.org.
  pause
  exit /b 1
)
echo Starting J-ROC AI CAM Repair Pro in mock mode.
echo Open http://127.0.0.1:8787 in your browser.
echo Press Ctrl+C in this window to stop the service.
py -3.12 dashboard_server.py --mock
if errorlevel 1 (
  echo.
  echo The dashboard stopped with an error. Check the message above.
  pause
)
endlocal
