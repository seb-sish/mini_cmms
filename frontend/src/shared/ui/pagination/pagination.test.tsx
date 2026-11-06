import Pagination from "./index";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/react";
import { getPageRange } from "./index";

describe("Pagination", () => {
  it("formats visible range", () => {
    expect(getPageRange(45, 20, 40)).toBe("41-45 из 45");
    expect(getPageRange(0, 20, 0)).toBe("0 из 0");
  });

  it("is hidden when everything fits on one page", () => {
    const { container } = render(
      <Pagination total={5} limit={20} offset={0} onChange={vi.fn()} />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("moves between pages by limit", async () => {
    const handleChange = vi.fn();

    render(
      <Pagination total={45} limit={20} offset={20} onChange={handleChange} />
    );

    expect(screen.getByText("2 / 3")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "Следующая страница" })
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Предыдущая страница" })
    );

    expect(handleChange).toHaveBeenNthCalledWith(1, 40);
    expect(handleChange).toHaveBeenNthCalledWith(2, 0);
  });

  it("disables previous button on the first page", () => {
    render(<Pagination total={45} limit={20} offset={0} onChange={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: "Предыдущая страница" })
    ).toBeDisabled();
  });
});
