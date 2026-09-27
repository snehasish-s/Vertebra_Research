const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");
let accessToken = ""; // In memory only: never embed a shared passphrase in the built site.

export function setAccessToken(value) {
  accessToken = value;
}

export async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    options.upload ? 240000 : 120000,
  );
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        typeof body.detail === "string"
          ? body.detail
          : "The request could not be completed. Please try again.",
      );
    }
    if (response.status === 204) return null;
    return options.pdf ? response.arrayBuffer() : response.json();
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error(
        "The request timed out. Refresh the library to check whether processing finished.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the research service. It may be waking up; please try again in a minute.",
      );
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function uploadDocument(file) {
  const body = new FormData();
  body.append("file", file);
  return request("/api/documents", { method: "POST", body, upload: true });
}

export function askQuestion(question) {
  return request("/api/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
