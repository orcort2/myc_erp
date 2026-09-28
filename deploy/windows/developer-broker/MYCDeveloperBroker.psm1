#Requires -Version 5.1
<#
.SYNOPSIS
  DEV-1C: shared functions of the MYCDeveloperBroker deployment scripts.

.DESCRIPTION
  Windows-facing half of the deployment: SCM, service identity/SID
  resolution, ACLs (icacls), SeServiceLogonRight (secedit), runtime checks.
  Every policy decision that can be tested off-Windows (ACL plan and ACL
  policy, service compatibility, secedit INF merge, WinSW XML rendering,
  managed backend\.env block, secret handling) lives in broker_deploy.py.

  Invariants:
  - the HMAC secret never passes through a command line, a log, the console
    or an exception message. It is NOT only ever a SecureString: with
    -SecretSource Prompt it is typed into SecureStrings, but PowerShell
    materializes it transiently as a plain .NET string (to compare the two
    prompts and to write it to broker_deploy.py's stdin); those strings live
    only in this process' memory until garbage collection. With Generate or
    Reuse the secret never enters PowerShell at all;
  - no SID is invented: the Broker SID is resolved on the host from two
    independent sources that must agree;
  - no download, no ntrights.exe, no wholesale local-policy overwrite;
  - every native command's exit code is checked;
  - DEV-1C only re-ACLs directories it owns (directory-plan "owned"); their
    parents (C:\MYC\Deployment, C:\MYC\Logs) are inspected, never modified,
    except creating a missing C:\MYC\Deployment without touching its ACL;
  - install-state.json is an ownership ledger written before the first
    mutation that needs rollback and updated after each one; uninstall
    undoes only what it records.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$script:ServiceId = 'MYCDeveloperBroker'
$script:ServiceAccount = 'NT SERVICE\MYCDeveloperBroker'
$script:ServiceDisplayName = 'MYC Developer Broker'
$script:ServiceDescription = 'MYC Developer Broker (Named Pipe + HMAC, broker.health only). Dedicated virtual account; never LocalSystem.'
$script:BackendServiceName = 'MYCBackend'
$script:SystemSid = 'S-1-5-18'
$script:AdministratorsSid = 'S-1-5-32-544'
$script:UsersSid = 'S-1-5-32-545'
$script:TrustedOwnerSids = @('S-1-5-18', 'S-1-5-32-544', 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
$script:VirtualAccountSidPattern = '^S-1-5-80-\d+-\d+-\d+-\d+-\d+$'
$script:Tool = Join-Path $PSScriptRoot 'broker_deploy.py'
$script:Template = Join-Path $PSScriptRoot 'MYCDeveloperBroker.xml.template'
$script:ListeningMarker = 'Developer Broker escuchando'
$script:StartTimeoutSeconds = 30
$script:ListeningTimeoutSeconds = 30
$script:StopTimeoutSeconds = 45
$script:KillWaitSeconds = 10
$script:DeleteTimeoutSeconds = 30
$script:RequiredBrokerFiles = @(
    'backend\app\__init__.py',
    'backend\app\developer_broker\__init__.py',
    'backend\app\developer_broker\client.py',
    'backend\app\developer_broker\framing.py',
    'backend\app\developer_broker\host.py',
    'backend\app\developer_broker\pipe_name.py',
    'backend\app\developer_broker\protocol.py',
    'backend\app\developer_broker\replay.py',
    'backend\app\developer_broker\server.py',
    'backend\app\developer_broker\transport.py',
    'backend\app\developer_broker\windows_pipe.py',
    'deploy\windows\developer-broker\broker_deploy.py',
    'deploy\windows\developer-broker\MYCDeveloperBroker.xml.template'
)
$script:AllowedServiceDirFiles = @('MYCDeveloperBroker.exe', 'MYCDeveloperBroker.exe.config', 'MYCDeveloperBroker.xml', '.MYCDeveloperBroker.xml.new')

function Get-MYCSystemTool {
    param([Parameter(Mandatory = $true)][string]$Name)
    $path = Join-Path (Join-Path $env:SystemRoot 'System32') $Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Herramienta del sistema ausente: $Name" }
    return $path
}

function Assert-MYCElevated {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'MYCDeveloperBroker: se requiere PowerShell elevado (Ejecutar como administrador). No se modificó nada.'
    }
}

function Get-MYCBrokerLayout {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$ServicesRoot,
        [Parameter(Mandatory = $true)][string]$LogsRoot,
        [Parameter(Mandatory = $true)][string]$DeploymentRoot
    )
    $backend = Join-Path $RepoRoot 'backend'
    $venv = Join-Path $RepoRoot 'venv'
    $serviceDir = Join-Path $ServicesRoot 'developer-broker'
    $stateDir = Join-Path $DeploymentRoot 'developer-broker'
    return [pscustomobject]@{
        RepoRoot      = $RepoRoot
        Backend       = $backend
        EnvFile       = Join-Path $backend '.env'
        Venv          = $venv
        Python        = Join-Path $venv 'Scripts\python.exe'
        PyVenvCfg     = Join-Path $venv 'pyvenv.cfg'
        ServicesRoot  = $ServicesRoot
        ServiceDir    = $serviceDir
        Wrapper       = Join-Path $serviceDir 'MYCDeveloperBroker.exe'
        WrapperConfig = Join-Path $serviceDir 'MYCDeveloperBroker.exe.config'
        ServiceXml    = Join-Path $serviceDir 'MYCDeveloperBroker.xml'
        LogsRoot      = $LogsRoot
        LogDir        = Join-Path $LogsRoot 'developer-broker'
        DeploymentRoot = $DeploymentRoot
        StateDir      = $stateDir
        StateFile     = Join-Path $stateDir 'install-state.json'
        AclBackupDir  = Join-Path $DeploymentRoot 'acl-backups'
    }
}

function Invoke-MYCNativeResult {
    <# Runs a native command with an explicit argument array and returns
       [pscustomobject]@{ Output; ExitCode } -- the exit code is captured here,
       immediately, so no caller depends on the global $LASTEXITCODE.
       NEVER pass secret material through this function. #>
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'  # PS 5.1: stderr of a native command must not become a terminating error
    try {
        $output = @(& $FilePath @ArgumentList 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    return [pscustomobject]@{ Output = $output; ExitCode = [int]$code }
}

function Invoke-MYCNative {
    <# Invoke-MYCNativeResult + exit-code check; returns the output lines. #>
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [int[]]$AllowedExitCodes = @(0)
    )
    $result = Invoke-MYCNativeResult -FilePath $FilePath -ArgumentList $ArgumentList
    if ($AllowedExitCodes -notcontains $result.ExitCode) {
        $summary = ($result.Output | Select-Object -First 5) -join ' | '
        throw ('{0} falló (exit {1}): {2}' -f (Split-Path -Leaf $FilePath), $result.ExitCode, $summary)
    }
    return $result.Output
}

function Invoke-MYCDeployTool {
    <# Runs broker_deploy.py with the venv interpreter and returns its JSON
       result. The optional secret goes through stdin only. stderr is
       discarded on purpose: nothing from the tool reaches the console except
       its JSON (fixed error codes, never values). #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Security.SecureString]$SecretInput,
        [switch]$AllowRefusal
    )
    $toolArgs = @('-B', '-s', $script:Tool) + $Arguments
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($null -ne $SecretInput) {
            $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretInput)
            try {
                $stdout = @([Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) | & $Layout.Python @toolArgs 2>$null)
            } finally {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
            }
        } else {
            $stdout = @(& $Layout.Python @toolArgs 2>$null)
        }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    $json = $stdout | Where-Object { "$_".Trim() } | Select-Object -Last 1
    $result = $null
    if ($json) { $result = "$json" | ConvertFrom-Json }
    if ($code -eq 0 -and $null -ne $result) { return $result }
    if ($code -eq 3 -and $null -ne $result) {
        if ($AllowRefusal) { return $result }
        throw ('broker_deploy.py {0} rechazó la operación: {1}' -f $Arguments[0], $result.error)
    }
    throw ('broker_deploy.py {0} falló (exit {1}); ejecútelo manualmente con el intérprete del venv para diagnosticar.' -f $Arguments[0], $code)
}

