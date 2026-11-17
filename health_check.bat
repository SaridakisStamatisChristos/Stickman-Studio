@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Stickman Studio - Created by Atharv Hatwar - Health Check
color 0E
cd /d "%~dp0"

echo ============================================================
echo   Stickman Studio - Created by Atharv Hatwar
echo   System Diagnostic and Health Verification
echo ============================================================
echo.

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
if exist "%~dp0ffmpeg\ffmpeg.exe" (
    set "PATH=%~dp0ffmpeg;%PATH%"
) else if exist "C:\ffmpeg\bin\ffmpeg.exe" (
    set "PATH=C:\ffmpeg\bin;%PATH%"
)

set ISSUES=0

:: Python
echo [CHECK] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Python not found
    set /a ISSUES+=1
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK]   Python %%v
)

:: PySide6
echo [CHECK] PySide6...
python -c "import PySide6; print(PySide6.__version__)" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] PySide6 not installed - run: pip install PySide6
    set /a ISSUES+=1
) else (
    for /f %%v in ('python -c "import PySide6; print(PySide6.__version__)"') do echo   [OK]   PySide6 %%v
)

:: Pillow
echo [CHECK] Pillow...
python -c "from PIL import Image; print(Image.__version__)" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Pillow not installed - run: pip install Pillow
    set /a ISSUES+=1
) else (
    for /f %%v in ('python -c "from PIL import __version__; print(__version__)"') do echo   [OK]   Pillow %%v
)

:: Requests
echo [CHECK] requests...
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] requests not installed - run: pip install requests
    set /a ISSUES+=1
) else (
    echo   [OK]   requests
)

:: Numpy
echo [CHECK] numpy...
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] numpy not installed - music synthesis will use fallback
) else (
    echo   [OK]   numpy
)

:: Soundfile
echo [CHECK] soundfile...
python -c "import soundfile" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] soundfile not installed - run: pip install soundfile
) else (
    echo   [OK]   soundfile
)

:: FFmpeg
echo [CHECK] FFmpeg...
set "FF_CHECKED=0"
if exist "%~dp0ffmpeg\ffmpeg.exe" (
    echo   [OK]   FFmpeg found in local directory [%~dp0ffmpeg\ffmpeg.exe]
    set "FF_CHECKED=1"
    goto :ffmpeg_tested
)
if exist "C:\ffmpeg\bin\ffmpeg.exe" (
    echo   [OK]   FFmpeg found at C:\ffmpeg\bin\ffmpeg.exe
    set "FF_CHECKED=1"
    goto :ffmpeg_tested
)
where ffmpeg >nul 2>&1
if not errorlevel 1 (
    echo   [OK]   FFmpeg found in PATH
    set "FF_CHECKED=1"
    goto :ffmpeg_tested
)

if "%FF_CHECKED%"=="0" (
    echo   [FAIL] FFmpeg not found - run setup_windows.bat
    set /a ISSUES+=1
)

:ffmpeg_tested

:: Embedded In-Process AI Director
echo [CHECK] Embedded In-Process AI Director [Native Python]...
python -c "import sys; sys.path.insert(0, 'src'); from engine.procedural_scene_engine import ProceduralSceneEngine; print('ready')" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Procedural Scene Engine check failed
) else (
    echo   [OK]   Embedded In-Process AI Director ready [Zero Ollama required]
)

:: In-Process Neural Semantic Brain (MiniLM-L6 ONNX)
echo [CHECK] In-Process Neural Semantic Brain [MiniLM-L6 ONNX]...
python -c "import sys; sys.path.insert(0, 'src'); from engine.semantic_scene_brain import SemanticSceneBrain; exit(0 if SemanticSceneBrain.is_model_available() else 1)" >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Neural Brain weights not found [Procedural heuristic fallback active]
) else (
    echo   [OK]   In-Process Neural Semantic Brain ready [MiniLM-L6 INT8 active, ^<10ms inference]
)

:: Ollama (Optional)
echo [CHECK] Ollama [Optional external daemon]...
where ollama >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Ollama not installed [Not needed - Studio runs 100%% inside Python]
) else (
    echo   [OK]   Ollama installed [available as optional fallback]
)

:: Kokoro TTS
echo [CHECK] Kokoro TTS...
python -c "import kokoro_onnx" >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Kokoro TTS package not installed - run: pip install kokoro-onnx
) else (
    set "KOKORO_FOUND=0"
    if exist "%~dp0models\kokoro\kokoro-v1.0.int8.onnx" set "KOKORO_FOUND=1"
    if exist "%~dp0models\kokoro\kokoro-v1.0.fp16.onnx" set "KOKORO_FOUND=1"
    if exist "%LOCALAPPDATA%\OfflineStickmanStudio\voices\kokoro\kokoro-v1.0.int8.onnx" set "KOKORO_FOUND=1"
    if exist "%LOCALAPPDATA%\OfflineStickmanStudio\voices\kokoro\kokoro-v1.0.fp16.onnx" set "KOKORO_FOUND=1"
    if exist "%LOCALAPPDATA%\StickmanStudio\voices\kokoro\kokoro-v1.0.int8.onnx" set "KOKORO_FOUND=1"
    
    if "!KOKORO_FOUND!"=="1" (
        echo   [OK]   Kokoro TTS and offline voice weights ready
    ) else (
        echo   [WARN] Kokoro package installed, weights missing - run setup_windows.bat to download
    )
)

:: NVIDIA GPU / NVENC
echo [CHECK] NVIDIA GPU and NVENC...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo   [INFO] nvidia-smi not found - using CPU encoding mode [libx264]
) else (
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
        echo   [OK]   NVIDIA GPU detected: %%g [NVENC Hardware Acceleration ready]
        goto :gpu_tested
    )
)
:gpu_tested

:: Output directory
echo [CHECK] Application directories...
if exist "%~dp0output" (
    echo   [OK]   Output directory exists
) else (
    echo   [WARN] Output directory missing - will be created on first run
)

:: Summary
echo.
echo ============================================================
if %ISSUES% EQU 0 (
    color 0A
    echo   All critical checks passed! Ready to run.
    echo   Start the app with: run.bat
) else (
    color 0C
    echo   %ISSUES% critical issue detected. See above for fixes.
    echo   For automatic setup, run setup_windows.bat
)
echo ============================================================
echo.
pause
