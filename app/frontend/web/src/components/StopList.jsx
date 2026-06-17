import { useState } from "react";

export default function StopList({ stops, onRemove, onUpdate }) {
  const [expanded, setExpanded] = useState(null);

  if (stops.length === 0) {
    return (
      <div className="empty-stops">
        <span className="empty-icon">🧭</span>
        <p>No stops yet</p>
        <small>Search above to add delivery locations.</small>
      </div>
    );
  }

  const toggle = (id) => setExpanded((cur) => (cur === id ? null : id));
  const hasWindow = (s) => s.timeWindowStart || s.timeWindowEnd;

  return (
    <ul className="stop-list">
      {stops.map((stop, i) => {
        const open = expanded === stop.id;
        const name = stop.address.split(",")[0];
        const showMeta = !open && (hasWindow(stop) || stop.demand !== 1);

        return (
          <li key={stop.id} className={`stop-item ${open ? "open" : ""}`}>
            <div className="stop-main">
              <span className="stop-badge">{i + 1}</span>
              <span className="stop-name" title={stop.address}>{name}</span>
              <button
                type="button"
                className={`icon-btn ${open ? "active" : ""}`}
                onClick={() => toggle(stop.id)}
                aria-label="Options"
                title="Demand & time window"
              >
                ⚙
              </button>
              <button
                type="button"
                className="icon-btn danger"
                onClick={() => onRemove(stop.id)}
                aria-label="Remove stop"
              >
                ×
              </button>
            </div>

            {showMeta && (
              <div className="stop-meta">
                {stop.demand !== 1 && <span>📦 {stop.demand}</span>}
                {hasWindow(stop) && (
                  <span>🕒 {stop.timeWindowStart || "…"}–{stop.timeWindowEnd || "…"}</span>
                )}
              </div>
            )}

            {open && (
              <div className="stop-options">
                <div className="opt-row">
                  <label>Demand</label>
                  <input
                    type="number"
                    min="0"
                    value={stop.demand}
                    onChange={(e) => onUpdate(stop.id, { demand: parseInt(e.target.value, 10) || 0 })}
                  />
                </div>
                <div className="opt-row">
                  <label>Time window</label>
                  <div className="time-range small">
                    <input
                      type="time"
                      value={stop.timeWindowStart}
                      onChange={(e) => onUpdate(stop.id, { timeWindowStart: e.target.value })}
                      aria-label="Deliver after"
                    />
                    <span>–</span>
                    <input
                      type="time"
                      value={stop.timeWindowEnd}
                      onChange={(e) => onUpdate(stop.id, { timeWindowEnd: e.target.value })}
                      aria-label="Deliver before"
                    />
                  </div>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
