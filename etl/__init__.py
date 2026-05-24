# =========================================================
# Paquete ETL - Sistema Experto Vocacional
# =========================================================
# Agrupa los tres módulos de la Fase 1 (ejecución única offline):
#   - scraper.py     : Paso 1.1 - extracción HTML de oferta académica
#   - normalizer.py  : Paso 1.2 - saneamiento y unificación de sinónimos
#   - onet_mapper.py : Paso 1.3 - enriquecimiento RIASEC desde O*NET
#
# El orquestador build_dataset.py (en la raíz) corre los tres en orden
# y persiste el JSON maestro carreras_argentina.json.
# =========================================================
