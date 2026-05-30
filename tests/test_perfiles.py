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
from engine.inference import (  # noqa: E402
    DIMENSIONES_RIASEC,
    calcular_vector_usuario,
    correlacion_pearson,
    ranking_carreras,
    similitud_coseno,
)

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
    # El #1 es una carrera cuantitativa/de datos: alto Investigador Y
    # Convencional (perfil I+C), que es exactamente lo que pidió el usuario.
    top = rk[0]
    assert top["riasec"]["I"] >= 4 and top["riasec"]["C"] >= 4, top["id"]


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
    """Perfil Realista+Investigador -> el #1 es fuertemente Realista y las
    ingenierías aparecen arriba.

    Nota: con los vectores fieles a O*NET, Odontología (Dentists: R/I muy
    altos en O*NET) compite con las ingenierías por el #1 para un perfil
    R puro sin vetos; es psicométricamente correcto. Por eso la aserción
    valida 'el #1 es Realista' + 'ingenierías presentes', no un id fijo."""
    rk = _evaluar({"R": 5, "I": 4, "A": 2, "S": 2, "E": 2, "C": 2})
    # El #1 tiene a Realista entre sus intereses dominantes.
    assert rk[0]["riasec"]["R"] >= 4, rk[0]["id"]
    # Ingeniería Mecánica entra al podio y la familia de Ingeniería domina el top-5.
    assert "ingenieria_mecanica" in _ids(rk, 3)
    assert sum(c["area"] == "Ingeniería y Tecnología" for c in rk[:5]) >= 2


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


def test_veta_politica() -> None:
    """Perfil fuertemente Social+Investigador+Emprendedor (S/I/E alto): el
    motor RIASEC lo empareja con Ciencia Política (#1 sin veto). Con el filtro
    de aversión 'dominio_politico' la carrera debe DESAPARECER del ranking.

    Nota: el id real en el catálogo es 'ciencia_politica' (singular)."""
    perfil = {"R": 2, "I": 5, "A": 2, "S": 5, "E": 5, "C": 2}

    sin_veto = _ids(_evaluar(perfil))
    con_veto = _ids(_evaluar(perfil, {"dominio_politico": 1}))

    # Premisa del test: sin veto, Ciencia Política es candidata fuerte (Top 3).
    assert "ciencia_politica" in sin_veto[:3]
    # Con el veto político, desaparece por completo del ranking.
    assert "ciencia_politica" not in con_veto


# -----------------------------------------------------------------
# Tests del motor refactorizado (Coseno + Pearson híbrido)
# -----------------------------------------------------------------
def test_coseno_y_pearson_son_distintos() -> None:
    """El híbrido combina DOS señales reales: coseno (dirección) y Pearson
    (forma). Deben diferir (la versión previa calculaba Pearson dos veces)."""
    u = {"R": 5, "I": 4, "A": 2, "S": 2, "E": 3, "C": 3}
    c = {"R": 4.5, "I": 4.1, "A": 1.5, "S": 1.0, "E": 2.1, "C": 3.0}
    cos = similitud_coseno(u, c)
    pear = correlacion_pearson(u, c)
    assert abs(cos - pear) > 1e-3            # son métricas distintas
    assert -1.0 <= cos <= 1.0 and -1.0 <= pear <= 1.0


def test_sin_colisiones_de_vectores() -> None:
    """El catálogo NO debe tener vectores RIASEC duplicados.

    El único par que colisionaba (los dos profesorados que compartían el
    SOC O*NET 25-2031.00) se resolvió eliminando 'profesorado_educacion_fisica'
    del catálogo. Con eso, cada una de las carreras restantes tiene un
    vector único (ver analisis_catalogo.md)."""
    grupos: dict[tuple, list[str]] = {}
    for c in CATALOGO:
        clave = tuple(c["riasec"][d] for d in DIMENSIONES_RIASEC)
        grupos.setdefault(clave, []).append(c["id"])
    colisiones = [ids for ids in grupos.values() if len(ids) > 1]
    assert colisiones == [], colisiones
    # Sanity: tantos vectores únicos como carreras (length dinámico, no fijo).
    assert len(grupos) == len(CATALOGO)


