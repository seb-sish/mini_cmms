import { buildBackendHeaders } from "./backendProxy";
import { isSameOriginRequest } from "./backendProxy";
import { pickResponseHeaders } from "./backendProxy";
import { getBackendBaseUrl } from "./backendProxy";
import { isUnsafeMethod } from "./backendProxy";
import { NextRequest } from "next/server";

describe("backend proxy helpers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("forwards only allowed request headers and adds bearer token", () => {
    const headers = buildBackendHeaders(
      new Headers({
        "content-type": "application/json",
        "if-match": '"a:1"',
        cookie: "secret=1",
        host: "x",
      }),
      "token-value"
    );

    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.get("if-match")).toBe('"a:1"');
    expect(headers.get("authorization")).toBe("Bearer token-value");
    expect(headers.get("cookie")).toBeNull();
    expect(headers.get("host")).toBeNull();
  });

  it("exposes ETag, Retry-After and Location while disabling caching", () => {
    const headers = pickResponseHeaders(
      new Headers({
        etag: '"a:2"',
        "retry-after": "60",
        location: "/api/v1/faults/1",
        server: "uvicorn",
      })
    );

    expect(headers.get("etag")).toBe('"a:2"');
    expect(headers.get("retry-after")).toBe("60");
    expect(headers.get("location")).toBe("/api/v1/faults/1");
    expect(headers.get("server")).toBeNull();
    expect(headers.get("cache-control")).toBe("no-store");
  });

  it("detects unsafe methods", () => {
    expect(isUnsafeMethod("patch")).toBe(true);
    expect(isUnsafeMethod("GET")).toBe(false);
  });

  it("rejects cross-origin requests", () => {
    const sameOrigin = new NextRequest("http://localhost:3000/api/v1/faults", {
      method: "POST",
      headers: { origin: "http://localhost:3000", host: "localhost:3000" },
    });
    const crossOrigin = new NextRequest("http://localhost:3000/api/v1/faults", {
      method: "POST",
      headers: { origin: "https://evil.example", host: "localhost:3000" },
    });
    const withoutOrigin = new NextRequest(
      "http://localhost:3000/api/v1/faults",
      {
        method: "POST",
        headers: { host: "localhost:3000" },
      }
    );

    expect(isSameOriginRequest(sameOrigin)).toBe(true);
    expect(isSameOriginRequest(crossOrigin)).toBe(false);
    expect(isSameOriginRequest(withoutOrigin)).toBe(true);
  });

  it("requires configured backend URL and strips trailing slash", () => {
    vi.stubEnv("CMMS_API_BASE_URL", "https://api.example.com/");

    expect(getBackendBaseUrl()).toBe("https://api.example.com");

    vi.stubEnv("CMMS_API_BASE_URL", "");

    expect(() => getBackendBaseUrl()).toThrow(
      "CMMS_API_BASE_URL is not configured"
    );
  });
});
