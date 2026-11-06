import { getRolePermissions } from "./permissions";
import { UserRole } from "./types";

describe("role permissions", () => {
  it("separates administrator from production data", () => {
    const permissions = getRolePermissions(UserRole.ADMIN);

    expect(permissions.canManageUsers).toBe(true);
    expect(permissions.canViewEquipment).toBe(false);
    expect(permissions.canViewWorkOrders).toBe(false);
    expect(permissions.canViewHistory).toBe(false);
  });

  it("gives engineer full production management without user management", () => {
    const permissions = getRolePermissions(UserRole.ENGINEER);

    expect(permissions.canManageUsers).toBe(false);
    expect(permissions.canManageEquipment).toBe(true);
    expect(permissions.canManagePlans).toBe(true);
    expect(permissions.canCreatePlannedWorkOrder).toBe(true);
    expect(permissions.canManageWorkOrders).toBe(true);
    expect(permissions.canExecuteWorkOrders).toBe(false);
  });

  it("lets technician execute work but not manage plans or create orders", () => {
    const permissions = getRolePermissions(UserRole.TECHNICIAN);

    expect(permissions.canExecuteWorkOrders).toBe(true);
    expect(permissions.canViewSchedules).toBe(true);
    expect(permissions.canManagePlans).toBe(false);
    expect(permissions.canCreateWorkOrder).toBe(false);
    expect(permissions.canCreateFault).toBe(false);
  });

  it("lets operator register faults and repair requests only", () => {
    const permissions = getRolePermissions(UserRole.OPERATOR);

    expect(permissions.canCreateFault).toBe(true);
    expect(permissions.canCreateWorkOrder).toBe(true);
    expect(permissions.canCreatePlannedWorkOrder).toBe(false);
    expect(permissions.canViewPlans).toBe(false);
    expect(permissions.canViewSchedules).toBe(false);
    expect(permissions.canViewNotifications).toBe(false);
  });
});
