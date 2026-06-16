"""Matrix providers: turn a list of (lat, lon) coordinates into an NxN travel-time matrix."""

from abc import ABC, abstractmethod
from typing import List, Sequence, Tuple

import requests

Coordinate = Tuple[float, float]


class MatrixProvider(ABC):
    @abstractmethod
    def compute_matrix(self, coordinates: List[Coordinate]) -> "tuple[List[List[float]], List[List[float]]]":
        """Returns (duration_matrix, distance_matrix), where
        duration_matrix[i][j] = travel time (seconds) and
        distance_matrix[i][j] = travel distance (meters) from coordinates[i]
        to coordinates[j]."""
        ...


class OSRMProvider(MatrixProvider):
    """OSRM /table service. Requests are chunked to stay within OSRM's
    default max-table-size limit, so matrices larger than `chunk_size`
    (e.g. up to 500 nodes) are assembled from multiple sub-requests."""

    def __init__(self, base_url: str = "http://router.project-osrm.org", profile: str = "driving",
                 session=None, chunk_size: int = 100):
        self._base_url = base_url.rstrip("/")
        self._profile = profile
        self._session = session or requests.Session()
        self._chunk_size = chunk_size

    def compute_matrix(self, coordinates: List[Coordinate]) -> "tuple[List[List[float]], List[List[float]]]":
        n = len(coordinates)
        if n == 0:
            return [], []
        if n <= self._chunk_size:
            return self._table_request(coordinates, list(range(n)), list(range(n)))

        indices = list(range(n))
        durations = [[0.0] * n for _ in range(n)]
        distances = [[0.0] * n for _ in range(n)]
        for i_start in range(0, n, self._chunk_size):
            sources = indices[i_start:i_start + self._chunk_size]
            for j_start in range(0, n, self._chunk_size):
                destinations = indices[j_start:j_start + self._chunk_size]
                duration_block, distance_block = self._table_request(coordinates, sources, destinations)
                for bi, i in enumerate(sources):
                    for bj, j in enumerate(destinations):
                        durations[i][j] = duration_block[bi][bj]
                        distances[i][j] = distance_block[bi][bj]
        return durations, distances

    def _table_request(self, coordinates: List[Coordinate], sources: Sequence[int],
                        destinations: Sequence[int]) -> "tuple[List[List[float]], List[List[float]]]":
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        url = f"{self._base_url}/table/v1/{self._profile}/{coords_str}"
        params = {
            "annotations": "duration,distance",
            "sources": ";".join(str(i) for i in sources),
            "destinations": ";".join(str(j) for j in destinations),
        }
        response = self._session.get(url, params=params, timeout=30)
        response.raise_for_status()
        body = response.json()
        return body["durations"], body["distances"]


class GoogleDistanceMatrixProvider(MatrixProvider):
    """Google Distance Matrix API, requesting live-traffic-adjusted durations
    (departure_time=now, traffic_model=best_guess).

    Requests are chunked to respect Google's per-request limits: at most 25
    origins/destinations and 100 origin x destination elements per request."""

    BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
    MAX_ELEMENTS = 100
    MAX_DIMENSION = 25

    def __init__(self, api_key: str, session=None):
        self._api_key = api_key
        self._session = session or requests.Session()

    def compute_matrix(self, coordinates: List[Coordinate]) -> "tuple[List[List[float]], List[List[float]]]":
        n = len(coordinates)
        if n == 0:
            return [], []

        source_chunk_size = max(1, min(self.MAX_DIMENSION, self.MAX_ELEMENTS // n))
        durations = [[0.0] * n for _ in range(n)]
        distances = [[0.0] * n for _ in range(n)]

        for i_start in range(0, n, source_chunk_size):
            sources = list(range(i_start, min(i_start + source_chunk_size, n)))
            for j_start in range(0, n, self.MAX_DIMENSION):
                destinations = list(range(j_start, min(j_start + self.MAX_DIMENSION, n)))
                duration_block, distance_block = self._matrix_request(coordinates, sources, destinations)
                for bi, i in enumerate(sources):
                    for bj, j in enumerate(destinations):
                        durations[i][j] = duration_block[bi][bj]
                        distances[i][j] = distance_block[bi][bj]
        return durations, distances

    def _matrix_request(self, coordinates: List[Coordinate], sources: Sequence[int],
                         destinations: Sequence[int]) -> "tuple[List[List[float]], List[List[float]]]":
        origins = "|".join(f"{coordinates[i][0]},{coordinates[i][1]}" for i in sources)
        dests = "|".join(f"{coordinates[j][0]},{coordinates[j][1]}" for j in destinations)
        params = {
            "origins": origins,
            "destinations": dests,
            "departure_time": "now",
            "traffic_model": "best_guess",
            "key": self._api_key,
        }
        response = self._session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "OK":
            raise RuntimeError(f"Google Distance Matrix error: {body.get('status')} {body.get('error_message', '')}")

        durations: List[List[float]] = []
        distances: List[List[float]] = []
        for row in body["rows"]:
            duration_row, distance_row = [], []
            for element in row["elements"]:
                if element.get("status") != "OK":
                    raise RuntimeError(f"Google Distance Matrix element error: {element.get('status')}")
                duration = element.get("duration_in_traffic", element["duration"])
                duration_row.append(float(duration["value"]))
                distance_row.append(float(element["distance"]["value"]))
            durations.append(duration_row)
            distances.append(distance_row)
        return durations, distances


class FallbackMatrixProvider(MatrixProvider):
    """Tries `primary` first (e.g. a live-traffic provider) and falls back to
    `fallback` if the primary raises, so the app keeps working even when the
    primary's API isn't available (e.g. not enabled/billed yet)."""

    def __init__(self, primary: MatrixProvider, fallback: MatrixProvider):
        self._primary = primary
        self._fallback = fallback

    def compute_matrix(self, coordinates: List[Coordinate]) -> "tuple[List[List[float]], List[List[float]]]":
        try:
            return self._primary.compute_matrix(coordinates)
        except (RuntimeError, requests.RequestException):
            return self._fallback.compute_matrix(coordinates)
