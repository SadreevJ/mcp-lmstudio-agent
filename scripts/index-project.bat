@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  python "%~dp0run_cli.py" index-project
) else (
  python "%~dp0run_cli.py" index-project --project "%~1"
)
