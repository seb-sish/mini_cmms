"use client";

import Button from "@shared/ui/button";
import TextField from "@shared/ui/textField";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { INITIAL_LOGIN_VALUES } from "../../model/loginForm";
import { validateLoginForm } from "../../model/loginForm";
import { toLoginPayload } from "../../model/loginForm";
import { LOGIN_LIMITS } from "../../model/loginForm";
import { TextFieldType } from "@shared/ui/textField";
import { ButtonAppearance } from "@shared/ui/button";
import { useMutation } from "@tanstack/react-query";
import { ILoginResponse } from "../../api/authApi";
import { useFormFields } from "@shared/lib/form";
import { loginRequest } from "../../api/authApi";
import { ButtonType } from "@shared/ui/button";
import { getErrorMessage } from "@shared/api";
import { hasErrors } from "@shared/lib/form";
import { ReactElement } from "react";
import { FormEvent } from "react";
import "./style.css";

interface ILoginFormProps {
  onSuccess: (response: ILoginResponse) => void;
}

const LoginForm = ({ onSuccess }: ILoginFormProps): ReactElement => {
  const { values, errors, setErrors, setFieldValue } =
    useFormFields(INITIAL_LOGIN_VALUES);

  const loginMutation = useMutation({
    mutationFn: loginRequest,
    onSuccess: (response) => onSuccess(response),
  });

  const updateLoginValue = (value: string) => {
    setFieldValue("login", value);
  };

  const updatePasswordValue = (value: string) => {
    setFieldValue("password", value);
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationErrors = validateLoginForm(values);

    setErrors(validationErrors);

    if (hasErrors(validationErrors)) return;

    loginMutation.mutate(toLoginPayload(values));
  };

  return (
    <form className="login-form" onSubmit={onSubmit} noValidate>
      {loginMutation.isError && (
        <SectionMessage appearance={SectionMessageAppearance.ERROR}>
          <p>{getErrorMessage(loginMutation.error)}</p>
        </SectionMessage>
      )}
      <TextField
        label="Логин"
        name="login"
        value={values.login}
        onChange={updateLoginValue}
        errorMessage={errors.login}
        maxLength={LOGIN_LIMITS.LOGIN_MAX}
        autoComplete="username"
        isRequired
        autoFocus
      />
      <TextField
        label="Пароль"
        name="password"
        type={TextFieldType.PASSWORD}
        value={values.password}
        onChange={updatePasswordValue}
        errorMessage={errors.password}
        maxLength={LOGIN_LIMITS.PASSWORD_MAX}
        autoComplete="current-password"
        isRequired
      />
      <Button
        label="Войти"
        type={ButtonType.SUBMIT}
        appearance={ButtonAppearance.PRIMARY}
        isLoading={loginMutation.isPending}
        shouldFitContainer
      />
    </form>
  );
};

export default LoginForm;
