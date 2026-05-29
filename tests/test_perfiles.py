"""
=================================================================
TESTS POR PERFIL DEL SISTEMA EXPERTO
=================================================================
Valida el pipeline completo (vector RIASEC -> 2da capa de filtros ->
ranking de coseno) con perfiles de usuario sintéticos, comprobando
que las recomendaciones tengan sentido vocacional.

Se ejecuta de dos formas:
    python tests/test_perfiles.py     # imprime un reporte legible
    pytest tests/test_perfiles.py     # como suite de pytest

No requiere dependencias extra más allá de las del proyecto.
=================================================================
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite ejecutar el archivo directamente (python tests/test_perfiles.py)
# agregando la raíz del repo al path de import.
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from engine.filters import aplicar_filtros, etiquetas_vetadas  # noqa: E402
from engine.inference import calcular_vector_usuario, ranking_carreras  # noqa: E402

# ---- Carga de datos (una vez) ----
_DATA = RAIZ / "data"
CATALOGO = json.loads((_DATA / "carreras.json").read_text(encoding="utf-8"))["carreras"]
_PREG_RAW = json.loads((_DATA / "preguntas.json").read_text(encoding="utf-8"))
PREGUNTAS = _PREG_RAW["preguntas"]
FILTROS = _PREG_RAW["filtros"]


# -----------------------------------------------------------------
# Helpers para construir respuestas sintéticas
# -----------------------------------------------------------------
def _respuestas(niveles: dict[str, int]) -> dict[str, int]:
    """Todas las preguntas de una dimensión responden el mismo nivel.

    `niveles` mapea cada dimensión RIASEC a un puntaje 1-5.
    """
    return {q["id"]: niveles[q["dimension"]] for q in PREGUNTAS}


def _respuestas_filtro(vetos: dict[str, int]) -> dict[str, int]:
    """Construye respuestas a los filtros. `vetos` mapea etiqueta->puntaje;
    lo no especificado responde 3 (neutro, no veta)."""
    return {f["id"]: vetos.get(f["etiqueta"], 3) for f in FILTROS}


def _evaluar(niveles: dict[str, int], vetos: dict[str, int] | None = None) -> list[dict]:
    """Corre el pipeline completo y devuelve el ranking de carreras."""
    vector = calcular_vector_usuario(_respuestas(niveles), PREGUNTAS)
    vetadas = etiquetas_vetadas(_respuestas_filtro(vetos or {}), FILTROS)
    elegibles = aplicar_filtros(CATALOGO, vetadas)
    return ranking_carreras(vector, elegibles)


def _ids(ranking: list[dict], n: int | None = None) -> list[str]:
    return [c["id"] for c in (ranking[:n] if n else ranking)]


# -----------------------------------------------------------------
# Tests
# -----------------------------------------------------------------
def test_datos_veta_pacientes() -> None:
    """Perfil 'ama los datos' (I+C alto) que veta atender pacientes:
    NO debe recibir Medicina/Odontología ni ninguna carrera clínica."""
    rk = _evaluar({"R": 2, "I": 5, "A": 1, "S": 1, "E": 2, "C": 5},
                  {"contacto_pacientes": 1})
    ids = _ids(rk)
    # Ninguna carrera de atención a pacientes sobrevive al veto.
    assert all("contacto_pacientes" not in c["etiquetas"] for c in rk)
    assert "medicina" not in ids and "odontologia" not in ids
    # El #1 es una carrera cuantitativa/de datos.
    assert rk[0]["id"] in {"actuario", "ciencia_datos", "economia", "finanzas",
                           "contador_publico", "tecnologias_digitales"}


def test_perfil_social() -> None:
    """Perfil Social alto -> recomendaciones de ayuda/educación/salud."""
    rk = _evaluar({"R": 2, "I": 2, "A": 2, "S": 5, "E": 2, "C": 2})
    assert rk[0]["area"] in {"Ciencias de la Salud", "Ciencias Sociales y Humanidades", "Educación"}
    assert "trabajo_social" in _ids(rk, 6)


def test_perfil_artistico() -> None:
    """Perfil Artístico alto -> el #1 es del área Arte y Diseño."""
    rk = _evaluar({"R": 2, "I": 2, "A": 5, "S": 2, "E": 2, "C": 2})
    assert rk[0]["area"] == "Arte y Diseño"


def test_perfil_realista() -> None:
    """Perfil Realista+Investigador -> ingenierías arriba."""
    rk = _evaluar({"R": 5, "I": 4, "A": 2, "S": 2, "E": 2, "C": 2})
    assert rk[0]["area"] == "Ingeniería y Tecnología"
    assert "ingenieria_mecanica" in _ids(rk, 3)


def test_vector_nulo() -> None:
    """Responder todo igual -> afinidad 0 (lo detecta la app)."""
    rk = _evaluar({"R": 3, "I": 3, "A": 3, "S": 3, "E": 3, "C": 3})
    assert rk[0]["afinidad_pct"] == 0


def test_filtro_cambia_resultado() -> None:
    """Mismo perfil (I+S, compatible con Medicina), con y sin veto:
    el filtro de aversión saca a Medicina del ranking."""
    perfil = {"R": 2, "I": 5, "A": 2, "S": 5, "E": 2, "C": 2}

    sin_veto = _ids(_evaluar(perfil))
    con_veto = _ids(_evaluar(perfil, {"contacto_pacientes": 1}))

    assert "medicina" in sin_veto          # sin veto, Medicina es candidata
    assert "medicina" not in con_veto      # con veto, desaparece
    assert "psicologia" in con_veto[:3]    # queda una alternativa social sin contacto clínico


# -----------------------------------------------------------------
# Runner standalone (sin pytest)
# -----------------------------------------------------------------
def _main() -> int:
    tests = [
        ("Datos + veta pacientes", test_datos_veta_pacientes),
        ("Perfil social", test_perfil_social),
        ("Perfil artístico", test_perfil_artistico),
        ("Perfil realista", test_perfil_realista),
        ("Vector nulo", test_vector_nulo),
        ("Filtro cambia resultado (Medicina)", test_filtro_cambia_resultado),
    ]
    fallidos = 0
    for nombre, fn in tests:
        try:
            fn()
            print(f"  PASS  {nombre}")
        except AssertionError as e:
            fallidos += 1
            print(f"  FAIL  {nombre}  -> {e}")

    print(f"\n{len(tests) - fallidos}/{len(tests)} tests OK.")
    return 1 if fallidos else 0


if __name__ == "__main__":
    sys.exit(_main())
