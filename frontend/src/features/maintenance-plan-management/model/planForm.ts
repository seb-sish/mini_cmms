import { IMaintenancePlanCreatePayload } from "@entities/maintenance-plan";
import { IMaintenancePlanPatchPayload } from "@entities/maintenance-plan";
import { IChecklistTemplateItemInput } from "@entities/maintenance-plan";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { PLAN_LIMITS } from "@entities/maintenance-plan";
import { validateIntegerRange } from "@shared/lib/form";
import { PlanScope } from "@entities/maintenance-plan";
import { normalizeText } from "@shared/lib/form";
import { validateText } from "@shared/lib/form";
import { validateDate } from "@shared/lib/form";
import { FormErrors } from "@shared/lib/form";

export interface IChecklistDraftItem {
  key: string;
  title: string;
  required: boolean;
}

export interface IPlanFormValues {
  name: string;
  scope: PlanScope;
  equipment_id: string;
  category: string;
  interval_days: string;
  first_due_on: string;
  checklist: IChecklistDraftItem[];
}

export interface IPlanFormErrors
  extends FormErrors<Omit<IPlanFormValues, "checklist">> {
  checklist?: string;
  checklistItems?: Record<string, string>;
}

let draftKeyCounter = 0;

export const createChecklistDraftItem = (
  title: string = "",
  required: boolean = true
): IChecklistDraftItem => {
  draftKeyCounter += 1;

  return { key: `draft-${draftKeyCounter}`, title, required };
};

export const buildInitialPlanValues = (today: string): IPlanFormValues => ({
  name: "",
  scope: PlanScope.EQUIPMENT,
  equipment_id: "",
  category: "",
  interval_days: "30",
  first_due_on: today,
  checklist: [createChecklistDraftItem()],
});

export const toPlanFormValues = (plan: IMaintenancePlan): IPlanFormValues => ({
  name: plan.name,
  scope: plan.scope,
  equipment_id: plan.equipment_id ?? "",
  category: plan.category ?? "",
  interval_days: String(plan.interval_days),
  first_due_on: plan.first_due_on,
  checklist: [...plan.checklist]
    .sort((left, right) => left.order - right.order)
    .map((item) => createChecklistDraftItem(item.title, item.required)),
});

export const normalizeChecklistTitle = (title: string): string =>
  title.trim().replace(/\s+/g, " ");

export const validateChecklist = (
  checklist: IChecklistDraftItem[]
): Pick<IPlanFormErrors, "checklist" | "checklistItems"> => {
  if (checklist.length === 0)
    return { checklist: "Добавьте хотя бы одну операцию." };

  if (checklist.length > PLAN_LIMITS.CHECKLIST_MAX_ITEMS) {
    return {
      checklist: `Не более ${PLAN_LIMITS.CHECKLIST_MAX_ITEMS} операций.`,
    };
  }

  const seenTitles = new Set<string>();
  const checklistItems: Record<string, string> = {};

  checklist.forEach((item) => {
    const title = normalizeChecklistTitle(item.title);
    const textError = validateText(title, {
      isRequired: true,
      minLength: PLAN_LIMITS.CHECKLIST_TITLE_MIN,
      maxLength: PLAN_LIMITS.CHECKLIST_TITLE_MAX,
    });

    if (textError) {
      checklistItems[item.key] = textError;
      return;
    }

    if (seenTitles.has(title))
      checklistItems[item.key] = "Такая операция уже есть в списке.";

    seenTitles.add(title);
  });

  return Object.keys(checklistItems).length > 0 ? { checklistItems } : {};
};

export const validatePlanForm = (
  values: IPlanFormValues,
  isEditMode: boolean
): IPlanFormErrors => ({
  name: validateText(values.name, {
    isRequired: true,
    minLength: PLAN_LIMITS.NAME_MIN,
    maxLength: PLAN_LIMITS.NAME_MAX,
  }),
  equipment_id:
    !isEditMode && values.scope === PlanScope.EQUIPMENT && !values.equipment_id
      ? "Выберите оборудование."
      : undefined,
  category:
    !isEditMode && values.scope === PlanScope.CATEGORY
      ? validateText(values.category, {
          isRequired: true,
          maxLength: PLAN_LIMITS.CATEGORY_MAX,
        })
      : undefined,
  interval_days: validateIntegerRange(values.interval_days, {
    min: PLAN_LIMITS.INTERVAL_MIN,
    max: PLAN_LIMITS.INTERVAL_MAX,
  }),
  first_due_on: isEditMode
    ? undefined
    : validateDate(values.first_due_on, { isRequired: true }),
  ...validateChecklist(values.checklist),
});

export const hasPlanFormErrors = (errors: IPlanFormErrors): boolean =>
  Object.entries(errors).some(([key, value]) =>
    key === "checklistItems"
      ? Object.keys(value ?? {}).length > 0
      : Boolean(value)
  );

export const toChecklistPayload = (
  checklist: IChecklistDraftItem[]
): IChecklistTemplateItemInput[] =>
  checklist.map((item, index) => ({
    title: normalizeChecklistTitle(item.title),
    required: item.required,
    order: index + 1,
  }));

export const toPlanCreatePayload = (
  values: IPlanFormValues
): IMaintenancePlanCreatePayload => ({
  name: normalizeText(values.name),
  scope: values.scope,
  equipment_id:
    values.scope === PlanScope.EQUIPMENT ? values.equipment_id : null,
  category:
    values.scope === PlanScope.CATEGORY ? normalizeText(values.category) : null,
  interval_days: Number(values.interval_days),
  first_due_on: values.first_due_on,
  checklist: toChecklistPayload(values.checklist),
});

const isSameChecklist = (
  plan: IMaintenancePlan,
  checklist: IChecklistTemplateItemInput[]
): boolean => {
  const current = [...plan.checklist]
    .sort((left, right) => left.order - right.order)
    .map((item) => ({ title: item.title, required: item.required }));

  return (
    current.length === checklist.length &&
    current.every(
      (item, index) =>
        item.title === checklist[index].title &&
        item.required === checklist[index].required
    )
  );
};

export const buildPlanPatchPayload = (
  plan: IMaintenancePlan,
  values: IPlanFormValues
): IMaintenancePlanPatchPayload => {
  const payload: IMaintenancePlanPatchPayload = {};
  const name = normalizeText(values.name);
  const intervalDays = Number(values.interval_days);
  const checklist = toChecklistPayload(values.checklist);

  if (name !== plan.name) payload.name = name;
  if (intervalDays !== plan.interval_days) payload.interval_days = intervalDays;
  if (!isSameChecklist(plan, checklist)) payload.checklist = checklist;

  return payload;
};
