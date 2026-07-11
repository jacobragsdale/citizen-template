param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,47}$')]
    [string]$RunId,

    [Parameter(Mandatory = $true)]
    [string]$PayloadDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Write-Utf8File {
    param([string]$Path, [string]$Text)
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    throw 'The citizen harness must run as a standard user; the current token is elevated.'
}

$payload = (Resolve-Path $PayloadDir).Path
$manifestPath = Join-Path $payload 'payload-manifest.json'
if (-not (Test-Path $manifestPath -PathType Leaf)) {
    throw "Payload manifest is missing: $manifestPath"
}
$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.schema_version -ne 1) {
    throw 'The payload manifest schema is not supported.'
}

foreach ($artifact in $manifest.artifacts) {
    $artifactPath = Join-Path $payload $artifact.filename
    if (-not (Test-Path $artifactPath -PathType Leaf)) {
        throw "Payload artifact is missing: $($artifact.filename)"
    }
    $actual = (Get-FileHash -Algorithm SHA256 $artifactPath).Hash.ToLowerInvariant()
    if ($actual -ne $artifact.sha256) {
        throw "Payload checksum mismatch: $($artifact.filename)"
    }
}

$runRoot = Join-Path $env:LOCALAPPDATA "CitizenHarness\runs\$RunId"
if (Test-Path $runRoot) {
    throw "Run directory already exists; refusing to reuse state: $runRoot"
}
$tools = Join-Path $runRoot 'tools'
$workspaceName = 'caf' + [char]0x00e9 + ' demo'
$workspace = Join-Path $runRoot (Join-Path 'Citizen Apps' $workspaceName)
$evidence = Join-Path $runRoot 'evidence'
New-Item -ItemType Directory -Path $tools, $workspace, $evidence -Force | Out-Null

$uvDir = Join-Path $tools 'uv'
$gitDir = Join-Path $tools 'git'
New-Item -ItemType Directory -Path $uvDir, $gitDir -Force | Out-Null
Expand-Archive -Path (Join-Path $payload 'uv-windows.zip') -DestinationPath $uvDir
Expand-Archive -Path (Join-Path $payload 'mingit.zip') -DestinationPath $gitDir
tar.exe -xf (Join-Path $payload 'python-windows.tar.gz') -C $tools
Expand-Archive -Path (Join-Path $payload 'template-source.zip') -DestinationPath $workspace

$wheelhouseArchive = Join-Path $payload 'wheelhouse.zip'
$wheelhouse = Join-Path $runRoot 'wheelhouse'
if (Test-Path $wheelhouseArchive -PathType Leaf) {
    New-Item -ItemType Directory -Path $wheelhouse -Force | Out-Null
    Expand-Archive -Path $wheelhouseArchive -DestinationPath $wheelhouse
}

$uv = Join-Path $uvDir 'uv.exe'
$git = Join-Path $gitDir 'cmd\git.exe'
$python = Join-Path $tools 'python\python.exe'
foreach ($required in @($uv, $git, $python)) {
    if (-not (Test-Path $required -PathType Leaf)) {
        throw "A staged executable is missing after extraction: $required"
    }
}

$initialToolNames = @('uv', 'git', 'python', 'gh', 'docker', 'wsl')
$initialTools = @{}
foreach ($name in $initialToolNames) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    $initialTools[$name] = if ($null -eq $command) { $null } else { $command.Source }
}

$env:PATH = "$uvDir;$($gitDir)\cmd;$($tools)\python;$env:PATH"
$env:UV_CACHE_DIR = Join-Path $runRoot 'uv-cache'
$env:UV_PYTHON = $python
$env:UV_PYTHON_DOWNLOADS = 'never'
$env:UV_NO_MODIFY_PATH = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = Join-Path $workspace 'src'
if (Test-Path $wheelhouse -PathType Container) {
    $env:UV_FIND_LINKS = $wheelhouse
    $env:UV_OFFLINE = '1'
    $env:UV_NO_SYNC = '1'
    $env:CITIZEN_HARNESS_UI_LOCK = Join-Path $payload 'ui-uv.lock'
    $env:CITIZEN_HARNESS_UI_PROJECT = Join-Path $payload 'ui-pyproject.toml'
    if (-not (Test-Path $env:CITIZEN_HARNESS_UI_LOCK -PathType Leaf)) {
        throw 'The staged cross-platform UI lock is missing.'
    }
    if (-not (Test-Path $env:CITIZEN_HARNESS_UI_PROJECT -PathType Leaf)) {
        throw 'The staged cross-platform UI project is missing.'
    }
}

