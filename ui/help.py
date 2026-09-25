"""Ayuda dinámica y orientación del flujo de trabajo (mejora UX v1.7.1).

Tres canales de ayuda que trabajan juntos para que el usuario nunca se
quede sin contexto:

1. Globos de ayuda (Tooltip): al detener el cursor sobre cualquier
   botón o control aparece una explicación breve Y la misma frase se
   fija en la barra de estado inferior.
2. Mensajes de menú (MENU_HINTS): al abrir cualquier menú superior, la
   barra de estado explica para qué sirve.
3. Motor de siguiente paso (next_hint): tras cada acción, la barra de
   estado sugiere de forma amable cuál es el paso siguiente natural,
   para que el flujo se descubra solo y no resulte abrumador.

El contenido es puro (sin Tk) para poder probarlo headless.
"""

from __future__ import annotations

try:
    import tkinter as tk
except ImportError:
    tk = None  # type: ignore[assignment]
from typing import Any, Callable, Dict, Optional

# -- Ayuda por control (clave → texto orientador) ----------------------------
# Frases en segunda persona, con verbo y beneficio: "para qué me sirve
# esto" en menos de 12 palabras.
TOOLTIPS: Dict[str, str] = {
    "guide": "Guía rápida: un recorrido de 4 pasos para dominar la pantalla.",
    "fit": "Encuadra todo el proyecto en el lienzo (tecla F).",
    "zoom_in": "Acerca la vista. También la rueda del ratón sobre el plano.",
    "zoom_out": "Aleja la vista. También la rueda del ratón sobre el plano.",
    "new_object": "Crea un objeto nuevo: local, muro, puerta, nivel… "
                  "según tu disciplina activa.",
    "edit": "Cambia un dato del objeto seleccionado (por ejemplo, el "
            "espesor de un muro).",
    "search_field": "Elige por qué buscar: código, nombre, tipo, nivel…",
    "search_entry": "Escribe aquí y pulsa Enter: verás los resultados en "
                    "el explorador de la izquierda.",
    "search_btn": "Busca en todo el proyecto (o en la disciplina activa).",
    "clear_btn": "Limpia la búsqueda y vuelve al árbol completo del proyecto.",
    "level_combo": "Muestra solo los objetos de un nivel de la edificación.",
    "props_edit": "Edita el campo marcado con ✎ del objeto seleccionado.",
    "state_btn": "Avanza el ciclo de vida del objeto: borrador → propuesto "
                 "→ aprobado…",
    "warnings_tab": "Hallazgos de validación: qué revisar antes de exportar.",
    "log_tab": "Diario de la aplicación: cada acción queda registrada aquí.",
    "calc_tab": "Historial de cálculos de cantidades y presupuesto.",
    "canvas": "Rueda: zoom · Arrastrar (botón central/derecho): mover · "
              "Clic: seleccionar · Doble clic: editar o encuadrar.",
    "hint_bar": "Recordatorio de los gestos del lienzo.",
    "welcome_new": "Crea un proyecto nuevo y empieza de cero.",
    "welcome_open": "Abre un proyecto .arqgen que ya tengas guardado.",
    "welcome_demo": "Carga un proyecto de ejemplo para explorar sin miedo "
                    "a romper nada.",
}

# Ayudas para los campos de los formularios de creación (FASE 90.1).
FIELD_HINTS: Dict[str, str] = {
    "name": "Un nombre claro te ayudará a encontrarlo después.",
    "elevation_m": "Altura del piso sobre el terreno, en metros (0 = planta "
                   "baja).",
    "height_m": "Altura libre del piso o del elemento, en metros.",
    "space_type": "Clave del tipo de local (ROOM, KITCHEN, BATH…).",
    "boundary": "Contorno del local: pares «x,y» separados por espacios. "
                "Si lo dejas vacío se crea uno provisional.",
    "start": "Punto inicial del muro: «x, y» en metros.",
    "end": "Punto final del muro: «x, y» en metros.",
    "thickness_m": "Espesor del muro en metros (0.2 = 20 cm).",
    "width_m": "Dimension horizontal, en metros.",
    "offset_m": "Distancia desde el inicio del muro hasta el hueco.",
    "sill_height_m": "Altura del antepecho: de la planta a la base de la "
                     "ventana.",
    "wall_ref": "Elige el muro donde irá el hueco.",
    "level_ref": "Elige el nivel donde vivirá el objeto.",
    "kind": "Familia o tipo del elemento.",
    "shape": "Forma de la sección transversal.",
    "h_mm": "Dimensión h de la sección, en milímetros.",
    "b_mm": "Dimensión b de la sección, en milímetros.",
    "load_udl_kn_m": "Carga repartida uniforme sobre el elemento (kN/m).",
    "system": "Sistema de la red: agua, eléctrico, CCTV…",
    "description": "Opcional: una nota corta para saber qué hace esta "
                   "red.",
    "network_ref": "Red a la que se conecta el nodo.",
    "x": "Coordenada X en metros.",
    "y": "Coordenada Y en metros.",
    "fck_mpa": "Resistencia característica del hormigón (MPa).",
    "fy_mpa": "Límite elástico del acero (MPa).",
    "density_kn_m3": "Peso específico del material (kN/m³).",
}

# Mensajes que la barra de estado muestra al abrir cada menú superior.
MENU_HINTS: Dict[str, str] = {
    "Archivo": "Crear, abrir, guardar y exportar tu proyecto. Empieza por "
               "aquí si es tu primera vez.",
    "Editar": "Deshacer, rehacer, crear, editar y eliminar objetos.",
    "Ver": "Zoom, encuadre y cuadrícula del plano.",
    "Herramientas": "Validar el proyecto, calcular cantidades y presupuesto "
                    "y generar el informe.",
    "Ayuda": "Guía rápida, atajos de teclado e información de la app.",
}

