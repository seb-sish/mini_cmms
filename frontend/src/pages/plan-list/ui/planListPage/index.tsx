"use client";

import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import { PlanFormModal } from "@features/maintenance-plan-management";
import { IMaintenancePlan } from "@entities/maintenance-plan";
import { buildMaintenancePlanRoute } from "@shared/config";
import { useViewerPermissions } from "@entities/user";
import { ButtonAppearance } from "@shared/ui/button";
import { PlanTable } from "@widgets/plan-table";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";

const ALLOWED_ROLES: UserRole[] = [UserRole.ENGINEER, UserRole.TECHNICIAN];

const PlanListPage = (): ReactElement => {
  const router = useRouter();
  const permissions = useViewerPermissions();
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  const openCreate = () => setIsCreateOpen(true);
  const closeCreate = () => setIsCreateOpen(false);

  const handleSaved = (plan: IMaintenancePlan) => {
    router.push(buildMaintenancePlanRoute(plan.id));
  };

  const createButton = permissions.canManagePlans ? (
    <Button
      label="Создать регламент"
      appearance={ButtonAppearance.PRIMARY}
      iconBefore={IconName.ADD}
      onClick={openCreate}
    />
  ) : undefined;

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader
        title="Регламенты технического обслуживания"
        actions={createButton}
      />
      <PlanTable emptyAction={createButton} />
      {isCreateOpen && (
        <PlanFormModal onClose={closeCreate} onSaved={handleSaved} />
      )}
    </RoleGate>
  );
};

export default PlanListPage;
