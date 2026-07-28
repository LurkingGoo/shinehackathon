@echo off
rem ============================================================
rem  Morning Triage - stop local dev servers (Windows)
rem  Kills the two windows started by start.bat:
rem    * triage-scoring-service (uvicorn :8000)
rem    * triage-dashboard       (next dev :3000)
rem  Then sweeps anything still listening on :8000 / :3000
rem  (covers servers started by hand, without start.bat titles).
rem ============================================================
setlocal
echo Stopping triage dev servers...

taskkill /fi "WINDOWTITLE eq triage-scoring-service*" /t /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq triage-dashboard*" /t /f >nul 2>nul

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":8000 " ^| findstr "LISTENING"') do taskkill /pid %%P /t /f >nul 2>nul
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":3000 " ^| findstr "LISTENING"') do taskkill /pid %%P /t /f >nul 2>nul

set "LEFT="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":8000 " ^| findstr "LISTENING"') do set "LEFT=1"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":3000 " ^| findstr "LISTENING"') do set "LEFT=1"
if defined LEFT (
    echo [WARN] Something is still listening on :8000 or :3000 - check Task Manager.
) else (
    echo Done. Ports 8000 and 3000 are free.
)
timeout /t 3 >nul
exit /b 0
