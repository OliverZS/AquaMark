@echo off
rem =====================================================================
rem  AquaMark for Windows - launcher
rem  ASCII-only on purpose: Chinese text inside .bat would depend on the
rem  system codepage. See README.md for the Chinese manual.
rem
rem  Starts a loopback server (http://127.0.0.1:<port>/AquaMark.html) and
rem  opens Edge/Chrome in app-window mode. A loopback origin counts as a
rem  secure context, so Ctrl+S really writes back into your .md file.
rem  The server stops itself when the page closes.
rem =====================================================================
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
if errorlevel 1 (
  echo.
  echo [AquaMark] Failed to start. See README.md (Troubleshooting).
  echo [AquaMark] If Edge reports the address cannot be found, run
  echo [AquaMark] Start-AquaMark-NoServer.bat instead.
  pause
)
