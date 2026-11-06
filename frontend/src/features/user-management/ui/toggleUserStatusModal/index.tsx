"use client";

import ConfirmModal from "@shared/ui/confirmModal";
import { useUpdateUser } from "../../model/useUpdateUser";
import { ButtonAppearance } from "@shared/ui/button";
import { getErrorMessage } from "@shared/api";
import { UserStatus } from "@entities/user";
import { useViewer } from "@entities/user";
import { IUser } from "@entities/user";
import { ReactElement } from "react";

interface IToggleUserStatusModalProps {
  user: IUser;
  onClose: () => void;
}

const ToggleUserStatusModal = ({
  user,
  onClose,
}: IToggleUserStatusModalProps): ReactElement => {
  const viewer = useViewer();
  const isBlocking: boolean = user.status === UserStatus.ACTIVE;
  const updateMutation = useUpdateUser({
    user,
    successTitle: isBlocking
      ? "Пользователь заблокирован"
      : "Пользователь разблокирован",
    onSuccess: onClose,
  });

  const handleConfirm = () => {
    updateMutation.mutate({
      status: isBlocking ? UserStatus.BLOCKED : UserStatus.ACTIVE,
    });
  };

  return (
    <ConfirmModal
      title={
        isBlocking
          ? `Заблокировать ${user.login}?`
          : `Разблокировать ${user.login}?`
      }
      confirmLabel={isBlocking ? "Заблокировать" : "Разблокировать"}
      confirmAppearance={
        isBlocking ? ButtonAppearance.DANGER : ButtonAppearance.PRIMARY
      }
      onConfirm={handleConfirm}
      onClose={onClose}
      isPending={updateMutation.isPending}
      errorMessage={
        updateMutation.isError ? getErrorMessage(updateMutation.error) : null
      }
    >
      {isBlocking ? (
        <p>
          Пользователь не сможет войти в систему, все его активные сессии будут
          завершены. Заявки и история работ сохранятся.
        </p>
      ) : (
        <p>Пользователь снова сможет войти в систему с действующим паролем.</p>
      )}
      {isBlocking && user.id === viewer.id && (
        <p className="text-subtle">
          Вы блокируете собственную учётную запись и будете отключены.
        </p>
      )}
    </ConfirmModal>
  );
};

export default ToggleUserStatusModal;
