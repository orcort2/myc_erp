#Requires -Version 5.1
#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [string]$ProjectPath = 'C:\Users\SMM ADMIN\myc_erp'
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$BackendPath = Join-Path $ProjectPath 'backend'
$FrontendPath = Join-Path $ProjectPath 'frontend'

$Python = Join-Path $ProjectPath 'venv\Scripts\python.exe'
$Requirements = Join-Path $ProjectPath 'requirements.txt'

$FrontendDist = Join-Path $FrontendPath 'dist'
$FrontendNextDist = Join-Path $FrontendPath 'dist.__next'
$FrontendPreviousDist = Join-Path $FrontendPath 'dist.__previous'

$BackendService = 'MYCBackend'
$FrontendService = 'MYCFrontend'
$CloudflaredService = 'Cloudflared'
$WireGuardService = 'WireGuardTunnel$myc-vpn'
$DeveloperBrokerService = 'MYCDeveloperBroker'

$LocalBackendHealth = 'http://127.0.0.1:8000/api/health'
$LocalFrontendHealth = 'http://127.0.0.1:5173'
$PublicBackendHealth = 'https://api-erp.mycmetrology.com.mx/api/health'
$PublicFrontendHealth = 'https://erp.mycmetrology.com.mx/'

function Write-Step {
    param([string]$Title)

    Write-Host ''
    Write-Host '========================================'
    Write-Host $Title
    Write-Host '========================================'
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
            throw "Comando fallo con codigo $LASTEXITCODE`: $Executable $($Arguments -join ' ')"
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

function Wait-ServiceState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [ValidateSet('Running', 'Stopped')]
        [string]$ExpectedStatus,

        [int]$TimeoutSeconds = 30
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    do {
        $Service = Get-Service -Name $Name -ErrorAction Stop

        if ($Service.Status.ToString() -eq $ExpectedStatus) {
            return
        }

        Start-Sleep -Seconds 1
    }
    while ((Get-Date) -lt $Deadline)

    throw "El servicio '$Name' no alcanzo el estado '$ExpectedStatus' dentro de $TimeoutSeconds segundos."
}

function Assert-ServiceRunning {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $Service = Get-Service -Name $Name -ErrorAction Stop

    if ($Service.Status -ne 'Running') {
        throw "El servicio '$Name' no esta Running. Estado: $($Service.Status)"
    }

    Write-Host "$Name -> Running"
}

function Wait-HttpSuccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$Attempts = 15,

        [int]$DelaySeconds = 2
    )

    $LastError = $null

    for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
        try {
            $Response = Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 10

            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 400) {
                Write-Host "OK $Url -> HTTP $($Response.StatusCode)"
                return
            }

            $LastError = "HTTP $($Response.StatusCode)"
        }
        catch {
            $LastError = $_.Exception.Message
        }

        if ($Attempt -lt $Attempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    throw "Health check fallo para '$Url'. Ultimo error: $LastError"
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
        [Parameter(Mandatory = $true)]
        [string[]]$ChangedFiles,

        [Parameter(Mandatory = $true)]
        [string[]]$Prefixes
    )

    foreach ($File in $ChangedFiles) {
        foreach ($Prefix in $Prefixes) {
            if ($File -eq $Prefix -or $File.StartsWith($Prefix)) {
                return $true
            }
        }
    }

    return $false
}

function Test-FileChangedBetween {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OldCommit,

        [Parameter(Mandatory = $true)]
        [string]$NewCommit,

        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    if ($OldCommit -eq $NewCommit) {
        return $false
    }

    $ChangedFiles = @(
        Get-GitOutput -Arguments @(
            'diff',
            '--name-only',
            $OldCommit,
            $NewCommit
        )
    )

    foreach ($Path in $Paths) {
        if ($ChangedFiles -contains $Path) {
            return $true
        }
    }

    return $false
}

