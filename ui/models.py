"""Headless UI models for the main window (spec sections 90-93).

Todo el comportamiento de la interfaz vive aquí, sin tkinter, para que
sea verificable con unittest en cualquier entorno:

- ExplorerModel   — filas por disciplina (§91) desde el proyecto abierto
- SearchEngine    — buscador por los 9 campos del §92
- PropertiesModel — propiedades de la selección
- EntityStateFlow / StateService — sistema de estados de entidades (§93)
- CanvasModel     — primitivas geométricas dibujables por disciplina
- Viewport        — transformación mundo↔pantalla con zoom y encuadre
- StatusModel     — avisos, log de eventos y estado de cálculos (§93)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.entities.base import EntityStatus
from ui.disciplines import DISCIPLINE_BY_KEY, DISCIPLINES, SECURITY_SYSTEMS
from ui.disciplines import discipline_label

# -- §92: campos del buscador -------------------------------------------------

SEARCH_FIELDS: tuple[str, ...] = (
    "Todo", "ID", "Código", "Nombre", "Descripción", "Tipo",
    "Disciplina", "Nivel", "Zona", "Etiqueta",
)


@dataclass
class ObjectRow:
    """Una fila del explorador/buscador con los campos del §92."""

    uid: str                 # UUID de la entidad (o clave sintética)
    code: str = ""
    name: str = ""
    description: str = ""
    type: str = ""           # tipo de entidad (WALL, NODE, QUANTITY, ...)
    discipline: str = ""     # clave de disciplina (§91)
    level: str = ""          # nombre del nivel
    zone: str = ""           # nombre de la zona
    label: str = ""          # etiqueta (sistema, kind, tags)
    parent_uid: str = ""     # red contenedora (nodos/tramos)
    entity: Any = None       # entidad cargada (si aplica)
    summary: str = ""        # dato destacado (área, total, estado...)

    def field_value(self, field_name: str) -> str:
        if field_name == "ID":
            return self.uid
        if field_name == "Código":
            return self.code
        if field_name == "Nombre":
            return self.name
        if field_name == "Descripción":
            return self.description
        if field_name == "Tipo":
            return self.type
        if field_name == "Disciplina":
            return self.discipline
        if field_name == "Nivel":
            return self.level
        if field_name == "Zona":
            return self.zone
        if field_name == "Etiqueta":
            return self.label
        return " ".join(filter(None, (
            self.uid, self.code, self.name, self.description, self.type,
            self.discipline, self.level, self.zone, self.label)))


# -- Explorador (§91) ---------------------------------------------------------

@dataclass
class ExplorerModel:
    """Construye las filas del explorador desde el ProjectContext."""

    ctx: Any
    _level_names: Dict[str, str] = field(default_factory=dict, repr=False)
    _zone_names: Dict[str, str] = field(default_factory=dict, repr=False)

    def _refresh_names(self) -> None:
        pid = self.ctx.project.id
        self._level_names = {lv.id: (lv.name or lv.code)
                             for lv in self.ctx.architecture.list("LEVEL", pid)}
        self._zone_names = {zn.id: (zn.name or zn.code)
                            for zn in self.ctx.architecture.list("ZONE", pid)}

    def _level_of(self, level_id: str) -> str:
        return self._level_names.get(level_id, level_id or "")

    def rows_for(self, discipline_key: str,
                 level_id: str = "") -> List[ObjectRow]:
        """Filas de una disciplina; ``level_id`` filtra Arquitectura."""
        self._refresh_names()
        if discipline_key == "ARCHITECTURE":
            return self._arch_rows(level_id)
        if discipline_key == "INSTALLATIONS":
            return self._install_rows()
        if discipline_key == "STRUCTURE":
            return self._structure_rows()
        if discipline_key == "QTO":
            return self._qto_rows()
        if discipline_key == "BUDGET":
            return self._budget_rows()
        if discipline_key == "BIM":
            return self._bim_rows()
        if discipline_key == "COORDINATION":
            return self._clash_rows()
        if discipline_key == "DOCUMENTATION":
            return self._doc_rows()
        if discipline_key in DISCIPLINE_BY_KEY and DISCIPLINE_BY_KEY[discipline_key].systems:
            return self._security_rows(discipline_key)
        return []

    def all_rows(self, level_id: str = "") -> Dict[str, List[ObjectRow]]:
        return {d.key: self.rows_for(d.key, level_id) for d in DISCIPLINES}

    # -- Arquitectura -------------------------------------------------------
    def _arch_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        rows: List[ObjectRow] = []
        seen: set[str] = set()
        # "OPENING" es el superset de DOOR/WINDOW (tabla compartida);
        # se recorren primero los kinds específicos y se deduplica.
        for kind in ("LEVEL", "ZONE", "SPACE", "WALL", "DOOR", "WINDOW",
                     "OPENING"):
            for entity in self.ctx.architecture.list(kind, pid):
                if entity.id in seen:
                    continue
                if kind in ("SPACE", "WALL", "DOOR", "WINDOW", "OPENING") \
                        and level_id and entity.level_id != level_id:
                    continue
                seen.add(entity.id)
                zone = ""
                if getattr(entity, "zone_id", None):
                    zone = self._zone_names.get(entity.zone_id, entity.zone_id)
                summary = ""
                if kind == "SPACE":
                    summary = f"{entity.area_m2():.2f} m2"
                elif kind == "WALL":
                    summary = f"{entity.length_m:.2f} m"
                elif kind in ("DOOR", "WINDOW", "OPENING"):
                    summary = f"{entity.width_m:.2f} x {entity.height_m:.2f} m"
                rows.append(ObjectRow(
                    uid=entity.id, code=entity.code,
                    name=getattr(entity, "name", "") or entity.code,
                    description=getattr(entity, "description", ""),
                    type=entity.ENTITY_TYPE, discipline="ARCHITECTURE",
                    level=self._level_of(getattr(entity, "level_id", "")),
                    zone=zone, label=entity.status.value,
                    entity=entity, summary=summary))
        return rows

    # -- Estructura ----------------------------------------------------------
    def _structure_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        rows: List[ObjectRow] = []
        for kind in ("MATERIAL", "SECTION", "ELEMENT", "LOAD_CASE",
                     "COMBINATION"):
            for entity in self.ctx.structure.list(kind, pid):
                summary = ""
                if kind == "ELEMENT":
                    summary = entity.kind
                rows.append(ObjectRow(
                    uid=entity.id, code=entity.code,
                    name=getattr(entity, "name", "") or entity.code,
                    description=getattr(entity, "description", ""),
                    type=kind, discipline="STRUCTURE",
                    level=self._level_of(getattr(entity, "level_id", "")),
                    label=entity.status.value, entity=entity,
                    summary=summary))
        return rows

    # -- Instalaciones y seguridad -------------------------------------------
    def _networks(self, systems: Optional[set[str]] = None,
                  exclude_security: bool = False) -> List[Any]:
        pid = self.ctx.project.id
        result = []
        for network in self.ctx.installations.list("NETWORK", pid):
            if exclude_security and network.system in SECURITY_SYSTEMS:
                continue
            if systems and network.system not in systems:
                continue
            result.append(network)
        return result

    def _install_rows(self, level_id: str = "") -> List[ObjectRow]:
        rows: List[ObjectRow] = []
        for network in self._networks(exclude_security=True):
            rows.append(self._network_row(network, "INSTALLATIONS"))
            rows.extend(self._net_children(network, "INSTALLATIONS"))
        return rows

    def _security_rows(self, discipline_key: str) -> List[ObjectRow]:
        systems = set(DISCIPLINE_BY_KEY[discipline_key].systems)
        rows: List[ObjectRow] = []
        for network in self._networks(systems=systems):
            rows.append(self._network_row(network, discipline_key))
            rows.extend(self._net_children(network, discipline_key))
        return rows

    def _network_row(self, network, discipline: str) -> ObjectRow:
        return ObjectRow(
            uid=network.id, code=network.code, name=network.name,
            description=network.description, type="NETWORK",
            discipline=discipline, label=network.system,
            entity=network, summary=network.status.value)

    def _net_children(self, network, discipline: str) -> List[ObjectRow]:
        rows: List[ObjectRow] = []
        for node in self.ctx.installations.nodes_of(network.id):
            rows.append(ObjectRow(
                uid=node.id, code=node.code,
                name=node.name or node.kind, type="NODE",
                discipline=discipline, label=f"{node.kind}",
                parent_uid=network.id, entity=node,
                summary=f"({node.x:.2f}, {node.y:.2f})"))
        for segment in self.ctx.installations.segments_of(network.id):
            rows.append(ObjectRow(
                uid=segment.id, code=segment.code,
                name=segment.name or segment.kind, type="SEGMENT",
                discipline=discipline, label=segment.kind,
                parent_uid=network.id, entity=segment,
                summary=f"{segment.length_m:.2f} m"))
        return rows

    # -- Cantidades -----------------------------------------------------------
    def _qto_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        totals: Dict[str, Tuple[float, str]] = {}
        for row in self.ctx.quantities_repo.all(pid):
            code = row["formula_code"]
            quantity, unit = totals.get(code, (0.0, row["unit"] or ""))
            totals[code] = (quantity + float(row["final_quantity"]),
                            row["unit"] or unit)
        rows = []
        for code in sorted(totals):
            quantity, unit = totals[code]
            rows.append(ObjectRow(
                uid=f"qto:{code}", code=code, name=code, type="QUANTITY",
                discipline="QTO", label=unit,
                summary=f"{quantity:.2f} {unit}"))
        return rows

    # -- Presupuesto -----------------------------------------------------------
    def _budget_rows(self, level_id: str = "") -> List[ObjectRow]:
        budget = self.ctx.budget_repo.latest_budget(self.ctx.project.id)
        if not budget:
            return []
        rows = [ObjectRow(
            uid=f"budget:{budget['id']}", code=budget.get("code", ""),
            name=budget.get("name", "Presupuesto"), type="BUDGET",
            discipline="BUDGET", label=budget.get("currency", "CUP"),
            summary=f"{float(budget['total_cost']):,.2f} "
                    f"{budget.get('currency', 'CUP')}")]
        for item in self.ctx.budget_repo.budget_items_full(budget["id"]):
            chapter = item.get("chapter") or {}
            rows.append(ObjectRow(
                uid=f"item:{item['id']}", code=item.get("code", ""),
                name=item.get("description", ""), type="BUDGET_ITEM",
                discipline="BUDGET",
                label=str(chapter.get("name", "")),
                summary=f"{float(item.get('direct_cost', 0.0)):,.2f} "
                        f"{item.get('unit', '')}"))
        return rows

    # -- BIM --------------------------------------------------------------------
    def _bim_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        rows: List[ObjectRow] = []
        for level in self.ctx.architecture.list("LEVEL", pid):
            spaces = [s for s in self.ctx.architecture.list("SPACE", pid)
                      if s.level_id == level.id]
            walls = [w for w in self.ctx.architecture.list("WALL", pid)
                     if w.level_id == level.id]
            rows.append(ObjectRow(
                uid=f"bim:{level.id}", code=level.code,
                name=level.name or level.code, type="IFC_STOREY",
                discipline="BIM",
                label=f"{level.elevation_m:.2f} m",
                entity=level,
                summary=(f"{len(spaces)} locales, {len(walls)} muros")))
        return rows

    # -- Coordinación -------------------------------------------------------------
    def _clash_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        rows: List[ObjectRow] = []
        for clash in self.ctx.clash_repo.list(pid):
            rows.append(ObjectRow(
                uid=clash.id, code=clash.code, name=clash.type,
                type="CLASH", discipline="COORDINATION",
                label=clash.status,
                entity=clash, summary=clash.severity))
        return rows
    # -- Documentación -------------------------------------------------------------
    def _doc_rows(self, level_id: str = "") -> List[ObjectRow]:
        pid = self.ctx.project.id
        rows: List[ObjectRow] = []
        for drawing in self.ctx.documentation.drawings.list(pid):
            title = drawing.titleblock.get("title", "") if drawing.titleblock else ""
            rows.append(ObjectRow(
                uid=drawing.id, code=drawing.code,
                name=title or drawing.sheet or drawing.code,
                type="DRAWING", discipline="DOCUMENTATION",
                label=f"{drawing.sheet_size} {drawing.scale}",
                entity=drawing))
        for template in self.ctx.documentation.templates.list(pid):
            rows.append(ObjectRow(
                uid=template.id, code=template.code,
                name=template.name or template.code, type="DOC_TEMPLATE",
                discipline="DOCUMENTATION", entity=template))
        return rows


# -- Buscador (§92) --------------------------------------------------------------

class SearchEngine:
    """Busca en las filas del explorador por los campos del §92."""

    def __init__(self, explorer: ExplorerModel) -> None:
        self.explorer = explorer

    def search(self, query: str, search_field: str = "Todo",
               level_id: str = "") -> List[ObjectRow]:
        query = (query or "").strip().casefold()
        if not query:
            return []
        results: List[ObjectRow] = []
        for discipline in DISCIPLINES:
            for row in self.explorer.rows_for(discipline.key, level_id):
                if search_field == "Todo":
                    haystack = row.field_value("Todo")
                else:
                    haystack = row.field_value(search_field)
                if query in haystack.casefold():
                    results.append(row)
        return results


# -- Propiedades -----------------------------------------------------------------

_SKIP_FIELDS = {"ENTITY_TYPE", "allowed_kinds"}


class PropertiesModel:
    """Filas campo/valor de la selección, genéricas por dataclass."""

    @staticmethod
    def properties(row: ObjectRow) -> List[Tuple[str, str]]:
        if row.entity is not None:
            return PropertiesModel._from_entity(row.entity)
        generic = [
            ("uid", row.uid), ("código", row.code), ("nombre", row.name),
            ("tipo", row.type), ("disciplina", row.discipline),
            ("nivel", row.level), ("zona", row.zone),
            ("etiqueta", row.label), ("resumen", row.summary),
        ]
        return [(k, v) for k, v in generic if v]

    @staticmethod
    def _from_entity(entity: Any) -> List[Tuple[str, str]]:
        rows: List[Tuple[str, str]] = []
        for f in dataclasses.fields(entity):
            if f.name in _SKIP_FIELDS:
                continue
            value = getattr(entity, f.name, None)
            if value is None:
                continue
            if f.name == "status":
                value = (value.value if hasattr(value, "value")
                         else str(value))
            elif isinstance(value, float):
                value = f"{value:.3f}"
            elif isinstance(value, (list, tuple)):
                if not value:
                    continue
                value = _compact(value)
            elif isinstance(value, dict):
                if not value:
                    continue
                value = _compact(value)
            rows.append((f.name, str(value)))
        return rows


def _compact(value: Any, limit: int = 90) -> str:
    text = repr(value)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


# -- Sistema de estados (§93) ------------------------------------------------------

class EntityStateFlow:
    """Transiciones válidas entre estados de entidad (§93)."""

    TRANSITIONS: Dict[str, tuple[str, ...]] = {
        EntityStatus.DRAFT.value: ("PROPOSED", "ARCHIVED"),
        EntityStatus.PROPOSED.value: ("APPROVED", "DRAFT"),
        EntityStatus.APPROVED.value: ("ACTIVE", "DRAFT"),
        EntityStatus.ACTIVE.value: ("SUPERSEDED", "ARCHIVED"),
        EntityStatus.SUPERSEDED.value: ("ARCHIVED", "ACTIVE"),
        EntityStatus.ARCHIVED.value: ("ACTIVE",),
    }

    ENTITY_REPO_KINDS: Dict[str, tuple[str, ...]] = {
        "architecture": ("LEVEL", "ZONE", "SPACE", "WALL", "DOOR",
                         "WINDOW", "OPENING", "SPACE_RELATIONSHIP"),
        "installations": ("NETWORK", "NODE", "SEGMENT"),
        "structure": ("MATERIAL", "SECTION", "ELEMENT", "LOAD_CASE",
                      "COMBINATION"),
        "clash": ("CLASH",),
        "documentation": ("DRAWING", "DOC_TEMPLATE"),
    }

    @classmethod
    def next_states(cls, status: str) -> tuple[str, ...]:
        return cls.TRANSITIONS.get(status, ())

    @classmethod
    def can_transition(cls, old: str, new: str) -> bool:
        return new in cls.next_states(old)

    @classmethod
    def repo_for_type(cls, entity_type: str):
        for repo_key, kinds in cls.ENTITY_REPO_KINDS.items():
            if entity_type in kinds:
                return repo_key
        return None


class StateService:
    """Cambia el estado §93 de una entidad con auditoría y eventos."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def _repo(self, entity_type: str):
        repo_key = EntityStateFlow.repo_for_type(entity_type)
        if repo_key is None:
            raise ValueError(
                f"El tipo {entity_type} no admite estados §93")
        return getattr(self.ctx, repo_key)

    def change_status(self, row: ObjectRow, new_status: str) -> Any:
        repo = self._repo(row.type)
        entity = repo.get(row.type, row.uid)
        if entity is None:
            raise ValueError(f"Entidad no encontrada: {row.uid}")
        old_value = (entity.status.value if hasattr(entity.status, "value")
                     else str(entity.status))
        if not EntityStateFlow.can_transition(old_value, new_status):
            raise ValueError(
                f"Transición de estado no válida: {old_value} → {new_status}")
        old_snapshot = {"status": old_value}
        entity.status = EntityStatus(new_status)
        entity.touch()
        repo.save(entity)
        # Auditoría (§71) y evento (§75)
        from core.audit.models import make_audit_event
        self.ctx.audit_repo.append(make_audit_event(
            self.ctx.user, entity.id, entity.ENTITY_TYPE, "SET_STATUS",
            old_snapshot, {"status": new_status}, "Cambio desde la UI"))
        self.ctx.emit("OBJECT_UPDATED",
                      {"id": entity.id, "type": entity.ENTITY_TYPE,
                       "code": entity.code, "status": new_status},
                      source="ui")
        self.ctx.commit()
        # La fila de la UI refleja el cambio inmediatamente.
        row.entity = entity
        row.label = new_status
        return entity


