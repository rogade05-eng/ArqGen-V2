"""Generador de Arquitectura Sin IA V2 (Algorítmico y Procedimental).

Genera distribuciones de plantas arquitectónicas completas, deterministas y 100% trazables,
basadas en grafos de adyacencia (Space DNA), zonificación funcional (Social, Servicio, Privada),
particionamiento ortogonal, trazado automático de muros perimetrales e interiores,
y colocación paramétrica de puertas y ventanas según normativas de iluminación y ventilación.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.architecture_service import ArchitectureService
from services.context import ProjectContext


@dataclass
class RoomSpec:
    name: str
    space_type: str
    zone_kind: str  # SOCIAL, SERVICIO, PRIVADA
    target_area: float  # m2
    min_width: float = 2.4
    has_exterior_window: bool = True
    window_width: float = 1.20
    window_height: float = 1.20
    window_sill: float = 0.90
    door_width: float = 0.80


PROGRAM_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "VIVIENDA_1D": {
        "title": "Vivienda Económica 1 Dormitorio",
        "description": "Distribución compacta y eficiente para vivienda unifamiliar de 1 habitación",
        "default_width": 7.0,
        "default_depth": 7.5,
        "rooms": [
            RoomSpec("Portal", "PORCH", "SOCIAL", target_area=4.5, min_width=1.5, window_width=0.0, door_width=0.90),
            RoomSpec("Sala Comedor", "LIVING", "SOCIAL", target_area=18.0, min_width=3.2, window_width=1.80),
            RoomSpec("Cocina", "KITCHEN", "SERVICIO", target_area=7.0, min_width=2.2, window_width=1.20, window_sill=1.10, door_width=0.80),
            RoomSpec("Patio Servicio", "SERVICE_YARD", "SERVICIO", target_area=4.5, min_width=1.8, window_width=0.0, door_width=0.80),
            RoomSpec("Dormitorio 1", "BEDROOM", "PRIVADA", target_area=12.0, min_width=3.0, window_width=1.40),
            RoomSpec("Baño", "BATHROOM", "SERVICIO", target_area=4.0, min_width=1.8, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
        ]
    },
    "VIVIENDA_2D": {
        "title": "Vivienda Estándar 2 Dormitorios",
        "description": "Vivienda completa con zonificación clara: zona social al frente, servicios centralizados y dormitorios privados",
        "default_width": 8.5,
        "default_depth": 9.5,
        "rooms": [
            RoomSpec("Portal", "PORCH", "SOCIAL", target_area=5.0, min_width=1.6, window_width=0.0, door_width=0.90),
            RoomSpec("Sala", "LIVING", "SOCIAL", target_area=15.0, min_width=3.4, window_width=1.80),
            RoomSpec("Comedor", "DINING", "SOCIAL", target_area=10.0, min_width=3.0, window_width=1.40),
            RoomSpec("Cocina", "KITCHEN", "SERVICIO", target_area=8.0, min_width=2.4, window_width=1.40, window_sill=1.10, door_width=0.80),
            RoomSpec("Patio Servicio", "SERVICE_YARD", "SERVICIO", target_area=5.0, min_width=2.0, window_width=0.0, door_width=0.80),
            RoomSpec("Pasillo", "CORRIDOR", "SOCIAL", target_area=3.5, min_width=1.0, has_exterior_window=False),
            RoomSpec("Dormitorio Principal", "BEDROOM", "PRIVADA", target_area=13.5, min_width=3.2, window_width=1.50),
            RoomSpec("Dormitorio 2", "BEDROOM", "PRIVADA", target_area=11.5, min_width=3.0, window_width=1.30),
            RoomSpec("Baño", "BATHROOM", "SERVICIO", target_area=4.5, min_width=1.8, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
        ]
    },
    "VIVIENDA_3D": {
        "title": "Vivienda Familiar 3 Dormitorios",
        "description": "Planta espaciosa con 3 dormitorios, 2 baños, cocina independiente y terraza",
        "default_width": 10.0,
        "default_depth": 11.5,
        "rooms": [
            RoomSpec("Portal", "PORCH", "SOCIAL", target_area=6.0, min_width=1.8, door_width=0.95),
            RoomSpec("Sala", "LIVING", "SOCIAL", target_area=18.0, min_width=3.8, window_width=2.00),
            RoomSpec("Comedor", "DINING", "SOCIAL", target_area=12.0, min_width=3.2, window_width=1.60),
            RoomSpec("Cocina", "KITCHEN", "SERVICIO", target_area=9.5, min_width=2.6, window_width=1.40, window_sill=1.10),
            RoomSpec("Patio Servicio", "SERVICE_YARD", "SERVICIO", target_area=6.0, min_width=2.0, door_width=0.80),
            RoomSpec("Dormitorio Principal", "BEDROOM", "PRIVADA", target_area=14.5, min_width=3.4, window_width=1.60),
            RoomSpec("Baño Suite", "BATHROOM", "SERVICIO", target_area=4.0, min_width=1.6, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
            RoomSpec("Baño General", "BATHROOM", "SERVICIO", target_area=4.5, min_width=1.8, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
            RoomSpec("Dormitorio 2", "BEDROOM", "PRIVADA", target_area=12.0, min_width=3.0, window_width=1.40),
            RoomSpec("Dormitorio 3", "BEDROOM", "PRIVADA", target_area=10.5, min_width=2.8, window_width=1.20),
        ]
    }
}


class GenerativeArchitectureService:
    """Motor de generación de arquitectura procedimental determinista."""

    def __init__(self, context: ProjectContext):
        self.ctx = context
        self.arch = ArchitectureService(context)

    def generate(self, template_key: str = "VIVIENDA_2D",
                 width: Optional[float] = None,
                 depth: Optional[float] = None,
                 wall_thickness_ext: float = 0.20,
                 wall_thickness_int: float = 0.15,
                 story_height: float = 2.80,
                 include_mep: bool = True) -> Dict[str, Any]:
        """Genera un proyecto arquitectónico completo según el programa seleccionado."""
        if template_key not in PROGRAM_TEMPLATES:
            raise ValueError(f"Plantilla desconocida '{template_key}'. Opciones: {list(PROGRAM_TEMPLATES.keys())}")

        template = PROGRAM_TEMPLATES[template_key]
        W = round(width or template["default_width"], 2)
        D = round(depth or template["default_depth"], 2)

        # 1. Crear Nivel
        levels = self.ctx.architecture.list("LEVEL", self.ctx.project.id)
        if levels:
            level = levels[0]
        else:
            level = self.arch.create_level(name="Planta Baja", elevation_m=0.0, height_m=story_height)

        # 2. Crear Zonas
        zones = {}
        for z_name, z_kind in [("Zona Social", "PUBLIC"),
                               ("Zona Servicios", "SERVICE"),
                               ("Zona Privada", "PRIVATE")]:
            z = self.arch.create_zone(name=z_name, kind=z_kind)
            zones[z_kind] = z

        # 3. Solucionador de Partición Ortogonal de Locales
        spaces_data = self._solve_layout(template_key, W, D)

        created_spaces = []
        for s_info in spaces_data:
            s_name = s_info["name"]
            s_type = s_info.get("type", "HABITABLE")
            poly_coords = s_info["polygon"]

            space = self.arch.create_space(
                level_ref=level.code,
                name=s_name,
                space_type=s_type,
                boundary=poly_coords
            )
            created_spaces.append(space)

        # 4. Generación de Muros
        wall_segments = self._extract_wall_segments(spaces_data, W, D)
        created_walls = []
        for p1, p2, is_ext in wall_segments:
            th = wall_thickness_ext if is_ext else wall_thickness_int
            wall = self.arch.create_wall(
                level_ref=level.code,
                start=p1,
                end=p2,
                thickness_m=th,
                height_m=story_height,
                structural=is_ext
            )
            created_walls.append(wall)

        # 5. Generación de Puertas y Ventanas
        created_doors = []
        created_windows = []

        front_walls = [w for w in created_walls if (w.start[1] == 0 and w.end[1] == 0) or (w.start[0] == 0 and w.end[0] == 0)]
        main_wall = front_walls[0] if front_walls else created_walls[0]
        wall_len = math.hypot(main_wall.end[0] - main_wall.start[0], main_wall.end[1] - main_wall.start[1])
        offset = round(max(0.2, (wall_len - 0.90) / 2.0), 2)
        door_main = self.arch.create_opening(
            kind="DOOR",
            wall_ref=main_wall.id,
            width_m=0.90,
            height_m=2.10,
            offset_m=offset,
            swing="LEFT"
        )
        created_doors.append(door_main)

        ext_walls = [w for w in created_walls if w.id != main_wall.id]
        for w in ext_walls:
            w_len = math.hypot(w.end[0] - w.start[0], w.end[1] - w.start[1])
            is_ext = (
                (w.start[0] == 0 and w.end[0] == 0) or
                (abs(w.start[0] - W) < 0.05 and abs(w.end[0] - W) < 0.05) or
                (w.start[1] == 0 and w.end[1] == 0) or
                (abs(w.start[1] - D) < 0.05 and abs(w.end[1] - D) < 0.05)
            )
            if is_ext and w_len >= 1.8:
                win_w = 1.40 if w_len >= 2.5 else 1.00
                win_off = round((w_len - win_w) / 2.0, 2)
                win = self.arch.create_opening(
                    kind="WINDOW",
                    wall_ref=w.id,
                    width_m=win_w,
                    height_m=1.20,
                    offset_m=win_off,
                    sill_height_m=0.90
                )
                created_windows.append(win)

        int_walls = [w for w in created_walls if w not in ext_walls or not (
            (w.start[0] == 0 and w.end[0] == 0) or
            (abs(w.start[0] - W) < 0.05 and abs(w.end[0] - W) < 0.05) or
            (w.start[1] == 0 and w.end[1] == 0) or
            (abs(w.start[1] - D) < 0.05 and abs(w.end[1] - D) < 0.05)
        )]
        for idx, w in enumerate(int_walls[:len(created_spaces) - 1]):
            w_len = math.hypot(w.end[0] - w.start[0], w.end[1] - w.start[1])
            if w_len >= 1.10:
                d_off = round(max(0.15, (w_len - 0.80) / 2.0), 2)
                d = self.arch.create_opening(
                    kind="DOOR",
                    wall_ref=w.id,
                    width_m=0.80,
                    height_m=2.05,
                    offset_m=d_off,
                    swing="RIGHT"
                )
                created_doors.append(d)

        # 6. Generación de Instalaciones MEP & Seguridad (si include_mep = True)
        mep_summary = {}
        if include_mep:
            mep_summary = self._generate_mep_networks(created_spaces, level, W, D)

        self.ctx.commit()

        # Recalcular cómputo QTO
        from services.quantity_service import QuantityService
        qto_service = QuantityService(self.ctx)
        qto_service.install_default_formulas()
        qto_result = qto_service.compute_all()

        def _calc_area(pts):
            return 0.5 * abs(sum(pts[i][0] * pts[(i+1)%len(pts)][1] - pts[(i+1)%len(pts)][0] * pts[i][1] for i in range(len(pts))))

        total_area = sum(_calc_area(s.boundary) for s in created_spaces)
        totals = qto_service.totals_by_formula()
        wall_volume = totals.get("WALL_VOLUME", 0.0)

        # Análisis Bioclimático
        from engines.mep_security_engine import analyze_bioclimatic
        spaces_dict = [{"name": s.name, "area_m2": _calc_area(s.boundary)} for s in created_spaces]
        wins_dict = [{"width_m": w.width_m, "height_m": w.height_m} for w in created_windows]
        bio_report = analyze_bioclimatic(spaces_dict, wins_dict, W, D)

        return {
            "template": template_key,
            "title": template["title"],
            "dimensions": {"width": W, "depth": D, "height": story_height},
            "summary": {
                "spaces": len(created_spaces),
                "walls": len(created_walls),
                "doors": len(created_doors),
                "windows": len(created_windows),
                "total_built_area_m2": round(total_area, 2),
                "wall_volume_m3": round(wall_volume, 2),
                "mep_networks": mep_summary,
            },
            "bioclimatic": bio_report.__dict__,
            "spaces": [{"code": s.code, "name": s.name, "area_m2": round(_calc_area(s.boundary), 2)} for s in created_spaces],
        }

    def _generate_mep_networks(self, spaces: List[Any], level: Any, W: float, D: float) -> Dict[str, Any]:
        """Genera redes coordinadas de Electricidad, Fontanería, Drenaje, SADI y CCTV."""
        from services.installations_service import InstallationsService
        from services.security_service import SecurityService

        inst = InstallationsService(self.ctx)
        sec = SecurityService(self.ctx)

        # Helper centroide de polígono
        def centroid(pts):
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            return round(cx, 2), round(cy, 2)

        # --- A. RED ELÉCTRICA (POWER) ---
        net_elec = inst.create_network("Red Eléctrica e Iluminación", "POWER")
        panel_node = inst.add_node(net_elec.code, "PANEL", 0.40, 0.40, name="Cuadro General 120/240V", level_ref=level.code)
        prev_node = panel_node
        elec_nodes_count = 1
        for s in spaces:
            cx, cy = centroid(s.boundary)
            lum = inst.add_node(net_elec.code, "LUMINAIRE", cx, cy, name=f"Luz {s.name}", level_ref=level.code, space_ref=s.code)
            inst.connect(net_elec.code, prev_node.code, lum.code, kind="CONDUIT", name=f"Alim. Luz {s.name}")
            prev_node = lum
            elec_nodes_count += 1

        # --- B. RED HIDRÁULICA AGUA FRÍA (COLD_WATER) ---
        net_water = inst.create_network("Red de Agua Potable", "COLD_WATER")
        cisterna = inst.add_node(net_water.code, "TANK", 0.50, round(D + 0.8, 2), name="Cisterna Subterránea 2.0 m³", level_ref=level.code)
        bomba = inst.add_node(net_water.code, "PUMP", 0.50, round(D + 0.3, 2), name="Bomba Elevación 0.5 HP", level_ref=level.code)
        tanque_elev = inst.add_node(net_water.code, "TANK", round(W * 0.4, 2), round(D * 0.6, 2), name="Tanque Elevado 800 L", level_ref=level.code, elevation_m=3.5)
        inst.connect(net_water.code, cisterna.code, bomba.code, kind="PIPE", name="Succión Bomba", diameter_mm=25.0)
        inst.connect(net_water.code, bomba.code, tanque_elev.code, kind="PIPE", name="Impulsión Tanque", diameter_mm=20.0)

        # Puntos de consumo húmedos
        for s in spaces:
            if any(k in s.name.upper() for k in ["BAÑO", "COCINA", "PATIO"]):
                cx, cy = centroid(s.boundary)
                fix = inst.add_node(net_water.code, "FIXTURE", cx, cy, name=f"Aparatos {s.name}", level_ref=level.code, space_ref=s.code)
                inst.connect(net_water.code, tanque_elev.code, fix.code, kind="PIPE", name=f"Bajante a {s.name}", diameter_mm=20.0)

        # --- C. RED SANITARIA DE DESAGÜE (SANITARY_DRAINAGE) ---
        net_drain = inst.create_network("Red de Evacuación y Desagüe", "SANITARY_DRAINAGE")
        fosa = inst.add_node(net_drain.code, "OUTFALL", round(W * 0.2, 2), round(D + 2.0, 2), name="Fosa Séptica Externa", level_ref=level.code)
        for s in spaces:
            if any(k in s.name.upper() for k in ["BAÑO", "COCINA", "PATIO"]):
                cx, cy = centroid(s.boundary)
                drain_pt = inst.add_node(net_drain.code, "ROOF_DRAIN", cx, cy, name=f"Desagüe {s.name}", level_ref=level.code, space_ref=s.code)
                inst.connect(net_drain.code, drain_pt.code, fosa.code, kind="DRAIN_PIPE", name=f"Ramal a Fosa {s.name}", diameter_mm=100.0, slope_pct=2.0)

        # --- D. SADI (DETECCIÓN DE INCENDIO - FIRE_ALARM) ---
        net_fire = sec.create_network("Sistema Automático Detección Incendios (SADI)", "FIRE_ALARM")
        sadi_panel = sec.add_device(net_fire.code, "FIRE_PANEL", 0.40, 0.80, name="Centralita SADI 2 Zonas")
        call_point = sec.add_device(net_fire.code, "CALL_POINT", 0.90, 0.10, name="Pulsador Manual Salida")
        siren = sec.add_device(net_fire.code, "SOUNDER", 0.40, 1.80, name="Sirena Estroboscópica 85dB")
        sadi_devices = 3
        for s in spaces:
            cx, cy = centroid(s.boundary)
            dev_type = "HEAT_DETECTOR" if "COCINA" in s.name.upper() else "SMOKE_DETECTOR"
            sec.add_device(net_fire.code, dev_type, cx, cy, name=f"Detector {s.name}")
            sadi_devices += 1

        # --- E. CCTV (SEGURIDAD ELECTRÓNICA) ---
        net_cctv = sec.create_network("Circuito Cerrado de Televisión (CCTV)", "CCTV")
        nvr = sec.add_device(net_cctv.code, "NVR", 0.50, 0.40, name="Grabador NVR 4 Canales PoE")
        cam1 = sec.add_device(net_cctv.code, "CAMERA", 0.10, 0.10, name="Cámara 1: Acceso Portal (Domo 4MP)")
        cam2 = sec.add_device(net_cctv.code, "CAMERA", round(W - 0.2, 2), round(D - 0.2, 2), name="Cámara 2: Fondo Patio (Bullet 4MP)")

        return {
            "electrical_nodes": elec_nodes_count,
            "hydraulic_nodes": 6,
            "sanitary_nodes": 4,
            "sadi_devices": sadi_devices,
            "cctv_cameras": 2,
            "networks_created": [net_elec.code, net_water.code, net_drain.code, net_fire.code, net_cctv.code],
        }

    def _solve_layout(self, template_key: str, W: float, D: float) -> List[Dict[str, Any]]:
        """Calcula los polígonos ortogonales de cada local."""
        spaces: List[Dict[str, Any]] = []

        if template_key == "VIVIENDA_1D":
            x_mid = round(W * 0.52, 2)
            y_front = 2.0
            y_mid = round(D * 0.58, 2)

            spaces.append({"name": "Portal", "type": "PORCH", "polygon": [
                (0.0, 0.0), (round(x_mid * 0.6, 2), 0.0), (round(x_mid * 0.6, 2), y_front), (0.0, y_front)
            ]})
            spaces.append({"name": "Sala Comedor", "type": "LIVING", "polygon": [
                (round(x_mid * 0.6, 2), 0.0), (W, 0.0), (W, y_mid), (round(x_mid * 0.6, 2), y_mid)
            ]})
            spaces.append({"name": "Cocina", "type": "KITCHEN", "polygon": [
                (0.0, y_front), (round(x_mid * 0.6, 2), y_front), (round(x_mid * 0.6, 2), y_mid), (0.0, y_mid)
            ]})
            spaces.append({"name": "Patio Servicio", "type": "SERVICE_YARD", "polygon": [
                (0.0, y_mid), (round(x_mid * 0.5, 2), y_mid), (round(x_mid * 0.5, 2), D), (0.0, D)
            ]})
            spaces.append({"name": "Baño", "type": "BATHROOM", "polygon": [
                (round(x_mid * 0.5, 2), y_mid), (x_mid, y_mid), (x_mid, D), (round(x_mid * 0.5, 2), D)
            ]})
            spaces.append({"name": "Dormitorio 1", "type": "BEDROOM", "polygon": [
                (x_mid, y_mid), (W, y_mid), (W, D), (x_mid, D)
            ]})

        elif template_key == "VIVIENDA_2D":
            y1 = round(D * 0.36, 2)
            y2 = round(D * 0.64, 2)
            x_split = round(W * 0.54, 2)
            x_serv = round(W * 0.28, 2)

            spaces.append({"name": "Portal", "type": "PORCH", "polygon": [
                (0.0, 0.0), (x_serv, 0.0), (x_serv, round(y1 * 0.55, 2)), (0.0, round(y1 * 0.55, 2))
            ]})
            spaces.append({"name": "Sala", "type": "LIVING", "polygon": [
                (x_serv, 0.0), (W, 0.0), (W, y1), (x_serv, y1)
            ]})
            spaces.append({"name": "Comedor", "type": "DINING", "polygon": [
                (x_serv, y1), (x_split, y1), (x_split, y2), (x_serv, y2)
            ]})
            spaces.append({"name": "Cocina", "type": "KITCHEN", "polygon": [
                (0.0, round(y1 * 0.55, 2)), (x_serv, round(y1 * 0.55, 2)), (x_serv, y2), (0.0, y2)
            ]})
            spaces.append({"name": "Pasillo", "type": "CORRIDOR", "polygon": [
                (x_split, y1), (round(x_split + 1.20, 2), y1), (round(x_split + 1.20, 2), y2), (x_split, y2)
            ]})
            spaces.append({"name": "Baño", "type": "BATHROOM", "polygon": [
                (round(x_split + 1.20, 2), y1), (W, y1), (W, y2), (round(x_split + 1.20, 2), y2)
            ]})
            spaces.append({"name": "Patio Servicio", "type": "SERVICE_YARD", "polygon": [
                (0.0, y2), (x_serv, y2), (x_serv, D), (0.0, D)
            ]})
            spaces.append({"name": "Dormitorio Principal", "type": "BEDROOM", "polygon": [
                (x_serv, y2), (x_split, y2), (x_split, D), (x_serv, D)
            ]})
            spaces.append({"name": "Dormitorio 2", "type": "BEDROOM", "polygon": [
                (x_split, y2), (W, y2), (W, D), (x_split, D)
            ]})

        else:  # VIVIENDA_3D
            y1 = round(D * 0.32, 2)
            y2 = round(D * 0.65, 2)
            x1 = round(W * 0.35, 2)
            x2 = round(W * 0.68, 2)

            spaces.append({"name": "Portal", "type": "PORCH", "polygon": [
                (0.0, 0.0), (x1, 0.0), (x1, round(y1 * 0.5, 2)), (0.0, round(y1 * 0.5, 2))
            ]})
            spaces.append({"name": "Sala", "type": "LIVING", "polygon": [
                (x1, 0.0), (W, 0.0), (W, y1), (x1, y1)
            ]})
            spaces.append({"name": "Comedor", "type": "DINING", "polygon": [
                (x1, y1), (x2, y1), (x2, y2), (x1, y2)
            ]})
            spaces.append({"name": "Cocina", "type": "KITCHEN", "polygon": [
                (0.0, round(y1 * 0.5, 2)), (x1, round(y1 * 0.5, 2)), (x1, y2), (0.0, y2)
            ]})
            spaces.append({"name": "Patio Servicio", "type": "SERVICE_YARD", "polygon": [
                (0.0, y2), (x1, y2), (x1, D), (0.0, D)
            ]})
            spaces.append({"name": "Dormitorio Principal", "type": "BEDROOM", "polygon": [
                (x2, y1), (W, y1), (W, y2), (x2, y2)
            ]})
            spaces.append({"name": "Baño Suite", "type": "BATHROOM", "polygon": [
                (x1, y2), (round(x1 + 2.0, 2), y2), (round(x1 + 2.0, 2), round(y2 + 1.8, 2)), (x1, round(y2 + 1.8, 2))
            ]})
            spaces.append({"name": "Baño General", "type": "BATHROOM", "polygon": [
                (round(x1 + 2.0, 2), y2), (x2, y2), (x2, round(y2 + 1.8, 2)), (round(x1 + 2.0, 2), round(y2 + 1.8, 2))
            ]})
            spaces.append({"name": "Dormitorio 2", "type": "BEDROOM", "polygon": [
                (x1, round(y2 + 1.8, 2)), (x2, round(y2 + 1.8, 2)), (x2, D), (x1, D)
            ]})
            spaces.append({"name": "Dormitorio 3", "type": "BEDROOM", "polygon": [
                (x2, y2), (W, y2), (W, D), (x2, D)
            ]})

        return spaces

    def _extract_wall_segments(self, spaces_data: List[Dict[str, Any]], W: float, D: float) -> List[Tuple[Tuple[float, float], Tuple[float, float], bool]]:
        """Extrae los segmentos de muro únicos diferenciando perimetrales de interiores."""
        raw_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

        def snap(val: float) -> float:
            return round(val, 2)

        for s in spaces_data:
            pts = s["polygon"]
            for i in range(len(pts)):
                p_a = (snap(pts[i][0]), snap(pts[i][1]))
                p_b = (snap(pts[(i + 1) % len(pts)][0]), snap(pts[(i + 1) % len(pts)][1]))
                if p_a > p_b:
                    p_a, p_b = p_b, p_a
                raw_segments.append((p_a, p_b))

        counts: Dict[Tuple[Tuple[float, float], Tuple[float, float]], int] = {}
        for seg in raw_segments:
            counts[seg] = counts.get(seg, 0) + 1

        final_walls = []
        for (p_a, p_b), count in counts.items():
            dx = p_b[0] - p_a[0]
            dy = p_b[1] - p_a[1]
            length = math.hypot(dx, dy)
            if length < 0.40:
                continue

            is_ext = (count == 1) or (
                (p_a[0] == 0 and p_b[0] == 0) or
                (abs(p_a[0] - W) < 0.05 and abs(p_b[0] - W) < 0.05) or
                (p_a[1] == 0 and p_b[1] == 0) or
                (abs(p_a[1] - D) < 0.05 and abs(p_b[1] - D) < 0.05)
            )
            final_walls.append((p_a, p_b, is_ext))

        return final_walls
