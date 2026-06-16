"""Build real road routes from ordered stops."""

from typing import Dict, List

from ..vrp.models import VRPSolution
from .models import Coordinate, RouteGeometry
from .provider import RoutingProvider


class RoutingService:
    def __init__(self, provider: RoutingProvider):
        self._provider = provider

    def build_route(self, coordinates: List[Coordinate]) -> RouteGeometry:
        """Returns road geometry for an ordered list of (lat, lon) waypoints."""
        if len(coordinates) < 2:
            return RouteGeometry()
        return self._provider.get_route(coordinates)

    def build_routes_for_solution(
        self, solution: VRPSolution, depot: Coordinate, stop_coordinates: Dict[str, Coordinate]
    ) -> Dict[str, RouteGeometry]:
        """For each vehicle route in a VRP solution, builds depot -> stops (in
        solver order) road geometry, ending at the last stop rather than
        returning to the depot. Keyed by vehicle_id, so the result lines up
        1:1 with `solution.routes`."""
        routes = {}
        for route in solution.routes:
            waypoints = [depot] + [stop_coordinates[rs.stop_id] for rs in route.stops]
            routes[route.vehicle_id] = self.build_route(waypoints)
        return routes
