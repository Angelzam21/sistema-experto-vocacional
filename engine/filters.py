"""
=================================================================
FASE 3.2 - FILTROS DUROS
=================================================================
Implementa los "Filtros Duros" del flujo de evaluación: restricciones
binarias (sí/no) que excluyen carreras del cálculo de coseno *antes*
de ejecutarlo, ahorrando cómputo y evitando recomendaciones
inviables (ej.: ofrecer una carrera presencial en CABA a alguien que
solo puede estudiar a distancia en Tucumán).

Estos filtros NO modifican el vector RIASEC del usuario: simplemente
recortan el universo de carreras candidatas.
=================================================================
"""

from __future__ import annotations

from typing import Iterable


def aplicar_filtros_duros(
    carreras: Iterable[dict],
    zonas_permitidas: list[str] | None = None,
    modalidades_permitidas: list[str] | None = None,
) -> list[dict]:
    """Filtra la lista de carreras según restricciones del usuario.

    Args:
        carreras: catálogo completo (lista de dicts con keys
                  'zona_geografica' y 'modalidad', ambos listas).
        zonas_permitidas: zonas donde el usuario puede/quiere estudiar.
                          None o lista vacía = sin restricción.
        modalidades_permitidas: idem para 'Presencial' / 'Híbrida' /
                                'A Distancia'.

    Returns:
        Sub-lista de carreras que cumplen TODOS los filtros activos.

    Semántica:
      - Una carrera pasa el filtro de zona si AL MENOS UNA de sus
        zonas figura en `zonas_permitidas` (intersección no vacía).
      - Idem para modalidad.
      - Si un filtro está vacío/None, no se aplica (pasa todo).
    """
    zonas_set = set(zonas_permitidas) if zonas_permitidas else None
    moda_set = set(modalidades_permitidas) if modalidades_permitidas else None

    salida: list[dict] = []
    for c in carreras:
        # Filtro por zona geográfica (intersección de conjuntos).
        if zonas_set is not None:
            zonas_carrera = set(c.get("zona_geografica", []))
            if zonas_set.isdisjoint(zonas_carrera):
                continue

        # Filtro por modalidad.
        if moda_set is not None:
            modas_carrera = set(c.get("modalidad", []))
            if moda_set.isdisjoint(modas_carrera):
                continue

        salida.append(c)

    return salida


def todas_las_zonas(carreras: list[dict]) -> list[str]:
    """Helper para poblar el multiselect de zonas en la UI.

    Recorre el catálogo y devuelve la unión ordenada alfabéticamente
    de todas las zonas presentes. Evita hardcodear la lista en la UI:
    si mañana se suma "San Luis", aparece automáticamente.
    """
    zonas: set[str] = set()
    for c in carreras:
        zonas.update(c.get("zona_geografica", []))
    return sorted(zonas)


def todas_las_modalidades(carreras: list[dict]) -> list[str]:
    """Idem para modalidades. Misma lógica que todas_las_zonas."""
    modas: set[str] = set()
    for c in carreras:
        modas.update(c.get("modalidad", []))
    # Orden semántico, no alfabético: presencial primero.
    orden = {"Presencial": 0, "Híbrida": 1, "A Distancia": 2}
    return sorted(modas, key=lambda m: orden.get(m, 99))
