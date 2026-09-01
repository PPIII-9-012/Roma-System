"""
Backend Flask — Roma Automotores (roma-2)
Proxy Infoauto + Motor de cálculo prendario PSA Finance
"""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

# Configurar stdout seguro para evitar problemas con codificación cp1252 en Windows
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from flask import Flask, jsonify, request, send_from_directory, render_template, redirect, url_for, session
from flask_cors import CORS
from auth import authenticate_user

def _load_env():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'").strip('"')
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env()

app = Flask(
    __name__,
    static_folder="login/static",
    static_url_path="/static",
    template_folder="login/templates"
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
CORS(app)


# ---------------------------------------------------------------------------
# CONFIGURACIÓN INFOAUTO
EMAIL = os.environ.get("INFOAUTO_EMAIL", "")
PASSWORD = os.environ.get("INFOAUTO_PASSWORD", "")
BASE_URL = os.environ.get("INFOAUTO_BASE_URL", "https://api.infoauto.com.ar")
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
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Credenciales INFOAUTO_EMAIL o INFOAUTO_PASSWORD no configuradas en .env")
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
    print("[OK] Login Infoauto exitoso")


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

        print(f"[WARN] Infoauto {r.status_code} en {endpoint}: {detail}")
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




# ---------------------------------------------------------------------------
# TABLA OFICIAL PSA FINANCE JUNIO 2026
# ---------------------------------------------------------------------------
TABLA_PSA: dict = {
    "PROMO_FIJA": {
        "nombre": "Promo Fija Usados",
        "tipo": "fijo",
        "max_prestamo": 12_000_000,
        "plazos": {
            12: {"tna": 0.000, "factor": 83.33, "ce": 0.10},
            18: {"tna": 0.199, "factor": 68.20, "ce": 0.10},
            24: {"tna": 0.269, "factor": 59.04, "ce": 0.10},
            36: {"tna": 0.329, "factor": 49.81, "ce": 0.10},
        },
    },
    "TRADICIONAL_VO": {
        "nombre": "Tradicional VO",
        "tipo": "fijo",
        "max_prestamo": None,
        "plazos": {
            12: {"tna": 0.475, "factor": 114.61, "ce": 0.025},
            18: {"tna": 0.475, "factor": 87.04,  "ce": 0.010},
            24: {"tna": 0.475, "factor": 73.62,  "ce": 0.010},
            36: {"tna": 0.475, "factor": 60.89,  "ce": 0.000},
            48: {"tna": 0.475, "factor": 55.17,  "ce": 0.000},
            60: {"tna": 0.475, "factor": 52.17,  "ce": 0.000},
        },
    },
    "TRADICIONAL_VO10": {
        "nombre": "Tradicional VO 10%",
        "tipo": "fijo",
        "max_prestamo": None,
        "plazos": {
            12: {"tna": 0.235, "factor": 98.43, "ce": 0.10},
            18: {"tna": 0.305, "factor": 75.26, "ce": 0.10},
            24: {"tna": 0.345, "factor": 64.29, "ce": 0.10},
            36: {"tna": 0.385, "factor": 53.98, "ce": 0.10},
            48: {"tna": 0.395, "factor": 48.65, "ce": 0.10},
            60: {"tna": 0.415, "factor": 47.02, "ce": 0.10},
        },
    },
    "PROMO_UVA": {
        "nombre": "Promo UVA VO",
        "tipo": "uva",
        "max_prestamo": 17_000_000,
        "plazos": {
            12: {"tna": 0.000, "factor": 83.33, "ce": 0.06},
            24: {"tna": 0.069, "factor": 45.93, "ce": 0.06},
            36: {"tna": 0.099, "factor": 33.95, "ce": 0.06},
        },
    },
    "UVA_TRAD": {
        "nombre": "UVA Tradicional VO",
        "tipo": "uva",
        "max_prestamo": 40_000_000,
        "plazos": {
            12: {"tna": 0.249, "factor": 99.35, "ce": 0.00},
            24: {"tna": 0.249, "factor": 57.68, "ce": 0.00},
            36: {"tna": 0.249, "factor": 44.06, "ce": 0.00},
            48: {"tna": 0.249, "factor": 37.46, "ce": 0.00},
            60: {"tna": 0.249, "factor": 33.65, "ce": 0.00},
        },
    },
    "UVA_TRAD10": {
        "nombre": "UVA Tradicional 10%",
        "tipo": "uva",
        "max_prestamo": 40_000_000,
        "plazos": {
            12: {"tna": 0.069, "factor": 87.69, "ce": 0.10},
            24: {"tna": 0.159, "factor": 51.70, "ce": 0.10},
            36: {"tna": 0.179, "factor": 39.23, "ce": 0.10},
            48: {"tna": 0.189, "factor": 33.15, "ce": 0.10},
            60: {"tna": 0.189, "factor": 29.19, "ce": 0.10},
        },
    },
}

IVA = 1.21          # IVA 21%
RCI_MAX_FIJO = 0.50  # Límite cuota/ingreso fijos
RCI_MAX_UVA  = 0.30  # Límite cuota/ingreso UVA


@dataclass
class ResultadoCredito:
    plan_key:         str
    plan_nombre:      str
    plan_tipo:        str
    tna:              float
    tna_pct:          float
    plazo:            int
    cuota_pura:       float
    quebranto_neto:   float
    quebranto_iva:    float
    primera_cuota:    float
    total_pagado:     float
    costo_financiero: float
    max_por_ltv:      float
    rci:              Optional[float]
    rci_pct:          Optional[float]
    rci_estado:       str
    efectivo_salon:   float
    disponible:       bool
    errores:          list = field(default_factory=list)


def calcular_antiguedad(anio_auto: int) -> int:
    if not anio_auto:
        return 0
    return max(0, date.today().year - int(anio_auto))


def calcular_max_ltv(antiguedad: int, precio_auto: float) -> float:
    """
    Calcula el monto máximo financiable según la política de LTV de PSA Finance sobre la unidad financiada.
      0 años (0km) → sin límite por tabla de usados (tope general $50M)
      1-3 años     → 80% del valor, tope $50M
      4-7 años     → 75% del valor, tope $30M
      8-10 años    → 50% del valor, tope $15M
      +10 años     → no financia (devuelve 0)
    """
    if antiguedad == 0:
        return 50_000_000
    elif antiguedad <= 3:
        return min(precio_auto * 0.80, 50_000_000)
    elif antiguedad <= 7:
        return min(precio_auto * 0.75, 30_000_000)
    elif antiguedad <= 10:
        return min(precio_auto * 0.50, 15_000_000)
    else:
        return 0.0


def calcular_max_plazo(antiguedad: int) -> int:
    """
    Devuelve el plazo máximo permitido según la antigüedad del auto financiado.
    """
    if antiguedad <= 7:
        return 60
    elif antiguedad == 8:
        return 48
    elif antiguedad == 9:
        return 36
    elif antiguedad == 10:
        return 24
    else:
        return 0


def calcular_credito(
    plan_key:       str,
    plazo:          int,
    monto:          float,
    precio_nuevo:   float,
    anio_nuevo:     int = 2026,
    gastos_transf:  float = 0.0,
    precio_toma:    float = 0.0,
    anio_usado:     int = 0,
    precio_revista: float = 0.0,
    ingresos:       float = 0.0,
) -> ResultadoCredito:
    errores = []

    if plan_key not in TABLA_PSA:
        raise ValueError(f"Plan '{plan_key}' no existe en TABLA_PSA.")

    plan = TABLA_PSA[plan_key]

    if plazo not in plan["plazos"]:
        raise ValueError(
            f"Plazo {plazo} no disponible para '{plan['nombre']}'. "
            f"Opciones: {sorted(plan['plazos'].keys())}"
        )

    datos_plazo = plan["plazos"][plazo]
    tna         = datos_plazo["tna"]
    factor      = datos_plazo["factor"]
    ce          = datos_plazo["ce"]

    # 1. Antigüedad y LTV del vehículo FINANCIADO (a comprar)
    antiguedad_financiado = calcular_antiguedad(anio_nuevo) if anio_nuevo else 0
    max_ltv = calcular_max_ltv(antiguedad_financiado, precio_nuevo) if precio_nuevo > 0 else float('inf')
    max_plazo = calcular_max_plazo(antiguedad_financiado) if anio_nuevo else 60

    if antiguedad_financiado > 10:
        errores.append(
            f"El vehículo a financiar tiene {antiguedad_financiado} años de antigüedad. "
            "PSA Finance no financia autos con más de 10 años."
        )

    if plazo > max_plazo and max_plazo > 0:
        errores.append(
            f"El plazo máximo para financiar un auto de {antiguedad_financiado} años es {max_plazo} meses. "
            f"Plazo solicitado: {plazo} meses."
        )

    if precio_nuevo > 0 and monto > max_ltv and max_ltv > 0 and antiguedad_financiado > 0:
        errores.append(
            f"El monto solicitado (${monto:,.0f}) supera el máximo LTV "
            f"permitido (${max_ltv:,.0f}) para este vehículo."
        )

    # 2. Tope del plan
    max_plan = plan.get("max_prestamo")
    if max_plan and monto > max_plan:
        errores.append(
            f"El monto solicitado (${monto:,.0f}) supera el tope del plan "
            f"'{plan['nombre']}' (${max_plan:,.0f})."
        )

    # 3. Cuotas
    cuota_pura = (monto / 1000.0) * factor
    quebranto_neto = monto * ce
    quebranto_iva  = quebranto_neto * IVA
    primera_cuota  = cuota_pura + quebranto_iva
    total_pagado     = (cuota_pura * plazo) + quebranto_iva
    costo_financiero = total_pagado - monto

    # 4. RCI
    if ingresos > 0:
        rci    = cuota_pura / ingresos
        limite = RCI_MAX_UVA if plan["tipo"] == "uva" else RCI_MAX_FIJO
        if rci <= limite:
            rci_estado = "ok"
        elif plan["tipo"] == "uva":
            rci_estado = "rechazado"
            errores.append(
                f"La cuota (${cuota_pura:,.0f}) representa el {rci*100:.1f}% de los ingresos. "
                f"Límite UVA: {RCI_MAX_UVA*100:.0f}%."
            )
        else:
            rci_estado = "alerta"
    else:
        rci        = None
        rci_estado = "sin_datos"

    # 5. Efectivo en salón
    efectivo_salon = (precio_nuevo + gastos_transf) - precio_toma - monto
    efectivo_salon = max(efectivo_salon, 0)

    return ResultadoCredito(
        plan_key         = plan_key,
        plan_nombre      = plan["nombre"],
        plan_tipo        = plan["tipo"],
        tna              = tna,
        tna_pct          = round(tna * 100, 2),
        plazo            = plazo,
        cuota_pura       = round(cuota_pura, 2),
        quebranto_neto   = round(quebranto_neto, 2),
        quebranto_iva    = round(quebranto_iva, 2),
        primera_cuota    = round(primera_cuota, 2),
        total_pagado     = round(total_pagado, 2),
        costo_financiero = round(costo_financiero, 2),
        max_por_ltv      = round(max_ltv, 2) if max_ltv != float('inf') else 0.0,
        rci              = round(rci, 4) if rci is not None else None,
        rci_pct          = round(rci * 100, 2) if rci is not None else None,
        rci_estado       = rci_estado,
        efectivo_salon   = round(efectivo_salon, 2),
        disponible       = len(errores) == 0,
        errores          = errores,
    )


def calcular_todos_los_planes(
    monto:          float,
    precio_nuevo:   float,
    anio_nuevo:     int = 2026,
    gastos_transf:  float = 0.0,
    precio_toma:    float = 0.0,
    anio_usado:     int = 0,
    precio_revista: float = 0.0,
    ingresos:       float = 0.0,
) -> list[dict]:
    resultados = []
    for plan_key in TABLA_PSA:
        for plazo in TABLA_PSA[plan_key]["plazos"]:
            r = calcular_credito(
                plan_key       = plan_key,
                plazo          = plazo,
                monto          = monto,
                precio_nuevo   = precio_nuevo,
                anio_nuevo     = anio_nuevo,
                gastos_transf  = gastos_transf,
                precio_toma    = precio_toma,
                anio_usado     = anio_usado,
                precio_revista = precio_revista,
                ingresos       = ingresos,
            )
            resultados.append(asdict(r))
    return resultados


# ---------------------------------------------------------------------------
# RUTAS DE LA API & WEB
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def login_page():
    if "user" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email") or request.form.get("username")
        password = request.form.get("password")

        if not email or not password:
            return render_template(
                "login.html",
                error="Por favor, completá todos los campos.",
                email=email
            )

        try:
            response = authenticate_user(email, password)

            if response and response.user:
                session["user"] = {
                    "id": response.user.id,
                    "email": response.user.email
                }
                return redirect(url_for("home"))

        except Exception:
            pass

        return render_template(
            "login.html",
            error="Email o contraseña incorrectos",
            email=email
        )

    return render_template("login.html")


@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login_page"))

    return send_from_directory(".", "index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Parámetro 'q' requerido"}), 400
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


