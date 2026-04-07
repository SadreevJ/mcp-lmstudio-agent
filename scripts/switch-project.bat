@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

if not "%~1"=="" (
  python "%~dp0run_cli.py" switch-project "%~1"
  exit /b %errorlevel%
)

set "WS=workspace"
if not exist "%WS%\" (
  echo Папка %WS% не найдена.
  exit /b 1
)

set count=0
for /f "delims=" %%D in ('dir /b /ad "%WS%" 2^>nul') do (
  set /a count+=1
  set "proj!count!=%%D"
  echo !count!. %%D
)

if !count! equ 0 (
  echo В workspace нет подпапок. Создайте папку проекта в %WS%\.
  exit /b 1
)

set /p choice=Номер проекта: 
if "!choice!"=="" exit /b 1

set "selected="
for /l %%i in (1,1,!count!) do (
  if "!choice!"=="%%i" set "selected=!proj%%i!"
)

if not defined selected (
  echo Неверный номер.
  exit /b 1
)

python "%~dp0run_cli.py" switch-project "!selected!"
