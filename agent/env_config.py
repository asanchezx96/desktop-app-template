"""
env_config.py — Configuración centralizada desde variables de entorno (.env).
Proporciona valores predeterminados para que el proyecto pueda ejecutarse
inmediatamente sin ningún .env presente.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Intentar leer version.txt si existe
try:
    _version_file = Path(__file__).resolve().parent.parent / "version.txt"
    if hasattr(sys, '_MEIPASS'):
        _version_file = Path(sys._MEIPASS) / "version.txt"
    with open(_version_file, "r", encoding="utf-8") as _f:
        APP_VERSION = _f.read().strip()
except Exception:
    APP_VERSION = "1.0.0"


# Resolver ruta de bundle de PyInstaller en produccion vs desarrollo
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundle_dir = Path(sys._MEIPASS)
else:
    bundle_dir = Path(__file__).resolve().parent.parent

env_path = bundle_dir / ".env"
env_local_path = bundle_dir / ".env.local"

if env_local_path.exists():
    load_dotenv(dotenv_path=str(env_local_path))
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de tipado
# ══════════════════════════════════════════════════════════════════════════════

def _optional(key: str, default: str = "") -> str:
    """Obtiene una variable de entorno opcional con valor por defecto."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    return val.strip()


def _optional_int(key: str, default: int) -> int:
    """Obtiene una variable de entorno opcional como entero."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val.strip())
    except ValueError:
        print(f"[WARN] La variable {key} debe ser un número entero. Usando default: {default}")
        return default


def _optional_bool(key: str, default: bool = False) -> bool:
    """Obtiene una variable de entorno opcional como booleano."""
    val = os.getenv(key, "").strip().lower()
    if val == "":
        return default
    return val in ("1", "true", "yes", "si")


# ══════════════════════════════════════════════════════════════════════════════
# Configuración del servidor local
# ══════════════════════════════════════════════════════════════════════════════

# Puerto del servidor web backend HTTP
SERVER_PORT = _optional_int("SERVER_PORT", 15050)

# Modo desarrollo: la ventana apunta al dev server de Vite en vez de al bundle
# ya compilado que sirve el propio backend (hot-reload al editar el frontend).
DEV_MODE = _optional_bool("DEV_MODE", False)
DEV_URL = _optional("DEV_URL", "http://localhost:15173")

# ══════════════════════════════════════════════════════════════════════════════
# Configuración Dinámica (Branding)
# ══════════════════════════════════════════════════════════════════════════════
# Estos tres valores son lo único que hay que tocar para renombrar la app
# resultante de este template (título de ventana, carpeta en AppData, tooltip
# de la bandeja del sistema). Sobrescríbelos en .env.
APP_NAME = _optional("APP_NAME", "DesktopAppTemplate")
APP_TITLE = _optional("APP_TITLE", "Desktop App Template")
TRAY_TOOLTIP = _optional("TRAY_TOOLTIP", "Desktop App Template")