# -- Guía rápida (recorrido de 4 pasos) ---------------------------------------
GUIDE_STEPS = (
    ("1 · Mira y navega",
     "El explorador de la izquierda agrupa el proyecto en 13 disciplinas. "
     "Pulsa sobre cualquier objeto y verás sus datos a la derecha y su "
     "figura en el plano central."),
    ("2 · Crea y edita",
     "El botón «+ Objeto» crea locales, muros, puertas… El botón «Editar» "
     "modifica lo seleccionado. Todo queda en el diario (pestaña Log) y se "
     "puede deshacer con Ctrl+Z."),
    ("3 · Calcula",
     "En «Herramientas ▸ Recalcular todo» obtienes cantidades (QTO) y "
     "presupuesto. Los hallazgos de validación aparecen en la pestaña "
     "«Avisos»."),
    ("4 · Comparte",
     "Cuando estés conforme, usa «Archivo ▸ Exportar» (DXF, XLSX, CSV, "
     "JSON, IFC) o genera el informe descriptivo en Markdown."),
)

# Sugerencia por defecto cuando no hay nada mejor que proponer.
DEFAULT_HINT = ("Todo listo. Si dudas, pulsa «Guía rápida» o abre "
                "Archivo ▸ Proyecto de demostración para explorar.")


def next_hint(*, spaces: int = 0, walls: int = 0, doors: int = 0,
              calculations: int = 0, warnings: int = -1,
              searching: bool = False) -> str:
    """Devuelve el siguiente paso sugerido según el estado del proyecto.

    Función pura: los parámetros resumen el proyecto y la respuesta es
    una frase amable y concreta. El orden replica el flujo natural de
    trabajo: modelar locales → muros → huecos → calcular → validar.
    """
    if searching:
        return ("Haz clic en un resultado para saltar a él, o pulsa "
                "Escape para volver al árbol completo.")
    if spaces == 0:
        return ("Paso siguiente: crea tu primer local con «+ Objeto» "
                "(o carga Archivo ▸ Proyecto de demostración).")
    if walls == 0:
        return ("Paso siguiente: añade muros con «+ Objeto ▸ WALL» para "
                "delimitar los espacios.")
    if doors == 0:
        return ("Paso siguiente: inserta puertas o ventanas sobre los "
                "muros con «+ Objeto».")
    if calculations == 0:
        return ("Paso siguiente: Herramientas ▸ Recalcular todo para "
                "obtener cantidades y presupuesto.")
    if warnings > 0:
        return ("Revisa la pestaña «Avisos»: hay hallazgos que conviene "
                "atender antes de exportar.")
    if warnings == 0:
        return ("Validación limpia. Ya puedes exportar con Archivo ▸ "
                "Exportar o generar el informe.")
    return DEFAULT_HINT


class Tooltip:
    """Globo de ayuda al pasar el cursor + eco en la barra de estado.

    - Al entrar el cursor: fija `text` en la barra de estado (si se
      pasó `status_var`) y, tras `delay` ms, muestra un globo oscuro
      junto al control.
    - Al salir o al pulsar: retira el globo y restaura la barra.
    """

    def __init__(self, widget: Any, text: str,
                 status_var: Optional[tk.StringVar] = None,
                 restore: Optional[Callable[[], str]] = None,
                 delay: int = 550) -> None:
        self.widget = widget
        self.text = text
        self.status_var = status_var
        self.restore = restore
        self.delay = max(120, int(delay))
        self._after_id: Optional[str] = None
        self._balloon: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    # -- comportamiento --------------------------------------------------------
    def _on_enter(self, _event=None) -> None:
        if self.status_var is not None:
            self.status_var.set(self.text)
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _event=None) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001 - widget ya destruido
                pass
            self._after_id = None
        self._hide()
        if self.status_var is not None and self.restore is not None:
            self.status_var.set(self.restore())

    def _show(self) -> None:
        if self._balloon is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + \
                self.widget.winfo_height() + 6
            balloon = tk.Toplevel(self.widget)
        except Exception:  # noqa: BLE001 - ventana cerrada entre medias
            return
        balloon.wm_overrideredirect(True)
        balloon.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            balloon, text=self.text, justify="left", wraplength=340,
            background="#1D2129", foreground="#E9ECF1",
            highlightthickness=1, highlightbackground="#3E68B8",
            padx=10, pady=6, font=("TkTextFont", 9))
        label.pack()
        self._balloon = balloon

    def _hide(self) -> None:
        if self._balloon is not None:
            try:
                self._balloon.destroy()
            except Exception:  # noqa: BLE001 - ya destruido
                pass
            self._balloon = None


def attach_menu_hints(menu: tk.Menu, status_var: tk.StringVar) -> None:
    """Explica cada menú superior en la barra de estado al abrirlo.

    Usa el `postcommand` del submenú de cada cascada, que Tk dispara
    justo antes de desplegarlo: funciona igual en Windows, Linux y
    macOS.
    """
    for label, hint in MENU_HINTS.items():
        try:
            index = menu.index(label)
        except Exception:  # noqa: BLE001 - etiqueta ausente
            continue
        if index is None or menu.type(index) != "cascade":
            continue
        try:
            submenu = menu.nametowidget(menu.entrycget(index, "menu"))
        except Exception:  # noqa: BLE001 - cascada sin submenú
            continue
        submenu.configure(postcommand=lambda h=hint: status_var.set(h))


__all__ = [
    "TOOLTIPS", "FIELD_HINTS", "MENU_HINTS", "GUIDE_STEPS", "DEFAULT_HINT",
    "next_hint", "Tooltip", "attach_menu_hints",
]
