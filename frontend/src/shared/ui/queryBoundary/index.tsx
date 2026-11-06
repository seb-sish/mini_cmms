"use client";

import Button from "@shared/ui/button";
import Spinner from "@shared/ui/spinner";
import SectionMessage from "@shared/ui/sectionMessage";
import { SectionMessageAppearance } from "@shared/ui/sectionMessage";
import { SpinnerSize } from "@shared/ui/spinner";
import { getErrorMessage } from "@shared/api";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IQueryBoundaryProps {
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
  children: ReactNode;
}

const QueryBoundary = ({
  isLoading,
  error,
  onRetry,
  children,
}: IQueryBoundaryProps): ReactElement => {
  if (isLoading) {
    return (
      <div className="query-boundary-loading">
        <Spinner size={SpinnerSize.LARGE} />
      </div>
    );
  }

  if (error) {
    return (
      <SectionMessage
        appearance={SectionMessageAppearance.ERROR}
        title="Не удалось загрузить данные"
        actions={onRetry && <Button label="Повторить" onClick={onRetry} />}
      >
        <p>{getErrorMessage(error)}</p>
      </SectionMessage>
    );
  }

  return <>{children}</>;
};

export default QueryBoundary;
