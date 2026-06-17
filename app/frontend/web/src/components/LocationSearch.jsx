import { useEffect, useRef } from "react";
import { useMapsLibrary } from "@vis.gl/react-google-maps";

// A plain <input> wired up to Google Places Autocomplete. Selecting a
// suggestion calls onPlaceSelected with {address, lat, lon} and clears
// the input, ready for the next search.
//
// `bias` (optional {lat, lon}) biases suggestions toward that point — used
// so that, once a depot is set, nearby stop addresses rank first instead of
// a broad worldwide search.
export default function LocationSearch({ placeholder, onPlaceSelected, bias }) {
  const placesLib = useMapsLibrary("places");
  const inputRef = useRef(null);
  const autocompleteRef = useRef(null);
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
    autocompleteRef.current = autocomplete;

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
      autocompleteRef.current = null;
    };
  }, [placesLib]);

  // Bias predictions toward the depot (~30 km radius) so nearby addresses
  // are prioritised. This is a soft bias, not a hard restriction — far-away
  // places can still be picked if typed explicitly.
  useEffect(() => {
    const autocomplete = autocompleteRef.current;
    if (!autocomplete || !bias || !window.google) return;

    const circle = new window.google.maps.Circle({
      center: { lat: bias.lat, lng: bias.lon },
      radius: 30000,
    });
    autocomplete.setBounds(circle.getBounds());
  }, [bias, placesLib]);

  return (
    <div className="search-field">
      <svg className="search-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
        <path
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          d="M21 21l-4.3-4.3M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z"
        />
      </svg>
      <input ref={inputRef} type="text" placeholder={placeholder} className="location-search" />
    </div>
  );
}