function New-MYCTempJsonFile {
    param([Parameter(Mandatory = $true)]$InputObject)
    # Non-secret data only (ACL snapshots, service metadata).
    $path = [IO.Path]::GetTempFileName()
    ConvertTo-Json -InputObject $InputObject -Depth 6 -Compress | Set-Content -LiteralPath $path -Encoding UTF8
    return $path
}

# --- identities --------------------------------------------------------------------

function Get-MYCServiceInfo {
    param([Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z][A-Za-z0-9]+$')][string]$Name)
    $service = Get-CimInstance -ClassName Win32_Service -Filter ("Name='{0}'" -f $Name)
    if ($null -eq $service) {
        return [pscustomobject]@{ exists = $false; start_name = ''; path_name = ''; service_type = ''; state = ''; start_mode = ''; process_id = 0 }
    }
    return [pscustomobject]@{
        exists       = $true
        start_name   = [string]$service.StartName
        path_name    = [string]$service.PathName
        service_type = [string]$service.ServiceType
        state        = [string]$service.State
        start_mode   = [string]$service.StartMode
        process_id   = [int]$service.ProcessId
    }
}

function Get-MYCBrokerServiceVerdict {
    param([Parameter(Mandatory = $true)]$Layout)
    $info = Get-MYCServiceInfo -Name $script:ServiceId
    $inputFile = New-MYCTempJsonFile -InputObject $info
    try {
        $verdict = Invoke-MYCDeployTool -Layout $Layout -Arguments @('service-verdict', '--input', $inputFile, '--expected-binary', $Layout.Wrapper)
    } finally {
        Remove-Item -LiteralPath $inputFile -Force -ErrorAction SilentlyContinue
    }
    return [pscustomobject]@{ Info = $info; Verdict = [string]$verdict.verdict; Reasons = @($verdict.reasons) }
}

function Resolve-MYCBrokerServiceSid {
    <# The Broker SID, resolved from the existing service by two independent
       Windows sources (LSA account translation and the SCM). Never computed,
       never hard-coded; a disagreement or a non-virtual-account SID aborts. #>
    $account = New-Object Security.Principal.NTAccount($script:ServiceAccount)
    $viaLsa = $account.Translate([Security.Principal.SecurityIdentifier]).Value
    $viaScm = $null
    foreach ($line in (Invoke-MYCNative -FilePath (Get-MYCSystemTool 'sc.exe') -ArgumentList @('showsid', $script:ServiceId))) {
        if ($line -match '(S-1-5-80(-\d+){5})') { $viaScm = $Matches[1] }
    }
    if (-not $viaScm -or $viaScm -ne $viaLsa) { throw 'SID del Broker no verificable: LSA y SCM no coinciden. No se continúa.' }
    if ($viaLsa -notmatch $script:VirtualAccountSidPattern) { throw 'SID del Broker no es de cuenta virtual de servicio (S-1-5-80-*). No se continúa.' }
    return $viaLsa
}

function Get-MYCBrokerServiceSids {
    <# Raw, non-throwing read of the Broker SID from LSA and from the SCM
       (the guard decides; nothing is assumed here). #>
    $lsa = $null
    $scm = $null
    try {
        $lsa = (New-Object Security.Principal.NTAccount($script:ServiceAccount)).Translate([Security.Principal.SecurityIdentifier]).Value
    } catch { $lsa = $null }
    $showsid = Invoke-MYCNativeResult -FilePath (Get-MYCSystemTool 'sc.exe') -ArgumentList @('showsid', $script:ServiceId)
    foreach ($line in $showsid.Output) {
        if ($line -match '(S-1-5-80(-\d+){5})') { $scm = $Matches[1] }
    }
    return [pscustomobject]@{ Lsa = $lsa; Scm = $scm }
}

function Assert-MYCBrokerServiceStillOurs {
    <# The ONE ownership gate for any mutation of an EXISTING
       MYCDeveloperBroker: a fresh SCM verdict (account, binary, type) plus
       the SID from LSA and from the SCM, judged by broker_deploy.py
       scm-guard against the ledger (service pending|owned, same SID).
       Returns the verified SID. Callers use it ONLY through
       Invoke-MYCGuardedScm / Stop-MYCBrokerService, with nothing else
       between this check and the sc.exe call. A script cannot make the check
       and sc.exe atomic; the window is reduced to the minimum. #>
    param([Parameter(Mandatory = $true)]$Layout, [string]$ExpectedSid)
    $fresh = Get-MYCBrokerServiceVerdict -Layout $Layout
    $sids = Get-MYCBrokerServiceSids
    $guard = Invoke-MYCDeployTool -Layout $Layout -Arguments @(
        'scm-guard', '--verdict', $fresh.Verdict, '--lsa-sid', [string]$sids.Lsa, '--scm-sid', [string]$sids.Scm,
        '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot)
    if ($ExpectedSid -and $guard.sid -ne $ExpectedSid) { throw 'El SID actual del servicio no coincide con el esperado; no se toca.' }
    return [string]$guard.sid
}

function Invoke-MYCGuardedScm {
    <# Every sc.exe mutation of the existing service (config, sidtype,
       description, failure, failureflag, start, stop, delete) goes through
       here: fresh guard IMMEDIATELY followed by the single sc.exe call. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string[]]$Arguments, [int[]]$AllowedExitCodes = @(0))
    if ($Arguments.Count -lt 2 -or $Arguments[1] -ne $script:ServiceId) { throw 'Mutación SCM guardada sólo sobre MYCDeveloperBroker.' }
    $sid = Assert-MYCBrokerServiceStillOurs -Layout $Layout
    Invoke-MYCNative -FilePath (Get-MYCSystemTool 'sc.exe') -ArgumentList $Arguments -AllowedExitCodes $AllowedExitCodes | Out-Null
    return $sid
}

function Get-MYCLocalSystemSid {
    $sid = New-Object Security.Principal.SecurityIdentifier([Security.Principal.WellKnownSidType]::LocalSystemSid, $null)
    return $sid.Value
}

function Get-MYCProcessOwnerSid {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $process = Get-CimInstance -ClassName Win32_Process -Filter ("ProcessId={0}" -f $ProcessId)
    if ($null -eq $process) { return $null }
    $owner = Invoke-CimMethod -InputObject $process -MethodName GetOwnerSid
    if ($owner.ReturnValue -ne 0) { return $null }
    return [string]$owner.Sid
}

function Get-MYCProcessTree {
    param([Parameter(Mandatory = $true)][int]$RootProcessId)
    $all = @(Get-CimInstance -ClassName Win32_Process)
    $tree = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootProcessId)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        if ($tree.Contains($current)) { continue }
        $tree.Add($current)
        foreach ($child in ($all | Where-Object { $_.ParentProcessId -eq $current -and $_.ProcessId -ne $current })) {
            $queue.Enqueue([int]$child.ProcessId)
        }
    }
    return $tree.ToArray()
}

# --- ACLs ------------------------------------------------------------------------------

