import { IWorkOrderCreatePayload } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { WorkOrderPriority } from "@entities/work-order";
import { WorkOrderType } from "@entities/work-order";
import { normalizeText } from "@shared/lib/form";
import { validateText } from "@shared/lib/form";
import { FormErrors } from "@shared/lib/form";

export interface IWorkOrderCreateFormValues {
  type: WorkOrderType;
  equipment_id: string;
  fault_id: string;
  schedule_id: string;
  title: string;
  description: string;
  priority: WorkOrderPriority;
}

export interface IWorkOrderCreateInitial {
  type?: WorkOrderType;
  equipmentId?: string;
  faultId?: string;
  scheduleId?: string;
}

const DEFAULT_TITLES: Record<WorkOrderType, string> = {
  [WorkOrderType.REPAIR]: "Устранение неисправности",
  [WorkOrderType.PLANNED]: "Плановое техническое обслуживание",
};

export const buildInitialWorkOrderValues = ({
  type = WorkOrderType.REPAIR,
  equipmentId = "",
  faultId = "",
  scheduleId = "",
}: IWorkOrderCreateInitial): IWorkOrderCreateFormValues => ({
  type,
  equipment_id: equipmentId,
  fault_id: type === WorkOrderType.REPAIR ? faultId : "",
  schedule_id: type === WorkOrderType.PLANNED ? scheduleId : "",
  title: faultId || scheduleId ? DEFAULT_TITLES[type] : "",
  description: "",
  priority: WorkOrderPriority.NORMAL,
});

export const validateWorkOrderCreateForm = (
  values: IWorkOrderCreateFormValues
): FormErrors<IWorkOrderCreateFormValues> => ({
  equipment_id: values.equipment_id ? undefined : "Выберите оборудование.",
  schedule_id:
    values.type === WorkOrderType.PLANNED && !values.schedule_id
      ? "Для плановой заявки выберите график ТО."
      : undefined,
  title: validateText(values.title, {
    isRequired: true,
    minLength: WORK_ORDER_LIMITS.TITLE_MIN,
    maxLength: WORK_ORDER_LIMITS.TITLE_MAX,
  }),
  description: validateText(values.description, {
    isRequired: true,
    minLength: WORK_ORDER_LIMITS.DESCRIPTION_MIN,
    maxLength: WORK_ORDER_LIMITS.DESCRIPTION_MAX,
  }),
});

export const toWorkOrderCreatePayload = (
  values: IWorkOrderCreateFormValues
): IWorkOrderCreatePayload => ({
  type: values.type,
  equipment_id: values.equipment_id,
  fault_id:
    values.type === WorkOrderType.REPAIR && values.fault_id
      ? values.fault_id
      : null,
  schedule_id:
    values.type === WorkOrderType.PLANNED ? values.schedule_id : null,
  title: normalizeText(values.title),
  description: normalizeText(values.description),
  priority: values.priority,
});
