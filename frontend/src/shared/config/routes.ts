export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  EQUIPMENT: "/equipment",
  FAULTS: "/faults",
  MAINTENANCE_PLANS: "/maintenance-plans",
  SCHEDULES: "/schedules",
  WORK_ORDERS: "/work-orders",
  HISTORY: "/history",
  NOTIFICATIONS: "/notifications",
  USERS: "/users",
} as const;

export const LOGIN_REDIRECT_PARAM: string = "next";

export const buildEquipmentRoute = (equipmentId: string): string =>
  `${ROUTES.EQUIPMENT}/${equipmentId}`;

export const buildFaultRoute = (faultId: string): string =>
  `${ROUTES.FAULTS}/${faultId}`;

export const buildMaintenancePlanRoute = (planId: string): string =>
  `${ROUTES.MAINTENANCE_PLANS}/${planId}`;

export const buildWorkOrderRoute = (workOrderId: string): string =>
  `${ROUTES.WORK_ORDERS}/${workOrderId}`;

export const buildHistoryRoute = (historyId: string): string =>
  `${ROUTES.HISTORY}/${historyId}`;

export const buildUserRoute = (userId: string): string =>
  `${ROUTES.USERS}/${userId}`;

export const buildLoginRoute = (nextPath?: string): string => {
  if (!nextPath || nextPath === ROUTES.HOME) return ROUTES.LOGIN;

  return `${ROUTES.LOGIN}?${LOGIN_REDIRECT_PARAM}=${encodeURIComponent(nextPath)}`;
};

export const resolveSafeRedirect = (nextPath: string | null): string => {
  if (!nextPath || !nextPath.startsWith("/") || nextPath.startsWith("//")) {
    return ROUTES.HOME;
  }

  return nextPath;
};
