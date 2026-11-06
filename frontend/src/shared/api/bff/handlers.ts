import { createProblemResponse } from "./backendProxy";
import { buildBackendHeaders } from "./backendProxy";
import { isSameOriginRequest } from "./backendProxy";
import { pickResponseHeaders } from "./backendProxy";
import { clearSessionCookie } from "./sessionCookie";
import { SESSION_COOKIE_NAME } from "@shared/config";
import { setSessionCookie } from "./sessionCookie";
import { forwardToBackend } from "./backendProxy";
import { toClientResponse } from "./backendProxy";
import { isUnsafeMethod } from "./backendProxy";
import { NextResponse } from "next/server";
import { NextRequest } from "next/server";

interface IBackendTokenResponse {
  access_token: string;
  expires_at: string;
  user: unknown;
}

const UNAUTHORIZED_STATUS = 401;
const BAD_GATEWAY_STATUS = 502;
const FORBIDDEN_STATUS = 403;
const NOT_FOUND_STATUS = 404;

const BLOCKED_PROXY_PATHS: string[] = ["/auth/login", "/auth/logout"];

const BACKEND_UNAVAILABLE_DETAIL = "Backend API is unavailable.";

const backendUnavailableResponse = (): NextResponse =>
  createProblemResponse(
    BAD_GATEWAY_STATUS,
    "DEPENDENCY_UNAVAILABLE",
    BACKEND_UNAVAILABLE_DETAIL
  );

const readBody = async (
  request: NextRequest
): Promise<ArrayBuffer | undefined> =>
  request.method === "GET" || request.method === "HEAD"
    ? undefined
    : request.arrayBuffer();

export const handleApiProxy = async (
  request: NextRequest,
  pathSegments: string[]
): Promise<NextResponse> => {
  const path = `/${pathSegments.map(encodeURIComponent).join("/")}`;

  if (BLOCKED_PROXY_PATHS.includes(path)) {
    return createProblemResponse(
      NOT_FOUND_STATUS,
      "NOT_FOUND",
      "Use /api/auth endpoints."
    );
  }

  if (isUnsafeMethod(request.method) && !isSameOriginRequest(request)) {
    return createProblemResponse(
      FORBIDDEN_STATUS,
      "ACCESS_DENIED",
      "Cross-origin request rejected."
    );
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;

  try {
    const backendResponse = await forwardToBackend({
      method: request.method,
      path,
      search: request.nextUrl.search,
      headers: buildBackendHeaders(request.headers, token),
      body: await readBody(request),
    });

    const response = await toClientResponse(backendResponse);

    if (backendResponse.status === UNAUTHORIZED_STATUS && token)
      clearSessionCookie(response);

    return response;
  } catch {
    return backendUnavailableResponse();
  }
};

export const handleLogin = async (
  request: NextRequest
): Promise<NextResponse> => {
  if (!isSameOriginRequest(request)) {
    return createProblemResponse(
      FORBIDDEN_STATUS,
      "ACCESS_DENIED",
      "Cross-origin request rejected."
    );
  }

  try {
    const backendResponse = await forwardToBackend({
      method: "POST",
      path: "/auth/login",
      search: "",
      headers: buildBackendHeaders(request.headers, undefined),
      body: await request.arrayBuffer(),
    });

    if (!backendResponse.ok) return toClientResponse(backendResponse);

    const tokenResponse =
      (await backendResponse.json()) as IBackendTokenResponse;
    const response = NextResponse.json(
      { user: tokenResponse.user, expires_at: tokenResponse.expires_at },
      { headers: pickResponseHeaders(new Headers()) }
    );

    setSessionCookie(
      response,
      tokenResponse.access_token,
      tokenResponse.expires_at
    );

    return response;
  } catch {
    return backendUnavailableResponse();
  }
};

export const handleLogout = async (
  request: NextRequest
): Promise<NextResponse> => {
  if (!isSameOriginRequest(request)) {
    return createProblemResponse(
      FORBIDDEN_STATUS,
      "ACCESS_DENIED",
      "Cross-origin request rejected."
    );
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  const response = new NextResponse(null, { status: 204 });

  clearSessionCookie(response);

  if (!token) return response;

  try {
    await forwardToBackend({
      method: "POST",
      path: "/auth/logout",
      search: "",
      headers: buildBackendHeaders(new Headers(), token),
    });
  } catch {
    return response;
  }

  return response;
};
