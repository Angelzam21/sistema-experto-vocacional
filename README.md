# ORIENTAI — Sistema Experto de Orientación Vocacional

**ORIENTAI** es un sistema experto que recomienda carreras de grado a partir de los intereses del usuario, cruzando el modelo psicométrico **RIASEC (Holland)** con el estándar ocupacional internacional **O\*NET**. Diseñado para jóvenes de 17-20 años en proceso de orientación vocacional; corre íntegramente en el navegador, sin backend, sin red y sin persistir datos.

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| UI + lógica unificada | **Streamlit** (stateless, en memoria) |
| Cálculo vectorial | **NumPy** — similitud de coseno + correlación de Pearson |
| Visualización | **Plotly** — Radar Chart RIASEC |
| Tests E2E | **Playwright** (Node.js) |
| Tests de motor | `tests/test_perfiles.py` (Python estándar) |

No hay scraping, base de datos ni llamadas de red. El catálogo se genera offline a partir de la tabla O\*NET hardcodeada en `build_catalog.py`.

---

## Estructura del proyecto

```
.
├── app.py                      # State machine: BIENVENIDA → TEST → FILTROS → RESULTADOS
├── build_catalog.py            # Genera data/carreras.json (offline, determinista)
├── requirements.txt            # streamlit, numpy, plotly
├── package.json                # Playwright (tests E2E)
│
├── .streamlit/
│   └── config.toml             # Tema monocromático (paper/ink)
│
├── assets/
│   └── ORIENTAI.SVG.svg        # Logo oficial de la marca
│
├── data/
│   ├── carreras.json           # Catálogo: 75 carreras, vectores RIASEC float O*NET
│   └── preguntas.json          # 42 preguntas RIASEC + 8 preguntas filtro
│
├── engine/
│   ├── inference.py            # Vector usuario + scoring híbrido + ranking
│   └── filters.py              # 2da capa: knockout por etiqueta de aversión
│
├── ui/
│   ├── header.py               # Navbar: logo (link) + título + subtítulo
│   ├── keyboard.py             # Puente JS para atajos 1–5 + Enter
│   ├── styles.py               # CSS Neo-Brutalismo Gamificado
│   └── visualizations.py       # Radar Chart + tarjetas de recomendación
│
├── scripts/
│   ├── auditoria_onet.py       # Auditoría de fidelidad de vectores vs O*NET
│   └── montecarlo.py           # Simulación 500×3 escenarios + calibración
│
└── tests/
    ├── test_perfiles.py        # 10 tests del pipeline con perfiles sintéticos
    └── visual.spec.js          # Tests Playwright de capturas de pantalla
```

---

## Instalación y uso

```bash
# Instalar dependencias Python
pip install -r requirements.txt

# Correr la app (el CLI de Streamlit puede no estar en PATH)
python -m streamlit run app.py
# → http://localhost:8501

# Regenerar catálogo desde la tabla O*NET
python build_catalog.py
python build_catalog.py --dry-run   # valida sin escribir

# Correr tests del motor
python tests/test_perfiles.py

# Tests E2E (requiere npm install primero)
npm install
npm run test:e2e
```

---

## Motor lógico: modelo Holland (RIASEC) + O\*NET

### El modelo RIASEC

Holland (1959) propone que los intereses vocacionales se agrupan en 6 dimensiones:

| Dimensión | Foco |
|---|---|
| **R** — Realista | Tareas físicas, mecánicas, técnicas |
| **I** — Investigador | Análisis, ciencia, abstracción |
| **A** — Artístico | Creatividad, expresión, estética |
| **S** — Social | Ayudar, enseñar, vincularse |
| **E** — Emprendedor | Liderar, persuadir, vender |
| **C** — Convencional | Orden, datos, normas |

El test RIASEC consiste en **42 preguntas** (7 por dimensión), adaptadas del *O\*NET Interest Profiler* (dominio público, U.S. Department of Labor) con localización para Argentina. Escala Likert 1 ("Lo detestaría") a 5 ("Me encantaría").

### Construcción del vector de usuario

El sistema promedia las respuestas por dimensión para obtener un vector de 6 componentes en `[1.0, 5.0]`:

```
V_usuario = { R: 4.2, I: 2.1, A: 1.5, S: 4.8, E: 3.0, C: 2.5 }
```

### Vectores de carrera (O\*NET, float de alta resolución)

Cada carrera del catálogo se mapea a un código SOC de O\*NET. Los valores de interés O\*NET (escala 1-7) se reescalan a 1-5 **sin redondear** (float):

```
riasec_carrera[d] = 1 + (onet_valor[d] − 1) / 6 × 4
```

