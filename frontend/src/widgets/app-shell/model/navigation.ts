import { IRolePermissions } from "@entities/user";
import { IconName } from "@shared/ui/icon";
import { ROUTES } from "@shared/config";

export interface INavigationItem {
  label: string;
  href: string;
  icon: IconName;
  isVisible: (permissions: IRolePermissions) => boolean;
}

export const NAVIGATION_ITEMS: INavigationItem[] = [
  {
    label: "Обзор",
    href: ROUTES.HOME,
    icon: IconName.DASHBOARD,
    isVisible: (permissions) => !permissions.canManageUsers,
  },
  {
    label: "Заявки",
    href: ROUTES.WORK_ORDERS,
    icon: IconName.WORK_ORDER,
    isVisible: (permissions) => permissions.canViewWorkOrders,
  },
  {
    label: "Оборудование",
    href: ROUTES.EQUIPMENT,
    icon: IconName.EQUIPMENT,
    isVisible: (permissions) => permissions.canViewEquipment,
  },
  {
    label: "Неисправности",
    href: ROUTES.FAULTS,
    icon: IconName.FAULT,
    isVisible: (permissions) => permissions.canViewFaults,
  },
  {
    label: "График ТО",
    href: ROUTES.SCHEDULES,
    icon: IconName.CALENDAR,
    isVisible: (permissions) => permissions.canViewSchedules,
  },
  {
    label: "Регламенты ТО",
    href: ROUTES.MAINTENANCE_PLANS,
    icon: IconName.PLAN,
    isVisible: (permissions) => permissions.canViewPlans,
  },
  {
    label: "История работ",
    href: ROUTES.HISTORY,
    icon: IconName.HISTORY,
    isVisible: (permissions) => permissions.canViewHistory,
  },
  {
    label: "Уведомления",
    href: ROUTES.NOTIFICATIONS,
    icon: IconName.BELL,
    isVisible: (permissions) => permissions.canViewNotifications,
  },
  {
    label: "Пользователи",
    href: ROUTES.USERS,
    icon: IconName.USERS,
    isVisible: (permissions) => permissions.canManageUsers,
  },
];

export const isNavigationItemActive = (
  pathname: string,
  href: string
): boolean =>
  href === ROUTES.HOME
    ? pathname === ROUTES.HOME
    : pathname === href || pathname.startsWith(`${href}/`);
