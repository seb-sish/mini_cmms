"use client";

import Button from "@shared/ui/button";
import Spinner from "@shared/ui/spinner";
import TopNavigation from "../topNavigation";
import SideNavigation from "../sideNavigation";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { SpinnerSize } from "@shared/ui/spinner";
import { useViewerQuery } from "@entities/user";
import { ViewerProvider } from "@entities/user";
import { getErrorMessage } from "@shared/api";
import { ApiErrorCode } from "@shared/api";
import { hasErrorCode } from "@shared/api";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IAppShellProps {
  children: ReactNode;
}

const AppShell = ({ children }: IAppShellProps): ReactElement => {
  const { data: viewer, error, refetch } = useViewerQuery();

  const handleRetry = () => {
    refetch();
  };

  if (error && !hasErrorCode(error, ApiErrorCode.UNAUTHENTICATED)) {
    return (
      <div className="app-shell-state">
        <SectionMessage
          appearance={SectionMessageAppearance.ERROR}
          title="Не удалось загрузить данные пользователя"
          actions={<Button label="Повторить" onClick={handleRetry} />}
        >
          <p>{getErrorMessage(error)}</p>
        </SectionMessage>
      </div>
    );
  }

  if (!viewer) {
    return (
      <div className="app-shell-state">
        <Spinner size={SpinnerSize.LARGE} label="Проверка сессии" />
      </div>
    );
  }

  return (
    <ViewerProvider viewer={viewer}>
      <div className="app-shell">
        <TopNavigation />
        <div className="app-shell-body">
          <SideNavigation />
          <main className="app-shell-content" id="main-content">
            {children}
          </main>
        </div>
      </div>
    </ViewerProvider>
  );
};

export default AppShell;
