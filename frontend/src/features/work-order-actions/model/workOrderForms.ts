import { IWorkOrderCompletePayload } from "@entities/work-order";
import { IWorkOrderPatchPayload } from "@entities/work-order";
import { WORK_ORDER_LIMITS } from "@entities/work-order";
import { WorkOrderPriority } from "@entities/work-order";
import { IWorkOrder } from "@entities/work-order";
import { normalizeText } from "@shared/lib/form";
import { validateText } from "@shared/lib/form";
import { FormErrors } from "@shared/lib/form";

export interface IWorkOrderEditFormValues {
  title: string;
  description: string;
  priority: WorkOrderPriority;
}

export interface IWorkOrderCompleteFormValues {
  result: string;
  replacedParts: string[];
  partDraft: string;
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const toWorkOrderEditValues = (
  workOrder: IWorkOrder
): IWorkOrderEditFormValues => ({
  title: workOrder.title,
  description: workOrder.description,
  priority: workOrder.priority,
});

export const validateWorkOrderEditForm = (
  values: IWorkOrderEditFormValues
): FormErrors<IWorkOrderEditFormValues> => ({
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

export const buildWorkOrderPatchPayload = (
  workOrder: IWorkOrder,
  values: IWorkOrderEditFormValues
): IWorkOrderPatchPayload => {
  const payload: IWorkOrderPatchPayload = {};
  const title = normalizeText(values.title);
  const description = normalizeText(values.description);

  if (title !== workOrder.title) payload.title = title;
  if (description !== workOrder.description) payload.description = description;
  if (values.priority !== workOrder.priority)
    payload.priority = values.priority;

  return payload;
};

export const INITIAL_COMPLETE_VALUES: IWorkOrderCompleteFormValues = {
  result: "",
  replacedParts: [],
  partDraft: "",
};

export const validateReplacedPart = (
  part: string,
  existingParts: string[]
): string | undefined => {
  const normalizedPart = normalizeText(part);
  const lengthError = validateText(normalizedPart, {
    isRequired: true,
    maxLength: WORK_ORDER_LIMITS.REPLACED_PART_MAX,
  });

  if (lengthError) return lengthError;

  if (existingParts.length >= WORK_ORDER_LIMITS.REPLACED_PARTS_MAX_ITEMS) {
    return `Не более ${WORK_ORDER_LIMITS.REPLACED_PARTS_MAX_ITEMS} деталей.`;
  }

  return undefined;
};

export const validateCompleteForm = (
  values: IWorkOrderCompleteFormValues
): FormErrors<IWorkOrderCompleteFormValues> => ({
  result: validateText(values.result, {
    isRequired: true,
    maxLength: WORK_ORDER_LIMITS.RESULT_MAX,
  }),
  partDraft: normalizeText(values.partDraft)
    ? 'Добавьте деталь в список кнопкой "Добавить" или очистите поле.'
    : undefined,
});

export const toCompletePayload = (
  values: IWorkOrderCompleteFormValues
): IWorkOrderCompletePayload => ({
  result: normalizeText(values.result),
  replaced_parts: values.replacedParts,
});

export const validateCancellationReason = (
  reason: string
): string | undefined =>
  validateText(reason, {
    isRequired: true,
    maxLength: WORK_ORDER_LIMITS.CANCELLATION_REASON_MAX,
  });

export const validateAssigneeId = (assigneeId: string): string | undefined => {
  if (!assigneeId.trim()) return "Выберите исполнителя.";

  return UUID_PATTERN.test(assigneeId.trim())
    ? undefined
    : "Некорректный идентификатор техника.";
};
