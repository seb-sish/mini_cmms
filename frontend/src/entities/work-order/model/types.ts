export const enum WorkOrderType {
  REPAIR = "REPAIR",
  PLANNED = "PLANNED",
}

export const enum WorkOrderStatus {
  CREATED = "CREATED",
  ASSIGNED = "ASSIGNED",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  CLOSED = "CLOSED",
  CANCELLED = "CANCELLED",
}

export const enum WorkOrderPriority {
  LOW = "LOW",
  NORMAL = "NORMAL",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

export const enum WorkOrderEventType {
  CREATED = "CREATED",
  ASSIGNED = "ASSIGNED",
  REASSIGNED = "REASSIGNED",
  STARTED = "STARTED",
  UPDATED = "UPDATED",
  CHECKLIST_ITEM_UPDATED = "CHECKLIST_ITEM_UPDATED",
  COMPLETED = "COMPLETED",
  CLOSED = "CLOSED",
  CANCELLED = "CANCELLED",
}

export const enum WorkOrderSort {
  CREATED_ASC = "created_at",
  CREATED_DESC = "-created_at",
  STATUS_ASC = "status",
  STATUS_DESC = "-status",
}

export interface IWorkChecklistItem {
  id: string;
  title: string;
  required: boolean;
  order: number;
  checked: boolean;
  comment: string | null;
  checked_at: string | null;
}

export interface IWorkOrder {
  id: string;
  number: string;
  type: WorkOrderType;
  equipment_id: string;
  fault_id: string | null;
  schedule_id: string | null;
  planned_due_on: string | null;
  title: string;
  description: string;
  priority: WorkOrderPriority;
  status: WorkOrderStatus;
  author_id: string;
  assignee_id: string | null;
  checklist: IWorkChecklistItem[];
  result: string | null;
  replaced_parts: string[];
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  version: number;
  cancelled_at: string | null;
  cancelled_by: string | null;
  cancellation_reason: string | null;
}

export interface IWorkOrderEvent {
  id: string;
  work_order_id: string;
  event_type: WorkOrderEventType;
  actor_id: string;
  occurred_at: string;
  from_status: WorkOrderStatus | null;
  to_status: WorkOrderStatus | null;
  old_assignee_id: string | null;
  new_assignee_id: string | null;
  details: string | null;
}

export interface IWorkOrderCreatePayload {
  type: WorkOrderType;
  equipment_id: string;
  fault_id: string | null;
  schedule_id: string | null;
  title: string;
  description: string;
  priority: WorkOrderPriority;
}

export interface IWorkOrderPatchPayload {
  title?: string;
  description?: string;
  priority?: WorkOrderPriority;
}

export interface IWorkOrderCompletePayload {
  result: string;
  replaced_parts: string[];
}

export interface IChecklistItemUpdatePayload {
  checked: boolean;
  comment?: string | null;
}

export interface IWorkOrderListParams {
  limit: number;
  offset: number;
  q?: string;
  equipment_id?: string;
  type?: WorkOrderType | "";
  status?: WorkOrderStatus | "";
  priority?: WorkOrderPriority | "";
  assignee_id?: string;
  fault_id?: string;
  schedule_id?: string;
  sort?: WorkOrderSort;
}

export const WORK_ORDER_TYPES: readonly WorkOrderType[] = [
  WorkOrderType.REPAIR,
  WorkOrderType.PLANNED,
];

export const WORK_ORDER_STATUSES: readonly WorkOrderStatus[] = [
  WorkOrderStatus.CREATED,
  WorkOrderStatus.ASSIGNED,
  WorkOrderStatus.IN_PROGRESS,
  WorkOrderStatus.COMPLETED,
  WorkOrderStatus.CLOSED,
  WorkOrderStatus.CANCELLED,
];

export const WORK_ORDER_PRIORITIES: readonly WorkOrderPriority[] = [
  WorkOrderPriority.LOW,
  WorkOrderPriority.NORMAL,
  WorkOrderPriority.HIGH,
  WorkOrderPriority.CRITICAL,
];

export const WORK_ORDER_LIMITS = {
  TITLE_MIN: 3,
  TITLE_MAX: 200,
  DESCRIPTION_MIN: 5,
  DESCRIPTION_MAX: 2000,
  RESULT_MAX: 4000,
  REPLACED_PART_MAX: 200,
  REPLACED_PARTS_MAX_ITEMS: 100,
  CANCELLATION_REASON_MAX: 1000,
  CHECKLIST_COMMENT_MAX: 1000,
} as const;
