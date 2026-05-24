"""
=================================================================
PASO 1.2 - ESTRUCTURACIÓN Y NORMALIZACIÓN
=================================================================
Saneamiento de los textos extraídos por scraper.py para eliminar
inconsistencias de nomenclatura entre universidades.

Estrategias usadas:
  1. Limpieza lexical: trim, lowercase, eliminar acentos, espacios
     múltiples, signos de puntuación irrelevantes.
  2. Regex de expansión: convertir abreviaturas comunes.
  3. Fuzzy matching: comparar el nombre limpio contra una lista
     canónica balanceada de 60 carreras usando RapidFuzz.

La salida es una lista de dicts con la estructura mínima requerida
por el JSON maestro, dejando los campos RIASEC en None para que la
Fase 1.3 (onet_mapper) los complete.
=================================================================
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# RapidFuzz: librería C++/Python para fuzzy string matching.
from rapidfuzz import fuzz, process

log = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Diccionario canónico: id_maestro -> lista de variantes/sinónimos.
# Balanceado: 10 carreras por dimensión RIASEC (60 en total).
# -----------------------------------------------------------------
CANONICO: dict[str, list[str]] = {
    # 1. REALISTA
    "ingenieria_mecanica": ["Ingeniería Mecánica", "Mecánica"],
    "ingenieria_civil": ["Ingeniería Civil", "Civil"],
    "ingenieria_electronica": ["Ingeniería Electrónica", "Electrónica"],
    "agronomia": ["Ingeniería Agronómica", "Agronomía", "Ciencias Agrarias"],
    "arquitectura": ["Arquitectura", "Arquitectura y Urbanismo"],
    "veterinaria": ["Veterinaria", "Ciencias Veterinarias", "Medicina Veterinaria"],
    "tec_energias_renovables": ["Tecnicatura en Energías Renovables", "Energías Renovables"],
    "tec_mantenimiento_industrial": ["Tecnicatura en Mantenimiento Industrial", "Mantenimiento Industrial"],
    "tec_higiene_seguridad": ["Tecnicatura en Higiene y Seguridad", "Higiene y Seguridad en el Trabajo"],
    "tec_produccion_agropecuaria": ["Tecnicatura en Producción Agropecuaria", "Producción Agropecuaria"],
    "ingenieria_industrial": ["Ingeniería Industrial"],
    "ingenieria_quimica": ["Ingeniería Química"],
    "gastronomia": ["Gastronomía", "Artes Culinarias", "Gestión Gastronómica"],
    "tec_instrumentacion_quirurgica": ["Instrumentación Quirúrgica", "Tecnicatura en Instrumentación Quirúrgica", "Instrumentador Quirúrgico"],
    "ingenieria_mecatronica": ["Ingeniería Mecatrónica", "Mecatrónica", "Automatización y Control"],
    "ingenieria_electrica": ["Ingeniería Eléctrica", "Ingeniería en Energía Eléctrica"],

    # 2. INVESTIGADOR
    "medicina": ["Medicina", "Doctorado en Medicina", "Médico"],
    "ingenieria_sistemas": ["Ingeniería en Sistemas", "Ingeniería Informática", "Lic. en Sistemas"],
    "biologia": ["Ciencias Biológicas", "Biología", "Lic. en Biología"],
    "quimica": ["Licenciatura en Química", "Ciencias Químicas", "Química"],
    "matematica": ["Licenciatura en Matemática", "Matemática", "Ciencias Matemáticas"],
    "fisica": ["Licenciatura en Física", "Física", "Ciencias Físicas"],
    "biotecnologia": ["Biotecnología", "Lic. en Biotecnología"],
    "farmacia": ["Farmacia", "Lic. en Farmacia"],
    "tec_programacion": ["Tecnicatura en Programación", "Desarrollo de Software", "Analista de Sistemas"],
    "tec_laboratorio": ["Tecnicatura en Laboratorio", "Análisis Clínicos", "Laboratorio Clínico"],
    "ciberseguridad": ["Ciberseguridad", "Seguridad Informática", "Lic. en Seguridad Informática"],
    "tec_anestesia": ["Técnico en Anestesia", "Tecnicatura en Anestesia", "Anestesiología"],
    "tecnologias_digitales": ["Tecnologías Digitales", "Licenciatura en Tecnologías Digitales", "Enseñanza con Tecnologías Digitales"],

    # 3. ARTÍSTICO 
    "diseno_grafico": ["Diseño Gráfico", "Lic. en Diseño Gráfico", "Diseño Visual"],
    "diseno_industrial": ["Diseño Industrial", "Diseño de Productos"],
    "diseno_indumentaria": ["Diseño de Indumentaria", "Diseño Textil", "Indumentaria"],
    "artes_visuales": ["Artes Visuales", "Bellas Artes", "Lic. en Artes Plásticas"],
    "musica": ["Música", "Composición Musical", "Lic. en Música"],
    "artes_audiovisuales": ["Artes Audiovisuales", "Cine y Televisión", "Realización Audiovisual"],
    "actuacion": ["Actuación", "Artes Dramáticas", "Teatro"],
    "letras": ["Letras", "Lic. en Letras", "Literatura"],
    "fotografia": ["Fotografía", "Tecnicatura en Fotografía"],
    "diseno_multimedial": ["Diseño Multimedial", "Animación", "Artes Digitales"],
    "traductorado": ["Traductorado Público", "Traducción", "Traductorado Literario"],
    "creacion_videojuegos": ["Desarrollo y Producción de Videojuegos", "Creación de Videojuegos", "Diseño de Videojuegos"],

    # 4. SOCIAL 
    "psicologia": ["Psicología", "Lic. en Psicología"],
    "trabajo_social": ["Trabajo Social", "Lic. en Trabajo Social", "Servicio Social"],
    "ciencias_educacion": ["Ciencias de la Educación", "Lic. en Educación", "Pedagogía"],
    "enfermeria": ["Licenciatura en Enfermería", "Enfermería"],
    "kinesiologia": ["Kinesiología", "Fisioterapia", "Kinesiología y Fisiatría"],
    "nutricion": ["Licenciatura en Nutrición", "Nutrición"],
    "fonoaudiologia": ["Fonoaudiología", "Lic. en Fonoaudiología"],
    "odontologia": ["Odontología", "Odontólogo"],
    "profesorado_educacion_fisica": ["Profesorado de Educación Física", "Educación Física"],
    "acompanamiento_terapeutico": ["Acompañamiento Terapéutico", "Tecnicatura en Acompañamiento Terapéutico"],
    "sociologia": ["Sociología", "Lic. en Sociología"],
    "profesorado_educacion_primaria": ["Profesorado Universitario de Educación Primaria", "Profesorado de Educación Primaria", "Educación Primaria"],
    "profesorado_ciencias_exactas": ["Profesorado Universitario en Ciencias Exactas y Naturales", "Profesorado de Ciencias Exactas", "Profesorado de Matemática y Física"],

    # 5. EMPRENDEDOR 
    "administracion_empresas": ["Administración de Empresas", "Lic. en Administración"],
    "abogacia": ["Abogacía", "Derecho", "Ciencias Jurídicas"],
    "marketing": ["Marketing", "Lic. en Marketing", "Comercialización"],
    "relaciones_publicas": ["Relaciones Públicas", "Lic. en Relaciones Públicas", "RRPP"],
    "comercio_internacional": ["Comercio Internacional", "Comercio Exterior"],
    "recursos_humanos": ["Recursos Humanos", "Relaciones del Trabajo", "RRHH"],
    "comunicacion_social": ["Comunicación Social", "Periodismo", "Lic. en Comunicación"],
    "ciencia_politica": ["Ciencia Política", "Politología", "Ciencias Políticas"],
    "tec_turismo": ["Tecnicatura en Turismo", "Turismo y Hotelería", "Guía de Turismo"],
    "martillero_publico": ["Martillero Público", "Corredor Inmobiliario", "Bienes Raíces"],
    "negocios_digitales": ["Negocios Digitales", "Lic. en Negocios Digitales", "E-commerce"],

    # 6. CONVENCIONAL 
    "contador_publico": ["Contador Público", "Contabilidad"],
    "economia": ["Economía", "Lic. en Economía", "Ciencias Económicas"],
    "finanzas": ["Finanzas", "Lic. en Finanzas"],
    "actuario": ["Actuario", "Ciencias Actuariales"],
    "administracion_publica": ["Administración Pública", "Gestión Pública"],
    "logistica": ["Logística", "Gestión de la Cadena de Suministro", "Lic. en Logística"],
    "ciencia_datos": ["Ciencia de Datos", "Estadística", "Data Science"],
    "archivologia": ["Archivología", "Bibliotecología", "Ciencias de la Información"],
    "tec_administracion_contable": ["Tecnicatura en Administración Contable", "Gestión Contable"],
    "secretariado_ejecutivo": ["Secretariado Ejecutivo", "Asistencia de Dirección"],
}

# Aplanado del diccionario a un map "variante -> id_maestro"
_VARIANTE_A_ID: dict[str, str] = {
    variante: id_maestro
    for id_maestro, variantes in CANONICO.items()
    for variante in variantes
}


# -----------------------------------------------------------------
# Funciones internas de limpieza
# -----------------------------------------------------------------
def _strip_acentos(texto: str) -> str:
    """Quita tildes/diacríticos manteniendo la base ASCII."""
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _expandir_abreviaturas(texto: str) -> str:
    """Reemplaza abreviaturas comunes por su forma completa."""
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
    """Pipeline completo de limpieza lexical."""
    t = texto.strip().lower()
    t = _strip_acentos(t)
    t = _expandir_abreviaturas(t)
    t = re.sub(r"\([^)]*\)", "", t)        # quita "(...)"
    t = re.sub(r"[^a-z0-9\s]", " ", t)     # solo alfanum + espacios
    t = re.sub(r"\s+", " ", t).strip()     # colapsa whitespace
    return t


# -----------------------------------------------------------------
# Pre-cálculo estático del diccionario limpio (Rendimiento)
# -----------------------------------------------------------------
_VARIANTES_LIMPIAS: dict[str, tuple[str, str]] = {
    limpiar_texto(variante): (variante, id_maestro)
    for variante, id_maestro in _VARIANTE_A_ID.items()
}

# Umbral de similitud (0-100) para considerar un match válido.
UMBRAL_FUZZY = 80


@dataclass
class CarreraNormalizada:
    """Carrera tras la normalización, lista para el cruce con O*NET."""
    id: str                       
    nombre: str                   
    universidad_sigla: str
    zona_geografica: str
    modalidad: str
    score_match: float            
    url_carrera: str | None = None  # Guardamos la URL de forma segura
    # Inicializamos el dict RIASEC vacío para llenarlo en el próximo paso
    riasec: dict[str, int | None] = field(default_factory=lambda: {"R": None, "I": None, "A": None, "S": None, "E": None, "C": None})


# -----------------------------------------------------------------
# Función pública: matcheo de una fila cruda
# -----------------------------------------------------------------
def match_carrera(nombre_raw: str) -> tuple[str | None, str | None, float]:
    """Devuelve el id_maestro más probable para un nombre crudo."""
    limpio = limpiar_texto(nombre_raw)
    if not limpio:
        return None, None, 0.0

    mejor = process.extractOne(
        limpio,
        _VARIANTES_LIMPIAS.keys(),
        scorer=fuzz.token_sort_ratio,
    )
    if mejor is None:
        return None, None, 0.0

    match_clave, score, _ = mejor
    nombre_canonico, id_maestro = _VARIANTES_LIMPIAS[match_clave]

    if score < UMBRAL_FUZZY:
        log.debug("Sin match para %r (mejor: %s @ %.1f)", nombre_raw, nombre_canonico, score)
        return None, None, score

    return id_maestro, nombre_canonico, float(score)


def normalizar_lote(
    carreras_crudas: Iterable,
) -> list[CarreraNormalizada]:
    """Normaliza un lote completo de filas crudas del scraper."""
    resultado: list[CarreraNormalizada] = []
    descartadas = 0

    for cruda in carreras_crudas:
        nombre = getattr(cruda, "nombre_raw", None) or cruda.get("nombre_raw", "")
        sigla = getattr(cruda, "universidad_sigla", None) or cruda.get("universidad_sigla", "")
        zona = getattr(cruda, "zona_geografica", None) or cruda.get("zona_geografica", "")
        modalidad = getattr(cruda, "modalidad", None) or cruda.get("modalidad", "Presencial")
        url_c = getattr(cruda, "url_carrera", None) or cruda.get("url_carrera", None)

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
                url_carrera=url_c,
            )
        )

    log.info(
        "Normalización: %d aceptadas, %d descartadas (sin match >= %d).",
        len(resultado), descartadas, UMBRAL_FUZZY,
    )
    return resultado


# -----------------------------------------------------------------
# CLI de prueba
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ejemplo = " ".join(sys.argv[1:]) or "Ing. en Sistemas de Informacion"
    id_m, nom, sc = match_carrera(ejemplo)
    print(f"Input:    {ejemplo!r}")
    print(f"Match:    {nom}  (id={id_m})")
    print(f"Score:    {sc:.1f}")
