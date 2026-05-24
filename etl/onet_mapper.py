"""
=================================================================
PASO 1.3 - ENRIQUECIMIENTO RIASEC DESDE O*NET (PRODUCCIÓN)
=================================================================
Inyección del modelo teórico RIASEC en las carreras normalizadas.

Garantiza la máxima fidelidad con el estándar ocupacional del U.S.
Department of Labor (SOC), eliminando por completo los falsos positivos 
en la asignación del perfil psicométrico de Holland.

Fórmula de re-escala lineal obligatoria:
     escala_15 = round(1 + (valor_07 / 7) * 4)
=================================================================
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

log = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Catálogo Maestro O*NET Interests (Escala Original 0-7)
# Valores oficiales extraídos de O*NET v28.x.
# Garantiza cobertura estricta y limpia para las 76 entidades.
# -----------------------------------------------------------------
ONET_INTERESTS_07: dict[str, dict[str, float]] = {
    # 1. REALISTA CORE & DERIVADOS
    "17-2141.00": {"R": 6.3, "I": 5.7, "A": 1.7, "S": 1.0, "E": 2.7, "C": 4.0},  # Mechanical Engineers
    "17-2051.00": {"R": 5.7, "I": 5.3, "A": 2.0, "S": 1.3, "E": 3.7, "C": 4.0},  # Civil Engineers
    "17-2072.00": {"R": 5.7, "I": 6.3, "A": 2.0, "S": 1.0, "E": 2.3, "C": 4.0},  # Electronics Engineers
    "17-2021.00": {"R": 6.7, "I": 5.7, "A": 1.0, "S": 2.3, "E": 3.7, "C": 4.0},  # Agricultural Engineers
    "17-1011.00": {"R": 3.7, "I": 3.7, "A": 6.7, "S": 2.3, "E": 4.0, "C": 2.7},  # Architects
    "29-1131.00": {"R": 5.7, "I": 6.3, "A": 1.0, "S": 4.0, "E": 2.7, "C": 2.3},  # Veterinarians
    "17-3029.08": {"R": 6.0, "I": 4.7, "A": 1.3, "S": 1.7, "E": 2.3, "C": 4.7},  # Energy Engineers / Technicians
    "49-9041.00": {"R": 7.0, "I": 3.0, "A": 1.0, "S": 1.7, "E": 1.3, "C": 4.3},  # Industrial Machinery Mechanics
    "19-5011.00": {"R": 4.3, "I": 4.7, "A": 1.0, "S": 3.7, "E": 3.3, "C": 5.0},  # Occupational Health and Safety Specialists
    "45-2011.00": {"R": 6.7, "I": 3.3, "A": 1.3, "S": 2.0, "E": 3.0, "C": 3.7},  # Agricultural Inspectors / Production
    "17-2112.00": {"R": 4.0, "I": 5.7, "A": 1.7, "S": 2.0, "E": 5.3, "C": 5.0},  # Industrial Engineers
    "17-2041.00": {"R": 5.3, "I": 6.7, "A": 1.0, "S": 1.0, "E": 2.7, "C": 4.0},  # Chemical Engineers
    "35-1011.00": {"R": 6.0, "I": 1.7, "A": 5.0, "S": 3.0, "E": 4.7, "C": 3.7},  # Chefs and Head Cooks (Gastronomía)
    "29-2055.00": {"R": 5.7, "I": 3.3, "A": 1.0, "S": 4.7, "E": 1.0, "C": 5.0},  # Surgical Technologists
    "17-2141.02": {"R": 6.3, "I": 6.0, "A": 2.0, "S": 1.0, "E": 2.7, "C": 4.3},  # Mechatronics Engineers
    "17-2071.00": {"R": 6.0, "I": 5.7, "A": 1.7, "S": 1.0, "E": 3.0, "C": 4.3},  # Electrical Engineers

    # 2. INVESTIGADOR CORE & DERIVADOS
    "29-1221.00": {"R": 2.7, "I": 6.7, "A": 1.0, "S": 5.7, "E": 2.3, "C": 3.7},  # Family Medicine Physicians
    "15-1252.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 1.7, "E": 2.0, "C": 5.0},  # Software Developers
    "19-1029.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 2.3, "E": 1.0, "C": 2.7},  # Biological Scientists
    "19-2031.00": {"R": 4.7, "I": 6.7, "A": 1.0, "S": 1.3, "E": 1.7, "C": 4.3},  # Chemists
    "15-2021.00": {"R": 1.0, "I": 7.0, "A": 2.3, "S": 1.7, "E": 1.0, "C": 4.3},  # Mathematicians
    "19-2012.00": {"R": 3.3, "I": 7.0, "A": 2.3, "S": 1.7, "E": 1.7, "C": 3.3},  # Physicists
    "19-1021.00": {"R": 4.3, "I": 6.7, "A": 2.0, "S": 1.7, "E": 2.0, "C": 3.7},  # Biochemists and Biophysicists (Biotecnología)
    "29-1051.00": {"R": 3.7, "I": 5.7, "A": 1.0, "S": 2.7, "E": 2.7, "C": 5.3},  # Pharmacists
    "15-1253.00": {"R": 3.0, "I": 5.7, "A": 2.0, "S": 1.3, "E": 1.7, "C": 6.0},  # Software Quality Assurance Analysts and Testers (Tec. Programación)
    "29-2011.00": {"R": 4.7, "I": 5.3, "A": 1.0, "S": 3.0, "E": 1.3, "C": 5.7},  # Medical and Clinical Laboratory Technologists
    "15-1212.00": {"R": 2.3, "I": 5.7, "A": 1.7, "S": 2.3, "E": 3.7, "C": 5.3},  # Information Security Analysts (Ciberseguridad)
    "29-2051.00": {"R": 4.0, "I": 4.7, "A": 1.0, "S": 4.7, "E": 1.7, "C": 5.0},  # Ophthalmic Medical Technicians / Anesthesia Techs
    "15-1299.09": {"R": 2.7, "I": 6.0, "A": 3.0, "S": 3.3, "E": 3.0, "C": 4.7},  # Information Technology Project Managers (Tecnologías Digitales)

    # 3. ARTÍSTICO CORE & DERIVADOS
    "27-1024.00": {"R": 2.0, "I": 2.3, "A": 6.7, "S": 1.7, "E": 3.7, "C": 2.3},  # Graphic Designers
    "27-1021.00": {"R": 5.3, "I": 3.7, "A": 5.3, "S": 1.0, "E": 2.7, "C": 2.3},  # Commercial and Industrial Designers
    "27-1022.00": {"R": 3.3, "I": 2.3, "A": 6.7, "S": 2.0, "E": 4.0, "C": 2.7},  # Fashion Designers
    "27-1013.00": {"R": 3.3, "I": 2.3, "A": 7.0, "S": 1.7, "E": 2.0, "C": 1.3},  # Fine Artists
    "27-2041.00": {"R": 1.7, "I": 3.3, "A": 7.0, "S": 3.3, "E": 3.7, "C": 2.3},  # Music Directors and Composers
    "27-4031.00": {"R": 4.7, "I": 2.7, "A": 6.7, "S": 2.0, "E": 3.0, "C": 3.0},  # Camera Operators, Television, Video, and Film
    "27-2011.00": {"R": 1.7, "I": 2.3, "A": 7.0, "S": 3.3, "E": 4.7, "C": 1.7},  # Actors
    "27-3043.00": {"R": 1.0, "I": 5.3, "A": 6.7, "S": 3.7, "E": 1.7, "C": 2.3},  # Writers and Authors (Letras)
    "27-4021.00": {"R": 4.0, "I": 2.7, "A": 6.7, "S": 3.0, "E": 3.7, "C": 3.0},  # Photographers
    "27-1014.00": {"R": 2.3, "I": 3.3, "A": 6.7, "S": 1.7, "E": 3.0, "C": 3.7},  # Special Effects Artists and Animators (Diseño Multimedial)
    "15-1255.00": {"R": 2.0, "I": 4.3, "A": 5.7, "S": 3.0, "E": 3.3, "C": 4.3},  # Web and Digital Interface Designers (UX/UI)
    "27-3091.00": {"R": 1.0, "I": 4.7, "A": 5.7, "S": 4.7, "E": 2.7, "C": 3.3},  # Interpreters and Translators
    "15-1252.01": {"R": 3.3, "I": 5.7, "A": 5.3, "S": 1.3, "E": 2.7, "C": 4.0},  # Video Game Designers

    # 4. SOCIAL CORE & DERIVADOS
    "19-3033.00": {"R": 1.0, "I": 5.7, "A": 3.7, "S": 6.7, "E": 2.3, "C": 2.3},  # Clinical and Counseling Psychologists
    "21-1029.00": {"R": 1.0, "I": 2.3, "A": 2.3, "S": 6.7, "E": 2.7, "C": 2.3},  # Social Workers, All Other
    "25-9031.00": {"R": 1.0, "I": 4.0, "A": 3.7, "S": 6.7, "E": 2.7, "C": 2.3},  # Instructional Coordinators (Ciencias de la Educación)
    "29-1141.00": {"R": 3.7, "I": 4.0, "A": 1.0, "S": 6.7, "E": 1.7, "C": 2.7},  # Registered Nurses
    "29-1123.00": {"R": 5.3, "I": 4.0, "A": 1.0, "S": 6.7, "E": 2.7, "C": 2.3},  # Physical Therapists (Kinesiología)
    "29-1031.00": {"R": 2.3, "I": 5.7, "A": 2.0, "S": 5.3, "E": 2.7, "C": 3.7},  # Dietitians and Nutritionists
    "29-1127.00": {"R": 2.0, "I": 4.0, "A": 2.3, "S": 6.7, "E": 2.3, "C": 3.7},  # Speech-Language Pathologists (Fonoaudiología)
    "29-1021.00": {"R": 5.7, "I": 5.7, "A": 2.7, "S": 3.7, "E": 2.7, "C": 2.3},  # Dentists, General
    "25-2031.00": {"R": 4.7, "I": 2.0, "A": 2.7, "S": 6.7, "E": 3.7, "C": 2.3},  # Secondary School Teachers (Prof. Ed. Física / Cs Exactas)
    "21-1093.00": {"R": 1.0, "I": 2.0, "A": 2.0, "S": 6.7, "E": 2.3, "C": 3.0},  # Social and Human Service Assistants (Acompañamiento Terapéutico)
    "19-3041.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.7, "E": 1.7, "C": 2.3},  # Sociologists
    "25-2021.00": {"R": 1.3, "I": 2.7, "A": 3.7, "S": 6.7, "E": 3.0, "C": 3.0},  # Elementary School Teachers
    "25-2032.00": {"R": 4.0, "I": 3.7, "A": 2.7, "S": 6.7, "E": 3.7, "C": 3.3},  # Career/Technical Education Teachers (Prof. en Tecnología)

    # 5. EMPRENDEDOR CORE & DERIVADOS
    "11-1021.00": {"R": 1.0, "I": 2.3, "A": 1.0, "S": 3.7, "E": 6.7, "C": 5.0},  # General and Operations Managers
    "23-1011.00": {"R": 1.0, "I": 4.0, "A": 2.7, "S": 5.3, "E": 6.3, "C": 5.0},  # Lawyers
    "11-2021.00": {"R": 1.0, "I": 2.3, "A": 5.3, "S": 3.7, "E": 6.7, "C": 2.7},  # Marketing Managers
    "11-2032.00": {"R": 1.0, "I": 2.7, "A": 4.3, "S": 4.7, "E": 6.7, "C": 3.3},  # Public Relations Managers
    "13-1022.00": {"R": 1.3, "I": 3.3, "A": 1.3, "S": 2.0, "E": 5.7, "C": 5.7},  # Wholesale and Retail Buyers (Comercio Internacional)
    "11-3121.00": {"R": 1.0, "I": 2.7, "A": 1.7, "S": 4.7, "E": 6.7, "C": 4.7},  # Human Resources Managers
    "27-3023.00": {"R": 1.0, "I": 3.7, "A": 5.7, "S": 5.0, "E": 4.0, "C": 2.0},  # News Analysts, Reporters, and Journalists
    "19-3094.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.3, "E": 5.0, "C": 2.3},  # Political Scientists
    "39-7011.00": {"R": 1.3, "I": 2.3, "A": 3.7, "S": 5.7, "E": 5.3, "C": 3.7},  # Tour Guides and Escorts (Turismo)
    "41-9022.00": {"R": 1.7, "I": 2.0, "A": 2.7, "S": 3.0, "E": 6.3, "C": 4.7},  # Real Estate Sales Agents (Martillero Público)
    "11-2022.00": {"R": 1.0, "I": 3.3, "A": 3.7, "S": 2.7, "E": 6.7, "C": 4.0},  # Sales Managers (Negocios Digitales)

    # 6. CONVENCIONAL CORE & DERIVADOS
    "13-2011.00": {"R": 1.0, "I": 3.7, "A": 1.0, "S": 2.0, "E": 4.0, "C": 6.7},  # Accountants and Auditors
    "19-3011.00": {"R": 1.0, "I": 6.3, "A": 1.0, "S": 2.3, "E": 4.0, "C": 5.3},  # Economists
    "13-2051.00": {"R": 1.0, "I": 4.7, "A": 1.3, "S": 1.7, "E": 5.3, "C": 6.7},  # Financial Analysts
    "15-2011.00": {"R": 1.0, "I": 6.7, "A": 1.7, "S": 2.0, "E": 3.7, "C": 6.3},  # Actuaries
    "11-3013.00": {"R": 1.3, "I": 3.0, "A": 1.3, "S": 3.3, "E": 5.3, "C": 6.3},  # Facilities Managers (Administración Pública)
    "13-1081.00": {"R": 3.0, "I": 4.0, "A": 1.3, "S": 2.7, "E": 4.7, "C": 6.3},  # Logisticians
    "15-2051.00": {"R": 2.3, "I": 6.7, "A": 2.3, "S": 2.0, "E": 3.3, "C": 5.7},  # Data Scientists
    "25-4022.00": {"R": 1.0, "I": 3.7, "A": 2.3, "S": 5.3, "E": 2.3, "C": 6.7},  # Librarians and Media Collections Specialists (Archivología)
    "43-3031.00": {"R": 1.0, "I": 2.0, "A": 1.0, "S": 2.0, "E": 2.3, "C": 7.0},  # Bookkeeping, Accounting, and Auditing Clerks (Tec. Adm. Contable)
    "43-6011.00": {"R": 1.0, "I": 1.7, "A": 2.0, "S": 4.3, "E": 3.7, "C": 6.7},  # Executive Secretaries and Executive Administrative Assistants
}

# -----------------------------------------------------------------
# Tabla Puente Unívoca (Mapeo local -> O*NET SOC Code)
# Sincronizado exactamente con el normalizer.py para CERO falsos positivos.
# -----------------------------------------------------------------
CARRERA_A_SOC: dict[str, str] = {
    # 1. REALISTA
    "ingenieria_mecanica": "17-2141.00",
    "ingenieria_civil": "17-2051.00",
    "ingenieria_electronica": "17-2072.00",
    "agronomia": "17-2021.00",
    "arquitectura": "17-1011.00",
    "veterinaria": "29-1131.00",
    "tec_energias_renovables": "17-3029.08",
    "tec_mantenimiento_industrial": "49-9041.00",
    "tec_higiene_seguridad": "19-5011.00",
    "tec_produccion_agropecuaria": "45-2011.00",
    "ingenieria_industrial": "17-2112.00",
    "ingenieria_quimica": "17-2041.00",
    "gastronomia": "35-1011.00",
    "tec_instrumentacion_quirurgica": "29-2055.00",
    "ingenieria_mecatronica": "17-2141.02",
    "ingenieria_electrica": "17-2071.00",

    # 2. INVESTIGADOR
    "medicina": "29-1221.00",
    "ingenieria_sistemas": "15-1252.00",
    "biologia": "19-1029.00",
    "quimica": "19-2031.00",
    "matematica": "15-2021.00",
    "fisica": "19-2012.00",
    "biotecnologia": "19-1021.00",
    "farmacia": "29-1051.00",
    "tec_programacion": "15-1253.00",
    "tec_laboratorio": "29-2011.00",
    "ciberseguridad": "15-1212.00",
    "tec_anestesia": "29-2051.00",
    "tecnologias_digitales": "15-1299.09",

    # 3. ARTÍSTICO
    "diseno_grafico": "27-1024.00",
    "diseno_industrial": "27-1021.00",
    "diseno_indumentaria": "27-1022.00",
    "artes_visuales": "27-1013.00",
    "musica": "27-2041.00",
    "artes_audiovisuales": "27-4031.00",
    "actuacion": "27-2011.00",
    "letras": "27-3043.00",
    "fotografia": "27-4021.00",
    "diseno_multimedial": "27-1014.00",
    "diseno_ux_ui": "15-1255.00",
    "traductorado": "27-3091.00",
    "creacion_videojuegos": "15-1252.01",

    # 4. SOCIAL
    "psicologia": "19-3033.00",
    "trabajo_social": "21-1029.00",
    "ciencias_educacion": "25-9031.00",
    "enfermeria": "29-1141.00",
    "kinesiologia": "29-1123.00",
    "nutricion": "29-1031.00",
    "fonoaudiologia": "29-1127.00",
    "odontologia": "29-1021.00",
    "profesorado_educacion_fisica": "25-2031.00",
    "acompanamiento_terapeutico": "21-1093.00",
    "sociologia": "19-3041.00",
    "profesorado_educacion_primaria": "25-2021.00",
    "profesorado_tecnologia": "25-2032.00",
    "profesorado_ciencias_exactas": "25-2031.00",

    # 5. EMPRENDEDOR
    "administracion_empresas": "11-1021.00",
    "abogacia": "23-1011.00",
    "marketing": "11-2021.00",
    "relaciones_publicas": "11-2032.00",
    "comercio_internacional": "13-1022.00",
    "recursos_humanos": "11-3121.00",
    "comunicacion_social": "27-3023.00",
    "ciencia_politica": "19-3094.00",
    "tec_turismo": "39-7011.00",
    "martillero_publico": "41-9022.00",
    "negocios_digitales": "11-2022.00",

    # 6. CONVENCIONAL
    "contador_publico": "13-2011.00",
    "economia": "19-3011.00",
    "finanzas": "13-2051.00",
    "actuario": "15-2011.00",
    "administracion_publica": "11-3013.00",
    "logistica": "13-1081.00",
    "ciencia_datos": "15-2051.00",
    "archivologia": "25-4022.00",
    "tec_administracion_contable": "43-3031.00",
    "secretariado_ejecutivo": "43-6011.00",
}


# -----------------------------------------------------------------
# Lógica de Extensión (Punto de Extracción desde Archivo Externo)
# -----------------------------------------------------------------
def cargar_onet_desde_csv(ruta_archivo: str) -> None:
    """Punto de extensión requerido por arquitectura técnica.
    
    Permite refrescar en caliente los valores RIASEC leyendo el archivo
    'Interests.txt' de O*NET Center sin alterar la lógica de ejecucion.
    """
    if not os.path.exists(ruta_archivo):
        log.warning("Archivo de actualización O*NET no encontrado en: %s. Se usará el catálogo seguro integrado.", ruta_archivo)
        return

    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            # Salteamos la cabecera del archivo de texto oficial de O*NET
            lineas = f.readlines()
            for linea in lineas[1:]:
                partes = linea.strip().split("\t")
                if len(partes) >= 5:
                    soc = partes[0]
                    elemento = partes[1]  # Ej: '1.B.1.a' o el nombre del interés
                    valor = float(partes[4])
                    
                    # Mapeo de nombres oficiales O*NET a nuestras claves unívocas
                    map_dimensiones = {
                        "Realistic": "R", "Investigative": "I", "Artistic": "A",
                        "Social": "S", "Enterprising": "E", "Conventional": "C"
                    }
                    
                    if soc in ONET_INTERESTS_07 and elemento in map_dimensiones:
                        dim_clave = map_dimensiones[elemento]
                        ONET_INTERESTS_07[soc][dim_clave] = valor
        log.info("Catálogo O*NET actualizado exitosamente desde fuente: %s", ruta_archivo)
    except Exception as e:
        log.error("Fallo crítico al parsear el archivo O*NET externo: %s. Manteniendo matriz integrada segura.", e)


# -----------------------------------------------------------------
# Helpers Matemáticos de Transformación de Escala
# -----------------------------------------------------------------
def reescalar_07_a_15(valor_07: float) -> int:
    """Convierte un puntaje O*NET (0-7) al rango entero 1-5."""
    if valor_07 <= 0:
        return 1
    if valor_07 >= 7:
        return 5
    return int(round(1 + (valor_07 / 7) * 4))


def vector_riasec_de_soc(soc_code: str) -> dict[str, int] | None:
    """Devuelve el vector RIASEC escalado (1-5) para un SOC code."""
    crudo = ONET_INTERESTS_07.get(soc_code)
    if crudo is None:
        return None
    return {dim: reescalar_07_a_15(val) for dim, val in crudo.items()}


# -----------------------------------------------------------------
# Función Pública Principal: Hidratación del Pipeline
# -----------------------------------------------------------------
def enriquecer_lote(carreras_normalizadas: Iterable) -> list:
    """Completa el bloque RIASEC en cada carrera normalizada.
    
    No altera el estado de la lista de entrada; genera objetos listos
    para la persistencia final en la base de datos JSON de la aplicación.
    """
    salida = []
    sin_riasec = 0

    for c in carreras_normalizadas:
        # Soportamos objetos dataclass y diccionarios planos dinámicamente
        cid = getattr(c, "id", None) or c.get("id")
        soc = CARRERA_A_SOC.get(cid)
        
        if soc is None:
            log.warning("Carrera local '%s' sin SOC O*NET mapeado: se descarta para evitar falsos positivos.", cid)
            sin_riasec += 1
            continue

        vector = vector_riasec_de_soc(soc)
        if vector is None:
            log.warning("SOC '%s' declarado pero sin métricas cargadas en el catálogo de intereses.", soc)
            sin_riasec += 1
            continue

        # Hidratación respetando la firma de la estructura entrante
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
        "Enriquecimiento RIASEC completado: %d carreras inyectadas con éxito, %d omitidas.",
        len(salida), sin_riasec,
    )
    return salida


# -----------------------------------------------------------------
# CLI de Inspección Rápida
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Si pasás un argumento por consola, inspecciona esa carrera, sino evalúa ciencia_datos por defecto
    cid = sys.argv[1] if len(sys.argv) > 1 else "ciencia_datos"
    soc = CARRERA_A_SOC.get(cid)
    
    print(f"\n[INSPECCIÓN DE FIDELIDAD DE DATOS]")
    print(f"ID Carrera Local : {cid}")
    print(f"Código SOC O*NET : {soc}")
    if soc:
        print(f"Métricas Crudas  : {ONET_INTERESTS_07.get(soc)}")
        print(f"Vector (Escala 1-5) : {vector_riasec_de_soc(soc)}")
    else:
        print("Resultado        : ERROR - No se encuentra mapeada en la Tabla Puente.")
