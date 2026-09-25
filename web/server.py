"""Servidor Web API y de visualización en vivo para ArqGen V2.

Conecta directamente el motor de Generación de Arquitectura Sin IA,
el Catálogo PRECONS III Oficial (15,981 renglones) y los cálculos
estructurales y de viento/sismo según Normas Cubanas (NC) con
una interfaz web moderna e interactiva 2D/3D.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any, Dict

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engines.cuban_standards_engine import (
    calculate_seismic_nc46,
    calculate_wind_nc285,
    design_concrete_beam,
    design_concrete_column,
)
from exporters.dxf_exporter import DXFExporter
from exporters.ifc_exporter import IfcExporter
from services.context import ApplicationContext
from services.generative_architecture_service import GenerativeArchitectureService
from services.precons_catalog_service import PreconsCatalogService

APP_CTX = ApplicationContext()
PRECONS_SRV = PreconsCatalogService()

# Proyecto en memoria / temporal activo
ACTIVE_PROJ_PATH = os.path.join(tempfile.gettempdir(), "arqgen_web_active.arqgen")
if os.path.exists(ACTIVE_PROJ_PATH):
    try:
        ACTIVE_CTX = APP_CTX.open_project(ACTIVE_PROJ_PATH)
    except Exception:
        os.remove(ACTIVE_PROJ_PATH)
        ACTIVE_CTX = APP_CTX.create_project(ACTIVE_PROJ_PATH, name="Proyecto ArqGen V2")
else:
    ACTIVE_CTX = APP_CTX.create_project(ACTIVE_PROJ_PATH, name="Proyecto ArqGen V2")
    # Generar demo inicial VIVIENDA_2D
    GenerativeArchitectureService(ACTIVE_CTX).generate("VIVIENDA_2D")


class ArqGenWebHandler(SimpleHTTPRequestHandler):
    """Handler HTTP para servir la UI web y endpoints JSON REST API."""

    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(PROJECT_ROOT, "web")
        super().__init__(*args, directory=static_dir, **kwargs)

    def end_headers(self):
        # Permitir CORS y hosts de Arena preview
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)
        return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # 1. API: Estado actual del modelo (locales, muros, vanos, redes MEP)
        if path == "/api/project/state":
            try:
                spaces = ACTIVE_CTX.architecture.list("SPACE", ACTIVE_CTX.project.id)
                walls = ACTIVE_CTX.architecture.list("WALL", ACTIVE_CTX.project.id)
                doors = ACTIVE_CTX.architecture.list("DOOR", ACTIVE_CTX.project.id)
                windows = ACTIVE_CTX.architecture.list("WINDOW", ACTIVE_CTX.project.id)

                # Cargar redes, nodos y tramos MEP
                networks = ACTIVE_CTX.installations.list("NETWORK", ACTIVE_CTX.project.id)
                net_map = {n.id: n.system for n in networks}
                nodes = ACTIVE_CTX.installations.list("NODE", ACTIVE_CTX.project.id)
                segs = ACTIVE_CTX.installations.list("SEGMENT", ACTIVE_CTX.project.id)
                node_pos = {nd.id: (nd.x, nd.y) for nd in nodes}

                data = {
                    "project_name": ACTIVE_CTX.project.name,
                    "spaces": [{
                        "id": s.id, "code": s.code, "name": s.name,
                        "type": s.space_type,
                        "boundary": s.boundary,
                        "area_m2": round(0.5 * abs(sum(
                            s.boundary[i][0] * s.boundary[(i+1)%len(s.boundary)][1] -
                            s.boundary[(i+1)%len(s.boundary)][0] * s.boundary[i][1]
                            for i in range(len(s.boundary))
                        )), 2)
                    } for s in spaces],
                    "walls": [{
                        "id": w.id, "code": w.code, "name": f"Muro {w.code}",
                        "start": w.start, "end": w.end,
                        "thickness_m": w.thickness_m, "height_m": w.height_m,
                        "structural": w.structural
                    } for w in walls],
                    "doors": [{
                        "id": d.id, "code": d.code, "wall_id": d.wall_id,
                        "width_m": d.width_m, "height_m": d.height_m,
                        "offset_m": d.offset_m, "swing": d.swing
                    } for d in doors],
                    "windows": [{
                        "id": win.id, "code": win.code, "wall_id": win.wall_id,
                        "width_m": win.width_m, "height_m": win.height_m,
                        "offset_m": win.offset_m, "sill_height_m": win.sill_height_m
                    } for win in windows],
                    "mep_networks": [{
                        "id": n.id, "code": n.code, "name": n.name, "system": n.system
                    } for n in networks],
                    "mep_nodes": [{
                        "id": nd.id, "code": nd.code, "name": nd.name, "kind": nd.kind,
                        "x": nd.x, "y": nd.y, "elevation_m": nd.elevation_m,
                        "system": net_map.get(nd.network_id, "MEP")
                    } for nd in nodes],
                    "mep_segments": [{
                        "id": s.id, "code": s.code, "name": s.name, "kind": s.kind,
                        "from_node": s.from_node_id, "to_node": s.to_node_id,
                        "x1": node_pos.get(s.from_node_id, (0, 0))[0],
                        "y1": node_pos.get(s.from_node_id, (0, 0))[1],
                        "x2": node_pos.get(s.to_node_id, (0, 0))[0],
                        "y2": node_pos.get(s.to_node_id, (0, 0))[1],
                        "diameter_mm": s.diameter_mm,
                        "system": net_map.get(s.network_id, "MEP")
                    } for s in segs]
                }
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # 2. API: Búsqueda PRECONS III
        if path == "/api/precons/search":
            query = qs.get("q", [""])[0]
            limit = int(qs.get("limit", [30])[0])
            results = PRECONS_SRV.search_renglones(query, limit=limit)
            self._send_json({"query": query, "count": len(results), "results": results})
            return

        # 3. API: APU PRECONS III
        if path == "/api/precons/apu":
            code = qs.get("code", ["030222"])[0]
            qty = float(qs.get("qty", [1.0])[0])
            try:
                apu = PRECONS_SRV.calculate_apu(code, quantity=qty)
                self._send_json(apu)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 4. API: Recursos PRECONS III
        if path == "/api/precons/resources":
            query = qs.get("q", [""])[0]
            tipo = qs.get("tipo", [None])[0]
            limit = int(qs.get("limit", [30])[0])
            results = PRECONS_SRV.search_recursos(query, kind=tipo, limit=limit)
            self._send_json({"results": results})
            return

        # 5. Exportar DXF
        if path == "/api/export/dxf":
            dxf_path = os.path.join(tempfile.gettempdir(), "planta_arqgen.dxf")
            DXFExporter().export(ACTIVE_CTX, dxf_path)
            with open(dxf_path, "rb") as fh:
                content = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/dxf")
            self.send_header("Content-Disposition", 'attachment; filename="planta_arqgen.dxf"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # 6. Exportar IFC
        if path == "/api/export/ifc":
            ifc_path = os.path.join(tempfile.gettempdir(), "modelo_arqgen.ifc")
            IfcExporter().export(ACTIVE_CTX, ifc_path)
            with open(ifc_path, "rb") as fh:
                content = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-step")
            self.send_header("Content-Disposition", 'attachment; filename="modelo_arqgen.ifc"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # Servir index.html y estáticos por defecto
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        # 1. Generador de Arquitectura Sin IA
        if path == "/api/generate":
            global ACTIVE_CTX
            template = body.get("template", "VIVIENDA_2D")
            width = body.get("width")
            depth = body.get("depth")
            include_mep = body.get("include_mep", True)

            try:
                # Reiniciar proyecto temporal limpio
                ACTIVE_CTX.close()
                if os.path.exists(ACTIVE_PROJ_PATH):
                    os.remove(ACTIVE_PROJ_PATH)
                ACTIVE_CTX = APP_CTX.create_project(ACTIVE_PROJ_PATH, name=f"Vivienda Generada ({template})")

                gen = GenerativeArchitectureService(ACTIVE_CTX)
                result = gen.generate(template_key=template, width=width, depth=depth, include_mep=include_mep)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # --- MEP & SEGURIDAD ENDPOINTS ---
        if path == "/api/mep/bioclimatic":
            from engines.mep_security_engine import analyze_bioclimatic
            try:
                width = float(body.get("width", 9.5))
                depth = float(body.get("depth", 8.5))
                orientation = str(body.get("orientation", "SUR"))
                spaces = [
                    {"name": "Sala-Comedor", "area_m2": round(width * depth * 0.45, 2)},
                    {"name": "Dormitorios", "area_m2": round(width * depth * 0.35, 2)},
                    {"name": "Servicios", "area_m2": round(width * depth * 0.20, 2)},
                ]
                wins = [
                    {"width_m": 1.40, "height_m": 1.20},
                    {"width_m": 1.40, "height_m": 1.20},
                    {"width_m": 1.20, "height_m": 1.20},
                    {"width_m": 1.00, "height_m": 1.00},
                ]
                res = analyze_bioclimatic(spaces, wins, width, depth, orientation=orientation)
                self._send_json(res.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/mep/hydraulic":
            from engines.mep_security_engine import calculate_hydraulic_plumbing
            try:
                occ = int(body.get("occupants", 4))
                aut = float(body.get("autonomy_days", 2.5))
                pw = calculate_hydraulic_plumbing(num_occupants=occ, reserve_days=aut)
                self._send_json(pw.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/mep/electrical":
            from engines.mep_security_engine import calculate_electrical_panel
            try:
                ac = int(body.get("ac_units", 2)) > 0
                heater = bool(body.get("water_heater", True))
                el = calculate_electrical_panel(has_ac=ac, has_water_heater=heater)
                self._send_json(el.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/mep/sadi":
            from engines.mep_security_engine import calculate_sadi_saci
            try:
                area = float(body.get("area", 80.0))
                sadi = calculate_sadi_saci(building_area_m2=area)
                self._send_json(sadi.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/mep/saci":
            from engines.mep_security_engine import calculate_sadi_saci
            try:
                area = float(body.get("area", 80.0))
                hazard = str(body.get("hazard", "RESIDENCIAL_LIGERO"))
                saci = calculate_sadi_saci(building_area_m2=area, occupancy_risk=hazard)
                self._send_json(saci.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        if path == "/api/mep/cctv":
            from engines.mep_security_engine import calculate_cctv_system
            try:
                portal = bool(body.get("portal", True))
                patio = bool(body.get("patio", True))
                cctv = calculate_cctv_system(has_portal=portal, has_patio=patio)
                self._send_json(cctv.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 2. Viga NC 207
        if path == "/api/struct/beam":
            try:
                res = design_concrete_beam(
                    b_m=float(body.get("b", 0.20)),
                    h_m=float(body.get("h", 0.35)),
                    mu_kn_m=float(body.get("mu", 25.0)),
                    vu_kn=float(body.get("vu", 20.0)),
                    fc_mpa=float(body.get("fc", 25.0)),
                    fy_mpa=float(body.get("fy", 400.0))
                )
                self._send_json(res.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 3. Columna NC 207 / NC 450
        if path == "/api/struct/column":
            try:
                res = design_concrete_column(
                    b_m=float(body.get("b", 0.25)),
                    h_m=float(body.get("h", 0.25)),
                    pu_kn=float(body.get("pu", 300.0)),
                    mu_kn_m=float(body.get("mu", 15.0)),
                    fc_mpa=float(body.get("fc", 25.0)),
                    num_bars=int(body.get("bars", 4)),
                    bar_diameter_mm=float(body.get("diam", 16.0))
                )
                self._send_json(res.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 4. Viento NC 285
        if path == "/api/struct/wind":
            try:
                res = calculate_wind_nc285(
                    provincia=str(body.get("provincia", "La Habana")),
                    building_width_m=float(body.get("ancho", 10.0)),
                    building_height_m=float(body.get("alto", 3.0)),
                    terrain_cat=str(body.get("terreno", "B"))
                )
                self._send_json(res.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 5. Sismo NC 46
        if path == "/api/struct/seismic":
            try:
                res = calculate_seismic_nc46(
                    provincia=str(body.get("provincia", "Santiago de Cuba")),
                    building_area_m2=float(body.get("area", 80.0)),
                    building_height_m=float(body.get("alto", 3.0)),
                    num_stories=int(body.get("niveles", 1))
                )
                self._send_json(res.__dict__)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self._send_json({"error": "Ruta no encontrada"}, status=404)


def run_server(port: int = 3000):
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, ArqGenWebHandler)
    print(f"ArqGen V2 Web Studio corriendo en http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Deteniendo servidor...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_server(port)
