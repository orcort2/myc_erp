#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
  DEV-1C: installs (or re-applies) the MYCDeveloperBroker Windows service.

.DESCRIPTION
  MYCBackend (LocalSystem, S-1-5-18) --Named Pipe + HMAC--> MYCDeveloperBroker
  (virtual account NT SERVICE\MYCDeveloperBroker). broker.health only.

  Order: preflight (read-only) -> ownership ledger (install-state.json,
  created BEFORE any mutation that needs rollback) -> optional hardening of
  C:\MYC\Services -> DEV-1C-owned directories -> WinSW wrapper copy -> SCM
  registration directly under the virtual account (demand start; ownership
  recorded before sc.exe create) -> Broker SID resolution (LSA + SCM, must
  agree; recorded) -> SeServiceLogonRight only if not already effective
  (ownership recorded as pending before secedit and added after verifying)
  -> minimal ACL grants (recorded before applying) -> journaled provisioning
  of XML + backend\.env (block written with DEVELOPER_BROKER_ENABLED=false)
  -> start + runtime validation -> automatic start -> backend block enabled
  -> ledger phase "installed". MYCBackend is restarted only with
  -RestartBackend. C:\MYC\Deployment and C:\MYC\Logs are only inspected.

  Fail-closed: any failure after the service exists stops it and leaves it
  on demand start; the backend block is only enabled after the Broker was
  validated. Rollback: Uninstall-MYCDeveloperBroker.ps1.

  The secret is never a parameter value: -SecretSource Generate creates it
  inside broker_deploy.py, Reuse keeps the one already present in BOTH
  configurations (in both cases it never enters PowerShell), Prompt reads it
  with Read-Host -AsSecureString and hands it over stdin. With Prompt the
  secret exists transiently as a plain .NET string in this process (to
  compare both prompts and to write it to stdin); it is never printed,
  logged or put on a command line.

  WinSW integrity (P0): the source binary lived in C:\MYC\Services while it
  was writable by Authenticated Users, so it is used only if its SHA-256
  equals -WinSWExpectedSha256, a hash obtained from a trusted provenance
  (official WinSW release checksum). An accompanying .exe.config is copied
  only with a matching -WinSWConfigExpectedSha256. Point -WinSWSource at a
  verified copy if the current one cannot be proven legitimate.

.EXAMPLE
  .\Install-MYCDeveloperBroker.ps1 -PreflightOnly -WinSWExpectedSha256 <SHA-256 del release oficial de WinSW>
.EXAMPLE
  .\Install-MYCDeveloperBroker.ps1 -SecretSource Generate -HardenServicesAcl -WinSWExpectedSha256 <SHA-256 del release oficial de WinSW>
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = 'C:\Users\SMM ADMIN\myc_erp',
    [string]$ServicesRoot = 'C:\MYC\Services',
    [string]$LogsRoot = 'C:\MYC\Logs',
    [string]$DeploymentRoot = 'C:\MYC\Deployment',
    [string]$WinSWSource = 'C:\MYC\Services\backend\MYCBackend.exe',
    [string]$WinSWExpectedSha256,
    [string]$WinSWConfigExpectedSha256,
    [string]$PipeName = 'MYCDeveloperBroker',
    [ValidateSet('Generate', 'Prompt', 'Reuse')][string]$SecretSource,
    [switch]$PreflightOnly,
    [switch]$HardenServicesAcl,
    [switch]$AllowUsersReadOnServices,
    [switch]$RestartBackend
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'MYCDeveloperBroker.psm1') -Force
Assert-MYCElevated

$layout = Get-MYCBrokerLayout -RepoRoot $RepoRoot -ServicesRoot $ServicesRoot -LogsRoot $LogsRoot -DeploymentRoot $DeploymentRoot

