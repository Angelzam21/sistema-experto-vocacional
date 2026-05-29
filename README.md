# Sistema Experto Vocacional

Sistema experto que recomienda **carreras de grado** a partir de los intereses del usuario, cruzando el modelo psicométrico **RIASEC (Holland)** —en su variante **O\*NET**— con un catálogo de carreras.

El sistema trabaja en **dos capas**:

1. **Afinidad de intereses (RIASEC):** un test de 36 preguntas construye el perfil del usuario en 6 dimensiones y lo compara, por similitud de coseno, con el vector de cada carrera.
2. **Filtros de aversión (knockout):** 6 preguntas adicionales descartan carreras cuyo trabajo diario el usuario rechaza de plano (atender pacientes, programar, vender, etc.), aunque su perfil de intereses se les parezca.

> Ejemplo: alguien a quien "le encantan los datos" pero que **no quiere atender pacientes** nunca recibirá Medicina ni Odontología, aun cuando su perfil tenga afinidad con ellas.

---

## Stack

- **Python 3.10+**
- **Streamlit** — UI + motor algorítmico unificado, stateless en memoria.
- **NumPy** — cálculo vectorial (similitud de coseno).
- **Plotly** — Radar Chart monocromático.

No hay scraping, base de datos ni llamadas de red: todo corre offline y en memoria.

---

## Estructura del proyecto

```
.
├── app.py                      # App Streamlit (flujo bienvenida → test → filtros → resultados)
├── build_catalog.py            # Genera data/carreras.json desde la tabla O*NET (offline, determinista)
├── requirements.txt
├── plan_analisis.md            # Plan técnico
│
├── .streamlit/
│   └── config.toml             # Tema monocromático
│
├── data/
│   ├── carreras.json           # Catálogo: id, nombre, área, O*NET, riasec, etiquetas
│   └── preguntas.json          # 36 preguntas RIASEC + 6 preguntas filtro
│
├── engine/
│   ├── inference.py            # Vector de usuario + similitud de coseno + ranking
│   └── filters.py              # 2da capa: filtros de aversión (knockout por etiqueta)
│
├── ui/
│   ├── styles.py               # CSS clean UI monocromática
│   └── visualizations.py       # Radar Chart + tarjetas de recomendación
│
└── tests/
    └── test_perfiles.py        # Tests del pipeline con perfiles sintéticos
```

---

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/Mac  (.venv\Scripts\activate en Windows)
pip install -r requirements.txt
```

---

## Uso

### Correr la app web

```bash
streamlit run app.py
# o, si el CLI no está en PATH:
python -m streamlit run app.py
```

Abre `http://localhost:8501`. El flujo es:

1. **Bienvenida** → presentación y CTA.
2. **Test** → 36 preguntas Likert (1-5), una por pantalla → construye el vector RIASEC.
3. **Filtros** → 6 preguntas de aversión → descartan carreras vetadas.
4. **Resultados** → métricas RIASEC, Radar Chart y ranking de carreras (Top-5 + ranking completo).

### Regenerar el catálogo

`data/carreras.json` ya viene incluido. Para reconstruirlo desde la tabla O\*NET (por ejemplo, si corregís un valor de interés o agregás carreras en `build_catalog.py`):

```bash
python build_catalog.py            # genera data/carreras.json
python build_catalog.py --dry-run  # construye y valida sin escribir
```

### Correr los tests

```bash
python tests/test_perfiles.py      # reporte legible
pytest tests/test_perfiles.py      # como suite de pytest (opcional)
```

---

## Cómo funciona el motor

### 1ra capa — Afinidad RIASEC (coseno)

El test calcula el promedio del usuario por dimensión y lo compara con el vector de cada carrera. Se usa **similitud de coseno sobre vectores centrados** (equivalente a la correlación de Pearson): mide la *orientación* del perfil, no su magnitud, así que dos personas con el mismo patrón de intereses pero distinta intensidad reciben la misma recomendación. La correlación positiva se eleva al cubo para aumentar el contraste entre carreras muy y poco afines.

### 2da capa — Filtros de aversión (knockout)

Cada carrera lleva 0..N **etiquetas** (`contacto_pacientes`, `programacion`, `matematica_intensa`, `trabajo_fisico`, `exposicion_publica`, `expresion_artistica`). Cada pregunta filtro corresponde a una etiqueta. Si el usuario responde **≤ 2** ("no me gustaría" / "lo detestaría"), esa etiqueta queda **vetada** y todas las carreras que la tengan se eliminan del ranking antes de calcular afinidad.

---

## Modelo RIASEC

| Sigla | Nombre | Foco |
|---|---|---|
| **R** | Realista | Tareas físicas, mecánicas, técnicas |
| **I** | Investigador | Análisis, ciencia, abstracción |
| **A** | Artístico | Creatividad, expresión, estética |
| **S** | Social | Ayudar, enseñar, vincularse |
| **E** | Emprendedor | Liderar, persuadir, vender |
| **C** | Convencional | Orden, datos, normas |

---

## Decisiones de diseño

| Decisión | Justificación |
|---|---|
| **Coseno centrado (Pearson), no euclidiana** | Mide orientación del perfil, no magnitud; elimina el sesgo del que responde "alto en todo". |
| **Segunda capa de filtros como knockout** | La afinidad de intereses no captura los "deal-breakers"; un veto explícito evita recomendar carreras que el usuario jamás aceptaría. |
| **Escala 1-5 (no 0-7 cruda de O\*NET)** | Coherencia con la escala Likert que ve el usuario; la re-escala lineal preserva el orden. |
| **Catálogo generado por script** | Trazabilidad (cada vector RIASEC sale de un código SOC de O\*NET) y reproducibilidad. |
| **Stateless / `st.session_state`** | Privacidad por diseño: las respuestas nunca tocan el disco. |

---

## Licencia y créditos

- Banco de preguntas adaptado del **O\*NET Interest Profiler** (dominio público, U.S. Department of Labor).
- Puntajes RIASEC por ocupación derivados de **O\*NET Interests v28.x**.
- Proyecto académico — Análisis de Datos II.
