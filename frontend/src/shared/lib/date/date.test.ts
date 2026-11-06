import { getCompanyToday } from "./index";
import { formatDateTime } from "./index";
import { toCompanyDate } from "./index";
import { diffInDays } from "./index";
import { formatDate } from "./index";
import { isIsoDate } from "./index";
import { addDays } from "./index";

const MOSCOW = "Europe/Moscow";

describe("date helpers", () => {
  it("formats ISO date as dd.mm.yyyy", () => {
    expect(formatDate("2026-11-05")).toBe("05.11.2026");
  });

  it("formats timestamp in company timezone", () => {
    expect(formatDateTime("2026-11-05T20:30:00Z", MOSCOW)).toBe(
      "05.11.2026, 23:30"
    );
  });

  it("uses company timezone for local today", () => {
    expect(getCompanyToday(new Date("2026-10-06T21:30:00Z"), MOSCOW)).toBe(
      "2026-10-07"
    );
    expect(getCompanyToday(new Date("2026-10-06T20:59:59Z"), MOSCOW)).toBe(
      "2026-10-06"
    );
  });

  it("converts completion timestamp to company date", () => {
    expect(toCompanyDate("2026-11-05T20:30:00Z", MOSCOW)).toBe("2026-11-05");
  });

  it("adds days across month, year and leap boundaries", () => {
    expect(addDays("2026-11-05", 30)).toBe("2026-12-05");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2028-02-28", 1)).toBe("2028-02-29");
    expect(addDays("2026-11-05", -29)).toBe("2026-10-07");
  });

  it("calculates difference in days", () => {
    expect(diffInDays("2026-10-29", "2026-11-01")).toBe(3);
    expect(diffInDays("2026-10-29", "2026-10-25")).toBe(-4);
  });

  it("validates ISO dates strictly", () => {
    expect(isIsoDate("2026-02-28")).toBe(true);
    expect(isIsoDate("2026-02-30")).toBe(false);
    expect(isIsoDate("05.11.2026")).toBe(false);
  });
});
