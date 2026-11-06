import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

export const enum SectionMessageAppearance {
  INFORMATION = "information",
  WARNING = "warning",
  ERROR = "error",
  SUCCESS = "success",
  DISCOVERY = "discovery",
}

interface ISectionMessageProps {
  appearance?: SectionMessageAppearance;
  title?: string;
  children?: ReactNode;
  actions?: ReactNode;
}

const APPEARANCE_ICONS: Record<SectionMessageAppearance, IconName> = {
  [SectionMessageAppearance.INFORMATION]: IconName.INFO,
  [SectionMessageAppearance.WARNING]: IconName.WARNING,
  [SectionMessageAppearance.ERROR]: IconName.ERROR,
  [SectionMessageAppearance.SUCCESS]: IconName.SUCCESS,
  [SectionMessageAppearance.DISCOVERY]: IconName.INFO,
};

const SectionMessage = ({
  appearance = SectionMessageAppearance.INFORMATION,
  title,
  children,
  actions,
}: ISectionMessageProps): ReactElement => {
  const isAlert: boolean =
    appearance === SectionMessageAppearance.ERROR ||
    appearance === SectionMessageAppearance.WARNING;

  return (
    <section
      className={`section-message ${appearance}`}
      role={isAlert ? "alert" : "status"}
    >
      <span className="section-message-icon">
        <Icon name={APPEARANCE_ICONS[appearance]} />
      </span>
      <div className="section-message-content">
        {title && <h2 className="heading-small">{title}</h2>}
        {children && <div className="section-message-body">{children}</div>}
        {actions && <div className="section-message-actions">{actions}</div>}
      </div>
    </section>
  );
};

export default SectionMessage;
