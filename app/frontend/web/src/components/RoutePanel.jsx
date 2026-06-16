import { COLORS, formatETA } from "../lib/routeGeometry.js";

export default function RoutePanel({ result, stops }) {
  if (!result) return null;

  const nameById = Object.fromEntries((stops ?? []).map((s) => [s.id, s.address?.split(",")[0] ?? s.id]));

  return (
    <div className="routes">
      {result.routes.map((route) => {
        const etaByStop = {};
        for (const eta of route.stop_etas) etaByStop[eta.stop_id] = eta;

        return (
          <div className="route-card" key={route.vehicle_id}>
            <h4>Vehicle {route.vehicle_id}</h4>
            <p>
              Distance: {Math.round(route.distance)} m — Duration: {Math.round(route.duration / 60)} min
            </p>
            <ol>
              {route.stops.map((stopId, order) => {
                const eta = etaByStop[stopId];
                const etaStr = eta ? formatETA(eta.arrival_time) : "?";
                const color = COLORS[order % COLORS.length];

                return (
                  <li key={stopId}>
                    <span className="leg-swatch" style={{ background: color }} />
                    {nameById[stopId] ?? stopId} (ETA {etaStr})
                  </li>
                );
              })}
            </ol>
          </div>
        );
      })}
    </div>
  );
}
