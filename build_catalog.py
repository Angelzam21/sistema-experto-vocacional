"""
=================================================================
GENERADOR DEL CATÁLOGO DE CARRERAS (cruce con O*NET)
=================================================================
Este script construye la base de conocimiento del sistema experto:
la lista de carreras de grado/pregrado y su vector RIASEC (modelo de
Holland), derivado del estándar ocupacional O*NET (U.S. Department of
Labor).

NO hace scraping ni depende de internet. Es un proceso 100%
determinista y offline: toma dos tablas estáticas y curadas a mano
y produce `data/carreras.json`.

    CARRERAS (lista maestra) ──┐
                               ├──► reescala 0-7 → 1-5 ──► data/carreras.json
    ONET_INTERESTS_07 (RIASEC) ┘

¿Por qué un script y no escribir el JSON a mano?
  - Trazabilidad: queda explícito de qué ocupación O*NET sale cada
    vector RIASEC (campo `onet_soc`).
  - Reproducibilidad: si se corrige un valor O*NET, se regenera todo
    el catálogo con una sola corrida, sin tocar el JSON a mano.
  - Validación: el script verifica el contrato de datos antes de
    escribir (ver `validar()`).

Uso:
    python build_catalog.py            # genera data/carreras.json
    python build_catalog.py --dry-run  # corre y valida sin escribir
=================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
JSON_CATALOGO = DATA_DIR / "carreras.json"

# Orden canónico de las 6 dimensiones del modelo de Holland (RIASEC).
# Debe ser idéntico al de engine/inference.py.
DIMENSIONES = ("R", "I", "A", "S", "E", "C")

# Etiquetas válidas para la "segunda capa" de filtrado por aversión.
# Cada carrera puede llevar 0..N de estas etiquetas; las preguntas
# filtro (data/preguntas.json -> "filtros") permiten al usuario vetar
# una etiqueta y, con ella, todas las carreras que la tengan.
ETIQUETAS_VALIDAS = {
    "contacto_pacientes",   # tratar/cuidar cuerpos de personas o animales enfermos
    "programacion",         # escribir código gran parte de la jornada
    "matematica_intensa",   # cálculo/matemática avanzada de forma constante
    "trabajo_fisico",       # tareas manuales, físicas o al aire libre
    "exposicion_publica",   # vender, persuadir, liderar o hablar en público
    "expresion_artistica",  # crear obra artística / trabajar desde la creatividad
}


# -----------------------------------------------------------------
# TABLA 1 - Perfiles de interés O*NET (escala original 0 a 7)
# -----------------------------------------------------------------
# Valores oficiales de O*NET Interests v28.x. La clave es el código
# SOC de la ocupación. Estos son los datos "crudos" que luego se
# reescalan a la escala 1-5 que usa el sistema.
ONET_INTERESTS_07: dict[str, dict[str, float]] = {
    # --- Realista ---
    "17-2141.00": {"R": 6.3, "I": 5.7, "A": 1.7, "S": 1.0, "E": 2.7, "C": 4.0},  # Mechanical Engineers
    "17-2051.00": {"R": 5.7, "I": 5.3, "A": 2.0, "S": 1.3, "E": 3.7, "C": 4.0},  # Civil Engineers
    "17-2072.00": {"R": 5.7, "I": 6.3, "A": 2.0, "S": 1.0, "E": 2.3, "C": 4.0},  # Electronics Engineers
    "17-2021.00": {"R": 6.7, "I": 5.7, "A": 1.0, "S": 2.3, "E": 3.7, "C": 4.0},  # Agricultural Engineers
    "17-1011.00": {"R": 3.7, "I": 3.7, "A": 6.7, "S": 2.3, "E": 4.0, "C": 2.7},  # Architects
    "29-1131.00": {"R": 5.7, "I": 6.3, "A": 1.0, "S": 4.0, "E": 2.7, "C": 2.3},  # Veterinarians
    "17-3029.08": {"R": 6.0, "I": 4.7, "A": 1.3, "S": 1.7, "E": 2.3, "C": 4.7},  # Energy Engineering Technicians
    "49-9041.00": {"R": 7.0, "I": 3.0, "A": 1.0, "S": 1.7, "E": 1.3, "C": 4.3},  # Industrial Machinery Mechanics
    "19-5011.00": {"R": 4.3, "I": 4.7, "A": 1.0, "S": 3.7, "E": 3.3, "C": 5.0},  # Occupational Health & Safety Specialists
    "45-2011.00": {"R": 6.7, "I": 3.3, "A": 1.3, "S": 2.0, "E": 3.0, "C": 3.7},  # Agricultural Inspectors
    "17-2112.00": {"R": 4.0, "I": 5.7, "A": 1.7, "S": 2.0, "E": 5.3, "C": 5.0},  # Industrial Engineers
    "17-2041.00": {"R": 5.3, "I": 6.7, "A": 1.0, "S": 1.0, "E": 2.7, "C": 4.0},  # Chemical Engineers
    "35-1011.00": {"R": 6.0, "I": 1.7, "A": 5.0, "S": 3.0, "E": 4.7, "C": 3.7},  # Chefs and Head Cooks
    "29-2055.00": {"R": 5.7, "I": 3.3, "A": 1.0, "S": 4.7, "E": 1.0, "C": 5.0},  # Surgical Technologists
    "17-2141.02": {"R": 6.3, "I": 6.0, "A": 2.0, "S": 1.0, "E": 2.7, "C": 4.3},  # Mechatronics Engineers
    "17-2071.00": {"R": 6.0, "I": 5.7, "A": 1.7, "S": 1.0, "E": 3.0, "C": 4.3},  # Electrical Engineers

    # --- Investigador ---
    "29-1221.00": {"R": 2.7, "I": 6.7, "A": 1.0, "S": 5.7, "E": 2.3, "C": 3.7},  # Family Medicine Physicians
    "15-1252.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 1.7, "E": 2.0, "C": 5.0},  # Software Developers
    "19-1029.00": {"R": 3.7, "I": 6.7, "A": 2.3, "S": 2.3, "E": 1.0, "C": 2.7},  # Biological Scientists
    "19-2031.00": {"R": 4.7, "I": 6.7, "A": 1.0, "S": 1.3, "E": 1.7, "C": 4.3},  # Chemists
    "15-2021.00": {"R": 1.0, "I": 7.0, "A": 2.3, "S": 1.7, "E": 1.0, "C": 4.3},  # Mathematicians
    "19-2012.00": {"R": 3.3, "I": 7.0, "A": 2.3, "S": 1.7, "E": 1.7, "C": 3.3},  # Physicists
    "19-1021.00": {"R": 4.3, "I": 6.7, "A": 2.0, "S": 1.7, "E": 2.0, "C": 3.7},  # Biochemists and Biophysicists
    "29-1051.00": {"R": 3.7, "I": 5.7, "A": 1.0, "S": 2.7, "E": 2.7, "C": 5.3},  # Pharmacists
    "15-1253.00": {"R": 3.0, "I": 5.7, "A": 2.0, "S": 1.3, "E": 1.7, "C": 6.0},  # Software QA Analysts and Testers
    "29-2011.00": {"R": 4.7, "I": 5.3, "A": 1.0, "S": 3.0, "E": 1.3, "C": 5.7},  # Medical and Clinical Laboratory Technologists
    "15-1212.00": {"R": 2.3, "I": 5.7, "A": 1.7, "S": 2.3, "E": 3.7, "C": 5.3},  # Information Security Analysts
    "29-2051.00": {"R": 4.0, "I": 4.7, "A": 1.0, "S": 4.7, "E": 1.7, "C": 5.0},  # Anesthesia / Ophthalmic Medical Techs
    "15-1299.09": {"R": 2.7, "I": 6.0, "A": 3.0, "S": 3.3, "E": 3.0, "C": 4.7},  # IT Project Managers

    # --- Artístico ---
    "27-1024.00": {"R": 2.0, "I": 2.3, "A": 6.7, "S": 1.7, "E": 3.7, "C": 2.3},  # Graphic Designers
    "27-1021.00": {"R": 5.3, "I": 3.7, "A": 5.3, "S": 1.0, "E": 2.7, "C": 2.3},  # Commercial and Industrial Designers
    "27-1022.00": {"R": 3.3, "I": 2.3, "A": 6.7, "S": 2.0, "E": 4.0, "C": 2.7},  # Fashion Designers
    "27-1013.00": {"R": 3.3, "I": 2.3, "A": 7.0, "S": 1.7, "E": 2.0, "C": 1.3},  # Fine Artists
    "27-2041.00": {"R": 1.7, "I": 3.3, "A": 7.0, "S": 3.3, "E": 3.7, "C": 2.3},  # Music Directors and Composers
    "27-4031.00": {"R": 4.7, "I": 2.7, "A": 6.7, "S": 2.0, "E": 3.0, "C": 3.0},  # Camera Operators (Film/TV)
    "27-2011.00": {"R": 1.7, "I": 2.3, "A": 7.0, "S": 3.3, "E": 4.7, "C": 1.7},  # Actors
    "27-3043.00": {"R": 1.0, "I": 5.3, "A": 6.7, "S": 3.7, "E": 1.7, "C": 2.3},  # Writers and Authors
    "27-4021.00": {"R": 4.0, "I": 2.7, "A": 6.7, "S": 3.0, "E": 3.7, "C": 3.0},  # Photographers
    "27-1014.00": {"R": 2.3, "I": 3.3, "A": 6.7, "S": 1.7, "E": 3.0, "C": 3.7},  # Special Effects Artists and Animators
    "15-1255.00": {"R": 2.0, "I": 4.3, "A": 5.7, "S": 3.0, "E": 3.3, "C": 4.3},  # Web and Digital Interface Designers
    "27-3091.00": {"R": 1.0, "I": 4.7, "A": 5.7, "S": 4.7, "E": 2.7, "C": 3.3},  # Interpreters and Translators
    "15-1252.01": {"R": 3.3, "I": 5.7, "A": 5.3, "S": 1.3, "E": 2.7, "C": 4.0},  # Video Game Designers

    # --- Social ---
    "19-3033.00": {"R": 1.0, "I": 5.7, "A": 3.7, "S": 6.7, "E": 2.3, "C": 2.3},  # Clinical and Counseling Psychologists
    "21-1029.00": {"R": 1.0, "I": 2.3, "A": 2.3, "S": 6.7, "E": 2.7, "C": 2.3},  # Social Workers
    "25-9031.00": {"R": 1.0, "I": 4.0, "A": 3.7, "S": 6.7, "E": 2.7, "C": 2.3},  # Instructional Coordinators
    "29-1141.00": {"R": 3.7, "I": 4.0, "A": 1.0, "S": 6.7, "E": 1.7, "C": 2.7},  # Registered Nurses
    "29-1123.00": {"R": 5.3, "I": 4.0, "A": 1.0, "S": 6.7, "E": 2.7, "C": 2.3},  # Physical Therapists
    "29-1031.00": {"R": 2.3, "I": 5.7, "A": 2.0, "S": 5.3, "E": 2.7, "C": 3.7},  # Dietitians and Nutritionists
    "29-1127.00": {"R": 2.0, "I": 4.0, "A": 2.3, "S": 6.7, "E": 2.3, "C": 3.7},  # Speech-Language Pathologists
    "29-1021.00": {"R": 5.7, "I": 5.7, "A": 2.7, "S": 3.7, "E": 2.7, "C": 2.3},  # Dentists, General
    "25-2031.00": {"R": 4.7, "I": 2.0, "A": 2.7, "S": 6.7, "E": 3.7, "C": 2.3},  # Secondary School Teachers
    "21-1093.00": {"R": 1.0, "I": 2.0, "A": 2.0, "S": 6.7, "E": 2.3, "C": 3.0},  # Social and Human Service Assistants
    "19-3041.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.7, "E": 1.7, "C": 2.3},  # Sociologists
    "25-2021.00": {"R": 1.3, "I": 2.7, "A": 3.7, "S": 6.7, "E": 3.0, "C": 3.0},  # Elementary School Teachers

    # --- Emprendedor ---
    "11-1021.00": {"R": 1.0, "I": 2.3, "A": 1.0, "S": 3.7, "E": 6.7, "C": 5.0},  # General and Operations Managers
    "23-1011.00": {"R": 1.0, "I": 4.0, "A": 2.7, "S": 5.3, "E": 6.3, "C": 5.0},  # Lawyers
    "11-2021.00": {"R": 1.0, "I": 2.3, "A": 5.3, "S": 3.7, "E": 6.7, "C": 2.7},  # Marketing Managers
    "11-2032.00": {"R": 1.0, "I": 2.7, "A": 4.3, "S": 4.7, "E": 6.7, "C": 3.3},  # Public Relations Managers
    "13-1022.00": {"R": 1.3, "I": 3.3, "A": 1.3, "S": 2.0, "E": 5.7, "C": 5.7},  # Wholesale and Retail Buyers
    "11-3121.00": {"R": 1.0, "I": 2.7, "A": 1.7, "S": 4.7, "E": 6.7, "C": 4.7},  # Human Resources Managers
    "27-3023.00": {"R": 1.0, "I": 3.7, "A": 5.7, "S": 5.0, "E": 4.0, "C": 2.0},  # News Analysts, Reporters, and Journalists
    "19-3094.00": {"R": 1.0, "I": 6.0, "A": 2.7, "S": 5.3, "E": 5.0, "C": 2.3},  # Political Scientists
    "39-7011.00": {"R": 1.3, "I": 2.3, "A": 3.7, "S": 5.7, "E": 5.3, "C": 3.7},  # Tour Guides and Escorts
    "41-9022.00": {"R": 1.7, "I": 2.0, "A": 2.7, "S": 3.0, "E": 6.3, "C": 4.7},  # Real Estate Sales Agents
    "11-2022.00": {"R": 1.0, "I": 3.3, "A": 3.7, "S": 2.7, "E": 6.7, "C": 4.0},  # Sales Managers

    # --- Convencional ---
    "13-2011.00": {"R": 1.0, "I": 3.7, "A": 1.0, "S": 2.0, "E": 4.0, "C": 6.7},  # Accountants and Auditors
    "19-3011.00": {"R": 1.0, "I": 6.3, "A": 1.0, "S": 2.3, "E": 4.0, "C": 5.3},  # Economists
    "13-2051.00": {"R": 1.0, "I": 4.7, "A": 1.3, "S": 1.7, "E": 5.3, "C": 6.7},  # Financial Analysts
    "15-2011.00": {"R": 1.0, "I": 6.7, "A": 1.7, "S": 2.0, "E": 3.7, "C": 6.3},  # Actuaries
    "11-3013.00": {"R": 1.3, "I": 3.0, "A": 1.3, "S": 3.3, "E": 5.3, "C": 6.3},  # Facilities Managers
    "13-1081.00": {"R": 3.0, "I": 4.0, "A": 1.3, "S": 2.7, "E": 4.7, "C": 6.3},  # Logisticians
    "15-2051.00": {"R": 2.3, "I": 6.7, "A": 2.3, "S": 2.0, "E": 3.3, "C": 5.7},  # Data Scientists
    "25-4022.00": {"R": 1.0, "I": 3.7, "A": 2.3, "S": 5.3, "E": 2.3, "C": 6.7},  # Librarians
    "43-3031.00": {"R": 1.0, "I": 2.0, "A": 1.0, "S": 2.0, "E": 2.3, "C": 7.0},  # Bookkeeping/Accounting Clerks
    "43-6011.00": {"R": 1.0, "I": 1.7, "A": 2.0, "S": 4.3, "E": 3.7, "C": 6.7},  # Executive Secretaries
}


# -----------------------------------------------------------------
# TABLA 2 - Lista maestra de carreras
# -----------------------------------------------------------------
# Cada carrera define:
#   id          -> identificador interno único (kebab/snake).
#   nombre      -> nombre legible que ve el usuario.
#   area        -> área de conocimiento (agrupador informativo).
#   onet_soc    -> código SOC de la ocupación O*NET equivalente
#                  (de aquí sale el vector RIASEC vía ONET_INTERESTS_07).
#   onet_titulo -> nombre de la ocupación O*NET (para trazabilidad/UI).
#   etiquetas   -> tags para la 2da capa de filtrado por aversión.
#
# Catálogo balanceado a través de las 6 dimensiones de Holland; cada
# carrera apunta a su ocupación O*NET de mayor afinidad real.
CARRERAS: list[dict] = [
    # ===================== Ingeniería y Tecnología =====================
    {"id": "ingenieria_mecanica", "nombre": "Ingeniería Mecánica", "area": "Ingeniería y Tecnología", "onet_soc": "17-2141.00", "onet_titulo": "Mechanical Engineers", "etiquetas": ["matematica_intensa"]},
    {"id": "ingenieria_civil", "nombre": "Ingeniería Civil", "area": "Ingeniería y Tecnología", "onet_soc": "17-2051.00", "onet_titulo": "Civil Engineers", "etiquetas": ["matematica_intensa", "trabajo_fisico"]},
    {"id": "ingenieria_electronica", "nombre": "Ingeniería Electrónica", "area": "Ingeniería y Tecnología", "onet_soc": "17-2072.00", "onet_titulo": "Electronics Engineers", "etiquetas": ["matematica_intensa"]},
    {"id": "ingenieria_industrial", "nombre": "Ingeniería Industrial", "area": "Ingeniería y Tecnología", "onet_soc": "17-2112.00", "onet_titulo": "Industrial Engineers", "etiquetas": ["matematica_intensa"]},
    {"id": "ingenieria_quimica", "nombre": "Ingeniería Química", "area": "Ingeniería y Tecnología", "onet_soc": "17-2041.00", "onet_titulo": "Chemical Engineers", "etiquetas": ["matematica_intensa"]},
    {"id": "ingenieria_mecatronica", "nombre": "Ingeniería Mecatrónica", "area": "Ingeniería y Tecnología", "onet_soc": "17-2141.02", "onet_titulo": "Mechatronics Engineers", "etiquetas": ["matematica_intensa", "programacion"]},
    {"id": "ingenieria_electrica", "nombre": "Ingeniería Eléctrica", "area": "Ingeniería y Tecnología", "onet_soc": "17-2071.00", "onet_titulo": "Electrical Engineers", "etiquetas": ["matematica_intensa"]},
    {"id": "ingenieria_sistemas", "nombre": "Ingeniería en Sistemas / Informática", "area": "Ingeniería y Tecnología", "onet_soc": "15-1252.00", "onet_titulo": "Software Developers", "etiquetas": ["programacion", "matematica_intensa"]},
    {"id": "ciberseguridad", "nombre": "Licenciatura en Ciberseguridad", "area": "Ingeniería y Tecnología", "onet_soc": "15-1212.00", "onet_titulo": "Information Security Analysts", "etiquetas": ["programacion"]},
    {"id": "tecnologias_digitales", "nombre": "Licenciatura en Tecnologías Digitales", "area": "Ingeniería y Tecnología", "onet_soc": "15-1299.09", "onet_titulo": "IT Project Managers", "etiquetas": ["programacion"]},
    {"id": "tec_programacion", "nombre": "Tecnicatura en Programación", "area": "Ingeniería y Tecnología", "onet_soc": "15-1253.00", "onet_titulo": "Software QA Analysts and Testers", "etiquetas": ["programacion"]},
    {"id": "ciencia_datos", "nombre": "Licenciatura en Ciencia de Datos", "area": "Ingeniería y Tecnología", "onet_soc": "15-2051.00", "onet_titulo": "Data Scientists", "etiquetas": ["programacion", "matematica_intensa"]},
    {"id": "tec_energias_renovables", "nombre": "Tecnicatura en Energías Renovables", "area": "Ingeniería y Tecnología", "onet_soc": "17-3029.08", "onet_titulo": "Energy Engineering Technicians", "etiquetas": ["trabajo_fisico"]},
    {"id": "tec_mantenimiento_industrial", "nombre": "Tecnicatura en Mantenimiento Industrial", "area": "Ingeniería y Tecnología", "onet_soc": "49-9041.00", "onet_titulo": "Industrial Machinery Mechanics", "etiquetas": ["trabajo_fisico"]},
    {"id": "tec_higiene_seguridad", "nombre": "Tecnicatura en Higiene y Seguridad Laboral", "area": "Ingeniería y Tecnología", "onet_soc": "19-5011.00", "onet_titulo": "Occupational Health & Safety Specialists", "etiquetas": ["trabajo_fisico"]},

    # ===================== Ciencias Naturales y Exactas =====================
    {"id": "biologia", "nombre": "Licenciatura en Biología", "area": "Ciencias Naturales y Exactas", "onet_soc": "19-1029.00", "onet_titulo": "Biological Scientists", "etiquetas": []},
    {"id": "quimica", "nombre": "Licenciatura en Química", "area": "Ciencias Naturales y Exactas", "onet_soc": "19-2031.00", "onet_titulo": "Chemists", "etiquetas": []},
    {"id": "matematica", "nombre": "Licenciatura en Matemática", "area": "Ciencias Naturales y Exactas", "onet_soc": "15-2021.00", "onet_titulo": "Mathematicians", "etiquetas": ["matematica_intensa"]},
    {"id": "fisica", "nombre": "Licenciatura en Física", "area": "Ciencias Naturales y Exactas", "onet_soc": "19-2012.00", "onet_titulo": "Physicists", "etiquetas": ["matematica_intensa"]},
    {"id": "biotecnologia", "nombre": "Licenciatura en Biotecnología", "area": "Ciencias Naturales y Exactas", "onet_soc": "19-1021.00", "onet_titulo": "Biochemists and Biophysicists", "etiquetas": []},
    {"id": "agronomia", "nombre": "Ingeniería Agronómica", "area": "Ciencias Naturales y Exactas", "onet_soc": "17-2021.00", "onet_titulo": "Agricultural Engineers", "etiquetas": ["trabajo_fisico"]},
    {"id": "tec_produccion_agropecuaria", "nombre": "Tecnicatura en Producción Agropecuaria", "area": "Ciencias Naturales y Exactas", "onet_soc": "45-2011.00", "onet_titulo": "Agricultural Inspectors", "etiquetas": ["trabajo_fisico"]},

    # ===================== Ciencias de la Salud =====================
    {"id": "medicina", "nombre": "Medicina", "area": "Ciencias de la Salud", "onet_soc": "29-1221.00", "onet_titulo": "Family Medicine Physicians", "etiquetas": ["contacto_pacientes"]},
    {"id": "odontologia", "nombre": "Odontología", "area": "Ciencias de la Salud", "onet_soc": "29-1021.00", "onet_titulo": "Dentists, General", "etiquetas": ["contacto_pacientes"]},
    {"id": "enfermeria", "nombre": "Licenciatura en Enfermería", "area": "Ciencias de la Salud", "onet_soc": "29-1141.00", "onet_titulo": "Registered Nurses", "etiquetas": ["contacto_pacientes"]},
    {"id": "kinesiologia", "nombre": "Kinesiología y Fisiatría", "area": "Ciencias de la Salud", "onet_soc": "29-1123.00", "onet_titulo": "Physical Therapists", "etiquetas": ["contacto_pacientes"]},
    {"id": "nutricion", "nombre": "Licenciatura en Nutrición", "area": "Ciencias de la Salud", "onet_soc": "29-1031.00", "onet_titulo": "Dietitians and Nutritionists", "etiquetas": ["contacto_pacientes"]},
    {"id": "fonoaudiologia", "nombre": "Fonoaudiología", "area": "Ciencias de la Salud", "onet_soc": "29-1127.00", "onet_titulo": "Speech-Language Pathologists", "etiquetas": ["contacto_pacientes"]},
    {"id": "veterinaria", "nombre": "Veterinaria", "area": "Ciencias de la Salud", "onet_soc": "29-1131.00", "onet_titulo": "Veterinarians", "etiquetas": ["contacto_pacientes", "trabajo_fisico"]},
    {"id": "farmacia", "nombre": "Farmacia", "area": "Ciencias de la Salud", "onet_soc": "29-1051.00", "onet_titulo": "Pharmacists", "etiquetas": []},
    {"id": "tec_laboratorio", "nombre": "Tecnicatura en Análisis Clínicos / Laboratorio", "area": "Ciencias de la Salud", "onet_soc": "29-2011.00", "onet_titulo": "Medical and Clinical Laboratory Technologists", "etiquetas": []},
    {"id": "tec_instrumentacion_quirurgica", "nombre": "Instrumentación Quirúrgica", "area": "Ciencias de la Salud", "onet_soc": "29-2055.00", "onet_titulo": "Surgical Technologists", "etiquetas": ["contacto_pacientes"]},
    {"id": "tec_anestesia", "nombre": "Tecnicatura en Anestesia", "area": "Ciencias de la Salud", "onet_soc": "29-2051.00", "onet_titulo": "Anesthesia / Ophthalmic Medical Techs", "etiquetas": ["contacto_pacientes"]},
    {"id": "acompanamiento_terapeutico", "nombre": "Acompañamiento Terapéutico", "area": "Ciencias de la Salud", "onet_soc": "21-1093.00", "onet_titulo": "Social and Human Service Assistants", "etiquetas": ["contacto_pacientes"]},
    {"id": "gastronomia", "nombre": "Gastronomía", "area": "Ciencias de la Salud", "onet_soc": "35-1011.00", "onet_titulo": "Chefs and Head Cooks", "etiquetas": ["trabajo_fisico"]},

    # ===================== Arte y Diseño =====================
    {"id": "arquitectura", "nombre": "Arquitectura", "area": "Arte y Diseño", "onet_soc": "17-1011.00", "onet_titulo": "Architects", "etiquetas": ["expresion_artistica"]},
    {"id": "diseno_grafico", "nombre": "Diseño Gráfico", "area": "Arte y Diseño", "onet_soc": "27-1024.00", "onet_titulo": "Graphic Designers", "etiquetas": ["expresion_artistica"]},
    {"id": "diseno_industrial", "nombre": "Diseño Industrial", "area": "Arte y Diseño", "onet_soc": "27-1021.00", "onet_titulo": "Commercial and Industrial Designers", "etiquetas": ["expresion_artistica"]},
    {"id": "diseno_indumentaria", "nombre": "Diseño de Indumentaria", "area": "Arte y Diseño", "onet_soc": "27-1022.00", "onet_titulo": "Fashion Designers", "etiquetas": ["expresion_artistica"]},
    {"id": "diseno_multimedial", "nombre": "Diseño Multimedial y Animación", "area": "Arte y Diseño", "onet_soc": "27-1014.00", "onet_titulo": "Special Effects Artists and Animators", "etiquetas": ["expresion_artistica"]},
    {"id": "diseno_ux_ui", "nombre": "Diseño de Interfaces (UX/UI)", "area": "Arte y Diseño", "onet_soc": "15-1255.00", "onet_titulo": "Web and Digital Interface Designers", "etiquetas": ["expresion_artistica"]},
    {"id": "artes_visuales", "nombre": "Artes Visuales", "area": "Arte y Diseño", "onet_soc": "27-1013.00", "onet_titulo": "Fine Artists", "etiquetas": ["expresion_artistica"]},
    {"id": "musica", "nombre": "Música", "area": "Arte y Diseño", "onet_soc": "27-2041.00", "onet_titulo": "Music Directors and Composers", "etiquetas": ["expresion_artistica"]},
    {"id": "artes_audiovisuales", "nombre": "Artes Audiovisuales", "area": "Arte y Diseño", "onet_soc": "27-4031.00", "onet_titulo": "Camera Operators (Film/TV)", "etiquetas": ["expresion_artistica"]},
    {"id": "fotografia", "nombre": "Fotografía", "area": "Arte y Diseño", "onet_soc": "27-4021.00", "onet_titulo": "Photographers", "etiquetas": ["expresion_artistica"]},
    {"id": "actuacion", "nombre": "Actuación / Artes Dramáticas", "area": "Arte y Diseño", "onet_soc": "27-2011.00", "onet_titulo": "Actors", "etiquetas": ["expresion_artistica", "exposicion_publica"]},
    {"id": "creacion_videojuegos", "nombre": "Desarrollo y Producción de Videojuegos", "area": "Arte y Diseño", "onet_soc": "15-1252.01", "onet_titulo": "Video Game Designers", "etiquetas": ["programacion", "expresion_artistica"]},

    # ===================== Ciencias Sociales y Humanidades =====================
    {"id": "psicologia", "nombre": "Psicología", "area": "Ciencias Sociales y Humanidades", "onet_soc": "19-3033.00", "onet_titulo": "Clinical and Counseling Psychologists", "etiquetas": []},
    {"id": "trabajo_social", "nombre": "Licenciatura en Trabajo Social", "area": "Ciencias Sociales y Humanidades", "onet_soc": "21-1029.00", "onet_titulo": "Social Workers", "etiquetas": []},
    {"id": "sociologia", "nombre": "Sociología", "area": "Ciencias Sociales y Humanidades", "onet_soc": "19-3041.00", "onet_titulo": "Sociologists", "etiquetas": []},
    {"id": "ciencia_politica", "nombre": "Ciencia Política", "area": "Ciencias Sociales y Humanidades", "onet_soc": "19-3094.00", "onet_titulo": "Political Scientists", "etiquetas": []},
    {"id": "abogacia", "nombre": "Abogacía", "area": "Ciencias Sociales y Humanidades", "onet_soc": "23-1011.00", "onet_titulo": "Lawyers", "etiquetas": ["exposicion_publica"]},
    {"id": "comunicacion_social", "nombre": "Comunicación Social / Periodismo", "area": "Ciencias Sociales y Humanidades", "onet_soc": "27-3023.00", "onet_titulo": "News Analysts, Reporters, and Journalists", "etiquetas": ["exposicion_publica"]},
    {"id": "letras", "nombre": "Letras", "area": "Ciencias Sociales y Humanidades", "onet_soc": "27-3043.00", "onet_titulo": "Writers and Authors", "etiquetas": ["expresion_artistica"]},
    {"id": "traductorado", "nombre": "Traductorado", "area": "Ciencias Sociales y Humanidades", "onet_soc": "27-3091.00", "onet_titulo": "Interpreters and Translators", "etiquetas": []},
    {"id": "archivologia", "nombre": "Bibliotecología y Archivología", "area": "Ciencias Sociales y Humanidades", "onet_soc": "25-4022.00", "onet_titulo": "Librarians", "etiquetas": []},

    # ===================== Educación =====================
    {"id": "ciencias_educacion", "nombre": "Ciencias de la Educación", "area": "Educación", "onet_soc": "25-9031.00", "onet_titulo": "Instructional Coordinators", "etiquetas": []},
    {"id": "profesorado_educacion_primaria", "nombre": "Profesorado de Educación Primaria", "area": "Educación", "onet_soc": "25-2021.00", "onet_titulo": "Elementary School Teachers", "etiquetas": []},
    {"id": "profesorado_educacion_fisica", "nombre": "Profesorado de Educación Física", "area": "Educación", "onet_soc": "25-2031.00", "onet_titulo": "Secondary School Teachers", "etiquetas": ["trabajo_fisico"]},
    {"id": "profesorado_ciencias_exactas", "nombre": "Profesorado en Ciencias Exactas", "area": "Educación", "onet_soc": "25-2031.00", "onet_titulo": "Secondary School Teachers", "etiquetas": ["matematica_intensa"]},

    # ===================== Economía y Negocios =====================
    {"id": "administracion_empresas", "nombre": "Licenciatura en Administración de Empresas", "area": "Economía y Negocios", "onet_soc": "11-1021.00", "onet_titulo": "General and Operations Managers", "etiquetas": ["exposicion_publica"]},
    {"id": "marketing", "nombre": "Licenciatura en Marketing", "area": "Economía y Negocios", "onet_soc": "11-2021.00", "onet_titulo": "Marketing Managers", "etiquetas": ["exposicion_publica"]},
    {"id": "relaciones_publicas", "nombre": "Relaciones Públicas", "area": "Economía y Negocios", "onet_soc": "11-2032.00", "onet_titulo": "Public Relations Managers", "etiquetas": ["exposicion_publica"]},
    {"id": "recursos_humanos", "nombre": "Relaciones del Trabajo / Recursos Humanos", "area": "Economía y Negocios", "onet_soc": "11-3121.00", "onet_titulo": "Human Resources Managers", "etiquetas": ["exposicion_publica"]},
    {"id": "comercio_internacional", "nombre": "Comercio Internacional", "area": "Economía y Negocios", "onet_soc": "13-1022.00", "onet_titulo": "Wholesale and Retail Buyers", "etiquetas": ["exposicion_publica"]},
    {"id": "negocios_digitales", "nombre": "Negocios Digitales", "area": "Economía y Negocios", "onet_soc": "11-2022.00", "onet_titulo": "Sales Managers", "etiquetas": ["exposicion_publica"]},
    {"id": "tec_turismo", "nombre": "Tecnicatura en Turismo", "area": "Economía y Negocios", "onet_soc": "39-7011.00", "onet_titulo": "Tour Guides and Escorts", "etiquetas": ["exposicion_publica"]},
    {"id": "martillero_publico", "nombre": "Martillero Público y Corredor Inmobiliario", "area": "Economía y Negocios", "onet_soc": "41-9022.00", "onet_titulo": "Real Estate Sales Agents", "etiquetas": ["exposicion_publica"]},
    {"id": "contador_publico", "nombre": "Contador Público", "area": "Economía y Negocios", "onet_soc": "13-2011.00", "onet_titulo": "Accountants and Auditors", "etiquetas": []},
    {"id": "economia", "nombre": "Licenciatura en Economía", "area": "Economía y Negocios", "onet_soc": "19-3011.00", "onet_titulo": "Economists", "etiquetas": ["matematica_intensa"]},
    {"id": "finanzas", "nombre": "Licenciatura en Finanzas", "area": "Economía y Negocios", "onet_soc": "13-2051.00", "onet_titulo": "Financial Analysts", "etiquetas": ["matematica_intensa"]},
    {"id": "actuario", "nombre": "Ciencias Actuariales (Actuario)", "area": "Economía y Negocios", "onet_soc": "15-2011.00", "onet_titulo": "Actuaries", "etiquetas": ["matematica_intensa"]},
    {"id": "administracion_publica", "nombre": "Administración Pública", "area": "Economía y Negocios", "onet_soc": "11-3013.00", "onet_titulo": "Facilities / Public Administration Managers", "etiquetas": []},
    {"id": "logistica", "nombre": "Licenciatura en Logística", "area": "Economía y Negocios", "onet_soc": "13-1081.00", "onet_titulo": "Logisticians", "etiquetas": []},
    {"id": "tec_administracion_contable", "nombre": "Tecnicatura en Administración Contable", "area": "Economía y Negocios", "onet_soc": "43-3031.00", "onet_titulo": "Bookkeeping / Accounting Clerks", "etiquetas": []},
    {"id": "secretariado_ejecutivo", "nombre": "Secretariado Ejecutivo", "area": "Economía y Negocios", "onet_soc": "43-6011.00", "onet_titulo": "Executive Secretaries", "etiquetas": []},
]


# -----------------------------------------------------------------
# Reescala de la escala O*NET (0-7) a la escala interna (1-5)
# -----------------------------------------------------------------
def reescalar_07_a_15(valor_07: float) -> int:
    """Convierte un puntaje O*NET (0-7) al rango entero 1-5.

    Fórmula lineal: 1 + (valor/7) * 4, redondeada al entero más
    cercano. Mantiene el orden relativo de los intereses y los lleva
    a la misma escala Likert que responde el usuario.
    """
    if valor_07 <= 0:
        return 1
    if valor_07 >= 7:
        return 5
    return int(round(1 + (valor_07 / 7) * 4))


def vector_riasec(soc_code: str) -> dict[str, int]:
    """Devuelve el vector RIASEC (1-5) de una ocupación O*NET."""
    crudo = ONET_INTERESTS_07[soc_code]
    # Reordenamos según DIMENSIONES para garantizar consistencia.
    return {dim: reescalar_07_a_15(crudo[dim]) for dim in DIMENSIONES}


# -----------------------------------------------------------------
# Construcción y validación del catálogo
# -----------------------------------------------------------------
def construir() -> list[dict]:
    """Arma la lista final de carreras con su vector RIASEC."""
    catalogo: list[dict] = []
    for c in CARRERAS:
        catalogo.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "area": c["area"],
            "onet_soc": c["onet_soc"],
            "onet_titulo": c["onet_titulo"],
            "riasec": vector_riasec(c["onet_soc"]),
            "etiquetas": list(c["etiquetas"]),
        })
    return catalogo


def validar(catalogo: list[dict]) -> None:
    """Verifica el contrato de datos. Lanza AssertionError si algo falla."""
    ids_vistos = set()
    for c in catalogo:
        assert c["id"] not in ids_vistos, f"ID duplicado: {c['id']}"
        ids_vistos.add(c["id"])

        assert c["onet_soc"] in ONET_INTERESTS_07, f"{c['id']}: SOC sin datos O*NET"

        assert set(c["riasec"].keys()) == set(DIMENSIONES), f"{c['id']}: RIASEC incompleto"
        for dim, val in c["riasec"].items():
            assert isinstance(val, int) and 1 <= val <= 5, f"{c['id']}: {dim}={val!r} fuera de 1-5"

        for tag in c["etiquetas"]:
            assert tag in ETIQUETAS_VALIDAS, f"{c['id']}: etiqueta desconocida {tag!r}"

    print(f"Validación OK: {len(catalogo)} carreras, sin duplicados, RIASEC y etiquetas correctas.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera data/carreras.json desde la tabla O*NET.")
    parser.add_argument("--dry-run", action="store_true", help="Construye y valida pero no escribe el JSON.")
    args = parser.parse_args()

    catalogo = construir()
    validar(catalogo)

    if args.dry_run:
        print("[dry-run] no se escribió disco.")
        return 0

    dataset = {
        "_meta": {
            "descripcion": "Catálogo de carreras con su vector RIASEC (Holland) derivado de O*NET. Generado por build_catalog.py.",
            "fuente_riasec": "O*NET Interests v28.x (U.S. Department of Labor), reescalado 0-7 -> 1-5.",
            "total_carreras": len(catalogo),
        },
        "carreras": catalogo,
    }
    JSON_CATALOGO.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Catálogo escrito: {JSON_CATALOGO} ({len(catalogo)} carreras).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
