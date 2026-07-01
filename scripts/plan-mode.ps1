<#
.SYNOPSIS
    shinehackathon DeepSeek META-PLANNING launcher (thin wrapper over the shared engine).

.DESCRIPTION
    Delegates to the vault engine at _tools\deepseek-fallback\plan-mode-core.ps1, passing
    shinehackathon's plan-mode.config.json. All logic (routing matrix, balance pre-check,
    scope banner, env self-check, -DryRun, claude launch) lives in the engine; this file
    only resolves the engine, asserts a compatible VERSION, and forwards every argument.

    SCOPE (from the config): META-PLANNING ONLY -- never feed resident/health/PII data.

    Usage (unchanged):
      powershell scripts/plan-mode.ps1                 # orchestrated planning (pro lead)
      powershell scripts/plan-mode.ps1 -Mode flash     # all-cheap mechanical session
      powershell scripts/plan-mode.ps1 -Mode plan -DryRun   # print routing, do not launch
#>
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$engine = Join-Path $here '..\..\_tools\deepseek-fallback'
$core = Join-Path $engine 'plan-mode-core.ps1'
$cfg  = Join-Path $here 'plan-mode.config.json'
$REQUIRED_ENGINE_VERSION = 1

if (-not (Test-Path $core)) {
    Write-Error "DeepSeek engine not found at $core. Expected the shared engine in the vault's _tools\deepseek-fallback\."
    exit 1
}
$v = [int](& $core -Version)
if ($v -lt $REQUIRED_ENGINE_VERSION) {
    Write-Error "DeepSeek engine VERSION $v < required $REQUIRED_ENGINE_VERSION. Update _tools\deepseek-fallback\."
    exit 1
}

& $core -ConfigPath $cfg @args
exit $LASTEXITCODE
