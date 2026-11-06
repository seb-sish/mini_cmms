import { UserRole } from "./types";

export interface IRolePermissions {
  canManageUsers: boolean;
  canViewEquipment: boolean;
  canManageEquipment: boolean;
  canViewFaults: boolean;
  canCreateFault: boolean;
  canViewPlans: boolean;
  canManagePlans: boolean;
  canViewSchedules: boolean;
  canViewWorkOrders: boolean;
  canCreateWorkOrder: boolean;
  canCreatePlannedWorkOrder: boolean;
  canManageWorkOrders: boolean;
  canExecuteWorkOrders: boolean;
  canViewHistory: boolean;
  canViewNotifications: boolean;
}

const NO_PERMISSIONS: IRolePermissions = {
  canManageUsers: false,
  canViewEquipment: false,
  canManageEquipment: false,
  canViewFaults: false,
  canCreateFault: false,
  canViewPlans: false,
  canManagePlans: false,
  canViewSchedules: false,
  canViewWorkOrders: false,
  canCreateWorkOrder: false,
  canCreatePlannedWorkOrder: false,
  canManageWorkOrders: false,
  canExecuteWorkOrders: false,
  canViewHistory: false,
  canViewNotifications: false,
};

export const ROLE_PERMISSIONS: Record<UserRole, IRolePermissions> = {
  [UserRole.ADMIN]: {
    ...NO_PERMISSIONS,
    canManageUsers: true,
  },
  [UserRole.ENGINEER]: {
    ...NO_PERMISSIONS,
    canViewEquipment: true,
    canManageEquipment: true,
    canViewFaults: true,
    canCreateFault: true,
    canViewPlans: true,
    canManagePlans: true,
    canViewSchedules: true,
    canViewWorkOrders: true,
    canCreateWorkOrder: true,
    canCreatePlannedWorkOrder: true,
    canManageWorkOrders: true,
    canViewHistory: true,
    canViewNotifications: true,
  },
  [UserRole.TECHNICIAN]: {
    ...NO_PERMISSIONS,
    canViewEquipment: true,
    canViewFaults: true,
    canViewPlans: true,
    canViewSchedules: true,
    canViewWorkOrders: true,
    canExecuteWorkOrders: true,
    canViewHistory: true,
    canViewNotifications: true,
  },
  [UserRole.OPERATOR]: {
    ...NO_PERMISSIONS,
    canViewEquipment: true,
    canViewFaults: true,
    canCreateFault: true,
    canViewWorkOrders: true,
    canCreateWorkOrder: true,
    canViewHistory: true,
  },
};

export const getRolePermissions = (role: UserRole): IRolePermissions =>
  ROLE_PERMISSIONS[role];
