"use client";

import Link from "next/link";
import { useMaintenancePlanQuery } from "../../api/maintenancePlanQueries";
import { buildMaintenancePlanRoute } from "@shared/config";
import { shortenId } from "@shared/lib/options";
import { ReactElement } from "react";

interface IPlanNameProps {
  planId: string;
  isLink?: boolean;
}

const PlanName = ({ planId, isLink = true }: IPlanNameProps): ReactElement => {
  const { data: plan, isError } = useMaintenancePlanQuery(planId);

  if (isError) {
    return (
      <span className="text-subtlest" title={planId}>
        Регламент {shortenId(planId)}
      </span>
    );
  }

  if (!plan) return <span className="text-subtlest">Загрузка...</span>;

  if (!isLink) return <span>{plan.name}</span>;

  return <Link href={buildMaintenancePlanRoute(planId)}>{plan.name}</Link>;
};

export default PlanName;
