import { fetchTechnicians } from "./userApi";

describe("technician directory", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads every page of active technicians from the read-only directory", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{ id: "first", login: "first" }], total: 2, limit: 100, offset: 0 })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{ id: "second", login: "second" }], total: 2, limit: 100, offset: 1 })));
    vi.stubGlobal("fetch", fetchMock);
    const people = await fetchTechnicians();
    expect(people.map((person) => person.id)).toEqual(["first", "second"]);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/users/directory?role=TECHNICIAN&status=ACTIVE&limit=100&offset=0",
      "/api/v1/users/directory?role=TECHNICIAN&status=ACTIVE&limit=100&offset=1",
    ]);
  });
});
