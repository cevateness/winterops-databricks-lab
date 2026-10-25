# Read-only connectivity checks. Never dumps tokens or user identity to reports.
[CmdletBinding()]
param(
  [string]$Profile = 'winterops',
  [string]$WorkspaceHost = '',
  [switch]$Login
)
$ErrorActionPreference = 'Stop'
$cli = Get-Command 'databricks' -ErrorAction SilentlyContinue
if (-not $cli) { throw 'Databricks CLI not found. See docs/WINDOWS_SETUP.md.' }
if ($Login) {
    if (-not ($WorkspaceHost -match '^https://[^/]+/?$')) { throw 'Specify -WorkspaceHost https://<your-actual-workspace-host> with -Login.' }
    & $cli.Source auth login --host $WorkspaceHost.TrimEnd('/') --profile $Profile
    if ($LASTEXITCODE -ne 0) { throw 'CLI login failed; inspect the browser/account and profile locally.' }
}
$checks = [ordered]@{}
function Test-Command([string]$Name, [string[]]$Arguments) {
    Write-Host "Testing $Name..."
    try {
        # Redirect stdout/stderr to avoid printing names, workspace IDs or tokens.
        $output = & $cli.Source @Arguments 2>&1
        $ok = ($LASTEXITCODE -eq 0)
        if ($ok) { Write-Host "PASS: $Name" } else { Write-Warning "BLOCKED: $Name (exit $LASTEXITCODE)" }
        return $ok
    } catch {
        Write-Warning "BLOCKED: $Name (see local authentication/permissions)"
        return $false
    }
}
$checks['auth_profiles'] = Test-Command 'auth profiles' @('auth','profiles')
$checks['current_user'] = Test-Command 'current-user me' @('current-user','me','--profile',$Profile)
if ($checks['current_user']) {
    $checks['workspace_list'] = Test-Command 'workspace list' @('workspace','list','/Workspace','--profile',$Profile)
    $checks['jobs_list'] = Test-Command 'jobs list (optional)' @('jobs','list','--profile',$Profile)
} else {
    Write-Warning 'No authenticated workspace identity. Other read-only API checks skipped.'
}
Write-Host "Diagnostic status: $($checks | ConvertTo-Json -Compress)"
if (-not $checks['current_user']) { exit 2 }
exit 0
