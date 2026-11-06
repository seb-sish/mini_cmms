import { setUnauthorizedHandler } from "./httpClient";
import { buildIfMatch } from "./httpClient";
import { apiRequest } from "./httpClient";
import { HttpMethod } from "./httpClient";
import { ApiErrorCode } from "./apiError";
import { ApiError } from "./apiError";

const jsonResponse = (
  status: number,
  body: unknown,
  headers: Record<string, string> = {}
): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });

describe("httpClient", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
  });

  it("builds strong If-Match value from id and version", () => {
    expect(buildIfMatch("abc", 3)).toBe('"abc:3"');
  });

  it("sends JSON body, query and If-Match to the same-origin proxy", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { id: "1" }));

    await apiRequest("/equipment/1", {
      method: HttpMethod.PATCH,
      body: { name: "Пресс" },
      query: { q: "x", empty: "", missing: undefined },
      ifMatch: '"1:2"',
    });

    const [url, init] = fetchMock.mock.calls[0];

    expect(url).toBe("/api/v1/equipment/1?q=x");
    expect(init.method).toBe("PATCH");
    expect(init.headers["If-Match"]).toBe('"1:2"');
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ name: "Пресс" }));
  });

  it("returns undefined for 204 responses", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(
      apiRequest("/auth/logout", { method: HttpMethod.POST })
    ).resolves.toBeUndefined();
  });

  it("converts problem details into ApiError with field errors and Retry-After", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        429,
        {
          status: 429,
          code: "RATE_LIMITED",
          detail: "Too many",
          errors: [{ field: "login", message: "x" }],
        },
        { "Retry-After": "120" }
      )
    );

    const error = await apiRequest("/x").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 429,
      code: "RATE_LIMITED",
      retryAfterSeconds: 120,
      fieldErrors: [{ field: "login", message: "x" }],
    });
  });

  it("notifies the unauthorized handler on expired session", async () => {
    const handler = vi.fn();

    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(
      jsonResponse(401, { status: 401, code: "UNAUTHENTICATED" })
    );

    await expect(apiRequest("/auth/me")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not treat invalid credentials as an expired session", async () => {
    const handler = vi.fn();

    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(
      jsonResponse(401, { status: 401, code: "INVALID_CREDENTIALS" })
    );

    await expect(apiRequest("/auth/login")).rejects.toMatchObject({
      code: "INVALID_CREDENTIALS",
    });
    expect(handler).not.toHaveBeenCalled();
  });

  it("maps transport failures to NETWORK_ERROR", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(apiRequest("/x")).rejects.toMatchObject({
      code: ApiErrorCode.NETWORK_ERROR,
      status: 0,
    });
  });
});
