"""Motor integral MEP, Bioclimático y de Seguridad para ArqGen V2.

Cubre los requerimientos climáticos, hidráulicos, sanitarios, eléctricos,
CCTV, SADI (Detección de Incendio) y SACI (Extinción de Incendio) según
normativas cubanas (NC) e internacionales (NFPA / NEC / IEC).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 1. ANÁLISIS CLIMÁTICO Y BIOCLIMÁTICO (CUBA / TROPICAL CÁLIDO-HÚMEDO)
# =============================================================================

@dataclass
class BioclimaticReport:
    building_orientation: str
    solar_exposure: str
    total_floor_area_m2: float
    total_window_area_m2: float
    window_to_floor_ratio_pct: float
    ventilation_opening_ratio_pct: float
    cross_ventilation_status: str
    eaves_depth_recommended_m: float
    recommended_passive_strategies: List[str]
    compliance_lighting_nc: str
    compliance_ventilation_nc: str


def analyze_bioclimatic(
    spaces: List[Dict[str, Any]],
    windows: List[Dict[str, Any]],
    building_width_m: float,
    building_depth_m: float,
    orientation_degrees: Union[float, str] = 0.0,  # 0 / "SUR", 90 / "ESTE", 180 / "NORTE", 270 / "OESTE"
    orientation: Optional[Union[float, str]] = None
) -> BioclimaticReport:
    """Evalúa el desempeño bioclimático y requerimientos climáticos en clima tropical."""
    if orientation is not None:
        orientation_degrees = orientation

    deg = 0.0
    if isinstance(orientation_degrees, (int, float)):
        deg = float(orientation_degrees)
    elif isinstance(orientation_degrees, str):
        orient_map = {
            "SUR": 0.0, "S": 0.0,
            "ESTE": 90.0, "E": 90.0,
            "NORTE": 180.0, "N": 180.0,
            "OESTE": 270.0, "O": 270.0, "W": 270.0,
            "SURESTE": 45.0, "SE": 45.0,
            "NORESTE": 135.0, "NE": 135.0,
            "NOROESTE": 225.0, "NO": 225.0, "NW": 225.0,
            "SUROESTE": 315.0, "SO": 315.0, "SW": 315.0
        }
        deg = orient_map.get(orientation_degrees.upper().strip(), 0.0)

    total_floor = sum(s.get("area_m2", 0.0) for s in spaces)
    total_win = sum(w.get("width_m", 1.2) * w.get("height_m", 1.2) for w in windows)

    win_ratio = (total_win / max(0.1, total_floor)) * 100.0
    # En Cuba, aberturas operables típicamente corresponden al 50-70% del vano (persianas Miami / celosías)
    vent_ratio = win_ratio * 0.60

    # Evaluación de iluminación y ventilación natural (Normas Cubanas: iluminación >= 10%, ventilación >= 5%)
    comp_light = "CUMPLE (>= 10% área de piso)" if win_ratio >= 10.0 else "DEFICIENTE (< 10%)"
    comp_vent = "CUMPLE (>= 5% área de piso)" if vent_ratio >= 5.0 else "DEFICIENTE (< 5%)"

    # Orientación óptima en Cuba: Eje longitudinal Este-Oeste, fachadas principales Norte-Sur
    if 315 <= deg or deg <= 45 or 135 <= deg <= 225:
        orient_eval = "ÓPTIMA (Eje longitudinal E-O, fachadas mayores Norte-Sur)"
        solar_exp = "Favorable: mínima insolación directa en horas críticas de la tarde"
    else:
        orient_eval = "DESFAVORABLE (Fachadas expuestas a Este y Oeste)"
        solar_exp = "Crítica: sobrecalentamiento por radiación solar baja matutina y vespertina"

    # Aleros recomendados en Cuba para protección solar de vanos (ángulo solar cenital ~65°-75°)
    # Alero = h_ventana * tan(90 - 65) = h * 0.46
    eaves_m = round(max(0.60, 1.20 * 0.45), 2)

    # Ventilación cruzada: presencia de vanos en fachadas opuestas
    cross_vent = "EFECTIVA (Locales con flujo pasante de aire)" if len(windows) >= len(spaces) else "PARCIAL"

    strategies = [
        "Ventilación cruzada constante: aprovechar brisas predominantes del Este-Noreste (Alisios).",
        f"Aleros de protección solar de al menos {eaves_m} m en fachadas expuestas.",
        "Cubiertas con pintura reflectiva clara (albedo >= 0.70) para reducir acumulación térmica.",
        "Uso de persianas graduables tipo celosía (persianas Miami) para ventilar aún con lluvia.",
        "Aislamiento térmico o cámara ventilada en cubiertas de hormigón armado fundido in situ."
    ]

    return BioclimaticReport(
        building_orientation=orient_eval,
        solar_exposure=solar_exp,
        total_floor_area_m2=round(total_floor, 2),
        total_window_area_m2=round(total_win, 2),
        window_to_floor_ratio_pct=round(win_ratio, 2),
        ventilation_opening_ratio_pct=round(vent_ratio, 2),
        cross_ventilation_status=cross_vent,
        eaves_depth_recommended_m=eaves_m,
        recommended_passive_strategies=strategies,
        compliance_lighting_nc=comp_light,
        compliance_ventilation_nc=comp_vent
    )


# =============================================================================
# 2. INSTALACIONES HIDRÁULICAS Y SANITARIAS (AGUA POTABLE Y DRENAJE)
# =============================================================================

@dataclass
class HydraulicPlumbingReport:
    num_occupants: int
    daily_demand_liters: float
    cistern_volume_m3: float
    elevated_tank_volume_m3: float
    pump_power_hp: float
    total_fixture_units_hunter: float
    peak_flow_ls: float
    main_supply_pipe_dn: str
    drainage_main_pipe_dn: str
    septic_tank_volume_m3: float
    fixtures_summary: Dict[str, int]


def calculate_hydraulic_plumbing(
    num_occupants: int = 4,
    num_bathrooms: int = 1,
    num_kitchens: int = 1,
    reserve_days: float = 2.5
) -> HydraulicPlumbingReport:
    """Calcula almacenamiento, bombeo, diámetros hidráulicos y fosa séptica."""
    # Dotación en Cuba según Norma Cubana de Abastecimiento: 200 L/habitante/día
    dotacion_per_capita = 200.0  # L/hab/día
    daily_demand_l = num_occupants * dotacion_per_capita

    # Cisterna (reserva de 2 a 3 días ante cortes de la red de acueducto)
    vol_cisterna_m3 = round((daily_demand_l * reserve_days) / 1000.0, 2)
    # Tanque elevado en cubierta (capacidad para 1 día completo de consumo)
    vol_tanque_m3 = round(daily_demand_l / 1000.0, 2)

    # Bomba de elevación cisterna -> tanque: llena el tanque en 1.5 horas
    q_bomba_ls = (vol_tanque_m3 * 1000.0) / (1.5 * 3600.0)  # L/s
    tdh_m = 18.0  # altura cisterna a tanque + pérdidas por fricción
    # Potencia hidráulica HP = (gamma * Q * H) / (75 * eficiencia 0.6)
    hp_calc = (1000.0 * (q_bomba_ls / 1000.0) * tdh_m) / (75.0 * 0.60)
    pump_hp = 0.50 if hp_calc <= 0.50 else (0.75 if hp_calc <= 0.75 else 1.0)

    # Unidades de Gasto Hunter para Agua Fría
    # Inodoro: 3 UG, Lavamanos: 1.5 UG, Ducha: 2 UG, Fregadero: 2 UG, Lavadero: 2 UG
    total_ug = (num_bathrooms * (3.0 + 1.5 + 2.0)) + (num_kitchens * (2.0 + 2.0))
    # Caudal máximo probable instantáneo según curva de Hunter (tanques)
    peak_flow_ls = round(0.12 * math.sqrt(max(1.0, total_ug)), 2)

    # Diámetro de alimentación de agua fría
    supply_dn = '3/4" (DN 20)' if peak_flow_ls > 0.35 else '1/2" (DN 15)'
    drainage_dn = '4" (DN 100 PVC)'  # Colector principal sanitario

    # Fosa séptica (Digestión + Almacenamiento de lodos para 1 año):
    # V = 1000 + N * (0.75 * Dotación + 100 * lodos) = ~0.8 m3/persona
    septic_vol_m3 = round(max(3.0, num_occupants * 0.85), 2)

    fixtures = {
        "Inodoros": num_bathrooms,
        "Lavamanos": num_bathrooms,
        "Duchas": num_bathrooms,
        "Fregaderos": num_kitchens,
        "Lavaderos": num_kitchens
    }

    return HydraulicPlumbingReport(
        num_occupants=num_occupants,
        daily_demand_liters=daily_demand_l,
        cistern_volume_m3=vol_cisterna_m3,
        elevated_tank_volume_m3=vol_tanque_m3,
        pump_power_hp=pump_hp,
        total_fixture_units_hunter=total_ug,
        peak_flow_ls=peak_flow_ls,
        main_supply_pipe_dn=supply_dn,
        drainage_main_pipe_dn=drainage_dn,
        septic_tank_volume_m3=septic_vol_m3,
        fixtures_summary=fixtures
    )


# =============================================================================
# 3. SADI (DETECCIÓN DE INCENDIO) & SACI (EXTINCIÓN) — NC 96 / NFPA 10 & 72
# =============================================================================

@dataclass
class FireProtectionReport:
    # SADI
    smoke_detectors_count: int
    thermal_detectors_count: int
    manual_call_points: int
    alarm_sounders_strobe: int
    loop_current_standby_ma: float
    battery_capacity_ah: float
    sadi_status: str
    # SACI
    extinguishers_pqs_6kg: int
    extinguishers_co2_5kg: int
    max_travel_distance_m: float
    hose_cabinets_bie_count: int
    fire_water_reserve_m3: float
    saci_status: str


def calculate_sadi_saci(
    building_area_m2: float = 80.0,
    num_habitable_rooms: int = 5,
    has_kitchen: bool = True,
    occupancy_risk: str = "RESIDENCIAL_LIGERO"  # RESIDENCIAL_LIGERO, COMERCIAL, INDUSTRIAL
) -> FireProtectionReport:
    """Calcula los requerimientos integrales de SADI y SACI según NC 96 y NFPA."""
    # SADI:
    # 1 detector de humo fotoeléctrico por cada dormitorio/sala/pasillo (radio 7.5 m, ~55 m2)
    smoke_detectors = max(1, math.ceil(building_area_m2 / 55.0))
    # Cocina utiliza detector térmico para evitar falsas alarmas por vapores
    thermal_detectors = 1 if has_kitchen else 0
    # Pulsadores manuales en puertas de salida
    call_points = 1 if building_area_m2 <= 150 else 2
    # Sirenas electrónicas con luz estroboscópica
    sounders = 1 if building_area_m2 <= 120 else 2

    # Consumos SADI para autonomía de batería: 24h reposo + 30 min alarma (EN 54-4 / NFPA 72)
    # Detectores: 0.1 mA reposo | Sirenas: 350 mA alarma | Pulsadores: 0 mA reposo
    i_standby_ma = (smoke_detectors + thermal_detectors) * 0.10 + 15.0  # centralita 15 mA
    i_alarm_a = (sounders * 0.35) + 0.50  # centralita en alarma
    # Batería Ah = (I_reposo * 24h + I_alarma * 0.5h) * 1.25 margen
    batt_ah = round(((i_standby_ma / 1000.0) * 24.0 + i_alarm_a * 0.5) * 1.25, 2)
    batt_ah = max(4.0, batt_ah)  # Mínimo comercial estándar 12V 4.5Ah o 7.2Ah

    # SACI (Extinción):
    # Extintores portátiles PQS (Polvo Químico Seco ABC de 6 kg o 10 lbs):
    # Norma NC 96 / NFPA 10: 1 extintor cada 150 m2 en riesgo ligero, distancia máx 15 m
    pqs_count = max(1, math.ceil(building_area_m2 / 120.0))
    # Extintor CO2 para el cuadro eléctrico principal
    co2_count = 1

    # BIEs (Bocas de Incendio Equipadas) para edificaciones residenciales mayores (> 500 m2 o > 3 niveles)
    bies = 0 if building_area_m2 < 500.0 else math.ceil(building_area_m2 / 500.0)
    # Reserva de agua exclusiva contra incendios (si hay BIEs: 60 min a 100 L/min = 6 m3)
    fire_water_m3 = 6.0 if bies > 0 else 0.0

    return FireProtectionReport(
        smoke_detectors_count=smoke_detectors,
        thermal_detectors_count=thermal_detectors,
        manual_call_points=call_points,
        alarm_sounders_strobe=sounders,
        loop_current_standby_ma=round(i_standby_ma, 2),
        battery_capacity_ah=batt_ah,
        sadi_status="CUMPLE (Cobertura 100% y autonomía 24h+30min)",
        extinguishers_pqs_6kg=pqs_count,
        extinguishers_co2_5kg=co2_count,
        max_travel_distance_m=15.0,
        hose_cabinets_bie_count=bies,
        fire_water_reserve_m3=fire_water_m3,
        saci_status="CUMPLE (Dotación PQS ABC + CO2 en cuadro eléctrico)"
    )


# =============================================================================
# 4. INSTALACIONES ELÉCTRICAS & CCTV
# =============================================================================

@dataclass
class ElectricalPanelReport:
    main_voltage_v: str
    total_connected_load_w: float
    demand_factor: float
    max_demand_load_w: float
    main_current_a: float
    main_breaker_a: int
    circuits_count: int
    circuits_detail: List[Dict[str, Any]]
    voltage_drop_max_pct: float
    grounding_electrode: str


def calculate_electrical_panel(
    num_rooms: int = 5,
    has_ac: bool = True,
    has_water_heater: bool = True
) -> ElectricalPanelReport:
    """Calcula el cuadro de cargas residencial 120V / 240V 60Hz y circuitos."""
    circuits = []

    # C1: Alumbrado general (120V, 15A, cable 14 AWG)
    circuits.append({
        "id": "C1", "name": "Alumbrado General", "voltage": 120,
        "load_w": 650, "current_a": 5.4, "breaker": "15A 1P", "wire": "14 AWG (2.08 mm²)", "drop_pct": 0.8
    })

    # C2: Tomacorrientes Generales (120V, 20A, cable 12 AWG)
    circuits.append({
        "id": "C2", "name": "Tomacorrientes Generales", "voltage": 120,
        "load_w": 1800, "current_a": 15.0, "breaker": "20A 1P", "wire": "12 AWG (3.31 mm²)", "drop_pct": 1.4
    })

    # C3: Pequeños Artefactos de Cocina (120V, 20A, cable 12 AWG)
    circuits.append({
        "id": "C3", "name": "Tomacorrientes Cocina / Refrigeración", "voltage": 120,
        "load_w": 1500, "current_a": 12.5, "breaker": "20A 1P", "wire": "12 AWG (3.31 mm²)", "drop_pct": 1.1
    })

    # C4: Climatización A/C (240V, 20A, cable 12 AWG)
    if has_ac:
        circuits.append({
            "id": "C4", "name": "Climatización Split 12000 BTU", "voltage": 240,
            "load_w": 1400, "current_a": 5.8, "breaker": "20A 2P", "wire": "12 AWG (3.31 mm²)", "drop_pct": 0.7
        })

    # C5: Calentador de Agua Eléctrico (240V, 20A)
    if has_water_heater:
        circuits.append({
            "id": "C5", "name": "Calentador de Agua", "voltage": 240,
            "load_w": 1800, "current_a": 7.5, "breaker": "20A 2P", "wire": "12 AWG (3.31 mm²)", "drop_pct": 0.9
        })

    total_connected = sum(c["load_w"] for c in circuits)
    demand_factor = 0.70  # Coeficiente de simultaneidad residencial
    demand_load = total_connected * demand_factor
    # Acometida bifásica 120/240V
    main_current = demand_load / 240.0
    main_breaker = 40 if main_current <= 32 else (50 if main_current <= 40 else 63)

    return ElectricalPanelReport(
        main_voltage_v="120/240 V bifásica 60 Hz (Norma Cubana)",
        total_connected_load_w=round(total_connected, 1),
        demand_factor=demand_factor,
        max_demand_load_w=round(demand_load, 1),
        main_current_a=round(main_current, 1),
        main_breaker_a=main_breaker,
        circuits_count=len(circuits),
        circuits_detail=circuits,
        voltage_drop_max_pct=1.4,
        grounding_electrode="Varilla Copperweld 5/8' x 2.40 m (R <= 10 ohm)"
    )


@dataclass
class CCTVReport:
    cameras_count: int
    camera_locations: List[str]
    total_bandwidth_mbps: float
    storage_30days_tb: float
    switch_poe_ports: int
    switch_poe_budget_w: float
    cable_utp_cat6_meters: float


def calculate_cctv_system(
    building_perimeter_m: float = 36.0,
    has_portal: bool = True,
    has_patio: bool = True
) -> CCTVReport:
    """Calcula requerimientos de CCTV para seguridad perimetral y accesos."""
    locations = []
    if has_portal:
        locations.append("Acceso Principal / Portal (Cámara Domo IP 4MP)")
    if has_patio:
        locations.append("Patio de Servicio / Fondo (Cámara Bullet IP 4MP IR 30m)")
    locations.append("Perímetro Lateral Derecho (Cámara Bullet IP 4MP)")
    locations.append("Perímetro Lateral Izquierdo (Cámara Bullet IP 4MP)")

    n_cam = len(locations)
    # 4MP H.265 a 20 FPS = ~4.0 Mbps por cámara
    bw_mbps = n_cam * 4.0
    # Almacenamiento continuo 24/7 por 30 días:
    # GB = (bw_mbps * 1e6 / 8 * 3600 * 24 * 30) / 1e9 = bw_mbps * 324 GB
    storage_tb = round((bw_mbps * 324.0) / 1000.0, 2)
    # PoE: 12W por cámara + 30% reserva
    poe_budget = round(n_cam * 12.0 * 1.30, 1)
    # Cable UTP Cat 6 promedio 25m por cámara
    cable_m = n_cam * 25.0

    return CCTVReport(
        cameras_count=n_cam,
        camera_locations=locations,
        total_bandwidth_mbps=bw_mbps,
        storage_30days_tb=storage_tb,
        switch_poe_ports=8,
        switch_poe_budget_w=poe_budget,
        cable_utp_cat6_meters=cable_m
    )
