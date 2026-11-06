import UserName from "./index";
import { ViewerProvider } from "../../model/viewerContext";
import { buildUserFixture } from "../../testing";
import { UserRole } from "../../model/types";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

describe("UserName", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("resolves an author's summary for a technician", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "author", login: "engineer", role: "ENGINEER", status: "BLOCKED" }))));
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ViewerProvider viewer={buildUserFixture({ role: UserRole.TECHNICIAN })}>
          <UserName userId="author" />
        </ViewerProvider>
      </QueryClientProvider>
    );
    expect(await screen.findByText("engineer")).toBeInTheDocument();
  });
});
