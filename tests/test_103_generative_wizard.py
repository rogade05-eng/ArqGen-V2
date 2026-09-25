# -*- coding: utf-8 -*-
"""Pruebas unitarias del Asistente Generativo Multi-Paso y Gestión de Niveles (spec v2)."""

from __future__ import annotations

import os
import tempfile
import unittest

from app.bootstrap import bootstrap
from services.generative_architecture_service import GenerativeArchitectureService


class TestGenerativeWizard(unittest.TestCase):
    """Verifica la generación algorítmica por requerimientos y aislamiento de niveles."""

    def setUp(self) -> None:
        self.app_ctx, _ = bootstrap()
        self.tmp = tempfile.mktemp(suffix=".arqgen")
        self.ctx = self.app_ctx.create_project(self.tmp, "Proyecto Test Generativo")
        self.gen = GenerativeArchitectureService(self.ctx)

    def tearDown(self) -> None:
        self.ctx.close()
        if os.path.exists(self.tmp):
            try:
                os.remove(self.tmp)
            except OSError:
                pass

    def test_01_generate_custom_on_specific_level(self) -> None:
        """Verifica que generate_custom cree el nivel y asigne todos los objetos a él."""
        config = {
            "level_name": "Nivel 1 - Vivienda",
            "elevation_m": 0.0,
            "story_height": 2.80,
            "building_type": "VIVIENDA",
            "rooms": [
                {"name": "Sala", "space_type": "LIVING", "zone_kind": "SOCIAL", "target_area": 16.0},
                {"name": "Cocina", "space_type": "KITCHEN", "zone_kind": "SERVICIO", "target_area": 8.0},
                {"name": "Dormitorio", "space_type": "BEDROOM", "zone_kind": "PRIVADA", "target_area": 12.0},
                {"name": "Baño", "space_type": "BATHROOM", "zone_kind": "SERVICIO", "target_area": 4.5},
            ],
            "relationships": [
                {"from_room": "Sala", "to_room": "Cocina", "connection_type": "DOOR", "element_size": 0.85},
                {"from_room": "Sala", "to_room": "Dormitorio", "connection_type": "DOOR", "element_size": 0.85},
                {"from_room": "Cocina", "to_room": "Baño", "connection_type": "WALL"},
            ],
            "climatic": {"orientation": "SUR", "cross_ventilation": True},
            "structural": {"wall_ext_th": 0.20, "wall_int_th": 0.15},
            "security": {"fire_sadi": True, "intrusion_grade2": True, "cctv": True}
        }
        res = self.gen.generate_custom(config)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["level_name"], "Nivel 1 - Vivienda")
        self.assertEqual(res["summary"]["spaces"], 4)
        self.assertGreater(res["summary"]["walls"], 6)
        self.assertGreater(res["summary"]["doors"], 2)

        pid = self.ctx.project.id
        spaces = self.ctx.architecture.list("SPACE", pid)
        walls = self.ctx.architecture.list("WALL", pid)
        self.assertEqual(len(spaces), 4)
        for s in spaces:
            self.assertEqual(s.level_id, res["level_id"])
        for w in walls:
            self.assertEqual(w.level_id, res["level_id"])

    def test_02_spatial_relationships_connection_types(self) -> None:
        """Verifica que las relaciones espaciales (DOOR, OPENING) se apliquen en los muros compartidos."""
        config = {
            "level_name": "Planta Baja",
            "rooms": [
                {"name": "Sala", "space_type": "LIVING", "zone_kind": "SOCIAL", "target_area": 18.0},
                {"name": "Comedor", "space_type": "DINING", "zone_kind": "SOCIAL", "target_area": 12.0},
                {"name": "Cocina", "space_type": "KITCHEN", "zone_kind": "SERVICIO", "target_area": 8.0},
            ],
            "relationships": [
                {"from_room": "Sala", "to_room": "Comedor", "connection_type": "OPENING", "element_size": 1.60},
                {"from_room": "Comedor", "to_room": "Cocina", "connection_type": "DOOR", "element_size": 0.80},
            ]
        }
        res = self.gen.generate_custom(config)
        applied = res["relationships_applied"]
        self.assertGreater(len(applied), 0)
        types_applied = [r["type"] for r in applied if r.get("status") == "APPLIED"]
        self.assertTrue("OPENING" in types_applied or "DOOR" in types_applied)

    def test_03_multi_level_isolation(self) -> None:
        """Verifica que múltiples niveles mantengan sus entidades aisladas sin interferir."""
        # Nivel 1
        res1 = self.gen.generate_custom({
            "level_name": "Planta Baja",
            "elevation_m": 0.0,
            "rooms": [
                {"name": "Sala", "target_area": 16.0},
                {"name": "Comedor", "target_area": 12.0}
            ]
        })
        # Nivel 2
        res2 = self.gen.generate_custom({
            "level_name": "Planta Alta",
            "elevation_m": 3.0,
            "rooms": [
                {"name": "Dormitorio 1", "target_area": 14.0},
                {"name": "Dormitorio 2", "target_area": 12.0},
                {"name": "Baño", "target_area": 4.5}
            ]
        })

        pid = self.ctx.project.id
        levels = self.ctx.architecture.list("LEVEL", pid)
        self.assertEqual(len(levels), 2)

        lvl1_spaces = [s for s in self.ctx.architecture.list("SPACE", pid) if s.level_id == res1["level_id"]]
        lvl2_spaces = [s for s in self.ctx.architecture.list("SPACE", pid) if s.level_id == res2["level_id"]]

        self.assertEqual(len(lvl1_spaces), 2)
        self.assertEqual(len(lvl2_spaces), 3)

    def test_04_clean_level_regeneration(self) -> None:
        """Verifica que regenerar un nivel con clean_level=True reemplace sus entidades sin afectar otros niveles."""
        self.gen.generate_custom({
            "level_name": "Nivel A",
            "rooms": [{"name": "Local A1", "target_area": 10.0}]
        })
        self.gen.generate_custom({
            "level_name": "Nivel B",
            "rooms": [{"name": "Local B1", "target_area": 12.0}]
        })

        # Regenerar Nivel A con 3 locales
        self.gen.generate_custom({
            "level_name": "Nivel A",
            "clean_level": True,
            "rooms": [
                {"name": "Local A1_nuevo", "target_area": 8.0},
                {"name": "Local A2_nuevo", "target_area": 8.0},
                {"name": "Local A3_nuevo", "target_area": 8.0}
            ]
        })

        pid = self.ctx.project.id
        lvls = {lv.name: lv.id for lv in self.ctx.architecture.list("LEVEL", pid)}
        spaces_a = [s for s in self.ctx.architecture.list("SPACE", pid) if s.level_id == lvls["Nivel A"]]
        spaces_b = [s for s in self.ctx.architecture.list("SPACE", pid) if s.level_id == lvls["Nivel B"]]

        self.assertEqual(len(spaces_a), 3)
        self.assertEqual(len(spaces_b), 1)


if __name__ == "__main__":
    unittest.main()
