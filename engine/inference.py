"""
=================================================================
FASE 2 - MOTOR DE INFERENCIA
=================================================================
Implementa los pasos 2.1 y 2.2 del plan técnico:

  - calcular_vector_usuario(): a partir de las respuestas a las
    preguntas RIASEC, calcula el vector promedio normalizado del
    usuario en el espacio de 6 dimensiones.

  - similitud_coseno(): núcleo matemático del emparejamiento.

  - ranking_carreras(): aplica la similitud sobre el catálogo completo
    y devuelve las carreras ordenadas en forma descendente.

¿Por qué similitud de coseno y NO distancia euclidiana?
  El plan lo justifica: la distancia euclidiana penaliza diferencias
  de magnitud absoluta entre vectores, sesgando hacia usuarios que
  responden con valores más altos. El coseno mide la *orientación*
  (perfil de intereses) y es invariante a la escala, por lo que dos
  usuarios con la misma proporción RIASEC pero distinta intensidad
  reciben la misma recomendación. Esto es exactamente lo que pide
  el modelo de Holland.
=================================================================
"""

from __future__ import annotations

import numpy as np

# Orden CANÓNICO de las dimensiones. Es CRÍTICO mantenerlo igual en
# todo el proyecto (vectores, gráficos, JSON) para evitar bugs
# silenciosos en la similitud de coseno.
DIMENSIONES_RIASEC: tuple[str, ...] = ("R", "I", "A", "S", "E", "C")


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
        devuelve 3.0 (neutro) en lugar de NaN para no romper el coseno.

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
            # Se podría exigir respuesta obligatoria desde la UI.
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
# Paso 2.2 - Similitud de coseno
# -----------------------------------------------------------------

def _a_array(vec: dict[str, float] | dict[str, int]) -> np.ndarray:
    """Convierte un dict RIASEC al ndarray ordenado canónicamente y centra la media.

    Al restar la media del propio vector, transformamos la similitud
    de coseno en el Coeficiente de Correlación de Pearson, calibrando
    la escala personal del usuario (sesgo de indulgencia).
    """
    arr = np.array([float(vec[d]) for d in DIMENSIONES_RIASEC], dtype=np.float64)
    # Restamos la media exacta (con decimales) a todo el arreglo
    return arr - np.mean(arr)


def similitud_coseno(
    vector_usuario: dict[str, float],
    vector_carrera: dict[str, int],
) -> float:
    """Calcula cos(θ) entre el vector usuario y el de la carrera.

    Fórmula:                  A · B
                cos(θ) = ─────────────
                          ‖A‖ · ‖B‖

    Devuelve un valor en [-1.0, 1.0], donde 1.0 es una correlación perfecta (perfiles idénticos),
    0.0 es falta de correlación, 
    y -1.0 son perfiles completamente opuestos.
    """
    a = _a_array(vector_usuario)
    b = _a_array(vector_carrera)

    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)

    # Edge case: si alguna norma fuera 0 (no debería pasar pero por
    # robustez), devolvemos 0.0 en lugar de propagar NaN.
    if norma_a == 0.0 or norma_b == 0.0:
        return 0.0

    return float(np.dot(a, b) / (norma_a * norma_b))


# -----------------------------------------------------------------
# Ranking final de carreras
# -----------------------------------------------------------------
def ranking_carreras(
    vector_usuario: dict[str, float],
    carreras: list[dict],
) -> list[dict]:
    """Devuelve la lista de carreras ordenada por similitud DESC.

    Aplica un castigo exponencial (al cubo) sobre la correlación
    positiva para aumentar la varianza y mejorar la experiencia de
    usuario, hundiendo los porcentajes de carreras mediocres.
    """
    ranking = []
    for c in carreras:
        sim = similitud_coseno(vector_usuario, c["riasec"])
        
        # 1. Ignoramos correlaciones negativas (intereses opuestos = 0%)
        sim_positiva = max(0.0, sim)
        
        # 2. Elevamos al CUBO para castigar perfiles que no encajan 
        # perfectamente y pasamos a porcentaje.
        afinidad_pct = int(round((sim_positiva ** 3) * 100))
        
        ranking.append({
            **c,
            "similitud": sim,
            "afinidad_pct": afinidad_pct,
        })

    # Orden descendente: del más afín al menos afín, usando el valor crudo
    ranking.sort(key=lambda x: x["similitud"], reverse=True)
    return ranking
