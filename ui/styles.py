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
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

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

/* ---------- 3. Ocultar marca Streamlit + matar espacio muerto superior ---------- */
#MainMenu      { visibility: hidden; }
footer         { visibility: hidden; }
/* CLAVE (bug del espacio muerto): el header se ocultaba con visibility:hidden,
   pero así SEGUÍA reservando su altura -> ése era el hueco que empujaba todo
   hacia abajo. Con display:none lo sacamos del flujo del layout por completo.
   Lo matamos por TAG (`header`) Y por testid: el nombre del data-testid cambia
   entre versiones de Streamlit, así que cubrimos ambos para que sea robusto. */
header,
[data-testid="stHeader"]       { display: none !important; }
[data-testid="stToolbar"]      { visibility: hidden; }
[data-testid="stDecoration"]   { visibility: hidden; }
[data-testid="stStatusWidget"] { visibility: hidden; }

/* El contenedor central de Streamlit trae un padding-top enorme (~6rem) por
   defecto: lo recortamos a 1rem y anulamos cualquier margin-top heredado para
   que el contenido quede pegado al borde superior. */
.block-container {
    padding-top: 1rem !important;
    margin-top: 0 !important;
}

/* ---------- 4. Header / Navbar ORIENTAI ---------- */
.orientai-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 12px 20px;   /* logo pegado al borde superior (~12px) */
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
    font-weight: 700;
    font-size: 1.4rem;
    color: var(--ink);
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
    /* Excluimos background-color de la transición para evitar el flash
       lime→violet al seleccionar una opción. */
    transition: transform 0.15s ease-out, box-shadow 0.15s ease-out;
}
/* Hover solo cuando NO está seleccionado, para no solapar con violet */
div[role="radiogroup"] > label:hover:not([data-checked="true"]):not(:has(input:checked)) {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px var(--ink);
    background-color: var(--lime);
}
/* Al presionar (active) va directo a violet sin pasar por lime */
div[role="radiogroup"] > label:active {
    transform: translate(4px, 4px);
    box-shadow: 0px 0px 0px var(--ink);
    background-color: var(--violet);
}

/* Estado seleccionado (doble selector: Streamlit data-attr + CSS nativo) */
div[role="radiogroup"] > label[data-checked="true"],
div[role="radiogroup"] > label:has(input:checked) {
    transform: translate(4px, 4px);
    box-shadow: 0px 0px 0px var(--ink);
    background-color: var(--violet);
    transition: transform 0.15s ease-out, box-shadow 0.15s ease-out;
}

/* En dispositivos táctiles el :hover "se pega" tras el tap, provocando el
   parpadeo verde→morado al seleccionar. Lo anulamos: en touch la opción pasa
   directo a violet (seleccionada) sin teñirse de lime. */
@media (hover: none) {
    div[role="radiogroup"] > label:hover {
        background-color: var(--card);
        transform: none;
        box-shadow: var(--shadow-sm);
    }
    div[role="radiogroup"] > label[data-checked="true"],
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: var(--violet);
        transform: translate(4px, 4px);
        box-shadow: 0px 0px 0px var(--ink);
    }
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
    background-color: var(--violet);
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

/* ---------- 15. Atajo de teclado (oculto en mobile) ---------- */
.keyboard-hint {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 0.3rem;
}

/* ---------- 16a. Header compacto en la vista del test (mobile) ---------- */
@media (max-width: 768px) {
    .orientai-header--quiz {
        padding: 8px 12px;
        margin-bottom: 0.5rem;
    }
    /* En mobile dejamos SOLO el logo: fuera título/subtítulo para ganar
       espacio vertical en el layout zero-scroll. */
    .orientai-header--quiz .orientai-title,
    .orientai-header--quiz .orientai-subtitle {
        display: none;
    }
    .orientai-header--quiz .orientai-logo-link svg {
        height: 32px;
    }
    /* El rect verde que resalta "AI" se desalinea en pantallas chicas:
       lo ocultamos en todos los headers para mantener el logo limpio. */
    .orientai-ai-rect {
        display: none !important;
    }
}

