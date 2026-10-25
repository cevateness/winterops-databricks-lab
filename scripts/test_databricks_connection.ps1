# Read-only wrapper: explicitly select a profile AND expected workspace host.
# Authenticate separately with the official CLI. No credentials/CLI output are printed.
[CmdletBinding()]
param(
  [string]$Profile = 'winterops',
  [Parameter(Mandatory=$true)] [string]$WorkspaceHost,
  [switch]$IncludeJobs,
  [ValidateRange(1,60)] [int]$TimeoutSeconds = 30
)
$ErrorActionPreference = 'Stop'
$probeScript = Join-Path $PSScriptRoot 'check_databricks.py'
$probeArgs = @($probeScript, '--profile', $Profile, '--workspace-host', $WorkspaceHost,
               '--timeout', $TimeoutSeconds)
if ($IncludeJobs) { $probeArgs += '--include-jobs' }
& python @probeArgs
exit $LASTEXITCODE
