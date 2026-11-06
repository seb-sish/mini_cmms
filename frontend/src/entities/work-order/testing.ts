import { WorkOrderPriority } from "./model/types";
import { WorkOrderStatus } from "./model/types";
import { WorkOrderType } from "./model/types";
import { IWorkOrder } from "./model/types";

export const buildWorkOrderFixture = (
  overrides: Partial<IWorkOrder> = {}
): IWorkOrder => ({
  id: "wo-1",
  number: "WO-1",
  type: WorkOrderType.REPAIR,
  equipment_id: "equipment-1",
  fault_id: null,
  schedule_id: null,
  planned_due_on: null,
  title: "Замена подшипника",
  description: "Заменить подшипник",
  priority: WorkOrderPriority.NORMAL,
  status: WorkOrderStatus.CREATED,
  author_id: "author-1",
  assignee_id: null,
  checklist: [],
  result: null,
  replaced_parts: [],
  completed_at: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  closed_at: null,
  version: 1,
  cancelled_at: null,
  cancelled_by: null,
  cancellation_reason: null,
  ...overrides,
});
