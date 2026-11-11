@echo off
title Stickman Studio • Created by Atharv Hatwar
color 0A
cd /d "%~dp0"

echo ========================================================
echo         Stickman Studio - Created by Atharv Hatwar
echo ========================================================

:: Add local ffmpeg or C:\ffmpeg\bin to PATH if present
if exist "%~dp0ffmpeg\ffmpeg.exe" (
    set "PATH=%~dp0ffmpeg;%PATH%"
) else if exist "C:\ffmpeg\bin\ffmpeg.exe" (
    set "PATH=C:\ffmpeg\bin;%PATH%"
)

:: Locate Python interpreter
set "PY_CMD="
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)
if not defined PY_CMD (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)
if not defined PY_CMD if exist "C:\Python314\python.exe" (
    set "PY_CMD=C:\Python314\python.exe"
)

if not defined PY_CMD (
    echo ERROR: Python 3.11+ was not found on PATH.
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo Launching Stickman Studio...
%PY_CMD% main.py %*
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Application exited with error code %EXIT_CODE%.
    echo Check the log file at: %LOCALAPPDATA%\OfflineStickmanStudio\logs\stickman_studio.log
    pause
)
exit /b %EXIT_CODE%
