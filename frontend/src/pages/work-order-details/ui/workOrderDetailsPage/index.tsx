"use client";

import { WorkOrderDetails } from "@widgets/work-order-details";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";

interface IWorkOrderDetailsPageProps {
  workOrderId: string;
}

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const WorkOrderDetailsPage = ({
  workOrderId,
}: IWorkOrderDetailsPageProps): ReactElement => {
  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <WorkOrderDetails workOrderId={workOrderId} />
    </RoleGate>
  );
};

export default WorkOrderDetailsPage;
