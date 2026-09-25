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
    },
    "OFICINA_ADMIN": {
        "title": "Oficinas Administrativas",
        "description": "Distribución corporativa con recepción, sala de juntas, despachos y servicios",
        "default_width": 9.0,
        "default_depth": 10.0,
        "rooms": [
            RoomSpec("Recepción", "PORCH", "SOCIAL", target_area=12.0, min_width=3.0, door_width=1.00),
            RoomSpec("Sala de Juntas", "LIVING", "SOCIAL", target_area=16.0, min_width=3.5, window_width=1.80),
            RoomSpec("Oficina Operativa", "BEDROOM", "PRIVADA", target_area=20.0, min_width=4.0, window_width=1.80),
            RoomSpec("Despacho Dirección", "BEDROOM", "PRIVADA", target_area=14.0, min_width=3.2, window_width=1.50),
            RoomSpec("Aseo General", "BATHROOM", "SERVICIO", target_area=4.5, min_width=1.8, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
            RoomSpec("Archivo Servidores", "SERVICE_YARD", "SERVICIO", target_area=5.5, min_width=2.0, window_width=0.0, door_width=0.80),
        ]
    },
    "CONSULTORIO_SALUD": {
        "title": "Consultorio Médico / Salud",
        "description": "Distribución clínica con sala de espera, recepción, consultorios y aseos",
        "default_width": 8.5,
        "default_depth": 9.5,
        "rooms": [
            RoomSpec("Sala de Espera", "LIVING", "SOCIAL", target_area=14.0, min_width=3.2, window_width=1.60, door_width=0.95),
            RoomSpec("Recepción Admisión", "PORCH", "SOCIAL", target_area=8.0, min_width=2.4, door_width=0.85),
            RoomSpec("Consultorio Principal", "BEDROOM", "PRIVADA", target_area=16.0, min_width=3.6, window_width=1.50),
            RoomSpec("Área de Examen", "BEDROOM", "PRIVADA", target_area=10.0, min_width=2.8, window_width=1.20),
            RoomSpec("Baño Pacientes", "BATHROOM", "SERVICIO", target_area=4.5, min_width=1.8, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.80),
            RoomSpec("Aseo Personal", "BATHROOM", "SERVICIO", target_area=3.5, min_width=1.6, window_width=0.60, window_height=0.40, window_sill=1.80, door_width=0.70),
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
                 include_mep: bool = True,
                 level_ref: Optional[str] = None,
                 clean_level: bool = False) -> Dict[str, Any]:
        """Genera un proyecto arquitectónico completo según el programa seleccionado."""
        if template_key not in PROGRAM_TEMPLATES:
            raise ValueError(f"Plantilla desconocida '{template_key}'. Opciones: {list(PROGRAM_TEMPLATES.keys())}")

        template = PROGRAM_TEMPLATES[template_key]
        W = round(width or template["default_width"], 2)
        D = round(depth or template["default_depth"], 2)

        # 1. Crear o Resolver Nivel
        if level_ref:
            level = self._resolve_or_create_level(level_ref, height_m=story_height, clean=clean_level)
        else:
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

        # --- F. ALARMA CONTRA INTRUSIÓN Y ROBO (INTRUSION) ---
        net_int = sec.create_network("Alarma Contra Intrusión y Robo", "INTRUSION")
        int_panel = sec.add_device(net_int.code, "INTRUSION_PANEL", 0.40, 0.60, name="Central Intrusión Grado 2")
        keypad = sec.add_device(net_int.code, "KEYPAD", 0.90, 0.30, name="Teclado Numérico LCD Acceso")
        mag_contact = sec.add_device(net_int.code, "MAGNETIC_CONTACT", 0.90, 0.05, name="Contacto Magnético Puerta Principal", attrs={"zone": "ZONA-PERIMETRAL", "external": True})
        siren_int = sec.add_device(net_int.code, "SIREN", 0.40, 2.00, name="Sirena Interior 105 dB", attrs={"zone": "ZONA-SIRENAS"})
        int_devices = 4
        for s in spaces:
            if any(k in s.name.upper() for k in ["SALA", "PASILLO", "COMEDOR"]):
                cx, cy = centroid(s.boundary)
                sec.add_device(net_int.code, "PIR", cx, cy, name=f"Detector PIR {s.name}", attrs={"zone": "ZONA-VOLUMETRICA"})
                int_devices += 1

        return {
            "electrical_nodes": elec_nodes_count,
            "hydraulic_nodes": 6,
            "sanitary_nodes": 4,
            "sadi_devices": sadi_devices,
            "cctv_cameras": 2,
            "intrusion_devices": int_devices,
            "networks_created": [net_elec.code, net_water.code, net_drain.code, net_fire.code, net_cctv.code, net_int.code],
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

    # =========================================================================
    # MOTOR GENERATIVO PERSONALIZADO MULTI-PASO (REQUERIMIENTOS Y ASOCIACIONES)
    # =========================================================================

    def _resolve_or_create_level(self, level_ref: str, elevation_m: float = 0.0,
                                height_m: float = 2.80, clean: bool = False):
        """Busca un nivel existente por nombre/código o lo crea si no existe."""
        pid = self.ctx.project.id
        ref_clean = (level_ref or "Planta Baja").strip()
        level = None
        for cand in self.ctx.architecture.list("LEVEL", pid):
            if (cand.name.strip().lower() == ref_clean.lower() or
                cand.code.strip().lower() == ref_clean.lower() or
                cand.id == ref_clean):
                level = cand
                break
        if level is None:
            level = self.arch.create_level(name=ref_clean, elevation_m=elevation_m, height_m=height_m)
        elif clean:
            self._clean_level(level.id)
        return level

    def _clean_level(self, level_id: str) -> None:
        """Elimina espacios, muros y vanos asociados exclusivamente al nivel especificado."""
        pid = self.ctx.project.id
        # 1. Espacios
        spaces = [s for s in self.ctx.architecture.list("SPACE", pid) if getattr(s, "level_id", "") == level_id]
        for s in spaces:
            try:
                self.arch.delete_entity("SPACE", s.id)
            except Exception:
                pass
        # 2. Muros (elimina vanos en cascada)
        walls = [w for w in self.ctx.architecture.list("WALL", pid) if getattr(w, "level_id", "") == level_id]
        for w in walls:
            try:
                self.arch.delete_entity("WALL", w.id)
            except Exception:
                pass
        # 3. Nodos de instalaciones del nivel
        nodes = [nd for nd in self.ctx.installations.list("NODE", pid) if getattr(nd, "level_id", "") == level_id]
        for nd in nodes:
            try:
                self.ctx.installations_repo.delete("NODE", nd.id)
            except Exception:
                pass

    def _find_shared_segment(self, poly_a: List[Tuple[float, float]],
                             poly_b: List[Tuple[float, float]]) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Encuentra el segmento colineal común de frontera entre dos polígonos ortogonales."""
        def snap(val: float) -> float:
            return round(val, 2)

        for i in range(len(poly_a)):
            p1 = poly_a[i]
            p2 = poly_a[(i + 1) % len(poly_a)]
            for j in range(len(poly_b)):
                q1 = poly_b[j]
                q2 = poly_b[(j + 1) % len(poly_b)]

                # Colineal vertical
                if abs(p1[0] - p2[0]) < 0.02 and abs(q1[0] - q2[0]) < 0.02 and abs(p1[0] - q1[0]) < 0.05:
                    y1_min, y1_max = min(p1[1], p2[1]), max(p1[1], p2[1])
                    y2_min, y2_max = min(q1[1], q2[1]), max(q1[1], q2[1])
                    ov_min = max(y1_min, y2_min)
                    ov_max = min(y1_max, y2_max)
                    if ov_max - ov_min > 0.40:
                        return ((snap(p1[0]), snap(ov_min)), (snap(p1[0]), snap(ov_max)))

                # Colineal horizontal
                if abs(p1[1] - p2[1]) < 0.02 and abs(q1[1] - q2[1]) < 0.02 and abs(p1[1] - q1[1]) < 0.05:
                    x1_min, x1_max = min(p1[0], p2[0]), max(p1[0], p2[0])
                    x2_min, x2_max = min(q1[0], q2[0]), max(q1[0], q2[0])
                    ov_min = max(x1_min, x2_min)
                    ov_max = min(x1_max, x2_max)
                    if ov_max - ov_min > 0.40:
                        return ((snap(ov_min), snap(p1[1])), (snap(ov_max), snap(p1[1])))
        return None

    def _find_wall_for_segment(self, walls: List[Any], seg: Tuple[Tuple[float, float], Tuple[float, float]]) -> Optional[Any]:
        """Localiza el muro que contiene o solapa el segmento dado."""
        sp1, sp2 = seg
        for w in walls:
            # Vertical
            if abs(w.start[0] - w.end[0]) < 0.03 and abs(sp1[0] - sp2[0]) < 0.03 and abs(w.start[0] - sp1[0]) < 0.05:
                w_ymin, w_ymax = min(w.start[1], w.end[1]), max(w.start[1], w.end[1])
                s_ymin, s_ymax = min(sp1[1], sp2[1]), max(sp1[1], sp2[1])
                if s_ymin >= w_ymin - 0.05 and s_ymax <= w_ymax + 0.05:
                    return w
            # Horizontal
            if abs(w.start[1] - w.end[1]) < 0.03 and abs(sp1[1] - sp2[1]) < 0.03 and abs(w.start[1] - sp1[1]) < 0.05:
                w_xmin, w_xmax = min(w.start[0], w.end[0]), max(w.start[0], w.end[0])
                s_xmin, s_xmax = min(sp1[0], sp2[0]), max(sp1[0], sp2[0])
                if s_xmin >= w_xmin - 0.05 and s_xmax <= w_xmax + 0.05:
                    return w
        return None

    def _calc_offset_along_wall(self, wall: Any, seg: Tuple[Tuple[float, float], Tuple[float, float]], opening_width: float) -> float:
        """Calcula el offset paramétrico a lo largo del muro para centrar la abertura."""
        mx = (seg[0][0] + seg[1][0]) / 2.0
        my = (seg[0][1] + seg[1][1]) / 2.0
        dx = mx - wall.start[0]
        dy = my - wall.start[1]
        dist_along = math.hypot(dx, dy)
        wall_len = math.hypot(wall.end[0] - wall.start[0], wall.end[1] - wall.start[1])
        target_offset = dist_along - opening_width / 2.0
        max_offset = max(0.05, wall_len - opening_width - 0.05)
        return round(max(0.05, min(max_offset, target_offset)), 2)

    def _solve_custom_layout(self, rooms: List[Dict[str, Any]], relationships: List[Dict[str, Any]],
                             W: float, D: float) -> List[Dict[str, Any]]:
        """Particionamiento ortogonal recursivo (BSP) determinista para planta libre."""
        def bsp_partition(box: Tuple[float, float, float, float], rlist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            x0, y0, x1, y1 = box
            w = round(x1 - x0, 2)
            d = round(y1 - y0, 2)
            if len(rlist) == 1:
                return [{
                    "name": rlist[0]["name"],
                    "space_type": rlist[0].get("space_type", "HABITABLE"),
                    "zone_kind": rlist[0].get("zone_kind", "SOCIAL"),
                    "has_window": rlist[0].get("has_window", True),
                    "polygon": [
                        (round(x0, 2), round(y0, 2)),
                        (round(x1, 2), round(y0, 2)),
                        (round(x1, 2), round(y1, 2)),
                        (round(x0, 2), round(y1, 2))
                    ]
                }]

            total_area = sum(float(r.get("target_area", 10.0)) for r in rlist)
            split_idx = 1
            best_diff = float("inf")
            for i in range(1, len(rlist)):
                left_area = sum(float(r.get("target_area", 10.0)) for r in rlist[:i])
                right_area = total_area - left_area
                diff = abs(left_area - right_area)
                if diff < best_diff:
                    best_diff = diff
                    split_idx = i

            group1 = rlist[:split_idx]
            group2 = rlist[split_idx:]
            area1 = sum(float(r.get("target_area", 10.0)) for r in group1)
            ratio = area1 / total_area if total_area > 0 else 0.5
            ratio = max(0.18, min(0.82, ratio))

            if w >= d:
                split_x = round(x0 + w * ratio, 2)
                box1 = (x0, y0, split_x, y1)
                box2 = (split_x, y0, x1, y1)
            else:
                split_y = round(y0 + d * ratio, 2)
                box1 = (x0, y0, x1, split_y)
                box2 = (x0, split_y, x1, y1)

            return bsp_partition(box1, group1) + bsp_partition(box2, group2)

        # Ordenar por zonificación funcional: SOCIAL -> SERVICIO -> PRIVADA
        social = [r for r in rooms if r.get("zone_kind") == "SOCIAL"]
        service = [r for r in rooms if r.get("zone_kind") == "SERVICIO"]
        private = [r for r in rooms if r.get("zone_kind") == "PRIVADA"]
        other = [r for r in rooms if r not in social and r not in service and r not in private]

        ordered_rooms = social + service + private + other
        return bsp_partition((0.0, 0.0, W, D), ordered_rooms)

    def generate_custom(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Genera una planta arquitectónica automática completa y determinista según requerimientos."""
        level_name = (config.get("level_name") or "Planta Baja").strip()
        elevation_m = float(config.get("elevation_m", 0.0) or 0.0)
        story_height = float(config.get("story_height", 2.80) or 2.80)
        building_type = str(config.get("building_type", "VIVIENDA")).upper()
        clean_level = bool(config.get("clean_level", True))

        climatic = config.get("climatic", {})
        structural = config.get("structural", {})
        hydraulic = config.get("hydraulic_sanitary", {})
        security = config.get("security", {})
        wall_ext_th = float(structural.get("wall_ext_th", 0.20) or 0.20)
        wall_int_th = float(structural.get("wall_int_th", 0.15) or 0.15)

        # 1. Resolver o Crear Nivel
        level = self._resolve_or_create_level(level_name, elevation_m=elevation_m,
                                              height_m=story_height, clean=clean_level)

        # 2. Asegurar Zonas estándar
        pid = self.ctx.project.id
        zones = {}
        for z_name, z_kind in [("Zona Social", "PUBLIC"),
                               ("Zona Servicios", "SERVICE"),
                               ("Zona Privada", "PRIVATE")]:
            existing = [z for z in self.ctx.architecture.list("ZONE", pid) if z.name == z_name]
            if existing:
                zones[z_kind] = existing[0]
            else:
                zones[z_kind] = self.arch.create_zone(name=z_name, kind=z_kind)

        # 3. Locales y Huella
        raw_rooms = config.get("rooms", [])
        if not raw_rooms:
            # Programa por defecto según tipo de edificación
            template_key = "VIVIENDA_2D"
            if "OFICINA" in building_type:
                template_key = "OFICINA_ADMIN"
            elif "SALUD" in building_type or "CLINICA" in building_type:
                template_key = "CONSULTORIO_SALUD"
            t = PROGRAM_TEMPLATES[template_key]
            raw_rooms = [{"name": r.name, "space_type": r.space_type, "zone_kind": r.zone_kind,
                          "target_area": r.target_area, "has_window": r.has_exterior_window}
                         for r in t["rooms"]]

        total_target_area = sum(float(r.get("target_area", 10.0)) for r in raw_rooms)
        footprint_area = total_target_area * 1.18  # 18% para circulaciones y muros

        W = config.get("width")
        D = config.get("depth")
        if not W or float(W) <= 0:
            W = round(max(6.5, math.sqrt(footprint_area / 1.15)), 1)
        else:
            W = round(float(W), 2)
        if not D or float(D) <= 0:
            D = round(max(7.0, footprint_area / W), 1)
        else:
            D = round(float(D), 2)

        # 4. Solución de distribución ortogonal
        relationships = config.get("relationships", [])
        spaces_data = self._solve_custom_layout(raw_rooms, relationships, W, D)

        # 5. Creación de Locales (Spaces)
        created_spaces = []
        name_to_space = {}
        for s_info in spaces_data:
            s_name = s_info["name"]
            s_type = s_info.get("space_type", "HABITABLE")
            poly_coords = s_info["polygon"]

            sp = self.arch.create_space(
                level_ref=level.code,
                name=s_name,
                space_type=s_type,
                boundary=poly_coords
            )
            # Asignar zona
            z_kind = s_info.get("zone_kind", "SOCIAL")
            if z_kind in ("SOCIAL", "PUBLIC"):
                self.arch.set_space_zone(sp.code, zones["PUBLIC"].id)
            elif z_kind == "SERVICIO":
                self.arch.set_space_zone(sp.code, zones["SERVICE"].id)
            elif z_kind == "PRIVADA":
                self.arch.set_space_zone(sp.code, zones["PRIVATE"].id)

            created_spaces.append(sp)
            name_to_space[s_name.strip().lower()] = sp
            name_to_space[sp.code.strip().lower()] = sp

        # 6. Extracción y Creación de Muros (Walls)
        wall_segments = self._extract_wall_segments(spaces_data, W, D)
        created_walls = []
        for p1, p2, is_ext in wall_segments:
            th = wall_ext_th if is_ext else wall_int_th
            wall = self.arch.create_wall(
                level_ref=level.code,
                start=p1,
                end=p2,
                thickness_m=th,
                height_m=story_height,
                structural=is_ext
            )
            created_walls.append(wall)

        # 7. Puerta de Acceso Principal (en el muro frontal de la zona social)
        created_doors = []
        created_windows = []

        front_walls = [w for w in created_walls if (w.start[1] == 0 and w.end[1] == 0) or (w.start[0] == 0 and w.end[0] == 0)]
        main_wall = front_walls[0] if front_walls else created_walls[0]
        w_len = math.hypot(main_wall.end[0] - main_wall.start[0], main_wall.end[1] - main_wall.start[1])
        offset = round(max(0.15, (w_len - 0.95) / 2.0), 2)
        door_main = self.arch.create_opening(
            kind="DOOR",
            wall_ref=main_wall.id,
            width_m=0.95,
            height_m=2.10,
            offset_m=offset,
            swing="LEFT"
        )
        created_doors.append(door_main)

        # 8. Procesamiento de Relaciones Espaciales entre Locales (Asociaciones)
        relationships_applied = []
        used_walls_for_conn = set()

        # Mapa de polígonos por nombre
        poly_by_name = {s["name"].strip().lower(): s["polygon"] for s in spaces_data}

        for rel in relationships:
            r_from = str(rel.get("from_room", "")).strip().lower()
            r_to = str(rel.get("to_room", "")).strip().lower()
            conn_type = str(rel.get("connection_type", "DOOR")).upper()
            size = float(rel.get("element_size", 0.85) or 0.85)

            poly_a = poly_by_name.get(r_from)
            poly_b = poly_by_name.get(r_to)

            if not poly_a or not poly_b:
                continue

            shared_seg = self._find_shared_segment(poly_a, poly_b)
            if not shared_seg:
                relationships_applied.append({
                    "from": rel.get("from_room"), "to": rel.get("to_room"),
                    "type": conn_type, "status": "NO_SHARED_WALL"
                })
                continue

            target_wall = self._find_wall_for_segment(created_walls, shared_seg)
            if not target_wall or target_wall.id in used_walls_for_conn:
                continue

            seg_len = math.hypot(shared_seg[1][0] - shared_seg[0][0], shared_seg[1][1] - shared_seg[0][1])
            wall_len = math.hypot(target_wall.end[0] - target_wall.start[0], target_wall.end[1] - target_wall.start[1])

            if conn_type in ("DOOR", "PUERTA"):
                door_w = min(size, wall_len - 0.20)
                if door_w >= 0.60:
                    off = self._calc_offset_along_wall(target_wall, shared_seg, door_w)
                    d = self.arch.create_opening(kind="DOOR", wall_ref=target_wall.id,
                                                 width_m=door_w, height_m=2.05, offset_m=off)
                    created_doors.append(d)
                    used_walls_for_conn.add(target_wall.id)
                    relationships_applied.append({
                        "from": rel.get("from_room"), "to": rel.get("to_room"),
                        "type": "DOOR", "width_m": door_w, "status": "APPLIED"
                    })

            elif conn_type in ("OPENING", "VANO", "ARCO"):
                open_w = min(size or 1.60, wall_len - 0.20)
                if open_w >= 0.70:
                    off = self._calc_offset_along_wall(target_wall, shared_seg, open_w)
                    op = self.arch.create_opening(kind="OPENING", wall_ref=target_wall.id,
                                                  width_m=open_w, height_m=2.20, offset_m=off)
                    created_doors.append(op)
                    used_walls_for_conn.add(target_wall.id)
                    relationships_applied.append({
                        "from": rel.get("from_room"), "to": rel.get("to_room"),
                        "type": "OPENING", "width_m": open_w, "status": "APPLIED"
                    })

            elif conn_type in ("WINDOW", "VENTANA"):
                win_w = min(size or 1.20, wall_len - 0.20)
                if win_w >= 0.60:
                    off = self._calc_offset_along_wall(target_wall, shared_seg, win_w)
                    w_int = self.arch.create_opening(kind="WINDOW", wall_ref=target_wall.id,
                                                     width_m=win_w, height_m=1.00, offset_m=off, sill_height_m=1.00)
                    created_windows.append(w_int)
                    used_walls_for_conn.add(target_wall.id)
                    relationships_applied.append({
                        "from": rel.get("from_room"), "to": rel.get("to_room"),
                        "type": "WINDOW", "width_m": win_w, "status": "APPLIED"
                    })

            elif conn_type in ("OPEN_PLAN", "CONCEPTO_ABIERTO"):
                open_w = min(round(seg_len * 0.85, 2), wall_len - 0.20)
                if open_w >= 0.80:
                    off = self._calc_offset_along_wall(target_wall, shared_seg, open_w)
                    op = self.arch.create_opening(kind="OPENING", wall_ref=target_wall.id,
                                                  width_m=open_w, height_m=2.40, offset_m=off)
                    created_doors.append(op)
                    used_walls_for_conn.add(target_wall.id)
                    relationships_applied.append({
                        "from": rel.get("from_room"), "to": rel.get("to_room"),
                        "type": "OPEN_PLAN", "width_m": open_w, "status": "APPLIED"
                    })

            elif conn_type in ("WALL", "MURO"):
                relationships_applied.append({
                    "from": rel.get("from_room"), "to": rel.get("to_room"),
                    "type": "WALL", "status": "SOLID_WALL_KEPT"
                })

        # 9. Conectividad arquitectónica residual (asegurar que cada local tenga acceso)
        ext_wall_ids = set()
        for w in created_walls:
            if ((w.start[0] == 0 and w.end[0] == 0) or
                (abs(w.start[0] - W) < 0.05 and abs(w.end[0] - W) < 0.05) or
                (w.start[1] == 0 and w.end[1] == 0) or
                (abs(w.start[1] - D) < 0.05 and abs(w.end[1] - D) < 0.05)):
                ext_wall_ids.add(w.id)

        int_walls = [w for w in created_walls if w.id not in ext_wall_ids and w.id not in used_walls_for_conn]
        for w in int_walls:
            wall_len = math.hypot(w.end[0] - w.start[0], w.end[1] - w.start[1])
            if wall_len >= 1.20 and len(created_doors) < len(created_spaces) + 2:
                d_off = round(max(0.15, (wall_len - 0.80) / 2.0), 2)
                d = self.arch.create_opening(
                    kind="DOOR",
                    wall_ref=w.id,
                    width_m=0.80,
                    height_m=2.05,
                    offset_m=d_off,
                    swing="RIGHT"
                )
                created_doors.append(d)

        # 10. Ventanas Exteriores y Requerimientos Bioclimáticos
        cross_vent = bool(climatic.get("cross_ventilation", True))
        ext_walls = [w for w in created_walls if w.id in ext_wall_ids and w.id != main_wall.id]

        for w in ext_walls:
            w_len = math.hypot(w.end[0] - w.start[0], w.end[1] - w.start[1])
            if w_len >= 1.80:
                win_w = 1.40 if w_len >= 2.60 else 1.10
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

        # 11. Redes Coordinadas MEP y Seguridad
        mep_summary = self._generate_mep_networks(created_spaces, level, W, D)

        self.ctx.commit()

        # 12. Cómputo métrico QTO y Análisis Bioclimático
        from services.quantity_service import QuantityService
        qto_service = QuantityService(self.ctx)
        qto_service.install_default_formulas()
        qto_service.compute_all()

        def _calc_area(pts):
            return 0.5 * abs(sum(pts[i][0] * pts[(i+1)%len(pts)][1] - pts[(i+1)%len(pts)][0] * pts[i][1] for i in range(len(pts))))

        total_area = sum(_calc_area(s.boundary) for s in created_spaces)
        totals = qto_service.totals_by_formula()
        wall_volume = totals.get("WALL_VOLUME", 0.0)

        from engines.mep_security_engine import analyze_bioclimatic
        spaces_dict = [{"name": s.name, "area_m2": _calc_area(s.boundary)} for s in created_spaces]
        wins_dict = [{"width_m": w.width_m, "height_m": w.height_m} for w in created_windows]
        bio_report = analyze_bioclimatic(spaces_dict, wins_dict, W, D)

        return {
            "status": "success",
            "level_name": level.name or level.code,
            "level_id": level.id,
            "level_code": level.code,
            "building_type": building_type,
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
            "bioclimatic": bio_report.__dict__ if bio_report else {},
            "spaces": [{"code": s.code, "name": s.name, "area_m2": round(_calc_area(s.boundary), 2)} for s in created_spaces],
            "relationships_applied": relationships_applied,
        }

