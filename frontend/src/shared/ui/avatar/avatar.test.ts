import { getAvatarInitials } from "./index";
import { getAvatarColor } from "./index";

describe("avatar helpers", () => {
  it("builds initials from login parts", () => {
    expect(getAvatarInitials("fe_engineer")).toBe("FE");
    expect(getAvatarInitials("ivan.petrov")).toBe("IP");
    expect(getAvatarInitials("admin")).toBe("A");
  });

  it("returns stable color for the same name", () => {
    expect(getAvatarColor("admin")).toBe(getAvatarColor("admin"));
  });
});
