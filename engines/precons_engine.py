"""PRECONS Engine (spec section 59) y motor tipo SIECONS (spec 60).

La integración con PRECONS III es un **sistema versionado de reglas,
indicadores, partidas, recursos, rendimientos y precios** (datos JSON),
no una tabla rígida incrustada en Python (spec 59):

    PRECONS_RULESET → WORK ITEMS → INDICATORS → RESOURCES
                    → PRICE LIST → PRICE ANALYSIS

El motor reproduce funcionalmente los conceptos de un sistema
profesional de presupuestos (spec 60): partidas, renglones, recursos,
indicadores, rendimientos, precios, análisis, coeficientes, indirectos,
variantes, actualizaciones, comparaciones y reportes.

Cálculos (todos deterministas y trazables):
  - takeoff(item, quantity): renglones = cantidad × rendimiento ×
    (1 + desperdicio), agrupados por recurso.
  - price_analysis(item, prices): precio unitario = Σ renglones ×
    precio; directo por tipo (material/mano de obra/equipo/transporte);
    transporte como % del directo; indirectos y beneficio sobre el
    directo + transporte.
  - update_analysis: re-precio con nueva lista (actualizaciones).
  - compare_analyses: comparación entre variantes/fechas.

El importador/mapeador (spec 60) acepta estructuras externas distintas
vía un mapa de columnas explícito: nunca se asume una estructura fija.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.errors import CalculationError, DomainError

RESOURCE_KINDS: Tuple[str, ...] = ("MATERIAL", "LABOR", "EQUIPMENT",
                                   "TRANSPORT", "CONSUMABLE", "OTHER")


@dataclass
class PreconsRuleset:
    """Ruleset PRECONS versionado (spec 59)."""

    code: str = ""
    name: str = ""
    version: str = "1.0"
    currency: str = "CUP"
    description: str = ""
    coefficients: Dict[str, float] = field(default_factory=dict)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    work_items: List[Dict[str, Any]] = field(default_factory=list)
    variants: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "PreconsRuleset":
        if not os.path.exists(path):
            raise DomainError(
                message=f"Ruleset PRECONS no encontrado: {path}",
                code="ARQ-PRE-001")
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreconsRuleset":
        required = ("code", "work_items", "resources")
        for key in required:
            if key not in data:
                raise DomainError(
                    message=f"Ruleset PRECONS incompleto: falta '{key}'",
                    code="ARQ-PRE-002", context={"missing": key})
        return cls(
            code=data["code"], name=data.get("name", ""),
            version=str(data.get("version", "1.0")),
            currency=data.get("currency", "CUP"),
            description=data.get("description", ""),
            coefficients=dict(data.get("coefficients", {})),
            resources=list(data.get("resources", [])),
            work_items=list(data.get("work_items", [])),
            variants=list(data.get("variants", [])),
        )

    # -- acceso ---------------------------------------------------------------
    def item(self, code: str) -> Dict[str, Any]:
        for work_item in self.work_items:
            if work_item["code"] == code:
                return work_item
        raise DomainError(
            message=f"Partida PRECONS desconocida: {code}",
            code="ARQ-PRE-003", context={"code": code,
                                         "available": [i["code"] for i in self.work_items]})

    def resource(self, code: str) -> Dict[str, Any]:
        for resource in self.resources:
            if resource["code"] == code:
                return resource
        raise DomainError(
            message=f"Recurso PRECONS desconocido: {code}",
            code="ARQ-PRE-004", context={"code": code})

    def variant(self, code: str) -> Dict[str, Any]:
        for variant in self.variants:
            if variant["code"] == code:
                return variant
        raise DomainError(
            message=f"Variante desconocida: {code}",
            code="ARQ-PRE-005", context={"code": code})


# -- Renglones / takeoff (rendimientos) -----------------------------------------------

def takeoff(ruleset: PreconsRuleset, item_code: str, quantity: float,
            multiplier: float = 1.0) -> List[Dict[str, Any]]:
    """Renglones de recursos para una partida (indicadores/rendimientos).

    Devuelve [{resource, name, kind, unit, quantity}] con la cantidad
    = qty × rendimiento × (1 + desperdicio) × multiplicador de variante.
    """
    if quantity < 0:
        raise CalculationError(
            message="La cantidad de la partida no puede ser negativa",
            code="ARQ-PRE-006", context={"quantity": quantity})
    work_item = ruleset.item(item_code)
    lines: List[Dict[str, Any]] = []
    for indicator in work_item.get("indicators", []):
        resource = ruleset.resource(indicator["resource"])
        yield_value = float(indicator.get("yield", 0.0))
        if yield_value < 0:
            raise CalculationError(
                message=f"Rendimiento negativo en {item_code}/{indicator['resource']}",
                code="ARQ-PRE-007", context={"yield": yield_value})
        waste = float(indicator.get("waste_pct", 0.0))
        amount = quantity * yield_value * (1.0 + waste / 100.0) * multiplier
        lines.append({
            "resource": resource["code"], "name": resource.get("name", ""),
            "kind": resource.get("kind", "OTHER"),
            "unit": resource.get("unit", ""),
            "quantity": round(amount, 4),
        })
    return lines


# -- Análisis de precio ------------------------------------------------------------

@dataclass
class PriceAnalysis:
    """Análisis de precio unitario de una partida (price analysis)."""

    item: str = ""
    name: str = ""
    unit: str = ""
    quantity: float = 0.0
    variant: str = "BASE"
    direct_material: float = 0.0
    direct_labor: float = 0.0
    direct_equipment: float = 0.0
    direct_transport: float = 0.0
    direct_cost: float = 0.0
    transport_pct: float = 0.0
    indirect_pct: float = 0.0
    benefit_pct: float = 0.0
    indirect_cost: float = 0.0
    benefit: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0
    currency: str = "CUP"
    lines: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "item": self.item, "name": self.name, "unit": self.unit,
            "quantity": round(self.quantity, 3), "variant": self.variant,
            "direct_material": round(self.direct_material, 2),
            "direct_labor": round(self.direct_labor, 2),
            "direct_equipment": round(self.direct_equipment, 2),
            "direct_transport": round(self.direct_transport, 2),
            "direct_cost": round(self.direct_cost, 2),
            "transport_pct": self.transport_pct,
            "indirect_pct": self.indirect_pct,
            "benefit_pct": self.benefit_pct,
            "indirect_cost": round(self.indirect_cost, 2),
            "benefit": round(self.benefit, 2),
            "unit_price": round(self.unit_price, 2),
            "total_price": round(self.total_price, 2),
            "currency": self.currency,
            "lines": self.lines,
        }


def price_analysis(ruleset: PreconsRuleset, item_code: str, quantity: float,
                   prices: Dict[str, float], variant_code: str = "BASE"
                   ) -> PriceAnalysis:
    """Análisis de precio de una partida (precio/análisis/coeficientes).

    prices: {resource_code: precio unitario}. El transporte de la
    ruleset se aplica como % del costo directo (coeficiente), los
    indirectos y el beneficio sobre directo + transporte.
    """
    work_item = ruleset.item(item_code)
    missing = [i["resource"] for i in work_item.get("indicators", [])
               if i["resource"] not in prices]
    if missing:
        raise CalculationError(
            message=f"Faltan precios de recursos para {item_code}: "
                    f"{', '.join(missing)}",
            code="ARQ-PRE-008", context={"missing": missing})
    multiplier = 1.0
    if variant_code and variant_code != "BASE":
        multiplier = float(ruleset.variant(variant_code).get("multiplier", 1.0))
    coefficients = ruleset.coefficients
    analysis = PriceAnalysis(
        item=work_item["code"], name=work_item.get("name", ""),
        unit=work_item.get("unit", ""), quantity=quantity,
        variant=variant_code or "BASE",
        transport_pct=float(coefficients.get("transport_pct", 0.0)),
        indirect_pct=float(coefficients.get("indirect_pct", 0.0)),
        benefit_pct=float(coefficients.get("benefit_pct", 0.0)),
        currency=ruleset.currency)
    for line in takeoff(ruleset, item_code, quantity, multiplier):
        price = float(prices[line["resource"]])
        cost = line["quantity"] * price
        line["price"] = round(price, 4)
        line["cost"] = round(cost, 2)
        kind = line["kind"]
        if kind == "MATERIAL":
            analysis.direct_material += cost
        elif kind == "LABOR":
            analysis.direct_labor += cost
        elif kind == "EQUIPMENT":
            analysis.direct_equipment += cost
        elif kind == "TRANSPORT":
            analysis.direct_transport += cost
        analysis.lines.append(line)
    analysis.direct_cost = (analysis.direct_material + analysis.direct_labor
                            + analysis.direct_equipment
                            + analysis.direct_transport)
    # Transporte como coeficiente sobre materiales (si no está en renglones).
    if analysis.direct_transport == 0 and analysis.transport_pct > 0:
        analysis.direct_transport = \
            analysis.direct_material * analysis.transport_pct / 100.0
        analysis.direct_cost += analysis.direct_transport
    analysis.indirect_cost = analysis.direct_cost * analysis.indirect_pct / 100.0
    analysis.benefit = analysis.direct_cost * analysis.benefit_pct / 100.0
    total = analysis.direct_cost + analysis.indirect_cost + analysis.benefit
    analysis.unit_price = total / quantity if quantity > 0 else 0.0
    analysis.total_price = total
    return analysis


def compare_analyses(analyses: List[PriceAnalysis]) -> Dict[str, Any]:
    """Comparación entre variantes o versiones (comparaciones/variantes)."""
    if not analyses:
        raise CalculationError(
            message="No hay análisis que comparar", code="ARQ-PRE-009")
    rows = []
    for analysis in analyses:
        rows.append({
            "item": analysis.item, "variant": analysis.variant,
            "quantity": round(analysis.quantity, 3),
            "unit_price": round(analysis.unit_price, 2),
            "total_price": round(analysis.total_price, 2),
            "currency": analysis.currency,
        })
    by_item: Dict[str, Dict[str, float]] = {}
    for row in rows:
        entry = by_item.setdefault(row["item"], {})
        entry[row["variant"]] = row["unit_price"]
    return {"rows": rows, "unit_prices_by_variant": by_item}


def update_analysis(ruleset: PreconsRuleset, analysis: PriceAnalysis,
                    prices: Dict[str, float]) -> PriceAnalysis:
    """Actualizar un análisis con nueva lista de precios (actualizaciones)."""
    return price_analysis(ruleset, analysis.item, analysis.quantity,
                          prices, analysis.variant)


# -- Importador / mapeador (spec 60) -----------------------------------------------

def import_external(data: Any, mapping: Dict[str, str],
                    code: str = "imported", name: str = "",
                    version: str = "1.0") -> PreconsRuleset:
    """Importador con mapa de columnas explícito (spec 60).

    La estructura externa nunca se da por supuesta: ``mapping`` dice
    cómo se llama cada campo del ruleset dentro de ``data``:

        {"code": "codigo", "name": "descripcion", "unit": "um",
         "resources": "recursos", "work_items": "partidas",
         "indicators": "rendimientos", "resource": "insumo",
         "yield": "cantidad", "waste_pct": "desperdicio",
         "kind": "tipo", "coefficients": "coeficientes"}

    ``data`` puede ser dict ya cargado o lista de partidas planas.
    """
    if not isinstance(mapping, dict) or not mapping.get("work_items"):
        raise DomainError(
            message="El mapa de importación exige al menos la clave 'work_items'",
            code="ARQ-PRE-010")
    if isinstance(data, dict):
        raw_items = data.get(mapping["work_items"], [])
        raw_resources = data.get(mapping.get("resources", ""), [])
        coefficients = data.get(mapping.get("coefficients", ""), {}) or {}
    else:
        raw_items = data
        raw_resources = []
        coefficients = {}
    if not isinstance(raw_items, list):
        raise DomainError(
            message="Las partidas externas deben venir en una lista",
            code="ARQ-PRE-011")

    def pick(row: Dict[str, Any], key: str, default=None):
        external_key = mapping.get(key, key)
        return row.get(external_key, row.get(key, default))

    resources: List[Dict[str, Any]] = []
    for row in raw_resources or []:
        resources.append({
            "code": pick(row, "resource"),
            "name": pick(row, "name", ""),
            "kind": pick(row, "kind", "OTHER"),
            "unit": pick(row, "unit", ""),
        })
    work_items: List[Dict[str, Any]] = []
    for row in raw_items:
        raw_indicators = row.get(mapping.get("indicators", "indicators"), []) or []
        indicators = []
        for indicator in raw_indicators:
            indicators.append({
                "resource": pick(indicator, "resource"),
                "yield": float(pick(indicator, "yield", 0.0) or 0.0),
                "waste_pct": float(pick(indicator, "waste_pct", 0.0) or 0.0),
            })
        work_items.append({
            "code": pick(row, "code"),
            "name": pick(row, "name", ""),
            "unit": pick(row, "unit", ""),
            "qto_formula": pick(row, "qto_formula", ""),
            "indicators": indicators,
        })
    return PreconsRuleset.from_dict({
        "code": code, "name": name or code, "version": version,
        "currency": "CUP", "coefficients": coefficients,
        "resources": resources, "work_items": work_items,
    })


__all__ = [
    "PreconsRuleset", "PriceAnalysis", "RESOURCE_KINDS",
    "takeoff", "price_analysis", "compare_analyses", "update_analysis",
    "import_external",
]