def test_desempate_no_depende_del_orden_del_catalogo() -> None:
    """El ranking debe ser estable ante una permutación del catálogo
    (el desempate es por score/pearson/id, NO por posición en la lista)."""
    import random as _r
    vector = calcular_vector_usuario(_respuestas({"R": 4, "I": 5, "A": 2, "S": 2, "E": 3, "C": 3}), PREGUNTAS)
    base = _ids(ranking_carreras(vector, CATALOGO))
    barajado = list(CATALOGO)
    _r.Random(0).shuffle(barajado)
    assert _ids(ranking_carreras(vector, barajado)) == base


def test_afinidad_sin_castigo_al_cubo() -> None:
    """Una afinidad muy alta debe reflejarse como un % alto (la versión
    previa, con score^3, hundía 0.8 -> 51%). Un match casi perfecto > 85%."""
    rk = _evaluar({"R": 5, "I": 4, "A": 2, "S": 2, "E": 3, "C": 3})
    assert rk[0]["afinidad_pct"] >= 85
    # Y el % está alineado con el orden (monótono no creciente).
    pcts = [c["afinidad_pct"] for c in rk]
    assert pcts == sorted(pcts, reverse=True)


# -----------------------------------------------------------------
# Edge cases de la auditoría del motor (casos límite que históricamente
# producían falsos positivos o hacían colapsar el ranking)
# -----------------------------------------------------------------
def test_perfil_instrumentadora() -> None:
    """Caso real que motivó la auditoría: una Instrumentadora Quirúrgica
    (código Holland R+C alto, S medio) recibía resultados sin sentido con el
    motor PREVIO: 'Martillero Público' arriba, 'Medicina' al 0% y su propia
    carrera hundida por el castigo al cubo.

    Con el híbrido rebalanceado hacia Pearson (PESO_COSENO=0.3) el resultado
    es psicométricamente correcto:
      - Su propia carrera (Instrumentación) es el #1.
      - El área Ciencias de la Salud DOMINA el Top-5 (mayoría).
      - Las carreras comerciales (Martillero, Administración) quedan muy por
        debajo, fuera del Top y por detrás de Medicina/Enfermería.
      - Medicina ya NO aparece en 0%: tiene afinidad real (>0)."""
    rk = _evaluar({"R": 5, "I": 2, "A": 1, "S": 3, "E": 1, "C": 5})
    idx = {c["id"]: i for i, c in enumerate(rk)}

    # 1) Su propia carrera encabeza el ranking.
    assert rk[0]["id"] == "tec_instrumentacion_quirurgica", rk[0]["id"]

    # 2) Salud domina el Top-5 (mayoría: al menos 3 de 5).
    salud_top5 = sum(c["area"] == "Ciencias de la Salud" for c in rk[:5])
    assert salud_top5 >= 3, salud_top5

    # 3) Las comerciales quedan muy por debajo (fuera del Top-20)...
    top20 = _ids(rk, 20)
    assert "martillero_publico" not in top20
    assert "administracion_empresas" not in top20

    # 4) ...y por detrás de las carreras de salud afines a su perfil.
    assert idx["medicina"] < idx["martillero_publico"]
    assert idx["enfermeria"] < idx["administracion_empresas"]

    # 5) El bug histórico "Medicina 0%" no se reproduce: afinidad real.
    medicina = next(c for c in rk if c["id"] == "medicina")
    assert medicina["afinidad_pct"] > 0, medicina["afinidad_pct"]


def test_perfil_plano_indeciso() -> None:
    """Usuario indeciso que responde todo en el medio (3): perfil sin
    preferencia. El sistema NO debe colapsar (ni NaN, ni excepción, ni
    catálogo recortado): devuelve el catálogo completo con afinidad 0."""
    rk = _evaluar({"R": 3, "I": 3, "A": 3, "S": 3, "E": 3, "C": 3})
    assert len(rk) == len(CATALOGO)                  # no se cae ni recorta
    assert all(c["afinidad_pct"] == 0 for c in rk)   # perfil no informativo
    assert rk[0]["afinidad_pct"] == 0


