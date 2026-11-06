"use client";

import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import { EquipmentFormModal } from "@features/equipment-management";
import { EquipmentTable } from "@widgets/equipment-table";
import { useViewerPermissions } from "@entities/user";
import { buildEquipmentRoute } from "@shared/config";
import { ButtonAppearance } from "@shared/ui/button";
import { IEquipment } from "@entities/equipment";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const EquipmentListPage = (): ReactElement => {
  const router = useRouter();
  const permissions = useViewerPermissions();
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  const openCreate = () => setIsCreateOpen(true);
  const closeCreate = () => setIsCreateOpen(false);

  const handleSaved = (equipment: IEquipment) => {
    router.push(buildEquipmentRoute(equipment.id));
  };

  const createButton = permissions.canManageEquipment ? (
    <Button
      label="Добавить оборудование"
      appearance={ButtonAppearance.PRIMARY}
      iconBefore={IconName.ADD}
      onClick={openCreate}
    />
  ) : undefined;

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader title="Оборудование" actions={createButton} />
      <EquipmentTable emptyAction={createButton} />
      {isCreateOpen && (
        <EquipmentFormModal onClose={closeCreate} onSaved={handleSaved} />
      )}
    </RoleGate>
  );
};

export default EquipmentListPage;
