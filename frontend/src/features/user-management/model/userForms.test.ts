import { INITIAL_USER_CREATE_VALUES } from "./userForms";
import { validateUserPasswordForm } from "./userForms";
import { validateUserCreateForm } from "./userForms";
import { toUserCreatePayload } from "./userForms";
import { validateLogin } from "./userForms";
import { UserRole } from "@entities/user";

describe("user forms", () => {
  it("validates login pattern from contract", () => {
    expect(validateLogin("ivan.petrov_2")).toBeUndefined();
    expect(validateLogin("иван")).toBe(
      "Допустимы латинские буквы, цифры и символы . _ -"
    );
    expect(validateLogin("ab")).toBe("Минимальная длина: 3 симв.");
  });

  it("requires role and matching passwords of at least 12 characters", () => {
    const errors = validateUserCreateForm({
      ...INITIAL_USER_CREATE_VALUES,
      login: "operator1",
      password: "short",
      passwordConfirmation: "short",
    });

    expect(errors.role).toBe("Выберите роль.");
    expect(errors.password).toBe("Минимальная длина: 12 симв.");
    expect(errors.passwordConfirmation).toBeUndefined();
  });

  it("reports password mismatch", () => {
    expect(
      validateUserPasswordForm({
        password: "LongPassword-1",
        passwordConfirmation: "LongPassword-2",
      }).passwordConfirmation
    ).toBe("Пароли не совпадают.");
  });

  it("trims login but keeps password intact", () => {
    expect(
      toUserCreatePayload({
        login: "  operator1 ",
        password: " Secret-Pass-1 ",
        passwordConfirmation: " Secret-Pass-1 ",
        role: UserRole.OPERATOR,
      })
    ).toEqual({
      login: "operator1",
      password: " Secret-Pass-1 ",
      role: UserRole.OPERATOR,
    });
  });
});
