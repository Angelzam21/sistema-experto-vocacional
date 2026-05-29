"""
Header/Navbar de la marca ORIENTAI.

Inyecta el logo SVG oficial al tope del contenido de cada pantalla.
Como Streamlit no tiene un componente de navbar nativo, se usa
st.markdown con HTML inline. El SVG se lee desde disco una sola vez
gracias a @st.cache_data.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "ORIENTAI.SVG.svg"


@st.cache_data(show_spinner=False)
def _logo_svg() -> str:
    return _LOGO_PATH.read_text(encoding="utf-8")


def render_header(is_quiz: bool = False) -> None:
    """Renderiza el header con logo (link) y subtítulo ORIENTAI.

    Args:
        is_quiz: si True, agrega la clase --quiz que oculta el subtítulo
                 y reduce el padding en mobile para ganar espacio vertical.
    """
    extra_class = " orientai-header--quiz" if is_quiz else ""
    st.markdown(
        f"""<div class="orientai-header{extra_class}">
            <a href="/" class="orientai-logo-link">{_logo_svg()}</a>
            <span class="orientai-subtitle">Sistema experto para el proceso de orientación vocacional</span>
        </div>""",
        unsafe_allow_html=True,
    )
