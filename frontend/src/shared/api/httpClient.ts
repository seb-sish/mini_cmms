import { createApiErrorFromProblem } from "./apiError";
import { API_PROXY_PREFIX } from "@shared/config";
import { buildQueryString } from "./queryString";
import { IProblemDetail } from "./apiError";
import { QueryParams } from "./queryString";
import { ApiErrorCode } from "./apiError";
import { ApiError } from "./apiError";

export const enum HttpMethod {
  GET = "GET",
  POST = "POST",
  PATCH = "PATCH",
}

export interface IRequestOptions {
  method?: HttpMethod;
  query?: QueryParams;
  body?: unknown;
  ifMatch?: string;
  signal?: AbortSignal;
}

type UnauthorizedHandler = () => void;

const NO_CONTENT_STATUS = 204;
const UNAUTHORIZED_STATUS = 401;
const JSON_CONTENT_TYPE = "application/json";

let unauthorizedHandler: UnauthorizedHandler | null = null;

export const setUnauthorizedHandler = (
  handler: UnauthorizedHandler | null
): void => {
  unauthorizedHandler = handler;
};

export const buildIfMatch = (id: string, version: number): string =>
  `"${id}:${version}"`;

const readJson = async (response: Response): Promise<unknown> => {
  const text = await response.text();

  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
};

export const httpRequest = async <TResponse>(
  url: string,
  {
    method = HttpMethod.GET,
    query,
    body,
    ifMatch,
    signal,
  }: IRequestOptions = {}
): Promise<TResponse> => {
  const headers: Record<string, string> = { Accept: JSON_CONTENT_TYPE };

  if (body !== undefined) headers["Content-Type"] = JSON_CONTENT_TYPE;
  if (ifMatch) headers["If-Match"] = ifMatch;

  let response: Response;

  try {
    response = await fetch(`${url}${buildQueryString(query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;

    throw new ApiError({
      status: 0,
      code: ApiErrorCode.NETWORK_ERROR,
      detail: "",
    });
  }

  if (response.status === NO_CONTENT_STATUS) return undefined as TResponse;

  const payload = await readJson(response);

  if (!response.ok) {
    const apiError = createApiErrorFromProblem(
      response.status,
      payload as IProblemDetail | null,
      response.headers.get("Retry-After")
    );

    if (
      response.status === UNAUTHORIZED_STATUS &&
      apiError.code !== ApiErrorCode.INVALID_CREDENTIALS &&
      unauthorizedHandler
    ) {
      unauthorizedHandler();
    }

    throw apiError;
  }

  return payload as TResponse;
};

export const apiRequest = <TResponse>(
  path: string,
  options?: IRequestOptions
): Promise<TResponse> =>
  httpRequest<TResponse>(`${API_PROXY_PREFIX}${path}`, options);
