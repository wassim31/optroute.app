export default function StopList({ stops, onRemove, onUpdate }) {
  if (stops.length === 0) {
    return (
      <div className="empty-stops">
        <span className="empty-icon">🧭</span>
        <p>No stops yet</p>
        <small>Search above to add delivery locations.</small>
      </div>
    );
  }

  return (
    <ul className="stop-list">
      {stops.map((stop, i) => {
        const name = stop.address.split(",")[0];
        const incomplete =
          !(parseInt(stop.demand, 10) >= 1) || !stop.timeWindowStart || !stop.timeWindowEnd;

        return (
          <li key={stop.id} className={`stop-item ${incomplete ? "incomplete" : ""}`}>
            <div className="stop-main">
              <span className="stop-badge">{i + 1}</span>
              <span className="stop-name" title={stop.address}>{name}</span>
              <button
                type="button"
                className="icon-btn danger"
                onClick={() => onRemove(stop.id)}
                aria-label="Remove stop"
              >
                ×
              </button>
            </div>

            <div className="stop-fields">
              <div className="field">
                <label>Number of products needed <span className="req">*</span></label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 5"
                  value={stop.demand}
                  onChange={(e) => onUpdate(stop.id, { demand: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Delivery time <span className="req">*</span></label>
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
          </li>
        );
      })}
    </ul>
  );
}
