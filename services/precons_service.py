"""PreconsService (spec sections 59, 60, 102).

Facade of the PRECONS III integration and the SIECONS-like engine:
loads versioned rulesets from resources, resolves work items against
QTO totals (formula mapping), builds price analyses with project price
lists, compares variants and imports external databases through an
explicit column mapping. Analyses travel as CalculationResult records
(calculation type PRE, spec 102) — reproducible and auditable.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.errors import DomainError
from engines.precons_engine import (
    PreconsRuleset, PriceAnalysis, compare_analyses, import_external,
    price_analysis,
)
from services.context import ProjectContext


class PreconsService:
    """Facade of the PRECONS / SIECONS-like module (spec 59-60)."""

    def __init__(self, context: ProjectContext,
                 ruleset: Optional[PreconsRuleset] = None) -> None:
        self.ctx = context
        self.ruleset = ruleset

    # -- rulesets ------------------------------------------------------------
    def load_ruleset(self, code: str) -> PreconsRuleset:
        """Carga un ruleset PRECONS versionado desde resources (spec 59)."""
        from app.paths import resource_path
        path = resource_path("rulesets", f"{code}.json")
        self.ruleset = PreconsRuleset.from_file(path)
        return self.ruleset

    def _require_ruleset(self) -> PreconsRuleset:
        if self.ruleset is None:
            raise DomainError(
                message="No hay ruleset PRECONS cargado",
                code="ARQ-PRE-012",
                suggested_action="Use precons --ruleset <código> para cargarlo.")
        return self.ruleset

    # -- price list ------------------------------------------------------------
    def _prices_from_project(self, price_list_code: str = "GENERAL"
                             ) -> Dict[str, float]:
        """Último precio por recurso de la lista indicada (spec 61).

        Nunca se sobrescribe el histórico: se lee la vigencia más
        reciente con valid_from <= hoy.
        """
        repo = self.ctx.budget_repo
        plist = repo.get_price_list_by_code(self.ctx.project.id, price_list_code)
        if plist is None:
            raise DomainError(
                message=f"Lista de precios no encontrada: {price_list_code}",
                code="ARQ-PRE-013",
                suggested_action="Cree la lista con 'price set' antes de analizar.")
        rows = repo.session.query_all(
            """
            SELECT r.code AS code, p.price AS price
            FROM prices p
            JOIN resources r ON r.id = p.resource_id
            WHERE p.project_id = ? AND p.price_list_id = ?
              AND p.valid_from <= date('now')
            AND p.id = (
                SELECT p2.id FROM prices p2
                WHERE p2.resource_id = p.resource_id
                  AND p2.price_list_id = p.price_list_id
                  AND p2.valid_from <= date('now')
                ORDER BY p2.valid_from DESC, p2.created_at DESC LIMIT 1)
            """,
            (self.ctx.project.id, plist["id"]))
        prices: Dict[str, float] = {}
        for row in rows:
            prices[row["code"]] = float(row["price"])
        return prices

    # -- analyses ------------------------------------------------------------------
    def analyze_item(self, item_code: str, quantity: float,
                     variant: str = "BASE",
                     prices: Optional[Dict[str, float]] = None) -> PriceAnalysis:
        """Análisis de precio de una partida (price analysis)."""
        ruleset = self._require_ruleset()
        prices = prices if prices is not None else self._prices_from_project()
        analysis = price_analysis(ruleset, item_code, quantity, prices, variant)
        self._store(analysis, parameters={"variant": variant})
        return analysis

    def analyze_project(self, variant: str = "BASE",
                        prices: Optional[Dict[str, float]] = None
                        ) -> Dict[str, Any]:
        """Análisis del proyecto: partidas alimentadas por QTO (spec 59)."""
        ruleset = self._require_ruleset()
        prices = prices if prices is not None else self._prices_from_project()
        from services.quantity_service import QuantityService
        totals = QuantityService(self.ctx).totals_by_formula()
        analyses: List[PriceAnalysis] = []
        skipped: List[Dict[str, str]] = []
        for work_item in ruleset.work_items:
            formula = work_item.get("qto_formula", "")
            if not formula:
                skipped.append({"item": work_item["code"],
                                "reason": "sin fórmula QTO asociada"})
                continue
            quantity = totals.get(formula, 0.0)
            if quantity <= 0:
                skipped.append({"item": work_item["code"],
                                "reason": f"sin cantidades de {formula}"})
                continue
            missing = [i["resource"] for i in work_item.get("indicators", [])
                       if i["resource"] not in prices]
            if missing:
                skipped.append({"item": work_item["code"],
                                "reason": "sin precios: " + ", ".join(missing)})
                continue
            analyses.append(price_analysis(ruleset, work_item["code"],
                                           quantity, prices, variant))
        total = sum(a.total_price for a in analyses)
        for analysis in analyses:
            self._store(analysis, parameters={"variant": variant,
                                              "source": "project"})
        self.ctx.commit()
        return {
            "ruleset": ruleset.code, "version": ruleset.version,
            "variant": variant, "currency": ruleset.currency,
            "analyses": [a.to_dict() for a in analyses],
            "skipped": skipped,
            "total": round(total, 2),
        }

    def compare_variants(self, item_code: str, quantity: float,
                         variants: Optional[List[str]] = None,
                         prices: Optional[Dict[str, float]] = None
                         ) -> Dict[str, Any]:
        """Comparación de variantes de la ruleset (spec 60, 62)."""
        ruleset = self._require_ruleset()
        prices = prices if prices is not None else self._prices_from_project()
        variants = variants or [v.get("code", "BASE") for v in ruleset.variants] \
            or ["BASE"]
        analyses = [price_analysis(ruleset, item_code, quantity, prices, variant)
                    for variant in variants]
        for analysis in analyses:
            self._store(analysis, parameters={"source": "compare"})
        return compare_analyses(analyses)

    # -- importador (spec 60) ---------------------------------------------------
    def import_ruleset(self, data: Any, mapping: Dict[str, str],
                       code: str = "imported", name: str = "",
                       out_path: str = "") -> PreconsRuleset:
        """Importa una base externa con mapa de columnas (spec 60)."""
        ruleset = import_external(data, mapping, code=code, name=name)
        if out_path:
            import json
            directory = os.path.dirname(out_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump({
                    "code": ruleset.code, "name": ruleset.name,
                    "description": "Ruleset importado vía mapa de columnas",
                    "version": ruleset.version,
                    "currency": ruleset.currency,
                    "coefficients": ruleset.coefficients,
                    "resources": ruleset.resources,
                    "work_items": ruleset.work_items,
                    "variants": ruleset.variants,
                }, handle, ensure_ascii=False, indent=2)
        return ruleset

    # -- reporte (spec 60) ---------------------------------------------------------
    def report(self, variant: str = "BASE") -> Dict[str, Any]:
        """Reporte del análisis del proyecto (reportes)."""
        return self.analyze_project(variant=variant)

    # -- persistence -----------------------------------------------------------------
    def _store(self, analysis: PriceAnalysis,
               parameters: Optional[Dict[str, Any]] = None) -> None:
        result_calc = self.ctx.calculations_repo
        from core.calculations.contracts import (
            CalculationMode, CalculationResult, CalculationStatus,
        )
        ruleset = self._require_ruleset()
        result = CalculationResult(
            calculation_type="PRE",
            input_objects=[],
            parameters={"item": analysis.item, "ruleset": ruleset.code,
                        "ruleset_version": ruleset.version,
                        **(parameters or {})},
            values={
                "quantity": round(analysis.quantity, 4),
                "direct_cost": round(analysis.direct_cost, 2),
                "indirect_cost": round(analysis.indirect_cost, 2),
                "benefit": round(analysis.benefit, 2),
                "unit_price": round(analysis.unit_price, 2),
                "total_price": round(analysis.total_price, 2),
            },
            units={"quantity": analysis.unit, "unit_price": analysis.currency,
                   "total_price": analysis.currency},
            errors=[], mode=CalculationMode.BALANCED,
            status=CalculationStatus.COMPLETED, objects_processed=1)
        result_calc.save(result, self.ctx.project.id)


__all__ = ["PreconsService"]