function Get-MYCAclSnapshot {
    param([Parameter(Mandatory = $true)][string]$Path)
    $acl = Get-Acl -LiteralPath $Path
    $aces = @()
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        $aces += [pscustomobject]@{
            sid               = $rule.IdentityReference.Value
            rights            = [int64][int]$rule.FileSystemRights
            type              = [string]$rule.AccessControlType
            inherited         = [bool]$rule.IsInherited
            inheritance_flags = [int]$rule.InheritanceFlags
            propagation_flags = [int]$rule.PropagationFlags
        }
    }
    return [pscustomobject]@{
        path      = $Path
        owner_sid = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        protected = [bool]$acl.AreAccessRulesProtected
        aces      = @($aces)
    }
}

function Test-MYCAclPolicy {
    <# Returns the list of violations (empty == compliant). #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string[]]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('services_root', 'services_tree', 'service_dir', 'log_dir', 'secret_file', 'owned_parent')][string]$Policy,
        [string]$ServiceSid,
        [switch]$AllowUsersRead
    )
    $snapshots = @($Path | ForEach-Object { Get-MYCAclSnapshot -Path $_ })
    $inputFile = New-MYCTempJsonFile -InputObject $snapshots
    try {
        $arguments = @('evaluate-acl', '--input', $inputFile, '--policy', $Policy)
        if ($ServiceSid) { $arguments += @('--service-sid', $ServiceSid) }
        if ($AllowUsersRead) { $arguments += '--allow-users-read' }
        $result = Invoke-MYCDeployTool -Layout $Layout -Arguments $arguments
    } finally {
        Remove-Item -LiteralPath $inputFile -Force -ErrorAction SilentlyContinue
    }
    return @($result.violations)
}

