@echo off
setlocal EnableDelayedExpansion
title Stickman Studio • Created by Atharv Hatwar - Setup
color 0A

echo ============================================================
echo   Stickman Studio - Created by Atharv Hatwar
echo   Windows One-Click Environment Setup
echo ============================================================
echo.
echo This script will install all required components:
echo   1. Python dependencies (PySide6, Pillow, numpy, requests, etc.)
echo   2. Kokoro TTS offline neural voice models
echo   3. FFmpeg for hardware/CPU video encoding
echo   4. Application directory structure
echo.
echo AI Architecture:
echo   Stickman Studio includes an Embedded In-Process AI Director
echo   that runs 100%% inside Python. Zero external servers required!
echo.
echo INTERNET CONNECTION REQUIRED for this initial setup only.
echo After setup, the application runs fully OFFLINE.
echo.
echo ============================================================

:: Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+ from python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo     Found Python %PYVER%

:: Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found. Run: python -m ensurepip
    pause
    exit /b 1
)

:: Install Python dependencies
echo.
echo [2/5] Installing Python dependencies...
pip install PySide6 Pillow requests numpy tqdm soundfile --quiet
if errorlevel 1 (
    echo WARNING: Some packages may have failed. Trying individual installs...
    pip install PySide6 --quiet
    pip install Pillow --quiet
    pip install requests --quiet
    pip install numpy --quiet
    pip install tqdm --quiet
    pip install soundfile --quiet
)
echo     Python packages installed.

:: Install Kokoro TTS + Offline Voice Model (~115 MB)
echo.
echo [3/5] Installing Kokoro-82M TTS (natural offline voices)...
pip install kokoro-onnx piper-tts --quiet 2>nul
if errorlevel 1 (
    echo     Kokoro install failed - will use Windows SAPI as fallback
) else (
    echo     Kokoro TTS package installed. Checking offline voice model files (~115 MB)...
    set "KOKORO_DIR=%LOCALAPPDATA%\StickmanStudio\voices\kokoro"
    if not exist "%KOKORO_DIR%" mkdir "%KOKORO_DIR%"
    if not exist "%KOKORO_DIR%\kokoro-v1.0.int8.onnx" (
        echo     Downloading kokoro-v1.0.int8.onnx (88 MB)...
        powershell -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx' -OutFile '%KOKORO_DIR%\kokoro-v1.0.int8.onnx' -UseBasicParsing }"
    )
    if not exist "%KOKORO_DIR%\voices-v1.0.bin" (
        echo     Downloading voices-v1.0.bin (27 MB, 54 voices)...
        powershell -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin' -OutFile '%KOKORO_DIR%\voices-v1.0.bin' -UseBasicParsing }"
    )
    if exist "%KOKORO_DIR%\kokoro-v1.0.int8.onnx" (
        echo     Kokoro-82M offline voice models ready (54 voices across 8 languages).
    )
)

:: Check/Download FFmpeg
echo.
echo [4/5] Setting up FFmpeg...
if exist "ffmpeg\ffmpeg.exe" (
    echo     FFmpeg already installed in local directory.
) else if exist "C:\ffmpeg\bin\ffmpeg.exe" (
    echo     FFmpeg found at C:\ffmpeg\bin\ffmpeg.exe
) else (
    where ffmpeg >nul 2>&1
    if not errorlevel 1 (
        echo     FFmpeg found in system PATH.
    ) else (
        echo     Downloading FFmpeg (essential for video encoding)...
        echo     Downloading from GitHub releases - approx 70MB...
        
        powershell -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg_temp.zip' -UseBasicParsing }"
        
        if exist "ffmpeg_temp.zip" (
            echo     Extracting FFmpeg...
            powershell -Command "Expand-Archive -Path ffmpeg_temp.zip -DestinationPath ffmpeg_extract -Force"
            
            for /r ffmpeg_extract %%f in (ffmpeg.exe) do (
                if not exist "ffmpeg" mkdir ffmpeg
                copy "%%f" "ffmpeg\ffmpeg.exe" >nul
            )
            for /r ffmpeg_extract %%f in (ffprobe.exe) do (
                copy "%%f" "ffmpeg\ffprobe.exe" >nul
            )
            
            del ffmpeg_temp.zip
            rmdir /s /q ffmpeg_extract
            
            if exist "ffmpeg\ffmpeg.exe" (
                echo     FFmpeg installed to .\ffmpeg\ffmpeg.exe
            ) else (
                echo WARNING: FFmpeg extraction failed. Please install FFmpeg manually.
                echo     Download from: https://www.gyan.dev/ffmpeg/builds/
                echo     Extract and add to PATH, or place ffmpeg.exe in .\ffmpeg\
            )
        ) else (
            echo WARNING: FFmpeg download failed. 
            echo     Please download manually from: https://www.gyan.dev/ffmpeg/builds/
            echo     Extract ffmpeg.exe to the 'ffmpeg' folder in this directory.
        )
    )
)

:: Create required directories
echo.
echo [5/5] Creating application directories...
if not exist "output" mkdir output
if not exist "projects" mkdir projects
if not exist "temp" mkdir temp
if not exist "assets\music" mkdir assets\music
if not exist "assets\sfx" mkdir assets\sfx
if not exist "assets\voices" mkdir assets\voices

echo     Directories created.

:: Done
echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo To run the application:
echo   Double-click run.bat
echo   OR run: python main.py
echo.
echo Everything is configured to run 100%% OFFLINE.
echo ============================================================
echo.
pause
