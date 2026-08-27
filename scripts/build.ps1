# Script de Compilación para Windows
# Ejecución: .\scripts\build.ps1

$ErrorActionPreference = "Stop"

# Asegurar que la ejecución siempre sea desde la raíz del proyecto
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\.."
Set-Location $ProjectRoot

Write-Host "--- INICIANDO COMPILACION DE DESKTOP APP TEMPLATE ---" -ForegroundColor Cyan

# 1. Limpiar procesos antiguos
Write-Host "[1/4] Limpiando procesos antiguos..." -ForegroundColor Yellow
try {
    taskkill /F /IM DesktopAppTemplate.exe /T 2>$null
} catch {}

# Limpiar procesos en puerto 5055
try {
    $port = 5055
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        Write-Host "Detectado proceso ocupando el puerto $port. Matando proceso..." -ForegroundColor Yellow
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -gt 0) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    }
} catch {
    Write-Warning "No se pudo limpiar los procesos en el puerto 5055: $_"
}

# Limpiar carpeta build con reintentos
Write-Host "Limpiando directorio de construcción temporal..." -ForegroundColor Yellow
$buildPath = "build"
if (Test-Path $buildPath) {
    for ($i = 1; $i -le 3; $i++) {
        try {
            Remove-Item -Path $buildPath -Recurse -Force
            break
        } catch {
            if ($i -eq 3) {
                Write-Warning "No se pudo limpiar la carpeta 'build'. Continuando..."
            } else {
                Write-Host "Carpeta 'build' bloqueada. Reintentando en 2 segundos..." -ForegroundColor DarkYellow
                Start-Sleep -Seconds 2
            }
        }
    }
}

# 1.5. Generar Iconos y Favicons (opcional)
# El generador vive fuera del repo en otras máquinas; si no está, se usan los
# icon.png/icon.ico en assets/ ya versionados y el build continúa igual.
$pythonCmd = "python"
if (Test-Path ".venv\Scripts\python.exe") {
    $pythonCmd = ".venv\Scripts\python.exe"
}
if (Test-Path "apply_icon.py") {
    Write-Host "[1.5/4] Generando iconos desde icon-v3.svg..." -ForegroundColor Yellow
    try {
        & $pythonCmd apply_icon.py
    } catch {
        Write-Warning "No se pudo ejecutar apply_icon.py: $_"
    }
} else {
    Write-Host "[1.5/4] Sin apply_icon.py: se usan los iconos de assets/ ya versionados." -ForegroundColor Gray
}

# 2. Compilar Frontend
Write-Host "[2/4] Compilando Frontend (React/Vite)..." -ForegroundColor Yellow
Set-Location src/frontend
npm run build
Set-Location ../..

# 3. Sincronizar Versión
Write-Host "[3/4] Sincronizando versión..." -ForegroundColor Yellow
if (Test-Path "version.txt") {
    $currentVersion = Get-Content "version.txt"
    $currentVersion = $currentVersion.Trim()
    Write-Host "Versión detectada: $currentVersion" -ForegroundColor Gray
    
    if (Test-Path "packaging\desktop_app.iss") {
        (Get-Content packaging\desktop_app.iss) -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$currentVersion`"" | Set-Content packaging\desktop_app.iss
    }
} else {
    Write-Warning "No se encontró version.txt, usando 1.0.0 por defecto."
}

# 4. Compilar Ejecutable
Write-Host "[4/4] Compilando Ejecutable (PyInstaller)..." -ForegroundColor Yellow
$pyinstallerCmd = "pyinstaller"
if (Test-Path ".venv\Scripts\pyinstaller.exe") {
    $pyinstallerCmd = ".venv\Scripts\pyinstaller.exe"
    Write-Host "Usando PyInstaller del entorno virtual local: $pyinstallerCmd" -ForegroundColor Gray
}

try {
    & $pyinstallerCmd --clean packaging\desktop_app.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }
} catch {
    if (Test-Path "dist\DesktopAppTemplate.exe") {
        Write-Host "`n[!] PyInstaller encontró una advertencia durante el post-procesamiento, pero el ejecutable fue compilado." -ForegroundColor Yellow
    } else {
        Write-Error "Fallo al ejecutar PyInstaller. Asegúrate de tener el entorno virtual creado (.venv) y las dependencias instaladas (pip install -r requirements.txt)."
        throw $_
    }
}

# 4. Finalización
if (Test-Path "dist\DesktopAppTemplate.exe") {
    Write-Host "`n====================================================" -ForegroundColor Green
    Write-Host " EXITO! El ejecutable esta listo en: .\dist\DesktopAppTemplate.exe" -ForegroundColor Green
    Write-Host "====================================================`n" -ForegroundColor Green

    # --- Compilación del Instalador de Windows (Inno Setup) ---
    $innoPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $innoPath)) {
        $innoPath = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    }

    if (Test-Path $innoPath) {
        Write-Host "Inno Setup encontrado en: $innoPath" -ForegroundColor Gray
        Write-Host "Compilando instalador de Windows..." -ForegroundColor Yellow
        try {
            & $innoPath packaging\desktop_app.iss
            if ($LASTEXITCODE -eq 0 -and (Test-Path "dist\DesktopAppTemplate-setup.exe")) {
                Write-Host "¡Instalador compilado con éxito en: .\dist\DesktopAppTemplate-setup.exe!" -ForegroundColor Green
            } else {
                Write-Warning "Inno Setup terminó pero no se encontró dist\DesktopAppTemplate-setup.exe"
            }
        } catch {
            Write-Warning "No se pudo compilar el instalador con Inno Setup: $_"
        }
    } else {
        Write-Host "Inno Setup (ISCC.exe) no detectado. Si deseas generar el instalador (.exe setup) automáticamente, por favor instala Inno Setup 6 en tu máquina." -ForegroundColor Cyan
    }

    # version.json junto a los artefactos, para quien publique la actualización
    if (Test-Path "version.txt") {
        $vJSON = "{`"version`": `"$currentVersion`"}"
        Set-Content -Path "dist\version.json" -Value $vJSON -Encoding utf8
        Write-Host "version.json generado en dist\ con la versión $currentVersion" -ForegroundColor Green
    }

    Write-Host "`n--- REQUISITO EN MAQUINA DESTINO ---" -ForegroundColor Cyan
    Write-Host "La ventana usa Edge WebView2 nativo." -ForegroundColor Yellow
    Write-Host "La maquina donde se ejecute DesktopAppTemplate.exe necesita:" -ForegroundColor Yellow
    Write-Host "  Edge WebView2 Runtime (preinstalado en Win10 21H2+ y Win11)" -ForegroundColor White
    Write-Host "  Si no esta instalado, descargar de:" -ForegroundColor DarkGray
    Write-Host "  https://developer.microsoft.com/microsoft-edge/webview2/" -ForegroundColor DarkGray
    Write-Host "-----------------------------------`n" -ForegroundColor Cyan
} else {
    Write-Error "Fallo en la compilación: No se encontró .\dist\DesktopAppTemplate.exe"
}
