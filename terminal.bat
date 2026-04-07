@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python "%~dp0scripts\terminal_menu.py"
exit /b %errorlevel%
