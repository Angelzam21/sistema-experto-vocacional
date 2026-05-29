"""
=================================================================
PASO 4.3 - DASHBOARD ANALÍTICO Y RESULTADOS
=================================================================
Funciones de visualización:

  - radar_chart_riasec(): grafica el perfil del usuario contra el
    perfil de una carrera en formato Radar Chart MONOCROMÁTICO
    (negro / gris) con Plotly. Sin colores festivos, sin leyendas
    flotantes intrusivas.

  - tarjeta_recomendacion(): renderiza una tarjeta tipo "card"
    para cada uno de los Top-5 resultados, con título bold grande
    y porcentaje de afinidad en tipografía monoespaciada alineado
    a la derecha. Usa HTML personalizado para sortear las
    limitaciones de st.expander.

Todo se mantiene en la paleta blanco / negro / gris definida en
config.toml y styles.py.
=================================================================
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine.inference import DIMENSIONES_RIASEC


# Etiquetas humanas para los ejes del radar (más legibles que R/I/A/S/E/C).
ETIQUETAS_RIASEC: dict[str, str] = {
    "R": "Realista",
    "I": "Investigador",
    "A": "Artístico",
    "S": "Social",
    "E": "Emprendedor",
    "C": "Convencional",
}


def radar_chart_riasec(
    vector_usuario: dict[str, float],
    vector_carrera: dict[str, int] | None = None,
    titulo: str = "Tu perfil RIASEC",
) -> go.Figure:
    """Construye un Radar Chart con uno o dos polígonos superpuestos.

    Args:
        vector_usuario: dict {R..C: float} con el perfil del usuario.
        vector_carrera: opcional, dict {R..C: int} de una carrera para
                        superponer y comparar visualmente.
        titulo: título mostrado arriba del gráfico.

    Returns:
        figura Plotly lista para `st.plotly_chart(fig, use_container_width=True)`.

    Decisiones estéticas:
      - template "plotly_white": sin grilla oscura ni fondo azulado.
      - polígono usuario: línea NEGRA + fill translúcido rgba(0,0,0,0.1).
      - polígono carrera: línea GRIS + fill aún más sutil.
      - sin leyenda flotante: se usa el título del trace en hover.
    """
    # Cerramos el polígono repitiendo el primer punto al final.
    # Plotly necesita la lista cerrada para que la línea se vea continua.
    etiquetas = [ETIQUETAS_RIASEC[d] for d in DIMENSIONES_RIASEC]
    etiquetas_cerradas = etiquetas + [etiquetas[0]]

    valores_usuario = [vector_usuario[d] for d in DIMENSIONES_RIASEC]
    valores_usuario_cerrados = valores_usuario + [valores_usuario[0]]

    fig = go.Figure()

    # ---- Trace 1: usuario ----
    fig.add_trace(go.Scatterpolar(
        r=valores_usuario_cerrados,
        theta=etiquetas_cerradas,
        fill="toself",
        name="Tu perfil",
        line=dict(color="#000000", width=2),
        fillcolor="rgba(0,0,0,0.10)",
        hovertemplate="<b>%{theta}</b><br>Tu nivel: %{r:.2f}<extra></extra>",
    ))

    # ---- Trace 2 (opcional): carrera ----
    if vector_carrera is not None:
        valores_carrera = [vector_carrera[d] for d in DIMENSIONES_RIASEC]
        valores_carrera_cerrados = valores_carrera + [valores_carrera[0]]
        fig.add_trace(go.Scatterpolar(
            r=valores_carrera_cerrados,
            theta=etiquetas_cerradas,
            fill="toself",
            name="Carrera",
            line=dict(color="#666666", width=2, dash="dot"),
            fillcolor="rgba(102,102,102,0.08)",
            hovertemplate="<b>%{theta}</b><br>Carrera: %{r}<extra></extra>",
        ))

    fig.update_layout(
        template="plotly_white",
        title=dict(
            text=titulo,
            font=dict(size=18, color="#000000", family="Inter, sans-serif"),
            x=0.0, xanchor="left",
        ),
        polar=dict(
            bgcolor="#FFFFFF",
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
                tickfont=dict(size=10, color="#999999"),
                gridcolor="#E5E5E5",
                linecolor="#E5E5E5",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="#111111", family="Inter, sans-serif"),
                gridcolor="#EAEAEA",
                linecolor="#CCCCCC",
            ),
        ),
        showlegend=vector_carrera is not None,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#111111"),
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor="#FFFFFF",
    )

    return fig


def codigo_holland(riasec: dict[str, int]) -> str:
    """Devuelve el código de Holland de una carrera (sus 3 dimensiones
    dominantes), ej. {R:5,I:4,...} -> "RIC".

    Es la forma estándar de resumir un perfil RIASEC: las 3 letras de
    mayor puntaje, en orden descendente.
    """
    top3 = sorted(DIMENSIONES_RIASEC, key=lambda d: riasec[d], reverse=True)[:3]
    return "".join(top3)


def tarjeta_recomendacion(carrera: dict, posicion: int) -> None:
    """Renderiza una tarjeta de resultado individual (Top-N).

    Layout (HTML+CSS de ui/styles.py): número de ranking a la izquierda,
    nombre + área + código Holland en el centro, % de afinidad en
    monoespaciada a la derecha. El detalle expandible muestra la
    ocupación O*NET equivalente y un radar usuario vs. carrera.
    """
    cod = codigo_holland(carrera["riasec"])
    st.markdown(
        f"""
        <div class="recom-card">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:baseline; gap:0.9rem;">
                    <span style="
                        font-family:'JetBrains Mono', monospace;
                        font-size:1.1rem; color:#999999; min-width:2rem;
                    ">#{posicion:02d}</span>
                    <div>
                        <p class="recom-title">{carrera['nombre']}</p>
                        <p class="recom-subtitle">
                            {carrera.get('area', '')}
                            &nbsp;·&nbsp; Código Holland: {cod}
                        </p>
                    </div>
                </div>
                <div class="recom-pct">{carrera['afinidad_pct']}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detalle expandible. El CSS nativo del expander ya está sobrescrito
    # para que se vea como un panel limpio.
    with st.expander("Ver detalle"):
        st.markdown(
            f"**Equivalente ocupacional O\\*NET:** {carrera.get('onet_titulo', '—')} "
            f"(`{carrera.get('onet_soc', '—')}`)"
        )
        st.markdown(
            "El vector RIASEC de esta carrera se deriva de esa ocupación del "
            "estándar O\\*NET. Abajo se compara con tu perfil:"
        )

        # Mini-radar comparativo usuario vs. carrera.
        if "vector_usuario" in st.session_state:
            fig = radar_chart_riasec(
                st.session_state["vector_usuario"],
                carrera["riasec"],
                titulo=f"Tu perfil vs. {carrera['nombre']}",
            )
            st.plotly_chart(fig, use_container_width=True)
