async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    const error = new Error("Request failed");
    error.data = data;
    throw error;
  }
  return data;
}

export async function getConfig() {
  const res = await fetch("/config");
  if (!res.ok) throw new Error("Failed to load /config");
  return res.json();
}

export function optimize(requestBody) {
  return postJson("/optimize", requestBody);
}