@app.route("/planes", methods=["GET"])
def obtener_planes():
    """Devuelve la configuración y lista de planes PSA Finance."""
    return jsonify({
        "planes": TABLA_PSA,
        "iva": IVA,
        "rci_max_fijo": RCI_MAX_FIJO,
        "rci_max_uva": RCI_MAX_UVA,
    })


@app.route("/simular", methods=["POST"])
def simular():
    """Calcula el crédito para un plan y plazo específicos."""
    data = request.get_json(force=True) or {}
    try:
        resultado = calcular_credito(
            plan_key       = str(data.get("plan_key", "TRADICIONAL_VO")),
            plazo          = int(data.get("plazo", 24)),
            monto          = float(data.get("monto", 0)),
            precio_nuevo   = float(data.get("precio_nuevo", 0)),
            anio_nuevo     = int(data.get("anio_nuevo", 2026)),
            gastos_transf  = float(data.get("gastos_transf", 0)),
            precio_toma    = float(data.get("precio_toma", 0)),
            anio_usado     = int(data.get("anio_usado", 0)),
            precio_revista = float(data.get("precio_revista", 0)),
            ingresos       = float(data.get("ingresos", 0)),
        )
        return jsonify(asdict(resultado)), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/simular-todos", methods=["POST"])
def simular_todos():
    """Calcula y compara todos los planes y plazos disponibles."""
    data = request.get_json(force=True) or {}
    try:
        resultados = calcular_todos_los_planes(
            monto          = float(data.get("monto", 0)),
            precio_nuevo   = float(data.get("precio_nuevo", 0)),
            anio_nuevo     = int(data.get("anio_nuevo", 2026)),
            gastos_transf  = float(data.get("gastos_transf", 0)),
            precio_toma    = float(data.get("precio_toma", 0)),
            anio_usado     = int(data.get("anio_usado", 0)),
            precio_revista = float(data.get("precio_revista", 0)),
            ingresos       = float(data.get("ingresos", 0)),
        )
        return jsonify({"resultados": resultados}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/<path:filename>")
def serve_static(filename):
    if filename == "index.html" and "user" not in session:
        return redirect(url_for("login_page"))

    if filename.startswith("."):
        return "", 404

    return send_from_directory(".", filename)


PORT = int(os.environ.get("PORT", 5050))

if __name__ == "__main__":
    def try_initial_login():
        try:
            login()
        except Exception as e:
            print(f"[WARN] Advertencia login Infoauto: {e}")
    threading.Thread(target=try_initial_login, daemon=True).start()
    print(f"[OK] Backend Roma Automotores listo en http://localhost:{PORT}")
    app.run(debug=True, port=PORT, host="0.0.0.0")


