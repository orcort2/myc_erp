#Requires -Version 5.1
#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'

$Updater = Join-Path $PSScriptRoot 'deploy\windows\Update-MYCProduction.ps1'

if (-not (Test-Path $Updater)) {
    throw "No se encontro el actualizador de produccion: $Updater"
}

& $Updater @args

exit $LASTEXITCODE
