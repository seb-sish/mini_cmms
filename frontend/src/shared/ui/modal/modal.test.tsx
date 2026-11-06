import Modal from "./index";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/react";

describe("Modal", () => {
  it("renders accessible dialog and focuses first field", () => {
    render(
      <Modal title="Новая заявка" onClose={vi.fn()}>
        <input aria-label="Заголовок" />
      </Modal>
    );

    expect(
      screen.getByRole("dialog", { name: "Новая заявка" })
    ).toHaveAttribute("aria-modal", "true");
    expect(screen.getByLabelText("Заголовок")).toHaveFocus();
  });

  it("closes on Escape and close button", async () => {
    const handleClose = vi.fn();

    render(
      <Modal title="Новая заявка" onClose={handleClose}>
        <input aria-label="Заголовок" />
      </Modal>
    );

    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: "Закрыть" }));

    expect(handleClose).toHaveBeenCalledTimes(2);
  });

  it("cannot be dismissed while submission is in progress", async () => {
    const handleClose = vi.fn();

    render(
      <Modal title="Новая заявка" onClose={handleClose} isDismissDisabled>
        <input aria-label="Заголовок" />
      </Modal>
    );

    await userEvent.keyboard("{Escape}");

    expect(handleClose).not.toHaveBeenCalled();
  });
});
