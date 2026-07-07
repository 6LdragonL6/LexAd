@echo off
setlocal

set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\stop-dev.ps1"

echo.
echo Press any key to close this window.
pause >nul

endlocal
