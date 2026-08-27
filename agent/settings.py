"""
agent/settings.py — Estado local persistente de la aplicación.

Por ahora solo guarda el token de autenticación local: es lo único que la
base necesita conservar entre sesiones (el tema de la interfaz vive en
localStorage, en el propio frontend).
"""

import json
import os
import logging
import secrets
import tempfile
from pathlib import Path

from agent.env_config import APP_NAME

logger = logging.getLogger(f"{APP_NAME}.settings")

# Guardar settings en ~/.{app_name}/settings.json (persistente entre sesiones)
_APP_DATA_DIR = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"
_APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = str(_APP_DATA_DIR / "settings.json")

# Clave interna usada para persistir el token de autenticación local.
_LOCAL_AUTH_TOKEN_KEY = "_local_auth_token"


def _atomic_write_json(path: str, data: dict):
    """Escribe JSON de forma atómica: escribe a un temporal en el mismo
    directorio y hace os.replace() para evitar corrupción ante un corte
    de energía o cierre abrupto a mitad de escritura."""
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".settings_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError as e:
        logger.warning("No se pudieron restringir permisos de %s: %s", path, e)


def _read_raw_settings_file() -> dict:
    """Lee el archivo settings.json completo (incluye claves internas)."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.exception("Error leyendo settings.json: %s", e)
    return {}


def get_or_create_local_auth_token() -> str:
    """
    Devuelve el token secreto local usado para autenticar al frontend embebido
    contra el backend FastAPI de esta misma máquina. Se genera una única vez
    de forma aleatoria y se persiste en settings.json.
    """
    data = _read_raw_settings_file()
    token = data.get(_LOCAL_AUTH_TOKEN_KEY)
    if isinstance(token, str) and len(token) >= 32:
        return token

    token = secrets.token_urlsafe(32)
    data[_LOCAL_AUTH_TOKEN_KEY] = token
    try:
        _atomic_write_json(SETTINGS_FILE, data)
    except Exception as e:
        logger.exception("Error persistiendo token de autenticación local: %s", e)
    return token
