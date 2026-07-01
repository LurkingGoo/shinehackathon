@echo off
REM ============================================================================
REM shinehackathon -- DeepSeek fallback WATCHER (double-click; leave running)
REM ----------------------------------------------------------------------------
REM Start this ONCE at the beginning of a work block and leave the window open.
REM It watches this project's Claude Code transcript and, the moment Claude
REM reports "you've hit your session limit", AUTOMATICALLY opens a fresh DeepSeek
REM META-PLANNING window (plan-mode.cmd) so you can keep drafting plans.
REM
REM This is the sanctioned "automatic" fallback:
REM   - It runs as a SEPARATE process, so it survives the limit-locked session.
REM   - It NEVER routes the live session to DeepSeek, NEVER sends resident/health
REM     data, NEVER makes decisions. It only opens the existing guarded launcher.
REM
REM Stop it with Ctrl+C or by closing this window.
REM ============================================================================
setlocal
cd /d "%~dp0.."
echo Starting DeepSeek fallback watcher (auto-opens plan-mode on a Claude session-limit hit)...
echo Scope: planning only. Leave this window open. Ctrl+C to stop.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\plan-mode-watch.ps1" %*
echo.
echo [watcher stopped] Press any key to close this window.
pause >nul
