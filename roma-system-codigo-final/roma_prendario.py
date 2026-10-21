"""
Roma Automotores — Motor de cálculo prendario
PSA Finance · Tabla Junio 2026

Uso:
    from roma_prendario import calcular_credito, TABLA_PSA

    resultado = calcular_credito(
        plan_key       = "TRADICIONAL_VO",
        plazo          = 24,
        monto          = 8_000_000,
        precio_nuevo   = 23_000_000,
        anio_nuevo     = 2026,
        gastos_transf  = 1_740_000,
        precio_toma    = 10_000_000,
        anio_usado     = 2019,
        precio_revista = 20_000_000,
        ingresos       = 1_000_000,
    )
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


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
    plan_nombre:      str
    plan_tipo:        str
    tna:              float
    plazo:            int
    cuota_pura:       float
    quebranto_neto:   float
    quebranto_iva:    float
    primera_cuota:    float
    total_pagado:     float
    costo_financiero: float
    max_por_ltv:      float
    rci:              Optional[float]
    rci_estado:       str
    efectivo_salon:   float
    errores:          list = field(default_factory=list)


def calcular_antiguedad(anio_auto: int) -> int:
    if not anio_auto:
        return 0
    return max(0, date.today().year - int(anio_auto))


def calcular_max_ltv(antiguedad: int, precio_auto: float) -> float:
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

    # Antigüedad y LTV del auto a FINANCIAR
    antiguedad_financiado = calcular_antiguedad(anio_nuevo) if anio_nuevo else 0
    max_ltv   = calcular_max_ltv(antiguedad_financiado, precio_nuevo) if precio_nuevo > 0 else float('inf')
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

    max_plan = plan.get("max_prestamo")
    if max_plan and monto > max_plan:
        errores.append(
            f"El monto solicitado (${monto:,.0f}) supera el tope del plan "
            f"'{plan['nombre']}' (${max_plan:,.0f})."
        )

    # Cuotas
    cuota_pura     = (monto / 1000.0) * factor
    quebranto_neto = monto * ce
    quebranto_iva  = quebranto_neto * IVA
    primera_cuota  = cuota_pura + quebranto_iva
    total_pagado     = (cuota_pura * plazo) + quebranto_iva
    costo_financiero = total_pagado - monto

    # RCI
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

    # Efectivo en salón (Saldo vehículo + 1ra Cuota completa c/quebranto IVA)
    saldo_auto     = max(0.0, (precio_nuevo + gastos_transf) - precio_toma - monto)
    efectivo_salon = saldo_auto + primera_cuota

    return ResultadoCredito(
        plan_nombre      = plan["nombre"],
        plan_tipo        = plan["tipo"],
        tna              = tna,
        plazo            = plazo,
        cuota_pura       = round(cuota_pura, 2),
        quebranto_neto   = round(quebranto_neto, 2),
        quebranto_iva    = round(quebranto_iva, 2),
        primera_cuota    = round(primera_cuota, 2),
        total_pagado     = round(total_pagado, 2),
        costo_financiero = round(costo_financiero, 2),
        max_por_ltv      = round(max_ltv, 2) if max_ltv != float('inf') else 0.0,
        rci              = round(rci, 4) if rci is not None else None,
        rci_estado       = rci_estado,
        efectivo_salon   = round(efectivo_salon, 2),
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
            resultados.append({
                "plan_key":        plan_key,
                "plan_nombre":     r.plan_nombre,
                "plan_tipo":       r.plan_tipo,
                "plazo":           r.plazo,
                "tna_pct":         round(r.tna * 100, 2),
                "cuota_pura":      r.cuota_pura,
                "quebranto_iva":   r.quebranto_iva,
                "primera_cuota":   r.primera_cuota,
                "total_pagado":    r.total_pagado,
                "costo_financiero":r.costo_financiero,
                "max_por_ltv":     r.max_por_ltv,
                "rci_pct":         round(r.rci * 100, 2) if r.rci else None,
                "rci_estado":      r.rci_estado,
                "efectivo_salon":  r.efectivo_salon,
                "disponible":      len(r.errores) == 0,
                "errores":         r.errores,
            })
    return resultados


if __name__ == "__main__":
    r = calcular_credito(
        plan_key     = "TRADICIONAL_VO",
        plazo        = 24,
        monto        = 8_000_000,
        precio_nuevo = 23_000_000,
        anio_nuevo   = 2026,
        gastos_transf= 1_740_000,
        precio_toma  = 10_000_000,
        anio_usado   = 2019,
        precio_revista = 20_000_000,
        ingresos     = 1_000_000,
    )
    print(f"Plan: {r.plan_nombre} ({r.plazo}m) - 1ra cuota: ${r.primera_cuota:,.2f} - LTV: ${r.max_por_ltv:,.2f}")