Push-Location $workspace
try {
    & $git init --quiet
    & $git config user.name 'Citizen Harness'
    & $git config user.email 'citizen-harness@invalid.example'
    & $git config core.autocrlf false
    & $git add --all
    & $git commit --quiet -m 'Harness source snapshot'
    if (Test-Path $wheelhouse -PathType Container) {
        $requirements = Join-Path $wheelhouse 'requirements.txt'
        if (-not (Test-Path $requirements -PathType Leaf)) {
            throw 'The staged wheelhouse is missing requirements.txt.'
        }
        & $uv venv .venv --python $python
        if ($LASTEXITCODE -ne 0) {
            throw "uv venv failed with exit code $LASTEXITCODE"
        }
        $venvPython = Join-Path $workspace '.venv\Scripts\python.exe'
        & $uv pip install `
            --python $venvPython `
            --offline `
            --find-links $wheelhouse `
            --requirements $requirements `
            hatchling `
            editables
        if ($LASTEXITCODE -ne 0) {
            throw "offline dependency install failed with exit code $LASTEXITCODE"
        }
        & $uv pip install `
            --python $venvPython `
            --offline `
            --find-links $wheelhouse `
            --no-build-isolation `
            --no-deps `
            --editable .
        if ($LASTEXITCODE -ne 0) {
            throw "offline project install failed with exit code $LASTEXITCODE"
        }
    } else {
        & $uv sync --python $python
        if ($LASTEXITCODE -ne 0) {
            throw "uv sync failed with exit code $LASTEXITCODE"
        }
    }
} finally {
    Pop-Location
}

function Quote-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

$environmentScript = @(
    "`$env:PATH = $(Quote-PowerShellLiteral "$uvDir;$($gitDir)\cmd;$($tools)\python;") + `$env:PATH",
    "`$env:UV_CACHE_DIR = $(Quote-PowerShellLiteral $env:UV_CACHE_DIR)",
    "`$env:UV_PYTHON = $(Quote-PowerShellLiteral $python)",
    "`$env:UV_PYTHON_DOWNLOADS = 'never'",
    "`$env:UV_NO_MODIFY_PATH = '1'",
    "`$env:PYTHONUTF8 = '1'",
    "`$env:PYTHONIOENCODING = 'utf-8'",
    "`$env:PYTHONPATH = $(Quote-PowerShellLiteral $env:PYTHONPATH)",
    "`$env:CITIZEN_HARNESS_RUN_ROOT = $(Quote-PowerShellLiteral $runRoot)",
    "`$env:CITIZEN_HARNESS_WORKSPACE = $(Quote-PowerShellLiteral $workspace)",
    "`$env:CITIZEN_HARNESS_EVIDENCE_DIR = $(Quote-PowerShellLiteral $evidence)"
)
if (Test-Path $wheelhouse -PathType Container) {
    $environmentScript += "`$env:UV_FIND_LINKS = $(Quote-PowerShellLiteral $wheelhouse)"
    $environmentScript += "`$env:UV_OFFLINE = '1'"
    $environmentScript += "`$env:UV_NO_SYNC = '1'"
    $environmentScript += "`$env:CITIZEN_HARNESS_UI_LOCK = $(Quote-PowerShellLiteral $env:CITIZEN_HARNESS_UI_LOCK)"
    $environmentScript += "`$env:CITIZEN_HARNESS_UI_PROJECT = $(Quote-PowerShellLiteral $env:CITIZEN_HARNESS_UI_PROJECT)"
}
$environmentPath = Join-Path $runRoot 'environment.ps1'
$powerShellEncoding = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText(
    $environmentPath,
    (($environmentScript -join "`r`n") + "`r`n"),
    $powerShellEncoding
)

$windows = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
Add-Type -AssemblyName Microsoft.VisualBasic
$computer = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
$groups = @((whoami /groups /fo csv /nh) | ForEach-Object { $_ })
$environmentEvidence = [ordered]@{
    schema_version = 1
    run_id = $RunId
    username = $identity.Name
    elevated = $isAdmin
    windows_caption = $windows.ProductName
    windows_version = $windows.DisplayVersion
    windows_build = $windows.CurrentBuildNumber
    memory_bytes = [int64]$computer.TotalPhysicalMemory
    culture = [Globalization.CultureInfo]::CurrentCulture.Name
    initial_tools = $initialTools
    groups = $groups
    run_root = $runRoot
    workspace = $workspace
    source = $manifest.source
}
Write-Utf8File -Path (Join-Path $evidence 'environment.json') -Text (($environmentEvidence | ConvertTo-Json -Depth 8) + "`n")

$result = [ordered]@{
    schema_version = 1
    run_id = $RunId
    run_root = $runRoot
    workspace = $workspace
    evidence = $evidence
    environment_script = $environmentPath
}
Write-Utf8File -Path (Join-Path $evidence 'bootstrap-result.json') -Text (($result | ConvertTo-Json -Depth 5) + "`n")
$result | ConvertTo-Json -Compress
