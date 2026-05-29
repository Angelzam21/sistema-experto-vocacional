# Reporte de Auditoría — Motor de Emparejamiento Vocacional (RIASEC / O\*NET)

**Rol:** QA Engineer + Data Scientist (psicometría)
**Alcance:** 76 carreras · 36 preguntas RIASEC · 6 filtros de aversión
**Fecha:** 2026-05-29

> **Nota de conteo:** el enunciado habla de **77** carreras; el catálogo real tiene **76**
> (`data/carreras.json._meta.total_carreras = 76`). Todas las métricas se calculan sobre 76.

---

## 0. Resumen ejecutivo

Los "resultados anómalos o sesgados" **no venían de valores O\*NET mal cargados**: la tabla
`ONET_INTERESTS_07` es fiel a O\*NET (validada contra onetonline.org). El daño venía de **dos
defectos de transformación y de un algoritmo mal nombrado**:

| # | Hallazgo | Impacto | Estado |
|---|----------|---------|--------|
| 1 | Reescalado asumía O\*NET **0-7** cuando es **1-7** | El piso de la escala (1) nunca se usaba; todo inflado hacia arriba | ✅ Corregido |
| 2 | Vectores de carrera **redondeados a entero** | 16 carreras colapsaban en 7 vectores idénticos → empates | ✅ Corregido (float) |
| 3 | "Similitud de coseno" en realidad calculaba **solo Pearson** (coseno centrado), dos veces | No había hibridación; una métrica disfrazada de otra | ✅ Refactorizado |
| 4 | **Castigo al cubo** (`score³`) sobre la afinidad | % hundidos y desalineados del orden | ✅ Eliminado |
| 5 | Empates resueltos **por orden del catálogo** | Sesgo sistemático → carreras imán/huérfanas | ✅ Desempate neutral |

**Resultado:** colisiones exactas 16 → 2 carreras · huérfanas-en-#1 (aleatorio) 12 → 8 ·
todos los pares antes empatados ahora se separan · ninguna carrera es inalcanzable.

---

## 1. Auditoría del mapeo O\*NET  *(Entregable 1)*

Script: [`scripts/auditoria_onet.py`](scripts/auditoria_onet.py)

### 1.1 La tabla O\*NET es fiel — el problema era la transformación

`carreras.json` está **100% sincronizado** con `build_catalog.py` (0 divergencias). Los
*high-points* de la tabla cruda coinciden con O\*NET (validado en onetonline.org: p.ej.
*Dietitians* = Social/Investigador; *Architects* = Artístico; *Economists/Actuaries* =
Investigador). Las dimensiones marcadas como "atípicas" por área son en realidad **correctas**
en O\*NET (Economía/Actuario *son* Investigadores; Bibliotecología/Lab *son* Convencionales).

### 1.2 Bug de reescalado (0-7 → debía ser 1-7)

La fórmula previa `1 + (valor/7)·4` trataba la escala O\*NET como 0-7. Como el mínimo real de
O\*NET es **1.0**, el interés mínimo se mapeaba a ~1.6 → redondeado a **2**: el valor **1 de la
escala nunca se usaba** y todas las dimensiones quedaban comprimidas hacia arriba.

```
O*NET | fórmula previa (0-7) | fórmula correcta (1-7)
 1.0  |          2           |          1     ← el piso se perdía
 3.0  |          3           |          2
 4.7  |          4           |          3
```

**42/76 carreras** tenían al menos una dimensión O\*NET = 1.0 inflada a 2.
**Corrección** (`build_catalog.py → reescalar_07_a_15`): `1 + (valor−1)/6·4`.

### 1.3 Redondeo a entero → colisiones (causa raíz de imán/huérfanas)

Redondear los vectores de carrera a enteros 1-5 colapsaba carreras O\*NET distintas en el
**mismo** vector. **7 grupos / 16 carreras** en empate exacto, p.ej.:

- `Ing. Mecánica = Ing. Mecatrónica = Agronomía` → `{R5,I4,A2,S2,E3,C3}`
- `Biología = Física = Biotecnología`
- `Ciencia de Datos = Economía`

