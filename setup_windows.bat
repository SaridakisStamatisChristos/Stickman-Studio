@echo off
title Stickman Studio - Windows Setup - Created by Atharv Hatwar
color 0A
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %*
if errorlevel 1 goto :setup_failed
goto :setup_success

:setup_failed
echo.
echo [ERROR] Setup encountered an issue.
echo Please review the diagnostic messages above.
pause
exit /b 1

:setup_success
pause
exit /b 0
