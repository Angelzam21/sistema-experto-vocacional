"""
=================================================================
SISTEMA VISUAL "NEO-BRUTALISMO GAMIFICADO" — MARCA ORIENTAI
=================================================================
Paleta oficial ORIENTAI:

  --ink    #111111  bordes y sombras
  --paper  #f6f1e7  fondo principal (tono cálido tipo papel)
  --card   #fffdf8  fondo de tarjetas y botones inactivos
  --violet #c4b5fd  acento primario (seleccionado)
  --lime   #c6ff4d  acento secundario / destellos (hover)

Bug fix de selección visual (v2):
  Se agrega :has(input:checked) junto a [data-checked="true"].
  Streamlit no siempre establece el atributo data-checked en el
  render inicial (option pre-seleccionada por defecto), pero el
  estado nativo del <input type="radio"> SIEMPRE está correcto.
  :has(input:checked) lee ese estado directamente desde el DOM,
  garantizando feedback visual en todos los casos.
=================================================================
"""

from __future__ import annotations

import streamlit as st


_CSS = """
<style>
/* ---------- 0. Paleta ORIENTAI (única fuente de verdad) ---------- */
:root {
    --ink: #111111;
    --paper: #f6f1e7;
    --card: #fffdf8;
    --violet: #c4b5fd;
    --lime: #c6ff4d;
    --shadow-sm: 4px 4px 0px var(--ink);
}

/* ---------- 1. Tipografía ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ---------- 2. Fondo "papel técnico" con patrón de puntos ---------- */
body,
[data-testid="stAppViewContainer"] {
    background-color: var(--paper) !important;
    color: var(--ink) !important;
    background-image: radial-gradient(rgba(17, 17, 17, 0.07) 1px,
                                       transparent 1px) !important;
    background-size: 22px 22px !important;
}

/* Bloque central de contenido: tono cálido, no blanco puro. */
[data-testid="stAppViewBlockContainer"] {
    background-color: transparent !important;
}

/* ---------- 3. Ocultar marca Streamlit ---------- */
#MainMenu      { visibility: hidden; }
footer         { visibility: hidden; }
header         { visibility: hidden; }
[data-testid="stToolbar"]      { visibility: hidden; }
[data-testid="stDecoration"]   { visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }

/* ---------- 4. Header / Navbar ORIENTAI ---------- */
.orientai-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 20px;
    border-bottom: 2px solid var(--ink);
    background: var(--paper);
    margin-bottom: 1.5rem;
}
.orientai-logo-link {
    flex-shrink: 0;
    line-height: 0;
    text-decoration: none;
}
.orientai-logo-link svg {
    height: 48px;
    width: auto;
    max-width: 200px;
}
.orientai-brand {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
}
.orientai-title {
    font-weight: 800;
    font-size: 1.5rem;
    color: var(--ink);
    line-height: 1;
    letter-spacing: -0.02em;
}
.orientai-subtitle {
    font-weight: 300;
    font-size: 0.82rem;
    color: var(--violet);
    line-height: 1.3;
}
@media (max-width: 640px) {
    .orientai-header {
        flex-wrap: wrap;
        padding: 14px;
    }
}

/* ---------- 5. Jerarquía tipográfica ---------- */
h1 {
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    font-size: 2.6rem !important;
    color: var(--ink);
    margin-bottom: 0.3rem !important;
}
h2 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin-top: 2rem !important;
}
h3 {
    font-weight: 600 !important;
    color: var(--ink);
}

/* ---------- 6. Botones de navegación (Neo-Brutalistas) ---------- */
.stButton > button {
    background-color: var(--ink);
    color: var(--card);
    border: 2px solid var(--ink);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    font-weight: 700;
    padding: 0.55rem 1.4rem;
    transition: all 0.15s ease-out;
}
.stButton > button:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--ink);
}
.stButton > button:active,
.stButton > button:focus-visible {
    transform: translate(4px, 4px);
    box-shadow: 0px 0px 0px var(--ink) !important;
    outline: none !important;
}
.stButton > button:disabled {
    opacity: 0.4;
    transform: none;
    box-shadow: var(--shadow-sm);
    cursor: not-allowed;
}
.stButton > button[kind="secondary"] {
    background-color: var(--card);
    color: var(--ink);
}
.stButton > button[kind="secondary"]:hover {
    background-color: var(--lime);
}

/* ---------- 7. Inputs ---------- */
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    border-radius: 12px;
    border: 2px solid var(--ink);
    box-shadow: none !important;
    background-color: var(--card);
}
.stSlider [data-baseweb="slider"] > div {
    background-color: #d5cfc2;
}
.stSlider [data-baseweb="slider"] > div > div {
    background-color: var(--ink) !important;
}

/* ============================================================== */
/* 8. OPCIONES DE RESPUESTA — escala Likert                       */
/*                                                                */
/* BUG FIX: se usa DOBLE selector para capturar el estado         */
/* seleccionado en todos los casos:                               */
/*  A) [data-checked="true"] → atributo que Streamlit inyecta    */
/*     DESPUÉS del primer click del usuario.                      */
/*  B) :has(input:checked) → estado nativo del DOM; es el         */
/*     único que se establece desde el PRIMER render (valor por   */
/*     defecto). Sin él, la opción pre-seleccionada no muestra    */
/*     feedback visual hasta que el usuario interactúa.           */
/* ============================================================== */
div[role="radiogroup"] {
    gap: 0.8rem;
}

/* Ocultamos el círculo nativo: la "tecla física" (::before) es el
   único indicador visual de posición de cada opción. */
div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

div[role="radiogroup"] > label {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background-color: var(--card);
    border: 2px solid var(--ink);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    padding: 0.55rem 1.0rem;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.15s ease-out;
}
div[role="radiogroup"] > label:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--ink);
    background-color: var(--lime);
}

/* Estado seleccionado (doble selector: Streamlit data-attr + CSS nativo) */
div[role="radiogroup"] > label[data-checked="true"],
div[role="radiogroup"] > label:has(input:checked) {
    transform: translate(4px, 4px);
    box-shadow: 0px 0px 0px var(--ink);
    background-color: var(--violet);
}

/* ---------- 8b. Atajos de teclado ("teclas físicas") ---------- */
div[role="radiogroup"] > label::before {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-weight: 700;
    font-size: 0.85rem;
    line-height: 1;
    color: var(--card);
    background-color: var(--ink);
    border: 2px solid var(--ink);
    border-radius: 6px;
    padding: 0.25rem 0.45rem;
    min-width: 1.4rem;
    text-align: center;
    box-shadow: 1px 1px 0px var(--ink);
    flex-shrink: 0;
}
/* Colores invertidos de la tecla al seleccionar */
div[role="radiogroup"] > label[data-checked="true"]::before,
div[role="radiogroup"] > label:has(input:checked)::before {
    color: var(--ink);
    background-color: var(--card);
    box-shadow: none;
}
div[role="radiogroup"] > label:nth-of-type(1)::before { content: "1"; }
div[role="radiogroup"] > label:nth-of-type(2)::before { content: "2"; }
div[role="radiogroup"] > label:nth-of-type(3)::before { content: "3"; }
div[role="radiogroup"] > label:nth-of-type(4)::before { content: "4"; }
div[role="radiogroup"] > label:nth-of-type(5)::before { content: "5"; }

/* ---------- 9. Expanders (tarjetas de carrera) ---------- */
[data-testid="stExpander"] {
    border: 2px solid var(--ink);
    border-radius: 12px;
    background-color: var(--card);
    box-shadow: var(--shadow-sm);
    margin-bottom: 0.8rem;
}
[data-testid="stExpander"] summary {
    font-weight: 700;
    padding: 0.6rem 0.8rem;
}
[data-testid="stExpander"] summary:hover {
    background-color: var(--lime);
    border-radius: 10px;
}

/* ---------- 10. Métricas (st.metric) ---------- */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    font-weight: 700;
    color: var(--ink);
}
[data-testid="stMetricLabel"] {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    color: #6b7280;
}

/* ---------- 11. Progress bar ---------- */
.stProgress > div > div > div {
    border: 2px solid var(--ink);
    border-radius: 8px;
    background-color: var(--card);
}
.stProgress > div > div > div > div {
    background-color: var(--lime);
}

/* ---------- 12. Tarjeta de recomendación ---------- */
.recom-card {
    border: 2px solid var(--ink);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1.1rem;
    background-color: var(--card);
    box-shadow: var(--shadow-sm);
    transition: all 0.15s ease-out;
}
.recom-card:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--ink);
}
.recom-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--ink);
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
    color: var(--ink);
    text-align: right;
}

/* ---------- 13. Sidebar ---------- */
[data-testid="stSidebar"] {
    background-color: var(--card);
    border-right: 2px solid var(--ink);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 1.1rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ---------- 14. Divider ---------- */
hr {
    border-top: 2px solid var(--ink) !important;
    opacity: 0.12;
    margin: 1.5rem 0 !important;
}
</style>
"""


def inject_css() -> None:
    """Inyecta el bloque CSS en la página actual.

    Debe llamarse UNA sola vez por sesión, idealmente justo después
    de `st.set_page_config(...)` y antes de renderizar cualquier
    contenido visible.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
