"""
=================================================================
PASO 4.2 - INYECCIÓN DE CSS PERSONALIZADO (CLEAN UI)
=================================================================
Anula los estilos por defecto de Streamlit que delatan el framework
y aplica la estética monocromática descrita en el plan:

  - Tipografía geométrica moderna (Inter como primaria, luego stack
    nativo del SO como fallback).
  - Botones planos, afilados, sin sombras ni bordes redondeados grandes.
  - Header / footer / menú de hamburguesa ocultos por completo.
  - Contenedores sin bordes evidentes; separación por espacio en blanco.

Se aplica una sola vez al inicio de la app llamando a `inject_css()`.
=================================================================
"""

from __future__ import annotations

import streamlit as st


# CSS completo en un único string. Lo mantenemos así (en vez de
# múltiples llamadas) para inyectar un solo <style> y minimizar el
# tiempo de re-render en Streamlit.
_CSS = """
<style>
/* ---------- 1. Tipografía ---------- */
/* Importamos Inter desde Google Fonts: emula la familia geométrica
   moderna (similar a SF Pro de Apple) sin requerir instalación local. */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ---------- 2. Ocultar marca y cromos de Streamlit ---------- */
/* Estos selectores eliminan el menú hamburguesa, el footer
   "Made with Streamlit" y la barra de decoración superior. */
#MainMenu      { visibility: hidden; }
footer         { visibility: hidden; }
header         { visibility: hidden; }
[data-testid="stToolbar"]   { visibility: hidden; }
[data-testid="stDecoration"]{ visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }

/* ---------- 3. Jerarquía tipográfica ---------- */
h1 {
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    font-size: 2.6rem !important;
    color: #000000;
    margin-bottom: 0.3rem !important;
}
h2 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: #000000;
    margin-top: 2rem !important;
}
h3 {
    font-weight: 600 !important;
    color: #111111;
}

/* ---------- 4. Botones planos y afilados ---------- */
.stButton > button {
    background-color: #000000;
    color: #FFFFFF;
    border: 1px solid #000000;
    border-radius: 4px;          /* máximo permitido por el plan */
    box-shadow: none;            /* eliminar sombras */
    font-weight: 600;
    padding: 0.55rem 1.4rem;
    transition: background-color 120ms ease, color 120ms ease;
}
.stButton > button:hover {
    background-color: #FFFFFF;
    color: #000000;
    border-color: #000000;
    box-shadow: none;
}
.stButton > button:active,
.stButton > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Botón secundario (kind="secondary") con look invertido. */
.stButton > button[kind="secondary"] {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #111111;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #111111;
    color: #FFFFFF;
}

/* ---------- 5. Inputs sin bordes evidentes ---------- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    border-radius: 4px;
    border: 1px solid #E5E5E5;
    box-shadow: none !important;
}

/* Slider track más sobrio. */
.stSlider [data-baseweb="slider"] > div {
    background-color: #E5E5E5;
}
.stSlider [data-baseweb="slider"] > div > div {
    background-color: #000000 !important;
}

/* ---------- 6. Radio buttons (escala Likert) horizontal ---------- */
div[role="radiogroup"] {
    gap: 0.8rem;
}
div[role="radiogroup"] > label {
    background-color: #F5F5F5;
    border: 1px solid #E5E5E5;
    border-radius: 4px;
    padding: 0.55rem 1.0rem;
    cursor: pointer;
    transition: all 120ms ease;
    font-weight: 500;
}
div[role="radiogroup"] > label:hover {
    border-color: #000000;
}
div[role="radiogroup"] > label[data-checked="true"] {
    background-color: #000000;
    color: #FFFFFF;
    border-color: #000000;
}

/* ---------- 7. Expanders limpios (tarjetas de carrera) ---------- */
[data-testid="stExpander"] {
    border: 1px solid #E5E5E5;
    border-radius: 4px;
    background-color: #FFFFFF;
    box-shadow: none;
    margin-bottom: 0.8rem;
}
[data-testid="stExpander"] summary {
    font-weight: 700;
    padding: 0.6rem 0.8rem;
}
[data-testid="stExpander"] summary:hover {
    background-color: #F5F5F5;
}

/* ---------- 8. Métricas (st.metric) con fuente monoespaciada ---------- */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    font-weight: 700;
    color: #000000;
}
[data-testid="stMetricLabel"] {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    color: #666666;
}

/* ---------- 9. Progress bar negra ---------- */
.stProgress > div > div > div > div {
    background-color: #000000;
}

/* ---------- 10. Tarjeta de recomendación (clase custom) ---------- */
/* Estas clases se usan desde visualizations.py para los Top-5. */
.recom-card {
    border: 1px solid #E5E5E5;
    border-radius: 4px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    background-color: #FFFFFF;
    transition: border-color 150ms ease;
}
.recom-card:hover {
    border-color: #000000;
}
.recom-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #000000;
    margin: 0;
}
.recom-subtitle {
    font-size: 0.85rem;
    color: #666666;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.recom-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #000000;
    text-align: right;
}

/* ---------- 11. Sidebar más sobria ---------- */
[data-testid="stSidebar"] {
    background-color: #FAFAFA;
    border-right: 1px solid #EAEAEA;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 1.1rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ---------- 12. Divider más sutil ---------- */
hr {
    border-top: 1px solid #EAEAEA !important;
    margin: 1.5rem 0 !important;
}
</style>
"""


def inject_css() -> None:
    """Inyecta el bloque CSS en la página actual.

    Debe llamarse UNA sola vez por sesión, idealmente justo después
    de `st.set_page_config(...)` y antes de renderizar cualquier
    contenido visible. Streamlit re-ejecuta el script en cada
    interacción, así que la inyección se repite pero es idempotente.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
