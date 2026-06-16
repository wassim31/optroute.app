"""Travel-time matrix computation with caching."""

import hashlib
import json
from typing import List, Optional, Tuple

from ..cache import CacheBackend, InMemoryCache
from .provider import MatrixProvider

CACHE_KEY_PREFIX = "matrix:"


class MatrixService:
    def __init__(self, provider: MatrixProvider, cache: Optional[CacheBackend] = None):
        self._provider = provider
        self._cache = cache or InMemoryCache()

    def compute_matrix(self, coordinates: List[Tuple[float, float]]) -> Tuple[List[List[float]], List[List[float]]]:
        """Returns (duration_matrix, distance_matrix) for the given coordinates,
        caching the result so repeated requests for the same coordinate set
        avoid recomputation."""
        key = self._cache_key(coordinates)
        cached = self._cache.get(key)
        if cached is not None:
            return cached["duration"], cached["distance"]

        duration_matrix, distance_matrix = self._provider.compute_matrix(coordinates)
        self._cache.set(key, {"duration": duration_matrix, "distance": distance_matrix})
        return duration_matrix, distance_matrix

    @staticmethod
    def _cache_key(coordinates: List[Tuple[float, float]]) -> str:
        serialized = json.dumps(coordinates)
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        return f"{CACHE_KEY_PREFIX}{digest}"
