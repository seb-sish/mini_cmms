"use client";

import { fetchMaintenancePlans } from "./maintenancePlanApi";
import { IMaintenancePlanListParams } from "../model/types";
import { fetchMaintenancePlan } from "./maintenancePlanApi";
import { keepPreviousData } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";

export const maintenancePlanKeys = {
  all: ["maintenance-plans"] as const,
  lists: () => [...maintenancePlanKeys.all, "list"] as const,
  list: (params: IMaintenancePlanListParams) =>
    [...maintenancePlanKeys.lists(), params] as const,
  details: () => [...maintenancePlanKeys.all, "detail"] as const,
  detail: (planId: string) =>
    [...maintenancePlanKeys.details(), planId] as const,
};

export const useMaintenancePlansQuery = (
  params: IMaintenancePlanListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: maintenancePlanKeys.list(params),
    queryFn: () => fetchMaintenancePlans(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export const useMaintenancePlanQuery = (
  planId: string,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: maintenancePlanKeys.detail(planId),
    queryFn: () => fetchMaintenancePlan(planId),
    staleTime: 60_000,
    enabled: isEnabled,
  });
