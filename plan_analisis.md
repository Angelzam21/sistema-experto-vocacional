# PLAN TÉCNICO: SISTEMA EXPERTO VOCACIONAL

Sistema experto que recomienda **carreras de grado** a partir de los intereses del usuario, cruzando el modelo psicométrico **RIASEC (Holland)** con el estándar ocupacional **O\*NET**.

**Objetivo de arquitectura:** MVP ágil, *stateless*, ejecutado íntegramente en memoria con Streamlit. Sin scraping, sin backend, sin base de datos, sin red. Prioriza velocidad, simplicidad y privacidad por diseño.

> **Nota de alcance:** una versión anterior cruzaba los intereses con la oferta académica de universidades públicas (scraping + filtros de zona/modalidad). Ese módulo fue **eliminado**. El sistema ahora se concentra en lo esencial: la lista de carreras y su perfil de Holland. La recomendación de *dónde* cursar queda fuera de alcance.

---

## Fase 1: Base de conocimiento (catálogo O\*NET)

La base de conocimiento es un archivo estático `data/carreras.json` generado **offline y de forma determinista** por `build_catalog.py` (no hay scraping ni internet).

### Paso 1.1 — Lista maestra de carreras
Catálogo curado de ~76 carreras de grado/pregrado, balanceado a través de las 6 dimensiones RIASEC. Cada carrera define: `id`, `nombre`, `area` (agrupador), `onet_soc`, `onet_titulo` y `etiquetas` (ver Fase 3).

### Paso 1.2 — Cruce con O\*NET (vector RIASEC)
Cada carrera se vincula a la ocupación O\*NET de mayor afinidad mediante su **código SOC** (ej. `Contador Público → 13-2011.00 Accountants and Auditors`). De esa ocupación se toma el perfil de intereses O\*NET (escala 0-7) y se reescala linealmente a la escala interna 1-5:

```
escala_15 = round(1 + (valor_07 / 7) * 4)
```

`build_catalog.py` valida el contrato de datos (sin IDs duplicados, RIASEC completo en rango 1-5, etiquetas conocidas) antes de escribir el JSON.

---

## Fase 2: Banco de preguntas y motor de inferencia

### Paso 2.1 — Banco de preguntas (`data/preguntas.json`)
- **36 preguntas RIASEC** (6 por dimensión), adaptadas del *O\*NET Interest Profiler* (dominio público) con localización para Argentina. Escala Likert 1 (Lo detestaría) … 5 (Me encantaría).
- **6 preguntas filtro** (segunda capa, ver Fase 3).

### Paso 2.2 — Vector de perfil de usuario
Promedio (ponderado) por dimensión RIASEC → vector de 6 dimensiones. Ej.: `[R 4.2, I 2.1, A 1.5, S 4.8, E 3.0, C 2.5]`.

### Paso 2.3 — Scoring híbrido (Coseno + Pearson)
Emparejamiento por **score híbrido** `0.4·coseno + 0.6·pearson`:
- **Coseno** (escala 1-5): alineación direccional (dirección + intensidad).
- **Pearson** (coseno centrado en la media): similitud de forma del perfil, invariante al sesgo de magnitud.

El peso fue **calibrado por Monte Carlo** (Pearson-dominante: el coseno sobre vectores 1-5 está comprimido). El score `[-1,1]` se mapea a `% = 100·max(0, score)` (sin "castigo al cubo") y se ordena DESC con desempate neutral (Pearson, luego id). Los vectores de carrera son **float de alta resolución** (O*NET 1-7 reescalado a 1-5 sin redondear), lo que elimina los empates por colisión que producían carreras imán/huérfanas.

---

## Fase 3: Segunda capa — Filtros de aversión (knockout)

La afinidad de intereses no captura los *deal-breakers*. Esta capa los modela como reglas de exclusión:

- Cada carrera lleva 0..N **etiquetas**: `contacto_pacientes`, `programacion`, `matematica_intensa`, `trabajo_fisico`, `exposicion_publica`, `expresion_artistica`.
- Cada **pregunta filtro** corresponde a una etiqueta.
- Si el usuario responde **≤ 2** ("no me gustaría" / "lo detestaría"), la etiqueta queda **vetada** y todas las carreras que la tengan se eliminan del ranking **antes** del cálculo de afinidad.

Ejemplo: perfil con datos altos (I/C) que veta `contacto_pacientes` → Medicina y Odontología se descartan aunque su perfil de intereses se les parezca.

Salvaguarda: si los vetos descartan el catálogo completo, la app muestra igualmente el ranking completo con una advertencia.

---

## Fase 4: Arquitectura unificada y UI (Streamlit)

Streamlit actúa como motor algorítmico y capa de presentación.

- **Catálogo en memoria:** `@st.cache_data` lee los JSON una sola vez por proceso.
- **State machine:** `BIENVENIDA → TEST (36) → FILTROS (6) → RESULTADOS`, manejada con `st.session_state`.
- **Privacidad:** respuestas y vector viven sólo en la sesión efímera; nada se persiste.
- **UI monocromática:** tema `config.toml` + CSS personalizado (`ui/styles.py`); Radar Chart Plotly en blanco/negro; tarjetas de recomendación con nombre, área, código Holland y % de afinidad, más un radar comparativo usuario vs. carrera.

---

## Fase 5: Validación

`tests/test_perfiles.py` corre el pipeline completo con perfiles sintéticos y verifica que:
- un perfil de datos que veta pacientes no reciba carreras clínicas;
- perfiles social / artístico / realista devuelvan el área esperada arriba;
- el vector nulo (responder todo igual) dé afinidad 0;
- el veto cambie efectivamente el resultado (Medicina aparece sin veto y desaparece con él).
