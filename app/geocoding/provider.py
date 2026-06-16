"""Geocoding providers: turn a raw address string into (lat, lon)."""

import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import requests


class GeocodingProvider(ABC):
    @abstractmethod
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Returns (lat, lon) or None if the address could not be resolved."""
        ...


class NominatimProvider(GeocodingProvider):
    """OpenStreetMap Nominatim geocoder. Respects the 1 req/sec usage policy."""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self, user_agent: str = "route-me-geocoder", session=None, rate_limit_seconds: float = 1.0):
        self._session = session or requests.Session()
        self._user_agent = user_agent
        self._rate_limit_seconds = rate_limit_seconds
        self._last_request_at = 0.0

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        self._throttle()
        response = self._session.get(
            self.BASE_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": self._user_agent},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._rate_limit_seconds:
            time.sleep(self._rate_limit_seconds - elapsed)
        self._last_request_at = time.monotonic()
