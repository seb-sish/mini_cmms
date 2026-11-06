import WorkOrderActivity from "./index";
import { ViewerProvider } from "@entities/user";
import { buildUserFixture } from "@entities/user/testing";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

describe("work order activity", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows user details without exposing legacy technical messages", async () => {
    const event = { work_order_id: "work", actor_id: "user-1", occurred_at: "2026-11-06T12:00:00Z", from_status: null, to_status: null, old_assignee_id: null, new_assignee_id: null };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [
      { ...event, id: "1", event_type: "COMPLETED", details: "Replaced bearing <script>unsafe</script>" },
      { ...event, id: "2", event_type: "CREATED", details: "Work order created" },
    ], total: 2, limit: 100, offset: 0 }))));
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ViewerProvider viewer={buildUserFixture()}>
          <WorkOrderActivity workOrderId="work" />
        </ViewerProvider>
      </QueryClientProvider>
    );
    expect(await screen.findByText("Replaced bearing <script>unsafe</script>")).toBeInTheDocument();
    expect(screen.queryByText("Work order created")).not.toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
