"use client";

import PageHeader from "@shared/ui/pageHeader";
import { ScheduleTable } from "@widgets/schedule-table";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import "./style.css";

const ALLOWED_ROLES: UserRole[] = [UserRole.ENGINEER, UserRole.TECHNICIAN];

const ScheduleListPage = (): ReactElement => {
  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader title="График технического обслуживания" />
      <p className="text-subtle schedule-list-hint">
        Сроки отсортированы от ближайшего. Просрочкой считается срок раньше
        сегодняшнего дня без выполненной работы.
      </p>
      <ScheduleTable />
    </RoleGate>
  );
};

export default ScheduleListPage;
