"use client";

import PageHeader from "@shared/ui/pageHeader";
import { HistoryTable } from "@widgets/history-table";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const HistoryListPage = (): ReactElement => {
  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader title="История выполненных работ" />
      <HistoryTable />
    </RoleGate>
  );
};

export default HistoryListPage;
