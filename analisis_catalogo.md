# Análisis del Catálogo de Carreras — Balance y Volumen Óptimo

> **Conclusión:** el catálogo óptimo tiene **75 carreras**. Se eliminó **1**
> carrera (`profesorado_educacion_fisica`) por colisión exacta de vector. **No
> corresponde podar más:** las 75 restantes cubren los 6 arquetipos RIASEC de
> forma estadísticamente equilibrada y todas tienen un vector único y
> separable por el motor. Reproducir cifras: `python scripts/montecarlo.py`.

---

## 0. Conteo: de 77 → 76 → 75

| Estado | N | Motivo |
|---|---|---|
| Enunciado original | 77 (declarado) | Cifra del brief; **nunca fue real** |
| Catálogo previo | 76 | `data/carreras.json` real antes de este cambio |
| **Catálogo final** | **75** | Se quita la colisión `profesorado_educacion_fisica` |

El "77" del enunciado era un error de conteo: el catálogo ya tenía 76 (ver
`REPORTE_AUDITORIA.md`). Quitar la colisión deja **75**, no 76. El número ya
no se hardcodea en ningún lado: `build_catalog.py` escribe
`_meta.total_carreras = len(catálogo)` y los scripts/tests usan `len(...)`.

---

## 1. La colisión eliminada (Entregable 1)

`profesorado_educacion_fisica` y `profesorado_ciencias_exactas` apuntaban al
**mismo** código O*NET (`25-2031.00`, *Secondary School Teachers*), por lo que
producían el **vector RIASEC idéntico** `{R:3.47, I:1.67, A:2.13, S:4.80,
E:2.80, C:1.87}`.

- **Distancia euclídea entre ambos = 0.000** → empate puro.
- Para el motor (coseno + Pearson) eran **indistinguibles**: misma afinidad
  para cualquier usuario; el orden entre ellas dependía sólo del desempate.
- Era el **único** par duplicado del catálogo.

Se eliminó `profesorado_educacion_fisica` (según lo pedido). Tras hacerlo, la
**distancia euclídea mínima** entre dos vectores cualesquiera pasa a **0.346 >
0**: ya no hay dos carreras con el mismo vector. El test
`test_sin_colisiones_de_vectores` ahora exige `colisiones == []`.

---

## 2. Balance del espectro RIASEC (Entregable 2)

Para cada carrera se toma su **dimensión dominante** (`argmax` del vector
RIASEC) y se cuenta cuántas carreras "viven" en cada arquetipo de Holland:

| Arquetipo | Carreras | Reparto |
|---|---:|---|
| **R** · Realista     | 12 | `############` |
| **I** · Investigador | 21 | `#####################` |
| **A** · Artístico    | 13 | `#############` |
| **S** · Social       | 10 | `##########` |
| **E** · Emprendedor  |  8 | `########` |
| **C** · Convencional | 11 | `###########` |

**¿Está bien distribuido? Sí, y es contrastable estadísticamente:**

- **Entropía normalizada de la distribución de arquetipos = 0.972** (sobre un
  máximo de 1.0 = equilibrio perfecto entre los 6). Es decir, la "masa" del
  catálogo está repartida casi uniformemente entre R/I/A/S/E/C.
- **Prueba χ² de bondad de ajuste contra la uniformidad:** χ² = **8.12** con 5
  g.l.; el valor crítico al 5 % es 11.07. Como 8.12 < 11.07, **no se rechaza**
  la hipótesis de reparto uniforme: la sobre/sub-representación observada no es
  estadísticamente significativa.
- **Cobertura total:** los 6 arquetipos están representados, y un usuario
  "puro" en cada dimensión recibe un #1 de su propia dominante:

  | Usuario puro | #1 recomendado | Dominante del #1 |
  |---|---|---|
  | R | `tec_produccion_agropecuaria` | R |
  | I | `fisica` | I |
  | A | `artes_visuales` | A |
  | S | `trabajo_social` | S |
  | E | `negocios_digitales` | E |
  | C | `tec_administracion_contable` | C |

**Único desbalance leve:** Investigador (I) lidera con 21. Es esperable y
deseable: I es el arquetipo más transversal del catálogo moderno (solapa
STEM + salud + datos). Recortar carreras I para "emparejar" los conteos
abriría huecos vocacionales reales sin ganar nada psicométrico (la χ² ya
indica que no hay desbalance significativo).

