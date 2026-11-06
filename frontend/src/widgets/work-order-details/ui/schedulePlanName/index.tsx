"use client";

import { useMaintenanceScheduleQuery } from "@entities/maintenance-schedule";
import { PlanName } from "@entities/maintenance-plan";
import { ReactElement } from "react";

interface ISchedulePlanNameProps {
  scheduleId: string;
}

const SchedulePlanName = ({
  scheduleId,
}: ISchedulePlanNameProps): ReactElement => {
  const { data: schedule, isError } = useMaintenanceScheduleQuery(scheduleId);

  if (isError)
    return <span className="text-subtlest">Регламент недоступен</span>;

  if (!schedule) return <span className="text-subtlest">Загрузка...</span>;

  return <PlanName planId={schedule.plan_id} />;
};

export default SchedulePlanName;
