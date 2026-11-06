"use client";

import Button from "@shared/ui/button";
import PageHeader from "@shared/ui/pageHeader";
import { CreateUserModal } from "@features/user-management";
import { ButtonAppearance } from "@shared/ui/button";
import { UserTable } from "@widgets/user-table";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";

const ALLOWED_ROLES: UserRole[] = [UserRole.ADMIN];

const UserListPage = (): ReactElement => {
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);

  const openCreate = () => setIsCreateOpen(true);
  const closeCreate = () => setIsCreateOpen(false);

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <PageHeader
        title="Пользователи"
        actions={
          <Button
            label="Создать пользователя"
            appearance={ButtonAppearance.PRIMARY}
            iconBefore={IconName.ADD}
            onClick={openCreate}
          />
        }
      />
      <UserTable />
      {isCreateOpen && <CreateUserModal onClose={closeCreate} />}
    </RoleGate>
  );
};

export default UserListPage;
