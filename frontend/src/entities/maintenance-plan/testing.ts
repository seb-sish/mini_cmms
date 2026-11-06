import { IMaintenancePlan } from "./model/types";
import { PlanScope } from "./model/types";

export const buildMaintenancePlanFixture = (
  overrides: Partial<IMaintenancePlan> = {}
): IMaintenancePlan => ({
  id: "plan-1",
  name: "ТО компрессоров",
  scope: PlanScope.CATEGORY,
  equipment_id: null,
  category: "Компрессоры",
  interval_days: 30,
  first_due_on: "2026-11-05",
  enabled: true,
  checklist: [
    { id: "item-2", title: "Очистить фильтр", required: false, order: 2 },
    {
      id: "item-1",
      title: "Проверить уровень масла",
      required: true,
      order: 1,
    },
  ],
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  version: 1,
  ...overrides,
});
