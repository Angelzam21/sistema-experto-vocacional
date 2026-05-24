# Sistema Experto Vocacional Basado en Datos

Sistema experto que recomienda carreras universitarias a estudiantes argentinos cruzando el modelo psicométrico **RIASEC (Holland)** —en su variante O\*NET— con la **oferta académica real** de las universidades públicas nacionales.

Implementación del plan técnico definido en [`plan_analisis.md`](plan_analisis.md).

---

## Stack

- **Python 3.10+**
- **Streamlit** — UI + motor algorítmico unificado, stateless en memoria.
- **NumPy** — cálculo vectorial (similitud de coseno).
- **Plotly** — Radar Chart monocromático.
- **BeautifulSoup + Requests** — scraping de oferta académica (Fase 1).
- **RapidFuzz** — normalización por fuzzy matching.

---

## Estructura del proyecto

```
.
├── app.py                          # App Streamlit (Fase 3)
├── build_dataset.py                # Orquestador ETL (Fase 1)
├── requirements.txt
├── plan_analisis.md                # Plan técnico fuente
│
├── .streamlit/
│   └── config.toml                 # Tema monocromático (Fase 4.1)
│
├── data/
│   ├── carreras_argentina.json     # Dataset maestro (salida Fase 1)
│   └── preguntas_riasec_ar.json    # Banco de preguntas (Fase 2.0)
│
├── etl/
│   ├── scraper.py                  # Fase 1.1 - scraping universidades
│   ├── normalizer.py               # Fase 1.2 - fuzzy matching
│   └── onet_mapper.py              # Fase 1.3 - enriquecimiento RIASEC
│
├── engine/
│   ├── inference.py                # Fase 2.1 + 2.2 - vector + coseno
│   └── filters.py                  # Fase 3.2 - filtros duros
│
└── ui/
    ├── styles.py                   # Fase 4.2 - CSS clean UI
    └── visualizations.py           # Fase 4.3 - radar + tarjetas
```

---

## Instalación

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## Uso

### Correr la app web

```bash
streamlit run app.py
```

Abre `http://localhost:8501`. El flujo es:

1. **Bienvenida** → presentación y CTA.
2. **Filtros duros** → zona geográfica + modalidad.
3. **Test** → 36 preguntas Likert (1-5), una por pantalla.
4. **Resultados** → métricas RIASEC, Radar Chart y Top-5 con detalle por carrera.

### Re-generar el dataset maestro (opcional)

El JSON `data/carreras_argentina.json` ya viene incluido. Si querés reconstruirlo desde cero (por ejemplo si actualizás `etl/onet_mapper.py` o las fuentes de scraping):

```bash
python build_dataset.py            # pipeline completo
python build_dataset.py --dry-run  # corre sin escribir disco
python build_dataset.py --verify   # solo valida el JSON existente
```

Antes de sobrescribir, `build_dataset.py` crea un backup `.bak` por seguridad.

---

## Decisiones de diseño relevantes

| Decisión | Justificación |
|---|---|
| **Similitud de coseno (no euclidiana)** | El coseno mide *orientación* del perfil, no magnitud. Dos usuarios con perfiles proporcionales reciben la misma recomendación, eliminando el sesgo del que responde "alto en todo". |
| **Escala 1-5 (no 0-7 cruda de O\*NET)** | Coherencia con la escala Likert que ve el usuario y simplificación visual. La re-escala lineal preserva el orden. |
| **Stateless / `st.session_state`** | Privacidad por diseño. El vector RIASEC nunca toca el disco ni se loguea. |
| **`@st.cache_data` en cargadores JSON** | Lectura única del disco por proceso; las re-ejecuciones del script (cada click) reusan la memoria. |
| **Filtros duros antes del coseno** | No tiene sentido calcular afinidad con carreras a las que el usuario no puede acceder; además ahorra cómputo. |
| **CSS personalizado + `plotly_white`** | Anular la estética genérica de Streamlit para proyectar una imagen analítica, premium y consistente. |

---

## Modelo RIASEC

Las 6 dimensiones de Holland:

| Sigla | Nombre | Foco |
|---|---|---|
| **R** | Realista | Tareas físicas, mecánicas, técnicas |
| **I** | Investigador | Análisis, ciencia, abstracción |
| **A** | Artístico | Creatividad, expresión, estética |
| **S** | Social | Ayudar, enseñar, vincularse |
| **E** | Emprendedor | Liderar, persuadir, vender |
| **C** | Convencional | Orden, datos, normas |

---

## Licencia y créditos

- Banco de preguntas adaptado del **O\*NET Interest Profiler** (dominio público, U.S. Department of Labor).
- Puntajes RIASEC por ocupación derivados de **O\*NET Interests v28.x**.
- Proyecto académico — Análisis de Datos II.
