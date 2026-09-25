# -*- coding: utf-8 -*-
"""Asistente de Diseño Generativo de Arquitectura en 2 Pasos (ui/generative_wizard.py).

Ventana 1: Requerimientos Generales y Programa de Locales
  - Nivel de destino (seleccionar o crear nuevo)
  - Tipo de edificación y altura de entrepiso
  - Huella aproximada (manual o automática)
  - Cantidad y tipo de locales con áreas objetivo y zonas funcionales

Ventana 2: Relaciones Espaciales y Especialidades Técnicas
  - Asociaciones y enlaces espaciales (mediante qué elemento se asocian: Puerta, Vano Libre,
    Ventana Interior, Muro Divisorio, Espacio Integrado)
  - Requerimientos climáticos y ambientales (orientación, ventilación cruzada)
  - Requerimientos estructurales (sistema, espesor de muros, luces)
  - Requerimientos hidráulicos y sanitarios (núcleo húmedo agrupado NC 600)
  - Requerimientos de seguridad (SADI, Intrusión Grado 2, CCTV, Red Eléctrica)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    _BaseDialog = tk.Toplevel
except ImportError:
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    _BaseDialog = object  # type: ignore[assignment, misc]

from services.generative_architecture_service import GenerativeArchitectureService, PROGRAM_TEMPLATES


class GenerativeWizardDialog(_BaseDialog):
    """Diálogo modal interactivo de generación arquitectónica automática en 2 pasos."""

    def __init__(self, parent: Any, ctx: Any, current_level: str = "",
                 on_generated: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        if tk is None:
            raise RuntimeError("Tkinter no está disponible en este entorno.")
        super().__init__(parent)
        self.title("⚡ Asistente de Diseño Generativo de Arquitectura (Sin IA)")
        self.transient(parent)
        self.grab_set()
        self.ctx = ctx
        self.on_generated = on_generated
        self.geometry("820x660")
        self.minsize(760, 600)

        self.current_step = 1

        # Variables Paso 1 (Generales)
        pid = self.ctx.project.id
        self.existing_levels = [lv.name or lv.code for lv in self.ctx.architecture.list("LEVEL", pid)]
        if not self.existing_levels:
            self.existing_levels = ["Planta Baja"]

        default_lvl = current_level if current_level in self.existing_levels else self.existing_levels[0]
        self.level_var = tk.StringVar(value=default_lvl)
        self.new_level_name_var = tk.StringVar(value="")
        self.elevation_var = tk.DoubleVar(value=0.0)
        self.height_var = tk.DoubleVar(value=2.80)
        self.bldg_type_var = tk.StringVar(value="Vivienda Unifamiliar")
        self.auto_footprint_var = tk.BooleanVar(value=True)
        self.width_var = tk.DoubleVar(value=8.5)
        self.depth_var = tk.DoubleVar(value=9.5)

        # Variables Paso 2 (Especialidades)
        self.orient_var = tk.StringVar(value="SUR")
        self.climate_zone_var = tk.StringVar(value="Costa Norte")
        self.cross_vent_var = tk.BooleanVar(value=True)
        self.solar_shading_var = tk.BooleanVar(value=True)

        self.struct_system_var = tk.StringVar(value="Muros Portantes de Mampostería")
        self.wall_ext_th_var = tk.DoubleVar(value=0.20)
        self.wall_int_th_var = tk.DoubleVar(value=0.15)
        self.max_span_var = tk.DoubleVar(value=4.50)

        self.wet_core_var = tk.BooleanVar(value=True)
        self.water_supply_var = tk.StringVar(value="Cisterna + Tanque Elevado")

        self.sadi_var = tk.BooleanVar(value=True)
        self.intrusion_var = tk.BooleanVar(value=True)
        self.cctv_var = tk.BooleanVar(value=True)
        self.power_var = tk.BooleanVar(value=True)

        # Datos en memoria
        self.rooms_list: List[Dict[str, Any]] = []
        self.relationships_list: List[Dict[str, Any]] = []

        self._build_header()
        self.container = ttk.Frame(self, padding=(12, 6))
        self.container.pack(fill="both", expand=True)

        # Cargar programa inicial por defecto (Vivienda 2D)
        self._load_template_rooms("VIVIENDA_2D")

        self._show_step_1()

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(12, 10))
        header.pack(side="top", fill="x")

        title = ttk.Label(header, text="⚡ Generador Automático de Planta Arquitectónica",
                          font=("TkDefaultFont", 12, "bold"))
        title.pack(anchor="w")

        self.step_label = ttk.Label(header, text="[ PASO 1 DE 2: Requerimientos Generales y Programa de Locales ]",
                                    font=("TkDefaultFont", 9, "bold"), foreground="#007acc")
        self.step_label.pack(anchor="w", pady=(2, 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x")

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    # =========================================================================
    # PASO 1: REQUERIMIENTOS GENERALES Y PROGRAMA DE LOCALES
    # =========================================================================

    def _show_step_1(self) -> None:
        self.current_step = 1
        self.step_label.configure(
            text="[ PASO 1 DE 2: Requerimientos Generales y Programa de Locales ] ➔ Paso 2: Relaciones y Especialidades",
            foreground="#007acc")
        self._clear_container()

        # Marco General
        gen_box = ttk.LabelFrame(self.container, text="1. Parámetros Generales de la Edificación", padding=(10, 8))
        gen_box.pack(fill="x", pady=(0, 8))

        row1 = ttk.Frame(gen_box)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Nivel de destino:", width=18).pack(side="left")
        opts_level = self.existing_levels + ["(+ Crear nuevo nivel...)"]
        combo_lvl = ttk.Combobox(row1, textvariable=self.level_var, values=opts_level, state="readonly", width=22)
        combo_lvl.pack(side="left", padx=4)
        combo_lvl.bind("<<ComboboxSelected>>", self._on_level_selected)

        ttk.Label(row1, text="Nuevo nivel:").pack(side="left", padx=(12, 2))
        self.entry_new_lvl = ttk.Entry(row1, textvariable=self.new_level_name_var, width=18, state="disabled")
        self.entry_new_lvl.pack(side="left")

        row2 = ttk.Frame(gen_box)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Tipo de edificación:", width=18).pack(side="left")
        bldg_types = ["Vivienda Unifamiliar", "Vivienda Colectiva", "Oficinas / Administrativo",
                      "Consultorio / Salud", "Centro Educativo", "Comercio / Servicios"]
        ttk.Combobox(row2, textvariable=self.bldg_type_var, values=bldg_types, state="readonly", width=22).pack(side="left", padx=4)

        ttk.Label(row2, text="Altura entrepiso (m):").pack(side="left", padx=(12, 2))
        ttk.Entry(row2, textvariable=self.height_var, width=8).pack(side="left")

        row3 = ttk.Frame(gen_box)
        row3.pack(fill="x", pady=2)
        ttk.Checkbutton(row3, text="Calcular huella óptima automáticamente según locales",
                        variable=self.auto_footprint_var, command=self._toggle_footprint).pack(side="left")
        ttk.Label(row3, text="  o especificar Ancho x Fondo (m):").pack(side="left")
        self.entry_w = ttk.Entry(row3, textvariable=self.width_var, width=6, state="disabled")
        self.entry_w.pack(side="left", padx=2)
        ttk.Label(row3, text="x").pack(side="left")
        self.entry_d = ttk.Entry(row3, textvariable=self.depth_var, width=6, state="disabled")
        self.entry_d.pack(side="left", padx=2)

        # Marco Programa de Locales
        rooms_box = ttk.LabelFrame(self.container, text="2. Programa Arquitectónico de Locales", padding=(10, 8))
        rooms_box.pack(fill="both", expand=True, pady=(0, 8))

        # Tabla de locales
        tree_frame = ttk.Frame(rooms_box)
        tree_frame.pack(fill="both", expand=True)

        cols = ("name", "space_type", "zone_kind", "area", "window")
        self.tree_rooms = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        self.tree_rooms.heading("name", text="Nombre del Local")
        self.tree_rooms.heading("space_type", text="Tipo")
        self.tree_rooms.heading("zone_kind", text="Zona")
        self.tree_rooms.heading("area", text="Área Objetivo (m²)")
        self.tree_rooms.heading("window", text="Ventana Exterior")

        self.tree_rooms.column("name", width=180)
        self.tree_rooms.column("space_type", width=110)
        self.tree_rooms.column("zone_kind", width=110)
        self.tree_rooms.column("area", width=120, anchor="e")
        self.tree_rooms.column("window", width=110, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_rooms.yview)
        self.tree_rooms.configure(yscrollcommand=scroll.set)
        self.tree_rooms.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Formulario rápido para añadir local
        add_frame = ttk.Frame(rooms_box, padding=(0, 6))
        add_frame.pack(fill="x")

        ttk.Label(add_frame, text="Nombre:").pack(side="left")
        self.new_room_name = ttk.Entry(add_frame, width=14)
        self.new_room_name.pack(side="left", padx=2)

        ttk.Label(add_frame, text="Tipo:").pack(side="left", padx=(4, 0))
        types = ["LIVING", "DINING", "KITCHEN", "BEDROOM", "BATHROOM", "CORRIDOR", "PORCH", "OFFICE", "SERVICE", "OTHER"]
        self.new_room_type = ttk.Combobox(add_frame, values=types, width=10, state="readonly")
        self.new_room_type.set("BEDROOM")
        self.new_room_type.pack(side="left", padx=2)

        ttk.Label(add_frame, text="Zona:").pack(side="left", padx=(4, 0))
        zones = ["SOCIAL", "SERVICIO", "PRIVADA"]
        self.new_room_zone = ttk.Combobox(add_frame, values=zones, width=9, state="readonly")
        self.new_room_zone.set("PRIVADA")
        self.new_room_zone.pack(side="left", padx=2)

        ttk.Label(add_frame, text="Área m²:").pack(side="left", padx=(4, 0))
        self.new_room_area = ttk.Entry(add_frame, width=6)
        self.new_room_area.insert(0, "12.0")
        self.new_room_area.pack(side="left", padx=2)

        self.new_room_win = tk.BooleanVar(value=True)
        ttk.Checkbutton(add_frame, text="Ventana", variable=self.new_room_win).pack(side="left", padx=4)

        ttk.Button(add_frame, text="+ Añadir", command=self._add_custom_room).pack(side="left", padx=2)
        ttk.Button(add_frame, text="− Quitar", command=self._remove_selected_room).pack(side="left", padx=2)

        # Plantillas rápidas
        tpl_frame = ttk.Frame(rooms_box)
        tpl_frame.pack(fill="x", pady=(4, 0))
        ttk.Label(tpl_frame, text="Cargar programa predefinido:", font=("TkDefaultFont", 8, "italic")).pack(side="left")
        for key, label in [("VIVIENDA_1D", "🏠 Viv. 1D"), ("VIVIENDA_2D", "🏡 Viv. 2D"),
                           ("VIVIENDA_3D", "🏘️ Viv. 3D"), ("OFICINA_ADMIN", "🏢 Oficina"),
                           ("CONSULTORIO_SALUD", "🩺 Clínica")]:
            ttk.Button(tpl_frame, text=label, command=lambda k=key: self._load_template_rooms(k)).pack(side="left", padx=2)

        self._refresh_rooms_tree()

        # Botones inferiores
        bot_frame = ttk.Frame(self.container)
        bot_frame.pack(side="bottom", fill="x", pady=(6, 0))

        ttk.Button(bot_frame, text="Cancelar", command=self.destroy).pack(side="left")
        ttk.Button(bot_frame, text="Siguiente: Relaciones Espaciales y Especialidades ➔",
                   style="Accent.TButton", command=self._show_step_2).pack(side="right")

    def _on_level_selected(self, _event=None) -> None:
        val = self.level_var.get()
        if "(+ Crear nuevo nivel...)" in val:
            self.entry_new_lvl.configure(state="normal")
            self.entry_new_lvl.focus_set()
        else:
            self.entry_new_lvl.configure(state="disabled")

    def _toggle_footprint(self) -> None:
        if self.auto_footprint_var.get():
            self.entry_w.configure(state="disabled")
            self.entry_d.configure(state="disabled")
        else:
            self.entry_w.configure(state="normal")
            self.entry_d.configure(state="normal")

    def _add_custom_room(self) -> None:
        name = self.new_room_name.get().strip()
        if not name:
            messagebox.showwarning("Atención", "Escribe un nombre para el local.", parent=self)
            return
        try:
            area = float(self.new_room_area.get())
            if area <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Atención", "El área debe ser un número positivo.", parent=self)
            return

        self.rooms_list.append({
            "name": name,
            "space_type": self.new_room_type.get(),
            "zone_kind": self.new_room_zone.get(),
            "target_area": area,
            "has_window": self.new_room_win.get(),
        })
        self.new_room_name.delete(0, "end")
        self._refresh_rooms_tree()

    def _remove_selected_room(self) -> None:
        sel = self.tree_rooms.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.rooms_list):
            del self.rooms_list[idx]
            self._refresh_rooms_tree()

    def _refresh_rooms_tree(self) -> None:
        for item in self.tree_rooms.get_children():
            self.tree_rooms.delete(item)
        for idx, r in enumerate(self.rooms_list):
            win_txt = "Sí" if r.get("has_window", True) else "No"
            self.tree_rooms.insert("", "end", iid=str(idx), values=(
                r["name"], r.get("space_type", "ROOM"), r.get("zone_kind", "SOCIAL"),
                f"{r.get('target_area', 10.0):.1f}", win_txt
            ))

    def _load_template_rooms(self, template_key: str) -> None:
        if template_key not in PROGRAM_TEMPLATES:
            return
        t = PROGRAM_TEMPLATES[template_key]
        self.rooms_list = [
            {"name": r.name, "space_type": r.space_type, "zone_kind": r.zone_kind,
             "target_area": r.target_area, "has_window": r.has_exterior_window}
            for r in t["rooms"]
        ]
        self.width_var.set(t.get("default_width", 8.5))
        self.depth_var.set(t.get("default_depth", 9.5))
        self._auto_generate_relationships()
        if hasattr(self, "tree_rooms") and self.tree_rooms.winfo_exists():
            self._refresh_rooms_tree()

    def _auto_generate_relationships(self) -> None:
        """Genera asociaciones espaciales lógicas basadas en Space DNA según los locales actuales."""
        names = [r["name"] for r in self.rooms_list]
        self.relationships_list.clear()

        # Reglas de asociación arquitectónica
        def find_name(hint: str) -> Optional[str]:
            for n in names:
                if hint.lower() in n.lower():
                    return n
            return None

        portal = find_name("portal") or find_name("recepc") or find_name("espera")
        sala = find_name("sala")
        comedor = find_name("comedor") or find_name("juntas")
        cocina = find_name("cocina") or find_name("oficina")
        pasillo = find_name("pasillo") or find_name("distrib")
        patio = find_name("patio") or find_name("archivo")
        bano = find_name("baño") or find_name("aseo")

        # Portal ↔ Sala
        if portal and sala:
            self.relationships_list.append({"from_room": portal, "to_room": sala, "connection_type": "DOOR", "element_size": 0.95})
        # Sala ↔ Comedor (Vano libre)
        if sala and comedor and sala != comedor:
            self.relationships_list.append({"from_room": sala, "to_room": comedor, "connection_type": "OPENING", "element_size": 1.60})
        # Comedor ↔ Cocina (Puerta)
        if comedor and cocina:
            self.relationships_list.append({"from_room": comedor, "to_room": cocina, "connection_type": "DOOR", "element_size": 0.85})
        elif sala and cocina:
            self.relationships_list.append({"from_room": sala, "to_room": cocina, "connection_type": "DOOR", "element_size": 0.85})
        # Cocina ↔ Patio de Servicio
        if cocina and patio:
            self.relationships_list.append({"from_room": cocina, "to_room": patio, "connection_type": "DOOR", "element_size": 0.80})

        # Dormitorios ↔ Pasillo o Sala
        hub = pasillo or sala or comedor
        for n in names:
            if "dormitorio" in n.lower() or "despacho" in n.lower() or "consultorio" in n.lower():
                if hub:
                    self.relationships_list.append({"from_room": hub, "to_room": n, "connection_type": "DOOR", "element_size": 0.85})
        # Baño ↔ Pasillo o Sala
        if bano and hub:
            self.relationships_list.append({"from_room": hub, "to_room": bano, "connection_type": "DOOR", "element_size": 0.75})

    # =========================================================================
    # PASO 2: RELACIONES ESPACIALES Y ESPECIALIDADES TÉCNICAS
    # =========================================================================

    def _show_step_2(self) -> None:
        if not self.rooms_list:
            messagebox.showwarning("Atención", "Debe haber al menos un local en el programa.", parent=self)
            return

        self.current_step = 2
        self.step_label.configure(
            text="Paso 1: Requerimientos Generales ➔ [ PASO 2 DE 2: Relaciones Espaciales y Especialidades ]",
            foreground="#007acc")
        self._clear_container()

        # Marco 1: Relaciones Espaciales entre Locales
        rel_box = ttk.LabelFrame(self.container, text="1. Relaciones Espaciales y Conexiones entre Locales", padding=(10, 8))
        rel_box.pack(fill="both", expand=True, pady=(0, 6))

        info_lbl = ttk.Label(rel_box, text="Asocia los locales indicando mediante qué elemento arquitectónico se comunican:",
                             font=("TkDefaultFont", 8, "italic"))
        info_lbl.pack(anchor="w", pady=(0, 4))

        tree_f = ttk.Frame(rel_box)
        tree_f.pack(fill="both", expand=True)

        cols = ("from", "to", "type", "size")
        self.tree_rel = ttk.Treeview(tree_f, columns=cols, show="headings", height=5)
        self.tree_rel.heading("from", text="Local Origen")
        self.tree_rel.heading("to", text="Local Destino")
        self.tree_rel.heading("type", text="Elemento de Conexión")
        self.tree_rel.heading("size", text="Dimensión (m)")

        self.tree_rel.column("from", width=180)
        self.tree_rel.column("to", width=180)
        self.tree_rel.column("type", width=160)
        self.tree_rel.column("size", width=100, anchor="e")

        sc = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree_rel.yview)
        self.tree_rel.configure(yscrollcommand=sc.set)
        self.tree_rel.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")

        # Controles para añadir relación
        add_r = ttk.Frame(rel_box, padding=(0, 4))
        add_r.pack(fill="x")

        room_names = [r["name"] for r in self.rooms_list]
        ttk.Label(add_r, text="De:").pack(side="left")
        self.combo_rel_from = ttk.Combobox(add_r, values=room_names, state="readonly", width=14)
        if room_names:
            self.combo_rel_from.current(0)
        self.combo_rel_from.pack(side="left", padx=2)

        ttk.Label(add_r, text="A:").pack(side="left", padx=(4, 0))
        self.combo_rel_to = ttk.Combobox(add_r, values=room_names, state="readonly", width=14)
        if len(room_names) > 1:
            self.combo_rel_to.current(1)
        elif room_names:
            self.combo_rel_to.current(0)
        self.combo_rel_to.pack(side="left", padx=2)

        ttk.Label(add_r, text="Mediante:").pack(side="left", padx=(4, 0))
        conn_types = ["Puerta Batiente", "Vano Libre / Arco", "Ventana Interior", "Espacio Integrado (Abierto)", "Muro Divisorio"]
        self.combo_conn_type = ttk.Combobox(add_r, values=conn_types, state="readonly", width=16)
        self.combo_conn_type.set("Puerta Batiente")
        self.combo_conn_type.pack(side="left", padx=2)

        ttk.Label(add_r, text="Ancho:").pack(side="left", padx=(4, 0))
        self.entry_conn_size = ttk.Entry(add_r, width=5)
        self.entry_conn_size.insert(0, "0.85")
        self.entry_conn_size.pack(side="left", padx=2)

        ttk.Button(add_r, text="+ Conectar", command=self._add_relationship).pack(side="left", padx=2)
        ttk.Button(add_r, text="− Quitar", command=self._remove_relationship).pack(side="left", padx=2)
        ttk.Button(add_r, text="🔄 Auto-conectar Space DNA", command=self._reconnect_space_dna).pack(side="right", padx=2)

        self._refresh_rel_tree()

        # Marco 2: Especialidades Técnicas (Notebook)
        spec_box = ttk.LabelFrame(self.container, text="2. Requerimientos Técnicos y de Especialidades", padding=(8, 6))
        spec_box.pack(fill="x", pady=(0, 6))

        nb = ttk.Notebook(spec_box)
        nb.pack(fill="x")

        # Tab Climático
        tab_clim = ttk.Frame(nb, padding=8)
        nb.add(tab_clim, text="☀️ Climático & Bioclimático")
        r1 = ttk.Frame(tab_clim); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Orientación fachada principal:").pack(side="left")
        ttk.Combobox(r1, textvariable=self.orient_var, values=["SUR", "NORTE", "ESTE", "OESTE", "NORESTE"],
                     state="readonly", width=10).pack(side="left", padx=6)
        ttk.Label(r1, text="Zona bioclimática:").pack(side="left", padx=(10, 0))
        ttk.Combobox(r1, textvariable=self.climate_zone_var, values=["Costa Norte", "Costa Sur", "Llanura Central", "Montañosa"],
                     state="readonly", width=14).pack(side="left", padx=6)
        r2 = ttk.Frame(tab_clim); r2.pack(fill="x", pady=2)
        ttk.Checkbutton(r2, text="Exigir ventilación cruzada en locales habitables (NC 120)", variable=self.cross_vent_var).pack(side="left")
        ttk.Checkbutton(r2, text="Aleros y protección solar en ventanas expuestas", variable=self.solar_shading_var).pack(side="left", padx=16)

        # Tab Estructural
        tab_str = ttk.Frame(nb, padding=8)
        nb.add(tab_str, text="🧱 Estructural")
        s1 = ttk.Frame(tab_str); s1.pack(fill="x", pady=2)
        ttk.Label(s1, text="Sistema estructural:").pack(side="left")
        ttk.Combobox(s1, textvariable=self.struct_system_var,
                     values=["Muros Portantes de Mampostería", "Pórticos de Hormigón Armado", "Sistema Mixto"],
                     state="readonly", width=26).pack(side="left", padx=6)
        ttk.Label(s1, text="Luz máx. (m):").pack(side="left", padx=(10, 0))
        ttk.Entry(s1, textvariable=self.max_span_var, width=6).pack(side="left", padx=4)
        s2 = ttk.Frame(tab_str); s2.pack(fill="x", pady=2)
        ttk.Label(s2, text="Espesor muro exterior (m):").pack(side="left")
        ttk.Entry(s2, textvariable=self.wall_ext_th_var, width=6).pack(side="left", padx=4)
        ttk.Label(s2, text="Espesor muro interior (m):").pack(side="left", padx=(12, 0))
        ttk.Entry(s2, textvariable=self.wall_int_th_var, width=6).pack(side="left", padx=4)

        # Tab Hidráulico y Sanitario
        tab_hid = ttk.Frame(nb, padding=8)
        nb.add(tab_hid, text="💧 Hidráulico & Sanitario")
        h1 = ttk.Frame(tab_hid); h1.pack(fill="x", pady=2)
        ttk.Checkbutton(h1, text="Agrupar locales húmedos (núcleo sanitario compartido Baño/Cocina - NC 600)",
                        variable=self.wet_core_var).pack(side="left")
        h2 = ttk.Frame(tab_hid); h2.pack(fill="x", pady=2)
        ttk.Label(h2, text="Suministro de agua:").pack(side="left")
        ttk.Combobox(h2, textvariable=self.water_supply_var, values=["Cisterna + Tanque Elevado", "Directa de red"],
                     state="readonly", width=22).pack(side="left", padx=6)

        # Tab Seguridad e Instalaciones
        tab_sec = ttk.Frame(nb, padding=8)
        nb.add(tab_sec, text="🛡️ Seguridad & MEP")
        sec1 = ttk.Frame(tab_sec); sec1.pack(fill="x", pady=2)
        ttk.Checkbutton(sec1, text="Detección de Incendio SADI (óptico/térmico)", variable=self.sadi_var).pack(side="left")
        ttk.Checkbutton(sec1, text="Alarma de Intrusión Grado 2 (sensores PIR)", variable=self.intrusion_var).pack(side="left", padx=12)
        sec2 = ttk.Frame(tab_sec); sec2.pack(fill="x", pady=2)
        ttk.Checkbutton(sec2, text="CCTV en accesos principales", variable=self.cctv_var).pack(side="left")
        ttk.Checkbutton(sec2, text="Red Eléctrica con Cuadro General (TD)", variable=self.power_var).pack(side="left", padx=12)

        # Botones inferiores Paso 2
        bot_frame = ttk.Frame(self.container)
        bot_frame.pack(side="bottom", fill="x", pady=(6, 0))

        ttk.Button(bot_frame, text="◀ Atrás (Requerimientos Generales)", command=self._show_step_1).pack(side="left")
        ttk.Button(bot_frame, text="⚡ GENERAR PLANTA ARQUITECTÓNICA AUTOMÁTICA",
                   style="Accent.TButton", command=self._execute_generation).pack(side="right")

    def _add_relationship(self) -> None:
        r_from = self.combo_rel_from.get()
        r_to = self.combo_rel_to.get()
        if not r_from or not r_to:
            return
        if r_from == r_to:
            messagebox.showwarning("Atención", "No se puede conectar un local consigo mismo.", parent=self)
            return

        c_type_raw = self.combo_conn_type.get()
        map_types = {
            "Puerta Batiente": "DOOR",
            "Vano Libre / Arco": "OPENING",
            "Ventana Interior": "WINDOW",
            "Espacio Integrado (Abierto)": "OPEN_PLAN",
            "Muro Divisorio": "WALL",
        }
        conn_code = map_types.get(c_type_raw, "DOOR")
        try:
            sz = float(self.entry_conn_size.get())
        except ValueError:
            sz = 0.85

        self.relationships_list.append({
            "from_room": r_from, "to_room": r_to,
            "connection_type": conn_code, "element_size": sz
        })
        self._refresh_rel_tree()

    def _remove_relationship(self) -> None:
        sel = self.tree_rel.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.relationships_list):
            del self.relationships_list[idx]
            self._refresh_rel_tree()

    def _reconnect_space_dna(self) -> None:
        self._auto_generate_relationships()
        self._refresh_rel_tree()

    def _refresh_rel_tree(self) -> None:
        for item in self.tree_rel.get_children():
            self.tree_rel.delete(item)
        label_map = {
            "DOOR": "Puerta Batiente",
            "OPENING": "Vano Libre / Arco",
            "WINDOW": "Ventana Interior",
            "OPEN_PLAN": "Espacio Integrado",
            "WALL": "Muro Divisorio"
        }
        for idx, rel in enumerate(self.relationships_list):
            t_lbl = label_map.get(rel.get("connection_type", "DOOR"), rel.get("connection_type"))
            self.tree_rel.insert("", "end", iid=str(idx), values=(
                rel["from_room"], rel["to_room"], t_lbl, f"{rel.get('element_size', 0.85):.2f}"
            ))

    # =========================================================================
    # EJECUCIÓN DEL MOTOR GENERATIVO
    # =========================================================================

    def _execute_generation(self) -> None:
        # Resolver nombre de nivel
        lvl_selected = self.level_var.get()
        if "(+ Crear nuevo nivel...)" in lvl_selected:
            new_name = self.new_level_name_var.get().strip()
            if not new_name:
                messagebox.showwarning("Atención", "Por favor ingresa un nombre para el nuevo nivel.", parent=self)
                return
            target_level_name = new_name
        else:
            target_level_name = lvl_selected

        w_val = None if self.auto_footprint_var.get() else self.width_var.get()
        d_val = None if self.auto_footprint_var.get() else self.depth_var.get()

        payload = {
            "level_name": target_level_name,
            "elevation_m": self.elevation_var.get(),
            "story_height": self.height_var.get(),
            "building_type": self.bldg_type_var.get(),
            "width": w_val,
            "depth": d_val,
            "rooms": self.rooms_list,
            "relationships": self.relationships_list,
            "climatic": {
                "orientation": self.orient_var.get(),
                "climate_zone": self.climate_zone_var.get(),
                "cross_ventilation": self.cross_vent_var.get(),
                "solar_shading": self.solar_shading_var.get(),
            },
            "structural": {
                "system": self.struct_system_var.get(),
                "wall_ext_th": self.wall_ext_th_var.get(),
                "wall_int_th": self.wall_int_th_var.get(),
                "max_span_m": self.max_span_var.get(),
            },
            "hydraulic_sanitary": {
                "wet_core_cluster": self.wet_core_var.get(),
                "water_supply": self.water_supply_var.get(),
            },
            "security": {
                "fire_sadi": self.sadi_var.get(),
                "intrusion_grade2": self.intrusion_var.get(),
                "cctv": self.cctv_var.get(),
                "power_network": self.power_var.get(),
            },
            "clean_level": True
        }

        try:
            gen = GenerativeArchitectureService(self.ctx)
            result = gen.generate_custom(payload)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error en Generación", f"No se pudo generar la planta:\n{exc}", parent=self)
            return

        self.destroy()

        if self.on_generated:
            self.on_generated(result)
