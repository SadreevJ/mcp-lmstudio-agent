@echo off
cd /d "%~dp0"
python "%~dp0scripts\gui_launcher.py"
if errorlevel 1 pause
