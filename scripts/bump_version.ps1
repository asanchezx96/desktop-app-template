# Incrementa la versión del proyecto (SemVer: major.minor.patch).
# Ejecución: .\scripts\bump_version.ps1 -Part patch|minor|major
#
# - major → X+1.0.0   (rompe compatibilidad)
# - minor → X.Y+1.0   (funcionalidad nueva compatible)
# - patch → X.Y.Z+1   (fix/ajuste)
#
# Actualiza version.txt y el badge de versión en README.md. El instalador de
# Windows (packaging/desktop_app.iss) ya se sincroniza solo desde version.txt
# en cada build.ps1, así que no hace falta tocarlo aquí.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("major", "minor", "patch")]
    [string]$Part
)

$ErrorActionPreference = "Stop"

# Windows PowerShell 5.1 no es de fiar con UTF-8: Get-Content sin -Encoding
# puede leer un archivo UTF-8 sin BOM como si fuera ANSI (corrompe acentos),
# y Set-Content -Encoding utf8 siempre escribe con BOM (contamina version.txt,
# que luego se lee en Python con encoding="utf-8" estricto). Por eso aquí se
# usa System.IO.File directamente con UTF-8 sin BOM explícito.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\.."
$VersionFile = Join-Path $ProjectRoot "version.txt"
$ReadmeFile = Join-Path $ProjectRoot "README.md"

if (-not (Test-Path $VersionFile)) {
    Write-Error "No se encontró version.txt en $VersionFile"
    exit 1
}

$current = ([System.IO.File]::ReadAllText($VersionFile, [System.Text.Encoding]::UTF8)).Trim()
if ($current -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
    Write-Error "version.txt no tiene el formato esperado X.Y.Z (valor actual: '$current')"
    exit 1
}

$majorNum = [int]$Matches[1]
$minorNum = [int]$Matches[2]
$patchNum = [int]$Matches[3]

switch ($Part) {
    "major" { $majorNum++; $minorNum = 0; $patchNum = 0 }
    "minor" { $minorNum++; $patchNum = 0 }
    "patch" { $patchNum++ }
}

$newVersion = "$majorNum.$minorNum.$patchNum"

[System.IO.File]::WriteAllText($VersionFile, "$newVersion`n", $Utf8NoBom)

if (Test-Path $ReadmeFile) {
    $readme = [System.IO.File]::ReadAllText($ReadmeFile, [System.Text.Encoding]::UTF8)
    $readme = $readme -replace 'badge/version-[\d\.]+-blue\.svg', "badge/version-$newVersion-blue.svg"
    [System.IO.File]::WriteAllText($ReadmeFile, $readme, $Utf8NoBom)
}

Write-Host "Versión actualizada ($Part): $current -> $newVersion" -ForegroundColor Green
