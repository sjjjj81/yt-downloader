@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   YouTube Downloader - Setup
echo ==========================================
echo.

REM Resolve the project directory (where this script lives)
set "PROJECT_DIR=%~dp0"
REM Remove trailing backslash
set "PROJECT_DIR=%PROJECT_DIR:\=/%"
cd /d "%PROJECT_DIR%"

REM ---- 1. Check Python 3.11+ -------------------------------------------
echo [1/5] Checking Python version...

REM Try python first, then python3
python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python is not found in PATH.
        echo.
        echo Please install Python 3.11 or later from the official site:
        echo   https://www.python.org/downloads/
        echo.
        echo During installation, check the box "Add Python to PATH".
        echo.
        pause
        exit /b 1
    ) else (
        set "PYTHON_CMD=python3"
    )
) else (
    set "PYTHON_CMD=python"
)

for /f "tokens=1,2 delims=." %%a in ('%PYTHON_CMD% --version 2^>^&1') do (
    set "PYTHON_VERSION=%%a"
    set "PYTHON_MINOR=%%b"
)
REM Strip non-numeric chars
for /f "tokens=1 delims=0123456789." %%a in ("%PYTHON_VERSION%") do set "PYTHON_VERSION=%PYTHON_VERSION:%%a=%"
for /f "tokens=1 delims=0123456789." %%a in ("%PYTHON_MINOR%") do set "PYTHON_MINOR=%PYTHON_MINOR:%%a=%"

set /a PY_MAJOR=%PYTHON_VERSION%
set /a PY_MINOR=%PYTHON_MINOR%

if %PY_MAJOR% lss 3 (
    echo ERROR: Python %PYTHON_VERSION%.%PYTHON_MINOR% is too old.
    echo This project requires Python 3.11 or later.
    echo.
    echo Download the latest version from:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 11 (
    echo ERROR: Python %PYTHON_VERSION%.%PYTHON_MINOR% is too old.
    echo This project requires Python 3.11 or later.
    echo.
    echo Download the latest version from:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo   %PYTHON_CMD% %PYTHON_VERSION%.%PYTHON_MINOR% detected.
echo.

REM ---- 2. Create virtual environment ------------------------------------
echo [2/5] Setting up virtual environment...
if not exist ".venv" (
    echo   Creating .venv...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        echo.
        echo Please ensure Python is installed correctly and try again.
        echo.
        pause
        exit /b 1
    )
) else (
    echo   .venv already exists.
)
echo.

REM ---- 3. Install dependencies -----------------------------------------
echo [3/5] Installing dependencies...
"%PROJECT_DIR%.venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%PROJECT_DIR%.venv\Scripts\pip.exe" install -r "%PROJECT_DIR%requirements.txt"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    echo.
    echo Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo   Dependencies installed successfully.
echo.

REM ---- 4. Verify Python environment ------------------------------------
echo [4/5] Verifying Python environment...
"%PROJECT_DIR%.venv\Scripts\python.exe" -c "import flask, yt_dlp; print('   Flask', flask.__version__); print('   yt-dlp', yt_dlp.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python environment verification failed.
    echo.
    echo The virtual environment may be corrupted. Try deleting .venv and running setup.bat again.
    echo.
    pause
    exit /b 1
)
echo   Environment verified successfully.
echo.

REM ---- 5. Check FFmpeg --------------------------------------------------
echo [5/5] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1-3" %%a in ('ffmpeg -version 2^>nul ^| findstr /i "ffmpeg"') do (
        echo   FFmpeg found: %%a %%b %%c
        goto :ffmpeg_done
    )
)
:ffmpeg_done
if %errorlevel% neq 0 (
    echo WARNING: FFmpeg not found in PATH.
    echo.
    echo FFmpeg is required for video/audio post-processing (merging, format conversion).
    echo Without it, direct video downloads will still work, but:
    echo   - Audio extraction will fail (cannot convert to mp3/m4a)
    echo   - Multiple video streams cannot be merged into one file
    echo.
    echo Install it from one of these sources:
    echo   - Official site: https://ffmpeg.org/download.html
    echo   - Chocolatey: choco install ffmpeg
    echo   - winget: winget install FFmpeg
    echo.
    echo After installing, restart this script or add FFmpeg to your PATH.
    echo.
) else (
    echo   FFmpeg is available.
)
echo.

REM ---- 6. Check JavaScript runtime (Node.js) ---------------------------
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo NOTE: Node.js not found in PATH.
    echo.
    echo Node.js is not strictly required for the core downloader, but some
    echo yt-dlp extractor integrations benefit from it.
    echo.
    echo Install from: https://nodejs.org/
    echo.
) else (
    for /f "tokens=1" %%a in ('node --version 2^>nul') do (
        echo   Node.js found: %%a
        goto :node_done
    )
)
:node_done
echo.

echo ==========================================
echo   Setup complete!
echo ==========================================
echo.
echo To start the application, run:
echo   start.bat
echo.
echo Open http://127.0.0.1:5000 in your browser after startup.
echo.
pause
exit /b 0