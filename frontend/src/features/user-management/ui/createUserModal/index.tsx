"use client";

import Select from "@shared/ui/select";
import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { INITIAL_USER_CREATE_VALUES } from "../../model/userForms";
import { validateUserCreateForm } from "../../model/userForms";
import { toUserCreatePayload } from "../../model/userForms";
import { USER_FORM_LIMITS } from "../../model/userForms";
import { useQueryClient } from "@tanstack/react-query";
import { TextFieldType } from "@shared/ui/textField";
import { useMutation } from "@tanstack/react-query";
import { buildOptions } from "@shared/lib/options";
import { USER_ROLE_LABELS } from "@entities/user";
import { FlagAppearance } from "@shared/ui/flag";
import { useFormFields } from "@shared/lib/form";
import { getErrorMessage } from "@shared/api";
import { getFieldErrors } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { createUser } from "@entities/user";
import { USER_ROLES } from "@entities/user";
import { useFlags } from "@shared/ui/flag";
import { userKeys } from "@entities/user";
import { UserRole } from "@entities/user";
import { IUser } from "@entities/user";
import { ReactElement } from "react";

interface ICreateUserModalProps {
  onClose: () => void;
  onCreated?: (user: IUser) => void;
}

const ROLE_OPTIONS = buildOptions(USER_ROLES, USER_ROLE_LABELS);

const CreateUserModal = ({
  onClose,
  onCreated,
}: ICreateUserModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const { values, errors, setErrors, setFieldValue } = useFormFields(
    INITIAL_USER_CREATE_VALUES
  );

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: "Пользователь создан",
        description: `Учётная запись ${user.login} активна.`,
      });
      onCreated?.(user);
      onClose();
    },
    onError: (error) => {
      setErrors((prev) => ({ ...prev, ...getFieldErrors(error) }));
    },
  });

  const handleSubmit = () => {
    const validationErrors = validateUserCreateForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    createMutation.mutate(toUserCreatePayload(values));
  };

  const updateLogin = (value: string) => {
    setFieldValue("login", value);
  };

  const updateRole = (value: string) => {
    setFieldValue("role", value as UserRole);
  };

  const updatePassword = (value: string) => {
    setFieldValue("password", value);
  };

  const updatePasswordConfirmation = (value: string) => {
    setFieldValue("passwordConfirmation", value);
  };

  return (
    <FormModal
      title="Новый пользователь"
      submitLabel="Создать"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={createMutation.isPending}
      errorMessage={
        createMutation.isError ? getErrorMessage(createMutation.error) : null
      }
    >
      <TextField
        label="Логин"
        value={values.login}
        onChange={updateLogin}
        errorMessage={errors.login}
        helperText="Латинские буквы, цифры и символы . _ -"
        maxLength={USER_FORM_LIMITS.LOGIN_MAX}
        autoComplete="off"
        isRequired
      />
      <Select
        label="Роль"
        value={values.role}
        options={ROLE_OPTIONS}
        onChange={updateRole}
        placeholder="Выберите роль"
        errorMessage={errors.role}
        isRequired
      />
      <TextField
        label="Пароль"
        type={TextFieldType.PASSWORD}
        value={values.password}
        onChange={updatePassword}
        errorMessage={errors.password}
        helperText={`Не менее ${USER_FORM_LIMITS.PASSWORD_MIN} символов`}
        maxLength={USER_FORM_LIMITS.PASSWORD_MAX}
        autoComplete="new-password"
        isRequired
      />
      <TextField
        label="Повторите пароль"
        type={TextFieldType.PASSWORD}
        value={values.passwordConfirmation}
        onChange={updatePasswordConfirmation}
        errorMessage={errors.passwordConfirmation}
        maxLength={USER_FORM_LIMITS.PASSWORD_MAX}
        autoComplete="new-password"
        isRequired
      />
    </FormModal>
  );
};

export default CreateUserModal;
