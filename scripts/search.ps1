<#
Thin wrapper over the shared vault-search engine (_tools/vault-search).
Scopes results to this project by default; -AllProjects searches the whole vault.

  scripts/search.ps1 "what did we decide about transport"
  scripts/search.ps1 "engine wiring" -K 5
  scripts/search.ps1 "filesystem first" -AllProjects
#>
param(
  [Parameter(Mandatory = $true, Position = 0)] [string]$Query,
  [int]$K = 8,
  [switch]$AllProjects
)
$py = "C:\Users\lucas\anaconda3\python.exe"
$engine = "D:\Project\_tools\vault-search\query.py"
$argv = @($engine, $Query, "--k", $K)
if (-not $AllProjects) { $argv += @("--project", "shinehackathon") }
& $py @argv
