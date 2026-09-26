#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  DEV-1C: explicit restore of a C:\MYC\Services ACL backup made by the
  hardening (Backup-MYCAcl, JSON per-entry SDDL).

.DESCRIPTION
  Recovery tool, never run by the installer or by Uninstall. The backup is
  a JSON list [{"path": ..., "sddl": ...}] (NOT an icacls /save file, so
  icacls /restore does not apply to it).

  1. broker_deploy.py restore-plan validates the file strictly (structure,
     canonical absolute paths, no "..", only inside -ServicesRoot and never
     inside the Broker's own developer-broker directory, no duplicates,
     valid SDDL, root entry present) and returns the safe order: deepest
     entries first, the root LAST (children are restored while the hardened
     parents still grant Administrators full control).
  2. Before changing anything, every entry must exist, be canonical and not
     be (or sit under) a reparse point; otherwise nothing is restored.
  3. Each entry: reparse re-check, SDDL applied with Set-Acl
     (SetSecurityDescriptorSddlForm; never icacls /restore), re-read, and the
     effective SDDL must equal the backup. A final pass re-reads all entries.
  No other path is touched. -WhatIf shows the plan.

.EXAMPLE
  .\Restore-MYCServicesAcl.ps1 -BackupFile 'C:\MYC\Deployment\acl-backups\services-20260925T120000Z.acl.json' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][string]$BackupFile,
    [string]$RepoRoot = 'C:\Users\SMM ADMIN\myc_erp',
    [string]$ServicesRoot = 'C:\MYC\Services',
    [string]$LogsRoot = 'C:\MYC\Logs',
    [string]$DeploymentRoot = 'C:\MYC\Deployment'
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'MYCDeveloperBroker.psm1') -Force
Assert-MYCElevated

$layout = Get-MYCBrokerLayout -RepoRoot $RepoRoot -ServicesRoot $ServicesRoot -LogsRoot $LogsRoot -DeploymentRoot $DeploymentRoot
try {
    if (-not $BackupFile.EndsWith('.acl.json', [StringComparison]::OrdinalIgnoreCase)) { throw 'Se espera un respaldo .acl.json de Backup-MYCAcl.' }
    if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) { throw "Respaldo inexistente: $BackupFile" }
    if (Test-MYCIsReparsePoint -Path $BackupFile) { throw 'El archivo de respaldo es un reparse point; se aborta.' }

    $plan = Invoke-MYCDeployTool -Layout $layout -Arguments @(
        'restore-plan', '--backup', $BackupFile, '--services-root', $layout.ServicesRoot, '--exclude', $layout.ServiceDir)
    $entries = @($plan.entries)

    # Everything is checked before the first change.
    foreach ($entry in $entries) {
        if (-not (Test-Path -LiteralPath $entry.path)) { throw "Entrada del respaldo inexistente: $($entry.path)" }
        Assert-MYCNoRedirectedPath -Path $entry.path   # the path and every component: no reparse point
    }

    $restored = 0
    foreach ($entry in $entries) {
        if (-not $PSCmdlet.ShouldProcess($entry.path, 'Restaurar ACL (SDDL del respaldo)')) { continue }
        Assert-MYCNoRedirectedPath -Path $entry.path   # re-check right before the change
        $acl = Get-Acl -LiteralPath $entry.path
        $acl.SetSecurityDescriptorSddlForm([string]$entry.sddl)
        Set-Acl -LiteralPath $entry.path -AclObject $acl
        $effective = (Get-Acl -LiteralPath $entry.path).Sddl
        if ($effective -cne [string]$entry.sddl) { throw "El SDDL efectivo no coincide con el respaldo tras restaurar: $($entry.path)" }
        $restored++
    }

    if (-not $WhatIfPreference) {
        # Final pass: restoring a parent re-propagates its inheritable ACEs;
        # every entry must still equal the backup.
        $mismatch = @($entries | Where-Object { (Get-Acl -LiteralPath $_.path).Sddl -cne [string]$_.sddl } | ForEach-Object { $_.path })
        if ($mismatch.Count -gt 0) { throw ('Tras la restauración, estas entradas no coinciden con el respaldo: ' + ($mismatch -join '; ')) }
    }
} catch {
    Write-MYCFailure ('Restauración de ACL FALLÓ: ' + $_.Exception.Message)
    exit 1
}
Write-Host ('Restauración de ACL: {0} de {1} entradas restauradas y verificadas desde {2}.' -f $restored, $entries.Count, $BackupFile)
exit 0
