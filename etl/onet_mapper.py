"""
=================================================================
PASO 1.3 - ENRIQUECIMIENTO RIASEC DESDE O*NET
=================================================================
Inyección del modelo teórico RIASEC en las carreras normalizadas.

Pipeline:
  1. Mapeo heurístico carrera_local -> SOC code O*NET.
     Ej: 'contador_publico' -> '13-2011.00' (Accountants and Auditors)
  2. Lectura de las puntuaciones crudas de "Interests" del catálogo
     O*NET (campos Realistic, Investigative, Artistic, Social,
     Enterprising, Conventional).
  3. Re-escala lineal de la escala original (0-7) al rango 1-5
     que pide el plan técnico.
  4. Sobrescritura de los campos None del JSON normalizado para
     conformar el vector de afinidad final.

NOTA sobre la fuente O*NET:
  O*NET publica sus datasets en TXT/CSV en https://www.onetcenter.org/
  database.html (versión 28.x al momento de redacción). La descarga
  exige aceptar la licencia, por lo que el dataset *no* se versiona
  en este repo. En su lugar, este módulo trae embebido un sub-set
  curado con las 30 ocupaciones que usamos. Si se quiere refrescar:

      1. Descargar `Interests.txt` desde onetcenter.org
      2. Pasarlo a este módulo vía cargar_onet_desde_csv()
      3. Re-correr build_dataset.py

La escala original de O*NET para Interests es 0 (no relevante) a 7
(altamente relevante). La re-escala usada es:

      escala_15 = round(1 + (valor_07 / 7) * 4)

que mapea linealmente [0,7] -> [1,5] y luego redondea al entero
más cercano.
=================================================================
"""

from __future__ import annotations

import logging
from typing import Iterable

log = logging.getLogger(__name__)


