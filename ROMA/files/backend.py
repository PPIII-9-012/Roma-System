"""
Backend Flask - sirve la web Y hace de proxy para Infoauto
==========================================================
    pip install flask flask-cors requests
    python backend.py   ->   http://localhost:5000
"""

from __future__ import annotations

import base64
import json
import threading
import time
import webbrowser

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

EMAIL = "federico.mallo@romaautos.com.ar"
PASSWORD = "Roma2026@"
BASE_URL = "https://api.infoauto.com.ar"
TOKEN_SAFETY_WINDOW = 120

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
}

tokens = {
    "access": None,
    "refresh": None,
    "access_exp": 0,
    "last_whoami": 0,
}


def _decode_jwt_payload(token):
    try:
        payload_part = token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        raw = base64.urlsafe_b64decode(payload_part + padding)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _store_access_token(token):
    tokens["access"] = token
    payload = _decode_jwt_payload(token or "")
    tokens["access_exp"] = int(payload.get("exp") or 0)


def _access_valid():
    if not tokens["access"]:
        return False
    exp = int(tokens.get("access_exp") or 0)
    if not exp:
        return True
    return time.time() < (exp - TOKEN_SAFETY_WINDOW)


def login():
    creds = base64.b64encode(f"{EMAIL}:{PASSWORD}".encode()).decode()
    r = requests.post(
        f"{BASE_URL}/cars/auth/login",
        headers={
            "Content-type": "application/json",
            "Authorization": f"Basic {creds}",
            **COMMON_HEADERS,
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    access = data.get("access_token") or data.get("accessToken")
    refresh = data.get("refresh_token") or data.get("refreshToken")
    if not access or not refresh:
        raise RuntimeError(f"Login sin tokens validos: {data}")

    _store_access_token(access)
    tokens["refresh"] = refresh
    tokens["last_whoami"] = 0
    print("Login Infoauto OK")


def refresh_access():
    if not tokens["refresh"]:
        return False

    r = requests.post(
        f"{BASE_URL}/cars/auth/refresh",
        headers={
            "Authorization": f"Bearer {tokens['refresh']}",
            **COMMON_HEADERS,
        },
        timeout=20,
    )
    if not r.ok:
        return False

    data = r.json()
    access = data.get("access_token") or data.get("accessToken")
    if not access:
        return False

    _store_access_token(access)
    tokens["last_whoami"] = 0
    return True


def whoami_ok():
    if not tokens["access"]:
        return False

    now = time.time()
    if now - float(tokens.get("last_whoami") or 0) < 30:
        return True

    r = requests.get(
        f"{BASE_URL}/cars/auth/whoami",
        headers={
            "Authorization": f"Bearer {tokens['access']}",
            **COMMON_HEADERS,
        },
        timeout=20,
    )
    if r.ok:
        tokens["last_whoami"] = now
        return True

    return False


def ensure_session():
    if _access_valid() and whoami_ok():
        return

    if _access_valid() and refresh_access():
        return

    login()


def api_get(endpoint, params=None):
    ensure_session()

    r = requests.get(
        f"{BASE_URL}{endpoint}",
        headers={
            "Authorization": f"Bearer {tokens['access']}",
            **COMMON_HEADERS,
        },
        params=params,
        timeout=20,
    )

    if r.status_code in (401, 403):
        tokens["access"] = None
        tokens["access_exp"] = 0

        if refresh_access():
            r = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {tokens['access']}",
                    **COMMON_HEADERS,
                },
                params=params,
                timeout=20,
            )

        if r.status_code in (401, 403):
            login()
            r = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={
                    "Authorization": f"Bearer {tokens['access']}",
                    **COMMON_HEADERS,
                },
                params=params,
                timeout=20,
            )

    return r


def api_public_get(endpoint, params=None):
    return requests.get(
        f"{BASE_URL}{endpoint}",
        headers=COMMON_HEADERS,
        params=params,
        timeout=20,
    )


def proxy_endpoint(endpoint, params=None):
    try:
        r = api_get(endpoint, params=params)
    except requests.RequestException as exc:
        return jsonify({"error": "No se pudo conectar con Infoauto", "detail": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": "Error inesperado al consultar Infoauto", "detail": str(exc)}), 500

    if r.status_code >= 400:
        detail = r.text
        try:
            detail = r.json()
        except Exception:
            pass

        print(f"Infoauto {r.status_code} en {endpoint}: {detail}")
        return jsonify(
            {
                "error": "Infoauto rechazo la peticion",
                "status": r.status_code,
                "detail": detail,
            }
        ), r.status_code

    try:
        data = r.json()
    except Exception:
        data = r.text
    return jsonify(data), r.status_code


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Parametro 'q' requerido"}), 400
    return proxy_endpoint(
        "/cars/pub/search/",
        params={"page": 1, "page_size": 20, "query_string": q},
    )


@app.route("/precios/<int:codia>")
def precios(codia):
    return proxy_endpoint(f"/cars/pub/models/{codia}/prices/")


@app.route("/ficha/<int:codia>")
def ficha(codia):
    return proxy_endpoint(f"/cars/pub/models/{codia}/features/")


@app.route("/equipamiento/<int:codia>")
def equipamiento(codia):
    return proxy_endpoint(f"/cars/pub/models/{codia}/features/")


@app.route("/as_codia/<int:codia>")
def as_codia(codia):
    return proxy_endpoint(f"/cars/pub/models/{codia}/as_codia")


if __name__ == "__main__":
    print("Backend listo en http://localhost:5000")
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000)
