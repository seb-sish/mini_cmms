"use client";

import PageHeader from "@shared/ui/pageHeader";
import { NotificationList } from "@widgets/notification-list";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";

const ALLOWED_ROLES: UserRole[] = [UserRole.ENGINEER, UserRole.TECHNICIAN];

const NotificationListPage = (): ReactElement => {
  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader title="Уведомления" />
      <NotificationList />
    </RoleGate>
  );
};

export default NotificationListPage;
