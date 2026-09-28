#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  DEV-1C: removes the MYCDeveloperBroker service (rollback of the installer).

.DESCRIPTION
  Bounded and explicit. Every step is a ShouldProcess action (-WhatIf shows
  the plan; ConfirmImpact High asks per step unless -Confirm:$false).

  Ownership: only what install-state.json (validated schema/identity;
  corrupt or foreign -> refuse) records as created/added by DEV-1C is
  undone, also after a partially failed installation. Each undo step clears
  its own ledger entry; the ledger is deleted only when it owns nothing.
  A compatible MYCDeveloperBroker service with no ledger is not adopted.

   0. An interrupted XML/.env provisioning (journal) is restored first.
   1. backend\.env managed block: DEVELOPER_BROKER_ENABLED=false (always) or
      removed entirely with -RemoveBackendConfig. MYCBackend is restarted only
      with -RestartBackend; it is never stopped, reconfigured or deleted.
   2. Broker stop: SCM stop, at most 45 s; then only processes of the service
      tree owned by the Broker SID are terminated, at most 10 s more; else fail.
   3. Service deletion (sc.exe delete), waiting at most 30 s -- only if the
      ledger records DEV-1C as its creator.
   4. Broker ACEs removed from every path recorded in the ledger.
   5. SeServiceLogonRight revoked ONLY if the ledger records it as added (or
      pending) by DEV-1C; never a right that pre-existed or came from
      NT SERVICE\ALL SERVICES.
   6. Files: the service directory (it contains the secret-bearing XML) is
      removed only with -RemoveServiceFiles, the log directory only with
      -RemoveLogs. Kept otherwise, with a warning.

  NOT reverted: the C:\MYC\Services ACL hardening (a security fix). Its
  pre-hardening ACL lives in C:\MYC\Deployment\acl-backups
  as per-entry SDDL (JSON); restoring it is an explicit, separate action:
  Restore-MYCServicesAcl.ps1 -BackupFile <file> (never run by Uninstall).

.EXAMPLE
  .\Uninstall-MYCDeveloperBroker.ps1 -WhatIf
.EXAMPLE
  .\Uninstall-MYCDeveloperBroker.ps1 -RemoveServiceFiles -RestartBackend
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [string]$RepoRoot = 'C:\Users\SMM ADMIN\myc_erp',
    [string]$ServicesRoot = 'C:\MYC\Services',
    [string]$LogsRoot = 'C:\MYC\Logs',
    [string]$DeploymentRoot = 'C:\MYC\Deployment',
    [switch]$RemoveBackendConfig,
    [switch]$RemoveServiceFiles,
    [switch]$RemoveLogs,
    [switch]$RestartBackend
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'MYCDeveloperBroker.psm1') -Force
Assert-MYCElevated

$layout = Get-MYCBrokerLayout -RepoRoot $RepoRoot -ServicesRoot $ServicesRoot -LogsRoot $LogsRoot -DeploymentRoot $DeploymentRoot
$sc = Get-MYCSystemTool 'sc.exe'

