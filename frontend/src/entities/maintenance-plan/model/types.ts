export const enum PlanScope {
  EQUIPMENT = "EQUIPMENT",
  CATEGORY = "CATEGORY",
}

export interface IChecklistTemplateItem {
  id: string;
  title: string;
  required: boolean;
  order: number;
}

export interface IChecklistTemplateItemInput {
  title: string;
  required: boolean;
  order: number;
}

export interface IMaintenancePlan {
  id: string;
  name: string;
  scope: PlanScope;
  equipment_id: string | null;
  category: string | null;
  interval_days: number;
  first_due_on: string;
  enabled: boolean;
  checklist: IChecklistTemplateItem[];
  created_at: string;
  updated_at: string;
  version: number;
}

export interface IMaintenancePlanCreatePayload {
  name: string;
  scope: PlanScope;
  equipment_id: string | null;
  category: string | null;
  interval_days: number;
  first_due_on: string;
  checklist: IChecklistTemplateItemInput[];
}

export interface IMaintenancePlanPatchPayload {
  name?: string;
  interval_days?: number;
  enabled?: boolean;
  checklist?: IChecklistTemplateItemInput[];
}

export interface IMaintenancePlanListParams {
  limit: number;
  offset: number;
  q?: string;
  scope?: PlanScope | "";
  enabled?: boolean;
  category?: string;
  equipment_id?: string;
}

export const PLAN_SCOPES: readonly PlanScope[] = [
  PlanScope.EQUIPMENT,
  PlanScope.CATEGORY,
];

export const PLAN_LIMITS = {
  NAME_MIN: 2,
  NAME_MAX: 200,
  CATEGORY_MAX: 100,
  INTERVAL_MIN: 1,
  INTERVAL_MAX: 3650,
  CHECKLIST_MAX_ITEMS: 100,
  CHECKLIST_TITLE_MIN: 2,
  CHECKLIST_TITLE_MAX: 300,
  CHECKLIST_ORDER_MIN: 0,
  CHECKLIST_ORDER_MAX: 999,
} as const;