function Get-MYCTreeEntries {
    <# Every descendant of $Path as {Path; IsReparse}, WITHOUT ever descending
       into a reparse point (Get-ChildItem -Recurse in PowerShell 5.1 follows
       junctions, so it is never used for DEV-1C trees). -Exclude skips a
       subtree entirely. #>
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Exclude)
    $entries = New-Object System.Collections.Generic.List[object]
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $entries.ToArray() }
    $excludePrefix = $null
    if ($Exclude) { $excludePrefix = $Exclude.TrimEnd('\') + '\' }
    $pending = New-Object 'System.Collections.Generic.Stack[System.IO.DirectoryInfo]'
    $pending.Push((New-Object IO.DirectoryInfo($Path)))
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($entry in $directory.EnumerateFileSystemInfos()) {
            if ($excludePrefix -and ($entry.FullName + '\').StartsWith($excludePrefix, [StringComparison]::OrdinalIgnoreCase)) { continue }
            $isReparse = [bool]($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)
            $entries.Add([pscustomobject]@{ Path = $entry.FullName; IsReparse = $isReparse })
            if (-not $isReparse -and $entry -is [IO.DirectoryInfo]) { $pending.Push($entry) }
        }
    }
    return $entries.ToArray()
}

function Get-MYCServicesTreePaths {
    <# Everything under the services root except the Broker's own directory
       (which has its own, stricter policy); inspection only, same safe walker. #>
    param([Parameter(Mandatory = $true)]$Layout)
    return @(Get-MYCTreeEntries -Path $Layout.ServicesRoot -Exclude $Layout.ServiceDir)
}

function Test-MYCServicesAcl {
    param([Parameter(Mandatory = $true)]$Layout, [switch]$AllowUsersRead)
    $violations = @(Test-MYCAclPolicy -Layout $Layout -Path @($Layout.ServicesRoot) -Policy services_root -AllowUsersRead:$AllowUsersRead)
    $tree = @(Get-MYCServicesTreePaths -Layout $Layout)
    $violations += @($tree | Where-Object { $_.IsReparse } | ForEach-Object { '{0}: reparse_point' -f $_.Path })
    $plain = @($tree | Where-Object { -not $_.IsReparse } | ForEach-Object { $_.Path })
    if ($plain.Count -gt 0) {
        $violations += @(Test-MYCAclPolicy -Layout $Layout -Path $plain -Policy services_tree -AllowUsersRead:$AllowUsersRead)
    }
    return $violations
}

function Test-MYCIsReparsePoint {
    param([Parameter(Mandatory = $true)][string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    return [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Assert-MYCNoRedirectedPath {
    <# $Path must be canonical and no existing component, from the drive root
       to $Path itself, may be a reparse point (junction, symlink, mount
       point): the path must be exactly the directory it names. #>
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    if ($full.TrimEnd('\') -ine $Path.TrimEnd('\')) { throw "Ruta no canónica; se aborta: $Path" }
    $current = $full
    while ($current) {
        if ((Test-Path -LiteralPath $current) -and (Test-MYCIsReparsePoint -Path $current)) {
            throw "Ruta redirigida (reparse point/junction/symlink) no permitida; se aborta: $current"
        }
        $parent = Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) { break }
        $current = $parent
    }
}

function Get-MYCDirectoryProofInput {
    <# Read-back of a DEV-1C directory for broker_deploy.py directory-proof:
       ACL snapshot, canonical form, reparse flag and (no-follow) entries. #>
    param([Parameter(Mandatory = $true)][string]$Path)
    $canonical = ([IO.Path]::GetFullPath($Path).TrimEnd('\') -ieq $Path.TrimEnd('\'))
    return [pscustomobject]@{
        snapshot   = Get-MYCAclSnapshot -Path $Path
        canonical  = $canonical
        is_reparse = (Test-MYCIsReparsePoint -Path $Path)
        entries    = @(Get-MYCTreeEntries -Path $Path | ForEach-Object { [pscustomobject]@{ path = $_.Path; is_reparse = $_.IsReparse } })
    }
}

function Test-MYCDirectoryProof {
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('creation', 'owned')][string]$Mode,
        [ValidateSet('service_dir', 'log_dir')][string]$Kind = 'service_dir',
        [string]$ServiceSid
    )
    $inputFile = New-MYCTempJsonFile -InputObject (Get-MYCDirectoryProofInput -Path $Path)
    try {
        $arguments = @('directory-proof', '--input', $inputFile, '--mode', $Mode, '--kind', $Kind)
        if ($ServiceSid) { $arguments += @('--service-sid', $ServiceSid) }
        return (Invoke-MYCDeployTool -Layout $Layout -Arguments $arguments)
    } finally {
        Remove-Item -LiteralPath $inputFile -Force -ErrorAction SilentlyContinue
    }
}

function Remove-MYCOwnedTree {
    <# Deletes a DEV-1C-owned directory only after a fresh ownership proof
       (protected ACL: only SYSTEM/Administrators can write). The deletion
       itself is broker_deploy.py remove-owned-tree: bottom-up, lstat
       re-check of every entry immediately before unlink/rmdir, never
       following a junction/symlink, non-recursive rmdir (fails if anything
       appeared). Never Remove-Item -Recurse. #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('service_dir', 'log_dir')][string]$Kind,
        [string]$ServiceSid
    )
    $owned = @(Get-MYCOwnedDirectories -Layout $Layout | ForEach-Object { $_.TrimEnd('\') })
    if ($owned -notcontains $Path.TrimEnd('\')) { throw "Eliminación fuera del alcance de propiedad de DEV-1C: $Path" }
    Assert-MYCNoRedirectedPath -Path $Path
    $proof = Test-MYCDirectoryProof -Layout $Layout -Path $Path -Mode owned -Kind $Kind -ServiceSid $ServiceSid
    if (-not $proof.proven) { throw ('No se elimina {0}: propiedad no demostrada ({1}).' -f $Path, (@($proof.violations) -join '; ')) }
    Invoke-MYCDeployTool -Layout $Layout -Arguments @(
        'remove-owned-tree', '--path', $Path, '--deployment-root', $Layout.DeploymentRoot,
        '--services-root', $Layout.ServicesRoot, '--logs-root', $Layout.LogsRoot) | Out-Null
}

function Remove-MYCUnexpectedExplicitAces {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string[]]$KeepSids)
    $snapshot = Get-MYCAclSnapshot -Path $Path
    $icacls = Get-MYCSystemTool 'icacls.exe'
    # Full normalization of a DEV-1C-protected directory: every explicit Deny
    # is removed (/remove:d; the policy has no Deny at all) and every explicit
    # Allow outside the expected set is removed (/remove:g). Inherited ACEs
    # are handled by /inheritance:r in the caller.
    $denied = @($snapshot.aces | Where-Object { -not $_.inherited -and $_.type -eq 'Deny' } | ForEach-Object { $_.sid } | Sort-Object -Unique)
    foreach ($sid in $denied) {
        Invoke-MYCNative -FilePath $icacls -ArgumentList @($Path, '/remove:d', ('*' + $sid)) | Out-Null
    }
    $unexpected = @($snapshot.aces | Where-Object { -not $_.inherited -and $_.type -eq 'Allow' -and $KeepSids -notcontains $_.sid } | ForEach-Object { $_.sid } | Sort-Object -Unique)
    foreach ($sid in $unexpected) {
        Invoke-MYCNative -FilePath $icacls -ArgumentList @($Path, '/remove:g', ('*' + $sid)) | Out-Null
    }
}

function Set-MYCProtectedAcl {
    <# Owner = Administrators; inheritance disabled; SYSTEM and Administrators
       full control; plus exactly $Grants; every other explicit ACE removed;
       descendants reset to inherit from $Path.

       Order matters (C:\MYC\Services was writable by Authenticated Users):
       1. the ROOT is closed first, without /T;
       2. then the tree is walked top-down, "lock then enumerate": each entry
          is re-checked as not being a reparse point, gets its owner and
          /reset individually (never /T), and a directory is enumerated only
          AFTER it has been reset, i.e. once it already inherits the closed
          ACL. Any reparse point aborts. The walk never follows a link.
       Windows itself propagates inheritable ACEs when a directory DACL
       changes; that propagation is the OS's, not a /T traversal of ours. #>
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$Grants = @(),
        [string[]]$ExcludeChildren = @()
    )
    Assert-MYCNoRedirectedPath -Path $Path
    $icacls = Get-MYCSystemTool 'icacls.exe'
    # 1. root, non-recursive
    Invoke-MYCNative -FilePath $icacls -ArgumentList @($Path, '/setowner', ('*' + $script:AdministratorsSid), '/C', '/Q') | Out-Null
    $grantArgs = @('/grant:r', ('*{0}:(OI)(CI)(F)' -f $script:SystemSid), ('*{0}:(OI)(CI)(F)' -f $script:AdministratorsSid)) + $Grants
    Invoke-MYCNative -FilePath $icacls -ArgumentList (@($Path, '/inheritance:r') + $grantArgs) | Out-Null
    $KeepSids = @($script:SystemSid, $script:AdministratorsSid)
    foreach ($grant in $Grants) {
        if ($grant -notmatch '^\*(S-1-[0-9-]+):') { throw "Concesión ACL mal formada: $grant" }
        $KeepSids += $Matches[1]
    }
    Remove-MYCUnexpectedExplicitAces -Path $Path -KeepSids $KeepSids
    if (Test-MYCIsReparsePoint -Path $Path) { throw "La raíz se convirtió en reparse point; se aborta: $Path" }
    # 2. lock then enumerate, top-down, no-follow
    $pending = New-Object 'System.Collections.Generic.Stack[string]'
    $pending.Push($Path)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($entry in (New-Object IO.DirectoryInfo($directory)).EnumerateFileSystemInfos()) {
            if ($directory -eq $Path -and $ExcludeChildren -contains $entry.Name) { continue }
            if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point en un árbol protegido; se aborta: $($entry.FullName)" }
            Invoke-MYCNative -FilePath $icacls -ArgumentList @($entry.FullName, '/setowner', ('*' + $script:AdministratorsSid), '/C', '/Q') | Out-Null
            Invoke-MYCNative -FilePath $icacls -ArgumentList @($entry.FullName, '/reset', '/C', '/Q') | Out-Null
            if (Test-MYCIsReparsePoint -Path $entry.FullName) { throw "Reparse point en un árbol protegido; se aborta: $($entry.FullName)" }
            if ($entry -is [IO.DirectoryInfo]) { $pending.Push($entry.FullName) }
        }
    }
}

function Get-MYCOwnedDirectories {
    <# Lifecycle-owned paths only; persistent backups never authorize deletion. #>
    param([Parameter(Mandatory = $true)]$Layout)
    $plan = Invoke-MYCDeployTool -Layout $Layout -Arguments @(
        'directory-plan', '--deployment-root', $Layout.DeploymentRoot, '--services-root', $Layout.ServicesRoot, '--logs-root', $Layout.LogsRoot)
    return @($plan.owned)
}

function Get-MYCProtectableDirectories {
    <# ACL protection authority only; MUST NOT be used to authorize deletion. #>
    param([Parameter(Mandatory = $true)]$Layout)
    $plan = Invoke-MYCDeployTool -Layout $Layout -Arguments @(
        'directory-plan', '--deployment-root', $Layout.DeploymentRoot, '--services-root', $Layout.ServicesRoot, '--logs-root', $Layout.LogsRoot)
    return @($plan.owned) + @($plan.persistent_protected)
}

function New-MYCProtectedDirectory {
    <# Creates (or re-protects) a lifecycle-owned or persistent-protected directory: owner
       Administrators, protected ACL, descendants reset. Refuses any path that
       is not in the protection plan (never a parent such as C:\MYC\Deployment)
       and a pre-existing directory with an untrusted owner unless -Adopt. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$Path, [string[]]$Grants = @(), [switch]$Adopt)
    $protectable = @(Get-MYCProtectableDirectories -Layout $Layout | ForEach-Object { $_.TrimEnd('\') })
    if ($protectable -notcontains $Path.TrimEnd('\')) {
        throw "Ruta fuera del alcance de protección de DEV-1C; no se modifica su ACL: $Path"
    }
    Assert-MYCNoRedirectedPath -Path $Path
    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Se esperaba un directorio: $Path" }
        $owner = (Get-MYCAclSnapshot -Path $Path).owner_sid
        if (-not $Adopt -and $script:TrustedOwnerSids -notcontains $owner) {
            throw "Directorio preexistente con propietario no confiable (posible pre-creación maliciosa): $Path"
        }
    } else {
        if (-not (Test-Path -LiteralPath (Split-Path -Parent $Path) -PathType Container)) { throw "Directorio padre inexistente: $Path" }
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
    Set-MYCProtectedAcl -Path $Path -Grants $Grants
}

function New-MYCOwnedDirectory {
    <# Service/log directory transaction (ledger none -> pending -> owned):
       an existing directory is accepted only if the ledger says 'owned' AND a
       fresh proof passes; otherwise: record 'pending', create it (New-Item
       fails if something appeared meanwhile), protect it, read it back and
       prove it (canonical, no reparse, owner Administrators, exact base ACL,
       EMPTY), and only then record 'owned'. A failure leaves 'pending',
       which never authorises deletion. #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet('service_dir', 'log_dir')][string]$Kind
    )
    $flag = @{ service_dir = '--service-dir'; log_dir = '--log-dir' }[$Kind]
    $ledger = (Read-MYCBrokerState -Layout $Layout).state
    $ownership = [string]$ledger.owned.$Kind
    if (Test-Path -LiteralPath $Path) {
        if ($ownership -ne 'owned') { throw "Directorio preexistente no demostrado como propio ($ownership): $Path" }
        $proof = Test-MYCDirectoryProof -Layout $Layout -Path $Path -Mode owned -Kind $Kind -ServiceSid ([string]$ledger.service_sid)
        if (-not $proof.proven) { throw ('Directorio propio alterado ({0}): {1}' -f (@($proof.violations) -join '; '), $Path) }
        # Reinstall: the ACL is NOT touched here. Re-protecting to the base
        # (SYSTEM/Administrators only) would drop the Broker's operational ACE
        # until the ACL step; that step normalizes it with the exact plan.
        return
    }
    Update-MYCBrokerState -Layout $Layout -Arguments @($flag, 'pending') | Out-Null
    Assert-MYCNoRedirectedPath -Path $Path
    New-Item -ItemType Directory -Path $Path | Out-Null   # throws if it appeared since the check
    Set-MYCProtectedAcl -Path $Path
    $proof = Test-MYCDirectoryProof -Layout $Layout -Path $Path -Mode creation -Kind $Kind
    if (-not $proof.proven) { throw ('No se puede demostrar que {0} fue creado por esta ejecución ({1}); queda pending.' -f $Path, (@($proof.violations) -join '; ')) }
    Update-MYCBrokerState -Layout $Layout -Arguments @($flag, 'owned') | Out-Null
}

function Assert-MYCSafeParent {
    <# Inspect-only: a parent of a DEV-1C directory must not let a
       non-administrative principal delete, rename or re-ACL our child. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$Path)
    $violations = @(Test-MYCAclPolicy -Layout $Layout -Path @($Path) -Policy owned_parent)
    if ($violations.Count -gt 0) { throw ('Directorio padre inseguro {0}: {1}' -f $Path, ($violations -join '; ')) }
}

function Initialize-MYCStateDirectory {
    <# C:\MYC\Deployment is only inspected (created plainly if missing, never
       re-ACLed); C:\MYC\Deployment\developer-broker is protected. #>
    param([Parameter(Mandatory = $true)]$Layout)
    if (-not (Test-Path -LiteralPath $Layout.DeploymentRoot)) {
        if (-not (Test-Path -LiteralPath (Split-Path -Parent $Layout.DeploymentRoot) -PathType Container)) {
            throw "Directorio padre inexistente: $($Layout.DeploymentRoot)"
        }
        New-Item -ItemType Directory -Path $Layout.DeploymentRoot | Out-Null
    }
    Assert-MYCSafeParent -Layout $Layout -Path $Layout.DeploymentRoot
    New-MYCProtectedDirectory -Layout $Layout -Path $Layout.StateDir
}

function Backup-MYCAcl {
    <# Pre-hardening ACL backup WITHOUT icacls /save /T: the root and every
       entry from the no-follow walker, each as {path, sddl}, in a JSON file
       inside the protected deployment ACL-backup directory (outside Broker state). A reparse point aborts before
       anything is changed. Restore: Restore-MYCServicesAcl.ps1 (explicit,
       never automatic). #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Label)
    Initialize-MYCStateDirectory -Layout $Layout
    New-MYCProtectedDirectory -Layout $Layout -Path $Layout.AclBackupDir
    Assert-MYCNoRedirectedPath -Path $Path
    # The Broker's own directory is never part of this backup (it is not
    # hardened here and Restore-MYCServicesAcl.ps1 refuses it).
    $entries = @(Get-MYCTreeEntries -Path $Path -Exclude $Layout.ServiceDir)
    $reparse = @($entries | Where-Object { $_.IsReparse })
    if ($reparse.Count -gt 0) { throw "Reparse point en el árbol a respaldar; se aborta: $($reparse[0].Path)" }
    $records = @([pscustomobject]@{ path = $Path; sddl = (Get-Acl -LiteralPath $Path).Sddl })
    foreach ($entry in $entries) {
        $records += [pscustomobject]@{ path = $entry.Path; sddl = (Get-Acl -LiteralPath $entry.Path).Sddl }
    }
    $file = Join-Path $Layout.AclBackupDir ('{0}-{1}.acl.json' -f $Label, (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))
    ConvertTo-Json -InputObject $records -Depth 4 | Set-Content -LiteralPath $file -Encoding UTF8
    return $file
}

function Set-MYCServicesAclHardening {
    <# C:\MYC\Services: SYSTEM and Administrators full control; Users
       read/execute only with -AllowUsersRead; Authenticated Users (and every
       other broad principal) removed. The previous ACLs are saved first as
       per-entry SDDL (Backup-MYCAcl) for a manual restore. The Broker's own directory
       is excluded (it gets its own protected ACL). #>
    param([Parameter(Mandatory = $true)]$Layout, [switch]$AllowUsersRead)
    $backup = Backup-MYCAcl -Layout $Layout -Path $Layout.ServicesRoot -Label 'services'
    $grants = @()
    if ($AllowUsersRead) { $grants += ('*{0}:(OI)(CI)(RX)' -f $script:UsersSid) }
    Set-MYCProtectedAcl -Path $Layout.ServicesRoot -Grants $grants -ExcludeChildren @('developer-broker')
    $violations = @(Test-MYCServicesAcl -Layout $Layout -AllowUsersRead:$AllowUsersRead)
    if ($violations.Count -gt 0) {
        throw ('El endurecimiento de {0} no quedó conforme: {1}. Respaldo: {2}' -f $Layout.ServicesRoot, ($violations -join '; '), $backup)
    }
    return $backup
}

function Grant-MYCBrokerAcl {
    <# /grant:r REPLACES any explicit grant of the Broker SID on that path by
       exactly the planned one (least privilege is normalized, never merged),
       then the resulting ACL is re-read and must match exactly. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)]$Grant)
    if (-not (Test-Path -LiteralPath $Grant.path)) { throw "Ruta del plan ACL inexistente: $($Grant.path)" }
    Assert-MYCNoRedirectedPath -Path $Grant.path
    Invoke-MYCNative -FilePath (Get-MYCSystemTool 'icacls.exe') -ArgumentList @($Grant.path, '/grant:r', $Grant.icacls_grant, '/C', '/Q') | Out-Null
    $snapshotFile = New-MYCTempJsonFile -InputObject (Get-MYCAclSnapshot -Path $Grant.path)
    try {
        Invoke-MYCDeployTool -Layout $Layout -Arguments @('external-grant-verify', '--snapshot', $snapshotFile, '--path', $Grant.path, '--grant', $Grant.icacls_grant) | Out-Null
    } finally {
        Remove-Item -LiteralPath $snapshotFile -Force -ErrorAction SilentlyContinue
    }
}

function Get-MYCExternalGrantDecision {
    <# FRESH decision for ONE grant on a path DEV-1C does not own (repo, venv,
       Python home), taken immediately before that grant is recorded/applied:
       'apply' (no explicit Broker ACE), 'reapply_owned' (the ledger owns it
       and it is still EXACT), 'reconcile_pending_exact' (pending + exact ACE:
       the result of our own /grant:r before a crash). A redirected path, a
       pre-existing ACE, drift or an ambiguous pending ACE throw. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)]$Grant)
    if (-not (Test-Path -LiteralPath $Grant.path)) { throw "Ruta del plan ACL inexistente: $($Grant.path)" }
    Assert-MYCNoRedirectedPath -Path $Grant.path
    $snapshotFile = New-MYCTempJsonFile -InputObject (Get-MYCAclSnapshot -Path $Grant.path)
    try {
        return [string](Invoke-MYCDeployTool -Layout $Layout -Arguments @(
            'external-grant-check', '--snapshot', $snapshotFile, '--path', $Grant.path, '--grant', $Grant.icacls_grant,
            '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot)).decision
    } finally {
        Remove-Item -LiteralPath $snapshotFile -Force -ErrorAction SilentlyContinue
    }
}

function Set-MYCBrokerStateGrant {
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$Path, [string]$Grant,
          [Parameter(Mandatory = $true)][ValidateSet('pending', 'owned', 'remove')][string]$Status)
    $arguments = @('--grant-path', $Path, '--grant-status', $Status)
    if ($Grant) { $arguments += @('--grant-value', $Grant) }
    Update-MYCBrokerState -Layout $Layout -Arguments $arguments | Out-Null
}

function Test-MYCGrantExact {
    <# Re-reads the ACL of $Grant.path: exactly one explicit Allow ACE of the
       Broker SID with the planned rights, inheritance and propagation. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)]$Grant)
    $snapshotFile = New-MYCTempJsonFile -InputObject (Get-MYCAclSnapshot -Path $Grant.path)
    try {
        Invoke-MYCDeployTool -Layout $Layout -Arguments @('external-grant-verify', '--snapshot', $snapshotFile, '--path', $Grant.path, '--grant', $Grant.icacls_grant) | Out-Null
    } finally {
        Remove-Item -LiteralPath $snapshotFile -Force -ErrorAction SilentlyContinue
    }
}

