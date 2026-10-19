import { NextRequest } from "next/server";
const allowed =
  /^(operations\/(?:overview|metrics|activity|thresholds|correlations\/[0-9a-f-]+)|incidents(?:\/(?:detect|[0-9a-f-]+(?:\/(?:acknowledge|assign|investigate|resolve|close|notes))?))?|execution-jobs(?:\/[0-9a-f-]+(?:\/(?:cancel|retry|attempts|events))?)?|approvals(?:\/[0-9a-f-]+(?:\/(?:approve|reject|cancel))?)?|action-executions\/[0-9a-f-]+|actions|action-proposals(?:\/[0-9a-f-]+(?:\/(?:decision|revalidate|approval-requests|execute))?)?|auth\/(login|logout|me)|tools(?:\/execute)?|investigations(?:\/[0-9a-f-]+(?:\/(?:events|evidence(?:\/[0-9a-f-]+)?|sources|conflicts|gaps|findings|cancel|resume|action-proposal))?)?|health|ready|customers(?:\/[0-9a-f-]+)?|accounts(?:\/[0-9a-f-]+)?|tickets(?:\/[0-9a-f-]+)?)$/;
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const route = path.join("/");
  const fail = (status: number, message: string) =>
    Response.json(
      {
        error: {
          code: "proxy_error",
          message,
          request_id: crypto.randomUUID(),
        },
      },
      { status, headers: { "Cache-Control": "no-store" } },
    );
  if (!allowed.test(route)) return fail(404, "Resource not found");
  const headers = new Headers();
  for (const name of [
    "cookie",
    "origin",
    "content-type",
    "sec-fetch-site",
    "idempotency-key",
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  let body: Uint8Array | undefined;
  if (request.method === "POST" && request.body) {
    const reader = request.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8192) {
        await reader.cancel();
        return fail(413, "Request too large");
      }
      chunks.push(value);
    }
    body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.byteLength;
    }
  }
  try {
    const base = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    const upstream = await fetch(
      `${base}/api/v1/${route}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: body as BodyInit | undefined,
        cache: "no-store",
        redirect: "manual",
        signal: AbortSignal.timeout(
          route.startsWith("investigations") ? 35000 : 10000,
        ),
      },
    );
    const outgoing = new Headers({
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    for (const name of ["content-type", "x-request-id", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie())
      outgoing.append("set-cookie", cookie);
    return new Response(upstream.status === 204 ? null : upstream.body, {
      status: upstream.status,
      headers: outgoing,
    });
  } catch {
    return fail(503, "Service unavailable. Please try again.");
  }
}
export const GET = proxy;
export const POST = proxy;
