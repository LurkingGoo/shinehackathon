@echo off
rem ============================================================
rem  Morning Triage — one-click local run (Windows)
rem  Double-click this file. It starts:
rem    * scoring service (FastAPI)  -> http://localhost:8000
rem    * triage dashboard (Next.js) -> http://localhost:3000
rem  Each runs in its own window; close the windows to stop.
rem  Requires: Python 3.11+ and Node 18+ on PATH.
rem ============================================================
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.11+ from python.org
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found on PATH. Install Node.js 18+ from nodejs.org
    pause
    exit /b 1
)

echo Starting scoring service on http://localhost:8000 ...
start "triage-scoring-service" cmd /k "cd /d "%~dp0scoring-service" && python -m pip install -q -r requirements.txt && python -m uvicorn app.main:app --port 8000"

echo Starting dashboard on http://localhost:3000 ...
start "triage-dashboard" cmd /k "cd /d "%~dp0triage-dashboard" && (if not exist node_modules npm install) && npm run dev"

echo.
echo   ----------------------------------------------
echo    dashboard    -^>  http://localhost:3000
echo    judge brief  -^>  http://localhost:3000/judge-brief.html
echo    slides (pdf) -^>  http://localhost:3000/slides.pdf
echo    service API  -^>  http://localhost:8000
echo   ----------------------------------------------
echo   Opening the dashboard in your browser shortly...
timeout /t 12 /nobreak >nul
start "" http://localhost:3000
exit /b 0
