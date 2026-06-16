// Converts between "HH:MM" (used by <input type="time">) and
// seconds-since-midnight (used by the /optimize API).

export function timeToSeconds(value) {
  if (!value) return null;
  const [h, m] = value.split(":").map(Number);
  return h * 3600 + m * 60;
}

export function secondsToTime(seconds) {
  const h = Math.floor(seconds / 3600) % 24;
  const m = Math.floor((seconds % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
