@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  python "%~dp0run_cli.py" rebuild-context
) else (
  python "%~dp0run_cli.py" rebuild-context --project "%~1"
)
