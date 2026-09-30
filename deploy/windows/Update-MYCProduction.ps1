#Requires -Version 5.1
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [string]$ProjectPath = 'C:\Users\SMM ADMIN\myc_erp'
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

# ============================================================
# MYC PRODUCTION UPDATER
#
# Autoridades independientes:
#
# - Git HEAD: codigo presente en el worktree.
# - Deployment state: ultimo commit desplegado exitosamente.
# - Alembic: estado real del esquema PostgreSQL.
# - frontend/dist: artefacto real publicado.
#
# Un git pull NO equivale a un deployment.
# ============================================================

$BackendPath = Join-Path $ProjectPath 'backend'
$FrontendPath = Join-Path $ProjectPath 'frontend'

$Python = Join-Path $ProjectPath 'venv\Scripts\python.exe'
$Requirements = Join-Path $ProjectPath 'requirements.txt'

$FrontendPackageJson = Join-Path $FrontendPath 'package.json'
$FrontendPackageLock = Join-Path $FrontendPath 'package-lock.json'
$FrontendNodeModules = Join-Path $FrontendPath 'node_modules'

$FrontendDist = Join-Path $FrontendPath 'dist'
$FrontendNextDist = Join-Path $FrontendPath 'dist.__next'
$FrontendPreviousDist = Join-Path $FrontendPath 'dist.__previous'

$StateRoot = 'C:\MYC\state'
$DeploymentStatePath = Join-Path $StateRoot 'production-deployment.json'

$BackendService = 'MYCBackend'
$FrontendService = 'MYCFrontend'
$CloudflaredService = 'Cloudflared'
$WireGuardService = 'WireGuardTunnel$myc-vpn'
$DeveloperBrokerService = 'MYCDeveloperBroker'

$LocalBackendHealth = 'http://127.0.0.1:8000/api/health'
$LocalFrontendHealth = 'http://127.0.0.1:5173'
$PublicBackendHealth = 'https://api-erp.mycmetrology.com.mx/api/health'
$PublicFrontendHealth = 'https://erp.mycmetrology.com.mx/'

$ExpectedPublicApiHost = 'api-erp.mycmetrology.com.mx'

function Write-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '========================================'
    Write-Host $Title
    Write-Host '========================================'
}

function Write-Ok {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "OK  $Message"
}

function Write-Warn {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "WARN  $Message" -ForegroundColor Yellow
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [string[]]$Arguments = @(),

        [string]$WorkingDirectory
    )

    $PreviousLocation = Get-Location

    try {
        if ($WorkingDirectory) {
            Set-Location $WorkingDirectory
        }

        & $Executable @Arguments

        if ($LASTEXITCODE -ne 0) {
            throw (
                "Comando fallo con codigo {0}: {1} {2}" -f
                $LASTEXITCODE,
                $Executable,
                ($Arguments -join ' ')
            )
        }
    }
    finally {
        Set-Location $PreviousLocation
    }
}

function Get-GitOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $Output = @(& git @Arguments)

    if ($LASTEXITCODE -ne 0) {
        throw "Git fallo: git $($Arguments -join ' ')"
    }

    return $Output
}

function Test-GitCommitExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Commit
    )

    & git cat-file -e "$Commit^{commit}" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-GitAncestor {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Ancestor,

        [Parameter(Mandatory = $true)]
        [string]$Descendant
    )

    & git merge-base --is-ancestor $Ancestor $Descendant 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Get-ChangedFilesBetween {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OldCommit,

        [Parameter(Mandatory = $true)]
        [string]$NewCommit
    )

    if ($OldCommit -eq $NewCommit) {
        return @()
    }

    return @(
        Get-GitOutput -Arguments @(
            'diff',
            '--name-only',
            $OldCommit,
            $NewCommit
        )
    )
}

