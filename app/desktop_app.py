"""
desktop_app.py — Entry point de la aplicación de escritorio.
Orquesta:
  - Levanta el backend FastAPI en un hilo daemon.
  - Abre una ventana webview con el frontend React.
  - Icono en bandeja del sistema (system tray) para operar en segundo plano.
"""

import os
import sys
import threading
import time
import logging
import socket
from pathlib import Path

# ─── Force pythonnet to use .NET Framework (netfx) before anything loads CLR ─
if os.name == 'nt':
    os.environ['PYTHONNET_RUNTIME'] = 'netfx'
    try:
        import pythonnet
        pythonnet.load('netfx')
    except Exception as e:
        print(f"[WARN] No se pudo cargar pythonnet en modo netfx: {e}")

# ─── Pre-flight: verificar requisitos del sistema ────────────────────────
if os.name == 'nt':
    from preflight_check import run_preflight
    if not run_preflight():
        sys.exit(0)

import webview

# ─── Path resolution ────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    project_root = Path(sys.executable).parent
    sys.path.insert(0, str(project_root))
    bundled_root = Path(sys._MEIPASS)
else:
    # Este archivo vive en app/, un nivel por debajo de la raíz real del
    # proyecto (donde están los paquetes agent/ y src/).
    project_root = Path(os.path.abspath(__file__)).parent.parent
    sys.path.insert(0, str(project_root))
    bundled_root = project_root

from agent.env_config import APP_NAME, APP_TITLE, TRAY_TOOLTIP
from logging.handlers import RotatingFileHandler

ICON_PATH = bundled_root / "assets" / "icon.png"
if not ICON_PATH.is_file():
    ICON_PATH = bundled_root / "icon.png"

# On Windows/macOS, the app icon is set at build time by PyInstaller/BUNDLE.
# Passing a PNG to webview.start() crashes on Windows Forms, so we only pass it on Linux.
WEBVIEW_ICON = str(ICON_PATH) if (sys.platform.startswith('linux') and ICON_PATH.is_file()) else None

# ─── Global logs directory (AppData) ────────────────────────────────────
def _get_global_logs_dir():
    """Resuelve la carpeta global de logs en AppData o directorio personal."""
    if os.name == 'nt':
        app_data = Path(os.environ.get('APPDATA', '')) / APP_NAME
    else:
        app_data = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"
    return app_data / "logs"

log_dir = _get_global_logs_dir()
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"{APP_NAME.lower().replace(' ', '_')}.log"

