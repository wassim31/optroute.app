"""Orchestrates the full pipeline: geocode -> matrix -> solve -> route."""

from typing import List

from ..routing.models import Coordinate
from ..routing.service import RoutingService
from ..vrp.models import Stop, Vehicle
from .schemas import LocationIn, OptimizeRequest, OptimizeResponse, RouteGeometryOut, RouteOut, RouteSegmentOut, StopETAOut


def _resolve_coordinates(locations: List[LocationIn], geocoding_service) -> List[Coordinate]:
    """Returns one (lat, lon) per location, geocoding any that only have an address."""
    addresses = [loc.address for loc in locations if loc.lat is None or loc.lon is None]

    geocoded = {}
    if addresses:
        for address, result in zip(addresses, geocoding_service.geocode_batch(addresses)):
            if result["lat"] is None or result["lon"] is None:
                raise ValueError(f"could not geocode address: {address!r}")
            geocoded[address] = (result["lat"], result["lon"])

    coordinates = []
    for loc in locations:
        if loc.lat is not None and loc.lon is not None:
            coordinates.append((loc.lat, loc.lon))
        else:
            coordinates.append(geocoded[loc.address])
    return coordinates


def run_optimize_pipeline(
    request: OptimizeRequest, geocoding_service, matrix_service, routing_service: RoutingService, vrp_solver_factory
) -> OptimizeResponse:
    locations = [request.depot] + list(request.stops)
    coordinates = _resolve_coordinates(locations, geocoding_service)
    depot_coord, stop_coords = coordinates[0], coordinates[1:]

    time_matrix, distance_matrix = matrix_service.compute_matrix(coordinates)

    vrp_stops = [
        Stop(
            id=stop.id,
            demand=stop.demand,
            time_window=tuple(stop.time_window),
            service_time=stop.service_time,
        )
        for stop in request.stops
    ]
    vrp_vehicles = [Vehicle(id=request.vehicle.id, capacity=request.vehicle.capacity, shift=tuple(request.vehicle.shift))]

    solver = vrp_solver_factory(time_matrix, distance_matrix, vrp_stops, vrp_vehicles)
    solution = solver.solve()

    stop_coordinates = dict(zip((stop.id for stop in request.stops), stop_coords))
    geometries = routing_service.build_routes_for_solution(solution, depot_coord, stop_coordinates)

    routes_out = []
    for route in solution.routes:
        geometry = geometries.get(route.vehicle_id)
        distance, duration, geometry_out = route.distance, route.duration, None

        if geometry and geometry.segments:
            distance, duration = geometry.distance, int(geometry.duration)
            geometry_out = RouteGeometryOut(
                polyline=geometry.polyline,
                segments=[RouteSegmentOut(distance=seg.distance, duration=seg.duration) for seg in geometry.segments],
            )

        routes_out.append(
            RouteOut(
                vehicle_id=route.vehicle_id,
                stops=[rs.stop_id for rs in route.stops],
                stop_etas=[
                    StopETAOut(
                        stop_id=rs.stop_id,
                        arrival_time=rs.arrival_time,
                        departure_time=rs.departure_time,
                    )
                    for rs in route.stops
                ],
                distance=distance,
                duration=duration,
                geometry=geometry_out,
            )
        )

    return OptimizeResponse(routes=routes_out)
