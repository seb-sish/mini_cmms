import Button from "./index";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/react";
import { ButtonAppearance } from "./index";
import { IconName } from "@shared/ui/icon";

describe("Button", () => {
  it("calls onClick", async () => {
    const handleClick = vi.fn();

    render(
      <Button
        label="Сохранить"
        appearance={ButtonAppearance.PRIMARY}
        onClick={handleClick}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and busy while loading", () => {
    render(<Button label="Сохранить" isLoading />);

    const button = screen.getByRole("button", { name: /Сохранить/ });

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("uses label as accessible name for icon-only buttons", () => {
    render(<Button label="Закрыть" iconBefore={IconName.CLOSE} isIconOnly />);

    expect(screen.getByRole("button", { name: "Закрыть" })).toHaveAttribute(
      "title",
      "Закрыть"
    );
  });
});
