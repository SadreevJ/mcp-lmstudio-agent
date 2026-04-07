@echo off
setlocal
cd /d "%~dp0.."
python "%~dp0run_cli.py" status %*
