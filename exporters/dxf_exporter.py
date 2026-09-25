"""DXF exporter via ezdxf (spec sections 64, 65, 69, 95).

Real multi-layer DXF: wall outlines, openings, space boundaries with
name/area labels, level separated by DXF layout. Units = meters.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.errors import ExportError
from domain.model import Level, Opening, Space, Wall


class DXFExporter:
    LAYERS = {
        "ARQ-WALL": {"color": 7},
        "ARQ-OPENING": {"color": 3},
        "ARQ-SPACE": {"color": 8},
        "ARQ-TEXT": {"color": 1},
        "ARQ-AXIS": {"color": 5},
    }

    def export(self, context, out_path: str, level_ref: Optional[str] = None) -> str:
        try:
            import ezdxf
        except ImportError as exc:  # pragma: no cover - dependency guarded by requirements
            raise ExportError(
                message="ezdxf no está instalado; ejecute el bat de instalación de dependencias",
                code="ARQ-EXP-030") from exc

        project_id = context.project.id
        walls = context.architecture.list("WALL", project_id)
        openings = context.architecture.list("OPENING", project_id)
        spaces = context.architecture.list("SPACE", project_id)
        levels = {l.id: l for l in context.architecture.list("LEVEL", project_id)}

        if level_ref:
            level = self._resolve_level(levels, level_ref)
            walls = [w for w in walls if w.level_id == level.id]
            openings = [o for o in openings if o.level_id == level.id]
            spaces = [s for s in spaces if s.level_id == level.id]
            levels = {level.id: level}

        if not walls and not spaces:
            raise ExportError(
                message="No hay geometría que exportar (muros o locales)",
                code="ARQ-EXP-031",
                suggested_action="Cree muros o locales antes de exportar el plano.",
            )

        doc = ezdxf.new("R2010", setup=True)
        doc.header["$INSUNITS"] = 6  # meters
        doc.header["$MEASUREMENT"] = 1
        for layer, props in self.LAYERS.items():
            if layer not in doc.layers:
                doc.layers.add(name=layer, color=props["color"])

        openings_by_wall: Dict[str, List[Opening]] = {}
        for opening in openings:
            openings_by_wall.setdefault(opening.wall_id, []).append(opening)

        # One layout per level (paperspace layouts support the same entity factory).
        for index, (level_id, level) in enumerate(levels.items()):
            offset_y = index * 100.0
            layout_name = f"PLANTA_{(level.name or f'NIVEL_{index+1}').upper().replace(' ', '_')}"
            try:
                target = doc.layouts.get(layout_name)
            except Exception:
                target = doc.layouts.new(layout_name)

            for wall in [w for w in walls if w.level_id == level_id]:
                self._draw_wall(target, wall, openings_by_wall.get(wall.id, []), offset_y)
            for space in [s for s in spaces if s.level_id == level_id]:
                self._draw_space(target, space, offset_y)

        directory = os.path.dirname(os.path.abspath(out_path))
        os.makedirs(directory, exist_ok=True)
        try:
            doc.saveas(out_path)
        except Exception as exc:
            raise ExportError(
                message=f"No se pudo escribir el DXF: {exc}",
                code="ARQ-EXP-032", context={"path": out_path}) from exc
        context.emit("EXPORT_COMPLETED", {"format": "DXF", "path": out_path})
        return out_path

    @staticmethod
    def _resolve_level(levels: Dict[str, Level], ref: str) -> Level:
        for level in levels.values():
            if level.id == ref or level.code == ref or level.name.lower() == ref.lower():
                return level
        raise ExportError(message=f"Nivel no encontrado: {ref}", code="ARQ-EXP-033")

    def _draw_wall(self, msp, wall: Wall, openings: List[Opening], offset_y: float) -> None:
        from core.geometry import engine as ge
        from core.geometry.primitives import Line, Point
        axis = Line(Point(*wall.start), Point(*wall.end))
        outline = ge.wall_outline(axis, wall.thickness_m)
        points = [(p.x, p.y + offset_y) for p in outline.points]
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "ARQ-WALL"})
        # Openings: rectangle on the wall + door swing arc
        if axis.length <= 0:
            return
        for opening in openings:
            self._draw_opening(msp, axis, wall, opening, offset_y)

    def _draw_opening(self, msp, axis, wall: Wall, opening: Opening, offset_y: float) -> None:
        from core.geometry import engine as ge
        from core.geometry.primitives import Line, Point
        t0 = opening.offset_m / axis.length
        t1 = (opening.offset_m + opening.width_m) / axis.length
        p_a = Point(axis.start.x + (axis.end.x - axis.start.x) * t0,
                    axis.start.y + (axis.end.y - axis.start.y) * t0)
        p_b = Point(axis.start.x + (axis.end.x - axis.start.x) * t1,
                    axis.start.y + (axis.end.y - axis.start.y) * t1)
        half = wall.thickness_m / 2.0
        left_a = ge.offset_line(Line(p_a, p_b), half).start
        right_a = ge.offset_line(Line(p_a, p_b), -half).start
        left_b = ge.offset_line(Line(p_a, p_b), half).end
        right_b = ge.offset_line(Line(p_a, p_b), -half).end
        rect = [left_a.to_tuple(), left_b.to_tuple(), right_b.to_tuple(), right_a.to_tuple()]
        shifted = [(x, y + offset_y) for x, y in rect]
        msp.add_lwpolyline(shifted, close=True, dxfattribs={"layer": "ARQ-OPENING"})
        if opening.kind == "DOOR":
            # Swing arc (90°) from hinge at left_a
            radius = opening.width_m
            start_angle = Line(left_a, p_b).angle_deg()
            msp.add_arc(
                center=(left_a.x, left_a.y + offset_y), radius=radius,
                start_angle=start_angle, end_angle=start_angle + 90,
                dxfattribs={"layer": "ARQ-OPENING"})
        elif opening.kind == "WINDOW":
            mid = Point((left_a.x + right_b.x) / 2, (left_a.y + right_b.y) / 2)
            msp.add_line((left_a.x, left_a.y + offset_y), (right_b.x, right_b.y + offset_y),
                         dxfattribs={"layer": "ARQ-OPENING"})

    def _draw_space(self, msp, space: Space, offset_y: float) -> None:
        if len(space.boundary) < 3:
            return
        points = [(x, y + offset_y) for x, y in space.boundary]
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "ARQ-SPACE"})
        centroid_x = sum(p[0] for p in points) / len(points)
        centroid_y = sum(p[1] for p in points) / len(points)
        label = f"{space.name} ({space.area_m2():.1f} m2)"
        msp.add_text(
            label,
            height=0.2,
            dxfattribs={"layer": "ARQ-TEXT"},
        ).set_placement((centroid_x - 0.5, centroid_y + offset_y))
        area_text = f"AREA {space.area_m2():.2f} m2"
        msp.add_text(
            area_text,
            height=0.15,
            dxfattribs={"layer": "ARQ-TEXT"},
        ).set_placement((centroid_x - 0.5, centroid_y - 0.35 + offset_y))


__all__ = ["DXFExporter"]
