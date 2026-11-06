import { LOGIN_REDIRECT_PARAM } from "@shared/config";
import { LoginPage } from "@pages/login";
import { ReactElement } from "react";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Вход",
};

interface ILoginRouteProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

const LoginRoute = async ({
  searchParams,
}: ILoginRouteProps): Promise<ReactElement> => {
  const nextParam = (await searchParams)[LOGIN_REDIRECT_PARAM];

  return (
    <LoginPage nextPath={typeof nextParam === "string" ? nextParam : null} />
  );
};

export default LoginRoute;
