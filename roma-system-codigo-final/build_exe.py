"""
Build Script — Generador de Ejecutable Standalone (PyInstaller + GUI Nativa)
Roma Automotores
"""

import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def create_ico_from_png():
    png_path = BASE_DIR / "logotiporoma.png"
    ico_path = BASE_DIR / "roma.ico"
    if png_path.exists():
        try:
            from PIL import Image
            img = Image.open(png_path)
            img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            return ico_path
        except Exception:
            return None
    return None

def build():
    # Cerrar cualquier instancia previa de RomaSystem
    try:
        subprocess.run(["powershell", "-Command", "Stop-Process -Name 'RomaSystem' -Force -ErrorAction SilentlyContinue"], capture_output=True)
    except Exception:
        pass

    ico_path = create_ico_from_png()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name", "RomaSystem",
        "--add-data", f"{BASE_DIR / 'templates'};templates",
        "--add-data", f"{BASE_DIR / 'login'};login",
        "--add-data", f"{BASE_DIR / 'auth.py'};.",
        "--add-data", f"{BASE_DIR / 'psa_pdf.py'};.",
        "--hidden-import", "flask",
        "--hidden-import", "flask_cors",
        "--hidden-import", "requests",
        "--hidden-import", "webview",
        "--hidden-import", "werkzeug",
        "--hidden-import", "certifi",
        "--hidden-import", "urllib3",
        "--hidden-import", "auth",
        "--hidden-import", "psa_pdf",
        "--hidden-import", "pypdf",
        "--hidden-import", "supabase",
        "--hidden-import", "supabase_auth",
        "--hidden-import", "supabase_functions",
        "--hidden-import", "postgrest",
        "--hidden-import", "realtime",
        "--hidden-import", "storage3",
        "--hidden-import", "httpx",
        "--hidden-import", "httpcore",
        "--hidden-import", "anyio",
        "--hidden-import", "sniffio",
        "--hidden-import", "h11",
        "--hidden-import", "websockets",
        "--collect-all", "webview",
        "--collect-all", "pypdf",
        "--collect-all", "certifi",
        "--collect-all", "requests",
        "--collect-all", "urllib3",
        "--collect-all", "supabase",
        "--collect-all", "supabase_auth",
        "--collect-all", "supabase_functions",
        "--collect-all", "postgrest",
        "--collect-all", "realtime",
        "--collect-all", "storage3",
        "--collect-all", "httpx",
        "--collect-all", "httpcore",
        "--copy-metadata", "requests",
        "--copy-metadata", "certifi",
        "--copy-metadata", "supabase",
        "--copy-metadata", "supabase-auth",
        "--copy-metadata", "postgrest",
        "--copy-metadata", "httpx",
    ]
    
    # Agregar index.html si existe en raíz
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        cmd.extend(["--add-data", f"{index_file};."])

    env_file = BASE_DIR / ".env"
    if env_file.exists():
        cmd.extend(["--add-data", f"{env_file};."])
    for img in BASE_DIR.glob("*.png"):
        cmd.extend(["--add-data", f"{img};."])
    for img in BASE_DIR.glob("*.jpg"):
        cmd.extend(["--add-data", f"{img};."])
    if ico_path and ico_path.exists():
        cmd.extend(["--icon", str(ico_path)])
        cmd.extend(["--add-data", f"{ico_path};."])
    cmd.append(str(BASE_DIR / "app_launcher.py"))
    
    subprocess.check_call(cmd, cwd=BASE_DIR)

if __name__ == "__main__":
    build()
