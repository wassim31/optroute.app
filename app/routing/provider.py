"""Routing providers: turn an ordered list of coordinates into real road geometry."""

from abc import ABC, abstractmethod
from typing import List

import requests

from .models import Coordinate, RouteGeometry, RouteSegment


class RoutingProvider(ABC):
    @abstractmethod
    def get_route(self, coordinates: List[Coordinate]) -> RouteGeometry:
        """Returns road geometry + per-segment distance/duration for the
        ordered list of (lat, lon) waypoints."""
        ...


class OSRMRoutingProvider(RoutingProvider):
    """OSRM /route service."""

    def __init__(self, base_url: str = "http://router.project-osrm.org", profile: str = "driving", session=None):
        self._base_url = base_url.rstrip("/")
        self._profile = profile
        self._session = session or requests.Session()

    def get_route(self, coordinates: List[Coordinate]) -> RouteGeometry:
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        url = f"{self._base_url}/route/v1/{self._profile}/{coords_str}"
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}

        response = self._session.get(url, params=params, timeout=30)
        response.raise_for_status()
        route = response.json()["routes"][0]

        polyline = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
        segments = [RouteSegment(distance=leg["distance"], duration=leg["duration"]) for leg in route["legs"]]

        return RouteGeometry(
            polyline=polyline,
            distance=route["distance"],
            duration=route["duration"],
            segments=segments,
        )
