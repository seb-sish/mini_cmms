import { IWorkChecklistItem } from "./types";
import { addDays } from "@shared/lib/date";
import { WorkOrderStatus } from "./types";

export const WORKFLOW_STATUSES: readonly WorkOrderStatus[] = [
  WorkOrderStatus.CREATED,
  WorkOrderStatus.ASSIGNED,
  WorkOrderStatus.IN_PROGRESS,
  WorkOrderStatus.COMPLETED,
  WorkOrderStatus.CLOSED,
];

export const UNFINISHED_STATUSES: readonly WorkOrderStatus[] = [
  WorkOrderStatus.CREATED,
  WorkOrderStatus.ASSIGNED,
  WorkOrderStatus.IN_PROGRESS,
  WorkOrderStatus.COMPLETED,
];

export const isTerminalStatus = (status: WorkOrderStatus): boolean =>
  status === WorkOrderStatus.CLOSED || status === WorkOrderStatus.CANCELLED;

export const isUnfinishedStatus = (status: WorkOrderStatus): boolean =>
  UNFINISHED_STATUSES.includes(status);

export const getMissingRequiredItems = (
  checklist: IWorkChecklistItem[]
): IWorkChecklistItem[] =>
  checklist.filter((item) => item.required && !item.checked);

export const sortChecklist = (
  checklist: IWorkChecklistItem[]
): IWorkChecklistItem[] =>
  [...checklist].sort(
    (left, right) => left.order - right.order || left.id.localeCompare(right.id)
  );

export const getEarliestCompletionDate = (
  plannedDueOn: string,
  intervalDays: number
): string => addDays(plannedDueOn, 1 - intervalDays);

export const isTooEarlyToComplete = (
  companyToday: string,
  plannedDueOn: string,
  intervalDays: number
): boolean => addDays(companyToday, intervalDays) <= plannedDueOn;
