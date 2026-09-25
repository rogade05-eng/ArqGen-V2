"""Domain entities of the unique semantic model (spec sections 7, 20).

Project → Site → Building → Level → Zone → Space → Wall → Door/Window/Opening.
One wall is ONE wall: every discipline reads the same object (spec 111).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.entities.base import Entity, EntityStatus
from core.errors import DomainError
from core.geometry.engine import area as geom_area
from core.geometry.primitives import Point, Polygon


@dataclass
class Project(Entity):
    ENTITY_TYPE = "PROJECT"
    name: str = ""
    client: str = ""
    address: str = ""
    description: str = ""
    units_length: str = "m"
    ruleset_code: str = ""
    currency: str = "CUP"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.name:
            raise DomainError(
                message="El proyecto requiere un nombre",
                code="ARQ-DOM-002",
            )


@dataclass
class Site(Entity):
    ENTITY_TYPE = "SITE"
    name: str = ""
    area_m2: float = 0.0
    boundary: Optional[List[Tuple[float, float]]] = None


@dataclass
class Building(Entity):
    ENTITY_TYPE = "BUILDING"
    site_id: Optional[str] = None
    name: str = ""
    floors: int = 1
    description: str = ""


@dataclass
class Level(Entity):
    ENTITY_TYPE = "LEVEL"
    building_id: Optional[str] = None
    name: str = ""
    elevation_m: float = 0.0
    height_m: float = 3.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.height_m <= 0:
            raise DomainError(
                message=f"La altura del nivel '{self.name}' debe ser positiva",
                code="ARQ-DOM-003",
                context={"height_m": self.height_m},
            )


@dataclass
class Zone(Entity):
    """Zones: PUBLIC / PRIVATE / SERVICE / TECHNICAL / CIRCULATION / EMERGENCY / EXTERIOR (spec 17)."""

    ENTITY_TYPE = "ZONE"
    name: str = ""
    kind: str = "SERVICE"
    allowed_kinds: Tuple[str, ...] = (
        "PUBLIC", "PRIVATE", "SERVICE", "TECHNICAL",
        "CIRCULATION", "EMERGENCY", "EXTERIOR",
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind not in self.allowed_kinds:
            raise DomainError(
                message=f"Tipo de zona inválido: {self.kind}",
                code="ARQ-DOM-004",
                context={"kind": self.kind, "allowed": list(self.allowed_kinds)},
            )


@dataclass
class Space(Entity):
    ENTITY_TYPE = "SPACE"
    level_id: str = ""
    zone_id: Optional[str] = None
    name: str = ""
    space_type: str = "ROOM"          # key into Space DNA
    boundary: List[Tuple[float, float]] = field(default_factory=list)  # meters

    def polygon(self) -> Polygon:
        return Polygon([Point(x, y) for x, y in self.boundary])

    def area_m2(self) -> float:
        if len(self.boundary) < 3:
            return 0.0
        return geom_area(self.polygon())

    def perimeter_m(self) -> float:
        if len(self.boundary) < 3:
            return 0.0
        return sum(s.length for s in self.polygon().segments())


RELATIONSHIP_KINDS: Tuple[str, ...] = (
    "adjacent_to",
    "accessible_from",
    "requires_access",
    "visually_related_to",
    "acoustically_separated_from",
    "service_related_to",
)


@dataclass
class SpaceRelationship(Entity):
    """Relationships are logical entities too (spec section 8)."""

    ENTITY_TYPE = "SPACE_RELATIONSHIP"
    from_space_id: str = ""
    to_space_id: str = ""
    kind: str = "adjacent_to"
    source: str = "manual"  # geometry | knowledge | manual

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind not in RELATIONSHIP_KINDS:
            raise DomainError(
                message=f"Tipo de relación inválido: {self.kind}",
                code="ARQ-DOM-005",
                context={"kind": self.kind, "allowed": list(RELATIONSHIP_KINDS)},
            )


@dataclass
class Wall(Entity):
    ENTITY_TYPE = "WALL"
    level_id: str = ""
    start: Tuple[float, float] = (0.0, 0.0)
    end: Tuple[float, float] = (1.0, 0.0)
    thickness_m: float = 0.2
    height_m: float = 3.0
    base_offset_m: float = 0.0
    material_id: Optional[str] = None
    structural: bool = False

    @property
    def length_m(self) -> float:
        return Point(*self.start).distance_to(Point(*self.end))


@dataclass
class Opening(Entity):
    """Base for Door / Window / generic Opening cut into a wall."""

    ENTITY_TYPE = "OPENING"
    level_id: str = ""
    wall_id: str = ""
    kind: str = "OPENING"            # DOOR | WINDOW | OPENING
    width_m: float = 0.9
    height_m: float = 2.1
    offset_m: float = 0.0            # distance along wall from start
    sill_height_m: float = 0.0       # for windows
    swing: str = "LEFT"              # doors
    material_id: Optional[str] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind not in ("DOOR", "WINDOW", "OPENING"):
            raise DomainError(
                message=f"Tipo de vano inválido: {self.kind}",
                code="ARQ-DOM-006",
                context={"kind": self.kind},
            )
        if self.width_m <= 0 or self.height_m <= 0:
            raise DomainError(
                message="Las dimensiones del vano deben ser positivas",
                code="ARQ-DOM-007",
                context={"width_m": self.width_m, "height_m": self.height_m},
            )

    @property
    def area_m2(self) -> float:
        return self.width_m * self.height_m


@dataclass
class Door(Opening):
    ENTITY_TYPE = "DOOR"
    kind: str = "DOOR"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.kind = "DOOR"


@dataclass
class Window(Opening):
    ENTITY_TYPE = "WINDOW"
    kind: str = "WINDOW"

    def __post_init__(self) -> None:
        super().__post_init__()
        self.kind = "WINDOW"
        if self.sill_height_m < 0:
            raise DomainError(
                message="La altura de antepecho no puede ser negativa",
                code="ARQ-DOM-008",
            )


__all__ = [
    "Project", "Site", "Building", "Level", "Zone", "Space",
    "SpaceRelationship", "RELATIONSHIP_KINDS",
    "Wall", "Opening", "Door", "Window",
]
