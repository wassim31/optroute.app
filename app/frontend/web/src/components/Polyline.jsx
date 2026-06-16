import { useEffect, useRef } from "react";
import { useMap } from "@vis.gl/react-google-maps";

// Imperative wrapper around google.maps.Polyline, since
// @vis.gl/react-google-maps doesn't ship a <Polyline> component.
export default function Polyline({ path, options }) {
  const map = useMap();
  const polylineRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    const polyline = new window.google.maps.Polyline({
      ...options,
      path: path.map(([lat, lng]) => ({ lat, lng })),
      map,
    });
    polylineRef.current = polyline;

    return () => polyline.setMap(null);
  }, [map, path, options]);

  return null;
}
