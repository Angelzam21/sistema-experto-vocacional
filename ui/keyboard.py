"""
=================================================================
NAVEGACIÓN POR TECLADO DEL TEST (atajos numéricos + Enter)
=================================================================
Streamlit no expone un API nativo de "key listeners". El patrón estándar
es inyectar un puente de JavaScript con `components.html`, que crea un
iframe `srcdoc` *del mismo origen* que la app; desde ahí podemos acceder
al documento padre (`window.parent.document`) y escuchar el teclado de
TODA la página, no sólo del iframe.

¿Qué hace el puente?
  - Teclas `1`..`N`  -> marca la opción Likert correspondiente (hace click
    en el N-ésimo <label> del único radiogroup de la pantalla de test).
  - `Enter`          -> valida y avanza: hace click en el botón PRIMARIO
    ("Siguiente →" / "Definir límites →"), que dispara la lógica de
    avance ya existente en app.py (calcula vector en la última pregunta).

CICLO DE VIDA / CLEANUP (clave para no romper el render):
  Streamlit RE-EJECUTA el script en cada interacción y, con él, vuelve a
  inyectar este componente. Si en cada corrida hiciéramos
  `addEventListener` sin más, los listeners se APILARÍAN y un solo tecleo
  dispararía el handler N veces (avances dobles, selecciones saltadas).
  Para evitarlo, guardamos el handler vigente en `doc.__voc_key_handler`
  y, antes de registrar el nuevo, REMOVEMOS el anterior. Así, sin importar
  cuántos reruns ocurran, SIEMPRE hay exactamente UN listener activo.

Los selectores del DOM (`div[role="radiogroup"] > label`, `button[kind=
"primary"]`) son los mismos que ya usa ui/styles.py, así que son estables
para la versión de Streamlit del proyecto.
=================================================================
"""
from __future__ import annotations

import streamlit.components.v1 as components


def inyectar_navegacion_teclado(num_opciones: int) -> None:
    """Activa los atajos de teclado del test (1..N y Enter).

    Debe llamarse UNA vez por render de la pantalla de test, DESPUÉS de
    dibujar el radio y los botones (el JS corre en el navegador una vez
    construido el DOM padre, así que el orden de inyección no es crítico,
    pero lo invocamos al final por claridad).

    Args:
        num_opciones: cantidad de opciones de la escala Likert (p. ej. 5).
            Acota qué teclas numéricas son válidas (1..num_opciones).
    """
    js = f"""
    <script>
    (function() {{
      const NUM = {int(num_opciones)};
      const doc = window.parent.document;   // documento de la app (no el iframe)

      // --- CLEANUP: quitar el handler de la corrida anterior --------------
      // Sin esto, cada rerun apilaría un listener nuevo y un tecleo
      // dispararía la acción varias veces.
      if (doc.__voc_key_handler) {{
        doc.removeEventListener('keydown', doc.__voc_key_handler);
      }}

      const handler = function(e) {{
        // No secuestrar el teclado cuando se escribe en un campo de texto.
        const t = e.target;
        const tag = (t && t.tagName) ? t.tagName.toLowerCase() : '';
        if (tag === 'textarea' || (t && t.isContentEditable)) return;
        if (tag === 'input' && t.type === 'text') return;
        // Ignorar combinaciones con modificadores (atajos del navegador).
        if (e.ctrlKey || e.metaKey || e.altKey) return;

        // --- Teclas 1..N -> seleccionar la opción Likert correspondiente ---
        const n = parseInt(e.key, 10);
        if (!isNaN(n) && n >= 1 && n <= NUM) {{
          const grupos = doc.querySelectorAll('div[role="radiogroup"]');
          if (grupos.length) {{
            const labels = grupos[0].querySelectorAll('label');
            if (labels[n - 1]) {{
              labels[n - 1].click();   // marca la respuesta (Streamlit re-ejecuta)
              e.preventDefault();
            }}
          }}
          return;
        }}

        // --- Enter -> validar y avanzar (click al botón primario) ----------
        if (e.key === 'Enter') {{
          const btns = doc.querySelectorAll('button[kind="primary"]');
          if (btns.length) {{
            btns[0].click();           // en el test el único primario es "avanzar"
            e.preventDefault();        // evita doble-activación si hay foco en otro botón
          }}
        }}
      }};

      doc.__voc_key_handler = handler;
      doc.addEventListener('keydown', handler);
    }})();
    </script>
    """
    # height/width 0: el iframe es invisible; sólo sirve de puente JS.
    components.html(js, height=0, width=0)
