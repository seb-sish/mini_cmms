"use client";

import Panel from "@shared/ui/panel";
import Button from "@shared/ui/button";
import Avatar from "@shared/ui/avatar";
import PageHeader from "@shared/ui/pageHeader";
import DetailsLayout from "@shared/ui/detailsLayout";
import QueryBoundary from "@shared/ui/queryBoundary";
import DescriptionList from "@shared/ui/descriptionList";
import { ToggleUserStatusModal } from "@features/user-management";
import { ChangePasswordModal } from "@features/user-management";
import { ChangeRoleModal } from "@features/user-management";
import { ButtonAppearance } from "@shared/ui/button";
import { UserStatusLozenge } from "@entities/user";
import { USER_ROLE_LABELS } from "@entities/user";
import { formatDateTime } from "@shared/lib/date";
import { AvatarSize } from "@shared/ui/avatar";
import { useUserQuery } from "@entities/user";
import { UserStatus } from "@entities/user";
import { IconName } from "@shared/ui/icon";
import { RoleGate } from "@entities/user";
import { UserRole } from "@entities/user";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import { useState } from "react";

const enum UserDialog {
  ROLE = "role",
  PASSWORD = "password",
  STATUS = "status",
}

interface IUserDetailsPageProps {
  userId: string;
}

const ALLOWED_ROLES: UserRole[] = [UserRole.ADMIN];

const UserDetailsPage = ({ userId }: IUserDetailsPageProps): ReactElement => {
  const [openedDialog, setOpenedDialog] = useState<UserDialog | null>(null);
  const { data: user, isLoading, error, refetch } = useUserQuery(userId);

  const closeDialog = () => setOpenedDialog(null);
  const openRole = () => setOpenedDialog(UserDialog.ROLE);
  const openPassword = () => setOpenedDialog(UserDialog.PASSWORD);
  const openStatus = () => setOpenedDialog(UserDialog.STATUS);

  const handleRetry = () => {
    refetch();
  };

  return (
    <RoleGate allowedRoles={ALLOWED_ROLES}>
      <QueryBoundary isLoading={isLoading} error={error} onRetry={handleRetry}>
        {user && (
          <>
            <PageHeader
              breadcrumbs={[{ label: "Пользователи", href: ROUTES.USERS }]}
              title={
                <>
                  <Avatar name={user.login} size={AvatarSize.MEDIUM} />
                  <span>{user.login}</span>
                  <UserStatusLozenge status={user.status} />
                </>
              }
              actions={
                <>
                  <Button
                    label="Сменить роль"
                    iconBefore={IconName.USER}
                    onClick={openRole}
                  />
                  <Button
                    label="Сменить пароль"
                    iconBefore={IconName.LOCK}
                    onClick={openPassword}
                  />
                  <Button
                    label={
                      user.status === UserStatus.ACTIVE
                        ? "Заблокировать"
                        : "Разблокировать"
                    }
                    appearance={
                      user.status === UserStatus.ACTIVE
                        ? ButtonAppearance.DANGER
                        : ButtonAppearance.PRIMARY
                    }
                    iconBefore={
                      user.status === UserStatus.ACTIVE
                        ? IconName.LOCK
                        : IconName.UNLOCK
                    }
                    onClick={openStatus}
                  />
                </>
              }
            />
            <DetailsLayout
              main={
                <Panel title="Права роли">
                  <p>
                    Роль &quot;{USER_ROLE_LABELS[user.role]}&quot; определяет
                    доступные пользователю разделы и действия. Права проверяются
                    сервером при каждом запросе.
                  </p>
                  <p className="text-subtle">
                    Удаление пользователей не предусмотрено: для прекращения
                    доступа используйте блокировку. Связанные заявки и история
                    работ сохраняются.
                  </p>
                </Panel>
              }
              side={
                <Panel title="Учётная запись">
                  <DescriptionList
                    items={[
                      { label: "Логин", value: user.login },
                      { label: "Роль", value: USER_ROLE_LABELS[user.role] },
                      {
                        label: "Состояние",
                        value: <UserStatusLozenge status={user.status} />,
                      },
                      {
                        label: "Создана",
                        value: formatDateTime(user.created_at),
                      },
                      {
                        label: "Изменена",
                        value: formatDateTime(user.updated_at),
                      },
                    ]}
                  />
                </Panel>
              }
            />
            {openedDialog === UserDialog.ROLE && (
              <ChangeRoleModal user={user} onClose={closeDialog} />
            )}
            {openedDialog === UserDialog.PASSWORD && (
              <ChangePasswordModal user={user} onClose={closeDialog} />
            )}
            {openedDialog === UserDialog.STATUS && (
              <ToggleUserStatusModal user={user} onClose={closeDialog} />
            )}
          </>
        )}
      </QueryBoundary>
    </RoleGate>
  );
};

export default UserDetailsPage;
