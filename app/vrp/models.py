"""Data model for the VRPTW problem and its solution.

Node 0 is always the depot. `stops[i]` corresponds to matrix node `i + 1`.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

# A day-wide window used when a stop/vehicle does not specify its own.
UNBOUNDED_WINDOW: Tuple[int, int] = (0, 24 * 3600)


@dataclass
class Stop:
    id: str
    demand: int = 0
    time_window: Tuple[int, int] = UNBOUNDED_WINDOW
    service_time: int = 0


@dataclass
class Vehicle:
    id: str
    capacity: int = 0
    shift: Tuple[int, int] = UNBOUNDED_WINDOW


@dataclass
class RouteStop:
    stop_id: str
    arrival_time: int
    departure_time: int


@dataclass
class Route:
    vehicle_id: str
    stops: List[RouteStop] = field(default_factory=list)
    distance: float = 0.0
    duration: int = 0


@dataclass
class VRPSolution:
    routes: List[Route]
    total_distance: float
    total_duration: int
    vehicles_used: int
