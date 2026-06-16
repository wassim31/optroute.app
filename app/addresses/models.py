"""Data model for address validation/geocoding results."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidAddress:
    address: str
    lat: float
    lon: float
    role: str


@dataclass
class InvalidAddress:
    address: str
    status: str
    role: str


@dataclass
class AddressValidationResult:
    valid: List[ValidAddress] = field(default_factory=list)
    invalid: List[InvalidAddress] = field(default_factory=list)
