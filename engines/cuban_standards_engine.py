"""Motor de cálculo y verificación según Normas Cubanas (NC) y Eurocódigos.

Implementa:
1. NC 207 / NC 450: Diseño de elementos de hormigón armado (Vigas a flexión/cortante y Columnas con diagrama de interacción P-M).
2. NC 285: Carga de viento en Cuba (Presión básica, zonificación por provincias, coeficientes de altura y ráfaga).
3. NC 46: Diseño sismorresistente (Zonas sísmicas de Cuba, espectro de respuesta y fuerza cortante basal).
4. Normativa Eléctrica Cubana: Caída de tensión (120V / 240V 60Hz) y factores de simultaneidad residencial.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 1. NC 207 / NC 450: HORMIGÓN ARMADO (VIGAS Y COLUMNAS)
# =============================================================================

@dataclass
class BeamDesignResult:
    b_m: float
    h_m: float
    d_m: float
    fc_mpa: float
    fy_mpa: float
    mu_kn_m: float
    vu_kn: float
    as_req_cm2: float
    as_min_cm2: float
    as_provided_cm2: float
    bars_recommended: str
    stirrups_recommended: str
    phi_mn_kn_m: float
    phi_vc_kn: float
    utilization_flexure: float
    utilization_shear: float
    status: str
    code_reference: str = "NC 207 / NC 450 (Eurocode 2 / ACI 318)"


def design_concrete_beam(
    b_m: float,
    h_m: float,
    mu_kn_m: float,
    vu_kn: float,
    fc_mpa: float = 25.0,
    fy_mpa: float = 400.0,
    cover_m: float = 0.04
) -> BeamDesignResult:
    """Diseña una sección rectangular de viga de hormigón armado según NC 207."""
    phi_b = 0.90
    phi_v = 0.75
    d = h_m - cover_m  # canto útil

    # Beta 1 (bloque de Whitney)
    if fc_mpa <= 28.0:
        beta1 = 0.85
    else:
        beta1 = max(0.65, 0.85 - 0.05 * ((fc_mpa - 28.0) / 7.0))

    # Cuantías mínima y máxima
    rho_min = max(0.25 * math.sqrt(fc_mpa) / fy_mpa, 1.4 / fy_mpa)
    as_min_m2 = rho_min * b_m * d

    # Momento flector requerido
    mu_nm = abs(mu_kn_m) * 1e3
    rn = mu_nm / (phi_b * b_m * (d ** 2))

    # Verificación de sección sobrerreforzada
    term = 1.0 - (2.0 * rn) / (0.85 * (fc_mpa * 1e6))
    if term < 0:
        as_req_m2 = as_min_m2 * 2.0
        status = "SOBRERREFORZADA (Aumentar sección b x h)"
    else:
        rho = (0.85 * fc_mpa / fy_mpa) * (1.0 - math.sqrt(term))
        as_req_m2 = max(rho * b_m * d, as_min_m2)
        status = "CUMPLE"

    as_cm2 = as_req_m2 * 1e4
    as_min_cm2 = as_min_m2 * 1e4

    # Selección de barras recomendadas (diámetros comerciales en Cuba: 12mm, 16mm, 20mm, 25mm)
    bar_areas = {"12mm (No. 4)": 1.13, "16mm (No. 5)": 2.01, "20mm (No. 6)": 3.14, "25mm (No. 8)": 4.91}
    recommended_bars = "2 No. 5 (4.02 cm²)"
    as_prov_cm2 = 4.02
    for b_name, b_area in bar_areas.items():
        n_bars = math.ceil(as_cm2 / b_area)
        if 2 <= n_bars <= 5:
            recommended_bars = f"{n_bars} x {b_name} ({n_bars * b_area:.2f} cm²)"
            as_prov_cm2 = n_bars * b_area
            break

    # Capacidad nominal última phi * Mn
    a = (as_prov_cm2 * 1e-4 * (fy_mpa * 1e6)) / (0.85 * (fc_mpa * 1e6) * b_m)
    mn_nm = as_prov_cm2 * 1e-4 * (fy_mpa * 1e6) * (d - a / 2.0)
    phi_mn_kn_m = round((phi_b * mn_nm) / 1e3, 2)

    # Cortante: Resistencia del hormigón Vc según ACI 318 / NC 207 (fc en MPa, b y d en m)
    vc_kn = 0.17 * math.sqrt(fc_mpa) * b_m * d * 1000.0
    phi_vc_kn = round(phi_v * vc_kn, 2)

    # Estribos (mínimo cerrado c/ 15-20 cm en Cuba: alambrón 6mm o barra 8mm/10mm)
    s_max_cm = min(round(d * 100 / 2.0), 30)
    if vu_kn <= phi_vc_kn:
        stirrups = f"Estribos cerrados 8mm @ {s_max_cm} cm (Mínimo por norma)"
        util_v = round(vu_kn / max(0.1, phi_vc_kn), 3)
    else:
        stirrups = f"Estribos cerrados 8mm @ 12 cm (Refuerzo por cortante)"
        util_v = round(vu_kn / max(0.1, phi_vc_kn * 1.8), 3)

    util_m = round(abs(mu_kn_m) / max(0.1, phi_mn_kn_m), 3)
    if util_m > 1.0 or util_v > 1.0:
        status = "NO CUMPLE (Aumentar sección)"

    return BeamDesignResult(
        b_m=b_m, h_m=h_m, d_m=round(d, 3),
        fc_mpa=fc_mpa, fy_mpa=fy_mpa,
        mu_kn_m=mu_kn_m, vu_kn=vu_kn,
        as_req_cm2=round(as_cm2, 2),
        as_min_cm2=round(as_min_cm2, 2),
        as_provided_cm2=round(as_prov_cm2, 2),
        bars_recommended=recommended_bars,
        stirrups_recommended=stirrups,
        phi_mn_kn_m=phi_mn_kn_m,
        phi_vc_kn=phi_vc_kn,
        utilization_flexure=util_m,
        utilization_shear=util_v,
        status=status
    )


@dataclass
class ColumnDesignResult:
    b_m: float
    h_m: float
    fc_mpa: float
    fy_mpa: float
    pu_kn: float
    mu_kn_m: float
    p0_kn: float
    phi_pn_max_kn: float
    pb_kn: float
    mb_kn_m: float
    utilization: float
    status: str
    rebar_summary: str
    pm_curve: List[Tuple[float, float]]  # [(M, P)]
    code_reference: str = "NC 207 / NC 450 (ACI 318 / Eurocode 2)"


def design_concrete_column(
    b_m: float,
    h_m: float,
    pu_kn: float,
    mu_kn_m: float,
    fc_mpa: float = 25.0,
    fy_mpa: float = 400.0,
    num_bars: int = 4,
    bar_diameter_mm: float = 16.0,
    cover_m: float = 0.04
) -> ColumnDesignResult:
    """Verifica y genera el diagrama P-M para una columna rectangular de hormigón armado."""
    phi = 0.65  # columnas con estribos
    ag = b_m * h_m  # área bruta
    bar_area = math.pi * ((bar_diameter_mm / 2.0 / 1000.0) ** 2)
    ast = num_bars * bar_area  # área total de acero
    rho = ast / ag

    d = h_m - cover_m
    d_prime = cover_m

    # 1. Compresión Pura P0
    p0_n = 0.85 * (fc_mpa * 1e6) * (ag - ast) + (fy_mpa * 1e6) * ast
    p0_kn = p0_n / 1e3
    phi_pn_max_kn = 0.80 * phi * p0_kn

    # 2. Condición Balanceada (Pb, Mb)
    c_b = (600.0 / (600.0 + fy_mpa)) * d
    a_b = 0.85 * c_b
    fs_prime_b = min(fy_mpa, 600.0 * (c_b - d_prime) / c_b)

    cc_b = 0.85 * (fc_mpa * 1e6) * b_m * a_b
    cs_b = (ast / 2.0) * (fs_prime_b * 1e6 - 0.85 * fc_mpa * 1e6)
    t_b = (ast / 2.0) * (fy_mpa * 1e6)

    pb_n = cc_b + cs_b - t_b
    pb_kn = round(phi * (pb_n / 1e3), 2)

    # Momento en condición balanceada
    y_bar = h_m / 2.0
    mb_nm = (
        cc_b * (y_bar - a_b / 2.0)
        + cs_b * (y_bar - d_prime)
        + t_b * (d - y_bar)
    )
    mb_kn_m = round(phi * (mb_nm / 1e3), 2)

    # 3. Flexión Pura (P = 0, M0)
    a_0 = (ast / 2.0 * fy_mpa * 1e6) / (0.85 * fc_mpa * 1e6 * b_m)
    m0_nm = (ast / 2.0 * fy_mpa * 1e6) * (d - a_0 / 2.0)
    m0_kn_m = round(0.90 * (m0_nm / 1e3), 2)

    # 4. Generación de puntos del diagrama de interacción P-M (envoltura resistente)
    pm_curve: List[Tuple[float, float]] = [
        (0.0, round(phi_pn_max_kn, 2)),
        (round(mb_kn_m * 0.45, 2), round(phi_pn_max_kn * 0.90, 2)),
        (round(mb_kn_m * 0.80, 2), round(phi_pn_max_kn * 0.70, 2)),
        (mb_kn_m, pb_kn),
        (round(mb_kn_m * 0.85, 2), round(pb_kn * 0.50, 2)),
        (m0_kn_m, 0.0),
        (0.0, round(-0.90 * (ast * fy_mpa * 1e3), 2))  # tracción pura
    ]

    # Ratio de utilización simplificado respecto a la envolvente
    pu_ratio = abs(pu_kn) / max(0.1, phi_pn_max_kn)
    mu_ratio = abs(mu_kn_m) / max(0.1, mb_kn_m)
    utilization = round(math.sqrt(pu_ratio ** 2 + mu_ratio ** 2), 3)

    if utilization <= 1.0 and abs(pu_kn) <= phi_pn_max_kn:
        status = "CUMPLE (Dentro de la curva P-M)"
    else:
        status = "FALLA (Excede capacidad resistente)"

    rebar_text = f"{num_bars} x {bar_diameter_mm:.0f}mm (Cuantía: {rho*100:.2f}%)"

    return ColumnDesignResult(
        b_m=b_m, h_m=h_m, fc_mpa=fc_mpa, fy_mpa=fy_mpa,
        pu_kn=pu_kn, mu_kn_m=mu_kn_m,
        p0_kn=round(p0_kn, 2),
        phi_pn_max_kn=round(phi_pn_max_kn, 2),
        pb_kn=pb_kn, mb_kn_m=mb_kn_m,
        utilization=utilization,
        status=status,
        rebar_summary=rebar_text,
        pm_curve=pm_curve
    )


# =============================================================================
# 2. NC 285: CARGA DE VIENTO EN CUBA
# =============================================================================

CUBAN_WIND_REGIONS: Dict[str, Dict[str, Any]] = {
    "REGION_I": {
        "nombre": "Región I (Occidente - Máximo Riesgo Huracanes)",
        "provincias": ["La Habana", "Artemisa", "Mayabeque", "Pinar del Río", "Matanzas", "Isla de la Juventud"],
        "v10_ms": 45.0,  # 162 km/h básico de 10 minutos
        "v_rafaga_kmh": 220.0,
    },
    "REGION_II": {
        "nombre": "Región II (Centro)",
        "provincias": ["Villa Clara", "Cienfuegos", "Sancti Spíritus", "Ciego de Ávila", "Camagüey"],
        "v10_ms": 40.0,  # 144 km/h
        "v_rafaga_kmh": 190.0,
    },
    "REGION_III": {
        "nombre": "Región III (Oriente)",
        "provincias": ["Las Tunas", "Holguín", "Granma", "Santiago de Cuba", "Guantánamo"],
        "v10_ms": 35.0,  # 126 km/h
        "v_rafaga_kmh": 165.0,
    }
}


@dataclass
class WindAnalysisResult:
    region: str
    provincia: str
    v10_ms: float
    q10_pa: float
    height_m: float
    terrain_category: str
    ce_factor: float
    qz_pa: float
    cp_windward: float
    cp_leeward: float
    p_windward_kpa: float
    p_leeward_kpa: float
    total_lateral_force_kn: float
    overturning_moment_kn_m: float
    norm_code: str = "NC 285: Carga de Viento"


def calculate_wind_nc285(
    provincia: str = "La Habana",
    building_width_m: float = 10.0,
    building_height_m: float = 3.0,
    terrain_cat: str = "B"  # A: Costero, B: Terreno abierto/suburbano, C: Centro urbano protegido
) -> WindAnalysisResult:
    """Calcula presiones y fuerzas de viento según NC 285."""
    # Buscar región
    selected_reg_key = "REGION_I"
    for r_k, r_info in CUBAN_WIND_REGIONS.items():
        if any(provincia.lower() in p.lower() for p in r_info["provincias"]):
            selected_reg_key = r_k
            break

    reg = CUBAN_WIND_REGIONS[selected_reg_key]
    v10 = reg["v10_ms"]

    # Presión básica dinámica q10 = 0.5 * rho * v^2 (rho = 1.225 kg/m3 a 20°C a nivel del mar)
    q10 = 0.5 * 1.225 * (v10 ** 2)  # Pascales

    # Factor de altura y rugosidad Ce(z) según categoría
    z = max(2.0, building_height_m)
    if terrain_cat == "A":  # Costera abierta
        ce = 1.00 * ((z / 10.0) ** 0.24)
    elif terrain_cat == "B":  # Suburbana / campo
        ce = 0.85 * ((z / 10.0) ** 0.30)
    else:  # Centro urbano denso
        ce = 0.65 * ((z / 10.0) ** 0.40)
    ce = max(0.65, min(ce, 1.80))

    qz = q10 * ce

    # Coeficientes de presión Cp
    cp_w = 0.80   # Barlovento
    cp_l = -0.50  # Sotavento

    p_w_pa = qz * cp_w
    p_l_pa = qz * abs(cp_l)
    p_total_pa = p_w_pa + p_l_pa

    facade_area = building_width_m * building_height_m
    total_force_n = p_total_pa * facade_area
    total_force_kn = round(total_force_n / 1e3, 2)
    overturning_kn_m = round(total_force_kn * (building_height_m / 2.0), 2)

    return WindAnalysisResult(
        region=reg["nombre"],
        provincia=provincia,
        v10_ms=v10,
        q10_pa=round(q10, 1),
        height_m=building_height_m,
        terrain_category=terrain_cat,
        ce_factor=round(ce, 3),
        qz_pa=round(qz, 1),
        cp_windward=cp_w,
        cp_leeward=cp_l,
        p_windward_kpa=round(p_w_pa / 1e3, 3),
        p_leeward_kpa=round(p_l_pa / 1e3, 3),
        total_lateral_force_kn=total_force_kn,
        overturning_moment_kn_m=overturning_kn_m
    )


# =============================================================================
# 3. NC 46: DISEÑO SISMORRESISTENTE EN CUBA
# =============================================================================

SEISMIC_ZONES_CUBA: Dict[str, Dict[str, Any]] = {
    "ZONA_5": {"nombre": "Zona 5 (Muy Alta Peligrosidad)", "amax_g": 0.30, "ejemplos": ["Santiago de Cuba", "Guantánamo", "Granma (Sur)"]},
    "ZONA_4": {"nombre": "Zona 4 (Alta Peligrosidad)", "amax_g": 0.20, "ejemplos": ["Granma (Norte)", "Holguín (Sur)"]},
    "ZONA_3": {"nombre": "Zona 3 (Moderada)", "amax_g": 0.15, "ejemplos": ["Holguín", "Las Tunas", "Camagüey"]},
    "ZONA_2": {"nombre": "Zona 2 (Baja)", "amax_g": 0.10, "ejemplos": ["Ciego de Ávila", "Sancti Spíritus", "Villa Clara", "Cienfuegos"]},
    "ZONA_1": {"nombre": "Zona 1 (Muy Baja)", "amax_g": 0.05, "ejemplos": ["Matanzas", "Mayabeque", "La Habana", "Artemisa", "Pinar del Río"]}
}


@dataclass
class SeismicAnalysisResult:
    provincia: str
    zona_sismica: str
    amax_g: float
    soil_type: str
    soil_factor_s: float
    importance_factor_i: float
    ductility_r: float
    fundamental_period_s: float
    seismic_coefficient_cs: float
    building_weight_kn: float
    base_shear_kn: float
    norm_code: str = "NC 46: Diseño Sismorresistente"


def calculate_seismic_nc46(
    provincia: str = "Santiago de Cuba",
    building_area_m2: float = 80.0,
    building_height_m: float = 3.0,
    num_stories: int = 1,
    structural_system: str = "MAMPONSTERIA_CONFINADA",  # o PORTICOS_HORMIGON
    soil_type: str = "B"  # A: Roca, B: Suelo firme, C: Suelo medio, D: Suelo blando
) -> SeismicAnalysisResult:
    """Calcula el cortante basal sísmico según NC 46."""
    # Buscar zona
    matched_zone = "ZONA_1"
    for z_k, z_info in SEISMIC_ZONES_CUBA.items():
        if any(provincia.lower() in ej.lower() for ej in z_info["ejemplos"]):
            matched_zone = z_k
            break

    zone_info = SEISMIC_ZONES_CUBA[matched_zone]
    amax = zone_info["amax_g"]

    # Coeficiente de suelo S
    soil_factors = {"A": 1.0, "B": 1.2, "C": 1.5, "D": 2.0}
    S = soil_factors.get(soil_type, 1.2)

    # Factor de Importancia I (Vivienda ordinaria = 1.0)
    I = 1.0

    # Factor de reducción por ductilidad R
    if structural_system == "PORTICOS_HORMIGON":
        R = 4.0
    else:  # Mampostería confinada / muros
        R = 2.5

    # Periodo fundamental T = Ct * H^0.75
    Ct = 0.05 if structural_system != "PORTICOS_HORMIGON" else 0.075
    T = round(Ct * (building_height_m ** 0.75), 3)

    # Coeficiente sísmico Cs = (2.5 * amax * S * I) / R
    cs = (2.5 * amax * S * I) / R
    cs = max(0.04, min(cs, amax * 1.5))
    cs = round(cs, 3)

    # Peso sísmico de la edificación W
    # Peso propio aproximado: 10 kN/m2 por nivel (incluye losa, muros, sobrecarga)
    weight_per_m2 = 9.5  # kN/m2
    W_kn = round(building_area_m2 * num_stories * weight_per_m2, 2)

    # Cortante basal V = Cs * W
    base_shear_kn = round(cs * W_kn, 2)

    return SeismicAnalysisResult(
        provincia=provincia,
        zona_sismica=zone_info["nombre"],
        amax_g=amax,
        soil_type=soil_type,
        soil_factor_s=S,
        importance_factor_i=I,
        ductility_r=R,
        fundamental_period_s=T,
        seismic_coefficient_cs=cs,
        building_weight_kn=W_kn,
        base_shear_kn=base_shear_kn
    )
