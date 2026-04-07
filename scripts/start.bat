@echo off
setlocal
cd /d "%~dp0.."
call "%~dp0bootstrap.bat"
python "%~dp0run_cli.py" status
