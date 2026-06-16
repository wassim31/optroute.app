import math

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.routing.models import RouteGeometry, RouteSegment
from app.vrp import VRPSolver


class FakeGeocodingService:
    """Maps known addresses to fixed coordinates."""

    KNOWN = {
        "Depot HQ": {"lat": 0.0, "lon": 0.0},
        "Stop A": {"lat": 0.0, "lon": 1.0},
        "Stop B": {"lat": 1.0, "lon": 1.0},
    }

    def geocode_batch(self, addresses):
        return [{"address": a, **self.KNOWN.get(a, {"lat": None, "lon": None})} for a in addresses]


class FakeMatrixService:
    """Returns a Euclidean-distance-based matrix (seconds) for both duration and distance."""

    def compute_matrix(self, coordinates):
        matrix = [
            [round(math.dist(a, b) * 1000) for b in coordinates]
            for a in coordinates
        ]
        return matrix, matrix


class FakeRoutingService:
    def build_routes_for_solution(self, solution, depot, stop_coordinates):
        geometries = {}
        for route in solution.routes:
            waypoints = [depot] + [stop_coordinates[rs.stop_id] for rs in route.stops]
            segments = [RouteSegment(distance=50.0, duration=100.0) for _ in range(len(waypoints) - 1)]
            geometries[route.vehicle_id] = RouteGeometry(
                polyline=waypoints,
                distance=sum(s.distance for s in segments),
                duration=sum(s.duration for s in segments),
                segments=segments,
            )
        return geometries


def _fast_solver_factory(time_matrix, distance_matrix, stops, vehicles):
    return VRPSolver(time_matrix, distance_matrix, stops, vehicles, time_limit_seconds=2)


def _make_client():
    app = create_app(
        geocoding_service=FakeGeocodingService(),
        matrix_service=FakeMatrixService(),
        routing_service=FakeRoutingService(),
        vrp_solver_factory=_fast_solver_factory,
    )
    return TestClient(app)


def test_optimize_with_coordinates():
    client = _make_client()
    payload = {
        "depot": {"lat": 0.0, "lon": 0.0},
        "stops": [
            {"id": "A", "lat": 0.0, "lon": 1.0, "time_window": [0, 3600]},
            {"id": "B", "lat": 1.0, "lon": 1.0, "time_window": [0, 3600]},
        ],
        "vehicle": {"id": "v1", "capacity": 10, "shift": [0, 3600]},
    }

    response = client.post("/optimize", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert len(body["routes"]) == 1
    route = body["routes"][0]
    assert route["vehicle_id"] == "v1"
    assert set(route["stops"]) == {"A", "B"}
    assert route["geometry"]["segments"]
    assert {eta["stop_id"] for eta in route["stop_etas"]} == {"A", "B"}
    assert all("arrival_time" in eta for eta in route["stop_etas"])


def test_optimize_with_addresses_geocodes_first():
    client = _make_client()
    payload = {
        "depot": {"address": "Depot HQ"},
        "stops": [
            {"id": "A", "address": "Stop A", "time_window": [0, 3600]},
            {"id": "B", "address": "Stop B", "time_window": [0, 3600]},
        ],
        "vehicle": {"id": "v1", "capacity": 10, "shift": [0, 3600]},
    }

    response = client.post("/optimize", json=payload)

    assert response.status_code == 200
    body = response.json()
    visited = {s for route in body["routes"] for s in route["stops"]}
    assert visited == {"A", "B"}


def test_optimize_rejects_unresolvable_address():
    client = _make_client()
    payload = {
        "depot": {"address": "Unknown Place"},
        "stops": [{"id": "A", "address": "Stop A"}],
        "vehicle": {"id": "v1", "capacity": 10, "shift": [0, 3600]},
    }

    response = client.post("/optimize", json=payload)

    assert response.status_code == 422


def test_optimize_requires_location_for_each_stop():
    client = _make_client()
    payload = {
        "depot": {"lat": 0.0, "lon": 0.0},
        "stops": [{"id": "A"}],
        "vehicle": {"id": "v1", "capacity": 10, "shift": [0, 3600]},
    }

    response = client.post("/optimize", json=payload)

    assert response.status_code == 422


def test_optimize_requires_non_empty_stops():
    client = _make_client()
    payload = {"depot": {"lat": 0.0, "lon": 0.0}, "stops": []}

    response = client.post("/optimize", json=payload)

    assert response.status_code == 422


def test_config_endpoint(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_MAPS_MAP_ID", "test-map-id")
    client = _make_client()

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"googleMapsApiKey": "test-key", "googleMapsMapId": "test-map-id"}


def test_config_endpoint_defaults(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_MAP_ID", raising=False)
    client = _make_client()

    response = client.get("/config")

    assert response.status_code == 200
    assert response.json() == {"googleMapsApiKey": "", "googleMapsMapId": "DEMO_MAP_ID"}


def test_validate_addresses_endpoint():
    client = _make_client()
    payload = {
        "depot": "Depot HQ",
        "stops": ["Stop A", "  stop a  ", "Unknown Place", "", "Ab"],
    }

    response = client.post("/addresses/validate", json=payload)

    assert response.status_code == 200
    body = response.json()

    valid_addresses = {v["address"] for v in body["valid"]}
    assert valid_addresses == {"Depot HQ", "Stop A"}
    assert {v["role"] for v in body["valid"]} == {"depot", "stop"}

    invalid_by_status = {i["address"]: i["status"] for i in body["invalid"]}
    assert invalid_by_status["stop a"] == "DUPLICATE_ADDRESS"
    assert invalid_by_status["Unknown Place"] == "INVALID_ADDRESS"
    assert invalid_by_status[""] == "EMPTY_ADDRESS"
    assert invalid_by_status["Ab"] == "TOO_SHORT"