El paso a float fue una corrección crítica: la versión anterior redondeaba a entero, colapsando 16 carreras en 7 vectores idénticos que producían "carreras imán" y "carreras huérfanas" por artefacto de orden de lista.

### Scoring híbrido (Coseno + Pearson)

El motor usa **dos métricas complementarias**:

- **Similitud de coseno** (sobre vectores 1-5 sin centrar): alineación *direccional* — mide si usuario y carrera apuntan hacia el mismo lado, con sensibilidad a la intensidad del interés.
- **Correlación de Pearson** (coseno sobre vectores centrados en su media): similitud de *forma* del perfil — invariante al sesgo de quien responde "alto en todo" o "bajo en todo".

```python
score = 0.4 × coseno + 0.6 × pearson   # PESO_COSENO = 0.4
afinidad_pct = round(100 × max(0, score))
```

El peso **0.4/0.6** fue calibrado mediante simulación Monte Carlo (ver QA): el coseno sobre vectores en el ortante positivo 1-5 está comprimido (~0.99) y aporta poca discriminación; el óptimo es Pearson-dominante.

**Desempate neutral:** a igual score, se desempata por Pearson descendente y luego `id` alfabético. Elimina el sesgo por orden de catálogo de la versión anterior.

**Guarda de varianza nula:** si el usuario responde exactamente igual en todas las preguntas (todo-3, todo-5, etc.), su perfil no es informativo → `afinidad_pct = 0` para todas y la app avisa.

### 2da capa: filtros de aversión (knockout)

La afinidad de intereses no captura los *deal-breakers*. Esta capa los modela como reglas de exclusión explícitas:

Cada carrera lleva **etiquetas** (`contacto_pacientes`, `programacion`, `matematica_intensa`, `trabajo_fisico`, `exposicion_publica`, `expresion_artistica`). Las 6 preguntas filtro corresponden una a una. Si el usuario responde **≤ 2** ("No me gustaría" / "Lo detestaría"), esa etiqueta queda **vetada** y todas las carreras con esa etiqueta se eliminan del ranking *antes* de calcular afinidad.

> Ejemplo: perfil I/C alto que veta `contacto_pacientes` → Medicina y Odontología no aparecen en resultados, aunque su perfil de intereses se les parezca.

Salvaguarda: si los vetos descartan el catálogo completo, la app muestra el ranking completo con advertencia en lugar de una pantalla vacía.

---

## Arquitectura de UI: Neo-Brutalismo Gamificado

### Paleta ORIENTAI

```css
--ink:    #111111   /* bordes, sombras, texto */
--paper:  #f6f1e7   /* fondo principal (tono cálido tipo papel) */
--card:   #fffdf8   /* fondo de tarjetas e inputs */
--violet: #c4b5fd   /* acento primario (seleccionado / subtítulo) */
--lime:   #c6ff4d   /* acento secundario (hover) */
```

### Principios visuales

- **Neo-Brutalismo:** bordes 2px sólidos `#111111`, sombra `4px 4px 0px #111111`, sin gradientes decorativos. Los elementos "se presionan" (`translate 4px 4px`, sombra a 0) al ser seleccionados, simulando teclas físicas.
- **Fondo "papel técnico":** `--paper` en `body` + patrón de puntos con `radial-gradient` (1px cada 22px), aporta textura de datos sin distraer.
- **Gamificación por hardware:** cada opción Likert tiene una "tecla física" (badge monospace `::before`) con el número de atajo (1-5). El CSS usa doble selector (`[data-checked="true"]` + `:has(input:checked)`) para garantizar feedback visual en el primer render.

### Navegación por teclado

`ui/keyboard.py` inyecta un puente JavaScript (un solo `keydown` listener, con cleanup entre reruns) que conecta las teclas físicas con la UI de Streamlit:

- **1–5** seleccionan la opción Likert correspondiente.
- **Enter** hace click en el botón primario de la pantalla (avanzar).

---

## QA: simulaciones Monte Carlo + Playwright

### Simulación Monte Carlo (`scripts/montecarlo.py`)

500 usuarios sintéticos × 3 escenarios, semilla fija (reproducible):

| Escenario | Descripción |
|---|---|
| **A — Aleatorio** | 36 respuestas uniformes en {1..5} |
| **B — Arquetípico puro** | Una dimensión al máximo, el resto bajas |
| **C — Ruido / indeciso** | Respuestas en torno al neutro 3 |

