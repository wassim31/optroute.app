import time

from app.cache import InMemoryCache
from app.matrix import MatrixService
from app.matrix.provider import MatrixProvider


class FakeProvider(MatrixProvider):
    """Deterministic provider that records every call it receives.

    Returns distinguishable duration/distance matrices so callers can verify
    both are propagated correctly."""

    def __init__(self):
        self.calls = 0

    def compute_matrix(self, coordinates):
        self.calls += 1
        n = len(coordinates)
        durations = [
            [0.0 if i == j else abs(i - j) * 10.0 for j in range(n)]
            for i in range(n)
        ]
        distances = [
            [0.0 if i == j else abs(i - j) * 100.0 for j in range(n)]
            for i in range(n)
        ]
        return durations, distances


def _grid_coordinates(n):
    return [(float(i), float(i)) for i in range(n)]


def test_matrix_is_nxn_and_correct():
    provider = FakeProvider()
    service = MatrixService(provider, cache=InMemoryCache())

    coordinates = _grid_coordinates(5)
    duration_matrix, distance_matrix = service.compute_matrix(coordinates)

    assert len(duration_matrix) == 5
    assert all(len(row) == 5 for row in duration_matrix)
    assert duration_matrix[0][0] == 0.0
    assert duration_matrix[1][3] == 20.0

    assert len(distance_matrix) == 5
    assert all(len(row) == 5 for row in distance_matrix)
    assert distance_matrix[0][0] == 0.0
    assert distance_matrix[1][3] == 200.0


def test_caching_avoids_recomputation():
    provider = FakeProvider()
    service = MatrixService(provider, cache=InMemoryCache())

    coordinates = _grid_coordinates(10)
    service.compute_matrix(coordinates)
    service.compute_matrix(coordinates)

    assert provider.calls == 1


def test_100_node_matrix_is_fast():
    provider = FakeProvider()
    service = MatrixService(provider, cache=InMemoryCache())

    coordinates = _grid_coordinates(100)

    start = time.monotonic()
    duration_matrix, distance_matrix = service.compute_matrix(coordinates)
    elapsed = time.monotonic() - start

    assert len(duration_matrix) == 100
    assert len(distance_matrix) == 100
    assert elapsed < 5


def test_osrm_provider_chunks_large_matrices():
    from app.matrix.provider import OSRMProvider

    class RecordingProvider(OSRMProvider):
        def __init__(self):
            super().__init__(chunk_size=2)
            self.requests = []

        def _table_request(self, coordinates, sources, destinations):
            self.requests.append((tuple(sources), tuple(destinations)))
            durations = [[float(i * 10 + j) for j in destinations] for i in sources]
            distances = [[float(i * 100 + j) for j in destinations] for i in sources]
            return durations, distances

    provider = RecordingProvider()
    coordinates = _grid_coordinates(5)
    duration_matrix, distance_matrix = provider.compute_matrix(coordinates)

    assert len(duration_matrix) == 5
    assert all(len(row) == 5 for row in duration_matrix)
    assert len(distance_matrix) == 5
    assert all(len(row) == 5 for row in distance_matrix)
    # 5 nodes with chunk_size=2 -> 3x3 blocks of source/destination chunks
    assert len(provider.requests) == 9
    # spot-check values assembled from a non-first block
    assert duration_matrix[4][4] == 4 * 10 + 4
    assert distance_matrix[4][4] == 4 * 100 + 4


def test_osrm_provider_requests_duration_and_distance_annotations():
    from app.matrix.provider import OSRMProvider

    class RecordingSession:
        def __init__(self):
            self.params = None

        def get(self, url, params=None, timeout=None):
            self.params = params

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    n = len(coordinates)
                    return {
                        "durations": [[0.0] * n for _ in range(n)],
                        "distances": [[0.0] * n for _ in range(n)],
                    }

            return Response()

    session = RecordingSession()
    provider = OSRMProvider(session=session)
    coordinates = _grid_coordinates(3)
    provider.compute_matrix(coordinates)

    assert session.params["annotations"] == "duration,distance"


