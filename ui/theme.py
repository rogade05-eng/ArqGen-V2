"""Tema oscuro moderno de ARQ GEN (mejora UX v1.7.1).

Centraliza la paleta y las fuentes para que toda la interfaz use un
lenguaje visual coherente: fondo oscuro, letras claras, un único color
de acento y jerarquía por capas (fondo general → panel → control →
campo). Ninguna otra parte de la UI define colores sueltos: importa
aquí lo que necesite.

El tema se aplica con `apply_dark_theme(root)` ANTES de construir los
widgets; devuelve el diccionario COLORS por si un módulo necesita un
tono concreto (p. ej. el lienzo).
"""

from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import font as tkfont
    from tkinter import ttk
except ImportError:  # headless / environments without Tk
    tk = None  # type: ignore[assignment]
    tkfont = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
from typing import Any, Dict

# -- Paleta base (oscura, letras claras) ------------------------------------
COL_BG = "#15171C"         # fondo general de la ventana
COL_BG_ALT = "#1B1E24"     # paneles y cabeceras
COL_RAISE = "#242832"      # botones / pestañas / controles
COL_FIELD = "#2A2F3A"      # campos de texto, treeviews, listas
COL_HOVER = "#323846"      # hover de botones y pestañas
COL_BORDER = "#3A4150"     # bordes sutiles
COL_TEXT = "#E9ECF1"       # texto principal (claro)
COL_TEXT_DIM = "#A6ADBA"   # texto secundario / ayudas
COL_ACCENT = "#5B8DEF"     # acento amable (azul)
COL_ACCENT_DARK = "#3E68B8"
COL_OK = "#63D69B"
COL_WARN = "#F2C14E"
COL_ERROR = "#F07171"
COL_CANVAS = "#101216"     # lienzo de dibujo (más profundo que el fondo)
COL_SELECTION = "#FF7A88"  # resalte de selección en el lienzo

# Colores de la selección en widgets (ttk map).
SEL_BG = "#3D5A96"
SEL_FG = "#FFFFFF"

# -- Paleta del lienzo adaptada al fondo oscuro ------------------------------
# Misma semántica que la PALETTE histórica de app_window (space, wall,
# grid...) pero con tonos legibles sobre oscuro. Los colores por
# tipo/sistema se recalculan aclarándolos para conservar el matiz.
CANVAS_DARK: Dict[str, str] = {
    "space_fill": "#1C2534",
    "space_text": "#C7CFDC",
    "wall": "#8B95A6",
    "grid": "#1E222B",
    "axis": "#39414F",
    "selection": COL_SELECTION,
    "welcome_card": "#1D2129",
    "welcome_border": COL_ACCENT_DARK,
    "welcome_title": COL_ACCENT,
    "welcome_text": COL_TEXT_DIM,
}

# Colores por tipo/sistema ajustados para contrastar sobre el lienzo
# oscuro (mismo matiz que la paleta original, +luminosidad).
ENTITY_COLORS: Dict[str, str] = {
    "space": "#7FA6E8", "wall": "#8B95A6", "DOOR": "#F0A64B",
    "WINDOW": "#4FC3F7", "OPENING": "#B9C2CF",
    "SPACE": "#7FA6E8", "BEAM": "#8E9BFF", "COLUMN": "#B18CFF",
    "BRACE": "#C084FC", "SLAB": "#A5B4FC", "TRUSS": "#A78BFA",
    "FOUNDATION": "#D3A05C",
    "POWER": "#FF7B72", "LIGHTING": "#FFD166", "HVAC": "#4ED9A4",
    "WATER": "#5B9BF5", "DRAINAGE": "#B18CFF", "STORMWATER": "#54C1F0",
    "GAS": "#FF9457", "TELECOM": "#4ADE80", "CCTV": "#4DD0E1",
    "FIRE_ALARM": "#FF6B6B", "INTRUSION": "#C084FC",
    "ACCESS_CONTROL": "#2DD4BF", "PERIMETER": "#A3D65C",
    "DATA": "#6EE787", "FIRE": "#FF6B6B", "ELECTRICAL": "#FF7B72",
    "SANITARY": "#5B9BF5", "SECURITY": "#C084FC",
}


def _configure_fonts(root: tk.Tk) -> None:
    """Tipografía legible y amable (sin forzar familia inexistente)."""
    for name, size in (("TkDefaultFont", 10), ("TkTextFont", 10),
                       ("TkFixedFont", 9), ("TkMenuFont", 10),
                       ("TkHeadingFont", 10)):
        try:
            f = tkfont.nametofont(name)
            f.configure(size=size)
        except Exception:  # noqa: BLE001 - fuente no disponible
            pass


