import { IUserCreatePayload } from "@entities/user";
import { validatePassword } from "@shared/lib/form";
import { validateText } from "@shared/lib/form";
import { FormErrors } from "@shared/lib/form";
import { UserRole } from "@entities/user";

export interface IUserCreateFormValues {
  login: string;
  password: string;
  passwordConfirmation: string;
  role: UserRole | "";
}

export interface IUserPasswordFormValues {
  password: string;
  passwordConfirmation: string;
}

export const USER_FORM_LIMITS = {
  LOGIN_MIN: 3,
  LOGIN_MAX: 64,
  PASSWORD_MIN: 12,
  PASSWORD_MAX: 128,
} as const;

const LOGIN_PATTERN = /^[A-Za-z0-9_.-]+$/;

export const INITIAL_USER_CREATE_VALUES: IUserCreateFormValues = {
  login: "",
  password: "",
  passwordConfirmation: "",
  role: "",
};

export const INITIAL_USER_PASSWORD_VALUES: IUserPasswordFormValues = {
  password: "",
  passwordConfirmation: "",
};

const validatePasswordPair = (
  password: string,
  passwordConfirmation: string
): FormErrors<IUserPasswordFormValues> => {
  const passwordError = validatePassword(password, {
    minLength: USER_FORM_LIMITS.PASSWORD_MIN,
    maxLength: USER_FORM_LIMITS.PASSWORD_MAX,
  });

  return {
    password: passwordError,
    passwordConfirmation:
      !passwordError && password !== passwordConfirmation
        ? "Пароли не совпадают."
        : undefined,
  };
};

export const validateLogin = (login: string): string | undefined => {
  const lengthError = validateText(login, {
    isRequired: true,
    minLength: USER_FORM_LIMITS.LOGIN_MIN,
    maxLength: USER_FORM_LIMITS.LOGIN_MAX,
  });

  if (lengthError) return lengthError;

  return LOGIN_PATTERN.test(login.trim())
    ? undefined
    : "Допустимы латинские буквы, цифры и символы . _ -";
};

export const validateUserCreateForm = (
  values: IUserCreateFormValues
): FormErrors<IUserCreateFormValues> => ({
  login: validateLogin(values.login),
  role: values.role ? undefined : "Выберите роль.",
  ...validatePasswordPair(values.password, values.passwordConfirmation),
});

export const validateUserPasswordForm = (
  values: IUserPasswordFormValues
): FormErrors<IUserPasswordFormValues> =>
  validatePasswordPair(values.password, values.passwordConfirmation);

export const toUserCreatePayload = (
  values: IUserCreateFormValues
): IUserCreatePayload => ({
  login: values.login.trim(),
  password: values.password,
  role: values.role as UserRole,
});
