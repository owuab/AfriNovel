$ErrorActionPreference = 'Stop'

$taskName = 'AfriNovelPublicDomainHarvest'

schtasks.exe /Delete /TN $taskName /F
Write-Host "Scheduled task '$taskName' removed if it existed."