function Remove-MYCBrokerGrantExact {
    <# Uninstall of ONE recorded grant, from a fresh read of the path's ACL:
       'record_none' (no explicit Broker ACE: nothing to revoke), 'revoke'
       (exactly the recorded ACE: removed, then re-read to confirm no
       explicit Broker ACE remains) or 'refuse_manual' (anything else: the
       ACL is not touched). Never a broad revocation by SID merely because
       the path is in the ledger. Returns the decision. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)]$Grant)
    if (-not (Test-Path -LiteralPath $Grant.path)) { return 'record_none' }
    Assert-MYCNoRedirectedPath -Path $Grant.path
    $snapshotFile = New-MYCTempJsonFile -InputObject (Get-MYCAclSnapshot -Path $Grant.path)
    try {
        $decision = [string](Invoke-MYCDeployTool -Layout $Layout -Arguments @(
            'acl-grant-uninstall-action', '--snapshot', $snapshotFile, '--path', $Grant.path, '--grant', $Grant.grant, '--status', $Grant.status)).action
    } finally {
        Remove-Item -LiteralPath $snapshotFile -Force -ErrorAction SilentlyContinue
    }
    if ($decision -ne 'revoke') { return $decision }
    if ($Grant.grant -notmatch '^\*(S-1-5-80(-\d+){5}):') { throw 'Concesión registrada mal formada.' }
    # The ONLY explicit ACEs of this SID are exactly the recorded one, so this
    # removes nothing else; the result is re-read and verified.
    Invoke-MYCNative -FilePath (Get-MYCSystemTool 'icacls.exe') -ArgumentList @($Grant.path, '/remove:g', ('*' + $Matches[1]), '/C', '/Q') | Out-Null
    $afterFile = New-MYCTempJsonFile -InputObject (Get-MYCAclSnapshot -Path $Grant.path)
    try {
        Invoke-MYCDeployTool -Layout $Layout -Arguments @(
            'acl-grant-uninstall-action', '--snapshot', $afterFile, '--path', $Grant.path, '--grant', $Grant.grant, '--status', $Grant.status, '--after-revoke') | Out-Null
    } finally {
        Remove-Item -LiteralPath $afterFile -Force -ErrorAction SilentlyContinue
    }
    return 'revoke'
}

