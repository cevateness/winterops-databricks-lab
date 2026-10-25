# Initial one-time publication to an existing EMPTY GitHub repository.
# Never creates the remote repository; never force pushes; never deletes local files.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)] [string]$RepositoryUrl
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
if (-not (Test-Path (Join-Path $root 'PROJECT_REFERENCE.md'))) { throw 'Run this script from the WinterOps package; project reference missing.' }
if ($RepositoryUrl -notmatch '^https://github\.com/[A-Za-z0-9_.-]+/winterops-databricks-lab(?:\.git)?$') {
  throw 'Expected https://github.com/<owner>/winterops-databricks-lab.git. Confirm the correct PUBLIC repository URL.'
}
$git = Get-Command 'git' -ErrorAction SilentlyContinue
if (-not $git) { throw 'Git is not installed or not on PATH. Install official Git for Windows first.' }
if (-not (Test-Path '.git')) {
  & $git.Source init
  if ($LASTEXITCODE -ne 0) { throw 'git init failed.' }
}
& $git.Source add --all
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
$staged = @(& $git.Source diff --cached --name-only)
# Explicit allowlist: unknown CSVs must never be accidentally made public.
$csvAllowed = @('data/synthetic/snowplow_demo_synthetic.csv', 'docs/DATA_SOURCE_REGISTER.csv')
$unreviewedCsv = @($staged | Where-Object { $_ -match '\.csv$' -and $_ -notin $csvAllowed })
if ($unreviewedCsv.Count -gt 0) { throw "Refusing to publish unreviewed CSV files: $($unreviewedCsv -join ', ')" }
$forbidden = @($staged | Where-Object {
    $_ -match '(^|/)(data/(raw|private|downloads|imported)/|\.env($|\.)|\.databrickscfg$|\.databricks/|\.bundle/|reports/private/)' -or
    $_ -match '\.(exe|msi|pem|key|p12|parquet|delta|duckdb|db|zip|tar\.gz)$'
})
if ($forbidden.Count -gt 0) {
   throw "Refusing to publish suspicious staged files: $($forbidden -join ', ')"
}
Write-Host "Staged $($staged.Count) files for publication; no sensitive paths matched the basic guard."
Write-Host 'Review git diff --cached --stat and git diff --cached before approving public publication.'
& $git.Source diff --cached --stat
$hasCommit = (& $git.Source rev-parse --verify HEAD 2>$null)
if ($LASTEXITCODE -ne 0) {
    & $git.Source commit -m 'Bootstrap WinterOps Databricks learning project'
    if ($LASTEXITCODE -ne 0) { throw 'git commit failed. Check local git config user.name and user.email.' }
} elseif ($staged.Count -gt 0) {
    throw 'Local repository already has commits and staged changes; review them and commit manually before publishing.'
}
& $git.Source branch -M main
if ($LASTEXITCODE -ne 0) { throw 'Could not set main branch.' }
$remote = (& $git.Source remote get-url origin 2>$null)
if ($LASTEXITCODE -eq 0) {
    if ($remote -ne $RepositoryUrl) { throw "Existing origin differs from requested URL: $remote" }
} else {
    & $git.Source remote add origin $RepositoryUrl
    if ($LASTEXITCODE -ne 0) { throw 'Unable to configure origin remote.' }
}
Write-Host "Pushing to $RepositoryUrl; Git may ask you to authenticate in a browser."
& $git.Source push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Confirm the repository exists and is empty, and your GitHub credentials have write access. DO NOT force push.' }
Write-Host 'PASS: first publication pushed. Verify the public repository page and contents.'
