from app.addresses import normalize_address, validate_addresses
from app.addresses.service import (
    STATUS_DUPLICATE,
    STATUS_EMPTY,
    STATUS_INVALID_ADDRESS,
    STATUS_TOO_SHORT,
)


class FakeGeocodingService:
    KNOWN = {
        "depot hq": (48.85, 2.35),
        "eiffel tower paris": (48.8584, 2.2945),
        "la defense paris": (48.8918, 2.2360),
    }

    def __init__(self):
        self.calls = []

    def geocode_batch(self, addresses):
        self.calls.append(list(addresses))
        results = []
        for address in addresses:
            coords = self.KNOWN.get(address.lower())
            if coords is None:
                results.append({"address": address, "lat": None, "lon": None})
            else:
                results.append({"address": address, "lat": coords[0], "lon": coords[1]})
        return results


def test_normalize_collapses_whitespace():
    assert normalize_address("   Eiffel  Tower   Paris  ") == "Eiffel Tower Paris"


def test_valid_depot_and_stops_are_geocoded():
    geocoding = FakeGeocodingService()
    result = validate_addresses("Depot HQ", ["Eiffel Tower Paris", "La Defense Paris"], geocoding)

    assert len(result.valid) == 3
    assert len(result.invalid) == 0
    assert result.valid[0].role == "depot"
    assert result.valid[0].address == "Depot HQ"
    assert result.valid[1].role == "stop"


def test_empty_and_too_short_addresses_are_rejected():
    geocoding = FakeGeocodingService()
    result = validate_addresses("Depot HQ", ["", "Ab"], geocoding)

    statuses = {a.address: a.status for a in result.invalid}
    assert statuses[""] == STATUS_EMPTY
    assert statuses["Ab"] == STATUS_TOO_SHORT
    # Only the depot should reach the geocoder.
    assert geocoding.calls == [["Depot HQ"]]


def test_duplicate_addresses_are_rejected():
    geocoding = FakeGeocodingService()
    result = validate_addresses("Depot HQ", ["Eiffel Tower Paris", "eiffel  tower   paris"], geocoding)

    assert len(result.valid) == 2  # depot + first occurrence
    assert len(result.invalid) == 1
    assert result.invalid[0].status == STATUS_DUPLICATE
    assert result.invalid[0].role == "stop"


def test_unresolvable_address_is_invalid_and_not_in_valid_list():
    geocoding = FakeGeocodingService()
    result = validate_addresses("Depot HQ", ["Nowhere Land"], geocoding)

    assert len(result.valid) == 1  # only depot
    assert len(result.invalid) == 1
    assert result.invalid[0].status == STATUS_INVALID_ADDRESS
    assert result.invalid[0].address == "Nowhere Land"


def test_100_addresses_processed():
    geocoding = FakeGeocodingService()
    stops = [f"{i} Main Street, Paris" for i in range(100)]
    # Make all 100 resolvable.
    geocoding.KNOWN = {**geocoding.KNOWN, **{s.lower(): (48.0, 2.0) for s in stops}}

    result = validate_addresses("Depot HQ", stops, geocoding)

    assert len(result.valid) == 101
    assert len(result.invalid) == 0
