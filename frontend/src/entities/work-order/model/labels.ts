import { LozengeAppearance } from "@shared/ui/lozenge";
import { WorkOrderEventType } from "./types";
import { WorkOrderPriority } from "./types";
import { IconName } from "@shared/ui/icon";
import { WorkOrderStatus } from "./types";
import { WorkOrderType } from "./types";

export const WORK_ORDER_TYPE_LABELS: Record<WorkOrderType, string> = {
  [WorkOrderType.REPAIR]: "Ремонт",
  [WorkOrderType.PLANNED]: "Плановое ТО",
};

export const WORK_ORDER_STATUS_LABELS: Record<WorkOrderStatus, string> = {
  [WorkOrderStatus.CREATED]: "Создана",
  [WorkOrderStatus.ASSIGNED]: "Назначена",
  [WorkOrderStatus.IN_PROGRESS]: "В работе",
  [WorkOrderStatus.COMPLETED]: "Выполнена",
  [WorkOrderStatus.CLOSED]: "Закрыта",
  [WorkOrderStatus.CANCELLED]: "Отменена",
};

export const WORK_ORDER_STATUS_APPEARANCES: Record<
  WorkOrderStatus,
  LozengeAppearance
> = {
  [WorkOrderStatus.CREATED]: LozengeAppearance.NEW,
  [WorkOrderStatus.ASSIGNED]: LozengeAppearance.DEFAULT,
  [WorkOrderStatus.IN_PROGRESS]: LozengeAppearance.IN_PROGRESS,
  [WorkOrderStatus.COMPLETED]: LozengeAppearance.MOVED,
  [WorkOrderStatus.CLOSED]: LozengeAppearance.SUCCESS,
  [WorkOrderStatus.CANCELLED]: LozengeAppearance.REMOVED,
};

export const WORK_ORDER_PRIORITY_LABELS: Record<WorkOrderPriority, string> = {
  [WorkOrderPriority.LOW]: "Низкий",
  [WorkOrderPriority.NORMAL]: "Обычный",
  [WorkOrderPriority.HIGH]: "Высокий",
  [WorkOrderPriority.CRITICAL]: "Критический",
};

export const WORK_ORDER_PRIORITY_ICONS: Record<WorkOrderPriority, IconName> = {
  [WorkOrderPriority.LOW]: IconName.PRIORITY_LOW,
  [WorkOrderPriority.NORMAL]: IconName.PRIORITY_NORMAL,
  [WorkOrderPriority.HIGH]: IconName.PRIORITY_HIGH,
  [WorkOrderPriority.CRITICAL]: IconName.PRIORITY_CRITICAL,
};

export const WORK_ORDER_EVENT_LABELS: Record<WorkOrderEventType, string> = {
  [WorkOrderEventType.CREATED]: "создал(а) заявку",
  [WorkOrderEventType.ASSIGNED]: "назначил(а) исполнителя",
  [WorkOrderEventType.REASSIGNED]: "переназначил(а) исполнителя",
  [WorkOrderEventType.STARTED]: "начал(а) работу",
  [WorkOrderEventType.UPDATED]: "изменил(а) заявку",
  [WorkOrderEventType.CHECKLIST_ITEM_UPDATED]: "обновил(а) пункт чек-листа",
  [WorkOrderEventType.COMPLETED]: "отметил(а) выполнение",
  [WorkOrderEventType.CLOSED]: "принял(а) работу и закрыл(а) заявку",
  [WorkOrderEventType.CANCELLED]: "отменил(а) заявку",
};
