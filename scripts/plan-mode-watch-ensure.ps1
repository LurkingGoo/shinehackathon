<#
.SYNOPSIS
    shinehackathon "ensure the watcher is running" (thin wrapper over the shared engine).
    Called by the UserPromptSubmit hook every turn -> idempotent, keeps one hidden watcher.

.DESCRIPTION
    Delegates to _tools\deepseek-fallback\plan-mode-watch-ensure.ps1, pointing it at the
    engine watcher and forwarding THIS project's watch args (-ProjectRoot + the launcher to
    open). Supports -Status / -Stop (forwarded). Executes nothing DeepSeek itself.
#>
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$proj = Split-Path -Parent $here
$engine = Join-Path $here '..\..\_tools\deepseek-fallback'
$ensure = Join-Path $engine 'plan-mode-watch-ensure.ps1'
$watch  = Join-Path $engine 'plan-mode-watch.ps1'
$REQUIRED_ENGINE_VERSION = 2   # per-project IdentToken scoping needs engine >= 2

if (-not (Test-Path $ensure)) {
    Write-Error "DeepSeek engine not found at $ensure. Expected the shared engine in _tools\deepseek-fallback\."
    exit 1
}
$v = [int]((Get-Content (Join-Path $engine 'VERSION') -Raw).Trim())
if ($v -lt $REQUIRED_ENGINE_VERSION) {
    Write-Error "DeepSeek engine VERSION $v < required $REQUIRED_ENGINE_VERSION. Update _tools\deepseek-fallback\."
    exit 1
}

& $ensure -WatchScript $watch -IdentToken $proj -WatchArgs @('-ProjectRoot', $proj, '-LauncherPath', (Join-Path $here 'plan-mode.cmd')) @args
exit $LASTEXITCODE
