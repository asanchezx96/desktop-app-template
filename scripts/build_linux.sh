#!/bin/bash
# Script de Compilación para Linux
# Ejecución: chmod +x scripts/build_linux.sh && ./scripts/build_linux.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo -e "\033[36m--- INICIANDO COMPILACION DE DESKTOP APP TEMPLATE (Linux) ---\033[0m"

# 1. Limpiar procesos antiguos
echo -e "\033[33m[1/4] Limpiando procesos antiguos...\033[0m"
pkill -f DesktopAppTemplate || true

# Limpiar procesos en puerto 5050
PID=$(lsof -t -i:5050 || true)
if [ ! -z "$PID" ]; then
    echo -e "\033[33mDetectado proceso ocupando el puerto 5050 (PIDs: $PID). Matando...\033[0m"
    kill -9 $PID || true
fi

# Limpiar carpetas temporales
rm -rf build dist

# 1.5. Generar Iconos y Favicons (opcional, ver build.ps1)
PYTHON_CMD="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
fi
if [ -f "apply_icon.py" ]; then
    echo -e "\033[33m[1.5/4] Generando iconos desde icon-v3.svg...\033[0m"
    $PYTHON_CMD apply_icon.py || echo -e "\033[31m[WARN] Fallo la ejecucion de apply_icon.py\033[0m"
else
    echo -e "\033[90m[1.5/4] Sin apply_icon.py: se usan los iconos de assets/ ya versionados.\033[0m"
fi

# 2. Compilar Frontend
echo -e "\033[33m[2/4] Compilando Frontend (React/Vite)...\033[0m"
cd src/frontend
npm run build
cd ../..

# 3. Compilar Ejecutable
echo -e "\033[33m[3/4] Compilando Ejecutable (PyInstaller)...\033[0m"
PYINSTALLER_CMD="pyinstaller"
if [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER_CMD=".venv/bin/pyinstaller"
    echo -e "\033[90mUsando PyInstaller del entorno virtual local: $PYINSTALLER_CMD\033[0m"
fi

APP_OUTPUT_NAME=DesktopAppTemplate-linux $PYINSTALLER_CMD --clean packaging/desktop_app.spec

# 4. Finalización
if [ -f "dist/DesktopAppTemplate-linux" ]; then
    echo -e "\n\033[32m====================================================\033[0m"
    echo -e "\033[32m EXITO! El ejecutable Linux esta listo en: ./dist/DesktopAppTemplate-linux\033[0m"
    echo -e "\033[32m====================================================\n\033[0m"
    echo -e "\033[36m--- REQUISITO EN MAQUINA DESTINO ---\033[0m"
    echo -e "\033[33mLa maquina donde se ejecute necesita librerías GTK y WebKit2GTK:\033[0m"
    echo -e "\033[37m  Debian/Ubuntu: sudo apt install libwebkit2gtk-4.0-37\033[0m"
    echo -e "\033[37m  Arch Linux:    sudo pacman -S webkit2gtk\033[0m"
    echo -e "\033[36m-----------------------------------\033[0m"
else
    echo -e "\033[31mFallo en la compilación: No se encontró ./dist/DesktopAppTemplate-linux\033[0m"
    exit 1
fi
