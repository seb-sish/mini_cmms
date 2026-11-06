import Icon from "@shared/ui/icon";
import { IconName } from "@shared/ui/icon";
import { IconSize } from "@shared/ui/icon";
import { ReactElement } from "react";
import { ReactNode } from "react";
import "./style.css";

interface IEmptyStateProps {
  title: string;
  description?: string;
  icon?: IconName;
  action?: ReactNode;
}

const EmptyState = ({
  title,
  description,
  icon = IconName.SEARCH,
  action,
}: IEmptyStateProps): ReactElement => {
  return (
    <div className="empty-state">
      <span className="empty-state-icon">
        <Icon name={icon} size={IconSize.LARGE} />
      </span>
      <h3 className="heading-medium">{title}</h3>
      {description && (
        <p className="empty-state-description text-subtle">{description}</p>
      )}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
};

export default EmptyState;
