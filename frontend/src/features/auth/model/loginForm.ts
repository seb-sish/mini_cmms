import { validatePassword } from "@shared/lib/form";
import { validateText } from "@shared/lib/form";
import { ILoginPayload } from "../api/authApi";
import { FormErrors } from "@shared/lib/form";

export const LOGIN_LIMITS = {
  LOGIN_MIN: 3,
  LOGIN_MAX: 64,
  PASSWORD_MIN: 8,
  PASSWORD_MAX: 128,
} as const;

export const INITIAL_LOGIN_VALUES: ILoginPayload = {
  login: "",
  password: "",
};

export const validateLoginForm = (
  values: ILoginPayload
): FormErrors<ILoginPayload> => ({
  login: validateText(values.login, {
    isRequired: true,
    minLength: LOGIN_LIMITS.LOGIN_MIN,
    maxLength: LOGIN_LIMITS.LOGIN_MAX,
  }),
  password: validatePassword(values.password, {
    minLength: LOGIN_LIMITS.PASSWORD_MIN,
    maxLength: LOGIN_LIMITS.PASSWORD_MAX,
  }),
});

export const toLoginPayload = (values: ILoginPayload): ILoginPayload => ({
  login: values.login.trim(),
  password: values.password,
});
