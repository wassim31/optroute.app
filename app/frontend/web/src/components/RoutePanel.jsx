import { COLORS, formatETA } from "../lib/routeGeometry.js";

function formatDuration(seconds) {
  const min = Math.round(seconds / 60);
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h${String(m).padStart(2, "0")}` : `${m} min`;
}

export default function RoutePanel({ result, stops }) {
  if (!result) return null;

  const nameById = Object.fromEntries((stops ?? []).map((s) => [s.id, s.address?.split(",")[0] ?? s.id]));

  return (
    <div className="results">
      {result.routes.map((route) => {
        const etaByStop = {};
        for (const eta of route.stop_etas) etaByStop[eta.stop_id] = eta;
        const km = (route.distance / 1000).toFixed(1);

        return (
          <div className="result-card" key={route.vehicle_id}>
            <h3 className="result-title">✓ Optimized route</h3>

            <div className="result-metrics">
              <div className="metric">
                <span className="metric-val">{km}</span>
                <span className="metric-lbl">km</span>
              </div>
              <div className="metric">
                <span className="metric-val">{formatDuration(route.duration)}</span>
                <span className="metric-lbl">duration</span>
              </div>
              <div className="metric">
                <span className="metric-val">{route.stops.length}</span>
                <span className="metric-lbl">stops</span>
              </div>
            </div>

            <ol className="result-stops">
              {route.stops.map((stopId, order) => {
                const eta = etaByStop[stopId];
                const etaStr = eta ? formatETA(eta.arrival_time) : "?";
                const color = COLORS[order % COLORS.length];

                return (
                  <li key={stopId}>
                    <span className="leg-dot" style={{ background: color }}>{order + 1}</span>
                    <span className="leg-name">{nameById[stopId] ?? stopId}</span>
                    <span className="leg-eta">{etaStr}</span>
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
