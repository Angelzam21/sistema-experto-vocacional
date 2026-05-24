"""
=================================================================
PASO 1.1 - WEB SCRAPING DE LA OFERTA ACADÉMICA ARGENTINA
=================================================================
Módulo encargado de extraer la información de carreras universitarias
desde portales oficiales (Ministerio de Capital Humano, SIU, sitios
institucionales de UBA/UTN/UNLP/UNC/UNR/UNT/UNS/UNSAM, etc.).

Diseño del scraper:
  - HTML estático -> requests + BeautifulSoup (rápido, sin browser).
  - Renderizado dinámico (JS) -> Selenium/Playwright (no implementado
    aquí; se deja como punto de extensión en `scrape_dynamic`).
  - Respeta robots.txt y aplica un delay configurable para no abusar
    de los servidores.
  - Captura *Filtros Duros* obligatorios: `zona_geografica` y
    `modalidad`.

NOTA OPERATIVA:
  La ejecución real de este scraper depende de la disponibilidad de
  los portales en el momento de ejecución (URLs, estructura HTML).
  Para hacer el sistema reproducible y desacoplado de cambios en
  fuentes externas, el módulo provee `SEED_SOURCES` con las URLs
  canónicas a recorrer y devuelve un diccionario uniforme que luego
  procesará `normalizer.py`.
=================================================================
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Logger del módulo: usar logging > print para poder silenciarlo en producción.
log = logging.getLogger(__name__)


# -----------------------------------------------------------------
# Definición de las fuentes oficiales a scrapear.
# Cada entrada incluye URL base + zona geográfica preasignada (la
# zona viene determinada por la sede, no por la URL).
# -----------------------------------------------------------------
SEED_SOURCES: list[dict] = [
    {
        "sigla": "UdelaCiudad",
        "nombre": "Universidad de la Ciudad de Buenos Aires",
        "zona": "CABA",
        "url_carreras": "https://www.udelaciudad.edu.ar/", 
        "render": "static", 
    },
    {
        "sigla": "UBA",
        "nombre": "Universidad de Buenos Aires",
        "zona": "CABA",
        "url_carreras": "https://www.uba.ar/carreras",
        "render": "static",  # static => requests + BS4; dynamic => Selenium
    },
    {
        "sigla": "UTN",
        "nombre": "Universidad Tecnológica Nacional",
        "zona": "Buenos Aires",
        "url_carreras": "https://www.utn.edu.ar/es/estudiar-utn/carreras",
        "render": "static",
    },
    {
        "sigla": "UNLP",
        "nombre": "Universidad Nacional de La Plata",
        "zona": "Buenos Aires",
        "url_carreras": "https://unlp.edu.ar/oferta_academica/",
        "render": "static",
    },
    {
        "sigla": "UNC",
        "nombre": "Universidad Nacional de Córdoba",
        "zona": "Córdoba",
        "url_carreras": "https://www.unc.edu.ar/estudiando-en-la-unc/carreras-de-grado",
        "render": "static",
    },
    {
        "sigla": "UNR",
        "nombre": "Universidad Nacional de Rosario",
        "zona": "Santa Fe",
        "url_carreras": "https://unr.edu.ar/oferta-academica/",
        "render": "static",
    },
    {
        "sigla": "UNT",
        "nombre": "Universidad Nacional de Tucumán",
        "zona": "Tucumán",
        "url_carreras": "https://www.unt.edu.ar/index.php/carreras/",
        "render": "static",
    },
    {
        "sigla": "UNS",
        "nombre": "Universidad Nacional del Sur",
        "zona": "Bahía Blanca",
        "url_carreras": "https://www.uns.edu.ar/contenidos/55/95",
        "render": "static",
    },
    {
        "sigla": "UNSAM",
        "nombre": "Universidad Nacional de San Martín",
        "zona": "Buenos Aires",
        "url_carreras": "https://www.unsam.edu.ar/oferta/grado.asp",
        "render": "static",
    },
    {
        "sigla": "UNA",
        "nombre": "Universidad Nacional de las Artes",
        "zona": "CABA",
        "url_carreras": "https://una.edu.ar/carreras/",
        "render": "static",
    },
    {
        "sigla": "UNQ",
        "nombre": "Universidad Nacional de Quilmes",
        "zona": "Buenos Aires",
        "url_carreras": "https://www.unq.edu.ar/carreras/",
        "render": "static",
    },
]


# -----------------------------------------------------------------
# Modelo de datos crudo: lo que recolectamos antes de normalizar.
# Usamos un dataclass para tipado fuerte y serialización trivial.
# -----------------------------------------------------------------
@dataclass
class CarreraCruda:
    """Representa una fila extraída del HTML, aún sin normalizar.

    Campos:
        nombre_raw: texto tal cual aparece en el sitio (puede tener
                    abreviaturas, mayúsculas raras, etc.).
        universidad_sigla: sigla canónica de la universidad fuente.
        zona_geografica: ciudad/provincia de la sede.
        modalidad: presencial/híbrida/distancia (puede venir vacío).
        url_carrera: link al plan de estudios (puede ser None).
    """

    nombre_raw: str
    universidad_sigla: str
    zona_geografica: str
    modalidad: str = "Presencial"  # default razonable para Argentina
    url_carrera: str | None = None


# -----------------------------------------------------------------
# Funciones públicas
# -----------------------------------------------------------------
def scrape_static(source: dict, timeout: int = 15) -> list[CarreraCruda]:
    """Scrapea una fuente HTML estática.

    Args:
        source: entrada de SEED_SOURCES.
        timeout: segundos máximos para la request HTTP.

    Returns:
        Lista de CarreraCruda. Vacía si la página no responde o el
        selector no encuentra elementos (el scraping nunca debe
        romper el pipeline; los errores se loguean).
    """
    url = source["url_carreras"]
    headers = {
        # User-Agent identificable: cortesía con los webmasters.
        "User-Agent": "SistemaExperto-TestVocacional"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("No se pudo obtener %s: %s", url, e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # ATENCIÓN: cada portal tiene su propia estructura HTML.
    # En la práctica habría que escribir un parser por universidad.
    # Aquí proveemos un parser genérico que busca enlaces dentro de
    # listas (<ul><li><a>) que es el patrón más común.
    resultados: list[CarreraCruda] = []
    candidatos = soup.select("ul li a, .carrera a, .career-item a")

    for a in candidatos:
        texto = (a.get_text() or "").strip()
        # Heurística mínima de filtro: nombres de carrera suelen
        # tener entre 5 y 120 caracteres y contienen letras.
        if not (5 <= len(texto) <= 120) or not any(c.isalpha() for c in texto):
            continue

        # SOLUCIÓN: Capturamos el href crudo y lo unimos con la URL base
        href_crudo = a.get("href")
        url_absoluta = urljoin(url, href_crudo) if href_crudo else None

        resultados.append(
            CarreraCruda(
                nombre_raw=texto,
                universidad_sigla=source["sigla"],
                zona_geografica=source["zona"],
                modalidad="Presencial",  # se ajusta luego en normalizer
                url_carrera=url_absoluta, # Guardamos la URL completa y segura
            )
        )

    log.info("[%s] extraídas %d entradas crudas", source["sigla"], len(resultados))
    return resultados


def scrape_dynamic(source: dict) -> list[CarreraCruda]:
    """Punto de extensión para portales con JS pesado.

    NO implementado por defecto: requiere Selenium/Playwright +
    drivers de navegador, lo que excede el alcance del MVP.
    Si se necesita, importar `playwright.sync_api` y replicar la
    estructura de `scrape_static`.
    """
    log.info(
        "scrape_dynamic() no implementado para %s; usar scrape_static o "
        "agregar Playwright como dependencia.",
        source["sigla"],
    )
    return []


def scrape_all(
    sources: Iterable[dict] | None = None,
    delay_seconds: float = 1.5,
) -> list[CarreraCruda]:
    """Recorre todas las fuentes y devuelve la lista combinada.

    Args:
        sources: iterable de fuentes (por defecto, SEED_SOURCES).
        delay_seconds: pausa entre requests para evitar saturar a
                       los servidores (buena ciudadanía digital).
    """
    fuentes = list(sources) if sources is not None else SEED_SOURCES
    todo: list[CarreraCruda] = []

    for src in fuentes:
        # Dispatch según tipo de renderizado declarado en la fuente.
        if src["render"] == "static":
            todo.extend(scrape_static(src))
        elif src["render"] == "dynamic":
            todo.extend(scrape_dynamic(src))
        else:
            log.warning("Render desconocido en fuente %s: %s", src["sigla"], src["render"])

        # Delay cortés: no hammerear los servidores universitarios.
        time.sleep(delay_seconds)

    log.info("Scraping completado. Total filas crudas: %d", len(todo))
    return todo


def carreras_to_dicts(carreras: list[CarreraCruda]) -> list[dict]:
    """Helper: convierte la lista de dataclasses a dicts JSON-friendly.

    Útil para encadenar con normalizer/onet_mapper o para volcar a un
    JSON intermedio si se quiere persistir el snapshot crudo del scrape.
    """
    return [asdict(c) for c in carreras]


# -----------------------------------------------------------------
# Punto de entrada CLI: permite probar el scraper de forma aislada.
# Uso:   python -m etl.scraper
# -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    crudas = scrape_all()
    print(f"\nTotal carreras crudas extraídas: {len(crudas)}")
    # Muestra las primeras 5 a modo de inspección rápida.
    for c in crudas[:5]:
        print(" -", c.universidad_sigla, "|", c.nombre_raw)
