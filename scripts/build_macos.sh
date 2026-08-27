#!/bin/bash
# Script de Compilación para macOS
# Genera .app + DMG en dist/
# Ejecución: chmod +x scripts/build_macos.sh && ./scripts/build_macos.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo -e "\033[36m--- INICIANDO COMPILACION DE DESKTOP APP TEMPLATE (macOS) ---\033[0m"

# 1. Limpiar procesos antiguos
echo -e "\033[33m[1/5] Limpiando procesos antiguos...\033[0m"
pkill -x DesktopAppTemplate || true

PID=$(lsof -t -i:5050 || true)
if [ ! -z "$PID" ]; then
    echo -e "\033[33mDetectado proceso ocupando el puerto 5050 (PIDs: $PID). Matando...\033[0m"
    kill -9 $PID || true
fi

# Limpiar carpetas temporales
rm -rf build dist
rm -f "/tmp/DesktopAppTemplate.dmg"

# 1.5. Generar Iconos y Favicons (opcional, ver build.ps1)
PYTHON_CMD="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
fi
if [ -f "apply_icon.py" ]; then
    echo -e "\033[33m[1.5/5] Generando iconos desde icon-v3.svg...\033[0m"
    $PYTHON_CMD apply_icon.py || echo -e "\033[31m[WARN] Fallo la ejecucion de apply_icon.py\033[0m"
else
    echo -e "\033[90m[1.5/5] Sin apply_icon.py: se usan los iconos de assets/ ya versionados.\033[0m"
fi

# 2. Compilar Frontend
echo -e "\033[33m[2/5] Compilando Frontend (React/Vite)...\033[0m"
cd src/frontend
npm run build
cd ../..

# 3. Compilar Ejecutable (.app bundle)
echo -e "\033[33m[3/5] Compilando Ejecutable (PyInstaller)...\033[0m"
PYINSTALLER_CMD="pyinstaller"
if [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER_CMD=".venv/bin/pyinstaller"
    echo -e "\033[90mUsando PyInstaller del entorno virtual local: $PYINSTALLER_CMD\033[0m"
fi

$PYINSTALLER_CMD --clean packaging/desktop_app_macos.spec

# 4. Crear DMG
APP_BUNDLE="dist/DesktopAppTemplate.app"
DMG_NAME="DesktopAppTemplate.dmg"
DMG_PATH="dist/$DMG_NAME"

if [ -d "$APP_BUNDLE" ]; then
    echo -e "\033[33m[4/5] Creando DMG con hdiutil...\033[0m"

    # Crear DMG básico. El usuario arrastra el .app a Aplicaciones.
    # Primero creamos un DMG temporal, luego lo convertimos a comprimido.
    STAGING="/tmp/DesktopAppTemplate-staging"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"

    # Copiar la app y crear un enlace simbólico a /Applications
    cp -R "$APP_BUNDLE" "$STAGING/"
    ln -s "/Applications" "$STAGING/Applications"

    # Crear el DMG
    hdiutil create -volname "DesktopAppTemplate" \
        -srcfolder "$STAGING" \
        -ov -format UDZO \
        "$DMG_PATH" 2>&1

    rm -rf "$STAGING"

    if [ -f "$DMG_PATH" ]; then
        echo -e "\n\033[32m====================================================\033[0m"
        echo -e "\033[32m EXITO! La aplicacion macOS esta lista en:\033[0m"
        echo -e "\033[32m   $APP_BUNDLE\033[0m"
        echo -e "\033[32m   $DMG_PATH\033[0m"
        echo -e "\033[32m====================================================\n\033[0m"
    else
        echo -e "\033[31mError: No se pudo crear el DMG\033[0m"
        exit 1
    fi

elif [ -f "dist/DesktopAppTemplate" ]; then
    echo -e "\033[33m[4/5] Binario plano detectado (fallback)...\033[0m"
    echo -e "\033[33m[5/5] Empaquetando en DMG...\033[0m"

    STAGING="/tmp/DesktopAppTemplate-staging"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"
    cp "dist/DesktopAppTemplate" "$STAGING/"
    ln -s "/Applications" "$STAGING/Applications"

    hdiutil create -volname "DesktopAppTemplate" \
        -srcfolder "$STAGING" \
        -ov -format UDZO \
        "$DMG_PATH" 2>&1

    rm -rf "$STAGING"

    echo -e "\n\033[33m====================================================\033[0m"
    echo -e "\033[33m WARNING: No se genero .app, se empaqueto binario plano en DMG\033[0m"
    echo -e "\033[33m   $DMG_PATH\033[0m"
    echo -e "\033[33m====================================================\n\033[0m"
else
    echo -e "\033[31mFallo en la compilación: No se encontró ./dist/DesktopAppTemplate.app\033[0m"
    exit 1
fi