def test_perfil_extremo() -> None:
    """Perfil extremo: 5 en una sola dimensión (R) y 1 en todas las demás.
    El motor no debe romperse y debe priorizar el polo dominante: el #1 es
    una carrera fuertemente Realista (R es su dimensión máxima) y los
    porcentajes son sanos (monótonos y dentro de [0, 100])."""
    rk = _evaluar({"R": 5, "I": 1, "A": 1, "S": 1, "E": 1, "C": 1})
    top = rk[0]["riasec"]
    assert top["R"] >= 4, rk[0]["id"]                  # el #1 es Realista
    assert top["R"] == max(top.values()), rk[0]["id"]  # R es su dim dominante
    assert rk[0]["afinidad_pct"] >= 70
    pcts = [c["afinidad_pct"] for c in rk]
    assert pcts == sorted(pcts, reverse=True)          # monótono no creciente
    assert all(0 <= p <= 100 for p in pcts)


def test_perfil_multipotencial() -> None:
    """Perfil 'multipotencial': 5 en dos dimensiones OPUESTAS del hexágono de
    Holland (R y S, enfrentadas). El motor no debe quedarse con un solo polo:
    el Top debe contener carreras de AMBOS extremos y privilegiar las que
    tienden un puente entre lo manual y lo asistencial (p. ej. Kinesiología,
    R+S altos)."""
    rk = _evaluar({"R": 5, "I": 1, "A": 1, "S": 5, "E": 1, "C": 1})
    top10 = rk[:10]
    assert any(c["riasec"]["R"] >= 4 for c in top10)   # polo Realista presente
    assert any(c["riasec"]["S"] >= 4 for c in top10)   # polo Social presente
    # Una carrera "puente" R+S domina el podio.
    assert "kinesiologia" in _ids(rk, 5)
    pcts = [c["afinidad_pct"] for c in rk]
    assert pcts == sorted(pcts, reverse=True)


def test_filtro_rutina_administrativa() -> None:
    """Nuevo filtro (F8 -> etiqueta 'rutina_administrativa'): un perfil
    Convencional puro saca arriba las carreras de back-office (Contable,
    Secretariado, Logística, etc.). Si el usuario VETA la rutina
    administrativa, todas esas carreras deben desaparecer del ranking."""
    perfil = {"R": 2, "I": 2, "A": 1, "S": 2, "E": 3, "C": 5}
    clericales = {"contador_publico", "tec_administracion_contable",
                  "secretariado_ejecutivo", "administracion_publica",
                  "archivologia", "logistica"}

    sin_veto = _ids(_evaluar(perfil))
    con_veto = _ids(_evaluar(perfil, {"rutina_administrativa": 1}))

    # Sin veto, las administrativas son candidatas fuertes (varias en el Top-10).
    assert len(clericales.intersection(sin_veto[:10])) >= 3
    # Con el veto, ninguna sobrevive.
    assert clericales.isdisjoint(con_veto)
    # El veto recorta exactamente esas carreras del catálogo.
    assert len(con_veto) == len(sin_veto) - len(clericales)


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
        ("Veta dominio político", test_veta_politica),
        ("Coseno != Pearson (híbrido real)", test_coseno_y_pearson_son_distintos),
        ("Sin colisiones de vectores", test_sin_colisiones_de_vectores),
        ("Desempate neutral (orden catálogo)", test_desempate_no_depende_del_orden_del_catalogo),
        ("Afinidad sin castigo al cubo", test_afinidad_sin_castigo_al_cubo),
        ("Edge: Instrumentadora (R+C alto, S medio)", test_perfil_instrumentadora),
        ("Edge: Plano / indeciso (no colapsa)", test_perfil_plano_indeciso),
        ("Edge: Extremo (una dim al máximo)", test_perfil_extremo),
        ("Edge: Multipotencial (R y S opuestos)", test_perfil_multipotencial),
        ("Filtro nuevo: veta rutina administrativa", test_filtro_rutina_administrativa),
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
