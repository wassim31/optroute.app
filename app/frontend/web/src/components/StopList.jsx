export default function StopList({ stops, onRemove, onUpdate }) {
  if (stops.length === 0) {
    return <p className="hint">No stops added yet — search above to add one.</p>;
  }

  return (
    <ol className="stop-list">
      {stops.map((stop, i) => (
        <li key={stop.id}>
          <div className="stop-row">
            <span className="stop-order">{i + 1}</span>
            <span className="stop-address">{stop.address}</span>
            <input
              type="number"
              className="stop-demand"
              min="0"
              value={stop.demand}
              onChange={(e) => onUpdate(stop.id, { demand: parseInt(e.target.value, 10) || 0 })}
              title="Demand (e.g. crates to deliver)"
              aria-label="Demand"
            />
            <button type="button" className="remove-btn" onClick={() => onRemove(stop.id)} aria-label="Remove stop">
              ×
            </button>
          </div>
          <div className="stop-time-window">
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
        </li>
      ))}
    </ol>
  );
}
