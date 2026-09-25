"""Main window of ARQ GEN (FASE 90, spec sections 90-93).

Layout §90: MENU/TOOLBAR · PROJECT EXPLORER | CANVAS | PROPERTIES ·
WARNINGS/LOG/CALCULATION STATUS. Navigation by the 13 disciplines of
§91, search box with the 9 fields of §92, and the §93 state system
(entity states via the StateService, calculation states in the status
panel). All logic lives in ui.models; this module is only widgets.

Mejora UX v1.7.1: tema oscuro con letras claras (ui.theme), ayuda
dinámica en cada control (ui.help: globos + barra de estado), mensajes
orientadores al abrir cada menú, panel de bienvenida en proyectos
vacíos y sugerencias del siguiente paso tras cada acción.
"""

from __future__ import annotations

import os
import tempfile
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    _BaseWindow = tk.Tk
except ImportError:  # headless / environments without Tk
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    _BaseWindow = object  # type: ignore[assignment,misc]
from typing import Any, Dict, List, Optional

from core import APP_VERSION
from ui import help as help_mod
from ui import theme
from ui.disciplines import DISCIPLINES, discipline_label
from ui.help import (FIELD_HINTS, GUIDE_STEPS,
                     Tooltip, attach_menu_hints, next_hint)
from ui.models import (CanvasModel, CREATE_SPECS, EditService,
                       EntityStateFlow, ExplorerModel, ObjectRow, SEARCH_FIELDS,
                       PropertiesModel, PropertyEditor, SearchEngine,
                       StateService, StatusModel, Viewport)
from ui.theme import CANVAS_DARK, ENTITY_COLORS, menu_kwargs

# Paleta determinista por tipo/sistema: tonos del tema oscuro ajustados
# para contrastar sobre el lienzo profundo (los originales siguen
# disponibles vía ENTITY_COLORS invertidos si se necesitara).
PALETTE: Dict[str, str] = dict(ENTITY_COLORS)
PALETTE.update({
    "selection": CANVAS_DARK["selection"],
    "grid": CANVAS_DARK["grid"],
    "axis": CANVAS_DARK["axis"],
})

# Atajos de teclado §90 (documentados en Ayuda → Atajos y verificables
# headless desde tests/test_097).
ACCELERATORS: Dict[str, str] = {
    "<Control-n>": "new_project",
    "<Control-o>": "open_project_dialog",
    "<Control-s>": "save_project",
    "<Control-z>": "undo",
    "<Control-y>": "redo",
    "<Control-f>": "focus_search",
    "<Control-e>": "edit_property_dialog",
    "<Delete>": "delete_selection",
    "<Key-plus>": "zoom_in",
    "<Key-minus>": "zoom_out",
    "<Key-f>": "fit_view",
    "<Escape>": "clear_search",
    "<F1>": "show_quick_guide",
}


