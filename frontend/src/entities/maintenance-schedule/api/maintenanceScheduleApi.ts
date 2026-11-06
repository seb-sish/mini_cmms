import { IMaintenanceScheduleListParams } from "../model/types";
import { IMaintenanceSchedule } from "../model/types";
import { apiRequest } from "@shared/api";
import { IPage } from "@shared/api";

export const fetchMaintenanceSchedules = (
  params: IMaintenanceScheduleListParams
): Promise<IPage<IMaintenanceSchedule>> =>
  apiRequest<IPage<IMaintenanceSchedule>>("/maintenance-schedules", {
    query: { ...params },
  });

export const fetchMaintenanceSchedule = (
  scheduleId: string
): Promise<IMaintenanceSchedule> =>
  apiRequest<IMaintenanceSchedule>(`/maintenance-schedules/${scheduleId}`);
