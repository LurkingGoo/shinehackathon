<#
.SYNOPSIS
    shinehackathon fallback WATCHER (thin wrapper over the shared engine).

.DESCRIPTION
    Delegates to _tools\deepseek-fallback\plan-mode-watch.ps1, telling it to watch THIS
    project's transcripts (-ProjectRoot) and to open THIS project's launcher
    (scripts\plan-mode.cmd) on a genuine Claude session-limit hit. Detection + loop live
    in the engine. Forwards any extra args (e.g. -Once -FromStart -DryRun -TranscriptFile).

    Manual use: double-click scripts\plan-mode-watch.cmd (or run this directly).
#>
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$proj = Split-Path -Parent $here
$watch = Join-Path $here '..\..\_tools\deepseek-fallback\plan-mode-watch.ps1'

if (-not (Test-Path $watch)) {
    Write-Error "DeepSeek engine watcher not found at $watch. Expected the shared engine in _tools\deepseek-fallback\."
    exit 1
}

& $watch -ProjectRoot $proj -LauncherPath (Join-Path $here 'plan-mode.cmd') @args
exit $LASTEXITCODE
