import { IMaintenancePlanCreatePayload } from "../model/types";
import { IMaintenancePlanPatchPayload } from "../model/types";
import { IMaintenancePlanListParams } from "../model/types";
import { IMaintenancePlan } from "../model/types";
import { buildIfMatch } from "@shared/api";
import { apiRequest } from "@shared/api";
import { HttpMethod } from "@shared/api";
import { IPage } from "@shared/api";

export const fetchMaintenancePlans = (
  params: IMaintenancePlanListParams
): Promise<IPage<IMaintenancePlan>> =>
  apiRequest<IPage<IMaintenancePlan>>("/maintenance-plans", {
    query: { ...params },
  });

export const fetchMaintenancePlan = (
  planId: string
): Promise<IMaintenancePlan> =>
  apiRequest<IMaintenancePlan>(`/maintenance-plans/${planId}`);

export const createMaintenancePlan = (
  payload: IMaintenancePlanCreatePayload
): Promise<IMaintenancePlan> =>
  apiRequest<IMaintenancePlan>("/maintenance-plans", {
    method: HttpMethod.POST,
    body: payload,
  });

export const updateMaintenancePlan = (
  plan: IMaintenancePlan,
  payload: IMaintenancePlanPatchPayload
): Promise<IMaintenancePlan> =>
  apiRequest<IMaintenancePlan>(`/maintenance-plans/${plan.id}`, {
    method: HttpMethod.PATCH,
    body: payload,
    ifMatch: buildIfMatch(plan.id, plan.version),
  });
