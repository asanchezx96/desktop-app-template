"""
server_app.py — Backend FastAPI + WebSocket de la aplicación.
Define la app FastAPI, un canal WebSocket autenticado de eventos en tiempo
real y la API REST base (bootstrap de auth, control de ventana, estáticos).
"""

import os
import sys
import time
import queue
import asyncio
from starlette.concurrency import run_in_threadpool
import logging
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from agent.settings import get_or_create_local_auth_token
from agent.env_config import APP_NAME

load_dotenv()

logger = logging.getLogger(f"{APP_NAME}.server")


# ─── Token de autenticación local (C1) ──────────────────────────────────
# Generado/persistido una única vez por instalación (ver agent/settings.py)
# (clave interna, nunca expuesta). El frontend embebido lo obtiene una sola vez
# a través de /api/bootstrap/token al arrancar y lo adjunta en el header
# X-Local-Auth-Token en todas las llamadas subsiguientes.
LOCAL_AUTH_TOKEN = get_or_create_local_auth_token()
LOCAL_AUTH_HEADER = "x-local-auth-token"


async def require_local_auth(request: Request):
    """Dependency de FastAPI: exige el token secreto local en el header
    X-Local-Auth-Token para cualquier endpoint /api/* sensible."""
    provided = request.headers.get(LOCAL_AUTH_HEADER, "")
    if not provided or not secrets_compare(provided, LOCAL_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Token de autenticación local inválido o ausente")


def secrets_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


# ─── Path resolution (PyInstaller vs source) ───────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_frontend_dist() -> str:
    """Resuelve la carpeta frontend/dist con múltiples fallbacks."""
    candidates = [
        os.path.join(BASE_DIR, "frontend", "dist"),
        os.path.join(os.getcwd(), "src", "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "frontend", "dist"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


STATIC_DIR = resolve_frontend_dist()

_log_queue = queue.Queue()
_ws_clients: set = set()


# ─── Helpers ────────────────────────────────────────────────────────────
async def _broadcast_log(msg: str, tag: str = "info", extra: Optional[dict] = None):
    """Envía un log a todos los WebSocket conectados."""
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] [{tag.upper()}] {msg}")
    except UnicodeEncodeError:
        print(f"[{ts}] [{tag.upper()}] {msg.encode('ascii', 'replace').decode('ascii')}")
    except Exception:
        pass  # sin consola (pythonw) el print no debe tumbar el broadcast
    payload = {"ts": ts, "msg": msg, "tag": tag}
    if extra:
        payload.update(extra)
    dead = set()
    # Copia del set: `send_json` cede el control y, si mientras tanto alguien
    # abre otro WebSocket (p.ej. al abrir la consola de un proceso), iterar el
    # set original lanzaba "Set changed size during iteration".
    for ws in list(_ws_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ─── Background log broadcaster ─────────────────────────────────────────
async def _log_broadcaster():
    """Drena la cola de mensajes en background y los envía por WebSocket."""
    while True:
        try:
            while True:
                msg, tag, extra = _log_queue.get_nowait()
                await _broadcast_log(msg, tag, extra)
        except queue.Empty:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            # Esta tarea es la única vía de logs en tiempo real: si muere, la
            # interfaz se queda congelada hasta reiniciar la app. Ningún
            # fallo puntual de un envío puede terminarla.
            logger.exception("Error emitiendo logs por WebSocket; el broadcaster continúa")
        await asyncio.sleep(0.1)


def broadcast_from_thread(msg: str, tag: str = "info", extra: Optional[dict] = None):
    """Puente hilo→asyncio: permite que código corriendo en un hilo síncrono
    (p.ej. un worker que lee stdout de un subproceso) encole un mensaje para
    que _log_broadcaster lo envíe por WebSocket desde el event loop."""
    _log_queue.put((msg, tag, extra))


# ─── Lifespan ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_log_broadcaster())
    yield


app = FastAPI(lifespan=lifespan)

# ─── Middlewares ────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS restringido a orígenes locales conocidos de la propia app (C1).
# Nunca "*" combinado con allow_credentials=True: cualquier pestaña de
# navegador en la misma máquina podría, si no, leer la API local. Solo se
# permiten los orígenes localhost/127.0.0.1 usados por el webview embebido y
# por el servidor de desarrollo de Vite.
_CORS_ALLOWED_ORIGINS = [
    f"http://127.0.0.1:{p}" for p in range(5050, 5200)
] + [
    f"http://localhost:{p}" for p in range(5050, 5200)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════
#  WebSocket — streaming de logs en tiempo real
# ══════════════════════════════════════════════════════════════════════════
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # Los WebSocket no pueden llevar el header X-Local-Auth-Token habitual
    # (el navegador no permite headers custom en el handshake), así que el
    # token viaja como query param. Sin esto, cualquier página abierta en el
    # navegador del usuario podía conectarse a ws://127.0.0.1:<puerto>/ws y
    # recibir en tiempo real los logs (rutas locales, comandos, etc.)
    # sin necesitar el token secreto local.
    provided_token = ws.query_params.get("token", "")
    origin = ws.headers.get("origin", "")
    if not secrets_compare(provided_token, LOCAL_AUTH_TOKEN) or (origin and origin not in _CORS_ALLOWED_ORIGINS):
        await ws.close(code=1008)  # Policy Violation
        return

    await ws.accept()
    _ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(ws)


# ══════════════════════════════════════════════════════════════════════════
#  REST API
# ══════════════════════════════════════════════════════════════════════════

# ── Bootstrap (única ruta /api/* sin autenticación) ─────────────────────
# Sirve el token local al frontend embebido para que pueda adjuntarlo en
# todas las llamadas subsiguientes. Al estar el CORS restringido a los
# orígenes propios de la app (ver _CORS_ALLOWED_ORIGINS), ninguna pestaña
# de navegador externa puede leer la respuesta de este endpoint gracias a
# la Same-Origin Policy (el navegador bloquea la lectura de la respuesta
# aunque la petición llegue a dispararse).
@app.get("/api/bootstrap/token")
async def bootstrap_token():
    return {"token": LOCAL_AUTH_TOKEN}


# ── Control de la ventana de escritorio (instancia única) ──────────────
_window_controller = None


def set_window_controller(callback):
    """Registra la función que saca la ventana de la bandeja.

    La llama desktop_app al arrancar. Si el backend corre suelto (desarrollo),
    no hay ninguna registrada y /api/window/show lo dice explícitamente, para
    que quien pregunte sepa que debe abrir su propia ventana.
    """
    global _window_controller
    _window_controller = callback


@app.post("/api/window/show", dependencies=[Depends(require_local_auth)])
async def window_show():
    """Trae al frente la ventana de la instancia ya en ejecución."""
    if _window_controller is None:
        return {"ok": False, "reason": "no_window"}
    try:
        await run_in_threadpool(_window_controller)
        return {"ok": True}
    except Exception as e:
        logger.exception("No se pudo mostrar la ventana del escritorio")
        return {"ok": False, "reason": str(e)}


# ══════════════════════════════════════════════════════════════════════════
#  Static files (React SPA)
# ══════════════════════════════════════════════════════════════════════════
if os.path.isdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        """SPA fallback: cualquier ruta no API sirve index.html."""
        if full_path and full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = os.path.join(STATIC_DIR, full_path) if full_path else ""
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            # no-store: el webview cacheaba index.html y seguía pidiendo el
            # bundle anterior tras cada build, dejando la interfaz desfasada
            # respecto al backend. Los assets sí se cachean: llevan hash.
            return FileResponse(index_path, headers={"Cache-Control": "no-store, must-revalidate"})
        return {"error": "Frontend no encontrado"}
else:
    @app.get("/")
    async def no_frontend():
        return {
            "error": "Frontend no construido",
            "hint": "Ejecuta 'npm run build' en src/frontend/",
        }


# ══════════════════════════════════════════════════════════════════════════
#  Server starter (para ser llamado desde desktop_app.py o CLI)
# ══════════════════════════════════════════════════════════════════════════
def _find_available_port(host: str, start_port: int, max_attempts: int = 20) -> int:
    """Busca un puerto disponible a partir de start_port intentando hacer bind."""
    import socket

    for offset in range(max_attempts):
        port = start_port + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return port
        except OSError:
            continue
    return start_port


def _write_env_local(port: int):
    """Persiste el puerto elegido en .env.local para que el frontend y los
    siguientes arranques usen el mismo."""
    try:
        if getattr(sys, "frozen", False):
            env_local_path = os.path.join(os.path.dirname(sys.executable), ".env.local")
        else:
            env_local_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                ".env.local",
            )

        lines = []
        if os.path.exists(env_local_path):
            with open(env_local_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = []
        port_written = False
        for line in lines:
            if line.strip().startswith("SERVER_PORT="):
                new_lines.append(f"SERVER_PORT={port}\n")
                port_written = True
            else:
                new_lines.append(line)

        if not port_written:
            new_lines.append(f"SERVER_PORT={port}\n")

        with open(env_local_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print(f"[ENV] Guardado SERVER_PORT={port} en {env_local_path}")
    except Exception as e:
        print(f"[WARN] No se pudo escribir en .env.local: {e}")


def start_server(host: str = "127.0.0.1", port: int = 5050) -> str:
    """Inicia uvicorn en un hilo y espera a que esté listo. Retorna la URL."""
    import socket as sock_module
    import threading

    port = _find_available_port(host, port)
    _write_env_local(port)
    url = f"http://{host}:{port}"

    t = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": host, "port": port, "log_level": "info"},
        daemon=True,
    )
    t.start()

    # Esperar a que el servidor esté listo
    start = time.time()
    timeout = 15
    while time.time() - start < timeout:
        try:
            with sock_module.create_connection((host, port), timeout=1):
                print(f"[SERVER] Servidor listo en {url}")
                break
        except (sock_module.timeout, ConnectionRefusedError):
            time.sleep(0.5)
    else:
        print(f"[WARN] El servidor tardó más de {timeout}s en responder")

    return url


if __name__ == "__main__":
    from agent.env_config import SERVER_PORT

    host = "127.0.0.1"
    port = _find_available_port(host, SERVER_PORT)
    _write_env_local(port)

    print(f"Iniciando servidor FastAPI en {host}:{port}...")

    uvicorn.run(
        "src.backend.server_app:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))]
    )
