"""
=================================================================
FASE 2 - MOTOR DE INFERENCIA  (scoring híbrido Coseno + Pearson)
=================================================================
Empareja el vector RIASEC del usuario con cada carrera del catálogo.

  - calcular_vector_usuario(): promedio ponderado por dimensión RIASEC
    -> vector de 6 dimensiones del usuario (escala 1-5, float).

  - similitud_coseno():   alineación DIRECCIONAL (magnitud + dirección).
  - correlacion_pearson(): similitud de FORMA del perfil (picos/valles),
    invariante al sesgo de indulgencia/severidad del usuario.
  - score_hibrido():       combinación ponderada de ambas.
  - ranking_carreras():    aplica el score sobre el catálogo y ordena.

¿POR QUÉ DOS MÉTRICAS Y NO UNA?  (resultado de la auditoría)
  La versión previa decía "coseno" pero, al centrar la media de AMBOS
  vectores, calculaba en realidad SOLO la correlación de Pearson (coseno
  centrado == Pearson). Es decir, no había hibridación: una métrica
  disfrazada de otra. Además:
    * ordenaba por la correlación cruda pero MOSTRABA (correlación)^3,
      un "castigo al cubo" arbitrario que hundía los porcentajes y
      desalineaba el orden mostrado del % mostrado;
    * los empates se resolvían por el ORDEN del catálogo -> sesgo
      sistemático hacia la primera carrera listada ("carrera imán").

  Aquí se separan las dos señales (son complementarias):
    - Coseno mide si usuario y carrera "apuntan" al mismo lado en el
      espacio 1-5 (intensidad y dirección del interés).
    - Pearson mide si el PERFIL tiene la misma forma relativa, sin
      importar cuán alto/bajo responde la persona (calibra el sesgo
      de escala personal).
  El híbrido (w·coseno + (1-w)·pearson) combina "dirección" y "forma".
=================================================================
"""

from __future__ import annotations

import numpy as np

# Orden CANÓNICO de las dimensiones. Es CRÍTICO mantenerlo igual en
# todo el proyecto (vectores, gráficos, JSON) para evitar bugs
# silenciosos en el emparejamiento.
DIMENSIONES_RIASEC: tuple[str, ...] = ("R", "I", "A", "S", "E", "C")

# Peso del coseno en el score híbrido (Pearson lleva el complemento).
#
# AUDITORÍA (caso "Instrumentadora", ver tests/test_perfiles.py):
#   El coseno sobre vectores 1-5 vive SIEMPRE en el ortante positivo, así
#   que para casi cualquier par usuario/carrera vale ~0.7-1.0. Es decir,
#   INFLA la afinidad y es justamente la fuente de los falsos positivos por
#   "coincidencia en una dimensión secundaria": un usuario alto en C
#   (Convencional) saca un coseno espuriamente alto con carreras
#   comerciales E/C (Martillero/bienes raíces) aunque NO compartan su R.
#   Pearson, al centrar por la media, compara la FORMA del perfil y por
#   ende la prominencia relativa de las letras dominantes del código
#   Holland: discrimina el patrón dominante de la coincidencia aislada.
#
#   Por eso se rebalanceó hacia Pearson: 0.4 -> 0.3. La simulación Monte
#   Carlo (scripts/montecarlo.py) confirma que mejora la dispersión
#   (cobertura 67->69, entropía 0.894->0.899) y suprime ~3x los falsos
#   positivos comerciales (Martillero, perfil Instrumentadora: 16%->6%)
#   sin hundir las carreras legítimamente afines.
#
#   Nota: también se probó PONDERAR las dimensiones dominantes del usuario
#   (boost a sus 2-3 letras Holland). La simulación lo DESCARTÓ: promueve
#   los "confounds" que comparten las letras fuertes del usuario (p. ej. un
#   técnico industrial comparte R+C con la instrumentadora) y hunde afines
#   legítimas (Medicina). La forma (Pearson) ya prioriza el código Holland
#   de manera robusta, sin ese efecto colateral.
PESO_COSENO: float = 0.3

# Umbral de varianza por debajo del cual consideramos que el usuario
# "respondió todo igual": un perfil plano no contiene preferencia y no
# es emparejable. Vale tanto para todo-3, todo-5 o todo-1.
_EPS_VARIANZA = 1e-9


# -----------------------------------------------------------------
# Paso 2.1 - Construcción del vector de usuario
# -----------------------------------------------------------------
def calcular_vector_usuario(
    respuestas: dict[str, int],
    preguntas: list[dict],
) -> dict[str, float]:
    """Calcula el promedio ponderado por dimensión RIASEC.

    Args:
        respuestas: dict {id_pregunta: puntaje_likert_1_a_5}.
        preguntas: lista de items del banco (con su dimensión y peso).

    Returns:
        Vector {R: x, I: x, A: x, S: x, E: x, C: x} con cada x en
        [1.0, 5.0]. Si una dimensión no fue contestada (caso borde),
        devuelve 3.0 (neutro) en lugar de NaN para no romper el score.

    Ejemplo de salida:
        {'R': 4.2, 'I': 2.1, 'A': 1.5, 'S': 4.8, 'E': 3.0, 'C': 2.5}
    """
    # Acumuladores por dimensión: (suma_ponderada, suma_pesos).
    acumuladores: dict[str, list[float]] = {
        dim: [0.0, 0.0] for dim in DIMENSIONES_RIASEC
    }

    for q in preguntas:
        qid = q["id"]
        if qid not in respuestas:
            # El usuario no contestó esta pregunta -> la salteamos.
            continue
        valor = float(respuestas[qid])
        peso = float(q.get("ponderacion", 1.0))
        dim = q["dimension"]
        acumuladores[dim][0] += valor * peso
        acumuladores[dim][1] += peso

    vector: dict[str, float] = {}
    for dim, (suma, total_pesos) in acumuladores.items():
        if total_pesos == 0:
            vector[dim] = 3.0   # neutro -> no inclina la similitud
        else:
            vector[dim] = round(suma / total_pesos, 2)

    return vector