# -- Canvas (§90) -------------------------------------------------------------------

@dataclass
class Primitive:
    """Primitiva dibujable en coordenadas de mundo (metros)."""

    kind: str                     # space | wall | opening | node | segment | element
    coords: Tuple[Tuple[float, float], ...]
    row: ObjectRow
    color_key: str = ""           # clave de color por sistema/kind


class CanvasModel:
    """Primitivas geométricas de la disciplina activa."""

    def __init__(self, ctx: Any, explorer: ExplorerModel) -> None:
        self.ctx = ctx
        self.explorer = explorer

    def primitives(self, discipline_key: str,
                   level_id: str = "") -> List[Primitive]:
        if discipline_key in ("ARCHITECTURE", "BIM"):
            return self._architecture_primitives(level_id)
        if discipline_key in ("INSTALLATIONS", "CCTV", "FIRE", "INTRUSION",
                              "ACCESS", "PERIMETER"):
            return self._network_primitives(discipline_key)
        if discipline_key == "STRUCTURE":
            return self._structure_primitives()
        return []  # Cantidades/Presupuesto/Coordinación/Documentación

    # -- Arquitectura --------------------------------------------------------
    def _architecture_primitives(self, level_id: str) -> List[Primitive]:
        pid = self.ctx.project.id
        primitives: List[Primitive] = []
        walls = self.ctx.architecture.list("WALL", pid)
        spaces = self.ctx.architecture.list("SPACE", pid)
        openings: list = []
        seen_openings: set[str] = set()
        for kind in ("DOOR", "WINDOW", "OPENING"):
            for opening in self.ctx.architecture.list(kind, pid):
                if opening.id in seen_openings:
                    continue  # OPENING es superset de DOOR/WINDOW
                seen_openings.add(opening.id)
                openings.append(opening)
        wall_by_id = {w.id: w for w in walls}
        for space in spaces:
            if level_id and space.level_id != level_id:
                continue
            if len(space.boundary) >= 3:
                primitives.append(Primitive(
                    "space", tuple(space.boundary),
                    ObjectRow(uid=space.id, code=space.code,
                              name=space.name or space.code,
                              type="SPACE", discipline="ARCHITECTURE"),
                    color_key="space"))
        for wall in walls:
            if level_id and wall.level_id != level_id:
                continue
            rect = _wall_rectangle(wall.start, wall.end, wall.thickness_m)
            primitives.append(Primitive(
                "wall", rect,
                ObjectRow(uid=wall.id, code=wall.code,
                          name=wall.code, type="WALL",
                          discipline="ARCHITECTURE",
                          entity=wall, summary=f"{wall.length_m:.2f} m"),
                color_key="wall"))
        for opening in openings:
            if level_id and opening.level_id != level_id:
                continue
            wall = wall_by_id.get(opening.wall_id)
            if wall is None:
                continue
            center = _point_along(wall.start, wall.end, opening.offset_m,
                                  opening.width_m)
            if center is None:
                continue
            half = min(opening.width_m / 2.0, wall.length_m / 2.0)
            rect = _wall_rectangle(
                (center[0], center[1]), center, 0.0)  # placeholder
            sx, sy = wall.end[0] - wall.start[0], wall.end[1] - wall.start[1]
            length = (sx * sx + sy * sy) ** 0.5 or 1.0
            ux, uy = sx / length, sy / length
            rect = (
                (center[0] - ux * half, center[1] - uy * half),
                (center[0] + ux * half, center[1] + uy * half))
            primitives.append(Primitive(
                "opening", rect,
                ObjectRow(uid=opening.id, code=opening.code,
                          name=opening.code, type=opening.kind,
                          discipline="ARCHITECTURE", entity=opening),
                color_key=opening.kind))
        return primitives

    # -- Instalaciones / seguridad ---------------------------------------------
    def _network_primitives(self, discipline_key: str) -> List[Primitive]:
        rows = self.explorer.rows_for(discipline_key)
        nodes = {row.uid: row.entity for row in rows
                 if row.type == "NODE" and row.entity is not None}
        primitives: List[Primitive] = []
        for row in rows:
            if row.type == "NODE" and row.entity is not None:
                node = row.entity
                primitives.append(Primitive(
                    "node", ((node.x, node.y),),
                    row, color_key=row.label))
            elif row.type == "SEGMENT" and row.entity is not None:
                segment = row.entity
                start = nodes.get(segment.from_node_id)
                end = nodes.get(segment.to_node_id)
                if start is None or end is None:
                    continue
                primitives.append(Primitive(
                    "segment", ((start.x, start.y), (end.x, end.y)),
                    row, color_key=row.label))
        return primitives

    # -- Estructura ---------------------------------------------------------------
    def _structure_primitives(self) -> List[Primitive]:
        pid = self.ctx.project.id
        primitives: List[Primitive] = []
        for element in self.ctx.structure.list("ELEMENT", pid):
            start = getattr(element, "start", None)
            end = getattr(element, "end", None)
            if not start or not end:
                continue
            primitives.append(Primitive(
                "element", (tuple(start), tuple(end)),
                ObjectRow(uid=element.id, code=element.code,
                          name=element.name or element.code,
                          type=element.kind, discipline="STRUCTURE",
                          entity=element),
                color_key=element.kind))
        return primitives


