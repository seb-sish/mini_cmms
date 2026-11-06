"use client";

import Icon from "@shared/ui/icon";
import { useQueryClient } from "@tanstack/react-query";
import { resolveSafeRedirect } from "@shared/config";
import { APP_DESCRIPTION } from "@shared/config";
import { ILoginResponse } from "@features/auth";
import { useRouter } from "next/navigation";
import { LoginForm } from "@features/auth";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { APP_NAME } from "@shared/config";
import { userKeys } from "@entities/user";
import { ReactElement } from "react";
import "./style.css";

interface ILoginPageProps {
  nextPath: string | null;
}

const LoginPage = ({ nextPath }: ILoginPageProps): ReactElement => {
  const router = useRouter();
  const queryClient = useQueryClient();

  const handleLoginSuccess = (response: ILoginResponse) => {
    queryClient.clear();
    queryClient.setQueryData(userKeys.viewer(), response.user);
    router.replace(resolveSafeRedirect(nextPath));
  };

  return (
    <div className="login-page">
      <div className="login-page-card">
        <div className="login-page-brand">
          <span className="login-page-logo" aria-hidden="true">
            <Icon name={IconName.WRENCH} size={IconSize.LARGE} />
          </span>
          <div>
            <h1 className="heading-xlarge">{APP_NAME}</h1>
            <p className="text-subtle">{APP_DESCRIPTION}</p>
          </div>
        </div>
        <h2 className="heading-medium">Вход в систему</h2>
        <LoginForm onSuccess={handleLoginSuccess} />
        <p className="body-small text-subtlest">
          Учётные записи создаёт администратор. Если нет доступа, обратитесь к
          администратору системы.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
