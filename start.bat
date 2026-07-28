@echo off
rem ============================================================
rem  Morning Triage - one-click local run (Windows)
rem  Double-click this file. It starts:
rem    * scoring service (FastAPI)  -> http://localhost:8000
rem    * triage dashboard (Next.js) -> http://localhost:3000
rem  Each runs in its own window; close the windows or run
rem  stop.bat to stop.
rem  Requires: Python 3.11+ and Node 18+ on PATH.
rem ============================================================
setlocal
cd /d "%~dp0"

rem --- Python: prefer the machine-profile interpreter over PATH.
rem     PATH `python` can be the Microsoft Store stub, which makes the
rem     scoring-service window die silently at pip install.
set "PY=python"
if exist "%~dp0..\_tools\vault.config.json" (
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "(Get-Content '%~dp0..\_tools\vault.config.json' -Raw | ConvertFrom-Json).python" 2^>nul`) do (
        if exist "%%P" set "PY=%%P"
    )
)
if "%PY%"=="python" (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python not found on PATH. Install Python 3.11+ from python.org
        pause
        exit /b 1
    )
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found on PATH. Install Node.js 18+ from nodejs.org
    pause
    exit /b 1
)

rem --- Telegram config check. Values set with `setx` live in the registry
rem     but are invisible to shells/Explorer launched before they were set,
rem     so a fresh session can look unconfigured when it isn't. Hydrate from
rem     HKCU\Environment when missing. Values are never printed.
if not defined SHINEHACKATHON_TELEGRAM_BOT_TOKEN (
    for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v SHINEHACKATHON_TELEGRAM_BOT_TOKEN 2^>nul ^| findstr /i "SHINEHACKATHON_TELEGRAM_BOT_TOKEN"') do set "SHINEHACKATHON_TELEGRAM_BOT_TOKEN=%%B"
)
if not defined SHINEHACKATHON_TELEGRAM_CHAT_ID (
    for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v SHINEHACKATHON_TELEGRAM_CHAT_ID 2^>nul ^| findstr /i "SHINEHACKATHON_TELEGRAM_CHAT_ID"') do set "SHINEHACKATHON_TELEGRAM_CHAT_ID=%%B"
)
if defined SHINEHACKATHON_TELEGRAM_BOT_TOKEN (
    if defined SHINEHACKATHON_TELEGRAM_CHAT_ID (
        echo [telegram] configured - falls will send REAL Telegram pings
    ) else (
        echo [telegram] PARTIAL config: bot token set but chat id missing - alerts will NOT send
    )
) else (
    if defined SHINEHACKATHON_TELEGRAM_CHAT_ID (
        echo [telegram] PARTIAL config: chat id set but bot token missing - alerts will NOT send
    ) else (
        echo [telegram] not configured - dashboard-only, no Telegram alerts
    )
)

echo Starting scoring service on http://localhost:8000 ...
start "triage-scoring-service" cmd /k "cd /d "%~dp0scoring-service" && "%PY%" -m pip install -q -r requirements.txt && "%PY%" -m uvicorn app.main:app --port 8000"

echo Starting dashboard on http://localhost:3000 ...
rem npm install runs unconditionally: a pull can add deps to package.json while
rem node_modules already exists (bit us 2026-07-27 - /watch 500 on the demo laptop).
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