---

## 3. ¿Hay carreras redundantes que podar? (Entregable 3)

El criterio ingenuo "misma área + coseno casi idéntico" **no es válido aquí**,
y demostrarlo es la parte central del análisis.

### 3.1 El coseno crudo NO sirve como criterio de redundancia

Los vectores viven en `[1,5]^6`, es decir, **todos en el ortante positivo**.
Eso comprime el coseno hacia arriba artificialmente: dos carreras *muy*
distintas igual comparten dirección general. Sobre los 2.775 pares posibles:

| Percentil del coseno | Valor |
|---|---:|
| p50 (mediana) | 0.842 |
| p75 | 0.917 |
| p90 | 0.958 |
| p95 | 0.975 |

Aplicar un umbral tipo "coseno ≥ 0.99" marcaría **37 pares** como
"redundantes" (≥ 0.95 marcaría **350**). Eso no es redundancia: es el piso
estructural de una escala positiva. Podar por coseno **mutilaría** el catálogo.

### 3.2 La métrica correcta es la FORMA (Pearson), que es la que pondera el motor

El motor es **Pearson-dominante** (`score = 0.4·coseno + 0.6·pearson`). Pearson
(coseno centrado) mide la *forma* del perfil y su rango sí es ancho y
discriminante:

| | coseno | pearson |
|---|---:|---:|
| pares ≥ 0.999 | **1** | **0** |
| pares ≥ 0.99 | 37 | 3 |
| pares ≥ 0.97 | 179 | 20 |
| pares ≥ 0.95 | 350 | 37 |

Sólo **1 par** supera coseno 0.999 y **ningún** par supera Pearson 0.999.

### 3.3 El par más cercano sigue siendo separable

El máximo de similitud lo da `ingenieria_mecanica` vs `ingenieria_mecatronica`
(coseno 0.9994, Pearson 0.9972). Aun así **no son redundantes para el motor**:
para un usuario ingenieril (R4 I5 A2 S2 E3 C3) sus scores difieren
(Δscore ≈ 0.0012) y el desempate es determinista. Justamente, el paso a
**vectores float de alta resolución** (ver `inference.py` / `montecarlo.py`)
se hizo *para* mantener estas familias distinguibles en vez de fusionarlas.
Podarlas desharía esa decisión de diseño y perdería una carrera real (un
estudiante de Mecatrónica no es un estudiante de Mecánica).

### 3.4 Veredicto

> No existe **ningún** par que sea, a la vez, **misma área** y
> **estadísticamente inseparable por el motor** (la única que lo era —la
> colisión exacta— ya se eliminó). Por lo tanto **no se poda ninguna carrera
> adicional.**

---

## 4. ¿Por qué 75 es el volumen óptimo? (Entregable 4)

1. **Sin redundancia:** 75 vectores únicos; distancia mínima 0.346 > 0; ningún
   par inseparable por el motor.
2. **Sin huecos:** los 6 arquetipos RIASEC están cubiertos y son alcanzables
   como #1; la distribución es estadísticamente uniforme (χ² no significativo,
   entropía 0.972).
3. **Sin saturar el modelo:** el motor recorre las 75 carreras en O(N) por
   usuario; la limitación de la diversidad del Top-1 **no** viene del tamaño
   del catálogo sino de la **granularidad de las preguntas** (36 ítems → el
   vector de usuario es relativamente grueso), como muestra el Monte Carlo
   (cobertura Top-1 ≈ 67/75 en el escenario realista). Agregar carreras no
   mejora esa cobertura; sólo añade vecinos cercanos.
4. **Trazabilidad:** cada carrera mapea a una ocupación O*NET distinta, así que
   el volumen está acotado por la realidad ocupacional, no inflado a mano.

**Quitar más** carreras crearía huecos de arquetipo (reduciría la cobertura ya
medida); **agregar más** sólo introduciría vecinos de alta similitud (más
"imanes/huérfanas") sin ampliar el espectro. **75 es el punto de equilibrio.**

---

### Reproducibilidad

```bash
python build_catalog.py --dry-run   # valida: 75 carreras, sin duplicados
python scripts/montecarlo.py        # distribución del Top-1, sensibilidad intra-familia
python scripts/auditoria_onet.py    # auditoría de los vectores O*NET
python tests/test_perfiles.py       # 10/10, incl. test_sin_colisiones_de_vectores
```