def _wall_rectangle(start, end, thickness: float):
    """Rectángulo del muro como polígono de 4 vértices (espesor simétrico)."""
    sx, sy = end[0] - start[0], end[1] - start[1]
    length = (sx * sx + sy * sy) ** 0.5
    if length <= 0:
        return (start, start, end, end)
    ux, uy = sx / length, sy / length
    nx, ny = -uy, ux
    half = thickness / 2.0
    return (
        (start[0] + nx * half, start[1] + ny * half),
        (end[0] + nx * half, end[1] + ny * half),
        (end[0] - nx * half, end[1] - ny * half),
        (start[0] - nx * half, start[1] - ny * half),
    )


def _point_along(start, end, offset: float, width: float):
    """Centro de un vano situado a ``offset`` del inicio del muro."""
    sx, sy = end[0] - start[0], end[1] - start[1]
    length = (sx * sx + sy * sy) ** 0.5
    if length <= 0:
        return None
    t = offset + width / 2.0
    if t < 0 or t > length:
        return None
    ux, uy = sx / length, sy / length
    return (start[0] + ux * t, start[1] + uy * t)


class Viewport:
    """Transformación mundo (m) ↔ pantalla (px) con zoom acotado."""

    MIN_SCALE = 0.05    # px por metro
    MAX_SCALE = 500.0

    def __init__(self, center_x: float = 0.0, center_y: float = 0.0,
                 scale: float = 20.0) -> None:
        self.center_x = center_x
        self.center_y = center_y
        self.scale = scale

    def to_screen(self, x: float, y: float,
                  width: int = 0, height: int = 0) -> Tuple[float, float]:
        return (width / 2 + (x - self.center_x) * self.scale,
                height / 2 - (y - self.center_y) * self.scale)

    def from_screen(self, px: float, py: float,
                    width: int = 0, height: int = 0) -> Tuple[float, float]:
        return (self.center_x + (px - width / 2) / self.scale,
                self.center_y - (py - height / 2) / self.scale)

    def zoom(self, factor: float) -> None:
        self.scale = max(self.MIN_SCALE,
                         min(self.MAX_SCALE, self.scale * factor))

    def zoom_at(self, factor: float, px: float, py: float,
                width: int, height: int) -> None:
        """Zoom manteniendo fijo el punto de mundo bajo el cursor."""
        wx, wy = self.from_screen(px, py, width, height)
        self.zoom(factor)
        ax, ay = self.from_screen(px, py, width, height)
        self.center_x += wx - ax
        self.center_y += wy - ay

    def fit(self, bounds: Tuple[float, float, float, float],
            width: int, height: int, margin_px: int = 40) -> None:
        min_x, min_y, max_x, max_y = bounds
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        scale = min((width - 2 * margin_px) / span_x,
                    (height - 2 * margin_px) / span_y)
        self.scale = max(self.MIN_SCALE,
                         min(self.MAX_SCALE, scale))
        self.center_x = (min_x + max_x) / 2.0
        self.center_y = (min_y + max_y) / 2.0

    def bounds_of(self, primitives: List[Primitive]
                  ) -> Optional[Tuple[float, float, float, float]]:
        xs: List[float] = []
        ys: List[float] = []
        for primitive in primitives:
            for x, y in primitive.coords:
                xs.append(x)
                ys.append(y)
        if not xs:
            return None
        return (min(xs), min(ys), max(xs), max(ys))


