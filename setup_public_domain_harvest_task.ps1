$ErrorActionPreference = 'Stop'

$taskName = 'AfriNovelPublicDomainHarvest'
$batPath = (Resolve-Path (Join-Path $PSScriptRoot 'run_public_domain_harvest.bat')).Path

if (-not (Test-Path $batPath)) {
    throw "The batch launcher was not found at: $batPath"
}

# Quote the full path for Task Scheduler so the batch file launches correctly.
$taskCommand = '"' + $batPath + '"'

schtasks.exe /Create /TN $taskName /TR $taskCommand /SC HOURLY /MO 1 /RL HIGHEST /F

Write-Host "Scheduled task '$taskName' created successfully."
Write-Host "The harvest will run every hour in the background."
Write-Host "To disable it later, run:"
Write-Host "  schtasks.exe /Delete /TN $taskName /F"
