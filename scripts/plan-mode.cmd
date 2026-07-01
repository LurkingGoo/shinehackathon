@echo off
REM ============================================================================
REM shinehackathon -- DeepSeek META-PLANNING fallback (double-click launcher)
REM ----------------------------------------------------------------------------
REM Double-click this when the primary Claude budget is exhausted and you need
REM to keep DRAFTING PLANS. It opens a fresh Claude Code session on DeepSeek v4
REM by running scripts\plan-mode.ps1 (which holds the routing matrix, balance
REM pre-check, and self-check).
REM
REM HARD SCOPE (operator decision): META-PLANNING ONLY.
REM   - No decisions of record. Drafting plans / task breakdowns / docs only.
REM   - NEVER paste resident, health, incident, or PII data into this session
REM     (eldercare data-residency). No fixtures / ResidentDetail / IncidentEvent.
REM   - There is intentionally NO auto-switch: this is a deliberate manual launch
REM     in a SEPARATE process, so the live session never silently routes data.
REM
REM Default mode is "plan" (pro lead + flash workers). Pass args to override, e.g.
REM   plan-mode.cmd -Mode flash
REM ============================================================================
setlocal
cd /d "%~dp0.."
echo Launching DeepSeek META-PLANNING profile (manual fallback)...
echo Scope: planning only. Do NOT feed resident/health/PII data into this session.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\plan-mode.ps1" %*
echo.
echo [DeepSeek planning session ended] Press any key to close this window.
pause >nul
