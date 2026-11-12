@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo   YouTube Downloader - Starting
echo ==========================================
echo.

REM Resolve the project directory (where this script lives)
set "PROJECT_DIR=%~dp0"
REM Remove trailing backslash
set "PROJECT_DIR=%PROJECT_DIR:\=/%"
cd /d "%PROJECT_DIR%"

REM ---- 1. Check .venv exists -------------------------------------------
if not exist ".venv" (
    echo ERROR: Virtual environment not found.
    echo.
    echo Please run setup.bat first to create the environment and install dependencies.
    echo.
    pause
    exit /b 1
)

REM ---- 2. Check required packages --------------------------------------
"%PROJECT_DIR%.venv\Scripts\python.exe" -c "import flask, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Required packages are missing.
    echo.
    echo Please run setup.bat to install dependencies.
    echo.
    pause
    exit /b 1
)

REM ---- 3. Check port 5000 is available --------------------------------
set "PORT=5000"
netstat -an | findstr "LISTENING" | findstr ":%PORT%" >nul 2>&1
if %errorlevel% equ 0 (
    echo ERROR: Port %PORT% is already in use.
    echo.
    echo Another instance of this application may already be running.
    echo.
    echo To fix this:
    echo   - Close any existing YouTube Downloader windows
    echo   - Or stop the service occupying port %PORT%
    echo.
    echo You can check what is using the port with:
    echo   netstat -ano ^| findstr ":%PORT%"
    echo.
    pause
    exit /b 1
)

REM ---- 4. Start Flask bound to 127.0.0.1 ------------------------------
echo Starting Flask server on http://127.0.0.1:%PORT% ...
echo.

REM Set host explicitly to prevent binding to 0.0.0.0
set "FLASK_HOST=127.0.0.1"
set "FLASK_PORT=%PORT%"

"%PROJECT_DIR%.venv\Scripts\python.exe" "%PROJECT_DIR%run.py"

REM If we get here, the server exited (likely via Ctrl+C or crash)
if %errorlevel% neq 0 (
    echo.
    echo ERROR: The server exited with an error.
    echo.
    echo Check the error message above for details.
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo Server stopped.
pause
exit /b 0