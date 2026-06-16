"""Batch geocoding service with caching and deduplication."""

from typing import List, Optional

from ..cache import CacheBackend, InMemoryCache
from .provider import GeocodingProvider

CACHE_KEY_PREFIX = "geocode:"


class GeocodingService:
    def __init__(self, provider: GeocodingProvider, cache: Optional[CacheBackend] = None):
        self._provider = provider
        self._cache = cache or InMemoryCache()

    def geocode_batch(self, addresses: List[str]) -> List[dict]:
        """Resolves a list of addresses to {address, lat, lon}, in input order.

        Duplicate addresses (after normalization) are only resolved once, and
        results are cached so repeated calls avoid hitting the provider again.
        """
        resolved: dict = {}

        for address in addresses:
            key = self._normalize(address)
            if key in resolved:
                continue

            cached = self._cache.get(self._cache_key(key))
            if cached is not None:
                resolved[key] = cached
                continue

            coords = self._provider.geocode(address)
            value = {"lat": coords[0], "lon": coords[1]} if coords else {"lat": None, "lon": None}
            self._cache.set(self._cache_key(key), value)
            resolved[key] = value

        return [
            {"address": address, "lat": resolved[self._normalize(address)]["lat"], "lon": resolved[self._normalize(address)]["lon"]}
            for address in addresses
        ]

    @staticmethod
    def _normalize(address: str) -> str:
        return " ".join(address.strip().lower().split())

    @staticmethod
    def _cache_key(normalized_address: str) -> str:
        return f"{CACHE_KEY_PREFIX}{normalized_address}"
