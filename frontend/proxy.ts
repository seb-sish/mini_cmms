import { LOGIN_REDIRECT_PARAM } from "@shared/config/routes";
import { SESSION_COOKIE_NAME } from "@shared/config/app";
import { ROUTES } from "@shared/config/routes";
import { NextResponse } from "next/server";
import { NextRequest } from "next/server";

export const proxy = (request: NextRequest): NextResponse => {
  const { pathname, search } = request.nextUrl;
  const hasSession: boolean = request.cookies.has(SESSION_COOKIE_NAME);
  const isLoginPage: boolean = pathname === ROUTES.LOGIN;

  if (isLoginPage && hasSession) {
    return NextResponse.redirect(new URL(ROUTES.HOME, request.url));
  }

  if (!isLoginPage && !hasSession) {
    const loginUrl = new URL(ROUTES.LOGIN, request.url);

    if (pathname !== ROUTES.HOME)
      loginUrl.searchParams.set(LOGIN_REDIRECT_PARAM, `${pathname}${search}`);

    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
};

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
