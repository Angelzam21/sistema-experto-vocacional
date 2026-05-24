# PLAN TÉCNICO DE IMPLEMENTACIÓN: SISTEMA EXPERTO VOCACIONAL BASADO EN DATOS

Este plan define la arquitectura técnica detallada y el mapa de ruta paso a paso para la construcción del Sistema Experto Vocacional Basado en Datos. El propósito fundamental de esta plataforma es fusionar la oferta académica real de las universidades públicas con el estándar de evaluación psicométrica internacional O*NET, estructurando un motor de inferencia algorítmico capaz de proveer recomendaciones precisas, contextualizadas y libres de sesgos artificiales.

**Objetivo de Arquitectura:** Despliegue de un MVP ágil, stateless (sin estado), ejecutado íntegramente en memoria mediante Streamlit, priorizando velocidad, bajo costo de infraestructura y privacidad de datos por diseño.

---

## Fase 1: Proceso ETL (Ejecución Única / Offline)

Esta fase de ingeniería de datos establece el dataset maestro del proyecto. Se ejecuta localmente **una sola vez** mediante un script independiente. El resultado es un archivo JSON estático que actuará como la base de conocimiento y API local del sistema.

### Paso 1.1: Web Scraping de la Oferta Académica Argentina
Extracción de información de las 30 carreras universitarias de mayor demanda en el país, cruzándose con las mallas de las principales universidades públicas nacionales (ej: UBA, UTN, UNLP, UNC, UNR, UNT, UNS, UNSAM).
*   **Fuentes de Datos:** Buscador de Carreras del Ministerio de Capital Humano, guías SIU y portales oficiales de admisión.
*   **Herramientas:** Script automatizado en Python utilizando `BeautifulSoup` (HTML estático) y/o `Selenium`/`Playwright` (renderizado dinámico).
*   **Captura de Filtros Duros:** Durante el scraping, se extraerán obligatoriamente metadatos clave para el filtrado posterior:
    *   `zona_geografica` (ej. "CABA", "Buenos Aires", "Córdoba").
    *   `modalidad` (ej. "Presencial", "Híbrida", "A Distancia").

### Paso 1.2: Estructuración y Normalización
Saneamiento de cadenas de texto para evitar inconsistencias de nomenclatura en bases de datos abiertas.
*   **Normalización:** Aplicación de Regex y Fuzzy Matching para unificar sinónimos (ej: 'Ing. en Sistemas' e 'Ingeniería de Sistemas' bajo un ID maestro).
*   **Salida (API Local):** Creación del archivo maestro `carreras_argentina.json`. En esta etapa contendrá la identidad básica y los filtros, dejando los campos del Modelo Holland (RIASEC) nulos provisionalmente.

### Paso 1.3: Enriquecimiento de Datos mediante O*NET (Mapeo RIASEC)
Inyección del modelo teórico RIASEC (Realista, Investigador, Artístico, Social, Emprendedor, Convencional) vinculando las carreras locales con los códigos SOC de O*NET.
*   **Mapeo:** Correspondencia heurística (Ej: 'Contador Público' -> 'Accountants and Auditors', Código O*NET: 13-2011.00).
*   **Ingesta y Normalización Algorítmica:** Extracción de las puntuaciones crudas de intereses ("Interests") desde O*NET. Conversión de las escalas variables de O*NET a una escala discreta del 1 al 5.
*   **Consolidación Final:** Los puntajes estandarizados (1-5) sobrescriben los campos nulos en `carreras_argentina.json`, conformando el **vector de afinidad estático** de cada carrera. Este archivo se guarda en el repositorio y finaliza la Fase 1.

---

## Fase 2: Banco de Preguntas y Motor de Inferencia

Esta fase define los inputs psicométricos del usuario y la matemática pura del backend para procesar el emparejamiento.

### Paso 2.0: Construcción y Localización del Banco de Preguntas
Generación de las preguntas reactivas para la interfaz web, basadas en el instrumento oficial de dominio público *O*NET Interest Profiler*, pero con localización cultural y lingüística para estudiantes en Argentina.
*   **Almacenamiento estático:** Creación de un archivo secundario llamado `preguntas_riasec_ar.json` estructurado como: `[ID, Dimensión_RIASEC, Pregunta, Ponderación]`.
*   **Ejemplos de Localización ("Argentinización"):**
    *   *Realista (R):* "Arreglar motores de autos o motos" (O*NET: Repair cars).
    *   *Investigador (I):* "Hacer experimentos en un laboratorio" (O*NET: Work in a biology lab).
    *   *Emprendedor (E):* "Administrar un local comercial o una Pyme" (O*NET: Manage a retail store).
*   **Escala Likert de Entrada:** 1 (Lo detestaría) | 2 (No me gustaría) | 3 (Me da igual) | 4 (Me gustaría) | 5 (Me encantaría).

