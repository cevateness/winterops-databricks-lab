# Installs official Databricks CLI standalone binary under the user's LocalAppData.
# No WinGet or administrator privilege required. Designed for Windows PowerShell 5.1+.
[CmdletBinding()]
param(
    [string]$Destination = "$env:LOCALAPPDATA\WinterOps\bin",
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core') {
    if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
        throw 'This installer is for Windows PowerShell only.'
    }
}
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

$existing = Get-Command databricks -ErrorAction SilentlyContinue
if ($existing -and -not $Force) {
    Write-Host "Databricks command already found at: $($existing.Source)"
    & $existing.Source version
    Write-Host 'Use -Force only if you intentionally want to install the standalone CLI alongside the existing command.'
    exit 0
}

$arch = $env:PROCESSOR_ARCHITECTURE
switch -Regex ($arch) {
    '^AMD64$' { $archName = 'amd64'; break }
    '^ARM64$' { $archName = 'arm64'; break }
    default { throw "Unsupported Windows architecture '$arch'. Use official releases manually." }
}
$headers = @{ 'User-Agent'='WinterOps-CLI-Installer'; 'Accept'='application/vnd.github+json' }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/databricks/cli/releases/latest' -Headers $headers
$pattern = "^databricks_cli_.*_windows_${archName}\.(zip|tar\.gz)$"
$asset = @($release.assets | Where-Object { $_.name -match $pattern } | Sort-Object -Property name)[0]
if (-not $asset) { throw "No official Windows/$archName CLI asset found. Use https://github.com/databricks/cli/releases/latest" }

$tempParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$tempRoot = Join-Path $tempParent ("winterops-databricks-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    $assetPath = Join-Path $tempRoot $asset.name
    Write-Host "Downloading official release: $($asset.name)"
    Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -Headers @{ 'User-Agent'='WinterOps-CLI-Installer' } -OutFile $assetPath
    $expected = $null
    if ($asset.digest -and $asset.digest -match '^sha256:([0-9a-fA-F]{64})$') { $expected = $Matches[1] }
    if (-not $expected) {
        $manifest = @($release.assets | Where-Object { $_.name -match 'SHA256SUMS$' })[0]
        if ($manifest) {
            $manifestFile = Join-Path $tempRoot $manifest.name
            Invoke-WebRequest -UseBasicParsing -Uri $manifest.browser_download_url -Headers @{ 'User-Agent'='WinterOps-CLI-Installer' } -OutFile $manifestFile
            $line = Get-Content $manifestFile | Where-Object { $_ -match [regex]::Escape($asset.name) + '$' } | Select-Object -First 1
            if ($line -and $line -match '^([0-9a-fA-F]{64})\s+') { $expected = $Matches[1] }
        }
    }
    if (-not $expected) { throw 'Release SHA-256 checksum could not be established. Refusing to execute/download unverified CLI.' }
    $actual = (Get-FileHash -Algorithm SHA256 -Path $assetPath).Hash
    if ($actual -ine $expected) { throw "SHA-256 mismatch for $($asset.name)" }
    Write-Host 'SHA-256 verified against release metadata.'
    $unpack = Join-Path $tempRoot 'unpacked'
    New-Item -ItemType Directory -Path $unpack | Out-Null
    if ($asset.name.EndsWith('.zip')) {
        Expand-Archive -LiteralPath $assetPath -DestinationPath $unpack -Force
    } elseif ($asset.name.EndsWith('.tar.gz')) {
        $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
        if (-not $tar) { throw 'Windows tar.exe not found. Download the .zip release manually or enable tar support.' }
        & $tar.Source -xzf $assetPath -C $unpack
        if ($LASTEXITCODE -ne 0) { throw 'Archive extraction failed.' }
    } else { throw 'Unsupported archive extension.' }
    $exe = Get-ChildItem -Path $unpack -Filter 'databricks.exe' -Recurse -File | Select-Object -First 1
    if (-not $exe) { throw 'Could not locate databricks.exe after extraction.' }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $target = Join-Path $Destination 'databricks.exe'
    Copy-Item -LiteralPath $exe.FullName -Destination $target -Force
    $env:Path = "$Destination;$env:Path"
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @($userPath -split ';' | Where-Object { $_ })
    if (-not ($parts | Where-Object { $_.TrimEnd('\') -ieq $Destination.TrimEnd('\') })) {
        [Environment]::SetEnvironmentVariable('Path', (($parts + $Destination) -join ';'), 'User')
    }
    Write-Host "Installed verified CLI to $target"
    & $target version
    if ($LASTEXITCODE -ne 0) { throw 'Installed CLI version check failed.' }
    Write-Host 'Start a new PowerShell session if the command is not yet on PATH.'
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        $cleanupTarget = (Resolve-Path -LiteralPath $tempRoot).ProviderPath
        if ((Split-Path -Parent $cleanupTarget) -ine $tempParent -or
            (Split-Path -Leaf $cleanupTarget) -notmatch '^winterops-databricks-[0-9a-f]{32}$') {
            throw 'Refusing cleanup outside the installer temporary directory.'
        }
        Remove-Item -LiteralPath $cleanupTarget -Recurse -Force
    }
}
