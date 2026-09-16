@echo off
echo.
echo  NetManager — Starting Up
echo  ========================
echo.

set BACKEND=%~dp0backend

if not exist "%BACKEND%\venv" (
    echo Creating Python virtualenv...
    python -m venv "%BACKEND%\venv"
)

call "%BACKEND%\venv\Scripts\activate.bat"

echo Installing dependencies...
pip install -q -r "%BACKEND%\requirements.txt"

echo.
echo Starting FastAPI server at http://localhost:8000
echo Press Ctrl+C to stop.
echo.

cd /d "%BACKEND%"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
