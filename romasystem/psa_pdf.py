from pathlib import Path

from pypdf import PdfReader


def extraer_texto_pdf(ruta_pdf):
    """
    Extrae el texto de todas las páginas de una circular de PSA Finance.
    Devuelve una lista donde cada elemento corresponde a una página.
    """
    ruta_pdf = Path(ruta_pdf)
    reader = PdfReader(str(ruta_pdf))

    paginas = []

    for numero, pagina in enumerate(reader.pages, start=1):
        texto = pagina.extract_text() or ""

        paginas.append({
            "numero": numero,
            "texto": texto.strip()
        })

    return paginas

import re
MESES = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

def extraer_datos_circular(paginas):
    """
    Extrae los datos generales de la circular PSA.
    """
    texto_primera_pagina = paginas[0]["texto"]

    vigencia_match = re.search(
        r"VIGENCIA:\s*([A-ZÁÉÍÓÚÑ]+)/(\d{4})",
        texto_primera_pagina,
        re.IGNORECASE
    )

    circular_match = re.search(
        r"CIRCULAR\s+COMERCIAL\s+NRO\.\s*([\d.]+)",
        texto_primera_pagina,
        re.IGNORECASE
    )

    if not vigencia_match:
        raise ValueError("No se pudo encontrar la vigencia de la circular.")

    if not circular_match:
        raise ValueError("No se pudo encontrar el número de circular.")

    mes_nombre = vigencia_match.group(1).upper()
    mes = MESES.get(mes_nombre)

    if not mes:
        raise ValueError(f"Mes de vigencia no reconocido: {mes_nombre}")

    anio = int(vigencia_match.group(2))

    return {
        "mes": mes,
        "anio": anio,
        "vigencia": f"{anio}-{mes:02d}-01",
        "numero_circular": circular_match.group(1)
    }

def extraer_filas_tasas(texto):
    """
    Extrae las filas numéricas de financiación.

    Ejemplo:
    12 19,9% 10,0% $ 68,20
    """
    patron = re.compile(
        r"^\s*(\d+)\s+"
        r"(\d+,\d+)%\s+"
        r"(\d+,\d+)%\s+"
        r"\$\s*([\d.,]+)\s*$"
    )

    filas = []

    for linea in texto.splitlines():
        match = patron.match(linea)

        if not match:
            continue

        plazo = int(match.group(1))
        tna = float(match.group(2).replace(",", "."))
        aporte_ce = float(match.group(3).replace(",", "."))
        cuota_por_1000 = float(
            match.group(4)
            .replace(".", "")
            .replace(",", ".")
        )

        filas.append({
            "plazo": plazo,
            "tna": tna,
            "aporte_ce": aporte_ce,
            "cuota_por_1000": cuota_por_1000,
        })

    return filas

def agrupar_tasas_por_plan(filas):
    """
    Agrupa las filas extraídas según las líneas de financiación
    de usados que utiliza el simulador.
    """
    estructura = [
        ("PROMO_FIJA", "Promo Fija Usados", "fijo", 12_000_000, 4),
        ("TRADICIONAL_VO", "Tradicional VO", "fijo", None, 6),
        ("TRADICIONAL_VO10", "Tradicional VO 10%", "fijo", None, 6),
        ("PROMO_UVA", "Promo UVA VO", "uva", 17_000_000, 3),
        ("UVA_TRAD", "UVA Tradicional VO", "uva", 40_000_000, 5),
        ("UVA_TRAD10", "UVA Tradicional 10%", "uva", 40_000_000, 5),
    ]

    cantidad_esperada = sum(item[4] for item in estructura)

    if len(filas) != cantidad_esperada:
        raise ValueError(
            f"Se esperaban {cantidad_esperada} filas de tasas, "
            f"pero se encontraron {len(filas)}."
        )

    planes = {}
    posicion = 0

    for clave, nombre, tipo, max_prestamo, cantidad in estructura:
        tasas_plan = filas[posicion:posicion + cantidad]

        planes[clave] = {
            "nombre": nombre,
            "tipo": tipo,
            "max_prestamo": max_prestamo,
            "tasas": tasas_plan,
        }

        posicion += cantidad

    return planes

def preparar_tasas_para_supabase(planes):
    """
    Convierte los planes extraídos del PDF en filas compatibles
    con la tabla tasas_psa.
    """
    filas_supabase = []

    for clave, plan in planes.items():
        for tasa in plan["tasas"]:
            filas_supabase.append({
                "categoria": plan["tipo"],
                "nombre_linea": clave,
                "modelo": None,
                "canal": None,
                "monto_maximo": plan["max_prestamo"],
                "plazo": tasa["plazo"],
                "tna": tasa["tna"],
                "aporte_ce": tasa["aporte_ce"],
                "cuota_por_1000": tasa["cuota_por_1000"],
                "ltv": None,
            })

    return filas_supabase

def buscar_pagina_financiacion_usados(paginas):
    for pagina in paginas:
        texto = pagina["texto"]

        if "FINANCIACIÓN USADOS" in texto.upper():
            return pagina

    raise ValueError(
        "No se encontró la sección FINANCIACIÓN USADOS en el PDF."
    )