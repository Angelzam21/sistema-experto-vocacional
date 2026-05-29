"""
=================================================================
SISTEMA VISUAL "NEO-BRUTALISMO GAMIFICADO" — MARCA ORIENTAI
=================================================================
Reemplaza la antigua estética monocromática plana por un sistema
de diseño táctil de alto contraste:

  - Sombras sólidas (sin blur) tipo Neo-Brutalismo.
  - Bordes gruesos oscuros y radios moderados (12px).
  - Feedback de "presión" al seleccionar / enfocar (el elemento se
    desplaza hacia su sombra y ésta desaparece).
  - Atajos de teclado renderizados como "teclas físicas".
  - Acentos "Tech-Pop" (violeta) para el estado seleccionado.

Toda la paleta vive en variables CSS en :root para mantener un
único punto de verdad. Se inyecta una sola vez con `inject_css()`.
=================================================================
"""

from __future__ import annotations

import streamlit as st


# CSS completo en un único string. Lo mantenemos así (en vez de
# múltiples llamadas) para inyectar un solo <style> y minimizar el
# tiempo de re-render en Streamlit.
_CSS = """
<style>
/* ---------- 0. Variables del sistema de diseño (ORIENTAI) ---------- */
:root {
    --bg-main: #f8f9fa;
    --text-main: #111827;
    --border-dark: #111827;
    --accent-base: #ffffff;
    --accent-hover: #e0e7ff;
    --accent-selected: #c4b5fd;
    --shadow-offset: 4px;
}

/* ---------- 1. Tipografía ---------- */
/* Inter para UI + JetBrains Mono para datos y teclas físicas. */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ---------- 2. Fondo "sistema de datos" ---------- */
/* Color base + patrón sutil de puntos (radial-gradient) para dar
   sensación de superficie técnica. Lo aplicamos al contenedor de la
   app de Streamlit (que tapa al <body>) además del propio body. */
body,
[data-testid="stAppViewContainer"] {
    background-color: var(--bg-main) !important;
    color: var(--text-main) !important;
    background-image: radial-gradient(rgba(17, 24, 39, 0.07) 1px,
                                       transparent 1px) !important;
    background-size: 22px 22px !important;
}

/* ---------- 3. Ocultar marca y cromos de Streamlit ---------- */
#MainMenu      { visibility: hidden; }
footer         { visibility: hidden; }
header         { visibility: hidden; }
[data-testid="stToolbar"]   { visibility: hidden; }
[data-testid="stDecoration"]{ visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }

/* ---------- 4. Jerarquía tipográfica ---------- */
h1 {
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    font-size: 2.6rem !important;
    color: var(--text-main);
    margin-bottom: 0.3rem !important;
}
h2 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: var(--text-main);
    margin-top: 2rem !important;
}
h3 {
    font-weight: 600 !important;
    color: var(--text-main);
}

/* ---------- 5. Botones de navegación (Neo-Brutalistas) ---------- */
/* Aplicamos el mismo lenguaje táctil que a las opciones para que el
   sistema sea coherente: borde grueso, sombra sólida y "presión". */
.stButton > button {
    background-color: var(--text-main);
    color: var(--accent-base);
    border: 2px solid var(--border-dark);
    border-radius: 12px;
    box-shadow: var(--shadow-offset) var(--shadow-offset) 0px var(--border-dark);
    font-weight: 700;
    padding: 0.55rem 1.4rem;
    transition: all 0.15s ease-out;
}
.stButton > button:hover {
    /* Movimiento sutil hacia la sombra (medio camino a la presión). */
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--border-dark);
}
.stButton > button:active,
.stButton > button:focus-visible {
    /* Presión completa: el botón ocupa el lugar de su sombra. */
    transform: translate(var(--shadow-offset), var(--shadow-offset));
    box-shadow: 0px 0px 0px var(--border-dark) !important;
    outline: none !important;
}
.stButton > button:disabled {
    opacity: 0.4;
    transform: none;
    box-shadow: var(--shadow-offset) var(--shadow-offset) 0px var(--border-dark);
    cursor: not-allowed;
}

/* Botón secundario (kind="secondary"): claro con texto oscuro. */
.stButton > button[kind="secondary"] {
    background-color: var(--accent-base);
    color: var(--text-main);
}
.stButton > button[kind="secondary"]:hover {
    background-color: var(--accent-hover);
}

/* ---------- 6. Inputs ---------- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    border-radius: 12px;
    border: 2px solid var(--border-dark);
    box-shadow: none !important;
}

/* Slider track. */
.stSlider [data-baseweb="slider"] > div {
    background-color: #E5E5E5;
}
.stSlider [data-baseweb="slider"] > div > div {
    background-color: var(--text-main) !important;
}

/* ============================================================== */
/* 7. OPCIONES DE RESPUESTA (.option-btn) — escala Likert         */
/* Las "opciones" del test son los <label> del st.radio. Les damos */
/* el tratamiento Neo-Brutalista completo y los convertimos en     */
/* botones-tecla.                                                  */
/* ============================================================== */
div[role="radiogroup"] {
    gap: 0.8rem;
}

/* Ocultamos el círculo nativo del radio: la "tecla física" (::before)
   pasa a ser el único indicador visual de cada opción. */
div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

div[role="radiogroup"] > label {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background-color: var(--accent-base);
    border: 2px solid var(--border-dark);
    border-radius: 12px;
    box-shadow: var(--shadow-offset) var(--shadow-offset) 0px var(--border-dark);
    padding: 0.55rem 1.0rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.15s ease-out;
}
div[role="radiogroup"] > label:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--border-dark);
    background-color: var(--accent-hover);
}
/* Estado seleccionado / activo / foco-teclado: presión completa. */
div[role="radiogroup"] > label[data-checked="true"],
div[role="radiogroup"] > label:active,
div[role="radiogroup"] > label:focus-visible {
    transform: translate(var(--shadow-offset), var(--shadow-offset));
    box-shadow: 0px 0px 0px var(--border-dark);
    background-color: var(--accent-selected);
}

/* ---------- 7b. Atajos de teclado (.keyboard-hint) ---------- */
/* Badge de "tecla física" antes del texto de cada opción. El número
   se deriva de la posición (nth-of-type), por eso el texto de la
   opción en app.py ya NO incluye el prefijo numérico. */
div[role="radiogroup"] > label::before {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-weight: 700;
    font-size: 0.85rem;
    line-height: 1;
    color: var(--accent-base);
    background-color: var(--text-main);
    border: 2px solid var(--border-dark);
    border-radius: 6px;
    padding: 0.25rem 0.45rem;
    min-width: 1.4rem;
    text-align: center;
    box-shadow: 1px 1px 0px var(--border-dark);
}
/* Invertimos los colores de la tecla cuando la opción está seleccionada. */
div[role="radiogroup"] > label[data-checked="true"]::before {
    color: var(--text-main);
    background-color: var(--accent-base);
}
div[role="radiogroup"] > label:nth-of-type(1)::before { content: "1"; }
div[role="radiogroup"] > label:nth-of-type(2)::before { content: "2"; }
div[role="radiogroup"] > label:nth-of-type(3)::before { content: "3"; }
div[role="radiogroup"] > label:nth-of-type(4)::before { content: "4"; }
div[role="radiogroup"] > label:nth-of-type(5)::before { content: "5"; }

/* ---------- 8. Expanders (tarjetas de carrera) ---------- */
[data-testid="stExpander"] {
    border: 2px solid var(--border-dark);
    border-radius: 12px;
    background-color: var(--accent-base);
    box-shadow: var(--shadow-offset) var(--shadow-offset) 0px var(--border-dark);
    margin-bottom: 0.8rem;
}
[data-testid="stExpander"] summary {
    font-weight: 700;
    padding: 0.6rem 0.8rem;
}
[data-testid="stExpander"] summary:hover {
    background-color: var(--accent-hover);
}

/* ---------- 9. Métricas (st.metric) ---------- */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    font-weight: 700;
    color: var(--text-main);
}
[data-testid="stMetricLabel"] {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    color: #6b7280;
}

/* ---------- 10. Progress bar Neo-Brutalista ---------- */
.stProgress > div > div > div {
    border: 2px solid var(--border-dark);
    border-radius: 8px;
    background-color: var(--accent-base);
}
.stProgress > div > div > div > div {
    background-color: var(--accent-selected);
}

/* ---------- 11. Tarjeta de recomendación (clase custom) ---------- */
/* Usada desde visualizations.py para los Top-5. */
.recom-card {
    border: 2px solid var(--border-dark);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1.1rem;
    background-color: var(--accent-base);
    box-shadow: var(--shadow-offset) var(--shadow-offset) 0px var(--border-dark);
    transition: all 0.15s ease-out;
}
.recom-card:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--border-dark);
}
.recom-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--text-main);
    margin: 0;
}
.recom-subtitle {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.recom-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text-main);
    text-align: right;
}

/* ---------- 12. Sidebar ---------- */
[data-testid="stSidebar"] {
    background-color: var(--accent-base);
    border-right: 2px solid var(--border-dark);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 1.1rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ---------- 13. Divider ---------- */
hr {
    border-top: 2px solid var(--border-dark) !important;
    opacity: 0.15;
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