class ARQGenWindow(_BaseWindow):
    """Ventana principal §90 sobre las fachadas de servicios."""

    def __init__(self, context: Any, application: Any = None) -> None:
        if tk is None:
            raise RuntimeError("Tkinter no está disponible en este entorno.")
        super().__init__()
        self.ctx = context
        self.application = application
        self.title(f"ARQ GEN {APP_VERSION} — {context.project.name}")
        self.geometry("1280x800")
        theme.apply_dark_theme(self)

        self.explorer = ExplorerModel(context)
        self.search_engine = SearchEngine(self.explorer)
        self.canvas_model = CanvasModel(context, self.explorer)
        self.state_service = StateService(context)
        self.edit_service = EditService(context, self.explorer)
        self.status_model = StatusModel(context)
        self.viewport = Viewport()

        self.current_discipline = "ARCHITECTURE"
        self.selection: Optional[ObjectRow] = None
        self._primitives: List[Any] = []
        self._result_rows: List[ObjectRow] = []
        self._pan_start: Optional[tuple[float, float]] = None
        self._coord_var: Optional[Any] = None
        self._status_base = ""
        self._tooltips: List[Tooltip] = []

        self._build_menu()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()
        self._wire_canvas()
        self._bind_accelerators()
        self._subscribe_events()
        self.refresh_all(fit=True)
        self._say("Bienvenido a ARQ GEN. Pasa el cursor por cualquier "
                  "botón para ver qué hace.",
                  next_hint(**self._project_stats()))

    # -- construcción de la UI (§90) -------------------------------------
    def _bind_accelerators(self) -> None:
        for sequence, method_name in ACCELERATORS.items():
            handler = getattr(self, method_name, None)
            if callable(handler):
                self.bind_all(sequence, lambda _e, h=handler: h())

    def _build_menu(self) -> None:
        menubar = tk.Menu(self, **menu_kwargs())

        m_file = tk.Menu(menubar, **menu_kwargs())
        m_file.add_command(label="Nuevo proyecto…",
                           command=self.new_project,
                           accelerator="Ctrl+N")
        m_file.add_command(label="Abrir…", command=self.open_project_dialog,
                           accelerator="Ctrl+O")
        m_file.add_command(label="Proyecto de demostración",
                           command=self.open_demo)
        m_file.add_separator()
        export_menu = tk.Menu(m_file, **menu_kwargs())
        for fmt in ("DXF", "JSON", "XLSX", "CSV", "IFC"):
            export_menu.add_command(
                label=f"Exportar {fmt}…",
                command=lambda f=fmt: self.export(f))
        m_file.add_cascade(label="Exportar", menu=export_menu)
        m_file.add_separator()
        m_file.add_command(label="Salir", command=self.on_close)
        menubar.add_cascade(label="Archivo", menu=m_file)

        m_edit = tk.Menu(menubar, **menu_kwargs())
        m_edit.add_command(label="Deshacer\tCtrl+Z", command=self.undo)
        m_edit.add_command(label="Rehacer\tCtrl+Y", command=self.redo)
        m_edit.add_separator()
        m_edit.add_command(label="Nuevo objeto…",
                           command=self.new_object_dialog)
        m_edit.add_command(label="Editar propiedad…\tCtrl+E",
                           command=self.edit_property_dialog)
        m_edit.add_command(label="Estado de la entidad…",
                           command=self.change_state_dialog)
        m_edit.add_separator()
        m_edit.add_command(label="Eliminar selección\tSupr",
                           command=self.delete_selection)
        menubar.add_cascade(label="Editar", menu=m_edit)

        m_design = tk.Menu(menubar, **menu_kwargs())
        m_design.add_command(label="⚡ Asistente de Generación Arquitectónica…",
                             command=self.open_generative_wizard)
        m_design.add_separator()
        m_design.add_command(label="Plantilla: Vivienda 1 Dormitorio",
                             command=lambda: self.generate_from_template("VIVIENDA_1D"))
        m_design.add_command(label="Plantilla: Vivienda 2 Dormitorios",
                             command=lambda: self.generate_from_template("VIVIENDA_2D"))
        m_design.add_command(label="Plantilla: Vivienda 3 Dormitorios",
                             command=lambda: self.generate_from_template("VIVIENDA_3D"))
        m_design.add_command(label="Plantilla: Oficinas Administrativas",
                             command=lambda: self.generate_from_template("OFICINA_ADMIN"))
        m_design.add_command(label="Plantilla: Consultorio Médico",
                             command=lambda: self.generate_from_template("CONSULTORIO_SALUD"))
        menubar.add_cascade(label="Diseño", menu=m_design)

        m_view = tk.Menu(menubar, **menu_kwargs())
        m_view.add_command(label="Zoom +\t+", command=lambda: self.zoom(1.25))
        m_view.add_command(label="Zoom −\t−", command=lambda: self.zoom(0.8))
        m_view.add_command(label="Encuadrar todo\tF",
                           command=self.fit_view)
        m_view.add_checkbutton(label="Cuadrícula", onvalue=True,
                               offvalue=False, variable=self._grid_var(),
                               command=self.redraw)
        menubar.add_cascade(label="Ver", menu=m_view)

        m_tools = tk.Menu(menubar, **menu_kwargs())
        m_tools.add_command(label="Validar proyecto",
                            command=self.run_validation)
        m_tools.add_command(label="Calcular cantidades (QTO)",
                            command=self.run_qto)
        m_tools.add_command(label="Calcular presupuesto",
                            command=self.run_budget)
        m_tools.add_command(label="Recalcular todo (QTO + presupuesto)",
                            command=self.run_recompute_all)
        m_tools.add_separator()
        m_tools.add_command(label="Informe descriptivo (Markdown)…",
                            command=self.export_report)
        menubar.add_cascade(label="Herramientas", menu=m_tools)

        m_help = tk.Menu(menubar, **menu_kwargs())
        m_help.add_command(label="Guía rápida…", accelerator="F1",
                           command=self.show_quick_guide)
        m_help.add_command(label="Atajos de teclado…",
                           command=self.show_shortcuts)
        m_help.add_command(label="Acerca de…", command=self.about)
        menubar.add_cascade(label="Ayuda", menu=m_help)
        self.config(menu=menubar)
        attach_menu_hints(menubar, self.status_var_for_menus())

    def status_var_for_menus(self) -> tk.StringVar:
        """Barra de estado aunque los menús se construyan antes."""
        if not hasattr(self, "status_var"):
            self.status_var = tk.StringVar(value="")
        return self.status_var

    def _grid_var(self) -> tk.BooleanVar:
        if not hasattr(self, "_show_grid"):
            self._show_grid = tk.BooleanVar(value=True)
        return self._show_grid

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=(8, 4))
        bar.pack(side="top", fill="x")

        self._tip(ttk.Button(bar, text="Guía rápida",
                             style="Guide.TButton",
                             command=self.show_quick_guide),
                  "guide").pack(side="left")

        self._tip(ttk.Button(bar, text="Encuadrar (F)",
                             command=self.fit_view),
                  "fit").pack(side="left", padx=(10, 0))
        self._tip(ttk.Button(bar, text="Zoom +",
                             command=lambda: self.zoom(1.25)),
                  "zoom_in").pack(side="left", padx=2)
        self._tip(ttk.Button(bar, text="Zoom −",
                             command=lambda: self.zoom(0.8)),
                  "zoom_out").pack(side="left")

        # Botones de edición rápida (FASE 90.1)
        self._tip(ttk.Button(bar, text="+ Objeto",
                             command=self.new_object_dialog),
                  "new_object").pack(side="left", padx=(12, 2))
        self._tip(ttk.Button(bar, text="⚡ Generar Planta (Asistente)",
                             style="Accent.TButton",
                             command=self.open_generative_wizard),
                  "generative_wizard").pack(side="left", padx=2)
        self._tip(ttk.Button(bar, text="Editar",
                             command=self.edit_property_dialog),
                  "edit").pack(side="left", padx=2)

        # Buscador §92: campo + texto
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y",
                                                   padx=8)
        self.search_field = ttk.Combobox(bar, values=list(SEARCH_FIELDS),
                                         width=11, state="readonly")
        self.search_field.set("Todo")
        self.search_field.pack(side="left")
        self._tip(self.search_field, "search_field")
        self.search_entry = ttk.Entry(bar, width=28)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda _e: self.run_search())
        self._tip(self.search_entry, "search_entry")
        self._tip(ttk.Button(bar, text="Buscar",
                             command=self.run_search),
                  "search_btn").pack(side="left")
        self._tip(ttk.Button(bar, text="Limpiar",
                             command=self.clear_search),
                  "clear_btn").pack(side="left", padx=2)

        # Filtro de nivel (solo disciplinas espaciales)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y",
                                                   padx=8)
        ttk.Label(bar, text="Nivel:").pack(side="left")
        self.level_var = tk.StringVar(value="")
        self.level_combo = ttk.Combobox(bar, textvariable=self.level_var,
                                        width=18, state="readonly",
                                        values=["(todos)"])
        self.level_combo.current(0)
        self.level_combo.bind("<<ComboboxSelected>>",
                              lambda _e: self.refresh_all())
        self.level_combo.pack(side="left", padx=2)
        self._tip(self.level_combo, "level_combo")

    # -- ayuda dinámica -------------------------------------------------------
    def _tip(self, widget: Any, key: str) -> Any:
        """Registra un globo de ayuda + eco en la barra de estado."""
        text = help_mod.TOOLTIPS.get(key, "")
        if not text:
            return widget
        self._tooltips.append(Tooltip(widget, text,
                                      self.status_var_for_menus(),
                                      restore=lambda: self._status_base))
        return widget

    def _say(self, message: str, hint: str = "") -> None:
        """Mensaje orientador en la barra de estado.

        Combina lo que acaba de pasar (message) con el paso siguiente
        sugerido (hint); también actualiza la línea base que los
        tooltips restauran al salir el cursor.
        """
        base = message if not hint else f"{message} → {hint}"
        self._status_base = base
        self.status_var.set(base)

    def _build_layout(self) -> None:
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(side="top", fill="both", expand=True)

        # -- Explorador de proyecto (§90 izquierda, §91) -----------------
        left = ttk.Frame(paned)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(left, orient="vertical",
                                    command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        paned.add(left, weight=1)

        # -- Canvas (§90 centro) ------------------------------------------
        center = ttk.Frame(paned)
        self.canvas = tk.Canvas(center, bg=theme.COL_CANVAS,
                                highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._tip(self.canvas, "canvas")
        hint = ttk.Label(center,
                         text="Rueda: zoom · Arrastrar (botón central/derecho): "
                              "mover · Clic: seleccionar · Doble clic: editar "
                              "o encuadrar",
                         style="Hint.TLabel")
        hint.pack(side="bottom", fill="x")
        self._tip(hint, "hint_bar")
        paned.add(center, weight=4)

        # -- Propiedades (§90 derecha) --------------------------------------
        right = ttk.Frame(paned)
        self.props = ttk.Treeview(right, columns=("valor",), show="headings",
                                  selectmode="none", height=22)
        self.props.heading("valor", text="Valor")
        self.props.column("#0", width=140, stretch=False)
        self.props.column("valor", width=180, stretch=True)
        props_scroll = ttk.Scrollbar(right, orient="vertical",
                                     command=self.props.yview)
        self.props.configure(yscrollcommand=props_scroll.set)
        self.props.pack(side="top", fill="both", expand=True)
        props_scroll.pack(side="right", fill="y")
        self._tip(ttk.Button(right, text="Editar propiedad… (Ctrl+E)",
                             command=self.edit_property_dialog),
                  "props_edit").pack(side="bottom", fill="x", pady=2)
        self._tip(ttk.Button(right, text="Estado de la entidad…",
                             command=self.change_state_dialog),
                  "state_btn").pack(side="bottom", fill="x", pady=2)
        paned.add(right, weight=1)

        # -- Panel inferior: avisos / log / cálculos (§90 abajo) ------------
        bottom = ttk.Notebook(self, height=170)
        self.warnings_text = tk.Text(bottom, height=6, state="disabled",
                                     wrap="word", font=("TkFixedFont", 9),
                                     background=theme.COL_FIELD,
                                     foreground=theme.COL_TEXT,
                                     insertbackground=theme.COL_TEXT,
                                     relief="flat", padx=8, pady=6)
        bottom.add(self.warnings_text, text="Avisos")
        self.log_text = tk.Text(bottom, height=6, state="disabled",
                                wrap="word", font=("TkFixedFont", 9),
                                background=theme.COL_FIELD,
                                foreground=theme.COL_TEXT,
                                insertbackground=theme.COL_TEXT,
                                relief="flat", padx=8, pady=6)
        bottom.add(self.log_text, text="Log")
        calc_frame = ttk.Frame(bottom)
        self.calc_tree = ttk.Treeview(
            calc_frame, columns=("tipo", "estado", "objetos", "ms", "fecha"),
            show="headings", selectmode="none", height=6)
        for column, text, width in (
                ("tipo", "Cálculo", 150), ("estado", "Estado", 100),
                ("objetos", "Objetos", 70), ("ms", "ms", 60),
                ("fecha", "Fecha", 170)):
            self.calc_tree.heading(column, text=text)
            self.calc_tree.column(column, width=width, anchor="w")
        calc_scroll = ttk.Scrollbar(calc_frame, orient="vertical",
                                    command=self.calc_tree.yview)
        self.calc_tree.configure(yscrollcommand=calc_scroll.set)
        self.calc_tree.pack(side="left", fill="both", expand=True)
        calc_scroll.pack(side="right", fill="y")
        bottom.add(calc_frame, text="Estado de cálculos")
        bottom.pack(side="bottom", fill="x")
        # Ayuda dinámica en las pestañas del panel inferior
        for tab_widget, key in ((self.warnings_text, "warnings_tab"),
                                (self.log_text, "log_tab"),
                                (self.calc_tree, "calc_tab")):
            self._tip(tab_widget, key)

    def _build_statusbar(self) -> None:
        self.status_var_for_menus()  # garantiza una única instancia
        bar = ttk.Frame(self, padding=(2, 0))
        bar.pack(side="bottom", fill="x")
        left = ttk.Label(bar, textvariable=self.status_var, anchor="w",
                         padding=(6, 3))
        left.pack(side="left", fill="x", expand=True)
        self._info_var = tk.StringVar(value="")
        middle = ttk.Label(bar, textvariable=self._info_var, anchor="e",
                           padding=(6, 3))
        middle.pack(side="right")
        self._coord_var = tk.StringVar(value="x: —, y: —")
        right = ttk.Label(bar, textvariable=self._coord_var, anchor="e",
                          padding=(6, 3), width=24)
        right.pack(side="right")

    # -- eventos del lienzo -------------------------------------------------
    def _wire_canvas(self) -> None:
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<Button-2>", self.on_pan_start)
        self.canvas.bind("<ButtonRelease-2>", self.on_pan_end)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<Button-3>", self.on_pan_start)
        self.canvas.bind("<ButtonRelease-3>", self.on_pan_end)
        self.canvas.bind("<B3-Motion>", self.on_pan_move)
        # Rueda del ratón: Windows/macOS <MouseWheel>, Linux Button-4/5
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at_event(1.1, e))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at_event(1 / 1.1, e))
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Configure>", lambda _e: self.redraw())

    def _on_wheel(self, event) -> None:
        # Delta con signo en Windows; delta crudo en macOS.
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._zoom_at_event(factor, event)

    def _on_motion(self, event) -> None:
        """Coordenadas de mundo bajo el cursor (lectura en la barra)."""
        if self._coord_var is None:
            return
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 600)
        wx, wy = self.viewport.from_screen(event.x, event.y, width, height)
        self._coord_var.set(f"x: {wx:.2f} m, y: {wy:.2f} m")

    def _zoom_at_event(self, factor: float, event) -> None:
        """Zoom anclado al cursor (FASE 90.1)."""
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 600)
        self.viewport.zoom_at(factor, event.x, event.y, width, height)
        self.redraw()

    def _subscribe_events(self) -> None:
        self.ctx.event_bus.subscribe("*", self._on_bus_event)

    def _on_bus_event(self, event) -> None:
        try:
            self.after(0, self._handle_bus_event, event)
        except Exception:  # noqa: BLE001 - ventana ya destruida
            pass

    def _handle_bus_event(self, event) -> None:
        self.refresh_log()
        self.refresh_statusbar()

    # -- datos: explorador, canvas, propiedades -----------------------------
    def _level_filter(self) -> str:
        value = self.level_var.get()
        if not value or value == "(todos)":
            return ""
        for level_id, name in self.explorer._level_names.items():
            if name == value:
                return level_id
        return ""

    def refresh_all(self, fit: bool = False) -> None:
        self.refresh_levels()
        self.refresh_tree()
        self.redraw(fit=fit)
        self.refresh_properties()
        self.refresh_log()
        self.refresh_calcs()
        self.refresh_statusbar()

    def refresh_levels(self) -> None:
        self.explorer._refresh_names()
        names = ["(todos)"] + sorted(
            (n for n in self.explorer._level_names.values() if n))
        current = self.level_var.get() or "(todos)"
        self.level_combo.configure(values=names)
        if current in names:
            self.level_combo.set(current)
        else:
            self.level_combo.set("(todos)")

    def refresh_tree(self) -> None:
        search = self.search_entry.get().strip()
        self.tree.delete(*self.tree.get_children())
        if search:
            self._fill_tree_results()
        else:
            self._fill_tree_disciplines()

    def _fill_tree_disciplines(self) -> None:
        level_id = self._level_filter()
        for discipline in DISCIPLINES:
            node = self.tree.insert("", "end",
                                    iid=f"disc:{discipline.key}",
                                    text=f"{discipline.label} "
                                         f"({discipline.key})",
                                    open=(discipline.key
                                          == self.current_discipline))
            for row in self.explorer.rows_for(discipline.key, level_id):
                if self.tree.exists(row.uid):
                    continue  # defensive: same entity listed twice
                text = f"{row.code} — {row.name}".strip(" —")
                if row.summary:
                    text = f"{text}  [{row.summary}]"
                self.tree.insert(node, "end", iid=row.uid,
                                 text=text or row.uid)

    def _fill_tree_results(self) -> None:
        results = self._result_rows
        root = self.tree.insert("", "end", iid="results",
                                text=f"Resultados ({len(results)})",
                                open=True)
        for index, row in enumerate(results):
            text = (f"[{discipline_label(row.discipline)}] "
                    f"{row.type} · {row.code} {row.name}").strip()
            self.tree.insert(root, "end", iid=f"res:{index}",
                             text=text or row.uid)

    def redraw(self, fit: bool = False) -> None:
        self.canvas.delete("all")
        level_id = self._level_filter()
        self._primitives = self.canvas_model.primitives(
            self.current_discipline, level_id)
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 600)
        if fit:
            bounds = self.viewport.bounds_of(self._primitives)
            if bounds:
                self.viewport.fit(bounds, width, height)
        if self._grid_var().get():
            self._draw_grid(width, height)
        self._draw_primitives(width, height)
        if not self._primitives:
            level_name = self.level_var.get()
            if level_name and level_name != "(todos)":
                self._draw_empty_level_card(width, height, level_name)
            else:
                self._draw_welcome(width, height)

    def _draw_empty_level_card(self, width: int, height: int, level_name: str) -> None:
        """Tarjeta interactiva cuando se selecciona un nivel vacío."""
        card_w, card_h = 520, 240
        x0, y0 = width // 2 - card_w // 2, height // 2 - card_h // 2
        card_tag = "card_empty_lvl"
        self.canvas.create_rectangle(
            x0, y0, x0 + card_w, y0 + card_h,
            fill=CANVAS_DARK["welcome_card"],
            outline=CANVAS_DARK["accent"], width=2, tags=(card_tag, "clickable"))
        cx = width // 2
        self.canvas.create_text(
            cx, y0 + 36, text=f"Nivel «{level_name}» (Sin elementos)",
            fill=CANVAS_DARK["welcome_title"],
            font=("TkDefaultFont", 13, "bold"), tags=(card_tag,))
        msg = (
            f"El nivel «{level_name}» está seleccionado pero aún no contiene muros ni locales.\n\n"
            "Puedes usar el Asistente de Diseño Generativo para generar su planta\n"
            "automática con locales, requerimientos climáticos, estructura y MEP,\n"
            "o añadir elementos manualmente con «+ Objeto».")
        self.canvas.create_text(
            cx, y0 + 105, text=msg,
            fill=CANVAS_DARK["space_text"], font=("TkDefaultFont", 10),
            justify="center", tags=(card_tag,))

        # Botón visual de acción
        btn_w, btn_h = 340, 36
        bx0, by0 = cx - btn_w // 2, y0 + card_h - 55
        self.canvas.create_rectangle(
            bx0, by0, bx0 + btn_w, by0 + btn_h,
            fill="#007acc", outline="#005999", width=1, tags=(card_tag, "btn_wizard"))
        self.canvas.create_text(
            cx, by0 + btn_h // 2,
            text="⚡ Abrir Asistente Generativo para este nivel",
            fill="#ffffff", font=("TkDefaultFont", 10, "bold"), tags=(card_tag, "btn_wizard"))

        def _on_card_click(_event=None):
            self.open_generative_wizard(target_level=level_name)

        self.canvas.tag_bind(card_tag, "<Button-1>", _on_card_click)

    def _draw_welcome(self, width: int, height: int) -> None:
        """Tarjeta de bienvenida cuando el lienzo está vacío.

        En lugar de un plano en blanco, ofrece los tres primeros pasos
        del flujo para que la app se explique sola (no abruma: son
        solo acciones, sin tecnicismos).
        """
        searching = bool(self.search_entry.get().strip()) if \
            hasattr(self, "search_entry") else False
        if searching:
            self.canvas.create_text(
                width // 2, height // 2,
                text="Sin resultados para esta búsqueda",
                fill=CANVAS_DARK["welcome_text"],
                font=("TkDefaultFont", 12), justify="center")
            return
        card_w, card_h = 460, 250
        x0, y0 = width // 2 - card_w // 2, height // 2 - card_h // 2
        self.canvas.create_rectangle(
            x0, y0, x0 + card_w, y0 + card_h,
            fill=CANVAS_DARK["welcome_card"],
            outline=CANVAS_DARK["welcome_border"], width=2)
        cx = width // 2
        self.canvas.create_text(
            cx, y0 + 36, text="Empecemos con tu proyecto",
            fill=CANVAS_DARK["welcome_title"],
            font=("TkDefaultFont", 14, "bold"))
        steps = (
            "1 · Crea un nivel y un local con «+ Objeto»\n"
            "2 · Dibuja muros y coloca puertas o ventanas\n"
            "3 · Calcula con Herramientas ▸ Recalcular todo\n"
            "4 · Exporta o genera el informe cuando estés listo")
        self.canvas.create_text(
            cx, y0 + 112, text=steps,
            fill=CANVAS_DARK["space_text"], font=("TkDefaultFont", 11),
            justify="left")
        self.canvas.create_text(
            cx, y0 + card_h - 42,
            text="¿Prefieres ver un ejemplo?\n"
                 "Archivo ▸ Proyecto de demostración",
            fill=CANVAS_DARK["welcome_text"], font=("TkDefaultFont", 10),
            justify="center")

    def _draw_grid(self, width: int, height: int) -> None:
        step_m = 1 if self.viewport.scale >= 8 else \
            5 if self.viewport.scale >= 2 else 25
        x0, y0 = self.viewport.from_screen(0, 0, width, height)
        x1, y1 = self.viewport.from_screen(width, height, width, height)
        x = int(x0 // step_m) * step_m
        while x <= x1:
            px = self.viewport.to_screen(x, 0, width, height)[0]
            color = PALETTE["axis"] if abs(x) < 1e-9 else PALETTE["grid"]
            self.canvas.create_line(px, 0, px, height, fill=color)
            x += step_m
        y = int(y0 // step_m) * step_m
        while y <= y1:
            py = self.viewport.to_screen(0, y, width, height)[1]
            color = PALETTE["axis"] if abs(y) < 1e-9 else PALETTE["grid"]
            self.canvas.create_line(0, py, width, py, fill=color)
            y += step_m

    def _draw_primitives(self, width: int, height: int) -> None:
        for primitive in self._primitives:
            color = PALETTE.get(primitive.color_key, PALETTE["wall"])
            points: List[float] = []
            for x, y in primitive.coords:
                px, py = self.viewport.to_screen(x, y, width, height)
                points.extend((px, py))
            if primitive.kind == "space":
                self.canvas.create_polygon(
                    points, fill=CANVAS_DARK["space_fill"], outline=color,
                    width=1, tags=(primitive.row.uid,))
                self._space_label(primitive, width, height)
            elif primitive.kind == "wall":
                self.canvas.create_polygon(
                    points, fill=color, outline="", tags=(primitive.row.uid,))
            elif primitive.kind == "opening":
                self.canvas.create_line(
                    points, fill=color, width=4,
                    capstyle="round", tags=(primitive.row.uid,))
            elif primitive.kind == "node":
                px, py = self.viewport.to_screen(
                    primitive.coords[0][0], primitive.coords[0][1],
                    width, height)
                self.canvas.create_oval(
                    px - 6, py - 6, px + 6, py + 6, fill=color,
                    outline="", tags=(primitive.row.uid,))
            elif primitive.kind in ("segment", "element"):
                self.canvas.create_line(
                    points, fill=color,
                    width=3 if primitive.kind == "element" else 2,
                    tags=(primitive.row.uid,))
        if self.selection is not None:
            self._highlight_selection(width, height)

    def _space_label(self, primitive, width: int, height: int) -> None:
        xs = [p[0] for p in primitive.coords]
        ys = [p[1] for p in primitive.coords]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        px, py = self.viewport.to_screen(cx, cy, width, height)
        text = primitive.row.name
        if self.viewport.scale >= 10:
            text = f"{text}\n{primitive.row.summary or ''}".strip()
        self.canvas.create_text(px, py, text=text, justify="center",
                                font=("TkDefaultFont", 8),
                                fill=CANVAS_DARK["space_text"])

    def _highlight_selection(self, width: int, height: int) -> None:
        for primitive in self._primitives:
            if primitive.row.uid != self.selection.uid:
                continue
            points: List[float] = []
            for x, y in primitive.coords:
                px, py = self.viewport.to_screen(x, y, width, height)
                points.extend((px, py))
            if primitive.kind in ("node",):
                px, py = self.viewport.to_screen(
                    primitive.coords[0][0], primitive.coords[0][1],
                    width, height)
                self.canvas.create_oval(px - 9, py - 9, px + 9, py + 9,
                                        outline=PALETTE["selection"],
                                        width=2)
            elif len(points) >= 4:
                self.canvas.create_line(
                    points, fill=PALETTE["selection"], width=2,
                    dash=(4, 2))
                if primitive.kind in ("space", "wall"):
                    self.canvas.create_polygon(points, fill="",
                                               outline=PALETTE["selection"],
                                               width=2)

    # -- interacción ---------------------------------------------------------
    def on_tree_select(self, _event=None) -> None:
        iid = self.tree.focus()
        if not iid or iid.startswith(("disc:", "results", "res:")):
            return
        row = self._find_row(iid)
        if row is None:
            return
        if iid.startswith("res:"):
            # Un resultado de búsqueda cambia a su disciplina.
            self.current_discipline = row.discipline
            self.search_entry.delete(0, "end")
            self._result_rows = []
            self.refresh_all()
            self.tree.selection_set(row.uid)
            self.tree.focus(row.uid)
            return
        self.selection = row
        self.refresh_properties()
        self.redraw()

    def _find_row(self, uid: str) -> Optional[ObjectRow]:
        if self._result_rows:
            index = uid[len("res:"):] if uid.startswith("res:") else None
            if index is not None and index.isdigit():
                return self._result_rows[int(index)]
        level_id = self._level_filter()
        for row in self.explorer.rows_for(self.current_discipline, level_id):
            if row.uid == uid:
                return row
        return None

    def on_canvas_click(self, event) -> None:
        items = self.canvas.find_withtag("current")
        if not items:
            return
        tags = self.canvas.gettags(items[0])
        for tag in tags:
            row = self._find_row(tag)
            if row is not None:
                self.selection = row
                self.refresh_properties()
                self.redraw()
                return

    def on_canvas_double_click(self, event) -> None:
        """Doble clic sobre un objeto: sus propiedades; sobre vacío: encuadrar."""
        items = self.canvas.find_withtag("current")
        if not items:
            self.fit_view()
            return
        tags = self.canvas.gettags(items[0])
        for tag in tags:
            row = self._find_row(tag)
            if row is not None:
                self.selection = row
                self.refresh_properties()
                self.redraw()
                self.edit_property_dialog()
                return

    def on_pan_start(self, event) -> None:
        self._pan_start = (event.x, event.y)

    def on_pan_move(self, event) -> None:
        if self._pan_start is None:
            return
        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]
        self._pan_start = (event.x, event.y)
        self.viewport.center_x -= dx / self.viewport.scale
        self.viewport.center_y += dy / self.viewport.scale
        self.redraw()

    def on_pan_end(self, _event=None) -> None:
        self._pan_start = None

    def zoom(self, factor: float) -> None:
        self.viewport.zoom(factor)
        self.redraw()

    def fit_view(self) -> None:
        self.redraw(fit=True)

    # -- buscador §92 ----------------------------------------------------------
    def run_search(self) -> None:
        query = self.search_entry.get()
        field = self.search_field.get()
        self._result_rows = self.search_engine.search(
            query, field, level_id=self._level_filter())
        self.refresh_tree()
        if self._result_rows:
            self._say(
                f"Búsqueda «{query}»: {len(self._result_rows)} "
                "resultado(s)",
                next_hint(searching=True))
        else:
            self._say(
                f"Sin resultados para «{query}». Prueba con otro término "
                "o cambia el campo de búsqueda (por ejemplo, «Nombre»).",
                "Pulsa Escape o «Limpiar» para volver al árbol")

    def clear_search(self) -> None:
        self.search_entry.delete(0, "end")
        self._result_rows = []
        self.refresh_tree()
        self._say("Búsqueda limpia: de nuevo ves el árbol completo del "
                  "proyecto.",
                  next_hint(**self._project_stats()))

    # -- propiedades ---------------------------------------------------------------
    def refresh_properties(self) -> None:
        self.props.delete(*self.props.get_children())
        if self.selection is None:
            self.props.insert("", "end", iid="prop:hint",
                              values=("Selecciona un objeto en el "
                                      "explorador o en el plano y sus "
                                      "datos aparecerán aquí",))
            return
        row = self.selection
        editable = set()
        if row.entity is not None:
            editable = set(PropertyEditor.EDITABLE_FIELDS.get(
                row.entity.ENTITY_TYPE, ()))
        for field_name, value in PropertiesModel.properties(row):
            mark = "✎ " if field_name in editable else ""
            self.props.insert("", "end", iid=f"prop:{field_name}",
                              text=mark + field_name, values=(value,))
        if editable:
            self.props.bind("<Double-1>", self._on_prop_double_click)

    def _on_prop_double_click(self, _event=None) -> None:
        iid = self.props.focus()
        if iid.startswith("prop:"):
            self.edit_property_dialog(iid[len("prop:"):])

    # -- estados §93 ------------------------------------------------------------------
    def change_state_dialog(self) -> None:
        if self.selection is None or self.selection.entity is None:
            messagebox.showinfo(
                "Estado de la entidad",
                "Selecciona antes un objeto (no un grupo ni un cálculo): "
                "los estados describen su ciclo de vida, de borrador a "
                "archivado.", parent=self)
            return
        entity = self.selection.entity
        current = (entity.status.value if hasattr(entity.status, "value")
                   else str(entity.status))
        options = EntityStateFlow.next_states(current)
        if not options:
            messagebox.showinfo(
                "Estado de la entidad",
                f"El estado «{current}» es final: no admite más "
                "transiciones.",
                parent=self)
            return
        dialog = tk.Toplevel(self)
        dialog.title("Estado de la entidad")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=f"{self.selection.code} — estado actual: "
                               f"{current}").pack(anchor="w", padx=10,
                                                  pady=(10, 4))
        ttk.Label(dialog,
                  text="Elige el siguiente estado del objeto:",
                  style="Dim.TLabel").pack(anchor="w", padx=10)
        chosen = tk.StringVar(value=options[0])
        for option in options:
            ttk.Radiobutton(dialog, text=option, value=option,
                            variable=chosen).pack(anchor="w", padx=16)
        def apply() -> None:
            try:
                self.state_service.change_status(self.selection, chosen.get())
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Estado de la entidad", str(exc),
                                     parent=dialog)
                return
            dialog.destroy()
            self.refresh_all()
            self._say(f"Estado de {self.selection.code} cambiado a "
                      f"{chosen.get()}.",
                      "El historial del objeto queda registrado en la "
                      "auditoría")
        ttk.Button(dialog, text="Aplicar", style="Accent.TButton",
                   command=apply).pack(
            side="right", padx=10, pady=10)
        ttk.Button(dialog, text="Cancelar",
                   command=dialog.destroy).pack(side="right")

    # -- herramientas -------------------------------------------------------------
    def _project_stats(self) -> Dict[str, int]:
        """Resumen del proyecto para el motor de sugerencias."""
        rows = self.explorer.all_rows()
        def _count(discipline: str, type_name: str) -> int:
            return sum(1 for r in rows.get(discipline, [])
                       if r.type == type_name)
        calcs = len(self.status_model.calculation_rows(limit=50))
        return {"spaces": _count("ARCHITECTURE", "SPACE"),
                "walls": _count("ARCHITECTURE", "WALL"),
                "doors": _count("ARCHITECTURE", "DOOR") +
                         _count("ARCHITECTURE", "WINDOW"),
                "calculations": calcs}

    def run_validation(self) -> None:
        lines = self.status_model.validation_warnings()
        self.warnings_text.configure(state="normal")
        self.warnings_text.delete("1.0", "end")
        self.warnings_text.insert("1.0", "\n".join(lines) or
                                  "Sin hallazgos: el proyecto pasa la "
                                  "validación sin incidencias.")
        self.warnings_text.configure(state="disabled")
        stats = self._project_stats()
        stats["warnings"] = len(lines)
        if lines:
            self._say(f"Validación: {len(lines)} hallazgo(s) en la "
                      "pestaña «Avisos».", next_hint(**stats))
        else:
            self._say("Validación limpia: todo en orden.",
                      next_hint(**stats))

    def run_qto(self) -> None:
        from services.quantity_service import QuantityService
        stats = QuantityService(self.ctx).compute_all()
        self.refresh_calcs()
        self.refresh_statusbar()
        processed = stats.get('objects_processed', 0)
        self._say(f"Cantidades calculadas para {processed} objeto(s).",
                  "Abre la disciplina «Cantidades» en el explorador "
                  "para ver los resultados")

    def run_budget(self) -> None:
        from services.budget_service import BudgetService
        total = BudgetService(self.ctx).compute()
        self.refresh_calcs()
        self._say(f"Presupuesto calculado: {total:,.2f} "
                  f"{self.ctx.project.currency}.",
                  "Abre la disciplina «Presupuesto» en el explorador "
                  "para ver el desglose")

    def undo(self) -> None:
        from app.undo_service import PersistentUndoService
        try:
            result = PersistentUndoService(self.ctx).undo()
            self.ctx.commit()
            self.refresh_all()
            self._say(f"Deshecho: {result['command']}.",
                      "¿Te arrepientes? Ctrl+Y vuelve a rehacerlo")
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning("Deshacer", str(exc), parent=self)

    def redo(self) -> None:
        from app.undo_service import PersistentUndoService
        try:
            result = PersistentUndoService(self.ctx).redo()
            self.ctx.commit()
            self.refresh_all()
            self._say(f"Rehecho: {result['command']}.",
                      "Ctrl+Z lo vuelve a deshacer si lo necesitas")
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning("Rehacer", str(exc), parent=self)

    # -- atajos y acciones rápidas (FASE 90.1) ---------------------------------
    def save_project(self) -> None:
        self.ctx.commit()
        self._say("Proyecto guardado: todos los cambios están a salvo "
                  "(SQLite).",
                  next_hint(**self._project_stats()))

    def focus_search(self) -> None:
        self.search_field.focus_set()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def zoom_in(self) -> None:
        self.zoom(1.25)

    def zoom_out(self) -> None:
        self.zoom(0.8)

    # -- atajos y ayuda -----------------------------------------------------------
    def show_quick_guide(self) -> None:
        """Recorrido de 4 pasos: qué hace esta pantalla y en qué orden."""
        dialog = tk.Toplevel(self)
        dialog.title("Guía rápida de ARQ GEN")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(background=theme.COL_BG_ALT)
        header = ttk.Frame(dialog, style="Panel.TFrame", padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Todo lo que necesitas son 4 pasos",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(header,
                  text="Pasa el cursor por cualquier botón y la barra "
                       "inferior te explicará qué hace.",
                  style="Dim.TLabel").pack(anchor="w", pady=(2, 0))
        body = ttk.Frame(dialog, padding=(16, 8))
        body.pack(fill="both", expand=True)
        for title, text in GUIDE_STEPS:
            card = ttk.Frame(body, style="Card.TFrame", padding=(12, 8))
            card.pack(fill="x", pady=4)
            ttk.Label(card, text=title, style="Accent.TLabel",
                      font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            ttk.Label(card, text=text, style="Guide.TLabel",
                      wraplength=520, justify="left").pack(anchor="w",
                                                          pady=(2, 0))
        ttk.Button(dialog, text="Entendido, a trabajar",
                   style="Accent.TButton",
                   command=dialog.destroy).pack(pady=(4, 12))
        dialog.wait_window()

    def show_shortcuts(self) -> None:
        labels = {
            "Ctrl+N": "Nuevo proyecto", "Ctrl+O": "Abrir proyecto",
            "Ctrl+S": "Guardar (commit)", "Ctrl+Z": "Deshacer",
            "Ctrl+Y": "Rehacer", "Ctrl+F": "Buscador",
            "Ctrl+E": "Editar propiedad", "Supr": "Eliminar selección",
            "+ / −": "Zoom", "F": "Encuadrar todo",
            "Escape": "Limpiar buscador", "F1": "Guía rápida",
        }
        lines = "\n".join(f"{key:>12}  {label}" for key, label in
                          labels.items())
        messagebox.showinfo("Atajos de teclado", lines, parent=self)

    # -- edición de propiedades (FASE 90.1) -------------------------------------
    def edit_property_dialog(self, field_name: str = "") -> None:
        if self.selection is None or self.selection.entity is None:
            messagebox.showinfo(
                "Editar propiedad",
                "Primero selecciona un objeto (en el explorador o en el "
                "plano). Los campos que admiten edición aparecen marcados "
                "con ✎ en el panel derecho.", parent=self)
            return
        entity = self.selection.entity
        fields = PropertyEditor.editable_fields(entity)
        if not fields:
            messagebox.showinfo(
                "Editar propiedad",
                f"Los objetos de tipo {entity.ENTITY_TYPE} no admiten "
                "edición de campos: sus datos se calculan solos.",
                parent=self)
            return
        if not field_name:
            field_name = fields[0][0]
        current = PropertyEditor.format_value(getattr(entity, field_name))
        dialog = tk.Toplevel(self)
        dialog.title(f"Editar {entity.ENTITY_TYPE}.{field_name}")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=f"{self.selection.code} · {field_name}",
                  font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", padx=10, pady=(10, 2))
        entry = ttk.Entry(dialog, width=34)
        entry.insert(0, current)
        entry.pack(anchor="w", padx=10, pady=4)
        entry.select_range(0, "end")
        field_hint = FIELD_HINTS.get(
            field_name,
            "El valor debe ser válido para el tipo del campo "
            "(texto o número).")
        ttk.Label(dialog, text=field_hint, style="Dim.TLabel",
                  wraplength=300, justify="left").pack(
            anchor="w", padx=10, pady=(0, 4))

        def apply() -> None:
            try:
                self.edit_service.edit(self.selection, field_name,
                                       entry.get())
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Editar propiedad", str(exc),
                                     parent=dialog)
                return
            dialog.destroy()
            self.refresh_tree()
            self.refresh_properties()
            self.redraw()
            self._say(f"Editado {self.selection.code}.{field_name} = "
                      f"{entry.get()}.",
                      "Los cambios ya están en el diario; Ctrl+S los "
                      "consolida")
        entry.bind("<Return>", lambda _e: apply())
        ttk.Button(dialog, text="Aplicar", command=apply).pack(
            side="right", padx=10, pady=10)
        ttk.Button(dialog, text="Cancelar",
                   command=dialog.destroy).pack(side="right")
        entry.focus_set()

    # -- borrado (FASE 90.1) ------------------------------------------------------
    def delete_selection(self) -> None:
        if self.selection is None or self.selection.entity is None:
            messagebox.showinfo(
                "Eliminar selección",
                "Primero selecciona un objeto real (creado por ti) para "
                "eliminar. Si no es lo que buscabas, la operación se "
                "puede deshacer con Ctrl+Z.", parent=self)
            return
        row = self.selection
        if not messagebox.askyesno(
                "Eliminar selección",
                f"¿Eliminar {row.type} {row.code} — {row.name}?\n\n"
                "Tranquilidad: la operación queda registrada y puedes "
                "deshacerla con Ctrl+Z.", parent=self):
            return
        try:
            code = self.edit_service.delete(row)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Eliminar selección", str(exc), parent=self)
            return
        self.selection = None
        self.refresh_all()
        self._say(f"Eliminado {row.type} {code}.",
                  "¿Fue un error? Ctrl+Z lo recupera al instante")

    # -- creación de objetos (FASE 90.1) -------------------------------------------
    def new_object_dialog(self) -> None:
        entity_type = self._ask_entity_type()
        if not entity_type:
            return
        spec = CREATE_SPECS[entity_type][1]
        dialog = tk.Toplevel(self)
        dialog.title(f"Nuevo objeto — {entity_type}")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog,
                  text="Los campos con * son obligatorios; el resto puede "
                       "dejarlos como están.",
                  style="Dim.TLabel", wraplength=340,
                  justify="left").pack(anchor="w", padx=10, pady=(8, 4))
        entries: Dict[str, Any] = {}
        for index, (param, label, kind, required, options,
                    default) in enumerate(spec):
            row_frame = ttk.Frame(dialog)
            row_frame.pack(fill="x", padx=10, pady=2)
            mark = "* " if required else ""
            ttk.Label(row_frame, text=mark + label, width=28).pack(side="left")
            if kind == "choice":
                values = list(options) if options else \
                    self.edit_service.choices(options or "")
                combo = ttk.Combobox(row_frame, values=values, width=24,
                                     state="readonly")
                if default and default in values:
                    combo.set(default)
                combo.pack(side="left", fill="x", expand=True)
                entries[param] = combo
                self._field_tip(combo, param)
                continue
            entry = ttk.Entry(row_frame, width=26)
            if default not in ("", None):
                entry.insert(0, str(default))
            entry.pack(side="left", fill="x", expand=True)
            entries[param] = entry
            self._field_tip(entry, param)

        def apply() -> None:
            values = {param: widget.get() for param, widget in entries.items()}
            try:
                entity = self.edit_service.create(entity_type, values)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Nuevo objeto", str(exc), parent=dialog)
                return
            dialog.destroy()
            self.refresh_all()
            if entity_type == "LEVEL":
                lvl_name = getattr(entity, "name", "") or getattr(entity, "code", "")
                self.level_var.set(lvl_name)
                self.refresh_all(fit=True)
                if messagebox.askyesno(
                    "Nivel Creado",
                    f"Se ha creado el nivel «{lvl_name}».\n\n"
                    "¿Deseas abrir el Asistente Generativo para diseñar automáticamente "
                    "su planta arquitectónica con todos sus requerimientos (locales, clima, estructura, MEP)?",
                    parent=self
                ):
                    self.open_generative_wizard(target_level=lvl_name)
                    return
            self._say(f"Creado {entity_type} "
                      f"{getattr(entity, 'code', '')}.",
                      "Sigue construyendo con «+ Objeto» o edítalo con "
                      "doble clic")

        ttk.Button(dialog, text="Crear", style="Accent.TButton",
                   command=apply).pack(
            side="right", padx=10, pady=10)
        ttk.Button(dialog, text="Cancelar",
                   command=dialog.destroy).pack(side="right")

    def _field_tip(self, widget: Any, param: str) -> None:
        """Ayuda específica del campo en formularios de creación."""
        hint = FIELD_HINTS.get(param)
        if hint:
            self._tooltips.append(Tooltip(widget, hint,
                                          self.status_var_for_menus(),
                                          restore=lambda: self._status_base))

    def _ask_entity_type(self) -> str:
        """Elige tipo de objeto: por defecto, los de la disciplina activa."""
        available = list(CREATE_SPECS)
        preferred = {
            "ARCHITECTURE": ["SPACE", "WALL", "DOOR", "WINDOW", "LEVEL",
                             "ZONE"],
            "STRUCTURE": ["ELEMENT", "MATERIAL", "SECTION"],
            "INSTALLATIONS": ["NETWORK", "NODE"],
        }.get(self.current_discipline, [])
        ordered = [t for t in preferred if t in available] + \
                  [t for t in available if t not in preferred]
        dialog = tk.Toplevel(self)
        dialog.title("Nuevo objeto")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog,
                  text="¿Qué quieres crear? Te proponemos primero los "
                       "objetos de la disciplina activa.",
                  style="Dim.TLabel", wraplength=320,
                  justify="left").pack(anchor="w", padx=10,
                                       pady=(10, 4))
        combo = ttk.Combobox(dialog, values=ordered, state="readonly",
                             width=24)
        if ordered:
            combo.set(ordered[0])
        combo.pack(anchor="w", padx=10, fill="x", expand=True)
        chosen: Dict[str, str] = {}

        def ok() -> None:
            chosen["type"] = combo.get()
            dialog.destroy()
        ttk.Button(dialog, text="Continuar", command=ok).pack(
            side="right", padx=10, pady=10)
        ttk.Button(dialog, text="Cancelar",
                   command=dialog.destroy).pack(side="right")
        dialog.wait_window()
        return chosen.get("type", "")

    # -- herramientas adicionales (FASE 90.1) -------------------------------------
    def run_recompute_all(self) -> None:
        from services.budget_service import BudgetService
        from services.quantity_service import QuantityService
        stats = QuantityService(self.ctx).compute_all()
        total = BudgetService(self.ctx).compute()
        self.refresh_all()
        self._say(
            f"Cálculos completos: {stats.get('objects_processed', 0)} "
            f"objetos · presupuesto {total:,.2f} "
            f"{self.ctx.project.currency}.",
            "Echa un vistazo a las disciplinas «Cantidades» y "
            "«Presupuesto» del explorador")

    def open_generative_wizard(self, target_level: str = "") -> None:
        """Abre el asistente de diseño generativo automático en 2 pasos."""
        from ui.generative_wizard import GenerativeWizardDialog
        curr = target_level or (self.level_var.get() if self.level_var.get() != "(todos)" else "")
        GenerativeWizardDialog(self, self.ctx, current_level=curr, on_generated=self._on_wizard_generated)

    def _on_wizard_generated(self, result: Dict[str, Any]) -> None:
        """Callback ejecutado tras completar la generación de la planta arquitectónica."""
        level_name = result.get("level_name", "Planta Baja")
        self.refresh_levels()
        self.level_var.set(level_name)
        self.refresh_all(fit=True)
        self.fit_view()
        summary = result.get("summary", {})
        self._say(
            f"⚡ Planta de «{level_name}» generada: {summary.get('spaces', 0)} locales, "
            f"{summary.get('walls', 0)} muros, {summary.get('doors', 0)} puertas, "
            f"{summary.get('windows', 0)} ventanas.",
            "Visualiza la planta en el lienzo, edita entidades o exporta a DXF/IFC/XLSX")

    def generate_from_template(self, template_key: str) -> None:
        """Generación directa a partir de una plantilla arquitectónica típica."""
        from services.generative_architecture_service import GenerativeArchitectureService
        curr_lvl = self.level_var.get()
        target_lvl = curr_lvl if curr_lvl and curr_lvl != "(todos)" else "Planta Baja"
        try:
            gen = GenerativeArchitectureService(self.ctx)
            result = gen.generate(template_key=template_key, level_ref=target_lvl, clean_level=True)
            self._on_wizard_generated(result)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Generador", str(exc), parent=self)

    def export_report(self) -> None:
        from services.documentation_service import DocumentationService
        path = filedialog.asksaveasfilename(
            title="Informe del proyecto (Markdown)",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Texto", "*.txt")])
        if not path:
            return
        report = DocumentationService(self.ctx).generate_informe()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(report)
        self._say(f"Informe exportado: {path}",
                  "Ábrelo con cualquier editor de texto o visor Markdown")

    # -- archivo -------------------------------------------------------------------
    def new_project(self) -> None:
        if self.application is None:
            return
        path = filedialog.asksaveasfilename(
            title="Nuevo proyecto", defaultextension=".arqgen",
            filetypes=[("Proyecto ARQ GEN", "*.arqgen")])
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self.ctx.close()
        self.ctx = self.application.create_project(path, name=name)
        self._after_context_change()
        self._say(f"Proyecto «{name}» creado y listo. Está vacío: es un "
                  "lienzo en blanco.",
                  next_hint(spaces=0))

    def open_project_dialog(self) -> None:
        if self.application is None:
            return
        path = filedialog.askopenfilename(
            title="Abrir proyecto", filetypes=[("Proyecto ARQ GEN",
                                                "*.arqgen")])
        if not path or not os.path.exists(path):
            return
        self.ctx.close()
        self.ctx = self.application.open_project(path)
        self._after_context_change()
        self._say(f"Proyecto abierto: {os.path.basename(path)}.",
                  next_hint(**self._project_stats()))

    def open_demo(self) -> None:
        if self.application is None:
            return
        path = os.path.join(tempfile.gettempdir(), "arqgen_gui_demo.arqgen")
        self.ctx.close()
        from app.demo import build_demo
        self.ctx = build_demo(self.application, path)
        self._after_context_change()
        self._say("Proyecto de demostración cargado: explóralo sin "
                  "compromiso; nada de lo que hagas aquí rompe nada.",
                  "Pulsa sobre cualquier objeto del plano para ver sus "
                  "datos")

    def _after_context_change(self) -> None:
        self.explorer = ExplorerModel(self.ctx)
        self.search_engine = SearchEngine(self.explorer)
        self.canvas_model = CanvasModel(self.ctx, self.explorer)
        self.state_service = StateService(self.ctx)
        self.edit_service = EditService(self.ctx, self.explorer)
        self.status_model = StatusModel(self.ctx)
        self.selection = None
        self.title(f"ARQ GEN {APP_VERSION} — {self.ctx.project.name}")
        self.refresh_all(fit=True)

    def export(self, fmt: str) -> None:
        from services.export_service import ExportService
        extension = {"DXF": ".dxf", "JSON": ".json", "XLSX": ".xlsx",
                     "CSV": ".csv", "IFC": ".ifc"}[fmt]
        path = filedialog.asksaveasfilename(
            title=f"Exportar {fmt}", defaultextension=extension)
        if not path:
            return
        ExportService().export(self.ctx, fmt, path)
        self._say(f"Exportado {fmt}: {os.path.basename(path)}.",
                  "El archivo ya está donde elegiste; listo para "
                  "compartir")

    # -- paneles inferiores -------------------------------------------------------------
    def refresh_log(self) -> None:
        lines = self.status_model.log_lines(limit=80)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(reversed(lines)))
        self.log_text.configure(state="disabled")

    def refresh_calcs(self) -> None:
        self.calc_tree.delete(*self.calc_tree.get_children())
        for row in self.status_model.calculation_rows(limit=50):
            self.calc_tree.insert("", "end", values=(
                row.get("calculation_type", ""),
                row.get("status", ""),
                row.get("objects_processed", 0),
                row.get("duration_ms", 0),
                row.get("timestamp", "")))

    def refresh_statusbar(self) -> None:
        # El canal izquierdo es de ORIENTACIÓN (_say/tooltips); los datos
        # técnicos viven a la derecha para no pisar los mensajes.
        self._info_var.set(
            f"{self.ctx.project.name} · "
            f"disciplina: {discipline_label(self.current_discipline)} · "
            f"{len(self._primitives)} objetos en el plano")

    def about(self) -> None:
        messagebox.showinfo(
            "Acerca de ARQ GEN",
            f"ARQ GEN {APP_VERSION}\nBIM/BEQ offline para AEC.\n\n"
            "Una herramienta sencilla: explora, crea, calcula y exporta "
            "sin conexión. Si te pierdes, pulsa F1 y la guía rápida te "
            "orienta en 4 pasos.", parent=self)

    def on_close(self) -> None:
        try:
            self.ctx.close()
        finally:
            self.destroy()


def launch(file_path: str = "", demo: bool = False,
           width: int = 1280, height: int = 800) -> int:
    """Entry point of the GUI (`main.py gui [archivo] [--demo]`)."""
    from app.bootstrap import bootstrap

    application, _loader = bootstrap()
    if demo or not file_path:
        path = os.path.join(tempfile.gettempdir(), "arqgen_gui_demo.arqgen")
        from app.demo import build_demo
        context = build_demo(application, path)
    else:
        context = application.open_project(file_path)
    window = ARQGenWindow(context, application)
    window.geometry(f"{width}x{height}")
    window.protocol("WM_DELETE_WINDOW", window.on_close)
    window.mainloop()
    return 0


__all__ = ["ARQGenWindow", "launch", "PALETTE"]
