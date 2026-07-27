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
rem npm install runs unconditionally: a pull can add deps to package.json while
rem node_modules already exists (bit us 2026-07-27 — /watch 500 on the demo laptop).
start "triage-dashboard" cmd /k "cd /d "%~dp0triage-dashboard" && npm install && (npm run fetch-pose-assets || echo pose assets skipped - /watch will use the CDN) && npm run dev"

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
