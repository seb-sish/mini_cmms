import { IChecklistItemUpdatePayload } from "../model/types";
import { IWorkOrderCompletePayload } from "../model/types";
import { IWorkOrderCreatePayload } from "../model/types";
import { IWorkOrderPatchPayload } from "../model/types";
import { IWorkOrderListParams } from "../model/types";
import { IWorkChecklistItem } from "../model/types";
import { IWorkOrderEvent } from "../model/types";
import { IWorkOrder } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IPage } from "@shared/api";

const workOrderPath = (workOrderId: string): string =>
  `/work-orders/${workOrderId}`;

const postCommand = (
  workOrderId: string,
  command: string,
  body?: unknown
): Promise<IWorkOrder> =>
  apiRequest<IWorkOrder>(`${workOrderPath(workOrderId)}/${command}`, {
    method: HttpMethod.POST,
    body,
  });

export const fetchWorkOrders = (
  params: IWorkOrderListParams
): Promise<IPage<IWorkOrder>> =>
  apiRequest<IPage<IWorkOrder>>("/work-orders", { query: { ...params } });

export const fetchWorkOrder = (workOrderId: string): Promise<IWorkOrder> =>
  apiRequest<IWorkOrder>(workOrderPath(workOrderId));

export const fetchWorkOrderEvents = (
  workOrderId: string,
  limit: number,
  offset: number
): Promise<IPage<IWorkOrderEvent>> =>
  apiRequest<IPage<IWorkOrderEvent>>(`${workOrderPath(workOrderId)}/events`, {
    query: { limit, offset },
  });

export const createWorkOrder = (
  payload: IWorkOrderCreatePayload
): Promise<IWorkOrder> =>
  apiRequest<IWorkOrder>("/work-orders", {
    method: HttpMethod.POST,
    body: payload,
  });

export const updateWorkOrder = (
  workOrder: IWorkOrder,
  payload: IWorkOrderPatchPayload
): Promise<IWorkOrder> =>
  apiRequest<IWorkOrder>(workOrderPath(workOrder.id), {
    method: HttpMethod.PATCH,
    body: payload,
    ifMatch: buildIfMatch(workOrder.id, workOrder.version),
  });

export const assignWorkOrder = (
  workOrderId: string,
  assigneeId: string
): Promise<IWorkOrder> =>
  postCommand(workOrderId, "assign", { assignee_id: assigneeId });

export const reassignWorkOrder = (
  workOrderId: string,
  assigneeId: string
): Promise<IWorkOrder> =>
  postCommand(workOrderId, "reassign", { assignee_id: assigneeId });

export const startWorkOrder = (workOrderId: string): Promise<IWorkOrder> =>
  postCommand(workOrderId, "start");

export const completeWorkOrder = (
  workOrderId: string,
  payload: IWorkOrderCompletePayload
): Promise<IWorkOrder> => postCommand(workOrderId, "complete", payload);

export const closeWorkOrder = (workOrderId: string): Promise<IWorkOrder> =>
  postCommand(workOrderId, "close");

export const cancelWorkOrder = (
  workOrderId: string,
  reason: string
): Promise<IWorkOrder> => postCommand(workOrderId, "cancel", { reason });

export const updateChecklistItem = (
  workOrder: IWorkOrder,
  itemId: string,
  payload: IChecklistItemUpdatePayload
): Promise<IWorkChecklistItem> =>
  apiRequest<IWorkChecklistItem>(
    `${workOrderPath(workOrder.id)}/checklist/${itemId}`,
    {
      method: HttpMethod.PATCH,
      body: payload,
      ifMatch: buildIfMatch(workOrder.id, workOrder.version),
    }
  );
