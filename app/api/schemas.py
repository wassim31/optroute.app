"""Request/response models for POST /optimize (specs/06_api_contracts.md)."""

from typing import List, Optional, Tuple

from pydantic import BaseModel, root_validator

DEFAULT_TIME_WINDOW = (0, 24 * 3600)


class LocationIn(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None

    @root_validator
    def _require_location(cls, values):
        has_coords = values.get("lat") is not None and values.get("lon") is not None
        has_address = bool(values.get("address"))
        if not has_coords and not has_address:
            raise ValueError("either 'lat'/'lon' or 'address' must be provided")
        return values


class StopIn(LocationIn):
    id: str
    time_window: Tuple[int, int] = DEFAULT_TIME_WINDOW
    demand: int = 0
    service_time: int = 0


class VehicleIn(BaseModel):
    id: str
    capacity: int = 0
    shift: Tuple[int, int] = DEFAULT_TIME_WINDOW


class OptimizeRequest(BaseModel):
    depot: LocationIn
    stops: List[StopIn]
    vehicle: VehicleIn = VehicleIn(id="v1", capacity=0, shift=DEFAULT_TIME_WINDOW)

    @root_validator
    def _non_empty(cls, values):
        if not values.get("stops"):
            raise ValueError("'stops' must be a non-empty list")
        return values


class RouteSegmentOut(BaseModel):
    distance: float
    duration: float


class RouteGeometryOut(BaseModel):
    polyline: List[Tuple[float, float]]
    segments: List[RouteSegmentOut]


class StopETAOut(BaseModel):
    stop_id: str
    arrival_time: int
    departure_time: int


class RouteOut(BaseModel):
    vehicle_id: str
    stops: List[str]
    stop_etas: List[StopETAOut]
    distance: float
    duration: int
    geometry: Optional[RouteGeometryOut] = None


class OptimizeResponse(BaseModel):
    routes: List[RouteOut]


class AddressValidationRequest(BaseModel):
    depot: str
    stops: List[str]


class ValidAddressOut(BaseModel):
    address: str
    lat: float
    lon: float
    role: str


class InvalidAddressOut(BaseModel):
    address: str
    status: str
    role: str


class AddressValidationResponse(BaseModel):
    valid: List[ValidAddressOut]
    invalid: List[InvalidAddressOut]
