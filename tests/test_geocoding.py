from app.geocoding import GeocodingService, InMemoryCache
from app.geocoding.provider import GeocodingProvider


class FakeProvider(GeocodingProvider):
    """Deterministic provider that records every call it receives."""

    def __init__(self):
        self.calls = []

    def geocode(self, address):
        self.calls.append(address)
        seed = sum(ord(c) for c in address)
        return (seed % 90, (seed * 2) % 180)


def test_batch_of_100_addresses_processed_correctly():
    provider = FakeProvider()
    service = GeocodingService(provider, cache=InMemoryCache())

    addresses = [f"{i} Main Street" for i in range(100)]
    results = service.geocode_batch(addresses)

    assert len(results) == 100
    for address, result in zip(addresses, results):
        assert result["address"] == address
        assert isinstance(result["lat"], (int, float))
        assert isinstance(result["lon"], (int, float))


def test_caching_avoids_repeat_provider_calls():
    provider = FakeProvider()
    cache = InMemoryCache()
    service = GeocodingService(provider, cache=cache)

    addresses = ["1 Main Street", "2 Main Street"]
    service.geocode_batch(addresses)
    assert provider.calls == addresses

    # Second call should hit the cache, not the provider again.
    service.geocode_batch(addresses)
    assert provider.calls == addresses


def test_deduplication_within_a_batch():
    provider = FakeProvider()
    service = GeocodingService(provider, cache=InMemoryCache())

    addresses = ["1 Main Street", "1 main street ", "2 Main Street"]
    results = service.geocode_batch(addresses)

    assert provider.calls == ["1 Main Street", "2 Main Street"]
    assert results[0]["lat"] == results[1]["lat"]
    assert results[0]["lon"] == results[1]["lon"]


def test_unresolvable_address_returns_none_coords():
    class EmptyProvider(GeocodingProvider):
        def geocode(self, address):
            return None

    service = GeocodingService(EmptyProvider(), cache=InMemoryCache())
    results = service.geocode_batch(["Nowhere"])

    assert results == [{"address": "Nowhere", "lat": None, "lon": None}]


def test_output_format_matches_spec():
    provider = FakeProvider()
    service = GeocodingService(provider, cache=InMemoryCache())

    results = service.geocode_batch(["1 Main Street"])

    assert set(results[0].keys()) == {"address", "lat", "lon"}