def test_google_distance_matrix_requests_live_traffic():
    from app.matrix.provider import GoogleDistanceMatrixProvider

    class RecordingSession:
        def __init__(self):
            self.requests = []

        def get(self, url, params=None, timeout=None):
            self.requests.append(params)
            origins = params["origins"].split("|")
            destinations = params["destinations"].split("|")

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": "OK",
                        "rows": [
                            {
                                "elements": [
                                    {
                                        "status": "OK",
                                        "distance": {"value": 100.0},
                                        "duration": {"value": 50.0},
                                        "duration_in_traffic": {"value": 80.0},
                                    }
                                    for _ in destinations
                                ]
                            }
                            for _ in origins
                        ],
                    }

            return Response()

    session = RecordingSession()
    provider = GoogleDistanceMatrixProvider(api_key="test-key", session=session)
    coordinates = _grid_coordinates(3)
    duration_matrix, distance_matrix = provider.compute_matrix(coordinates)

    assert len(duration_matrix) == 3
    assert all(len(row) == 3 for row in duration_matrix)
    assert len(distance_matrix) == 3
    # duration_in_traffic is preferred over the traffic-free duration.
    assert duration_matrix[0][1] == 80.0
    assert distance_matrix[0][1] == 100.0

    assert session.requests[0]["departure_time"] == "now"
    assert session.requests[0]["traffic_model"] == "best_guess"
    assert session.requests[0]["key"] == "test-key"


def test_fallback_matrix_provider_uses_fallback_on_primary_error():
    from app.matrix.provider import FallbackMatrixProvider

    class FailingProvider(MatrixProvider):
        def compute_matrix(self, coordinates):
            raise RuntimeError("primary unavailable")

    fallback = FakeProvider()
    provider = FallbackMatrixProvider(FailingProvider(), fallback)
    coordinates = _grid_coordinates(3)

    duration_matrix, distance_matrix = provider.compute_matrix(coordinates)

    assert fallback.calls == 1
    assert duration_matrix[0][1] == 10.0


def test_fallback_matrix_provider_uses_primary_on_success():
    from app.matrix.provider import FallbackMatrixProvider

    primary = FakeProvider()
    fallback = FakeProvider()
    provider = FallbackMatrixProvider(primary, fallback)
    coordinates = _grid_coordinates(3)

    provider.compute_matrix(coordinates)

    assert primary.calls == 1
    assert fallback.calls == 0


def test_google_distance_matrix_chunks_large_requests():
    from app.matrix.provider import GoogleDistanceMatrixProvider

    class RecordingSession:
        def __init__(self):
            self.requests = []

        def get(self, url, params=None, timeout=None):
            self.requests.append(params)
            origins = params["origins"].split("|")
            destinations = params["destinations"].split("|")

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {
                        "status": "OK",
                        "rows": [
                            {
                                "elements": [
                                    {
                                        "status": "OK",
                                        "distance": {"value": 100.0},
                                        "duration": {"value": 50.0},
                                        "duration_in_traffic": {"value": 80.0},
                                    }
                                    for _ in destinations
                                ]
                            }
                            for _ in origins
                        ],
                    }

            return Response()

    session = RecordingSession()
    provider = GoogleDistanceMatrixProvider(api_key="test-key", session=session)
    coordinates = _grid_coordinates(11)
    duration_matrix, distance_matrix = provider.compute_matrix(coordinates)

    assert len(duration_matrix) == 11
    assert all(len(row) == 11 for row in duration_matrix)
    assert len(distance_matrix) == 11
    # 11 nodes -> Google's 100-element limit forces multiple requests.
    assert len(session.requests) > 1
    for params in session.requests:
        origins = params["origins"].split("|")
        destinations = params["destinations"].split("|")
        assert len(origins) * len(destinations) <= GoogleDistanceMatrixProvider.MAX_ELEMENTS
        assert len(origins) <= GoogleDistanceMatrixProvider.MAX_DIMENSION
        assert len(destinations) <= GoogleDistanceMatrixProvider.MAX_DIMENSION
