"""Cache backends shared across services (Redis with in-memory fallback)."""

import json
from abc import ABC, abstractmethod
from typing import Optional


class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[dict]:
        ...

    @abstractmethod
    def set(self, key: str, value: dict) -> None:
        ...


class InMemoryCache(CacheBackend):
    def __init__(self):
        self._store: dict = {}

    def get(self, key: str) -> Optional[dict]:
        return self._store.get(key)

    def set(self, key: str, value: dict) -> None:
        self._store[key] = value


class RedisCache(CacheBackend):
    def __init__(self, client, ttl_seconds: Optional[int] = None):
        self._client = client
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[dict]:
        raw = self._client.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict) -> None:
        self._client.set(key, json.dumps(value), ex=self._ttl)


def build_cache(redis_url: Optional[str] = None, ttl_seconds: Optional[int] = None) -> CacheBackend:
    """Returns a RedisCache if redis_url is reachable, else falls back to InMemoryCache."""
    if redis_url:
        try:
            import redis

            client = redis.from_url(redis_url)
            client.ping()
            return RedisCache(client, ttl_seconds=ttl_seconds)
        except Exception:
            pass
    return InMemoryCache()
