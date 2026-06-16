"""OR-Tools VRP solver for a single vehicle.

Goal: visit all stops with one vehicle, respecting each stop's time window
and the vehicle's capacity and shift, while minimizing total distance + total
travel time (the travel-time matrix is expected to reflect real-time traffic,
so this also favors routes that avoid current congestion).

Time windows are always hard constraints: if a stop's window can't be
reached, `solve()` raises.
"""

from typing import List

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .models import Route, RouteStop, Stop, Vehicle, VRPSolution

DEPOT = 0


class VRPSolver:
    def __init__(
        self,
        time_matrix: List[List[float]],
        distance_matrix: List[List[float]],
        stops: List[Stop],
        vehicles: List[Vehicle],
        time_limit_seconds: int = 10,
    ):
        """time_matrix is travel time in seconds, distance_matrix is travel
        distance in meters. Both are (1 + len(stops)) x (1 + len(stops)),
        node 0 = depot. stops[i] corresponds to matrix node i + 1."""
        self._time_matrix = time_matrix
        self._distance_matrix = distance_matrix
        self._stops = stops
        self._vehicles = vehicles
        self._time_limit_seconds = time_limit_seconds

    def solve(self) -> VRPSolution:
        num_nodes = len(self._time_matrix)
        manager = pywrapcp.RoutingIndexManager(num_nodes, len(self._vehicles), DEPOT)
        routing = pywrapcp.RoutingModel(manager)

        service_times = [0] + [stop.service_time for stop in self._stops]
        time_windows = [(0, max(v.shift[1] for v in self._vehicles))]
        time_windows += [stop.time_window for stop in self._stops]
        demands = [0] + [stop.demand for stop in self._stops]

        time_transit_index = self._register_time_callback(routing, manager, service_times)
        distance_transit_index = self._register_distance_callback(routing, manager)

        self._configure_cost(routing, manager, service_times)

        max_shift_end = max(v.shift[1] for v in self._vehicles)
        routing.AddDimension(time_transit_index, max_shift_end, max_shift_end, False, "Time")
        time_dimension = routing.GetDimensionOrDie("Time")

        for node, (start, end) in enumerate(time_windows):
            if node == DEPOT:
                continue
            index = manager.NodeToIndex(node)
            time_dimension.CumulVar(index).SetRange(start, end)

        for vehicle_id, vehicle in enumerate(self._vehicles):
            start_index = routing.Start(vehicle_id)
            end_index = routing.End(vehicle_id)
            time_dimension.CumulVar(start_index).SetRange(*vehicle.shift)
            time_dimension.CumulVar(end_index).SetRange(*vehicle.shift)
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(start_index))
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(end_index))

        demand_callback_index = routing.RegisterUnaryTransitCallback(
            lambda index: demands[manager.IndexToNode(index)]
        )
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [vehicle.capacity for vehicle in self._vehicles],
            True,
            "Capacity",
        )

        total_distance_upper_bound = int(sum(sum(row) for row in self._distance_matrix)) + 1
        routing.AddDimension(distance_transit_index, 0, total_distance_upper_bound, True, "Distance")
        distance_dimension = routing.GetDimensionOrDie("Distance")

        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = self._time_limit_seconds

        solution = routing.SolveWithParameters(search_params)
        if not solution:
            raise RuntimeError("No feasible VRP solution found")

        return self._build_solution(manager, routing, solution, time_dimension, distance_dimension)

    def _configure_cost(self, routing, manager, service_times):
        def cost_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            distance = self._distance_matrix[from_node][to_node]
            time = self._time_matrix[from_node][to_node] + service_times[from_node]
            return int(round(distance)) + int(round(time))

        cost_index = routing.RegisterTransitCallback(cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(cost_index)

    def _register_time_callback(self, routing, manager, service_times):
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(self._time_matrix[from_node][to_node])) + service_times[from_node]

        return routing.RegisterTransitCallback(time_callback)

    def _register_distance_callback(self, routing, manager):
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(self._distance_matrix[from_node][to_node]))

        return routing.RegisterTransitCallback(distance_callback)

    def _build_solution(self, manager, routing, solution, time_dimension, distance_dimension) -> VRPSolution:
        routes = []
        total_distance = 0.0
        total_duration = 0
        vehicles_used = 0

        for vehicle_id, vehicle in enumerate(self._vehicles):
            index = routing.Start(vehicle_id)
            route_stops: List[RouteStop] = []

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != DEPOT:
                    arrival = solution.Value(time_dimension.CumulVar(index))
                    stop = self._stops[node - 1]
                    route_stops.append(
                        RouteStop(
                            stop_id=stop.id,
                            arrival_time=arrival,
                            departure_time=arrival + stop.service_time,
                        )
                    )
                index = solution.Value(routing.NextVar(index))

            if not route_stops:
                continue

            vehicles_used += 1
            end_index = routing.End(vehicle_id)
            start_index = routing.Start(vehicle_id)
            distance = solution.Value(distance_dimension.CumulVar(end_index))
            duration = solution.Value(time_dimension.CumulVar(end_index)) - solution.Value(
                time_dimension.CumulVar(start_index)
            )

            routes.append(Route(vehicle_id=vehicle.id, stops=route_stops, distance=distance, duration=duration))
            total_distance += distance
            total_duration += duration

        return VRPSolution(
            routes=routes,
            total_distance=total_distance,
            total_duration=total_duration,
            vehicles_used=vehicles_used,
        )
