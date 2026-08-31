"""
START — Roma Automotores (roma-2)
Levanta el backend unificado y abre el navegador
=================================================
    python start.py
"""

import subprocess
import sys
import time
import webbrowser
import os
import urllib.request

# Configurar stdout para evitar problemas con codificación en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PUERTO = int(os.environ.get("PORT", 5050))


def instalar_dependencias():
    paquetes = ["flask", "flask-cors", "requests"]
    print("[*] Verificando dependencias...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", *paquetes, "-q"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("[OK] Dependencias listas.")


def esperar_backend(intentos=15):
    print(f"[*] Esperando que el backend levante en puerto {PUERTO}...", end="", flush=True)
    for _ in range(intentos):
        try:
            urllib.request.urlopen(f"http://localhost:{PUERTO}/planes", timeout=2)
            print(" Listo!")
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(1)
    print(" Timeout.")
    return False


def main():
    print("=" * 60)
    print("   ROMA AUTOMOTORES (roma-2) - PRENDARIOS & INFOAUTO")
    print("=" * 60 + "\n")

    instalar_dependencias()

    # Arrancar el backend en proceso separado
    print("[*] Arrancando backend Flask...")
    backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend.py")
    proc = subprocess.Popen(
        [sys.executable, backend_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # Esperar a que esté listo
    if esperar_backend():
        print(f"[*] Abriendo la plataforma web en http://localhost:{PUERTO} ...\n")
        webbrowser.open(f"http://localhost:{PUERTO}")
        print("  Todo corriendo. Presiona Ctrl+C para apagar el servidor.\n")
    else:
        print("[ERROR] El backend no respondio a tiempo. Logs:\n")

    # Mostrar logs del backend en tiempo real
    try:
        for linea in proc.stdout:
            print(f"  [backend] {linea}", end="")
    except KeyboardInterrupt:
        print("\n\n[*] Cerrando...")
        proc.terminate()


if __name__ == "__main__":
    main()
