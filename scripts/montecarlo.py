"""
=================================================================
SIMULACIÓN MONTE CARLO DEL MOTOR DE EMPAREJAMIENTO
=================================================================
Compara el motor PREVIO (vectores enteros + "Pearson disfrazado de
coseno" + castigo al cubo + desempate por orden de catálogo) contra el
motor NUEVO (vectores float de alta resolución + híbrido Coseno/Pearson
+ desempate neutral) sobre 500 usuarios sintéticos en 3 escenarios:

  A) Aleatorio:     36 respuestas uniformes en {1..5}.
  B) Arquetípico:   se fuerza cada dimensión R/I/A/S/E/C al máximo
                    (con ruido leve); 500 usuarios repartidos en los 6.
  C) Ruido/indeciso: respuestas en torno a 3 (neutro), baja varianza.

Mide, por (motor × escenario), la distribución del Top-1 sobre TODAS las
carreras del catálogo actual (su número se toma dinámicamente de
`data/carreras.json` vía TOTAL = len(...), no se hardcodea): cobertura,
carreras huérfanas (nunca #1), carrera imán (top-1 desproporcionado),
entropía normalizada y Gini.

También: (1) barrido del peso del coseno para calibrar PESO_COSENO y
(2) prueba de sensibilidad intra-familia (pares casi idénticos).

Uso:  python scripts/montecarlo.py
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from build_catalog import CARRERAS, ONET_INTERESTS_07  # noqa: E402
from engine.inference import (  # noqa: E402
    DIMENSIONES_RIASEC as DIMS,
    calcular_vector_usuario,
    ranking_carreras,
)

N = 500
SEED = 20260529
DATA = RAIZ / "data"
PREG = json.loads((DATA / "preguntas.json").read_text("utf-8"))["preguntas"]
CAT_NEW = json.loads((DATA / "carreras.json").read_text("utf-8"))["carreras"]


def _resc_old(v: float) -> int:
    """Reescala PREVIA (asumía 0-7 y redondeaba a entero) -> reproduce el
    catálogo que se enviaba antes de la corrección, para el antes/después."""
    if v <= 0:
        return 1
    if v >= 7:
        return 5
    return int(round(1 + (v / 7) * 4))


# Catálogo PREVIO reconstruido (vectores enteros) a partir del mismo SOC.
CAT_OLD = [
    {**c, "riasec": {d: _resc_old(ONET_INTERESTS_07[c["onet_soc"]][d]) for d in DIMS}}
    for c in CARRERAS
]
TOTAL = len(CAT_NEW)
PREG_POR_DIM: dict[str, list[str]] = {d: [q["id"] for q in PREG if q["dimension"] == d] for d in DIMS}


# -----------------------------------------------------------------
# Reproducción del motor PREVIO (para el antes/después)
# -----------------------------------------------------------------
def _arr_centrado(vec) -> np.ndarray:
    a = np.array([float(vec[d]) for d in DIMS], dtype=np.float64)
    return a - a.mean()


def ranking_old(vector_usuario, carreras):
    """Motor previo: coseno centrado (==Pearson), castigo al cubo,
    orden por similitud cruda con desempate por ORDEN de catálogo
    (sort estable de Python => gana la primera listada)."""
    out = []
    a = _arr_centrado(vector_usuario)
    na = np.linalg.norm(a)
    for c in carreras:
        b = _arr_centrado(c["riasec"])
        nb = np.linalg.norm(b)
        sim = 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))
        pct = int(round((max(0.0, sim) ** 3) * 100))
        out.append({**c, "similitud": sim, "afinidad_pct": pct})
    out.sort(key=lambda x: x["similitud"], reverse=True)  # estable: empata por orden
    return out


# -----------------------------------------------------------------
# Generadores de usuarios sintéticos
# -----------------------------------------------------------------
def u_aleatorio(rng: random.Random) -> dict[str, int]:
    return {q["id"]: rng.randint(1, 5) for q in PREG}


def u_arquetipo(rng: random.Random, dim: str) -> dict[str, int]:
    """Fuerza `dim` al máximo (4-5) y deja el resto bajo (1-2), con ruido."""
    r = {}
    for q in PREG:
        if q["dimension"] == dim:
            r[q["id"]] = rng.choice([4, 5, 5, 5])
        else:
            r[q["id"]] = rng.choice([1, 1, 2, 3])
    return r


def u_ruido(rng: random.Random) -> dict[str, int]:
    """Indeciso: respuestas en torno al neutro 3, baja varianza."""
    return {q["id"]: rng.choice([2, 3, 3, 3, 4]) for q in PREG}


# -----------------------------------------------------------------
# Métricas de distribución
# -----------------------------------------------------------------
def entropia_norm(conteos: Counter) -> float:
    total = sum(conteos.values())
    if total == 0:
        return 0.0
    h = -sum((n / total) * math.log2(n / total) for n in conteos.values() if n)
    return h / math.log2(TOTAL)  # 1.0 = reparto uniforme sobre las TOTAL carreras


def gini(conteos: Counter) -> float:
    xs = sorted([conteos.get(c["id"], 0) for c in CAT_NEW])
    n = len(xs)
    s = sum(xs)
    if s == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * s) - (n + 1) / n


def reporte_dist(nombre: str, top1: Counter) -> None:
    cobertura = len(top1)
    huerfanas = TOTAL - cobertura
    magnet_id, magnet_n = top1.most_common(1)[0]
    print(f"\n  [{nombre}]")
    print(f"    cobertura Top-1 : {cobertura}/{TOTAL} carreras   (huérfanas: {huerfanas})")
    print(f"    carrera imán    : {magnet_id}  ({magnet_n}/{N} = {100*magnet_n/N:.1f}% de los usuarios)")
    print(f"    entropía norm.  : {entropia_norm(top1):.3f}   (1.0 = reparto uniforme)")
    print(f"    Gini            : {gini(top1):.3f}   (0 = equitativo, 1 = concentrado)")
    top5 = top1.most_common(5)
    print(f"    top-5 imanes    : " + ", ".join(f"{i}:{n}" for i, n in top5))


# -----------------------------------------------------------------
# 1) Barrido de peso del coseno (calibración de PESO_COSENO)
# -----------------------------------------------------------------
def barrido_peso():
    print("=" * 70)
    print("1. CALIBRACIÓN DEL PESO DEL COSENO  (escenario aleatorio, motor nuevo)")
    print("=" * 70)
    print("  Buscamos el peso que MAXIMIZA la dispersión del Top-1 (más")
    print("  carreras alcanzables, menos imán). Métrica: entropía y cobertura.")
    rng = random.Random(SEED)
    usuarios = [u_aleatorio(rng) for _ in range(N)]
    vecs = [calcular_vector_usuario(u, PREG) for u in usuarios]
    print(f"\n  {'w_coseno':>8} | {'cobertura':>9} | {'entropía':>8} | {'Gini':>6} | imán %")
    for w in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        top1 = Counter(ranking_carreras(v, CAT_NEW, w_coseno=w)[0]["id"] for v in vecs)
        _, mn = top1.most_common(1)[0]
        print(f"  {w:>8.1f} | {len(top1):>9} | {entropia_norm(top1):>8.3f} | "
              f"{gini(top1):>6.3f} | {100*mn/N:>5.1f}")


# -----------------------------------------------------------------
# 2) Antes/Después por escenario
# -----------------------------------------------------------------
def comparar_escenarios():
    for nombre, gen in [
        ("A · ALEATORIO", lambda rng, i: u_aleatorio(rng)),
        ("B · ARQUETÍPICO PURO", lambda rng, i: u_arquetipo(rng, DIMS[i % 6])),
        ("C · RUIDO / INDECISO", lambda rng, i: u_ruido(rng)),
    ]:
        print("\n" + "=" * 70)
        print(f"2. ESCENARIO {nombre}  (N={N})")
        print("=" * 70)
        rng = random.Random(SEED)
        vecs = [calcular_vector_usuario(gen(rng, i), PREG) for i in range(N)]
        top1_old = Counter(ranking_old(v, CAT_OLD)[0]["id"] for v in vecs)
        top1_new = Counter(ranking_carreras(v, CAT_NEW)[0]["id"] for v in vecs)
        reporte_dist("MOTOR PREVIO", top1_old)
        reporte_dist("MOTOR NUEVO", top1_new)


# -----------------------------------------------------------------
# 3) Sensibilidad intra-familia (pares antes idénticos)
# -----------------------------------------------------------------
def sensibilidad():
    print("\n" + "=" * 70)
    print("3. SENSIBILIDAD INTRA-FAMILIA  (pares que ANTES colisionaban)")
    print("=" * 70)
    pares = [
        ("ingenieria_mecanica", "ingenieria_mecatronica"),
        ("biologia", "fisica"),
        ("ciencia_datos", "economia"),
        ("ingenieria_civil", "ingenieria_electrica"),
    ]
    new_by = {c["id"]: c for c in CAT_NEW}
    old_by = {c["id"]: c for c in CAT_OLD}
    # usuario "ingenieril realista-investigador" para tensionar los pares
    u = {"R": 4.0, "I": 5.0, "A": 2.0, "S": 2.0, "E": 3.0, "C": 3.0}
    from engine.inference import score_hibrido
    print("  Score híbrido del MISMO usuario {R4,I5,A2,S2,E3,C3} a cada par:")
    for a, b in pares:
        sa = score_hibrido(u, new_by[a]["riasec"])[0]
        sb = score_hibrido(u, new_by[b]["riasec"])[0]
        # ¿colisionaban antes? (vectores int idénticos)
        col = old_by[a]["riasec"] == old_by[b]["riasec"]
        print(f"    {a:24s} {sa:+.4f}   vs   {b:24s} {sb:+.4f}   "
              f"| Δ={abs(sa-sb):.4f} {'(antes EMPATE)' if col else ''}")


if __name__ == "__main__":
    np.random.seed(SEED)
    barrido_peso()
    comparar_escenarios()
    sensibilidad()
    print()