/* ---------- 16b. Plotly: evitar captura de scroll táctil ---------- */
[data-testid="stPlotlyChart"],
[data-testid="stPlotlyChart"] .js-plotly-plot,
[data-testid="stPlotlyChart"] .plotly {
    touch-action: pan-y !important;
}

/* ---------- 16. Mobile / Responsive ---------- */
@media (max-width: 640px) {

    /* Radios: de fila a columna */
    div[role="radiogroup"] {
        flex-direction: column !important;
        align-items: stretch !important;
    }
    /* Al apilarse, cada opción ocupa TODO el ancho: así todas miden lo
       mismo y se elimina el "efecto escalera" (ancho según el texto). */
    div[role="radiogroup"] > label {
        padding: 0.7rem 1.0rem;
        width: 100% !important;
        box-sizing: border-box;
    }

    /* Columnas Streamlit: apilar verticalmente */
    [data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }

    /* Reducir padding del bloque central */
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }

    /* Tipografía reducida */
    h1 { font-size: 2rem !important; }
    h3 { font-size: 1.15rem !important; }

    /* Tarjeta de recomendación: wrap en pantallas chicas */
    .recom-inner {
        flex-wrap: wrap !important;
        gap: 0.4rem;
    }
    .recom-pct {
        text-align: left !important;
        width: 100%;
        font-size: 1.3rem;
    }

    /* Ocultar atajos de teclado (no aplican en mobile) */
    .keyboard-hint { display: none; }
}

/* ============================================================== */
/* 17. LAYOUT DEL TEST — botonera lateral + barra inferior        */
/*                                                                */
/* El split opciones|botonera se escopa con .st-key-quiz_split:    */
/* la clase que aporta el wrapper st.container(key="quiz_split")   */
/* de app.py. Es un hook estable que NO depende de :has(), así el  */
/* layout en fila se garantiza también en mobile. El nivel de      */
/* página (zero-scroll 100dvh) sigue detectando la pantalla de     */
/* test vía :has(.orientai-header--quiz). La botonera lateral y la  */
/* barra inferior aplican en todos los anchos; el 100dvh es mobile. */
/* ============================================================== */

/* --- 17a. Contenedor PADRE (wrapper) en FILA: opciones | botonera ---
   Dentro de .st-key-quiz_split vive UN stHorizontalBlock (las 2 columnas de
   st.columns): ése es el flex-row que jamás debe apilarse, ni en mobile. */
