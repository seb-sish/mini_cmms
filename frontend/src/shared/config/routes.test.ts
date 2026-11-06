import { resolveSafeRedirect } from "./routes";
import { buildLoginRoute } from "./routes";
import { ROUTES } from "./routes";

describe("routes", () => {
  it("builds login route with encoded return path", () => {
    expect(buildLoginRoute("/work-orders?status=CREATED")).toBe(
      "/login?next=%2Fwork-orders%3Fstatus%3DCREATED"
    );
    expect(buildLoginRoute(ROUTES.HOME)).toBe(ROUTES.LOGIN);
  });

  it("prevents open redirects after login", () => {
    expect(resolveSafeRedirect("/equipment/1")).toBe("/equipment/1");
    expect(resolveSafeRedirect("https://evil.example")).toBe(ROUTES.HOME);
    expect(resolveSafeRedirect("//evil.example")).toBe(ROUTES.HOME);
    expect(resolveSafeRedirect(null)).toBe(ROUTES.HOME);
  });
});
