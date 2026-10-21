"""
Suite de Pruebas Automatizadas de Lógica - Roma Automotores
Verifica cálculos de PSA Finance, límites de LTV, plazos máximos, quebrantos, RCI y endpoints.
"""

import json
import os
import urllib.request
import sys

PORT = os.environ.get("PORT", "5050")
BASE_URL = f"http://localhost:{PORT}"

def run_test(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except AssertionError as e:
        print(f"[FAIL] {name}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False

def test_endpoints():
    # 1. /planes
    res = urllib.request.urlopen(f"{BASE_URL}/planes")
    assert res.status == 200, "Status /planes no es 200"
    data = json.loads(res.read())
    assert "planes" in data, "No hay planes en respuesta"
    assert len(data["planes"]) == 6, f"Se esperaban 6 planes PSA, recibidos {len(data['planes'])}"

def test_simular_0km():
    # 0km 2026, $23M precio, $8M financiados en 24 meses
    payload = {
        "plan_key": "TRADICIONAL_VO",
        "plazo": 24,
        "monto": 8000000,
        "precio_nuevo": 23000000,
        "anio_nuevo": 2026,
        "gastos_transf": 1740000,
        "precio_toma": 10000000,
        "ingresos": 1500000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    d = json.loads(res.read())
    assert d["disponible"] is True, f"0km debería estar disponible: {d['errores']}"
    # Factor 24m Tradicional VO es 73.62 -> cuota pura = (8000000 / 1000) * 73.62 = 588960
    assert abs(d["cuota_pura"] - 588960) < 1, f"Cuota pura incorrecta: {d['cuota_pura']}"
    # CE es 0.010 -> quebranto neto = 80000, c/IVA 21% = 96800
    assert abs(d["quebranto_iva"] - 96800) < 1, f"Quebranto IVA incorrecto: {d['quebranto_iva']}"
    # 1ra cuota = 588960 + 96800 = 685760
    assert abs(d["primera_cuota"] - 685760) < 1, f"Primera cuota incorrecta: {d['primera_cuota']}"
    # Efectivo en salón = (23M + 1.74M) - 10M - 8M = 6.74M
    assert abs(d["efectivo_salon"] - 6740000) < 1, f"Efectivo salón incorrecto: {d['efectivo_salon']}"

def test_simular_ltv_usado_excedido():
    # Usado 2018 (8 años -> LTV 50% máx $15M). Precio: $10M -> Máx LTV = $5M.
    # Monto pedido: $8M -> debe rechazar por superar LTV
    payload = {
        "plan_key": "TRADICIONAL_VO",
        "plazo": 24,
        "monto": 8000000,
        "precio_nuevo": 10000000,
        "anio_nuevo": 2018,
        "precio_toma": 0,
        "ingresos": 1500000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    d = json.loads(res.read())
    assert d["disponible"] is False, "Debería rechazar por LTV"
    assert any("LTV" in err for err in d["errores"]), f"No se encontró error de LTV: {d['errores']}"

def test_simular_antiguedad_mas_de_10_anos():
    # Usado 2012 (14 años > 10 años) -> debe rechazar
    payload = {
        "plan_key": "TRADICIONAL_VO",
        "plazo": 24,
        "monto": 3000000,
        "precio_nuevo": 8000000,
        "anio_nuevo": 2012,
        "precio_toma": 0,
        "ingresos": 1000000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    d = json.loads(res.read())
    assert d["disponible"] is False, "Debería rechazar por auto de más de 10 años"
    assert any("10" in err for err in d["errores"]), f"No se encontró error de antigüedad: {d['errores']}"

def test_simular_plazo_maximo_por_antiguedad():
    # Usado 2017 (9 años -> plazo máx 36 meses). Pedir 48 meses -> debe rechazar
    payload = {
        "plan_key": "TRADICIONAL_VO",
        "plazo": 48,
        "monto": 3000000,
        "precio_nuevo": 10000000,
        "anio_nuevo": 2017,
        "precio_toma": 0,
        "ingresos": 1000000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    d = json.loads(res.read())
    assert d["disponible"] is False, "Debería rechazar por plazo excesivo para antigüedad"
    assert any("plazo maximo" in err.lower() or "plazo máximo" in err.lower() for err in d["errores"])

def test_rci_uva_rechazo():
    # Plan UVA con cuota pura superior al 30% de los ingresos
    # Monto $16M en 12 meses -> cuota pura = (16000000/1000) * 83.33 = 1.333.280
    # Ingresos $2M -> RCI = 66.6% > 30% -> debe rechazar
    payload = {
        "plan_key": "PROMO_UVA",
        "plazo": 12,
        "monto": 16000000,
        "precio_nuevo": 25000000,
        "anio_nuevo": 2026,
        "precio_toma": 0,
        "ingresos": 2000000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    d = json.loads(res.read())
    assert d["rci_estado"] == "rechazado", f"RCI UVA debería ser rechazado, obtenido: {d['rci_estado']}"
    assert d["disponible"] is False

def test_simular_todos():
    payload = {
        "monto": 6000000,
        "precio_nuevo": 20000000,
        "anio_nuevo": 2026,
        "gastos_transf": 1500000,
        "precio_toma": 8000000,
        "ingresos": 1200000
    }
    req = urllib.request.Request(
        f"{BASE_URL}/simular-todos",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    d = json.loads(res.read())
    assert "resultados" in d
    assert len(d["resultados"]) > 10, f"Debe devolver todas las combinaciones plan/plazo, obtenidos {len(d['resultados'])}"

if __name__ == "__main__":
    tests = [
        ("Configuración y Planes", test_endpoints),
        ("Cálculo 0km y cuotas/efectivo", test_simular_0km),
        ("Validación LTV Usado Excedido", test_simular_ltv_usado_excedido),
        ("Rechazo Auto > 10 años", test_simular_antiguedad_mas_de_10_anos),
        ("Validación Plazo Máximo por Antigüedad", test_simular_plazo_maximo_por_antiguedad),
        ("Rechazo RCI UVA > 30%", test_rci_uva_rechazo),
        ("Simulación Todos los Planes", test_simular_todos),
    ]

    passed = 0
    for name, fn in tests:
        if run_test(name, fn):
            passed += 1

    print(f"\nResultado final: {passed}/{len(tests)} pruebas superadas.")
    if passed == len(tests):
        sys.exit(0)
    else:
        sys.exit(1)
