"""ExportService: format registry and dispatch (spec section 95)."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from core.errors import ExportError
from services.context import ProjectContext

ExportFunc = Callable[[ProjectContext, str], str]


class ExportService:
    """export(project, format, options) — spec 95 contract."""

    def __init__(self) -> None:
        self._formats: Dict[str, Callable[..., str]] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        from exporters.csv_exporter import CSVExporter
        from exporters.dxf_exporter import DXFExporter
        from exporters.ifc_exporter import IfcExporter
        from exporters.json_io import JSONExporter
        from exporters.xlsx_exporter import XLSXExporter

        self._formats["DXF"] = DXFExporter().export
        self._formats["JSON"] = JSONExporter().export
        self._formats["XLSX"] = XLSXExporter().export
        self._formats["CSV"] = CSVExporter().export
        self._formats["IFC"] = IfcExporter().export

    def register(self, fmt: str, func: ExportFunc) -> None:
        """Plugins may register additional exporters (spec 89)."""
        self._formats[fmt.upper()] = func

    def formats(self) -> list[str]:
        return sorted(self._formats)

    def export(self, context: ProjectContext, fmt: str, out_path: str,
               options: Optional[Dict[str, str]] = None) -> str:
        key = (fmt or "").upper()
        func = self._formats.get(key)
        if func is None:
            raise ExportError(
                message=f"Formato de exportación no soportado: {fmt}",
                code="ARQ-EXP-060",
                context={"supported": self.formats()},
            )
        options = options or {}
        if key == "CSV":
            return func(context, out_path, table=options.get("table", "quantities"))
        if key == "DXF":
            return func(context, out_path, level_ref=options.get("level"))
        return func(context, out_path)


__all__ = ["ExportService"]