function Get-MYCPythonHome {
    param([Parameter(Mandatory = $true)]$Layout)
    foreach ($line in (Get-Content -LiteralPath $Layout.PyVenvCfg)) {
        if ($line -match '^\s*home\s*=\s*(.+?)\s*$') { return $Matches[1] }
    }
    throw 'pyvenv.cfg no declara home: no se puede determinar el runtime base de Python.'
}

function Get-MYCBrokerAclPlan {
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$ServiceSid)
    $plan = Invoke-MYCDeployTool -Layout $Layout -Arguments @(
        'acl-plan', '--repo-root', $Layout.RepoRoot, '--python-home', (Get-MYCPythonHome -Layout $Layout),
        '--service-dir', $Layout.ServiceDir, '--log-dir', $Layout.LogDir, '--service-sid', $ServiceSid)
    return @($plan.grants)
}

# --- SeServiceLogonRight (secedit; never ntrights, never a wholesale policy) --------

$script:LsaSource = @'
using System;
using System.Runtime.InteropServices;
using System.Security.Principal;

public static class MYCLsaRights
{
    [StructLayout(LayoutKind.Sequential)]
    private struct LSA_UNICODE_STRING { public ushort Length; public ushort MaximumLength; public IntPtr Buffer; }

    [StructLayout(LayoutKind.Sequential)]
    private struct LSA_OBJECT_ATTRIBUTES
    {
        public int Length; public IntPtr RootDirectory; public IntPtr ObjectName;
        public int Attributes; public IntPtr SecurityDescriptor; public IntPtr SecurityQualityOfService;
    }

    [DllImport("advapi32.dll")]
    private static extern uint LsaOpenPolicy(IntPtr systemName, ref LSA_OBJECT_ATTRIBUTES attributes, int access, out IntPtr policy);
    [DllImport("advapi32.dll")]
    private static extern uint LsaRemoveAccountRights(IntPtr policy, byte[] accountSid, bool allRights, LSA_UNICODE_STRING[] rights, int count);
    [DllImport("advapi32.dll")]
    private static extern uint LsaClose(IntPtr policy);
    [DllImport("advapi32.dll")]
    private static extern int LsaNtStatusToWinError(uint status);

    private const int POLICY_LOOKUP_NAMES = 0x00000800;
    private const int ERROR_FILE_NOT_FOUND = 2;

    // Removes ONE right from ONE account. Returns 0, or ERROR_FILE_NOT_FOUND
    // when the account holds no rights (already absent); other Win32 codes
    // are failures.
    public static int RemoveAccountRight(string sid, string right)
    {
        SecurityIdentifier identifier = new SecurityIdentifier(sid);
        byte[] sidBytes = new byte[identifier.BinaryLength];
        identifier.GetBinaryForm(sidBytes, 0);
        LSA_OBJECT_ATTRIBUTES attributes = new LSA_OBJECT_ATTRIBUTES();
        attributes.Length = Marshal.SizeOf(typeof(LSA_OBJECT_ATTRIBUTES));
        IntPtr policy = IntPtr.Zero;
        IntPtr buffer = IntPtr.Zero;
        uint status = LsaOpenPolicy(IntPtr.Zero, ref attributes, POLICY_LOOKUP_NAMES, out policy);
        if (status != 0) { return LsaNtStatusToWinError(status); }
        try
        {
            // Allocation happens INSIDE try: the policy handle is always closed.
            buffer = Marshal.StringToHGlobalUni(right);
            LSA_UNICODE_STRING[] rights = new LSA_UNICODE_STRING[1];
            rights[0].Buffer = buffer;
            rights[0].Length = (ushort)(right.Length * 2);
            rights[0].MaximumLength = (ushort)((right.Length + 1) * 2);
            status = LsaRemoveAccountRights(policy, sidBytes, false, rights, 1);
            return status == 0 ? 0 : LsaNtStatusToWinError(status);
        }
        finally
        {
            if (buffer != IntPtr.Zero) { Marshal.FreeHGlobal(buffer); }
            if (policy != IntPtr.Zero) { LsaClose(policy); }
        }
    }
}
'@