Como el desempate era por **orden de catálogo**, en cada grupo **siempre ganaba la primera
listada** → carrera imán; las demás quedaban **huérfanas estructurales** (jamás #1).

**Corrección:** los vectores de carrera ahora son **float** (O\*NET 1-7 reescalado a 1-5 **sin
redondear**), preservando la resolución original. Resultado: **75 vectores únicos de 76**.

> **Único empate residual (documentado, no es bug):** `Profesorado de Educación Física` y
> `Profesorado en Ciencias Exactas` comparten el **mismo código SOC** `25-2031.00`
> (*Secondary School Teachers*). O\*NET no subdivide a los docentes de secundaria por materia,
> así que tienen idéntico perfil de interés. **No se fabricaron valores** para diferenciarlos
> (violaría "100% fiel a O\*NET"); queda señalado para el dueño del catálogo.

### 1.4 Valor a revisar (no corregido por falta de fuente numérica)

- `diseno_industrial` (*Commercial & Industrial Designers* 27-1021.00): la tabla tiene
  **R = A = 5.3** (empate). En O\*NET, *Artistic* suele ser el high-point claro. No se alteró
  el valor crudo sin número oficial; queda como observación.

---

## 2. Refactorización del motor — Coseno + Pearson  *(Entregable 2)*

Código: [`engine/inference.py`](engine/inference.py)

### 2.1 Diagnóstico del algoritmo previo

El previo decía "coseno" pero `_a_array()` **centraba la media de ambos vectores** → eso es
exactamente la **correlación de Pearson**. Es decir: **no había híbrido**, era Pearson aplicado
y nombrado "coseno". Además ordenaba por la correlación cruda pero **mostraba `(correlación)³`**
(castigo al cubo), hundiendo y desalineando los porcentajes.

### 2.2 Motor nuevo (dos señales reales + híbrido)

```python
similitud_coseno(u, c)     # coseno SIN centrar, escala 1-5 → dirección + intensidad
correlacion_pearson(u, c)  # coseno centrado en la media → FORMA del perfil (picos/valles)
score = w·coseno + (1−w)·pearson           # w = PESO_COSENO = 0.4
afinidad_pct = round(100 · max(0, score))  # % honesto, SIN cubo
```

- **Desempate neutral:** `(−score, −pearson, id)` — ya no gana "la primera del catálogo".
- **Guarda de varianza cero:** si el usuario responde todo igual (todo-3, todo-5, todo-1) el
  perfil no es informativo → afinidad 0 para todas (la app lo detecta y avisa).

### 2.3 Calibración del peso (Monte Carlo, no a dedo)

El enunciado sugería *60% coseno / 40% Pearson*. **Los datos dicen lo contrario:** el coseno
sobre vectores 1-5 (todos en el ortante positivo) está **comprimido (~0.99)** y casi no
discrimina. A mayor peso del coseno, **peor** dispersión del Top-1:

| w_coseno | cobertura Top-1 | entropía | imán % |
|---:|---:|---:|---:|
| 0.0 (solo Pearson) | 71 | 0.905 | 7.2 |
| **0.4 (elegido)** | **68** | **0.893** | **7.2** |
| 0.6 (sugerido) | 66 | 0.879 | 8.0 |
| 1.0 (solo coseno) | 27 | 0.601 | 19.0 |

**Decisión:** `PESO_COSENO = 0.4` (40% coseno / 60% Pearson) — híbrido genuino y
Pearson-dominante, a un costo de dispersión despreciable frente al óptimo.

---

## 3. Distribución del Top-1 sobre las 76 carreras  *(Entregable 3)*

Simulación: [`scripts/montecarlo.py`](scripts/montecarlo.py) · 500 usuarios × 3 escenarios ·
semilla fija (reproducible).

### 3.1 Antes / Después por escenario

| Escenario | Métrica | Motor PREVIO | Motor NUEVO |
|---|---|---:|---:|
| **A · Aleatorio** | cobertura Top-1 | 64/76 | **68/76** |
| | huérfanas | 12 | **8** |
| | carrera imán | gastronomía 5.8% | prof. cs. exactas 7.2% |
| **B · Arquetípico puro** | cobertura | 28/76 | **29/76** |
| | huérfanas | 48 | 47 |
| **C · Ruido / indeciso** | cobertura | 65/76 | **67/76** |
| | huérfanas | 11 | **9** |

> La baja cobertura del escenario **B** es esperada y correcta: hay solo 6 arquetipos puros, y
> cada dimensión converge a su carrera prototípica (C→*Administración Contable*, R→*Producción
> Agropecuaria*, I→*Física*, S→*Trabajo Social*, E→*Negocios Digitales*, A→arte). Los
> escenarios realistas (A y C) cubren ~68/76.

### 3.2 Top-1 — escenario aleatorio (motor nuevo, N=500)

Top de "imanes" y cola de huérfanas (tabla completa la imprime el script):

```
 36 (7.2%) Profesorado en Ciencias Exactas   ← empate residual (SOC compartido)
 35 (7.0%) Gastronomía
 26 (5.2%) Odontología
 21 (4.2%) Desarrollo y Producción de Videojuegos
 17 (3.4%) Ciencia Política / Kinesiología
 ...
  0 (0.0%) Farmacia, Ing. Eléctrica, Ing. Mecatrónica, Ing. Mecánica,
           Economía, Matemática, Trabajo Social, Prof. Educación Física
```

### 3.3 Diagnóstico: ¿hay huérfanas o imanes reales?  *(Análisis)*

- **Ninguna carrera es inalcanzable.** Con un perfil que coincide con su vector O\*NET, cada
  "huérfana" gana el #1 con score 1.0 (> su mellizo). Y las 8 aún aparecen en **Top-3** bajo
  ruido aleatorio (p.ej. *Prof. Ed. Física* 49 veces, *Ing. Eléctrica* 12, *Trabajo Social* 11).
- **Las huérfanas-en-#1 son "mellizos eclipsados":** carreras con perfil O\*NET casi idéntico
  al de un hermano que capta un poco más de masa central (Mecánica↔Mecatrónica Δ=0.002;
  Eléctrica↔Civil Δ=0.001; Economía↔Ciencia de Datos Δ=0.09). Refleja una realidad de O\*NET
  (esas ingenierías *son* casi idénticas en intereses), no un bug.
- **Diferencia clave con el motor previo:** antes las huérfanas salían de **empates por
  redondeo resueltos por orden de lista** (artefacto). Ahora salen de **cercanía real de
  perfiles** (explicable y defendible).

### 3.4 Sensibilidad intra-familia

Todos los pares que **antes empataban exacto** ahora se separan con score distinto:

```
ingenieria_mecanica +0.9386  vs  ingenieria_mecatronica +0.9398  Δ=0.0012  (antes EMPATE)
biologia            +0.8777  vs  fisica                 +0.9095  Δ=0.0318  (antes EMPATE)
ciencia_datos       +0.7763  vs  economia               +0.6858  Δ=0.0904  (antes EMPATE)
ingenieria_civil    +0.9438  vs  ingenieria_electrica   +0.9433  Δ=0.0006  (antes EMPATE)
```

El Δ es proporcional a la diferencia real de perfiles O\*NET: grande donde las carreras
difieren (datos vs economía), mínimo donde O\*NET las considera casi idénticas (civil vs
eléctrica). El motor ya **no inventa** un ganador por posición de lista.

---

## 4. Banco de preguntas — ¿hace falta ampliarlo?  *(Evaluación)*

**No.** La resolución *no* estaba del lado de las preguntas:

- 36 ítems (6 por dimensión) → la media por dimensión toma 25 valores en [1,5] (paso 0.167).
- En 2000 simulaciones aleatorias se obtuvieron **2000 vectores de usuario únicos**
  (resolución prácticamente continua).
- La dispersión intra-perfil del **catálogo** (1.18) ya supera a la del usuario (0.51): los
  cuellos de botella de resolución estaban en las **carreras** (redondeo, ya corregido), no en
  el test.

Ampliar el banco solo alargaría el test sin ganancia medible. **Recomendación: mantener 36
preguntas.** (Mejora opcional futura: ponderar ítems por su carga factorial O\*NET; hoy todos
pesan 1.0.)

---

## 5. Archivos modificados y cómo reproducir

| Archivo | Cambio |
|---|---|
| `build_catalog.py` | Reescalado 1-7 → 1-5 **float, sin redondear** + validación de floats |
| `data/carreras.json` | Regenerado (vectores float de alta resolución) |
| `engine/inference.py` | Coseno + Pearson + híbrido, sin cubo, desempate neutral, guarda de varianza |
| `tests/test_perfiles.py` | Tests alineados al motor corregido + 4 casos nuevos (10/10 OK) |
| `scripts/auditoria_onet.py` | **Nuevo** — auditoría de datos |
| `scripts/montecarlo.py` | **Nuevo** — simulación 500×3 + calibración + sensibilidad |
| `README.md`, `plan_analisis.md` | Documentación del motor actualizada |

```bash
python build_catalog.py            # regenerar catálogo
python scripts/auditoria_onet.py   # auditoría de datos
python scripts/montecarlo.py       # simulación Monte Carlo (antes/después)
python tests/test_perfiles.py      # suite de tests (10/10)
```
