import { validateIntegerRange } from "./validators";
import { validatePassword } from "./validators";
import { REQUIRED_MESSAGE } from "./validators";
import { validateText } from "./validators";
import { validateDate } from "./validators";
import { hasErrors } from "./validators";

describe("form validators", () => {
  it("rejects whitespace-only required text", () => {
    expect(validateText("   ", { isRequired: true })).toBe(REQUIRED_MESSAGE);
  });

  it("checks text length after trimming", () => {
    expect(validateText("  ab  ", { minLength: 3 })).toBe(
      "Минимальная длина: 3 симв."
    );
    expect(validateText("abcd", { maxLength: 3 })).toBe(
      "Максимальная длина: 3 симв."
    );
    expect(
      validateText("  abc ", { isRequired: true, minLength: 3, maxLength: 3 })
    ).toBeUndefined();
  });

  it("allows empty optional text", () => {
    expect(validateText("", {})).toBeUndefined();
  });

  it("does not trim passwords", () => {
    expect(
      validatePassword("           a", { minLength: 12, maxLength: 128 })
    ).toBeUndefined();
    expect(validatePassword("short", { minLength: 12, maxLength: 128 })).toBe(
      "Минимальная длина: 12 симв."
    );
    expect(validatePassword("", { minLength: 12, maxLength: 128 })).toBe(
      REQUIRED_MESSAGE
    );
  });

  it("rejects dates after the given boundary", () => {
    expect(
      validateDate("2026-10-30", { isRequired: true, notAfter: "2026-10-29" })
    ).toBe("Дата не может быть позже сегодняшней.");
    expect(
      validateDate("2026-10-29", { isRequired: true, notAfter: "2026-10-29" })
    ).toBeUndefined();
    expect(validateDate("2026-13-01", {})).toBe("Некорректная дата.");
  });

  it("validates integer ranges", () => {
    expect(validateIntegerRange("0", { min: 1, max: 3650 })).toBe(
      "Допустимо от 1 до 3650."
    );
    expect(validateIntegerRange("3651", { min: 1, max: 3650 })).toBe(
      "Допустимо от 1 до 3650."
    );
    expect(validateIntegerRange("1.5", { min: 1, max: 3650 })).toBe(
      "Введите целое число."
    );
    expect(validateIntegerRange("30", { min: 1, max: 3650 })).toBeUndefined();
  });

  it("detects presence of errors", () => {
    expect(hasErrors({ name: undefined })).toBe(false);
    expect(hasErrors({ name: "error" })).toBe(true);
  });
});