function Invoke-Preflight {
    $results = New-Object System.Collections.Generic.List[object]
    $add = { param($name, $status, $detail) $results.Add([pscustomobject]@{ Check = $name; Status = $status; Detail = "$detail" }) }
    $pf = { param($ok) if ($ok) { 'PASS' } else { 'FAIL' } }

    & $add 'elevated' 'PASS' 'Administrador'
    & $add 'windows' (& $pf ($env:OS -eq 'Windows_NT')) $env:OS
    & $add 'repo_exists' (& $pf (Test-Path -LiteralPath $layout.RepoRoot -PathType Container)) $layout.RepoRoot
    & $add 'git_checkout' (& $pf (Test-Path -LiteralPath (Join-Path $layout.RepoRoot '.git'))) '.git'
    $missing = @($RequiredBrokerFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $layout.RepoRoot $_) -PathType Leaf) })
    & $add 'required_files' (& $pf ($missing.Count -eq 0)) ($missing -join ', ')
    $deployDir = (Resolve-Path -LiteralPath $PSScriptRoot).Path.TrimEnd('\')
    $expectedDeployDir = (Join-Path $layout.RepoRoot 'deploy\windows\developer-broker').TrimEnd('\')
    & $add 'scripts_from_repo' (& $pf ($deployDir -ieq $expectedDeployDir)) $deployDir

    $pythonOk = Test-Path -LiteralPath $layout.Python -PathType Leaf
    & $add 'venv_python' (& $pf $pythonOk) $layout.Python
    $pythonHome = $null
    try { $pythonHome = Get-MYCPythonHome -Layout $layout } catch { $pythonHome = $null }
    & $add 'python_home' (& $pf ($pythonHome -and (Test-Path -LiteralPath $pythonHome -PathType Container))) $pythonHome
    if (-not $pythonOk) { return $results.ToArray() }

    $pywin32 = Invoke-MYCNativeResult -FilePath $layout.Python -ArgumentList @('-B', '-s', '-c', 'import pywintypes, win32api, win32event, win32file, win32pipe, win32security')
    & $add 'pywin32_imports' (& $pf ($pywin32.ExitCode -eq 0)) 'pywintypes win32api win32event win32file win32pipe win32security'
    $validation = $null
    try { $validation = Invoke-MYCDeployTool -Layout $layout -Arguments @('validate', '--pipe-name', $PipeName) } catch { $validation = $null }
    & $add 'broker_import_and_pipe_name' (& $pf ($null -ne $validation)) $PipeName

    $winswOk = $false
    $winswDetail = $WinSWSource
    if (Test-Path -LiteralPath $WinSWSource -PathType Leaf) {
        $version = (Get-Item -LiteralPath $WinSWSource).VersionInfo
        $winswOk = ("$($version.ProductName) $($version.FileDescription) $($version.OriginalFilename)" -match 'WinSW|Windows Service Wrapper')
        $winswDetail = '{0} {1}' -f $version.ProductName, $version.FileVersion
        # Metadata is informative only; integrity is the SHA-256 check below.
        $integrityDetail = 'SHA-256 coincide con -WinSWExpectedSha256'
        $integrityOk = $false
        try {
            Test-MYCWinSWIntegrity -Layout $layout -Source $WinSWSource -ExpectedSha256 $WinSWExpectedSha256 -ExpectedConfigSha256 $WinSWConfigExpectedSha256 | Out-Null
            $integrityOk = $true
        } catch {
            $integrityDetail = $_.Exception.Message + ' -- obtenga el SHA-256 de la versión oficial de WinSW (procedencia confiable) o use una copia verificada'
        }
        & $add 'winsw_integrity' (& $pf $integrityOk) $integrityDetail
        $signature = Get-AuthenticodeSignature -LiteralPath $WinSWSource
        & $add 'winsw_signature' $(if ([string]$signature.Status -eq 'Valid') { 'PASS' } else { 'WARN' }) ('Authenticode: {0} {1}' -f $signature.Status, $(if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { '' }))
    }
    & $add 'winsw_source' (& $pf $winswOk) $winswDetail

    $backend = Get-MYCServiceInfo -Name $BackendServiceName
    & $add 'backend_service_exists' (& $pf $backend.exists) $BackendServiceName
    & $add 'backend_runs_as_localsystem' (& $pf ($backend.start_name -eq 'LocalSystem')) $backend.start_name
    $resolvedLocalSystem = Get-MYCLocalSystemSid
    & $add 'client_sid_is_localsystem' (& $pf ($resolvedLocalSystem -eq $SystemSid)) $resolvedLocalSystem
    if ($backend.exists -and $backend.process_id -gt 0) {
        $owners = @(Get-MYCProcessTree -RootProcessId $backend.process_id | ForEach-Object { Get-MYCProcessOwnerSid -ProcessId $_ } | Sort-Object -Unique)
        & $add 'backend_process_identity' (& $pf (($owners.Count -eq 1) -and ($owners[0] -eq $SystemSid))) ($owners -join ',')
    } else {
        & $add 'backend_process_identity' 'WARN' 'MYCBackend no está en ejecución'
    }

    $verdict = Get-MYCBrokerServiceVerdict -Layout $layout
    & $add 'broker_service_state' (& $pf ($verdict.Verdict -ne 'incompatible')) ('{0} {1}' -f $verdict.Verdict, ($verdict.Reasons -join ','))
    & $add 'wrapper_path_without_spaces' (& $pf ($layout.Wrapper -notmatch '[\s"]')) $layout.Wrapper
    & $add 'services_root' (& $pf (Test-Path -LiteralPath $layout.ServicesRoot -PathType Container)) $layout.ServicesRoot
    & $add 'logs_root' (& $pf (Test-Path -LiteralPath $layout.LogsRoot -PathType Container)) $layout.LogsRoot

    $stateInfo = $null
    try { $stateInfo = Read-MYCBrokerState -Layout $layout } catch { $stateInfo = $null }
    & $add 'install_state' (& $pf ($null -ne $stateInfo)) $(if ($null -eq $stateInfo) { 'install-state.json corrupto o de otra instalación: no se confía en él' } elseif ($stateInfo.exists) { 'válido' } else { 'no existe (se creará)' })
    $ledger = $null
    if ($null -ne $stateInfo -and $stateInfo.exists) { $ledger = $stateInfo.state }
    # Service: compatible is a normal reinstall ONLY when the ledger says
    # 'owned'; 'pending' = partial install to reconcile with Uninstall;
    # 'none'/no ledger = not proven ours.
    if ($null -ne $stateInfo) {
        $decisionOk = $true
        $decisionDetail = ''
        try {
            $decisionDetail = (Invoke-MYCDeployTool -Layout $layout -Arguments @('service-install-decision', '--verdict', $verdict.Verdict, '--file', $layout.StateFile, '--repo-root', $layout.RepoRoot)).action
        } catch {
            $decisionOk = $false
            $decisionDetail = $_.Exception.Message
        }
        & $add 'broker_service_owned' (& $pf $decisionOk) $decisionDetail
    }
    # Owned directories: a pre-existing one is accepted only if the ledger
    # records it as DEV-1C's (e.g. retained by a previous uninstall).
    $serviceDirOwned = ($null -ne $ledger) -and ($ledger.owned.service_dir -eq 'owned')
    $logDirOwned = ($null -ne $ledger) -and ($ledger.owned.log_dir -eq 'owned')
    if (Test-Path -LiteralPath $layout.ServiceDir) {
        $unexpected = @(Get-MYCTreeEntries -Path $layout.ServiceDir | Where-Object { $AllowedServiceDirFiles -notcontains (Split-Path -Leaf $_.Path) -or $_.IsReparse } | ForEach-Object { $_.Path })
        & $add 'service_dir_contents' (& $pf ($serviceDirOwned -and $unexpected.Count -eq 0)) $(if (-not $serviceDirOwned) { 'preexistente y no registrado como propio en el ledger' } else { $unexpected -join ', ' })
    } else {
        & $add 'service_dir_contents' 'PASS' 'no existe (se creará)'
    }
    if (Test-Path -LiteralPath $layout.LogDir) {
        & $add 'log_dir_preexisting' (& $pf $logDirOwned) $(if ($logDirOwned) { 'registrado como propio en el ledger' } else { 'preexistente y no registrado como propio en el ledger' })
    }
    $registryEnv = $null
    $serviceKey = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceId"
    if (Test-Path -LiteralPath $serviceKey) { $registryEnv = (Get-ItemProperty -LiteralPath $serviceKey -Name Environment -ErrorAction SilentlyContinue) }
    & $add 'no_registry_service_environment' (& $pf ($null -eq $registryEnv)) $serviceKey

    $envInfo = $null
    try { $envInfo = Invoke-MYCDeployTool -Layout $layout -Arguments @('inspect-env', '--env-file', $layout.EnvFile) } catch { $envInfo = $null }
    & $add 'backend_env_safe' (& $pf ($null -ne $envInfo)) 'sin DEVELOPER_BROKER_* fuera del bloque gestionado'
    if ($null -ne $envInfo -and $envInfo.managed_block) {
        # A managed block is DEV-1C's only if the ledger's evidence proves this
        # exact block (marker + fingerprint), whatever the recorded state.
        $blockOwned = $false
        if ($null -ne $stateInfo -and $stateInfo.exists) {
            try {
                $blockOwned = [bool](Invoke-MYCDeployTool -Layout $layout -Arguments @('backend-config-action', '--file', $layout.StateFile, '--repo-root', $layout.RepoRoot, '--env-file', $layout.EnvFile)).proven
            } catch { $blockOwned = $false }
        }
        & $add 'backend_block_owned' (& $pf $blockOwned) $(if ($blockOwned) { 'bloque registrado como propio' } else { 'bloque gestionado presente sin propiedad demostrada en el ledger: no se sobrescribe' })
    }
    if (Test-Path -LiteralPath $layout.EnvFile -PathType Leaf) {
        $envAcl = @(Test-MYCAclPolicy -Layout $layout -Path @($layout.EnvFile) -Policy secret_file)
        & $add 'backend_env_acl' (& $pf ($envAcl.Count -eq 0)) ($envAcl -join '; ')
    }

    $secretDetail = $SecretSource
    $secretOk = $false
    if ($SecretSource -eq 'Generate') { $secretOk = $true }
    if ($SecretSource -eq 'Prompt') { $secretOk = [Environment]::UserInteractive }
    if ($SecretSource -eq 'Reuse') {
        $secretOk = ($null -ne $envInfo) -and $envInfo.secret_present -and (Test-Path -LiteralPath $layout.ServiceXml -PathType Leaf)
    }
    if (-not $SecretSource) { $secretDetail = 'falta -SecretSource Generate|Prompt|Reuse' }
    if ($PreflightOnly -and -not $SecretSource) {
        & $add 'secret_source' 'WARN' $secretDetail
    } else {
        & $add 'secret_source' (& $pf $secretOk) $secretDetail
    }

    $pipeInUse = Test-MYCPipePresent -PipeName $PipeName
    $brokerRunning = $verdict.Info.exists -and $verdict.Info.state -eq 'Running' -and $verdict.Verdict -eq 'compatible'
    & $add 'pipe_name_not_squatted' (& $pf ((-not $pipeInUse) -or $brokerRunning)) $PipeName

    if (Test-Path -LiteralPath $layout.ServicesRoot -PathType Container) {
        $violations = @(Test-MYCServicesAcl -Layout $layout -AllowUsersRead:$AllowUsersReadOnServices)
        if ($violations.Count -eq 0) {
            & $add 'services_acl' 'PASS' 'conforme'
        } elseif ($HardenServicesAcl) {
            & $add 'services_acl' 'WARN' ('se endurecerá (-HardenServicesAcl): ' + ($violations -join '; '))
        } else {
            & $add 'services_acl' 'FAIL' ('inseguro; use -HardenServicesAcl: ' + ($violations -join '; '))
        }
    }
    foreach ($parent in @($layout.LogsRoot, $layout.DeploymentRoot)) {
        if (Test-Path -LiteralPath $parent -PathType Container) {
            $v = @(Test-MYCAclPolicy -Layout $layout -Path @($parent) -Policy owned_parent)
            & $add ('parent_acl ' + $parent) (& $pf ($v.Count -eq 0)) $(if ($v.Count -eq 0) { 'sólo inspección' } else { $v -join '; ' })
        }
    }
    foreach ($context in @($layout.LogsRoot, (Split-Path -Parent $layout.ServicesRoot))) {
        if (Test-Path -LiteralPath $context -PathType Container) {
            $v = @(Test-MYCAclPolicy -Layout $layout -Path @($context) -Policy services_tree)
            if ($v.Count -gt 0) { & $add ('context_acl ' + $context) 'WARN' (($v -join '; ') + ' (fuera del alcance DEV-1C; revisar)') }
        }
    }
    foreach ($tool in @('sc.exe', 'icacls.exe', 'secedit.exe')) {
        $present = Test-Path -LiteralPath (Join-Path (Join-Path $env:SystemRoot 'System32') $tool) -PathType Leaf
        & $add ('tool ' + $tool) (& $pf $present) ''
    }
    return $results.ToArray()
}

Write-Host '== MYCDeveloperBroker: preflight (sólo lectura) =='
$preflight = @(Invoke-Preflight)
Write-MYCResults -Results $preflight
$failures = @($preflight | Where-Object { $_.Status -eq 'FAIL' })
if ($failures.Count -gt 0) {
    Write-MYCFailure ('Preflight falló ({0} verificaciones). No se modificó nada.' -f $failures.Count)
    exit 1
}
if ($PreflightOnly) {
    Write-Host 'Preflight correcto. -PreflightOnly: no se modificó nada.'
    exit 0
}

$secureSecret = $null
if ($SecretSource -eq 'Prompt') {
    $first = Read-Host -AsSecureString 'Secreto HMAC del Developer Broker'
    $second = Read-Host -AsSecureString 'Confirme el secreto'
    $a = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($first)
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($second)
    try {
        $same = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($a) -ceq [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($a)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
    }
    if (-not $same) { Write-MYCFailure 'Los secretos no coinciden. No se modificó nada.'; exit 1 }
    $secureSecret = $first
}

$verdict = Get-MYCBrokerServiceVerdict -Layout $layout
$serviceSid = $null
$scStarted = $false
$backendEnabledByThisRun = $false
$sc = Get-MYCSystemTool 'sc.exe'
try {
    # 0. Ownership ledger BEFORE any mutation that needs rollback. Only
    #    C:\MYC\Deployment\developer-broker is protected; its parent is inspected.
    Start-MYCBrokerState -Layout $layout | Out-Null

    # 1. C:\MYC\Services hardening (explicit, backed up as per-entry SDDL; a
    #    deliberate security fix, deliberately NOT part of the Broker rollback).
    if (@(Test-MYCServicesAcl -Layout $layout -AllowUsersRead:$AllowUsersReadOnServices).Count -gt 0) {
        $backup = Set-MYCServicesAclHardening -Layout $layout -AllowUsersRead:$AllowUsersReadOnServices
        Write-Host "C:\MYC\Services endurecido. ACL previa respaldada en: $backup"
    }

    # 2. DEV-1C-owned directories (SYSTEM + Administrators only for now).
    #    none -> pending -> (create, protect, read back, prove) -> owned.
    Assert-MYCSafeParent -Layout $layout -Path $layout.LogsRoot
    New-MYCOwnedDirectory -Layout $layout -Path $layout.ServiceDir -Kind service_dir
    New-MYCOwnedDirectory -Layout $layout -Path $layout.LogDir -Kind log_dir

    # 3. The SCM decision is re-evaluated against the ledger (create only if
    #    absent+none; reconfigure only if compatible+owned; anything else aborts).
    #    The SCM is queried AGAIN here: the preflight verdict is never reused.
    $verdict = Get-MYCBrokerServiceVerdict -Layout $layout
    $serviceAction = (Invoke-MYCDeployTool -Layout $layout -Arguments @('service-install-decision', '--verdict', $verdict.Verdict, '--file', $layout.StateFile, '--repo-root', $layout.RepoRoot)).action
    if ($serviceAction -eq 'reconfigure') {
        # Guarded stop: fresh SCM + SID + ledger check immediately before sc stop.
        Stop-MYCBrokerService -Layout $layout
    }

    # 4. WinSW wrapper: only a copy whose SHA-256 matches the trusted hash
    #    (re-checked on the source now and on the copied file after). No download.
    Test-MYCWinSWIntegrity -Layout $layout -Source $WinSWSource -ExpectedSha256 $WinSWExpectedSha256 -ExpectedConfigSha256 $WinSWConfigExpectedSha256 | Out-Null
    Copy-Item -LiteralPath $WinSWSource -Destination $layout.Wrapper -Force
    $winswConfig = "$WinSWSource.config"
    if (Test-Path -LiteralPath $winswConfig -PathType Leaf) {
        Copy-Item -LiteralPath $winswConfig -Destination $layout.WrapperConfig -Force
    } elseif (Test-Path -LiteralPath $layout.WrapperConfig -PathType Leaf) {
        Remove-Item -LiteralPath $layout.WrapperConfig -Force  # stale config from an older WinSW: never kept unverified
    }
    Test-MYCWinSWIntegrity -Layout $layout -Source $layout.Wrapper -ExpectedSha256 $WinSWExpectedSha256 -ExpectedConfigSha256 $WinSWConfigExpectedSha256 | Out-Null
    $winswHash = (Get-FileHash -LiteralPath $layout.Wrapper -Algorithm SHA256).Hash

    # 5. SCM registration directly under the virtual account (never LocalSystem).
    #    Ownership is recorded BEFORE sc.exe create: a crash in between leaves
    #    a record for a service that may not exist (harmless: uninstall only
    #    deletes a service whose identity and binary are ours).
    if ($serviceAction -eq 'create') {
        Update-MYCBrokerState -Layout $layout -Arguments @('--service', 'pending') | Out-Null
        $create = Invoke-MYCNativeResult -FilePath $sc -ArgumentList @('create', $ServiceId, 'binPath=', $layout.Wrapper, 'start=', 'demand', 'obj=', $ServiceAccount, 'DisplayName=', $ServiceDisplayName)
        $afterCreate = Get-MYCBrokerServiceVerdict -Layout $layout   # re-query the SCM: never trust the exit code alone
        $outcome = Invoke-MYCDeployTool -Layout $layout -Arguments @('service-create-outcome', '--exit-code', [string]$create.ExitCode, '--verdict', $afterCreate.Verdict)
        if ($outcome.service -ne 'pending') {
            Update-MYCBrokerState -Layout $layout -Arguments @('--service', [string]$outcome.service) | Out-Null
        }
        if (-not $outcome.ok) {
            throw ('sc.exe create (exit {0}): {1}; propiedad del servicio en el ledger: {2}{3}' -f $create.ExitCode, $outcome.reason, $outcome.service,
                $(if ($outcome.service -eq 'pending') { ' -- inspección manual requerida antes de desinstalar' } else { '' }))
        }
    } else {
        Invoke-MYCGuardedScm -Layout $layout -Arguments @('config', $ServiceId, 'start=', 'demand') | Out-Null
    }
    # Every mutation of the (now existing) service: fresh guard + single sc.exe call.
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('sidtype', $ServiceId, 'unrestricted') | Out-Null
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('description', $ServiceId, $ServiceDescription) | Out-Null
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('failure', $ServiceId, 'reset=', '3600', 'actions=', 'restart/10000/restart/30000/restart/60000') | Out-Null
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('failureflag', $ServiceId, '1') | Out-Null
    $registered = Get-MYCBrokerServiceVerdict -Layout $layout
    if ($registered.Verdict -ne 'compatible') { throw ('Registro SCM inesperado: ' + ($registered.Reasons -join ',')) }

    # 6. Broker SID: resolved, never invented; recorded (a different SID than
    #    the one already in the ledger aborts).
    $serviceSid = Resolve-MYCBrokerServiceSid
    Update-MYCBrokerState -Layout $layout -Arguments @('--service-sid', $serviceSid) | Out-Null
    Write-Host "SID del Broker (resuelto por LSA y SCM): $serviceSid"

    # 7. SeServiceLogonRight only if the effective policy does not cover it;
    #    the function persists its own ownership (pending -> added). A right
    #    that was already effective is never recorded as owned, and an
    #    ownership recorded by a previous run is kept.
    $logonStatus = Set-MYCServiceLogonRight -Layout $layout -ServiceSid $serviceSid -Action grant
    Write-Host "SeServiceLogonRight: $logonStatus"

    # 8. Minimal ACL grants (no Modify outside the Broker log directory).
    #    Per grant, never by intent: fresh check -> ledger 'pending' ->
    #    apply (/grant:r, or the owned directory's protected ACL) -> re-read
    #    and verify EXACTLY (SID, Allow, rights, inheritance, propagation)
    #    -> ledger 'owned'. An owned grant is re-applied only if still exact.
    $plan = @(Get-MYCBrokerAclPlan -Layout $layout -ServiceSid $serviceSid)
    $ownedDirs = @($layout.ServiceDir, $layout.LogDir)
    foreach ($grant in $plan) {
        $recorded = @((Read-MYCBrokerState -Layout $layout).state.owned.acl_grants | Where-Object { $_.path -ieq $grant.path })
        $isOwnedDir = $ownedDirs -icontains $grant.path
        if ($isOwnedDir) {
            # DEV-1C's own protected directory: fully normalized to base + exact grant.
            if ($recorded.Count -eq 0) { Set-MYCBrokerStateGrant -Layout $layout -Path $grant.path -Grant $grant.icacls_grant -Status pending }
            Set-MYCProtectedAcl -Path $grant.path -Grants @($grant.icacls_grant)
        } else {
            $decision = Get-MYCExternalGrantDecision -Layout $layout -Grant $grant   # fresh, right before recording
            if ($decision -eq 'apply' -and $recorded.Count -eq 0) {
                Set-MYCBrokerStateGrant -Layout $layout -Path $grant.path -Grant $grant.icacls_grant -Status pending
            }
            Grant-MYCBrokerAcl -Layout $layout -Grant $grant   # /grant:r + exact re-verification
        }
        Test-MYCGrantExact -Layout $layout -Grant $grant
        Set-MYCBrokerStateGrant -Layout $layout -Path $grant.path -Grant $grant.icacls_grant -Status owned
    }

    # 9. Secret + configuration (backend block written DISABLED).
    $mode = @{ Generate = 'generate'; Prompt = 'stdin'; Reuse = 'reuse' }[$SecretSource]
    $provisionArgs = @(
        'provision', '--template', $Template, '--xml-out', $layout.ServiceXml, '--env-file', $layout.EnvFile,
        '--pipe-name', $PipeName, '--client-sid', $SystemSid, '--service-sid', $serviceSid,
        '--python-exe', $layout.Python, '--working-dir', $layout.Backend, '--log-dir', $layout.LogDir,
        '--journal-dir', $layout.StateDir, '--state-file', $layout.StateFile, '--repo-root', $layout.RepoRoot, '--secret-mode', $mode)
    # backend\.env block ownership is handled by the tool itself: an existing
    # block must be PROVEN DEV-1C's (marker + fingerprint); the new block's
    # evidence is persisted ('pending', or 'owned' + fingerprint_next) BEFORE
    # the commit, re-read after it, and only then recorded 'owned'.
    if ($null -ne $secureSecret) {
        Invoke-MYCDeployTool -Layout $layout -Arguments $provisionArgs -SecretInput $secureSecret | Out-Null
    } else {
        Invoke-MYCDeployTool -Layout $layout -Arguments $provisionArgs | Out-Null
    }
    $secureSecret = $null
    $envCheck = Invoke-MYCDeployTool -Layout $layout -Arguments @('inspect-env', '--env-file', $layout.EnvFile)
    if (-not $envCheck.managed_block -or $envCheck.backend_enabled) { throw 'El bloque gestionado de backend\.env no quedó como se provisionó.' }
    if ([string](Read-MYCBrokerState -Layout $layout).state.owned.backend_config -ne 'owned') { throw 'El ledger no registra el bloque de backend\.env como propio tras aprovisionar.' }
    $violations = @(Test-MYCAclPolicy -Layout $layout -Path @($layout.ServiceDir) -Policy service_dir -ServiceSid $serviceSid)
    if ($violations.Count -gt 0) { throw ('ACL del directorio del servicio no conforme: ' + ($violations -join '; ')) }

    # 10. Start and validate before anything depends on it.
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('config', $ServiceId, 'start=', 'auto') | Out-Null
    Invoke-MYCGuardedScm -Layout $layout -Arguments @('start', $ServiceId) | Out-Null
    $scStarted = $true
    if (-not (Wait-MYCServiceState -Name $ServiceId -State 'Running' -TimeoutSeconds $StartTimeoutSeconds)) { throw 'El Broker no llegó a Running.' }
    $runtime = @(Test-MYCBrokerRuntime -Layout $layout -ServiceSid $serviceSid -PipeName $PipeName -AllowUsersRead:$AllowUsersReadOnServices)
    Write-Host '== Validación posterior a la instalación =='
    Write-MYCResults -Results $runtime
    $runtimeFailures = @($runtime | Where-Object { $_.Status -ne 'PASS' })
    if ($runtimeFailures.Count -gt 0) { throw ('Validación del Broker falló: ' + (($runtimeFailures | ForEach-Object { $_.Check }) -join ', ')) }

    # 11. Only now the ERP side is enabled.
    $backendEnabledByThisRun = $true   # set BEFORE the call: a failure inside it may already have written the file
    Invoke-MYCDeployTool -Layout $layout -Arguments @('set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'true') | Out-Null
    $verify = Invoke-MYCDeployTool -Layout $layout -Arguments @(
        'verify', '--xml', $layout.ServiceXml, '--env-file', $layout.EnvFile, '--pipe-name', $PipeName,
        '--client-sid', $SystemSid, '--service-sid', $serviceSid, '--python-exe', $layout.Python, '--working-dir', $layout.Backend)
    if (-not $verify.ok -or -not $verify.backend_enabled) { throw 'Configuración ERP/Broker inconsistente tras habilitar.' }

    Update-MYCBrokerState -Layout $layout -Arguments @('--phase', 'installed', '--winsw-sha256', $winswHash, '--backend-activation', 'pending_restart') | Out-Null
} catch {
    $message = $_.Exception.Message
    # 1. The ERP side first: if THIS run enabled it, disable it again before
    #    stopping the Broker. Never claim it is disabled unless verified.
    $backendNote = 'El backend NO fue habilitado por este intento.'
    if ($backendEnabledByThisRun) {
        try {
            Invoke-MYCDeployTool -Layout $layout -Arguments @('set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'false') | Out-Null
            $envState = Invoke-MYCDeployTool -Layout $layout -Arguments @('inspect-env', '--env-file', $layout.EnvFile)
            if ($envState.backend_enabled) { throw 'DEVELOPER_BROKER_ENABLED sigue en true' }
            $backendNote = 'Este intento había habilitado el backend; se revirtió y verificó DEVELOPER_BROKER_ENABLED=false.'
        } catch {
            $backendNote = ('ATENCIÓN: este intento habilitó el backend y NO se pudo revertir ({0}). backend\.env puede seguir con DEVELOPER_BROKER_ENABLED=true: corríjalo (Uninstall-MYCDeveloperBroker.ps1) ANTES de reiniciar MYCBackend.' -f $_.Exception.Message)
        }
    }
    # 2. Then the Broker: stopped and left on demand start -- ONLY if the
    #    guard proves, fresh, that it is ours (compatible, LSA SID == SCM SID,
    #    ledger service pending|owned, same SID as the ledger). This holds even
    #    when $serviceSid was never resolved in this run. Otherwise the SCM is
    #    not touched and manual reconciliation is requested.
    $current = Get-MYCServiceInfo -Name $ServiceId
    if ($current.exists) {
        try {
            Stop-MYCBrokerService -Layout $layout
            Invoke-MYCGuardedScm -Layout $layout -Arguments @('config', $ServiceId, 'start=', 'demand') | Out-Null
        } catch {
            Write-Warning ('No se modificó el servicio {0}: no pudo demostrarse que es de DEV-1C o falló la operación ({1}). Reconciliación manual.' -f $ServiceId, $_.Exception.Message)
        }
    }
    Write-MYCFailure ("Instalación del Broker FALLÓ: {0}`n{1}`nRevierta con Uninstall-MYCDeveloperBroker.ps1 (deshace sólo lo registrado en install-state.json)." -f $message, $backendNote)
    exit 1
}

# Activation is separate from deployment: the Broker is installed and
# validated at this point; a failed MYCBackend restart is an activation
# failure (exit 3, recorded in the ledger), never an uncontrolled exception.
if ($RestartBackend) {
    $restartError = $null
    try {
        Restart-Service -Name $BackendServiceName -ErrorAction Stop
    } catch {
        $restartError = $_.Exception.Message
    }
    $backendRunning = Wait-MYCServiceState -Name $BackendServiceName -State 'Running' -TimeoutSeconds 60
    if ($restartError -or -not $backendRunning) {
        try { Update-MYCBrokerState -Layout $layout -Arguments @('--backend-activation', 'restart_failed') | Out-Null } catch { }
        $backendState = (Get-MYCServiceInfo -Name $BackendServiceName).state
        Write-MYCFailure ((
            "Despliegue del Broker: INSTALADO y validado. Activación: FALLÓ el reinicio de MYCBackend (estado actual: {0}{1}).`n" +
            "Recuperación: 1) Start-Service MYCBackend y revise C:\MYC\Logs\backend; 2) si no arranca por la configuración del Broker, " +
            "Uninstall-MYCDeveloperBroker.ps1 (pone DEVELOPER_BROKER_ENABLED=false) y vuelva a iniciar MYCBackend.") -f $backendState,
            $(if ($restartError) { '; ' + $restartError } else { '' }))
        exit 3
    }
    try { Update-MYCBrokerState -Layout $layout -Arguments @('--backend-activation', 'restarted') | Out-Null } catch {
        Write-Warning ('MYCBackend reiniciado, pero no se pudo registrar la activación en el ledger: ' + $_.Exception.Message)
    }
    Write-Host 'MYCBackend reiniciado: el Broker queda habilitado para el ERP.'
} else {
    Write-Warning 'MYCBackend NO se reinició: el ERP usará el Broker tras su próximo reinicio (o vuelva a ejecutar con -RestartBackend).'
}
Write-Host 'MYCDeveloperBroker instalado y validado. Health end-to-end: GET /api/mobile/v1/developer/broker/health con DeveloperSession + developer.system.read.'
exit 0
