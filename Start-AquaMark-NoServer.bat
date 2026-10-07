@echo off
rem =====================================================================
rem  AquaMark for Windows - minimal launcher (no local server)
rem  Use this one if corporate policy / antivirus blocks the loopback
rem  server started by Start-AquaMark.bat.
rem  Everything works; Ctrl+S saves a copy into the Downloads folder
rem  instead of overwriting the original file.
rem =====================================================================
cd /d "%~dp0"

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" -NoServer
if errorlevel 1 (
  echo.
  echo [AquaMark] Failed to start. See README.md (Troubleshooting).
  pause
)
