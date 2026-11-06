export const enum ApiErrorCode {
  VALIDATION_ERROR = "VALIDATION_ERROR",
  UNAUTHENTICATED = "UNAUTHENTICATED",
  INVALID_CREDENTIALS = "INVALID_CREDENTIALS",
  ACCESS_DENIED = "ACCESS_DENIED",
  NOT_FOUND = "NOT_FOUND",
  RATE_LIMITED = "RATE_LIMITED",
  VERSION_CONFLICT = "VERSION_CONFLICT",
  PRECONDITION_REQUIRED = "PRECONDITION_REQUIRED",
  INVALID_WORK_ORDER_STATE = "INVALID_WORK_ORDER_STATE",
  EQUIPMENT_ARCHIVED = "EQUIPMENT_ARCHIVED",
  ACTIVE_WORK_ORDERS = "ACTIVE_WORK_ORDERS",
  LAST_ACTIVE_ADMIN = "LAST_ACTIVE_ADMIN",
  INVALID_DATE_RANGE = "INVALID_DATE_RANGE",
  DUPLICATE_PLANNED_WORK_ORDER = "DUPLICATE_PLANNED_WORK_ORDER",
  DUPLICATE_INVENTORY_NUMBER = "DUPLICATE_INVENTORY_NUMBER",
  DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE",
  ACTIVE_MAINTENANCE_WORK = "ACTIVE_MAINTENANCE_WORK",
  TOO_EARLY_TO_COMPLETE = "TOO_EARLY_TO_COMPLETE",
  SAME_ASSIGNEE = "SAME_ASSIGNEE",
  NOT_ARCHIVED = "NOT_ARCHIVED",
  ALREADY_ARCHIVED = "ALREADY_ARCHIVED",
  NON_ADVANCING_DUE_DATE = "NON_ADVANCING_DUE_DATE",
  LOGIN_ALREADY_EXISTS = "LOGIN_ALREADY_EXISTS",
  INVALID_ASSIGNEE_ROLE = "INVALID_ASSIGNEE_ROLE",
  INVALID_ASSIGNEE = "INVALID_ASSIGNEE",
  ASSIGNEE_NOT_ACTIVE = "ASSIGNEE_NOT_ACTIVE",
  INCOMPLETE_CHECKLIST = "INCOMPLETE_CHECKLIST",
  INACTIVE_MAINTENANCE_SCHEDULE = "INACTIVE_MAINTENANCE_SCHEDULE",
  FUTURE_DETECTED_DATE = "FUTURE_DETECTED_DATE",
  FAULT_HAS_ACTIVE_WORK_ORDER = "FAULT_HAS_ACTIVE_WORK_ORDER",
  EQUIPMENT_MISMATCH = "EQUIPMENT_MISMATCH",
  DUPLICATE_CHECKLIST_ITEM = "DUPLICATE_CHECKLIST_ITEM",
  DUPLICATE_ACTIVE_WORK_ORDER = "DUPLICATE_ACTIVE_WORK_ORDER",
  ACTIVE_ASSIGNMENTS = "ACTIVE_ASSIGNMENTS",
  MALFORMED_JSON = "MALFORMED_JSON",
  UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE",
  METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED",
  NETWORK_ERROR = "NETWORK_ERROR",
  UNKNOWN_ERROR = "UNKNOWN_ERROR",
}

export interface IFieldError {
  field: string;
  message: string;
}

export interface IProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
  instance?: string;
  errors?: IFieldError[];
}

interface IApiErrorParams {
  status: number;
  code: string;
  detail: string;
  fieldErrors?: IFieldError[];
  retryAfterSeconds?: number | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: string;
  readonly fieldErrors: IFieldError[];
  readonly retryAfterSeconds: number | null;

  constructor({
    status,
    code,
    detail,
    fieldErrors = [],
    retryAfterSeconds = null,
  }: IApiErrorParams) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export const isApiError = (error: unknown): error is ApiError =>
  error instanceof ApiError;

export const hasErrorCode = (error: unknown, code: ApiErrorCode): boolean =>
  isApiError(error) && error.code === code;

export const parseRetryAfter = (value: string | null): number | null => {
  if (!value) return null;

  const seconds = Number(value);

  return Number.isFinite(seconds) && seconds >= 0 ? Math.ceil(seconds) : null;
};

export const createApiErrorFromProblem = (
  status: number,
  problem: IProblemDetail | null,
  retryAfterHeader: string | null
): ApiError =>
  new ApiError({
    status,
    code: problem?.code ?? ApiErrorCode.UNKNOWN_ERROR,
    detail: problem?.detail ?? problem?.title ?? "",
    fieldErrors: Array.isArray(problem?.errors) ? problem.errors : [],
    retryAfterSeconds: parseRetryAfter(retryAfterHeader),
  });
