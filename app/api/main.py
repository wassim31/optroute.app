"""FastAPI app exposing POST /optimize."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from ..addresses import validate_addresses
from ..cache import build_cache
from ..geocoding import GeocodingService, NominatimProvider
from ..matrix import FallbackMatrixProvider, GoogleDistanceMatrixProvider, MatrixService, OSRMProvider
from ..routing import OSRMRoutingProvider, RoutingService
from ..vrp import VRPSolver
from .pipeline import run_optimize_pipeline
from .schemas import (
    AddressValidationRequest,
    AddressValidationResponse,
    InvalidAddressOut,
    OptimizeRequest,
    OptimizeResponse,
    ValidAddressOut,
)

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def _default_matrix_provider():
    """Use live-traffic-aware Google Distance Matrix when an API key is
    configured, falling back to OSRM (no traffic data) if that API is
    unavailable (e.g. not enabled for the project) or no key is set."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if api_key:
        return FallbackMatrixProvider(GoogleDistanceMatrixProvider(api_key), OSRMProvider())
    return OSRMProvider()


def create_app(geocoding_service=None, matrix_service=None, routing_service=None, vrp_solver_factory=None) -> FastAPI:
    redis_url = os.environ.get("REDIS_URL")
    geocoding_service = geocoding_service or GeocodingService(NominatimProvider(), cache=build_cache(redis_url))
    matrix_service = matrix_service or MatrixService(_default_matrix_provider(), cache=build_cache(redis_url))
    routing_service = routing_service or RoutingService(OSRMRoutingProvider())
    vrp_solver_factory = vrp_solver_factory or (
        lambda time_matrix, distance_matrix, stops, vehicles: VRPSolver(time_matrix, distance_matrix, stops, vehicles)
    )

    app = FastAPI(title="route.me")

    @app.post("/optimize", response_model=OptimizeResponse)
    def optimize(request: OptimizeRequest) -> OptimizeResponse:
        try:
            return run_optimize_pipeline(request, geocoding_service, matrix_service, routing_service, vrp_solver_factory)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.get("/config")
    def config() -> dict:
        return {
            "googleMapsApiKey": os.environ.get("GOOGLE_MAPS_API_KEY", ""),
            "googleMapsMapId": os.environ.get("GOOGLE_MAPS_MAP_ID") or "DEMO_MAP_ID",
        }

    @app.post("/addresses/validate", response_model=AddressValidationResponse)
    def validate(request: AddressValidationRequest) -> AddressValidationResponse:
        result = validate_addresses(request.depot, request.stops, geocoding_service)
        return AddressValidationResponse(
            valid=[ValidAddressOut(address=a.address, lat=a.lat, lon=a.lon, role=a.role) for a in result.valid],
            invalid=[InvalidAddressOut(address=a.address, status=a.status, role=a.role) for a in result.invalid],
        )

    static_dir = Path(__file__).resolve().parent.parent / "frontend" / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


app = create_app()
