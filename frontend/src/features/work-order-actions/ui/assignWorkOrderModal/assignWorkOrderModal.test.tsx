import AssignWorkOrderModal from "./index";
import userEvent from "@testing-library/user-event";
import { buildWorkOrderFixture } from "@entities/work-order/testing";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { FlagsProvider } from "@shared/ui/flag";
import { render, screen } from "@testing-library/react";

describe("assign work order", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("offers an active technician by name without manual UUID input", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [{ id: "33333333-3333-4333-8333-333333333333", login: "tech.ivanov", role: "TECHNICIAN", status: "ACTIVE" }],
      total: 1, limit: 100, offset: 0,
    })));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <FlagsProvider>
          <AssignWorkOrderModal workOrder={buildWorkOrderFixture()} onClose={vi.fn()} />
        </FlagsProvider>
      </QueryClientProvider>
    );
    expect(await screen.findByRole("option", { name: "tech.ivanov" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/UUID/)).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole("combobox"), "33333333-3333-4333-8333-333333333333");
    expect(screen.getByRole("button", { name: "Назначить" })).toBeEnabled();
  });
});
