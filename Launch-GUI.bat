@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_gui.py
) else (
  echo No .venv found. Run once:  pwsh -ExecutionPolicy Bypass -File setup_venv.ps1
  python run_gui.py
)
if errorlevel 1 pause
