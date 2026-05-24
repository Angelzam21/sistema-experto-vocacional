"""
=================================================================
PASO 1.2 - ESTRUCTURACIÓN Y NORMALIZACIÓN
=================================================================
Saneamiento de los textos extraídos por scraper.py para eliminar
inconsistencias de nomenclatura entre universidades. Por ejemplo:

    'Ing. en Sistemas'       \\
    'INGENIERÍA EN SISTEMAS'  >  -> id_maestro = 'ingenieria_sistemas'
    'Lic. en Informática'    /

Estrategias usadas:
  1. Limpieza lexical: trim, lowercase, eliminar acentos, espacios
     múltiples, signos de puntuación irrelevantes.
  2. Regex de expansión: convertir abreviaturas comunes
     ('Ing.' -> 'Ingenieria').
  3. Fuzzy matching: comparar el nombre limpio contra una lista
     canónica de carreras usando RapidFuzz (Levenshtein optimizado).
     Si la similitud supera un umbral (default 80%) se asigna el ID
     maestro; de lo contrario el registro queda flagged como 'sin_match'
     para revisión manual.

La salida es una lista de dicts con la estructura mínima requerida
por el JSON maestro, dejando los campos RIASEC en None para que la
Fase 1.3 (onet_mapper) los complete.
=================================================================
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

# RapidFuzz: librería C++/Python para fuzzy string matching.
# Usa la distancia de Levenshtein normalizada (token_sort_ratio).
from rapidfuzz import fuzz, process

log = logging.getLogger(__name__)


# -----------------------------------------------------------------
# Diccionario canónico: id_maestro -> lista de variantes/sinónimos.
# Es la "fuente de la verdad" para la normalización. Cada entrada
# corresponde a una de las 30 carreras del dataset maestro.
# -----------------------------------------------------------------
CANONICO: dict[str, list[str]] = {
    "medicina": ["Medicina", "Doctorado en Medicina", "Médico"],
    "ingenieria_sistemas": [
        "Ingeniería en Sistemas de Información",
        "Ingeniería en Sistemas",
        "Ingeniería de Sistemas",
        "Ingeniería Informática",
        "Licenciatura en Sistemas",
        "Lic. en Informática",
    ],
    "abogacia": ["Abogacía", "Derecho", "Ciencias Jurídicas"],
    "psicologia": ["Psicología", "Lic. en Psicología"],
    "contador_publico": ["Contador Público", "Contabilidad"],
    "administracion_empresas": [
        "Administración de Empresas",
        "Lic. en Administración",
    ],
    "ingenieria_civil": ["Ingeniería Civil"],
    "ingenieria_industrial": ["Ingeniería Industrial"],
    "ingenieria_electronica": ["Ingeniería Electrónica"],
    "ingenieria_mecanica": ["Ingeniería Mecánica"],
    "ingenieria_quimica": ["Ingeniería Química"],
    "arquitectura": ["Arquitectura"],
    "diseno_grafico": ["Diseño Gráfico", "Lic. en Diseño Gráfico"],
    "diseno_industrial": ["Diseño Industrial", "Diseño de Productos"],
    "comunicacion_social": [
        "Comunicación Social",
        "Periodismo",
        "Lic. en Comunicación",
    ],
    "marketing": ["Marketing", "Lic. en Marketing", "Publicidad"],
    "economia": ["Economía", "Lic. en Economía"],
    "sociologia": ["Sociología", "Lic. en Sociología"],
    "trabajo_social": ["Trabajo Social", "Lic. en Trabajo Social"],
    "ciencias_educacion": ["Ciencias de la Educación", "Lic. en Educación"],
    "enfermeria": ["Licenciatura en Enfermería", "Enfermería"],
    "kinesiologia": ["Kinesiología", "Fisioterapia"],
    "odontologia": ["Odontología"],
    "veterinaria": ["Veterinaria", "Ciencias Veterinarias"],
    "biologia": ["Ciencias Biológicas", "Biología", "Lic. en Biología"],
    "farmacia": ["Farmacia", "Lic. en Farmacia"],
    "nutricion": ["Licenciatura en Nutrición", "Nutrición"],
    "ciencia_politica": ["Ciencia Política", "Politología"],
    "letras": ["Letras", "Lic. en Letras"],
    "agronomia": ["Ingeniería Agronómica", "Agronomía"],
}

# Aplanado del diccionario a un map "variante -> id_maestro" para
# que el matcher pueda buscar contra todas las variantes de una vez.
_VARIANTE_A_ID: dict[str, str] = {
    variante: id_maestro
    for id_maestro, variantes in CANONICO.items()
    for variante in variantes
}

# Umbral de similitud (0-100) para considerar un match válido.
# 80 es conservador: tolera errores tipográficos chicos sin generar
# falsos positivos entre carreras distintas (ej: "Biología" vs "Sociología").
UMBRAL_FUZZY = 80


@dataclass
class CarreraNormalizada:
    """Carrera tras la normalización, antes del enriquecimiento RIASEC."""
    id: str                       # id maestro (ej: 'ingenieria_sistemas')
    nombre: str                   # nombre canónico
    universidad_sigla: str
    zona_geografica: str
    modalidad: str
    score_match: float            # 0-100, calidad del fuzzy match
    riasec: dict[str, int | None] = None  # se completará en Fase 1.3


# -----------------------------------------------------------------
# Funciones internas de limpieza
# -----------------------------------------------------------------
def _strip_acentos(texto: str) -> str:
    """Quita tildes/diacríticos manteniendo la base ASCII.

    Usa la descomposición NFD de Unicode: separa el carácter base de
    su marca diacrítica y filtra estas últimas.
    """
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _expandir_abreviaturas(texto: str) -> str:
    """Reemplaza abreviaturas comunes por su forma completa.

    Hacerlo *antes* del fuzzy matching aumenta significativamente
    la tasa de aciertos (la distancia de Levenshtein penaliza
    fuerte las diferencias de longitud).
    """
    reemplazos = [
        (r"\bing\.?\b", "ingenieria"),
        (r"\blic\.?\b", "licenciatura"),
        (r"\bprof\.?\b", "profesorado"),
        (r"\btec\.?\b", "tecnicatura"),
        (r"\bcs\.?\b", "ciencias"),
        (r"\bcont\.?\b", "contador"),
        (r"\badm\.?\b", "administracion"),
    ]
    out = texto
    for patron, reemplazo in reemplazos:
        out = re.sub(patron, reemplazo, out, flags=re.IGNORECASE)
    return out


def limpiar_texto(texto: str) -> str:
    """Pipeline completo de limpieza lexical.

    Aplica en orden:
      1. trim + lowercase
      2. eliminación de acentos
      3. expansión de abreviaturas
      4. colapso de espacios múltiples
      5. remoción de paréntesis y su contenido (ej: "(plan 2018)")
    """
    t = texto.strip().lower()
    t = _strip_acentos(t)
    t = _expandir_abreviaturas(t)
    t = re.sub(r"\([^)]*\)", "", t)        # quita "(...)"
    t = re.sub(r"[^a-z0-9\s]", " ", t)     # solo alfanum + espacios
    t = re.sub(r"\s+", " ", t).strip()     # colapsa whitespace
    return t


# -----------------------------------------------------------------
# Función pública: matcheo de una fila cruda
# -----------------------------------------------------------------
def match_carrera(nombre_raw: str) -> tuple[str | None, str | None, float]:
    """Devuelve el id_maestro más probable para un nombre crudo.

    Returns:
        (id_maestro, nombre_canonico, score). Si no supera el
        umbral, devuelve (None, None, score) para que el caller
        decida si descartar la fila o marcarla para revisión.
    """
    limpio = limpiar_texto(nombre_raw)
    if not limpio:
        return None, None, 0.0

    # Pre-procesamos también las variantes del canónico para que la
    # comparación sea apples-to-apples (mismo tratamiento de acentos
    # y abreviaturas).
    variantes_limpias = {
        limpiar_texto(variante): (variante, id_maestro)
        for variante, id_maestro in _VARIANTE_A_ID.items()
    }

    # process.extractOne devuelve el mejor match y su score (0-100).
    # token_sort_ratio tokeniza, ordena alfabéticamente y compara
    # -> tolerante al orden de las palabras ("Ing. Civil" vs "Civil Ingenieria").
    mejor = process.extractOne(
        limpio,
        variantes_limpias.keys(),
        scorer=fuzz.token_sort_ratio,
    )
    if mejor is None:
        return None, None, 0.0

    match_clave, score, _ = mejor
    nombre_canonico, id_maestro = variantes_limpias[match_clave]

    if score < UMBRAL_FUZZY:
        log.debug("Sin match para %r (mejor: %s @ %.1f)", nombre_raw, nombre_canonico, score)
        return None, None, score

    return id_maestro, nombre_canonico, float(score)


def normalizar_lote(
    carreras_crudas: Iterable,
) -> list[CarreraNormalizada]:
    """Normaliza un lote completo de filas crudas del scraper.

    Las filas sin match (score < UMBRAL_FUZZY) son descartadas y se
    loguean para auditoría. Las filas con match se devuelven con el
    bloque RIASEC inicializado a None (lo completará onet_mapper).
    """
    resultado: list[CarreraNormalizada] = []
    descartadas = 0

    for cruda in carreras_crudas:
        # Soportamos tanto CarreraCruda como dict (para flexibilidad).
        nombre = getattr(cruda, "nombre_raw", None) or cruda.get("nombre_raw", "")
        sigla = getattr(cruda, "universidad_sigla", None) or cruda.get("universidad_sigla", "")
        zona = getattr(cruda, "zona_geografica", None) or cruda.get("zona_geografica", "")
        modalidad = getattr(cruda, "modalidad", None) or cruda.get("modalidad", "Presencial")

        id_m, nombre_canon, score = match_carrera(nombre)
        if id_m is None:
            descartadas += 1
            continue

        resultado.append(
            CarreraNormalizada(
                id=id_m,
                nombre=nombre_canon,
                universidad_sigla=sigla,
                zona_geografica=zona,
                modalidad=modalidad,
                score_match=score,
                # RIASEC inicializado en None: la Fase 1.3 lo llenará
                # consultando el dataset O*NET y mapeando por SOC code.
                riasec={"R": None, "I": None, "A": None, "S": None, "E": None, "C": None},
            )
        )

    log.info(
        "Normalización: %d aceptadas, %d descartadas (sin match >= %d).",
        len(resultado), descartadas, UMBRAL_FUZZY,
    )
    return resultado


# -----------------------------------------------------------------
# CLI de prueba: pasar un nombre y ver con qué carrera matchea.
# Uso:   python -m etl.normalizer "Ing en sistemas"
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ejemplo = " ".join(sys.argv[1:]) or "Ing. en Sistemas de Informacion"
    id_m, nom, sc = match_carrera(ejemplo)
    print(f"Input:    {ejemplo!r}")
    print(f"Match:    {nom}  (id={id_m})")
    print(f"Score:    {sc:.1f}")