Métricas por motor × escenario: cobertura Top-1, huérfanas (carreras nunca #1), carrera imán, entropía normalizada y Gini.

**Resultados (motor actual, escenario A aleatorio, N=500):**

| Métrica | Motor previo | Motor actual |
|---|---:|---:|
| Cobertura Top-1 | 64/76 | **68/75** |
| Huérfanas | 12 | **7** |
| Imán | gastronomía 5.8% | prof. cs. exactas 7.2% |

La simulación también calibró `PESO_COSENO = 0.4` (w=0.4 maximiza cobertura y entropía) y verificó sensibilidad intra-familia: todos los pares que antes empataban exacto (por redondeo) ahora se separan con scores distintos proporcionales a la diferencia real de perfiles O\*NET.

### Tests de motor (`tests/test_perfiles.py`)

10 casos con perfiles sintéticos que verifican propiedades del pipeline:

- Perfil datos + veto pacientes → no aparece Medicina/Odontología.
- Perfiles social / artístico / realista → área esperada en Top-1.
- Vector nulo (todo-igual) → `afinidad_pct = 0` para todas.
- Veto efectivo: una carrera aparece sin veto y desaparece con él.

```bash
python tests/test_perfiles.py   # → 10/10 OK
```

### Tests E2E (`tests/visual.spec.js`)

Tests Playwright sobre Chromium que verifican capturas de pantalla de las pantallas principales (bienvenida, quiz, selección). El servidor de Streamlit se lanza automáticamente en el `webServer` de la config.

---

## Bitácora de soluciones técnicas

### 1. Paso a vectores float de alta resolución

**Problema:** la versión anterior redondeaba los valores O\*NET a enteros 1-5. Resultado: 16 de 76 carreras colapsaban en 7 grupos de vectores idénticos. El desempate era por orden de catálogo → "carreras imán" estructurales (siempre #1) y "carreras huérfanas" (nunca #1), ambos artefactos de implementación, no de los datos.

**Solución:** reescalado sin redondear en `build_catalog.py`. Distancia euclídea mínima entre cualquier par pasó de 0 a 0.346. Colisiones exactas: 16 → 0 (excepto un par documentado con el mismo código SOC).

### 2. Normalización lineal del score de afinidad (eliminación del castigo al cubo)

**Problema:** la versión anterior calculaba el score y luego lo mostraba como `(score)³`, un "castigo al cubo" que hundía los porcentajes y desalineaba el orden mostrado del % mostrado (la UI mostraba un número diferente al que determinaba el ranking).

**Solución:** `afinidad_pct = round(100 × max(0, score))` — mapeo lineal honesto sin distorsión. El score y el porcentaje mostrado son coherentes.

### 3. Fix del feedback visual del DOM (selector doble CSS)

**Problema:** Streamlit establece el atributo `data-checked="true"` en el label del radio *después del primer click del usuario*, pero no en el render inicial aunque haya un valor por defecto pre-seleccionado. Resultado: la opción pre-seleccionada (valor 3, neutro) no mostraba el fondo violeta hasta que el usuario interactuaba.

**Solución:** doble selector en el CSS:
```css
div[role="radiogroup"] > label[data-checked="true"],
div[role="radiogroup"] > label:has(input:checked) {
    background-color: var(--violet);
}
```
`:has(input:checked)` lee el estado nativo del `<input type="radio">`, que **siempre** está correcto desde el primer render. Cubre el caso que `data-checked` no alcanza.

---

## Decisiones de diseño

| Decisión | Justificación |
|---|---|
| Híbrido Coseno + Pearson, no euclidiana | Coseno: dirección/intensidad. Pearson: forma del perfil sin sesgo de magnitud. Peso calibrado por Monte Carlo. |
| 2da capa knockout explícita | La afinidad de intereses no captura deal-breakers (un perfil datos puede odiar pacientes). |
| Vectores float (no enteros) | Preserva la resolución original O\*NET; elimina colisiones y carreras imán por artefacto. |
| Stateless / `st.session_state` | Privacidad por diseño: respuestas y vector nunca tocan el disco. |
| 42 preguntas (7 por dimensión) | Banco simétrico: cada dimensión RIASEC se mide con la misma cantidad de ítems para no sesgar el vector. La resolución del vector usuario es prácticamente continua; el límite de precisión es el catálogo, no la cantidad de ítems. |
| Catálogo generado por script | Trazabilidad: cada vector RIASEC sale de un código SOC oficial de O\*NET. Reproducible con `python build_catalog.py`. |

---

## Créditos

- Banco de preguntas adaptado del **O\*NET Interest Profiler** (dominio público, U.S. Department of Labor).
- Puntajes RIASEC por ocupación: **O\*NET Interests v28.x** (onetonline.org).
- Proyecto académico — Análisis de Datos II.