.st-key-quiz_split [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: stretch !important;
    flex-wrap: nowrap !important;
    gap: 12px !important;
    width: 100% !important;
}
/* Columna IZQUIERDA (opciones Likert 1-5): toma todo el espacio libre. */
.st-key-quiz_split [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:first-child {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-width: 0 !important;
    width: auto !important;
    gap: 10px;
}
/* Columna DERECHA (rail X / ← / →): ancho FIJO estricto para no colapsar. */
.st-key-quiz_split [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child {
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    flex: 0 0 50px !important;
    min-width: 50px !important;
    width: 50px !important;
}
.st-key-quiz_split [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child [data-testid="stVerticalBlock"] {
    align-items: center;
    gap: 0.6rem;
}
/* Los botones tienen ancho fijo y el tooltip de `help` envuelve al <button>;
   centramos toda la cadena para que el rail quede prolijo. */
.st-key-quiz_split [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child .stButton,
.st-key-quiz_split [data-testid="stHorizontalBlock"]
        > [data-testid="stColumn"]:last-child [data-testid="stTooltipHoverTarget"] {
    display: flex !important;
    justify-content: center !important;
    width: 100%;
}

/* --- 17b. Opciones Likert del MISMO tamaño (no varían con el texto) --- */
.st-key-quiz_split div[role="radiogroup"] > label {
    min-height: 48px;
    justify-content: flex-start;
    white-space: nowrap;       /* texto en 1 línea => todas iguales */
}

/* --- 17c. Botonera lateral neo-brutalista (Salir / Atrás / Siguiente) --- */
.st-key-quiz_exit button,
.st-key-quiz_prev button,
.st-key-quiz_next button {
    display: flex !important;
    align-items: center;
    justify-content: center;
    padding: 0 !important;
    min-width: 0 !important;
    border: 2px solid var(--ink) !important;
    border-radius: 12px !important;
    box-shadow: 3px 3px 0px var(--ink) !important;
    font-size: 1.4rem;
    font-weight: 800;
    line-height: 1;
    transition: transform 0.15s ease-out, box-shadow 0.15s ease-out;
}
/* Salir (✕): 40x40, rojo de alerta, empujado lejos de la navegación. */
.st-key-quiz_exit { margin-bottom: 1.75rem; }   /* safety spacing */
.st-key-quiz_exit button {
    width: 40px; height: 40px;
    background: #ff3333 !important;
    color: var(--card) !important;
}
/* Atrás (←): 48x48, neutro. */
.st-key-quiz_prev button {
    width: 48px; height: 48px;
    background: var(--card) !important;
    color: var(--ink) !important;
}
/* Siguiente (→): 48x48, acción principal. */
.st-key-quiz_next button {
    width: 48px; height: 48px;
    background: var(--violet) !important;
    color: var(--ink) !important;
}
/* Interacción (hover/active) coherente con el sistema neo-brutalista. */
.st-key-quiz_exit button:hover,
.st-key-quiz_prev button:hover,
.st-key-quiz_next button:hover {
    transform: translate(2px, 2px);
    box-shadow: 1px 1px 0px var(--ink) !important;
}
.st-key-quiz_exit button:hover { background: #e60000 !important; }
.st-key-quiz_prev button:hover { background: var(--lime) !important; }
.st-key-quiz_exit button:active,
.st-key-quiz_prev button:active,
.st-key-quiz_next button:active {
    transform: translate(3px, 3px);
    box-shadow: 0px 0px 0px var(--ink) !important;
}
.st-key-quiz_prev button:disabled {
    opacity: 0.35;
    transform: none;
    box-shadow: 3px 3px 0px var(--ink) !important;
}

/* --- 17d. Barra de progreso FIJA al fondo de la pantalla --- */
.quiz-progress {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background: var(--paper);
    border-top: 2px solid var(--ink);
    padding: 8px 16px;
    z-index: 50;
}
.quiz-progress__label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-align: center;
    color: var(--ink);
    margin-bottom: 5px;
}
.quiz-progress__track {
    height: 10px;
    width: 100%;
    background: var(--card);
    border: 2px solid var(--ink);
    border-radius: 8px;
    overflow: hidden;
}
.quiz-progress__fill {
    height: 100%;
    background: var(--violet);
    transition: width 0.25s ease-out;
}

/* --- 17e. Zero-Scroll 100dvh — SOLO mobile (en desktop deja fluir) --- */
@media (max-width: 768px) {
    [data-testid="stMain"]:has(.orientai-header--quiz) {
        height: 100dvh;
        overflow: hidden;
    }
    [data-testid="stMainBlockContainer"]:has(.orientai-header--quiz) {
        padding-top: 0.5rem !important;
        padding-bottom: 84px !important;   /* deja sitio a la barra inferior */
    }
    /* Compactar títulos de la pregunta para que todo entre sin scroll. */
    [data-testid="stMainBlockContainer"]:has(.orientai-header--quiz) h5 {
        margin: 0 0 0.15rem 0 !important;
        font-size: 0.8rem !important;
    }
    [data-testid="stMainBlockContainer"]:has(.orientai-header--quiz) h3 {
        margin: 0.1rem 0 0.6rem 0 !important;
        font-size: 1.15rem !important;
        line-height: 1.25;
    }
    /* Apretar los gaps verticales de los bloques del test. */
    [data-testid="stMainBlockContainer"]:has(.orientai-header--quiz)
            [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    /* Opciones Likert un poco más compactas en mobile. */
    .st-key-quiz_split div[role="radiogroup"] {
        gap: 0.5rem !important;
    }
    .st-key-quiz_split div[role="radiogroup"] > label {
        min-height: 44px;
        padding: 0.45rem 0.8rem;
    }
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
