"""
=================================================================
SISTEMA EXPERTO VOCACIONAL - APP PRINCIPAL (Streamlit)
=================================================================
Implementa la Fase 3 del plan: Streamlit actúa simultáneamente como
motor algorítmico y capa de presentación, sin backend externo, sin
base de datos, sin estado persistente.

Flujo de la aplicación (state machine basada en st.session_state):

    BIENVENIDA  ->  FILTROS  ->  TEST  ->  RESULTADOS
                                              ^
                                              |
                                          REINICIAR

Privacidad por diseño: el vector RIASEC del usuario vive sólo en
st.session_state (memoria volátil de la sesión). No se loguea ni se
persiste en ningún archivo.

Ejecución:
    streamlit run app.py
=================================================================
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from engine.filters import (
    aplicar_filtros_duros,
    todas_las_modalidades,
    todas_las_zonas,
)
from engine.inference import (
    DIMENSIONES_RIASEC,
    calcular_vector_usuario,
    ranking_carreras,
)
from ui.styles import inject_css
from ui.visualizations import (
    ETIQUETAS_RIASEC,
    radar_chart_riasec,
    tarjeta_recomendacion,
)


# -----------------------------------------------------------------
# Constantes de rutas + configuración de página
# -----------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
PATH_CARRERAS = DATA_DIR / "carreras_argentina.json"
PATH_PREGUNTAS = DATA_DIR / "preguntas_riasec_ar.json"

# Etapas del flujo (state machine).
ETAPA_BIENVENIDA = "bienvenida"
ETAPA_FILTROS = "filtros"
ETAPA_TEST = "test"
ETAPA_RESULTADOS = "resultados"

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
# 1. CARGA DE DATOS EN MEMORIA (Paso 3.1)
# =================================================================
# El decorador @st.cache_data garantiza que los JSON se lean del disco
# UNA SOLA VEZ por proceso. Las re-ejecuciones del script (cada
# interacción del usuario en Streamlit) reusan el resultado cacheado.
@st.cache_data(show_spinner=False)
def cargar_catalogo() -> list[dict]:
    """Lee carreras_argentina.json y devuelve la lista de carreras.

    La función está cacheada: la primera invocación lee y parsea;
    las siguientes devuelven la referencia ya parseada.
    """
    raw = json.loads(PATH_CARRERAS.read_text(encoding="utf-8"))
    return raw["carreras"]


@st.cache_data(show_spinner=False)
def cargar_preguntas() -> list[dict]:
    """Lee preguntas_riasec_ar.json y devuelve la lista de items."""
    raw = json.loads(PATH_PREGUNTAS.read_text(encoding="utf-8"))
    return raw["preguntas"]


# =================================================================
# 2. INICIALIZACIÓN DEL ESTADO DE SESIÓN
# =================================================================
# st.session_state persiste entre re-ejecuciones del script mientras
# dure la conexión del navegador. Es nuestro único "almacén" mutable.
def init_session() -> None:
    """Inicializa todas las claves de session_state usadas por la app.

    Patrón defensivo: setdefault asegura que cada clave exista sin
    sobrescribir si ya fue seteada (necesario porque Streamlit corre
    todo el script en cada interacción).
    """
    st.session_state.setdefault("etapa", ETAPA_BIENVENIDA)
    st.session_state.setdefault("filtros_zonas", [])
    st.session_state.setdefault("filtros_modalidades", [])
    st.session_state.setdefault("respuestas", {})       # {qid: 1..5}
    st.session_state.setdefault("vector_usuario", None) # dict RIASEC
    st.session_state.setdefault("indice_pregunta", 0)   # progreso del test


def avanzar_a(etapa: str) -> None:
    """Cambia la etapa actual y fuerza re-render."""
    st.session_state["etapa"] = etapa
    st.rerun()


# =================================================================
# 3. PANTALLAS
# =================================================================

def pantalla_bienvenida() -> None:
    """Landing inicial: explicación + CTA para empezar."""
    st.markdown("# Test Vocacional")
    st.markdown("## Sistema Experto")
    st.markdown(
        "##### Este breve test te ayudará a elegir tu carrera ideal y en cual universidad pública argentina podes cursarla."
    )
    st.markdown("---")

    st.markdown(
        """
       Este sistema analiza tus **intereses personales** basándose en el Modelo de Holland y los cruza con la oferta académica de las 
       principales universidades públicas del país, utilizando el estándar internacional **O*NET.** 

        **Cómo funciona:**

        1. Indicás tus restricciones (zona donde podés cursar y modalidad).
        2. Respondés un test corto de 36 preguntas.
        3. Nuestro algoritmo traza tu perfil vocacional y calcula matemáticamente el porcentaje de coincidencia con los requisitos de cada carrera.
        4. Recibís un ranking de afinidad y un análisis visual de tu perfil.

        **Privacidad:** tus respuestas viven sólo en esta sesión. Nada 
        se guarda ni se envía a servidores externos. 
        """
    )

    st.markdown("&nbsp;")
    if st.button("Comenzar →", type="primary", use_container_width=True):
        avanzar_a(ETAPA_FILTROS)


def pantalla_filtros() -> None:
    """Captura los Filtros Duros: zona y modalidad (Paso 3.2)."""
    st.markdown("# Restricciones Previas")
    st.markdown("## (opcional)")
    st.markdown(
        "Antes de analizar tus intereses, contanos en qué zonas del pais "
        "podes cursar y qué modalidad preferis. Asi evitamos recomendarte opciones que no se ajusten a tus posibilidades."
    )
    st.markdown("---")

    catalogo = cargar_catalogo()
    zonas_disp = todas_las_zonas(catalogo)
    modas_disp = todas_las_modalidades(catalogo)

    st.markdown("### Zona geográfica")
    st.caption("Seleccioná todas las que te sirvan. Si no elegís ninguna, no se aplica filtro.")
    zonas = st.multiselect(
        label="Zonas donde podés estudiar",
        options=zonas_disp,
        default=st.session_state["filtros_zonas"],
        label_visibility="collapsed",
    )

    st.markdown("### Modalidad")
    st.caption("Seleccioná las que te sirvan. Si no elegís ninguna todas las modalidades aceptadas.")
    modalidades = st.multiselect(
        label="Modalidades aceptadas",
        options=modas_disp,
        default=st.session_state["filtros_modalidades"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("← Volver", type="secondary", use_container_width=True):
            avanzar_a(ETAPA_BIENVENIDA)
    with col_b:
        if st.button("Continuar al test →", type="primary", use_container_width=True):
            st.session_state["filtros_zonas"] = zonas
            st.session_state["filtros_modalidades"] = modalidades

            # Pre-check: con los filtros actuales, ¿quedan carreras?
            sobreviven = aplicar_filtros_duros(catalogo, zonas, modalidades)
            if not sobreviven:
                st.error(
                    "Con esos filtros ninguna carrera del catálogo es "
                    "viable. Probá relajar zonas o modalidades."
                )
            else:
                st.session_state["indice_pregunta"] = 0
                st.session_state["respuestas"] = {}
                avanzar_a(ETAPA_TEST)


def pantalla_test() -> None:
    """Test reactivo: una pregunta a la vez con escala Likert 1-5."""
    preguntas = cargar_preguntas()
    total = len(preguntas)
    idx = st.session_state["indice_pregunta"]

    # Cabecera con progreso (barra negra + contador).
    st.markdown("# Test de intereses")
    st.progress((idx) / total, text=f"Pregunta {idx + 1} de {total}")
    st.markdown("---")

    pregunta = preguntas[idx]
    dimension_humana = ETIQUETAS_RIASEC[pregunta["dimension"]]

    st.markdown(f"##### Dimensión: *{dimension_humana}*")
    st.markdown(f"### ¿Cuánto te gustaría {pregunta['pregunta'].lower()}?")

    # Recuperamos la respuesta previa (si el usuario volvió) para
    # preseleccionarla. Default = 3 (neutro) si nunca contestó.
    respuesta_previa = st.session_state["respuestas"].get(pregunta["id"], 3)

    # Escala Likert horizontal con radio buttons (estética cuidada via CSS).
    opciones = {
        1: "1 · Lo detestaría",
        2: "2 · No me gustaría",
        3: "3 · Me da igual",
        4: "4 · Me gustaría",
        5: "5 · Me encantaría",
    }
    seleccion = st.radio(
        label="Tu respuesta",
        options=list(opciones.keys()),
        format_func=lambda v: opciones[v],
        index=list(opciones.keys()).index(respuesta_previa),
        horizontal=True,
        label_visibility="collapsed",
        key=f"radio_{pregunta['id']}",
    )

    # Guardamos inmediatamente la respuesta en session_state.
    st.session_state["respuestas"][pregunta["id"]] = int(seleccion)

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        if st.button("← Anterior", use_container_width=True, disabled=(idx == 0), type="secondary"):
            st.session_state["indice_pregunta"] = max(0, idx - 1)
            st.rerun()
    with col_b:
        if st.button("Cancelar test", use_container_width=True, type="secondary"):
            avanzar_a(ETAPA_FILTROS)
    with col_c:
        es_ultima = idx == total - 1
        label_btn = "Ver resultados →" if es_ultima else "Siguiente →"
        if st.button(label_btn, use_container_width=True, type="primary"):
            if es_ultima:
                # Calcular el vector ANTES de cambiar de pantalla.
                st.session_state["vector_usuario"] = calcular_vector_usuario(
                    st.session_state["respuestas"],
                    preguntas,
                )
                avanzar_a(ETAPA_RESULTADOS)
            else:
                st.session_state["indice_pregunta"] = idx + 1
                st.rerun()


def pantalla_resultados() -> None:
    """Dashboard final: vector usuario + ranking Top-5."""
    vector = st.session_state["vector_usuario"]
    if vector is None:
        # Defensa contra accesos directos sin haber hecho el test.
        st.warning("Aún no hay vector calculado. Volvé al test.")
        if st.button("Volver al inicio"):
            reiniciar()
        return

    st.markdown("# Resultados")
    st.markdown("##### Tu perfil de intereses y las 5 carreras más afines.")
    st.markdown("---")

    # --------- Panel 1: Métricas RIASEC ---------
    st.markdown("### Tu perfil RIASEC")
    cols = st.columns(6)
    for col, dim in zip(cols, DIMENSIONES_RIASEC):
        # st.metric con CSS personalizado (label en uppercase + mono).
        col.metric(label=ETIQUETAS_RIASEC[dim], value=f"{vector[dim]:.2f}")

    # --------- Panel 2: Radar Chart ---------
    fig = radar_chart_riasec(vector, titulo="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --------- Panel 3: Ranking Top-5 ---------
    catalogo = cargar_catalogo()
    elegibles = aplicar_filtros_duros(
        catalogo,
        st.session_state["filtros_zonas"],
        st.session_state["filtros_modalidades"],
    )
    ranking = ranking_carreras(vector, elegibles)
    top5 = ranking[:5]

    st.markdown(f"### Top {len(top5)} de carreras recomendadas")
    st.caption(
        f"Calculado sobre {len(elegibles)} carreras viables (de "
        f"{len(catalogo)} totales) según tus filtros previos."
    )
    st.markdown("&nbsp;")

    for i, carrera in enumerate(top5, start=1):
        tarjeta_recomendacion(carrera, posicion=i)

    # --------- Panel 4: Ranking completo (colapsable) ---------
    with st.expander(f"Ver ranking completo ({len(ranking)} carreras)"):
        for i, c in enumerate(ranking, start=1):
            st.markdown(
                f"**{i:02d}.** {c['nombre']} — `{c['afinidad_pct']}%`"
            )

    st.markdown("---")
    if st.button("Hacer otro test", type="primary", use_container_width=True):
        reiniciar()


# =================================================================
# 4. UTILIDADES Y ROUTER
# =================================================================
def reiniciar() -> None:
    """Limpia el session_state y vuelve a la bienvenida."""
    # Conservamos solo las claves del framework; vaciamos las nuestras.
    for k in [
        "etapa", "filtros_zonas", "filtros_modalidades",
        "respuestas", "vector_usuario", "indice_pregunta",
    ]:
        st.session_state.pop(k, None)
    init_session()
    st.rerun()


def main() -> None:
    """Router principal: despacha según la etapa actual."""
    init_session()

    etapa = st.session_state["etapa"]
    if etapa == ETAPA_BIENVENIDA:
        pantalla_bienvenida()
    elif etapa == ETAPA_FILTROS:
        pantalla_filtros()
    elif etapa == ETAPA_TEST:
        pantalla_test()
    elif etapa == ETAPA_RESULTADOS:
        pantalla_resultados()
    else:
        # Estado corrupto: re-inicializamos defensivamente.
        reiniciar()


# Streamlit ejecuta el script top-down en cada interacción del usuario.
# Llamamos main() incondicionalmente: la convención en Streamlit es no
# usar el guard __name__ == "__main__" porque el módulo SIEMPRE corre
# cuando lo lanza `streamlit run`.
main()
