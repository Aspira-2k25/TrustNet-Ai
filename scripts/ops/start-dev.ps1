# PowerShell entry point delegates to the canonical readiness-checked launcher.
param([switch]$Restart)
$taskArguments = @()
if ($Restart) { $taskArguments += '--restart' }
& (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'start-dev.bat') @taskArguments
exit $LASTEXITCODE
