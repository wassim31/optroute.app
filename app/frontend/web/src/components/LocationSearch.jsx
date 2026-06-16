import { useEffect, useRef } from "react";
import { useMapsLibrary } from "@vis.gl/react-google-maps";

// A plain <input> wired up to Google Places Autocomplete. Selecting a
// suggestion calls onPlaceSelected with {address, lat, lon} and clears
// the input, ready for the next search.
export default function LocationSearch({ placeholder, onPlaceSelected }) {
  const placesLib = useMapsLibrary("places");
  const inputRef = useRef(null);
  const onPlaceSelectedRef = useRef(onPlaceSelected);
  onPlaceSelectedRef.current = onPlaceSelected;

  // Create the Autocomplete widget once placesLib is ready. Re-creating it
  // on every callback change (e.g. when adding stops) would attach a second
  // widget to the same input and break suggestions/selection.
  useEffect(() => {
    if (!placesLib || !inputRef.current) return;

    const autocomplete = new placesLib.Autocomplete(inputRef.current, {
      fields: ["formatted_address", "name", "geometry"],
    });

    const listener = autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();
      const location = place.geometry && place.geometry.location;
      if (!location) return;

      onPlaceSelectedRef.current({
        address: place.formatted_address || place.name || "",
        lat: location.lat(),
        lon: location.lng(),
      });

      if (inputRef.current) inputRef.current.value = "";
    });

    return () => {
      listener.remove();
      window.google.maps.event.clearInstanceListeners(autocomplete);
    };
  }, [placesLib]);

  return <input ref={inputRef} type="text" placeholder={placeholder} className="location-search" />;
}