try {
    $stateInfo = Read-MYCBrokerState -Layout $layout   # corrupt/foreign -> throws: fail closed
    $verdict = Get-MYCBrokerServiceVerdict -Layout $layout
    if ($verdict.Verdict -eq 'incompatible') {
        throw ('Existe un servicio {0} que NO corresponde a esta instalación ({1}); no se toca.' -f $ServiceId, ($verdict.Reasons -join ','))
    }
    if (-not $stateInfo.exists -and $verdict.Verdict -eq 'compatible') {
        throw 'Servicio compatible sin install-state.json: DEV-1C no puede demostrar que lo creó; no se adopta (inspección manual).'
    }
    if (-not $stateInfo.exists) {
        # No ledger: DEV-1C cannot prove it owns ANYTHING here -- not the SCM
        # entry, the ACEs, the logon right, the directories, nor a
        # DEVELOPER_BROKER_* block in backend\.env. Nothing is modified
        # (cleaning an orphan block is a separate, explicit manual action).
        Write-Host 'No existe install-state.json: no hay nada cuya propiedad DEV-1C pueda demostrar. No se modificó nada (tampoco backend\.env).'
        exit 0
    }
    $actions = $stateInfo.rollback
    $serviceSid = [string]$actions.service_sid
    if ($verdict.Verdict -eq 'compatible') {
        $resolved = Resolve-MYCBrokerServiceSid
        if ($serviceSid -and $serviceSid -ne $resolved) { throw 'El SID registrado no coincide con el del servicio existente; no se continúa.' }
        if (-not $serviceSid) {
            # Crash between sc.exe create and the SID record: nothing SID-based was granted yet.
            if (-not $WhatIfPreference) { Update-MYCBrokerState -Layout $layout -Arguments @('--service-sid', $resolved) | Out-Null }
            $serviceSid = $resolved
        }
    }
    if (-not $WhatIfPreference) {
        Update-MYCBrokerState -Layout $layout -Arguments @('--phase', 'uninstalling') | Out-Null
    }

    # 0-1. backend\.env is touched ONLY if the ledger records the block
    #      (pending|owned) AND its evidence proves the block present is
    #      exactly DEV-1C's (marker + fingerprint). An interrupted
    #      provisioning is restored from its journal first.
    if ($actions.backend_config -ne 'none' -and (Test-Path -LiteralPath $layout.EnvFile -PathType Leaf)) {
        if ($PSCmdlet.ShouldProcess($layout.StateDir, 'Recuperar un aprovisionamiento XML/.env interrumpido (si existe journal)')) {
            Invoke-MYCDeployTool -Layout $layout -Arguments @('provision-recover', '--journal-dir', $layout.StateDir, '--xml', $layout.ServiceXml, '--env-file', $layout.EnvFile) | Out-Null
        }
        $envAction = (Invoke-MYCDeployTool -Layout $layout -Arguments @('backend-config-action', '--file', $layout.StateFile, '--repo-root', $layout.RepoRoot, '--env-file', $layout.EnvFile)).action
        if ($envAction -eq 'record_none') {
            if ($PSCmdlet.ShouldProcess($layout.StateFile, 'Registrar que no existe bloque gestionado propio')) {
                Update-MYCBrokerState -Layout $layout -Arguments @('--backend-config', 'none') | Out-Null
            }
        } elseif ($envAction -eq 'refuse_manual') {
            Write-Warning 'backend\.env: el bloque gestionado presente no coincide con la evidencia de DEV-1C (marcador/huella); NO se modifica. Reconciliación manual.'
        } elseif ($RemoveBackendConfig) {
            if ($PSCmdlet.ShouldProcess($layout.EnvFile, 'Eliminar el bloque gestionado DEVELOPER_BROKER_*')) {
                Invoke-MYCDeployTool -Layout $layout -Arguments @('remove-backend-block', '--env-file', $layout.EnvFile) | Out-Null
                Update-MYCBrokerState -Layout $layout -Arguments @('--backend-config', 'none') | Out-Null
            }
        } elseif ($PSCmdlet.ShouldProcess($layout.EnvFile, 'DEVELOPER_BROKER_ENABLED=false')) {
            Invoke-MYCDeployTool -Layout $layout -Arguments @('set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'false') | Out-Null
        }
    } elseif ($actions.backend_config -eq 'none') {
        Write-Host 'backend\.env: el ledger no registra un bloque gestionado propio; no se modifica.'
    }

    # 2-3. Stop (bounded) and delete the service -- only if the ledger says
    #      'owned' or 'pending' AND the SCM, re-queried now, shows exactly our
    #      account, binary and type (verdict 'compatible'; 'incompatible' was
    #      refused above). A 'pending' service is never deleted on trust.
    if ($actions.delete_service) {
        # Fresh SCM query right here; the verdict from the start is not reused.
        $fresh = Get-MYCBrokerServiceVerdict -Layout $layout
        if ($fresh.Verdict -eq 'absent') {
            if ($PSCmdlet.ShouldProcess($layout.StateFile, 'Registrar que el servicio no existe')) {
                Update-MYCBrokerState -Layout $layout -Arguments @('--service', 'none') | Out-Null
            }
        } elseif ($PSCmdlet.ShouldProcess($ServiceId, 'Detener (máx. 45 s + 10 s) y eliminar el servicio')) {
            # Both go through the guard (fresh SCM + SID + ledger immediately before sc.exe).
            Stop-MYCBrokerService -Layout $layout
            Invoke-MYCGuardedScm -Layout $layout -Arguments @('delete', $ServiceId) | Out-Null
            if (-not (Wait-MYCServiceState -Name $ServiceId -State 'Deleted' -TimeoutSeconds $DeleteTimeoutSeconds)) {
                throw "El servicio quedó marcado para eliminación pero sigue registrado (handles abiertos). Cierre services.msc/consolas y reintente."
            }
            Update-MYCBrokerState -Layout $layout -Arguments @('--service', 'none') | Out-Null
        }
    }

    # 4. ACEs of the Broker SID: per recorded grant, from a fresh read of the
    #    ACL -- exact ACE -> revoked and verified; no explicit ACE -> record
    #    only; anything else -> refused for manual reconciliation (ACL untouched).
    foreach ($grant in @($actions.acl_grants)) {
        if (-not $PSCmdlet.ShouldProcess($grant.path, "Quitar la ACE exacta registrada del Broker ($($grant.grant), $($grant.status))")) { continue }
        $grantAction = Remove-MYCBrokerGrantExact -Layout $layout -Grant $grant
        if ($grantAction -eq 'refuse_manual') {
            Write-Warning "$($grant.path): la ACE del Broker no coincide exactamente con la registrada; no se toca (reconciliación manual)."
            continue
        }
        Set-MYCBrokerStateGrant -Layout $layout -Path $grant.path -Status remove
    }

    # 5. Logon right only if DEV-1C added it (pending/added in the ledger).
    if ($actions.revoke_logon_right) {
        if ($PSCmdlet.ShouldProcess('SeServiceLogonRight', "Revocar $serviceSid (agregado por DEV-1C)")) {
            Set-MYCServiceLogonRight -Layout $layout -ServiceSid $serviceSid -Action revoke | Out-Null
        }
    }

    # 6. Files: broker_deploy.py directory-uninstall-action decides per
    #    directory. 'pending' never authorises deletion (absent -> none;
    #    present -> kept for manual reconciliation); 'owned' is deleted only on
    #    request and after a fresh ownership proof.
    $retained = @()
    foreach ($item in @(
            @{ Path = $layout.ServiceDir; Kind = 'service_dir'; Flag = '--service-dir'; Remove = [bool]$RemoveServiceFiles; What = 'directorio del servicio (wrapper + XML con el secreto)' },
            @{ Path = $layout.LogDir; Kind = 'log_dir'; Flag = '--log-dir'; Remove = [bool]$RemoveLogs; What = 'logs del Broker' })) {
        $ownership = [string]$actions.($item.Kind)
        $exists = Test-Path -LiteralPath $item.Path
        $proofOk = $false
        if ($ownership -eq 'owned' -and $exists -and $item.Remove) {
            $proofOk = [bool](Test-MYCDirectoryProof -Layout $layout -Path $item.Path -Mode owned -Kind $item.Kind -ServiceSid $serviceSid).proven
        }
        $decision = (Invoke-MYCDeployTool -Layout $layout -Arguments @(
            'directory-uninstall-action', '--ownership', $ownership, '--exists', ([string]$exists).ToLower(),
            '--remove', ([string]$item.Remove).ToLower(), '--proof-ok', ([string]$proofOk).ToLower())).action
        switch ($decision) {
            'untouched' { if ($exists) { Write-Warning "$($item.Path) existe pero el ledger no lo registra como propio: no se toca." } }
            'record_none' { if (-not $WhatIfPreference) { Update-MYCBrokerState -Layout $layout -Arguments @($item.Flag, 'none') | Out-Null } }
            'keep_pending_manual' {
                $retained += $item.Path
                Write-Warning "$($item.Path) quedó 'pending' (creación no demostrada): no se elimina; requiere reconciliación manual."
            }
            'retain' { $retained += $item.Path }
            'refuse_unproven' {
                $retained += $item.Path
                Write-Warning "$($item.Path) no supera la prueba de propiedad: no se elimina."
            }
            'delete' {
                if ($PSCmdlet.ShouldProcess($item.Path, 'Eliminar ' + $item.What)) {
                    Remove-MYCOwnedTree -Layout $layout -Path $item.Path -Kind $item.Kind -ServiceSid $serviceSid
                    Update-MYCBrokerState -Layout $layout -Arguments @($item.Flag, 'none') | Out-Null
                }
            }
        }
    }
    if ($retained -contains $layout.ServiceDir -and (Test-Path -LiteralPath $layout.ServiceXml)) {
        Write-Warning "Se conserva $($layout.ServiceXml), que contiene el secreto HMAC (sólo SYSTEM/Administradores). Use -RemoveServiceFiles para eliminarlo."
    }

    # 7. The ledger is deleted only when it owns nothing. While owned
    #    directories are retained it stays as a tombstone (phase
    #    'uninstalled'), so a later install recognises them as DEV-1C's
    #    instead of refusing them as unknown pre-existing directories.
    if ($stateInfo.exists -and -not $WhatIfPreference -and $PSCmdlet.ShouldProcess($layout.StateFile, 'Cerrar el estado de instalación')) {
        $closed = Remove-MYCBrokerState -Layout $layout
        if ($closed.retained) {
            Write-Host ('install-state.json se conserva (fase uninstalled) porque se retienen artefactos propios: {0}' -f ($retained -join '; '))
        }
    }
} catch {
    Write-MYCFailure ('Desinstalación del Broker FALLÓ: ' + $_.Exception.Message)
    exit 1
}

# The rollback is complete here; a failed MYCBackend restart is an
# activation failure (exit 3), never an uncontrolled exception.
if ($RestartBackend -and $PSCmdlet.ShouldProcess($BackendServiceName, 'Reiniciar para aplicar DEVELOPER_BROKER_ENABLED=false')) {
    $restartError = $null
    try {
        Restart-Service -Name $BackendServiceName -ErrorAction Stop
    } catch {
        $restartError = $_.Exception.Message
    }
    if ($restartError -or -not (Wait-MYCServiceState -Name $BackendServiceName -State 'Running' -TimeoutSeconds 60)) {
        $backendState = (Get-MYCServiceInfo -Name $BackendServiceName).state
        Write-MYCFailure ((
            "Desinstalación del Broker: COMPLETADA. Activación: FALLÓ el reinicio de MYCBackend (estado actual: {0}{1}).`n" +
            "Recuperación: Start-Service MYCBackend y revise C:\MYC\Logs\backend (DEVELOPER_BROKER_ENABLED ya es false).") -f $backendState,
            $(if ($restartError) { '; ' + $restartError } else { '' }))
        exit 3
    }
}
if ($WhatIfPreference) {
    Write-Host 'Simulación de desinstalación de MYCDeveloperBroker completada (-WhatIf). No se ha desinstalado el Broker.'
} else {
    Write-Host 'MYCDeveloperBroker desinstalado. El endurecimiento de C:\MYC\Services se conserva (ver respaldo en acl-backups).'
}
exit 0
