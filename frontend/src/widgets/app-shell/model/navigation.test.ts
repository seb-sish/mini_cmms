import { isNavigationItemActive } from "./navigation";
import { getRolePermissions } from "@entities/user";
import { NAVIGATION_ITEMS } from "./navigation";
import { UserRole } from "@entities/user";

const getVisibleLabels = (role: UserRole): string[] =>
  NAVIGATION_ITEMS.filter((item) =>
    item.isVisible(getRolePermissions(role))
  ).map((item) => item.label);

describe("navigation", () => {
  it("shows only user management to administrator", () => {
    expect(getVisibleLabels(UserRole.ADMIN)).toEqual(["Пользователи"]);
  });

  it("hides plans, schedule and notifications from operator", () => {
    expect(getVisibleLabels(UserRole.OPERATOR)).toEqual([
      "Обзор",
      "Заявки",
      "Оборудование",
      "Неисправности",
      "История работ",
    ]);
  });

  it("shows full production navigation to engineer", () => {
    expect(getVisibleLabels(UserRole.ENGINEER)).not.toContain("Пользователи");
    expect(getVisibleLabels(UserRole.ENGINEER)).toContain("Регламенты ТО");
  });

  it("matches nested routes but keeps home exact", () => {
    expect(isNavigationItemActive("/work-orders/123", "/work-orders")).toBe(
      true
    );
    expect(isNavigationItemActive("/work-orders-archive", "/work-orders")).toBe(
      false
    );
    expect(isNavigationItemActive("/equipment", "/")).toBe(false);
    expect(isNavigationItemActive("/", "/")).toBe(true);
  });
});