def apply_dark_theme(root: tk.Tk) -> Dict[str, str]:
    """Aplica el tema oscuro a la ventana y a todos los estilos ttk.

    Debe llamarse antes de construir cualquier widget. Devuelve el
    diccionario de colores por si el llamador necesita tonos concretos.
    """
    _configure_fonts(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")  # el más configurable multiplataforma
    except Exception:  # noqa: BLE001 - mantener el nativo
        pass

    root.configure(background=COL_BG)
    root.option_add("*TCombobox*Listbox.background", COL_FIELD)
    root.option_add("*TCombobox*Listbox.foreground", COL_TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SEL_BG)
    root.option_add("*TCombobox*Listbox.selectForeground", SEL_FG)
    root.option_add("*TCombobox*Listbox.font", ("TkTextFont", 10))

    style.configure(".", background=COL_BG, foreground=COL_TEXT,
                    fieldbackground=COL_FIELD, bordercolor=COL_BORDER,
                    lightcolor=COL_RAISE, darkcolor=COL_BG_ALT,
                    troughcolor=COL_BG_ALT, focuscolor=COL_ACCENT,
                    selectbackground=SEL_BG, selectforeground=SEL_FG,
                    font=("TkTextFont", 10))

    # -- Frames / paneles -----------------------------------------------------
    style.configure("TFrame", background=COL_BG)
    style.configure("Panel.TFrame", background=COL_BG_ALT)
    style.configure("Card.TFrame", background=COL_RAISE, relief="flat")
    style.configure("TPanedwindow", background=COL_BG)
    style.configure("TSeparator", background=COL_BORDER)

    # -- Etiquetas ------------------------------------------------------------
    style.configure("TLabel", background=COL_BG, foreground=COL_TEXT)
    style.configure("Dim.TLabel", background=COL_BG,
                    foreground=COL_TEXT_DIM)
    style.configure("Hint.TLabel", background=COL_BG_ALT,
                    foreground=COL_TEXT_DIM, padding=(8, 4))
    style.configure("Title.TLabel", background=COL_BG,
                    foreground=COL_TEXT, font=("TkDefaultFont", 12, "bold"))
    style.configure("Accent.TLabel", background=COL_BG,
                    foreground=COL_ACCENT)
    style.configure("Guide.TLabel", background=COL_RAISE,
                    foreground=COL_TEXT)

    # -- Botones ---------------------------------------------------------------
    style.configure("TButton", background=COL_RAISE, foreground=COL_TEXT,
                    bordercolor=COL_BORDER, focuscolor=COL_ACCENT,
                    padding=(10, 5), relief="flat", borderradius=6)
    style.map("TButton",
              background=[("active", COL_HOVER),
                          ("pressed", COL_ACCENT_DARK)],
              foreground=[("disabled", COL_TEXT_DIM)],
              bordercolor=[("focus", COL_ACCENT)])
    style.configure("Accent.TButton", background=COL_ACCENT_DARK,
                    foreground=COL_TEXT, padding=(12, 5))
    style.map("Accent.TButton",
              background=[("active", COL_ACCENT),
                          ("pressed", COL_ACCENT_DARK)])
    style.configure("Guide.TButton", background=COL_RAISE,
                    foreground=COL_ACCENT, padding=(10, 5))
    style.map("Guide.TButton",
              background=[("active", COL_HOVER)],
              foreground=[("active", COL_TEXT)])

    # -- Entradas y combinaciones ---------------------------------------------
    style.configure("TEntry", fieldbackground=COL_FIELD,
                    foreground=COL_TEXT, insertcolor=COL_TEXT,
                    bordercolor=COL_BORDER, lightcolor=COL_FIELD,
                    darkcolor=COL_FIELD, padding=(6, 4))
    style.map("TEntry", bordercolor=[("focus", COL_ACCENT)])
    style.configure("TCombobox", fieldbackground=COL_FIELD,
                    background=COL_RAISE, foreground=COL_TEXT,
                    arrowcolor=COL_TEXT, bordercolor=COL_BORDER,
                    lightcolor=COL_FIELD, darkcolor=COL_FIELD,
                    padding=(6, 3))
    style.map("TCombobox",
              fieldbackground=[("readonly", COL_FIELD)],
              foreground=[("readonly", COL_TEXT)],
              bordercolor=[("focus", COL_ACCENT)])

    # -- Treeviews (explorador, propiedades, cálculos) -------------------------
    style.configure("Treeview", background=COL_FIELD, foreground=COL_TEXT,
                    fieldbackground=COL_FIELD, bordercolor=COL_BG,
                    rowheight=24, font=("TkTextFont", 10))
    style.map("Treeview",
              background=[("selected", SEL_BG)],
              foreground=[("selected", SEL_FG)])
    style.configure("Treeview.Heading", background=COL_BG_ALT,
                    foreground=COL_TEXT_DIM, relief="flat",
                    font=("TkDefaultFont", 9, "bold"), padding=(6, 4))
    style.map("Treeview.Heading", background=[("active", COL_HOVER)])

    # -- Notebook (panel inferior) ----------------------------------------------
    style.configure("TNotebook", background=COL_BG,
                    bordercolor=COL_BORDER, tabmargins=(4, 3, 4, 0))
    style.configure("TNotebook.Tab", background=COL_BG_ALT,
                    foreground=COL_TEXT_DIM, padding=(14, 5),
                    font=("TkDefaultFont", 9))
    style.map("TNotebook.Tab",
              background=[("selected", COL_RAISE)],
              foreground=[("selected", COL_TEXT)])

    # -- Checkbuttons / Radiobuttons ---------------------------------------------
    style.configure("TCheckbutton", background=COL_BG,
                    foreground=COL_TEXT, focuscolor=COL_ACCENT,
                    padding=(4, 2))
    style.map("TCheckbutton",
              background=[("active", COL_BG)],
              indicatorcolor=[("selected", COL_ACCENT),
                              ("!selected", COL_FIELD)])
    style.configure("TRadiobutton", background=COL_BG_ALT,
                    foreground=COL_TEXT, focuscolor=COL_ACCENT,
                    padding=(4, 2))
    style.map("TRadiobutton",
              background=[("active", COL_BG_ALT)],
              indicatorcolor=[("selected", COL_ACCENT),
                              ("!selected", COL_FIELD)])

    # -- Scrollbars discretas -----------------------------------------------------
    style.configure("Vertical.TScrollbar", background=COL_RAISE,
                    troughcolor=COL_BG_ALT, bordercolor=COL_BG_ALT,
                    arrowcolor=COL_TEXT_DIM, gripcount=0)
    style.configure("Horizontal.TScrollbar", background=COL_RAISE,
                    troughcolor=COL_BG_ALT, bordercolor=COL_BG_ALT,
                    arrowcolor=COL_TEXT_DIM, gripcount=0)

    # -- Menús (tk.Menu nativo) -----------------------------------------------------
    menu_kw: Dict[str, Any] = dict(
        background=COL_BG_ALT, foreground=COL_TEXT,
        activebackground=COL_ACCENT_DARK, activeforeground=COL_TEXT,
        disabledforeground=COL_TEXT_DIM, borderwidth=0,
        activeborderwidth=0, relief="flat")
    root.option_add("*Menu.background", COL_BG_ALT)
    root.option_add("*Menu.foreground", COL_TEXT)
    root.option_add("*Menu.activeBackground", COL_ACCENT_DARK)
    root.option_add("*Menu.activeForeground", COL_TEXT)
    root.option_add("*Menu.borderWidth", 0)
    return dict(bg=COL_BG, bg_alt=COL_BG_ALT, raise_=COL_RAISE,
                field=COL_FIELD, hover=COL_HOVER, border=COL_BORDER,
                text=COL_TEXT, text_dim=COL_TEXT_DIM, accent=COL_ACCENT,
                canvas=COL_CANVAS)


def menu_kwargs() -> Dict[str, Any]:
    """Argumentos de color para crear tk.Menu coherentes con el tema."""
    return dict(tearoff=0, background=COL_BG_ALT, foreground=COL_TEXT,
                activebackground=COL_ACCENT_DARK,
                activeforeground=COL_TEXT,
                disabledforeground=COL_TEXT_DIM, borderwidth=0)


__all__ = [
    "apply_dark_theme", "menu_kwargs", "CANVAS_DARK", "ENTITY_COLORS",
    "COL_BG", "COL_BG_ALT", "COL_RAISE", "COL_FIELD", "COL_HOVER",
    "COL_BORDER", "COL_TEXT", "COL_TEXT_DIM", "COL_ACCENT",
    "COL_ACCENT_DARK", "COL_OK", "COL_WARN", "COL_ERROR", "COL_CANVAS",
    "COL_SELECTION", "SEL_BG", "SEL_FG",
]
