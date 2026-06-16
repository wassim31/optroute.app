"""Address input validation, normalization, deduplication and geocoding
(specs/08_address_input.md).

Pipeline: validate -> normalize -> deduplicate -> geocode -> coordinates
"""

import re
from typing import List

from .models import AddressValidationResult, InvalidAddress, ValidAddress

MIN_ADDRESS_LENGTH = 5

STATUS_EMPTY = "EMPTY_ADDRESS"
STATUS_TOO_SHORT = "TOO_SHORT"
STATUS_DUPLICATE = "DUPLICATE_ADDRESS"
STATUS_INVALID_ADDRESS = "INVALID_ADDRESS"

DEPOT_ROLE = "depot"
STOP_ROLE = "stop"


def normalize_address(address: str) -> str:
    """Collapses whitespace and trims, per specs/08_address_input.md."""
    return re.sub(r"\s+", " ", address.strip())


def validate_addresses(depot: str, stops: List[str], geocoding_service) -> AddressValidationResult:
    result = AddressValidationResult()

    entries = [(DEPOT_ROLE, depot)] + [(STOP_ROLE, stop) for stop in stops]
    candidates = []  # (role, normalized_address)
    seen: set = set()

    for role, raw_address in entries:
        normalized = normalize_address(raw_address)

        if not normalized:
            result.invalid.append(InvalidAddress(address=raw_address, status=STATUS_EMPTY, role=role))
            continue
        if len(normalized) < MIN_ADDRESS_LENGTH:
            result.invalid.append(InvalidAddress(address=normalized, status=STATUS_TOO_SHORT, role=role))
            continue

        key = normalized.lower()
        if key in seen:
            result.invalid.append(InvalidAddress(address=normalized, status=STATUS_DUPLICATE, role=role))
            continue

        seen.add(key)
        candidates.append((role, normalized))

    if candidates:
        geocoded = geocoding_service.geocode_batch([address for _, address in candidates])
        for (role, address), geo in zip(candidates, geocoded):
            if geo["lat"] is None or geo["lon"] is None:
                result.invalid.append(InvalidAddress(address=address, status=STATUS_INVALID_ADDRESS, role=role))
            else:
                result.valid.append(ValidAddress(address=address, lat=geo["lat"], lon=geo["lon"], role=role))

    return result
