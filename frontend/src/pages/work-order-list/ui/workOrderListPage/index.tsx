"use client";

import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import { CreateWorkOrderModal } from "@features/work-order-create";
import { WorkOrderTable } from "@widgets/work-order-table";
import { useViewerPermissions } from "@entities/user";
import { buildWorkOrderRoute } from "@shared/config";
import { ButtonAppearance } from "@shared/ui/button";
import { IWorkOrder } from "@entities/work-order";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const PAGE_TITLES: Partial<Record<UserRole, string>> = {
  [UserRole.ENGINEER]: "Заявки на обслуживание",
  [UserRole.TECHNICIAN]: "Мои назначенные заявки",
  [UserRole.OPERATOR]: "Мои заявки",
};

const WorkOrderListPage = (): ReactElement => {
  const router = useRouter();
  const viewer = useViewer();
  const permissions = useViewerPermissions();
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  const openCreate = () => setIsCreateOpen(true);
  const closeCreate = () => setIsCreateOpen(false);

  const handleCreated = (workOrder: IWorkOrder) => {
    router.push(buildWorkOrderRoute(workOrder.id));
  };

  const createButton = permissions.canCreateWorkOrder ? (
    <Button
      label="Создать заявку"
      appearance={ButtonAppearance.PRIMARY}
      iconBefore={IconName.ADD}
      onClick={openCreate}
    />
  ) : undefined;

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader
        title={PAGE_TITLES[viewer.role] ?? "Заявки"}
        actions={createButton}
      />
      <WorkOrderTable emptyAction={createButton} />
      {isCreateOpen && (
        <CreateWorkOrderModal onClose={closeCreate} onCreated={handleCreated} />
      )}
    </RoleGate>
  );
};

export default WorkOrderListPage;
