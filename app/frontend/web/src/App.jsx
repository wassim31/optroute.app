import { useCallback, useEffect, useState } from "react";
import { APIProvider } from "@vis.gl/react-google-maps";
import MapView from "./components/MapView.jsx";
import LocationSearch from "./components/LocationSearch.jsx";
import StopList from "./components/StopList.jsx";
import RoutePanel from "./components/RoutePanel.jsx";
import { getConfig, optimize } from "./lib/api.js";
import { timeToSeconds } from "./lib/time.js";

const FULL_DAY_WINDOW = [0, 24 * 3600];

const DEFAULT_DEPOT = { address: "13 rue Pitre Chevalier, Nantes, France", lat: 47.2241112, lon: -1.5502079 };

const DEFAULT_STOPS = [
  { address: "Château des Ducs de Bretagne, Nantes, France", lat: 47.2161171, lon: -1.5493127 },
  { address: "Cathédrale Saint-Pierre-et-Saint-Paul, Nantes, France", lat: 47.2186, lon: -1.5475 },
  { address: "Passage Pommeraye, Nantes, France", lat: 47.2138, lon: -1.5559 },
  { address: "Place Graslin, Nantes, France", lat: 47.2127, lon: -1.5572 },
  { address: "Place Royale, Nantes, France", lat: 47.2143, lon: -1.5543 },
  { address: "Jardin des Plantes, Nantes, France", lat: 47.2208, lon: -1.5466 },
  { address: "Île de Nantes, Nantes, France", lat: 47.2055, lon: -1.5475 },
  { address: "Les Machines de l'île, Nantes, France", lat: 47.2047, lon: -1.5478 },
  { address: "Musée d'Arts de Nantes, Nantes, France", lat: 47.2178, lon: -1.5512 },
  { address: "Cours des 50 Otages, Nantes, France", lat: 47.2155, lon: -1.5552 },
];

export default function App() {
  const [config, setConfig] = useState(null);
  const [depot, setDepot] = useState(null);
  const [stops, setStops] = useState([]);
  const [vehicleCapacity, setVehicleCapacity] = useState(20);
  const [shiftStart, setShiftStart] = useState("08:00");
  const [shiftEnd, setShiftEnd] = useState("16:00");
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

  // Pre-fill the depot and a set of default Nantes stops on first load, so
  // the app is ready to optimize without manual searching every time.
  useEffect(() => {
    setDepot(DEFAULT_DEPOT);
    setStops(
      DEFAULT_STOPS.map((stop, i) => ({
        id: `S${i + 1}`,
        ...stop,
        demand: 1,
        timeWindowStart: "",
        timeWindowEnd: "",
      }))
    );
    setNextStopNum(DEFAULT_STOPS.length + 1);
  }, []);

  const handleDepotSelected = useCallback((place) => {
    setDepot(place);
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

  const handleOptimize = async () => {
    setError("");
    setResult(null);

    if (!depot) {
      setError("Please search and select a depot location.");
      return;
    }
    if (stops.length === 0) {
      setError("Please add at least one stop location.");
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
      setError(JSON.stringify(e.data ?? { error: e.message }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  if (!config) {
    return <div className="loading">{error || "Loading..."}</div>;
  }

  return (
    <APIProvider apiKey={config.googleMapsApiKey} libraries={["places"]}>
      <div id="layout" data-tab={activeTab}>
        <div id="sidebar">
          <h3>route.me</h3>

          <label>Depot location</label>
          <LocationSearch placeholder="Search depot, e.g. 10 Rue de Rivoli, Paris" onPlaceSelected={handleDepotSelected} />
          {depot && <p className="selected-depot">📍 {depot.address}</p>}

          <label>Add a stop</label>
          <LocationSearch placeholder="Search a location, e.g. Commerce, Nantes" onPlaceSelected={handleStopSelected} />
          <StopList stops={stops} onRemove={handleRemoveStop} onUpdate={handleUpdateStop} />

          <label htmlFor="vehicleCapacity">Vehicle capacity</label>
          <input
            id="vehicleCapacity"
            type="number"
            min="1"
            value={vehicleCapacity}
            onChange={(e) => setVehicleCapacity(parseInt(e.target.value, 10) || 1)}
          />

          <label htmlFor="shift">Vehicle working hours</label>
          <div className="shift-range" id="shift">
            <input type="time" value={shiftStart} onChange={(e) => setShiftStart(e.target.value)} />
            <span>to</span>
            <input type="time" value={shiftEnd} onChange={(e) => setShiftEnd(e.target.value)} />
          </div>

          <button type="button" onClick={handleOptimize} disabled={loading}>
            {loading ? "Optimizing..." : "Optimize"}
          </button>

          {error && <div id="error">{error}</div>}

          <RoutePanel result={result} stops={stops} />
        </div>

        <div id="map">
          <MapView mapId={config.googleMapsMapId} depot={depot} stops={stops} result={result} />
        </div>

        <div className="tab-bar">
          <button
            className={activeTab === "plan" ? "active" : ""}
            onClick={() => setActiveTab("plan")}
          >
            ✏️ Plan
          </button>
          <button
            className={activeTab === "map" ? "active" : ""}
            onClick={() => setActiveTab("map")}
          >
            🗺️ Map{result ? " ✓" : ""}
          </button>
        </div>
      </div>
    </APIProvider>
  );
}
