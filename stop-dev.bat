@echo off
setlocal

set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\stop-dev.ps1"
set "STOP_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%STOP_EXIT_CODE%"=="0" (
  echo Shutdown did not complete. Review the output above.
)
echo Press any key to close this window.
pause >nul

endlocal & exit /b %STOP_EXIT_CODE%
