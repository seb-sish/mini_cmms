import { shouldRetryQuery } from "./queryClient";
import { ApiError } from "@shared/api";

const createError = (status: number) =>
  new ApiError({ status, code: "X", detail: "" });

describe("query retry policy", () => {
  it("does not retry client errors such as 403, 404 and 412", () => {
    expect(shouldRetryQuery(0, createError(403))).toBe(false);
    expect(shouldRetryQuery(0, createError(404))).toBe(false);
    expect(shouldRetryQuery(0, createError(412))).toBe(false);
  });

  it("retries server and network errors up to the limit", () => {
    expect(shouldRetryQuery(0, createError(503))).toBe(true);
    expect(shouldRetryQuery(1, createError(0))).toBe(true);
    expect(shouldRetryQuery(2, createError(503))).toBe(false);
  });
});
