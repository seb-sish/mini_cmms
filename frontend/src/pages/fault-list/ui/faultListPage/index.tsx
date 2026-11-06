"use client";

import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import { FaultFormModal } from "@features/fault-management";
import { useViewerPermissions } from "@entities/user";
import { ButtonAppearance } from "@shared/ui/button";
import { FaultTable } from "@widgets/fault-table";
import { buildFaultRoute } from "@shared/config";
import { useRouter } from "next/navigation";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { IFault } from "@entities/fault";
import { ReactElement } from "react";
import { useState } from "react";

const ALLOWED_ROLES: UserRole[] = [
  UserRole.ENGINEER,
  UserRole.TECHNICIAN,
  UserRole.OPERATOR,
];

const FaultListPage = (): ReactElement => {
  const router = useRouter();
  const permissions = useViewerPermissions();
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  const openCreate = () => setIsCreateOpen(true);
  const closeCreate = () => setIsCreateOpen(false);

  const handleSaved = (fault: IFault) => {
    router.push(buildFaultRoute(fault.id));
  };

  const createButton = permissions.canCreateFault ? (
    <Button
      label="Зарегистрировать неисправность"
      appearance={ButtonAppearance.PRIMARY}
      iconBefore={IconName.ADD}
      onClick={openCreate}
    />
  ) : undefined;

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader title="Журнал неисправностей" actions={createButton} />
      <FaultTable emptyAction={createButton} />
      {isCreateOpen && (
        <FaultFormModal onClose={closeCreate} onSaved={handleSaved} />
      )}
    </RoleGate>
  );
};

export default FaultListPage;
