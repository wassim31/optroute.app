import itertools

import pytest

from app.vrp import Stop, Vehicle, VRPSolver

# 1 depot (node 0) + 8 stops (nodes 1-8), travel time in minutes.
TIME_MATRIX = [
    [0, 10, 15, 20, 25, 30, 18, 22, 12],
    [10, 0, 12, 18, 22, 28, 14, 20, 10],
    [15, 12, 0, 8, 16, 22, 10, 15, 9],
    [20, 18, 8, 0, 10, 18, 8, 12, 14],
    [25, 22, 16, 10, 0, 12, 14, 10, 18],
    [30, 28, 22, 18, 12, 0, 20, 8, 22],
    [18, 14, 10, 8, 14, 20, 0, 9, 11],
    [22, 20, 15, 12, 10, 8, 9, 0, 14],
    [12, 10, 9, 14, 18, 22, 11, 14, 0],
]


def _stops(time_window=(0, 1440), demand=0):
    return [Stop(id=f"S{i}", demand=demand, time_window=time_window) for i in range(1, 9)]


def test_all_stops_assigned_to_single_vehicle():
    stops = _stops()
    vehicles = [Vehicle(id="v1", capacity=100, shift=(0, 300))]

    solver = VRPSolver(TIME_MATRIX, TIME_MATRIX, stops, vehicles, time_limit_seconds=5)
    solution = solver.solve()

    assert solution.vehicles_used == 1
    assert len(solution.routes) == 1
    visited = {rs.stop_id for rs in solution.routes[0].stops}
    assert visited == {stop.id for stop in stops}


def test_time_windows_are_respected():
    stops = _stops()
    # Force stop S1 to only be reachable late in the shift.
    stops[0] = Stop(id="S1", demand=0, time_window=(100, 150))
    vehicles = [Vehicle(id="v1", capacity=100, shift=(0, 300))]

    solver = VRPSolver(TIME_MATRIX, TIME_MATRIX, stops, vehicles, time_limit_seconds=5)
    solution = solver.solve()

    for route in solution.routes:
        for route_stop in route.stops:
            if route_stop.stop_id == "S1":
                assert 100 <= route_stop.arrival_time <= 150


def test_time_window_infeasible_raises():
    # The only route to S1 (direct from depot, or via S2) arrives at t=10 or
    # t=20, both after S1's window of (0, 5).
    matrix = [
        [0, 50, 10],
        [50, 0, 10],
        [10, 10, 0],
    ]
    stops = [Stop(id="S1", demand=0, time_window=(0, 5)), Stop(id="S2", demand=0, time_window=(0, 200))]
    vehicles = [Vehicle(id="v1", capacity=10, shift=(0, 200))]

    solver = VRPSolver(matrix, matrix, stops, vehicles, time_limit_seconds=5)
    with pytest.raises(RuntimeError):
        solver.solve()


def test_capacity_exceeded_raises():
    # Total demand 80, but the single vehicle can only carry 30.
    stops = _stops(demand=10)
    vehicles = [Vehicle(id="v1", capacity=30, shift=(0, 300))]

    solver = VRPSolver(TIME_MATRIX, TIME_MATRIX, stops, vehicles, time_limit_seconds=5)
    with pytest.raises(RuntimeError):
        solver.solve()


def test_minimizes_combined_distance_and_time():
    # depot=0, stops S1-S3 = nodes 1-3. Asymmetric matrices so tour order matters.
    time_matrix = [
        [0, 10, 20, 30],
        [12, 0, 15, 25],
        [22, 17, 0, 10],
        [32, 27, 12, 0],
    ]
    distance_matrix = [
        [0, 100, 200, 300],
        [120, 0, 150, 250],
        [220, 170, 0, 100],
        [320, 270, 120, 0],
    ]
    stops = [Stop(id=f"S{i}", demand=0, time_window=(0, 10000)) for i in range(1, 4)]
    vehicles = [Vehicle(id="v1", capacity=100, shift=(0, 10000))]

    solver = VRPSolver(time_matrix, distance_matrix, stops, vehicles, time_limit_seconds=5)
    solution = solver.solve()

    combined = [[time_matrix[i][j] + distance_matrix[i][j] for j in range(4)] for i in range(4)]

    def tour_cost(order):
        cost = combined[0][order[0]]
        for a, b in zip(order, order[1:]):
            cost += combined[a][b]
        cost += combined[order[-1]][0]
        return cost

    best_cost = min(tour_cost(p) for p in itertools.permutations([1, 2, 3]))

    visited_order = [int(rs.stop_id[1:]) for rs in solution.routes[0].stops]
    assert tour_cost(visited_order) == best_cost
