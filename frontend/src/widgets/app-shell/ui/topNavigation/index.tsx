"use client";

import Link from "next/link";
import Icon from "@shared/ui/icon";
import Avatar from "@shared/ui/avatar";
import Button from "@shared/ui/button";
import { useViewerPermissions } from "@entities/user";
import { ButtonAppearance } from "@shared/ui/button";
import { USER_ROLE_LABELS } from "@entities/user";
import { AvatarSize } from "@shared/ui/avatar";
import { useLogout } from "@features/auth";
import { IconName } from "@shared/ui/icon";
import { useViewer } from "@entities/user";
import { APP_NAME } from "@shared/config";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import "./style.css";

const TopNavigation = (): ReactElement => {
  const viewer = useViewer();
  const permissions = useViewerPermissions();
  const logoutMutation = useLogout();

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <header className="top-navigation">
      <Link className="top-navigation-brand" href={ROUTES.HOME}>
        <span className="top-navigation-logo" aria-hidden="true">
          <Icon name={IconName.WRENCH} />
        </span>
        <span className="top-navigation-title">{APP_NAME}</span>
      </Link>
      <div className="top-navigation-right">
        {permissions.canViewNotifications && (
          <Link
            className="top-navigation-icon-link"
            href={ROUTES.NOTIFICATIONS}
            aria-label="Уведомления"
            title="Уведомления"
          >
            <Icon name={IconName.BELL} />
          </Link>
        )}
        <div className="top-navigation-user">
          <Avatar name={viewer.login} size={AvatarSize.MEDIUM} />
          <div className="top-navigation-user-info">
            <span className="top-navigation-user-login">{viewer.login}</span>
            <span className="top-navigation-user-role body-small">
              {USER_ROLE_LABELS[viewer.role]}
            </span>
          </div>
        </div>
        <div className="top-navigation-logout">
          <Button
            label="Выйти"
            appearance={ButtonAppearance.SUBTLE}
            iconBefore={IconName.LOGOUT}
            isLoading={logoutMutation.isPending}
            onClick={handleLogout}
          />
        </div>
      </div>
    </header>
  );
};

export default TopNavigation;