function Test-AlembicAtHead {
    Push-Location $BackendPath

    try {
        $CurrentOutput = @(& $Python -m alembic current 2>&1)

        if ($LASTEXITCODE -ne 0) {
            throw 'alembic current fallo.'
        }

        $HeadsOutput = @(& $Python -m alembic heads 2>&1)

        if ($LASTEXITCODE -ne 0) {
            throw 'alembic heads fallo.'
        }

        Write-Host ''
        Write-Host 'Alembic current:'
        $CurrentOutput | ForEach-Object { Write-Host $_ }

        Write-Host ''
        Write-Host 'Alembic heads:'
        $HeadsOutput | ForEach-Object { Write-Host $_ }

        $CurrentRevisions = @(
            $CurrentOutput |
                ForEach-Object {
                    if ($_ -match '^([0-9a-f]+)\s') {
                        $Matches[1]
                    }
                } |
                Where-Object { $_ } |
                Sort-Object -Unique
        )

        $HeadRevisions = @(
            $HeadsOutput |
                ForEach-Object {
                    if ($_ -match '^([0-9a-f]+)\s') {
                        $Matches[1]
                    }
                } |
                Where-Object { $_ } |
                Sort-Object -Unique
        )

        if ($HeadRevisions.Count -eq 0) {
            throw 'No se pudo determinar el head de Alembic.'
        }

        if ($CurrentRevisions.Count -ne $HeadRevisions.Count) {
            throw 'Alembic no quedo alineado con head.'
        }

        foreach ($HeadRevision in $HeadRevisions) {
            if ($CurrentRevisions -notcontains $HeadRevision) {
                throw "Alembic current no contiene head $HeadRevision."
            }
        }

        Write-Host 'Alembic esta alineado con head.'
    }
    finally {
        Pop-Location
    }
}

Write-Step 'MYC SYSTEM - ACTUALIZACION PRODUCCION'

