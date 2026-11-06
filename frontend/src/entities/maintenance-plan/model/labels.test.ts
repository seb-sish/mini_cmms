import { formatInterval } from "./labels";

describe("formatInterval", () => {
  it.each([
    [1, "1 день"],
    [2, "2 дня"],
    [5, "5 дней"],
    [11, "11 дней"],
    [21, "21 день"],
    [14, "14 дней"],
    [30, "30 дней"],
    [3650, "3650 дней"],
  ])("formats %i days", (days, expected) => {
    expect(formatInterval(days)).toBe(expected);
  });
});