_handler = RotatingFileHandler(str(log_file), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
logging.basicConfig(
    handlers=[_handler],
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger(f"{APP_NAME}Launcher").error(
        "Excepción no manejada", exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

logger = logging.getLogger(f"{APP_NAME}Launcher")
logger.info(f"--- Iniciando {APP_TITLE} ---")
logger.info(f"Raíz detectada: {project_root}")

# ─── Helpers ────────────────────────────────────────────────────────────
def check_port_open(host: str, port: int) -> bool:
    """Verifica si un puerto ya está en uso."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


def wait_for_server(url: str, timeout: int = 15) -> bool:
    """Espera a que el servidor backend esté listo."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                logger.info("¡Servidor backend listo!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(0.5)
    logger.warning("El servidor tardó demasiado en responder.")
    return False


def _navigation_url(base_url: str) -> str:
    """URL para que webview navegue, con un query param único por llamada.

    Solo se usa en las navegaciones reales (no en las llamadas API/tray, que
    necesitan la base limpia). WebView2 (Chromium) aplica cacheo heurístico a
    index.html cuando este no lleva Cache-Control —versiones previas del
    backend no lo enviaban—, y esa decisión de caché queda fijada a la URL
    exacta con la que se cargó: un index.html cacheado así sigue sirviéndose
    para siempre en cada reapertura de ventana, aunque el backend actual ya
    envíe no-store. Una URL distinta en cada navegación nunca coincide con
    una entrada de caché previa.
    """
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}launch={int(time.time() * 1000)}"


def run_server(port: int = 5050) -> str:
    """Inicia el servidor backend y retorna la URL."""
    from src.backend.server_app import start_server

    url = start_server("127.0.0.1", port)
    # El bind real es en 127.0.0.1 (sin cambios); solo se usa "localhost" como
    # host de navegación/redirect_uri porque se lee mejor en la barra de
    # direcciones del navegador durante el flujo OAuth2 de nube.
    url = url.replace("127.0.0.1", "localhost")
    logger.info(f"Servidor backend iniciado en {url}")
    return url


# ─── Ciclo de vida de la ventana (hide-to-tray) ─────────────────────────
# Cerrar la ventana no termina el proceso: se oculta y la app sigue viva en
# el área de notificación. Es obligatorio vetar el cierre en vez de dejar que
# la ventana se destruya, porque uvicorn y la bandeja corren en hilos daemon
# de este proceso: en cuanto webview.start() retorna, el intérprete los mata
# a todos.
_quitting = threading.Event()
# Sin icono en la bandeja no hay forma de recuperar una ventana oculta: si el
# tray no llega a arrancar, cerrar la ventana vuelve a terminar la app.
_tray_ready = threading.Event()
_tray_icon = None
_window_minimized = False
_hide_notice_shown = False


def _show_main_window():
    """Trae la ventana al frente desde la bandeja.

    Seguro desde cualquier hilo: el backend WinForms de pywebview hace el
    marshalling al hilo de UI.
    """
    if not webview.windows:
        logger.warning("Se pidió mostrar la ventana, pero no hay ninguna creada.")
        return
    window = webview.windows[0]
    try:
        window.show()
        # restore() fuerza WindowState = Normal, así que solo se llama cuando la
        # ventana está realmente minimizada; si no, reabrir desde la bandeja
        # desmaximizaría la ventana que el usuario dejó maximizada.
        if _window_minimized:
            window.restore()
    except Exception as e:
        logger.exception(f"Error al mostrar la ventana desde la bandeja: {e}")


def _notify_running_in_background():
    """Avisa una sola vez de que la app sigue viva tras cerrar la ventana.

    Sin este aviso, una ventana que desaparece sin dejar rastro se percibe como
    un cierre normal y el usuario no busca el icono en la bandeja.
    """
    global _hide_notice_shown
    if _hide_notice_shown or _tray_icon is None:
        return
    _hide_notice_shown = True
    try:
        _tray_icon.notify(
            f"El agente {APP_NAME} sigue activo en segundo plano. Ábrelo desde este icono "
            "o usa «Salir» para cerrarlo del todo.",
            APP_TITLE,
        )
    except Exception as e:
        logger.info(f"No se pudo mostrar la notificación de bandeja: {e}")


def _hide_main_window():
    try:
        if webview.windows:
            webview.windows[0].hide()
    except Exception as e:
        logger.exception(f"Error al ocultar la ventana: {e}")
    _notify_running_in_background()


def _on_window_closing():
    """Handler de events.closing: veta el cierre y esconde la ventana.

    Devolver False cancela el cierre en pywebview. Solo «Salir» desde la bandeja
    marca _quitting, y entonces el cierre se deja pasar.
    """
    if _quitting.is_set() or not _tray_ready.is_set():
        return True

    # El ocultado se delega a otro hilo: este handler se ejecuta dentro del
    # FormClosing del hilo de UI y debe devolver el veto cuanto antes.
    threading.Thread(target=_hide_main_window, daemon=True).start()
    return False


def _on_window_minimized():
    global _window_minimized
    _window_minimized = True


def _on_window_restored():
    global _window_minimized
    _window_minimized = False


def _attach_window_events(window):
    window.events.closing += _on_window_closing
    window.events.minimized += _on_window_minimized
    window.events.restored += _on_window_restored
    window.events.maximized += _on_window_restored


def _try_focus_our_instance(port: int) -> tuple[bool, bool]:
    """Pide a la instancia ya abierta que muestre su ventana.

    Devuelve (es_nuestra_app, fue_enfocada).
    Si el puerto está ocupado por OTRA aplicación (Token 401), devuelve False, False.
    """
    try:
        import requests as req
        from agent.settings import get_or_create_local_auth_token

        resp = req.post(
            f"http://127.0.0.1:{port}/api/window/show",
            headers={"X-Local-Auth-Token": get_or_create_local_auth_token()},
            timeout=3,
        )
        if resp.status_code == 401:
            return False, False
        if resp.status_code == 200:
            return True, resp.json().get("ok") is True
        return False, False
    except Exception as e:
        logger.info(f"No se pudo contactar con una instancia previa en el puerto {port}: {e}")
        return False, False


# ─── System Tray ────────────────────────────────────────────────────────
def _make_tray_image(color=None):
    """Carga el logo del proyecto para la bandeja del sistema, con fallback circular."""
    try:
        from PIL import Image
        if ICON_PATH.is_file():
            return Image.open(ICON_PATH)
            
        # Fallback alternativo en CWD
        icon_path_alt = Path(os.getcwd()) / "icon.png"
        if icon_path_alt.is_file():
            return Image.open(icon_path_alt)
    except Exception as e:
        logger.warning(f"No se pudo cargar icon.png para el tray: {e}")

    # Fallback circular
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill_color = color or "#00D4FF"
        draw.ellipse([4, 4, 60, 60], fill=fill_color, outline="#ffffff", width=2)
        return img
    except ImportError:
        return None


def setup_tray():
    """Configura y ejecuta el icono de bandeja del sistema."""
    try:
        import pystray
        from pystray import MenuItem as TrayItem
    except ImportError:
        logger.warning("pystray no instalado. Omitiendo system tray.")
        return
    except Exception as e:
        logger.warning(f"Error importando pystray: {e}. Omitiendo system tray.")
        return

    def _open_window(icon=None, item=None):
        """Muestra la ventana desde la bandeja.

        La ventana ya no se destruye al cerrarla (solo se oculta), así que basta
        con volver a mostrarla: no hay que recrearla ni lanzar un segundo
        webview.start(), que en Windows exige el hilo principal.
        """
        _show_main_window()

    def _quit(icon, item):
        logger.info(f"Cerrando {APP_NAME} desde la bandeja del sistema.")
        # Levanta el veto de _on_window_closing: esta es la única vía por la que
        # el cierre de la ventana debe terminar el proceso.
        _quitting.set()
        try:
            icon.stop()
        except Exception as e:
            logger.exception(f"Error al detener el icono de la bandeja: {e}")
        try:
            # Destruir las ventanas webview hace que webview.start() retorne
            # en el hilo principal, permitiendo una salida natural del
            # programa. Se usa como mecanismo primario de cierre ordenado.
            for w in list(webview.windows):
                try:
                    w.destroy()
                except Exception:
                    pass
        except Exception as e:
            logger.exception(f"Error cerrando ventanas webview: {e}")

        # Red de seguridad: si tras un breve margen el proceso sigue vivo
        # (p.ej. algún hilo no-daemon quedó colgado), forzar la terminación.
        def _force_exit_if_still_alive():
            time.sleep(2.0)
            logger.warning("El proceso no terminó tras el cierre ordenado; forzando salida.")
            os._exit(0)

        threading.Thread(target=_force_exit_if_still_alive, daemon=True).start()

    menu = pystray.Menu(
        TrayItem("Abrir ventana", _open_window, default=True),
        pystray.Menu.SEPARATOR,
        TrayItem("Salir", _quit),
    )

    try:
        global _tray_icon
        icon = pystray.Icon(
            APP_NAME,
            _make_tray_image("#00D4FF"),
            TRAY_TOOLTIP,
            menu,
        )
        _tray_icon = icon
        _tray_ready.set()
        icon.run()
    except Exception as e:
        _tray_ready.clear()
        logger.warning(f"Error al iniciar system tray: {e}. La app continúa sin icono en la bandeja.")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # ── Detectar modo DEV ────────────────────────────────────────────────
    from agent.env_config import DEV_MODE, DEV_URL, SERVER_PORT as ENV_SERVER_PORT

    backend_port = ENV_SERVER_PORT
    server_already_running = check_port_open("127.0.0.1", backend_port)
    is_our_app = False

    if server_already_running:
        is_our_app, focused = _try_focus_our_instance(backend_port)
        if is_our_app:
            if focused:
                logger.info("Ya había una instancia en la bandeja; se le pidió mostrar su ventana.")
                sys.exit(0)
            else:
                logger.info(f"Nuestra instancia está en el puerto {backend_port}, pero sin ventana.")
        else:
            logger.info(f"El puerto {backend_port} está ocupado por otra aplicación. Se lanzará un nuevo servidor.")

    if not is_our_app:
        backend_url = run_server(backend_port)
        wait_for_server(backend_url)
        
        # Extraemos el nuevo puerto real por si run_server lo cambió
        from urllib.parse import urlparse
        backend_port = urlparse(backend_url).port
        
        # Deja que /api/window/show pueda sacar esta ventana de la bandeja.
        try:
            from src.backend.server_app import set_window_controller
            set_window_controller(_show_main_window)
        except Exception as e:
            logger.warning(f"No se pudo registrar el controlador de ventana: {e}")
    else:
        logger.info(f"Usando nuestra instancia de backend existente en puerto {backend_port}.")

    if DEV_MODE:
        # Modo desarrollo: pywebview apunta al Vite dev server
        url = DEV_URL
        logger.info(f"Modo DEV: pywebview -> {url} (Vite HMR)")
        logger.info(f"Esperando dev server de Vite en {DEV_URL}...")
        wait_for_server(DEV_URL, timeout=10)
    else:
        url = f"http://localhost:{backend_port}"

    # ── System tray en hilo separado ─────────────────────────────────────
    threading.Thread(target=setup_tray, daemon=True).start()

    # ── Abrir ventana principal ──────────────────────────────────────────
    logger.info(f"Abriendo ventana webview. Logs en: {log_dir}")
    window = webview.create_window(
        APP_TITLE,
        _navigation_url(url),
        width=820,
        height=580,
        min_size=(720, 500),
        background_color='#0D0F14',
        maximized=True
    )
    _attach_window_events(window)
    webview.start(icon=WEBVIEW_ICON)
