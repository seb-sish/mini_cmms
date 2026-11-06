"use client";

import { fetchMaintenanceSchedules } from "./maintenanceScheduleApi";
import { fetchMaintenanceSchedule } from "./maintenanceScheduleApi";
import { IMaintenanceScheduleListParams } from "../model/types";
import { keepPreviousData } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";

export const maintenanceScheduleKeys = {
  all: ["maintenance-schedules"] as const,
  lists: () => [...maintenanceScheduleKeys.all, "list"] as const,
  list: (params: IMaintenanceScheduleListParams) =>
    [...maintenanceScheduleKeys.lists(), params] as const,
  details: () => [...maintenanceScheduleKeys.all, "detail"] as const,
  detail: (scheduleId: string) =>
    [...maintenanceScheduleKeys.details(), scheduleId] as const,
};

export const useMaintenanceSchedulesQuery = (
  params: IMaintenanceScheduleListParams,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: maintenanceScheduleKeys.list(params),
    queryFn: () => fetchMaintenanceSchedules(params),
    placeholderData: keepPreviousData,
    enabled: isEnabled,
  });

export const useMaintenanceScheduleQuery = (
  scheduleId: string,
  isEnabled: boolean = true
) =>
  useQuery({
    queryKey: maintenanceScheduleKeys.detail(scheduleId),
    queryFn: () => fetchMaintenanceSchedule(scheduleId),
    enabled: isEnabled,
  });
