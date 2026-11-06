"use client";

import Select from "@shared/ui/select";
import FormModal from "@shared/ui/formModal";
import { useUpdateUser } from "../../model/useUpdateUser";
import { buildOptions } from "@shared/lib/options";
import { USER_ROLE_LABELS } from "@entities/user";
import { getErrorMessage } from "@shared/api";
import { USER_ROLES } from "@entities/user";
import { UserRole } from "@entities/user";
import { IUser } from "@entities/user";
import { ReactElement } from "react";
import { useState } from "react";

interface IChangeRoleModalProps {
  user: IUser;
  onClose: () => void;
}

const ROLE_OPTIONS = buildOptions(USER_ROLES, USER_ROLE_LABELS);

const ChangeRoleModal = ({
  user,
  onClose,
}: IChangeRoleModalProps): ReactElement => {
  const [role, setRole] = useState<UserRole>(user.role);
  const updateMutation = useUpdateUser({
    user,
    successTitle: "Роль изменена",
    onSuccess: onClose,
  });

  const updateRole = (value: string) => {
    setRole(value as UserRole);
  };

  const handleSubmit = () => {
    updateMutation.mutate({ role });
  };

  return (
    <FormModal
      title={`Роль пользователя ${user.login}`}
      submitLabel="Сохранить"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={updateMutation.isPending}
      isSubmitDisabled={role === user.role}
      errorMessage={
        updateMutation.isError ? getErrorMessage(updateMutation.error) : null
      }
    >
      <Select
        label="Роль"
        value={role}
        options={ROLE_OPTIONS}
        onChange={updateRole}
        helperText="Права новой роли применяются сразу. Данные пользователя сохраняются."
        isRequired
      />
    </FormModal>
  );
};

export default ChangeRoleModal;
