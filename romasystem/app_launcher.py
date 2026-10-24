"""
App Launcher — Roma Automotores (Native Desktop Window)
Inicia el servidor interno blindado y abre la ventana nativa de escritorio.
"""

import os
import sys

class NullOrFileStream:
    def __init__(self, filepath=None):
        self.f = None
        if filepath:
            try:
                self.f = open(filepath, "a", encoding="utf-8", errors="replace")
            except Exception:
                pass

    def write(self, s):
        if self.f:
            try:
                self.f.write(s)
                self.f.flush()
            except Exception:
                pass

    def flush(self):
        if self.f:
            try:
                self.f.flush()
            except Exception:
                pass

    def isatty(self):
        return False

# Protección fundamental para modo --noconsole
base_dir_app = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(base_dir_app, "roma_backend.log")
safe_stream = NullOrFileStream(log_file)

if sys.stdout is None or getattr(sys.stdout, "closed", False):
    sys.stdout = safe_stream
if sys.stderr is None or getattr(sys.stderr, "closed", False):
    sys.stderr = safe_stream

import socket
import threading
import time
import urllib.request
import webview
from werkzeug.serving import make_server

from backend import app, login


def buscar_puerto_libre(puerto_inicial: int = 5050) -> int:
    for p in range(puerto_inicial, puerto_inicial + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return puerto_inicial


class ServerThread(threading.Thread):
    def __init__(self, app, port):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", port, app, threaded=True)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def login_asincrono():
    try:
        login()
    except Exception:
        pass


def main():
    puerto = buscar_puerto_libre(5050)
    url = f"http://127.0.0.1:{puerto}"

    # Iniciar login en segundo plano
    threading.Thread(target=login_asincrono, daemon=True).start()

    # Iniciar servidor WSGI interno
    server_thread = ServerThread(app, puerto)
    server_thread.start()

    # Esperar confirmación de que el servidor responde
    listo = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"{url}/", timeout=1.0) as resp:
                if resp.status == 200:
                    listo = True
                    break
        except Exception:
            time.sleep(0.1)

    # Crear y abrir ventana nativa de escritorio
    webview.create_window(
        title="Roma Automotores — Sistema Comercial & Cotizador Prendario",
        url=url,
        width=1366,
        height=860,
        min_size=(1024, 700),
        text_select=True,
        zoomable=True
    )

    webview.start(gui="edgechromium")
    
    # Apagar servidor al cerrar la ventana
    server_thread.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
