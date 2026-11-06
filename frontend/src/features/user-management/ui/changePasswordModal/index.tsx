"use client";

import TextField from "@shared/ui/textField";
import FormModal from "@shared/ui/formModal";
import { INITIAL_USER_PASSWORD_VALUES } from "../../model/userForms";
import { validateUserPasswordForm } from "../../model/userForms";
import { useUpdateUser } from "../../model/useUpdateUser";
import { USER_FORM_LIMITS } from "../../model/userForms";
import { TextFieldType } from "@shared/ui/textField";
import { useFormFields } from "@shared/lib/form";
import { getErrorMessage } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { IUser } from "@entities/user";
import { ReactElement } from "react";

interface IChangePasswordModalProps {
  user: IUser;
  onClose: () => void;
}

const ChangePasswordModal = ({
  user,
  onClose,
}: IChangePasswordModalProps): ReactElement => {
  const { values, errors, setErrors, setFieldValue } = useFormFields(
    INITIAL_USER_PASSWORD_VALUES
  );
  const updateMutation = useUpdateUser({
    user,
    successTitle: "Пароль изменён",
    onSuccess: onClose,
  });

  const updatePassword = (value: string) => {
    setFieldValue("password", value);
  };

  const updatePasswordConfirmation = (value: string) => {
    setFieldValue("passwordConfirmation", value);
  };

  const handleSubmit = () => {
    const validationErrors = validateUserPasswordForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    updateMutation.mutate({ new_password: values.password });
  };

  return (
    <FormModal
      title={`Новый пароль для ${user.login}`}
      submitLabel="Сменить пароль"
      onSubmit={handleSubmit}
      onClose={onClose}
      isSubmitting={updateMutation.isPending}
      errorMessage={
        updateMutation.isError ? getErrorMessage(updateMutation.error) : null
      }
    >
      <p className="text-subtle">
        После смены пароля все активные сессии пользователя будут завершены.
      </p>
      <TextField
        label="Новый пароль"
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

export default ChangePasswordModal;
