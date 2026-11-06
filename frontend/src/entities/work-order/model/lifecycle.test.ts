import { getEarliestCompletionDate } from "./lifecycle";
import { getMissingRequiredItems } from "./lifecycle";
import { isTooEarlyToComplete } from "./lifecycle";
import { isUnfinishedStatus } from "./lifecycle";
import { isTerminalStatus } from "./lifecycle";
import { IWorkChecklistItem } from "./types";
import { sortChecklist } from "./lifecycle";
import { WorkOrderStatus } from "./types";

const buildItem = (
  overrides: Partial<IWorkChecklistItem>
): IWorkChecklistItem => ({
  id: "item",
  title: "Операция",
  required: true,
  order: 1,
  checked: false,
  comment: null,
  checked_at: null,
  ...overrides,
});

describe("work order lifecycle", () => {
  it("follows contract example for early completion of planned maintenance", () => {
    expect(isTooEarlyToComplete("2026-10-06", "2026-11-05", 30)).toBe(true);
    expect(isTooEarlyToComplete("2026-10-07", "2026-11-05", 30)).toBe(false);
    expect(getEarliestCompletionDate("2026-11-05", 30)).toBe("2026-10-07");
  });

  it("allows one-day interval only on due date or later", () => {
    expect(isTooEarlyToComplete("2026-11-04", "2026-11-05", 1)).toBe(true);
    expect(isTooEarlyToComplete("2026-11-05", "2026-11-05", 1)).toBe(false);
    expect(getEarliestCompletionDate("2026-11-05", 1)).toBe("2026-11-05");
  });

  it("returns only unchecked required checklist items", () => {
    const missing = getMissingRequiredItems([
      buildItem({ id: "a", required: true, checked: false }),
      buildItem({ id: "b", required: true, checked: true }),
      buildItem({ id: "c", required: false, checked: false }),
    ]);

    expect(missing.map((item) => item.id)).toEqual(["a"]);
  });

  it("sorts checklist by order and id without mutating input", () => {
    const items = [
      buildItem({ id: "b", order: 2 }),
      buildItem({ id: "z", order: 1 }),
      buildItem({ id: "a", order: 1 }),
    ];

    expect(sortChecklist(items).map((item) => item.id)).toEqual([
      "a",
      "z",
      "b",
    ]);
    expect(items[0].id).toBe("b");
  });

  it("classifies terminal and unfinished statuses", () => {
    expect(isTerminalStatus(WorkOrderStatus.CLOSED)).toBe(true);
    expect(isTerminalStatus(WorkOrderStatus.CANCELLED)).toBe(true);
    expect(isTerminalStatus(WorkOrderStatus.COMPLETED)).toBe(false);
    expect(isUnfinishedStatus(WorkOrderStatus.COMPLETED)).toBe(true);
    expect(isUnfinishedStatus(WorkOrderStatus.CANCELLED)).toBe(false);
  });
});