# -----------------------------------------------------------------
# Paso 2.2 - Métricas de similitud
# -----------------------------------------------------------------
def _a_array(vec: dict[str, float] | dict[str, int]) -> np.ndarray:
    """Convierte un dict RIASEC al ndarray ordenado canónicamente (sin centrar)."""
    return np.array([float(vec[d]) for d in DIMENSIONES_RIASEC], dtype=np.float64)


def _coseno(a: np.ndarray, b: np.ndarray) -> float:
    """Coseno entre dos arrays. 0.0 si alguna norma es 0 (evita NaN)."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def similitud_coseno(
    vector_usuario: dict[str, float],
    vector_carrera: dict[str, float],
) -> float:
    """Similitud de coseno (alineación DIRECCIONAL) en el espacio 1-5.

                       A · B
        cos(θ) = ─────────────
                  ‖A‖ · ‖B‖

    Mide si el usuario y la carrera "apuntan" hacia el mismo lado, con
    sensibilidad a la magnitud del interés. Rango [-1, 1] (en la práctica
    >0 porque ambos vectores viven en el ortante positivo 1-5).
    """
    return _coseno(_a_array(vector_usuario), _a_array(vector_carrera))


def correlacion_pearson(
    vector_usuario: dict[str, float],
    vector_carrera: dict[str, float],
) -> float:
    """Correlación de Pearson (similitud de FORMA del perfil).

    Equivale al coseno sobre los vectores centrados en su propia media:
    elimina el nivel general de respuesta (sesgo de indulgencia/severidad)
    y compara sólo la distribución relativa de picos y valles RIASEC.
    Rango [-1, 1]: 1 = misma forma, 0 = sin relación, -1 = forma opuesta.
    """
    a = _a_array(vector_usuario)
    b = _a_array(vector_carrera)
    return _coseno(a - a.mean(), b - b.mean())


def score_hibrido(
    vector_usuario: dict[str, float],
    vector_carrera: dict[str, float],
    w_coseno: float = PESO_COSENO,
) -> tuple[float, float, float]:
    """Score híbrido = w·coseno + (1-w)·pearson.

    Devuelve la terna (score, coseno, pearson) para trazabilidad. El
    score vive en [-1, 1]; >0 indica afinidad, <=0 indica perfiles
    no relacionados u opuestos.
    """
    cos = similitud_coseno(vector_usuario, vector_carrera)
    pear = correlacion_pearson(vector_usuario, vector_carrera)
    score = w_coseno * cos + (1.0 - w_coseno) * pear
    return score, cos, pear


# -----------------------------------------------------------------
# Ranking final de carreras
# -----------------------------------------------------------------
def ranking_carreras(
    vector_usuario: dict[str, float],
    carreras: list[dict],
    w_coseno: float = PESO_COSENO,
) -> list[dict]:
    """Devuelve las carreras ordenadas por afinidad (score híbrido) DESC.

    - Convierte el score [-1,1] a un porcentaje honesto de afinidad:
      `afinidad_pct = round(100 * max(0, score))`. Se eliminó el "castigo
      al cubo" de la versión previa (distorsionaba el % y desalineaba el
      orden mostrado).
    - Desempata de forma determinista y NEUTRAL: a igual score, primero
      mayor Pearson (forma), luego id alfabético. Ya NO gana "la primera
      del catálogo", lo que eliminaba la causa de carreras imán/huérfanas
      por orden de lista.
    - Usuario con varianza ~0 (responde todo igual): perfil no informativo
      -> afinidad 0 para todas (la app lo detecta y avisa).
    """
    u = _a_array(vector_usuario)
    usuario_plano = float(np.std(u)) < _EPS_VARIANZA

    ranking = []
    for c in carreras:
        if usuario_plano:
            score = cos = pear = 0.0
        else:
            score, cos, pear = score_hibrido(vector_usuario, c["riasec"], w_coseno)
        afinidad_pct = int(round(max(0.0, score) * 100))
        ranking.append({
            **c,
            "score": score,
            "similitud": cos,        # coseno (compatibilidad de nombre)
            "coseno": cos,
            "pearson": pear,
            "afinidad_pct": afinidad_pct,
        })

    # Orden: score DESC; desempate por pearson DESC y luego id (neutral).
    ranking.sort(key=lambda x: (-x["score"], -x["pearson"], x["id"]))
    return ranking
