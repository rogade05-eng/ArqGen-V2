"""Test Suite for MEP, Bioclimatic, and Security Engine & Services (V2.0.0)."""

import unittest
import tempfile
import os
from services.context import ApplicationContext
from engines.mep_security_engine import (
    analyze_bioclimatic,
    calculate_hydraulic_plumbing,
    calculate_electrical_panel,
    calculate_sadi_saci,
    calculate_cctv_system
)
from services.generative_architecture_service import GenerativeArchitectureService


class TestMEPSecurityEngine(unittest.TestCase):
    """Pruebas unitarias de los motores matemáticos y normativos de MEP y Seguridad."""

    def test_bioclimatic_analysis_south_orientation(self):
        spaces = [
            {"name": "Sala", "area_m2": 20.0},
            {"name": "Comedor", "area_m2": 15.0},
            {"name": "Dormitorio 1", "area_m2": 14.0},
            {"name": "Dormitorio 2", "area_m2": 12.0},
            {"name": "Cocina", "area_m2": 9.0},
            {"name": "Baño", "area_m2": 5.0},
        ]
        windows = [
            {"width_m": 1.40, "height_m": 1.20},
            {"width_m": 1.40, "height_m": 1.20},
            {"width_m": 1.20, "height_m": 1.20},
            {"width_m": 1.20, "height_m": 1.20},
            {"width_m": 1.00, "height_m": 1.00},
            {"width_m": 0.60, "height_m": 0.60},
        ]
        rep = analyze_bioclimatic(spaces, windows, building_width_m=8.5, building_depth_m=9.5, orientation="SUR")
        self.assertIn("ÓPTIMA", rep.building_orientation)
        self.assertGreaterEqual(rep.window_to_floor_ratio_pct, 10.0)
        self.assertIn("CUMPLE", rep.compliance_lighting_nc)
        self.assertIn("CUMPLE", rep.compliance_ventilation_nc)
        self.assertGreaterEqual(rep.eaves_depth_recommended_m, 0.50)
        self.assertGreater(len(rep.recommended_passive_strategies), 3)

    def test_bioclimatic_west_orientation(self):
        spaces = [{"name": "Sala", "area_m2": 25.0}]
        windows = [{"width_m": 1.00, "height_m": 1.00}]
        rep = analyze_bioclimatic(spaces, windows, 5.0, 5.0, orientation_degrees="OESTE")
        self.assertIn("DESFAVORABLE", rep.building_orientation)
        self.assertIn("Crítica", rep.solar_exposure)

    def test_hydraulic_plumbing_cuban_standard(self):
        # 5 ocupantes, dotación cubana 200 L/hab/d, 2.5 días reserva
        rep = calculate_hydraulic_plumbing(num_occupants=5, reserve_days=2.5)
        self.assertEqual(rep.num_occupants, 5)
        self.assertEqual(rep.daily_demand_liters, 1000.0)
        self.assertEqual(rep.cistern_volume_m3, 2.50)
        self.assertEqual(rep.elevated_tank_volume_m3, 1.00)
        self.assertGreaterEqual(rep.pump_power_hp, 0.50)
        self.assertGreater(rep.total_fixture_units_hunter, 5.0)
        self.assertIn("DN", rep.main_supply_pipe_dn)
        self.assertIn("4", rep.drainage_main_pipe_dn)
        self.assertGreaterEqual(rep.septic_tank_volume_m3, 3.0)

    def test_electrical_panelboard(self):
        rep = calculate_electrical_panel(has_ac=True, has_water_heater=True)
        self.assertIn("120/240", rep.main_voltage_v)
        self.assertGreater(rep.total_connected_load_w, 5000.0)
        self.assertEqual(rep.demand_factor, 0.70)
        self.assertGreater(rep.max_demand_load_w, 3000.0)
        self.assertGreaterEqual(rep.main_breaker_a, 40)
        self.assertEqual(rep.circuits_count, 5)
        self.assertLessEqual(rep.voltage_drop_max_pct, 3.0)
        self.assertIn("Copperweld", rep.grounding_electrode)

    def test_sadi_saci_fire_protection(self):
        rep = calculate_sadi_saci(building_area_m2=90.0, num_habitable_rooms=5, has_kitchen=True)
        # SADI
        self.assertGreaterEqual(rep.smoke_detectors_count, 2)
        self.assertEqual(rep.thermal_detectors_count, 1)  # Cocina
        self.assertGreaterEqual(rep.manual_call_points, 1)
        self.assertGreaterEqual(rep.alarm_sounders_strobe, 1)
        self.assertGreaterEqual(rep.battery_capacity_ah, 4.0)
        self.assertIn("CUMPLE", rep.sadi_status)
        # SACI
        self.assertGreaterEqual(rep.extinguishers_pqs_6kg, 1)
        self.assertEqual(rep.extinguishers_co2_5kg, 1)
        self.assertLessEqual(rep.max_travel_distance_m, 15.0)
        self.assertIn("CUMPLE", rep.saci_status)

    def test_cctv_system(self):
        rep = calculate_cctv_system(has_portal=True, has_patio=True)
        self.assertEqual(rep.cameras_count, 4)
        self.assertEqual(rep.total_bandwidth_mbps, 16.0)
        self.assertGreater(rep.storage_30days_tb, 4.0)
        self.assertEqual(rep.switch_poe_ports, 8)
        self.assertGreaterEqual(rep.switch_poe_budget_w, 50.0)
        self.assertGreater(rep.cable_utp_cat6_meters, 50.0)

    def test_intrusion_alarm_system(self):
        from engines.mep_security_engine import calculate_intrusion_system
        rep = calculate_intrusion_system(building_area_m2=85.0, num_exterior_doors=2, num_exterior_windows=5)
        self.assertEqual(rep.total_area_m2, 85.0)
        self.assertGreaterEqual(rep.pir_detectors_count, 2)
        self.assertGreaterEqual(rep.magnetic_contacts_count, 7)
        self.assertGreaterEqual(rep.glass_break_detectors_count, 1)
        self.assertEqual(rep.keypads_count, 1)
        self.assertEqual(rep.interior_sirens_count, 1)
        self.assertEqual(rep.exterior_sirens_count, 1)
        self.assertGreaterEqual(rep.battery_capacity_ah, 4.0)
        self.assertIn("Grado 2", rep.security_grade)
        self.assertIn("CUMPLE", rep.compliance_status)
        self.assertGreaterEqual(len(rep.recommended_devices), 5)