function Test-AnyPathChanged {
    param(
        [AllowEmptyCollection()]
        [string[]]$ChangedFiles = @(),

        [Parameter(Mandatory = $true)]
        [string[]]$Prefixes
    )

    if (-not $ChangedFiles -or $ChangedFiles.Count -eq 0) {
        return $false
    }

    foreach ($File in $ChangedFiles) {
        foreach ($Prefix in $Prefixes) {
            if (
                $File -eq $Prefix -or
                $File.StartsWith(
                    $Prefix,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            ) {
                return $true
            }
        }
    }

    return $false
}

function Test-ExactPathChanged {
    param(
        [AllowEmptyCollection()]
        [string[]]$ChangedFiles = @(),

        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    foreach ($File in $ChangedFiles) {
        foreach ($Path in $Paths) {
            if ($File -eq $Path) {
                return $true
            }
        }
    }

    return $false
}

function Read-DeploymentState {
    if (-not (Test-Path $DeploymentStatePath)) {
        return $null
    }

    try {
        $Raw = Get-Content `
            -Path $DeploymentStatePath `
            -Raw `
            -Encoding UTF8

        if ([string]::IsNullOrWhiteSpace($Raw)) {
            throw 'El archivo esta vacio.'
        }

        $State = $Raw | ConvertFrom-Json

        if (
            -not $State.deployed_commit -or
            [string]::IsNullOrWhiteSpace(
                [string]$State.deployed_commit
            )
        ) {
            throw 'deployed_commit no existe.'
        }

        return $State
    }
    catch {
        throw (
            "El deployment state es invalido: {0}. {1}" -f
            $DeploymentStatePath,
            $_.Exception.Message
        )
    }
}

function Write-DeploymentState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Commit,

        [string[]]$AlembicHeads = @()
    )

    if (-not (Test-Path $StateRoot)) {
        New-Item `
            -ItemType Directory `
            -Path $StateRoot `
            -Force |
            Out-Null
    }

    $State = [ordered]@{
        schema_version = 1
        deployed_commit = $Commit
        deployed_at = (
            Get-Date
        ).ToUniversalTime().ToString('o')
        alembic_heads = @($AlembicHeads)
        frontend_build_mode = 'tunnel'
        frontend_api_host = $ExpectedPublicApiHost
    }

    $Json = $State | ConvertTo-Json -Depth 5

    $TempPath = Join-Path `
        $StateRoot `
        ("production-deployment.{0}.tmp" -f [Guid]::NewGuid())

    $BackupPath = Join-Path `
        $StateRoot `
        'production-deployment.previous.json'

    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    try {
        [System.IO.File]::WriteAllText(
            $TempPath,
            $Json,
            $Utf8NoBom
        )

        if (Test-Path $DeploymentStatePath) {
            [System.IO.File]::Replace(
                $TempPath,
                $DeploymentStatePath,
                $BackupPath,
                $true
            )

            if (Test-Path $BackupPath) {
                Remove-Item `
                    -Path $BackupPath `
                    -Force
            }
        }
        else {
            Move-Item `
                -Path $TempPath `
                -Destination $DeploymentStatePath `
                -Force
        }
    }
    finally {
        if (Test-Path $TempPath) {
            Remove-Item `
                -Path $TempPath `
                -Force
        }
    }

    Write-Ok "deployment state actualizado: $Commit"
}

function Get-AlembicRevisions {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('current', 'heads')]
        [string]$Command
    )

    $StartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $StartInfo.FileName = $Python
    $StartInfo.WorkingDirectory = $BackendPath
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.Arguments = (
        '-m alembic {0}' -f $Command
    )

    $Process = New-Object System.Diagnostics.Process
    $Process.StartInfo = $StartInfo

    try {
        if (-not $Process.Start()) {
            throw "No se pudo iniciar alembic $Command."
        }

        $StdOut = $Process.StandardOutput.ReadToEnd()
        $StdErr = $Process.StandardError.ReadToEnd()

        $Process.WaitForExit()
        $ExitCode = $Process.ExitCode
    }
    finally {
        $Process.Dispose()
    }

    $Output = @()

    if (-not [string]::IsNullOrWhiteSpace($StdOut)) {
        $Output += @(
            $StdOut -split "\r?\n" |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                }
        )
    }

    if (-not [string]::IsNullOrWhiteSpace($StdErr)) {
        $Output += @(
            $StdErr -split "\r?\n" |
                Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                }
        )
    }

    if ($ExitCode -ne 0) {
        $Output | ForEach-Object {
            Write-Host $_
        }

        throw (
            "alembic $Command fallo con codigo $ExitCode."
        )
    }

    $Revisions = @(
        $Output |
            ForEach-Object {
                $Line = [string]$_

                if (
                    $Line -match '^\s*([0-9a-fA-F]+)(?:\s|\(|$)'
                ) {
                    $Matches[1].ToLowerInvariant()
                }
            } |
            Where-Object { $_ } |
            Sort-Object -Unique
    )

    return [pscustomobject]@{
        Output = @($Output)
        Revisions = @($Revisions)
    }
}

function Test-AlembicAligned {
    param(
        [Parameter(Mandatory = $true)]
        $Current,

        [Parameter(Mandatory = $true)]
        $Heads
    )

    if ($Heads.Revisions.Count -eq 0) {
        throw 'No se pudo determinar Alembic heads.'
    }

    if (
        $Current.Revisions.Count -ne
        $Heads.Revisions.Count
    ) {
        return $false
    }

    foreach ($Head in $Heads.Revisions) {
        if ($Current.Revisions -notcontains $Head) {
            return $false
        }
    }

    return $true
}

function Sync-AlembicToHead {
    Write-Host 'Consultando estado real de Alembic...'

    $Current = Get-AlembicRevisions -Command 'current'
    $Heads = Get-AlembicRevisions -Command 'heads'

    Write-Host ''
    Write-Host 'Alembic current:'

    $Current.Output | ForEach-Object {
        Write-Host $_
    }

    Write-Host ''
    Write-Host 'Alembic heads:'

    $Heads.Output | ForEach-Object {
        Write-Host $_
    }

    $WasMigrated = $false

    if (
        -not (
            Test-AlembicAligned `
                -Current $Current `
                -Heads $Heads
        )
    ) {
        Write-Warn (
            'Alembic no esta en head. ' +
            'Ejecutando upgrade head...'
        )

        Invoke-External `
            -Executable $Python `
            -Arguments @(
                '-m',
                'alembic',
                'upgrade',
                'head'
            ) `
            -WorkingDirectory $BackendPath

        $WasMigrated = $true

        $Current = Get-AlembicRevisions -Command 'current'
        $Heads = Get-AlembicRevisions -Command 'heads'

        if (
            -not (
                Test-AlembicAligned `
                    -Current $Current `
                    -Heads $Heads
            )
        ) {
            throw (
                'Alembic sigue desalineado despues de ' +
                'upgrade head.'
            )
        }
    }

    Write-Ok 'Alembic alineado con head.'

    return [pscustomobject]@{
        Migrated = $WasMigrated
        Current = @($Current.Revisions)
        Heads = @($Heads.Revisions)
    }
}

function Get-FrontendTextFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DistPath
    )

    if (-not (Test-Path $DistPath)) {
        return @()
    }

    return @(
        Get-ChildItem `
            -Path $DistPath `
            -Recurse `
            -File `
            -ErrorAction Stop |
            Where-Object {
                $_.Extension -in @(
                    '.js',
                    '.mjs',
                    '.cjs',
                    '.html',
                    '.css',
                    '.json',
                    '.map'
                )
            }
    )
}

function Test-FrontendBundle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DistPath,

        [switch]$ThrowOnFailure
    )

    if (-not (Test-Path $DistPath)) {
        if ($ThrowOnFailure) {
            throw "No existe frontend dist: $DistPath"
        }

        return $false
    }

    $Files = Get-FrontendTextFiles `
        -DistPath $DistPath

    if ($Files.Count -eq 0) {
        if ($ThrowOnFailure) {
            throw (
                'El build frontend no contiene assets de ' +
                'texto verificables.'
            )
        }

        return $false
    }

    $ForbiddenPatterns = @(
        '127\.0\.0\.1:8000',
        'localhost:8000'
    )

    foreach ($File in $Files) {
        $Content = Get-Content `
            -Path $File.FullName `
            -Raw `
            -ErrorAction Stop

        foreach ($Pattern in $ForbiddenPatterns) {
            if ($Content -match $Pattern) {
                if ($ThrowOnFailure) {
                    throw (
                        'El bundle frontend contiene una API ' +
                        'localhost y no es apto para produccion. ' +
                        "Archivo: $($File.FullName)"
                    )
                }

                return $false
            }
        }
    }

    $ExpectedPattern = [regex]::Escape(
        $ExpectedPublicApiHost
    )

    $PublicApiFound = $false

    foreach ($File in $Files) {
        $Content = Get-Content `
            -Path $File.FullName `
            -Raw `
            -ErrorAction Stop

        if ($Content -match $ExpectedPattern) {
            $PublicApiFound = $true
            break
        }
    }

    if (-not $PublicApiFound) {
        if ($ThrowOnFailure) {
            throw (
                'El bundle frontend no contiene la API publica ' +
                "esperada: $ExpectedPublicApiHost"
            )
        }

        return $false
    }

    return $true
}

function Build-FrontendProduction {
    Write-Host (
        'Construyendo frontend en modo tunnel/produccion...'
    )

    if (Test-Path $FrontendNextDist) {
        Remove-Item `
            -Path $FrontendNextDist `
            -Recurse `
            -Force
    }

    if (Test-Path $FrontendPreviousDist) {
        Remove-Item `
            -Path $FrontendPreviousDist `
            -Recurse `
            -Force
    }

    try {
        Invoke-External `
            -Executable 'npm.cmd' `
            -Arguments @(
                'run',
                'build:tunnel',
                '--',
                '--outDir',
                'dist.__next',
                '--emptyOutDir'
            ) `
            -WorkingDirectory $FrontendPath

        if (-not (Test-Path $FrontendNextDist)) {
            throw (
                'npm run build:tunnel termino sin crear ' +
                'dist.__next.'
            )
        }

        $null = Test-FrontendBundle `
            -DistPath $FrontendNextDist `
            -ThrowOnFailure

        Write-Ok (
            'bundle frontend candidato validado: ' +
            'API publica correcta y sin localhost.'
        )

        if (Test-Path $FrontendDist) {
            Move-Item `
                -Path $FrontendDist `
                -Destination $FrontendPreviousDist
        }

        try {
            Move-Item `
                -Path $FrontendNextDist `
                -Destination $FrontendDist
        }
        catch {
            if (
                -not (Test-Path $FrontendDist) -and
                (Test-Path $FrontendPreviousDist)
            ) {
                Move-Item `
                    -Path $FrontendPreviousDist `
                    -Destination $FrontendDist
            }

            throw
        }

        Write-Ok (
            'nuevo frontend publicado en dist; ' +
            'rollback temporal preservado.'
        )
    }
    catch {
        if (Test-Path $FrontendNextDist) {
            Remove-Item `
                -Path $FrontendNextDist `
                -Recurse `
                -Force
        }

        throw
    }
}

function Test-ServiceInstalled {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return (
        $null -ne (
            Get-Service `
                -Name $Name `
                -ErrorAction SilentlyContinue
        )
    )
}

function Wait-ServiceState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [ValidateSet('Running', 'Stopped')]
        [string]$ExpectedStatus,

        [int]$TimeoutSeconds = 30
    )

    $Deadline = (
        Get-Date
    ).AddSeconds($TimeoutSeconds)

    do {
        $Service = Get-Service `
            -Name $Name `
            -ErrorAction Stop

        if (
            $Service.Status.ToString() -eq
            $ExpectedStatus
        ) {
            return
        }

        Start-Sleep -Seconds 1
    }
    while ((Get-Date) -lt $Deadline)

    throw (
        "El servicio '$Name' no alcanzo '$ExpectedStatus' " +
        "en $TimeoutSeconds segundos."
    )
}

function Restart-MYCService {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-ServiceInstalled -Name $Name)) {
        throw "El servicio '$Name' no esta instalado."
    }

    Write-Host "Reiniciando $Name..."

    Restart-Service `
        -Name $Name `
        -Force `
        -ErrorAction Stop

    Wait-ServiceState `
        -Name $Name `
        -ExpectedStatus 'Running'

    Write-Ok "$Name -> Running"
}

function Assert-ServiceRunning {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $Service = Get-Service `
        -Name $Name `
        -ErrorAction Stop

    if ($Service.Status -ne 'Running') {
        throw (
            "El servicio '$Name' no esta Running. " +
            "Estado: $($Service.Status)"
        )
    }

    Write-Ok "$Name -> Running"
}

function Wait-HttpSuccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$Attempts = 15,

        [int]$DelaySeconds = 2
    )

    $LastError = $null

    for (
        $Attempt = 1;
        $Attempt -le $Attempts;
        $Attempt++
    ) {
        try {
            $Response = Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 10

            if (
                $Response.StatusCode -ge 200 -and
                $Response.StatusCode -lt 400
            ) {
                Write-Ok (
                    "$Url -> HTTP $($Response.StatusCode)"
                )
                return
            }

            $LastError = (
                "HTTP $($Response.StatusCode)"
            )
        }
        catch {
            $LastError = $_.Exception.Message
        }

        if ($Attempt -lt $Attempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    throw (
        "Health check fallo para '$Url'. " +
        "Ultimo error: $LastError"
    )
}

Write-Step 'MYC SYSTEM - ACTUALIZACION PRODUCCION'

try {
    Write-Step '[1/12] Preflight'

    if (-not (Test-Path $ProjectPath)) {
        throw "No existe el repositorio: $ProjectPath"
    }

    if (-not (Test-Path $BackendPath)) {
        throw "No existe backend: $BackendPath"
    }

    if (-not (Test-Path $FrontendPath)) {
        throw "No existe frontend: $FrontendPath"
    }

    if (-not (Test-Path $Python)) {
        throw "No existe Python del venv: $Python"
    }

    if (-not (Test-Path $FrontendPackageJson)) {
        throw (
            'No existe frontend/package.json: ' +
            $FrontendPackageJson
        )
    }

    Set-Location $ProjectPath

    $Branch = (
        Get-GitOutput -Arguments @(
            'branch',
            '--show-current'
        )
    ).Trim()

    if ($Branch -ne 'main') {
        throw (
            'Produccion debe actualizarse desde main. ' +
            "Branch actual: $Branch"
        )
    }

    $Dirty = @(
        Get-GitOutput -Arguments @(
            'status',
            '--porcelain'
        )
    )

    if ($Dirty.Count -gt 0) {
        Write-Host ''
        Write-Host 'Cambios locales detectados:'

        $Dirty | ForEach-Object {
            Write-Host $_
        }

        throw (
            'El worktree no esta limpio. ' +
            'No se actualizara produccion.'
        )
    }

    $HeadBeforeFetch = (
        Get-GitOutput -Arguments @(
            'rev-parse',
            'HEAD'
        )
    ).Trim()

    Write-Host 'Branch: main'
    Write-Host "HEAD actual: $HeadBeforeFetch"

    $DeploymentState = Read-DeploymentState
    $Bootstrap = ($null -eq $DeploymentState)

    if ($Bootstrap) {
        Write-Warn (
            'No existe deployment state. ' +
            'Se ejecutara bootstrap/reconciliacion.'
        )

        $LastDeployedCommit = $null
    }
    else {
        $LastDeployedCommit = (
            [string]$DeploymentState.deployed_commit
        ).Trim()

        Write-Host (
            'Ultimo commit desplegado: ' +
            $LastDeployedCommit
        )
    }

    Write-Step '[2/12] Sincronizando Git'

    Invoke-External `
        -Executable 'git' `
        -Arguments @(
            'fetch',
            'origin',
            '--prune'
        ) `
        -WorkingDirectory $ProjectPath

    $OriginMain = (
        Get-GitOutput -Arguments @(
            'rev-parse',
            'origin/main'
        )
    ).Trim()

    Write-Host "origin/main: $OriginMain"

    & git merge-base --is-ancestor HEAD origin/main

    if ($LASTEXITCODE -ne 0) {
        throw (
            'HEAD local no es ancestro de origin/main. ' +
            'Se requiere revision manual.'
        )
    }

    Invoke-External `
        -Executable 'git' `
        -Arguments @(
            'pull',
            '--ff-only',
            'origin',
            'main'
        ) `
        -WorkingDirectory $ProjectPath

    $NewHead = (
        Get-GitOutput -Arguments @(
            'rev-parse',
            'HEAD'
        )
    ).Trim()

    Write-Host "HEAD nuevo: $NewHead"

    $ChangedFiles = @()

    if (-not $Bootstrap) {
        if (
            -not (
                Test-GitCommitExists `
                    -Commit $LastDeployedCommit
            )
        ) {
            throw (
                'El deployed_commit registrado no existe en ' +
                "el repositorio local: $LastDeployedCommit"
            )
        }

        if (
            -not (
                Test-GitAncestor `
                    -Ancestor $LastDeployedCommit `
                    -Descendant $NewHead
            )
        ) {
            throw (
                'El deployed_commit no es ancestro del HEAD ' +
                'actual. Se requiere revision manual.'
            )
        }

        $ChangedFiles = @(
            Get-ChangedFilesBetween `
                -OldCommit $LastDeployedCommit `
                -NewCommit $NewHead
        )
    }

    $BackendChanged = (
        $Bootstrap -or
        (
            Test-AnyPathChanged `
                -ChangedFiles $ChangedFiles `
                -Prefixes @(
                    'backend/',
                    'requirements.txt'
                )
        )
    )

    $FrontendChanged = (
        $Bootstrap -or
        (
            Test-AnyPathChanged `
                -ChangedFiles $ChangedFiles `
                -Prefixes @(
                    'frontend/'
                )
        )
    )

    $DeveloperBrokerChanged = (
        $Bootstrap -or
        (
            Test-AnyPathChanged `
                -ChangedFiles $ChangedFiles `
                -Prefixes @(
                    'backend/app/developer_broker/',
                    'deploy/windows/'
                )
        )
    )

    $BackendRequirementsChanged = (
        -not $Bootstrap -and
        (
            Test-ExactPathChanged `
                -ChangedFiles $ChangedFiles `
                -Paths @(
                    'requirements.txt'
                )
        )
    )

    $FrontendDependenciesChanged = (
        -not $Bootstrap -and
        (
            Test-ExactPathChanged `
                -ChangedFiles $ChangedFiles `
                -Paths @(
                    'frontend/package.json',
                    'frontend/package-lock.json'
                )
        )
    )

    Write-Host ''
    Write-Host 'Alcance desde ultimo deployment:'
    Write-Host "Bootstrap        : $Bootstrap"
    Write-Host "Backend          : $BackendChanged"
    Write-Host "Frontend         : $FrontendChanged"
    Write-Host "Developer Broker : $DeveloperBrokerChanged"

    if (
        -not $Bootstrap -and
        $ChangedFiles.Count -eq 0
    ) {
        Write-Host (
            'Git no tiene cambios pendientes desde ' +
            'el ultimo deployment.'
        )
    }

    Write-Step '[3/12] Dependencias backend'

    if ($BackendRequirementsChanged) {
        if (-not (Test-Path $Requirements)) {
            throw (
                'requirements.txt cambio pero no existe: ' +
                $Requirements
            )
        }

        Invoke-External `
            -Executable $Python `
            -Arguments @(
                '-m',
                'pip',
                'install',
                '-r',
                $Requirements
            ) `
            -WorkingDirectory $ProjectPath
    }
    else {
        Write-Host (
            'requirements.txt sin cambios. ' +
            'No se reinstalan dependencias backend.'
        )
    }

    Invoke-External `
        -Executable $Python `
        -Arguments @(
            '-m',
            'pip',
            'check'
        ) `
        -WorkingDirectory $ProjectPath

    Write-Step '[4/12] Migraciones Alembic'

    $AlembicResult = Sync-AlembicToHead

    $BackendNeedsRestart = (
        $BackendChanged -or
        $AlembicResult.Migrated
    )

    Write-Step '[5/12] Dependencias frontend'

    $NeedFrontendDependencies = $false

    if (-not (Test-Path $FrontendNodeModules)) {
        $NeedFrontendDependencies = $true
    }

    if ($FrontendDependenciesChanged) {
        $NeedFrontendDependencies = $true
    }

    if ($NeedFrontendDependencies) {
        if (Test-Path $FrontendPackageLock) {
            Invoke-External `
                -Executable 'npm.cmd' `
                -Arguments @(
                    'ci'
                ) `
                -WorkingDirectory $FrontendPath
        }
        else {
            Invoke-External `
                -Executable 'npm.cmd' `
                -Arguments @(
                    'install'
                ) `
                -WorkingDirectory $FrontendPath
        }
    }
    else {
        Write-Host (
            'Dependencias frontend sin cambios y ' +
            'node_modules disponible.'
        )
    }

    Write-Step '[6/12] Evaluando build frontend'

    $ExistingFrontendValid = (
        Test-FrontendBundle `
            -DistPath $FrontendDist
    )

    if ($ExistingFrontendValid) {
        Write-Ok (
            'dist actual usa API publica y no contiene localhost.'
        )
    }
    else {
        Write-Warn (
            'dist inexistente o invalido. ' +
            'Se forzara build:tunnel.'
        )
    }

    $FrontendNeedsBuild = (
        $FrontendChanged -or
        -not $ExistingFrontendValid
    )

    Write-Host (
        "Frontend requiere build: $FrontendNeedsBuild"
    )

    Write-Step '[7/12] Build y validacion frontend'

    if ($FrontendNeedsBuild) {
        Build-FrontendProduction
    }
    else {
        $null = Test-FrontendBundle `
            -DistPath $FrontendDist `
            -ThrowOnFailure

        Write-Host (
            'Build existente valido; no se reconstruye.'
        )
    }

    Write-Step '[8/12] Publicando frontend'

    if ($FrontendNeedsBuild) {
        Restart-MYCService `
            -Name $FrontendService
    }
    else {
        Write-Host (
            'Frontend no requirio build; reinicio omitido.'
        )
    }

    Write-Step '[9/12] Reiniciando backend'

    if ($BackendNeedsRestart) {
        Restart-MYCService `
            -Name $BackendService
    }
    else {
        Write-Host (
            'Backend sin cambios ni migraciones; ' +
            'reinicio omitido.'
        )
    }

    Write-Step '[10/12] Developer Broker'

    if (
        Test-ServiceInstalled `
            -Name $DeveloperBrokerService
    ) {
        if ($DeveloperBrokerChanged) {
            Restart-MYCService `
                -Name $DeveloperBrokerService
        }
        else {
            Assert-ServiceRunning `
                -Name $DeveloperBrokerService
        }
    }
    else {
        Write-Host (
            'MYCDeveloperBroker no esta instalado. ' +
            'No se instala automaticamente.'
        )
    }

    Write-Step '[11/12] Validacion infraestructura'

    Assert-ServiceRunning `
        -Name $BackendService

    Assert-ServiceRunning `
        -Name $FrontendService

    Assert-ServiceRunning `
        -Name $CloudflaredService

    Assert-ServiceRunning `
        -Name $WireGuardService

    Write-Host ''
    Write-Host 'Health checks locales...'

    Wait-HttpSuccess `
        -Url $LocalBackendHealth

    Wait-HttpSuccess `
        -Url $LocalFrontendHealth

    Write-Host ''
    Write-Host 'Health checks publicos...'

    Wait-HttpSuccess `
        -Url $PublicBackendHealth

    Wait-HttpSuccess `
        -Url $PublicFrontendHealth

    Write-Step '[12/12] Validacion final'

    $FinalCurrent = Get-AlembicRevisions `
        -Command 'current'

    $FinalHeads = Get-AlembicRevisions `
        -Command 'heads'

    if (
        -not (
            Test-AlembicAligned `
                -Current $FinalCurrent `
                -Heads $FinalHeads
        )
    ) {
        throw (
            'Alembic dejo de estar alineado antes ' +
            'de cerrar el deployment.'
        )
    }

    $null = Test-FrontendBundle `
        -DistPath $FrontendDist `
        -ThrowOnFailure

    Write-DeploymentState `
        -Commit $NewHead `
        -AlembicHeads $FinalHeads.Revisions

    if (Test-Path $FrontendPreviousDist) {
        try {
            Remove-Item `
                -Path $FrontendPreviousDist `
                -Recurse `
                -Force

            Write-Ok (
                'rollback temporal del frontend eliminado.'
            )
        }
        catch {
            Write-Warn (
                'El deployment termino correctamente, pero ' +
                'no se pudo eliminar dist.__previous. ' +
                $_.Exception.Message
            )
        }
    }

    Write-Step 'ACTUALIZACION COMPLETADA'

    Write-Host ''

    if ($Bootstrap) {
        Write-Host (
            'Deployment previo : bootstrap / desconocido'
        )
    }
    else {
        Write-Host (
            "Deployment previo : $LastDeployedCommit"
        )
    }

    Write-Host "Commit actual     : $NewHead"

    Write-Host (
        'Alembic           : ' +
        ($FinalHeads.Revisions -join ', ')
    )

    Write-Host 'Frontend mode     : tunnel'

    Write-Host (
        "Frontend API      : $ExpectedPublicApiHost"
    )

    Write-Host ''
    Write-Host "$BackendService -> Running"
    Write-Host "$FrontendService -> Running"
    Write-Host "$CloudflaredService -> Running"
    Write-Host "$WireGuardService -> Running"

    if (
        Test-ServiceInstalled `
            -Name $DeveloperBrokerService
    ) {
        Write-Host (
            "$DeveloperBrokerService -> Running"
        )
    }
    else {
        Write-Host (
            "$DeveloperBrokerService -> No instalado"
        )
    }

    Write-Host ''
    Write-Host 'API publica      : OK'
    Write-Host 'Frontend publico : OK'
    Write-Host ''
    Write-Host (
        "Deployment state : $DeploymentStatePath"
    )

    exit 0
}
catch {
    Write-Host ''
    Write-Step 'ERROR EN ACTUALIZACION'

    Write-Host `
        $_.Exception.Message `
        -ForegroundColor Red

    Write-Host ''
    Write-Host 'La actualizacion fue detenida.'
    Write-Host (
        'El deployment state NO fue avanzado.'
    )

    Write-Host ''
    Write-Host (
        'Si el repositorio ya fue actualizado, la siguiente ' +
        'ejecucion retomara el deployment desde el ultimo ' +
        'commit registrado como desplegado.'
    )

    exit 1
}
