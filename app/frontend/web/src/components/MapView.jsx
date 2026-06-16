import { Fragment, useEffect, useMemo } from "react";
import { Map, AdvancedMarker, useMap } from "@vis.gl/react-google-maps";
import Polyline from "./Polyline.jsx";
import { COLORS, splitPolylineIntoLegs, formatETA } from "../lib/routeGeometry.js";

const PARIS_CENTER = { lat: 48.8566, lng: 2.3522 };

const CASING_OPTIONS = { strokeColor: "#ffffff", strokeWeight: 9, strokeOpacity: 0.9 };
// One color per step (leg), cycling through the palette, so each leg of the
// route is visually distinguishable.
const LEG_LINE_OPTIONS = COLORS.map((color) => ({ strokeColor: color, strokeWeight: 5, strokeOpacity: 0.95 }));

// Pre-computes {key, path} for every leg of the route, so the polyline
// path arrays stay referentially stable across re-renders that don't
// change the optimize result.
function buildLegSegments(result) {
  if (!result) return [];

  const legSegments = [];
  result.routes.forEach((route) => {
    if (!route.geometry || route.geometry.polyline.length < 2) return;
    const legs = splitPolylineIntoLegs(route.geometry.polyline, route.geometry.segments);
    legs.forEach((path, legIdx) => {
      if (path.length < 2) return;
      legSegments.push({ key: `${route.vehicle_id}-leg-${legIdx}`, path, legIdx });
    });
  });
  return legSegments;
}

function MarkerBadge({ label, color, title }) {
  return (
    <div className="marker-badge" style={{ background: color }} title={title}>
      {label}
    </div>
  );
}

function FitBounds({ depot, stops, result }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !window.google) return;

    const points = [];
    if (depot) points.push([depot.lat, depot.lon]);
    for (const stop of stops) points.push([stop.lat, stop.lon]);
    if (result) {
      for (const route of result.routes) {
        if (route.geometry) for (const p of route.geometry.polyline) points.push(p);
      }
    }
    if (points.length === 0) return;

    const bounds = new window.google.maps.LatLngBounds();
    for (const [lat, lon] of points) bounds.extend({ lat, lng: lon });
    map.fitBounds(bounds, 60);
  }, [map, depot, stops, result]);

  return null;
}

// Builds a stopId -> {color, order, etaStr, vehicleId} lookup from the
// optimize response. Each stop is the destination of one leg/step, so it
// gets that step's color (matching the map polyline).
function buildStopInfo(result) {
  const info = {};
  if (!result) return info;

  result.routes.forEach((route) => {
    const etaByStop = {};
    for (const eta of route.stop_etas) etaByStop[eta.stop_id] = eta;

    route.stops.forEach((stopId, order) => {
      const eta = etaByStop[stopId];
      info[stopId] = {
        color: COLORS[order % COLORS.length],
        order,
        etaStr: eta ? formatETA(eta.arrival_time) : "?",
        vehicleId: route.vehicle_id,
      };
    });
  });

  return info;
}

// On-map legend: one row per step (leg) showing its color and the stop it
// leads to, so a driver can match a map segment's color to its place in
// the route.
function RouteLegend({ result, stops }) {
  if (!result || result.routes.length === 0) return null;
  const route = result.routes[0];
  if (!route || route.stops.length === 0) return null;

  const nameById = Object.fromEntries(stops.map((s) => [s.id, s.address?.split(",")[0] ?? s.id]));

  return (
    <div className="route-legend">
      {route.stops.map((stopId, i) => {
        const color = COLORS[i % COLORS.length];

        return (
          <div className="route-legend-row" key={stopId}>
            <span className="route-legend-swatch" style={{ background: color }} />
            <span className="route-legend-label">
              <strong>Step {i + 1}</strong>
              <span className="route-legend-order">{nameById[stopId] ?? stopId}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function MapView({ mapId, depot, stops, result }) {
  const stopInfo = buildStopInfo(result);
  const legSegments = useMemo(() => buildLegSegments(result), [result]);

  return (
    <>
      <Map
        mapId={mapId}
        defaultCenter={PARIS_CENTER}
        defaultZoom={11}
        style={{ width: "100%", height: "100%" }}
        gestureHandling="greedy"
        disableDefaultUI={false}
      >
        <FitBounds depot={depot} stops={stops} result={result} />

        {depot && (
          <AdvancedMarker position={{ lat: depot.lat, lng: depot.lon }}>
            <MarkerBadge label="D" color="#000000" title={`Depot: ${depot.address}`} />
          </AdvancedMarker>
        )}

        {stops.map((stop, i) => {
          const info = stopInfo[stop.id];
          const label = info ? String(info.order + 1) : String(i + 1);
          const color = info ? info.color : "#666666";
          const title = info
            ? `${stop.address}\nVehicle: ${info.vehicleId}\nStop ${info.order + 1} of ${result.routes.find((r) => r.vehicle_id === info.vehicleId).stops.length}\nETA: ${info.etaStr}`
            : stop.address;

          return (
            <AdvancedMarker key={stop.id} position={{ lat: stop.lat, lng: stop.lon }}>
              <MarkerBadge label={label} color={color} title={title} />
            </AdvancedMarker>
          );
        })}

        {legSegments.map(({ key, path, legIdx }) => (
          <Fragment key={key}>
            <Polyline path={path} options={CASING_OPTIONS} />
            <Polyline path={path} options={LEG_LINE_OPTIONS[legIdx % LEG_LINE_OPTIONS.length]} />
          </Fragment>
        ))}
      </Map>
      <RouteLegend result={result} stops={stops} />
    </>
  );
}
