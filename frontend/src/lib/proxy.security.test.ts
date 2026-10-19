import {afterEach, describe, expect, it, vi} from "vitest";
import {NextRequest} from "next/server";
import {GET, POST} from "@/app/api/v1/[...path]/route";

afterEach(()=>{vi.unstubAllGlobals();vi.unstubAllEnvs();});
const context=(path:string[])=>({params:Promise.resolve({path})});

describe("API proxy security boundary",()=>{
  it.each([
    ["..","customers"],
    ["https:","foreign.invalid"],
    ["operations","correlations","123","extra"],
    ["incidents","123","execute"],
    ["tools","shell"],
  ])("rejects unregistered route %j without upstream dispatch",async(...path)=>{
    const fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);
    const response=await GET(new NextRequest("http://localhost/api/v1/probe"),context(path));
    expect(response.status).toBe(404);expect(fetcher).not.toHaveBeenCalled();
  });
  it("does not forward forged actor, tenant, role or authorization headers",async()=>{
    const fetcher=vi.fn().mockResolvedValue(Response.json({items:[]}));vi.stubGlobal("fetch",fetcher);
    await GET(new NextRequest("http://localhost/api/v1/customers",{headers:{"x-tenant-id":"foreign","x-actor-id":"admin","x-role":"admin","authorization":"Bearer forged",cookie:"synthetic=session"}}),context(["customers"]));
    const headers=fetcher.mock.calls[0][1].headers as Headers;
    for(const name of ["x-tenant-id","x-actor-id","x-role","authorization"])expect(headers.has(name)).toBe(false);
    expect(headers.get("cookie")).toBe("synthetic=session");
  });
  it("rejects an oversized mutation body before forwarding",async()=>{
    const fetcher=vi.fn();vi.stubGlobal("fetch",fetcher);
    const response=await POST(new NextRequest("http://localhost/api/v1/incidents/detect",{method:"POST",body:"x".repeat(8193)}),context(["incidents","detect"]));
    expect(response.status).toBe(413);expect(fetcher).not.toHaveBeenCalled();
  });
  it("uses a configured backend and manual redirects rather than a query-supplied destination",async()=>{
    vi.stubEnv("BACKEND_INTERNAL_URL","http://127.0.0.1:8000");
    const fetcher=vi.fn().mockResolvedValue(Response.json({items:[]}));vi.stubGlobal("fetch",fetcher);
    await GET(new NextRequest("http://localhost/api/v1/customers?url=https://foreign.invalid"),context(["customers"]));
    expect(fetcher.mock.calls[0][0]).toMatch(/^http:\/\/[^/]+\/api\/v1\/customers\?/);
    expect(fetcher.mock.calls[0][1].redirect).toBe("manual");
    expect(fetcher.mock.calls[0][1].cache).toBe("no-store");
  });
});
