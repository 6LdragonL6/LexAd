@echo off
setlocal

set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\start-dev.ps1"

if errorlevel 1 (
  echo.
  echo Startup failed. Press any key to close this window.
  pause >nul
)

endlocal
