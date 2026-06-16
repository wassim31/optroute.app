"""Data model for road-route geometry."""

from dataclasses import dataclass, field
from typing import List, Tuple

Coordinate = Tuple[float, float]


@dataclass
class RouteSegment:
    distance: float
    duration: float


@dataclass
class RouteGeometry:
    polyline: List[Coordinate] = field(default_factory=list)
    distance: float = 0.0
    duration: float = 0.0
    segments: List[RouteSegment] = field(default_factory=list)
