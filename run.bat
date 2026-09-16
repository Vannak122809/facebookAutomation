@echo off
cd /d "%~dp0"
call venv_new\Scripts\activate.bat
python main.py
pause
