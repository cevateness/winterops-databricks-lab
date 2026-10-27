# Windows PowerShell setup without WinGet

## Verified local state (2026-10-28)

The initial audit found no CLI, default `.databrickscfg` or `DATABRICKS_*` environment variables. A subsequent user installation attempt was blocked by the effective `Restricted` execution policy. The installer also carried an Internet-download mark (`ZoneId=3`).

Follow-up: after reviewing and unblocking only the installer, it ran successfully in a child process with `RemoteSigned`. The official Windows amd64 release passed its SHA-256 check and **Databricks CLI v1.22.1** was installed under `%LOCALAPPDATA%\WinterOps\bin`; direct version verification passed. The parent policy remains `Restricted`; no current-user or machine policy was changed. Authentication and workspace access are still pending; no login, workspace query or remote mutation was run. A browser sign-in is separate from CLI configuration.

Use the login steps below to establish the named profile when ready. Keep the actual host/profile configuration local; the repository records sanitized verification results only.

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
# After reviewing this repository script, remove its Internet-download mark if present.
Unblock-File -LiteralPath .\scripts\install_databricks_cli.ps1
# Allow local scripts only in this child PowerShell session.
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\install_databricks_cli.ps1
if ($LASTEXITCODE -ne 0) { throw 'CLI installation failed; stop before login.' }
$databricksExe = "$env:LOCALAPPDATA\WinterOps\bin\databricks.exe"
& $databricksExe version
```

This repository's script supports Windows x64/ARM64, `.zip` or `.tar.gz` official release assets. The installed executable is placed under `%LOCALAPPDATA%\WinterOps\bin`. It does **not** install the deprecated Python `databricks-cli` package. The GitHub API/asset download requires external HTTPS connectivity. Examine scripts before execution.

If direct script execution reports **"running scripts is disabled"**, the installer has not run; subsequent missing-CLI errors follow from that. The command above sets `RemoteSigned` only for the child process; it does not change the current-user or machine policy. A downloaded unsigned script may additionally report **"not digitally signed"**: after reviewing this specific script, `Unblock-File` removes its Internet-download mark. It does not sign the file or relax policy for other scripts. Group Policy still takes precedence. Inspect `Get-ExecutionPolicy -List` if it remains blocked. See [Microsoft's execution-policy documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-5.1#set-a-different-policy-for-one-session).

Because the installer runs in a child process, its PATH refresh does not reach the calling shell. Use the executable path above immediately. To use the short `databricks` command in this shell, run `$env:Path = "$env:LOCALAPPDATA\WinterOps\bin;$env:Path"`; future terminal processes inherit the updated user PATH. Windows PowerShell 5.1 downloads use `-UseBasicParsing`, avoiding the web-content parsing prompt documented by [Microsoft](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-webrequest?view=powershell-5.1).

For an immediate no-script/manual fallback, download the latest Windows asset from https://github.com/databricks/cli/releases/latest, verify its published SHA-256, extract `databricks.exe` to a user-writable folder, and call it via its full path.

## 3. Workspace authentication

Copy your **workspace URL** from the browser (the exact workspace host, not the account login/console URL):

```powershell
$databricksExe = "$env:LOCALAPPDATA\WinterOps\bin\databricks.exe"
$workspaceUrl = [uri](Read-Host 'Paste your actual Databricks workspace URL')
$hostUrl = $workspaceUrl.GetLeftPart([System.UriPartial]::Authority)
& $databricksExe auth login --host $hostUrl --profile winterops
if ($LASTEXITCODE -ne 0) { throw 'Login failed; stop before the connectivity check.' }
# Refresh PATH for the Python checker in this terminal.
$env:Path = "$env:LOCALAPPDATA\WinterOps\bin;$env:Path"
python scripts/check_databricks.py --profile winterops --workspace-host $hostUrl
```

Enter the actual workspace URL when prompted; `https://YOUR-WORKSPACE-HOST` is a placeholder and cannot authenticate. The command keeps only the scheme and authority, removing a notebook/editor path, query and fragment before login. If a previously saved profile includes a page path, repeat login using this corrected host; the checker intentionally rejects it rather than contacting an unintended endpoint. The Python checker avoids the PowerShell script-policy restriction. If you prefer the wrapper, review and unblock that specific script, then run `powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\test_databricks_connection.ps1 -Profile winterops -WorkspaceHost $hostUrl`.

If login doesn't open a browser, follow the CLI's instructions; do not paste session cookies, tokens or access codes into this chat or a GitHub issue. The connection checker does not log in or change authentication settings. It first inventories profile metadata using `auth profiles --skip-validate --output json`, rejects a missing/mismatched profile host, then performs `current-user me` and `workspace list /Workspace` with the named profile. CLI output is captured; only sanitized PASS/BLOCKED statuses are printed. Each command has a 30-second default timeout (maximum 60 seconds). Ambient Databricks credential/host variables are excluded so the named local profile determines authentication.

The equivalent portable check is:

```powershell
python scripts/check_databricks.py --profile winterops --workspace-host $hostUrl
# Optional Jobs API metadata probe; it does not start compute or submit a run.
python scripts/check_databricks.py --profile winterops --workspace-host $hostUrl --include-jobs
```

The checker exits `0` only when the requested checks pass and `2` for BLOCKED. `403` may mean missing endpoint permissions or a Free Edition limitation. Use a current standalone CLI; older/deprecated versions may not support these flags. Never use `auth token`, `auth env`, or `auth describe --sensitive` in shared logs. The original `-Login` wrapper switch is removed: authentication is a separate explicit CLI step.

For bounded analytics SQL rendering and the integration checklist, see [ANALYTICS_SLICE.md](ANALYTICS_SLICE.md). After connection verification and file-hash review, use Lesson 6 `mode=validate` to run read-only source and candidate-consumer checks. `mode=apply` requires separate approval for view writes. No workspace probe or Spark execution was performed in the 2026-10-28 audit.

## 4. Troubleshooting matrix

| Symptom | Check / remedy |
|---|---|
| `winget` not recognized | WinGet/App Installer missing or not on PATH; use portable script |
| `running scripts is disabled` | Run the reviewed local installer in a child `powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ...` session; inspect managed policy if still blocked |
| `git` not recognized | Install Git for Windows from official website or use GitHub's web UI upload |
| `databricks` not recognized after install | Start a new PowerShell session; inspect `%LOCALAPPDATA%\WinterOps\bin`; call `& "$env:LOCALAPPDATA\WinterOps\bin\databricks.exe" version` |
| Legacy CLI resolves first | Run `Get-Command databricks -All`; avoid obsolete pip `databricks-cli` binary shadowing the new CLI |
| OAuth failure | Check copied **workspace** host, browser/account access, local network and profile; never commit credentials |
| `401`/`403` on a workspace endpoint | Authentication expiry, target URL or user permissions; evaluate each endpoint separately |
| `jobs list` fails but `current-user me` works | CLI authenticated; Jobs API/permission unavailable; use website or other available interface |
| No Databricks access in Codex Cloud | Expected by default: cloud task cannot inherit Windows browser OAuth; keep CI offline until secure auth is supported |

Documentation: https://docs.databricks.com/aws/en/dev-tools/cli/install and https://docs.databricks.com/aws/en/dev-tools/cli/authentication
