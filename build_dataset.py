"""
=================================================================
ORQUESTADOR DE LA FASE 1 (ETL) - EJECUCIÓN ÚNICA / OFFLINE
=================================================================
Corre el pipeline completo:

    scraper.py  ->  normalizer.py  ->  onet_mapper.py
                                                |
                                                v
                              data/carreras_argentina.json

Uso:
    python build_dataset.py            # corre el pipeline completo
    python build_dataset.py --dry-run  # corre sin escribir disco
    python build_dataset.py --verify   # solo valida el JSON existente

Importante: el plan técnico indica que este script se ejecuta UNA
SOLA VEZ. Por eso preserva siempre una copia *.bak del JSON anterior
antes de sobrescribirlo (auditoría / rollback rápido).
=================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from etl import scraper, normalizer, onet_mapper

# ----- Configuración global -----
DATA_DIR = Path(__file__).parent / "data"
JSON_MAESTRO = DATA_DIR / "carreras_argentina.json"
JSON_BACKUP = DATA_DIR / "carreras_argentina.json.bak"

log = logging.getLogger("build_dataset")


# -----------------------------------------------------------------
# Validador: chequea que el JSON cumpla el contrato del plan.
# -----------------------------------------------------------------
def validar_json(path: Path) -> bool:
    """Verifica estructura mínima del JSON maestro.

    Reglas:
      - debe existir y ser JSON válido
      - clave 'carreras' presente y no vacía
      - cada carrera tiene id, nombre, riasec, modalidad, zona_geografica
      - riasec contiene las 6 dimensiones con valores int en [1,5]
    """
    if not path.exists():
        log.error("No existe %s", path)
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log.error("JSON inválido en %s: %s", path, e)
        return False

    carreras = data.get("carreras")
    if not carreras:
        log.error("Falta o está vacía la clave 'carreras'.")
        return False

    requeridos = {"id", "nombre", "riasec", "modalidad", "zona_geografica"}
    dimensiones = {"R", "I", "A", "S", "E", "C"}

    for c in carreras:
        faltantes = requeridos - c.keys()
        if faltantes:
            log.error("Carrera %s sin campos: %s", c.get("id", "?"), faltantes)
            return False

        riasec = c["riasec"]
        if set(riasec.keys()) != dimensiones:
            log.error("Carrera %s tiene RIASEC con dimensiones %s", c["id"], list(riasec.keys()))
            return False

        for dim, val in riasec.items():
            if not isinstance(val, int) or not (1 <= val <= 5):
                log.error("Carrera %s tiene RIASEC.%s = %r (esperado int 1-5)", c["id"], dim, val)
                return False

    log.info("Validación OK: %d carreras correctas.", len(carreras))
    return True


# -----------------------------------------------------------------
# Pipeline principal
# -----------------------------------------------------------------
def construir_dataset(dry_run: bool = False) -> dict:
    """Ejecuta el pipeline completo y devuelve el dataset construido.

    Si dry_run=True NO escribe a disco (útil para pruebas en CI).
    """
    log.info("=== Fase 1.1 - Web scraping ===")
    crudas = scraper.scrape_all()

    log.info("=== Fase 1.2 - Normalización ===")
    normalizadas = normalizer.normalizar_lote(crudas)

    log.info("=== Fase 1.3 - Enriquecimiento RIASEC ===")
    enriquecidas = onet_mapper.enriquecer_lote(normalizadas)

    # Empaquetado final con metadatos para trazabilidad.
    dataset = {
        "_meta": {
            "descripcion": "Dataset maestro generado por build_dataset.py",
            "total_carreras": len(enriquecidas),
            "pipeline_version": "1.0",
        },
        "carreras": [
            asdict(c) if is_dataclass(c) else c
            for c in enriquecidas
        ],
    }

    if dry_run:
        log.info("[dry-run] no se escribe disco. Carreras en memoria: %d", len(enriquecidas))
        return dataset

    # Backup defensivo: el plan dice "ejecución única" pero conviene
    # no perder la versión previa si alguien vuelve a correrlo.
    if JSON_MAESTRO.exists():
        shutil.copy2(JSON_MAESTRO, JSON_BACKUP)
        log.info("Backup creado: %s", JSON_BACKUP.name)

    JSON_MAESTRO.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("JSON maestro escrito: %s", JSON_MAESTRO)
    return dataset


# -----------------------------------------------------------------
# CLI
# -----------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline ETL del Sistema Experto Vocacional.")
    parser.add_argument("--dry-run", action="store_true", help="No escribir el JSON resultante.")
    parser.add_argument("--verify", action="store_true", help="Solo validar el JSON existente.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs DEBUG.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.verify:
        ok = validar_json(JSON_MAESTRO)
        return 0 if ok else 1

    construir_dataset(dry_run=args.dry_run)
    # Cuando NO es dry-run, validamos lo que acabamos de escribir.
    if not args.dry_run:
        if not validar_json(JSON_MAESTRO):
            log.error("El dataset generado no pasó la validación.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
