"""
=================================================================
SISTEMA EXPERTO VOCACIONAL - APP PRINCIPAL (Streamlit)
=================================================================
Streamlit actúa simultáneamente como motor algorítmico y capa de
presentación: sin backend externo.

Flujo de la aplicación (state machine sobre st.session_state):

    BIENVENIDA  ->  TEST  ->  FILTROS  ->  RESULTADOS
                                              ^
                                              |
                                          REINICIAR

  - TEST     : 36 preguntas RIASEC (1ra capa) -> construyen el perfil
               de intereses del usuario.
  - FILTROS  : 6 preguntas de aversión (2da capa) -> descartan carreras
               cuyo trabajo diario el usuario rechaza de plano.
  - RESULTADOS: ranking de carreras por afinidad de coseno, sobre el
               catálogo ya filtrado por la 2da capa.

Privacidad por diseño: las respuestas y el vector RIASEC viven sólo en
st.session_state (memoria volátil de la sesión). No se loguean ni se
persisten en disco.

Ejecución:
    streamlit run app.py
=================================================================
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from engine.filters import aplicar_filtros, etiquetas_vetadas
from engine.inference import (
    DIMENSIONES_RIASEC,
    calcular_vector_usuario,
    ranking_carreras,
)
from ui.keyboard import inyectar_navegacion_teclado
from ui.styles import inject_css
from ui.visualizations import (
    ETIQUETAS_RIASEC,
    radar_chart_riasec,
    tarjeta_recomendacion,
)


# -----------------------------------------------------------------
# Rutas a los datos + configuración de página
# -----------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
PATH_CARRERAS = DATA_DIR / "carreras.json"
PATH_PREGUNTAS = DATA_DIR / "preguntas.json"

# Etapas del flujo (state machine).
ETAPA_BIENVENIDA = "bienvenida"
ETAPA_TEST = "test"
ETAPA_FILTROS = "filtros"
ETAPA_RESULTADOS = "resultados"

# Claves propias en session_state (todo lo que reseteamos al reiniciar).
CLAVES_SESION = (
    "etapa", "respuestas", "respuestas_filtro", "vector_usuario", "indice_pregunta",
)

# Escala Likert compartida por el test y los filtros. El número de atajo
# (1..5) ya NO va en el texto: la UI lo renderiza como "tecla física"
# (badge ::before) sobre cada opción del radio (ver ui/styles.py).
OPCIONES_LIKERT = {
    1: "Lo detestaría",
    2: "No me gustaría",
    3: "Me da igual",
    4: "Me gustaría",
    5: "Me encantaría",
}

# st.set_page_config DEBE ser la primera instrucción de Streamlit.
st.set_page_config(
    page_title="Sistema Experto Vocacional",
    page_icon="◼",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS personalizado: ocultar marca Streamlit + estética monocromática.
inject_css()


# =================================================================
# 1. CARGA DE DATOS EN MEMORIA
# =================================================================
# @st.cache_data garantiza que cada JSON se lea del disco UNA SOLA VEZ
# por proceso. Las re-ejecuciones del script (cada interacción) reusan
# el resultado cacheado.
@st.cache_data(show_spinner=False)
def cargar_catalogo() -> list[dict]:
    """Lee data/carreras.json y devuelve la lista de carreras."""
    raw = json.loads(PATH_CARRERAS.read_text(encoding="utf-8"))
    return raw["carreras"]


@st.cache_data(show_spinner=False)
def cargar_preguntas() -> list[dict]:
    """Lee las 36 preguntas RIASEC (1ra capa)."""
    raw = json.loads(PATH_PREGUNTAS.read_text(encoding="utf-8"))
    return raw["preguntas"]


@st.cache_data(show_spinner=False)
def cargar_filtros() -> list[dict]:
    """Lee las 6 preguntas filtro de aversión (2da capa)."""
    raw = json.loads(PATH_PREGUNTAS.read_text(encoding="utf-8"))
    return raw["filtros"]


# =================================================================
# 2. ESTADO DE SESIÓN
# =================================================================
def init_session() -> None:
    """Inicializa las claves de session_state (patrón defensivo)."""
    st.session_state.setdefault("etapa", ETAPA_BIENVENIDA)
    st.session_state.setdefault("respuestas", {})         # {qid: 1..5}
    st.session_state.setdefault("respuestas_filtro", {})  # {fid: 1..5}
    st.session_state.setdefault("vector_usuario", None)   # dict RIASEC
    st.session_state.setdefault("indice_pregunta", 0)     # progreso del test


def avanzar_a(etapa: str) -> None:
    """Cambia la etapa actual y fuerza re-render."""
    st.session_state["etapa"] = etapa
    st.rerun()


def reiniciar() -> None:
    """Limpia el estado propio y vuelve a la bienvenida."""
    for k in CLAVES_SESION:
        st.session_state.pop(k, None)
    init_session()
    st.rerun()


# =================================================================
# 3. PANTALLAS
# =================================================================

def pantalla_bienvenida() -> None:
    """Landing inicial: explicación + CTA para empezar."""
    st.markdown("# Test Vocacional")
    st.caption("Sistema Experto")
    st.markdown(
        "##### Descubrí qué carreras de grado se ajustan mejor a tus intereses."
    )
    st.markdown("---")

    st.markdown(
        """
        Este sistema analiza tus **intereses personales** con el Modelo de
        Holland (RIASEC) y los cruza con el perfil ocupacional de cada
        carrera, derivado del estándar internacional **O\\*NET**.

        **Cómo funciona:**

        1. Respondés un test de **36 preguntas** sobre lo que te gusta hacer.
        2. Definís tus **límites**: 6 preguntas para descartar trabajos que
           no harías ni a palos (atender pacientes, programar, vender, etc.).
        3. El motor calcula tu perfil y mide matemáticamente la afinidad con
           cada carrera.
        4. Recibís un **ranking de carreras** y un análisis visual de tu perfil.

        **Privacidad:** tus respuestas viven sólo en esta sesión. Nada se
        guarda ni se envía a servidores externos.
        """
    )

    st.markdown("&nbsp;")
    if st.button("Comenzar →", type="primary", use_container_width=True):
        # Arrancamos el test desde cero.
        st.session_state["respuestas"] = {}
        st.session_state["indice_pregunta"] = 0
        avanzar_a(ETAPA_TEST)


def pantalla_test() -> None:
    """Test reactivo: una pregunta RIASEC a la vez con escala Likert 1-5."""
    preguntas = cargar_preguntas()
    total = len(preguntas)
    idx = st.session_state["indice_pregunta"]

    st.markdown("# Test de intereses")
    st.progress(idx / total, text=f"Pregunta {idx + 1} de {total}")
    st.markdown("---")

    pregunta = preguntas[idx]
    dimension_humana = ETIQUETAS_RIASEC[pregunta["dimension"]]

    st.markdown(f"##### Dimensión: *{dimension_humana}*")
    st.markdown(f"### ¿Cuánto te gustaría {pregunta['pregunta'].lower()}?")

    # Recuperamos la respuesta previa (si el usuario volvió) o 3 (neutro).
    respuesta_previa = st.session_state["respuestas"].get(pregunta["id"], 3)

    seleccion = st.radio(
        label="Tu respuesta",
        options=list(OPCIONES_LIKERT.keys()),
        format_func=lambda v: OPCIONES_LIKERT[v],
        index=list(OPCIONES_LIKERT.keys()).index(respuesta_previa),
        horizontal=True,
        label_visibility="collapsed",
        key=f"radio_{pregunta['id']}",
    )
    st.session_state["respuestas"][pregunta["id"]] = int(seleccion)

    # Pista de descubribilidad de los atajos de teclado.
    st.caption("Atajos: teclas **1–5** para responder · **Enter** para avanzar.")

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        if st.button("← Anterior", use_container_width=True, disabled=(idx == 0), type="secondary"):
            st.session_state["indice_pregunta"] = max(0, idx - 1)
            st.rerun()
    with col_b:
        if st.button("Cancelar", use_container_width=True, type="secondary"):
            reiniciar()
    with col_c:
        es_ultima = idx == total - 1
        label_btn = "Definir límites →" if es_ultima else "Siguiente →"
        if st.button(label_btn, use_container_width=True, type="primary"):
            if es_ultima:
                # Calculamos el vector RIASEC ANTES de pasar a la 2da capa.
                st.session_state["vector_usuario"] = calcular_vector_usuario(
                    st.session_state["respuestas"], preguntas,
                )
                avanzar_a(ETAPA_FILTROS)
            else:
                st.session_state["indice_pregunta"] = idx + 1
                st.rerun()

    # Atajos de teclado (1..5 = responder, Enter = avanzar). Se inyecta al
    # final, ya construido el DOM de la pregunta: el puente JS hace click
    # sobre el radio / botón primario de ARRIBA. Sólo en la pantalla de test,
    # donde hay un único radiogroup (en FILTROS habría 6 y sería ambiguo).
    # El componente se re-inyecta en cada rerun pero mantiene UN solo
    # listener vivo (ver cleanup en ui/keyboard.py).
    inyectar_navegacion_teclado(num_opciones=len(OPCIONES_LIKERT))


def pantalla_filtros() -> None:
    """Segunda capa: preguntas de aversión que descartan carreras."""
    filtros = cargar_filtros()

    st.markdown("# Tus límites")
    st.markdown("##### Última parte: ¿hay cosas que NO harías ni en tu peor día?")
    st.markdown(
        "Marcá cada actividad según cuánto estarías dispuesto/a a hacerla. "
        "Todo lo que respondas **\"No me gustaría\"** o **\"Lo detestaría\"** "
        "se usará para **descartar** las carreras que dependen de eso, aunque "
        "tu perfil de intereses se les parezca."
    )
    st.markdown("---")

    for f in filtros:
        st.markdown(f"### {f['pregunta']}")
        previa = st.session_state["respuestas_filtro"].get(f["id"], 3)
        seleccion = st.radio(
            label=f["pregunta"],
            options=list(OPCIONES_LIKERT.keys()),
            format_func=lambda v: OPCIONES_LIKERT[v],
            index=list(OPCIONES_LIKERT.keys()).index(previa),
            horizontal=True,
            label_visibility="collapsed",
            key=f"filtro_{f['id']}",
        )
        st.session_state["respuestas_filtro"][f["id"]] = int(seleccion)
        st.caption(f"Si lo evitás, se descartan: {f['descarta']}")
        st.markdown("&nbsp;")

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("← Volver al test", type="secondary", use_container_width=True):
            # Volvemos a la última pregunta del test.
            st.session_state["indice_pregunta"] = len(cargar_preguntas()) - 1
            avanzar_a(ETAPA_TEST)
    with col_b:
        if st.button("Ver resultados →", type="primary", use_container_width=True):
            avanzar_a(ETAPA_RESULTADOS)


def pantalla_resultados() -> None:
    """Dashboard final: perfil RIASEC + ranking ya filtrado."""
    vector = st.session_state["vector_usuario"]
    if vector is None:
        st.warning("Aún no hay vector calculado. Volvé a hacer el test.")
        if st.button("Volver al inicio"):
            reiniciar()
        return

    st.markdown("# Resultados")
    st.markdown("##### Tu perfil de intereses y las carreras más afines.")
    st.markdown("---")

    # --------- Panel 1: Métricas RIASEC ---------
    st.markdown("### Tu perfil RIASEC")
    cols = st.columns(6)
    for col, dim in zip(cols, DIMENSIONES_RIASEC):
        col.metric(label=ETIQUETAS_RIASEC[dim], value=f"{vector[dim]:.2f}")

    # --------- Panel 2: Radar Chart ---------
    fig = radar_chart_riasec(vector, titulo="")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")

    # --------- 2da capa: aplicar filtros de aversión ---------
    catalogo = cargar_catalogo()
    filtros = cargar_filtros()
    vetadas = etiquetas_vetadas(st.session_state["respuestas_filtro"], filtros)
    elegibles = aplicar_filtros(catalogo, vetadas)
    descartadas = len(catalogo) - len(elegibles)

    # Salvaguarda: si los filtros descartaron TODO, mostramos el catálogo
    # completo en lugar de una pantalla vacía.
    if not elegibles:
        st.warning(
            "Tus límites descartaron todas las carreras del catálogo. "
            "Mostramos igualmente el ranking completo: revisá tus respuestas "
            "si querés afinarlo."
        )
        elegibles = catalogo
        descartadas = 0

    # --------- Vector nulo (usuario que responde todo igual) ---------
    ranking = ranking_carreras(vector, elegibles)
    top5 = ranking[:5]
    if top5 and top5[0]["afinidad_pct"] == 0:
        st.warning(
            "**Notamos un patrón en tus respuestas.** Parece que contestaste "
            "casi lo mismo en todas las preguntas. Para poder recomendarte, el "
            "motor necesita que marques diferencias entre lo que te encanta y "
            "lo que no te gusta."
        )
        if st.button("🔄 Volver a hacer el test", type="primary"):
            reiniciar()
        return

    # --------- Panel 3: Ranking Top-5 ---------
    st.markdown(f"### Top {len(top5)} de carreras recomendadas")
    nota = (
        f"Calculado sobre {len(elegibles)} carreras viables (de "
        f"{len(catalogo)} totales)."
    )
    if descartadas:
        nota += f" Descartamos {descartadas} por tus límites."
    st.caption(nota)
    st.markdown("&nbsp;")

    for i, carrera in enumerate(top5, start=1):
        tarjeta_recomendacion(carrera, posicion=i)

    # --------- Panel 4: Ranking completo (colapsable) ---------
    with st.expander(f"Ver ranking completo ({len(ranking)} carreras)"):
        for i, c in enumerate(ranking, start=1):
            st.markdown(f"**{i:02d}.** {c['nombre']} — `{c['afinidad_pct']}%`")

    st.markdown("---")
    if st.button("Hacer otro test", type="primary", use_container_width=True):
        reiniciar()


# =================================================================
# 4. ROUTER
# =================================================================
def main() -> None:
    """Router principal: despacha según la etapa actual."""
    init_session()

    etapa = st.session_state["etapa"]
    if etapa == ETAPA_BIENVENIDA:
        pantalla_bienvenida()
    elif etapa == ETAPA_TEST:
        pantalla_test()
    elif etapa == ETAPA_FILTROS:
        pantalla_filtros()
    elif etapa == ETAPA_RESULTADOS:
        pantalla_resultados()
    else:
        # Estado corrupto: re-inicializamos defensivamente.
        reiniciar()


# Streamlit ejecuta el script top-down en cada interacción. Llamamos a
# main() incondicionalmente (convención del framework; no se usa el
# guard __name__ == "__main__" porque el módulo siempre corre con
# `streamlit run`).
main()
