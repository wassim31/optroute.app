from app.routing import RouteGeometry, RouteSegment, RoutingService
from app.routing.provider import RoutingProvider
from app.vrp.models import Route, RouteStop, VRPSolution


class FakeProvider(RoutingProvider):
    """Deterministic provider that records the waypoints it was asked to route."""

    def __init__(self):
        self.requests = []

    def get_route(self, coordinates):
        self.requests.append(coordinates)
        segments = [
            RouteSegment(distance=10.0, duration=60.0) for _ in range(len(coordinates) - 1)
        ]
        return RouteGeometry(
            polyline=coordinates,
            distance=sum(s.distance for s in segments),
            duration=sum(s.duration for s in segments),
            segments=segments,
        )


def test_build_route_returns_polyline_and_segments():
    provider = FakeProvider()
    service = RoutingService(provider)

    coordinates = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    geometry = service.build_route(coordinates)

    assert geometry.polyline == coordinates
    assert len(geometry.segments) == 2
    assert geometry.distance == 20.0
    assert geometry.duration == 120.0


def test_build_route_with_fewer_than_two_points_is_empty():
    service = RoutingService(FakeProvider())

    assert service.build_route([(0.0, 0.0)]) == RouteGeometry()


def test_build_routes_for_solution_matches_solver_order():
    provider = FakeProvider()
    service = RoutingService(provider)

    solution = VRPSolution(
        routes=[
            Route(
                vehicle_id="v1",
                stops=[
                    RouteStop(stop_id="A", arrival_time=10, departure_time=10),
                    RouteStop(stop_id="B", arrival_time=20, departure_time=20),
                ],
                distance=100,
                duration=200,
            )
        ],
        total_distance=100,
        total_duration=200,
        vehicles_used=1,
    )

    depot = (0.0, 0.0)
    stop_coordinates = {"A": (1.0, 1.0), "B": (2.0, 2.0)}

    routes = service.build_routes_for_solution(solution, depot, stop_coordinates)

    assert set(routes.keys()) == {"v1"}
    # depot -> A -> B, matching the solver's stop order, without returning to the depot
    assert provider.requests[0] == [depot, (1.0, 1.0), (2.0, 2.0)]
    assert len(routes["v1"].segments) == 2
