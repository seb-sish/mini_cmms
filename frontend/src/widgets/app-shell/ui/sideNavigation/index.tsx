"use client";

import Link from "next/link";
import Icon from "@shared/ui/icon";
import { isNavigationItemActive } from "../../model/navigation";
import { NAVIGATION_ITEMS } from "../../model/navigation";
import { useViewerPermissions } from "@entities/user";
import { usePathname } from "next/navigation";
import { ROUTES } from "@shared/config";
import { ReactElement } from "react";
import "./style.css";

const SideNavigation = (): ReactElement => {
  const pathname: string = usePathname() ?? ROUTES.HOME;
  const permissions = useViewerPermissions();
  const visibleItems = NAVIGATION_ITEMS.filter((item) =>
    item.isVisible(permissions)
  );

  return (
    <nav className="side-navigation" aria-label="Основная навигация">
      <ul className="side-navigation-list">
        {visibleItems.map((item) => {
          const isActive: boolean = isNavigationItemActive(pathname, item.href);

          return (
            <li key={item.href}>
              <Link
                className={`side-navigation-link ${isActive ? "active" : ""}`}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};

export default SideNavigation;