class TestGenerativeArchitectureMEP(unittest.TestCase):
    """Pruebas de generación arquitectónica coordinada con redes MEP y Seguridad."""

    def setUp(self):
        self.app = ApplicationContext()
        self.tmp = os.path.join(tempfile.gettempdir(), "test_gen_mep_auto.arqgen")
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        self.ctx = self.app.create_project(self.tmp, name="Proyecto Generado MEP")

    def tearDown(self):
        self.ctx.close()
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_generate_with_mep_networks(self):
        gen = GenerativeArchitectureService(self.ctx)
        result = gen.generate("VIVIENDA_2D", include_mep=True)

        self.assertIn("mep_networks", result["summary"])
        mep_summary = result["summary"]["mep_networks"]
        self.assertGreaterEqual(mep_summary["electrical_nodes"], 8)
        self.assertGreaterEqual(mep_summary["hydraulic_nodes"], 4)
        self.assertGreaterEqual(mep_summary["sadi_devices"], 5)
        self.assertGreaterEqual(mep_summary["cctv_cameras"], 2)

        # Verificar persistencia en repositorios de instalaciones
        networks = self.ctx.installations.list("NETWORK", self.ctx.project.id)
        systems = [n.system for n in networks]
        self.assertIn("POWER", systems)
        self.assertIn("COLD_WATER", systems)
        self.assertIn("SANITARY_DRAINAGE", systems)
        self.assertIn("FIRE_ALARM", systems)
        self.assertIn("CCTV", systems)

        nodes = self.ctx.installations.list("NODE", self.ctx.project.id)
        self.assertGreaterEqual(len(nodes), 25)

        segments = self.ctx.installations.list("SEGMENT", self.ctx.project.id)
        self.assertGreaterEqual(len(segments), 12)

        # Bioclimatic report attached
        self.assertIn("bioclimatic", result)
        bio = result["bioclimatic"]
        self.assertIn("building_orientation", bio)
        self.assertIn("compliance_lighting_nc", bio)

    def test_generate_without_mep_flag(self):
        gen = GenerativeArchitectureService(self.ctx)
        result = gen.generate("VIVIENDA_1D", include_mep=False)
        self.assertEqual(result["summary"]["mep_networks"], {})
        networks = self.ctx.installations.list("NETWORK", self.ctx.project.id)
        self.assertEqual(len(networks), 0)


if __name__ == "__main__":
    unittest.main()