# -- Panel inferior: avisos / log / estado de cálculos (§90, §93) ---------------------

class StatusModel:
    """Avisos de validación, log de eventos y estado de cálculos."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def log_lines(self, limit: int = 100) -> List[str]:
        lines: List[str] = []
        for event in self.ctx.events_repo.recent(limit=limit):
            payload = event.get("payload", {})
            brief = " ".join(f"{k}={v}" for k, v in list(payload.items())[:3])
            lines.append(f"[{event.get('timestamp', '')}] "
                         f"{event.get('type', '')} {brief}".rstrip())
        return lines

    def calculation_rows(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.ctx.calculations_repo.recent(limit=limit)

    def validation_warnings(self) -> List[str]:
        from services.analysis_service import ValidationService
        result = ValidationService(self.ctx).validate_project()
        lines: List[str] = []
        for finding in list(result.errors) + list(result.warnings) \
                + list(result.info):
            lines.append(f"{finding.severity}: {finding.code} "
                         f"{finding.message}")
        return lines


# -- Edición de propiedades y borrado/creación (FASE 90.1) ---------------------------
#
# Toda la lógica de edición vive aquí (headless) y reutiliza los mismos
# caminos que la CLI: fachadas de servicios, auditoría §71, eventos §75
# y undo/redo persistente §77 (snapshot completo old/new UPDATE_ENTITY).


class PropertyEditor:
    """Edita campos whitelisted de una entidad con auditoría y undo.

    - ``editable_fields``  → lista [(campo, valor_actual)] para el diálogo
    - ``edit``             → valida, convierte, guarda, audita UPDATE_ENTITY,
      emite OBJECT_UPDATED, invalida cálculos y hace commit
    Los snapshots old/new son completos, así que el undo persistente
    (PersistentUndoService) puede revertir la edición sin código extra.
    """

    # Campos editables por tipo de entidad (lista blanca explícita,
    # verificada contra los dataclasses del dominio).
    EDITABLE_FIELDS: Dict[str, tuple[str, ...]] = {
        "LEVEL": ("name", "elevation_m", "height_m"),
        "ZONE": ("name",),
        "SPACE": ("name", "space_type"),
        "WALL": ("thickness_m", "height_m", "start", "end"),
        "DOOR": ("width_m", "height_m", "offset_m", "sill_height_m"),
        "WINDOW": ("width_m", "height_m", "offset_m", "sill_height_m"),
        "OPENING": ("width_m", "height_m", "offset_m"),
        "NETWORK": ("name", "description"),
        "NODE": ("name", "x", "y", "elevation_m"),
        "SEGMENT": ("name", "diameter_mm", "width_mm", "height_mm"),
        "MATERIAL": ("name", "fck_mpa", "fy_mpa", "e_gpa",
                     "density_kn_m3"),
        "SECTION": ("name", "h_mm", "b_mm", "tw_mm", "tf_mm",
                    "d_mm", "weight_kg_m"),
        "ELEMENT": ("name", "start", "end", "z0", "z1",
                    "load_udl_kn_m"),
        "LOAD_CASE": ("name", "description", "factor"),
        "CLASH": ("notes",),
        "DOC_TEMPLATE": ("name",),
    }

    @classmethod
    def editable_fields(cls, entity: Any) -> List[Tuple[str, str]]:
        """[(campo, valor_mostrado)] de los campos editables con valor."""
        allowed = cls.EDITABLE_FIELDS.get(entity.ENTITY_TYPE, ())
        rows: List[Tuple[str, str]] = []
        for name in allowed:
            value = getattr(entity, name, None)
            if value is None:
                continue
            rows.append((name, cls.format_value(value)))
        return rows

    @staticmethod
    def format_value(value: Any) -> str:
        if isinstance(value, (tuple, list)):
            return ", ".join(f"{float(v):g}" for v in value)
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    @staticmethod
    def parse_value(field: str, current: Any, text: str) -> Any:
        """Convierte el texto al tipo del campo actual (mensajes en español)."""
        text = (text or "").strip()
        if isinstance(current, bool) or isinstance(current, str):
            return text
        if isinstance(current, (tuple, list)):
            parts = [p for p in text.replace("(", " ").replace(")", " ")
                     .replace(",", " ").split() if p]
            if len(parts) != len(current):
                raise ValueError(
                    f"Se esperaban {len(current)} números separados por "
                    f"comas o espacios: «{text}»")
            try:
                return tuple(float(p) for p in parts)
            except ValueError:
                raise ValueError(f"Números no válidos: «{text}»") from None
        # numérico (float o int)
        normalized = text.replace(" ", "").replace(",", ".")
        if normalized in ("", "-"):
            raise ValueError(f"Valor numérico vacío para «{field}»")
        try:
            number = float(normalized)
        except ValueError:
            raise ValueError(f"Número no válido: «{text}»") from None
        if isinstance(current, int) and not isinstance(current, bool):
            return int(round(number))
        return number

    @staticmethod
    def _repo(ctx: Any, entity: Any):
        from services.commands_impl import _repo_for
        return _repo_for(ctx, entity.ENTITY_TYPE)

    @classmethod
    def edit(cls, ctx: Any, row: ObjectRow, field: str, text: str) -> Any:
        """Aplica «campo = texto» a la entidad de la fila y persiste."""
        from core.audit.models import make_audit_event
        from services.commands_impl import entity_snapshot

        if row is None or row.entity is None:
            raise ValueError(
                "Seleccione una entidad real (no una fila sintética) para "
                "editar.")
        entity = row.entity
        allowed = cls.EDITABLE_FIELDS.get(entity.ENTITY_TYPE, ())
        if field not in allowed or not hasattr(entity, field):
            raise ValueError(
                f"El campo «{field}» no es editable para {entity.ENTITY_TYPE}. "
                f"Editables: {', '.join(allowed) or 'ninguno'}")
        current = getattr(entity, field)
        value = cls.parse_value(field, current, text)
        old_snapshot = entity_snapshot(entity)
        setattr(entity, field, value)
        entity.touch()
        cls._repo(ctx, entity).save(entity)
        ctx.audit_repo.append(make_audit_event(
            ctx.user, entity.id, entity.ENTITY_TYPE, "UPDATE_ENTITY",
            old_snapshot, entity_snapshot(entity),
            f"Edición desde la GUI: {field}"))
        ctx.emit("OBJECT_UPDATED",
                 {"id": entity.id, "type": entity.ENTITY_TYPE,
                  "code": entity.code, "field": field}, source="ui")
        ctx.calculations_repo.mark_stale_for_object(entity.id)
        ctx.commit()
        row.entity = entity
        return entity


# -- Creación de objetos desde la GUI (FASE 90.1) --------------------------------
#
# CREATE_SPECS describe formularios declarativos: (parametro, etiqueta,
# tipo, requerido, opciones|fuente, por_defecto). EditService.resolve_
# choices resuelve las fuentes dinámicas (niveles, muros, redes...) y
# create() despacha a las fachadas, que auditan y publican eventos igual
# que desde la CLI (mismo bus de comandos §76).

SpecField = Tuple[str, str, str, bool, Any, Any]

CREATE_SPECS: Dict[str, Tuple[str, Tuple[SpecField, ...]]] = {
    "LEVEL": ("ARCHITECTURE", (
        ("name", "Nombre", "text", True, None, "Nivel nuevo"),
        ("elevation_m", "Cota (m)", "float", False, None, 0.0),
        ("height_m", "Altura (m)", "float", False, None, 3.0),
    )),
    "ZONE": ("ARCHITECTURE", (
        ("name", "Nombre", "text", True, None, ""),
        ("kind", "Tipo de zona", "choice", True,
         ("PUBLIC", "PRIVATE", "SERVICE", "TECHNICAL", "CIRCULATION",
          "EMERGENCY", "EXTERIOR"), "SERVICE"),
    )),
    "SPACE": ("ARCHITECTURE", (
        ("level_ref", "Nivel", "choice", True, "levels", ""),
        ("name", "Nombre", "text", True, None, ""),
        ("space_type", "Tipo de local", "text", False, None, "ROOM"),
        ("boundary", "Contorno «x0,y0 x1,y1 x2,y2 …»", "text", False,
         None, ""),
    )),
    "WALL": ("ARCHITECTURE", (
        ("level_ref", "Nivel", "choice", True, "levels", ""),
        ("start", "Inicio «x, y» (m)", "point", True, None, ""),
        ("end", "Fin «x, y» (m)", "point", True, None, ""),
        ("thickness_m", "Espesor (m)", "float", False, None, 0.2),
        ("height_m", "Altura (m, vacío = nivel)", "float", False, None, ""),
    )),
    "DOOR": ("ARCHITECTURE", (
        ("wall_ref", "Muro", "choice", True, "walls", ""),
        ("width_m", "Ancho (m)", "float", True, None, 0.9),
        ("height_m", "Alto (m)", "float", True, None, 2.1),
        ("offset_m", "Offset en el muro (m)", "float", False, None, 0.0),
    )),
    "WINDOW": ("ARCHITECTURE", (
        ("wall_ref", "Muro", "choice", True, "walls", ""),
        ("width_m", "Ancho (m)", "float", True, None, 1.2),
        ("height_m", "Alto (m)", "float", True, None, 1.2),
        ("offset_m", "Offset en el muro (m)", "float", False, None, 0.0),
        ("sill_height_m", "Altura de antepecho (m)", "float", False,
         None, 0.9),
    )),
    "MATERIAL": ("STRUCTURE", (
        ("name", "Nombre", "text", True, None, ""),
        ("kind", "Tipo", "choice", True,
         ("CONCRETE", "STEEL", "MASONRY", "WOOD"), "CONCRETE"),
        ("fck_mpa", "fck (MPa)", "float", False, None, 0.0),
        ("fy_mpa", "fy (MPa)", "float", False, None, 0.0),
        ("density_kn_m3", "Peso específico (kN/m3)", "float", False,
         None, 0.0),
    )),
    "SECTION": ("STRUCTURE", (
        ("name", "Nombre", "text", True, None, ""),
        ("shape", "Forma", "choice", True,
         ("RECTANGLE", "CIRCLE", "I_PROFILE"), "RECTANGLE"),
        ("h_mm", "h (mm)", "float", False, None, 0.0),
        ("b_mm", "b (mm)", "float", False, None, 0.0),
    )),
    "ELEMENT": ("STRUCTURE", (
        ("kind", "Tipo de elemento", "choice", True,
         ("FOUNDATION", "COLUMN", "BEAM", "SLAB", "WALL", "TRUSS", "BRACE",
          "CONNECTION", "PLATE", "BOLT", "WELD"), "BEAM"),
        ("name", "Nombre", "text", True, None, ""),
        ("level_ref", "Nivel (opcional)", "choice", False, "levels", ""),
        ("start", "Inicio «x, y» (m)", "point", True, None, ""),
        ("end", "Fin «x, y» (m)", "point", True, None, ""),
        ("load_udl_kn_m", "Carga repartida (kN/m)", "float", False,
         None, 0.0),
    )),
    "NETWORK": ("INSTALLATIONS", (
        ("name", "Nombre", "text", True, None, ""),
        ("system", "Sistema", "choice", True, "systems", ""),
        ("description", "Descripción", "text", False, None, ""),
    )),
    "NODE": ("INSTALLATIONS", (
        ("network_ref", "Red", "choice", True, "networks", ""),
        ("kind", "Tipo de nodo", "choice", True, "node_kinds", ""),
        ("name", "Nombre (opcional)", "text", False, None, ""),
        ("x", "X (m)", "float", True, None, ""),
        ("y", "Y (m)", "float", True, None, ""),
    )),
}


class EditService:
    """Creación, edición y borrado desde la GUI por las mismas fachadas
    y el mismo bus de comandos que la CLI (§76)."""

    def __init__(self, ctx: Any, explorer: Optional[ExplorerModel] = None) -> None:
        self.ctx = ctx
        self.explorer = explorer

    def edit(self, row: ObjectRow, field: str, text: str) -> Any:
        """Edición de propiedades delegada en PropertyEditor (auditada)."""
        return PropertyEditor.edit(self.ctx, row, field, text)

    # -- choices dinámicas -----------------------------------------------------
    def choices(self, source: str) -> List[str]:
        ctx = self.ctx
        pid = ctx.project.id
        if source == "levels":
            return [lv.name or lv.code
                    for lv in ctx.architecture.list("LEVEL", pid)]
        if source == "walls":
            return [w.code + (f" — {w.name}" if getattr(w, "name", "") else "")
                    for w in ctx.architecture.list("WALL", pid)]
        if source == "networks":
            networks = ctx.installations.list("NETWORK", pid)
            return [n.code + (f" — {n.name}" if n.name else "")
                    for n in networks]
        if source == "systems":
            from domain.installations import SYSTEMS
            return sorted(SYSTEMS)
        if source == "node_kinds":
            from domain.installations import NODE_KINDS
            return list(NODE_KINDS)
        return []

    # -- creación -----------------------------------------------------------------
    def create(self, entity_type: str, values: Dict[str, Any]) -> Any:
        from services.architecture_service import ArchitectureService
        from services.installations_service import InstallationsService
        from services.structure_service import StructureService

        if entity_type not in CREATE_SPECS:
            raise ValueError(f"Tipo no creable desde la GUI: {entity_type}")
        values = self._normalize(values, CREATE_SPECS[entity_type][1])
        arch = ArchitectureService(self.ctx)
        if entity_type == "LEVEL":
            return arch.create_level(
                name=values["name"], elevation_m=values["elevation_m"],
                height_m=values["height_m"])
        if entity_type == "ZONE":
            return arch.create_zone(name=values["name"], kind=values["kind"])
        if entity_type == "SPACE":
            return arch.create_space(
                level_ref=values["level_ref"], name=values["name"],
                space_type=values["space_type"] or "ROOM",
                boundary=self._space_boundary(
                    values, self._space_count(values["level_ref"])))
        if entity_type == "WALL":
            return arch.create_wall(
                level_ref=values["level_ref"], start=values["start"],
                end=values["end"], thickness_m=values["thickness_m"],
                height_m=self._optional_float(values, "height_m"))
        if entity_type in ("DOOR", "WINDOW"):
            return arch.create_opening(
                kind=entity_type, wall_ref=values["wall_ref"],
                width_m=values["width_m"], height_m=values["height_m"],
                offset_m=values["offset_m"],
                sill_height_m=values.get("sill_height_m", 0.0) or 0.0)
        structure = StructureService(self.ctx)
        if entity_type == "MATERIAL":
            return structure.create_material(
                name=values["name"], kind=values["kind"],
                fck_mpa=values["fck_mpa"], fy_mpa=values["fy_mpa"],
                density_kn_m3=values["density_kn_m3"])
        if entity_type == "SECTION":
            return structure.create_section(
                name=values["name"], shape=values["shape"],
                h_mm=values["h_mm"], b_mm=values["b_mm"])
        if entity_type == "ELEMENT":
            return structure.create_element(
                kind=values["kind"], name=values["name"],
                level_ref=values.get("level_ref", ""),
                start=values["start"], end=values["end"],
                load_udl_kn_m=values["load_udl_kn_m"])
        installations = InstallationsService(self.ctx)
        if entity_type == "NETWORK":
            return installations.create_network(
                name=values["name"], system=values["system"],
                description=values["description"])
        if entity_type == "NODE":
            return installations.add_node(
                values["network_ref"], values["kind"], values["x"],
                values["y"], name=values["name"])
        raise ValueError(f"Tipo no creable desde la GUI: {entity_type}")

    # -- helpers de creación -----------------------------------------------------
    @staticmethod
    def _normalize(values: Dict[str, Any],
                   spec: Tuple[SpecField, ...]) -> Dict[str, Any]:
        """Texto → float/tupla según el spec (los Entry devuelven texto)."""
        out: Dict[str, Any] = {}
        for param, _label, kind, required, _options, default in spec:
            value = values.get(param, default)
            if kind == "float":
                if value in ("", None):
                    value = default  # puede ser "" (opcional) o numérico
                if isinstance(value, str):
                    if value.strip():
                        value = float(PropertyEditor.parse_value(
                            param, 0.0, value))
                elif isinstance(value, (int, float)):
                    value = float(value)
            elif kind == "point":
                if isinstance(value, str):
                    if value.strip():
                        value = PropertyEditor.parse_value(
                            param, (0.0, 0.0), value)
                    else:
                        value = ""  # lo detecta el chequeo de obligatorios
            out[param] = value
        missing = [param for param, _l, kind, required, _o, _d in spec
                   if required and not str(out.get(param, "")).strip()
                   and kind in ("text", "choice", "point")]
        if missing:
            raise ValueError("Faltan campos obligatorios: "
                             + ", ".join(missing))
        return out

    @staticmethod
    def _optional_float(values: Dict[str, Any], key: str) -> Optional[float]:
        value = values.get(key)
        if value in ("", None):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _space_count(self, level_ref: str) -> int:
        """Locales ya existentes en el nivel (para desplazar el rectángulo)."""
        try:
            from services.architecture_service import ArchitectureService
            level = ArchitectureService(self.ctx).get_level_by_name_or_code(
                level_ref)
        except Exception:  # noqa: BLE001 - nivel se validará al crear
            return 0
        if level is None:
            return 0
        pid = self.ctx.project.id
        return sum(1 for s in self.ctx.architecture.list("SPACE", pid)
                   if s.level_id == level.id)

    @staticmethod
    def _space_boundary(values: Dict[str, Any],
                        existing: int = 0) -> List[Tuple[float, float]]:
        text = (values.get("boundary") or "").strip()
        if text:
            pairs = text.replace("(", " ").replace(")", " ").split()
            if len(pairs) < 3:
                raise ValueError(
                    "Contorno no válido: use «x0,y0 x1,y1 x2,y2 …» (mínimo "
                    "3 vértices)")
            boundary: List[Tuple[float, float]] = []
            for pair in pairs:
                parts = pair.split(",")
                if len(parts) != 2:
                    raise ValueError(
                        f"Vértice no válido: «{pair}» (use x,y)")
                try:
                    boundary.append((float(parts[0].strip()),
                                     float(parts[1].strip())))
                except ValueError:
                    raise ValueError(
                        f"Números no válidos en «{pair}»") from None
            return boundary
        # Rectángulo 4x3 m por defecto, desplazado para no solapar.
        x0 = 2.0 + 6.0 * existing
        return [(x0, 0.0), (x0 + 4.0, 0.0), (x0 + 4.0, 3.0), (x0, 3.0)]

    # -- borrado ---------------------------------------------------------------------
    def delete(self, row: ObjectRow) -> str:
        """Borra la entidad de la fila por la fachada correspondiente."""
        if row is None or row.entity is None:
            raise ValueError(
                "Seleccione una entidad real (no una fila sintética) para "
                "borrar.")
        entity_type, uid, code = row.type, row.uid, row.code
        if entity_type in ("LEVEL", "ZONE", "SPACE", "WALL", "DOOR",
                           "WINDOW", "OPENING", "SPACE_RELATIONSHIP"):
            from services.architecture_service import ArchitectureService
            ArchitectureService(self.ctx).delete_entity(entity_type, uid)
        elif entity_type in ("NETWORK", "NODE", "SEGMENT"):
            from services.installations_service import InstallationsService
            InstallationsService(self.ctx).delete_entity(entity_type, uid)
        elif entity_type in ("MATERIAL", "SECTION", "ELEMENT", "LOAD_CASE",
                             "COMBINATION"):
            self._delete_generic(entity_type, uid)
        elif entity_type == "DRAWING":
            from services.documentation_service import DocumentationService
            DocumentationService(self.ctx).delete_drawing(code or uid)
            self.ctx.commit()
        else:
            raise ValueError(
                f"{discipline_label(row.discipline)}: {entity_type} no se "
                "puede borrar desde la GUI.")
        return code

    def _delete_generic(self, entity_type: str, entity_id: str) -> str:
        from core.audit.models import make_audit_event
        from services.commands_impl import (DeleteEntityCommand,
                                            entity_snapshot, _repo_for)
        repo = _repo_for(self.ctx, entity_type)
        entity = repo.get(entity_type, entity_id)
        if entity is None:
            raise ValueError(f"Objeto no encontrado: {entity_id}")
        command = DeleteEntityCommand(entity_type, entity.id)
        result = self.ctx.command_bus.execute(command, self.ctx)
        old_value = {"entity": (result or {}).get("snapshot", {}),
                     "cascade": (result or {}).get("cascade", [])}
        self.ctx.audit_repo.append(make_audit_event(
            self.ctx.user, entity.id, entity_type, "DELETE_ENTITY",
            old_value, None, "Borrado desde la GUI"))
        self.ctx.emit("OBJECT_DELETED",
                      {"id": entity.id, "type": entity_type,
                       "code": entity.code}, source="ui")
        self.ctx.calculations_repo.mark_stale_for_object(entity.id)
        self.ctx.quantities_repo.delete_for_object(entity.id)
        self.ctx.commit()
        return entity.code


__all__ = [
    "ObjectRow", "SEARCH_FIELDS", "ExplorerModel", "SearchEngine",
    "PropertiesModel", "EntityStateFlow", "StateService",
    "Primitive", "CanvasModel", "Viewport", "StatusModel",
    "PropertyEditor", "CREATE_SPECS", "EditService", "SpecField",
    "_wall_rectangle", "_point_along",
]
