import { NextResponse } from "next/server";
import { NextRequest } from "next/server";

export const BACKEND_API_PREFIX: string = "/api/v1";

const PROBLEM_CONTENT_TYPE = "application/problem+json";

const FORWARDED_REQUEST_HEADERS: string[] = [
  "accept",
  "content-type",
  "if-match",
];

const FORWARDED_RESPONSE_HEADERS: string[] = [
  "content-type",
  "etag",
  "location",
  "retry-after",
  "allow",
  "www-authenticate",
];

const UNSAFE_METHODS: string[] = ["POST", "PUT", "PATCH", "DELETE"];

const BODYLESS_STATUSES: number[] = [204, 304];

export const getBackendBaseUrl = (): string => {
  const baseUrl = process.env.CMMS_API_BASE_URL;

  if (!baseUrl) throw new Error("CMMS_API_BASE_URL is not configured");

  return baseUrl.replace(/\/+$/, "");
};

export const buildBackendHeaders = (
  incomingHeaders: Headers,
  token: string | undefined
): Headers => {
  const headers = new Headers();

  FORWARDED_REQUEST_HEADERS.forEach((name) => {
    const value = incomingHeaders.get(name);

    if (value) headers.set(name, value);
  });

  if (token) headers.set("authorization", `Bearer ${token}`);

  return headers;
};

export const pickResponseHeaders = (backendHeaders: Headers): Headers => {
  const headers = new Headers();

  FORWARDED_RESPONSE_HEADERS.forEach((name) => {
    const value = backendHeaders.get(name);

    if (value) headers.set(name, value);
  });

  headers.set("cache-control", "no-store");

  return headers;
};

export const isUnsafeMethod = (method: string): boolean =>
  UNSAFE_METHODS.includes(method.toUpperCase());

export const isSameOriginRequest = (request: NextRequest): boolean => {
  const origin = request.headers.get("origin");

  if (!origin) return true;

  try {
    return new URL(origin).host === request.headers.get("host");
  } catch {
    return false;
  }
};

export const createProblemResponse = (
  status: number,
  code: string,
  detail: string
): NextResponse =>
  NextResponse.json(
    { type: "about:blank", title: code, status, detail, code },
    { status, headers: { "content-type": PROBLEM_CONTENT_TYPE } }
  );

interface IForwardParams {
  method: string;
  path: string;
  search: string;
  headers: Headers;
  body?: ArrayBuffer;
}

export const forwardToBackend = async ({
  method,
  path,
  search,
  headers,
  body,
}: IForwardParams): Promise<Response> =>
  fetch(`${getBackendBaseUrl()}${BACKEND_API_PREFIX}${path}${search}`, {
    method,
    headers,
    body: body && body.byteLength > 0 ? body : undefined,
    cache: "no-store",
    redirect: "manual",
  });

export const toClientResponse = async (
  backendResponse: Response
): Promise<NextResponse> => {
  const headers = pickResponseHeaders(backendResponse.headers);

  if (BODYLESS_STATUSES.includes(backendResponse.status)) {
    return new NextResponse(null, { status: backendResponse.status, headers });
  }

  return new NextResponse(await backendResponse.arrayBuffer(), {
    status: backendResponse.status,
    headers,
  });
};
