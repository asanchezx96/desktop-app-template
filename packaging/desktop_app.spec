# -*- mode: python ; coding: utf-8 -*-
"""
desktop_app.spec — PyInstaller spec para Windows.
Genera DesktopAppTemplate.exe en la carpeta dist/.
"""

import os
import sys
from pathlib import Path

# ── Directorio raíz del proyecto ──────────────────────────────────────────
# NOTA: SPECPATH apunta a packaging/; PROJECT_ROOT es la raíz del proyecto.
PROJECT_ROOT = Path(SPECPATH).parent
FRONTEND_DIST = PROJECT_ROOT / "src" / "frontend" / "dist"

# ── Coleccionar datos del frontend (dist) ─────────────────────────────────
frontend_data = []
if FRONTEND_DIST.is_dir():
    for root, dirs, files in os.walk(str(FRONTEND_DIST)):
        rel_path = os.path.relpath(root, str(FRONTEND_DIST))
        dest = os.path.join("frontend", "dist", rel_path)
        for f in files:
            src_file = os.path.join(root, f)
            frontend_data.append((src_file, dest))

# ── Datos adicionales a empaquetar ──────────────────────────────────────
extra_data = [
    # .env y .env.local se copian a la raíz del ejecutable para que dotenv
    # los encuentre en tiempo de ejecución.
    (str(PROJECT_ROOT / ".env"), "."),
    (str(PROJECT_ROOT / ".env.local"), "."),
    # Icono para la bandeja del sistema y registro de Windows
    (str(PROJECT_ROOT / "assets" / "icon.png"), "."),
    (str(PROJECT_ROOT / "assets" / "icon.png"), "assets"),
    (str(PROJECT_ROOT / "assets" / "icon.ico"), "."),
    # Archivo de version
    (str(PROJECT_ROOT / "version.txt"), "."),
]

# ── Análisis ──────────────────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "app" / "desktop_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=frontend_data + extra_data,
    hiddenimports=[
        # ── Web / Server ──
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.middleware.gzip',
        'fastapi.staticfiles',
        'fastapi.responses',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.staticfiles',
        'starlette.responses',
        'requests',
        'dotenv',
        # ── Desktop / GUI ──
        'webview',
        'webview.platforms',
        'webview.platforms.win32_edge',
        'pystray',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        # ── .NET interop ──
        'pythonnet',
        'clr',
        'clr_loader',
        # ── Multiprocessing ──
        'multiprocessing',
        'multiprocessing.popen_spawn_win32',
        # ── Asyncio ──
        'asyncio',
        # ── Módulos del proyecto ──
        'agent',
        'agent.env_config',
        'agent.settings',
        'src',
        'src.backend',
        'src.backend.server_app',
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[],
    noarchive=False,
)

# ── Empaquetado PyInstaller ───────────────────────────────────────────────
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=os.environ.get('APP_OUTPUT_NAME', 'DesktopAppTemplate'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # Sin consola (GUI de escritorio)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "assets" / "icon.ico") if (PROJECT_ROOT / "assets" / "icon.ico").is_file() else None,
)
