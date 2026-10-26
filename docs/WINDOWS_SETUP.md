# Windows PowerShell setup without WinGet

## 1. Diagnose the actual problem

`winget : The term 'winget' is not recognized` means Windows cannot resolve Windows Package Manager. It is not a Databricks CLI authentication or execution failure.

```powershell
Get-Command winget -ErrorAction SilentlyContinue
Get-Command git -ErrorAction SilentlyContinue
Get-Command databricks -All -ErrorAction SilentlyContinue
```

Options:
- Restore the Microsoft **App Installer** package (which includes WinGet), if your device/security policy allows it. See https://learn.microsoft.com/windows/package-manager/winget/ .
- If Chocolatey is already installed, Databricks documents `choco install databricks-cli` but labels it experimental.
- **Recommended for this lab:** Install the official Databricks CLI standalone binary with the PowerShell script in this repository. It uses official GitHub release assets, verifies an available SHA-256 digest/checksum, extracts to a user-writable directory, and does not need WinGet or administrator rights.
- If downloading GitHub releases is blocked by corporate policy, stop and use an approved browser/manual download or use the Databricks website; do not disable security controls.

## 2. Portable CLI install (PowerShell)

```powershell
Set-Location '<your extracted WinterOps folder>'
.\scripts\install_databricks_cli.ps1
# Open a NEW terminal if PATH did not refresh in an existing shell.
databricks version
Get-Command databricks -All
```

This repository's script supports Windows x64/ARM64, `.zip` or `.tar.gz` official release assets. The installed executable is placed under `%LOCALAPPDATA%\WinterOps\bin`. It does **not** install the deprecated Python `databricks-cli` package. The GitHub API/asset download requires external HTTPS connectivity. Examine scripts before execution.

For an immediate no-script/manual fallback, download the latest Windows asset from https://github.com/databricks/cli/releases/latest, verify its published SHA-256, extract `databricks.exe` to a user-writable folder, and call it via its full path.

## 3. Workspace authentication

Copy your **workspace URL** from the browser (the exact workspace host, not the account login/console URL):

```powershell
$hostUrl = 'https://YOUR-REAL-WORKSPACE-HOST'
databricks auth login --host $hostUrl --profile winterops
.\scripts\test_databricks_connection.ps1 -Profile winterops -WorkspaceHost $hostUrl
```

If login doesn't open a browser, follow the CLI's instructions; do not paste session cookies, tokens or access codes into this chat or a GitHub issue. The connection checker does not log in or change authentication settings. It first inventories profile metadata using `auth profiles --skip-validate --output json`, rejects a missing/mismatched profile host, then performs `current-user me` and `workspace list /Workspace` with the named profile. CLI output is captured; only sanitized PASS/BLOCKED statuses are printed. Each command has a 30-second default timeout (maximum 60 seconds). Ambient Databricks credential/host variables are excluded so the named local profile determines authentication.

The equivalent portable check is:

```powershell
python scripts/check_databricks.py --profile winterops --workspace-host $hostUrl
# Optional Jobs API metadata probe; it does not start compute or submit a run.
python scripts/check_databricks.py --profile winterops --workspace-host $hostUrl --include-jobs
```

The checker exits `0` only when the requested checks pass and `2` for BLOCKED. `403` may mean missing endpoint permissions or a Free Edition limitation. Use a current standalone CLI; older/deprecated versions may not support these flags. Never use `auth token`, `auth env`, or `auth describe --sensitive` in shared logs. The original `-Login` wrapper switch is removed: authentication is a separate explicit CLI step.

For bounded analytics SQL rendering, notebook application and the integration acceptance checklist, see [ANALYTICS_SLICE.md](ANALYTICS_SLICE.md). No actual workspace probe or Spark execution was performed during this local implementation; the CLI is absent from the current PATH and no workspace target was supplied.

## 4. Troubleshooting matrix

| Symptom | Check / remedy |
|---|---|
| `winget` not recognized | WinGet/App Installer missing or not on PATH; use portable script |
| `git` not recognized | Install Git for Windows from official website or use GitHub's web UI upload |
| `databricks` not recognized after install | Start a new PowerShell session; inspect `%LOCALAPPDATA%\WinterOps\bin`; call `& "$env:LOCALAPPDATA\WinterOps\bin\databricks.exe" version` |
| Legacy CLI resolves first | Run `Get-Command databricks -All`; avoid obsolete pip `databricks-cli` binary shadowing the new CLI |
| OAuth failure | Check copied **workspace** host, browser/account access, local network and profile; never commit credentials |
| `401`/`403` on a workspace endpoint | Authentication expiry, target URL or user permissions; evaluate each endpoint separately |
| `jobs list` fails but `current-user me` works | CLI authenticated; Jobs API/permission unavailable; use website or other available interface |
| No Databricks access in Codex Cloud | Expected by default: cloud task cannot inherit Windows browser OAuth; keep CI offline until secure auth is supported |

Documentation: https://docs.databricks.com/aws/en/dev-tools/cli/install and https://docs.databricks.com/aws/en/dev-tools/cli/authentication
