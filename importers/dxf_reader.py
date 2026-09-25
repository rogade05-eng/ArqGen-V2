"""DXF entity import (spec 94): LINE segments -> walls, closed LWPOLYLINE
-> spaces. Layers are matched by explicit name or by deterministic hints
(muro/wall for walls, local/space/hab/ambiente for spaces). The APPLY
stage creates entities through ArchitectureService, so every import is
transactional (CommandBus), audited and emits the standard events.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from core.errors import ImportErrorARQ

WALL_LAYER_HINTS = ("muro", "wall", "arq-wall")
SPACE_LAYER_HINTS = ("local", "space", "hab", "ambiente", "arq-space")


def _layer_matches(layer: str, explicit: str, hints: Tuple[str, ...]) -> bool:
    if explicit:
        return layer.lower() == explicit.lower()
    return any(hint in layer.lower() for hint in hints)


def _polygon_area(points: List[Tuple[float, float]]) -> float:
    total = 0.0
    count = len(points)
    for i in range(count):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % count]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _point_inside(point: Tuple[float, float],
                  polygon: List[Tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    count = len(polygon)
    j = count - 1
    for i in range(count):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def _entity_text(entity) -> Optional[str]:
    try:
        if entity.dxftype() == "TEXT":
            return str(entity.dxf.text).strip()
        if entity.dxftype() == "MTEXT":
            return str(entity.text).strip()
    except Exception:  # malformed entity attributes
        return None
    return None


def _entity_point(entity) -> Optional[Tuple[float, float]]:
    try:
        insert = entity.dxf.insert
        return float(insert.x), float(insert.y)
    except Exception:
        return None


class DxfImporter:
    """Import pipeline for DXF drawings into wall/space entities."""

    def __init__(self, layer_walls: str = "", layer_spaces: str = "") -> None:
        self.layer_walls = layer_walls
        self.layer_spaces = layer_spaces
        self.report: Dict[str, Any] = {}

    def preview(self, path: str) -> Dict[str, Any]:
        """DETECT+PARSE+VALIDATE -> candidate report (no changes)."""
        if not os.path.isfile(path):
            raise ImportErrorARQ(
                message=f"Archivo DXF inexistente: {path}",
                code="ARQ-IMP-050", context={"path": path})
        try:
            import ezdxf
        except ImportError as exc:  # pragma: no cover
            raise ImportErrorARQ(
                message="ezdxf no está instalado; ejecute el bat de "
                "instalación de dependencias", code="ARQ-IMP-051") from exc
        try:
            doc = ezdxf.readfile(path)
        except Exception as exc:
            raise ImportErrorARQ(
                message=f"DXF ilegible: {exc}", code="ARQ-IMP-052",
                context={"path": path}) from exc

        layers_seen: Dict[str, Dict[str, int]] = {}
        wall_candidates: List[Dict[str, Any]] = []
        space_candidates: List[Dict[str, Any]] = []
        texts: List[Tuple[Tuple[float, float], str]] = []
        warnings: List[str] = []
        zero_length = 0
        unclosed = 0

        for entity in doc.modelspace():
            kind = entity.dxftype()
            layer = str(entity.dxf.layer)
            stats = layers_seen.setdefault(layer, {})
            stats[kind] = stats.get(kind, 0) + 1

            if kind == "TEXT" or kind == "MTEXT":
                point = _entity_point(entity)
                text = _entity_text(entity)
                if point and text:
                    texts.append((point, text))
            elif kind == "LINE" and _layer_matches(
                    layer, self.layer_walls, WALL_LAYER_HINTS):
                start, end = entity.dxf.start, entity.dxf.end
                a, b = (float(start.x), float(start.y)), (float(end.x), float(end.y))
                if (abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9):
                    zero_length += 1
                    continue
                wall_candidates.append({"start": a, "end": b, "layer": layer})
            elif kind == "LWPOLYLINE" and _layer_matches(
                    layer, self.layer_spaces, SPACE_LAYER_HINTS):
                points = [(float(x), float(y)) for x, y in entity.get_points("xy")]
                if not entity.closed:
                    unclosed += 1
                    warnings.append(
                        f"Polilínea abierta en capa '{layer}' ignorada")
                    continue
                if len(points) < 3:
                    zero_length += 1
                    continue
                space_candidates.append({"boundary": points, "layer": layer})
            elif kind == "LWPOLYLINE" and _layer_matches(
                    layer, self.layer_walls, WALL_LAYER_HINTS):
                points = [(float(x), float(y)) for x, y in entity.get_points("xy")]
                if entity.closed and len(points) == 4:
                    # rectangle outline of a wall: convert to axis (2nd->3rd edge)
                    warnings.append(
                        f"Contorno cerrado de muro en capa '{layer}': se "
                        "convierte a eje central (lado mayor)")
                    diag1 = ((points[0][0] + points[2][0]) / 2.0,
                             (points[0][1] + points[2][1]) / 2.0)
                    edge_a = _edge_mid(points[0], points[1])
                    edge_b = _edge_mid(points[2], points[3])
                    edge_c = _edge_mid(points[1], points[2])
                    edge_d = _edge_mid(points[3], points[0])
                    len_ad = _dist(edge_a, edge_b)
                    len_bc = _dist(edge_c, edge_d)
                    first, second = ((edge_a, edge_b) if len_ad >= len_bc
                                     else (edge_c, edge_d))
                    _ = diag1
                    wall_candidates.append({"start": first, "end": second,
                                            "layer": layer})
                else:
                    warnings.append(
                        f"LWPOLYLINE de muro no rectangular en capa '{layer}' "
                        "ignorada")

        # deterministic ordering + space naming from contained TEXT
        wall_candidates.sort(key=lambda w: (w["start"][1], w["start"][0],
                                            w["end"][0], w["end"][1]))
        space_candidates.sort(key=lambda s: (min(p[1] for p in s["boundary"]),
                                             min(p[0] for p in s["boundary"])))
        for index, candidate in enumerate(space_candidates, start=1):
            name = None
            for point, text in sorted(texts):
                if _point_inside(point, candidate["boundary"]):
                    name = text
                    break
            area = _polygon_area(candidate["boundary"])
            candidate["area_m2"] = round(area, 4)
            candidate["name"] = name or f"LOCAL-{index:03d}"

        errors: List[str] = []
        if not wall_candidates and not space_candidates:
            errors.append(
                "No se detectaron candidatos: ninguna entidad en capas de "
                f"muros ({', '.join(WALL_LAYER_HINTS)}) ni locales "
                f"({', '.join(SPACE_LAYER_HINTS)})")
            if layers_seen:
                errors.append(f"Capas vistas: {', '.join(sorted(layers_seen))}")

        self.report = {
            "file": path,
            "layer_walls": self.layer_walls or "(hint: muro/wall)",
            "layer_spaces": self.layer_spaces or "(hint: local/space/hab/ambiente)",
            "layers_seen": layers_seen,
            "counts": {"walls": len(wall_candidates),
                       "spaces": len(space_candidates),
                       "texts": len(texts),
                       "zero_length_or_invalid": zero_length,
                       "unclosed_polylines": unclosed},
            "spaces_preview": [{"name": s["name"], "area_m2": s["area_m2"],
                                "layer": s["layer"]}
                               for s in space_candidates[:10]],
            "warnings": warnings, "errors": errors,
            "_walls": wall_candidates, "_spaces": space_candidates,
        }
        return self.report

    def apply(self, path: str, architecture, level_ref: str,
              thickness_m: float = 0.2, height_m: Optional[float] = None
              ) -> Dict[str, Any]:
        """APPROVE+IMPORT stage: creates entities in the open project.

        ``architecture`` is a services.architecture_service.ArchitectureService.
        Returns the counts dict; audit + events are emitted here.
        """
        report = self.preview(path)
        if report["errors"]:
            raise ImportErrorARQ(
                message=f"La importación DXF tiene errores: {report['errors']}",
                code="ARQ-IMP-053", context={"file": path})
        try:
            level = architecture.get_level_by_name_or_code(level_ref)
        except Exception:
            level = architecture.create_level(name=level_ref)
        level_ref = level.code  # services resolve levels by code/name

        created_walls = 0
        for candidate in report["_walls"]:
            architecture.create_wall(
                level_ref, candidate["start"], candidate["end"],
                thickness_m=thickness_m, height_m=height_m)
            created_walls += 1
        created_spaces = 0
        for candidate in report["_spaces"]:
            architecture.create_space(
                level_ref, candidate["name"], "IMPORTED",
                candidate["boundary"])
            created_spaces += 1

        context = architecture.ctx
        from core.audit.models import make_audit_event
        context.audit_repo.append(make_audit_event(
            user=getattr(context, "user", "local"),
            object_id=context.project.id, object_type="PROJECT",
            command="IMPORT_DXF", old_value=None,
            new_value={"file": path, "level": level_ref,
                       "walls": created_walls, "spaces": created_spaces},
            reason="import", result="OK"))
        context.emit("DOCUMENT_CHANGED", {
            "action": "IMPORTED_DXF", "path": path,
            "walls": created_walls, "spaces": created_spaces})
        return {"walls": created_walls, "spaces": created_spaces,
                "level": level.name}


def _edge_mid(p1: Tuple[float, float], p2: Tuple[float, float]
              ) -> Tuple[float, float]:
    return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)


def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


__all__ = ["DxfImporter", "WALL_LAYER_HINTS", "SPACE_LAYER_HINTS"]
