param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,47}$')]
    [string]$RunId,

    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'bootstrap-smoke',
        'dashboard-happy',
        'job-happy',
        'revision-stress',
        'encoding-paths',
        'resume',
        'network-denied',
        'missing-browser'
    )]
    [string]$Scenario
)

$ErrorActionPreference = 'Stop'
$runRoot = Join-Path $env:LOCALAPPDATA "CitizenHarness\runs\$RunId"
$environment = Join-Path $runRoot 'environment.ps1'
if (-not (Test-Path $environment -PathType Leaf)) {
    throw "Harness bootstrap has not completed for run $RunId"
}
. $environment
Set-Location $env:CITIZEN_HARNESS_WORKSPACE

$arguments = @(
    'run',
    'python',
    'tools/windows-harness/scenario.py',
    '--scenario',
    $Scenario,
    '--evidence-dir',
    $env:CITIZEN_HARNESS_EVIDENCE_DIR
)
if ($env:UV_OFFLINE -eq '1') {
    $arguments = @('run', '--offline', '--find-links', $env:UV_FIND_LINKS) + $arguments[1..($arguments.Length - 1)]
}
& uv @arguments
exit $LASTEXITCODE
