"""Selftest: end-to-end verification used after packaging (build pipeline).

Runs the complete chain in a temporary directory: project → geometry →
QTO → budget → exports → round-trip. Exits non-zero on any failure so
the compile .bat can stop the pipeline.
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from typing import List, Tuple

from app.lifecycle import setup_logging, get_logger


def run_selftest(console: bool = True) -> Tuple[bool, List[str]]:
    checks: List[str] = []
    ok = True
    logger = get_logger("arqgen.selftest")
    tmp = tempfile.mkdtemp(prefix="arqgen_selftest_")
    try:
        from services.context import ApplicationContext

        application = ApplicationContext()
        setup_logging(os.path.join(tmp, "logs"), level="ERROR", console=False)

        # 1) Demo end-to-end
        from app.demo import build_demo
        db_path = os.path.join(tmp, "selftest.arqgen")
        context = build_demo(application, db_path)
        checks.append("demo: OK")
        context.close()

        # 2) Reopen and verify persistence
        context = application.open_project(db_path)
        walls = context.architecture.list("WALL", context.project.id)
        assert len(walls) == 7, f"esperados 7 muros, hay {len(walls)}"
        checks.append(f"persistencia: OK ({len(walls)} muros)")

        # 3) QTO totals present
        totals = {}
        for row in context.quantities_repo.all(context.project.id):
            totals[row["formula_code"]] = totals.get(row["formula_code"], 0.0) + row["final_quantity"]
        assert totals.get("WALL_LENGTH", 0) > 0, "WALL_LENGTH ausente"
        assert totals.get("WALL_VOLUME", 0) > 0, "WALL_VOLUME ausente"
        checks.append(f"QTO: OK (WALL_VOLUME={totals.get('WALL_VOLUME', 0):.2f} m3)")

        # 4) Budget present and positive
        budget = context.budget_repo.latest_budget(context.project.id)
        assert budget and budget["total_cost"] > 0, "presupuesto ausente"
        checks.append(f"presupuesto: OK (total={budget['total_cost']:.2f} {budget['currency']})")

        # 5) Exports
        from services.export_service import ExportService
        export_service = ExportService()
        out_dir = os.path.join(tmp, "out")
        dxf_path = export_service.export(context, "DXF", os.path.join(out_dir, "selftest.dxf"))
        json_path = export_service.export(context, "JSON", os.path.join(out_dir, "selftest.json"))
        xlsx_path = export_service.export(context, "XLSX", os.path.join(out_dir, "selftest.xlsx"))
        csv_path = export_service.export(context, "CSV", os.path.join(out_dir, "selftest.csv"),
                                         options={"table": "budget"})
        for path in (dxf_path, json_path, xlsx_path, csv_path):
            assert os.path.exists(path) and os.path.getsize(path) > 0, f"export vacío: {path}"
        checks.append("exportación: OK (DXF/JSON/XLSX/CSV)")

        # 6) DXF readable (walls live in per-level layouts)
        import ezdxf
        doc = ezdxf.readfile(dxf_path)
        wall_entities = []
        for layout in doc.layouts.names():
            wall_entities.extend(
                e for e in doc.layouts.get(layout) if e.dxf.layer == "ARQ-WALL")
        assert len(wall_entities) >= 7, f"DXF sin muros suficientes: {len(wall_entities)}"
        checks.append(f"DXF legible: OK ({len(wall_entities)} entidades ARQ-WALL)")

        # 7) JSON round-trip
        from services.import_service import ImportService
        importer = ImportService(application)
        result = importer.import_snapshot(
            json_path, os.path.join(tmp, "roundtrip.arqgen"), approve=True)
        assert result["approved"] and result["inserted"]["WALL"] == 7
        checks.append("round-trip JSON: OK")

        # 8) Validation runs
        from services.analysis_service import ValidationService
        validation = ValidationService(context).validate_project()
        checks.append(f"validación: OK (estado={validation.status.value})")

        # 9) Installations networks persisted and valid (spec 24-26, 30-32)
        networks = context.installations.list("NETWORK", context.project.id)
        assert len(networks) == 12, f"esperadas 12 redes, hay {len(networks)}"
        total_nodes = sum(len(context.installations.nodes_of(n.id)) for n in networks)
        total_segments = sum(len(context.installations.segments_of(n.id)) for n in networks)
        assert total_nodes >= 75, f"nodos de instalaciones insuficientes: {total_nodes}"
        assert total_segments >= 60, f"tramos de instalaciones insuficientes: {total_segments}"
        from services.installations_service import InstallationsService
        installations_service = InstallationsService(context)
        for network in networks:
            report = installations_service.validate_network(network.code)
            assert report["status"] in ("VALID", "VALID_WITH_WARNINGS"), \
                f"red {network.code} inválida: {report['status']}"
        checks.append(f"instalaciones: OK ({len(networks)} redes, {total_nodes} nodos, "
                      f"{total_segments} tramos)")

        # 10) Electrical summary deterministic (spec 27)
        panel = [n for n in context.installations.nodes_of(networks[0].id)
                 if n.kind == "PANEL"][0]
        summary = installations_service.panel_summary(panel.code)
        assert abs(summary["total_connected_w"] - 7180.0) < 0.5, \
            f"potencia conectada inesperada: {summary['total_connected_w']}"
        checks.append(f"eléctrico: OK (7180 W en 3 circuitos, "
                      f"principal {summary['main_breaker_a']:.0f} A)")

        # 11) QTO includes installation quantities (spec 24, 51)
        install_totals = {}
        for row in context.quantities_repo.all(context.project.id):
            install_totals[row["formula_code"]] = install_totals.get(row["formula_code"], 0.0)
            install_totals[row["formula_code"]] += row["final_quantity"]
        assert install_totals.get("CONDUIT_LENGTH", 0) > 0, "CONDUIT_LENGTH ausente"
        assert install_totals.get("CONDUCTOR_LENGTH", 0) > 0, "CONDUCTOR_LENGTH ausente"
        assert install_totals.get("PIPE_LENGTH", 0) > 0, "PIPE_LENGTH ausente"
        assert install_totals.get("COOLING_UNITS", 0) >= 4, "COOLING_UNITS ausente"
        checks.append(f"QTO instalaciones: OK (CONDUIT_LENGTH="
                      f"{install_totals.get('CONDUIT_LENGTH', 0):.1f} m, "
                      f"COOLING_UNITS={install_totals.get('COOLING_UNITS', 0):.0f})")

        # 12) Stormwater sizing deterministic (spec 30)
        storm = [n for n in networks if n.system == "STORMWATER"][0]
        storm_report = installations_service.size_stormwater(storm.code)
        assert len(storm_report["rows"]) >= 4, "dimensionado pluvial incompleto"
        # 45+35 m2, C=0.90, i=100 mm/h -> Q = 0.9*100*80/3600 = 2.0 L/s
        assert abs(storm_report["captured_ls"] - 2.0) < 0.01, \
            f"captación esperada 2.0 L/s, hay {storm_report['captured_ls']}"
        assert storm_report["detention"]["volume_l"] > 0, "detención pluvial ausente"
        checks.append(f"pluvial: OK (captación={storm_report['captured_ls']:.2f} L/s, "
                      f"detención={storm_report['detention']['volume_l']:.0f} L)")

        # 13) Gas sizing + validation (spec 31)
        gas = [n for n in networks if n.system == "GAS"][0]
        gas_report = installations_service.size_gas(gas.code)
        assert len(gas_report["rows"]) == 6, "dimensionado de gas incompleto"
        assert gas_report["appliances"] == 2, "aparatos de gas inesperados"
        gas_validation = installations_service.validate_gas(gas.code)
        assert gas_validation["status"] in ("VALID", "VALID_WITH_WARNINGS"), \
            f"validación de gas: {gas_validation['status']}"
        checks.append(f"gas: OK (tramos={len(gas_report['rows'])}, "
                      f"estado={gas_validation['status']})")

        # 14) Telecom sizing (spec 32)
        telecom = [n for n in networks if n.system == "TELECOM"][0]
        telecom_report = installations_service.size_telecom(telecom.code)
        assert len(telecom_report["rows"]) == 6, "dimensionado telecom incompleto"
        assert telecom_report["racks"] and telecom_report["panels"], "resumen rack/panel ausente"
        for row in telecom_report["rows"]:
            if "fill_pct" in row:  # CONDUIT rows
                assert row["fill_pct"] <= 40.0 + 1e-9, "llenado de conducto telecom > 40 %"
        checks.append(f"telecom: OK (tramos={len(telecom_report['rows'])}, "
                      f"racks={len(telecom_report['racks'])})")

        # 15) Structure analyzed (spec 33-34)
        from services.structure_service import StructureService
        elements = context.structure.list("ELEMENT", context.project.id)
        assert len(elements) == 4, f"esperados 4 elementos estructurales, hay {len(elements)}"
        analyzed = [e for e in elements if e.num("utilization") > 0
                    or e.num("truss_max_kn") > 0]
        assert len(analyzed) == 4, "elementos estructurales sin analizar"
        assert any(e.num("utilization") <= 1.0 for e in analyzed), \
            "elemento agotado en la demo"
        structure_service = StructureService(context)
        steel = structure_service.steel_quantities()
        assert steel["steel_weight_kg"] > 0, "peso de acero ausente"
        checks.append(f"estructura: OK (4 elementos, acero "
                      f"{steel['steel_weight_kg']:.0f} kg)")

        # 16) Security systems (spec 37-49)
        from services.security_service import SecurityService
        sec_service = SecurityService(context)
        cctv_network = [n for n in networks if n.system == "CCTV"][0]
        coverage = sec_service.cctv_coverage(cctv_network.code)
        assert coverage["cameras"] >= 2, "cámaras CCTV ausentes"
        fire_network = [n for n in networks if n.system == "FIRE_ALARM"][0]
        fire_status = sec_service.fire_check(fire_network.code)["status"]
        assert fire_status in ("VALID", "VALID_WITH_WARNINGS"), \
            f"detección de incendios: {fire_status}"
        intrusion_network = [n for n in networks if n.system == "INTRUSION"][0]
        intrusion_status = sec_service.intrusion_check(intrusion_network.code)["status"]
        assert intrusion_status in ("VALID", "VALID_WITH_WARNINGS"), \
            f"intrusión: {intrusion_status}"
        access_network = [n for n in networks if n.system == "ACCESS_CONTROL"][0]
        access_status = sec_service.access_check(access_network.code)["status"]
        assert access_status in ("VALID", "VALID_WITH_WARNINGS"), \
            f"control de acceso: {access_status}"
        perimeter_network = [n for n in networks if n.system == "PERIMETER"][0]
        assert sec_service.perimeter_check(perimeter_network.code)["report"]["ok"], \
            "perímetro con huecos"
        checks.append(f"seguridad: OK (CCTV {coverage['cameras']} cámaras, fuego "
                      f"{fire_status}, intrusión {intrusion_status}, acceso "
                      f"{access_status}, perímetro OK)")

        # 17) Coordination: demo coordinada sin choques duros (spec 35-36)
        from services.coordination_service import CoordinationService
        clash_service = CoordinationService(context)
        clash_report = clash_service.run_detection()
        assert clash_report["by_type"].get("HARD", 0) == 0, \
            f"demo con choques duros: {clash_report['by_type']}"
        checks.append(f"coordinación: OK (sin HARD, abiertas "
                      f"{clash_report['open']})")

        # 18) PRECONS project analysis (spec 59-60)
        from services.precons_service import PreconsService
        precons = PreconsService(context)
        precons.load_ruleset("precons_cuba_v1")
        precons_report = precons.analyze_project()
        assert precons_report["total"] > 0, "análisis PRECONS vacío"
        assert len(precons_report["analyses"]) >= 3, "análisis PRECONS incompleto"
        checks.append(f"PRECONS: OK (total={precons_report['total']:.2f} "
                      f"{precons_report['currency']})")

        # 19) IFC export (spec 63, 67)
        ifc_path = export_service.export(
            context, "IFC", os.path.join(out_dir, "selftest.ifc"))
        assert os.path.exists(ifc_path) and os.path.getsize(ifc_path) > 1000, \
            "export IFC vacío"
        with open(ifc_path, "r", encoding="utf-8") as handle:
            ifc_text = handle.read()
        assert ifc_text.startswith("ISO-10303-21;"), "IFC sin cabecera SPF"
        assert "FILE_SCHEMA(('IFC4'))" in ifc_text, "IFC sin esquema IFC4"
        assert ifc_text.count("IFCWALL(") == 7, "IFC sin muros completos"
        assert ifc_text.count("IFCDOOR(") == 4 and \
            ifc_text.count("IFCWINDOW(") == 3, "IFC sin vanos completos"
        checks.append(f"IFC: OK ({ifc_text.count('= IFC')} entidades, "
                      f"7 muros, 4 puertas, 3 ventanas)")

        # 20) Documentación (FASE 34, spec 68-70): memoria determinista
        from services.documentation_service import DocumentationService
        docs = DocumentationService(context)
        memoria = docs.generate_memoria()
        assert "Proyecto Demo Residencial" in memoria, "memoria sin proyecto"
        assert memoria == docs.generate_memoria(), "memoria no determinista"
        template = docs.create_template("selftest", "Cliente {{CLIENT.NAME}}.")
        rendered = docs.render_template(template.code)
        assert "Cliente Demo" in rendered, "plantilla sin resolver"
        variables = docs.variables()
        assert variables["QTO.DOOR_COUNT"] == 4 and \
            variables["QTO.WINDOW_COUNT"] == 3, "variables de vanos incorrectas"
        context.commit()
        checks.append("documentación: OK (memoria determinista, plantilla, "
                      "4 puertas + 3 ventanas)")

        # 21) Optimización multiobjetivo (FASE 35, spec 19): 12 objetivos
        from engines.optimization_engine import OBJECTIVES, Variant
        from services.optimization_service import OptimizationService
        current = OptimizationService(context).evaluate_current()
        assert set(current.objectives) == set(OBJECTIVES), \
            "objetivos del spec 19 incompletos"
        assert abs(current.objectives["AREA"] - 80.0) < 0.01, \
            f"AREA esperado 80, hay {current.objectives['AREA']}"
        worse = Variant(name="PEOR", objectives={
            **current.objectives, "COST": current.objectives["COST"] + 1})
        front = OptimizationService(context).pareto([current, worse])
        assert front["pareto_front"] == ["CURRENT"], "frente de Pareto erróneo"
        checks.append(f"optimización: OK (12 objetivos, AREA="
                      f"{current.objectives['AREA']:.1f} m2, Pareto OK)")

        # 22) Backup y recuperación (FASE 38, spec 81)
        from persistence.backup.service import BackupService
        backup_service = BackupService(os.path.join(tmp, "backups"))
        backup_service.create_full_backup(db_path, label="selftest")
        incremental = backup_service.create_incremental_backup(db_path)
        assert incremental["changed"], "incremental no detecta cambios"
        assert backup_service.recover(db_path)["recovered"] is False, \
            "recuperación innecesaria"
        verified = backup_service.verify_all()
        assert verified and all(v["integrity"] == "ok" for v in verified), \
            "backups con integridad comprometida"
        checks.append(f"backup: OK ({len(verified)} copias íntegras, "
                      "incremental y journal OK)")

        # 23) Benchmark y cachés (FASE 40, spec 86-87)
        from app.benchmark import cache_inventory, run_benchmarks
        caches = {c["cache"] for c in cache_inventory()}
        assert {"geometry_cache", "rules_cache", "catalog_cache",
                "calculation_cache", "routing_cache",
                "coverage_cache"} <= caches, "cachés del spec 87 incompletas"
        bench = run_benchmarks(context, iterations={
            "geometry_area": 2, "spatial_adjacency": 1, "qto_compute_all": 1,
            "budget_compute": 1, "optimization_current": 1,
            "documentation_memoria": 1, "clash_detection": 1, "export_json": 1})
        assert len(bench) == 8, "operaciones de benchmark incompletas"
        checks.append("benchmark: OK (8 operaciones medidas, 6 cachés)")

        # 24) Registro de plugins (FASE 15/§31, §88-89): GAS como plugin
        #     de instalaciones y lista §88 completa cargada sin errores.
        from plugins.plugin_api import PluginLoader
        loader = PluginLoader(application)
        loader.load_all()
        broken = [e for e in loader.loaded if e.error or e.plugin is None]
        assert not broken, f"plugins con error de carga: {broken}"
        registry = {e.plugin.plugin_id: e.plugin for e in loader.loaded}
        assert {"architecture", "structure", "installations", "cctv",
                "fire", "intrusion", "access", "perimeter", "qto",
                "budget", "bim", "documentation",
                "gas"} <= set(registry), "lista §88 incompleta"
        assert "installations" in registry["gas"].dependencies, \
            "gas debe declarar dependencia de installations (§31)"
        checks.append(f"plugins: OK ({len(registry)} cargados, §88 + gas§31)")

        # 25) GUI (FASE 90, spec 90-93): smoke de la ventana si hay
        #     display; en entornos headless se omite sin fallar.
        try:
            import tkinter as _tk
            _probe = _tk.Tk()
            _probe.withdraw()
            _probe.destroy()
            has_display = True
        except Exception:  # noqa: BLE001
            has_display = False
        if has_display:
            from ui.app_window import ARQGenWindow
            gui_window = ARQGenWindow(context, application)
            gui_window.update()
            assert len(gui_window.tree.get_children()) == 13, \
                "la GUI debe mostrar las 13 disciplinas del spec 91"
            gui_window.search_entry.insert(0, "ARQ")
            gui_window.run_search()
            assert gui_window._result_rows, "búsqueda GUI sin resultados"
            gui_window.fit_view()
            gui_window.update()
            gui_window.destroy()
            checks.append("GUI: OK (13 disciplinas, búsqueda, lienzo)")
        else:
            checks.append("GUI: omitida (sin display)")

        # 26) Edición GUI headless (FASE 90.1): PropertyEditor y
        #     EditService por las mismas fachadas que la CLI, con
        #     auditoría UPDATE_ENTITY y undo persistente §77.
        from ui.models import ExplorerModel, PropertyEditor, EditService
        gui_explorer = ExplorerModel(context)
        gui_edit = EditService(context, gui_explorer)
        wall_row = next(r for r in gui_explorer.rows_for("ARCHITECTURE")
                        if r.type == "WALL" and r.entity is not None)
        old_thickness = wall_row.entity.thickness_m
        PropertyEditor.edit(context, wall_row, "thickness_m", "0.33")
        wall_saved = context.architecture.get("WALL", wall_row.uid)
        assert abs(wall_saved.thickness_m - 0.33) < 1e-9, \
            "la edición GUI no persistió"
        audit_rows = [e for e in context.audit_repo.recent(limit=100)
                      if e["command"] == "UPDATE_ENTITY"
                      and e["object_id"] == wall_row.uid]
        assert audit_rows, "edición GUI sin auditoría UPDATE_ENTITY"
        space_created = gui_edit.create("SPACE", {
            "level_ref": gui_edit.choices("levels")[0],
            "name": "Local selftest"})
        assert len(space_created.boundary) == 4, \
            "creación GUI de local sin contorno"
        from app.undo_service import PersistentUndoService
        PersistentUndoService(context).undo()  # revierte la creación
        context.commit()
        assert context.architecture.get("SPACE", space_created.id) is None, \
            "undo GUI no revirtió la creación"
        PropertyEditor.edit(context, wall_row, "thickness_m",
                            str(old_thickness))
        checks.append("edición GUI: OK (propiedad auditada, creación, undo)")

        # 27) Scripts .bat (solo en desarrollo; en el ejecutable congelado
        #     no viajan junto al binario). Incidencia real: los .bat con
        #     fin de linea LF de Unix se caen en Windows sin ejecutar nada
        #     y sin dejar log. Garantias: CRLF, ASCII sin BOM, pause en
        #     errores y cd /d al directorio del script.
        if getattr(sys, "frozen", False):
            checks.append("scripts .bat: omitido (ejecutable compilado)")
        else:
            bat_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            bat_names = [
                "00_VERIFICAR_ENTORNO.bat", "01_INSTALAR_DEPENDENCIAS.bat",
                "02_PRUEBAS.bat", "03_COMPILAR.bat", "04_EJECUTAR.bat",
                "05_EJECUTAR_COMPILADO.bat", "06_DEMO.bat", "07_LIMPIAR.bat",
                "08_GUI.bat", "09_GUI_COMPILADO.bat",
            ]
            for bat_name in bat_names:
                bat_path = os.path.join(bat_root, bat_name)
                assert os.path.isfile(bat_path), f"falta {bat_name}"
                with open(bat_path, "rb") as bat_fh:
                    bat_raw = bat_fh.read()
                assert not bat_raw.startswith(b"\xef\xbb\xbf"), \
                    f"{bat_name} con BOM UTF-8"
                bat_lf = bat_raw.count(b"\n")
                assert bat_lf > 0, f"{bat_name} vacío"
                assert bat_lf == bat_raw.count(b"\r\n") == bat_raw.count(b"\r"), \
                    f"{bat_name} sin fin de linea CRLF (cmd.exe lo aborta)"
                bat_raw.decode("ascii")
                assert b"pause" in bat_raw, f"{bat_name} sin pause en errores"
                assert bat_raw.split(b"\r\n", 1)[0] == b"@echo off", \
                    f"{bat_name} sin @echo off"
            checks.append(f"scripts .bat: OK ({len(bat_names)} CRLF+ASCII+pause)")

        # 28) Importers spec 94: flat catalog auto-detection -> ruleset
        from importers.catalog import CatalogImporter
        from importers.dxf_reader import (DxfImporter, WALL_LAYER_HINTS,
                                          SPACE_LAYER_HINTS)
        from openpyxl import Workbook
        book = Workbook()
        sheet = book.active
        sheet.title = "BASE"
        sheet.append(["Partida", "Nombre", "UM", "Recurso", "Rendimiento", "Merma"])
        sheet.append(["E-01", "Muro de bloque", "m3", "BLOQUE", 72, 5])
        sheet.append(["E-01", "", "", "CEMENTO", 18, 3])
        cat_path = os.path.join(tmp, "selftest_catalogo.xlsx")
        book.save(cat_path)
        payload_cat, report_cat = CatalogImporter().apply(
            cat_path, code="SELFTEST",
            out_path=os.path.join(tmp, "selftest_ruleset.json"))
        assert report_cat["errors"] == [], \
            f"errores de importación: {report_cat['errors']}"
        assert len(payload_cat["work_items"]) == 1, "partida no importada"
        assert len(payload_cat["work_items"][0]["indicators"]) == 2, \
            "indicadores incompletos"
        assert os.path.getsize(os.path.join(tmp, "selftest_ruleset.json")) > 0
        assert WALL_LAYER_HINTS and SPACE_LAYER_HINTS
        _ = DxfImporter  # DXF importer available in the bundle
        checks.append("importadores §94: OK (catálogo plano -> ruleset)")

        # 29) UX v1.7.1: tema oscuro, ayuda dinámica y guía de flujo.
        #     Contratos: tooltips obligatorios, ayudas por campo de los
        #     formularios, mensajes de menú, guía de 4 pasos y el motor
        #     de siguiente paso (sin Tk: contenido puro verificable
        #     también en el ejecutable headless).
        from ui.help import (FIELD_HINTS, GUIDE_STEPS, MENU_HINTS,
                             TOOLTIPS, next_hint)
        from ui.app_window import ACCELERATORS as UX_ACCEL, PALETTE
        for key in ("guide", "new_object", "edit", "search_btn",
                    "level_combo", "canvas", "props_edit", "state_btn"):
            assert len(TOOLTIPS.get(key, "")) > 10, f"tooltip {key} vacío"
        from ui.models import CREATE_SPECS
        for entity_type, (_disc, fields) in CREATE_SPECS.items():
            for param, *_rest in fields:
                assert param in FIELD_HINTS, \
                    f"{entity_type}.{param} sin ayuda dinámica"
        for label in ("Archivo", "Editar", "Ver", "Herramientas", "Ayuda"):
            assert label in MENU_HINTS and len(MENU_HINTS[label]) > 20, \
                f"menú sin mensaje orientador: {label}"
        assert len(GUIDE_STEPS) == 4, "la guía rápida debe tener 4 pasos"
        assert UX_ACCEL.get("<F1>") == "show_quick_guide", "F1 sin guía"
        assert PALETTE["selection"] == "#FF7A88", "paleta oscura cambiada"
        assert "local" in next_hint(spaces=0) \
            and "muro" in next_hint(spaces=2, walls=0)
        checks.append("UX v1.7.1: OK (tema oscuro, ayuda dinámica, guía)")

        context.close()
    except Exception as exc:  # noqa: BLE001
        ok = False
        checks.append(f"FALLO: {type(exc).__name__}: {exc}")
        logger.error("Selftest falló: %s\n%s", exc, traceback.format_exc())
    finally:
        # Cleanup temp tree best-effort
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if console:
        print("=" * 56)
        print("ARQ GEN — SELFTEST")
        print("=" * 56)
        for check in checks:
            marker = "OK  " if not check.startswith("FALLO") else "FAIL"
            print(f"[{marker}] {check}")
        print("=" * 56)
        print("RESULTADO:", "CORRECTO" if ok else "CON FALLOS")
    return ok, checks


def main() -> int:
    ok, _ = run_selftest(console=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["run_selftest", "main"]
