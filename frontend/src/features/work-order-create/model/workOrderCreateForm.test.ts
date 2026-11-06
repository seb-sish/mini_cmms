import { validateWorkOrderCreateForm } from "./workOrderCreateForm";
import { buildInitialWorkOrderValues } from "./workOrderCreateForm";
import { toWorkOrderCreatePayload } from "./workOrderCreateForm";
import { WorkOrderPriority } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";

describe("work order create form", () => {
  it("prefills repair order from fault", () => {
    const values = buildInitialWorkOrderValues({
      equipmentId: "eq",
      faultId: "fault",
    });

    expect(values).toMatchObject({
      type: WorkOrderType.REPAIR,
      equipment_id: "eq",
      fault_id: "fault",
      schedule_id: "",
      priority: WorkOrderPriority.NORMAL,
    });
    expect(values.title).not.toBe("");
  });

  it("ignores fault for planned orders", () => {
    const values = buildInitialWorkOrderValues({
      type: WorkOrderType.PLANNED,
      faultId: "fault",
      scheduleId: "s",
    });

    expect(values.fault_id).toBe("");
    expect(values.schedule_id).toBe("s");
  });

  it("requires schedule for planned orders", () => {
    const errors = validateWorkOrderCreateForm({
      ...buildInitialWorkOrderValues({
        type: WorkOrderType.PLANNED,
        equipmentId: "eq",
      }),
      title: "Плановое ТО",
      description: "Выполнить чек-лист",
    });

    expect(errors.schedule_id).toBeDefined();
    expect(errors.equipment_id).toBeUndefined();
  });

  it("validates title and description lengths", () => {
    const errors = validateWorkOrderCreateForm({
      ...buildInitialWorkOrderValues({ equipmentId: "eq" }),
      title: "ab",
      description: "abcd",
    });

    expect(errors.title).toBe("Минимальная длина: 3 симв.");
    expect(errors.description).toBe("Минимальная длина: 5 симв.");
  });

  it("builds repair payload with optional fault and no schedule", () => {
    const payload = toWorkOrderCreatePayload({
      ...buildInitialWorkOrderValues({ equipmentId: "eq" }),
      schedule_id: "leftover",
      title: " Ремонт ",
      description: " Заменить ремень ",
    });

    expect(payload).toEqual({
      type: WorkOrderType.REPAIR,
      equipment_id: "eq",
      fault_id: null,
      schedule_id: null,
      title: "Ремонт",
      description: "Заменить ремень",
      priority: WorkOrderPriority.NORMAL,
    });
  });

  it("builds planned payload with schedule and without fault", () => {
    const payload = toWorkOrderCreatePayload({
      ...buildInitialWorkOrderValues({
        type: WorkOrderType.PLANNED,
        equipmentId: "eq",
        scheduleId: "s",
      }),
      fault_id: "leftover",
      title: "ТО",
      description: "Плановое ТО",
    });

    expect(payload.schedule_id).toBe("s");
    expect(payload.fault_id).toBeNull();
  });
});
