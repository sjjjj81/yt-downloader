@echo off
python --version
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    pip install -q -r requirements.txt
)
if exist "run.py" (
    python run.py
)
echo Server stopped.
pause