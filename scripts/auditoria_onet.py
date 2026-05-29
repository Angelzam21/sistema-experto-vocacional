"""
Auditoría del mapeo O*NET -> RIASEC del catálogo de carreras.

Diagnóstico (no modifica datos). Reporta:
  1. Divergencias entre carreras.json y lo que build_catalog.py generaría.
  2. Bug de reescalado: O*NET usa escala 1-7, no 0-7. Cuánto comprime el piso.
  3. High-point: dimensión dominante O*NET (0-7 crudo) vs Holland del vector
     1-5 almacenado. Marca STEM con pico Social, etc.
  4. Colisiones: grupos de carreras con vector RIASEC 1-5 idéntico (empates).
  5. Resolución: cuántos valores distintos toma cada dimensión.

Uso: python scripts/auditoria_onet.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from build_catalog import (  # noqa: E402
    CARRERAS,
    DIMENSIONES,
    ONET_INTERESTS_07,
    reescalar_07_a_15,
    vector_riasec,
)

CATALOGO = json.loads((RAIZ / "data" / "carreras.json").read_text("utf-8"))["carreras"]
POR_ID = {c["id"]: c for c in CATALOGO}


def hr(t: str) -> None:
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


def holland3(riasec: dict) -> str:
    return "".join(sorted(DIMENSIONES, key=lambda d: riasec[d], reverse=True)[:3])


# 1. JSON vs builder ---------------------------------------------------
hr("1. CONSISTENCIA carreras.json  vs  build_catalog.py")
divergencias = 0
for c in CARRERAS:
    esperado = vector_riasec(c["onet_soc"])
    real = POR_ID[c["id"]]["riasec"]
    if esperado != real:
        divergencias += 1
        print(f"  DIVERGE {c['id']}: json={real} builder={esperado}")
print(f"  -> {divergencias} divergencias (0 = el JSON está sincronizado con el builder).")

# 2. Bug de reescalado 0-7 vs 1-7 -------------------------------------
hr("2. REESCALADO  (fórmula actual asume 0-7; O*NET es 1-7)")
print("  valor_07 -> 1-5 con la fórmula ACTUAL  vs  fórmula 1-7 correcta")
print(f"  {'O*NET':>6} | {'actual (0-7)':>12} | {'correcta (1-7)':>14}")
for v in [1.0, 1.7, 2.3, 3.0, 3.7, 4.7, 5.7, 6.7, 7.0]:
    actual = reescalar_07_a_15(v)
    correcta = max(1, min(5, round(1 + (v - 1) / 6 * 4)))
    flag = "  <-- difiere" if actual != correcta else ""
    print(f"  {v:>6} | {actual:>12} | {correcta:>14}{flag}")
# ¿Cuántas carreras tienen algún 1.0 que se vuelve 2 en lugar de 1?
piso = 0
for c in CARRERAS:
    crudo = ONET_INTERESTS_07[c["onet_soc"]]
    if any(val <= 1.0 for val in crudo.values()):
        piso += 1
print(f"  -> {piso}/{len(CARRERAS)} carreras tienen una dimensión O*NET=1.0")
print("     que la fórmula actual eleva a 2 (debería ser 1). El piso de la")
print("     escala nunca se usa: la dimensión más débil jamás vale 1.")

# 3. High-point O*NET vs Holland del vector 1-5 -----------------------
hr("3. HIGH-POINT  (dominante O*NET 0-7  vs  dominante del vector 1-5)")
print("  Marca carreras donde el reescalado/redondeo cambió el dominante,")
print("  o donde el dominante O*NET es sorprendente para el área.")
familia_esperada = {
    "Ingeniería y Tecnología": set("RIC"),
    "Ciencias Naturales y Exactas": set("RI"),
    "Ciencias de la Salud": set("ISR"),
    "Arte y Diseño": set("A"),
    "Ciencias Sociales y Humanidades": set("SAIE"),
    "Educación": set("S"),
    "Economía y Negocios": set("ECS"),
}
for c in CARRERAS:
    crudo = ONET_INTERESTS_07[c["onet_soc"]]
    dom_onet = max(DIMENSIONES, key=lambda d: crudo[d])
    vec = POR_ID[c["id"]]["riasec"]
    dom_vec = max(DIMENSIONES, key=lambda d: vec[d])
    area = POR_ID[c["id"]]["area"]
    flags = []
    if dom_onet != dom_vec:
        flags.append(f"dominante cambió por redondeo: O*NET={dom_onet} vec={dom_vec}")
    if dom_onet not in familia_esperada.get(area, set(DIMENSIONES)):
        flags.append(f"dominante O*NET={dom_onet} atípico para área '{area}'")
    if flags:
        print(f"  {c['id']:34s} {holland3(vec)}  | " + " ; ".join(flags))

# 4. Colisiones de vectores -------------------------------------------
hr("4. COLISIONES  (carreras con vector RIASEC 1-5 idéntico = empate puro)")
grupos: dict[tuple, list[str]] = defaultdict(list)
for c in CATALOGO:
    clave = tuple(c["riasec"][d] for d in DIMENSIONES)
    grupos[clave].append(c["id"])
n_colision = 0
for clave, ids in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
    if len(ids) > 1:
        n_colision += len(ids)
        print(f"  {dict(zip(DIMENSIONES, clave))}  -> {ids}")
print(f"  -> {n_colision} carreras involucradas en empates exactos.")
print(f"  -> {len(grupos)} vectores únicos para {len(CATALOGO)} carreras.")

# 5. Resolución por dimensión -----------------------------------------
hr("5. RESOLUCIÓN  (valores distintos que toma cada dimensión en el catálogo)")
for d in DIMENSIONES:
    vals = Counter(c["riasec"][d] for c in CATALOGO)
    print(f"  {d}: {dict(sorted(vals.items()))}")