function Remove-MYCAccountRightViaLsa {
    <# Only for the case the Broker is the LAST member of SeServiceLogonRight
       (original state: right unassigned), which a one-line secedit INF cannot
       reliably express. Removes exactly this SID's SeServiceLogonRight via
       LsaRemoveAccountRights; nothing else in the local policy is touched. #>
    param([Parameter(Mandatory = $true)][string]$Sid)
    if ($Sid -notmatch $script:VirtualAccountSidPattern) { throw 'Revocación LSA rechazada: SID no es de cuenta virtual.' }
    if (-not ('MYCLsaRights' -as [type])) { Add-Type -TypeDefinition $script:LsaSource -Language CSharp }
    $code = [MYCLsaRights]::RemoveAccountRight($Sid, 'SeServiceLogonRight')
    if ($code -ne 0 -and $code -ne 2) { throw "LsaRemoveAccountRights falló (Win32 $code)." }
}

function Set-MYCServiceLogonRight {
    <# Grants or revokes SeServiceLogonRight for the Broker SID ONLY if the
       effective policy does not already cover it (directly or through
       NT SERVICE\ALL SERVICES). The INF applied contains a single line:
       SeServiceLogonRight with every existing member preserved.

       Ownership (install-state.json) is persisted around the change:
       grant: export proves the SID absent -> state 'pending' BEFORE secedit
       -> secedit + verified re-export -> state 'added'. A right that was
       already effective is never marked as owned. revoke: secedit + verified
       re-export -> state 'none'. Returns the resulting status. #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string]$ServiceSid,
        [Parameter(Mandatory = $true)][ValidateSet('grant', 'revoke')][string]$Action
    )
    $secedit = Get-MYCSystemTool 'secedit.exe'
    Initialize-MYCStateDirectory -Layout $Layout
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $export = Join-Path $Layout.StateDir "secedit-before-$Action-$stamp.inf"
    $inf = Join-Path $Layout.StateDir "secedit-$Action-$stamp.inf"
    $db = Join-Path $Layout.StateDir "secedit-$Action-$stamp.sdb"
    $log = Join-Path $Layout.StateDir "secedit-$Action-$stamp.log"
    $verify = Join-Path $Layout.StateDir "secedit-after-$Action-$stamp.inf"
    $unused = "$inf.unused"
    try {
        Invoke-MYCNative -FilePath $secedit -ArgumentList @('/export', '/mergedpolicy', '/cfg', $export, '/areas', 'USER_RIGHTS', '/quiet') | Out-Null
        $result = Invoke-MYCDeployTool -Layout $Layout -Arguments @('logon-right', '--export', $export, '--sid', $ServiceSid, '--out', $inf, '--action', $Action)
        $lastMember = ($Action -eq 'revoke') -and ([string]$result.status -eq 'revoke_last_member')
        if (-not $result.inf_written -and -not $lastMember) {
            if ($Action -eq 'revoke') { Update-MYCBrokerState -Layout $Layout -Arguments @('--logon-right', 'none') | Out-Null }
            return [string]$result.status
        }
        if ($Action -eq 'grant') { Update-MYCBrokerState -Layout $Layout -Arguments @('--logon-right', 'pending') | Out-Null }
        if ($lastMember) {
            # Restores the original "right unassigned" state instead of keeping
            # the privilege because the list would become empty.
            Remove-MYCAccountRightViaLsa -Sid $ServiceSid
        } else {
            Invoke-MYCNative -FilePath $secedit -ArgumentList @('/configure', '/db', $db, '/cfg', $inf, '/areas', 'USER_RIGHTS', '/log', $log, '/quiet') | Out-Null
        }
        Invoke-MYCNative -FilePath $secedit -ArgumentList @('/export', '/mergedpolicy', '/cfg', $verify, '/areas', 'USER_RIGHTS', '/quiet') | Out-Null
        $check = Invoke-MYCDeployTool -Layout $Layout -Arguments @('logon-right', '--export', $verify, '--sid', $ServiceSid, '--out', $unused, '--action', $Action)
        $expected = @{ grant = @('already_granted', 'granted_via_all_services'); revoke = @('not_present') }[$Action]
        if ($expected -notcontains [string]$check.status) { throw "SeServiceLogonRight no quedó en el estado esperado tras secedit ($Action)." }
        $final = @{ grant = 'added'; revoke = 'none' }[$Action]
        Update-MYCBrokerState -Layout $Layout -Arguments @('--logon-right', $final) | Out-Null
        return $final
    } finally {
        # Local-policy exports/templates/databases/logs never accumulate
        # (success or failure). They never contain the HMAC secret.
        foreach ($temporary in @($export, $inf, $db, $log, $verify, $unused)) {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    }
}

# --- WinSW integrity ------------------------------------------------------------------

