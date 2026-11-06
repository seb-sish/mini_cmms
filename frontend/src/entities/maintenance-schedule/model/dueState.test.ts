import { getScheduleDueState } from "./dueState";
import { getScheduleDueLabel } from "./dueState";
import { IMaintenanceSchedule } from "./types";
import { ScheduleDueState } from "./dueState";

const TODAY = "2026-10-29";

const buildSchedule = (
  overrides: Partial<IMaintenanceSchedule>
): IMaintenanceSchedule => ({
  id: "schedule",
  plan_id: "plan",
  equipment_id: "equipment",
  last_completed_on: null,
  next_due_on: TODAY,
  is_overdue: false,
  has_current_work_order: false,
  active: true,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  ...overrides,
});

describe("schedule due state", () => {
  it("treats due date itself as today, not overdue", () => {
    const schedule = buildSchedule({ next_due_on: TODAY });

    expect(getScheduleDueState(schedule, TODAY)).toBe(ScheduleDueState.TODAY);
    expect(getScheduleDueLabel(schedule, TODAY)).toBe("Сегодня");
  });

  it("relies on server overdue flag", () => {
    const schedule = buildSchedule({
      next_due_on: "2026-10-25",
      is_overdue: true,
    });

    expect(getScheduleDueState(schedule, TODAY)).toBe(ScheduleDueState.OVERDUE);
    expect(getScheduleDueLabel(schedule, TODAY)).toBe("Просрочено на 4 дн.");
  });

  it("highlights the three-day reminder window", () => {
    expect(
      getScheduleDueState(buildSchedule({ next_due_on: "2026-11-01" }), TODAY)
    ).toBe(ScheduleDueState.SOON);
    expect(
      getScheduleDueState(buildSchedule({ next_due_on: "2026-11-02" }), TODAY)
    ).toBe(ScheduleDueState.UPCOMING);
  });

  it("shows inactive schedules regardless of dates", () => {
    const schedule = buildSchedule({
      active: false,
      is_overdue: false,
      next_due_on: "2026-10-01",
    });

    expect(getScheduleDueState(schedule, TODAY)).toBe(
      ScheduleDueState.INACTIVE
    );
  });
});