### Paso 2.1: Captura del Vector de Perfil de Usuario
*   El sistema administra el banco de preguntas. Al finalizar, calcula el puntaje promedio por cada dimensión RIASEC.
*   **Output:** Un vector numérico normalizado en un espacio de 6 dimensiones. Ej: Usuario A = `[R: 4.2, I: 2.1, A: 1.5, S: 4.8, E: 3.0, C: 2.5]`.

### Paso 2.2: Algoritmo de Similitud de Coseno
El núcleo matemático del emparejamiento. Se descarta la Distancia Euclidiana para evitar sesgos de magnitud.
*   **Fórmula:** Implementación en NumPy o SciPy del cálculo vectorial:
$$ \text{Similitud} = \cos(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|} $$
*(Donde **A** es el vector RIASEC del usuario y **B** es el vector RIASEC de la carrera iterada).*
*   **Ponderación:** Ordenamiento descendente (de 1.0 a -1.0) de las 30 carreras basado en este índice.

---

## Fase 3: Arquitectura Unificada y Lógica de UI (Streamlit)

Se prescinde de infraestructuras backend complejas, bases de datos o APIs externas. Streamlit actuará simultáneamente como motor algorítmico y estructura de presentación.

### Paso 3.1: Catálogo Estático en Memoria (In-Memory Data)
*   **Carga Única:** Utilizando el decorador `@st.cache_data`, la aplicación leerá los archivos estáticos de forma local una única vez al iniciar el servidor. 
*   **Anonimato por Diseño:** Los vectores de usuario se alojan exclusivamente en el `st.session_state` de su sesión efímera.

### Paso 3.2: Flujo de Evaluación Interactivo
*   **Test Dinámico:** Las preguntas se presentan manejando el progreso mediante `st.session_state`.
*   **Filtros Previos:** Sección para determinar restricciones ("Filtros Duros") de ubicación y modalidad, las cuales excluirán carreras antes del cálculo de Coseno.

---

## Fase 4: Diseño de Interfaz de Usuario (UI/UX) y Estilización Avanzada

Para evitar el aspecto genérico por defecto de Streamlit y garantizar un estándar visual moderno, analítico y premium, se aplicarán estrictamente los siguientes filtros y configuraciones estéticas centradas en el minimalismo y el alto contraste (monocromático blanco/negro).

### Paso 4.1: Configuración Global del Tema (Archivo `.streamlit/config.toml`)
El sistema no utilizará el tema por defecto. Claude Code deberá crear y configurar el archivo `config.toml` para establecer una paleta dura:
*   `primaryColor = "#000000"` (Negro puro para acciones principales).
*   `backgroundColor = "#FFFFFF"` (Blanco puro de fondo principal).
*   `secondaryBackgroundColor = "#F5F5F5"` (Gris ultra claro para contenedores o secciones de contraste mínimo).
*   `textColor = "#111111"` (Gris casi negro para máxima legibilidad sin fatiga).
*   `font = "sans serif"` (Tipografía limpia por defecto).

### Paso 4.2: Inyección de CSS Personalizado (Clean UI)
Uso de `st.markdown("<style>...</style>", unsafe_allow_html=True)` en la inicialización de la app para anular los elementos genéricos que delatan el framework:
*   **Ocultar Marca Streamlit:** Desactivar por completo el menú de hamburguesa (`#MainMenu {visibility: hidden;}`), el pie de página (`footer {visibility: hidden;}`) y la barra de decoración superior (`header {visibility: hidden;}`).
*   **Tipografía y Botones Modernos:** Forzar el uso de fuentes geométricas modernas (ej. emulando San Francisco o Inter). Modificar las clases de los botones (`stButton`) para eliminar los radios de borde curvos (`border-radius: 4px;` máximo), eliminar las sombras, e implementar transiciones `hover` sutiles. Los botones deben verse planos y afilados.
*   **Contenedores Invisibles:** Eliminar los bordes evidentes de las cajas de Streamlit; la separación estructural debe lograrse mediante el uso adecuado de espacios en blanco (paddings/margins) y jerarquía tipográfica.

### Paso 4.3: Estilización del Dashboard Analítico y Resultados
Las visualizaciones de datos deben adherirse a la estética corporativa y moderna, evitando las paletas de colores festivas o genéricas.
*   **Radar Chart Monocromático (Plotly):** Configurar `st.plotly_chart` con `template="plotly_white"`. El polígono resultante (los 6 puntos RIASEC) no debe usar los colores vivos de Plotly. Las líneas deben ser negras o de un gris oscuro (`color='#000000'`), con un relleno sutil translúcido (`fillcolor='rgba(0,0,0,0.1)'`). Las etiquetas de los vértices deben ser sobrias y legibles.
*   **Tarjetas de Recomendación (Top 5):** Estructurar los resultados mediante `st.container` y `st.columns`. Al usar `st.expander` para revelar los detalles de la carrera (Universidades, Modalidad), modificar su CSS nativo para que luzcan como paneles limpios, con el título de la carrera en fuente **bold de gran tamaño** y el porcentaje de afinidad alineado a la derecha en tipografía monoespaciada o de alto contraste.