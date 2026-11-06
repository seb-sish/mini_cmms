import { WorkOrderStatus } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { IWorkOrder } from "@entities/work-order";
import { UserRole } from "@entities/user";
import { IUser } from "@entities/user";

export interface IWorkOrderActions {
  canEdit: boolean;
  canAssign: boolean;
  canReassign: boolean;
  canStart: boolean;
  canUpdateChecklist: boolean;
  canComplete: boolean;
  canClose: boolean;
  canCancel: boolean;
}

export const getWorkOrderActions = (
  viewer: IUser,
  workOrder: IWorkOrder
): IWorkOrderActions => {
  const isEngineer: boolean = viewer.role === UserRole.ENGINEER;
  const isAssignedTechnician: boolean =
    viewer.role === UserRole.TECHNICIAN && workOrder.assignee_id === viewer.id;
  const { status } = workOrder;

  return {
    canEdit: isEngineer && status === WorkOrderStatus.CREATED,
    canAssign: isEngineer && status === WorkOrderStatus.CREATED,
    canReassign:
      isEngineer &&
      (status === WorkOrderStatus.ASSIGNED ||
        status === WorkOrderStatus.IN_PROGRESS),
    canStart: isAssignedTechnician && status === WorkOrderStatus.ASSIGNED,
    canUpdateChecklist:
      isAssignedTechnician &&
      status === WorkOrderStatus.IN_PROGRESS &&
      workOrder.type === WorkOrderType.PLANNED,
    canComplete: isAssignedTechnician && status === WorkOrderStatus.IN_PROGRESS,
    canClose: isEngineer && status === WorkOrderStatus.COMPLETED,
    canCancel:
      isEngineer &&
      (status === WorkOrderStatus.CREATED ||
        status === WorkOrderStatus.ASSIGNED),
  };
};

export const hasAnyWorkOrderAction = (actions: IWorkOrderActions): boolean =>
  Object.values(actions).some(Boolean);