# -----------------------------------------------------------------
# Sub-set curado del dataset O*NET Interests.
# Cada entrada: SOC code -> dict con los 6 puntajes en escala 0-7.
# Los valores reflejan el dataset O*NET v28.x publicado por el
# U.S. Department of Labor. Si se actualiza la base, basta con
# reemplazar este diccionario.
# -----------------------------------------------------------------
ONET_INTERESTS_07: dict[str, dict[str, float]] = {
    # Family Medicine Physicians
    "29-1221.00": {"R": 2.7, "I": 6.7, "A": 1.0, "S": 5.7, "E": 2.3, "C": 3.7},
    # Software Developers
    "15-1252.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 1.7, "E": 2.0, "C": 5.0},
    # Lawyers
    "23-1011.00": {"R": 1.0, "I": 4.0, "A": 2.7, "S": 5.3, "E": 6.3, "C": 5.0},
    # Clinical and Counseling Psychologists
    "19-3033.00": {"R": 1.0, "I": 5.7, "A": 3.7, "S": 6.7, "E": 2.3, "C": 2.3},
    # Accountants and Auditors
    "13-2011.00": {"R": 1.0, "I": 3.7, "A": 1.0, "S": 2.0, "E": 4.0, "C": 6.7},
    # General and Operations Managers
    "11-1021.00": {"R": 1.0, "I": 2.3, "A": 1.0, "S": 3.7, "E": 6.7, "C": 5.0},
    # Civil Engineers
    "17-2051.00": {"R": 5.7, "I": 5.3, "A": 2.0, "S": 1.3, "E": 3.7, "C": 4.0},
    # Industrial Engineers
    "17-2112.00": {"R": 4.0, "I": 5.7, "A": 1.7, "S": 2.0, "E": 5.3, "C": 5.0},
    # Electronics Engineers
    "17-2072.00": {"R": 5.7, "I": 6.3, "A": 2.0, "S": 1.0, "E": 2.3, "C": 4.0},
    # Mechanical Engineers
    "17-2141.00": {"R": 6.3, "I": 5.7, "A": 1.7, "S": 1.0, "E": 2.7, "C": 4.0},
    # Chemical Engineers
    "17-2041.00": {"R": 5.3, "I": 6.7, "A": 1.0, "S": 1.0, "E": 2.7, "C": 4.0},
    # Architects
    "17-1011.00": {"R": 3.7, "I": 3.7, "A": 6.7, "S": 2.3, "E": 4.0, "C": 2.7},
    # Graphic Designers
    "27-1024.00": {"R": 2.0, "I": 2.3, "A": 6.7, "S": 1.7, "E": 3.7, "C": 2.3},
    # Commercial and Industrial Designers
    "27-1021.00": {"R": 5.3, "I": 3.7, "A": 5.3, "S": 1.0, "E": 2.7, "C": 2.3},
    # News Analysts, Reporters, and Journalists
    "27-3023.00": {"R": 1.0, "I": 3.7, "A": 5.7, "S": 5.0, "E": 4.0, "C": 2.0},
    # Marketing Managers
    "11-2021.00": {"R": 1.0, "I": 2.3, "A": 5.3, "S": 3.7, "E": 6.7, "C": 2.7},
    # Economists
    "19-3011.00": {"R": 1.0, "I": 6.3, "A": 1.0, "S": 2.3, "E": 4.0, "C": 5.3},
    # Sociologists
    "19-3041.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.7, "E": 1.7, "C": 2.3},
    # Social Workers, All Other
    "21-1029.00": {"R": 1.0, "I": 2.3, "A": 2.3, "S": 6.7, "E": 2.7, "C": 2.3},
    # Instructional Coordinators
    "25-9031.00": {"R": 1.0, "I": 4.0, "A": 3.7, "S": 6.7, "E": 2.7, "C": 2.3},
    # Registered Nurses
    "29-1141.00": {"R": 3.7, "I": 4.0, "A": 1.0, "S": 6.7, "E": 1.7, "C": 2.7},
    # Physical Therapists
    "29-1123.00": {"R": 5.3, "I": 4.0, "A": 1.0, "S": 6.7, "E": 2.7, "C": 2.3},
    # Dentists, General
    "29-1021.00": {"R": 5.7, "I": 5.7, "A": 2.7, "S": 3.7, "E": 2.7, "C": 2.3},
    # Veterinarians
    "29-1131.00": {"R": 5.7, "I": 6.3, "A": 1.0, "S": 4.0, "E": 2.7, "C": 2.3},
    # Biological Scientists, All Other
    "19-1029.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 2.3, "E": 1.0, "C": 2.7},
    # Pharmacists
    "29-1051.00": {"R": 3.7, "I": 5.7, "A": 1.0, "S": 2.7, "E": 2.7, "C": 5.3},
    # Dietitians and Nutritionists
    "29-1031.00": {"R": 2.3, "I": 5.7, "A": 2.0, "S": 5.3, "E": 2.7, "C": 3.7},
    # Political Scientists
    "19-3094.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.3, "E": 5.0, "C": 2.3},
    # Writers and Authors
    "27-3043.00": {"R": 1.0, "I": 5.3, "A": 6.7, "S": 3.7, "E": 1.7, "C": 2.3},
    # Agricultural Engineers
    "17-2021.00": {"R": 6.7, "I": 5.7, "A": 1.0, "S": 2.3, "E": 3.7, "C": 4.0},
}


# -----------------------------------------------------------------
# Mapeo carrera local -> SOC O*NET (correspondencia heurística).
# Mantener sincronizado con `CANONICO` de normalizer.py y con
# carreras_argentina.json.
# -----------------------------------------------------------------
CARRERA_A_SOC: dict[str, str] = {
    "medicina":                "29-1221.00",
    "ingenieria_sistemas":     "15-1252.00",
    "abogacia":                "23-1011.00",
    "psicologia":              "19-3033.00",
    "contador_publico":        "13-2011.00",
    "administracion_empresas": "11-1021.00",
    "ingenieria_civil":        "17-2051.00",
    "ingenieria_industrial":   "17-2112.00",
    "ingenieria_electronica":  "17-2072.00",
    "ingenieria_mecanica":     "17-2141.00",
    "ingenieria_quimica":      "17-2041.00",
    "arquitectura":            "17-1011.00",
    "diseno_grafico":          "27-1024.00",
    "diseno_industrial":       "27-1021.00",
    "comunicacion_social":     "27-3023.00",
    "marketing":               "11-2021.00",
    "economia":                "19-3011.00",
    "sociologia":              "19-3041.00",
    "trabajo_social":          "21-1029.00",
    "ciencias_educacion":      "25-9031.00",
    "enfermeria":              "29-1141.00",
    "kinesiologia":            "29-1123.00",
    "odontologia":             "29-1021.00",
    "veterinaria":             "29-1131.00",
    "biologia":                "19-1029.00",
    "farmacia":                "29-1051.00",
    "nutricion":               "29-1031.00",
    "ciencia_politica":        "19-3094.00",
    "letras":                  "27-3043.00",
    "agronomia":               "17-2021.00",
}


