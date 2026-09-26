#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  DEV-1C: read-only post-install validation of MYCDeveloperBroker.

.DESCRIPTION
  Changes nothing. Checks: service running under NT SERVICE\MYCDeveloperBroker
  (SID resolved by LSA + SCM), automatic start, whole process tree owned by
  the Broker SID (never LocalSystem), pipe present, pipe DACL refuses this
  elevated administrator, "Developer Broker escuchando" logged, secret absent
  from the logs, ERP/Broker configuration consistent (same secret, compared
  without printing it), MYCBackend still LocalSystem and the ACL policies of
  the service directory, log directory, C:\MYC\Services and backend\.env.

  It cannot perform broker.health itself: the pipe only admits the ERP
  identity (LocalSystem). The end-to-end health check is
  GET /api/mobile/v1/developer/broker/health (DeveloperSession +
  developer.system.read). Exit code 0 only if every check passes.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'C:\Users\SMM ADMIN\myc_erp',
    [string]$ServicesRoot = 'C:\MYC\Services',
    [string]$LogsRoot = 'C:\MYC\Logs',
    [string]$DeploymentRoot = 'C:\MYC\Deployment',
    [string]$PipeName = 'MYCDeveloperBroker',
    [switch]$AllowUsersReadOnServices
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'MYCDeveloperBroker.psm1') -Force
Assert-MYCElevated

$layout = Get-MYCBrokerLayout -RepoRoot $RepoRoot -ServicesRoot $ServicesRoot -LogsRoot $LogsRoot -DeploymentRoot $DeploymentRoot
try {
    $verdict = Get-MYCBrokerServiceVerdict -Layout $layout
    if ($verdict.Verdict -ne 'compatible') { throw ('Servicio {0}: {1} {2}' -f $ServiceId, $verdict.Verdict, ($verdict.Reasons -join ',')) }
    $serviceSid = Resolve-MYCBrokerServiceSid
    $results = @(Test-MYCBrokerRuntime -Layout $layout -ServiceSid $serviceSid -PipeName $PipeName -AllowUsersRead:$AllowUsersReadOnServices)
} catch {
    Write-MYCFailure ('Validación no ejecutable: ' + $_.Exception.Message)
    exit 1
}
Write-MYCResults -Results $results
$failures = @($results | Where-Object { $_.Status -ne 'PASS' })
if ($failures.Count -gt 0) {
    Write-MYCFailure ('{0} verificaciones fallaron.' -f $failures.Count)
    exit 1
}
Write-Host 'MYCDeveloperBroker: todas las verificaciones pasaron.'
exit 0
