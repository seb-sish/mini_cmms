import { SESSION_COOKIE_NAME } from "@shared/config";
import { NextResponse } from "next/server";

interface ISessionCookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  expires: Date;
}

export const buildSessionCookieOptions = (
  expiresAt: string
): ISessionCookieOptions => ({
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  path: "/",
  expires: new Date(expiresAt),
});

export const setSessionCookie = (
  response: NextResponse,
  token: string,
  expiresAt: string
): void => {
  response.cookies.set(
    SESSION_COOKIE_NAME,
    token,
    buildSessionCookieOptions(expiresAt)
  );
};

export const clearSessionCookie = (response: NextResponse): void => {
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
};
