#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  DEV-1C: hardens the ACL of C:\MYC\Services (standalone; the installer runs
  the same function with -HardenServicesAcl).

.DESCRIPTION
  Finding: C:\MYC\Services held the wrappers/XML of LocalSystem services
  (MYCBackend, MYCFrontend) while NT AUTHORITY\Authenticated Users had
  Modify: any local user could replace a LocalSystem service binary or its
  configuration.

  Result: owner Administrators (recursive); inheritance disabled; SYSTEM and
  Administrators full control; BUILTIN\Users read/execute ONLY with
  -AllowUsersRead (the LocalSystem services do not need it); Authenticated
  Users and every other explicit principal removed; descendants reset to
  inherit (except developer-broker, which keeps its own protected ACL).

  The previous ACLs are saved first as per-entry SDDL (JSON, no-follow walk)
  into C:\MYC\Deployment\developer-broker\acl-backups; restore explicitly
  with Restore-MYCServicesAcl.ps1 -BackupFile <file>. The root is closed first, then the tree is
  reset entry by entry, top-down, never following a reparse point.
  Without -Apply it only reports (read-only).
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'C:\Users\SMM ADMIN\myc_erp',
    [string]$ServicesRoot = 'C:\MYC\Services',
    [string]$LogsRoot = 'C:\MYC\Logs',
    [string]$DeploymentRoot = 'C:\MYC\Deployment',
    [switch]$AllowUsersRead,
    [switch]$Apply
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'MYCDeveloperBroker.psm1') -Force
Assert-MYCElevated

$layout = Get-MYCBrokerLayout -RepoRoot $RepoRoot -ServicesRoot $ServicesRoot -LogsRoot $LogsRoot -DeploymentRoot $DeploymentRoot
try {
    $violations = @(Test-MYCServicesAcl -Layout $layout -AllowUsersRead:$AllowUsersRead)
    if ($violations.Count -eq 0) {
        Write-Host "$ServicesRoot ya es conforme."
        exit 0
    }
    Write-Host "Violaciones actuales en ${ServicesRoot}:"
    $violations | ForEach-Object { Write-Host "  $_" }
    if (-not $Apply) {
        Write-Host 'Sólo lectura: vuelva a ejecutar con -Apply para endurecer (con respaldo previo).'
        exit 2
    }
    # Backup-MYCAcl protects only C:\MYC\Deployment\developer-broker (its
    # parent is inspected, never re-ACLed).
    $backup = Set-MYCServicesAclHardening -Layout $layout -AllowUsersRead:$AllowUsersRead
    Write-Host "Endurecido. ACL previa respaldada en: $backup"
    Get-Service -Name 'MYCBackend', 'MYCFrontend' -ErrorAction SilentlyContinue | Format-Table Name, Status -AutoSize | Out-String | Write-Host
} catch {
    Write-MYCFailure ('Endurecimiento FALLÓ: ' + $_.Exception.Message)
    exit 1
}
exit 0
