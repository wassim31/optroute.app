import { useCallback, useEffect, useState } from "react";
import { APIProvider } from "@vis.gl/react-google-maps";
import MapView from "./components/MapView.jsx";
import LocationSearch from "./components/LocationSearch.jsx";
import StopList from "./components/StopList.jsx";
import RoutePanel from "./components/RoutePanel.jsx";
import { getConfig, optimize } from "./lib/api.js";
import { timeToSeconds } from "./lib/time.js";

const FULL_DAY_WINDOW = [0, 24 * 3600];

export default function App() {
  const [config, setConfig] = useState(null);
  const [depot, setDepot] = useState(null);
  const [stops, setStops] = useState([]);
  const [vehicleCapacity, setVehicleCapacity] = useState(20);
  const [shiftStart, setShiftStart] = useState("08:00");
  const [shiftEnd, setShiftEnd] = useState("16:00");
  const [showSettings, setShowSettings] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [nextStopNum, setNextStopNum] = useState(1);
  const [activeTab, setActiveTab] = useState("plan");

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch((e) => setError(`Failed to load config: ${e.message}`));
  }, []);

  const handleDepotSelected = useCallback((place) => {
    setDepot(place);
    setResult(null);
  }, []);

  const handleClearDepot = useCallback(() => {
    setDepot(null);
    setResult(null);
  }, []);

  const handleStopSelected = useCallback(
    (place) => {
      setStops((prev) => [
        ...prev,
        { id: `S${nextStopNum}`, ...place, demand: 1, timeWindowStart: "", timeWindowEnd: "" },
      ]);
      setNextStopNum((n) => n + 1);
      setResult(null);
    },
    [nextStopNum]
  );

  const handleRemoveStop = useCallback((id) => {
    setStops((prev) => prev.filter((s) => s.id !== id));
    setResult(null);
  }, []);

  const handleUpdateStop = useCallback((id, patch) => {
    setStops((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)));
    setResult(null);
  }, []);

  const handleClearStops = useCallback(() => {
    setStops([]);
    setResult(null);
  }, []);

  const canOptimize = depot && stops.length > 0 && !loading;

  const handleOptimize = async () => {
    setError("");
    setResult(null);

    if (!depot) {
      setError("Please add a starting point first.");
      return;
    }
    if (stops.length === 0) {
      setError("Please add at least one stop.");
      return;
    }

    const shift = [timeToSeconds(shiftStart) ?? FULL_DAY_WINDOW[0], timeToSeconds(shiftEnd) ?? FULL_DAY_WINDOW[1]];

    const requestBody = {
      depot: { lat: depot.lat, lon: depot.lon },
      stops: stops.map((s) => {
        const start = timeToSeconds(s.timeWindowStart);
        const end = timeToSeconds(s.timeWindowEnd);
        const time_window = start !== null && end !== null ? [start, end] : FULL_DAY_WINDOW;
        return { id: s.id, lat: s.lat, lon: s.lon, demand: s.demand, time_window };
      }),
      vehicle: { id: "v1", capacity: vehicleCapacity, shift },
    };

    setLoading(true);
    try {
      const data = await optimize(requestBody);
      setResult(data);
      setActiveTab("map");
    } catch (e) {
      setError(e.data?.detail || e.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (!config) {
    return (
      <div className="loading">
        <span className="spinner" />
        {error || "Loading…"}
      </div>
    );
  }

  return (
    <APIProvider apiKey={config.googleMapsApiKey} libraries={["places"]}>
      <div id="layout" data-tab={activeTab}>
        <aside id="sidebar">
          <header className="app-header">
            <span className="brand-mark">📍</span>
            <div className="brand-text">
              <h1>route.me</h1>
              <p>Smart route optimization</p>
            </div>
          </header>

          <div className="sidebar-scroll">
            <section className="card">
              <div className="card-head">
                <span className="step-num">1</span>
                <h2>Starting point</h2>
              </div>
              {depot ? (
                <div className="chip">
                  <span className="chip-icon">🏠</span>
                  <span className="chip-text" title={depot.address}>{depot.address}</span>
                  <button className="chip-clear" onClick={handleClearDepot} aria-label="Change starting point">×</button>
                </div>
              ) : (
                <LocationSearch placeholder="Search your depot or warehouse…" onPlaceSelected={handleDepotSelected} />
              )}
            </section>

            <section className="card">
              <div className="card-head">
                <span className="step-num">2</span>
                <h2>Stops</h2>
                {stops.length > 0 && <span className="count-badge">{stops.length}</span>}
                {stops.length > 0 && (
                  <button className="link-btn" onClick={handleClearStops}>Clear</button>
                )}
              </div>
              <LocationSearch placeholder="Add a delivery stop…" onPlaceSelected={handleStopSelected} />
              <StopList stops={stops} onRemove={handleRemoveStop} onUpdate={handleUpdateStop} />
            </section>

            <section className="card">
              <button
                type="button"
                className="card-head as-toggle"
                onClick={() => setShowSettings((s) => !s)}
                aria-expanded={showSettings}
              >
                <span className="step-num">3</span>
                <h2>Vehicle settings</h2>
                <span className={`chevron ${showSettings ? "open" : ""}`}>⌄</span>
              </button>
              {showSettings && (
                <div className="settings-body">
                  <label htmlFor="vehicleCapacity">Capacity</label>
                  <input
                    id="vehicleCapacity"
                    type="number"
                    min="1"
                    value={vehicleCapacity}
                    onChange={(e) => setVehicleCapacity(parseInt(e.target.value, 10) || 1)}
                  />

                  <label htmlFor="shift">Working hours</label>
                  <div className="time-range" id="shift">
                    <input type="time" value={shiftStart} onChange={(e) => setShiftStart(e.target.value)} />
                    <span>–</span>
                    <input type="time" value={shiftEnd} onChange={(e) => setShiftEnd(e.target.value)} />
                  </div>
                </div>
              )}
            </section>

            <RoutePanel result={result} stops={stops} />
          </div>

          <footer className="sidebar-footer">
            {error && <div className="error-box">{error}</div>}
            <button type="button" className="optimize-btn" onClick={handleOptimize} disabled={!canOptimize}>
              {loading ? (
                <><span className="spinner sm" /> Optimizing…</>
              ) : (
                <>⚡ Optimize route</>
              )}
            </button>
          </footer>
        </aside>

        <div id="map">
          <MapView mapId={config.googleMapsMapId} depot={depot} stops={stops} result={result} />
        </div>

        <nav className="tab-bar">
          <button className={activeTab === "plan" ? "active" : ""} onClick={() => setActiveTab("plan")}>
            ✏️ Plan
          </button>
          <button className={activeTab === "map" ? "active" : ""} onClick={() => setActiveTab("map")}>
            🗺️ Map{result ? " ✓" : ""}
          </button>
        </nav>
      </div>
    </APIProvider>
  );
}
