export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  notify = true,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    if (response.status === 401 && notify)
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(
      response.status,
      payload?.error?.message || "Request failed. Please try again.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
