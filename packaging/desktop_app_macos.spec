# -*- mode: python ; coding: utf-8 -*-
"""Spec file for macOS .app bundle."""

import os
import sys
from pathlib import Path

block_cipher = None

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(SPECPATH).parent
FRONTEND_DIST = PROJECT_ROOT / "src" / "frontend" / "dist"
AGENT_DIR = PROJECT_ROOT / "agent"
SRC_DIR = PROJECT_ROOT / "src"
DB_DIR = PROJECT_ROOT / "db"

# Collect all agent and src Python files
agent_py = list(AGENT_DIR.rglob("*.py"))
src_py = list(SRC_DIR.rglob("*.py"))
db_py = list(DB_DIR.rglob("*.py")) if DB_DIR.exists() else []

# ── Analysis ───────────────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "app" / "desktop_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Frontend dist (React SPA)
        (str(FRONTEND_DIST), "frontend/dist"),
        # Agent package
        *[(str(p), f"agent/{p.relative_to(AGENT_DIR).parent}") for p in agent_py],
        # DB package
        *[(str(p), "db") for p in db_py],
        # Icono para la bandeja del sistema
        (str(PROJECT_ROOT / "assets" / "icon.png"), "."),
    ],
    hiddenimports=[
        "agent",
        "agent.env_config",
        "agent.settings",
        "src",
        "src.backend",
        "src.backend.server_app",
        "pystray",
        "PIL",
        "PIL._tkinter_finder",
        "webview",
        "webview.platforms",
        "webview.platforms.cocoa",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.middleware",
        "uvicorn.middleware.asgi2",
        "uvicorn.middleware.wsgi",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pydantic",
        "pydantic.deprecated.decorator",
        "starlette",
        "starlette.datastructures",
        "multipart",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.server",
        "websockets.legacy.client",
        "httptools",
        "click",
        "asyncio",
        "email",
        "email.mime",
        "email.mime.multipart",
        "email.mime.text",
        "email.mime.base",
        "socketserver",
        "http",
        "http.cookies",
        "http.client",
        "concurrent",
        "concurrent.futures",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        "distutils",
        "distutils.command",
        "setuptools",
        "pycparser",
        "cffi",
        "clr_loader",
        "pythonnet",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "cv2",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        "gi",
        "gtk",
        "pkg_resources",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ ─────────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ─────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DesktopAppTemplate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "assets" / "icon.icns") if (PROJECT_ROOT / "assets" / "icon.icns").is_file() else None,
)

# ── BUNDLE (.app) ───────────────────────────────────────────────────────
app = BUNDLE(
    exe,
    name="DesktopAppTemplate.app",
    icon=str(PROJECT_ROOT / "assets" / "icon.icns") if (PROJECT_ROOT / "assets" / "icon.icns").is_file() else None,
    display_name="Desktop App Template",
    version="1.0.0",
    bundle_identifier="com.example.desktopapptemplate",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticGraphicsSwitching": True,
        "LSBackgroundOnly": False,
        "LSUIElement": True,
    },
)
