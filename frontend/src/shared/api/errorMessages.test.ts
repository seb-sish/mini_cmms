import { translateFieldMessage } from "./errorMessages";
import { getErrorMessage } from "./errorMessages";
import { getFieldErrors } from "./errorMessages";
import { buildQueryString } from "./queryString";
import { parseRetryAfter } from "./apiError";
import { ApiErrorCode } from "./apiError";
import { ApiError } from "./apiError";

const createError = (
  code: string,
  extra: Partial<ConstructorParameters<typeof ApiError>[0]> = {}
) => new ApiError({ status: 409, code, detail: "server detail", ...extra });

describe("error messages", () => {
  it("maps stable codes to Russian messages without exposing server detail", () => {
    expect(
      getErrorMessage(createError(ApiErrorCode.TOO_EARLY_TO_COMPLETE))
    ).toContain("Слишком рано");
    expect(getErrorMessage(createError(ApiErrorCode.INVALID_CREDENTIALS))).toBe(
      "Неверный логин или пароль."
    );
    expect(getErrorMessage(createError("SOMETHING_NEW"))).not.toContain(
      "server detail"
    );
  });

  it("includes wait time for rate limit", () => {
    const error = createError(ApiErrorCode.RATE_LIMITED, {
      retryAfterSeconds: 150,
    });

    expect(getErrorMessage(error)).toBe(
      "Слишком много неудачных попыток входа. Повторите через 3 мин."
    );
  });

  it("returns default message for unknown errors", () => {
    expect(getErrorMessage(new Error("boom"))).toBe(
      "Не удалось выполнить операцию. Повторите попытку."
    );
  });

  it("translates validation messages and keeps first error per field", () => {
    const error = createError(ApiErrorCode.VALIDATION_ERROR, {
      fieldErrors: [
        {
          field: "password",
          message: "String should have at least 12 characters",
        },
        { field: "password", message: "second" },
        {
          field: "checklist.0.title",
          message: "Input should be a valid string",
        },
      ],
    });

    expect(getFieldErrors(error)).toEqual({
      password: "Минимальная длина: 12 симв.",
      checklist: "Недопустимое значение.",
    });
    expect(translateFieldMessage("unexpected")).toBe(
      "Значение не прошло проверку на сервере."
    );
  });

  it("parses Retry-After seconds", () => {
    expect(parseRetryAfter("59.2")).toBe(60);
    expect(parseRetryAfter(null)).toBeNull();
    expect(parseRetryAfter("soon")).toBeNull();
  });

  it("builds query strings skipping empty values", () => {
    expect(
      buildQueryString({
        q: "100%_test",
        limit: 20,
        empty: "",
        flag: false,
        missing: null,
      })
    ).toBe("?q=100%25_test&limit=20&flag=false");
    expect(buildQueryString({})).toBe("");
  });
});