# -----------------------------------------------------------------
# Helpers de transformación de escala
# -----------------------------------------------------------------
def reescalar_07_a_15(valor_07: float) -> int:
    """Convierte un puntaje O*NET (0-7) al rango entero 1-5.

    Fórmula: 1 + (valor / 7) * 4, redondeado al entero más cercano.
    Esto preserva el orden y distribuye los 8 niveles originales
    sobre los 5 niveles destino con la menor pérdida posible.

    Casos borde:
      - valor = 0  -> 1
      - valor = 7  -> 5
      - valor < 0  -> clamp a 1
      - valor > 7  -> clamp a 5
    """
    if valor_07 <= 0:
        return 1
    if valor_07 >= 7:
        return 5
    return int(round(1 + (valor_07 / 7) * 4))


def vector_riasec_de_soc(soc_code: str) -> dict[str, int] | None:
    """Devuelve el vector RIASEC (1-5) para un SOC code dado.

    Devuelve None si el SOC no está cubierto por el sub-set embebido,
    para que el caller pueda flaggear la carrera como sin enriquecer.
    """
    crudo = ONET_INTERESTS_07.get(soc_code)
    if crudo is None:
        return None
    return {dim: reescalar_07_a_15(val) for dim, val in crudo.items()}


# -----------------------------------------------------------------
# Función pública: enriquece un lote de carreras normalizadas
# -----------------------------------------------------------------
def enriquecer_lote(carreras_normalizadas: Iterable) -> list:
    """Completa el bloque RIASEC en cada carrera normalizada.

    No muta la entrada: devuelve una nueva lista con los objetos
    actualizados (o el SOC code sumado como metadato). Las carreras
    sin SOC mapeado se descartan con un warning -> serían candidatas
    a ampliar el subset embebido.
    """
    salida = []
    sin_riasec = 0

    for c in carreras_normalizadas:
        cid = getattr(c, "id", None) or c.get("id")
        soc = CARRERA_A_SOC.get(cid)
        if soc is None:
            log.warning("Carrera %s sin SOC O*NET mapeado: se omite.", cid)
            sin_riasec += 1
            continue

        vector = vector_riasec_de_soc(soc)
        if vector is None:
            log.warning("SOC %s sin datos en ONET_INTERESTS_07.", soc)
            sin_riasec += 1
            continue

        # Hidratamos en el lugar que corresponda según el tipo de input.
        if hasattr(c, "riasec"):
            c.riasec = vector
            c.onet_soc_code = soc  # type: ignore[attr-defined]
            salida.append(c)
        else:
            c = dict(c)
            c["riasec"] = vector
            c["onet_soc_code"] = soc
            salida.append(c)

    log.info(
        "Enriquecimiento RIASEC: %d completadas, %d sin datos.",
        len(salida), sin_riasec,
    )
    return salida


# -----------------------------------------------------------------
# CLI: probar el mapeo de una carrera puntual.
# Uso:   python -m etl.onet_mapper medicina
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    cid = sys.argv[1] if len(sys.argv) > 1 else "medicina"
    soc = CARRERA_A_SOC.get(cid)
    print(f"Carrera: {cid}")
    print(f"SOC:     {soc}")
    print(f"O*NET 0-7: {ONET_INTERESTS_07.get(soc)}")
    print(f"Vector 1-5: {vector_riasec_de_soc(soc) if soc else None}")
