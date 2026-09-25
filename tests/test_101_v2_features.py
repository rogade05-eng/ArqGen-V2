"""Tests de las funcionalidades V2 de ArqGen:

1. Catálogo Oficial PRECONS III (15,981 renglones, 4,383 recursos y cálculo de APU).
2. Generador de Arquitectura Sin IA V2 (Plantillas 1D, 2D, 3D, trazado determinista).
3. Normas Cubanas de Ingeniería (NC 207 vigas/columnas, NC 285 viento, NC 46 sismo).
"""

from __future__ import annotations

import os
import unittest

from engines.cuban_standards_engine import (
    calculate_seismic_nc46,
    calculate_wind_nc285,
    design_concrete_beam,
    design_concrete_column,
)
from services.context import ApplicationContext
from services.generative_architecture_service import GenerativeArchitectureService
from services.precons_catalog_service import PreconsCatalogService
from tests.base import ARQGenTestCase


class TestArqGenV2Features(ARQGenTestCase):
    """Verificación integral de las nuevas capacidades V2."""

    def test_precons_catalog_service_search_and_apu(self):
        srv = PreconsCatalogService()
        # Búsqueda de renglones
        res = srv.search_renglones("muro bloque", limit=5)
        self.assertGreater(len(res), 0)
        self.assertIn("031152", [r["codigo"] for r in res])

        # Obtener un renglón concreto
        item = srv.get_renglon("030222")
        self.assertIsNotNone(item)
        self.assertEqual(item["codigo"], "030222")
        self.assertEqual(item["unidad"], "m2")
        self.assertGreater(item["total_cup"], 0.0)

        # Cálculo de APU oficial
        apu = srv.calculate_apu("030222", quantity=25.0)
        self.assertEqual(apu["codigo"], "030222")
        self.assertEqual(apu["cantidad"], 25.0)
        self.assertGreater(apu["precio_unitario"], item["total_cup"])
        self.assertAlmostEqual(apu["total_cup"], round(apu["precio_unitario"] * 25.0, 2), places=1)

        # Búsqueda de recursos
        recursos = srv.search_recursos("cemento", limit=5)
        self.assertGreater(len(recursos), 0)

    def test_generative_architecture_v1d_v2d_v3d(self):
        for template in ["VIVIENDA_1D", "VIVIENDA_2D", "VIVIENDA_3D"]:
            proj_path = self.project_path(f"gen_{template}.arqgen")
            ctx = self.application.create_project(proj_path, name=f"Vivienda {template}")
            try:
                gen = GenerativeArchitectureService(ctx)
                res = gen.generate(template)

                self.assertIn("summary", res)
                self.assertGreater(res["summary"]["spaces"], 4)
                self.assertGreater(res["summary"]["walls"], 10)
                self.assertGreater(res["summary"]["doors"], 3)
                self.assertGreater(res["summary"]["windows"], 3)
                self.assertGreater(res["summary"]["total_built_area_m2"], 30.0)
                self.assertGreater(res["summary"]["wall_volume_m3"], 10.0)

                # Verificar persistencia en repositorios
                spaces = ctx.architecture.list("SPACE", ctx.project.id)
                walls = ctx.architecture.list("WALL", ctx.project.id)
                doors = ctx.architecture.list("DOOR", ctx.project.id)
                windows = ctx.architecture.list("WINDOW", ctx.project.id)

                self.assertEqual(len(spaces), res["summary"]["spaces"])
                self.assertEqual(len(walls), res["summary"]["walls"])
                self.assertEqual(len(doors), res["summary"]["doors"])
                self.assertEqual(len(windows), res["summary"]["windows"])
            finally:
                ctx.close()

    def test_cuban_standards_beam_design_nc207(self):
        beam = design_concrete_beam(b_m=0.20, h_m=0.35, mu_kn_m=20.0, vu_kn=15.0)
        self.assertEqual(beam.status, "CUMPLE")
        self.assertGreater(beam.as_req_cm2, 1.0)
        self.assertGreater(beam.phi_mn_kn_m, 20.0)
        self.assertGreater(beam.phi_vc_kn, 15.0)
        self.assertIn("Estribos", beam.stirrups_recommended)

    def test_cuban_standards_column_design_nc207_nc450(self):
        col = design_concrete_column(b_m=0.25, h_m=0.25, pu_kn=250.0, mu_kn_m=12.0)
        self.assertIn("CUMPLE", col.status)
        self.assertLess(col.utilization, 1.0)
        self.assertGreater(len(col.pm_curve), 4)

    def test_cuban_standards_wind_nc285(self):
        wind_hab = calculate_wind_nc285(provincia="La Habana", building_width_m=10.0, building_height_m=3.0)
        self.assertEqual(wind_hab.v10_ms, 45.0)
        self.assertGreater(wind_hab.total_lateral_force_kn, 10.0)

        wind_oriente = calculate_wind_nc285(provincia="Santiago de Cuba", building_width_m=10.0, building_height_m=3.0)
        self.assertEqual(wind_oriente.v10_ms, 35.0)
        self.assertLess(wind_oriente.total_lateral_force_kn, wind_hab.total_lateral_force_kn)

    def test_cuban_standards_seismic_nc46(self):
        seis_santiago = calculate_seismic_nc46(provincia="Santiago de Cuba", building_area_m2=80.0, building_height_m=3.0)
        self.assertEqual(seis_santiago.amax_g, 0.30)
        self.assertGreater(seis_santiago.base_shear_kn, 50.0)

        seis_habana = calculate_seismic_nc46(provincia="La Habana", building_area_m2=80.0, building_height_m=3.0)
        self.assertEqual(seis_habana.amax_g, 0.05)
        self.assertLess(seis_habana.base_shear_kn, seis_santiago.base_shear_kn)


if __name__ == "__main__":
    unittest.main()