try {
    # --------------------------------------------------
    # 1. PREFLIGHT
    # --------------------------------------------------

    Write-Step '[1/12] Preflight'

    if (-not (Test-Path $ProjectPath)) {
        throw "No existe el repositorio: $ProjectPath"
    }

    if (-not (Test-Path $Python)) {
        throw "No existe Python del venv: $Python"
    }

    if (-not (Test-Path $Requirements)) {
        throw "No existe requirements.txt raiz: $Requirements"
    }

    Set-Location $ProjectPath

    $Branch = (
        Get-GitOutput -Arguments @('branch', '--show-current')
    ).Trim()

    if ($Branch -ne 'main') {
        throw "Produccion debe actualizarse desde main. Branch actual: $Branch"
    }

    $Dirty = @(
        Get-GitOutput -Arguments @('status', '--porcelain')
    )

    if ($Dirty.Count -gt 0) {
        Write-Host ''
        Write-Host 'Cambios locales detectados:'
        $Dirty | ForEach-Object { Write-Host $_ }

        throw 'El worktree no esta limpio. No se actualizara produccion.'
    }

    $OldHead = (
        Get-GitOutput -Arguments @('rev-parse', 'HEAD')
    ).Trim()

    Write-Host 'Branch: main'
    Write-Host "HEAD actual: $OldHead"

    # --------------------------------------------------
    # 2. FETCH + FAST-FORWARD
    # --------------------------------------------------

    Write-Step '[2/12] Sincronizando Git'

    Invoke-External `
        -Executable 'git' `
        -Arguments @('fetch', 'origin', '--prune') `
        -WorkingDirectory $ProjectPath

    $OriginMain = (
        Get-GitOutput -Arguments @('rev-parse', 'origin/main')
    ).Trim()

    Write-Host "origin/main: $OriginMain"

    & git merge-base --is-ancestor HEAD origin/main

    if ($LASTEXITCODE -ne 0) {
        throw 'HEAD local no es ancestro de origin/main. Se requiere revision manual.'
    }

    Invoke-External `
        -Executable 'git' `
        -Arguments @('pull', '--ff-only', 'origin', 'main') `
        -WorkingDirectory $ProjectPath

    $NewHead = (
        Get-GitOutput -Arguments @('rev-parse', 'HEAD')
    ).Trim()

    Write-Host "HEAD nuevo: $NewHead"

    $ChangedFiles = Get-ChangedFilesBetween `
        -OldCommit $OldHead `
        -NewCommit $NewHead

    $BackendChanged = Test-AnyPathChanged `
        -ChangedFiles $ChangedFiles `
        -Prefixes @(
            'backend/',
            'requirements.txt'
        )

    $FrontendChanged = Test-AnyPathChanged `
        -ChangedFiles $ChangedFiles `
        -Prefixes @(
            'frontend/'
        )

    $BrokerChanged = Test-AnyPathChanged `
        -ChangedFiles $ChangedFiles `
        -Prefixes @(
            'deploy/windows/developer-broker/'
        )

    Write-Host ''
    Write-Host 'Alcance detectado:'
    Write-Host "Backend          : $BackendChanged"
    Write-Host "Frontend         : $FrontendChanged"
    Write-Host "Developer Broker : $BrokerChanged"

    # --------------------------------------------------
    # 3. DEPENDENCIAS BACKEND
    # --------------------------------------------------

    Write-Step '[3/12] Dependencias backend'

    $RequirementsChanged = Test-FileChangedBetween `
        -OldCommit $OldHead `
        -NewCommit $NewHead `
        -Paths @('requirements.txt')

    if (-not $BackendChanged) {
        Write-Host 'Sin cambios backend. Se omite sincronizacion de dependencias.'
    }
    elseif ($RequirementsChanged) {
        Write-Host 'requirements.txt cambio. Instalando dependencias...'

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
        Write-Host 'Backend cambio, pero requirements.txt no. Se conserva el venv actual.'
    }

    # --------------------------------------------------
    # 4. ALEMBIC
    # --------------------------------------------------

    Write-Step '[4/12] Migraciones Alembic'

    if ($BackendChanged) {
        Invoke-External `
            -Executable $Python `
            -Arguments @('-m', 'alembic', 'upgrade', 'head') `
            -WorkingDirectory $BackendPath

        Test-AlembicAtHead
    }
    else {
        Write-Host 'Sin cambios backend. Alembic omitido.'
    }

    # --------------------------------------------------
    # 5. DEPENDENCIAS FRONTEND
    # --------------------------------------------------

    Write-Step '[5/12] Dependencias frontend'

    $FrontendDepsChanged = Test-FileChangedBetween `
        -OldCommit $OldHead `
        -NewCommit $NewHead `
        -Paths @(
            'frontend/package.json',
            'frontend/package-lock.json'
        )

    if (-not $FrontendChanged) {
        Write-Host 'Sin cambios frontend. Dependencias frontend omitidas.'
    }
    elseif ($FrontendDepsChanged) {
        Write-Host 'Dependencias frontend cambiaron. Ejecutando npm ci...'

        Invoke-External `
            -Executable 'npm.cmd' `
            -Arguments @('ci') `
            -WorkingDirectory $FrontendPath
    }
    else {
        Write-Host 'Frontend cambio, pero dependencias no.'
    }

    # --------------------------------------------------
    # 6. BUILD FRONTEND STAGING
    # --------------------------------------------------

    Write-Step '[6/12] Build frontend'

    if (-not $FrontendChanged) {
        Write-Host 'Sin cambios frontend. Build omitido.'
    }
    else {
        if (Test-Path $FrontendNextDist) {
            Remove-Item $FrontendNextDist -Recurse -Force
        }

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
            throw "El build termino pero no existe $FrontendNextDist."
        }

        $IndexPath = Join-Path $FrontendNextDist 'index.html'

        if (-not (Test-Path $IndexPath)) {
            throw 'Build invalido: no existe index.html.'
        }
    }

    # --------------------------------------------------
    # 7. VALIDAR BUILD
    # --------------------------------------------------

    Write-Step '[7/12] Validando build frontend'

    if (-not $FrontendChanged) {
        Write-Host 'Sin cambios frontend. Validacion de build omitida.'
    }
    else {

    $InvalidReferences = Get-ChildItem $FrontendNextDist -Recurse -File |
        Select-String `
            -Pattern '127\.0\.0\.1:8000|localhost:8000' `
            -ErrorAction SilentlyContinue

    if ($InvalidReferences) {
        throw 'BUILD INVALIDO: contiene referencias a localhost:8000.'
    }

    $PublicApiReference = Get-ChildItem $FrontendNextDist -Recurse -File |
        Select-String `
            -Pattern 'api-erp\.mycmetrology\.com\.mx' `
            -ErrorAction SilentlyContinue

    if (-not $PublicApiReference) {
        throw 'BUILD INVALIDO: no se encontro api-erp.mycmetrology.com.mx.'
    }

        Write-Host 'Build de produccion validado.'
    }

    # --------------------------------------------------
    # 8. PUBLICAR FRONTEND
    # --------------------------------------------------

    Write-Step '[8/12] Publicando frontend'

    if (-not $FrontendChanged) {
        Write-Host 'Sin cambios frontend. Publicacion y reinicio omitidos.'
    }
    else {
        Stop-Service -Name $FrontendService -Force
    Wait-ServiceState `
        -Name $FrontendService `
        -ExpectedStatus 'Stopped'

    if (Test-Path $FrontendPreviousDist) {
        Remove-Item $FrontendPreviousDist -Recurse -Force
    }

    if (Test-Path $FrontendDist) {
        Move-Item `
            -Path $FrontendDist `
            -Destination $FrontendPreviousDist
    }

    try {
        Move-Item `
            -Path $FrontendNextDist `
            -Destination $FrontendDist

        Start-Service -Name $FrontendService

        Wait-ServiceState `
            -Name $FrontendService `
            -ExpectedStatus 'Running'

        Wait-HttpSuccess -Url $LocalFrontendHealth
    }
    catch {
        Write-Host ''
        Write-Host 'Fallo la publicacion del frontend. Intentando rollback...'

        try {
            Stop-Service `
                -Name $FrontendService `
                -Force `
                -ErrorAction SilentlyContinue

            if (Test-Path $FrontendDist) {
                Remove-Item $FrontendDist -Recurse -Force
            }

            if (Test-Path $FrontendPreviousDist) {
                Move-Item `
                    -Path $FrontendPreviousDist `
                    -Destination $FrontendDist
            }

            Start-Service -Name $FrontendService

            Wait-ServiceState `
                -Name $FrontendService `
                -ExpectedStatus 'Running'
        }
        catch {
            Write-Host 'ADVERTENCIA: el rollback del frontend tambien fallo.'
        }

        throw
    }

        if (Test-Path $FrontendPreviousDist) {
            Remove-Item $FrontendPreviousDist -Recurse -Force
        }
    }

    # --------------------------------------------------
    # 9. REINICIAR BACKEND
    # --------------------------------------------------

    Write-Step '[9/12] Reiniciando backend'

    if ($BackendChanged) {
        Restart-Service -Name $BackendService -Force

        Wait-ServiceState `
            -Name $BackendService `
            -ExpectedStatus 'Running'

        Wait-HttpSuccess -Url $LocalBackendHealth
    }
    else {
        Write-Host 'Sin cambios backend. Reinicio omitido.'
    }

    # --------------------------------------------------
    # 10. DEVELOPER BROKER
    # --------------------------------------------------

    Write-Step '[10/12] Developer Broker'

    $BrokerService = Get-Service `
        -Name $DeveloperBrokerService `
        -ErrorAction SilentlyContinue

    if ($BrokerService -and $BrokerChanged) {
        Write-Host 'MYCDeveloperBroker esta instalado y cambio su deployment. Reiniciando...'

        Restart-Service -Name $DeveloperBrokerService -Force

        Wait-ServiceState `
            -Name $DeveloperBrokerService `
            -ExpectedStatus 'Running'

        $BrokerTest = Join-Path `
            $ProjectPath `
            'deploy\windows\developer-broker\Test-MYCDeveloperBroker.ps1'

        if (Test-Path $BrokerTest) {
            Write-Host 'Ejecutando validacion read-only del Developer Broker...'

            & powershell.exe `
                -NoProfile `
                -ExecutionPolicy Bypass `
                -File $BrokerTest `
                -RepoRoot $ProjectPath

            if ($LASTEXITCODE -ne 0) {
                throw 'La validacion de MYCDeveloperBroker fallo.'
            }
        }
    }
    elseif ($BrokerService) {
        Write-Host 'MYCDeveloperBroker esta instalado, pero no cambio. Reinicio omitido.'
    }
    else {
        Write-Host 'MYCDeveloperBroker no esta instalado. No se instala automaticamente.'
    }

    # --------------------------------------------------
    # 11. INFRA + HEALTH PUBLICO
    # --------------------------------------------------

    Write-Step '[11/12] Validacion infraestructura'

    Assert-ServiceRunning -Name $BackendService
    Assert-ServiceRunning -Name $FrontendService
    Assert-ServiceRunning -Name $CloudflaredService
    Assert-ServiceRunning -Name $WireGuardService

    Write-Host ''
    Write-Host 'Health checks publicos...'

    Wait-HttpSuccess -Url $PublicBackendHealth
    Wait-HttpSuccess -Url $PublicFrontendHealth

    # --------------------------------------------------
    # 12. VALIDACION FINAL
    # --------------------------------------------------

    Write-Step '[12/12] Validacion final'

    Invoke-External `
        -Executable 'git' `
        -Arguments @('fetch', 'origin', '--prune') `
        -WorkingDirectory $ProjectPath

    $FinalHead = (
        Get-GitOutput -Arguments @('rev-parse', 'HEAD')
    ).Trim()

    $FinalOrigin = (
        Get-GitOutput -Arguments @('rev-parse', 'origin/main')
    ).Trim()

    if ($FinalHead -ne $FinalOrigin) {
        throw 'La actualizacion termino pero HEAD != origin/main.'
    }

    $FinalDirty = @(
        Get-GitOutput -Arguments @('status', '--porcelain')
    )

    if ($FinalDirty.Count -gt 0) {
        Write-Host ''
        Write-Host 'ADVERTENCIA: el worktree termino con cambios locales:'
        $FinalDirty | ForEach-Object { Write-Host $_ }
    }

    Write-Host ''
    Write-Host '========================================'
    Write-Host '        ACTUALIZACION COMPLETADA'
    Write-Host '========================================'
    Write-Host ''
    Write-Host "Commit anterior : $OldHead"
    Write-Host "Commit actual   : $FinalHead"
    Write-Host ''
    Write-Host 'Backend          : Running'
    Write-Host 'Frontend         : Running'
    Write-Host 'Cloudflared      : Running'
    Write-Host 'WireGuard        : Running'

    if ($BrokerService) {
        Write-Host 'DeveloperBroker  : Running'
    }
    else {
        Write-Host 'DeveloperBroker  : No instalado'
    }

    Write-Host ''
    Write-Host 'API publica      : OK'
    Write-Host 'Frontend publico : OK'
    Write-Host ''

    exit 0
}
catch {
    Write-Host ''
    Write-Host '========================================'
    Write-Host '          ERROR EN ACTUALIZACION'
    Write-Host '========================================'
    Write-Host ''
    Write-Host $_.Exception.Message
    Write-Host ''
    Write-Host 'La actualizacion fue detenida.'
    Write-Host ''
    exit 1
}
