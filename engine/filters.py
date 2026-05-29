"""
=================================================================
SEGUNDA CAPA - FILTROS DE AVERSIÓN (KNOCKOUT)
=================================================================
El motor de coseno (inference.py) ordena las carreras por afinidad de
INTERESES. Pero la afinidad de intereses no captura los "deal-breakers":
una persona puede tener un perfil que matchea con Medicina y aun así
NO querer jamás tocar un paciente.

Esta segunda capa resuelve exactamente eso. Funciona como un sistema
de reglas de exclusión (knockout):

  1. El usuario responde 6 preguntas filtro (data/preguntas.json -> "filtros").
     Cada filtro tiene una `etiqueta` (ej. "contacto_pacientes").
  2. Si responde <= UMBRAL_VETO ("no me gustaría" / "lo detestaría"),
     esa etiqueta queda VETADA.
  3. Toda carrera que lleve una etiqueta vetada se elimina del catálogo
     ANTES de calcular el ranking.

Ejemplo del enunciado: alguien a quien "le encantan los datos" (perfil
I/C alto) pero que veta `contacto_pacientes` no recibirá Medicina ni
Odontología, aunque su perfil de intereses se les parezca.

Esta capa NO modifica el vector RIASEC del usuario: solo recorta el
universo de carreras candidatas.
=================================================================
"""

from __future__ import annotations

from typing import Iterable

# Umbral de veto. Una respuesta filtro <= a este valor descarta las
# carreras con la etiqueta correspondiente.
#   1 = "Lo detestaría", 2 = "No me gustaría"  -> vetan
#   3 = "Me da igual", 4, 5                     -> no vetan
UMBRAL_VETO = 2


def etiquetas_vetadas(
    respuestas_filtro: dict[str, int],
    filtros: list[dict],
) -> set[str]:
    """Devuelve el conjunto de etiquetas que el usuario quiere evitar.

    Args:
        respuestas_filtro: dict {id_filtro: puntaje_1_a_5}.
        filtros: lista de filtros (cada uno con 'id' y 'etiqueta').

    Returns:
        Set de etiquetas con respuesta <= UMBRAL_VETO. Vacío si el
        usuario no vetó nada (todas las carreras siguen en juego).
    """
    vetadas: set[str] = set()
    for f in filtros:
        respuesta = respuestas_filtro.get(f["id"])
        if respuesta is not None and respuesta <= UMBRAL_VETO:
            vetadas.add(f["etiqueta"])
    return vetadas


def aplicar_filtros(
    carreras: Iterable[dict],
    etiquetas_a_vetar: set[str],
) -> list[dict]:
    """Elimina del catálogo las carreras con alguna etiqueta vetada.

    Una carrera se descarta si AL MENOS UNA de sus etiquetas figura en
    `etiquetas_a_vetar` (intersección no vacía). Si no hay etiquetas
    vetadas, devuelve el catálogo completo intacto.
    """
    carreras = list(carreras)
    if not etiquetas_a_vetar:
        return carreras

    return [
        c for c in carreras
        if etiquetas_a_vetar.isdisjoint(c.get("etiquetas", []))
    ]
