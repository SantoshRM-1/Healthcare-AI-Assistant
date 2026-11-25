const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export type Chat = { id: string; title: string; created_at: string; updated_at: string };
export async function api<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  if (!token) throw new Error("Your session is not ready. Please sign in again and retry.");
  const response = await fetch(`${base}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...init?.headers }, cache: "no-store" });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Your session expired or is invalid. Please sign in again, then retry.");
    let message = `Request failed (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string") message = body.detail;
      else if (typeof body === "object" && body !== null && "message" in body && typeof body.message === "string") message = body.message;
    } catch {
      // Keep the status-based message for non-JSON responses.
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
