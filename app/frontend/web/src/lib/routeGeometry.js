export const COLORS = [
  "#e6194b",
  "#3cb44b",
  "#4363d8",
  "#f58231",
  "#911eb4",
  "#46f0f0",
  "#f032e6",
  "#bcf60c",
];

export function formatETA(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

// Splits a full route polyline into one polyline per leg, using each leg's
// road distance to find the split points along the path.
export function splitPolylineIntoLegs(polyline, segments) {
  if (polyline.length < 2 || !segments || segments.length === 0) return [polyline];

  const cum = [0];
  for (let i = 1; i < polyline.length; i++) {
    const [lat1, lon1] = polyline[i - 1];
    const [lat2, lon2] = polyline[i];
    cum.push(cum[i - 1] + haversine(lat1, lon1, lat2, lon2));
  }
  const total = cum[cum.length - 1];
  const segTotal = segments.reduce((s, seg) => s + seg.distance, 0) || total;

  const legs = [];
  let pointIdx = 0;
  let cumDistance = 0;
  let startPoint = polyline[0];

  segments.forEach((segment, i) => {
    cumDistance += segment.distance;
    const targetDist = total * (cumDistance / segTotal);
    const legPoints = [startPoint];

    while (pointIdx + 1 < polyline.length && cum[pointIdx + 1] < targetDist) {
      pointIdx++;
      legPoints.push(polyline[pointIdx]);
    }

    if (i < segments.length - 1 && pointIdx + 1 < polyline.length) {
      const d0 = cum[pointIdx];
      const d1 = cum[pointIdx + 1];
      const t = d1 > d0 ? (targetDist - d0) / (d1 - d0) : 0;
      const [lat0, lon0] = polyline[pointIdx];
      const [lat1, lon1] = polyline[pointIdx + 1];
      const splitPoint = [lat0 + (lat1 - lat0) * t, lon0 + (lon1 - lon0) * t];
      legPoints.push(splitPoint);
      startPoint = splitPoint;
    } else {
      for (let j = pointIdx + 1; j < polyline.length; j++) legPoints.push(polyline[j]);
    }

    legs.push(legPoints);
  });

  return legs;
}
