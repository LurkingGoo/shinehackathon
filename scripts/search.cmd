@echo off
REM Double-click / cmd wrapper -> scripts/search.ps1 -> _tools/vault-search engine.
REM Usage: search.cmd "your query here"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0search.ps1" %*