function Test-MYCWinSWIntegrity {
    <# The WinSW binary (and its .exe.config, if any) is used only when its
       SHA-256 equals the hash the operator obtained from a trusted provenance
       (official WinSW release checksum). Metadata (ProductName...) proves
       nothing: C:\MYC\Services was writable by Authenticated Users. Returns
       the tool result; throws on any mismatch. #>
    param(
        [Parameter(Mandatory = $true)]$Layout,
        [Parameter(Mandatory = $true)][string]$Source,
        [string]$ExpectedSha256,
        [string]$ExpectedConfigSha256
    )
    $arguments = @('winsw-integrity', '--actual-sha256', (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash)
    if ($ExpectedSha256) { $arguments += @('--expected-sha256', $ExpectedSha256) }
    $config = "$Source.config"
    if (Test-Path -LiteralPath $config -PathType Leaf) {
        $arguments += @('--config-actual-sha256', (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash)
        if ($ExpectedConfigSha256) { $arguments += @('--config-expected-sha256', $ExpectedConfigSha256) }
    }
    return (Invoke-MYCDeployTool -Layout $Layout -Arguments $arguments)
}

# --- service lifecycle ----------------------------------------------------------------

function Wait-MYCServiceState {
    param([Parameter(Mandatory = $true)][string]$Name, [Parameter(Mandatory = $true)][string]$State, [Parameter(Mandatory = $true)][int]$TimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $info = Get-MYCServiceInfo -Name $Name
        if ($State -eq 'Deleted' -and -not $info.exists) { return $true }
        if ($info.exists -and $info.state -eq $State) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Stop-MYCBrokerService {
    <# Bounded stop through the guard: guarded SCM stop, wait
       StopTimeoutSeconds; if still running, a NEW guard and then terminate
       ONLY processes of the service tree owned by the verified Broker SID,
       wait KillWaitSeconds; otherwise fail. If the guard cannot prove the
       service is ours, nothing is stopped. #>
    param([Parameter(Mandatory = $true)]$Layout)
    $info = Get-MYCServiceInfo -Name $script:ServiceId
    if (-not $info.exists -or $info.state -eq 'Stopped') { return }
    Invoke-MYCGuardedScm -Layout $Layout -Arguments @('stop', $script:ServiceId) -AllowedExitCodes @(0, 1062) | Out-Null
    if (Wait-MYCServiceState -Name $script:ServiceId -State 'Stopped' -TimeoutSeconds $script:StopTimeoutSeconds) { return }
    $sid = Assert-MYCBrokerServiceStillOurs -Layout $Layout
    $info = Get-MYCServiceInfo -Name $script:ServiceId
    if ($info.process_id -gt 0) {
        foreach ($processId in (Get-MYCProcessTree -RootProcessId $info.process_id)) {
            if ((Get-MYCProcessOwnerSid -ProcessId $processId) -eq $sid) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }
    if (-not (Wait-MYCServiceState -Name $script:ServiceId -State 'Stopped' -TimeoutSeconds $script:KillWaitSeconds)) {
        throw "El servicio $($script:ServiceId) no se detuvo en el tiempo acotado."
    }
}

function Test-MYCPipePresent {
    param([Parameter(Mandatory = $true)][string]$PipeName)
    try {
        $wanted = '\\.\pipe\' + $PipeName
        return [bool]([IO.Directory]::GetFiles('\\.\pipe\') | Where-Object { $_ -ieq $wanted })
    } catch {
        return $false
    }
}

function Test-MYCPipeDeniesCurrentUser {
    <# The pipe DACL has exactly two ACEs (ERP LocalSystem + Broker). An
       elevated administrator must be refused at open: nothing is written. #>
    param([Parameter(Mandatory = $true)][string]$PipeName)
    $client = New-Object IO.Pipes.NamedPipeClientStream('.', $PipeName, [IO.Pipes.PipeDirection]::InOut)
    try {
        $client.Connect(2000)
        return $false
    } catch {
        $exception = $_.Exception
        while ($null -ne $exception) {
            if ($exception -is [UnauthorizedAccessException]) { return $true }
            $exception = $exception.InnerException
        }
        return $null
    } finally {
        $client.Dispose()
    }
}

function Test-MYCBrokerListening {
    param([Parameter(Mandatory = $true)]$Layout, [int]$TimeoutSeconds = $script:ListeningTimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $logs = @(Get-ChildItem -LiteralPath $Layout.LogDir -Filter '*.log' -File -ErrorAction SilentlyContinue)
        foreach ($log in $logs) {
            if (Select-String -LiteralPath $log.FullName -SimpleMatch $script:ListeningMarker -Quiet) { return $true }
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Test-MYCBrokerRuntime {
    <# Post-install validation. Returns check objects; never contacts the
       Broker protocol (that requires the ERP identity) and never reads the
       secret into PowerShell. #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string]$ServiceSid, [Parameter(Mandatory = $true)][string]$PipeName, [switch]$AllowUsersRead)
    $results = New-Object System.Collections.Generic.List[object]
    $add = { param($name, $ok, $detail) $results.Add([pscustomobject]@{ Check = $name; Status = $(if ($ok) { 'PASS' } else { 'FAIL' }); Detail = $detail }) }

    $info = Get-MYCServiceInfo -Name $script:ServiceId
    & $add 'broker_service_running' ($info.exists -and $info.state -eq 'Running') $info.state
    & $add 'broker_start_name' ($info.start_name -eq $script:ServiceAccount) $info.start_name
    & $add 'broker_start_mode_auto' ($info.start_mode -eq 'Auto') $info.start_mode
    $treeOk = $false
    $treeDetail = 'sin proceso'
    if ($info.process_id -gt 0) {
        $owners = @(Get-MYCProcessTree -RootProcessId $info.process_id | ForEach-Object { Get-MYCProcessOwnerSid -ProcessId $_ })
        $treeOk = ($owners.Count -ge 2) -and -not ($owners | Where-Object { $_ -ne $ServiceSid })
        $treeDetail = '{0} procesos; LocalSystem presente: {1}' -f $owners.Count, [bool]($owners -contains $script:SystemSid)
    }
    & $add 'broker_process_tree_identity' $treeOk $treeDetail
    & $add 'pipe_present' (Test-MYCPipePresent -PipeName $PipeName) $PipeName
    $denied = Test-MYCPipeDeniesCurrentUser -PipeName $PipeName
    & $add 'pipe_denies_administrator' ($denied -eq $true) $(if ($null -eq $denied) { 'no concluyente' } else { "$denied" })
    & $add 'broker_logged_listening' (Test-MYCBrokerListening -Layout $Layout) $script:ListeningMarker

    $scan = Invoke-MYCDeployTool -Layout $Layout -Arguments @('scan-for-secret', '--xml', $Layout.ServiceXml, '--dir', $Layout.LogDir)
    & $add 'secret_absent_from_logs' (-not $scan.secret_found) ('{0} archivos' -f $scan.files_scanned)
    $verify = Invoke-MYCDeployTool -Layout $Layout -AllowRefusal -Arguments @(
        'verify', '--xml', $Layout.ServiceXml, '--env-file', $Layout.EnvFile, '--pipe-name', $PipeName,
        '--client-sid', $script:SystemSid, '--service-sid', $ServiceSid, '--python-exe', $Layout.Python, '--working-dir', $Layout.Backend)
    $failed = @()
    if ($verify.PSObject.Properties.Name -contains 'checks') {
        $failed = @($verify.checks.PSObject.Properties | Where-Object { -not $_.Value } | ForEach-Object { $_.Name })
    }
    & $add 'configuration_consistent' ([bool]$verify.ok) ($failed -join ',')

    $backend = Get-MYCServiceInfo -Name $script:BackendServiceName
    & $add 'backend_still_localsystem' ($backend.start_name -eq 'LocalSystem') $backend.start_name
    $v = @(Test-MYCAclPolicy -Layout $Layout -Path @($Layout.ServiceDir) -Policy service_dir -ServiceSid $ServiceSid)
    & $add 'acl_service_dir' ($v.Count -eq 0) ($v -join '; ')
    $v = @(Test-MYCAclPolicy -Layout $Layout -Path @($Layout.LogDir) -Policy log_dir -ServiceSid $ServiceSid)
    & $add 'acl_log_dir' ($v.Count -eq 0) ($v -join '; ')
    $v = @(Test-MYCServicesAcl -Layout $Layout -AllowUsersRead:$AllowUsersRead)
    & $add 'acl_services_root' ($v.Count -eq 0) ($v -join '; ')
    $v = @(Test-MYCAclPolicy -Layout $Layout -Path @($Layout.EnvFile) -Policy secret_file)
    & $add 'acl_backend_env' ($v.Count -eq 0) ($v -join '; ')
    return $results.ToArray()
}

function Write-MYCFailure {
    <# Error line on stderr without a terminating error, so the calling
       script controls its exit code explicitly. #>
    param([Parameter(Mandatory = $true)][string]$Message)
    $Host.UI.WriteErrorLine($Message)
}

function Write-MYCResults {
    param([Parameter(Mandatory = $true)][object[]]$Results)
    $Results | Format-Table -AutoSize -Wrap | Out-String -Width 220 | Write-Host
}

# --- state ---------------------------------------------------------------------------------

function Read-MYCBrokerState {
    <# Validated ledger (schema, service, account, repo). Corrupt or foreign
       state throws: callers fail closed, nothing is guessed. #>
    param([Parameter(Mandatory = $true)]$Layout)
    return (Invoke-MYCDeployTool -Layout $Layout -Arguments @('state-show', '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot))
}

function Start-MYCBrokerState {
    <# Creates the ledger (or re-opens an existing one, keeping its
       ownership) before the first mutation that needs rollback. #>
    param([Parameter(Mandatory = $true)]$Layout)
    Initialize-MYCStateDirectory -Layout $Layout
    return (Invoke-MYCDeployTool -Layout $Layout -Arguments @('state-begin', '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot))
}

function Update-MYCBrokerState {
    <# Atomic, validated ledger transition (broker_deploy.py apply_state_update). #>
    param([Parameter(Mandatory = $true)]$Layout, [Parameter(Mandatory = $true)][string[]]$Arguments)
    return (Invoke-MYCDeployTool -Layout $Layout -Arguments (@('state-update', '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot) + $Arguments))
}

function Remove-MYCBrokerState {
    <# Refused by the tool while the ledger still owns any resource. #>
    param([Parameter(Mandatory = $true)]$Layout)
    return (Invoke-MYCDeployTool -Layout $Layout -Arguments @('state-delete', '--file', $Layout.StateFile, '--repo-root', $Layout.RepoRoot))
}

Export-ModuleMember -Function * -Variable ServiceId, ServiceAccount, ServiceDisplayName, ServiceDescription, BackendServiceName, SystemSid, VirtualAccountSidPattern, RequiredBrokerFiles, AllowedServiceDirFiles, StartTimeoutSeconds, StopTimeoutSeconds, DeleteTimeoutSeconds, Template
